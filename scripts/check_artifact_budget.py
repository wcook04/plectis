#!/usr/bin/env python3
"""Measure and bound the shipped public distribution footprint.

Plectis ships a small runtime package (``src/microcosm_core``) *plus* a large
evidence and research corpus — fixtures, exported example bundles, receipts,
standards, doctrine — declared in ``[tool.setuptools.data-files]`` of
``pyproject.toml``. That corpus is the conformance library and reference
material; it is also, by byte count, most of the wheel.

This script resolves exactly what would be packaged, *without* needing a build
backend, by reading the same manifest setuptools reads. It reports the footprint
broken down by category and — in the default ``--check`` mode — fails when the
footprint exceeds an explicit, version-controlled budget.

The budget is a deliberate brake, not a measurement. The shipped corpus only
grows on purpose: adding weight past the ceiling is an edit *here*, reviewed
next to whatever added the weight, instead of an accident that rides a green CI.
Run ``--report`` to see the current footprint and headroom.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = REPO_ROOT / "pyproject.toml"
RUNTIME_PACKAGE = REPO_ROOT / "src" / "microcosm_core"

# --- Budget ----------------------------------------------------------------
# Explicit ceiling for the shipped public distribution. See module docstring:
# this is a conscious brake on corpus weld, sized with headroom above the
# current footprint so ordinary churn passes but a new bulk-corpus import has
# to come here and justify the increase.
#
# Measured 2026-06-26: 131,777,513 bytes (125.7 MiB) / 3,661 files; corpus
# 116,152,961 bytes. The footprint is dominated by the example bundles
# (~70 MiB) and atlas json (~10.5 MiB in 5 files) — those are the levers if the
# wheel needs to slim down. Ceilings sit a few MiB / ~190 files above current.
ARTIFACT_BUDGET = {
    "max_total_bytes": 134_217_728,  # 128 MiB
    "max_total_files": 3_850,
    "max_data_files_bytes": 120_000_000,  # ~114.4 MiB
}


def _load_data_files() -> dict[str, list[str]]:
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return payload["tool"]["setuptools"]["data-files"]


def _category(dest: str) -> str:
    """Top-level shipped category for a data-files destination directory."""
    prefix = "share/plectis"
    if dest == prefix:
        return "root_docs"
    rel = dest[len(prefix) + 1 :] if dest.startswith(prefix + "/") else dest
    return rel.split("/", 1)[0] or "root_docs"


def _resolve_data_files() -> tuple[dict[Path, int], dict[str, dict[str, int]]]:
    """Resolve every data-files glob to concrete files, with per-category rollup."""
    files: dict[Path, int] = {}
    by_category: dict[str, dict[str, int]] = {}
    for dest, patterns in _load_data_files().items():
        category = _category(dest)
        bucket = by_category.setdefault(category, {"files": 0, "bytes": 0})
        for pattern in patterns:
            for path in sorted(REPO_ROOT.glob(pattern)):
                if not path.is_file():
                    continue
                if path in files:
                    continue
                size = path.stat().st_size
                files[path] = size
                bucket["files"] += 1
                bucket["bytes"] += size
    return files, by_category


def _resolve_runtime_package() -> dict[Path, int]:
    files: dict[Path, int] = {}
    if not RUNTIME_PACKAGE.is_dir():
        return files
    for path in RUNTIME_PACKAGE.rglob("*"):
        if not path.is_file():
            continue
        if "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        files[path] = path.stat().st_size
    return files


def measure() -> dict[str, object]:
    data_files, by_category = _resolve_data_files()
    package_files = _resolve_runtime_package()

    data_bytes = sum(data_files.values())
    package_bytes = sum(package_files.values())
    by_category["runtime_package"] = {
        "files": len(package_files),
        "bytes": package_bytes,
    }

    total_files = len(data_files) + len(package_files)
    total_bytes = data_bytes + package_bytes

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "data_files_count": len(data_files),
        "data_files_bytes": data_bytes,
        "runtime_package_files": len(package_files),
        "runtime_package_bytes": package_bytes,
        "by_category": dict(
            sorted(by_category.items(), key=lambda kv: kv[1]["bytes"], reverse=True)
        ),
    }


def _mib(byte_count: int) -> str:
    return f"{byte_count / (1024 * 1024):.2f} MiB"


def _print_report(stats: dict[str, object]) -> None:
    print("Plectis shipped-artifact footprint")
    print(f"  total:           {stats['total_files']} files, {_mib(stats['total_bytes'])}")
    print(
        f"  runtime package: {stats['runtime_package_files']} files, "
        f"{_mib(stats['runtime_package_bytes'])}"
    )
    print(
        f"  data-files corpus:{stats['data_files_count']} files, "
        f"{_mib(stats['data_files_bytes'])}"
    )
    print("  by category (bytes desc):")
    for name, roll in stats["by_category"].items():
        print(f"    {name:<22} {roll['files']:>5} files  {_mib(roll['bytes'])}")
    budget = ARTIFACT_BUDGET
    if budget["max_total_bytes"]:
        head_bytes = budget["max_total_bytes"] - int(stats["total_bytes"])
        head_files = budget["max_total_files"] - int(stats["total_files"])
        print("  budget headroom:")
        print(f"    bytes: {_mib(head_bytes)} under ceiling {_mib(budget['max_total_bytes'])}")
        print(f"    files: {head_files} under ceiling {budget['max_total_files']}")


def _check(stats: dict[str, object]) -> list[str]:
    failures: list[str] = []
    budget = ARTIFACT_BUDGET
    if not budget["max_total_bytes"]:
        failures.append(
            "artifact budget is unset (max_total_bytes=0); run --report and set "
            "ARTIFACT_BUDGET in scripts/check_artifact_budget.py before enabling --check"
        )
        return failures
    checks = (
        ("total_bytes", "max_total_bytes", "total shipped bytes"),
        ("total_files", "max_total_files", "total shipped files"),
        ("data_files_bytes", "max_data_files_bytes", "data-files corpus bytes"),
    )
    for stat_key, budget_key, label in checks:
        observed = int(stats[stat_key])
        ceiling = int(budget[budget_key])
        if observed > ceiling:
            failures.append(
                f"{label} {observed} exceeds budget {ceiling} "
                f"(over by {observed - ceiling}); a corpus increase must update "
                "ARTIFACT_BUDGET deliberately"
            )
    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--report",
        action="store_true",
        help="print the footprint and budget headroom, never fail",
    )
    mode.add_argument(
        "--check",
        action="store_true",
        help="fail if the footprint exceeds ARTIFACT_BUDGET (default)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    stats = measure()

    if args.json:
        print(json.dumps(stats, indent=2, sort_keys=True))
        if args.report:
            return 0
        failures = _check(stats)
        return 1 if failures else 0

    if args.report:
        _print_report(stats)
        return 0

    failures = _check(stats)
    if failures:
        print("Plectis artifact budget: fail", file=sys.stderr)
        for failure in failures:
            print(f"  {failure}", file=sys.stderr)
        return 1
    print(
        f"Plectis artifact budget: pass "
        f"({stats['total_files']} files, {_mib(int(stats['total_bytes']))})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
