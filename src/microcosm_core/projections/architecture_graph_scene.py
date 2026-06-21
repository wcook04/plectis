"""Plectis graph-scene projection for the architecture map.

The public site builder can use the private repo's ``system.lib`` helpers, but
the standalone microcosm-substrate compatibility package cannot. This module
exposes the same compact graph-scene fields from public Plectis source refs
without depending on the parent ai_workflow substrate.
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
    """Render a substrate-relative path as a public Plectis source ref.

    - Teleology: single chokepoint that stamps the ``microcosm-substrate/`` prefix so every node/edge provenance ref points at the public source tree, not a private path.
    - Guarantee: returns ``f"microcosm-substrate/{rel_path}"`` verbatim; no normalization, no filesystem check.
    - Fails: never raises; a malformed or absolute ``rel_path`` is returned prefixed as-is (caller owns ref hygiene).
    - When-needed: tracing where a scene node/edge claims its source authority lives.
    - Non-goal: does not verify the ref exists, is public-safe, or grants source-mutation/release authority.
    """
    return f"microcosm-substrate/{rel_path}"


def stable_json_hash(payload: Any, *, length: int = 32) -> str:
    """Compute a deterministic truncated sha256 over a JSON-canonicalized payload.

    - Teleology: gives the scene a content-addressed fingerprint/revision id so identical source state yields an identical scene id across machines and runs.
    - Guarantee: returns the first ``length`` hex chars of sha256 over ``json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)``; key order and whitespace cannot perturb the digest.
    - Fails: never raises for normal payloads; non-JSON-native values are coerced via ``default=str`` rather than erroring.
    - When-needed: explaining why a scene revision changed (the hashed payload is what moved).
    - Non-goal: not a cryptographic integrity proof and not a claim that the payload is public-safe or release-ready.
    """
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:length]


def _sha256_file(path: Path) -> str:
    """Compute a streamed ``sha256:``-prefixed digest of one source file.

    - Teleology: per-file content digest that lets the scene fingerprint detect when a source JSON body changed on disk, not just its row counts.
    - Guarantee: returns ``"sha256:" + hexdigest`` over the file's bytes, read in 1 MiB chunks so arbitrarily large files hash without loading whole into memory.
    - Fails: ``FileNotFoundError`` / ``OSError`` if ``path`` is absent or unreadable; the open is not guarded.
    - When-needed: explaining why ``source_fingerprint`` moved when row-shape is unchanged.
    - Reads: the file at ``path`` (one of the ``SOURCE_REFS`` JSON sources).
    - Non-goal: not a public-safety or integrity attestation; does not authorize source-body export or release.
    """
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return "sha256:" + hasher.hexdigest()


def _rows(payload: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    """Extract the dict rows under one key of a loaded source document.

    - Teleology: defensive row accessor so malformed/non-dict entries in a source list cannot poison downstream node/edge construction.
    - Guarantee: returns a list containing only the ``dict`` items of ``payload[key]``; a missing key or non-list value yields ``[]``.
    - Fails: never raises for mapping input; non-dict members are silently dropped rather than erroring.
    - When-needed: reasoning about why a source row was excluded from the scene before it reached node building.
    - Non-goal: does not validate row schema/content and grants no source-mutation or release authority.
    """
    return [row for row in payload.get(key, []) if isinstance(row, dict)]


def _source_hashes(root: Path) -> dict[str, str]:
    """Map each public source ref to the sha256 digest of its on-disk body.

    - Teleology: assembles the per-source digest table that feeds the scene's content fingerprint, binding the projection to exact source bytes.
    - Guarantee: returns ``{public_source_ref(rel): "sha256:<hex>"}`` for every path in ``SOURCE_REFS``, keyed by the public ``microcosm-substrate/`` ref.
    - Fails: ``FileNotFoundError`` / ``OSError`` (via ``_sha256_file``) if any ``SOURCE_REFS`` file under ``root`` is missing or unreadable.
    - When-needed: diagnosing a fingerprint change down to which specific source file moved.
    - Reads: every file in ``SOURCE_REFS`` resolved under ``root`` (organ_families/registry/atlas/architecture_kernel JSON).
    - Non-goal: does not check public-safety of source bodies and grants no export/release authority.
    """
    return {
        public_source_ref(rel_path): _sha256_file(root / rel_path)
        for rel_path in SOURCE_REFS
    }


def _scene_revision(source_fingerprint: str, *, focus_id: str | None = None) -> str:
    """Derive the deterministic ``gsc_`` revision id for a scene state.

    - Teleology: stamps a stable revision label that changes iff the adapter version, source schema, source fingerprint, or default focus changes — the delta-detection key.
    - Guarantee: returns ``"gsc_" + stable_json_hash({adapter_version, source_schema, source_fingerprint, default_projection, focus_id}, length=20)``; identical inputs always yield the same id.
    - Fails: never raises; an empty/None ``focus_id`` folds to ``""`` in the hashed payload.
    - When-needed: explaining why two scene builds report different revisions.
    - Escalates-to: ``stable_json_hash`` and the ``source_fingerprint`` inputs for what actually moved.
    - Non-goal: not a cryptographic version stamp and not a release or public-safety claim.
    """
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
    """Pick a human display label for a component node from its source row.

    - Teleology: gives every wired-component node a readable label, preferring source-declared naming over a derived id so the map is legible.
    - Guarantee: returns the stripped ``display_name`` else ``label`` from ``row`` if non-empty; otherwise the ``fallback`` id title-cased with underscores replaced by spaces.
    - Fails: never raises; missing/blank fields fall through to the title-cased ``fallback``.
    - When-needed: tracing why a node renders a given label versus its raw organ id.
    - Reads: the ``display_name`` / ``label`` fields of an ``organ_atlas.json`` organ row.
    - Non-goal: does not validate or sanitize label content for public exposure.
    """
    value = str(row.get("display_name") or row.get("label") or "").strip()
    if value:
        return value
    return fallback.replace("_", " ").title()


def _load_source_model(root: Path) -> dict[str, Any]:
    """Load and join the four public source JSONs into the scene's input model.

    - Teleology: the single source-custody read step — pulls families, the accepted-organ registry slice, atlas cards, and kernel primitives into one normalized model so the builder never touches raw files again.
    - Guarantee: returns ``{families, accepted_ids, atlas_by_id, family_of_component, primitive_rows, source_hashes, interaction_model}`` where only organs with ``status == "accepted_current_authority"`` are admitted and atlas/family membership is restricted to those accepted ids.
    - Fails: ``read_json_strict`` raises (FileNotFoundError / JSON decode error) if any of organ_families/organ_registry/organ_atlas/architecture_kernel JSON is missing or malformed.
    - When-needed: diagnosing why a component is absent from the scene (likely not accepted) or why source_hashes changed.
    - Reads: ``core/organ_families.json``, ``core/organ_registry.json``, ``core/organ_atlas.json``, ``core/architecture_kernel.json`` under ``root``.
    - Escalates-to: ``SOURCE_REFS`` and ``_source_hashes`` for the exact source bytes this model was built from.
    - Non-goal: does not validate source-body public-safety, does not mutate source, and grants no release authority.
    """
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
    """Build one focus-path record (a named, renderable node/edge subset).

    - Teleology: uniform constructor for the scene's saved camera targets so each focus carries the same ``id/label/node_ids/edge_ids`` shape the excerpt builder consumes.
    - Guarantee: returns ``{"id", "label", "node_ids", "edge_ids"}`` echoing the arguments verbatim; no validation that the referenced ids exist in the scene.
    - Fails: never raises; membership integrity is deferred to ``validate_graph_scene`` (``focus_path_member_missing``).
    - When-needed: tracing the composition of a focus before integrity validation runs.
    - Non-goal: does not check that ids resolve and grants no release authority.
    """
    return {
        "id": focus_id,
        "label": label,
        "node_ids": node_ids,
        "edge_ids": edge_ids,
    }


def _build_scene_rows(model: Mapping[str, Any]) -> dict[str, Any]:
    """Project the source model into clusters, nodes, edges, and focus paths.

    - Teleology: the core generation step that turns the loaded model into the renderable graph — area nodes bound to the shared path, the kernel-primitive spine sequence, and source-declared ``wires_to`` component edges.
    - Guarantee: returns ``{clusters, nodes, edges, focus_paths, wire_pairs}`` where every wiring edge is relation ``declared_dependency_untyped``, only ``wires_to`` targets present in the accepted atlas are linked, and each node/edge carries a ``provenance.source_ref``.
    - Fails: never raises for a well-formed model; rows with blank ``family_id`` / ``primitive_id`` and untargeted wirings are skipped rather than erroring.
    - When-needed: diagnosing missing nodes/edges or why a wiring pair did not render.
    - Escalates-to: ``validate_graph_scene`` for the integrity check over what this emitted, and the per-edge ``provenance.source_ref`` for origin.
    - Non-goal: emits no typed/causal/maturity relation — ``wires_to`` stays untyped; this is generated projection, not source authority or a release claim.
    """
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
    all_component_ids = set(model["accepted_ids"])
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

    for component_id in sorted(all_component_ids):
        card = atlas_by_id.get(component_id, {})
        family_id = model["family_of_component"].get(component_id, str(card.get("family") or ""))
        is_wired = component_id in wired_component_ids
        nodes.append(
            {
                "id": f"component:{component_id}",
                "label": _display_label(card, component_id),
                "kind": "wired_component" if is_wired else "component",
                "parent_cluster_id": f"cluster:{family_id}" if family_id else "cluster:areas",
                "state": "active",
                "metrics": {"declared_wiring_endpoint": is_wired},
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
            [f"component:{component_id}" for component_id in sorted(all_component_ids)],
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
    """Check graph-scene referential integrity and flag untyped wiring edges.

    - Teleology: structural gate that keeps the emitted scene renderable and honest — no dangling edges, no duplicate ids, no focus path pointing at absent members, and untyped ``wires_to`` edges surfaced as a warning rather than laundered into typed relations.
    - Guarantee: returns a ``graph_scene_validation_v1`` envelope ``{"ok": bool, "error_count", "errors", "warning_count", "warnings"}`` where ``ok`` is True iff no errors; errors cover duplicate_node_ids, duplicate_edge_ids, edge_endpoint_missing, and focus_path_member_missing.
    - Fails: never raises; integrity failures are reported as ``ok=False`` with typed error dicts, and declared_dependency_untyped edges add an ``explicit_wire_edges_are_untyped`` warning (does not flip ``ok``).
    - When-needed: before trusting a scene/excerpt for rendering, or when a focus path or edge fails to resolve.
    - Escalates-to: ``tests/`` graph-scene regression assertions and the per-edge ``provenance.source_ref`` for source-of-truth.
    - Non-goal: does not validate source-body semantics, edge causality/maturity, or authorize release of the scene.
    """
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
    """Summarize a built scene into a compact ``graph_scene_manifest_v1`` header.

    - Teleology: the bandwidth-bounded scene header — counts and kind/relation histograms a client reads to orient before (or instead of) pulling the full node/edge payload.
    - Guarantee: returns a ``graph_scene_manifest_v1`` dict carrying scene_id/source identity/revision, node-edge-cluster-focus counts, sorted ``node_kind_counts`` and ``relation_type_counts``, available/default focus ids, resolver_refs, the embedded ``validation``, and a fixed ``authority_posture`` of ``public_microcosm_projection_not_source_authority``.
    - Fails: ``KeyError`` if ``scene`` lacks required keys (``scene_id``/``source_schema``/``source_fingerprint``/``revision``/``core_version``/``default_focus_id``/``validation``); built scenes always provide them.
    - When-needed: building or reading the manifest header for the public packet.
    - Escalates-to: the full ``scene`` and ``build_architecture_graph_scene`` when counts are insufficient.
    - Non-goal: a derived projection header, not source-of-truth authority and not a release claim.
    """
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
    """Cut a bounded, self-consistent node/edge excerpt around one focus path.

    - Teleology: gives a cold reader a small first-paint slice of the scene (one focus, capped) instead of the full node/edge set, while staying internally consistent.
    - Guarantee: returns a ``graph_scene_focus_excerpt_v1`` dict whose ``edges`` only connect nodes present in the truncated ``nodes`` set; honours ``max_nodes``/``max_edges`` caps and records an ``omitted`` count for the rest.
    - Fails: ``KeyError`` if ``scene`` lacks ``scene_id``/``revision``/``source_fingerprint``; an unknown ``focus_id`` does not raise — it yields a labelled empty focus excerpt.
    - When-needed: building or debugging the default focus packet a client renders first.
    - Escalates-to: the full ``scene`` (via ``build_architecture_graph_scene``) when the excerpt omits a needed node/edge.
    - Non-goal: not the authoritative full scene and not a release/completeness claim.
    """
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
    """Compare a scene's revision against a prior one into a delta header.

    - Teleology: lets a client decide whether to re-fetch — reports whether this scene's revision differs from the caller-supplied ``previous_revision`` without diffing full payloads.
    - Guarantee: returns a ``graph_scene_delta_manifest_v1`` dict echoing scene_id/revision/source_fingerprint plus ``changed`` = None when ``previous_revision`` is None else ``previous_revision != scene["revision"]``, and carries the manifest counts/relation_type_counts.
    - Fails: ``KeyError`` if ``scene`` lacks ``manifest``/``scene_id``/``revision``/``source_fingerprint``; built scenes provide them.
    - When-needed: computing a cheap change signal against a client's last-known revision.
    - Escalates-to: ``_scene_revision`` / ``source_fingerprint`` for what moved when ``changed`` is True.
    - Non-goal: a coarse changed/unchanged signal, not a structural diff and not a release authority claim.
    """
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
    """Build the full deterministic architecture graph-scene from public source JSON.

    - Teleology: the package-native scene builder — projects organ families, accepted organs, architecture-kernel primitives, and declared ``wires_to`` wiring into one ``graph_scene_v1`` document without depending on the private ai_workflow substrate.
    - Guarantee: returns a self-contained scene carrying clusters/nodes/edges/focus_paths, a content-derived ``source_fingerprint`` and ``revision``, embedded ``validation`` and ``manifest``; a fixed ``generated_at`` keeps the output byte-stable for unchanged source.
    - Fails: ``read_json_strict`` raises (FileNotFoundError / JSON decode error) if any of organ_families/registry/atlas/architecture_kernel JSON is missing or malformed; on success the embedded ``validation.ok`` reports structural integrity without raising.
    - When-needed: regenerating the architecture map packet or diagnosing why the scene revision moved.
    - Escalates-to: the public source refs in ``SOURCE_REFS`` and the embedded ``validation`` block for integrity detail.
    - Non-goal: ``wires_to`` edges stay ``declared_dependency_untyped`` — this is not typed/causal/maturity relation authority, not source-mutation, and not a release or whole-system-correctness claim.
    """
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
    """Wrap the scene into a compact public packet (manifest + default focus, full scene optional).

    - Teleology: bandwidth-bounded delivery surface for the architecture map — ships summary/manifest/default-focus/delta/validation so a client paints without the full node/edge payload unless it opts in.
    - Guarantee: returns a ``microcosm_architecture_graph_scene_packet_v0`` dict that always carries summary, long_description, edge_semantics, source_refs, resolver_refs, graph_scene_manifest, graph_scene_default_focus, graph_scene_delta_manifest, and graph_scene_validation; the full ``graph_scene`` is included only when ``include_full_scene`` is True.
    - Fails: propagates ``build_architecture_graph_scene`` read errors (missing/invalid source JSON); does not raise on its own once the scene is built.
    - When-needed: producing the public architecture packet or computing a delta against ``previous_revision``.
    - Escalates-to: ``include_full_scene=True`` (or ``build_architecture_graph_scene``) when the manifest/excerpt is insufficient.
    - Non-goal: omitting the full scene is a size choice, not authority erasure — the packet still authorizes no release, no source mutation, and no typed-relation claim beyond the untyped wiring posture.
    """
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
