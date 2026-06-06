#!/usr/bin/env python3
"""Generate Microcosm doctrine-lattice instance projections.

Thin CLI wrapper over ``microcosm_core.doctrine_lattice``. The axiom,
principle, and anti-principle corpora are parity-seeded from current source
registries/entry routes/legacy markdown until receipts justify flipping source authority.
Generated markdown, mermaid, health, and atlas JSON remain projections below
the governed JSON/source registry.

Usage:
  PYTHONPATH=src python3 scripts/build_doctrine_projection.py --write
  PYTHONPATH=src python3 scripts/build_doctrine_projection.py --check
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = MICROCOSM_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from microcosm_core.doctrine_lattice import (  # noqa: E402
    ENTRY_CARD_REL,
    DOCTRINE_GRAPH_REL,
    DOCTRINE_HEALTH_REL,
    DOCTRINE_PROJECTION_REL,
    build_doctrine_projection,
    build_standard_instance_corpus,
    validate_concept_instance_corpus,
    validate_coverage_projection,
    validate_anti_principle_instance_corpus,
    validate_axiom_instance_corpus,
    validate_doctrine_projection,
    validate_entry_card,
    validate_mechanism_instance_corpus,
    validate_organ_instance_corpus,
    validate_paper_module_instance_corpus,
    validate_principle_instance_corpus,
    validate_skill_instance_corpus,
    validate_standard_instance_corpus,
    write_anti_principle_instance_corpus,
    write_axiom_instance_corpus,
    write_concept_instance_corpus,
    write_coverage_projection,
    write_doctrine_projection,
    write_entry_card,
    write_mechanism_instance_corpus,
    write_organ_instance_corpus,
    write_organ_instance,
    write_paper_module_instance_corpus,
    write_principle_instance_corpus,
    write_principle_instance,
    write_skill_instance_corpus,
)


COVERAGE_REL = "core/doctrine_lattice_coverage.json"
STATUS_SURFACE_RELS = (
    DOCTRINE_PROJECTION_REL,
    DOCTRINE_GRAPH_REL,
    DOCTRINE_HEALTH_REL,
    COVERAGE_REL,
    ENTRY_CARD_REL,
)


def _surface_status(root: Path, rel: str) -> dict[str, Any]:
    path = root / rel
    row: dict[str, Any] = {
        "path": rel,
        "exists": path.exists(),
    }
    if not path.exists():
        row["status"] = "missing"
        return row
    stat = path.stat()
    row.update(
        {
            "status": "available",
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
        }
    )
    if path.suffix != ".json":
        row["line_count"] = len(path.read_text(encoding="utf-8").splitlines())
        return row
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        row.update({"status": "invalid_json", "error": str(exc)})
        return row
    if isinstance(payload, dict):
        counts: dict[str, Any] = {}
        for key in ("nodes", "edges", "current_counts", "per_kind_coverage"):
            value = payload.get(key)
            if isinstance(value, (dict, list)):
                counts[key] = len(value)
        for key in (
            "organ_count",
            "accepted_current_authority_organ_count",
            "known_count",
            "edge_count",
            "missing_ref_count",
        ):
            value = payload.get(key)
            if isinstance(value, int):
                counts[key] = value
        row.update(
            {
                "schema_version": payload.get("schema_version"),
                "projection_status": payload.get("status") or payload.get("contract_status"),
                "projection_id": payload.get("projection_id") or payload.get("card_id") or payload.get("surface_id"),
                "counts": counts,
            }
        )
    return row


def build_status_card(root: Path) -> dict[str, Any]:
    rows = [_surface_status(root, rel) for rel in STATUS_SURFACE_RELS]
    missing_or_invalid = [
        row["path"]
        for row in rows
        if row.get("status") not in {"available"}
    ]
    return {
        "schema_version": "microcosm_doctrine_projection_status_card_v1",
        "status": "available" if not missing_or_invalid else "blocked",
        "read_only": True,
        "owner_surface": "./repo-python microcosm-substrate/scripts/build_doctrine_projection.py --status-only",
        "replacement_for": [
            "python -c JSON probes over core/doctrine_lattice_coverage.json",
            "full build_doctrine_projection.py --check when only projection availability/counts are needed",
        ],
        "full_validation_command": "./repo-python microcosm-substrate/scripts/build_doctrine_projection.py --check",
        "surface_count": len(rows),
        "missing_or_invalid": missing_or_invalid,
        "surfaces": rows,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_doctrine_projection",
        description="Generate doctrine-lattice JSON, markdown, graph, health, and atlas projections.",
    )
    parser.add_argument("--root", type=Path, default=MICROCOSM_ROOT)
    parser.add_argument(
        "--write",
        action="store_true",
        help="write axiom JSON/markdown plus doctrine projection surfaces",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail if axiom corpus or generated projection surfaces are stale",
    )
    parser.add_argument(
        "--status-only",
        action="store_true",
        help="read existing projection surfaces and emit a compact status card without building",
    )
    parser.add_argument(
        "--card",
        action="store_true",
        help="alias for --status-only",
    )
    parser.add_argument(
        "--write-axiom-corpus",
        action="store_true",
        help="write only axiom JSON/markdown instances from routing source",
    )
    parser.add_argument(
        "--check-axiom-corpus",
        action="store_true",
        help="check only axiom JSON instance parity",
    )
    parser.add_argument(
        "--write-principle-corpus",
        action="store_true",
        help="write only principle JSON/markdown instances from PRINCIPLES.md",
    )
    parser.add_argument(
        "--write-principle-instance",
        metavar="PRINCIPLE_ID",
        help="write one principle JSON/markdown instance from PRINCIPLES.md",
    )
    parser.add_argument(
        "--check-principle-corpus",
        action="store_true",
        help="check only principle JSON instance parity",
    )
    parser.add_argument(
        "--write-anti-principle-corpus",
        action="store_true",
        help="write only anti-principle JSON/markdown instances from ANTI_PRINCIPLES.md",
    )
    parser.add_argument(
        "--check-anti-principle-corpus",
        action="store_true",
        help="check only anti-principle JSON instance parity",
    )
    parser.add_argument(
        "--write-concept-corpus",
        action="store_true",
        help="write only concept JSON/markdown instances from entry-packet specimens",
    )
    parser.add_argument(
        "--check-concept-corpus",
        action="store_true",
        help="check only concept JSON instance parity",
    )
    parser.add_argument(
        "--write-mechanism-corpus",
        action="store_true",
        help="write only mechanism JSON/markdown instances from mechanism registry",
    )
    parser.add_argument(
        "--check-mechanism-corpus",
        action="store_true",
        help="check only mechanism JSON instance parity",
    )
    parser.add_argument(
        "--write-organ-corpus",
        action="store_true",
        help="write only organ JSON/markdown instances from organ atlas and accepted registry rows",
    )
    parser.add_argument(
        "--write-organ-instance",
        metavar="ORGAN_ID",
        help="write one organ JSON/markdown instance from organ atlas and accepted registry rows",
    )
    parser.add_argument(
        "--check-organ-corpus",
        action="store_true",
        help="check only organ JSON instance parity",
    )
    parser.add_argument(
        "--write-paper-module-corpus",
        action="store_true",
        help="write only paper-module JSON instances from capsule registry and legacy Markdown inventory",
    )
    parser.add_argument(
        "--check-paper-module-corpus",
        action="store_true",
        help="check only paper-module JSON instance parity",
    )
    parser.add_argument(
        "--write-skill-corpus",
        action="store_true",
        help="write only skill JSON instances from skill markdown projections",
    )
    parser.add_argument(
        "--check-skill-corpus",
        action="store_true",
        help="check only skill JSON instance parity",
    )
    parser.add_argument(
        "--check-standard-corpus",
        action="store_true",
        help="check only registry-backed standard JSON instance projection parity",
    )
    parser.add_argument(
        "--write-aggregate-surfaces",
        action="store_true",
        help="write only doctrine projection, graph, health, coverage, and entry-card surfaces",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    if args.status_only or args.card:
        result = build_status_card(root)
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))
        return 0 if result["status"] == "available" else 1
    if args.check_axiom_corpus:
        result = validate_axiom_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_axiom_corpus:
        result = write_axiom_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_principle_corpus:
        result = validate_principle_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_principle_corpus:
        result = write_principle_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.write_principle_instance:
        payload = write_principle_instance(args.write_principle_instance, root)
        validation = validate_principle_instance_corpus(root)
        result = {
            "schema_version": "microcosm_principle_instance_target_write_v1",
            "status": validation["status"],
            "principle_id": payload["id"],
            "written": [
                f"principles/{payload['id']}.json",
                f"principles/{payload['id']}.md",
            ],
            "principle_corpus": validation,
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.check_anti_principle_corpus:
        result = validate_anti_principle_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_anti_principle_corpus:
        result = write_anti_principle_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_concept_corpus:
        result = validate_concept_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_concept_corpus:
        result = write_concept_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_mechanism_corpus:
        result = validate_mechanism_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_mechanism_corpus:
        result = write_mechanism_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_organ_corpus:
        result = validate_organ_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_organ_corpus:
        result = write_organ_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.write_organ_instance:
        payload = write_organ_instance(args.write_organ_instance, root)
        validation = validate_organ_instance_corpus(root)
        result = {
            "schema_version": "microcosm_organ_instance_target_write_v1",
            "status": validation["status"],
            "organ_id": payload["id"],
            "written": [
                f"organs/{payload['id']}.json",
                f"organs/{payload['id']}.md",
            ],
            "organ_corpus": validation,
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.check_paper_module_corpus:
        result = validate_paper_module_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_paper_module_corpus:
        result = write_paper_module_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_skill_corpus:
        result = validate_skill_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_skill_corpus:
        result = write_skill_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["parity_status"] == "pass" else 1
    if args.check_standard_corpus:
        result = validate_standard_instance_corpus(root)
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.check:
        doctrine_result = validate_doctrine_projection(root)
        coverage_path = root / COVERAGE_REL
        entry_card_path = root / ENTRY_CARD_REL
        coverage_result = validate_coverage_projection(
            json.loads(coverage_path.read_text(encoding="utf-8")),
            root,
        )
        entry_card_result = validate_entry_card(
            json.loads(entry_card_path.read_text(encoding="utf-8")),
            root,
        )
        result = {
            "schema_version": "microcosm_doctrine_projection_builder_check_v1",
            "status": "pass"
            if all(
                row["status"] == "pass"
                for row in (doctrine_result, coverage_result, entry_card_result)
            )
            else "blocked",
            "doctrine_projection": doctrine_result,
            "coverage_projection": coverage_result,
            "entry_card": entry_card_result,
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write_aggregate_surfaces:
        command = "python scripts/build_doctrine_projection.py --write-aggregate-surfaces"
        projection = write_doctrine_projection(root, command=command)
        coverage = write_coverage_projection(
            root,
            root / COVERAGE_REL,
            command=command,
        )
        entry_card = write_entry_card(
            root,
            root / ENTRY_CARD_REL,
            command=command,
        )
        result = {
            "schema_version": "microcosm_doctrine_lattice_aggregate_surface_write_v1",
            "status": "pass"
            if projection["status"] == coverage["status"] == entry_card["status"] == "pass"
            else "blocked",
            "projection_status": projection["status"],
            "coverage_status": coverage["status"],
            "entry_card_status": entry_card["status"],
            "written": [
                DOCTRINE_PROJECTION_REL,
                DOCTRINE_GRAPH_REL,
                DOCTRINE_HEALTH_REL,
                COVERAGE_REL,
                ENTRY_CARD_REL,
            ],
        }
        print(json.dumps(result, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if result["status"] == "pass" else 1
    if args.write:
        corpus = write_axiom_instance_corpus(root)
        principle_corpus = write_principle_instance_corpus(root)
        anti_principle_corpus = write_anti_principle_instance_corpus(root)
        concept_corpus = write_concept_instance_corpus(root)
        mechanism_corpus = write_mechanism_instance_corpus(root)
        organ_corpus = write_organ_instance_corpus(root)
        paper_module_corpus = write_paper_module_instance_corpus(root)
        skill_corpus = write_skill_instance_corpus(root)
        standard_corpus = build_standard_instance_corpus(root)
        projection = write_doctrine_projection(root)
        coverage = write_coverage_projection(root, root / COVERAGE_REL)
        entry_card = write_entry_card(root, root / ENTRY_CARD_REL)
        summary: dict[str, Any] = {
            "status": "pass"
            if projection["status"] == coverage["status"] == entry_card["status"] == "pass"
            else "blocked",
            "axiom_corpus": {
                "json_instance_count": corpus["json_instance_count"],
                "parity_status": corpus["parity_status"],
                "authority_flip_status": corpus["authority_flip_status"],
            },
            "principle_corpus": {
                "json_instance_count": principle_corpus["json_instance_count"],
                "parity_status": principle_corpus["parity_status"],
                "authority_flip_status": principle_corpus["authority_flip_status"],
            },
            "anti_principle_corpus": {
                "json_instance_count": anti_principle_corpus["json_instance_count"],
                "parity_status": anti_principle_corpus["parity_status"],
                "authority_flip_status": anti_principle_corpus["authority_flip_status"],
            },
            "concept_corpus": {
                "json_instance_count": concept_corpus["json_instance_count"],
                "parity_status": concept_corpus["parity_status"],
                "authority_flip_status": concept_corpus["authority_flip_status"],
            },
            "mechanism_corpus": {
                "json_instance_count": mechanism_corpus["json_instance_count"],
                "parity_status": mechanism_corpus["parity_status"],
                "authority_flip_status": mechanism_corpus["authority_flip_status"],
            },
            "organ_corpus": {
                "json_instance_count": organ_corpus["json_instance_count"],
                "parity_status": organ_corpus["parity_status"],
                "authority_flip_status": organ_corpus["authority_flip_status"],
            },
            "paper_module_corpus": {
                "json_instance_count": paper_module_corpus["json_instance_count"],
                "parity_status": paper_module_corpus["parity_status"],
                "authority_flip_status": paper_module_corpus["authority_flip_status"],
                "legacy_only_count": paper_module_corpus["legacy_only_count"],
                "required_subject_gap_count": paper_module_corpus["required_subject_gap_count"],
            },
            "skill_corpus": {
                "json_instance_count": skill_corpus["json_instance_count"],
                "parity_status": skill_corpus["parity_status"],
                "authority_flip_status": skill_corpus["authority_flip_status"],
                "required_relation_gap_count": skill_corpus["required_relation_gap_count"],
                "unpopulated_selective_relation_count": skill_corpus["unpopulated_selective_relation_count"],
            },
            "standard_corpus": {
                "json_instance_count": standard_corpus["json_instance_count"],
                "parity_status": standard_corpus["parity_status"],
                "authority_flip_status": standard_corpus["authority_flip_status"],
                "legacy_or_draft_contract_count": standard_corpus["legacy_or_draft_contract_count"],
                "required_relation_gap_count": standard_corpus["required_relation_gap_count"],
                "unregistered_file_count": len(standard_corpus["extra_json_ids"]),
            },
            "written": [
                "axioms/*.json",
                "axioms/*.md",
                "principles/*.json",
                "principles/*.md",
                "anti_principles/*.json",
                "anti_principles/*.md",
                "concepts/*.json",
                "concepts/*.md",
                "mechanisms/*.json",
                "mechanisms/*.md",
                "organs/*.json",
                "organs/*.md",
                "paper_modules/*.json",
                "skills/*.json",
                DOCTRINE_PROJECTION_REL,
                DOCTRINE_GRAPH_REL,
                DOCTRINE_HEALTH_REL,
                COVERAGE_REL,
                ENTRY_CARD_REL,
            ],
            "read_source_authorities": [
                "standards/std_microcosm_*.json",
                "core/standards_registry.json",
            ],
        }
        print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
        return 0 if summary["status"] == "pass" else 1

    projection = build_doctrine_projection(root)
    print(
        json.dumps(
            {
                "status": projection["status"],
                "axiom_corpus": projection["axiom_instance_corpus"],
                "principle_corpus": projection["principle_instance_corpus"],
                "anti_principle_corpus": projection["anti_principle_instance_corpus"],
                "concept_corpus": projection["concept_instance_corpus"],
                "mechanism_corpus": projection["mechanism_instance_corpus"],
                "organ_corpus": projection["organ_instance_corpus"],
                "paper_module_corpus": projection["paper_module_instance_corpus"],
                "skill_corpus": projection["skill_instance_corpus"],
                "standard_corpus": projection["standard_instance_corpus"],
                "generated_surfaces": [
                    DOCTRINE_PROJECTION_REL,
                    DOCTRINE_GRAPH_REL,
                    DOCTRINE_HEALTH_REL,
                ],
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if projection["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
