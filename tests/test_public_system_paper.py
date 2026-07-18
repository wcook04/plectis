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


def test_public_system_paper_check_rejects_abstract_origin_as_fact(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "built to expose selected claims about a larger private system. I\n"
            "report that its published material was copied or adapted from that system,",
            "assembled from parts of a larger private system",
        )
        .replace(
            "The argument does not depend on that account or on the claimed origin of the\n"
            "published material.",
            "The argument is complete.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "assembled from parts of a larger private system" in failure
        for failure in failures
    )
    assert sum("missing cold-reader anchor" in failure for failure in failures) >= 2


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


def test_public_system_paper_check_rejects_opaque_distinction_summary(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"\subsection*{Public execution versus where the code came from}",
            r"\subsection*{Public execution versus private provenance}",
        )
        .replace(
            "Five labels organise the gaps",
            "five evidential distinctions",
        )
        .replace(
            r"The term \emph{provenance}"
            "\nmeans an object's origin and history",
            "Provenance is reported",
        )
        .replace(
            "For\norigin, one must assume\n"
            "that the public object came from the private one",
            "There is one assumption per distinction",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("cold-reader residue" in failure for failure in failures)
    assert sum("missing cold-reader anchor" in failure for failure in failures) >= 4


def test_public_system_paper_check_requires_five_gap_map_before_the_details(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "Five labels organise the gaps in Figure~\\ref{fig:gaps}: \\emph{origin}, where\n"
            "the material came from; \\emph{correctness}, whether an answer is right;\n"
            "\\emph{meaning}, whether a rule tests its claim; \\emph{reach}, whether shown\n"
            "cases stand for unshown ones; and \\emph{risk}, what the declared checks may\n"
            "miss. Each subsection separates observation from inference.",
            "Figure~\\ref{fig:gaps} lists five evidential dimensions.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert sum("missing early five-gap map" in failure for failure in failures) == 6


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
            "https://standards.nasa.gov/standard/NASA/NASA-STD-87398",
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
            "chooses scope,\n"
            "methods, and schedule",
            "follow the project's review plan",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("Results Reproduced" in failure for failure in failures)
    assert any("scope, methods, and schedule" in failure for failure in failures)


def test_public_system_paper_check_rejects_nasa_ivv_scope_overclaim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "not a universal test",
            "the universal test",
        )
        .replace(
            "has undergone\n"
            "no IV\\&V",
            "satisfied the NASA independence criteria",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("not a universal test" in failure for failure in failures)
    assert any(r"has undergone no IV\\&V" in failure for failure in failures)


def test_public_system_paper_check_rejects_unobservable_outside_evaluation_claim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "No other outside evaluation report is cited or included, and I know\n"
            "of none; an unreported private rerun would remain invisible.",
            "No outside evaluation has happened.",
        )
        .replace(
            "It includes no outside evaluator's report; I know of none,\n"
            "although a private rerun could be unreported.",
            "No outsider has ever rerun it.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("unreported private rerun" in failure for failure in failures)
    assert any("outside evaluator's report" in failure for failure in failures)


def test_public_system_paper_check_rejects_method_scope_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "descriptive analysis of one public repository, not a statistical\nstudy",
            "complete evaluation of the system",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("not a statistical study" in failure for failure in failures)


def test_public_system_paper_check_rejects_terms_used_before_definition(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    contract = r"\section{The component contract}"
    before, after = source.split(contract, 1)
    for index, term in enumerate(("validator", "commit")):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(
            before + f"\nThe opening uses {term} too early.\n" + contract + after,
            encoding="utf-8",
        )

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any(
            "technical term precedes its definition" in failure and term in failure
            for failure in failures
        )


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


def test_public_system_paper_check_rejects_late_paper_testing_jargon(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    for index, residue in enumerate(
        (
            "bounded, deterministic, and runnable in isolation",
            "supplies regression evidence",
            "held-out cases",
            "A second interpreter check",
            "the pinned manifest records none",
            "Route the audio example with",
        )
    ):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(source + f"\n{residue}\n", encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any("cold-reader residue" in failure for failure in failures)


def test_public_system_paper_check_rejects_opaque_academic_record_and_evaluation_terms(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    for index, residue in enumerate(
        (
            "machine-readable",
            "reference run",
            "Freezing a version",
            "version is frozen",
            "inputs to freeze",
            "inputs were frozen",
            "empirical adequacy",
            "artefact",
            "private origin",
            "support for the claim as worded",
            "behaviour beyond selected cases",
            "self-supplied success criteria",
            "in order to",
            "fixed denominator",
        )
    ):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(source + f"\n{residue}\n", encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any("cold-reader residue" in failure for failure in failures)


def test_public_system_paper_check_rejects_opening_definition_or_method_scope_loss(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    cases = (
        (
            "registered\ncomponents (separately testable parts)",
            "registered\ncomponents",
            "registered components (separately testable parts)",
        ),
        (
            "I borrow only those two terms",
            "I apply this method",
            "I borrow only those two terms",
        ),
    )
    for index, (original, replacement, expected_anchor) in enumerate(cases):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(source.replace(original, replacement), encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any(
            "missing plain-language orientation anchor" in failure
            and expected_anchor in failure
            for failure in failures
        )


def test_public_system_paper_check_rejects_ambiguous_limit_language(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    for index, residue in enumerate(
        (
            "Bounded public evidence",
            "record a bounded refusal",
            "bounded point of contact",
            "bounded correctness",
            "bounded examples",
            "bounded behaviour",
            "bounded calculation",
            "bounded cases only",
            "support bounded claims",
            r"bounded \code{make test} selection",
            "exercisability",
        )
    ):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(source + f"\n{residue}\n", encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any("cold-reader residue" in failure for failure in failures)


def test_public_system_paper_check_rejects_opaque_subtitle(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "What public evidence can and cannot show about a private system",
            "Bounded public evidence from a private system",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("cold-reader residue" in failure for failure in failures)
    assert any(
        "missing plain-language orientation anchor" in failure
        and "What public evidence can and cannot show" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_plain_language_reversal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "gives the same output from the same input, and runs in isolation",
            "is deterministic and can run alone",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language orientation anchor" in failure
        and "same output from the same input" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_internal_label_explanation_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "README-first order\n"
            r"(internally \component{readme_onboarding_route})",
            r"README-first order (\component{readme_onboarding_route})",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing appendix internal-label explanation" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_redundant_appendix_article(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\section{Dated reproduction record}",
            r"\section{A dated reproduction record}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing appendix internal-label explanation" in failure
        and "Dated reproduction record" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_example_bridge_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "The calculator check derives one expected number without the implementation.",
            "The example is complete.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing example-to-distinctions bridge" in failure
        and "without the implementation" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_arithmetic_oracle_overclaim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "but not of the project's formula.",
            "This oracle is independent of the project.",
        )
        .replace(
            "it does not validate the formula.",
            "That proves the formula is correct.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing arithmetic-oracle boundary" in failure
        and "not of the project's formula" in failure
        for failure in failures
    )
    assert any(
        "missing arithmetic-oracle boundary" in failure
        and "does not validate the formula" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_opaque_lean_trust_explanation(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "for six warning signs: unfinished proof placeholders; custom axioms\n"
            "(assumptions added without proof)",
            "for several trust issues",
        )
        .replace(
            "compiled calculations whose acceptance\n"
            "relies on more than Lean's small proof-checking core (the kernel)",
            "the kernel is not enough",
        )
        .replace(
            r"\code{partial} definitions, which can run but cannot be unfolded in proofs",
            r"\code{partial} definitions are opaque",
        )
        .replace(
            r"\code{unsafe} definitions, which cannot be used in theorems",
            r"\code{unsafe} definitions are excluded",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert sum("missing Lean check explanation" in failure for failure in failures) >= 4


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


def test_public_system_paper_check_rejects_receipt_reading_guidance_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "Copy the no-write line",
            "Run either command",
        )
        .replace(r"\code{expected\_level}", r"\code{result}")
        .replace(r"\code{anti\_claim}", r"\code{status}"),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "Copy the no-write line" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\\code{expected\\_level}" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\\code{anti\\_claim}" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_hash_explanation_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "a fixed 256-bit value calculated from its contents",
            "a digest",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language hash boundary" in failure
        and "fixed 256-bit value" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_collision_strength_source_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "resistance at 128 bits",
            "resistance at an unspecified strength",
        )
        .replace(
            r"\cite{nisthashfunctions}",
            r"\cite{nistfips1804}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language hash boundary" in failure
        and "collision resistance at 128 bits" in failure
        for failure in failures
    )
    assert "missing literature citation: nisthashfunctions" in failures


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


def test_public_system_paper_check_rejects_opaque_figure_vocabulary(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    cases = (
        ("change the input", "perturb it"),
        (r"I chose and\\adapted these", r"selection and\\re-expression"),
        (
            "Each public component\n"
            r"has the parts shown in Figure~\ref{fig:contract}",
            "Each, unpacked, has the anatomy of Figure",
        ),
        ("origin: evidence about where it came from", "origin: provenance evidence"),
        (
            "correctness: an answer derived separately",
            "standard: an independent oracle",
        ),
        (
            "Each dashed arrow needs a further assumption",
            "Each dashed arrow needs a further premise",
        ),
    )
    for index, (plain, opaque) in enumerate(cases):
        paper = tmp_path / f"paper-{index}.tex"
        paper.write_text(source.replace(plain, opaque), encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any("cold-reader residue" in failure for failure in failures)
        assert any("missing cold-reader anchor" in failure for failure in failures)


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
