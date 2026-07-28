"""The generated paper corpus must still describe this repository's manuscripts.

``docs/papers/`` is generated: available papers are copied or converted to
Markdown and indexed by a tool in the private system repository. Some registry
rows may remain explicitly unavailable when their source was not present at
export time.

What is checked is the thing that can be checked locally and cheaply, and it is
the failure that actually happens: someone edits a manuscript and the generated
text silently keeps describing the previous one. ``corpus.json`` records the
SHA-256 of every manuscript it was built from, so comparing hashes catches that.

The shipped checker is ``docs/papers/check_paper_corpus.py``; it is copied into
this repository by the export, so this module invokes it rather than restating
its logic.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = REPO_ROOT / "docs" / "papers"
CORPUS = CORPUS_DIR / "corpus.json"
CHECKER = CORPUS_DIR / "check_paper_corpus.py"


def test_corpus_is_present() -> None:
    assert CORPUS.is_file(), "docs/papers/corpus.json is missing; re-run the export"
    assert CHECKER.is_file(), "docs/papers/check_paper_corpus.py is missing"


def test_shipped_checker_reports_the_corpus_is_current() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_every_recorded_manuscript_hash_matches() -> None:
    """The same comparison, made here so a failure names the paper directly."""
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    checked = 0
    for paper in corpus["papers"]:
        if paper.get("availability") == "unavailable_at_build":
            continue
        source = REPO_ROOT / paper["local_source"]
        assert source.is_file(), f"{paper['paper_id']}: {paper['local_source']} is missing"
        digest = "sha256:" + hashlib.sha256(source.read_bytes()).hexdigest()
        assert digest == paper["source_sha256"], (
            f"{paper['paper_id']}: {paper['local_source']} has changed since the "
            "corpus was generated; re-run the export in the private system repository"
        )
        checked += 1
    assert checked > 0, "the corpus contains no locally checkable manuscripts"
    assert checked == sum("local_source" in paper for paper in corpus["papers"])


def test_unavailable_rows_are_explicit_and_non_deceptive() -> None:
    """An absent registered paper must not look like a locally inspectable one."""
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    unavailable = [
        paper
        for paper in corpus["papers"]
        if paper.get("availability") == "unavailable_at_build"
    ]
    for paper in unavailable:
        assert paper.get("reason")
        assert "local_source" not in paper
        assert "local_full_text" not in paper


@pytest.mark.parametrize("relation", ["native", "mirror"])
def test_every_paper_declares_where_its_authority_lives(relation: str) -> None:
    """A mirror that does not say it is a mirror would move authority by copying."""
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    matching = [
        paper
        for paper in corpus["papers"]
        if paper.get("relation_to_this_repository") == relation
    ]
    assert matching, f"no paper is marked {relation!r}"
    for paper in matching:
        assert paper["home_repository"]
        assert paper["not_authority_for"]
        if relation == "mirror":
            assert paper["home_repository"] != "plectis"
            assert "mirror_note" in paper
        else:
            assert paper["home_repository"] == "plectis"


def test_section_line_numbers_point_at_their_anchors() -> None:
    """The index is only useful if its line numbers are true."""
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    for paper in corpus["papers"]:
        if paper.get("availability") == "unavailable_at_build":
            continue
        lines = (REPO_ROOT / paper["local_full_text"]).read_text(
            encoding="utf-8"
        ).splitlines()
        for section in paper["sections"]:
            line = section.get("line")
            if line is None:
                continue
            assert f'id="{section["id"]}"' in lines[line - 1], (
                f"{paper['paper_id']}: section {section['id']} is recorded at line "
                f"{line}, which does not carry its anchor"
            )
