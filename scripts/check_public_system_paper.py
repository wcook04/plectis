#!/usr/bin/env python3
"""Check that the public-system paper stays coupled to its live evidence."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PAPER = ROOT / "paper/plectis-public-system.tex"
REGISTRY = ROOT / "core/organ_registry.json"
FAMILIES = ROOT / "core/organ_families.json"

MACRO_RE = re.compile(
    r"\\newcommand\{\\(?P<name>[A-Za-z]+)\}\{(?P<value>[^}]*)\}"
)

FAMILY_MACROS = {
    "entry_and_reveal": "entrycount",
    "architecture_and_navigation": "mappingcount",
    "formal_math_and_proof": "mathcount",
    "agent_reliability_and_safety": "safetycount",
    "research_and_science_replays": "researchcount",
    "import_projection_and_drift": "publiccopycount",
    "work_landing_and_continuity": "recoverycount",
}

TRUTH_BUCKET_MACROS = {
    "copied_non_secret_macro_body": "copiedsourcecount",
    "source_faithful_refactor": "refactorcount",
    "real_runtime_receipt": "runtimecount",
    "real_import_validation": "validatorcount",
}

FORBIDDEN_OVERCLAIMS = (
    "without trusting anyone",
    "verify it is non-secret",
    "verifies it is non-secret",
    "cannot silently drift",
    "no amount of inspection",
    "one deep artifact",
    "only form that counts",
    "earns attention exactly",
    "shows the system's breadth",
    "shows its depth",
    "python 3.11 or newer and nothing else",
    "guarantees privacy",
    "proves the private system",
    "certifies the private system",
)

# Sentences the paper's argument stands on.  The first block defines terms a
# cold reader needs; the second block carries the evidential distinctions
# (provenance, repeatability, selection, risk) that keep the paper's claims
# bounded.  Removing one is a claim-strength change, so it fails this check.
REQUIRED_COLD_READER_ANCHORS = (
    r"A \emph{repository} is",
    r"A \emph{component} in",
    r"Its \emph{fixture} is",
    r"its \emph{receipt} is",
    r"A \emph{validator} is",
    r"A \emph{commit} is",
    "basic command-line use",
    "The public repository lets a reader test claims",
    "cannot independently prove",
    "This note does not report an independent",
    "The artefact does not prove the story",
    "bounded refusal",
    r"their own \emph{oracle}",
    "share a mistake",
    "repeatability under that public test",
    "internal consistency, not",
    "The count is an inventory, not a score",
    "did not find the patterns it was designed to find",
    "who controls the consequential choices",
    "One successful run supports one bounded conclusion",
)

EXAMPLE_ORGAN_ID = "batch8_audio_level_rms_port"
EXAMPLE_RECEIPT = (
    "receipts/first_wave/batch8_audio_level_rms_port/"
    "batch8_audio_level_rms_port_validation_receipt.json"
)


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _macros(text: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in MACRO_RE.finditer(text)}


def _macro_int(macros: dict[str, str], name: str, failures: list[str]) -> int | None:
    value = macros.get(name)
    if value is None:
        failures.append(f"missing paper macro: {name}")
        return None
    try:
        return int(value)
    except ValueError:
        failures.append(f"paper macro {name} is not an integer: {value!r}")
        return None


def check_paper(
    paper_path: Path = PAPER,
    registry_path: Path = REGISTRY,
    families_path: Path = FAMILIES,
    *,
    check_git_commit: bool = True,
) -> list[str]:
    """Return every paper/evidence mismatch; an empty list is a pass."""
    text = paper_path.read_text(encoding="utf-8")
    normalized_text = re.sub(r"\s+", " ", text)
    lower = normalized_text.lower()
    registry = _load_json(registry_path)
    families = _load_json(families_path)
    macros = _macros(text)
    failures: list[str] = []

    organs = registry.get("implemented_organs", [])
    organ_ids = [str(row.get("organ_id") or "") for row in organs]
    if len(organ_ids) != len(set(organ_ids)):
        failures.append("organ registry contains duplicate organ ids")

    component_count = _macro_int(macros, "componentcount", failures)
    if component_count is not None and component_count != len(organs):
        failures.append(
            f"componentcount={component_count}, registry implemented_organs={len(organs)}"
        )

    family_rows = families.get("families", [])
    family_count = _macro_int(macros, "familycount", failures)
    if family_count is not None and family_count != len(family_rows):
        failures.append(f"familycount={family_count}, registry families={len(family_rows)}")

    families_by_id = {
        str(row.get("family_id") or ""): row for row in family_rows if isinstance(row, dict)
    }
    for family_id, macro_name in FAMILY_MACROS.items():
        row = families_by_id.get(family_id)
        if row is None:
            failures.append(f"missing family registry row: {family_id}")
            continue
        actual = len(row.get("organ_ids", []))
        declared = _macro_int(macros, macro_name, failures)
        if declared is not None and declared != actual:
            failures.append(f"{macro_name}={declared}, {family_id}={actual}")

    truth_counts: dict[str, int] = {}
    for row in organs:
        bucket = str(row.get("truth_accounting_bucket") or "")
        truth_counts[bucket] = truth_counts.get(bucket, 0) + 1
    for bucket, macro_name in TRUTH_BUCKET_MACROS.items():
        declared = _macro_int(macros, macro_name, failures)
        actual = truth_counts.get(bucket, 0)
        if declared is not None and declared != actual:
            failures.append(f"{macro_name}={declared}, {bucket}={actual}")
    undeclared_buckets = sorted(set(truth_counts) - set(TRUTH_BUCKET_MACROS))
    if undeclared_buckets:
        failures.append(f"paper does not account for truth buckets: {undeclared_buckets}")

    example = next((row for row in organs if row.get("organ_id") == EXAMPLE_ORGAN_ID), None)
    if EXAMPLE_ORGAN_ID not in text:
        failures.append(f"paper does not name its worked-example organ: {EXAMPLE_ORGAN_ID}")
    if Path(EXAMPLE_RECEIPT).name not in text:
        failures.append("paper does not name the worked-example validation receipt")
    if example is None:
        failures.append(f"worked-example organ is absent: {EXAMPLE_ORGAN_ID}")
    else:
        if EXAMPLE_RECEIPT not in example.get("generated_receipts", []):
            failures.append("worked-example receipt is not declared by the organ registry")
        command = str(example.get("validator_command") or "")
        if EXAMPLE_ORGAN_ID not in command or "--input" not in command or "--out" not in command:
            failures.append("worked-example validator command no longer has the documented shape")

    for phrase in FORBIDDEN_OVERCLAIMS:
        if phrase in lower:
            failures.append(f"forbidden overclaim remains in paper: {phrase!r}")
    for anchor in REQUIRED_COLD_READER_ANCHORS:
        if anchor not in normalized_text:
            failures.append(f"missing cold-reader anchor: {anchor!r}")

    snapshot = macros.get("snapshotcommit", "")
    if not re.fullmatch(r"[0-9a-f]{40}", snapshot):
        failures.append("snapshotcommit must be a full 40-character lowercase Git hash")
    elif check_git_commit and (ROOT / ".git").exists():
        result = subprocess.run(
            ["git", "cat-file", "-e", f"{snapshot}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            failures.append(f"snapshotcommit does not resolve in this repository: {snapshot}")
    if macros.get("snapshotshort") != snapshot[:12]:
        failures.append("snapshotshort must equal the first 12 characters of snapshotcommit")

    return failures


def main() -> int:
    failures = check_paper()
    if failures:
        print(
            f"Public-system paper check: {len(failures)} failure(s)",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  FAIL {failure}", file=sys.stderr)
        return 1

    print(
        "Public-system paper check: pass "
        f"({len(_load_json(REGISTRY)['implemented_organs'])} components; "
        "family counts, evidence routes, worked example, cold-reader anchors, "
        "and claim language agree)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
