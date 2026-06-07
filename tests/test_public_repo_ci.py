from __future__ import annotations

import re
from pathlib import Path
import tomllib

import pytest


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = MICROCOSM_ROOT / ".github/workflows/ci.yml"
PYPROJECT = MICROCOSM_ROOT / "pyproject.toml"
SHA_PIN_RE = re.compile(r"^[a-f0-9]{40}$", re.I)
PUBLIC_ACTION_TAG_RE = re.compile(
    r"^\s*#\s*Public action tag:\s*"
    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<tag>[^\s.]+)"
)
GITHUB_ACTION_USES_RE = re.compile(
    r"^\s*uses:\s*"
    r"(?P<repo>[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)@(?P<ref>[^\s#]+)"
)


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


def _github_action_rows(workflow: str) -> tuple[dict[str, str | bool | int], ...]:
    lines = workflow.splitlines()
    rows: list[dict[str, str | bool | int]] = []
    for index, line in enumerate(lines):
        uses_match = GITHUB_ACTION_USES_RE.match(line)
        if not uses_match:
            continue

        public_tag = ""
        public_repo = ""
        comment_line = 0
        for prior_index in range(index - 1, -1, -1):
            prior = lines[prior_index].strip()
            if not prior:
                continue
            tag_match = PUBLIC_ACTION_TAG_RE.match(prior)
            if tag_match:
                public_repo = tag_match.group("repo")
                public_tag = f"{public_repo}@{tag_match.group('tag')}"
                comment_line = prior_index + 1
            break

        rows.append(
            {
                "line": index + 1,
                "repo": uses_match.group("repo"),
                "ref": uses_match.group("ref"),
                "pin_is_sha": bool(SHA_PIN_RE.fullmatch(uses_match.group("ref"))),
                "public_repo": public_repo,
                "public_tag": public_tag,
                "public_tag_comment_line": comment_line,
            }
        )
    return tuple(rows)


def _assert_inspectable_pinned_github_actions(
    workflow: str,
    *,
    required_public_tags: set[str],
) -> None:
    rows = _github_action_rows(workflow)
    assert rows, "CI workflow must declare at least one GitHub Action step"

    for row in rows:
        action = f"{row['repo']}@{row['ref']}"
        assert row["pin_is_sha"], (
            f"{action} must stay pinned by a 40-character SHA; put the "
            "recognizable upstream tag in the adjacent Public action tag comment"
        )
        assert row["public_tag"], (
            f"{action} must have an adjacent Public action tag comment so "
            "first-read/tests can identify the upstream action without relaxing the pin"
        )
        assert row["public_repo"] == row["repo"], (
            f"Public action tag {row['public_tag']} must name the same action "
            f"as pinned ref {action}"
        )

    observed_public_tags = {
        str(row["public_tag"])
        for row in rows
        if row["public_tag"]
    }
    assert required_public_tags <= observed_public_tags


def test_github_action_identity_guard_rejects_unpinned_refs() -> None:
    workflow = (
        "steps:\n"
        "  - name: Check out repository\n"
        "    # Public action tag: actions/checkout@v4. The workflow pins the action by SHA below.\n"
        "    uses: actions/checkout@v4\n"
    )

    with pytest.raises(AssertionError, match="must stay pinned"):
        _assert_inspectable_pinned_github_actions(
            workflow,
            required_public_tags={"actions/checkout@v4"},
        )


def test_github_action_identity_guard_rejects_mismatched_comments() -> None:
    workflow = (
        "steps:\n"
        "  - name: Check out repository\n"
        "    # Public action tag: actions/setup-python@v5. The workflow pins the action by SHA below.\n"
        "    uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5\n"
    )

    with pytest.raises(AssertionError, match="must name the same action"):
        _assert_inspectable_pinned_github_actions(
            workflow,
            required_public_tags={"actions/setup-python@v5"},
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
        "concurrency:",
        "group: ${{ github.workflow }}-${{ github.ref }}",
        "cancel-in-progress: true",
        "timeout-minutes: 30",
        'python-version: ["3.11", "3.12", "3.13"]',
        "run: make ci",
    ):
        assert required in workflow
    _assert_inspectable_pinned_github_actions(
        workflow,
        required_public_tags={"actions/checkout@v4", "actions/setup-python@v5"},
    )

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
    assert pyproject["project"]["authors"] == [
        {"name": "William Cook", "email": "williamwkcook@gmail.com"}
    ]


def test_pyproject_urls_point_to_standalone_public_repository() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert pyproject["project"]["urls"] == {
        "Homepage": "https://github.com/wcook04/microcosm-substrate",
        "Documentation": (
            "https://github.com/wcook04/microcosm-substrate/blob/main/README.md"
        ),
        "Source": "https://github.com/wcook04/microcosm-substrate",
        "Issues": "https://github.com/wcook04/microcosm-substrate/issues",
        "Repository": "https://github.com/wcook04/microcosm-substrate",
    }
    assert all("zenith" not in url for url in pyproject["project"]["urls"].values())
    assert "zenith/blob/main/microcosm-substrate" not in (
        pyproject["project"]["urls"]["Documentation"]
    )
    assert "tree/main/microcosm-substrate" not in (
        pyproject["project"]["urls"]["Source"]
    )
    assert "Macro-System" not in pyproject["project"]["urls"]
    assert all(
        "ai-workflow-proof" not in url
        for url in pyproject["project"]["urls"].values()
    )


def test_pyproject_pytest_tmp_state_is_repo_local_and_bounded() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    assert pytest_options["addopts"] == "-q --basetemp=.microcosm/test-tmp/pytest"
    assert pytest_options["cache_dir"] == ".microcosm/test-tmp/.pytest_cache"
    assert pytest_options["tmp_path_retention_count"] == "1"
    assert pytest_options["tmp_path_retention_policy"] == "failed"
