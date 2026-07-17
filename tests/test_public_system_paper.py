from __future__ import annotations

from pathlib import Path

from scripts.check_public_system_paper import PAPER, check_paper


def test_public_system_paper_matches_live_public_evidence() -> None:
    assert check_paper() == []


def test_public_system_paper_check_rejects_count_drift(tmp_path: Path) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\newcommand{\componentcount}{88}",
            r"\newcommand{\componentcount}{89}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("componentcount=89" in failure for failure in failures)


def test_public_system_paper_check_rejects_provenance_overclaim(tmp_path: Path) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        + "\nA reader can verify it is non-secret and proceed without trusting anyone.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("verify it is non-secret" in failure for failure in failures)
    assert any("without trusting anyone" in failure for failure in failures)
