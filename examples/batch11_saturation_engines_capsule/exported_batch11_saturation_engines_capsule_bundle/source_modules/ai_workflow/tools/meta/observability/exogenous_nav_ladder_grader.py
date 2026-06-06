#!/usr/bin/env python3
"""Grade navigation-ladder answers against a filesystem-derived oracle.

The navigation plane cannot grade itself without recursion. This harness builds
the expected target set from direct filesystem evidence, then runs the public
navigation ladder under test and records the first surface that returns a
truthful path.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shlex
import subprocess
import sys
from typing import Any, Callable


REPO_ROOT = Path(__file__).resolve().parents[3]
SCHEMA_VERSION = "exogenous_nav_ladder_grade_v1"
TEXT_SUFFIXES = {
    ".md",
    ".py",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
    ".tsx",
    ".ts",
}
SKIP_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".mypy_cache",
    ".pytest_cache",
}


@dataclass(frozen=True)
class NavGradeCase:
    case_id: str
    query: str
    expected_paths: tuple[str, ...] = ()
    oracle_terms: tuple[str, ...] = ()
    source: str = "manual"
    max_hops: int = 3


DEFAULT_CASES: tuple[NavGradeCase, ...] = (
    NavGradeCase(
        case_id="session_prompt_obsidian_view",
        query="wire something to observe and screenshot my Obsidian view",
        expected_paths=(
            "system/lib/obsidian_observe.py",
            "tools/meta/observability/obsidian_observe.py",
        ),
        oracle_terms=("obsidian", "screenshot"),
        source="session-diagnostics:wake-prompts",
        max_hops=1,
    ),
    NavGradeCase(
        case_id="session_prompt_timing_flag",
        query="timing flag for navigation layer",
        expected_paths=(
            "codex/doctrine/paper_modules/agent_execution_trace.md",
            "codex/doctrine/skills/kernel/agent_session_diagnostics.md",
            "tools/meta/observability/session_analyzer.py",
        ),
        oracle_terms=("timing", "session", "diagnostics"),
        source="session-diagnostics:wake-prompts",
        max_hops=1,
    ),
    NavGradeCase(
        case_id="route_coverage_sidecar",
        query="paper module route coverage",
        expected_paths=(
            "codex/doctrine/paper_modules/_route_coverage.json",
            "codex/doctrine/skills/doctrine/paper_module_coverage.md",
        ),
        oracle_terms=("paper", "module", "route", "coverage"),
        source="paper-module-route-coverage",
        max_hops=1,
    ),
    NavGradeCase(
        case_id="wrapped_bash_eyesight",
        query="wrapped bash eyesight",
        expected_paths=("codex/doctrine/skills/kernel/navigation_seed.md",),
        oracle_terms=("wrapped", "bash", "eyesight"),
        source="required-surface:navigation_seed",
        max_hops=1,
    ),
    NavGradeCase(
        case_id="exact_path_docs_route",
        query="system/server/tests/test_docs_route.py",
        expected_paths=("system/server/tests/test_docs_route.py",),
        source="random-path-shape:exact-existing-file",
        max_hops=1,
    ),
)


CommandRunner = Callable[[str, list[str], float, Path], dict[str, Any]]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _repo_rel(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _is_probably_text(path: Path) -> bool:
    return path.suffix in TEXT_SUFFIXES


def _iter_candidate_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for path in root.rglob("*"):
        if any(part in SKIP_PARTS for part in path.parts):
            continue
        if not path.is_file() or not _is_probably_text(path):
            continue
        files.append(path)
    return files


def _read_limited_text(path: Path, max_bytes: int = 250_000) -> str:
    try:
        data = path.read_bytes()[:max_bytes]
    except OSError:
        return ""
    return data.decode("utf-8", errors="ignore")


def scan_filesystem_targets(
    root: Path,
    terms: tuple[str, ...],
    *,
    limit: int = 8,
) -> list[str]:
    """Return direct filesystem matches for terms without using nav outputs."""
    normalized = tuple(term.lower() for term in terms if term.strip())
    if not normalized:
        return []

    ranked: list[tuple[int, int, str]] = []
    for path in _iter_candidate_files(root):
        rel = _repo_rel(path, root)
        path_text = rel.lower()
        body = _read_limited_text(path).lower()
        score = 0
        for term in normalized:
            if term in path_text:
                score += 5
            if term in body:
                score += 1
        if score <= 0:
            continue
        ranked.append((-score, len(rel), rel))
    ranked.sort()
    return [rel for _, _, rel in ranked[:limit]]


def scan_expected_paths_for_terms(
    root: Path,
    expected_paths: list[str],
    terms: tuple[str, ...],
) -> list[str]:
    """Verify declared target paths cheaply before any repo-wide scan."""
    normalized = tuple(term.lower() for term in terms if term.strip())
    if not normalized:
        return []
    matches: list[str] = []
    for rel in expected_paths:
        path = root / rel
        body = _read_limited_text(path).lower()
        path_text = rel.lower()
        if any(term in path_text or term in body for term in normalized):
            matches.append(rel)
    return matches


def build_oracle(case: NavGradeCase, root: Path) -> dict[str, Any]:
    """Build the expected target set from filesystem facts only."""
    expected_existing: list[str] = []
    expected_missing: list[str] = []
    for rel in case.expected_paths:
        path = root / rel
        if path.exists():
            expected_existing.append(rel)
        else:
            expected_missing.append(rel)

    scanned: list[str] = []
    if case.oracle_terms:
        if expected_existing:
            scanned = scan_expected_paths_for_terms(root, expected_existing, case.oracle_terms)
        else:
            scanned = scan_filesystem_targets(root, case.oracle_terms)
    target_paths = list(dict.fromkeys([*expected_existing, *scanned]))

    return {
        "source": "direct_filesystem",
        "valid": bool(target_paths),
        "expected_paths_existing": expected_existing,
        "expected_paths_missing": expected_missing,
        "oracle_terms": list(case.oracle_terms),
        "scanned_paths": scanned,
        "target_paths": target_paths,
    }


def build_ladder_commands(case: NavGradeCase, root: Path, *, top_k: int) -> list[tuple[str, list[str]]]:
    repo_python = root / "repo-python"
    runner = str(repo_python if repo_python.exists() else Path(sys.executable))
    prefix = [runner]
    if not repo_python.exists():
        prefix.append(str(root / "kernel.py"))
    else:
        prefix.append("kernel.py")
    return [
        ("docs_route", [*prefix, "--docs-route", case.query]),
        ("paper_module", [*prefix, "--paper-module", case.query]),
        ("navigate", [*prefix, "--navigate", case.query, "--embed-top-k", str(top_k)]),
    ]


def run_command(surface: str, command: list[str], timeout_s: float, root: Path) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return {
            "surface": surface,
            "command": shlex.join(command),
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "timed_out": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "surface": surface,
            "command": shlex.join(command),
            "returncode": 124,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or f"timeout after {timeout_s}s",
            "timed_out": True,
        }


def _match_target_paths(output: str, root: Path, target_paths: list[str]) -> list[str]:
    matches: list[str] = []
    for rel in target_paths:
        absolute = str((root / rel).resolve())
        if rel in output or absolute in output:
            matches.append(rel)
    return matches


def _preview(text: str, limit: int = 1000) -> str:
    compact = " ".join(text.split())
    return compact[:limit]


def grade_case(
    case: NavGradeCase,
    root: Path,
    *,
    runner: CommandRunner = run_command,
    top_k: int = 8,
    timeout_s: float = 45.0,
    stop_after_first_truth: bool = True,
) -> dict[str, Any]:
    oracle = build_oracle(case, root)
    ladder_results: list[dict[str, Any]] = []
    first_truthful_surface: str | None = None
    first_truthful_hop: int | None = None
    first_matched_paths: list[str] = []

    for hop, (surface, command) in enumerate(build_ladder_commands(case, root, top_k=top_k), start=1):
        raw = runner(surface, command, timeout_s, root)
        combined = f"{raw.get('stdout') or ''}\n{raw.get('stderr') or ''}"
        matched_paths = _match_target_paths(combined, root, list(oracle["target_paths"]))
        result = {
            "surface": surface,
            "hop": hop,
            "command": raw.get("command") or shlex.join(command),
            "returncode": raw.get("returncode"),
            "timed_out": bool(raw.get("timed_out")),
            "matched_paths": matched_paths,
            "stdout_preview": _preview(str(raw.get("stdout") or "")),
            "stderr_preview": _preview(str(raw.get("stderr") or "")),
        }
        ladder_results.append(result)
        if matched_paths and first_truthful_surface is None:
            first_truthful_surface = surface
            first_truthful_hop = hop
            first_matched_paths = matched_paths
            if stop_after_first_truth:
                break
        if hop >= case.max_hops and first_truthful_surface is None and stop_after_first_truth:
            break

    docs_route = ladder_results[0] if ladder_results else {}
    passed = bool(oracle["valid"] and first_truthful_hop and first_truthful_hop <= case.max_hops)
    failure_reason = None
    if not oracle["valid"]:
        failure_reason = "oracle_has_no_filesystem_target"
    elif first_truthful_hop is None:
        failure_reason = "no_ladder_surface_returned_filesystem_target"
    elif first_truthful_hop > case.max_hops:
        failure_reason = f"first_truthful_hop_{first_truthful_hop}_exceeds_max_{case.max_hops}"

    return {
        "case_id": case.case_id,
        "query": case.query,
        "source": case.source,
        "max_hops": case.max_hops,
        "oracle": oracle,
        "ladder_results": ladder_results,
        "first_truthful_surface": first_truthful_surface,
        "first_truthful_hop": first_truthful_hop,
        "first_matched_paths": first_matched_paths,
        "docs_route_miss": not bool(docs_route.get("matched_paths")),
        "passed": passed,
        "failure_reason": failure_reason,
    }


def build_report(
    cases: list[NavGradeCase],
    root: Path,
    *,
    top_k: int,
    timeout_s: float,
    runner: CommandRunner = run_command,
    stop_after_first_truth: bool = True,
) -> dict[str, Any]:
    grades = [
        grade_case(
            case,
            root,
            runner=runner,
            top_k=top_k,
            timeout_s=timeout_s,
            stop_after_first_truth=stop_after_first_truth,
        )
        for case in cases
    ]
    truthful_hops = [
        grade["first_truthful_hop"]
        for grade in grades
        if isinstance(grade.get("first_truthful_hop"), int)
    ]
    by_surface: dict[str, int] = {}
    for grade in grades:
        surface = grade.get("first_truthful_surface") or "unresolved"
        by_surface[surface] = by_surface.get(surface, 0) + 1

    return {
        "kind": "exogenous_nav_ladder_grade",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _utc_now(),
        "contract": {
            "oracle": "direct filesystem existence/content scan only",
            "under_test": ["docs-route", "paper-module", "navigate"],
            "stop_after_first_truth": stop_after_first_truth,
            "recursion_guard": "Route ids, docs-route categories, and nav payload metadata are not used to choose expected targets.",
        },
        "summary": {
            "case_count": len(grades),
            "passed": sum(1 for grade in grades if grade["passed"]),
            "failed": sum(1 for grade in grades if not grade["passed"]),
            "docs_route_miss_count": sum(1 for grade in grades if grade["docs_route_miss"]),
            "oracle_invalid_count": sum(1 for grade in grades if not grade["oracle"]["valid"]),
            "average_first_truthful_hop": (
                round(sum(truthful_hops) / len(truthful_hops), 2) if truthful_hops else None
            ),
            "by_first_truthful_surface": by_surface,
        },
        "cases": grades,
    }


def _cases_from_args(args: argparse.Namespace) -> list[NavGradeCase]:
    if args.query:
        return [
            NavGradeCase(
                case_id=args.case_id,
                query=args.query,
                expected_paths=tuple(args.expect_path or ()),
                oracle_terms=tuple(args.oracle_term or ()),
                source="cli",
                max_hops=args.max_hops,
            )
        ]
    cases = list(DEFAULT_CASES)
    if args.limit is not None:
        cases = cases[: args.limit]
    return cases


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--limit", type=int, default=None, help="Run only the first N default cases.")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--timeout", type=float, default=45.0)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any case fails.")
    parser.add_argument(
        "--full-ladder",
        action="store_true",
        help="Run every ladder surface even after the first truthful path is found.",
    )
    parser.add_argument("--list-cases", action="store_true")
    parser.add_argument("--query", help="Run one ad hoc query instead of the default corpus.")
    parser.add_argument("--case-id", default="ad_hoc")
    parser.add_argument("--expect-path", action="append", default=[])
    parser.add_argument("--oracle-term", action="append", default=[])
    parser.add_argument("--max-hops", type=int, default=3)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(args.repo_root).resolve()
    cases = _cases_from_args(args)
    if args.list_cases:
        print(json.dumps([case.__dict__ for case in cases], indent=2))
        return 0
    report = build_report(
        cases,
        root,
        top_k=args.top_k,
        timeout_s=args.timeout,
        stop_after_first_truth=not args.full_ladder,
    )
    print(json.dumps(report, indent=2))
    if args.strict and report["summary"]["failed"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
