#!/usr/bin/env python3
"""
Implements scripts build code lens join index for the public Plectis package.

Callers enter through `build_join_index` and `main`; constants such as
`COUPLING_ZONE_MARKERS`, `SCHEMA_VERSION`, `_SECRET_SHAPE_RE`, `_PRIVATE_PATH_RE`, and 5
more pin local fixture names; dependencies include `argparse`, `json`, `re`, `pathlib`, and
1 more. Importing it does not authorize release work or hidden private-state access; those
effects live behind explicit calls.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from microcosm_core.component_index import validate_index as _validate_assurance_export, PUBLIC_TEXT_PATH_RE

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
_PRIVATE_PATH_RE = PUBLIC_TEXT_PATH_RE

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
    "owner_path": "scripts/build/build_code_lens_join_index.py",
    "blocked_on": "no Lean-aware proof-graph builder exists yet; see owner_path",
    "would_come_from": "a Lean-aware proof-graph builder feeding this join index",
}


def _load_json(path: Path, label: str) -> Any:
    """
    Load load JSON for `scripts.build.build_code_lens_join_index`.

    Input comes from `path` and `label`; malformed or missing data follows the exceptions
    and checks visible in the body.
    """
    if not path.is_file():
        raise SystemExit(f"2: {label} not found: {path}")
    try:
        return json.loads(path.read_text())
    except (ValueError, OSError) as exc:
        raise SystemExit(f"2: {label} unparseable: {path}: {exc}")


def _capsule_rows(lens: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Produce the capsule rows value used by `scripts.build.build_code_lens_join_index`.

    Inputs are `lens`; notable helpers are `get`.
    """
    rows = lens.get("symbol_capsule_rows")
    return rows if isinstance(rows, list) else []


def _custody_basis(path: str) -> str:
    """
    Produce the custody basis value used by `scripts.build.build_code_lens_join_index`.

    Inputs are `path`.
    """
    return (
        "directory_coupling_marker"
        if any(marker in path for marker in COUPLING_ZONE_MARKERS)
        else "owned"
    )


def _file_rollups(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """
    Return file rollups for the scripts build code lens join index flow.

    Inputs are `rows`; notable helpers are `setdefault`, `get`, and `_custody_basis`.
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
    """
    Compute resolved ref strings from `rows`.

    Inputs are `rows`; notable helpers are `append` and `get`.
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
    """
    Produce the screen value value used by `scripts.build.build_code_lens_join_index`.

    Inputs are `value` and `guard`; notable helpers are `search` and `get`.
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
    """
    Serialize `scripts.build.build_code_lens_join_index._claim_node` into the payload shape
    expected by scripts build code lens join index.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
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
    """
    Produce the route rows value used by `scripts.build.build_code_lens_join_index`.

    Inputs are `routes_doc`; notable helpers are `get`.
    """
    rows = (routes_doc or {}).get("routes") if isinstance(routes_doc, dict) else None
    return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []


def _route_organ_ids(route: dict[str, Any]) -> list[tuple[str, str]]:
    """
    Return route organ IDs for the scripts build code lens join index flow.

    Inputs are `route`; notable helpers are `get`, `append`, and `add`.
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
    """
    Return runner source ref for the scripts build code lens join index flow.

    Inputs are `runner`; notable helpers are `startswith` and `replace`.
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
    """
    Compute graph edges for organ from `organ_id` and `atlas_row`.

    Inputs are `organ_id` and `atlas_row`; notable helpers are `get`, `append`, and
    `_resolved_ref_strings`.
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
    """
    Compute claim edges from `claim`.

    Inputs are `claim`; notable helpers are `get` and `append`.
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
    *, assurance: dict[str, Any] | None = None,
    capsules: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Serialize `scripts.build.build_code_lens_join_index.build_join_index` into the payload shape
    expected by scripts build code lens join index.

    The mapping keys match the receipts, cards, or tests that consume this value downstream.
    """
    if capsules is not None and atlas is not None:
        from microcosm_core.component_descriptions import enrich_description_atlas, enrich_organ_route_rows
        atlas = enrich_description_atlas(atlas, capsules)
        routes = enrich_organ_route_rows(routes, atlas) if routes is not None else None
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
                "owner_path": "scripts/build/build_code_lens_join_index.py",
                "re_entry_command": (
                    "PYTHONPATH=src python3 scripts/build/build_code_lens_join_index.py"
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
                "owner_path": "scripts/build/build_code_lens_join_index.py",
                "re_entry_command": (
                    "PYTHONPATH=src python3 scripts/build/build_code_lens_join_index.py"
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
    if capsules is not None:
        generated_from["component_descriptions"] = "core/paper_module_capsules.json::compression"
    if route_nodes:
        generated_from["agent_task_routes"] = "atlas/agent_task_routes.json::routes"

    result = {
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
    return result if assurance is None else extend_claim_index(result, registry, atlas or {}, assurance)


def refresh_navigation(index: dict[str, Any]) -> dict[str, Any]:
    """Refresh this builder's route in a saved index without reasserting source evidence.

    The original lens snapshot may be unavailable in a public clone. Only the
    owned navigation pointer changes; graph edges and source evidence stay intact.
    """
    import copy

    result = copy.deepcopy(index)
    for row in result.get("graph", {}).get("deferred_edge_classes", []):
        if row.get("owner_path") == "scripts/build_code_lens_join_index.py":
            row["owner_path"] = "scripts/build/build_code_lens_join_index.py"
    return result


# This fragment is assembled into the EXISTING join-index builder in candidate/.
import ast
import copy
import hashlib
import math
import shlex
from pathlib import PurePosixPath

ASSURANCE_SCHEMA = "microcosm_claim_assurance_v1"
ASSURANCE_INDEX_SCHEMA = "microcosm_code_lens_join_index_v3"
CONTRACT_SCHEMA = "plectis_formal_contract_v1"
_PUBLIC_ID = re.compile(r"[a-z][a-z0-9_]*\Z")
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _unique(rows, key, label):
    if type(rows) is not list:
        raise ValueError(label + " must be a row list")
    result = {}
    for row in rows:
        identity = row.get(key) if type(row) is dict else None
        if type(identity) is not str or not identity or identity in result:
            raise ValueError("invalid or duplicate " + label)
        result[identity] = row
    return result


def _same_ids(expected, actual, label):
    if set(expected) != set(actual):
        raise ValueError(label + " does not cover the registered universe exactly")


def _public(value):
    if isinstance(value, str):
        masked = value.replace("<run>", "RUN").replace("<slug>", "SLUG")
        if _SECRET_SHAPE_RE.search(value) or _PRIVATE_PATH_RE.search(masked):
            raise ValueError("unsafe public index text")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("non-finite public index number")
    elif isinstance(value, dict):
        for key, child in value.items():
            _public(key)
            _public(child)
    elif isinstance(value, list):
        for child in value:
            _public(child)


def _text(value, label, maximum=1200):
    if type(value) is not str or not value.strip() or len(value) > maximum:
        raise ValueError("missing or oversized compact " + label)
    _public(value)
    return value


def _claim_digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _ref_parts(reference):
    if type(reference) is not str or not reference:
        raise ValueError("invalid public reference")
    _public(reference)
    path, separator, symbol = reference.partition("::" if "::" in reference else "#")
    pure = PurePosixPath(path)
    if (not path or pure.is_absolute() or str(pure) != path or ".." in pure.parts
            or "\\" in path or ":" in path or any(ord(c) < 32 for c in reference)
            or (separator and not symbol)):
        raise ValueError("escaping or malformed public reference")
    return path, symbol


def _primary_guides(atlas_by, capsules):
    from microcosm_core.component_descriptions import resolve_component_capsules
    # Assurance requires the explicit primary pointer, even where the shared
    # description reader supports a historical direct-ID compatibility route.
    if any(not row.get("paper_module_ref") for row in atlas_by.values()):
        raise ValueError("primary guide pointer must be explicit")
    resolved = resolve_component_capsules(list(atlas_by.values()), capsules.get("paper_modules"))
    return {organ_id: pair[0] for organ_id, pair in resolved.items()}


def _strict_json(path, *, root=None):
    def object_pairs(pairs):
        value = {}
        for key, child in pairs:
            if key in value:
                raise ValueError("duplicate source JSON key")
            value[key] = child
        return value

    def constant(_value):
        raise ValueError("non-finite source JSON")

    data = (_bounded_file(root, path.relative_to(root).as_posix()) if root is not None
            else path.read_bytes())
    return json.loads(data.decode("utf-8"), object_pairs_hook=object_pairs,
                      parse_constant=constant)


def _bounded_file(root, relative):
    path = root / relative
    if not path.resolve().is_relative_to(root):
        raise ValueError("escaping source reference")
    current = path
    while current != root:
        if current.is_symlink():
            raise ValueError("linked source reference")
        current = current.parent
    if not path.is_file() or path.stat().st_size > 4_000_000:
        raise ValueError("missing or oversized required reference: " + relative)
    return path.read_bytes()


def _reference_fact(root, reference, *, required=True, source_tokens=None):
    relative, symbol = _ref_parts(reference)
    path = root / relative
    try:
        if not required and not symbol and path.is_file():
            # Historical receipt availability is navigation evidence. Do not
            # read its payload or imply that its old pass is current.
            if not path.resolve().is_relative_to(root) or any(
                    p.is_symlink() for p in (path, *path.parents) if p != root):
                raise ValueError("linked historical reference")
            return {"ref": reference, "path": relative, "kind": "historical_asset",
                    "availability": "available", "href": relative,
                    "identity_status": "not_read_by_index"}
        if path.is_dir() and not symbol:
            if not path.resolve().is_relative_to(root) or any(
                    p.is_symlink() for p in (path, *path.parents) if p != root):
                raise ValueError("linked or escaping input directory")
            return {"ref": reference, "path": relative, "kind": "directory",
                    "availability": "available", "href": relative}
        data = _bounded_file(root, relative)
    except ValueError:
        if required or path.exists() or path.is_symlink():
            raise
        return {"ref": reference, "original_ref": reference, "kind": "historical_asset",
                "availability": "unavailable", "reason": "not included in this checkout"}
    if symbol:
        text = data.decode("utf-8")
        symbol_kind = None
        if path.suffix == ".py":
            tree = ast.parse(text)
            names = {n.name for n in ast.walk(tree)
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
            names.update(n.id for n in ast.walk(tree)
                         if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
            functions = {node.name for node in ast.walk(tree)
                         if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
            symbol_kind = "python_function" if symbol in functions else "python_name"
            if "::" in reference:
                tests = {node.name for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                         and node.name.startswith("test_")}
                if not relative.startswith("tests/") or symbol not in tests:
                    raise ValueError("test reference is not a collectable pytest function")
                symbol_kind = "test_function"
        elif path.suffix == ".dfy" and source_tokens:
            names = set(re.findall(r"\b(?:lemma|method|function|predicate)\s+(?:\{\s*:[^}]*\}\s*)*(\w+)",
                                   source_tokens(text)))
        elif relative == "core/paper_module_capsules.json":
            names = {row["id"] for row in json.loads(text)["paper_modules"]}
        else:
            raise ValueError("unsupported named reference: " + reference)
        if symbol not in names:
            raise ValueError("dangling named reference: " + reference)
    fact = {"ref": reference, "path": relative, "kind": "file", "availability": "available",
            "href": relative, "sha256": hashlib.sha256(data).hexdigest()}
    if symbol:
        fact["symbol"] = symbol
        if symbol_kind:
            fact["symbol_kind"] = symbol_kind
    return fact


def _read_replay_descriptors(root, registry_by):
    """Read existing route constants and native overrides as AST; execute no code."""
    shell_path = "src/microcosm_core/runtime_shell.py"
    shell = ast.parse(_bounded_file(root, shell_path).decode("utf-8"))
    declarations = [node for node in shell.body if isinstance(node, ast.AnnAssign)
                    and isinstance(node.target, ast.Name) and node.target.id == "RUNTIME_STEPS"]
    if len(declarations) != 1 or not isinstance(declarations[0].value, ast.Tuple):
        raise ValueError("unrecognized replay configuration")

    def constant(node, names, active=()):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name) and node.id in names and node.id not in active:
            return constant(names[node.id], names, (*active, node.id))
        if isinstance(node, ast.JoinedStr):
            parts = []
            for part in node.values:
                if isinstance(part, ast.FormattedValue) and part.format_spec is None and part.conversion == -1:
                    parts.append(str(constant(part.value, names, active)))
                elif isinstance(part, ast.Constant) and type(part.value) is str:
                    parts.append(part.value)
                else:
                    raise ValueError("unsupported native receipt expression")
            return "".join(parts)
        raise ValueError("unsupported native receipt constant")

    def runner_ref(node, organ_id, aliases=None):
        if isinstance(node, ast.Call):
            if (not isinstance(node.func, ast.Name) or node.func.id != "_keyword_command_runner"
                    or len(node.args) != 1 or node.keywords):
                raise ValueError("unknown replay runner wrapper")
            node = node.args[0]
        if not isinstance(node, ast.Attribute) or not isinstance(node.value, ast.Name):
            raise ValueError("unknown replay runner reference")
        module = registry_by[organ_id]["runner"]
        # RuntimeShell's registry-created lazy binding uses organ IDs as aliases;
        # pattern_assimilation_step intentionally resolves to validators.acceptance.
        expected = ("microcosm_core.organs." + aliases[node.value.id]
                    if aliases else module if node.value.id == organ_id else None)
        if module != expected:
            raise ValueError("replay runner differs from registry module")
        return "src/" + module.replace(".", "/") + ".py#" + node.attr

    descriptors = []
    for call in declarations[0].value.elts:
        if (not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name)
                or call.func.id != "RuntimeStep" or call.args):
            raise ValueError("unknown runtime step declaration")
        fields = {kw.arg: kw.value for kw in call.keywords}
        if set(fields) != {"organ_id", "span", "input_mode", "example_rel", "runner", "receipt_name"}:
            raise ValueError("incomplete runtime step")
        values = {key: ast.literal_eval(value) for key, value in fields.items() if key != "runner"}
        organ_id = values["organ_id"]
        if organ_id not in registry_by:
            raise ValueError("unknown replay component")
        values["runner_ref"] = runner_ref(fields["runner"], organ_id)
        values["configuration_refs"] = [shell_path + "#RUNTIME_STEPS",
                                         shell_path + "#_accepted_organ_runner_module_refs"]
        values["native_witness_requested"] = False
        descriptors.append(values)
    by_id = _unique(descriptors, "organ_id", "replay descriptors")
    _same_ids(registry_by, by_id, "replay descriptors")
    replay_path = "src/microcosm_core/component_replay.py"
    replay = ast.parse(_bounded_file(root, replay_path).decode("utf-8"))
    native = next(node for node in replay.body if isinstance(node, ast.FunctionDef)
                  and node.name == "native_replay_step")
    for branch in native.body:
        if not isinstance(branch, ast.If):
            continue
        condition = branch.test
        if (not isinstance(condition, ast.Compare) or len(condition.ops) != 1
                or not isinstance(condition.ops[0], ast.Eq)
                or ast.unparse(condition.left) != "step.organ_id"):
            raise ValueError("unknown native replay selection")
        organ_id = ast.literal_eval(condition.comparators[0])
        if organ_id not in by_id:
            raise ValueError("native override targets unknown component")
        aliases = {}
        for node in branch.body:
            if isinstance(node, ast.ImportFrom) and node.module == "microcosm_core.organs":
                aliases.update({alias.asname or alias.name: alias.name for alias in node.names})
        returned = [n for n in branch.body if isinstance(n, ast.Return)]
        if (len(returned) != 1 or not isinstance(returned[0].value, ast.Call)
                or ast.unparse(returned[0].value.func) != "replace"):
            raise ValueError("unknown native replay override")
        row = by_id[organ_id]
        row["declared_route"] = {key: row[key] for key in ("example_rel", "input_mode", "runner_ref", "receipt_name")}
        for keyword in returned[0].value.keywords:
            if keyword.arg == "runner":
                row["runner_ref"] = runner_ref(keyword.value, organ_id, aliases)
            elif keyword.arg == "receipt_name" and isinstance(keyword.value, ast.Attribute):
                owner = aliases[keyword.value.value.id]
                tree = ast.parse(_bounded_file(root, "src/microcosm_core/organs/" + owner + ".py").decode("utf-8"))
                named = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
                         for target in node.targets if isinstance(target, ast.Name)}
                if keyword.value.attr not in named:
                    raise ValueError("unknown native receipt constant")
                row["receipt_name"] = constant(named[keyword.value.attr], named)
            elif keyword.arg in {"example_rel", "input_mode"}:
                row[keyword.arg] = ast.literal_eval(keyword.value)
            else:
                raise ValueError("unknown native replay field")
        row["native_witness_requested"] = True
        row["configuration_refs"].append(replay_path + "#native_replay_step")
    return descriptors


def collect_claim_assurance_inputs(root, registry, atlas, *, proof_tools, metadata_proposals=None, include_explorer=True):
    """Bounded file/AST validation, distinct from the pure index join below.

    metadata_proposals is an external prototype seam. Every proposed metadata
    file must equal its current owner except for the optional contract block.
    Production CLI reads contract blocks from their adjacent metadata owners.
    """
    root = Path(root).resolve()
    if registry != _strict_json(root / "core/organ_registry.json", root=root):
        raise ValueError("registry input differs from its canonical source owner")
    if atlas != _strict_json(root / "core/organ_atlas.json", root=root):
        raise ValueError("atlas collection input must be its raw canonical source document")
    registry_by = _unique(registry.get("implemented_organs"), "organ_id", "components")
    atlas_by = _unique(atlas.get("organs"), "organ_id", "atlas")
    _same_ids(registry_by, atlas_by, "atlas")
    evidence = _strict_json(root / "core/organ_evidence_classes.json", root=root)
    capsules = _strict_json(root / "core/paper_module_capsules.json", root=root)
    guides = _primary_guides(atlas_by, capsules)
    proof_api = proof_tools
    kernels = proof_api["discover"](root)
    if metadata_proposals is not None and set(metadata_proposals) - set(kernels):
        raise ValueError("metadata proposal targets unknown kernel")
    for slug, proposed in (metadata_proposals or {}).items():
        current = proof_api["_read_json"](root / "formal/components" / slug / "metadata.json")
        if {key: value for key, value in proposed.items() if key != "contract"} != {
                key: value for key, value in current.items() if key != "contract"}:
            raise ValueError("stale metadata proposal before collection: " + slug)
    facts = {}
    file_hashes = {}

    def reference(ref, required=True):
        if ref in facts:
            if required and facts[ref]["availability"] != "available":
                raise ValueError("required reference was unavailable")
            return
        fact = _reference_fact(root, ref, required=required, source_tokens=proof_api["_source_tokens"])
        if fact.get("kind") == "file":
            previous = file_hashes.setdefault(fact["path"], fact["sha256"])
            if previous != fact["sha256"]:
                raise ValueError("reference changed during collection")
        facts[ref] = fact

    owner_refs = ["core/organ_registry.json", "core/organ_evidence_classes.json", "core/organ_atlas.json",
                  "core/paper_module_capsules.json"]
    for ref in owner_refs:
        reference(ref)

    def historical_header(ref):
        fact = facts.get(ref)
        header = {"artifact_ref": ref, "artifact_sha256": None,
                  "availability": fact["availability"] if fact else "unavailable",
                  "recorded_status": None, "created_at": None, "input_mode": None,
                  "native_observations": {"lean_available": None, "lake_available": None,
                                          "execution_witness_mode": None, "verification_performed": None},
                  "recorded_source_hashes": {}, "freshness": "historical_saved_artifact",
                  "source_binding": "not_checked_against_current_replay"}
        if not fact or fact["availability"] != "available":
            return header
        data = _bounded_file(root, _ref_parts(ref)[0])
        digest = hashlib.sha256(data).hexdigest()
        facts[ref] = {"ref": ref, "path": _ref_parts(ref)[0], "kind": "file", "availability": "available",
                      "href": _ref_parts(ref)[0], "sha256": digest}
        header["artifact_sha256"] = digest
        try:
            value = json.loads(data.decode("utf-8"))
        except (ValueError, UnicodeError):
            return header
        if type(value) is not dict:
            return header
        for key in ("status", "created_at", "input_mode"):
            if type(value.get(key)) is str and len(value[key]) <= 200:
                header["recorded_status" if key == "status" else key] = value[key]
        tools = value.get("tool_versions")
        if type(tools) is dict:
            for key in ("lean_available", "lake_available"):
                if type(tools.get(key)) is bool:
                    header["native_observations"][key] = tools[key]
        if type(value.get("execution_witness_mode")) is str and len(value["execution_witness_mode"]) <= 200:
            header["native_observations"]["execution_witness_mode"] = value["execution_witness_mode"]
        if type(value.get("verification_performed")) is bool:
            header["native_observations"]["verification_performed"] = value["verification_performed"]
        for key in ("source_sha256", "source_digest"):
            if type(value.get(key)) is str and _SHA256.fullmatch(value[key]):
                header["recorded_source_hashes"][key] = value[key]
        _public(header)
        return header

    replays = _read_replay_descriptors(root, registry_by)
    for organ_id, organ in registry_by.items():
        reference(guides[organ_id]["legacy_markdown_projection"])
        reference("src/" + organ["runner"].replace(".", "/") + ".py")
        for ref in set([organ["current_authority_receipt"], *organ["generated_receipts"]]):
            reference(ref, required=False)
        if organ.get("historical_source_authority_receipt"):
            reference(organ["historical_source_authority_receipt"], required=False)
    reference("scripts/check/check_component_replays.py")
    reference("Makefile")
    makefile = _bounded_file(root, "Makefile").decode("utf-8")
    declared_prerequisites = re.search(r"make component-replays\s+freshly replay[^\n]*\(([^)]*)\)", makefile)
    replay_prerequisites = ({"description": declared_prerequisites.group(1), "source_ref": "Makefile",
                             "availability_status": "not_assessed_by_index"}
                            if declared_prerequisites else {"status": "unrecorded", "source_ref": "Makefile"})
    for replay in replays:
        reference(replay["runner_ref"])
        reference(replay["example_rel"])
        if "declared_route" in replay:
            reference(replay["declared_route"]["runner_ref"])
            reference(replay["declared_route"]["example_rel"])
        for ref in replay["configuration_refs"]:
            reference(ref)
    historical_results, native_records = {}, {}
    for organ_id, organ in registry_by.items():
        historical_results[organ_id] = historical_header(organ["current_authority_receipt"])
        native_records[organ_id] = []
        if organ["evidence_class"] != "external_subprocess_witness":
            continue
        for ref in sorted(set([organ["current_authority_receipt"], *organ["generated_receipts"]])):
            header = historical_header(ref)
            observed = header["native_observations"]
            if ((observed["lean_available"] is True and observed["lake_available"] is True)
                    or (observed["execution_witness_mode"] == "live_lean_subprocess_verified"
                        and observed["verification_performed"] is True)):
                native_records[organ_id].append(header)
    proof_rows = []
    for slug, module in sorted(kernels.items()):
        metadata = proof_api["check_binding"](root, slug, module)
        selected = (metadata_proposals or {}).get(slug, metadata)
        if {key: value for key, value in selected.items() if key != "contract"} != {
                key: value for key, value in metadata.items() if key != "contract"}:
            raise ValueError("stale metadata proposal: " + slug)
        contract = selected.get("contract")
        if contract is None:
            continue
        prefix = "formal/components/" + slug + "/"
        generated = "src/plectis/components/" + slug + "/_generated/"
        references = [prefix + "metadata.json", prefix + metadata["source"],
                      "scripts/check/check_component_kernels.py#check_binding",
                      *[generated + name for name in metadata["generated_python"]],
                      "src/plectis/components/" + slug + "/_adapter.py",
                      "src/plectis/components/" + slug + "/__init__.py",
                      "src/plectis/components/_bridge.py", "src/plectis/components/_worker.py",
                      "src/plectis/_sealed_kernel.py", contract["formal_readme_ref"],
                      *contract["specification_refs"], *contract["entry_theorem_refs"],
                      *contract["mutant_refs"], contract["positive_test_ref"],
                      contract["adversarial_test_ref"]]
        for binding in contract["component_bindings"]:
            references += [*binding["runtime_refs"], *binding["test_refs"], binding["primary_guide_ref"]]
        for ref in references:
            reference(ref)
        proof_rows.append({"slug": slug, "module": module, "metadata": metadata,
                           "contract": copy.deepcopy(contract), "descriptor_origin":
                           "proposed_metadata_contract" if slug in (metadata_proposals or {}) else "metadata_contract"})
    inputs = {"schema_version": ASSURANCE_SCHEMA, "evidence_classes": evidence,
            "capsules": capsules, "replays": replays, "proofs": proof_rows, "references": facts,
            "owner_refs": owner_refs, "replay_prerequisites": replay_prerequisites,
            "historical_results": historical_results, "historical_native_records": native_records}
    if include_explorer:
        from microcosm_core.projections.component_explorer_metadata import collect_explorer_metadata
        from microcosm_core.projections.component_proof_excerpts import build_proof_enrichments
        from microcosm_core.projections.component_workflow_cores import build_workflow_cores, build_ownership_counterexample
        explorer = collect_explorer_metadata(root)
        explorer.update(schema_version="plectis_component_explorer_v1",
                        proof_details={"proof::dafny::" + row["slug"]: build_proof_enrichments(root, row["metadata"])
                                       for row in proof_rows},
                        cores=build_workflow_cores(root), ownership_example=build_ownership_counterexample(root))
        annotations_path = root / "core/component_claim_annotations.json"
        annotations = (_strict_json(annotations_path, root=root) if annotations_path.exists()
                       else {"schema_version": "plectis_component_annotations_v1",
                             "requirements_reviews": [], "claim_clause_coverage": []})
        if (type(annotations) is not dict or set(annotations) != {
                "schema_version", "requirements_reviews", "claim_clause_coverage"}
                or annotations["schema_version"] != "plectis_component_annotations_v1"):
            raise ValueError("invalid component claim annotation owner")
        explorer.update({key: annotations[key] for key in ("requirements_reviews", "claim_clause_coverage")})
        inputs["explorer"] = explorer
    return inputs


def extend_claim_index(base, registry, atlas, assurance):
    """Pure fail-closed join; performs no file reads, prover calls or runner imports."""
    if (base.get("schema_version") != SCHEMA_VERSION or assurance.get("schema_version") != ASSURANCE_SCHEMA
            or base.get("source_bodies_exported") is not False):
        raise ValueError("unsupported assurance input schema or source body export")
    if set(base) != {"schema_version", "export_band", "source_bodies_exported", "generated_from", "nodes",
                     "edges", "graph", "rollup", "authority_ceiling", "non_goals"}:
        raise ValueError("unknown base-index payload fields")
    node_fields = {
        "source_file": {"path", "source_class", "custody_basis", "symbol_count", "real_coverage", "body_specific", "generic_unique", "has_non_goal"},
        "claim": {"claim_id", "organ_id", "claim_ceiling", "claim_ceiling_restated", "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "validator_command", "authority_receipt"},
        "organ": {"organ_id", "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "real_substrate_disposition", "claim_ceiling", "status", "family", "runner_module", "runner_source_ref", "runner_source_resolved", "runner_custody_basis", "runner_specificity", "validator_command", "receipt_count", "authority_receipt"},
        "route": {"task_class", "route_role", "primary_organ_id", "primary_display_name", "first_command", "stop_condition", "allowed_scope", "organ_count"},
        "family": {"family_id", "organ_count"},
    }
    if set(base["nodes"]) != set(node_fields) or any(
            type(row) is not dict or set(row) - fields
            for kind, fields in node_fields.items() for row in base["nodes"][kind]):
        raise ValueError("unknown base node payload or body fields")
    registry_by = _unique(registry.get("implemented_organs"), "organ_id", "components")
    if not registry_by or any(not _PUBLIC_ID.fullmatch(oid) for oid in registry_by):
        raise ValueError("invalid registered component universe")
    atlas_by = _unique(atlas.get("organs"), "organ_id", "atlas")
    classes = assurance["evidence_classes"]
    class_by = _unique(classes.get("organ_evidence_classes"), "organ_id", "evidence classes")
    replay_by = _unique(assurance.get("replays"), "organ_id", "replay descriptors")
    result = copy.deepcopy(base)
    organ_by = _unique(result["nodes"].get("organ"), "organ_id", "base components")
    claim_by = _unique(result["nodes"].get("claim"), "organ_id", "base claims")
    for rows, label in ((atlas_by, "atlas"), (class_by, "evidence classes"),
                        (replay_by, "replays"), (organ_by, "base components"), (claim_by, "base claims")):
        _same_ids(registry_by, rows, label)
    guides = _primary_guides(atlas_by, assurance["capsules"])
    facts = assurance["references"]

    def asset(ref, required=True):
        _ref_parts(ref)
        fact = facts.get(ref)
        if type(fact) is not dict or fact.get("ref") != ref:
            raise ValueError("dangling reference fact: " + ref)
        if fact.get("availability") == "unavailable":
            if (required or set(fact) != {"ref", "original_ref", "kind", "availability", "reason"}
                    or fact.get("kind") != "historical_asset" or fact.get("original_ref") != ref
                    or not fact.get("reason")):
                raise ValueError("required asset unavailable: " + ref)
        elif (fact.get("availability") != "available" or fact.get("href") != _ref_parts(ref)[0]
              or fact.get("path") != _ref_parts(ref)[0] or fact.get("kind") not in {"file", "directory", "historical_asset"}
              or set(fact) - {"ref", "path", "kind", "availability", "href", "sha256", "symbol", "symbol_kind", "identity_status"}
              or fact.get("symbol", "") != _ref_parts(ref)[1]
              or (fact.get("kind") == "file" and not _SHA256.fullmatch(str(fact.get("sha256"))))
              or (fact.get("kind") == "historical_asset" and fact.get("identity_status") != "not_read_by_index")):
            raise ValueError("invalid available asset fact")
        return ref

    def test_asset(ref):
        asset(ref)
        if "::" not in ref or facts[ref].get("symbol_kind") != "test_function":
            raise ValueError("formal test reference is not a pytest function")
        return ref

    for ref in facts:
        asset(ref, required=facts[ref].get("availability") != "unavailable")

    endpoint_ids = {"organ": set(registry_by), "claim": {"claim::" + oid for oid in registry_by},
                    "route": set(_unique(result["nodes"]["route"], "task_class", "base routes")),
                    "family": set(_unique(result["nodes"]["family"], "family_id", "base families")),
                    "source_file": set(_unique(result["nodes"]["source_file"], "path", "base source files")),
                    "receipt": {ref for organ in registry_by.values() for ref in [organ["current_authority_receipt"], *organ["generated_receipts"],
                                *([organ["historical_source_authority_receipt"]] if organ.get("historical_source_authority_receipt") else [])]},
                    "validator_command": {organ["validator_command"] for organ in registry_by.values()},
                    "doctrine_ref": {edge["to"] for oid, row in atlas_by.items() for edge in _graph_edges_for_organ(oid, row) if edge["to_type"] == "doctrine_ref"}}
    edge_types = {"asserts_claim": ("organ", "claim"), "emits_receipt": ("organ", "receipt"),
                  "implemented_by_runner": ("organ", "source_file"), "member_of_family": ("organ", "family"),
                  "wires_to": ("organ", "organ"), "grounded_in_doctrine": ("organ", "doctrine_ref"),
                  "validated_by": ("claim", "validator_command"), "proven_by": ("claim", "receipt"),
                  "routes_to": ("route", "organ")}
    seen_edges = set()
    for old_edge in result["edges"]:
        if (set(old_edge) - {"from_type", "from", "to_type", "to", "kind", "ref_kind", "role"}
                or edge_types.get(old_edge.get("kind")) != (old_edge.get("from_type"), old_edge.get("to_type"))
                or old_edge.get("from") not in endpoint_ids.get(old_edge.get("from_type"), set())
                or old_edge.get("to") not in endpoint_ids.get(old_edge.get("to_type"), set())):
            raise ValueError("unknown or dangling typed graph endpoint")
        identity = json.dumps(old_edge, sort_keys=True)
        if identity in seen_edges:
            raise ValueError("duplicate graph edge")
        seen_edges.add(identity)
    additions = {"guide": {}, "replay": {}, "subclaim": {}, "specification": {}, "proof": {}}
    ignored_cache_fields = []

    def edge(from_type, source, to_type, target, kind):
        result["edges"].append({"from_type": from_type, "from": source,
                                "to_type": to_type, "to": target, "kind": kind})

    for organ_id, organ in registry_by.items():
        claim = claim_by[organ_id]
        if claim.get("claim_id") != "claim::" + organ_id:
            raise ValueError("claim identity changed")
        expected_claim = _claim_node(organ, atlas_by[organ_id], {"values_dropped": 0})
        changed_claim_fields = sorted(key for key in expected_claim if key != "claim_ceiling_restated"
                                      and claim.get(key) != expected_claim[key])
        if changed_claim_fields:
            ignored_cache_fields.append({"organ_id": organ_id, "node_type": "claim", "fields": changed_claim_fields})
        # The saved index is a retained lens snapshot, never a registry or
        # evidence authority. Rebuild all canonical fields instead of carrying
        # historical classes/receipt targets into current claim views.
        claim.clear()
        claim.update(expected_claim)
        claim["claim_ceiling_restated"] = _text(guides[organ_id]["compression"]["authority_ceiling"],
                                                 "canonical descriptive claim ceiling", 2400)
        expected_organ = {key: organ.get(key) for key in (
            "evidence_class", "evidence_strength_rank", "truth_accounting_bucket", "real_substrate_disposition",
            "claim_ceiling", "status", "validator_command")}
        expected_organ.update(family=atlas_by[organ_id].get("family"), runner_module=organ["runner"],
                              runner_source_ref=_runner_source_ref(organ["runner"]),
                              receipt_count=len(organ["generated_receipts"]),
                              authority_receipt=organ["current_authority_receipt"])
        changed_organ_fields = sorted(key for key, value in expected_organ.items() if organ_by[organ_id].get(key) != value)
        if changed_organ_fields:
            ignored_cache_fields.append({"organ_id": organ_id, "node_type": "organ", "fields": changed_organ_fields})
        organ_by[organ_id].update(expected_organ)
        evidence_class = organ["evidence_class"]
        if (evidence_class != class_by[organ_id]["evidence_class"]
                or evidence_class not in classes["class_profiles"]):
            raise ValueError("evidence class join mismatch")
        capsule = guides[organ_id]
        guide_ref = asset(capsule["legacy_markdown_projection"])
        guide_id = capsule["id"]
        additions["guide"][guide_id] = {"guide_id": guide_id, "ref": guide_ref}
        replay = copy.deepcopy(replay_by[organ_id])
        replay_id = "replay::" + organ_id
        replay["replay_id"] = replay_id
        replay["input_ref"] = asset(replay.pop("example_rel"))
        asset(replay["runner_ref"])
        if "declared_route" in replay:
            asset(replay["declared_route"]["runner_ref"])
            asset(replay["declared_route"]["example_rel"])
        if (type(replay["receipt_name"]) is not str or not replay["receipt_name"]
                or replay["receipt_name"] in {".", ".."}
                or any(c in replay["receipt_name"] for c in "/\\:#")
                or any(ord(c) < 32 for c in replay["receipt_name"])):
            raise ValueError("escaping fresh receipt name")
        replay.update(command="make component-replays", command_scope="all registered components",
                      command_ref="scripts/check/check_component_replays.py",
                      fresh_receipt_template=".microcosm/component-replays/<run>/" + organ_id + "/" + replay["receipt_name"],
                      execution_status="not_run_by_index", prerequisites_status="not_assessed_by_index")
        replay["prerequisites_ref"] = "Makefile"
        replay["declared_prerequisites"] = assurance["replay_prerequisites"]
        replay["guide_example"] = {"command": _text(atlas_by[organ_id]["first_command"], "guide command", 1600),
                                   "source_ref": "core/organ_atlas.json",
                                   "source_field": "organs[" + organ_id + "].first_command",
                                   "scope": "verbatim historical Atlas example; not an execution request and may target retained receipt paths",
                                   "usage": "verbatim_source_example_only",
                                   "writes_retained_receipts": None,
                                   "prerequisites_description": {"status": "unrecorded", "see": guide_ref},
                                   "expected_result_description": {"status": "unrecorded"}}
        try:
            tokens = shlex.split(replay["guide_example"]["command"])
            outputs = [tokens[i + 1] for i, token in enumerate(tokens[:-1]) if token == "--out"]
            outputs += [token.split("=", 1)[1] for token in tokens if token.startswith("--out=")]
            if outputs:
                replay["guide_example"]["writes_retained_receipts"] = any(
                    value.startswith(("receipts/", "state/")) for value in outputs)
        except ValueError:
            pass  # Source-only historical text is never dispatched as a command.
        replay["primary_execution"] = {"kind": "fixed_component_replay_api", "organ_id": organ_id,
                                        "argv": ["plectis", "component-replay", organ_id],
                                        "scope": "single_registered_component",
                                        "output_policy": "fresh ignored .microcosm/component-replays run under selected checkout",
                                        "input_override_supported": False,
                                        "implementation_state": "companion_external_backend_proposal",
                                        "worker_schema": "plectis_component_replay_worker_v1"}
        replay["last_result"] = assurance["historical_results"][organ_id]
        replay["last_result_selection"] = "registry current_authority_receipt; not a search for latest ignored run"
        additions["replay"][replay_id] = replay
        authority = asset(organ["current_authority_receipt"], required=False)
        historical = [asset(ref, required=False) for ref in organ["generated_receipts"]]
        if organ.get("historical_source_authority_receipt"):
            historical.append(asset(organ["historical_source_authority_receipt"], required=False))
        claim["card"] = {"title": _text(capsule["title"], "title", 160),
                         "summary": _text(capsule["compression"]["one_line"], "summary", 400),
                         "primary_guide_id": guide_id, "primary_guide_ref": guide_ref,
                         "registered_runner_ref": asset("src/" + organ["runner"].replace(".", "/") + ".py"),
                         "replay_id": replay_id, "formal_subclaim_ids": [],
                         "evidence": {"evidence_class": evidence_class,
                                      "authority_receipt_ref": authority,
                                      "authority_availability": facts[authority]["availability"],
                                      "receipt_time_basis": "historical_saved_artifact",
                                      "historical_receipt_refs": historical,
                                      "fresh_run_status": "not_run_by_index"},
                         "requirements_review": {"status": "unrecorded"}}
        claim["card"]["claim_text_sha256"] = _claim_digest({
            "title": claim["card"]["title"], "summary": claim["card"]["summary"],
            "claim_ceiling": claim.get("claim_ceiling"),
            "claim_ceiling_restated": claim.get("claim_ceiling_restated")})
        edge("claim", claim["claim_id"], "guide", guide_id, "explained_by_primary_guide")
        edge("claim", claim["claim_id"], "replay", replay_id, "has_replay_configuration")
        edge("replay", replay_id, "artifact", replay["runner_ref"], "invokes_named_runner")
        edge("replay", replay_id, "artifact", replay["input_ref"], "uses_execution_input")
        for ref in replay["configuration_refs"]:
            asset(ref)
            edge("replay", replay_id, "artifact", ref, "configured_by")
        for ref in sorted(set([authority, *historical])):
            edge("claim", claim["claim_id"], "artifact", ref, "has_historical_receipt")
    proof_by = _unique(assurance["proofs"], "slug", "proof descriptors")
    for slug, row in proof_by.items():
        if not _PUBLIC_ID.fullmatch(slug):
            raise ValueError("invalid kernel identity")
        contract, metadata = row["contract"], row["metadata"]
        if (set(contract) != {"schema_version", "contract_id", "statement", "input_model", "assumptions", "limits",
                             "specification_refs", "entry_theorem_refs", "component_bindings", "positive_test_ref",
                             "adversarial_test_ref", "mutant_refs", "formal_readme_ref"}
                or contract.get("schema_version") != CONTRACT_SCHEMA or contract.get("contract_id") != "contract::" + slug):
            raise ValueError("invalid formal contract identity")
        source = "formal/components/" + slug + "/" + metadata["source"]
        asset(source)
        if facts[source]["sha256"] != metadata["source_sha256"]:
            raise ValueError("stale formal source hash")
        generated = "src/plectis/components/" + slug + "/_generated/"
        for relative, digest in metadata["generated_python"].items():
            ref = asset(generated + relative)
            if facts[ref]["sha256"] != digest:
                raise ValueError("stale generated source hash")
        if (type(metadata["verified_tasks"]) is not int or metadata["verified_tasks"] <= 0
                or set(contract["mutant_refs"]) != {"formal/components/" + slug + "/" + n for n in metadata["negative_sources"]}):
            raise ValueError("incorrect retained proof coverage")
        for ref in [*contract["specification_refs"], *contract["entry_theorem_refs"]]:
            if not ref.startswith(source + "#"):
                raise ValueError("formal symbol belongs to another source")
            asset(ref)
        if not contract["specification_refs"] or not contract["entry_theorem_refs"]:
            raise ValueError("formal statement or entry theorem missing")
        for field in ("statement", "input_model", "assumptions", "limits"):
            _text(contract[field], field)
        for ref in [contract["formal_readme_ref"], *contract["mutant_refs"]]:
            asset(ref)
        test_asset(contract["positive_test_ref"])
        test_asset(contract["adversarial_test_ref"])
        bindings = _unique(contract["component_bindings"], "organ_id", "contract component bindings")
        if not bindings or set(bindings) - set(registry_by):
            raise ValueError("contract binds unknown component")
        for organ_id, binding in bindings.items():
            if set(binding) != {"organ_id", "runtime_refs", "test_refs", "primary_guide_ref"}:
                raise ValueError("invalid contract component binding fields")
            if binding["primary_guide_ref"] != guides[organ_id]["legacy_markdown_projection"]:
                raise ValueError("contract primary guide differs from atlas owner")
            if not binding["runtime_refs"] or not binding["test_refs"]:
                raise ValueError("contract lacks actual consumer/test references")
            for ref in [*binding["runtime_refs"], *binding["test_refs"]]:
                asset(ref)
            for ref in binding["runtime_refs"]:
                if facts[ref].get("symbol_kind") != "python_function":
                    raise ValueError("runtime hook reference is not a function")
            for ref in binding["test_refs"]:
                test_asset(ref)
        subclaim_id, spec_id, proof_id = ("subclaim::" + slug, "specification::" + slug, "proof::dafny::" + slug)
        additions["subclaim"][subclaim_id] = {"subclaim_id": subclaim_id, **copy.deepcopy(contract),
                                             "descriptor_origin": row["descriptor_origin"],
                                             "contract_sha256": _claim_digest(contract),
                                             "requirements_review": {"status": "unrecorded"},
                                             "scope": "named modeled algorithm contract only"}
        additions["specification"][spec_id] = {"specification_id": spec_id, "source_ref": source,
                                              "symbol_refs": contract["specification_refs"]}
        additions["proof"][proof_id] = {
            "proof_id": proof_id, "language": "dafny", "module": row["module"],
            "metadata_ref": "formal/components/" + slug + "/metadata.json",
            "entry_theorem_refs": contract["entry_theorem_refs"],
            "retained_verification": {"basis": "recorded_metadata", "verified_tasks": metadata["verified_tasks"],
                                      "dafny_version": metadata["dafny_version"]},
            "current_binding": {"status": "current_hash_binding_pass", "source_sha256": metadata["source_sha256"],
                                "generated_python": metadata["generated_python"],
                                "assessment_time_basis": "index_generation_only",
                                "checker_ref": "scripts/check/check_component_kernels.py#check_binding"},
            "fresh_prover_result": {"status": "not_run_by_index"},
            "generated_refs": [generated + name for name in sorted(metadata["generated_python"])],
            "adapter_ref": "src/plectis/components/" + slug + "/_adapter.py",
            "trusted_host_refs": ["src/plectis/components/_bridge.py", "src/plectis/components/_worker.py", "src/plectis/_sealed_kernel.py"],
            "negative_controls": [{"source_ref": "formal/components/" + slug + "/" + name,
                                   "source_sha256": metadata["negative_sha256"][name],
                                   "retained_result": {"basis": "recorded_metadata", **metadata["negative_results"][name]},
                                   "fresh_result": {"status": "not_run_by_index"}}
                                  for name in metadata["negative_sources"]],
        }
        for organ_id in bindings:
            claim = claim_by[organ_id]
            claim["card"]["formal_subclaim_ids"].append(subclaim_id)
            edge("claim", claim["claim_id"], "subclaim", subclaim_id, "has_formal_subclaim")
        edge("subclaim", subclaim_id, "specification", spec_id, "specified_by")
        edge("subclaim", subclaim_id, "proof", proof_id, "has_retained_formal_proof")
        edge("proof", proof_id, "specification", spec_id, "establishes_model_contract")
        for ref in additions["proof"][proof_id]["generated_refs"]:
            edge("proof", proof_id, "artifact", ref, "binds_generated_executable")
        for ref in [additions["proof"][proof_id]["adapter_ref"], *additions["proof"][proof_id]["trusted_host_refs"]]:
            asset(ref)
            edge("proof", proof_id, "artifact", ref, "relies_on_trusted_host")
        for binding in bindings.values():
            for ref in binding["runtime_refs"]:
                edge("subclaim", subclaim_id, "artifact", ref, "consumed_at_runtime_hook")
            for ref in binding["test_refs"]:
                edge("subclaim", subclaim_id, "artifact", ref, "challenged_by_test")
    for kind, rows in additions.items():
        result["nodes"][kind] = [rows[key] for key in sorted(rows)]
    result["nodes"]["artifact"] = [{"artifact_id": key, **facts[key]} for key in sorted(facts)]
    result["schema_version"] = ASSURANCE_INDEX_SCHEMA
    result["export_band"] = "presence_and_bounded_claim_cards"
    result["generated_from"]["claim_assurance"] = {
        "registry": "core/organ_registry.json", "evidence_classes": "core/organ_evidence_classes.json",
        "guide_authority": "core/organ_atlas.json.paper_module_ref -> core/paper_module_capsules.json",
        "formal_contracts": "formal/components/<slug>/metadata.json#contract",
        "replay_configuration": "src/microcosm_core/runtime_shell.py#RUNTIME_STEPS + src/microcosm_core/component_replay.py#native_replay_step"}
    result["assurance"] = {"schema_version": ASSURANCE_SCHEMA, "universe_source": "core/organ_registry.json#implemented_organs",
                           "component_count": len(registry_by), "formal_subclaim_count": len(proof_by),
                           "owner_refs": assurance["owner_refs"],
                           "canonical_field_provenance": {"normative_owner_refs": ["core/organ_registry.json", "core/organ_evidence_classes.json"],
                               "ignored_cache_fields": ignored_cache_fields,
                               "ignored_atlas_class_rows": sorted(oid for oid, row in atlas_by.items()
                                                                   if row.get("evidence_class") != registry_by[oid]["evidence_class"]),
                               "retained_lens_fields": ["runner_source_resolved", "runner_custody_basis", "runner_specificity", "source_file counts"]},
                           "optional_unavailable_assets": [facts[ref] for ref in sorted(facts) if facts[ref]["availability"] == "unavailable"],
                           "fresh_prover_invoked": False, "replay_executed": False,
                           "base_lens_evidence": "retained snapshot; not re-extracted by assurance enrichment",
                           "component_wide_verification_inferred": False,
                           "human_fields": "capsule title/compression.one_line and bounded formal contract fields; no source bodies"}
    result["graph"]["edge_semantics"].update({
        "proven_by": "Legacy compatibility: historical bounded authority receipt; never a domain theorem or fresh proof result.",
        "has_formal_subclaim": "A narrower modeled algorithm contract; never whole-component verification.",
        "has_retained_formal_proof": "Named retained Dafny contract with current source/generated hash binding; no fresh prover run.",
        "has_replay_configuration": "Declared runner/input/output configuration; no execution, freshness or domain correctness claim."})
    counts = {}
    for row in result["edges"]:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1
    result["graph"]["edge_kinds"] = sorted(counts)
    result["graph"]["edge_kind_counts"] = counts
    result["rollup"].update(edge_count=len(result["edges"]), formal_subclaim_count=len(proof_by),
                            proof_node_count=len(proof_by), guide_node_count=len(additions["guide"]))
    _public(result)
    from microcosm_core.component_index import _component_facets, _coverage_from_facets
    for claim in result["nodes"]["claim"]:
        claim["card"]["assurance_facets"] = _component_facets(
            result, claim["organ_id"], assurance["historical_native_records"][claim["organ_id"]])
    result["assurance"]["coverage"] = _coverage_from_facets(result)
    if "explorer" in assurance:
        result["explorer"] = copy.deepcopy(assurance["explorer"])
    _validate_assurance_export(result)
    return copy.deepcopy(result)
