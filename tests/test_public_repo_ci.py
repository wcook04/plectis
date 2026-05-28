from __future__ import annotations

from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
CI_WORKFLOW = MICROCOSM_ROOT / ".github/workflows/ci.yml"


def test_public_repo_has_inspectable_github_actions_ci() -> None:
    assert CI_WORKFLOW.is_file()

    workflow = CI_WORKFLOW.read_text(encoding="utf-8")

    for required in (
        "name: CI",
        "pull_request:",
        "workflow_dispatch:",
        "permissions:",
        "contents: read",
        'python-version: ["3.11", "3.12"]',
        "actions/checkout@v4",
        "actions/setup-python@v5",
        'python -m pip install -e \".[test]\"',
        "python -m pytest",
        "microcosm hello .",
        "python -m microcosm_core --version",
        "microcosm stripping-guard",
    ):
        assert required in workflow
