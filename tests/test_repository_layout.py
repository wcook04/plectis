"""Placement failures are caught before they become part of a public tree."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("layout", ROOT / "scripts/check/check_repository_layout.py")
layout = importlib.util.module_from_spec(spec)
spec.loader.exec_module(layout)
POLICY = json.loads((ROOT / layout.POLICY).read_text())


@pytest.mark.parametrize("path", [
    "scripts/new_tool.py", "docs/papers/new_tool.py", "scripts/check/test_gate.py",
    "scripts/release/build_map.py", "scripts/build/check_map.py", "scripts/unknown/tool.py",
    "src/example.pyc",
])
def test_rejects_misplaced_program(path):
    assert layout.violations(POLICY["required_paths"] + [path], POLICY)


def test_roles_and_historical_source_copies_remain_valid():
    paths = POLICY["required_paths"] + [
        "scripts/build/build_map.py", "scripts/check/check_map.py",
        "scripts/release/package.py", "scripts/inspect/card.py",
        "scripts/papers/build_index.py", "tests/test_gate.py",
        "examples/exported_bundle/source_modules/test_original.py",
    ]
    assert layout.violations(paths, POLICY) == []


def test_index_sees_staged_additions_and_deletions_ignores_local_output(tmp_path):
    def git(*args):
        return subprocess.run(["git", "-C", str(tmp_path), *args], check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / ".gitignore").write_text("scratch/\n")
    (tmp_path / "scratch").mkdir()
    (tmp_path / "scratch/ignored.py").write_text("ignored")
    (tmp_path / "untracked.py").write_text("untracked")
    (tmp_path / "scripts").mkdir()
    bad = tmp_path / "scripts/misplaced.py"
    bad.write_text("staged")
    git("add", ".gitignore", "scripts/misplaced.py")
    paths = layout.candidate_paths(tmp_path)
    assert paths == [".gitignore", "scripts/misplaced.py"]
    assert layout.violations(POLICY["required_paths"] + paths, POLICY)
    git("rm", "--cached", "scripts/misplaced.py")
    assert "scripts/misplaced.py" not in layout.candidate_paths(tmp_path)


def test_shipped_tree_fallback(tmp_path):
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts/bad.py").write_text("pass")
    assert layout.candidate_paths(tmp_path) == ["scripts/bad.py"]


def test_checkout_satisfies_layout():
    assert layout.violations(layout.candidate_paths(ROOT), POLICY) == []


def test_build_ignore_does_not_hide_maintained_builders(tmp_path):
    subprocess.run(["git", "-C", str(tmp_path), "init", "-q"], check=True)
    (tmp_path / ".gitignore").write_bytes((ROOT / ".gitignore").read_bytes())
    for relative, expected in (("build/output.py", 0), ("scripts/build/build_new.py", 1)):
        result = subprocess.run(
            ["git", "-C", str(tmp_path), "check-ignore", "--no-index", relative],
            capture_output=True,
        )
        assert result.returncode == expected, (relative, result.stdout, result.stderr)
