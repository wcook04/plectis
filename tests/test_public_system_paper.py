from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

import pytest

from scripts.check import check_public_system_paper as paper_check

GUIDE_CITATION = r"\newcommand{\artifactguide}{\href{\repourl/blob/main/paper/README.md}{Plectis artifact and reproduction guide}}"


@pytest.fixture
def paper_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path, dict[str, int]]:
    root = tmp_path / "checkout"
    root.mkdir()
    counts = dict(zip(paper_check.COUNT_MACROS, (12, 4, 236, 28, 9, 31)))
    for ref in paper_check.REQUIRED_ARTIFACTS:
        target = root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("source fixture\n", encoding="utf-8")
    recipes = []
    for _command, (target, scripts, native) in paper_check.REPRODUCTION.items():
        recipe = target + ":\n"
        for script in scripts:
            path = root / script
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# reproduction owner fixture\n", encoding="utf-8")
            recipe += '\tpython3 ' + script + (' --dafny "$(DAFNY)"' if native else '') + '\n'
        recipes.append(recipe)
    (root / "Makefile").write_text("\n".join(recipes), encoding="utf-8")
    paper = root / "paper/plectis-public-system.tex"
    paper.parent.mkdir()
    lines = [r"\newcommand{\repourl}{" + paper_check.REPOSITORY_URL + "}", GUIDE_CITATION]
    lines += ["\\newcommand{\\" + key + "}{" + str(value) + "}" for key, value in counts.items()]
    lines += ["Recorded evidence: " + " ".join("\\" + key + "{}" for key in counts), r"See the \artifactguide{}."]
    paper.write_text("\n".join(lines) + "\n", encoding="utf-8")
    guide = root / paper_check.GUIDE
    guide_lines = ["# Plectis artifact and reproduction guide"]
    guide_lines += ["[Source](../" + ref + ")" for ref in sorted(paper_check.REQUIRED_ARTIFACTS)]
    guide_lines += ["```sh", *paper_check.REPRODUCTION, "```"]
    guide.write_text("\n".join(guide_lines) + "\n", encoding="utf-8")
    monkeypatch.setattr(paper_check, "bound_counts", lambda selected_root: counts if selected_root == root else {})
    return root, paper, guide, counts


def test_public_system_paper_matches_bound_counts_refs_and_commands(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    assert paper_check.check_paper(paper, repository_root=root) == []


@pytest.mark.parametrize("name", paper_check.COUNT_MACROS)
def test_public_system_paper_rejects_count_drift(paper_case, name: str) -> None:
    root, paper, _guide, counts = paper_case
    before = "\\newcommand{\\" + name + "}{" + str(counts[name]) + "}"
    after = "\\newcommand{\\" + name + "}{" + str(counts[name] + 1) + "}"
    paper.write_text(paper.read_text().replace(before, after, 1))
    assert f"{name}={counts[name] + 1}, current bound metadata={counts[name]}" in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_rejects_full_catalogue_formalization_count(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text().replace(
        r"\newcommand{\formalcomponentcount}{12}", r"\newcommand{\formalcomponentcount}{88}", 1))
    assert "formalcomponentcount=88, current bound metadata=12" in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_rejects_missing_source_citation(paper_case) -> None:
    root, paper, guide, _counts = paper_case
    source = "formal/components/ownership_classification/OwnershipClassification.dfy"
    guide.write_text(guide.read_text().replace("[Source](../" + source + ")", "", 1))
    assert "artifact guide missing source link: " + source in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_rejects_source_path_drift(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    (root / "src/microcosm_core/component_replay.py").unlink()
    assert any("missing or nonlocal repository reference: src/microcosm_core/component_replay.py" in item
               for item in paper_check.check_paper(paper, repository_root=root))


@pytest.mark.parametrize("kind", ["absolute", "traversal", "symlink"])
def test_public_system_paper_rejects_reference_outside_checkout(paper_case, tmp_path: Path, kind: str) -> None:
    root, paper, guide, _counts = paper_case
    outside = tmp_path / "outside.py"
    outside.write_text("outside fixture\n")
    if kind == "absolute":
        ref = quote(str(outside))
    elif kind == "traversal":
        ref = "../../outside.py"
    else:
        (root / "linked.py").symlink_to(outside)
        ref = "../linked.py"
    guide.write_text(guide.read_text() + "[Outside](" + ref + ")\n")
    assert any("repository reference:" in item for item in paper_check.check_paper(paper, repository_root=root))


def test_public_system_paper_rejects_missing_reproduction_command(paper_case) -> None:
    root, paper, guide, _counts = paper_case
    command = "make verify-components DAFNY=/absolute/path/to/dafny"
    guide.write_text(guide.read_text().replace(command, "make verify-components", 1))
    assert "artifact guide missing literal reproduction command: " + command in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_rejects_reproduction_target_that_stops_verifying(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    makefile = root / "Makefile"
    makefile.write_text(makefile.read_text().replace(' --dafny "$(DAFNY)"', "", 1))
    assert any("Make target no longer invokes its reproduction owner: verify-components" in item
               for item in paper_check.check_paper(paper, repository_root=root))


def test_public_system_paper_ignores_comments_as_evidence(paper_case) -> None:
    root, paper, guide, _counts = paper_case
    ref = "formal/replay/ReplayAdmission.dfy"
    command = "make component-replays"
    text = guide.read_text().replace("[Source](../" + ref + ")", "<!-- [Source](../" + ref + ") -->", 1)
    guide.write_text(text.replace(command, "<!-- " + command + " -->", 1))
    failures = paper_check.check_paper(paper, repository_root=root)
    assert "artifact guide missing source link: " + ref in failures
    assert "artifact guide missing literal reproduction command: " + command in failures


def test_public_system_paper_rejects_declared_but_unused_or_duplicate_count(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    text = paper.read_text().replace(r"\mutantcount{}", "28", 1)
    paper.write_text(text + r"\newcommand{\formalcomponentcount}{12}" + "\n")
    failures = paper_check.check_paper(paper, repository_root=root)
    assert "paper count macro is not used: mutantcount" in failures
    assert "paper must declare one integer macro: formalcomponentcount" in failures


def test_public_system_paper_propagates_formal_binding_failure(paper_case, monkeypatch: pytest.MonkeyPatch) -> None:
    root, paper, _guide, _counts = paper_case

    def changed_source(_root: Path) -> dict[str, int]:
        raise ValueError("generated component bytes changed: ownership_classification")

    monkeypatch.setattr(paper_check, "bound_counts", changed_source)
    assert "formal evidence binding failed (proof not rerun): generated component bytes changed: ownership_classification" in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_main_keeps_exit_and_output_contract(paper_case, capsys) -> None:
    root, paper, guide, _counts = paper_case
    assert paper_check.main(["--root", str(root), "--paper", str(paper), "--guide", str(guide)]) == 0
    assert capsys.readouterr().out.startswith("Public-system paper check: pass")
    paper.unlink()
    assert paper_check.main(["--root", str(root), "--paper", str(paper)]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("Public-system paper check: 1 failure(s)")
    assert "cannot read paper:" in captured.err


def test_public_system_paper_does_not_require_prescribed_paragraphs(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + "The reader can inspect the operation and its finite input model.\n")
    assert paper_check.check_paper(paper, repository_root=root) == []


@pytest.mark.parametrize("snippet", [
    r"\begin{Verbatim}sample\end{Verbatim}",
    r"\begin{verbatim}sample\end{verbatim}",
    r"\begin{lstlisting}sample\end{lstlisting}",
    r"\begin{minted}{python}sample\end{minted}",
    r"\DefineVerbatimEnvironment{sample}{Verbatim}{}",
    r"\lstinputlisting{sample}",
    r"\newminted{dafny}{}",
    r"\texttt{method Compute}",
    r"\artifactref{formal/components/README.md}",
    r"\path{src/plectis/replay.py}",
    "```sh\nexample command\n```",
])
def test_public_system_paper_rejects_code_and_path_printing_mechanisms(paper_case, snippet: str) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + snippet + "\n")
    assert "manuscript must not contain code, command or path-printing blocks/macros" in paper_check.check_paper(paper, repository_root=root)


@pytest.mark.parametrize("path", [
    "formal/components/ownership_classification/OwnershipClassification.dfy",
    "src/microcosm_core/component_replay.py", "OwnershipClassification.dfy",
])
def test_public_system_paper_rejects_raw_implementation_paths(paper_case, path: str) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + path + "\n")
    assert "manuscript must not print raw implementation paths" in paper_check.check_paper(paper, repository_root=root)


@pytest.mark.parametrize("command", paper_check.REPRODUCTION)
def test_public_system_paper_rejects_reproduction_commands_in_manuscript(paper_case, command: str) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + command + "\n")
    assert "manuscript must not contain reproduction commands" in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_requires_human_readable_guide_citation(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text().replace(r"\artifactguide{}", "the guide", 1))
    assert "paper must cite the artifact and reproduction guide" in paper_check.check_paper(paper, repository_root=root)


@pytest.mark.parametrize("before,after", [
    ("Plectis artifact and reproduction guide", "paper/README.md"),
    ("blob/main/paper/README.md", "blob/main/paper/missing.md"),
])
def test_public_system_paper_rejects_wrong_guide_label_or_target(paper_case, before: str, after: str) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text().replace(before, after, 1))
    assert "paper must define its human-readable artifact-guide citation" in paper_check.check_paper(paper, repository_root=root)


def test_public_system_paper_external_guide_uses_its_public_logical_location(paper_case, tmp_path: Path) -> None:
    root, paper, guide, _counts = paper_case
    external = tmp_path / "candidate-guide.md"
    external.write_text(guide.read_text())
    assert paper_check.check_paper(paper, repository_root=root, artifact_guide_path=external) == []


def test_public_system_paper_allows_native_tikz_implementation(paper_case) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + r"\begin{tikzpicture}\path (0,0) edge (1,1);\end{tikzpicture}" + "\n")
    assert paper_check.check_paper(paper, repository_root=root) == []


@pytest.mark.parametrize("definition,failure", [
    (r"\newcommand{\proofsource}{src/microcosm_core/component_replay.py}", "manuscript must not print raw implementation paths"),
    (r"\newcommand{\reproduce}{make component-replays}", "manuscript must not contain reproduction commands"),
])
def test_public_system_paper_rejects_paths_or_commands_wrapped_in_macros(paper_case, definition: str, failure: str) -> None:
    root, paper, _guide, _counts = paper_case
    paper.write_text(paper.read_text() + definition + "\n")
    assert failure in paper_check.check_paper(paper, repository_root=root)
