"""Public-repository profile check: is the repo root a legible front door?

One shared contract, two profiles:

    python_research_tool              (Plectis itself, default)
    formalised_mathematics_artifact   (e.g. the plectis-lean-erdos249-257 repo)

The profile checks the *presentation* contract a stranger meets: a small
classified root, a human README with a runnable first screen, a bounded
AGENTS.md with an agent-first route and an immediate human redirect, resolving
links, conventional community files, and consistent citation/version
metadata. It deliberately does NOT re-run the deep
truth validators; those stay with their owners (`validators/readme_front_door.py`
and `validators/public_entry_docs.py` here, `scripts/check_release.py` in the
Lean repo), and `--deep` delegates to them by subprocess when asked.

Output is failure-first human text, or `--json`. Exit 1 only on unclassified
failures; classified exceptions (each pointing at its owning migration plan)
report as pending work without failing the gate.

Authority ceiling: root/README presentation legibility only. A pass is not a
release decision, quality score, correctness claim, or archive guarantee.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

PROFILE_VERSION = "1.1"
AGENT_ENTRY_MAX_BYTES = 32_768

# Files every profile expects at the root (missing -> failure).
SHARED_REQUIRED_FILES = ("README.md", "LICENSE", "CONTRIBUTING.md", "SECURITY.md", "CITATION.cff")

# Root entries the python_research_tool profile accepts without comment.
PYTHON_TOOL_ALLOWED = {
    ".git", ".github", ".gitignore", ".microcosm",
    "AGENTS.md", "AGENTS.override.md", "CLAUDE.md", "CHANGELOG.md", "CITATION.cff", "CONTRIBUTING.md",
    "LICENSE", "MANIFEST.in", "Makefile", "NOTICE", "QUICKSTART.md", "README.md",
    "SECURITY.md", "bootstrap.sh", "pyproject.toml",
    "assets", "atlas", "core", "docs", "examples", "fixtures", "paper",
    "paper_modules", "plectis-public-system.pdf",
    "receipts", "scripts", "skills", "src", "standards", "tests",
}

# Root entries that are KNOWN pending-migration surfaces, each classified to
# the plan that owns its move. Reported, not failed.
PYTHON_TOOL_CLASSIFIED_EXCEPTIONS = {
    name: "docs/maintainers/root-migration-plan.md"
    for name in (
        "AGENT_ROUTES.md", "ANTI_PRINCIPLES.md", "ARCHITECTURE.md", "AXIOMS.md",
        "CODEX.md", "CONSTITUTION.md", "CURSOR.md", "FIRST_ACTION.md",
        "ORGANS.md", "PRINCIPLES.md", "PROVENANCE.md", "RELEASE_DISCIPLINE.md",
        "RELEASE_REVIEW.md", "SOURCE_STATUS.md",
    )
}

MATH_ARTIFACT_ALLOWED = {
    ".git", ".github", ".gitignore",
    "AGENTS.md", "ARCHITECTURE.md", "CITATION.cff", "CLAUDE.md",
    "CONTRIBUTING.md", "LICENSE", "LICENSES", "METHODOLOGY.md", "README.md",
    "REUSE.toml", "SCOPE.md", "SECURITY.md",
    "claim-faithful-publication-systems-paper.pdf",
    "erdos249-257-main-paper.pdf", "erdos249-257-exposition.pdf",
    "docs", "examples", "experiments", "paper", "scripts",
    "lakefile.toml", "lake-manifest.json", "lean-toolchain",
    "erdos249-257-exposition.pdf",
}
MATH_ARTIFACT_CLASSIFIED_EXCEPTIONS: dict[str, str] = {}

# Old-name leakage scan for the hero region (python_research_tool only): the
# former product name may appear as a current label only in compatibility
# contexts.
LEGACY_NAME_ALLOWED_CONTEXTS = (
    "Microcosm became Plectis", "compatibility", "historical", "legacy",
    ".microcosm", "microcosm_core", "`microcosm ", "`microcosm`",
)


def _hero(text: str) -> str:
    marker = "\n## "
    return text.split(marker, 1)[0] if marker in text else text


def _fenced_blocks(text: str) -> list[str]:
    return re.findall(r"```[^\n]*\n(.*?)```", text, flags=re.DOTALL)


def _markdown_links(text: str) -> list[tuple[str, str]]:
    return [
        (m.group(1), m.group(2))
        for m in re.finditer(r"(?<!\!)\[([^\]]+)\]\(([^)]+)\)", text)
    ]


def _toml_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    m = re.search(r'^version\s*=\s*"([^"]+)"', path.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else None


def _cff_version(path: Path) -> str | None:
    if not path.is_file():
        return None
    m = re.search(r'^version:\s*"?([^"\n]+)"?\s*$', path.read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1).strip() if m else None


def _root_entries(root: Path) -> list[str]:
    """Top-level entries of the COMMITTED tree when this is a git checkout.

    The stranger meets the committed tree on GitHub; local build state
    (.lake/, venvs, editor dirs) is invisible there and must not fail the
    profile. Fall back to the filesystem for non-git roots.
    """
    if (root / ".git").exists():
        # The index view (`git ls-files`) IS the tree the next commit
        # publishes: staged adds, renames, and deletions are all reflected.
        proc = subprocess.run(
            ["git", "ls-files"],
            cwd=root, capture_output=True, text=True,
        )
        if proc.returncode == 0:
            return sorted(
                {line.split("/", 1)[0] for line in proc.stdout.splitlines() if line}
            )
    return sorted(p.name for p in root.iterdir())


def _check_root_allowlist(root: Path, mode: str, report: dict[str, Any]) -> None:
    allowed = PYTHON_TOOL_ALLOWED if mode == "python_research_tool" else MATH_ARTIFACT_ALLOWED
    exceptions = (
        PYTHON_TOOL_CLASSIFIED_EXCEPTIONS
        if mode == "python_research_tool"
        else MATH_ARTIFACT_CLASSIFIED_EXCEPTIONS
    )
    unclassified: list[str] = []
    pending: dict[str, str] = {}
    for entry in _root_entries(root):
        if entry in allowed:
            continue
        if entry in exceptions:
            pending[entry] = exceptions[entry]
            continue
        # Root Lean library files are the artifact itself in math mode.
        if mode == "formalised_mathematics_artifact" and (
            entry.endswith(".lean") or (root / entry / "Basic.lean").exists()
            or (root / entry).is_dir() and any((root / entry).glob("*.lean"))
        ):
            continue
        unclassified.append(entry)
    report["root_allowlist"] = {
        "unclassified_entries": unclassified,
        "classified_pending_migration": pending,
    }
    if unclassified:
        report["failures"].append(
            f"root_allowlist: unclassified root entries {unclassified}"
        )


def _check_required_files(root: Path, mode: str, report: dict[str, Any]) -> None:
    required = list(SHARED_REQUIRED_FILES)
    if mode == "python_research_tool":
        required += ["CHANGELOG.md", "pyproject.toml"]
    else:
        required += ["lakefile.toml", "lean-toolchain"]
    missing = [name for name in required if not (root / name).exists()]
    issue_forms = root / ".github/ISSUE_TEMPLATE"
    report["required_files"] = {"missing": missing, "issue_forms_present": issue_forms.is_dir()}
    if missing:
        report["failures"].append(f"required_files: missing {missing}")
    if not issue_forms.is_dir():
        report["failures"].append("required_files: no .github/ISSUE_TEMPLATE directory")


def _check_readme_first_screen(root: Path, mode: str, report: dict[str, Any]) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    hero = _hero(text)
    h1 = re.search(r"^#\s+(.+)$", hero, re.MULTILINE)
    install_markers = ("pip install", "lake build", "lake exe", "git clone")
    # A tool README shows the install in the hero; a scholarly artifact README
    # leads with results and may keep the build block in its own early
    # section, so the math profile scans the whole document for it.
    scan_region = hero if mode == "python_research_tool" else text
    blocks = _fenced_blocks(scan_region)
    has_install = any(any(m in b for m in install_markers) for b in blocks)
    links = _markdown_links(hero)
    row = {
        "h1": h1.group(1).strip() if h1 else None,
        "hero_install_block": has_install,
        "hero_link_count": len(links),
    }
    report["readme_first_screen"] = row
    if not h1:
        report["failures"].append("readme_first_screen: no H1 title")
    if not has_install:
        region = "hero" if mode == "python_research_tool" else "README"
        report["failures"].append(
            f"readme_first_screen: {region} has no install/build command block"
        )
    if len(links) < 2:
        report["failures"].append("readme_first_screen: hero routes fewer than 2 links")

    # No unrelated-repository promotion above the fold: hero links must stay
    # on this project's own surfaces. Compare exact owner/repo slugs, not
    # substrings (plectis-lean-... must not pass as plectis).
    own_slug = (
        "wcook04/plectis"
        if mode == "python_research_tool"
        else "wcook04/plectis-lean-erdos249-257"
    )
    related_slugs = {
        own_slug,
        (
            "wcook04/plectis-lean-erdos249-257"
            if mode == "python_research_tool"
            else "wcook04/plectis"
        ),
    }
    foreign = []
    for _label, dest in links:
        slug = re.search(r"github\.com/([\w.-]+/[\w.-]+)", dest)
        if slug and slug.group(1).removesuffix(".git") not in related_slugs:
            foreign.append(dest)
    row["foreign_repo_links_in_hero"] = foreign
    if foreign:
        report["failures"].append(
            f"readme_first_screen: unrelated repository promoted above the fold {foreign}"
        )

    if mode == "python_research_tool":
        leaks = []
        for line in hero.splitlines():
            if any(ctx in line for ctx in LEGACY_NAME_ALLOWED_CONTEXTS):
                continue
            if re.search(r"(?<![./\w`])Microcosm(?![_\w])", line):
                leaks.append(line.strip())
        row["legacy_name_leaks"] = leaks
        if leaks:
            report["failures"].append(
                f"readme_first_screen: former product name in hero: {leaks[:2]}"
            )


def _check_readme_links(root: Path, report: dict[str, Any]) -> None:
    readme = root / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    broken = []
    for _label, dest in _markdown_links(text):
        if dest.startswith(("http://", "https://", "mailto:", "#")):
            continue
        file_part = dest.partition("#")[0]
        if file_part and not (root / file_part).exists():
            broken.append(dest)
    report["readme_links"] = {"broken": broken}
    if broken:
        report["failures"].append(f"readme_links: broken relative links {broken}")


def _check_front_door_split(root: Path, mode: str, report: dict[str, Any]) -> None:
    readme = root / "README.md"
    agents = root / "AGENTS.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.is_file() else ""
    agents_text = agents.read_text(encoding="utf-8") if agents.is_file() else ""
    agents_head = agents_text[:4096]
    human_redirect = "README.md" in agents_text[:1024]
    task_route_markers = (
        ("comprehend --first-action", "agent-entry-composition")
        if mode == "python_research_tool"
        else ("docs/orientation.json", "scripts/query_corpus.py")
    )
    task_route_present = any(marker in agents_head for marker in task_route_markers)
    readme_h1 = re.search(r"^#\s+(.+)$", readme_text, re.MULTILINE)
    agents_h1 = re.search(r"^#\s+(.+)$", agents_text, re.MULTILINE)
    agents_size = len(agents_text.encode("utf-8"))
    row = {
        "standard_ref": "standards/std_public_repository_front_door.json",
        "readme_reader": "human",
        "agents_reader": "repository-aware coding agent",
        "readme_h1": readme_h1.group(1).strip() if readme_h1 else None,
        "agents_h1": agents_h1.group(1).strip() if agents_h1 else None,
        "agents_human_redirect_in_first_1024_bytes": human_redirect,
        "agents_task_route_in_first_4096_bytes": task_route_present,
        "agents_bytes": agents_size,
        "agents_max_bytes": AGENT_ENTRY_MAX_BYTES,
    }
    report["front_door_split"] = row
    if not agents.is_file():
        report["failures"].append("front_door_split: AGENTS.md missing")
    if not human_redirect:
        report["failures"].append(
            "front_door_split: AGENTS.md does not route people to README.md "
            "within its first 1024 bytes"
        )
    if not task_route_present:
        report["failures"].append(
            "front_door_split: AGENTS.md has no profile-appropriate task route "
            "within its first 4096 bytes"
        )
    if agents_size > AGENT_ENTRY_MAX_BYTES:
        report["failures"].append(
            f"front_door_split: AGENTS.md is {agents_size} bytes; "
            f"maximum is {AGENT_ENTRY_MAX_BYTES}"
        )
    if readme_h1 and "agent" in readme_h1.group(1).lower():
        report["failures"].append(
            "front_door_split: README title presents an agent contract instead "
            "of the project"
        )


def _check_version_consistency(root: Path, mode: str, report: dict[str, Any]) -> None:
    cff = _cff_version(root / "CITATION.cff")
    build = _toml_version(
        root / ("pyproject.toml" if mode == "python_research_tool" else "lakefile.toml")
    )
    report["version_consistency"] = {"citation_cff": cff, "build_metadata": build}
    if cff and build and cff != build:
        report["failures"].append(
            f"version_consistency: CITATION.cff {cff!r} != build metadata {build!r}"
        )


def _deep_delegate(root: Path, mode: str, report: dict[str, Any]) -> None:
    """Run the owning deep validator by subprocess (opt-in via --deep)."""
    if mode == "python_research_tool":
        cmd = [
            sys.executable, "-m",
            "microcosm_core.validators.readme_front_door", "--root", str(root),
        ]
        env_note = "PYTHONPATH must include src/"
    else:
        checker = root / "scripts/check_release.py"
        if not checker.is_file():
            report["failures"].append("deep: scripts/check_release.py missing")
            return
        cmd = [sys.executable, str(checker)]
        env_note = None
    proc = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
    report["deep"] = {
        "command": " ".join(cmd),
        "returncode": proc.returncode,
        "note": env_note,
        "tail": (proc.stdout + proc.stderr).strip().splitlines()[-5:],
    }
    if proc.returncode != 0:
        report["failures"].append(f"deep: owning validator failed ({proc.returncode})")


def run_profile(root: Path, mode: str, deep: bool = False) -> dict[str, Any]:
    report: dict[str, Any] = {
        "profile_version": PROFILE_VERSION,
        "mode": mode,
        "root": str(root),
        "failures": [],
        "authority_ceiling": {
            "presentation_legibility_only": True,
            "release_authorized": False,
            "correctness_claim": False,
        },
    }
    _check_root_allowlist(root, mode, report)
    _check_required_files(root, mode, report)
    _check_readme_first_screen(root, mode, report)
    _check_readme_links(root, report)
    _check_front_door_split(root, mode, report)
    _check_version_consistency(root, mode, report)
    if deep:
        _deep_delegate(root, mode, report)
    report["status"] = "pass" if not report["failures"] else "fail"
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=".", help="repository root to check")
    parser.add_argument(
        "--mode",
        choices=["python_research_tool", "formalised_mathematics_artifact"],
        default="python_research_tool",
    )
    parser.add_argument("--deep", action="store_true", help="also run the owning deep validator")
    parser.add_argument("--json", action="store_true", help="emit the JSON report")
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    report = run_profile(root, args.mode, deep=args.deep)
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"public repo profile ({args.mode}): {report['status']}")
        for failure in report["failures"]:
            print(f"  FAIL {failure}")
        pending = report["root_allowlist"]["classified_pending_migration"]
        if pending:
            plans = sorted(set(pending.values()))
            print(
                f"  pending migration: {len(pending)} root entries classified to "
                f"{', '.join(plans)}"
            )
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
