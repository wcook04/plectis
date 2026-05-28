from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def test_public_repo_gitignore_excludes_local_runtime_residue() -> None:
    residue_paths = [
        ".DS_Store",
        ".microcosm/state.json",
        ".pytest_cache/README.md",
        ".venv/pyvenv.cfg",
        "build/lib.txt",
        "dist/microcosm.whl",
        "microcosm-substrate/.microcosm/events.jsonl",
    ]
    inside_worktree = subprocess.run(
        ["git", "rev-parse", "--is-inside-work-tree"],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if inside_worktree.returncode != 0:
        pytest.skip("git ignore boundary check requires a Git worktree")

    result = subprocess.run(
        ["git", "check-ignore", "-v", *residue_paths],
        cwd=MICROCOSM_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    ignored_paths = {
        line.rsplit("\t", 1)[-1]
        for line in result.stdout.splitlines()
        if "\t" in line
    }
    assert ignored_paths == set(residue_paths)
