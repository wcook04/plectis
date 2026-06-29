#!/usr/bin/env python3
"""Check Station cockpit surfaces for raw geometry literals.

Station geometry is governed by std_station_aesthetic and the token layer in
system/server/ui/src/index.css. This checker keeps stable tracked cockpit files
from reintroducing raw Tailwind geometry literals where a Station token exists.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[3]
SOURCE_ROOTS = (
    "system/server/ui/src/components/world",
    "system/server/ui/src/components/station",
    "system/server/ui/src/pages",
)
STABLE_SUFFIX = ".tsx"
ALLOWLIST_PATHS = {
    # Active trace workbench is currently dirty in the shared tree and contains
    # large same-file in-flight work. Remove this exception when that work lands.
    "system/server/ui/src/components/world/AgentObservabilityLens.tsx",
}
ALLOW_COMMENT = "station-geometry-allow"

RADIUS_RE = re.compile(r"rounded-\[(?P<value>(?:6|8|10|12|14|16|18)px)\]")
SPACING_RE = re.compile(r"\b(?P<value>(?:gap|px|py)-2\.5)\b")
MIN_H_RE = re.compile(r"min-h-\[(?P<value>1(?:\.\d+)?rem)\]")

RADIUS_HINTS = {
    "6px": "rounded-[var(--zenith-radius-2xs)]",
    "8px": "rounded-[var(--zenith-radius-xs)]",
    "10px": "rounded-[var(--zenith-radius-sm)]",
    "12px": "rounded-[var(--zenith-radius-md)]",
    "14px": "rounded-[var(--zenith-radius-lg)]",
    "16px": "rounded-[var(--zenith-radius-region)]",
    "18px": "rounded-[var(--zenith-radius-panel)]",
}
SPACING_HINTS = {
    "gap-2.5": "gap-[var(--zenith-space-2-5)]",
    "px-2.5": "px-[var(--zenith-space-2-5)]",
    "py-2.5": "py-[var(--zenith-space-2-5)]",
}


@dataclass(frozen=True)
class GeometryViolation:
    path: str
    line: int
    kind: str
    token: str
    replacement_hint: str
    text: str


def _git_ls_files(repo_root: Path) -> set[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", *SOURCE_ROOTS],
            cwd=repo_root,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except (OSError, subprocess.CalledProcessError):
        return set()
    return {
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().endswith(STABLE_SUFFIX)
    }


def iter_station_files(repo_root: Path) -> Iterable[Path]:
    tracked = _git_ls_files(repo_root)
    if tracked:
        for rel_path in sorted(tracked):
            if rel_path in ALLOWLIST_PATHS:
                continue
            yield repo_root / rel_path
        return
    for root in SOURCE_ROOTS:
        for path in sorted((repo_root / root).glob(f"*{STABLE_SUFFIX}")):
            rel_path = path.relative_to(repo_root).as_posix()
            if rel_path not in ALLOWLIST_PATHS:
                yield path


def scan_text(text: str, *, rel_path: str) -> list[GeometryViolation]:
    violations: list[GeometryViolation] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if ALLOW_COMMENT in line or line.strip().startswith("//"):
            continue
        for match in RADIUS_RE.finditer(line):
            value = match.group("value")
            violations.append(
                GeometryViolation(
                    path=rel_path,
                    line=line_no,
                    kind="raw_radius",
                    token=match.group(0),
                    replacement_hint=RADIUS_HINTS[value],
                    text=line.strip(),
                )
            )
        for match in SPACING_RE.finditer(line):
            value = match.group("value")
            violations.append(
                GeometryViolation(
                    path=rel_path,
                    line=line_no,
                    kind="raw_dense_spacing",
                    token=value,
                    replacement_hint=SPACING_HINTS[value],
                    text=line.strip(),
                )
            )
        for match in MIN_H_RE.finditer(line):
            violations.append(
                GeometryViolation(
                    path=rel_path,
                    line=line_no,
                    kind="raw_dense_min_height",
                    token=match.group(0),
                    replacement_hint="use a Station token, shared primitive, or add a narrow station-geometry-allow comment",
                    text=line.strip(),
                )
            )
    return violations


def scan_repo(repo_root: Path) -> dict[str, object]:
    violations: list[GeometryViolation] = []
    scanned_files: list[str] = []
    for path in iter_station_files(repo_root):
        rel_path = path.relative_to(repo_root).as_posix()
        scanned_files.append(rel_path)
        violations.extend(scan_text(path.read_text(encoding="utf-8"), rel_path=rel_path))
    return {
        "schema": "station_geometry_check_v1",
        "ok": not violations,
        "scanned_file_count": len(scanned_files),
        "violation_count": len(violations),
        "allowlisted_paths": sorted(ALLOWLIST_PATHS),
        "source_roots": list(SOURCE_ROOTS),
        "violations": [asdict(violation) for violation in violations],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--check", action="store_true", help="Compatibility flag; this command is always a check.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(argv)

    payload = scan_repo(Path(args.repo_root).resolve())
    if args.json or not payload["ok"]:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print("station geometry clean")
    return 0 if payload["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
