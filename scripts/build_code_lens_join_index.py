#!/usr/bin/env python3
"""Build the code-lens join index: a source-body-free semantic property graph.

The join index is the intermediate representation the Comprehension Plane queries.
v2 joins FOUR public planes into one typed graph: what python-lens knows about
source symbols (atom coverage, specificity_v3 bands, source class), what the organ
registry knows about organs (runner module, governing validator command, generated
receipts, evidence class, authority ceiling), what the organ atlas knows about
topology (families, wires_to, doctrine refs), and what the agent task routes know
about entry (task_class -> organ fan-out with first commands and stop conditions).
It is a semantic/provenance/navigation graph -- NOT a static-analysis control-flow
or data-flow graph -- and it never exports docstring prose or source bodies.

- Teleology: turn the populated code-lens atoms + specificity scores + organ
  registry + organ atlas + agent task routes into one typed node/edge graph a cold
  agent can query by organ, claim, route, or family instead of rereading the repo.
- Guarantee: given a python-lens --full snapshot and core/organ_registry.json
  (plus, when present, core/organ_atlas.json and atlas/agent_task_routes.json),
  writes a microcosm_code_lens_join_index_v2 JSON of organ/source_file/claim/route/
  family nodes, the v0 implemented_by_runner / emits_receipt edges plus the v2
  asserts_claim / validated_by / proven_by / member_of_family / wires_to /
  routes_to / grounded_in_doctrine edges, a graph block whose resolved/deferred
  edge classes are COMPUTED from what was materialized, per-organ + per-file
  specificity rollups, and a non-authorizing ceiling; source_bodies_exported is
  always false.
- Fails: SystemExit(2) when a required input is missing/unparseable; SystemExit(3)
  if the lens snapshot reports any source-body export (refuses to join a leaky run).
- Reads: the --lens snapshot, the --registry organ registry, and (optional planes)
  the --atlas organ atlas and --routes agent task routes.
- Writes: the --out join index (default receipts/code_lens/code_lens_join_index_v0.json;
  the v0 filename is a stable artifact path, the schema_version inside is v2).
- Non-goal: does not authorize release, source-body export, static-analysis
  correctness, or whole-system correctness; it is a navigation read-model only.
  It also does not extract Lean proof-term structure: proof_internal_structure
  stays a computed deferred edge class until a Lean-aware proof-graph builder
  feeds this index.
- When-needed: run after python-lens/specificity_v3 or any atlas/route/registry
  refresh to rebuild the comprehension IR.
- Escalates-to: project_substrate.py (python-lens), core/organ_registry.json,
  core/organ_atlas.json, atlas/agent_task_routes.json.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

COUPLING_ZONE_MARKERS = ("/organs/", "/macro_tools/", "/engine_room/")

SCHEMA_VERSION = "microcosm_code_lens_join_index_v2"

# The atlas/route planes are public generated docs, but the join index screens the
# string values it copies anyway (defense in depth, mirroring the comprehension
# plane's excerpt guard): a secret-shaped or private-home-path value is dropped and
# counted, never emitted.
_SECRET_SHAPE_RE = re.compile(
    r"sk-[A-Za-z0-9]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{30,}"
    r"|xox[baprs]-[A-Za-z0-9-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY",
)
_PRIVATE_PATH_RE = re.compile(r"/Users/[A-Za-z0-9._-]+|/home/[A-Za-z0-9._-]+")

# The three comprehension edge classes the read packs historically deferred. v2
# resolves the first two from public substrate planes; the third stays deferred
# until a Lean-aware proof-graph builder exists, and the graph block says so with
# a precise residual (missing-source class + owner + re-entry command), never a
# vague someday note.
EDGE_CLASS_CLAIM = "claim_node_ontology"
EDGE_CLASS_ROUTE = "cross_organ_route_topology"
EDGE_CLASS_PROOF = "proof_internal_structure"

_PROOF_RESIDUAL: dict[str, str] = {
    "edge_class": EDGE_CLASS_PROOF,
    "missing": "theorem -> lemma -> tactic edges inside a proof organ",
    "missing_source_class": "lean_proof_term_graph_not_extracted",
    "owner_path": "scripts/build_code_lens_join_index.py",
    "blocked_on": "no Lean-aware proof-graph builder exists yet; see owner_path",
    "would_come_from": "a Lean-aware proof-graph builder feeding this join index",
}


def _load_json(path: Path, label: str) -> Any:
    """Parse a required JSON input or stop with a typed error.

    - Teleology: the one validated reader for the builder's two inputs.
    - Guarantee: returns the parsed JSON value when the file exists and parses.
    - Fails: SystemExit(2) when the path is missing or the body is not JSON.
    - Reads: the file at ``path``.
    - Writes: None.
    """
    if not path.is_file():
        raise SystemExit(f"2: {label} not found: {path}")
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"2: {label} unparseable: {path}: {exc}")


def _capsule_rows(lens: dict[str, Any]) -> list[dict[str, Any]]:
    """Return the symbol capsule rows from a python-lens snapshot.

    - Teleology: isolate the one snapshot field the join index consumes.
    - Guarantee: returns the list at ``symbol_capsule_rows`` or [] when absent.
    - Fails: never raises; a non-list value yields [].
    - Reads: the in-memory snapshot only.
    """
    rows = lens.get("symbol_capsule_rows")
    return rows if isinstance(rows, list) else []


def _custody_basis(path: str) -> str:
    """Classify a source file's custody basis from its path.

    - Teleology: tell a reader whether an organ's runner code is owned or an
      exact-copy macro body (which must not be authored locally).
    - Guarantee: returns "directory_coupling_marker" for organs/macro_tools/
      engine_room exact-copy zones, else "owned".
    - Fails: never raises (substring test).
    - Reads: only the supplied path string.
    """
    return (
        "directory_coupling_marker"
        if any(marker in path for marker in COUPLING_ZONE_MARKERS)
        else "owned"
    )


def _file_rollups(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Aggregate capsule rows into per-source-file specificity rollups.

    - Teleology: compress the flat capsule list into one node per source file
      carrying its atom coverage and specificity bands.
    - Guarantee: returns path -> {source_class, custody_basis, symbol_count,
      real_coverage, body_specific, generic_unique, has_non_goal}; counts only,
      no prose.
    - Fails: never raises; rows missing fields default to zero/empty.
    - Reads: the in-memory capsule rows only.
    """
    files: dict[str, dict[str, Any]] = {}
    for row in rows:
        path = str(row.get("path") or "")
        if not path:
            continue
        bucket = files.setdefault(
            path,
            {
                "source_class": row.get("source_class"),
                "custody_basis": _custody_basis(path),
                "symbol_count": 0,
                "real_coverage": 0,
                "body_specific": 0,
                "generic_unique": 0,
                "has_non_goal": 0,
            },
        )
        bucket["symbol_count"] += 1
        if row.get("is_real_coverage"):
            bucket["real_coverage"] += 1
            specificity = row.get("atom_specificity")
            if specificity == "body_specific":
                bucket["body_specific"] += 1
            elif specificity == "generic_unique":
                bucket["generic_unique"] += 1
            if row.get("atom_has_non_goal"):
                bucket["has_non_goal"] += 1
    return files


def _resolved_ref_strings(rows: Any) -> list[str]:
    """Flatten an atlas ref list ({ref, resolution_status} rows or strings) to refs.

    - Teleology: one extractor for the atlas's doctrine ref shapes so the graph
      builder and the comprehension plane read refs the same way.
    - Guarantee: returns the ref strings whose resolution_status is absent or
      "resolved"; plain strings pass through; non-list input yields [].
    - Fails: never raises.
    - Reads: only the supplied rows.
    """
    if not isinstance(rows, list):
        return []
    out: list[str] = []
    for row in rows:
        if isinstance(row, str):
            out.append(row)
        elif isinstance(row, dict) and row.get("resolution_status") in (None, "resolved"):
            ref = row.get("ref")
            if ref:
                out.append(str(ref))
    return out


def _screen_value(value: Any, guard: dict[str, int]) -> Any:
    """Drop (and count) a copied string value that looks like a secret/private path.

    - Teleology: defense-in-depth on the atlas/route pass-through -- the join index
      never becomes the surface that republishes a leaked credential or home path.
    - Guarantee: returns the value unchanged when clean or non-string; returns None
      and increments guard["values_dropped"] when a secret shape or private home
      path matches.
    - Fails: never raises.
    """
    if isinstance(value, str) and (
        _SECRET_SHAPE_RE.search(value) or _PRIVATE_PATH_RE.search(value)
    ):
        guard["values_dropped"] = guard.get("values_dropped", 0) + 1
        return None
    return value


def _claim_node(
    organ: dict[str, Any], atlas_row: dict[str, Any], guard: dict[str, int]
) -> dict[str, Any]:
    """Materialize the first-class claim node for one organ.

    - Teleology: give the claim its own graph identity (claim_node_ontology) so a
      claim trace reads graph nodes instead of re-deriving fields per packet.
    - Guarantee: returns {claim_id "claim::<organ_id>", organ_id, claim_ceiling,
      claim_ceiling_restated, evidence_class, evidence_strength_rank,
      truth_accounting_bucket, validator_command, authority_receipt}; the copied
      atlas restatement is screened via _screen_value.
    - Fails: never raises; absent fields become None.
    - Reads: only the supplied registry organ + atlas row.
    """
    organ_id = str(organ.get("organ_id") or "")
    return {
        "claim_id": f"claim::{organ_id}",
        "organ_id": organ_id,
        "claim_ceiling": organ.get("claim_ceiling"),
        "claim_ceiling_restated": _screen_value(
            atlas_row.get("claim_ceiling_restated"), guard
        ),
        "evidence_class": organ.get("evidence_class"),
        "evidence_strength_rank": organ.get("evidence_strength_rank"),
        "truth_accounting_bucket": organ.get("truth_accounting_bucket"),
        "validator_command": organ.get("validator_command"),
        "authority_receipt": organ.get("current_authority_receipt"),
    }


def _route_rows(routes_doc: Any) -> list[dict[str, Any]]:
    """Return the task-route rows from atlas/agent_task_routes.json.

    - Teleology: isolate the one routes field the graph consumes.
    - Guarantee: returns the dict rows under "routes"; [] when absent/malformed.
    - Fails: never raises.
    """
    rows = (routes_doc or {}).get("routes") if isinstance(routes_doc, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _route_organ_ids(route: dict[str, Any]) -> list[tuple[str, str]]:
    """Resolve a route row's organ fan-out to (organ_id, role) pairs.

    - Teleology: extract ONLY the ids from the route's heavy embedded organ cards
      so the graph carries fan-out topology, never duplicated card prose.
    - Guarantee: returns (organ_id, "primary"|"relevant") pairs, primary first,
      de-duplicated with the primary role winning.
    - Fails: never raises.
    - Non-goal: never copies relevant_organs card bodies into the graph.
    """
    pairs: list[tuple[str, str]] = []
    seen: set[str] = set()
    primary = str(route.get("primary_organ_id") or "")
    if primary:
        pairs.append((primary, "primary"))
        seen.add(primary)
    relevant = route.get("relevant_organs")
    for row in relevant if isinstance(relevant, list) else []:
        oid = str(row.get("organ_id") or "") if isinstance(row, dict) else str(row or "")
        if oid and oid not in seen:
            pairs.append((oid, "relevant"))
            seen.add(oid)
    return pairs


def _runner_source_ref(runner: str | None) -> str | None:
    """Resolve an organ runner's dotted module to a repo-relative source path.

    - Teleology: bridge the organ registry's dotted runner to the file the lens
      indexes, so organs can be joined to their code.
    - Guarantee: returns "src/<dotted/with/slashes>.py" for a microcosm_core.*
      runner; None when the runner is empty or not a microcosm_core module.
    - Fails: never raises (string shaping only).
    - Reads: only the supplied runner string.
    """
    if not runner or not runner.startswith("microcosm_core."):
        return None
    return "src/" + runner.replace(".", "/") + ".py"


_DOCTRINE_REF_FIELDS: tuple[tuple[str, str], ...] = (
    ("axiom_refs", "axiom"),
    ("principle_refs", "principle"),
    ("concept_refs", "concept"),
    ("mechanism_refs", "mechanism"),
)


def _graph_edges_for_organ(
    organ_id: str, atlas_row: dict[str, Any]
) -> list[dict[str, Any]]:
    """Build the v2 atlas-plane edges (family / wires_to / doctrine) for one organ.

    - Teleology: turn the atlas row's topology fields into typed graph edges so
      comprehension packets select edges instead of re-reading the atlas.
    - Guarantee: returns member_of_family, wires_to, and grounded_in_doctrine
      edges (ref_kind axiom/principle/concept/mechanism/paper_module); [] for an
      empty atlas row.
    - Fails: never raises.
    - Reads: only the supplied atlas row.
    """
    edges: list[dict[str, Any]] = []
    family = atlas_row.get("family")
    if family:
        edges.append(
            {
                "from_type": "organ",
                "from": organ_id,
                "to_type": "family",
                "to": str(family),
                "kind": "member_of_family",
            }
        )
    wires = atlas_row.get("wires_to")
    for peer in wires if isinstance(wires, list) else []:
        if peer:
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "organ",
                    "to": str(peer),
                    "kind": "wires_to",
                }
            )
    for field, ref_kind in _DOCTRINE_REF_FIELDS:
        for ref in _resolved_ref_strings(atlas_row.get(field)):
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "doctrine_ref",
                    "to": ref,
                    "kind": "grounded_in_doctrine",
                    "ref_kind": ref_kind,
                }
            )
    pmr = atlas_row.get("paper_module_ref")
    if pmr:
        edges.append(
            {
                "from_type": "organ",
                "from": organ_id,
                "to_type": "doctrine_ref",
                "to": str(pmr),
                "kind": "grounded_in_doctrine",
                "ref_kind": "paper_module",
            }
        )
    return edges


def _claim_edges(claim: dict[str, Any]) -> list[dict[str, Any]]:
    """Build the claim-ontology edges for one claim node.

    - Teleology: chain organ -> claim -> validator/receipt as graph edges so a
      claim trace is a selection, not a synthesis.
    - Guarantee: returns asserts_claim always, validated_by when a validator
      command exists, proven_by when an authority receipt exists.
    - Fails: never raises.
    - Reads: only the supplied claim node.
    """
    organ_id = claim["organ_id"]
    claim_id = claim["claim_id"]
    edges: list[dict[str, Any]] = [
        {
            "from_type": "organ",
            "from": organ_id,
            "to_type": "claim",
            "to": claim_id,
            "kind": "asserts_claim",
        }
    ]
    if claim.get("validator_command"):
        edges.append(
            {
                "from_type": "claim",
                "from": claim_id,
                "to_type": "validator_command",
                "to": str(claim["validator_command"]),
                "kind": "validated_by",
            }
        )
    if claim.get("authority_receipt"):
        edges.append(
            {
                "from_type": "claim",
                "from": claim_id,
                "to_type": "receipt",
                "to": str(claim["authority_receipt"]),
                "kind": "proven_by",
            }
        )
    return edges


def build_join_index(
    lens: dict[str, Any],
    registry: dict[str, Any],
    atlas: dict[str, Any] | None = None,
    routes: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble the join index from the lens, registry, atlas, and route planes.

    - Teleology: the composition root that turns code-lens + organ registry +
      organ atlas + agent task routes into the Comprehension Plane's queryable IR.
    - Guarantee: returns a microcosm_code_lens_join_index_v2 dict with organ /
      source_file / claim / route / family nodes, the v0 edges plus the v2
      claim/route/family/doctrine edges, a graph block whose resolved_edge_classes
      and deferred_edge_classes are computed from the materialized planes, rollups,
      and a non-authorizing ceiling; export_band is presence_only and
      source_bodies_exported is False; absent atlas/routes planes degrade to a
      smaller graph with the matching edge classes honestly re-deferred.
    - Fails: SystemExit(3) if the lens snapshot reports a source-body export.
    - Reads: the in-memory inputs only.
    - Non-goal: does not authorize release or source-body export; navigation only.
      Never copies route relevant_organs card bodies into the graph.
    - Escalates-to: _file_rollups / _runner_source_ref / _claim_node /
      _route_organ_ids / _graph_edges_for_organ for field provenance.
    """
    boundary = lens.get("payload_boundary", {})
    if isinstance(boundary, dict) and boundary.get("source_bodies_exported"):
        raise SystemExit("3: refusing to join a lens snapshot that exports source bodies")
    files = _file_rollups(_capsule_rows(lens))
    organs = registry.get("implemented_organs", [])
    atlas_rows = (atlas or {}).get("organs") or []
    atlas_by: dict[str, dict[str, Any]] = {
        str(r.get("organ_id")): r for r in atlas_rows if isinstance(r, dict)
    }
    route_rows = _route_rows(routes)
    leak_guard: dict[str, int] = {"values_dropped": 0}

    organ_nodes: list[dict[str, Any]] = []
    claim_nodes: list[dict[str, Any]] = []
    family_counts: dict[str, int] = {}
    source_file_paths: set[str] = set()
    edges: list[dict[str, Any]] = []
    resolved = 0
    for organ in organs:
        if not isinstance(organ, dict):
            continue
        organ_id = str(organ.get("organ_id") or "")
        runner = organ.get("runner")
        runner_ref = _runner_source_ref(runner)
        file_roll = files.get(runner_ref) if runner_ref else None
        if file_roll is not None:
            resolved += 1
            source_file_paths.add(runner_ref)
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "source_file",
                    "to": runner_ref,
                    "kind": "implemented_by_runner",
                }
            )
        receipts = organ.get("generated_receipts") or []
        for receipt in receipts:
            edges.append(
                {
                    "from_type": "organ",
                    "from": organ_id,
                    "to_type": "receipt",
                    "to": str(receipt),
                    "kind": "emits_receipt",
                }
            )
        atlas_row = atlas_by.get(organ_id) or {}
        claim = _claim_node(organ, atlas_row, leak_guard)
        claim_nodes.append(claim)
        edges.extend(_claim_edges(claim))
        edges.extend(_graph_edges_for_organ(organ_id, atlas_row))
        family = atlas_row.get("family")
        if family:
            family_counts[str(family)] = family_counts.get(str(family), 0) + 1
        organ_nodes.append(
            {
                "organ_id": organ_id,
                "evidence_class": organ.get("evidence_class"),
                "evidence_strength_rank": organ.get("evidence_strength_rank"),
                "truth_accounting_bucket": organ.get("truth_accounting_bucket"),
                "real_substrate_disposition": organ.get("real_substrate_disposition"),
                "claim_ceiling": organ.get("claim_ceiling"),
                "status": organ.get("status"),
                "family": atlas_row.get("family"),
                "runner_module": runner,
                "runner_source_ref": runner_ref,
                "runner_source_resolved": file_roll is not None,
                "runner_custody_basis": (file_roll or {}).get("custody_basis"),
                "runner_specificity": (
                    {
                        "real_coverage": file_roll.get("real_coverage", 0),
                        "body_specific": file_roll.get("body_specific", 0),
                        "generic_unique": file_roll.get("generic_unique", 0),
                    }
                    if file_roll
                    else None
                ),
                "validator_command": organ.get("validator_command"),
                "receipt_count": len(receipts),
                "authority_receipt": organ.get("current_authority_receipt"),
            }
        )

    route_nodes: list[dict[str, Any]] = []
    organs_routed: set[str] = set()
    for route in route_rows:
        task_class = str(route.get("task_class") or "")
        if not task_class:
            continue
        fan_out = _route_organ_ids(route)
        route_nodes.append(
            {
                "task_class": task_class,
                "route_role": route.get("route_role"),
                "primary_organ_id": route.get("primary_organ_id"),
                "primary_display_name": route.get("primary_display_name"),
                "first_command": _screen_value(route.get("first_command"), leak_guard),
                "stop_condition": _screen_value(route.get("stop_condition"), leak_guard),
                "allowed_scope": _screen_value(route.get("allowed_scope"), leak_guard),
                "organ_count": len(fan_out),
            }
        )
        for organ_id, role in fan_out:
            organs_routed.add(organ_id)
            edges.append(
                {
                    "from_type": "route",
                    "from": task_class,
                    "to_type": "organ",
                    "to": organ_id,
                    "kind": "routes_to",
                    "role": role,
                }
            )

    family_nodes = [
        {"family_id": fam, "organ_count": count}
        for fam, count in sorted(family_counts.items())
    ]
    source_file_nodes = [
        {"path": path, **files[path]} for path in sorted(source_file_paths)
    ]
    custody_split: dict[str, int] = {}
    for node in source_file_nodes:
        basis = str(node.get("custody_basis") or "unknown")
        custody_split[basis] = custody_split.get(basis, 0) + 1
    edge_kind_counts: dict[str, int] = {}
    for edge in edges:
        edge_kind_counts[edge["kind"]] = edge_kind_counts.get(edge["kind"], 0) + 1

    # Resolved/deferred edge classes are COMPUTED from what was materialized, so a
    # rebuild from degraded inputs re-defers honestly instead of overclaiming.
    resolved_classes: list[str] = []
    deferred_classes: list[dict[str, str]] = []
    if claim_nodes and edge_kind_counts.get("asserts_claim"):
        resolved_classes.append(EDGE_CLASS_CLAIM)
    else:
        deferred_classes.append(
            {
                "edge_class": EDGE_CLASS_CLAIM,
                "missing": "first-class claim nodes with asserts_claim/validated_by/proven_by edges",
                "missing_source_class": "organ_registry_claim_fields_not_joined",
                "owner_path": "scripts/build_code_lens_join_index.py",
                "re_entry_command": (
                    "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py"
                    " --lens <python-lens --full snapshot>"
                ),
                "would_come_from": "rebuilding this join index with the organ registry plane",
            }
        )
    if route_nodes and edge_kind_counts.get("routes_to"):
        resolved_classes.append(EDGE_CLASS_ROUTE)
    else:
        deferred_classes.append(
            {
                "edge_class": EDGE_CLASS_ROUTE,
                "missing": "route nodes fanning one task-class entry across organs",
                "missing_source_class": "agent_task_routes_plane_absent_from_join_index",
                "owner_path": "scripts/build_code_lens_join_index.py",
                "re_entry_command": (
                    "PYTHONPATH=src python3 scripts/build_code_lens_join_index.py"
                    " --lens <python-lens --full snapshot> --routes atlas/agent_task_routes.json"
                ),
                "would_come_from": "rebuilding this join index with atlas/agent_task_routes.json",
            }
        )
    deferred_classes.append(dict(_PROOF_RESIDUAL))

    organ_id_set = {n["organ_id"] for n in organ_nodes}
    organs_reachable = organs_routed & organ_id_set
    route_targets_unknown = organs_routed - organ_id_set

    generated_from = {
        "python_lens": "python-lens --full symbol_capsule_rows + specificity_v3",
        "organ_registry": "core/organ_registry.json::implemented_organs",
    }
    if atlas_by:
        generated_from["organ_atlas"] = "core/organ_atlas.json::organs"
    if route_nodes:
        generated_from["agent_task_routes"] = "atlas/agent_task_routes.json::routes"

    return {
        "schema_version": SCHEMA_VERSION,
        "export_band": "presence_only",
        "source_bodies_exported": False,
        "generated_from": generated_from,
        "nodes": {
            "organ": organ_nodes,
            "source_file": source_file_nodes,
            "claim": claim_nodes,
            "route": route_nodes,
            "family": family_nodes,
        },
        "edges": edges,
        "graph": {
            "edge_kinds": sorted(edge_kind_counts),
            "edge_kind_counts": edge_kind_counts,
            "edge_semantics": {
                "proven_by": (
                    "the authority receipt that last established the bounded claim "
                    "within its ceiling; not domain-truth proof"
                ),
                "routes_to": (
                    "a task-class entry point whose fan-out includes the organ; "
                    "navigation, not execution order"
                ),
            },
            "resolved_edge_classes": sorted(resolved_classes),
            "deferred_edge_classes": deferred_classes,
            "atlas_plane_present": bool(atlas_by),
            "route_plane_present": bool(route_nodes),
            "leak_guard": leak_guard,
        },
        "rollup": {
            "organ_count": len(organ_nodes),
            "organs_with_resolved_runner_source": resolved,
            "source_file_node_count": len(source_file_nodes),
            "claim_node_count": len(claim_nodes),
            "route_node_count": len(route_nodes),
            "family_node_count": len(family_nodes),
            "organs_reachable_from_routes": len(organs_reachable),
            "route_targets_unknown": len(route_targets_unknown),
            "edge_count": len(edges),
            "runner_custody_split": custody_split,
        },
        "authority_ceiling": {
            "release_authorized": False,
            "source_body_export_authorized": False,
            "static_analysis_authority": False,
            "whole_system_correctness_authorized": False,
        },
        "non_goals": [
            "not a control-flow / data-flow graph",
            "not source-body export",
            "not release approval",
            "not whole-system correctness",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    """CLI: read a lens snapshot + organ registry, write the join index.

    - Teleology: expose join-index building as a re-runnable command for the
      Comprehension Plane refresh.
    - Guarantee: writes the join index JSON to --out and returns 0 on success;
      absent --atlas/--routes files degrade to a smaller graph (with the matching
      edge classes re-deferred) instead of failing.
    - Fails: SystemExit(2) on lens/registry load errors; SystemExit(3) on a
      source-body leak; argparse exits non-zero on missing required arguments.
    - Reads: --lens, --registry, and optionally --atlas, --routes.
    - Writes: the --out join index (parent dirs created).
    - Escalates-to: build_join_index for the graph shape.
    """
    parser = argparse.ArgumentParser(description="Build the code-lens join index v2.")
    parser.add_argument("--lens", required=True, type=Path, help="python-lens --full snapshot JSON")
    parser.add_argument(
        "--registry",
        type=Path,
        default=Path("core/organ_registry.json"),
        help="organ registry JSON",
    )
    parser.add_argument(
        "--atlas",
        type=Path,
        default=Path("core/organ_atlas.json"),
        help="organ atlas JSON (family/wires_to/doctrine plane; optional)",
    )
    parser.add_argument(
        "--routes",
        type=Path,
        default=Path("atlas/agent_task_routes.json"),
        help="agent task routes JSON (task_class route plane; optional)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("receipts/code_lens/code_lens_join_index_v0.json"),
    )
    args = parser.parse_args(argv)
    lens = _load_json(args.lens, "lens snapshot")
    registry = _load_json(args.registry, "organ registry")
    if not isinstance(lens, dict) or not isinstance(registry, dict):
        raise SystemExit("2: lens and registry must both be JSON objects")
    atlas = _load_json(args.atlas, "organ atlas") if args.atlas.is_file() else None
    routes = _load_json(args.routes, "agent task routes") if args.routes.is_file() else None
    index = build_join_index(lens, registry, atlas=atlas, routes=routes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n")
    rollup = index["rollup"]
    print(
        f"wrote {args.out}: {rollup['organ_count']} organs, "
        f"{rollup['organs_with_resolved_runner_source']} runner-resolved, "
        f"{rollup['claim_node_count']} claims, {rollup['route_node_count']} routes, "
        f"{rollup['edge_count']} edges; resolved="
        f"{','.join(index['graph']['resolved_edge_classes']) or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
