"""Coverage tests for the python-lens self-description band.

Proves the lens is honest about which symbol capsules are authored (carry a
docstring with std_python contract atoms) versus locator_only (path/name/kind/
span only), without exporting any docstring prose.
"""
from __future__ import annotations

import json
from pathlib import Path

from microcosm_core import cli, project_substrate
from microcosm_core.public_payload_boundary import SOURCE_OPEN_BODY_POLICY


AUTHORED_MODULE = '''"""Module docstring.

- Teleology: prove authored capsules are detected.
"""


def authored_function():
    """Do the authored thing.

    - Teleology: exists to be classified as authored.
    - Guarantee: returns 1 after success.
    - Fails: never -> None -> None.
    """
    return 1


def bare_function():
    return 2


class AuthoredClass:
    """Coordinator.

    - Teleology: owns the authored-class path.
    """
'''


def _coverage_project(tmp_path: Path) -> Path:
    project = tmp_path / "coverage_project"
    (project / "src/cov_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Coverage\n\nLocal proof project.\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "cov-app"\nversion = "0.1.0"\n',
        encoding="utf-8",
    )
    (project / "src/cov_app/__init__.py").write_text("VALUE = 1\n", encoding="utf-8")
    (project / "src/cov_app/core.py").write_text(AUTHORED_MODULE, encoding="utf-8")
    (project / "tests/test_smoke.py").write_text(
        "from cov_app import VALUE\n\n\ndef test_value():\n    assert VALUE == 1\n",
        encoding="utf-8",
    )
    return project


def test_symbol_capsules_carry_authored_vs_locator_bands(tmp_path: Path) -> None:
    project = _coverage_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)

    capsules = {row["symbol_name"]: row for row in lens["symbol_capsule_rows"]}

    authored = capsules["authored_function"]
    assert authored["self_description_band"] == "authored"
    assert authored["has_docstring"] is True
    assert set(authored["authored_contract_atoms"]) == {"Teleology", "Guarantee", "Fails"}
    assert authored["authored_atom_count"] == 3
    assert authored["source_class"] == "source_module"
    # No docstring prose is exported onto the capsule row.
    assert authored["source_bodies_exported"] is False
    encoded_row = json.dumps(authored)
    assert "Do the authored thing" not in encoded_row
    assert "returns 1 after success" not in encoded_row

    # The full triad earns real coverage.
    assert authored["quality_tier"] == "authored_contract"
    assert authored["is_real_coverage"] is True

    bare = capsules["bare_function"]
    assert bare["self_description_band"] == "locator_only"
    assert bare["has_docstring"] is False
    assert bare["authored_contract_atoms"] == []
    assert bare["authored_atom_count"] == 0
    assert bare["quality_tier"] == "locator_only"
    assert bare["is_real_coverage"] is False

    klass = capsules["AuthoredClass"]
    assert klass["self_description_band"] == "authored"
    assert klass["symbol_kind"] == "class"
    assert klass["authored_contract_atoms"] == ["Teleology"]
    # Teleology-only is authored but below the real-coverage floor — un-gameable.
    assert klass["quality_tier"] == "authored_minimal"
    assert klass["is_real_coverage"] is False


def test_bare_docstring_cannot_inflate_the_scoreboard(tmp_path: Path) -> None:
    # A prose docstring with no contract atoms must NOT count as real coverage.
    project = tmp_path / "bare_project"
    (project / "src/bare_app").mkdir(parents=True)
    (project / "tests").mkdir()
    (project / "README.md").write_text("# Bare\n", encoding="utf-8")
    (project / "pyproject.toml").write_text(
        '[project]\nname = "bare-app"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (project / "src/bare_app/__init__.py").write_text("V = 1\n", encoding="utf-8")
    (project / "src/bare_app/core.py").write_text(
        'def bare():\n    """Does a thing with no contract atoms at all."""\n    return 1\n',
        encoding="utf-8",
    )
    lens = project_substrate.python_lens(project, write_state=False)
    capsule = next(
        row for row in lens["symbol_capsule_rows"] if row["symbol_name"] == "bare"
    )
    assert capsule["has_docstring"] is True
    assert capsule["self_description_band"] == "authored"
    assert capsule["quality_tier"] == "authored_bare"
    assert capsule["is_real_coverage"] is False
    assert lens["self_description_coverage"]["real_coverage_symbol_capsules"] == 0


def test_self_description_coverage_block_reports_honest_split(tmp_path: Path) -> None:
    project = _coverage_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)

    coverage = lens["self_description_coverage"]
    assert coverage["schema_version"] == "microcosm_python_self_description_coverage_v2"
    # authored_function, AuthoredClass authored; bare_function, test_value locator-only.
    assert coverage["total_symbol_capsules"] == 4
    assert coverage["authored_symbol_capsules"] == 2
    assert coverage["locator_only_symbol_capsules"] == 2
    assert coverage["authored_ratio"] == 0.5
    assert coverage["coverage_band"] == "mixed_self_description"
    # Only authored_function clears the triad floor; AuthoredClass is minimal.
    assert coverage["real_coverage_symbol_capsules"] == 1
    assert coverage["real_coverage_ratio"] == 0.25
    assert coverage["quality_band_counts"]["authored_contract"] == 1
    assert coverage["quality_band_counts"]["authored_minimal"] == 1
    assert coverage["quality_band_counts"]["locator_only"] == 2
    assert coverage["authored_atom_histogram"]["Teleology"] == 2
    assert coverage["authored_atom_histogram"]["Guarantee"] == 1
    assert coverage["by_source_class"]["source_module"] == {
        "total": 3,
        "authored": 2,
        "locator_only": 1,
    }
    assert coverage["by_source_class"]["test_module"]["authored"] == 0
    assert coverage["release_critical_coverage"]["critical_symbols"] >= 0
    assert coverage["source_bodies_exported"] is False

    # The same block is mirrored into the navigation assay and implementation atlas.
    assert lens["navigation_assay"]["self_description_coverage"] == coverage
    assert (
        lens["implementation_atlas"]["python_navigation_assay"][
            "self_description_coverage"
        ]
        == coverage
    )


def test_self_description_contract_block_names_donor_and_residual(tmp_path: Path) -> None:
    project = _coverage_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)

    contract = lens["self_description_contract"]
    assert (
        contract["donor_standard_ref"]
        == "macro:codex/standards/std_python.py::navigation_contract"
    )
    assert "Teleology" in contract["contract_atom_vocabulary"]
    assert contract["self_description_bands"] == ["authored", "locator_only"]


def test_compact_cli_defers_coverage_honestly(capsys, tmp_path: Path) -> None:
    # The default compact card defers the full symbol walk, so coverage must
    # report the deferral rather than claiming an empty/no_symbols tree.
    project = _coverage_project(tmp_path)
    assert cli.main(["python-lens", project.as_posix()]) == 0
    payload = json.loads(capsys.readouterr().out)
    coverage = payload["self_description_coverage"]
    assert coverage["scan_deferred"] is True
    assert coverage["coverage_band"] == "deferred_first_screen_summary"


def test_full_cli_reports_honest_split_and_keeps_payload_boundary_vocab(
    capsys, tmp_path: Path
) -> None:
    project = _coverage_project(tmp_path)
    assert cli.main(["python-lens", "--full", project.as_posix()]) == 0
    payload = json.loads(capsys.readouterr().out)
    encoded = json.dumps(payload, sort_keys=True)
    assert "payload_boundary" in encoded
    assert SOURCE_OPEN_BODY_POLICY in encoded
    assert payload["authority_ceiling"]["source_bodies_exported"] is False
    coverage = payload["self_description_coverage"]
    assert coverage["scan_deferred"] is False
    assert coverage["coverage_band"] == "mixed_self_description"
    assert coverage["authored_symbol_capsules"] == 2


def test_authoring_queue_ranks_owned_symbols_excludes_done_and_imports(
    tmp_path: Path,
) -> None:
    project = _coverage_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)

    queue = lens["authoring_queue"]
    assert queue["schema_version"] == "microcosm_code_lens_authoring_queue_v1"
    # 3 owned symbols (authored_function, bare_function, AuthoredClass); the test
    # function is excluded as non-owned.
    assert queue["owned_symbol_total"] == 3
    # authored_function already clears the floor -> not in the work-list.
    assert queue["owned_real_coverage"] == 1
    assert queue["owned_needing_authoring"] == 2
    queued_names = {row["symbol_name"] for row in queue["queue_rows"]}
    assert "authored_function" not in queued_names
    assert "bare_function" in queued_names
    assert "AuthoredClass" in queued_names
    assert "test_value" not in queued_names
    # Every queued row carries a batch + criticality + the source boundary.
    for row in queue["queue_rows"]:
        assert row["suggested_batch"].startswith(("A_", "B_", "C_", "D_", "E_", "F_", "G_"))
        assert row["criticality_class"] in project_substrate.CODE_LENS_CRITICALITY_CLASSES
        assert row["source_bodies_exported"] is False


def test_authoring_queue_excludes_imported_fixture_bundles(tmp_path: Path) -> None:
    # An imported bundle under fixtures/.../source_modules/ has a critical-looking
    # main(), but it is custody, not owned compliance: it must NOT enter the queue
    # or count as a release-critical owned symbol.
    project = _coverage_project(tmp_path)
    bundle = project / "fixtures/demo/input/source_modules/tools/meta"
    bundle.mkdir(parents=True)
    (bundle / "runner.py").write_text(
        "def main():\n    return 0\n", encoding="utf-8"
    )
    lens = project_substrate.python_lens(project, write_state=False)

    queue = lens["authoring_queue"]
    queued_paths = {row["path"] for row in queue["queue_rows"]}
    assert not any("source_modules" in p for p in queued_paths)
    # owned_symbol_total still reflects only the 3 owned cov_app symbols.
    assert queue["owned_symbol_total"] == 3
    # The bundle main() is classified imported, not a release-critical public entrypoint.
    cls, _rank = project_substrate._code_lens_criticality(
        "fixtures/demo/input/source_modules/tools/meta/runner.py", "main", "python_module"
    )
    assert cls == "trivial_or_imported"


def test_coupling_governed_in_tree_zones_excluded_from_owned_authoring() -> None:
    # organs/, macro_tools/, engine_room/ carry exact-copy macro bodies that must
    # byte-match upstream (the macro_body_import_floor coupling gate). Authoring
    # them breaks `microcosm spine`, so they must be excluded from the owned queue
    # even though they live under src/ with main()/validate_* entrypoints.
    for path in (
        "src/microcosm_core/organs/batch11_saturation_engines_capsule.py",
        "src/microcosm_core/macro_tools/bridge_resume.py",
        "src/microcosm_core/engine_room/bridge_campaign_dag.py",
    ):
        assert project_substrate._is_imported_source_bundle(path) is True
        cls, _rank = project_substrate._code_lens_criticality(path, "main", "source_module")
        assert cls == "trivial_or_imported"
    # A genuinely-owned native src file is NOT excluded.
    assert (
        project_substrate._is_imported_source_bundle(
            "src/microcosm_core/runtime_shell.py"
        )
        is False
    )


def test_manifest_custody_oracle_excludes_runner_outside_dir_heuristic(tmp_path: Path) -> None:
    # An organ runner can live OUTSIDE organs/ (real example: organ
    # pattern_assimilation_step -> microcosm_core.validators.acceptance). The
    # directory heuristic would miss it; the manifest oracle must exclude it, or
    # Batch B (validators) would author custody code and break `microcosm spine`.
    project = _coverage_project(tmp_path)
    (project / "core").mkdir()
    (project / "core/organ_registry.json").write_text(
        json.dumps(
            {
                "implemented_organs": [
                    {"organ_id": "demo_organ", "runner": "microcosm_core.special.custody_runner"}
                ]
            }
        ),
        encoding="utf-8",
    )
    custody_dir = project / "src/microcosm_core/special"
    custody_dir.mkdir(parents=True)
    (custody_dir / "custody_runner.py").write_text(
        "def main():\n    return 0\n", encoding="utf-8"
    )

    custody = project_substrate._load_manifest_custody_paths(project)
    assert "src/microcosm_core/special/custody_runner.py" in custody
    # The directory heuristic alone does NOT catch it (it's not under organs/).
    assert (
        project_substrate._is_imported_source_bundle(
            "src/microcosm_core/special/custody_runner.py"
        )
        is False
    )
    # But the manifest oracle does — basis is manifest_provenance.
    assert (
        project_substrate._custody_basis(
            "src/microcosm_core/special/custody_runner.py", custody
        )
        == "manifest_provenance"
    )

    lens = project_substrate.python_lens(project, write_state=False)
    queue = lens["authoring_queue"]
    queued = {r["path"] for r in queue["queue_rows"]}
    # The manifest-declared runner is excluded from the owned queue.
    assert "src/microcosm_core/special/custody_runner.py" not in queued
    # ...and the exclusion is recorded with an honest custody_basis.
    classification = queue["custody_classification"]
    assert classification["by_basis"].get("manifest_provenance", 0) >= 1
    assert classification["manifest_custody_paths_loaded"] >= 1


def test_full_cli_carries_queue_and_compact_defers_it(capsys, tmp_path: Path) -> None:
    project = _coverage_project(tmp_path)
    # --full emits the raw payload: the campaign consumes the full queue_rows.
    assert cli.main(["python-lens", "--full", project.as_posix()]) == 0
    full_payload = json.loads(capsys.readouterr().out)
    full_queue = full_payload["authoring_queue"]
    assert full_queue["owned_needing_authoring"] == 2
    assert len(full_queue["queue_rows"]) == 2

    # Compact mode defers the symbol walk; the queue card drops the heavy full
    # list and reports nothing to author over the unscanned tree.
    assert cli.main(["python-lens", project.as_posix()]) == 0
    compact_payload = json.loads(capsys.readouterr().out)
    assert compact_payload["self_description_coverage"]["scan_deferred"] is True
    compact_card = compact_payload["authoring_queue"]
    assert "queue_rows" not in compact_card
    assert compact_card["owned_needing_authoring"] == 0
