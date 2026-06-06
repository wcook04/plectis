"""Microcosm-native graph-scene projection for the architecture map.

The public site builder can use the private repo's ``system.lib`` helpers, but
the standalone Microcosm package cannot. This module exposes the same compact
graph-scene fields from public Microcosm source refs without depending on the
parent ai_workflow substrate.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.resource_root import microcosm_root
from microcosm_core.schemas import read_json_strict


SCHEMA_VERSION = "microcosm_architecture_graph_scene_packet_v0"
SOURCE_SCHEMA = "microcosm_architecture_graph_source_v1"
SCENE_SCHEMA = "graph_scene_v1"
MANIFEST_SCHEMA = "graph_scene_manifest_v1"
FOCUS_EXCERPT_SCHEMA = "graph_scene_focus_excerpt_v1"
DELTA_MANIFEST_SCHEMA = "graph_scene_delta_manifest_v1"
VALIDATION_SCHEMA = "graph_scene_validation_v1"
SEMANTIC_ZOOM_SCHEMA = "graph_scene_semantic_zoom_v1"
TYPE_REGISTRY_SCHEMA = "graph_scene_type_registry_v1"
ADAPTER_VERSION = "microcosm_architecture_graph_scene_adapter_v1"
DETERMINISTIC_GENERATED_AT = "1970-01-01T00:00:00+00:00"

SOURCE_REFS = (
    "core/organ_families.json",
    "core/organ_registry.json",
    "core/organ_atlas.json",
    "core/architecture_kernel.json",
)

AUTHORITY_POSTURE = "public_microcosm_projection_not_source_authority"
UNTYPED_WIRE_RELATION = "declared_dependency_untyped"


def public_source_ref(rel_path: str) -> str:
    return f"microcosm-substrate/{rel_path}"


def stable_json_hash(payload: Any, *, length: int = 32) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _rows(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    return [row for row in payload.get(key, []) if isinstance(row, dict)]


def _source_hashes(root: Path) -> dict[str, str]:
    return {
        public_source_ref(rel_path): _sha256_file(root / rel_path)
        for rel_path in SOURCE_REFS
    }


def _scene_revision(source_fingerprint: str, *, focus_id: str | None = None) -> str:
    digest = stable_json_hash(
        {
            "adapter_version": ADAPTER_VERSION,
            "source_schema": SOURCE_SCHEMA,
            "source_fingerprint": source_fingerprint,
            "default_projection": "cluster_overview",
            "focus_id": focus_id or "",
        },
        length=20,
    )
    return f"gsc_{digest}"


def _display_label(row: Mapping[str, Any], fallback: str) -> str:
    value = str(row.get("display_name") or row.get("label") or "").strip()
    if value:
        return value
    return fallback.replace("_", " ").title()


def _load_source_model(root: Path) -> dict[str, Any]:
    families_doc = read_json_strict(root / "core/organ_families.json")
    registry_doc = read_json_strict(root / "core/organ_registry.json")
    atlas_doc = read_json_strict(root / "core/organ_atlas.json")
    kernel_doc = read_json_strict(root / "core/architecture_kernel.json")

    families = _rows(families_doc, "families")
    accepted_rows = [
        row
        for row in _rows(registry_doc, "implemented_organs")
        if row.get("status") == "accepted_current_authority"
    ]
    accepted_ids = {str(row.get("organ_id")) for row in accepted_rows}
    atlas_by_id = {
        str(row.get("organ_id")): row
        for row in _rows(atlas_doc, "organs")
        if str(row.get("organ_id") or "") in accepted_ids
    }
    primitive_rows = _rows(kernel_doc, "primitives")
    source_hashes = _source_hashes(root)

    family_rows: list[dict[str, Any]] = []
    family_of_component: dict[str, str] = {}
    for family in families:
        family_id = str(family.get("family_id") or "").strip()
        if not family_id:
            continue
        organ_ids = [
            str(organ_id)
            for organ_id in family.get("organ_ids") or []
            if str(organ_id) in accepted_ids
        ]
        for organ_id in organ_ids:
            family_of_component[organ_id] = family_id
        family_rows.append(
            {
                "family_id": family_id,
                "label": str(family.get("label") or family_id.replace("_", " ").title()),
                "blurb": str(family.get("blurb") or ""),
                "organ_ids": organ_ids,
                "component_count": len(organ_ids),
            }
        )

    return {
        "families": family_rows,
        "accepted_ids": sorted(accepted_ids),
        "atlas_by_id": atlas_by_id,
        "family_of_component": family_of_component,
        "primitive_rows": primitive_rows,
        "source_hashes": source_hashes,
        "interaction_model": families_doc.get("interaction_model") or {},
    }


def _focus_path(focus_id: str, label: str, node_ids: list[str], edge_ids: list[str]) -> dict[str, Any]:
    return {
        "id": focus_id,
        "label": label,
        "node_ids": node_ids,
        "edge_ids": edge_ids,
    }


def _build_scene_rows(model: Mapping[str, Any]) -> dict[str, Any]:
    clusters = [
        {"id": "cluster:areas", "label": "Microcosm areas", "kind": "overview"},
        {"id": "cluster:shared_spine", "label": "Shared architecture spine", "kind": "spine"},
    ]
    nodes = [
        {
            "id": "shared_path",
            "label": "Shared path",
            "kind": "shared_spine",
            "parent_cluster_id": "cluster:shared_spine",
            "state": "active",
            "metrics": {"step_count": len(model["primitive_rows"])},
        }
    ]
    edges: list[dict[str, Any]] = []

    area_node_ids: list[str] = []
    area_edge_ids: list[str] = []
    for family in model["families"]:
        family_id = family["family_id"]
        cluster_id = f"cluster:{family_id}"
        node_id = f"area:{family_id}"
        edge_id = f"edge:area:{family_id}:shared_path"
        clusters.append({"id": cluster_id, "label": family["label"], "kind": "area"})
        nodes.append(
            {
                "id": node_id,
                "label": family["label"],
                "kind": "area",
                "parent_cluster_id": "cluster:areas",
                "state": "active",
                "metrics": {"component_count": family["component_count"]},
                "provenance": {
                    "source_ref": public_source_ref("core/organ_families.json"),
                    "source_field": "families",
                },
            }
        )
        edges.append(
            {
                "id": edge_id,
                "source": node_id,
                "target": "shared_path",
                "relation": "binds_to_shared_path",
                "label": "binds to shared path",
                "bundle_id": "bundle:area_shared_path",
            }
        )
        area_node_ids.append(node_id)
        area_edge_ids.append(edge_id)

    primitive_node_ids: list[str] = []
    primitive_edge_ids: list[str] = []
    previous_node_id: str | None = None
    for index, primitive in enumerate(model["primitive_rows"]):
        primitive_id = str(primitive.get("primitive_id") or "").strip()
        if not primitive_id:
            continue
        node_id = f"primitive:{primitive_id}"
        primitive_node_ids.append(node_id)
        nodes.append(
            {
                "id": node_id,
                "label": str(primitive.get("public_name") or primitive_id.replace("_", " ").title()),
                "kind": "spine_primitive",
                "parent_cluster_id": "cluster:shared_spine",
                "rank": index,
                "state": "active",
                "resolver_ref": str(primitive.get("state_ref") or ""),
                "provenance": {
                    "source_ref": public_source_ref("core/architecture_kernel.json"),
                    "source_field": "primitives",
                },
            }
        )
        if previous_node_id:
            edge_id = f"edge:spine:{previous_node_id}:{node_id}"
            primitive_edge_ids.append(edge_id)
            edges.append(
                {
                    "id": edge_id,
                    "source": previous_node_id,
                    "target": node_id,
                    "relation": "spine_sequence",
                    "label": "then",
                    "bundle_id": "bundle:shared_spine",
                }
            )
        previous_node_id = node_id

    atlas_by_id: Mapping[str, Mapping[str, Any]] = model["atlas_by_id"]
    wired_component_ids: set[str] = set()
    wire_edge_ids: list[str] = []
    wire_pairs: list[dict[str, str]] = []
    for organ_id in sorted(atlas_by_id):
        card = atlas_by_id[organ_id]
        targets = [
            str(target)
            for target in card.get("wires_to") or []
            if str(target) in atlas_by_id
        ]
        if not targets:
            continue
        wired_component_ids.add(organ_id)
        for target in targets:
            wired_component_ids.add(target)
            edge_id = f"edge:wire:{organ_id}:{target}"
            wire_edge_ids.append(edge_id)
            wire_pairs.append({"source": organ_id, "target": target, "relation": UNTYPED_WIRE_RELATION})
            edges.append(
                {
                    "id": edge_id,
                    "source": f"component:{organ_id}",
                    "target": f"component:{target}",
                    "relation": UNTYPED_WIRE_RELATION,
                    "label": "declared wiring",
                    "bundle_id": "bundle:explicit_wiring",
                    "authority_posture": "source_declared_untyped_relation",
                    "provenance": {
                        "source_ref": public_source_ref("core/organ_atlas.json"),
                        "source_field": "wires_to",
                    },
                }
            )

    for component_id in sorted(wired_component_ids):
        card = atlas_by_id.get(component_id, {})
        family_id = model["family_of_component"].get(component_id, str(card.get("family") or ""))
        nodes.append(
            {
                "id": f"component:{component_id}",
                "label": _display_label(card, component_id),
                "kind": "wired_component",
                "parent_cluster_id": f"cluster:{family_id}" if family_id else "cluster:areas",
                "state": "active",
                "metrics": {"declared_wiring_endpoint": True},
                "provenance": {
                    "source_ref": public_source_ref("core/organ_atlas.json"),
                    "source_field": "organs",
                },
            }
        )

    focus_paths = [
        _focus_path(
            "architecture_overview",
            "Areas and shared path",
            ["shared_path", *area_node_ids],
            area_edge_ids,
        ),
        _focus_path(
            "shared_spine",
            "Architecture kernel primitives",
            primitive_node_ids,
            primitive_edge_ids,
        ),
        _focus_path(
            "explicit_wiring",
            "Source-declared component wiring",
            [f"component:{component_id}" for component_id in sorted(wired_component_ids)],
            wire_edge_ids,
        ),
    ]

    return {
        "clusters": clusters,
        "nodes": nodes,
        "edges": edges,
        "focus_paths": focus_paths,
        "wire_pairs": wire_pairs,
    }


def validate_graph_scene(scene: Mapping[str, Any]) -> dict[str, Any]:
    nodes = [row for row in scene.get("nodes", []) if isinstance(row, dict)]
    edges = [row for row in scene.get("edges", []) if isinstance(row, dict)]
    node_ids = [str(row.get("id") or "") for row in nodes]
    edge_ids = [str(row.get("id") or "") for row in edges]
    node_id_set = set(node_ids)
    edge_id_set = set(edge_ids)

    errors: list[dict[str, Any]] = []
    duplicate_nodes = sorted(node_id for node_id, count in Counter(node_ids).items() if node_id and count > 1)
    duplicate_edges = sorted(edge_id for edge_id, count in Counter(edge_ids).items() if edge_id and count > 1)
    if duplicate_nodes:
        errors.append({"code": "duplicate_node_ids", "node_ids": duplicate_nodes})
    if duplicate_edges:
        errors.append({"code": "duplicate_edge_ids", "edge_ids": duplicate_edges})
    for edge in edges:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in node_id_set or target not in node_id_set:
            errors.append(
                {
                    "code": "edge_endpoint_missing",
                    "edge_id": edge.get("id"),
                    "source": source,
                    "target": target,
                }
            )
    for focus in scene.get("focus_paths", []):
        if not isinstance(focus, dict):
            continue
        missing_nodes = [
            node_id
            for node_id in focus.get("node_ids") or []
            if str(node_id) not in node_id_set
        ]
        missing_edges = [
            edge_id
            for edge_id in focus.get("edge_ids") or []
            if str(edge_id) not in edge_id_set
        ]
        if missing_nodes or missing_edges:
            errors.append(
                {
                    "code": "focus_path_member_missing",
                    "focus_id": focus.get("id"),
                    "missing_nodes": missing_nodes,
                    "missing_edges": missing_edges,
                }
            )

    warnings = []
    relation_counts = Counter(str(row.get("relation") or "") for row in edges)
    if relation_counts.get(UNTYPED_WIRE_RELATION):
        warnings.append(
            {
                "code": "explicit_wire_edges_are_untyped",
                "relation": UNTYPED_WIRE_RELATION,
                "count": relation_counts[UNTYPED_WIRE_RELATION],
                "reason": "wires_to is source-declared neighbour wiring, not typed proof, causal, or maturity relation authority.",
            }
        )
    return {
        "schema": VALIDATION_SCHEMA,
        "ok": not errors,
        "error_count": len(errors),
        "errors": errors,
        "warning_count": len(warnings),
        "warnings": warnings,
    }


def _build_manifest(scene: Mapping[str, Any]) -> dict[str, Any]:
    nodes = [row for row in scene.get("nodes", []) if isinstance(row, dict)]
    edges = [row for row in scene.get("edges", []) if isinstance(row, dict)]
    clusters = [row for row in scene.get("clusters", []) if isinstance(row, dict)]
    focus_paths = [row for row in scene.get("focus_paths", []) if isinstance(row, dict)]
    return {
        "schema": MANIFEST_SCHEMA,
        "scene_id": scene["scene_id"],
        "source_schema": scene["source_schema"],
        "source_fingerprint": scene["source_fingerprint"],
        "revision": scene["revision"],
        "core_version": scene["core_version"],
        "authority_posture": AUTHORITY_POSTURE,
        "counts": {
            "nodes": len(nodes),
            "edges": len(edges),
            "clusters": len(clusters),
            "focus_paths": len(focus_paths),
        },
        "node_kind_counts": dict(sorted(Counter(str(row.get("kind") or "node") for row in nodes).items())),
        "relation_type_counts": dict(sorted(Counter(str(row.get("relation") or "relates") for row in edges).items())),
        "available_focus_ids": [str(row.get("id")) for row in focus_paths if row.get("id")],
        "default_focus_id": scene["default_focus_id"],
        "resolver_refs": dict(scene.get("resolver_refs") or {}),
        "validation": scene["validation"],
    }


def build_default_focus_excerpt(
    scene: Mapping[str, Any],
    *,
    focus_id: str | None = None,
    max_nodes: int = 48,
    max_edges: int = 72,
) -> dict[str, Any]:
    selected_focus_id = focus_id or str(scene.get("default_focus_id") or "")
    focus = next(
        (
            row
            for row in scene.get("focus_paths", [])
            if isinstance(row, dict) and row.get("id") == selected_focus_id
        ),
        None,
    )
    if focus is None:
        focus = {"id": selected_focus_id or "default", "label": "Default focus", "node_ids": [], "edge_ids": []}
    node_ids = [str(row) for row in focus.get("node_ids") or []]
    edge_ids = [str(row) for row in focus.get("edge_ids") or []]
    nodes_by_id = {str(row.get("id")): row for row in scene.get("nodes", []) if isinstance(row, dict)}
    edges_by_id = {str(row.get("id")): row for row in scene.get("edges", []) if isinstance(row, dict)}
    selected_nodes = [nodes_by_id[node_id] for node_id in node_ids if node_id in nodes_by_id][:max_nodes]
    selected_node_ids = {str(row.get("id")) for row in selected_nodes}
    selected_edges = [
        edges_by_id[edge_id]
        for edge_id in edge_ids
        if edge_id in edges_by_id
        and str(edges_by_id[edge_id].get("source")) in selected_node_ids
        and str(edges_by_id[edge_id].get("target")) in selected_node_ids
    ][:max_edges]
    return {
        "schema": FOCUS_EXCERPT_SCHEMA,
        "scene_id": scene["scene_id"],
        "revision": scene["revision"],
        "source_fingerprint": scene["source_fingerprint"],
        "focus_id": focus.get("id"),
        "label": focus.get("label") or focus.get("id"),
        "nodes": selected_nodes,
        "edges": selected_edges,
        "counts": {"nodes": len(selected_nodes), "edges": len(selected_edges)},
        "omitted": {
            "full_scene": True,
            "node_count": max(0, len(scene.get("nodes", [])) - len(selected_nodes)),
            "edge_count": max(0, len(scene.get("edges", [])) - len(selected_edges)),
        },
        "resolver_refs": dict(scene.get("resolver_refs") or {}),
    }


def _build_delta_manifest(scene: Mapping[str, Any], previous_revision: str | None = None) -> dict[str, Any]:
    manifest = scene["manifest"]
    return {
        "schema": DELTA_MANIFEST_SCHEMA,
        "scene_id": scene["scene_id"],
        "revision": scene["revision"],
        "previous_revision": previous_revision,
        "changed": None if previous_revision is None else previous_revision != scene["revision"],
        "source_fingerprint": scene["source_fingerprint"],
        "counts": manifest["counts"],
        "relation_type_counts": manifest["relation_type_counts"],
        "resolver_refs": dict(scene.get("resolver_refs") or {}),
    }


def build_architecture_graph_scene(
    root: str | Path | None = None,
    *,
    generated_at: str = DETERMINISTIC_GENERATED_AT,
) -> dict[str, Any]:
    resolved_root = Path(root) if root is not None else microcosm_root()
    model = _load_source_model(resolved_root)
    scene_rows = _build_scene_rows(model)
    wire_pairs = scene_rows["wire_pairs"]
    source_fingerprint = stable_json_hash(
        {
            "schema": SOURCE_SCHEMA,
            "source_hashes": model["source_hashes"],
            "families": [
                {"family_id": row["family_id"], "component_count": row["component_count"]}
                for row in model["families"]
            ],
            "primitive_ids": [
                str(row.get("primitive_id") or "")
                for row in model["primitive_rows"]
                if row.get("primitive_id")
            ],
            "wire_pairs": wire_pairs,
        }
    )
    revision = _scene_revision(source_fingerprint, focus_id="architecture_overview")
    summary = {
        "schema": "microcosm_architecture_graph_scene_summary_v0",
        "area_count": len(model["families"]),
        "component_count": len(model["accepted_ids"]),
        "spine_step_count": len(model["primitive_rows"]),
        "wired_component_count": len({row["source"] for row in wire_pairs}),
        "explicit_wire_count": len(wire_pairs),
        "edge_semantics": UNTYPED_WIRE_RELATION,
        "source_refs": [public_source_ref(rel_path) for rel_path in SOURCE_REFS],
    }
    long_description = (
        f"This generated graph-scene packet shows {summary['area_count']} public areas, "
        f"{summary['spine_step_count']} shared architecture-kernel steps, and "
        f"{summary['component_count']} accepted components. "
        f"{summary['wired_component_count']} components declare "
        f"{summary['explicit_wire_count']} direct links to neighbours. "
        "Those direct links stay marked as source-declared untyped wiring, not "
        "stronger proof, causal, maturity, or release relations."
    )
    scene: dict[str, Any] = {
        "schema": SCENE_SCHEMA,
        "scene_id": "microcosm_architecture_graph_scene",
        "source_schema": SOURCE_SCHEMA,
        "source_fingerprint": source_fingerprint,
        "revision": revision,
        "core_version": ADAPTER_VERSION,
        "generated_at": generated_at,
        "authority_posture": AUTHORITY_POSTURE,
        "default_projection": "cluster_overview",
        "default_focus_id": "architecture_overview",
        "clusters": scene_rows["clusters"],
        "nodes": scene_rows["nodes"],
        "edges": scene_rows["edges"],
        "focus_paths": scene_rows["focus_paths"],
        "bundles": [
            {
                "id": "bundle:area_shared_path",
                "label": "area to shared path",
                "relation": "binds_to_shared_path",
            },
            {
                "id": "bundle:shared_spine",
                "label": "architecture kernel sequence",
                "relation": "spine_sequence",
            },
            {
                "id": "bundle:explicit_wiring",
                "label": "source-declared component wiring",
                "relation": UNTYPED_WIRE_RELATION,
            },
        ],
        "semantic_zoom": {
            "schema": SEMANTIC_ZOOM_SCHEMA,
            "levels": [
                {"id": "overview", "focus_id": "architecture_overview"},
                {"id": "spine", "focus_id": "shared_spine"},
                {"id": "wiring", "focus_id": "explicit_wiring"},
            ],
        },
        "type_registry": {
            "schema": TYPE_REGISTRY_SCHEMA,
            "relations": {
                "binds_to_shared_path": {
                    "authority_posture": "area_membership_projection",
                    "source_ref": public_source_ref("core/organ_families.json"),
                },
                "spine_sequence": {
                    "authority_posture": "architecture_kernel_order_projection",
                    "source_ref": public_source_ref("core/architecture_kernel.json"),
                },
                UNTYPED_WIRE_RELATION: {
                    "authority_posture": "source_declared_untyped_relation",
                    "source_ref": public_source_ref("core/organ_atlas.json"),
                },
            },
        },
        "resolver_refs": {
            "public_page": "sites/microcosm/docs/architecture.html",
            "public_packet": "sites/microcosm/docs/architecture-graph-scene.json",
            "organ_atlas": public_source_ref("core/organ_atlas.json"),
            "architecture_kernel": public_source_ref("core/architecture_kernel.json"),
        },
        "edge_semantics": {
            "explicit_wire_relation": UNTYPED_WIRE_RELATION,
            "typing_policy": "wires_to is source-declared neighbour wiring; wiring notes are human annotations, not typed relation authority.",
        },
        "source_refs": [public_source_ref(rel_path) for rel_path in SOURCE_REFS],
        "summary": summary,
        "long_description": long_description,
    }
    scene["validation"] = validate_graph_scene(scene)
    scene["manifest"] = _build_manifest(scene)
    return scene


def build_architecture_graph_scene_packet(
    root: str | Path | None = None,
    *,
    include_full_scene: bool = False,
    previous_revision: str | None = None,
) -> dict[str, Any]:
    scene = build_architecture_graph_scene(root)
    packet = {
        "schema": SCHEMA_VERSION,
        "authority_posture": AUTHORITY_POSTURE,
        "summary": scene["summary"],
        "long_description": scene["long_description"],
        "edge_semantics": scene["edge_semantics"],
        "source_refs": scene["source_refs"],
        "resolver_refs": scene["resolver_refs"],
        "graph_scene_manifest": scene["manifest"],
        "graph_scene_default_focus": build_default_focus_excerpt(scene),
        "graph_scene_delta_manifest": _build_delta_manifest(scene, previous_revision),
        "graph_scene_validation": scene["validation"],
    }
    if include_full_scene:
        packet["graph_scene"] = scene
    return packet
