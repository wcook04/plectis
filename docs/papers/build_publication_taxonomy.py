#!/usr/bin/env python3
"""Project scholarly publication metadata onto this repository's paper corpus.

``publication_state`` says only ``active`` or ``retired``. It does not say what
kind of document a manuscript is, whether anyone outside this project has read
it, or how to cite it. A reader who cannot tell a problem paper from a record
of failed routes, or an author-released report from a refereed one, has to
guess -- and the honest answer is available from data already in the corpus.

This builder adds, per paper:

``publication_class``
    ``problem_paper``, ``reasoning_surface``, ``methods_paper``, or
    ``software_paper``, decided by ordered rules over the manuscript's own
    ``owns``, ``title``, and ``home_repository`` fields. The rule that fired is
    recorded in ``publication_class_basis`` so the decision can be audited
    rather than taken on trust. An unrecognised paper is an error, never a
    silent default.

``manuscript_status``
    ``retired_provenance`` for a retired manuscript, ``working_research_record``
    for a reasoning surface, ``technical_report`` otherwise.

``peer_review_state``
    Always ``not_externally_reviewed``. Nothing in this corpus has been read by
    an external referee or a venue, and the repository says so in its own words;
    the summary block records where.

``doi`` and ``doi_absence_reason``
    ``null`` and ``no_archival_deposit_yet``. Nothing here is deposited in an
    archive that mints identifiers, so there is no identifier to record.

``preferred_citation``
    Assembled only from fields the corpus already carries: the manuscript title,
    the author and year from its copyright line, its home repository, its
    canonical source commit, and its licence. Nothing is looked up, guessed, or
    completed from outside the repository.

A top-level ``publication_taxonomy`` block carries the vocabulary, the counts,
and the explicit statement that no paper here has been externally peer reviewed.

These fields describe how a manuscript was published. They say nothing about
what it establishes; ``authority_order`` and ``verification_boundary`` still own
that, and are left untouched.

The canonical corpus builder lives in the private system repository and owns
every other field. This projector is deliberately additive and idempotent: it
reads ``corpus.json``, adds or refreshes only the keys above, and rewrites the
file in the same format. Running it twice produces no second diff.

    python3 docs/papers/build_publication_taxonomy.py            # write
    python3 docs/papers/build_publication_taxonomy.py --check    # exit 1 if stale

Exit status is 0 when the corpus is current, 1 when ``--check`` finds it stale,
and 2 when the corpus is missing, unreadable, or carries a paper no rule covers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

CORPUS_REL = "docs/papers/corpus.json"
CITATION_REL = "CITATION.cff"
BUILDER_REL = "docs/papers/build_publication_taxonomy.py"

PEER_REVIEW_STATE = "not_externally_reviewed"
DOI_ABSENCE_REASON = "no_archival_deposit_yet"

PUBLICATION_CLASSES = {
    "problem_paper": (
        "Exposition of a covered Erdős problem: what is proved, what is not, "
        "and where the boundary between them sits."
    ),
    "reasoning_surface": (
        "A long-form record of attempted routes, the routes that closed, and "
        "the obligations that survive."
    ),
    "methods_paper": (
        "A systems or methodology argument: how something is built, checked, "
        "or navigated."
    ),
    "software_paper": (
        "A description of a released software artefact and what running it does "
        "and does not establish."
    ),
}

MANUSCRIPT_STATUSES = {
    "technical_report": (
        "A self-contained report released by its author. Not a submission to a "
        "venue and not a record of one."
    ),
    "working_research_record": (
        "A record of an investigation that is still open, expected to change "
        "while the problem it tracks stays open."
    ),
    "retired_provenance": (
        "Superseded by later manuscripts and kept only so the earlier record "
        "stays readable."
    ),
}

PEER_REVIEW_STATES = {
    PEER_REVIEW_STATE: (
        "No external referee, venue, or third party has reviewed this "
        "manuscript."
    ),
}

# Candidate places where this repository already states its review posture in
# its own words. Only rows whose file exists here and still carries the quoted
# marker are recorded, so the two public repositories each cite what they
# actually ship rather than a shared assumption.
REVIEW_POSTURE_EVIDENCE = (
    ("SCOPE.md", "The release is not itself a peer-reviewed publication record"),
    (
        "docs/EXTERNAL_VERIFICATION.md",
        "no human mathematical peer review is claimed",
    ),
    (
        "docs/papers/full-text/plectis-public-system.md",
        "its receipts are author-generated, not independent review or validation",
    ),
)

NEW_PAPER_KEYS = (
    "publication_class",
    "publication_class_basis",
    "manuscript_status",
    "peer_review_state",
    "doi",
    "doi_absence_reason",
    "preferred_citation",
)

COPYRIGHT_RE = re.compile(r"^\s*(?P<year>\d{4})\s+(?P<holder>.+?)\s*$")


class TaxonomyError(RuntimeError):
    """A paper the ordered rules do not cover, or corpus data that is missing."""


def _classify(paper: dict[str, Any]) -> tuple[str, str]:
    """Decide a publication class from the manuscript's own recorded fields.

    Ordered rules. The first that matches wins, and the returned basis quotes
    the marker that decided it. No rule matching is an error: a new paper must
    be classified deliberately, not absorbed by a default.
    """
    owns = (paper.get("owns") or "").lower()
    title = (paper.get("title") or "").strip()
    home = (paper.get("home_repository") or "").strip()

    # Each basis quotes the deciding text in single quotes and nowhere else, so
    # a checker can lift the quoted fragment back out and confirm it really is
    # in the paper's own fields.
    if "reasoning surface" in owns:
        return "reasoning_surface", "owns names 'reasoning surface'"

    if home and title.lower().startswith(home.lower()):
        return "software_paper", f"title opens with its released artefact '{home}'"

    for marker in ("exposition for erdős", "mathematical exposition"):
        if marker in owns:
            return "problem_paper", f"owns names '{marker}'"

    for marker in ("design argument", "architecture", "methodology"):
        if marker in owns:
            return "methods_paper", f"owns names '{marker}'"

    raise TaxonomyError(
        f"{paper.get('paper_id')}: no publication_class rule matched.\n"
        f"    owns:  {paper.get('owns')!r}\n"
        f"    title: {title!r}\n"
        "    Classify it deliberately in build_publication_taxonomy.py; do not "
        "let it fall through to a default."
    )


def _manuscript_status(paper: dict[str, Any], publication_class: str) -> str:
    if paper.get("publication_state") == "retired":
        return "retired_provenance"
    if publication_class == "reasoning_surface":
        return "working_research_record"
    return "technical_report"


def _author_and_year(paper: dict[str, Any]) -> tuple[str, str]:
    """Read the author and year off the manuscript's own copyright line."""
    copyright_line = (paper.get("copyright") or "").strip()
    match = COPYRIGHT_RE.match(copyright_line)
    if not match:
        raise TaxonomyError(
            f"{paper.get('paper_id')}: copyright {copyright_line!r} is not "
            "'<year> <holder>', so the citation author and year cannot be read "
            "from it. Nothing may be supplied from outside the corpus."
        )
    return match.group("holder"), match.group("year")


def _preferred_citation(paper: dict[str, Any]) -> dict[str, Any]:
    """Assemble a citation from corpus fields only.

    The manuscript is pinned by its canonical source commit, which is the
    identifier this project actually has. No DOI, venue, or issue date is
    invented to stand in for one.
    """
    author, year = _author_and_year(paper)
    title = paper["title"]
    home = paper["home_repository"]
    commit = paper.get("canonical_source_commit")
    url = paper.get("canonical_source_url")
    licence = paper.get("licence")

    text = f"{author} ({year}). {title}. {home}"
    if commit:
        text += f", commit {commit}"
    text += "."
    if licence:
        text += f" {licence}."
    if url:
        text += f" {url}"

    citation: dict[str, Any] = {
        "author": author,
        "year": year,
        "title": title,
        "repository": home,
        "canonical_source_commit": commit,
        "canonical_source_url": url,
        "licence": licence,
        "identifier_kind": "commit_pinned_source",
        "text": text,
        "derived_from": [
            f"{CORPUS_REL}: title, copyright, home_repository, "
            "canonical_source_commit, canonical_source_url, licence"
        ],
    }
    return citation


def _read_citation_cff(root: Path) -> dict[str, Any] | None:
    """Read the top-level scalars and first author of ``CITATION.cff``.

    Deliberately small and indentation-strict: only lines in column 0 are
    top-level keys, so the nested ``references:`` list in one of these
    repositories cannot leak a cited third party's title or author into this
    repository's own citation metadata. No YAML dependency, because the sibling
    corpus checks are stdlib-only so they run in any CI job.
    """
    path = root / CITATION_REL
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    scalars: dict[str, str] = {}
    author: dict[str, str] = {}
    in_authors = False

    for line in lines:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        top_level = line[:1] not in (" ", "\t")
        if top_level:
            in_authors = False
            key, sep, value = line.partition(":")
            if not sep:
                continue
            key = key.strip()
            value = value.strip()
            if key == "authors" and not value:
                in_authors = True
                continue
            if key not in scalars:
                scalars[key] = value.strip('"').strip("'")
            continue
        if in_authors:
            entry = line.strip().lstrip("-").strip()
            key, sep, value = entry.partition(":")
            if not sep:
                continue
            key = key.strip()
            if key in ("family-names", "given-names", "name") and key not in author:
                author[key] = value.strip().strip('"').strip("'")

    if not scalars:
        return None

    named = " ".join(
        part
        for part in (author.get("given-names"), author.get("family-names"))
        if part
    ) or author.get("name")

    record: dict[str, Any] = {
        "source": CITATION_REL,
        "describes": (
            "this repository as released software, not the individual "
            "manuscripts it carries"
        ),
    }
    for key in ("title", "version", "date-released", "license", "type"):
        if key in scalars:
            record[key.replace("-", "_")] = scalars[key]
    if named:
        record["author"] = named
    return record


def _review_posture_evidence(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for rel, marker in REVIEW_POSTURE_EVIDENCE:
        path = root / rel
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if marker in body:
            rows.append({"path": rel, "states": marker})
    return rows


def _counts(records: list[dict[str, Any]], key: str, vocabulary: dict[str, str]) -> dict[str, int]:
    counts = {term: 0 for term in vocabulary}
    for record in records:
        counts[record[key]] = counts.get(record[key], 0) + 1
    return {term: count for term, count in counts.items() if count}


def _summary(records: list[dict[str, Any]], root: Path) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "generated_by": BUILDER_REL,
        "what_these_fields_are": (
            "How each manuscript was published: what kind of document it is, "
            "whether anyone outside this project reviewed it, and how to cite "
            "it."
        ),
        "what_these_fields_are_not": (
            "They do not describe what a manuscript establishes. "
            "authority_order and verification_boundary above still own that: no "
            "Lean kernel ran during this export, and reading a paper is not "
            "checking a proof. A publication_class is a document type, never a "
            "claim of correctness, novelty, or acceptance."
        ),
        "vocabulary": {
            "publication_class": dict(PUBLICATION_CLASSES),
            "manuscript_status": dict(MANUSCRIPT_STATUSES),
            "peer_review_state": dict(PEER_REVIEW_STATES),
        },
        "by_publication_class": _counts(records, "publication_class", PUBLICATION_CLASSES),
        "by_manuscript_status": _counts(records, "manuscript_status", MANUSCRIPT_STATUSES),
        "peer_review": {
            "externally_reviewed_paper_count": 0,
            "statement": (
                "No paper in this corpus has been externally peer reviewed. "
                "Every manuscript here is author-released. No referee, no "
                "editor, and no venue has assessed any of them, and no result "
                "in them carries the standing that such an assessment would "
                "confer."
            ),
            "repository_states_this_at": _review_posture_evidence(root),
        },
        "archival_deposit": {
            "papers_with_doi": 0,
            "doi_absence_reason": DOI_ABSENCE_REASON,
            "statement": (
                "No manuscript here is deposited in an archive that mints "
                "persistent identifiers, so no paper carries a DOI. A citation "
                "pins the manuscript by its canonical source commit instead."
            ),
        },
        "repository_citation_metadata": _read_citation_cff(root),
    }
    if summary["repository_citation_metadata"] is None:
        del summary["repository_citation_metadata"]
    return summary


def _project_paper(paper: dict[str, Any]) -> dict[str, Any]:
    """Return the paper with the taxonomy keys added after publication_state.

    Existing keys keep their order and their values. Re-running replaces the
    projected keys in place rather than appending a second copy, which is what
    makes the whole build idempotent.
    """
    publication_class, basis = _classify(paper)
    projected = {
        "publication_class": publication_class,
        "publication_class_basis": basis,
        "manuscript_status": _manuscript_status(paper, publication_class),
        "peer_review_state": PEER_REVIEW_STATE,
        "doi": None,
        "doi_absence_reason": DOI_ABSENCE_REASON,
        "preferred_citation": _preferred_citation(paper),
    }

    rebuilt: dict[str, Any] = {}
    for key, value in paper.items():
        if key in NEW_PAPER_KEYS:
            continue
        rebuilt[key] = value
        if key == "publication_state":
            rebuilt.update(projected)
    if "publication_state" not in paper:
        rebuilt.update(projected)
    return rebuilt


def build(corpus: dict[str, Any], root: Path) -> dict[str, Any]:
    papers = [_project_paper(paper) for paper in corpus.get("papers", [])]
    summary = _summary(papers, root)

    rebuilt: dict[str, Any] = {}
    for key, value in corpus.items():
        if key in ("publication_taxonomy", "papers"):
            continue
        rebuilt[key] = value
        if key == "paper_count":
            rebuilt["publication_taxonomy"] = summary
    if "paper_count" not in corpus:
        rebuilt["publication_taxonomy"] = summary
    rebuilt["papers"] = papers
    return rebuilt


def _serialise(corpus: dict[str, Any]) -> str:
    """Match the canonical builder's format exactly: indent 2, escaped, one newline.

    Anything else would rewrite every non-ASCII character in the file and bury
    the projection in a diff nobody can read.
    """
    return json.dumps(corpus, indent=2) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="do not write; exit 1 if the projection is not already current",
    )
    args = parser.parse_args(argv)

    repo_root = Path(__file__).resolve().parents[2]
    corpus_path = repo_root / CORPUS_REL
    try:
        current = corpus_path.read_text(encoding="utf-8")
        corpus = json.loads(current)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {CORPUS_REL}: {exc}", file=sys.stderr)
        return 2

    try:
        rebuilt = _serialise(build(corpus, repo_root))
    except TaxonomyError as exc:
        print(f"{exc}", file=sys.stderr)
        return 2

    if rebuilt == current:
        print(
            f"publication taxonomy current: {len(corpus.get('papers', []))} papers, "
            "0 externally reviewed, 0 with a DOI"
        )
        return 0

    if args.check:
        print(
            f"{CORPUS_REL} does not carry the current publication taxonomy.\n"
            f"Regenerate it:\n    python3 {BUILDER_REL}",
            file=sys.stderr,
        )
        return 1

    corpus_path.write_text(rebuilt, encoding="utf-8")
    print(
        f"publication taxonomy written: {len(corpus.get('papers', []))} papers, "
        "0 externally reviewed, 0 with a DOI"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
