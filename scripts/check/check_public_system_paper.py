#!/usr/bin/env python3
"""Bind the short paper's counts and its separate artifact/reproduction guide.

This current-file check reuses the formal owners' hash-only checks. It does
not run a prover, authenticate a past run, or review mathematical meaning.
Implementation paths and commands belong in the guide, outside the manuscript.
"""
from __future__ import annotations

import argparse
from pathlib import Path, PurePosixPath
import posixpath
import re
import runpy
import sys
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[2]
PAPER = ROOT / "paper/plectis-public-system.tex"
GUIDE = "paper/README.md"
REPOSITORY_URL = "https://github.com/wcook04/practical-formal-verification"
MACRO_RE = re.compile(r"\\newcommand\{\\([A-Za-z]+)\}\{([^{}]*)\}")
GUIDE_CITATION_RE = re.compile(
    r"\\newcommand\{\\artifactguide\}\s*\{\s*\\href\s*"
    r"\{\\repourl/blob/main/paper/README\.md\}\s*"
    r"\{Plectis\s+artifact\s+and\s+reproduction\s+guide\}\s*\}", re.DOTALL,
)
COUNT_MACROS = (
    "formalcomponentcount", "workflowcorecount", "verifiedtaskcount",
    "mutantcount", "ownershiptaskcount", "navigationtaskcount",
)
WORKFLOW_CHECKS = {
    "repair": "check_repair_kernel.py",
    "compatibility": "check_compatibility_kernel.py",
    "views": "check_views_kernel.py",
    "replay": "check_replay_kernel.py",
}
REQUIRED_ARTIFACTS = frozenset({
    "formal/components/ownership_classification/OwnershipClassification.dfy",
    "src/microcosm_core/organs/concurrency_mission_control.py",
    "tests/test_component_ownership_classification.py",
    "formal/components/evidence_diff/EvidenceDiff.dfy",
    "src/plectis/components/evidence_diff/_adapter.py",
    "tests/test_component_evidence_diff.py",
    "formal/replay/ReplayAdmission.dfy",
    "src/microcosm_core/component_replay.py",
    "formal/README.md",
    "formal/components/README.md",
})
REPRODUCTION = {
    "make verify-components DAFNY=/absolute/path/to/dafny": (
        "verify-components", ("scripts/check/check_component_kernels.py",), True,
    ),
    "make verify-operations DAFNY=/absolute/path/to/dafny": (
        "verify-operations", tuple("scripts/check/" + name for name in WORKFLOW_CHECKS.values()), True,
    ),
    "make component-replays": (
        "component-replays", ("scripts/check/check_component_replays.py",), False,
    ),
}
CODE_ENVIRONMENT_RE = re.compile(
    r"\\begin\{(?:[BLV]?verbatim|lstlisting|minted|alltt|code|codeblock|"
    r"commandblock|shell|console|algorithm|algorithmic|pseudocode|program)\*?\}", re.IGNORECASE,
)
CODE_MECHANISM_RE = re.compile(
    r"\\(?:verb|lstinline|mintinline|lstinputlisting|inputminted|verbatiminput|"
    r"VerbatimInput|DefineVerbatimEnvironment|lstnewenvironment|newminted|"
    r"texttt|ttfamily|code|artifactref)\b",
)
IMPLEMENTATION_PATH_RE = re.compile(
    r"\b(?:formal|src|tests|scripts|examples|fixtures|receipts|core|docs|paper_modules|standards|paper)/"
    r"[A-Za-z0-9_./-]+|\b[A-Za-z][A-Za-z0-9_-]*\.(?:dfy|py|json|tex|sh|lean)\b",
)
MANUSCRIPT_COMMAND_RE = re.compile(
    r"\bmake\s+(?:verify-components|verify-operations|component-replays)\b|"
    r"\b(?:python3?|plectis|tectonic|dafny)\s+(?:--?[A-Za-z]|scripts/|verify\b|build\b)",
)


def _visible_source(text: str) -> str:
    return re.sub(r"(?<!\\)%[^\n]*", "", text)


def _local_file(root: Path, ref: str) -> Path:
    path = PurePosixPath(ref)
    if not ref or path.is_absolute() or ".." in path.parts or "\x00" in ref:
        raise ValueError("unsafe repository reference: " + repr(ref))
    resolved = (root / ref).resolve()
    if not resolved.is_relative_to(root.resolve()) or not resolved.is_file():
        raise ValueError("missing or nonlocal repository reference: " + ref)
    return resolved


def _mutant_count(metadata: dict) -> int:
    if "negative_sources" in metadata:
        return len(metadata["negative_sources"])
    if "negative_controls" in metadata:
        return len(metadata["negative_controls"])
    return sum(key == "negative_source" or key.endswith("_negative_source") for key in metadata)


def bound_counts(root: Path) -> dict[str, int]:
    """Read counts only after the existing formal owners validate retained bytes."""
    component = runpy.run_path(str(root / "scripts/check/check_component_kernels.py"))
    kernels = component["discover"](root)
    component_rows = {slug: component["check_binding"](root, slug, module)
                      for slug, module in sorted(kernels.items())}
    actual_workflows = {path.parent.name for path in (root / "formal").glob("*/metadata.json")}
    if actual_workflows != set(WORKFLOW_CHECKS):
        raise ValueError("workflow formal inventory differs from the paper's reviewed cores")
    workflow_rows = {}
    for name, filename in WORKFLOW_CHECKS.items():
        owner = runpy.run_path(str(root / "scripts/check" / filename))
        generated = root / "src/plectis" / name / "_generated"
        if name == "views":
            owner["bindings"](generated)
        elif name == "replay":
            owner["check_binding"](root)
        else:
            owner["check_binding"](root, generated)
        workflow_rows[name] = component["_read_json"](root / "formal" / name / "metadata.json")
    rows = [*component_rows.values(), *workflow_rows.values()]
    return {
        "formalcomponentcount": len(component_rows), "workflowcorecount": len(workflow_rows),
        "verifiedtaskcount": sum(row["verified_tasks"] for row in rows),
        "mutantcount": sum(_mutant_count(row) for row in rows),
        "ownershiptaskcount": component_rows["ownership_classification"]["verified_tasks"],
        "navigationtaskcount": component_rows["navigation_metrics"]["verified_tasks"],
    }


def _command_failures(text: str, root: Path) -> list[str]:
    failures = []
    makefile = (root / "Makefile").read_text(encoding="utf-8")
    for command, (target, scripts, native) in REPRODUCTION.items():
        if not re.search(r"^[ \t]*" + re.escape(command) + r"[ \t]*$", text, re.MULTILINE):
            failures.append("artifact guide missing literal reproduction command: " + command)
        block = re.search(r"^" + re.escape(target) + r":[^\n]*\n((?:[ \t].*\n|\n)*)",
                          makefile, re.MULTILINE)
        recipe = block.group(1) if block else ""
        for script in scripts:
            _local_file(root, script)
            lines = [line for line in recipe.splitlines() if script in line and line.startswith("\t")]
            if not lines or (native and not any("--dafny" in line for line in lines)):
                failures.append("Make target no longer invokes its reproduction owner: " + target + ": " + script)
    return failures


def _guide_failures(guide_path: Path, root: Path) -> list[str]:
    _local_file(root, GUIDE)
    text = re.sub(r"<!--.*?-->", "", guide_path.read_text(encoding="utf-8"), flags=re.DOTALL)
    failures, refs = [], set()
    for target in re.findall(r"\[[^\]]+\]\(([^\s)]+)\)", text):
        url = urlsplit(target)
        if url.scheme or url.netloc:
            continue
        relative = posixpath.normpath(posixpath.join("paper", unquote(url.path)))
        try:
            refs.add(_local_file(root, relative).relative_to(root.resolve()).as_posix())
        except (OSError, RuntimeError, ValueError) as error:
            failures.append("artifact guide: " + str(error))
    for missing in sorted(REQUIRED_ARTIFACTS - refs):
        failures.append("artifact guide missing source link: " + missing)
    failures.extend(_command_failures(text, root))
    return failures


def check_paper(paper_path: Path = PAPER, *, repository_root: Path = ROOT,
                artifact_guide_path: Path | None = None) -> list[str]:
    """Return binding and document-format mismatches; never rerun a proof."""
    try:
        text = _visible_source(paper_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as error:
        return ["cannot read paper: " + str(error)]
    failures = []
    declarations = MACRO_RE.findall(text)
    macros = dict(declarations)
    citations = GUIDE_CITATION_RE.findall(text)
    without_citation = GUIDE_CITATION_RE.sub("", text)
    body = MACRO_RE.sub("", without_citation)
    if len(citations) != 1 or macros.get("repourl") != REPOSITORY_URL:
        failures.append("paper must define its human-readable artifact-guide citation")
    if not re.search(r"\\artifactguide\b", body):
        failures.append("paper must cite the artifact and reproduction guide")
    for name in COUNT_MACROS:
        values = [value for key, value in declarations if key == name]
        if len(values) != 1 or not re.fullmatch(r"[0-9]+", values[0]):
            failures.append("paper must declare one integer macro: " + name)
        if not re.search(r"\\" + name + r"\b", body):
            failures.append("paper count macro is not used: " + name)
    if CODE_ENVIRONMENT_RE.search(text) or CODE_MECHANISM_RE.search(text) or re.search(r"\\path\s*\{", text) or "```" in without_citation:
        failures.append("manuscript must not contain code, command or path-printing blocks/macros")
    if IMPLEMENTATION_PATH_RE.search(without_citation):
        failures.append("manuscript must not print raw implementation paths")
    if MANUSCRIPT_COMMAND_RE.search(without_citation):
        failures.append("manuscript must not contain reproduction commands")
    try:
        counts = bound_counts(repository_root)
    except (OSError, RuntimeError, ValueError, KeyError, TypeError) as error:
        failures.append("formal evidence binding failed (proof not rerun): " + str(error))
    else:
        for name, expected in counts.items():
            value = macros.get(name, "")
            if re.fullmatch(r"[0-9]+", value) and int(value) != expected:
                failures.append(f"{name}={value}, current bound metadata={expected}")
    try:
        failures.extend(_guide_failures(artifact_guide_path or repository_root / GUIDE, repository_root))
    except (OSError, RuntimeError, ValueError, UnicodeError) as error:
        failures.append("cannot check artifact guide: " + str(error))
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository to compare")
    parser.add_argument("--paper", type=Path, help="TeX source (defaults to paper/plectis-public-system.tex)")
    parser.add_argument("--guide", type=Path, help="Artifact guide (defaults to paper/README.md)")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    failures = check_paper(args.paper or root / "paper/plectis-public-system.tex",
                           repository_root=root, artifact_guide_path=args.guide)
    if failures:
        print(f"Public-system paper check: {len(failures)} failure(s)", file=sys.stderr)
        for failure in failures:
            print("  FAIL " + failure, file=sys.stderr)
        return 1
    print("Public-system paper check: pass (bound counts and artifact guide; proof not rerun)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
