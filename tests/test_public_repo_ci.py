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
        'python-version: ["3.11", "3.12", "3.13", "3.14"]',
        "run: make ci",
        # The published first screen, exercised on the platform where it broke.
        # Every Ubuntu job stayed green while `python3 -m pip install .` --
        # the README's first runnable command -- was refused under PEP 668 on
        # macOS. This job pins the interpreter to whatever the runner ships,
        # so the promise is tested against the machine a reader arrives on.
        'os: ["macos-latest", "ubuntu-latest"]',
        "PYTHONPATH=src python3 -m plectis tour --format text .",
        ".venv/bin/python -m pip install .",
    ):
        assert required in workflow

    # This job must NOT pin an interpreter: setting one up would test a machine
    # nobody arrives on and would have hidden the PEP 668 refusal again.
    first_contact = workflow[workflow.index("  first-contact:") :]
    first_contact = first_contact[: first_contact.index("  user-smoke:")]
    assert "uses: actions/setup-python" not in first_contact
    # These must name the versions the SHAs above actually resolve to. The set
    # is the only thing keeping the comments honest, since nothing offline can
    # check a SHA against its upstream tag -- and when Dependabot moves a pin it
    # does not touch the sentence beside it. Bump both together, or the guard
    # starts requiring the comment to misstate the version.
    _assert_inspectable_pinned_github_actions(
        workflow,
        required_public_tags={"actions/checkout@v7", "actions/setup-python@v6"},
    )

    for duplicated_command in (
        'python -m pip install -e ".[test]"',
        "python -m pytest",
        "plectis hello .",
        "python -m microcosm_core --version",
        "plectis stripping-guard",
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
        "Homepage": "https://github.com/wcook04/plectis",
        "Documentation": "https://wcook04.github.io/plectis/",
        "Source": "https://github.com/wcook04/plectis",
        "Issues": "https://github.com/wcook04/plectis/issues",
        "Repository": "https://github.com/wcook04/plectis",
    }
    assert all("zenith" not in url for url in pyproject["project"]["urls"].values())


def test_pyproject_description_matches_mechanism_first_identity() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    # This test is named for mechanism-first identity, but the string it used
    # to pin described the package as a harness for testing "the claims of an
    # AI-built system" -- someone else's system, not the reader's project. The
    # README and the repository description had both moved to what a reader
    # does with it; pyproject had not, and this assertion was the reason it
    # could not. It is the summary PyPI would publish, so it is the one place
    # the old framing would have outlived every surface that corrected it.
    assert pyproject["project"]["description"] == (
        "Checks claims about software nobody watched being built: point it at "
        "a project and it writes a local record you can re-run — the route it "
        "took, the evidence behind each finding, and where that finding stops. "
        "Runs entirely on your machine."
    )
    lowered = pyproject["project"]["description"].lower()
    for banned in ("impressive", "ambitious", "strongest public claim"):
        assert banned not in lowered
    # Pinning an exact string stops silent drift but cannot say what the string
    # has to mean. Name the property directly: the summary addresses a reader
    # about their own project, rather than advertising a system they cannot see.
    assert "point it at a project" in lowered
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


def test_pyproject_pytest_tmp_state_delegates_high_churn_paths() -> None:
    pyproject = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    pytest_options = pyproject["tool"]["pytest"]["ini_options"]
    assert pytest_options["addopts"] == "-q -p no:cacheprovider"
    assert "--basetemp" not in pytest_options["addopts"]
    assert "cacheprovider" in pytest_options["addopts"]
    assert "cache_dir" not in pytest_options
    assert pytest_options["tmp_path_retention_count"] == "1"
    assert pytest_options["tmp_path_retention_policy"] == "failed"


def test_exactly_one_github_pages_publication_owner() -> None:
    """No workflow may deploy Pages while the gh-pages branch builder serves it.

    The site is published by GitHub's legacy branch builder from `gh-pages`
    (Pages `build_type: legacy`). A workflow calling `actions/deploy-pages`
    publishes an artifact to the same environment, so whichever ran last wins
    and the served tree depends on ordering rather than on a decision.

    That is not hypothetical here: a deploy workflow copied a hardcoded list of
    files, so everything added to gh-pages afterwards - all three papers and
    `.well-known/security.txt` among them - 404'd on the live site until it was
    disabled. Disabling left the file in place and the second owner one toggle
    away, so the invariant is asserted rather than remembered.
    """
    workflow_dir = MICROCOSM_ROOT / ".github/workflows"
    deployers = [
        path.name
        for path in sorted(workflow_dir.glob("*.yml"))
        if "actions/deploy-pages" in path.read_text(encoding="utf-8")
    ]
    assert deployers == [], (
        "these workflows deploy GitHub Pages while the gh-pages branch builder "
        f"already owns publication: {deployers}. Keep exactly one owner - either "
        "delete the workflow, or switch Pages to workflow builds and retire the "
        "branch builder deliberately."
    )
