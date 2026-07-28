from __future__ import annotations

import ast
import json
from pathlib import Path

from scripts import check_public_system_paper as paper_check
from scripts.check_public_system_paper import PAPER, check_paper


def test_literal_mutation_sources_match_current_paper() -> None:
    """Reject negative fixtures whose literal replacement no longer takes effect."""
    paper_source = PAPER.read_text(encoding="utf-8")
    test_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    literal_replace_calls = [
        node
        for node in ast.walk(test_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "replace"
        and len(node.args) >= 2
        and isinstance(node.args[0], ast.Constant)
        and isinstance(node.args[0].value, str)
        and isinstance(node.args[1], ast.Constant)
        and isinstance(node.args[1].value, str)
    ]
    introduced = {node.args[1].value for node in literal_replace_calls}
    stale = sorted(
        {
            node.args[0].value
            for node in literal_replace_calls
            if node.args[0].value not in paper_source
            and node.args[0].value not in introduced
        }
    )
    assert stale == []


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
            "I report that its published material was copied or adapted from that\n"
            "system",
            "It was assembled from parts of a larger private system,",
        )
        .replace(
            "The argument does not depend on that account or on the\n"
            "claimed origin of the published material.",
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


def test_public_system_paper_check_rejects_universal_private_testimony_claim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "The repository cannot by itself support my assertions about the unseen private\n"
            "system. A component does something narrower: it gives a related public claim a\n"
            "procedure that can fail in front of a stranger. The procedure\n"
            "does not make the claim true or establish the published fragment's origin.",
            "An assertion about private software can only be believed or doubted as\n"
            "testimony. A component converts the assertion into a procedure, and the\n"
            "conversion does not make the claim true.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "forbidden overclaim remains in paper" in failure
        and "private software can only be believed" in failure
        for failure in failures
    )
    assert sum(
        "missing private-evidence scope boundary" in failure for failure in failures
    ) == len(paper_check.REQUIRED_PRIVATE_EVIDENCE_SCOPE_ANCHORS)


def test_public_system_paper_check_rejects_method_boundary_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"\paragraph{What I examined.}",
            r"\paragraph{Approach.}",
        )
        .replace(
            "At the named repository version, I read the list\n"
            "and plain descriptions of all \\componentcount{} components, counted them by\n"
            "project group and by the kind of public evidence offered, traced the worked\n"
            "component from input to limit, and reran the appendix's public commands. I did\n"
            "not compare every pass rule with its prose claim or derive fresh expected\n"
            "answers; Section~\\ref{sec:stronger} reserves those checks for an outside\n"
            "evaluator.",
            "I examined the repository and report the result.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert sum(
        "missing first-section method disclosure" in failure
        for failure in failures
    ) == 9


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
                "miss. These short labels correspond to familiar questions about provenance,\n"
                "test-oracle validity, claim--test fidelity, representativeness, and residual\n"
                "risk. They are not five new kinds of evidence. Each subsection separates what\n"
                "the public run directly shows from the additional premise needed for a stronger\n"
                "conclusion.",
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


def test_public_system_paper_check_rejects_pinned_receipt_flow_source_drift(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        paper_check,
        "_load_text_from_commit",
        lambda _commit, _path, _failures: "",
    )

    failures = paper_check.check_paper()

    assert any(
        "pinned receipt-flow source lacks" in failure
        and "expected_level" in failure
        for failure in failures
    )
    assert any(
        "pinned receipt-flow source lacks" in failure
        and "write_json_atomic" in failure
        for failure in failures
    )


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
        .replace(r"\bibitem{barr2015}", r"\bibitem{nasem2019}")
        .replace(r"\bibitem{order-swap}", r"\bibitem{barr2015}"),
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


def test_public_system_paper_check_rejects_test_oracle_source_drift(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "https://doi.org/10.1109/TSE.2014.2372785",
            "https://example.invalid/indirect-oracle-source",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "bibliography item barr2015 lacks canonical token" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_sacm_evidential_link_overclaim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "the relationship is itself an assertion by the case's author",
            "the relationship independently validates the claim",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing SACM source-fit explanation" in failure
        and "relationship is itself an assertion" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_opaque_test_oracle_explanation(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "procedure used to distinguish\n"
            "correct from incorrect behaviour",
            "mechanism used to judge output",
        )
        .replace(
            r"\textbf{Who or what supplies the expected answer}",
            r"\textbf{Where the oracle lives}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language test-oracle explanation" in failure
        for failure in failures
    )
    assert any("cold-reader residue" in failure for failure in failures)


def test_public_system_paper_check_rejects_missing_source_pinpoint(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\cite[conclusion 3-1]{nasem2019}",
            r"\cite{nasem2019}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing source pinpoint" in failure and "conclusion 3-1" in failure
        for failure in failures
    )
    assert not any(
        "missing literature citation: nasem2019" in failure for failure in failures
    )


def test_public_system_paper_check_rejects_missing_correctness_pinpoint(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\cite[p.~9]{nasem2019}",
            r"\cite{nasem2019}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing source pinpoint" in failure and "p.~9" in failure
        for failure in failures
    )
    assert not any(
        "missing literature citation: nasem2019" in failure for failure in failures
    )


def test_public_system_paper_check_rejects_narrow_bibliography_label_width(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\begin{thebibliography}{12}",
            r"\begin{thebibliography}{9}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert "bibliography label width must match item count: expected 12" in failures


def test_public_system_paper_check_rejects_tiny_bibliography_type(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            r"\fontsize{7.5pt}{8.3pt}\selectfont",
            r"\fontsize{6.6pt}{7.25pt}\selectfont",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert "bibliography font must be at least 7.5pt" in failures


def test_public_system_paper_check_rejects_prior_art_boundary_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "not an\nimplementation of that standard",
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
            "chooses scope, methods, and schedule",
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
    for index, term in enumerate(paper_check.FORBIDDEN_BEFORE_COMPONENT_CONTRACT):
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
            "The paper examines one author-curated software\ncollection",
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


def test_public_system_paper_check_rejects_abstract_answer_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace("The answer\nis narrow", "The design has several properties")
        .replace(
            "lets a reader inspect and rerun its published\n"
            "procedures",
            "provides a sophisticated architecture",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language orientation" in failure
        and "answer is narrow" in failure
        for failure in failures
    )
    assert any(
        "missing plain-language orientation" in failure
        and "inspect and rerun" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_unexpanded_first_use(
    tmp_path: Path,
) -> None:
    source = PAPER.read_text(encoding="utf-8")
    cases = (
        ("artificial\nintelligence (AI)", "AI"),
        ("Structured Assurance Case Metamodel (SACM)", "SACM"),
        ("Association for Computing Machinery (ACM)", "ACM"),
        ("National Institute of Standards and Technology (NIST)", "NIST"),
        ("National Aeronautics and Space Administration (NASA)", "NASA"),
    )
    for index, (expansion, abbreviation) in enumerate(cases):
        paper = tmp_path / f"paper-first-use-{index}.tex"
        paper.write_text(source.replace(expansion, abbreviation, 1), encoding="utf-8")

        failures = check_paper(paper_path=paper, check_git_commit=False)

        assert any(
            f"missing first-use expansion for {abbreviation}" in failure
            or f"abbreviation appears before its expansion: {abbreviation!r}"
            in failure
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
            "registered components (separately testable parts)",
            "registered components",
            "registered components (separately testable parts)",
        ),
        (
            "I\nborrow only those two terms",
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


def test_public_system_paper_check_keeps_legacy_names_in_appendix(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "Nothing in\n"
            "these labels grades the importance of what a component does.",
            "Nothing in\n"
            "these labels grades the importance of what a component does. "
            "The project was previously called Microcosm.",
        )
        .replace(
            "Formerly Microcosm, Plectis retains\n"
            "package",
            "Plectis uses package",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "legacy naming prose must stay in the reproduction appendix" in failure
        and "previously called Microcosm" in failure
        for failure in failures
    )
    assert any(
        "missing appendix legacy-name mapping" in failure
        and "Formerly Microcosm" in failure
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


def test_public_system_paper_check_rejects_unexplained_expected_refusal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "Here \\emph{pass} means ``refused as expected''; "
            "\\code{pcm24} was not accepted.",
            "The last row passed.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing expected-refusal explanation" in failure
        and "refused as expected" in failure
        for failure in failures
    )
    assert any(
        "missing expected-refusal explanation" in failure
        and "not accepted" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_arithmetic_oracle_overclaim(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "but not of the project's\nformula.",
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
            "six text patterns",
            "for several trust issues",
        )
        .replace(
            "compiled calculations whose acceptance\n"
            "relies on more than Lean's small proof-checking core",
            "the kernel is not enough",
        )
        .replace(
            r"\code{partial} definitions (runnable but not unfoldable in proofs)",
            r"\code{partial} definitions are opaque",
        )
        .replace(
            r"\code{unsafe} definitions (barred from theorems)",
            r"\code{unsafe} definitions are excluded",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert sum("missing Lean check explanation" in failure for failure in failures) >= 4


def test_public_system_paper_check_rejects_lean_scan_boundary_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "does not run Lean or verify\nproofs",
            "it checks Lean",
        )
        .replace(
            "The scan does not show whether files compile,\nproofs are valid",
            "A pass confirms the project is valid",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing Lean check explanation" in failure
        and "does not run Lean or verify proofs" in failure
        for failure in failures
    )
    assert any(
        "missing Lean check explanation" in failure
        and "files compile" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_lean_scan_execution_conflation(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "Separate components run Lean on small test projects; their results apply only\n"
            "to those projects.",
            "This scan confirms the same results as the Lean-running components.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing Lean check explanation" in failure
        and "Separate components run Lean on small test projects" in failure
        for failure in failures
    )
    assert any(
        "missing Lean check explanation" in failure
        and "results apply only to those projects" in failure
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
            "but do not run its first suggested\ncommand",
            "and run its first suggested\ncommand",
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
        and "do not run its first suggested command" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_receipt_reading_guidance_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "writes to the repository's saved receipt paths",
            "can be run safely",
        )
        .replace(r"\code{expected\_level}", r"\code{result}")
        .replace(r"\component{anti_claim}", r"\code{status}"),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "saved receipt paths" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\\code{expected\\_level}" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\\component{anti_claim}" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_concrete_challenge_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"\component{batch8_audio_level_rms_port_probe_manifest.json}",
            "the input file",
        )
        .replace(
            r"second sample from \code{0.05} to \code{0.06}",
            "one sample",
        )
        .replace(
            r"final number printed should be \code{1}",
            "the command should respond",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "probe_manifest.json" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "second sample" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "final number printed" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_noncopyable_challenge_commands(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "cp -R fixtures/first_wave/batch8_audio_level_rms_port/input/.",
            "copy the fixture input somewhere safe",
        )
        .replace(
            "--input /tmp/plectis-audio-rms-input",
            "--input the-copy",
        )
        .replace(
            "--out /tmp/plectis-audio-rms-probe",
            "--out somewhere",
        )
        .replace(
            "  --acceptance-out /tmp/plectis-audio-rms-check.json",
            "  --acceptance-out somewhere.json",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "cp -R fixtures" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "--input /tmp/plectis-audio-rms-input" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "--out /tmp/plectis-audio-rms-probe" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "--acceptance-out /tmp/plectis-audio-rms-check.json" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_unexplained_blocked_exit(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace("echo $?", "true")
        .replace(
            r"\code{status} should be \code{blocked}",
            "the status should indicate a problem",
        )
        .replace(
            "\\code{accepted} should be\n\\code{false}",
            "the run should not be accepted",
        )
        .replace(
            "validator caught the deliberate mismatch; the\n"
            "exercise did not crash",
            "the expected outcome",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing executable first-review route" in failure
        and "echo $?" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\code{status}" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and r"\code{accepted}" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "did not crash" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_copyable_worked_example_command_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "  batch8-audio-level-rms-port run \\\n",
            "  run-something \\\n",
        )
        .replace(
            r"\component{batch8_audio_level_rms_port_result.json}",
            r"\component{result.json}",
        )
        .replace(
            r"format. Open \code{exercise}",
            "In the result",
        )
        .replace(
            "The project wrote both cautions; no independent\n"
            "reviewer checked their limits.",
            "Both fields prove the stated limit.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing copyable worked-example command" in failure
        and "batch8-audio-level-rms-port" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "batch8_audio_level_rms_port_result.json"
        in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "exercise" in failure
        for failure in failures
    )
    assert any(
        "missing executable first-review route" in failure
        and "no independent reviewer" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_old_first_review_translation_detour(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        + "\nThe command starts with the installed command; replace it with another launcher.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert sum("cold-reader residue" in failure for failure in failures) >= 2


def test_public_system_paper_check_rejects_hash_explanation_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8").replace(
            "SHA-256 message digest, used here as a fingerprint: a 256-bit value calculated",
            "a digest",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language hash boundary" in failure
        and "SHA-256 message digest" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_second_preimage_distinction_source_removal(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            "NIST)\ncalls this second-preimage resistance",
            "NIST)\ncalls this a collision check",
        )
        .replace(
            "That differs from collision\nresistance",
            "That is collision\nresistance",
        )
        .replace(
            r"\cite[security-strength table]{nisthashfunctions}",
            r"\cite{nistfips1804}",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing plain-language hash boundary" in failure
        and "second-preimage resistance" in failure
        for failure in failures
    )
    assert any(
        "missing plain-language hash boundary" in failure
        and "differs from collision resistance" in failure
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
            "They cannot create an independent witness",
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


def test_public_system_paper_check_rejects_ambiguous_component_page_route(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"public component map," "\n" r"\component{ORGANS.md}",
            "component documentation",
        )
        .replace(
            r"\component{paper_modules/batch8_audio_level_rms_port.md}",
            "the worked example page",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing collection route explanation" in failure
        and "ORGANS.md" in failure
        for failure in failures
    )
    assert any(
        "missing collection route explanation" in failure
        and "batch8_audio_level_rms_port.md" in failure
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
            "Calling them evidence does not establish\n"
            "their adequacy",
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
            "custom axioms\n(unproved assumptions)",
            "custom axioms",
        )
        .replace(
            "scan does not show whether files compile,\n"
            "proofs are valid, or statements express their authors' intent",
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
            "This\nfigure has no dashed boxes",
            "The dashed boxes are hidden",
        )
        .replace("italic blue row", "blue row")
        .replace("Read the middle row from left to right", "Read the diagram")
        .replace("in italic\nblue", "in blue")
        + "\nA dashed outline marks what a stranger cannot run or observe directly.\n",
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("This figure has no dashed boxes" in failure for failure in failures)
    assert any("Read the middle row from left to right" in failure for failure in failures)
    assert any("italic blue row" in failure for failure in failures)
    assert any("in italic blue" in failure for failure in failures)
    assert any(
        "dashed outline marks what a stranger cannot" in failure
        for failure in failures
    )


def test_public_system_paper_check_rejects_inverted_receipt_flow(
    tmp_path: Path,
) -> None:
    paper = tmp_path / "paper.tex"
    paper.write_text(
        PAPER.read_text(encoding="utf-8")
        .replace(
            r"\draw[flow] (val) -- node[flabel, right]{records} (rec);",
            r"\draw[flow] (rec) -- (val);",
        )
        .replace(
            "does not determine the new verdict",
            "determines the new verdict",
        )
        .replace(
            "same checked values and verdict as the stored receipt",
            "stored receipt",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any(
        "missing receipt-flow explanation" in failure and "records" in failure
        for failure in failures
    )
    assert any(
        "missing receipt-flow explanation" in failure
        and "does not determine" in failure
        for failure in failures
    )
    assert any(
        "missing receipt-flow explanation" in failure
        and "same checked values" in failure
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
            "Moving a relevant choice out of the author's hands\n"
            "can strengthen evidence about that choice; it does not repair every gap.",
            "Stronger evidence requires at least one consequential choice to leave "
            "the author's hands.",
        ),
        encoding="utf-8",
    )

    failures = check_paper(paper_path=paper, check_git_commit=False)

    assert any("Moving a relevant choice" in failure for failure in failures)
    assert any("stronger evidence requires" in failure for failure in failures)
