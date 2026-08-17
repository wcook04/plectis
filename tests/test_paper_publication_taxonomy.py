"""The paper corpus must not claim a review or an identifier it does not have.

``publication_state`` says only ``active`` or ``retired``, which leaves a reader
unable to tell a problem paper from a record of closed routes, or an
author-released manuscript from a refereed one. ``corpus.json`` now carries a
publication taxonomy that says both plainly.

Saying it plainly is only safe if it stays true. Nothing in this corpus has been
read by an external referee or a venue, and nothing is deposited anywhere that
mints a DOI. A field that said otherwise would be read as a credential, and
would be worse than no field at all.

The shipped guard is ``docs/papers/check_publication_taxonomy.py``; it lives in
the corpus it guards so it runs in a bare clone. This module invokes it rather
than restating its rules, and adds the checks a test can make more directly:
that the projection is current, and that the classification of every paper is
backed by the field text that decided it.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = REPO_ROOT / "docs" / "papers"
CORPUS = CORPUS_DIR / "corpus.json"
BUILDER = CORPUS_DIR / "build_publication_taxonomy.py"
GUARD = CORPUS_DIR / "check_publication_taxonomy.py"

PUBLICATION_CLASSES = {
    "problem_paper",
    "reasoning_surface",
    "methods_paper",
    "software_paper",
}


def _corpus() -> dict:
    return json.loads(CORPUS.read_text(encoding="utf-8"))


def test_builder_and_guard_are_present() -> None:
    assert BUILDER.is_file(), "docs/papers/build_publication_taxonomy.py is missing"
    assert GUARD.is_file(), "docs/papers/check_publication_taxonomy.py is missing"


def test_shipped_guard_finds_no_claimed_review_or_identifier() -> None:
    result = subprocess.run(
        [sys.executable, str(GUARD)],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


def test_projection_is_current_and_idempotent() -> None:
    """A stale projection would describe papers the corpus no longer carries."""
    before = CORPUS.read_bytes()
    result = subprocess.run(
        [sys.executable, str(BUILDER), "--check"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert CORPUS.read_bytes() == before, "--check must not write"


def test_no_paper_claims_external_review() -> None:
    """Said here as well as in the guard, so a failure names the paper."""
    for paper in _corpus()["papers"]:
        assert paper["peer_review_state"] == "not_externally_reviewed", (
            f"{paper['paper_id']} claims {paper['peer_review_state']!r}. No "
            "referee, editor, or venue has assessed any manuscript in this "
            "corpus."
        )


def test_no_paper_carries_a_doi_and_every_absence_is_explained() -> None:
    for paper in _corpus()["papers"]:
        assert paper["doi"] is None, (
            f"{paper['paper_id']} carries doi {paper['doi']!r}; nothing here is "
            "deposited in an archive that mints identifiers"
        )
        assert paper["doi_absence_reason"] == "no_archival_deposit_yet", (
            f"{paper['paper_id']}: a null doi must say why it is null"
        )


def test_every_classification_is_backed_by_the_text_that_decided_it() -> None:
    """A class without a basis is an opinion; with one it can be checked."""
    for paper in _corpus()["papers"]:
        assert paper["publication_class"] in PUBLICATION_CLASSES
        basis = paper["publication_class_basis"]
        assert basis, f"{paper['paper_id']} has no publication_class_basis"
        haystack = f"{paper['owns']} {paper['title']} {paper['home_repository']}".lower()
        quoted = [
            fragment
            for fragment in basis.split("'")[1::2]
        ]
        for fragment in quoted:
            assert fragment.lower() in haystack, (
                f"{paper['paper_id']}: publication_class_basis quotes "
                f"{fragment!r}, which is not in the paper's own fields"
            )


def test_the_taxonomy_does_not_displace_the_authority_boundary() -> None:
    """Document type is not standing. The existing boundary keys must survive."""
    corpus = _corpus()
    assert corpus["authority_order"]
    assert corpus["verification_boundary"]["proof_recheck_performed"] is False
    disclaimer = corpus["publication_taxonomy"]["what_these_fields_are_not"]
    assert "authority_order" in disclaimer
    assert "verification_boundary" in disclaimer


def test_summary_counts_match_the_papers() -> None:
    corpus = _corpus()
    summary = corpus["publication_taxonomy"]
    counted: dict[str, int] = {}
    for paper in corpus["papers"]:
        value = paper["publication_class"]
        counted[value] = counted.get(value, 0) + 1
    assert summary["by_publication_class"] == counted
    assert sum(counted.values()) == corpus["paper_count"]
    assert summary["peer_review"]["externally_reviewed_paper_count"] == 0
    assert summary["archival_deposit"]["papers_with_doi"] == 0
