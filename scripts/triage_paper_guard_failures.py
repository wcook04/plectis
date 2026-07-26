#!/usr/bin/env python3
"""Classify paper-guard failures by whether the commitment is actually missing.

The guard reports a failure whenever an anchor string is absent. That count is
only a defect count if the paper really dropped that many commitments. It does
not, because the guard binds obligations to exact sentences: a rewrite that
preserves every commitment still fails hundreds of anchors.

This script separates the two. For each failing anchor it asks whether the
paper still carries the anchor's distinctive content words, and reports:

  verbatim  the text is there; the guard tripped on LaTeX or spacing alone
  reworded  every content word is present; the commitment survived a rewrite
  partial   most content words are present; needs a human read
  absent    the content words are largely gone; a candidate real loss

Only `absent` is evidence that the paper lost something. Run this before
treating the raw failure count as a backlog, and re-run it after any
restructuring pass.

Usage:  python3 scripts/triage_paper_guard_failures.py [--json OUT]
Exit:   0 always; this is a measurement, not a gate.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
GUARD = REPO_ROOT / "scripts/check_public_system_paper.py"
PAPER = REPO_ROOT / "paper/plectis-public-system.tex"

# Words too common to distinguish one commitment from another.
STOP = set(
    "a an the is are was were be been being of in on at to for from by with and or "
    "not no its it this that these those as into than then there their they them "
    "which who what when where how any all one two some each other more most only "
    "does do did has have had can could may might must shall should will would".split()
)

REWORDED_MIN = 1.0
PARTIAL_MIN = 0.6


def normalise(text: str) -> str:
    """Drop LaTeX markup and casing so only wording differences remain."""
    text = re.sub(r"\\[a-zA-Z]+\*?", " ", text)
    text = re.sub(r"[{}$\\~%^_&#]", " ", text)
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def content_words(text: str) -> list[str]:
    return [w for w in normalise(text).split() if w not in STOP and len(w) > 2]


def failing_anchors() -> list[tuple[str, str]]:
    result = subprocess.run(
        [sys.executable, str(GUARD)], cwd=REPO_ROOT, capture_output=True, text=True
    )
    report = (result.stdout or "") + (result.stderr or "")
    return re.findall(r"FAIL ([^:]*): '(.*)'\s*$", report, re.M)


def classify() -> dict[str, list[dict]]:
    paper_norm = normalise(PAPER.read_text(encoding="utf-8"))
    paper_vocab = set(paper_norm.split())
    buckets: dict[str, list[dict]] = {
        "verbatim": [], "reworded": [], "partial": [], "absent": []
    }

    for kind, raw in failing_anchors():
        anchor = raw.replace("\\\\", "\\")
        target = normalise(anchor)
        if not target:
            continue
        row = {"kind": kind.strip(), "anchor": anchor}
        if target in paper_norm:
            buckets["verbatim"].append({**row, "coverage": 1.0})
            continue
        words = content_words(anchor)
        if not words:
            buckets["absent"].append({**row, "coverage": 0.0})
            continue
        coverage = sum(1 for w in words if w in paper_vocab) / len(words)
        row["coverage"] = round(coverage, 2)
        if coverage >= REWORDED_MIN:
            buckets["reworded"].append(row)
        elif coverage >= PARTIAL_MIN:
            buckets["partial"].append(row)
        else:
            buckets["absent"].append(row)
    return buckets


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", type=Path, help="write the full classification here")
    args = parser.parse_args()

    buckets = classify()
    total = sum(len(v) for v in buckets.values())
    if not total:
        print("paper guard reports no failing anchors")
        return 0

    print(f"paper-guard failures: {total}\n")
    for name, label in [
        ("verbatim", "verbatim  (guard tripped on LaTeX/spacing only)"),
        ("reworded", "reworded  (every content word still present)"),
        ("partial", "partial   (most content words present; needs a read)"),
        ("absent", "absent    (candidate real loss)"),
    ]:
        rows = buckets[name]
        print(f"  {label:52} {len(rows):4}  {100 * len(rows) / total:3.0f}%")

    coupling = total - len(buckets["absent"])
    print(
        f"\n{coupling} of {total} failures ({100 * coupling / total:.0f}%) are the guard "
        f"holding a rendering, not the paper losing a commitment."
    )
    print(f"{len(buckets['absent'])} anchors are candidate real losses:\n")
    for row in sorted(buckets["absent"], key=lambda r: r["coverage"]):
        print(f"  [{row['coverage']:.2f}] {row['kind'][:34]:34} | {row['anchor'][:66]}")

    if args.json:
        args.json.write_text(json.dumps(buckets, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
