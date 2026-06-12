#!/usr/bin/env python3
"""Project doctrine-enrichment coverage health.

Reads the hand-authored enrichment source of record
(``core/doctrine_enrichment.json``) against the axiom/principle/anti-principle
instance corpora and reports per-kind coverage: how many objects are enriched
and how many carry each reader field. It also reads governed concept and
mechanism JSON rows to report the doctrine-routing floor beyond the 49
reader-enrichment cards. Coverage is PRESENCE / STRUCTURE, not correctness;
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
ROUTING_KIND_DIRS = {
    "concept": ("concepts", "concept.*.json"),
    "mechanism": ("mechanisms", "mechanism.*.json"),
}
REQUIRED_FIELDS = ("deep", "formal", "governs", "requires", "refuses", "example", "counterexample", "enforced_in", "does_not_prove")
ROUTING_REF_FIELDS = ("source_refs", "validator_refs", "receipt_refs", "anti_claims")
MECHANISM_PAYLOAD_REQUIRED_FIELDS = (
    "contract_version",
    "guardrails",
    "migration_contract",
    "projection_contract",
    "resolution_evidence",
    "support_contract",
)
ROUTING_REQUIRED_STRUCTURES = {
    "concept": [
        "source_refs",
        "valid_json_object",
        "validator_refs",
        "receipt_refs",
        "anti_claims",
        "entry_surface_contract",
        "cluster_flag",
        "relationships.edges",
        "resolved_mechanism_route",
        "empty_unpopulated_selective_relations",
    ],
    "mechanism": [
        "source_refs",
        "valid_json_object",
        "validator_refs",
        "receipt_refs",
        "anti_claims",
        "entry_surface_contract",
        "organ_refs",
        "mechanism_payload.contract",
        "relationships.edges",
        "resolved_concept_route",
        "resolved_existing_code_locus",
        "known_residual_selective_relations_counted_not_blocking",
    ],
}


def _corpus_ids(root: Path, kind: str) -> list[str]:
    """List the object ids present in one doctrine-kind instance corpus.

    - Teleology: enumerate the axiom/principle/anti-principle ids that enrichment coverage is measured against, drawn from the generated JSON instances.
    - Guarantee: returns the sorted-by-path list of `id` values for every well-formed JSON instance under the kind's directory/glob that carries a truthy `id`.
    - Fails: never raises for bad data — files that fail json.JSONDecodeError or lack an `id` are skipped; a missing directory yields an empty list. Only KIND_DIRS[kind] KeyError for an unknown kind would propagate.
    - Reads: the per-kind instance JSON files under root/<subdir>/<glob> (e.g. axioms/AX-*.json).
    - When-needed: when reconciling which corpus ids the health projection treats as the coverage denominator.
    - Non-goal: does not validate instance contents or authorize the corpus as source authority; id enumeration only.
    """
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


def _routing_records(root: Path, kind: str) -> list[dict[str, Any]]:
    """Load governed doctrine rows that participate in the routing floor.

    - Teleology: enumerate the non-reader-card doctrine objects whose
      relationships should be checker-visible before the enrichment floor grows
      to all doctrine kinds.
    - Guarantee: returns every JSON-path candidate under the configured routing
      kind directory/glob, sorted by path; malformed files become explicit
      load-error records so the floor cannot pass by omission.
    - Fails: KeyError for an unknown kind would propagate.
    - Reads: root/<subdir>/<glob>, currently concepts/concept.*.json and
      mechanisms/mechanism.*.json.
    - Non-goal: does not treat the row as source authority beyond its own
      governed JSON contract; this is a structural routing check only.
    """
    subdir, glob = ROUTING_KIND_DIRS[kind]
    records: list[dict[str, Any]] = []
    for path in sorted((root / subdir).glob(glob)):
        try:
            row = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            records.append(
                {
                    "id": f"{kind}.invalid_json.{path.name}",
                    "kind": kind,
                    "_routing_load_error": f"json_decode_error:{exc.msg}",
                }
            )
            continue
        if isinstance(row, dict):
            records.append(row)
        else:
            records.append(
                {
                    "id": f"{kind}.json_root_not_object.{path.name}",
                    "kind": kind,
                    "_routing_load_error": "json_root_not_object",
                }
            )
    return records


def _has_field(record: dict[str, Any], field: str) -> bool:
    """Decide whether one enrichment record meaningfully populates a reader field.

    - Teleology: the per-field presence predicate that drives the coverage counts; encodes the shape each REQUIRED_FIELD must take to count as present.
    - Guarantee: returns True iff the field carries real content per its kind — `formal` needs a non-empty latex string, `example`/`counterexample` a non-empty text string, `enforced_in` a non-empty list, and any other field a non-empty stringified value.
    - Fails: never raises; absent/empty/wrong-typed values return False.
    - Reads: the in-memory `record` dict only.
    - When-needed: when explaining why a record was counted enriched/partial for a given field.
    - Non-goal: PRESENCE only — does not judge correctness, fidelity, or render-validity of the field.
    """
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


def _audit_concept_routing_record(record: dict[str, Any]) -> list[str]:
    """Return structural routing-floor issues for one concept row.

    - Teleology: make concept routing visible to the same health checker that
      already protects the 49 reader-enrichment cards.
    - Guarantee: returns issue codes for missing source/validator/receipt refs,
      missing typed edges, unresolved selective relations, missing mechanism
      route, and under-specified edge justifications.
    - Non-goal: does not judge whether the concept taxonomy is complete or
      whether target mechanisms are domain-correct; it checks walkable,
      source-backed routes only.
    """
    issues: list[str] = []
    load_error = str(record.get("_routing_load_error") or "").strip()
    if load_error:
        return [load_error]

    concept_id = str(record.get("id") or "").strip()
    if not concept_id:
        issues.append("id_missing")
    if record.get("kind") != "concept":
        issues.append("kind_not_concept")
    if not str(record.get("authority_boundary") or "").strip():
        issues.append("authority_boundary_missing")

    for field in ROUTING_REF_FIELDS:
        if not isinstance(record.get(field), list) or not record[field]:
            issues.append(f"{field}_missing")

    entry_contract = record.get("entry_surface_contract")
    if not isinstance(entry_contract, dict) or entry_contract.get("required") is not True:
        issues.append("entry_surface_contract_missing")

    cluster_flag = record.get("cluster_flag")
    if not isinstance(cluster_flag, dict) or cluster_flag.get("concept_id") != concept_id:
        issues.append("cluster_flag_mismatch")

    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        issues.append("relationships_missing")
        return issues

    if relationships.get("unpopulated_selective_relations"):
        issues.append("unpopulated_selective_relations_present")

    edges = relationships.get("edges")
    if not isinstance(edges, list) or not edges:
        issues.append("edges_missing")
        edges = []

    mechanism_route_count = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edge_{index}_not_object")
            continue
        relation_id = str(edge.get("relation_id") or "")
        if not relation_id.startswith("concept."):
            issues.append(f"edge_{index}_relation_id_not_concept")
        for field in ("relation_verb", "reverse_verb", "target_id", "target_kind", "target_status"):
            if not str(edge.get(field) or "").strip():
                issues.append(f"edge_{index}_{field}_missing")
        justification = edge.get("justification")
        if not isinstance(justification, dict):
            issues.append(f"edge_{index}_justification_missing")
        else:
            if not str(justification.get("source_ref") or "").strip():
                issues.append(f"edge_{index}_source_ref_missing")
            if not str(justification.get("summary") or "").strip():
                issues.append(f"edge_{index}_summary_missing")
        if edge.get("target_status") != "resolved_json_instance":
            issues.append(f"edge_{index}_target_unresolved")
        if edge.get("target_kind") == "mechanism" and edge.get("target_status") == "resolved_json_instance":
            mechanism_route_count += 1

    if mechanism_route_count == 0:
        issues.append("resolved_mechanism_route_missing")
    return issues


def _audit_mechanism_routing_record(root: Path, record: dict[str, Any]) -> list[str]:
    """Return structural routing-floor issues for one mechanism row.

    - Teleology: make mechanism rows count as doctrine routing only when they
      walk to both an interpretive sibling concept and runnable substrate.
    - Guarantee: returns issue codes for missing refs, missing entry contract,
      missing payload contract, missing resolved concept edge, and missing
      resolved existing code locus.
    - Non-goal: does not require topology completeness; known
      unpopulated_selective_relations are surfaced in the kind summary instead
      of treated as proof that no neighbors exist.
    """
    issues: list[str] = []
    load_error = str(record.get("_routing_load_error") or "").strip()
    if load_error:
        return [load_error]

    mechanism_id = str(record.get("id") or "").strip()
    if not mechanism_id:
        issues.append("id_missing")
    if record.get("kind") != "mechanism":
        issues.append("kind_not_mechanism")
    if not str(record.get("authority_boundary") or "").strip():
        issues.append("authority_boundary_missing")

    for field in ROUTING_REF_FIELDS:
        if not isinstance(record.get(field), list) or not record[field]:
            issues.append(f"{field}_missing")

    entry_contract = record.get("entry_surface_contract")
    if not isinstance(entry_contract, dict) or entry_contract.get("required") is not True:
        issues.append("entry_surface_contract_missing")

    if not isinstance(record.get("organ_refs"), list) or not record["organ_refs"]:
        issues.append("organ_refs_missing")

    mechanism_payload = record.get("mechanism_payload")
    if not isinstance(mechanism_payload, dict):
        issues.append("mechanism_payload_missing")
    else:
        for field in MECHANISM_PAYLOAD_REQUIRED_FIELDS:
            if not mechanism_payload.get(field):
                issues.append(f"mechanism_payload_{field}_missing")

    code_loci = record.get("code_loci")
    resolved_existing_code_loci = 0
    if not isinstance(code_loci, list) or not code_loci:
        issues.append("code_loci_missing")
    else:
        for index, locus in enumerate(code_loci):
            if not isinstance(locus, dict):
                issues.append(f"code_locus_{index}_not_object")
                continue
            path = str(locus.get("path") or "").strip()
            if not path:
                issues.append(f"code_locus_{index}_path_missing")
            if locus.get("resolution") != "resolved":
                issues.append(f"code_locus_{index}_not_resolved")
            if path and locus.get("resolution") == "resolved":
                if (root / path).exists():
                    resolved_existing_code_loci += 1
                else:
                    issues.append(f"code_locus_{index}_path_not_found")
    if resolved_existing_code_loci == 0:
        issues.append("resolved_existing_code_locus_missing")

    relationships = record.get("relationships")
    if not isinstance(relationships, dict):
        issues.append("relationships_missing")
        return issues

    edges = relationships.get("edges")
    if not isinstance(edges, list) or not edges:
        issues.append("edges_missing")
        edges = []

    concept_route_count = 0
    for index, edge in enumerate(edges):
        if not isinstance(edge, dict):
            issues.append(f"edge_{index}_not_object")
            continue
        relation_id = str(edge.get("relation_id") or "")
        if not relation_id.startswith("mechanism."):
            issues.append(f"edge_{index}_relation_id_not_mechanism")
        for field in ("relation_verb", "reverse_verb", "target_id", "target_kind", "target_status"):
            if not str(edge.get(field) or "").strip():
                issues.append(f"edge_{index}_{field}_missing")
        justification = edge.get("justification")
        if not isinstance(justification, dict):
            issues.append(f"edge_{index}_justification_missing")
        else:
            if not str(justification.get("source_ref") or "").strip():
                issues.append(f"edge_{index}_source_ref_missing")
            if not str(justification.get("summary") or "").strip():
                issues.append(f"edge_{index}_summary_missing")
        if edge.get("target_kind") == "concept" and edge.get("target_status") == "resolved_json_instance":
            concept_route_count += 1

    if concept_route_count == 0:
        issues.append("resolved_concept_route_missing")
    return issues


def _mechanism_residual_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize mechanism routing residuals that are not floor blockers."""
    residual_rows: list[dict[str, Any]] = []
    planned_edge_rows: list[dict[str, Any]] = []
    for record in records:
        if record.get("_routing_load_error"):
            continue
        mechanism_id = str(record.get("id") or "<missing>")
        relationships = record.get("relationships")
        if not isinstance(relationships, dict):
            continue
        residuals = relationships.get("unpopulated_selective_relations")
        if isinstance(residuals, list) and residuals:
            residual_rows.append({"id": mechanism_id, "count": len(residuals)})
        edges = relationships.get("edges")
        if isinstance(edges, list):
            planned_count = sum(
                1
                for edge in edges
                if isinstance(edge, dict) and str(edge.get("target_status") or "").startswith("planned_")
            )
            if planned_count:
                planned_edge_rows.append({"id": mechanism_id, "count": planned_count})
    return {
        "known_residual_selective_relation_rows": residual_rows,
        "known_residual_selective_relation_row_count": len(residual_rows),
        "known_residual_selective_relation_count": sum(row["count"] for row in residual_rows),
        "planned_edge_rows": planned_edge_rows,
        "planned_edge_row_count": len(planned_edge_rows),
        "planned_edge_count": sum(row["count"] for row in planned_edge_rows),
        "residual_policy": "Residual selective relations and planned non-floor edges are disclosed as frontier pressure, not counted as support evidence or topology completeness.",
    }


def _build_routing_floor(root: Path) -> dict[str, Any]:
    """Build the non-reader-card doctrine routing floor.

    - Teleology: extend the health scoreboard beyond the 49 enrichment cards
      without inflating edge counts; every counted route must have a
      checker-readable reason and a walkable substrate path.
    - Guarantee: emits concept and mechanism routing coverage over governed
      JSON rows; status is complete only when every covered row passes its
      kind-specific structural audit.
    - Reads: governed concept and mechanism JSON rows.
    - Non-goal: does not cover paper modules yet and does not claim complete
      topology for mechanism rows with known residual selective relations.
    """
    kinds: dict[str, Any] = {}
    incomplete: list[dict[str, Any]] = []
    for kind in ROUTING_KIND_DIRS:
        records = _routing_records(root, kind)
        if kind == "concept":
            issue_rows = [
                {"id": str(record.get("id") or "<missing>"), "issues": _audit_concept_routing_record(record)}
                for record in records
            ]
        elif kind == "mechanism":
            issue_rows = [
                {"id": str(record.get("id") or "<missing>"), "issues": _audit_mechanism_routing_record(root, record)}
                for record in records
            ]
        else:
            issue_rows = []
        issue_rows = [row for row in issue_rows if row["issues"]]
        incomplete.extend(issue_rows)
        routed = len(records) - len(issue_rows)
        kind_row: dict[str, Any] = {
            "total": len(records),
            "routed": routed,
            "incomplete_ids": [row["id"] for row in issue_rows],
            "issue_rows": issue_rows,
            "required_structures": ROUTING_REQUIRED_STRUCTURES[kind],
        }
        if kind == "mechanism":
            kind_row.update(_mechanism_residual_summary(records))
        kinds[kind] = kind_row
    total = sum(row["total"] for row in kinds.values())
    routed = sum(row["routed"] for row in kinds.values())
    complete = not incomplete and total == routed
    return {
        "schema_version": "microcosm_doctrine_routing_floor_v2",
        "authority_boundary": "Concept and mechanism routing floor over governed JSON rows. Structure and route presence only; not concept completeness, topology completeness, support evidence, release authority, or proof correctness.",
        "status": "complete" if complete else "partial",
        "coverage_complete": complete,
        "source_of_record": {
            "concept": "concepts/concept.*.json",
            "mechanism": "mechanisms/mechanism.*.json",
        },
        "covered_kinds": sorted(ROUTING_KIND_DIRS),
        "total_objects": total,
        "routed_objects": routed,
        "kinds": kinds,
        "incomplete": incomplete,
    }


def build_health(root: Path) -> dict[str, Any]:
    """Build the doctrine-enrichment coverage-health projection for a root.

    - Teleology: project per-kind reader-enrichment completeness (how many doctrine objects are enriched and carry each reader field) plus the folded-in formal-soundness and reader-ladder structural gates.
    - Guarantee: returns a health dict (schema microcosm_doctrine_enrichment_health_v1) with per-kind totals/enriched/field counts/partials, an `incomplete` list, and a `status` of "complete" iff coverage is full AND formal soundness AND reader-ladder report zero unsound; else "partial".
    - Fails: raises json.JSONDecodeError / FileNotFoundError if core/doctrine_enrichment.json is missing or malformed; sub-gate exceptions from run_soundness/run_reader_ladder propagate.
    - Reads: core/doctrine_enrichment.json (source of record) and the axiom/principle/anti-principle instance corpora (via _corpus_ids); delegates to run_soundness and run_reader_ladder over the enrichment file.
    - When-needed: when deciding whether reader enrichment is complete before a dissemination build or as the data behind the --check CI gate.
    - Escalates-to: check_doctrine_formal_soundness.run and check_doctrine_reader_ladder.run for the structural sub-gates; the dissemination build's LaTeX-render test for render correctness.
    - Non-goal: measures PRESENCE not correctness, is never support evidence, and the emitted artifact is a generated projection — not source authority and not release authorization.
    """
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
    routing_floor = _build_routing_floor(root)
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
    # potential_misread), with no laundering, banned visible term, or lay overclaim.
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
    complete = (
        coverage_complete
        and soundness["unsound"] == 0
        and reader_ladder["unsound"] == 0
        and routing_floor["status"] == "complete"
    )
    return {
        "schema_version": "microcosm_doctrine_enrichment_health_v1",
        "source_of_record": ENRICHMENT_REL,
        "standard_ref": "standards/std_microcosm_doctrine_enrichment.json",
        "authority_boundary": "Coverage projection over reader enrichment plus concept and mechanism routing floors. Presence/structure, not correctness, and never support evidence. Generated; do not hand-edit.",
        "status": "complete" if complete else "partial",
        "coverage_complete": coverage_complete,
        "total_objects": total,
        "enriched_objects": enriched_total,
        "reader_enrichment_total_objects": total,
        "reader_enrichment_complete": coverage_complete,
        "governed_floor_total_objects": total + routing_floor["total_objects"],
        "governed_floor_complete": complete,
        "kinds": kinds,
        "incomplete": all_missing,
        "routing_floor": routing_floor,
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
