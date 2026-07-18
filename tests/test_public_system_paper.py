from __future__ import annotations

import json
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


def test_public_system_paper_check_rejects_lean_file_count_drift(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\newcommand{\leanfilecount}{58}",
            r"\newcommand{\leanfilecount}{59}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper)

    assert "leanfilecount=59, pinned Lean sources=58" in failures


def test_public_system_paper_check_rejects_public_test_receipt_drift(
    tmp_path: Path,
) -> None:
    receipt = tmp_path / "public-test-receipt.json"
    payload = paper_check._load_public_test_receipt(
        paper_check.PUBLIC_TEST_RECEIPT, []
    )
    payload["result"]["passed"] = 357
    receipt.write_text(
        json.dumps(payload),
        encoding="utf-8",
    )

    failures = check_paper(public_test_receipt_path=receipt)

    assert "public-test receipt passed=357, expected 356" in failures


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


def test_public_system_paper_check_rejects_bibliography_order_drift(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(r"\bibitem{nasem2019}", r"\bibitem{order-swap}")
        .replace(r"\bibitem{weyuker1982}", r"\bibitem{nasem2019}")
        .replace(r"\bibitem{order-swap}", r"\bibitem{weyuker1982}"),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "bibliography items must follow first-citation order" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_bibliography_identifier_drift(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "https://standards.nasa.gov/standard/nasa/nasa-std-87398",
            "https://example.invalid/wrong-standard",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "bibliography item nasa8739 lacks canonical token" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_prior_art_boundary_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "not an implementation of that standard",
            "an implementation of that standard",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("not an implementation" in failure for failure in failures)


def test_public_system_paper_check_rejects_standards_distinction_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace("Results Reproduced", "Results reviewed")
        .replace(
            "managerial independence (they choose what and how to assess)",
            "managerial independence",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("Results Reproduced" in failure for failure in failures)
    assert any("managerial independence" in failure for failure in failures)


def test_public_system_paper_check_rejects_method_scope_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "descriptive analysis of one artefact, not a statistical study",
            "complete evaluation of the system",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("not a statistical study" in failure for failure in failures)


def test_public_system_paper_check_rejects_early_contribution_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "The paper examines one author-curated software collection",
            "The paper next describes the repository",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing first-section orientation anchor" in failure
        and "examines one author-curated" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_cold_reader_residue(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        + "\nThis note reports no independent audit.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("cold-reader residue" in failure for failure in failures)


def test_public_system_paper_check_rejects_internal_label_explanation_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "README-first order (internally\n"
            r"\component{readme_onboarding_route})",
            r"README-first order (\component{readme_onboarding_route})",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing appendix internal-label explanation" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_example_bridge_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "The calculator check supplies an independent expected number for one row.",
            "The example is complete.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing example-to-distinctions bridge" in failure
        and "independent expected number" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_executable_first_review_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "Use the appendix's no-install block",
            "Use the repository somehow",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "no-install block" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_claim_routing_step_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "comprehend --first-action",
            '--show-something',
        )
        .replace(
            r"\code{no-write variant}",
            "the suggested command",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "--first-action" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "no-write variant" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_hash_explanation_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "a fixed-length value calculated from its contents",
            "a digest",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language hash boundary" in failure
        and "fixed-length value" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_selection_scope_layout_regression(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace("Selection acts at two levels", "Selection applies here")
        .replace(r"\begin{figure}[H]", r"\begin{figure}[t]"),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing two-level selection explanation" in failure for failure in failures
    )
    assert any("selection figure must not interrupt" in failure for failure in failures)


def test_public_system_paper_check_rejects_route_definition_regression(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"It calls this classification a \emph{route}",
            "It calls this a route",
        )
        .replace(
            "They cannot create an\nindependent witness",
            "The records agree",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing collection route explanation" in failure
        and "classification" in failure
        for failure in failures
    )
    assert any(
        "missing collection route explanation" in failure
        and "independent witness" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_central_term_definition_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"I use \emph{answerable} in a deliberately local sense",
            "I use answerable in its ordinary sense",
        )
        .replace(
            "Calling\n"
            "them evidence does not establish their adequacy",
            "These materials are adequate evidence",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("deliberately local sense" in failure for failure in failures)
    assert any("does not establish their adequacy" in failure for failure in failures)


def test_public_system_paper_check_rejects_evaluation_crosswalk_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "These evaluations do not pair one-for-one with the distinctions",
            "The five routes answer the five distinctions",
        )
        .replace(
            "None repairs a validator--claim mismatch",
            "Together they repair every gap",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("do not pair one-for-one" in failure for failure in failures)
    assert any(
        "None repairs a validator--claim mismatch" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_route_evaluation_collision(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "These are not the four publication routes",
            "These are five more routes",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing stronger-evaluation terminology boundary" in failure
        and "four publication routes" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_evaluation_figure_float_regression(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    section_marker = r"\section{What stronger evidence would look like}"
    before, stronger = source.split(section_marker, 1)
    stronger = stronger.replace(r"\begin{figure}[H]", r"\begin{figure}[t]", 1)
    paper = tmp_path / "paper.tex"
    paper.write_text(before + section_marker + stronger, encoding="utf-8")

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "stronger-evaluation figure must follow" in failure for failure in failures
    )


def test_public_system_paper_check_rejects_formal_math_overclaim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "The\nlabel itself supplies no theorem",
            "The group proves mathematics",
        )
        .replace(
            "custom axioms (assumptions added without\nproof)",
            "custom axioms",
        )
        .replace(
            "This search cannot show that each formal\nstatement says what its author intended",
            "Every formal statement has its intended meaning",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("missing formal-math evidence boundary" in failure for failure in failures)
    assert any("missing Lean check explanation" in failure for failure in failures)


def test_public_system_paper_check_rejects_misleading_figure_legend(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "This figure has no dashed boxes",
            "The dashed boxes are hidden",
        )
        .replace("italic blue row", "blue row")
        .replace("in italic\nblue", "in blue")
        + "\nA dashed outline marks what a stranger cannot run or observe directly.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("This figure has no dashed boxes" in failure for failure in failures)
    assert any("italic blue row" in failure for failure in failures)
    assert any("in italic blue" in failure for failure in failures)
    assert any(
        "dashed outline marks what a stranger cannot" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_independence_as_universal_requirement(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "Moving a relevant choice out\n"
            "of the author's hands can strengthen evidence about that choice; it does not\n"
            "repair every gap.",
            "Stronger evidence requires at least one consequential choice to leave "
            "the author's hands.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("Moving a relevant choice" in failure for failure in failures)
    assert any("stronger evidence requires" in failure for failure in failures)
