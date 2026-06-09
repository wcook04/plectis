from __future__ import annotations

import json
from pathlib import Path

from microcosm_core.projections import architecture_graph_scene
from microcosm_core.schemas import read_json_strict


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]


def _accepted_organ_count() -> int:
    registry = read_json_strict(MICROCOSM_ROOT / "core/organ_registry.json")
    return len(
        [
            row
            for row in registry["implemented_organs"]
            if row.get("status") == "accepted_current_authority"
        ]
    )


def _family_count() -> int:
    families = read_json_strict(MICROCOSM_ROOT / "core/organ_families.json")
    return len([row for row in families["families"] if isinstance(row, dict)])


def _spine_step_count() -> int:
    kernel = read_json_strict(MICROCOSM_ROOT / "core/architecture_kernel.json")
    return len([row for row in kernel["primitives"] if isinstance(row, dict)])


def _explicit_wire_count() -> int:
    atlas = read_json_strict(MICROCOSM_ROOT / "core/organ_atlas.json")
    atlas_ids = {
        str(row.get("organ_id"))
        for row in atlas["organs"]
        if isinstance(row, dict) and row.get("organ_id")
    }
    return sum(
        1
        for row in atlas["organs"]
        if isinstance(row, dict)
        for target in row.get("wires_to") or []
        if str(target) in atlas_ids
    )


def test_architecture_graph_scene_packet_is_compact_and_source_bound() -> None:
    packet = architecture_graph_scene.build_architecture_graph_scene_packet(
        MICROCOSM_ROOT
    )

    assert packet["schema"] == "microcosm_architecture_graph_scene_packet_v0"
    assert packet["authority_posture"] == (
        "public_microcosm_projection_not_source_authority"
    )
    assert "graph_scene" not in packet
    assert packet["summary"]["area_count"] == _family_count()
    assert packet["summary"]["component_count"] == _accepted_organ_count()
    assert packet["summary"]["spine_step_count"] == _spine_step_count()
    assert packet["summary"]["explicit_wire_count"] == _explicit_wire_count()
    assert packet["summary"]["edge_semantics"] == "declared_dependency_untyped"
    assert packet["edge_semantics"]["typing_policy"].startswith(
        "wires_to is source-declared"
    )
    assert "not stronger proof" in packet["long_description"]

    manifest = packet["graph_scene_manifest"]
    assert manifest["schema"] == "graph_scene_manifest_v1"
    assert manifest["source_schema"] == "microcosm_architecture_graph_source_v1"
    assert manifest["counts"]["nodes"] > packet["summary"]["area_count"]
    assert manifest["counts"]["edges"] >= packet["summary"]["explicit_wire_count"]
    assert manifest["relation_type_counts"]["declared_dependency_untyped"] == (
        _explicit_wire_count()
    )
    assert "architecture_overview" in manifest["available_focus_ids"]
    assert packet["graph_scene_validation"]["ok"] is True

    default_focus = packet["graph_scene_default_focus"]
    assert default_focus["schema"] == "graph_scene_focus_excerpt_v1"
    assert default_focus["focus_id"] == "architecture_overview"
    assert default_focus["omitted"]["full_scene"] is True
    assert default_focus["counts"]["nodes"] == _family_count() + 1
    assert {row["id"] for row in default_focus["nodes"]} >= {
        "shared_path",
        "area:architecture_and_navigation",
    }

    delta = packet["graph_scene_delta_manifest"]
    assert delta["schema"] == "graph_scene_delta_manifest_v1"
    assert delta["revision"] == manifest["revision"]
    assert delta["changed"] is None


def test_full_architecture_graph_scene_preserves_untyped_wire_authority() -> None:
    packet = architecture_graph_scene.build_architecture_graph_scene_packet(
        MICROCOSM_ROOT,
        include_full_scene=True,
    )
    scene = packet["graph_scene"]
    wire_edges = [
        edge
        for edge in scene["edges"]
        if edge.get("relation") == "declared_dependency_untyped"
    ]

    assert len(wire_edges) == packet["summary"]["explicit_wire_count"]
    assert scene["type_registry"]["relations"]["declared_dependency_untyped"][
        "authority_posture"
    ] == "source_declared_untyped_relation"
    assert all(
        edge["provenance"] == {
            "source_ref": "microcosm-substrate/core/organ_atlas.json",
            "source_field": "wires_to",
        }
        for edge in wire_edges
    )
    assert scene["resolver_refs"]["public_packet"] == (
        "sites/microcosm/docs/architecture-graph-scene.json"
    )
    assert scene["semantic_zoom"]["levels"] == [
        {"id": "overview", "focus_id": "architecture_overview"},
        {"id": "spine", "focus_id": "shared_spine"},
        {"id": "wiring", "focus_id": "explicit_wiring"},
    ]
    component_nodes = [
        node for node in scene["nodes"] if str(node.get("id") or "").startswith("component:")
    ]
    assert len(component_nodes) == packet["summary"]["component_count"]
    assert any(
        node.get("kind") == "component"
        and (node.get("metrics") or {}).get("declared_wiring_endpoint") is False
        for node in component_nodes
    )


def test_architecture_graph_scene_source_fingerprint_is_stable_and_source_bound(
    tmp_path: Path,
) -> None:
    core = tmp_path / "core"
    core.mkdir()
    (core / "organ_families.json").write_text(
        json.dumps(
            {
                "families": [
                    {
                        "family_id": "entry_and_reveal",
                        "label": "Entry & Reveal",
                        "organ_ids": ["cold_reader_route_map"],
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    (core / "organ_registry.json").write_text(
        json.dumps(
            {
                "implemented_organs": [
                    {
                        "organ_id": "cold_reader_route_map",
                        "status": "accepted_current_authority",
                    }
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    atlas_payload = {
        "organs": [
            {
                "organ_id": "cold_reader_route_map",
                "display_name": "Cold Reader Route Map",
                "wires_to": [],
            }
        ]
    }
    (core / "organ_atlas.json").write_text(
        json.dumps(atlas_payload, sort_keys=True),
        encoding="utf-8",
    )
    (core / "architecture_kernel.json").write_text(
        json.dumps(
            {
                "primitives": [
                    {"primitive_id": "project", "public_name": "Project"},
                    {"primitive_id": "catalog", "public_name": "Catalog"},
                ]
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    first = architecture_graph_scene.build_architecture_graph_scene_packet(tmp_path)
    second = architecture_graph_scene.build_architecture_graph_scene_packet(tmp_path)
    assert first["graph_scene_manifest"]["source_fingerprint"] == (
        second["graph_scene_manifest"]["source_fingerprint"]
    )
    assert first["graph_scene_manifest"]["revision"] == (
        second["graph_scene_manifest"]["revision"]
    )

    atlas_payload["organs"][0]["display_name"] = "Cold Reader Route Map v2"
    (core / "organ_atlas.json").write_text(
        json.dumps(atlas_payload, sort_keys=True),
        encoding="utf-8",
    )
    changed = architecture_graph_scene.build_architecture_graph_scene_packet(tmp_path)
    assert changed["graph_scene_manifest"]["source_fingerprint"] != (
        first["graph_scene_manifest"]["source_fingerprint"]
    )
    assert changed["graph_scene_manifest"]["revision"] != (
        first["graph_scene_manifest"]["revision"]
    )
