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

    bare = capsules["bare_function"]
    assert bare["self_description_band"] == "locator_only"
    assert bare["has_docstring"] is False
    assert bare["authored_contract_atoms"] == []
    assert bare["authored_atom_count"] == 0

    klass = capsules["AuthoredClass"]
    assert klass["self_description_band"] == "authored"
    assert klass["symbol_kind"] == "class"
    assert klass["authored_contract_atoms"] == ["Teleology"]


def test_self_description_coverage_block_reports_honest_split(tmp_path: Path) -> None:
    project = _coverage_project(tmp_path)
    lens = project_substrate.python_lens(project, write_state=False)

    coverage = lens["self_description_coverage"]
    assert coverage["schema_version"] == "microcosm_python_self_description_coverage_v1"
    # authored_function, AuthoredClass authored; bare_function, test_value locator-only.
    assert coverage["total_symbol_capsules"] == 4
    assert coverage["authored_symbol_capsules"] == 2
    assert coverage["locator_only_symbol_capsules"] == 2
    assert coverage["authored_ratio"] == 0.5
    assert coverage["coverage_band"] == "mixed_self_description"
    assert coverage["authored_atom_histogram"]["Teleology"] == 2
    assert coverage["authored_atom_histogram"]["Guarantee"] == 1
    assert coverage["by_source_class"]["source_module"] == {
        "total": 3,
        "authored": 2,
        "locator_only": 1,
    }
    assert coverage["by_source_class"]["test_module"]["authored"] == 0
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
