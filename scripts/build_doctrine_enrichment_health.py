#!/usr/bin/env python3
"""Project doctrine-enrichment coverage health.

Reads the hand-authored enrichment source of record
(``core/doctrine_enrichment.json``) against the axiom/principle/anti-principle
instance corpora and reports per-kind coverage: how many objects are enriched
and how many carry each reader field. Coverage is PRESENCE, not correctness;
the latex render check and voice/overclaim review live in the dissemination
build and tests, not here.

Usage:
  python3 scripts/build_doctrine_enrichment_health.py --write
  python3 scripts/build_doctrine_enrichment_health.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_doctrine_formal_soundness import run as run_soundness  # noqa: E402
from check_doctrine_reader_ladder import run as run_reader_ladder  # noqa: E402


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
ENRICHMENT_REL = "core/doctrine_enrichment.json"
HEALTH_REL = "core/doctrine_enrichment_health.json"
KIND_DIRS = {
    "axiom": ("axioms", "AX-*.json"),
    "principle": ("principles", "P-*.json"),
    "anti_principle": ("anti_principles", "AP-*.json"),
}
REQUIRED_FIELDS = ("deep", "formal", "governs", "requires", "refuses", "example", "counterexample", "enforced_in", "does_not_prove")


def _corpus_ids(root: Path, kind: str) -> list[str]:
    subdir, glob = KIND_DIRS[kind]
    ids: list[str] = []
    for path in sorted((root / subdir).glob(glob)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            ids.append(str(row["id"]))
    return ids


def _has_field(record: dict[str, Any], field: str) -> bool:
    value = record.get(field)
    if field == "formal":
        return isinstance(value, dict) and bool(str(value.get("latex") or "").strip())
    if field == "example":
        return isinstance(value, dict) and bool(str(value.get("text") or "").strip())
    if field == "counterexample":
        return isinstance(value, dict) and bool(str(value.get("text") or "").strip())
    if field == "enforced_in":
        return isinstance(value, list) and len(value) > 0
    return bool(str(value or "").strip())


def build_health(root: Path) -> dict[str, Any]:
    enrichment_path = root / ENRICHMENT_REL
    enrichment = json.loads(enrichment_path.read_text(encoding="utf-8"))
    by_id: dict[str, dict[str, Any]] = {}
    for record in enrichment.get("records") or []:
        if isinstance(record, dict) and record.get("id"):
            by_id[str(record["id"])] = record

    kinds: dict[str, Any] = {}
    all_missing: list[dict[str, Any]] = []
    for kind in KIND_DIRS:
        corpus_ids = _corpus_ids(root, kind)
        enriched = [oid for oid in corpus_ids if oid in by_id]
        field_counts = {field: 0 for field in REQUIRED_FIELDS}
        for oid in enriched:
            record = by_id[oid]
            for field in REQUIRED_FIELDS:
                if _has_field(record, field):
                    field_counts[field] += 1
        unenriched = [oid for oid in corpus_ids if oid not in by_id]
        partial: list[dict[str, Any]] = []
        for oid in enriched:
            missing = [f for f in REQUIRED_FIELDS if not _has_field(by_id[oid], f)]
            if missing:
                partial.append({"id": oid, "missing_fields": missing})
                all_missing.append({"id": oid, "missing_fields": missing})
        kinds[kind] = {
            "total": len(corpus_ids),
            "enriched": len(enriched),
            "unenriched_ids": unenriched,
            "field_present_counts": field_counts,
            "partial_records": partial,
        }
        all_missing.extend({"id": oid, "missing_fields": ["<no enrichment record>"]} for oid in unenriched)

    total = sum(k["total"] for k in kinds.values())
    enriched_total = sum(k["enriched"] for k in kinds.values())
    coverage_complete = all(
        kinds[kind]["enriched"] == kinds[kind]["total"]
        and not kinds[kind]["partial_records"]
        for kind in kinds
    )

    # Formal-statement soundness: every symbol in a formula is defined and every
    # declared symbol is used. This is a structural check the coverage counts
    # cannot see (a record can have a `formal` field that renders yet declare a
    # dangling symbol or use an undefined operator). Correctness of the maths is
    # still reviewed, not counted; this only enforces symbol/formula agreement.
    sound = run_soundness(enrichment_path)
    soundness = {
        "checked": sound["total"],
        "sound": sound["clean"],
        "unsound": sound["defective"],
        "defects": [
            {
                "id": r["id"],
                "dangling": r["dangling"],
                "undefined_vars": r["undefined_vars"],
                "undefined_ops": r["undefined_ops"],
            }
            for r in sound["results"]
            if not r["clean"]
        ],
        "gate": "scripts/check_doctrine_formal_soundness.py",
        "note": "Symbol/formula agreement, not mathematical correctness; correctness is reviewed, not counted.",
    }
    # Reader-ladder accessibility: every object carries a plain reading and a
    # bounded analogy (plain + analogy.text + maps + boundary + why_it_matters +
    # common_misread), with no laundering, banned visible term, or lay overclaim.
    # Like soundness, this is structural agreement, not a clarity score.
    ladder = run_reader_ladder(enrichment_path)
    reader_ladder = {
        "checked": ladder["total"],
        "sound": ladder["clean"],
        "unsound": ladder["defective"],
        "defects": [
            {"id": r["id"], "issues": r["issues"]}
            for r in ladder["results"]
            if not r["clean"]
        ],
        "gate": "scripts/check_doctrine_reader_ladder.py",
        "note": "Plain reading + bounded analogy present and laundering-free; analogy fidelity and boundary honesty are reviewed, not counted.",
    }
    complete = coverage_complete and soundness["unsound"] == 0 and reader_ladder["unsound"] == 0
    return {
        "schema_version": "microcosm_doctrine_enrichment_health_v1",
        "source_of_record": ENRICHMENT_REL,
        "standard_ref": "standards/std_microcosm_doctrine_enrichment.json",
        "authority_boundary": "Coverage projection over reader enrichment. Presence, not correctness, and never support evidence. Generated; do not hand-edit.",
        "status": "complete" if complete else "partial",
        "coverage_complete": coverage_complete,
        "total_objects": total,
        "enriched_objects": enriched_total,
        "kinds": kinds,
        "incomplete": all_missing,
        "formal_soundness": soundness,
        "reader_ladder": reader_ladder,
        "render_validation_note": "LaTeX render correctness is enforced by tools/meta/dissemination/tests/test_build_microcosm_public_site.py (zero raw-LaTeX fallbacks), not by this coverage projection.",
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry for the doctrine-enrichment coverage health projection.

    - Teleology: CLI front door that builds/writes/checks the enrichment coverage projection so agents and CI see doctrine reader-field completeness at a glance.
    - Guarantee: Prints the health JSON; with --write rewrites core/doctrine_enrichment_health.json; with --check returns 0 iff status is "complete" (full coverage, sound formulas, sound reader ladders).
    - Fails: missing/invalid core/doctrine_enrichment.json or corpus -> json.JSONDecodeError/FileNotFoundError -> uncaught traceback, nonzero exit.
    - Reads: core/doctrine_enrichment.json, axioms/principles/anti_principles corpora (via build_health, run_soundness, run_reader_ladder).
    - Writes: core/doctrine_enrichment_health.json (only with --write).
    - When-needed: deciding whether doctrine reader enrichment is complete before a dissemination build or as a CI gate.
    - Escalates-to: check_doctrine_formal_soundness.run, check_doctrine_reader_ladder.run for the structural sub-gates it folds in.
    """
    parser = argparse.ArgumentParser(prog="build_doctrine_enrichment_health")
    parser.add_argument("--root", type=Path, default=MICROCOSM_ROOT)
    parser.add_argument("--write", action="store_true", help="write the health projection")
    parser.add_argument("--check", action="store_true", help="fail if coverage is incomplete")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    health = build_health(root)
    if args.write:
        (root / HEALTH_REL).write_text(
            json.dumps(health, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    if not args.write or args.check:
        print(json.dumps(health, ensure_ascii=True, indent=2, sort_keys=True))
    if args.check:
        return 0 if health["status"] == "complete" else 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
