from __future__ import annotations

from pathlib import Path

from scripts import check_public_system_paper as paper_check
from scripts.check_public_system_paper import PAPER, check_paper


def test_public_system_paper_matches_pinned_public_evidence() -> None:
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
        + "\nA reader can verify it is non-secret and proceed without trusting anyone. "
        + "Plectis is designed not to read the private repository at all.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("verify it is non-secret" in failure for failure in failures)
    assert any("without trusting anyone" in failure for failure in failures)
    assert any(
        "designed not to read the private repository" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_distinction_anchor_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "The count is an inventory, not a score", "The count is large"
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("The count is an inventory" in failure for failure in failures)


def test_public_system_paper_check_reads_default_evidence_from_snapshot(
    monkeypatch,
) -> None:
    def reject_live_json(_path: Path) -> dict:
        raise AssertionError("default paper check must not read live registries")

    monkeypatch.setattr(paper_check, "_load_json", reject_live_json)

    assert paper_check.check_paper() == []


def test_public_system_paper_check_rejects_worked_example_value_drift(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace("0.489897949", "0.489897950"),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper)

    assert any(
        "does not display pinned worked-example value" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_missing_bibliography_item(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\bibitem{nasa8739}", r"\bibitem{missing-nasa8739}"
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper)

    assert "missing bibliography item: nasa8739" in failures


def test_public_system_paper_check_rejects_contribution_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "narrower contribution\nis the claim--evidence--limit contract",
            "narrower contribution\nis this case study",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("narrower contribution" in failure for failure in failures)
