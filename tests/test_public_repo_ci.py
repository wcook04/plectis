from __future__ import annotations

import re
from pathlib import Path
import tomllib


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = MICROCOSM_ROOT / ".github/workflows/ci.yml"
PYPROJECT = MICROCOSM_ROOT / "pyproject.toml"


def _setuptools_floor(build_requires: list[str]) -> tuple[int, ...]:
    for requirement in build_requires:
        match = re.match(r"setuptools\s*>=\s*([0-9]+(?:\.[0-9]+)*)", requirement, re.I)
        if match:
            return tuple(int(part) for part in match.group(1).split("."))
    raise AssertionError("build-system.requires must declare a setuptools lower bound")


def _ci_python_versions(workflow: str) -> tuple[str, ...]:
    match = re.search(r"python-version:\s*\[([^\]]+)\]", workflow)
    assert match, "CI workflow must declare an inline python-version matrix"
    return tuple(
        part.strip().strip("\"'")
        for part in match.group(1).split(",")
        if part.strip()
    )


def test_public_repo_has_inspectable_github_actions_ci() -> None:
    assert CI_WORKFLOW.is_file()

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "name: CI",
        "pull_request:",
        "workflow_dispatch:",
        "permissions:",
        "contents: read",
        'python-version: ["3.11", "3.12", "3.13"]',
        "actions/checkout@v4",
        "actions/setup-python@v5",
        "run: make ci",
    ):
        assert required in workflow

    for duplicated_command in (
        'python -m pip install -e ".[test]"',
        "python -m pytest",
        "microcosm hello .",
        "python -m microcosm_core --version",
        "microcosm stripping-guard",
    ):
        assert duplicated_command not in workflow


def test_pyproject_python_classifiers_match_ci_matrix() -> None:
    workflow = CI_WORKFLOW.read_text(encoding="utf-8")
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    matrix_versions = set(_ci_python_versions(workflow))
    classifiers = set(pyproject["project"]["classifiers"])
    python_classifiers = {
        classifier.rsplit(" :: ", 1)[-1]
        for classifier in classifiers
        if classifier.startswith("Programming Language :: Python :: 3.")
    }

    assert pyproject["project"]["requires-python"] == ">=3.11"
    assert "Programming Language :: Python :: 3" in classifiers
    assert python_classifiers == matrix_versions
    for version in matrix_versions:
        assert f"Programming Language :: Python :: {version}" in classifiers


def test_pyproject_license_metadata_matches_declared_build_backend_floor() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert pyproject["build-system"]["build-backend"] == "setuptools.build_meta"
    assert _setuptools_floor(pyproject["build-system"]["requires"]) >= (77, 0, 3)
    assert pyproject["project"]["license"] == "Apache-2.0"
    assert pyproject["project"]["license-files"] == ["LICENSE"]
    assert (
        "License :: OSI Approved :: Apache Software License"
        not in pyproject["project"]["classifiers"]
    )


def test_pyproject_urls_point_to_current_public_repository() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert pyproject["project"]["urls"] == {
        "Homepage": "https://github.com/wcook04/zenith",
        "Documentation": (
            "https://github.com/wcook04/zenith/blob/main/"
            "microcosm-substrate/README.md"
        ),
        "Source": "https://github.com/wcook04/zenith/tree/main/microcosm-substrate",
        "Issues": "https://github.com/wcook04/zenith/issues",
        "Repository": "https://github.com/wcook04/zenith",
    }
    assert "Macro-System" not in pyproject["project"]["urls"]
    assert all(
        "ai-workflow-proof" not in url
        for url in pyproject["project"]["urls"].values()
    )
