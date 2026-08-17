#!/usr/bin/env python3
"""Check that the paper corpus never claims a review or an identifier it lacks.

The corpus is a public evidence surface. The failure that would matter here is
not a stale hash -- ``check_paper_corpus.py`` already catches that -- but a
field that quietly upgrades an author-released manuscript into a reviewed one,
or hands it an archival identifier it was never given. Either would be read as
a credential, and neither is true of anything in this corpus.

So this check refuses, for every paper:

* any ``peer_review_state`` other than ``not_externally_reviewed``, and any
  value anywhere in the record that reads as a claim of external review;
* a ``doi`` that is not null, or a null ``doi`` without its stated reason;
* a ``preferred_citation`` that names a commit, title, or identifier the paper
  record does not carry -- a citation may only restate corpus data;
* a summary block whose counts disagree with the papers it summarises.

It reads the corpus and nothing else, uses only the standard library, and can
run in any CI job.

    python3 docs/papers/check_publication_taxonomy.py

Exit status is 0 when the corpus is honest about its own standing, 1 when it is
not, and 2 when the corpus is missing or unreadable.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

CORPUS_REL = "docs/papers/corpus.json"
BUILDER_REL = "docs/papers/build_publication_taxonomy.py"

PEER_REVIEW_STATE = "not_externally_reviewed"
DOI_ABSENCE_REASON = "no_archival_deposit_yet"

PUBLICATION_CLASSES = {
    "problem_paper",
    "reasoning_surface",
    "methods_paper",
    "software_paper",
}
MANUSCRIPT_STATUSES = {
    "technical_report",
    "working_research_record",
    "retired_provenance",
}

# Substrings that would read as an external-review claim if they appeared in a
# paper's publication metadata. The list is deliberately blunt: this check is
# the last thing standing between a mistaken edit and a public credential.
REVIEW_CLAIM_MARKERS = (
    "peer_reviewed",
    "peer-reviewed",
    "peer reviewed",
    "venue_reviewed",
    "refereed",
    "under_review",
    "under review",
    "in_review",
    "accepted",
    "published_in",
    "externally_reviewed",
)

REQUIRED_KEYS = (
    "publication_class",
    "manuscript_status",
    "peer_review_state",
    "doi",
    "doi_absence_reason",
    "preferred_citation",
)


def _metadata_strings(paper: dict[str, Any]) -> list[tuple[str, str]]:
    """Every string in the paper's publication metadata, with its field name."""
    found: list[tuple[str, str]] = []

    def walk(name: str, value: Any) -> None:
        if isinstance(value, str):
            found.append((name, value))
        elif isinstance(value, dict):
            for key, item in value.items():
                walk(f"{name}.{key}", item)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                walk(f"{name}[{index}]", item)

    for key in REQUIRED_KEYS:
        if key in paper:
            walk(key, paper[key])
    if "publication_class_basis" in paper:
        walk("publication_class_basis", paper["publication_class_basis"])
    return found


def _check_paper(paper: dict[str, Any]) -> list[str]:
    paper_id = paper.get("paper_id", "<unnamed paper>")
    failures: list[str] = []

    missing = [key for key in REQUIRED_KEYS if key not in paper]
    if missing:
        failures.append(
            f"{paper_id}: missing publication metadata {', '.join(missing)}; "
            f"run {BUILDER_REL}"
        )
        return failures

    # No paper in this corpus has been externally reviewed. Nothing may say so.
    state = paper["peer_review_state"]
    if state != PEER_REVIEW_STATE:
        failures.append(
            f"{paper_id}: peer_review_state is {state!r}, which claims a review "
            f"this corpus has not had. It must be {PEER_REVIEW_STATE!r}: no "
            "referee, editor, or venue has assessed any manuscript here."
        )

    for field, value in _metadata_strings(paper):
        # The one legitimate occurrence: the field whose whole job is to deny a
        # review necessarily contains the word. Anywhere else it is a claim.
        if field == "peer_review_state" and value == PEER_REVIEW_STATE:
            continue
        lowered = value.lower()
        for marker in REVIEW_CLAIM_MARKERS:
            if marker in lowered:
                failures.append(
                    f"{paper_id}: {field} contains {marker!r}, which reads as a "
                    f"claim of external review. Offending value: {value!r}"
                )

    if paper["doi"] is not None:
        failures.append(
            f"{paper_id}: doi is {paper['doi']!r}, but nothing in this corpus is "
            "deposited in an archive that mints identifiers. A DOI here would be "
            "fabricated."
        )
    if paper["doi_absence_reason"] != DOI_ABSENCE_REASON:
        failures.append(
            f"{paper_id}: doi is null but doi_absence_reason is "
            f"{paper['doi_absence_reason']!r}; it must be {DOI_ABSENCE_REASON!r} "
            "so a missing identifier is never read as an oversight."
        )

    if paper["publication_class"] not in PUBLICATION_CLASSES:
        failures.append(
            f"{paper_id}: publication_class {paper['publication_class']!r} is not "
            f"one of {sorted(PUBLICATION_CLASSES)}"
        )
    if paper["manuscript_status"] not in MANUSCRIPT_STATUSES:
        failures.append(
            f"{paper_id}: manuscript_status {paper['manuscript_status']!r} is not "
            f"one of {sorted(MANUSCRIPT_STATUSES)}"
        )

    retired = paper.get("publication_state") == "retired"
    provenance = paper["manuscript_status"] == "retired_provenance"
    if retired != provenance:
        failures.append(
            f"{paper_id}: publication_state {paper.get('publication_state')!r} and "
            f"manuscript_status {paper['manuscript_status']!r} disagree about "
            "whether this manuscript is retired"
        )

    # A citation may only restate what the paper record already carries.
    citation = paper["preferred_citation"]
    if not isinstance(citation, dict):
        failures.append(f"{paper_id}: preferred_citation must be an object")
        return failures
    for field, corpus_key in (
        ("title", "title"),
        ("repository", "home_repository"),
        ("canonical_source_commit", "canonical_source_commit"),
        ("canonical_source_url", "canonical_source_url"),
        ("licence", "licence"),
    ):
        if citation.get(field) != paper.get(corpus_key):
            failures.append(
                f"{paper_id}: preferred_citation.{field} is "
                f"{citation.get(field)!r}, which is not the paper's "
                f"{corpus_key} ({paper.get(corpus_key)!r}). A citation may only "
                "restate corpus data."
            )
    if "doi" in citation:
        failures.append(
            f"{paper_id}: preferred_citation carries a doi field; there is no DOI "
            "to carry"
        )
    if "doi" in str(citation.get("text", "")).lower():
        failures.append(
            f"{paper_id}: preferred_citation.text mentions a DOI: "
            f"{citation.get('text')!r}"
        )
    author = citation.get("author")
    year = citation.get("year")
    copyright_line = paper.get("copyright") or ""
    if not author or author not in copyright_line:
        failures.append(
            f"{paper_id}: preferred_citation.author {author!r} does not appear in "
            f"the manuscript's copyright line {copyright_line!r}"
        )
    if not year or year not in copyright_line:
        failures.append(
            f"{paper_id}: preferred_citation.year {year!r} does not appear in the "
            f"manuscript's copyright line {copyright_line!r}"
        )

    return failures


def _check_summary(corpus: dict[str, Any], papers: list[dict[str, Any]]) -> list[str]:
    failures: list[str] = []
    summary = corpus.get("publication_taxonomy")
    if not isinstance(summary, dict):
        failures.append(
            f"the corpus has no publication_taxonomy summary; run {BUILDER_REL}"
        )
        return failures

    for key, field in (
        ("by_publication_class", "publication_class"),
        ("by_manuscript_status", "manuscript_status"),
    ):
        recorded = summary.get(key)
        actual: dict[str, int] = {}
        for paper in papers:
            value = paper.get(field)
            if isinstance(value, str):
                actual[value] = actual.get(value, 0) + 1
        if recorded != actual:
            failures.append(
                f"publication_taxonomy.{key} records {recorded!r} but the papers "
                f"count {actual!r}"
            )

    peer_review = summary.get("peer_review")
    if not isinstance(peer_review, dict):
        failures.append("publication_taxonomy.peer_review is missing")
    else:
        if peer_review.get("externally_reviewed_paper_count") != 0:
            failures.append(
                "publication_taxonomy.peer_review.externally_reviewed_paper_count "
                f"is {peer_review.get('externally_reviewed_paper_count')!r}; it "
                "must be 0"
            )
        statement = str(peer_review.get("statement", ""))
        if "has been externally peer reviewed" not in statement:
            failures.append(
                "publication_taxonomy.peer_review.statement must say plainly that "
                "no paper has been externally peer reviewed; it says "
                f"{statement!r}"
            )

    deposit = summary.get("archival_deposit")
    if not isinstance(deposit, dict):
        failures.append("publication_taxonomy.archival_deposit is missing")
    elif deposit.get("papers_with_doi") != 0 or deposit.get(
        "doi_absence_reason"
    ) != DOI_ABSENCE_REASON:
        failures.append(
            "publication_taxonomy.archival_deposit must record 0 papers with a "
            f"DOI and the reason {DOI_ABSENCE_REASON!r}; it records "
            f"{deposit.get('papers_with_doi')!r} and "
            f"{deposit.get('doi_absence_reason')!r}"
        )

    # The new fields must not be readable as a change to what the corpus
    # establishes. The existing boundary keys stay, and the summary says so.
    for key in ("authority_order", "verification_boundary"):
        if key not in corpus:
            failures.append(
                f"the corpus no longer carries {key}; the publication taxonomy "
                "must not replace the authority boundary"
            )
    disclaimer = str(summary.get("what_these_fields_are_not", ""))
    for required in ("authority_order", "verification_boundary"):
        if required not in disclaimer:
            failures.append(
                "publication_taxonomy.what_these_fields_are_not must name "
                f"{required} so these fields cannot be read as authority"
            )

    return failures


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    corpus_path = repo_root / CORPUS_REL
    try:
        corpus = json.loads(corpus_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"cannot read {CORPUS_REL}: {exc}", file=sys.stderr)
        return 2

    papers = corpus.get("papers", [])
    if not papers:
        print(f"{CORPUS_REL} carries no papers", file=sys.stderr)
        return 2

    failures: list[str] = []
    for paper in papers:
        failures.extend(_check_paper(paper))
    failures.extend(_check_summary(corpus, papers))

    if failures:
        print(
            "The paper corpus claims standing it does not have.\n", file=sys.stderr
        )
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        print(
            "\nEvery manuscript in this corpus is author-released and carries no "
            "archival identifier.\nFix the source of the claim, then regenerate:\n"
            f"    python3 {BUILDER_REL}",
            file=sys.stderr,
        )
        return 1

    print(
        f"publication taxonomy honest: {len(papers)} papers, "
        "0 claiming external review, 0 carrying a DOI"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
