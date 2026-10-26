#!/usr/bin/env python3
"""Frontend-wide View Quality Census.

This is the first widening step after the Surface Atlas salience guard:
measure graph-like and artifact views with one registry/contract before trying
to merge their React components.

Inputs are existing projections:

  * state/frontend_navigation/navigation_graph.json
  * tools/meta/observability/station_views.json

The output is a census, not a final aesthetic verdict. A view with missing
markers is reported as partial_unmeasured rather than ugly.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_NAVIGATION_GRAPH = REPO_ROOT / "state/frontend_navigation/navigation_graph.json"
DEFAULT_STATION_VIEWS = REPO_ROOT / "tools/meta/observability/station_views.json"
DEFAULT_RENDER_LOAD_INDEX = REPO_ROOT / "state/observability/render_load_index.json"
DEFAULT_OUT_DIR = REPO_ROOT / "state/observability/view_quality"
DEFAULT_OUT = DEFAULT_OUT_DIR / "frontend_view_quality_census_v0.json"
DEFAULT_VIEW_PACKET_DIR = DEFAULT_OUT_DIR / "views"
DEFAULT_VIEW_PACKET_INDEX = DEFAULT_OUT_DIR / "frontend_view_observation_index_v0.json"
DEFAULT_VIEW_PACKET_INDEX_MD = DEFAULT_OUT_DIR / "frontend_view_observation_index_v0.md"
DEFAULT_VISUAL_SETTLEMENT = DEFAULT_OUT_DIR / "frontend_visual_settlement_v0.json"

VIEW_QUALITY_CENSUS_SCHEMA = "frontend_view_quality_census_v0"
VIEW_QUALITY_RECEIPT_SCHEMA_V1 = "view_quality_receipt_v1"
METRIC_QUALITY_RECEIPT_SCHEMA_V1 = "metric_quality_receipt_v1"
METRIC_QUALITY_VECTOR_SCHEMA_V1 = "view_quality_metric_vector_v1"
GEOMETRY_VECTOR_SCHEMA_V1 = "view_quality_geometry_vector_v1"
GEOMETRY_CALIBRATION_PROFILE_SCHEMA_V1 = "view_quality_geometry_calibration_profile_v1"
GEOMETRY_CALIBRATION_REVIEW_SCHEMA_V1 = "view_quality_geometry_calibration_review_v1"
CALIBRATED_WATCH_RESOLUTION_SCHEMA_V1 = "calibrated_watch_resolution_v1"
CALIBRATED_WATCH_RESOLUTION_ROLLUP_SCHEMA_V1 = "calibrated_watch_resolution_rollup_v1"
VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1 = "view_quality_resolution_action_receipt_v1"
VIEW_QUALITY_RESOLUTION_ACTION_ROLLUP_SCHEMA_V1 = "view_quality_resolution_action_rollup_v1"
VIEW_QUALITY_ACTION_ROW_SCHEMA_V1 = "view_quality_action_row_v1"
VIEW_QUALITY_ACTION_MAP_SCHEMA_V1 = "view_quality_action_map_v1"
VIEW_QUALITY_HOT_ACTION_ROLLUP_SCHEMA_V1 = "view_quality_hot_action_rollup_v1"
ROOT_NAVIGATOR_CAPTURE_SUMMARY_SCHEMA_V1 = "root_navigator_capture_summary_v1"
VIEW_GEOMETRY_CAPTURE_SUMMARY_SCHEMA_V1 = "view_geometry_capture_summary_v1"
MEASURE_REGISTRY_SCHEMA = "view_quality_measure_registry_v0"
GRAPH_SURFACE_CONTRACT_SCHEMA = "graph_surface_contract_v0"
VIEW_OBSERVATION_PACKET_SCHEMA_V0 = "frontend_view_observation_packet_v0"
VIEW_OBSERVATION_INDEX_SCHEMA_V0 = "frontend_view_observation_index_v0"
SCREENSHOT_LEDGER_SCHEMA_V0 = "frontend_view_screenshot_ledger_v0"
VIEW_OBSERVATION_VISUAL_DELTA_SCHEMA_V1 = "frontend_view_observation_visual_delta_v1"
STATION_RENDER_VISUAL_DELTA_SCHEMA_V1 = "station_render_view_observation_visual_delta_v1"
FRONTEND_VISUAL_SETTLEMENT_SCHEMA_V0 = "frontend_visual_settlement_v0"
FRONTEND_VISUAL_MEMORY_DISCOVERY_SCHEMA_V0 = "frontend_visual_memory_discovery_v0"

FRONTEND_VISUAL_MEMORY_ALIAS_TERMS = (
    "screenshot ledger",
    "frontend screenshot ledger",
    "view observation memory",
    "view observation packet",
    "visual memory cell",
    "frontend visual memory",
    "frontend visual settlement",
    "latest visual delta",
)

VISUAL_SETTLEMENT_REVIEW_STATUSES = {
    "review_needed",
    "baseline_pending",
    "unbound_to_station_render",
    "blocked_capture",
}

DEFAULT_SEED_VIEW_IDS = (
    "station",
    "rootNavigator",
    "codemap",
    "topology",
    "graph",
    "navigation",
    "history",
    "intelligence",
)

GRAPH_FAMILIES = {"atlas_map", "graph_surface"}

CALIBRATED_WATCH_RESOLUTION_CLASSES = (
    "extractor_gap",
    "scene_policy_gap",
    "threshold_profile_gap",
    "acceptable_by_constitution",
)


def _view_memory_discoverability(view_id: Any = "<view_id>") -> dict[str, Any]:
    view_selector = str(view_id or "<view_id>")
    return {
        "schema": FRONTEND_VISUAL_MEMORY_DISCOVERY_SCHEMA_V0,
        "alias_terms": list(FRONTEND_VISUAL_MEMORY_ALIAS_TERMS),
        "docs_route": './repo-python kernel.py --docs-route "screenshot ledger"',
        "view_option_surface": "./repo-python kernel.py --option-surface frontend_views --band cluster_flag",
        "open_view_card": f"./repo-python kernel.py --option-surface frontend_views --band card --ids {view_selector}",
        "packet_index_ref": str(DEFAULT_VIEW_PACKET_INDEX.relative_to(REPO_ROOT)),
        "visual_settlement_ref": str(DEFAULT_VISUAL_SETTLEMENT.relative_to(REPO_ROOT)),
        "packet_dir": str(DEFAULT_VIEW_PACKET_DIR.relative_to(REPO_ROOT)),
        "owner_builder": "tools/meta/observability/view_quality_census.py",
        "capture_engine": "tools/meta/observability/station_render.py",
        "contract": (
            "A frontend view memory cell couples purpose, expected landmarks, "
            "design principles, screenshot freshness, visual delta, and settlement state; "
            "the screenshot is evidence, not standalone authority."
        ),
    }

RESOLUTION_ACTIONS_BY_CLASS: dict[str, dict[str, Any]] = {
    "extractor_gap": {
        "action": "extractor_patch",
        "decision": "extractor_patch_pending",
        "action_lane": "measurement_harness",
        "status": "open",
        "next_owner_shape": "extractor_resolution",
        "closure_condition": (
            "Patch selector/extractor logic, then prove the row with new live geometry "
            "and before/after view-quality evidence."
        ),
        "required_proof_refs": [
            "before_geometry_ref",
            "after_geometry_ref",
            "view_quality_before",
            "view_quality_after",
        ],
        "refactor_relevance": "measurement_harness_before_ui",
        "component_unification_gate": "Do not use this row for graph-component promotion until extractor evidence is trustworthy.",
    },
    "scene_policy_gap": {
        "action": "scene_policy_resolution",
        "decision": "scene_policy_resolution_pending",
        "action_lane": "scene_policy",
        "status": "open",
        "next_owner_shape": "scene_policy_resolution",
        "closure_condition": (
            "Resolve whether the scene default, data state, route mode, or constitution "
            "must change; closure needs fresh geometry and a changed class or accepted constitution."
        ),
        "required_proof_refs": [
            "before_geometry_ref",
            "after_geometry_ref",
            "before_screenshot_ref",
            "after_screenshot_ref",
            "view_quality_before",
            "view_quality_after",
            "visual_delta_ref",
        ],
        "refactor_relevance": "scene_policy_before_component_unification",
        "component_unification_gate": "Do not promote a graph surface as a shared parent while its default scene is unresolved.",
    },
    "threshold_profile_gap": {
        "action": "threshold_profile_review",
        "decision": "threshold_refinement_pending",
        "action_lane": "threshold_profile",
        "status": "open",
        "next_owner_shape": "threshold_profile_review",
        "closure_condition": (
            "Accept, refine, or reroute the threshold profile using fresh geometry, screenshot review, "
            "and mode constitution evidence."
        ),
        "required_proof_refs": [
            "geometry_ref",
            "screenshot_ref",
            "view_quality_after",
        ],
        "refactor_relevance": "threshold_profile_before_ui_patch",
        "component_unification_gate": "Do not convert a threshold watch into UI debt until the profile decision is explicit.",
    },
    "acceptable_by_constitution": {
        "action": "constitution_acceptance_record",
        "decision": "acceptance_evidence_pending",
        "action_lane": "constitution_profile",
        "status": "acceptance_pending",
        "next_owner_shape": "constitution_acceptance_profile",
        "closure_condition": (
            "Record the mode-specific constitution/profile note that makes the watch acceptable; "
            "no UI mutation is required after acceptance evidence exists."
        ),
        "required_proof_refs": [
            "mode_constitution_ref",
            "profile_acceptance_ref",
            "view_quality_after",
        ],
        "refactor_relevance": "valid_difference_before_defect_pressure",
        "component_unification_gate": "Treat accepted constitutional differences as refactor constraints, not defects.",
    },
}

GRAPH_COMPONENT_HINTS: dict[str, dict[str, str]] = {
    "StationSurfaceAtlas": {
        "graph_kind": "route_graph",
        "layout_engine": "reactflow",
        "camera_policy": "fit_view",
    },
    "RootNavigator": {
        "graph_kind": "system_atlas",
        "layout_engine": "reactflow",
        "camera_policy": "fit_view",
    },
    "SystemGraph": {
        "graph_kind": "task_graph",
        "layout_engine": "reactflow",
        "camera_policy": "fit_view",
    },
    "GraphViewer": {
        "graph_kind": "task_graph",
        "layout_engine": "reactflow",
        "camera_policy": "fit_view",
    },
    "CodeMapLens": {
        "graph_kind": "codemap",
        "layout_engine": "custom",
        "camera_policy": "unknown",
    },
    "TopologyAtlasScene": {
        "graph_kind": "system_atlas",
        "layout_engine": "custom",
        "camera_policy": "unknown",
    },
    "ShardGraph": {
        "graph_kind": "shard_graph",
        "layout_engine": "custom",
        "camera_policy": "unknown",
    },
}

COMPONENT_SOURCE_HINTS: dict[str, list[str]] = {
    "StationSurfaceAtlas": [
        "system/server/ui/src/components/world/home/StationSurfaceAtlas.tsx",
    ],
    "RootNavigator": [
        "system/server/ui/src/pages/RootNavigator.tsx",
    ],
    "CodeMapLens": [
        "system/server/ui/src/pages/CodeMapLens.tsx",
        "system/server/ui/src/components/codemap/CodeMapFlow.tsx",
        "system/server/ui/src/components/codemap/CodeMapNode.tsx",
        "system/server/ui/src/components/codemap/CodeMapEgoEdge.tsx",
    ],
    "TopologyAtlasScene": [
        "system/server/ui/src/components/world/TopologyAtlasScene.tsx",
        "system/server/ui/src/components/world/SystemViewLens.tsx",
    ],
    "SystemGraph": [
        "system/server/ui/src/components/world/SystemGraph.tsx",
        "system/server/ui/src/components/GraphViewer.tsx",
    ],
    "History": [
        "system/server/ui/src/pages/History.tsx",
    ],
}


def _utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> Any:
    if not path.exists():
        return {}
    return _read_json(path)


def _as_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _compact_reason(text: str, limit: int = 220) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    return f"{text[: limit - 1]}..."


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _parse_time(value: Any) -> _dt.datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return _dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _mtime(path: Path) -> _dt.datetime | None:
    try:
        return _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc)
    except OSError:
        return None


def _iso(value: _dt.datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(_dt.timezone.utc).replace(microsecond=0).isoformat()


def _text_blob(*parts: Any) -> str:
    return " ".join(str(part or "") for part in parts).lower()


def _capture_slug(view: Mapping[str, Any]) -> str | None:
    capture = _as_dict(view.get("capture"))
    return capture.get("slug") or view.get("capture_slug")


def _station_view_index(station_views: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("slug")): row
        for row in _as_list(station_views.get("views"))
        if isinstance(row, Mapping) and row.get("slug")
    }


def _view_index(navigation_graph: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(row.get("id")): row
        for row in _as_list(navigation_graph.get("views"))
        if isinstance(row, Mapping) and row.get("id")
    }


def _primary_component_name(view: Mapping[str, Any]) -> str:
    audit = _as_dict(view.get("surface_audit"))
    return str(audit.get("primary_component_name") or audit.get("primary_component") or "")


def _evidence_refs(view: Mapping[str, Any]) -> list[str]:
    audit = _as_dict(view.get("surface_audit"))
    return [str(ref) for ref in _as_list(audit.get("evidence_refs"))]


def _source_path_from_ref(ref: str) -> Path | None:
    match = re.search(r"(system/server/ui/src/[^:\s]+?\.(?:tsx|ts|css))", ref)
    if not match:
        return None
    return REPO_ROOT / match.group(1)


def _read_source_text(view: Mapping[str, Any], *, max_total_chars: int = 900_000) -> str:
    paths: list[Path] = []
    seen: set[Path] = set()
    component = _primary_component_name(view)
    for rel_path in COMPONENT_SOURCE_HINTS.get(component, []):
        path = REPO_ROOT / rel_path
        if path.exists() and path not in seen:
            paths.append(path)
            seen.add(path)
    for ref in _evidence_refs(view):
        path = _source_path_from_ref(ref)
        if path is None or path in seen or not path.exists():
            continue
        paths.append(path)
        seen.add(path)

    chunks: list[str] = []
    remaining = max_total_chars
    for path in paths:
        if remaining <= 0:
            break
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        chunks.append(text[:remaining])
        remaining -= len(chunks[-1])
    return "\n".join(chunks)


def default_measure_registry() -> dict[str, Any]:
    families = [
        {
            "id": "constitutional_effectiveness",
            "purpose": "Visible hierarchy matches the view constitution and dominant artifact.",
            "metric_ids": [
                "dominant_artifact_presence",
                "dominant_artifact_salience",
                "rail_to_artifact_ratio",
                "task_to_visual_hierarchy_alignment",
            ],
            "applies_to": ["atlas_map", "graph_surface", "artifact_review", "operator_cockpit"],
            "anti_gaming_note": "Selector presence cannot satisfy the gate when measured salience contradicts the constitution.",
        },
        {
            "id": "graph_readability",
            "purpose": "Node-link scenes expose enough geometry to judge legibility.",
            "metric_ids": [
                "node_overlap",
                "edge_crossing_count",
                "edge_crossing_angle",
                "edge_tunneling",
                "label_collision",
                "label_coverage",
                "node_union_to_viewport",
                "node_union_to_stage",
                "cluster_overlap",
                "path_spaghetti",
            ],
            "applies_to": ["atlas_map", "graph_surface"],
            "anti_gaming_note": "A tidy graph is not sufficient if it hides the dominant task object.",
        },
        {
            "id": "spacing_relative_positioning",
            "purpose": "4px token hygiene becomes a distribution of coherent gutters, margins, and densities.",
            "metric_ids": [
                "atomic_spacing_compliance",
                "inter_group_gutter",
                "intra_group_density",
                "nearest_neighbor_distance_distribution",
                "alignment_error",
                "dead_space_island",
                "visual_kissing",
                "card_rhythm",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "Token compliance is a floor; it does not prove scene-level coherence.",
        },
        {
            "id": "visibility_obstruction",
            "purpose": "Required artifacts and controls remain visible, unobstructed, and reopenable.",
            "metric_ids": [
                "required_region_visible",
                "required_control_visible",
                "above_fold_dominant_artifact_visible",
                "occlusion_by_rail",
                "collapsed_without_reopen_affordance",
                "clip_or_scroll_trap",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "A hidden-but-present DOM node is not a passing visual artifact.",
        },
        {
            "id": "visual_clutter_density",
            "purpose": "Competing marks, text, and edges do not overload the operator's first read.",
            "metric_ids": [
                "edge_density",
                "text_density",
                "component_count_above_fold",
                "feature_congestion_proxy",
                "entropy_proxy",
                "competing_salience_count",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "Reducing clutter cannot erase necessary task state.",
        },
        {
            "id": "interface_aesthetics",
            "purpose": "Classical computable aesthetics remain subordinate to task truth.",
            "metric_ids": [
                "balance",
                "equilibrium",
                "symmetry",
                "sequence",
                "cohesion",
                "unity",
                "proportion",
                "simplicity",
                "density",
                "regularity",
                "economy",
                "homogeneity",
                "rhythm",
                "order_complexity",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "No universal beauty scalar; weights vary by view family and mode.",
        },
        {
            "id": "color_contrast",
            "purpose": "Semantic color, contrast, and palette drift are measured in role-aware terms.",
            "metric_ids": [
                "semantic_color_consistency",
                "status_color_correctness",
                "hue_role_distance",
                "lightness_ladder_monotonicity",
                "contrast_floor",
                "muted_state_legibility",
                "alert_color_overuse",
                "palette_drift",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "Color alone cannot carry state; pair color with text, shape, border, or pattern.",
        },
        {
            "id": "shape_morphology",
            "purpose": "Node, port, card, and hit-target shapes carry distinct semantics.",
            "metric_ids": [
                "radius_token_compliance",
                "radius_role_consistency",
                "shape_language_consistency",
                "port_marker_legibility",
                "node_shape_distinctiveness",
                "card_vs_node_confusion",
            ],
            "applies_to": ["all"],
            "anti_gaming_note": "Uniform rounded rectangles can be tidy while semantically weak.",
        },
        {
            "id": "interaction_motion",
            "purpose": "Screenshot quality is rejected when cameras, selection, or drawers feel unstable.",
            "metric_ids": [
                "camera_jitter",
                "fit_view_jump",
                "layout_delta_after_selection",
                "hover_latency",
                "pan_fps_proxy",
                "animation_energy",
                "selection_context_survival",
                "drawer_open_cost",
            ],
            "applies_to": ["atlas_map", "graph_surface", "operator_cockpit"],
            "anti_gaming_note": "Static beauty cannot be bought by live interaction instability.",
        },
        {
            "id": "implementation_divergence",
            "purpose": "Graph-like components declare comparable capability signatures before code unification.",
            "metric_ids": [
                "graph_surface_contract_compliance",
                "layout_engine_signature",
                "camera_policy_signature",
                "region_marker_completeness",
                "receipt_schema_coverage",
                "duplicated_layout_logic_risk",
                "unshared_metric_gap",
            ],
            "applies_to": ["atlas_map", "graph_surface"],
            "anti_gaming_note": "Duplication is bad only when it creates repeated quality failures or drift.",
        },
    ]
    return {
        "schema": MEASURE_REGISTRY_SCHEMA,
        "receipt_schema": VIEW_QUALITY_RECEIPT_SCHEMA_V1,
        "metric_receipt_schema": METRIC_QUALITY_RECEIPT_SCHEMA_V1,
        "families": families,
        "grading_labels": ["measured_pass", "measured_watch", "measured_fail", "partial_unmeasured", "not_yet_in_census"],
        "measurement_tiers": [
            "not_yet_in_census",
            "partial_unmeasured",
            "measured_watch_generic",
            "measured_watch_metric",
            "measured_watch_geometry",
            "measured_pass",
        ],
        "calibration_statuses": [
            "not_started",
            "screenshot_pending",
            "geometry_pending_review",
            "geometry_watch",
            "calibrated_watch",
            "calibrated_pass",
            "blocked_missing_vectors",
            "surface_atlas_visual_truth_microcosm",
        ],
        "calibrated_watch_resolution_classes": list(CALIBRATED_WATCH_RESOLUTION_CLASSES),
        "resolution_action_receipt_schema": VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1,
        "view_quality_action_map_schema": VIEW_QUALITY_ACTION_MAP_SCHEMA_V1,
        "view_quality_hot_action_rollup_schema": VIEW_QUALITY_HOT_ACTION_ROLLUP_SCHEMA_V1,
        "view_quality_action_classes": [
            "census_binding_gap",
            "measurement_contract_gap",
            "metric_depth_gap",
            "rendered_geometry_gap",
            "geometry_evidence_gap",
            "calibration_gap",
            "diagnosed_quality_gap",
            "failed_quality_gap",
            "monitor",
            "accepted_difference",
        ],
        "calibrated_watch_resolution_actions": {
            resolution_class: {
                "action": action["action"],
                "action_lane": action["action_lane"],
                "next_owner_shape": action["next_owner_shape"],
            }
            for resolution_class, action in sorted(RESOLUTION_ACTIONS_BY_CLASS.items())
        },
    }


def graph_surface_contract() -> dict[str, Any]:
    return {
        "schema": GRAPH_SURFACE_CONTRACT_SCHEMA,
        "purpose": "Shared capability signature for graph-like frontend surfaces before component unification.",
        "signature_fields": [
            "graph_kind",
            "layout_engine",
            "camera_policy",
            "emits_node_rects",
            "emits_edge_paths",
            "emits_region_markers",
            "emits_quality_receipt",
        ],
        "minimum_for_measured_graph_surface": [
            "emits_node_rects",
            "emits_edge_paths",
            "emits_region_markers",
            "emits_quality_receipt",
        ],
        "minimum_for_metric_bearing_graph_surface": [
            "emits_node_rects",
            "emits_edge_paths",
            "emits_region_markers",
            "emits_quality_receipt",
            "quality_receipt_source=metric_quality_receipt_v1",
        ],
        "known_layout_engines": ["reactflow", "manual_packer", "dagre", "elk", "force", "grid", "custom", "unknown"],
        "known_camera_policies": ["fit_view", "selected_center", "persistent_viewport", "unknown"],
    }


def classify_view_family(view: Mapping[str, Any], capture: Mapping[str, Any] | None = None) -> str:
    component = _primary_component_name(view)
    capture = _as_dict(capture)
    blob = _text_blob(
        view.get("id"),
        view.get("route"),
        view.get("label"),
        view.get("purpose"),
        view.get("shell_group"),
        view.get("station_group"),
        capture.get("purpose"),
        capture.get("capture_group"),
        component,
    )

    if view.get("id") == "station" or component == "StationSurfaceAtlas":
        return "atlas_map"
    if any(token in blob for token in ("root navigator", "graph", "topology", "codemap", "map lens", "atlas scene")):
        return "graph_surface"
    if any(token in blob for token in ("history", "archive", "diff", "artifact", "review", "evidence replay")):
        return "artifact_review"
    if "timeline" in blob or "sequence" in blob:
        return "timeline"
    if any(token in blob for token in ("paper", "doctrine", "document", "docs")):
        return "document"
    if any(token in blob for token in ("cockpit", "operate", "intelligence", "control", "mission")):
        return "operator_cockpit"
    return "artifact_review"


def default_mode_for_family(family: str) -> str:
    return {
        "atlas_map": "map_first",
        "graph_surface": "graph_first",
        "artifact_review": "review_first",
        "timeline": "review_first",
        "document": "read_first",
        "operator_cockpit": "operate_first",
    }.get(family, "review_first")


def constitution_for_family(family: str, view: Mapping[str, Any]) -> dict[str, Any]:
    if family == "atlas_map":
        return {
            "dominant_artifact": "navigation_graph",
            "subordinate_regions": ["left_group_rail", "right_detail_rail", "legend", "inspector"],
            "must_be_visible": ["graph_stage", "visible_nodes", "reopen_affordances"],
            "may_defer": ["detail_rail", "group_rail", "legend_rows"],
        }
    if family == "graph_surface":
        return {
            "dominant_artifact": "graph_canvas",
            "subordinate_regions": ["axis_rail", "inspector", "filters", "legend"],
            "must_be_visible": ["graph_stage", "nodes_or_clusters", "selection_context"],
            "may_defer": ["inspector_detail", "legend_rows", "advanced_filters"],
        }
    if family == "operator_cockpit":
        return {
            "dominant_artifact": "active_operational_plane",
            "subordinate_regions": ["filters", "inspector", "status_rail"],
            "must_be_visible": ["active_state", "next_action", "blocked_or_stale_state"],
            "may_defer": ["deep_history", "secondary_lenses"],
        }
    if family == "document":
        return {
            "dominant_artifact": "readable_document",
            "subordinate_regions": ["metadata", "navigation", "evidence_links"],
            "must_be_visible": ["document_body", "source_handle"],
            "may_defer": ["full_metadata", "related_docs"],
        }
    return {
        "dominant_artifact": "review_artifact",
        "subordinate_regions": ["metadata", "filters", "inspector"],
        "must_be_visible": ["artifact_body", "source_or_receipt_handle"],
        "may_defer": ["secondary_metadata", "historical_context"],
    }


def _infer_layout_engine(source_text: str, component: str) -> str:
    lower = source_text.lower()
    if "reactflow" in source_text or "react-flow" in lower:
        return "reactflow"
    if "dagre" in lower:
        return "dagre"
    if "elk" in lower:
        return "elk"
    if "forcesimulation" in lower or "forceSimulation" in source_text:
        return "force"
    if "grid" in lower:
        return "grid"
    return GRAPH_COMPONENT_HINTS.get(component, {}).get("layout_engine", "unknown")


def _infer_camera_policy(source_text: str, component: str) -> str:
    lower = source_text.lower()
    if "fitview" in lower or "fit_view" in lower:
        return "fit_view"
    if "selected" in lower and ("center" in lower or "centroid" in lower):
        return "selected_center"
    if "persistent_viewport" in lower or "viewport" in lower:
        return "persistent_viewport"
    return GRAPH_COMPONENT_HINTS.get(component, {}).get("camera_policy", "unknown")


def build_graph_surface_signature(view: Mapping[str, Any], source_text: str | None = None) -> dict[str, Any]:
    source_text = source_text if source_text is not None else _read_source_text(view)
    component = _primary_component_name(view)
    lower = source_text.lower()
    hints = GRAPH_COMPONENT_HINTS.get(component, {})

    emits_node_rects = any(
        token in source_text
        for token in (
            "data-zenith-atlas-node-id",
            "data-zenith-root-graph-visual-node",
            "data-zenith-root-workbench-node",
            "data-zenith-codemap-node",
            "data-zenith-topology-node",
            "data-zenith-system-graph-node",
        )
    )
    emits_edge_paths = any(
        token in source_text
        for token in (
            "data-zenith-root-graph-visual-edge",
            "data-zenith-root-workbench-edge",
            "data-zenith-root-graph-edge",
            "data-zenith-atlas-edge",
            "data-zenith-surface-atlas-edge",
            "data-zenith-codemap-edge",
            "data-zenith-system-graph-edge",
        )
    )

    if "reactflow" in source_text or "react-flow" in lower:
        emits_node_rects = emits_node_rects or "nodes" in lower
        emits_edge_paths = emits_edge_paths or "edges" in lower

    emits_region_markers = "data-zenith-view-region" in source_text
    if "data-zenith-surface-atlas-scene-candidate-receipt" in source_text or component == "StationSurfaceAtlas":
        quality_receipt_source = "surface_atlas_scene_candidate"
    elif METRIC_QUALITY_RECEIPT_SCHEMA_V1 in source_text:
        quality_receipt_source = METRIC_QUALITY_RECEIPT_SCHEMA_V1
    elif "data-zenith-view-quality-receipt" in source_text or "view_quality_receipt" in source_text:
        quality_receipt_source = "generic_view_quality_marker"
    else:
        quality_receipt_source = "none"
    emits_quality_receipt = quality_receipt_source != "none"

    return {
        "schema": GRAPH_SURFACE_CONTRACT_SCHEMA,
        "graph_kind": hints.get("graph_kind", "unknown"),
        "layout_engine": _infer_layout_engine(source_text, component),
        "camera_policy": _infer_camera_policy(source_text, component),
        "primary_component": component or "unknown",
        "emits_node_rects": bool(emits_node_rects),
        "emits_edge_paths": bool(emits_edge_paths),
        "emits_region_markers": bool(emits_region_markers),
        "emits_quality_receipt": bool(emits_quality_receipt),
        "quality_receipt_source": quality_receipt_source,
    }


def _quality_receipt_source_from_text(source_text: str) -> str:
    if METRIC_QUALITY_RECEIPT_SCHEMA_V1 in source_text:
        return METRIC_QUALITY_RECEIPT_SCHEMA_V1
    if "data-zenith-surface-atlas-scene-candidate-receipt" in source_text:
        return "surface_atlas_scene_candidate"
    if "data-zenith-view-quality-receipt" in source_text or "view_quality_receipt" in source_text:
        return "generic_view_quality_marker"
    return "none"


def _source_marker_count(source_text: str, marker: str) -> int:
    return source_text.count(marker.replace("'", '"')) + source_text.count(marker.replace('"', "'"))


def _build_metric_vector(
    *,
    family: str,
    mode: str,
    has_capture_contract: bool,
    ready_selector: str,
    source_text: str,
    signature: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if family not in GRAPH_FAMILIES or not signature:
        return None
    if signature.get("quality_receipt_source") != METRIC_QUALITY_RECEIPT_SCHEMA_V1:
        return None

    dominant_region_count = _source_marker_count(source_text, 'data-zenith-view-region="dominant_artifact"')
    rail_region_count = _source_marker_count(source_text, 'data-zenith-view-region="rail"')
    inspector_region_count = _source_marker_count(source_text, 'data-zenith-view-region="inspector"')
    node_selector_count = sum(
        source_text.count(token)
        for token in (
            "data-zenith-root-graph-visual-node",
            "data-zenith-root-workbench-node",
            "data-zenith-root-graph-node",
            "data-zenith-system-graph-node",
            "data-zenith-codemap-node",
            "data-zenith-atlas-node-id",
        )
    )
    edge_selector_count = sum(
        source_text.count(token)
        for token in (
            "data-zenith-root-graph-visual-edge",
            "data-zenith-root-workbench-edge",
            "data-zenith-root-graph-edge",
            "data-zenith-system-graph-edge",
            "data-zenith-codemap-edge",
            "data-zenith-surface-atlas-edge",
            "data-zenith-atlas-edge",
        )
    )

    return {
        "schema": METRIC_QUALITY_VECTOR_SCHEMA_V1,
        "source": "static_marker_contract_plus_capture_manifest",
        "viewport_mode": mode,
        "dominant_artifact_geometry_present": bool(has_capture_contract and ready_selector and dominant_region_count > 0),
        "graph_region_marker_count": dominant_region_count,
        "rail_or_inspector_region_marker_count": rail_region_count + inspector_region_count,
        "node_selector_count": node_selector_count,
        "edge_selector_count": edge_selector_count,
        "node_rect_count": None,
        "node_rect_count_source": "runtime_dom_capture_pending_static_selector_present"
        if node_selector_count > 0
        else "missing_static_selector",
        "edge_path_count": None,
        "edge_path_count_source": "runtime_dom_capture_pending_static_selector_present"
        if edge_selector_count > 0
        else "missing_static_selector",
        "graph_region_area_ratio": None,
        "rail_or_inspector_area_ratio": None,
        "node_union_to_graph_region": None,
        "visible_label_coverage": None,
        "calibration_limit": "Static marker/capture-manifest vector only; geometry ratios require a DOM capture summary.",
    }


def _number_or_none(value: Any) -> float | int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _area_ratio(region: Mapping[str, Any] | None) -> float | None:
    region = _as_dict(region)
    value = _number_or_none(region.get("area_ratio"))
    if value is None:
        value = _number_or_none(region.get("viewport_area_ratio"))
    return round(float(value), 4) if value is not None else None


def _region_geometry_from_summary(summary: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(summary, Mapping):
        return []
    regions = _as_dict(summary.get("regions"))
    rows: list[dict[str, Any]] = []
    for key, value in regions.items():
        if isinstance(value, list):
            for index, item in enumerate(value):
                item_dict = _as_dict(item)
                rows.append({"id": f"{key}:{index}", **item_dict})
            continue
        item_dict = _as_dict(value)
        if item_dict:
            rows.append({"id": key, **item_dict})
    return rows


def _derive_geometry_hard_gates(geometry_vector: Mapping[str, Any]) -> dict[str, str]:
    graph_area = _number_or_none(geometry_vector.get("graph_region_area_ratio"))
    competing_area = _number_or_none(geometry_vector.get("rail_or_inspector_area_ratio"))
    node_count = _number_or_none(geometry_vector.get("node_rect_count"))
    label_coverage = _number_or_none(geometry_vector.get("visible_label_coverage"))

    gates: dict[str, str] = {
        "dominant_artifact_visible": "pass"
        if graph_area is not None and graph_area >= 0.25
        else ("watch" if graph_area is not None and graph_area >= 0.15 else "fail"),
        "graph_first_not_rail_dominated": "pass"
        if graph_area is not None and competing_area is not None and competing_area <= graph_area
        else ("watch" if graph_area is not None and competing_area is not None else "fail"),
        "node_geometry_available": "pass" if node_count is not None and node_count > 0 else "fail",
        "label_coverage_available": "pass"
        if label_coverage is not None and label_coverage >= 0.6
        else ("watch" if label_coverage is not None else "fail"),
    }
    return gates


def _geometry_calibration_profile(
    *,
    view_id: str,
    family: str,
    mode: str,
) -> dict[str, Any]:
    if view_id == "rootNavigator" and mode == "graph_first":
        return {
            "schema": GEOMETRY_CALIBRATION_PROFILE_SCHEMA_V1,
            "profile_id": "root_navigator_graph_first_v1",
            "view_id": view_id,
            "view_family": family,
            "mode": mode,
            "dominant_artifact": "root_unified_graph_canvas",
            "competing_regions": ["axis_rail", "inspector"],
            "thresholds": {
                "graph_region_area_ratio": {"pass_min": 0.35, "watch_min": 0.25},
                "competing_region_margin": {"pass_max_delta": 0.0, "watch_max_delta": 0.08},
                "node_rect_count": {"pass_min": 4, "watch_min": 1},
                "visible_label_coverage": {"pass_min": 0.6, "watch_min": 0.3},
            },
            "edge_path_policy": "visible_edges_expected_for_workbench_scene",
            "anti_gaming_note": "A live geometry vector cannot pass if graph area exists but competing chrome visually rivals the graph.",
        }
    return {
        "schema": GEOMETRY_CALIBRATION_PROFILE_SCHEMA_V1,
        "profile_id": "generic_graph_surface_graph_first_v1",
        "view_id": view_id,
        "view_family": family,
        "mode": mode,
        "dominant_artifact": "graph_canvas",
        "competing_regions": ["rail", "inspector", "overlay"],
        "thresholds": {
            "graph_region_area_ratio": {"pass_min": 0.35, "watch_min": 0.2},
            "competing_region_margin": {"pass_max_delta": 0.0, "watch_max_delta": 0.12},
            "node_rect_count": {"pass_min": 1, "watch_min": 1},
            "visible_label_coverage": {"pass_min": 0.5, "watch_min": 0.25},
        },
        "edge_path_policy": "visible_edges_preferred_unless_mode_declares_not_applicable",
        "anti_gaming_note": "Generic graph calibration is a first threshold profile, not a final component-unification verdict.",
    }


def _threshold_gate(value: float | int | None, *, pass_min: float, watch_min: float) -> str:
    if value is None:
        return "fail"
    if float(value) >= pass_min:
        return "pass"
    if float(value) >= watch_min:
        return "watch"
    return "fail"


def _competing_region_gate(
    *,
    graph_area: float | int | None,
    competing_area: float | int | None,
    profile: Mapping[str, Any],
) -> str:
    if graph_area is None:
        return "fail"
    if competing_area is None:
        return "pass"
    thresholds = _as_dict(_as_dict(profile.get("thresholds")).get("competing_region_margin"))
    pass_delta = float(thresholds.get("pass_max_delta") or 0.0)
    watch_delta = float(thresholds.get("watch_max_delta") or 0.08)
    delta = float(competing_area) - float(graph_area)
    if delta <= pass_delta:
        return "pass"
    if delta <= watch_delta:
        return "watch"
    return "fail"


def _edge_path_interpretation(
    *,
    view_id: str,
    mode: str,
    edge_count: float | int | None,
) -> dict[str, Any]:
    if edge_count is None:
        return {
            "status": "fail",
            "interpretation": "geometry_missing",
            "evidence_required": ["DOM selector check", "mode constitution"],
        }
    if int(edge_count) > 0:
        return {
            "status": "pass",
            "interpretation": "measured_visible_edges",
            "evidence_required": [],
        }
    if view_id == "rootNavigator" and mode == "graph_first":
        return {
            "status": "watch",
            "interpretation": "extractor_pending",
            "evidence_required": [
                "DOM selector check for data-zenith-root-workbench-edge",
                "screenshot review of visible relation lines",
                "mode constitution",
            ],
        }
    return {
        "status": "watch",
        "interpretation": "true_zero_or_not_applicable_by_constitution",
        "evidence_required": ["mode constitution", "screenshot review"],
    }


def _watch_resolution_for_violation(
    *,
    violation: str,
    view_id: str,
    mode: str,
    family: str,
    profile: Mapping[str, Any],
    geometry_vector: Mapping[str, Any],
    edge_interpretation: Mapping[str, Any],
) -> dict[str, Any]:
    graph_area = _number_or_none(geometry_vector.get("graph_region_area_ratio"))
    competing_area = _number_or_none(geometry_vector.get("rail_or_inspector_area_ratio"))
    node_count = _number_or_none(geometry_vector.get("node_rect_count"))
    edge_count = _number_or_none(geometry_vector.get("edge_path_count"))
    edge_policy = str(profile.get("edge_path_policy") or "")
    edge_status = str(edge_interpretation.get("interpretation") or "")

    resolution_class = "threshold_profile_gap"
    interpretation = "profile_review_required"
    next_owner_shape = "threshold_profile_review"
    evidence_required = ["fresh_geometry", "screenshot_review", "mode_constitution"]
    reason = "The calibrated watch has live evidence, but its threshold interpretation is not terminal."

    if violation == "competing_regions_rival_dominant_artifact":
        delta = (
            round(float(competing_area) - float(graph_area), 4)
            if graph_area is not None and competing_area is not None
            else None
        )
        if (
            view_id == "rootNavigator"
            and mode == "graph_first"
            and delta is not None
            and delta <= 0.03
        ):
            resolution_class = "threshold_profile_gap"
            interpretation = "close_margin_combined_chrome_area"
            next_owner_shape = "threshold_profile_review"
            reason = (
                "Root Navigator's summed rail/inspector area only slightly exceeds the graph; "
                "profile review should decide whether area sum or salience-weighted balance is the right target."
            )
        else:
            resolution_class = "scene_policy_gap"
            interpretation = "dominant_artifact_subordinate_to_chrome"
            next_owner_shape = "scene_policy_resolution"
            reason = (
                "The declared dominant graph artifact is geometrically subordinated to competing regions."
            )
    elif violation == "edge_geometry_ambiguous":
        if edge_status == "extractor_pending":
            resolution_class = "extractor_gap"
            interpretation = "edge_selector_or_extractor_pending"
            next_owner_shape = "extractor_resolution"
            evidence_required = ["DOM selector check", "screenshot edge review", "mode constitution"]
            reason = "The view expects visible edges, but the extractor still returned zero edge paths."
        elif edge_count == 0 and view_id == "graph" and graph_area is not None and graph_area >= 0.8:
            resolution_class = "scene_policy_gap"
            interpretation = "sparse_graph_scene_despite_dominant_canvas"
            next_owner_shape = "scene_policy_resolution"
            evidence_required = ["fresh_geometry", "screenshot_review", "graph_mode_constitution"]
            reason = (
                "The graph canvas dominates the viewport, but the rendered scene exposes no edges and too little topology."
            )
        elif edge_count == 0 and node_count is not None and node_count > 1:
            resolution_class = "extractor_gap"
            interpretation = "multi_node_zero_edge_extractor_suspect"
            next_owner_shape = "extractor_resolution"
            evidence_required = ["DOM selector check", "SVG edge selector audit", "screenshot edge review"]
            reason = "Multiple nodes with zero measured edges is more likely an extraction gap than a quality judgement."
        elif "not_applicable" in edge_policy:
            resolution_class = "acceptable_by_constitution"
            interpretation = "edge_paths_not_applicable_by_mode"
            next_owner_shape = "constitution_acceptance_profile"
            evidence_required = ["mode constitution"]
            reason = "This mode declares edge paths as not applicable, so the watch needs profile acceptance rather than UI repair."
        else:
            resolution_class = "scene_policy_gap"
            interpretation = "zero_visible_edges_in_graph_first_surface"
            next_owner_shape = "scene_policy_resolution"
            evidence_required = ["fresh_geometry", "screenshot edge review", "mode constitution"]
            reason = "The graph-first surface does not yet render enough edge structure to satisfy its graph constitution."

    return {
        "schema": CALIBRATED_WATCH_RESOLUTION_SCHEMA_V1,
        "view_id": view_id,
        "view_family": family,
        "mode": mode,
        "violation": violation,
        "resolution_class": resolution_class,
        "interpretation": interpretation,
        "next_owner_shape": next_owner_shape,
        "evidence_required": evidence_required,
        "evidence": {
            "graph_region_area_ratio": graph_area,
            "rail_or_inspector_area_ratio": competing_area,
            "node_rect_count": int(node_count) if isinstance(node_count, (int, float)) else None,
            "edge_path_count": int(edge_count) if isinstance(edge_count, (int, float)) else None,
        },
        "reason": reason,
    }


def _watch_resolution_next_owner_shape(resolutions: list[Mapping[str, Any]]) -> str | None:
    if not resolutions:
        return None
    priority = {
        "extractor_gap": 0,
        "scene_policy_gap": 1,
        "threshold_profile_gap": 2,
        "acceptable_by_constitution": 3,
    }
    selected = min(
        resolutions,
        key=lambda row: priority.get(str(row.get("resolution_class")), 99),
    )
    return str(selected.get("next_owner_shape") or "calibrated_watch_resolution")


def _resolution_action_for_watch_resolution(resolution: Mapping[str, Any]) -> dict[str, Any]:
    resolution_class = str(resolution.get("resolution_class") or "")
    action_template = RESOLUTION_ACTIONS_BY_CLASS.get(
        resolution_class,
        {
            "action": "resolution_review",
            "decision": "resolution_review_pending",
            "action_lane": "view_quality",
            "status": "open",
            "next_owner_shape": "calibrated_watch_resolution",
            "closure_condition": "Review the unresolved calibrated-watch row and emit a typed action.",
            "required_proof_refs": ["view_quality_before", "view_quality_after"],
            "refactor_relevance": "unclassified_watch_before_refactor",
            "component_unification_gate": "Do not use unresolved watch rows as refactor evidence.",
        },
    )
    view_id = str(resolution.get("view_id") or "")
    violation = str(resolution.get("violation") or "")
    decision = str(action_template["decision"])
    closure_condition = str(action_template["closure_condition"])
    if (
        view_id == "rootNavigator"
        and resolution_class == "threshold_profile_gap"
        and violation == "competing_regions_rival_dominant_artifact"
    ):
        decision = "threshold_refinement_pending"
        closure_condition = (
            "Decide whether close graph/chrome balance needs salience-weighted thresholds, "
            "constitution acceptance, or a reroute to scene-policy demotion."
        )
    elif view_id == "graph" and resolution_class == "scene_policy_gap":
        decision = "scene_policy_resolution_pending"
        closure_condition = (
            "Resolve sparse graph-first default as data_state_gap, true_zero_state, "
            "mode_not_applicable, or scene_policy_defect before component promotion."
        )

    return {
        "schema": VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1,
        "view_id": view_id,
        "view_family": resolution.get("view_family"),
        "mode": resolution.get("mode"),
        "resolution_class": resolution_class,
        "input_violation": violation,
        "source_resolution_schema": resolution.get("schema") or CALIBRATED_WATCH_RESOLUTION_SCHEMA_V1,
        "action": action_template["action"],
        "action_lane": action_template["action_lane"],
        "decision": decision,
        "status": action_template["status"],
        "next_owner_shape": resolution.get("next_owner_shape") or action_template["next_owner_shape"],
        "evidence": _as_dict(resolution.get("evidence")),
        "source_resolution": dict(resolution),
        "required_evidence": _as_list(resolution.get("evidence_required")),
        "required_proof_refs": list(action_template["required_proof_refs"]),
        "closure_condition": closure_condition,
        "refactor_intelligence": {
            "refactor_relevance": action_template["refactor_relevance"],
            "component_unification_gate": action_template["component_unification_gate"],
        },
        "selection_reason": (
            "A calibrated_watch resolution is diagnostic only; this receipt names the "
            "governed action lane and closure proof before UI mutation or component unification."
        ),
    }


def _selected_resolution_action(row: Mapping[str, Any]) -> dict[str, Any] | None:
    actions = [_as_dict(item) for item in _as_list(row.get("resolution_action_receipts"))]
    if not actions:
        return None
    action_priority = {
        "extractor_patch": 0,
        "scene_policy_resolution": 1,
        "threshold_profile_review": 2,
        "constitution_acceptance_record": 3,
    }
    return min(
        actions,
        key=lambda item: (
            action_priority.get(str(item.get("action")), 99),
            str(item.get("input_violation") or ""),
        ),
    )


def _action_score(action_row: Mapping[str, Any]) -> int:
    action_class = str(action_row.get("action_class") or "")
    action_label = str(action_row.get("action_label") or "")
    view_id = str(action_row.get("view_id") or "")
    family = str(action_row.get("view_family") or "")
    base_by_class = {
        "diagnosed_quality_gap": 100,
        "failed_quality_gap": 92,
        "geometry_evidence_gap": 84,
        "calibration_gap": 78,
        "rendered_geometry_gap": 72,
        "metric_depth_gap": 64,
        "measurement_contract_gap": 58,
        "census_binding_gap": 50,
        "accepted_difference": 10,
        "monitor": 4,
    }
    score = base_by_class.get(action_class, 40)
    if family in GRAPH_FAMILIES:
        score += 8
    if view_id in {"station", "rootNavigator", "graph", "codemap", "topology", "history"}:
        score += 4
    if action_label == "scene_policy_resolution":
        score += 6
    elif action_label == "extractor_patch":
        score += 5
    elif action_label == "threshold_profile_review":
        score += 4
    elif action_label in {"monitor_regression_guard", "accepted_no_ui_action"}:
        score = min(score, 20)
    return int(score)


def _view_quality_action_for_missing_view_id(view_id: str) -> dict[str, Any]:
    action = {
        "schema": VIEW_QUALITY_ACTION_ROW_SCHEMA_V1,
        "view_id": view_id,
        "view_family": "unknown",
        "grade": "not_yet_in_census",
        "measurement_tier": "not_yet_in_census",
        "calibration_status": "not_started",
        "action_class": "census_binding_gap",
        "action_label": "add_to_census_or_bind_capture",
        "action_lane": "capture_or_navigation_contract",
        "action_reason": "Requested view id did not resolve to a census row.",
        "next_owner_shape": "view_census_binding",
        "closure_condition": "Bind the view to frontend navigation/capture metadata so it appears in the census with a stable view_id.",
        "source_ref": "missing_requested_view_ids",
        "child_resolution_actions": [],
    }
    action["hot_action_score"] = _action_score(action)
    action["hot"] = False
    return action


def _view_quality_action_for_row(row: Mapping[str, Any]) -> dict[str, Any]:
    view_id = str(row.get("view_id") or "")
    family = str(row.get("view_family") or "")
    grade = str(row.get("grade") or "")
    tier = str(row.get("measurement_tier") or row.get("measurement_maturity") or grade)
    calibration_status = str(row.get("calibration_status") or "not_started")
    selected_resolution_action = _selected_resolution_action(row)
    resolution_actions = [
        _as_dict(item) for item in _as_list(row.get("resolution_action_receipts"))
    ]

    if selected_resolution_action:
        resolution_class = str(selected_resolution_action.get("resolution_class") or "")
        if resolution_class == "acceptable_by_constitution":
            action_class = "accepted_difference"
            action_label = "accepted_no_ui_action"
            action_lane = "no_ui_action"
            action_reason = "Calibrated watch is acceptable only after constitution/profile evidence is recorded."
        else:
            action_class = "diagnosed_quality_gap"
            action_label = str(selected_resolution_action.get("action") or "resolution_action")
            action_lane = str(selected_resolution_action.get("action_lane") or "resolution_action")
            action_reason = (
                f"calibrated_watch {resolution_class} on "
                f"{selected_resolution_action.get('input_violation') or 'unresolved_violation'}"
            )
        next_owner_shape = str(
            selected_resolution_action.get("next_owner_shape")
            or row.get("next_owner_shape")
            or "calibrated_watch_resolution"
        )
        closure_condition = str(
            selected_resolution_action.get("closure_condition")
            or "Close by changing the quality class, accepting the constitution, or repairing measurement evidence."
        )
        source_ref = VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1
    elif grade == "not_yet_in_census" or tier == "not_yet_in_census":
        action_class = "census_binding_gap"
        action_label = "add_to_census_or_bind_capture"
        action_lane = "capture_or_navigation_contract"
        action_reason = "View is known as a requested target but is not bound to a census row."
        next_owner_shape = "view_census_binding"
        closure_condition = "View appears in the census with a stable view_id and capture/navigation contract."
        source_ref = "view_quality_census_row"
    elif tier == "partial_unmeasured":
        action_class = "measurement_contract_gap"
        action_label = "contract_marker_patch"
        action_lane = "marker_or_capture_contract_patch"
        missing = ", ".join(str(item) for item in _as_list(row.get("missing_vectors"))) or "unknown_vectors"
        action_reason = f"Missing measurement vectors: {missing}."
        next_owner_shape = str(row.get("next_owner_shape") or "view_constitution_marker_patch")
        closure_condition = "Patch the semantic/capture/graph contract so missing_vectors decrease."
        source_ref = "missing_vectors"
    elif tier == "measured_watch_generic":
        action_class = "metric_depth_gap"
        action_label = "metric_receipt_upgrade"
        action_lane = "metric_receipt_upgrade"
        action_reason = "Generic markers make the view addressable, but no metric vector is available yet."
        next_owner_shape = str(row.get("next_owner_shape") or "metric_receipt_upgrade")
        closure_condition = "Emit a metric-quality receipt or metric vector for the declared constitution."
        source_ref = "measurement_tier"
    elif tier == "measured_watch_metric":
        action_class = "rendered_geometry_gap"
        action_label = "geometry_capture_bridge"
        action_lane = "station_render_geometry_bridge"
        action_reason = "Metric vector exists, but rendered geometry evidence is not available yet."
        next_owner_shape = str(row.get("next_owner_shape") or "metric_vector_capture_calibration")
        closure_condition = "Produce live geometry or record an explicit unavailable reason."
        source_ref = "measurement_tier"
    elif tier == "measured_watch_geometry":
        if calibration_status == "calibrated_pass":
            action_class = "monitor"
            action_label = "monitor_regression_guard"
            action_lane = "regression_guard"
            action_reason = "Rendered geometry passed its calibration profile."
            next_owner_shape = "view_quality_regression_guard"
            closure_condition = "No mutation required unless source or capture evidence changes."
        elif calibration_status == "geometry_watch":
            action_class = "geometry_evidence_gap"
            action_label = "currentness_or_geometry_repair"
            action_lane = "station_render_geometry_currentness"
            action_reason = "Geometry exists but is synthetic, stale, or not reviewable as live evidence."
            next_owner_shape = str(row.get("next_owner_shape") or "live_geometry_currentness_review")
            closure_condition = "Refresh or repair geometry evidence until live/current, or record an unavailable reason."
        elif calibration_status == "calibrated_watch":
            action_class = "diagnosed_quality_gap"
            action_label = "resolution_action"
            action_lane = "resolution_action"
            action_reason = "Calibration produced watch findings but no typed child resolution action is attached."
            next_owner_shape = str(row.get("next_owner_shape") or "calibrated_watch_resolution")
            closure_condition = "Attach a typed resolution action before UI mutation or component unification."
        else:
            action_class = "calibration_gap"
            action_label = "calibration_profile_review"
            action_lane = "threshold_profile_review"
            action_reason = "Rendered geometry exists but has not been interpreted by an accepted calibration profile."
            next_owner_shape = str(row.get("next_owner_shape") or "live_geometry_currentness_review")
            closure_condition = "Review thresholds/currentness and move to calibrated_watch, calibrated_pass, or geometry_watch with reason."
        source_ref = "geometry_calibration"
    elif grade == "measured_fail":
        action_class = "failed_quality_gap"
        action_label = "quality_failure_triage"
        action_lane = "view_quality_failure_triage"
        action_reason = "Hard view-quality gates failed for the declared constitution."
        next_owner_shape = str(row.get("next_owner_shape") or "quality_failure_triage")
        closure_condition = "Repair the failing proof lane or record a typed blocking reason."
        source_ref = "hard_gates"
    elif tier == "measured_pass" or grade == "measured_pass":
        action_class = "monitor"
        action_label = "monitor_regression_guard"
        action_lane = "regression_guard"
        action_reason = "Hard gates pass for the declared constitution."
        next_owner_shape = "view_quality_regression_guard"
        closure_condition = "No mutation required unless source or capture evidence changes."
        source_ref = "measurement_tier"
    else:
        action_class = "metric_depth_gap"
        action_label = "metric_receipt_upgrade"
        action_lane = "metric_receipt_upgrade"
        action_reason = "View is measured-watch but lacks a deeper metric action."
        next_owner_shape = str(row.get("next_owner_shape") or "metric_receipt_upgrade")
        closure_condition = "Emit a metric-quality receipt or record why the view cannot be measured deeper."
        source_ref = "measurement_tier"

    action = {
        "schema": VIEW_QUALITY_ACTION_ROW_SCHEMA_V1,
        "view_id": view_id,
        "view_family": family,
        "grade": grade,
        "measurement_tier": tier,
        "calibration_status": calibration_status,
        "action_class": action_class,
        "action_label": action_label,
        "action_lane": action_lane,
        "action_reason": action_reason,
        "next_owner_shape": next_owner_shape,
        "closure_condition": closure_condition,
        "source_ref": source_ref,
        "child_resolution_actions": resolution_actions,
    }
    action["hot_action_score"] = _action_score(action)
    action["hot"] = False
    return action


def _geometry_calibration_review(
    *,
    row: Mapping[str, Any],
    geometry_vector: Mapping[str, Any] | None,
    screenshot_ledger: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not geometry_vector:
        return None
    view_id = str(row.get("view_id") or "")
    family = str(row.get("view_family") or "")
    mode = str(row.get("mode") or geometry_vector.get("viewport_mode") or "graph_first")
    profile = _geometry_calibration_profile(view_id=view_id, family=family, mode=mode)
    thresholds = _as_dict(profile.get("thresholds"))
    graph_area = _number_or_none(geometry_vector.get("graph_region_area_ratio"))
    competing_area = _number_or_none(geometry_vector.get("rail_or_inspector_area_ratio"))
    node_count = _number_or_none(geometry_vector.get("node_rect_count"))
    edge_count = _number_or_none(geometry_vector.get("edge_path_count"))
    label_coverage = _number_or_none(geometry_vector.get("visible_label_coverage"))
    evidence_kind = str(geometry_vector.get("evidence_kind") or "")
    screenshot_status = str(_as_dict(screenshot_ledger).get("status") or "missing_screenshot_context")

    gates: dict[str, str] = {
        "geometry_summary_live_not_synthetic": "pass" if evidence_kind == "live_dom_capture" else "watch",
        "geometry_current_with_source": "pass" if screenshot_status == "fresh" else "watch",
        "graph_region_not_subordinate_to_competing_regions": _competing_region_gate(
            graph_area=graph_area,
            competing_area=competing_area,
            profile=profile,
        ),
        "node_geometry_plausible": _threshold_gate(
            node_count,
            pass_min=float(_as_dict(thresholds.get("node_rect_count")).get("pass_min") or 1),
            watch_min=float(_as_dict(thresholds.get("node_rect_count")).get("watch_min") or 1),
        ),
        "label_coverage_available": _threshold_gate(
            label_coverage,
            pass_min=float(_as_dict(thresholds.get("visible_label_coverage")).get("pass_min") or 0.5),
            watch_min=float(_as_dict(thresholds.get("visible_label_coverage")).get("watch_min") or 0.25),
        ),
        "dominant_artifact_visible": _threshold_gate(
            graph_area,
            pass_min=float(_as_dict(thresholds.get("graph_region_area_ratio")).get("pass_min") or 0.35),
            watch_min=float(_as_dict(thresholds.get("graph_region_area_ratio")).get("watch_min") or 0.2),
        ),
    }
    edge_interpretation = _edge_path_interpretation(view_id=view_id, mode=mode, edge_count=edge_count)
    gates["edge_geometry_plausible_or_explicitly_not_applicable"] = str(edge_interpretation["status"])

    watch_gates = sorted(gate for gate, status in gates.items() if status == "watch")
    failed_gates = sorted(gate for gate, status in gates.items() if status == "fail")
    pass_gates = sorted(gate for gate, status in gates.items() if status == "pass")
    if gates["geometry_summary_live_not_synthetic"] != "pass" or gates["geometry_current_with_source"] != "pass":
        status = "geometry_watch"
    elif failed_gates or watch_gates:
        status = "calibrated_watch"
    else:
        status = "calibrated_pass"

    violations: list[str] = []
    if gates["graph_region_not_subordinate_to_competing_regions"] != "pass":
        violations.append("competing_regions_rival_dominant_artifact")
    if gates["edge_geometry_plausible_or_explicitly_not_applicable"] != "pass":
        violations.append("edge_geometry_ambiguous")
    if gates["geometry_summary_live_not_synthetic"] != "pass":
        violations.append("synthetic_or_unreviewed_geometry")
    if gates["geometry_current_with_source"] != "pass":
        violations.append("geometry_not_current_with_screenshot")

    unique_violations = sorted(set(violations))
    watch_resolutions = (
        [
            _watch_resolution_for_violation(
                violation=violation,
                view_id=view_id,
                mode=mode,
                family=family,
                profile=profile,
                geometry_vector=geometry_vector,
                edge_interpretation=edge_interpretation,
            )
            for violation in unique_violations
        ]
        if status == "calibrated_watch"
        else []
    )
    resolution_class_counts = Counter(
        str(row.get("resolution_class")) for row in watch_resolutions
    )

    return {
        "schema": GEOMETRY_CALIBRATION_REVIEW_SCHEMA_V1,
        "status": status,
        "profile": profile,
        "hard_gates": gates,
        "pass_gates": pass_gates,
        "watch_gates": watch_gates,
        "failed_gates": failed_gates,
        "edge_path_count": {
            "value": int(edge_count) if isinstance(edge_count, (int, float)) else None,
            **edge_interpretation,
        },
        "evidence": {
            "evidence_kind": evidence_kind,
            "screenshot_status": screenshot_status,
            "graph_region_area_ratio": graph_area,
            "rail_or_inspector_area_ratio": competing_area,
            "node_rect_count": int(node_count) if isinstance(node_count, (int, float)) else None,
            "visible_label_coverage": label_coverage,
        },
        "violations": unique_violations,
        "watch_resolutions": watch_resolutions,
        "resolution_class_counts": dict(sorted(resolution_class_counts.items())),
        "selection_reason": (
            "Rendered geometry was interpreted through a calibration profile; "
            "numbers exist is not treated as calibrated quality."
        ),
    }


def _geometry_vector_from_summary(
    summary: Mapping[str, Any] | None,
    *,
    mode: str,
) -> dict[str, Any] | None:
    if not isinstance(summary, Mapping):
        return None
    schema = str(summary.get("schema") or "")
    if schema not in {
        ROOT_NAVIGATOR_CAPTURE_SUMMARY_SCHEMA_V1,
        VIEW_GEOMETRY_CAPTURE_SUMMARY_SCHEMA_V1,
    }:
        return None

    regions = _as_dict(summary.get("regions"))
    graph_metrics = _as_dict(summary.get("graph_metrics"))
    dominant = _as_dict(regions.get("dominant_artifact"))
    axis_rail = _as_dict(regions.get("axis_rail"))
    inspector = _as_dict(regions.get("inspector"))
    rails = [_as_dict(item) for item in _as_list(regions.get("rails"))]

    graph_area = _area_ratio(dominant)
    axis_area = _area_ratio(axis_rail)
    inspector_area = _area_ratio(inspector)
    rail_area = sum(_area_ratio(rail) or 0.0 for rail in rails) if rails else None
    competing_parts = [value for value in (axis_area, inspector_area, rail_area) if value is not None]
    competing_area = round(sum(competing_parts), 4) if competing_parts else None

    node_count = _number_or_none(graph_metrics.get("node_rect_count"))
    edge_count = _number_or_none(graph_metrics.get("edge_path_count"))
    node_union = _number_or_none(graph_metrics.get("node_union_to_graph_region"))
    label_coverage = _number_or_none(graph_metrics.get("visible_label_coverage"))
    visible_label_count = _number_or_none(graph_metrics.get("visible_label_count"))
    edge_density = _number_or_none(graph_metrics.get("edge_density"))
    salience_rank = None
    if graph_area is not None and competing_parts:
        salience_rank = 1 if graph_area >= max(competing_parts) else 2

    geometry_vector = {
        "schema": GEOMETRY_VECTOR_SCHEMA_V1,
        "source_schema": schema,
        "source": "dom_capture_summary",
        "evidence_kind": summary.get("evidence_kind") or "capture_summary",
        "geometry_currentness": summary.get("geometry_currentness") or "capture_summary_currentness_unreviewed",
        "viewport_mode": mode,
        "capture_context": _as_dict(summary.get("capture_context")),
        "graph_region_area_ratio": graph_area,
        "axis_rail_area_ratio": axis_area,
        "inspector_area_ratio": inspector_area,
        "rail_area_ratio": rail_area,
        "rail_or_inspector_area_ratio": competing_area,
        "node_rect_count": int(node_count) if isinstance(node_count, (int, float)) else None,
        "edge_path_count": int(edge_count) if isinstance(edge_count, (int, float)) else None,
        "node_union_to_graph_region": round(float(node_union), 4) if node_union is not None else None,
        "visible_label_count": int(visible_label_count) if isinstance(visible_label_count, (int, float)) else None,
        "visible_label_coverage": round(float(label_coverage), 4) if label_coverage is not None else None,
        "edge_density": round(float(edge_density), 4) if edge_density is not None else None,
        "dominant_artifact_salience_rank": salience_rank,
    }
    geometry_vector["hard_gates"] = _derive_geometry_hard_gates(geometry_vector)
    summary_gates = _as_dict(summary.get("hard_gates"))
    if summary_gates:
        geometry_vector["source_hard_gates"] = summary_gates
    return geometry_vector


def _metric_vector_with_geometry(
    metric_vector: dict[str, Any] | None,
    geometry_vector: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if metric_vector is None or geometry_vector is None:
        return metric_vector
    merged = dict(metric_vector)
    for key in (
        "graph_region_area_ratio",
        "rail_or_inspector_area_ratio",
        "node_rect_count",
        "edge_path_count",
        "node_union_to_graph_region",
        "visible_label_coverage",
    ):
        if geometry_vector.get(key) is not None:
            merged[key] = geometry_vector.get(key)
    if geometry_vector.get("node_rect_count") is not None:
        merged["node_rect_count_source"] = "dom_capture_summary"
    if geometry_vector.get("edge_path_count") is not None:
        merged["edge_path_count_source"] = "dom_capture_summary"
    merged["source"] = "static_marker_contract_plus_dom_capture_summary"
    merged["geometry_vector_schema"] = geometry_vector.get("schema")
    merged["calibration_limit"] = (
        "Geometry populated from a capture summary; screenshot/operator threshold review still pending."
    )
    return merged


def _measurement_tier(
    *,
    grade: str,
    family: str,
    signature: dict[str, Any] | None,
    metric_vector: dict[str, Any] | None,
    geometry_vector: dict[str, Any] | None,
    missing_vectors: list[str],
) -> str:
    if grade == "not_yet_in_census":
        return "not_yet_in_census"
    if grade == "measured_fail":
        return "measured_fail"
    if missing_vectors:
        return "partial_unmeasured"
    if grade == "measured_pass":
        return "measured_pass"
    if metric_vector and geometry_vector:
        return "measured_watch_geometry"
    if metric_vector:
        return "measured_watch_metric"
    if family in GRAPH_FAMILIES and signature and signature.get("quality_receipt_source") == "generic_view_quality_marker":
        return "measured_watch_generic"
    if grade == "measured_watch":
        return "measured_watch_generic"
    return grade


def _calibration_status(measurement_tier: str) -> str:
    if measurement_tier == "measured_watch_geometry":
        return "geometry_pending_review"
    if measurement_tier == "calibrated_watch":
        return "calibrated_watch"
    if measurement_tier == "measured_watch_metric":
        return "screenshot_pending"
    if measurement_tier == "measured_pass":
        return "surface_atlas_visual_truth_microcosm"
    if measurement_tier == "measured_watch_generic":
        return "not_started"
    if measurement_tier == "partial_unmeasured":
        return "blocked_missing_vectors"
    return "not_started"


def _grade_row(
    *,
    family: str,
    has_capture_contract: bool,
    signature: dict[str, Any] | None,
    missing_vectors: list[str],
    hard_gates: dict[str, str],
) -> str:
    if not has_capture_contract:
        return "not_yet_in_census"
    if hard_gates.get("dominant_artifact_contract_present") == "fail":
        return "measured_fail"
    if family in GRAPH_FAMILIES:
        if not signature:
            return "partial_unmeasured"
        minimum = ["emits_node_rects", "emits_edge_paths", "emits_region_markers", "emits_quality_receipt"]
        if all(signature.get(field) for field in minimum):
            if signature.get("quality_receipt_source") == "surface_atlas_scene_candidate" and not missing_vectors:
                return "measured_pass"
            return "measured_watch"
        return "partial_unmeasured"
    return "partial_unmeasured" if missing_vectors else "measured_watch"


def _objective_vector(
    *,
    family: str,
    has_capture_contract: bool,
    latest_capture_status: str | None,
    signature: dict[str, Any] | None,
    geometry_vector: dict[str, Any] | None = None,
) -> dict[str, float | None]:
    implementation_score = None
    graph_readability = None
    visual_truth = None
    responsive_survival = None
    if family in GRAPH_FAMILIES and signature:
        fields = ["emits_node_rects", "emits_edge_paths", "emits_region_markers", "emits_quality_receipt"]
        implementation_score = round(sum(1 for field in fields if signature.get(field)) / len(fields), 2)
        graph_readability = 0.55 if signature.get("emits_node_rects") and signature.get("emits_edge_paths") else None
        visual_truth = 0.62 if signature.get("emits_quality_receipt") else None
        responsive_survival = 0.6 if signature.get("camera_policy") != "unknown" else None
    if geometry_vector:
        if geometry_vector.get("node_rect_count") and geometry_vector.get("edge_path_count"):
            graph_readability = 0.68
        if geometry_vector.get("graph_region_area_ratio") is not None:
            visual_truth = max(visual_truth or 0, 0.7)
        if geometry_vector.get("rail_or_inspector_area_ratio") is not None:
            responsive_survival = max(responsive_survival or 0, 0.64)

    return {
        "constitutional_effectiveness": 0.65 if has_capture_contract else None,
        "graph_readability": graph_readability,
        "spacing_rhythm": None,
        "color_system_fit": None,
        "visual_clutter": None,
        "responsive_survival": responsive_survival,
        "interaction_smoothness": None,
        "implementation_divergence": implementation_score,
        "visual_truth": visual_truth,
        "capture_currentness": 1.0 if latest_capture_status == "captured" else (0.5 if latest_capture_status else None),
    }


def _source_paths_for_view(view: Mapping[str, Any]) -> list[Path]:
    paths: list[Path] = [DEFAULT_NAVIGATION_GRAPH, DEFAULT_STATION_VIEWS]
    seen: set[Path] = set(paths)
    audit = _as_dict(view.get("surface_audit"))
    primary = audit.get("primary_component")
    if isinstance(primary, str) and primary.startswith("system/server/ui/src/"):
        path = REPO_ROOT / primary
        if path not in seen:
            paths.append(path)
            seen.add(path)
    component = _primary_component_name(view)
    for rel_path in COMPONENT_SOURCE_HINTS.get(component, []):
        path = REPO_ROOT / rel_path
        if path not in seen:
            paths.append(path)
            seen.add(path)
    for ref in _evidence_refs(view):
        path = _source_path_from_ref(ref)
        if path is None or path in seen:
            continue
        paths.append(path)
        seen.add(path)
    return paths


def _newest_source_snapshot(paths: list[Path]) -> dict[str, Any]:
    existing: list[tuple[Path, _dt.datetime]] = []
    missing: list[str] = []
    for path in paths:
        mtime = _mtime(path)
        if mtime is None:
            missing.append(_rel(path))
        else:
            existing.append((path, mtime))
    newest = max(existing, key=lambda item: item[1]) if existing else None
    return {
        "source_paths": [_rel(path) for path, _ in existing],
        "missing_source_paths": missing,
        "newest_source_path": _rel(newest[0]) if newest else None,
        "newest_source_mtime": _iso(newest[1]) if newest else None,
    }


def _normalize_changed_paths(changed_paths: list[str] | None) -> list[str]:
    normalized: list[str] = []
    for raw in changed_paths or []:
        path = Path(raw)
        if path.is_absolute():
            try:
                normalized.append(str(path.relative_to(REPO_ROOT)))
            except ValueError:
                normalized.append(str(path))
        else:
            normalized.append(str(path))
    return sorted(set(normalized))


def _changed_path_affects_view(
    *,
    changed_paths: list[str],
    view_source_paths: list[Path],
) -> tuple[bool, list[str], str]:
    if not changed_paths:
        return False, [], "no_changed_path_context"
    source_rel = {_rel(path) for path in view_source_paths}
    matched: list[str] = []
    global_frontend_paths = (
        "system/server/ui/src/App.tsx",
        "system/server/ui/src/main.tsx",
        "system/server/ui/src/index.css",
        "system/server/ui/src/navigation/",
        "system/server/ui/src/api/",
        "tools/meta/observability/station_views.json",
        "state/frontend_navigation/navigation_graph.json",
    )
    for changed in changed_paths:
        if changed in source_rel:
            matched.append(changed)
            continue
        if any(changed == prefix.rstrip("/") or changed.startswith(prefix) for prefix in global_frontend_paths):
            matched.append(changed)
            continue
        if changed.startswith("system/server/ui/src/") and not source_rel:
            matched.append(changed)
    if matched:
        return True, sorted(set(matched)), "direct_or_global_frontend_source_match"
    if any(changed.startswith("system/server/ui/src/") for changed in changed_paths):
        return True, sorted(set(changed_paths)), "conservative_frontend_source_match"
    return False, [], "no_view_coupling_match"


def _latest_render_for_view(
    *,
    capture_slug: str | None,
    render_load_index: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if not capture_slug:
        return {}
    row = _as_dict(_as_dict((render_load_index or {}).get("views")).get(capture_slug))
    latest = _as_dict(row.get("latest") or row.get("latest_promoted") or row.get("latest_attempt"))
    if not latest:
        return {}
    compact_keys = (
        "recorded_at",
        "run_stamp",
        "receipt_ref",
        "receipt_path",
        "engine",
        "viewport_slug",
        "route",
        "status",
        "load_ms",
        "ready_ms",
        "output_path",
        "preload_output_path",
        "geometry_summary_path",
        "geometry_summary_schema",
        "visual_delta_schema",
        "visual_delta_status",
        "visual_delta_review_status",
        "visual_delta_receipt_path",
        "visual_delta_prior_output_path",
        "visual_delta_diff_output_path",
        "visual_delta_changed_pixels",
        "visual_delta_changed_percent",
        "visual_delta_threshold_percent",
        "error_kind",
        "error_message",
        "readiness_attrs",
    )
    compact = {key: latest.get(key) for key in compact_keys if key in latest}
    compact["latest_required_engine_coverage"] = row.get("latest_required_engine_coverage")
    return compact


def _build_screenshot_ledger(
    *,
    capture_slug: str | None,
    view_source_paths: list[Path],
    render_load_index: Mapping[str, Any] | None,
    changed_paths: list[str],
) -> dict[str, Any]:
    latest = _latest_render_for_view(capture_slug=capture_slug, render_load_index=render_load_index)
    source_snapshot = _newest_source_snapshot(view_source_paths)
    affects_view, matched_paths, coupling_reason = _changed_path_affects_view(
        changed_paths=changed_paths,
        view_source_paths=view_source_paths,
    )
    output_path = latest.get("output_path")
    output_abs = REPO_ROOT / str(output_path) if output_path else None
    artifact_exists = bool(output_abs and output_abs.exists())
    captured_at = _parse_time(latest.get("recorded_at")) or (_mtime(output_abs) if output_abs else None)
    source_mtime = _parse_time(source_snapshot.get("newest_source_mtime"))

    if not capture_slug:
        status = "not_bound_to_station_render"
    elif not latest:
        status = "missing_render"
    elif latest.get("status") != "captured":
        status = "latest_attempt_failed"
    elif not artifact_exists:
        status = "missing_screenshot_artifact"
    elif source_mtime and captured_at and source_mtime > captured_at:
        status = "stale_source_newer_than_screenshot"
    elif affects_view:
        status = "due_changed_path"
    else:
        status = "fresh"

    refresh_due = status != "fresh"
    viewport = str(latest.get("viewport_slug") or "fhd_landscape")
    engine = str(latest.get("engine") or "chromium")
    refresh_command = (
        f"./repo-python -m tools.meta.observability.station_render render "
        f"--view {capture_slug} --engine {engine} --viewport {viewport}"
        if capture_slug
        else None
    )
    return {
        "schema": SCREENSHOT_LEDGER_SCHEMA_V0,
        "source": "state/observability/render_load_index.json_plus_station_render_receipts",
        "capture_slug": capture_slug,
        "status": status,
        "refresh_due": refresh_due,
        "refresh_reason": status,
        "refresh_command": refresh_command,
        "changed_path_coupling": {
            "status": "affected" if affects_view else "not_affected",
            "reason": coupling_reason,
            "changed_paths": changed_paths,
            "matched_paths": matched_paths,
        },
        "latest_screenshot": {
            "output_path": output_path,
            "geometry_summary_path": latest.get("geometry_summary_path"),
            "geometry_summary_schema": latest.get("geometry_summary_schema"),
            "visual_delta_schema": latest.get("visual_delta_schema"),
            "visual_delta_status": latest.get("visual_delta_status"),
            "visual_delta_review_status": latest.get("visual_delta_review_status"),
            "visual_delta_receipt_path": latest.get("visual_delta_receipt_path"),
            "visual_delta_prior_output_path": latest.get("visual_delta_prior_output_path"),
            "visual_delta_diff_output_path": latest.get("visual_delta_diff_output_path"),
            "visual_delta_changed_pixels": latest.get("visual_delta_changed_pixels"),
            "visual_delta_changed_percent": latest.get("visual_delta_changed_percent"),
            "visual_delta_threshold_percent": latest.get("visual_delta_threshold_percent"),
            "artifact_exists": artifact_exists,
            "recorded_at": latest.get("recorded_at"),
            "captured_at": _iso(captured_at),
            "run_stamp": latest.get("run_stamp"),
            "engine": latest.get("engine"),
            "viewport_slug": latest.get("viewport_slug"),
            "status": latest.get("status"),
            "receipt_ref": latest.get("receipt_ref"),
            "receipt_path": latest.get("receipt_path"),
            "readiness_attrs": latest.get("readiness_attrs"),
            "latest_required_engine_coverage": latest.get("latest_required_engine_coverage"),
        },
        "source_freshness": source_snapshot,
        "update_policy": {
            "frontend_source_change": "refresh the affected view packet and station_render screenshot",
            "uncertain_coupling": "conservatively treat frontend source edits as screenshot-due until a view-source map proves otherwise",
            "generated_projection_role": "latest screenshot index is a projection; durable proof is the station_render per-run manifest",
        },
    }


def _data_attrs(selector: str, limit: int = 14) -> list[str]:
    attrs = sorted(set(re.findall(r"data-[a-zA-Z0-9_-]+", selector or "")))
    return attrs[:limit]


def _scene_record(row: Mapping[str, Any]) -> dict[str, Any]:
    family = str(row.get("view_family") or "artifact_review")
    continuity_by_family = {
        "atlas_map": "system_hologram",
        "graph_surface": "navigation_topology",
        "operator_cockpit": "agent_metabolism_loop",
        "document": "principle_mechanism_chain",
        "timeline": "public_workitem_loop",
        "artifact_review": "public_workitem_loop",
    }
    scene_species_by_family = {
        "atlas_map": "atlas",
        "graph_surface": "topology",
        "operator_cockpit": "cockpit",
        "document": "artifact_review",
        "timeline": "proof_spine",
        "artifact_review": "artifact_review",
    }
    constitution = _as_dict(row.get("constitution"))
    title = str(row.get("title") or row.get("view_id") or "view")
    purpose = str(row.get("purpose") or "project the relevant substrate for operator action")
    return {
        "scene_id": row.get("view_id"),
        "continuity_object": continuity_by_family.get(family, "public_workitem_loop"),
        "scene_species": scene_species_by_family.get(family, "artifact_review"),
        "shell_mode": row.get("mode"),
        "operator_question": f"What can I decide or verify from {title} without leaving the frontend?",
        "teleology": {
            "purpose": purpose,
            "job_to_be_done": f"Let the operator inspect {purpose}",
            "done_when": "the dominant artifact is visible, source-backed, capture-ready, and screenshot-fresh",
        },
        "proof_obligations": [
            "capture contract present",
            "view quality census row present",
            "latest screenshot artifact linked or refresh due is explicit",
            "dominant artifact and stale/blocked state are visible rather than implied",
        ],
        "dominant_artifact": constitution.get("dominant_artifact"),
        "must_show_strata": constitution.get("must_be_visible", []),
        "must_demote_strata": constitution.get("may_defer", []),
        "release_boundary": "private_runtime_projection",
    }


def _design_principles_for_row(row: Mapping[str, Any]) -> list[dict[str, str]]:
    family = str(row.get("view_family") or "")
    selected = [
        ("P1", "scene-before-page", "the packet starts from operator scene and dominant artifact"),
        ("P2", "dominant visual model before metric labels", "quality is judged against the main artifact, not badges"),
        ("P5", "substrate-first; React is projection", "runtime facts route through graph, manifest, and receipts"),
        ("P7", "honest gates over fake green", "missing or stale screenshots become explicit refresh_due state"),
        ("P10", "visual receipt as proof", "station_render screenshot and manifest are first-class evidence"),
    ]
    if family in GRAPH_FAMILIES:
        selected.extend(
            [
                ("P3", "routes through card interiors", "graph surfaces must expose geometry and route semantics"),
                ("P4", "holographic band ladder", "view packets connect flag/card/capture/evidence layers"),
            ]
        )
    if family == "atlas_map":
        selected.extend(
            [
                ("P8", "compact resting chrome", "rails and legends must stay subordinate to the Atlas"),
                ("P12", "dark shell plus muted signal", "Atlas-native color roles remain the default"),
            ]
        )
    if family == "operator_cockpit":
        selected.append(("P6", "inspector is contextual", "operational metadata belongs in contextual rails"))
    selected.append(("P13", "reject alien product identity claims", "view packet keeps System Atlas / Root Navigator vocabulary"))
    return [
        {
            "id": principle_id,
            "label": label,
            "applies_because": applies_because,
        }
        for principle_id, label, applies_because in selected
    ]


def _expected_visible_landmarks(
    *,
    row: Mapping[str, Any],
    capture_contract: Mapping[str, Any],
    signature: Mapping[str, Any] | None,
) -> list[str]:
    constitution = _as_dict(row.get("constitution"))
    landmarks = [str(item) for item in _as_list(constitution.get("must_be_visible"))]
    dominant = constitution.get("dominant_artifact")
    if dominant:
        landmarks.insert(0, f"dominant_artifact:{dominant}")
    for attr in _data_attrs(str(capture_contract.get("ready_selector") or "")):
        landmarks.append(f"ready_attr:{attr}")
    if signature:
        landmarks.append(f"graph_layout:{signature.get('layout_engine')}")
        landmarks.append(f"camera_policy:{signature.get('camera_policy')}")
    return list(dict.fromkeys(landmarks))[:18]


def _visual_delta_status(
    *,
    latest_screenshot: Mapping[str, Any],
    changed_path_coupling: Mapping[str, Any],
) -> str:
    raw_status = str(latest_screenshot.get("visual_delta_status") or "")
    review_status = str(latest_screenshot.get("visual_delta_review_status") or "")
    affected_by_changed_path = (
        changed_path_coupling.get("status") == "affected"
        and bool(changed_path_coupling.get("changed_paths"))
    )
    if raw_status == "no_material_visual_delta" or review_status == "no_material_visual_delta":
        return "no_material_visual_delta"
    if raw_status == "no_prior_comparable" or review_status == "baseline_pending":
        return "baseline_pending"
    if raw_status == "material_visual_delta" and affected_by_changed_path:
        return "expected_by_changed_path"
    if raw_status or review_status:
        return "review_needed"
    return "missing_delta_receipt"


def _build_latest_visual_delta(
    *,
    latest_screenshot: Mapping[str, Any],
    screenshot_ledger: Mapping[str, Any],
    scene_record: Mapping[str, Any],
    expected_landmarks: list[str],
    design_principles: list[Mapping[str, str]],
) -> dict[str, Any]:
    changed_path_coupling = _as_dict(screenshot_ledger.get("changed_path_coupling"))
    status = _visual_delta_status(
        latest_screenshot=latest_screenshot,
        changed_path_coupling=changed_path_coupling,
    )
    teleology = _as_dict(scene_record.get("teleology"))
    return {
        "schema": VIEW_OBSERVATION_VISUAL_DELTA_SCHEMA_V1,
        "source": "station_render_visual_delta_receipt_via_render_load_index",
        "station_render_schema": latest_screenshot.get("visual_delta_schema"),
        "status": status,
        "raw_status": latest_screenshot.get("visual_delta_status"),
        "review_status": latest_screenshot.get("visual_delta_review_status"),
        "receipt_path": latest_screenshot.get("visual_delta_receipt_path"),
        "prior_output_path": latest_screenshot.get("visual_delta_prior_output_path"),
        "current_output_path": latest_screenshot.get("output_path"),
        "diff_output_path": latest_screenshot.get("visual_delta_diff_output_path"),
        "changed_pixels": latest_screenshot.get("visual_delta_changed_pixels"),
        "changed_percent": latest_screenshot.get("visual_delta_changed_percent"),
        "threshold_changed_percent": latest_screenshot.get("visual_delta_threshold_percent"),
        "changed_path_context": changed_path_coupling,
        "constitution_frame": {
            "purpose": teleology.get("purpose"),
            "dominant_artifact": scene_record.get("dominant_artifact"),
            "expected_landmarks": expected_landmarks[:12],
            "design_principle_ids": [
                str(principle.get("id"))
                for principle in design_principles
                if principle.get("id")
            ],
            "interpretation_rule": (
                "pixel delta is advisory until read through the view purpose, "
                "dominant artifact, landmarks, and changed-path coupling"
            ),
        },
    }


def build_view_observation_packet(
    *,
    view: Mapping[str, Any],
    row: Mapping[str, Any],
    capture_contract: Mapping[str, Any],
    render_load_index: Mapping[str, Any] | None,
    changed_paths: list[str],
) -> dict[str, Any]:
    source_paths = _source_paths_for_view(view)
    screenshot_ledger = _build_screenshot_ledger(
        capture_slug=str(row.get("capture_slug") or "") or None,
        view_source_paths=source_paths,
        render_load_index=render_load_index,
        changed_paths=changed_paths,
    )
    signature = _as_dict(row.get("graph_surface_signature"))
    scene_record = _scene_record(row)
    expected_landmarks = _expected_visible_landmarks(
        row=row,
        capture_contract=capture_contract,
        signature=signature,
    )
    design_principles = _design_principles_for_row(row)
    latest_visual_delta = _build_latest_visual_delta(
        latest_screenshot=_as_dict(screenshot_ledger.get("latest_screenshot")),
        screenshot_ledger=screenshot_ledger,
        scene_record=scene_record,
        expected_landmarks=expected_landmarks,
        design_principles=design_principles,
    )
    return {
        "schema": VIEW_OBSERVATION_PACKET_SCHEMA_V0,
        "view_id": row.get("view_id"),
        "title": row.get("title"),
        "route": row.get("route"),
        "capture_slug": row.get("capture_slug"),
        "packet_role": "ai_visual_ground_truth_and_frontend_view_contract",
        "authority_boundary": "projection_over_navigation_graph_station_views_render_load_index_and_view_quality_census",
        "scene_record": scene_record,
        "what_agent_should_see": expected_landmarks,
        "design_principles_applied": design_principles,
        "raw_principle_refs": ["pri_058", "pri_104", "pri_109", "pri_110", "pri_114"],
        "quality_census": {
            "grade": row.get("grade"),
            "measurement_tier": row.get("measurement_tier"),
            "calibration_status": row.get("calibration_status"),
            "missing_vectors": row.get("missing_vectors", []),
            "violations": row.get("violations", []),
            "next_owner_shape": row.get("next_owner_shape"),
        },
        "screenshot_ledger": screenshot_ledger,
        "latest_visual_delta": latest_visual_delta,
        "discoverability": _view_memory_discoverability(row.get("view_id")),
        "change_coupling": {
            "watched_source_paths": [_rel(path) for path in source_paths],
            "global_hook_trigger_paths": [
                "system/server/ui/src/**",
                "tools/meta/observability/station_views.json",
                "state/frontend_navigation/navigation_graph.json",
            ],
            "post_edit_refresh_rule": "run the census with --changed-path for edited files; rows with screenshot_ledger.refresh_due=true need station_render refresh",
        },
        "source_refs": row.get("source_refs", {}),
        "observation_commands": {
            "open_view_card": f"./repo-python kernel.py --option-surface frontend_views --band card --ids {row.get('view_id')}",
            "refresh_census": "./repo-python tools/meta/observability/view_quality_census.py --all --out state/observability/view_quality/frontend_view_quality_census_v0.json --write-view-packets --write-visual-settlement",
            "refresh_screenshot": screenshot_ledger.get("refresh_command"),
        },
    }


def build_view_quality_row(
    view: Mapping[str, Any],
    station_view_index: Mapping[str, dict[str, Any]],
    geometry_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    render_load_index: Mapping[str, Any] | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    capture = _as_dict(view.get("capture"))
    manifest_capture = _as_dict(station_view_index.get(_capture_slug(view) or ""))
    capture_contract = capture or manifest_capture
    family = classify_view_family(view, capture_contract)
    mode = default_mode_for_family(family)
    source_text = _read_source_text(view)
    signature = build_graph_surface_signature(view, source_text) if family in GRAPH_FAMILIES else None
    quality_receipt_source = (
        str(signature.get("quality_receipt_source"))
        if signature
        else _quality_receipt_source_from_text(source_text)
    )

    ready_selector = str(capture_contract.get("ready_selector") or "")
    latest_capture_status = _as_dict(_as_dict(capture.get("load_timing")).get("latest_required_engine_coverage")).get("captured")
    latest_status = _as_dict(capture.get("load_timing")).get("latest_status")
    has_capture_contract = bool(capture_contract)
    hard_gates: dict[str, str] = {
        "capture_contract_present": "pass" if has_capture_contract else "fail",
        "dominant_artifact_contract_present": "pass" if ready_selector else ("watch" if has_capture_contract else "fail"),
    }
    missing_vectors: list[str] = []
    violations: list[str] = []

    if family in GRAPH_FAMILIES:
        assert signature is not None
        hard_gates["graph_surface_contract_declared"] = "pass"
        if not signature.get("emits_node_rects"):
            missing_vectors.append("node_rects")
        if not signature.get("emits_edge_paths"):
            missing_vectors.append("edge_paths")
        if not signature.get("emits_region_markers"):
            missing_vectors.append("region_markers")
        if not signature.get("emits_quality_receipt"):
            missing_vectors.append("view_quality_receipt")
        hard_gates["graph_geometry_emittable"] = "pass" if "node_rects" not in missing_vectors and "edge_paths" not in missing_vectors else "watch"
        hard_gates["region_marker_completeness"] = "pass" if "region_markers" not in missing_vectors else "watch"
        hard_gates["quality_receipt_available"] = "pass" if "view_quality_receipt" not in missing_vectors else "watch"
        if missing_vectors:
            violations.append("graph_surface_partial_measurement")
    else:
        hard_gates["graph_surface_contract_declared"] = "not_applicable"
        emits_quality_receipt = "view_quality_receipt" in source_text or "data-zenith-view-quality" in source_text
        hard_gates["quality_receipt_available"] = "pass" if emits_quality_receipt else "watch"
        if not emits_quality_receipt:
            missing_vectors.append("view_quality_receipt")
        if not has_capture_contract:
            missing_vectors.append("capture_contract")
        if not ready_selector:
            missing_vectors.append("dominant_artifact_ready_selector")

    if has_capture_contract and not latest_status:
        missing_vectors.append("live_capture_status")

    grade = _grade_row(
        family=family,
        has_capture_contract=has_capture_contract,
        signature=signature,
        missing_vectors=missing_vectors,
        hard_gates=hard_gates,
    )
    metric_vector = _build_metric_vector(
        family=family,
        mode=mode,
        has_capture_contract=has_capture_contract,
        ready_selector=ready_selector,
        source_text=source_text,
        signature=signature,
    )
    geometry_summary = _as_dict((geometry_summaries or {}).get(str(view.get("id") or "")))
    geometry_vector = _geometry_vector_from_summary(geometry_summary, mode=mode)
    metric_vector = _metric_vector_with_geometry(metric_vector, geometry_vector)
    geometry_gates = _as_dict(geometry_vector.get("hard_gates")) if geometry_vector else {}
    hard_gates.update(geometry_gates)
    measurement_tier = _measurement_tier(
        grade=grade,
        family=family,
        signature=signature,
        metric_vector=metric_vector,
        geometry_vector=geometry_vector,
        missing_vectors=missing_vectors,
    )
    if grade == "partial_unmeasured" and family in GRAPH_FAMILIES:
        violations.append("unshared_metric_gap")

    known_vectors = {
        "dominant_artifact_presence": hard_gates["dominant_artifact_contract_present"],
        "capture_contract": hard_gates["capture_contract_present"],
        "latest_capture_status": str(latest_status or "unknown"),
        "region_marker_completeness": hard_gates.get("region_marker_completeness", "not_applicable"),
        "graph_surface_contract": hard_gates.get("graph_surface_contract_declared", "not_applicable"),
        "view_quality_receipt": hard_gates.get("quality_receipt_available", "not_applicable"),
        "geometry_vector": "pass" if geometry_vector else "watch",
    }

    reason_base = [
        f"family={family}",
        f"capture={'present' if has_capture_contract else 'missing'}",
        f"latest_capture={latest_status or 'unknown'}",
    ]
    if signature:
        reason_base.append(f"layout={signature['layout_engine']}")
        reason_base.append(f"camera={signature['camera_policy']}")
        reason_base.append(f"receipt_source={quality_receipt_source}")

    missing_measure_reasons = [
        f"{vector}: producer marker or receipt not yet exposed through this view's captured contract"
        for vector in missing_vectors
    ]

    row = {
        "schema": VIEW_QUALITY_RECEIPT_SCHEMA_V1,
        "view_id": view.get("id"),
        "view_family": family,
        "mode": mode,
        "grade": grade,
        "measurement_maturity": measurement_tier,
        "measurement_tier": measurement_tier,
        "quality_receipt_source": quality_receipt_source,
        "metric_vector_available": metric_vector is not None,
        "geometry_vector_available": geometry_vector is not None,
        "calibration_status": _calibration_status(measurement_tier),
        "route": view.get("route"),
        "capture_slug": _capture_slug(view),
        "title": view.get("label"),
        "purpose": _compact_reason(view.get("purpose") or capture_contract.get("purpose") or ""),
        "constitution": constitution_for_family(family, view),
        "capture_context": {
            "route": view.get("route"),
            "selected_state": None,
            "capture_group": capture_contract.get("capture_group"),
            "latest_status": latest_status,
            "latest_captured_count": latest_capture_status,
        },
        "region_geometry": _region_geometry_from_summary(geometry_summary),
        "metric_vector": metric_vector,
        "geometry_vector": geometry_vector,
        "objective_vector": _objective_vector(
            family=family,
            has_capture_contract=has_capture_contract,
            latest_capture_status=latest_status if isinstance(latest_status, str) else None,
            signature=signature,
            geometry_vector=geometry_vector,
        ),
        "known_vectors": known_vectors,
        "missing_vectors": sorted(set(missing_vectors)),
        "hard_gates": hard_gates,
        "violations": sorted(set(violations)),
        "confidence": 0.74 if grade.startswith("measured_") else (0.52 if has_capture_contract else 0.25),
        "missing_measure_reasons": missing_measure_reasons,
        "graph_surface_signature": signature,
        "next_owner_shape": _next_owner_shape(family, signature, missing_vectors),
        "receipt_refs": [METRIC_QUALITY_RECEIPT_SCHEMA_V1] if metric_vector else [],
        "source_refs": {
            "navigation_graph": "state/frontend_navigation/navigation_graph.json",
            "station_views": "tools/meta/observability/station_views.json",
            "component_refs": _evidence_refs(view),
        },
        "selection_reason": "; ".join(reason_base),
    }
    packet = build_view_observation_packet(
        view=view,
        row=row,
        capture_contract=capture_contract,
        render_load_index=render_load_index,
        changed_paths=list(changed_paths or []),
    )
    calibration_review = _geometry_calibration_review(
        row=row,
        geometry_vector=geometry_vector,
        screenshot_ledger=packet["screenshot_ledger"],
    )
    if calibration_review:
        row["geometry_calibration"] = calibration_review
        watch_resolutions = [
            _as_dict(item) for item in _as_list(calibration_review.get("watch_resolutions"))
        ]
        resolution_actions = [
            _resolution_action_for_watch_resolution(resolution)
            for resolution in watch_resolutions
        ]
        if watch_resolutions:
            row["calibrated_watch_resolutions"] = watch_resolutions
        if resolution_actions:
            row["resolution_action_receipts"] = resolution_actions
        row["calibration_status"] = calibration_review["status"]
        row["hard_gates"].update(_as_dict(calibration_review.get("hard_gates")))
        row["violations"] = sorted(
            set(_as_list(row.get("violations")) + _as_list(calibration_review.get("violations")))
        )
        row["known_vectors"]["geometry_calibration"] = calibration_review["status"]
        row["known_vectors"]["calibrated_watch_resolution"] = (
            "pass" if watch_resolutions else "not_applicable"
        )
        row["known_vectors"]["resolution_action"] = (
            "pass" if resolution_actions else "not_applicable"
        )
        if metric_vector is not None:
            metric_vector["geometry_calibration_status"] = calibration_review["status"]
            metric_vector["geometry_calibration_schema"] = calibration_review["schema"]
            if watch_resolutions:
                metric_vector["calibrated_watch_resolution_classes"] = sorted(
                    {
                        str(resolution.get("resolution_class"))
                        for resolution in watch_resolutions
                    }
                )
            if resolution_actions:
                metric_vector["resolution_action_count"] = len(resolution_actions)
                metric_vector["resolution_action_lanes"] = sorted(
                    {
                        str(action.get("action_lane"))
                        for action in resolution_actions
                    }
                )
        if geometry_vector is not None:
            geometry_vector["geometry_calibration_status"] = calibration_review["status"]
            geometry_vector["geometry_calibration_profile_id"] = _as_dict(
                calibration_review.get("profile")
            ).get("profile_id")
            if watch_resolutions:
                geometry_vector["calibrated_watch_resolution_classes"] = sorted(
                    {
                        str(resolution.get("resolution_class"))
                        for resolution in watch_resolutions
                    }
                )
            if resolution_actions:
                geometry_vector["resolution_action_count"] = len(resolution_actions)
                geometry_vector["resolution_action_lanes"] = sorted(
                    {
                        str(action.get("action_lane"))
                        for action in resolution_actions
                    }
                )
        if calibration_review["schema"] not in row["receipt_refs"]:
            row["receipt_refs"].append(calibration_review["schema"])
        if resolution_actions and VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1 not in row["receipt_refs"]:
            row["receipt_refs"].append(VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1)
        resolution_next_owner_shape = _watch_resolution_next_owner_shape(watch_resolutions)
        if resolution_next_owner_shape:
            row["next_owner_shape"] = resolution_next_owner_shape
        elif calibration_review["status"] == "calibrated_pass":
            row["next_owner_shape"] = "second_surface_geometry_transfer"
        elif calibration_review["status"] == "calibrated_watch":
            row["next_owner_shape"] = "threshold_or_scene_review"
        else:
            row["next_owner_shape"] = "live_geometry_currentness_review"
        packet["quality_census"].update(
            {
                "calibration_status": row["calibration_status"],
                "violations": row["violations"],
                "next_owner_shape": row["next_owner_shape"],
                "calibrated_watch_resolutions": watch_resolutions,
                "resolution_action_receipts": resolution_actions,
            }
        )
        packet["geometry_calibration"] = calibration_review
    row["screenshot_ledger"] = packet["screenshot_ledger"]
    row["latest_visual_delta"] = packet["latest_visual_delta"]
    row["view_observation_packet"] = packet
    row["observation_packet_ref"] = f"state/observability/view_quality/views/{row['view_id']}.json"
    return row


def _next_owner_shape(family: str, signature: dict[str, Any] | None, missing_vectors: list[str]) -> str:
    if family not in GRAPH_FAMILIES:
        return "view_constitution_marker_patch" if missing_vectors else "quality_receipt_candidate"
    if not signature:
        return "graph_surface_contract_marker_patch"
    if "view_quality_receipt" in missing_vectors:
        return "graph_surface_quality_receipt_patch"
    if "region_markers" in missing_vectors:
        return "graph_surface_region_marker_patch"
    if "node_rects" in missing_vectors or "edge_paths" in missing_vectors:
        return "graph_geometry_marker_patch"
    return "candidate_metric_calibration"


def _build_view_quality_action_surfaces(
    *,
    rows: list[dict[str, Any]],
    missing_requested: list[str],
) -> tuple[dict[str, Any], dict[str, Any]]:
    row_actions: list[dict[str, Any]] = []
    action_by_view_id: dict[str, dict[str, Any]] = {}
    for row in rows:
        action = _view_quality_action_for_row(row)
        row_actions.append(action)
        action_by_view_id[str(action.get("view_id") or "")] = action

    missing_actions = [
        _view_quality_action_for_missing_view_id(view_id)
        for view_id in missing_requested
    ]
    action_rows = row_actions + missing_actions
    open_hot_candidates = [
        action
        for action in action_rows
        if str(action.get("action_class")) not in {"monitor", "accepted_difference"}
        and int(action.get("hot_action_score") or 0) >= 80
    ]
    hot_rows = sorted(
        open_hot_candidates,
        key=lambda action: (
            -int(action.get("hot_action_score") or 0),
            str(action.get("view_id") or ""),
            str(action.get("action_label") or ""),
        ),
    )[:12]
    hot_keys = {
        (
            str(action.get("view_id") or ""),
            str(action.get("action_label") or ""),
            str(action.get("source_ref") or ""),
        )
        for action in hot_rows
    }
    for action in action_rows:
        key = (
            str(action.get("view_id") or ""),
            str(action.get("action_label") or ""),
            str(action.get("source_ref") or ""),
        )
        action["hot"] = key in hot_keys

    for row in rows:
        action = action_by_view_id.get(str(row.get("view_id") or ""))
        if not action:
            continue
        row["view_quality_action"] = action
        receipt_refs = row.setdefault("receipt_refs", [])
        if VIEW_QUALITY_ACTION_MAP_SCHEMA_V1 not in receipt_refs:
            receipt_refs.append(VIEW_QUALITY_ACTION_MAP_SCHEMA_V1)
        packet = _as_dict(row.get("view_observation_packet"))
        if packet:
            quality = _as_dict(packet.get("quality_census"))
            quality["view_quality_action"] = action
            packet["quality_census"] = quality
            row["view_observation_packet"] = packet

    action_counts = Counter(str(action.get("action_label")) for action in action_rows)
    action_class_counts = Counter(str(action.get("action_class")) for action in action_rows)
    action_lane_counts = Counter(str(action.get("action_lane")) for action in action_rows)
    family_counts = Counter(str(action.get("view_family")) for action in action_rows)
    tier_counts = Counter(str(action.get("measurement_tier")) for action in action_rows)

    action_map = {
        "schema": VIEW_QUALITY_ACTION_MAP_SCHEMA_V1,
        "source": VIEW_QUALITY_CENSUS_SCHEMA,
        "view_count": len(action_rows),
        "census_row_count": len(rows),
        "missing_requested_action_count": len(missing_actions),
        "action_counts": dict(sorted(action_counts.items())),
        "action_class_counts": dict(sorted(action_class_counts.items())),
        "action_lane_counts": dict(sorted(action_lane_counts.items())),
        "family_counts": dict(sorted(family_counts.items())),
        "measurement_tier_counts": dict(sorted(tier_counts.items())),
        "principle": (
            "Every view-quality row gets the next epistemically correct action; "
            "hot actions are ranked projections, not the universe of frontend quality work."
        ),
        "rows": action_rows,
    }
    hot_rollup = {
        "schema": VIEW_QUALITY_HOT_ACTION_ROLLUP_SCHEMA_V1,
        "source": VIEW_QUALITY_ACTION_MAP_SCHEMA_V1,
        "row_count": len(hot_rows),
        "selection_rule": "Top-ranked open action rows with hot_action_score >= 80; monitor and accepted-difference rows stay out of preflight pressure.",
        "action_counts": dict(sorted(Counter(str(row.get("action_label")) for row in hot_rows).items())),
        "action_class_counts": dict(sorted(Counter(str(row.get("action_class")) for row in hot_rows).items())),
        "rows": hot_rows,
    }
    return action_map, hot_rollup


def build_view_quality_census(
    navigation_graph: Mapping[str, Any],
    station_views: Mapping[str, Any],
    *,
    view_ids: list[str] | None = None,
    include_all: bool = False,
    generated_at: str | None = None,
    geometry_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    render_load_index: Mapping[str, Any] | None = None,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    views = _view_index(navigation_graph)
    station_index = _station_view_index(station_views)
    selected_ids = list(views.keys()) if include_all else list(view_ids or DEFAULT_SEED_VIEW_IDS)
    changed_path_list = _normalize_changed_paths(changed_paths)
    rows: list[dict[str, Any]] = []
    missing_requested: list[str] = []
    for view_id in selected_ids:
        view = views.get(view_id)
        if view is None:
            missing_requested.append(view_id)
            continue
        rows.append(
            build_view_quality_row(
                view,
                station_index,
                geometry_summaries=geometry_summaries,
                render_load_index=render_load_index,
                changed_paths=changed_path_list,
            )
        )

    grade_counts = Counter(str(row["grade"]) for row in rows)
    measurement_tier_counts = Counter(str(row.get("measurement_tier") or row.get("measurement_maturity")) for row in rows)
    calibration_status_counts = Counter(str(row.get("calibration_status") or "not_started") for row in rows)
    family_counts = Counter(str(row["view_family"]) for row in rows)
    missing_vector_counts = Counter(vector for row in rows for vector in row.get("missing_vectors", []))
    screenshot_status_counts = Counter(
        str(_as_dict(row.get("screenshot_ledger")).get("status") or "unknown") for row in rows
    )
    visual_delta_status_counts = Counter(
        str(_as_dict(row.get("latest_visual_delta")).get("status") or "unknown")
        for row in rows
    )
    calibrated_watch_resolution_rows = [
        {
            "view_id": row.get("view_id"),
            "view_family": row.get("view_family"),
            "calibration_status": row.get("calibration_status"),
            **resolution,
        }
        for row in rows
        for resolution in [
            _as_dict(item) for item in _as_list(row.get("calibrated_watch_resolutions"))
        ]
    ]
    calibrated_watch_resolution_counts = Counter(
        str(row.get("resolution_class")) for row in calibrated_watch_resolution_rows
    )
    resolution_action_rows = [
        {
            "view_id": row.get("view_id"),
            "view_family": row.get("view_family"),
            "calibration_status": row.get("calibration_status"),
            **action,
        }
        for row in rows
        for action in [
            _as_dict(item) for item in _as_list(row.get("resolution_action_receipts"))
        ]
    ]
    resolution_action_counts = Counter(
        str(row.get("action")) for row in resolution_action_rows
    )
    resolution_action_class_counts = Counter(
        str(row.get("resolution_class")) for row in resolution_action_rows
    )
    resolution_action_lane_counts = Counter(
        str(row.get("action_lane")) for row in resolution_action_rows
    )
    action_priority = {
        "extractor_patch": 0,
        "scene_policy_resolution": 1,
        "threshold_profile_review": 2,
        "constitution_acceptance_record": 3,
    }
    resolution_action_priority_rows = sorted(
        (
            {
                "view_id": row.get("view_id"),
                "resolution_class": row.get("resolution_class"),
                "input_violation": row.get("input_violation"),
                "action": row.get("action"),
                "action_lane": row.get("action_lane"),
                "decision": row.get("decision"),
                "status": row.get("status"),
                "next_owner_shape": row.get("next_owner_shape"),
                "closure_condition": row.get("closure_condition"),
            }
            for row in resolution_action_rows
        ),
        key=lambda row: (
            action_priority.get(str(row.get("action")), 99),
            str(row.get("view_id")),
            str(row.get("input_violation")),
        ),
    )
    class_actions: dict[str, list[dict[str, Any]]] = {}
    for action in resolution_action_priority_rows:
        resolution_class = str(action.get("resolution_class") or "unknown")
        class_actions.setdefault(resolution_class, []).append(action)
    graph_rows = [row for row in rows if row["view_family"] in GRAPH_FAMILIES]
    refresh_due_rows = [
        {
            "view_id": row.get("view_id"),
            "capture_slug": row.get("capture_slug"),
            "status": _as_dict(row.get("screenshot_ledger")).get("status"),
            "refresh_command": _as_dict(row.get("screenshot_ledger")).get("refresh_command"),
        }
        for row in rows
        if _as_dict(row.get("screenshot_ledger")).get("refresh_due")
    ]
    priority_rows = sorted(
        (
            {
                "view_id": row["view_id"],
                "view_family": row["view_family"],
                "grade": row["grade"],
                "missing_vectors": row.get("missing_vectors", []),
                "next_owner_shape": row.get("next_owner_shape"),
                "priority_score": _coverage_priority_score(row),
            }
            for row in rows
            if row.get("grade") in {"partial_unmeasured", "not_yet_in_census"}
        ),
        key=lambda row: (-int(row["priority_score"]), str(row["view_id"])),
    )
    calibration_rows = sorted(
        (
            {
                "view_id": row["view_id"],
                "view_family": row["view_family"],
                "grade": row["grade"],
                "measurement_tier": row.get("measurement_tier"),
                "quality_receipt_source": row.get("quality_receipt_source"),
                "metric_vector_available": row.get("metric_vector_available"),
                "geometry_vector_available": row.get("geometry_vector_available"),
                "calibration_status": row.get("calibration_status"),
                "next_owner_shape": _calibration_next_owner_shape(row),
                "priority_score": _calibration_priority_score(row),
            }
            for row in rows
            if row.get("measurement_tier")
            in {"measured_watch_generic", "measured_watch_metric", "measured_watch_geometry"}
        ),
        key=lambda row: (-int(row["priority_score"]), str(row["view_id"])),
    )
    view_quality_action_map, hot_action_rollup = _build_view_quality_action_surfaces(
        rows=rows,
        missing_requested=missing_requested,
    )

    return {
        "schema": VIEW_QUALITY_CENSUS_SCHEMA,
        "generated_at": generated_at or _utc_now(),
        "authority_boundary": "projection_over_frontend_navigation_graph_and_station_views_not_final_visual_judgment",
        "source_refs": {
            "navigation_graph": str(DEFAULT_NAVIGATION_GRAPH.relative_to(REPO_ROOT)),
            "station_views": str(DEFAULT_STATION_VIEWS.relative_to(REPO_ROOT)),
            "render_load_index": str(DEFAULT_RENDER_LOAD_INDEX.relative_to(REPO_ROOT)),
            "surface_standard": "codex/standards/std_station_aesthetic.json",
        },
        "measure_registry": default_measure_registry(),
        "graph_surface_contract": graph_surface_contract(),
        "summary": {
            "view_count": len(rows),
            "requested_view_count": len(selected_ids),
            "missing_requested_view_ids": missing_requested,
            "graph_surface_count": len(graph_rows),
            "grade_counts": dict(sorted(grade_counts.items())),
            "measurement_tier_counts": dict(sorted(measurement_tier_counts.items())),
            "calibration_status_counts": dict(sorted(calibration_status_counts.items())),
            "family_counts": dict(sorted(family_counts.items())),
            "missing_vector_counts": dict(sorted(missing_vector_counts.items())),
            "screenshot_status_counts": dict(sorted(screenshot_status_counts.items())),
            "screenshot_refresh_due_count": len(refresh_due_rows),
            "visual_delta_status_counts": dict(sorted(visual_delta_status_counts.items())),
            "visual_delta_review_needed_count": visual_delta_status_counts.get(
                "review_needed", 0
            ),
            "calibrated_watch_resolution_counts": dict(
                sorted(calibrated_watch_resolution_counts.items())
            ),
            "resolution_action_counts": dict(sorted(resolution_action_counts.items())),
            "resolution_action_class_counts": dict(
                sorted(resolution_action_class_counts.items())
            ),
            "resolution_action_lane_counts": dict(
                sorted(resolution_action_lane_counts.items())
            ),
            "view_quality_action_counts": view_quality_action_map["action_counts"],
            "view_quality_action_class_counts": view_quality_action_map["action_class_counts"],
            "view_quality_action_lane_counts": view_quality_action_map["action_lane_counts"],
            "view_quality_hot_action_count": hot_action_rollup["row_count"],
            "changed_paths": changed_path_list,
            "principle": "Refactor by measurement before refactoring by component unification.",
        },
        "coverage_expansion_priority": priority_rows[:12],
        "calibration_priority": calibration_rows[:12],
        "calibrated_watch_resolution_rollup": {
            "schema": CALIBRATED_WATCH_RESOLUTION_ROLLUP_SCHEMA_V1,
            "row_count": len(calibrated_watch_resolution_rows),
            "class_counts": dict(sorted(calibrated_watch_resolution_counts.items())),
            "principle": (
                "Every calibrated_watch routes to extractor_gap, scene_policy_gap, "
                "threshold_profile_gap, or acceptable_by_constitution before refactor."
            ),
            "rows": calibrated_watch_resolution_rows[:30],
        },
        "resolution_action_rollup": {
            "schema": VIEW_QUALITY_RESOLUTION_ACTION_ROLLUP_SCHEMA_V1,
            "inputs": {
                "calibrated_watch_resolution_rollup": CALIBRATED_WATCH_RESOLUTION_ROLLUP_SCHEMA_V1,
            },
            "row_count": len(resolution_action_rows),
            "action_counts": dict(sorted(resolution_action_counts.items())),
            "class_counts": dict(sorted(resolution_action_class_counts.items())),
            "lane_counts": dict(sorted(resolution_action_lane_counts.items())),
            "class_actions": {
                key: value[:12] for key, value in sorted(class_actions.items())
            },
            "refactor_intelligence": {
                "principle": (
                    "Diagnosis is not closure: every calibrated-watch row must route "
                    "to action, acceptance, or measurement repair before graph-surface unification."
                ),
                "extractor_gap": "Improve measurement before touching UI.",
                "scene_policy_gap": "Resolve default scene/data/constitution before promoting an implementation.",
                "threshold_profile_gap": "Review threshold or salience profile before creating UI debt.",
                "acceptable_by_constitution": "Record accepted mode-specific differences as refactor constraints.",
            },
            "rows": resolution_action_rows[:30],
        },
        "resolution_action_priority": resolution_action_priority_rows[:12],
        "view_quality_action_map": view_quality_action_map,
        "hot_action_rollup": hot_action_rollup,
        "screenshot_refresh_due": refresh_due_rows[:20],
        "view_observation_packets": {
            "schema": VIEW_OBSERVATION_INDEX_SCHEMA_V0,
            "role": "per-view AI-readable purpose, teleology, visible-landmark, principle, screenshot, and quality-census packets",
            "packet_dir": str(DEFAULT_VIEW_PACKET_DIR.relative_to(REPO_ROOT)),
            "write_command": "./repo-python tools/meta/observability/view_quality_census.py --all --out state/observability/view_quality/frontend_view_quality_census_v0.json --write-view-packets --write-visual-settlement",
            "row_count": len(rows),
            "packet_refs": [
                {
                    "view_id": row.get("view_id"),
                    "path": row.get("observation_packet_ref"),
                    "screenshot_status": _as_dict(row.get("screenshot_ledger")).get("status"),
                    "refresh_due": _as_dict(row.get("screenshot_ledger")).get("refresh_due"),
                    "visual_delta_status": _as_dict(row.get("latest_visual_delta")).get("status"),
                }
                for row in rows
            ],
        },
        "rows": rows,
    }


def _coverage_priority_score(row: Mapping[str, Any]) -> int:
    score = 0
    family = row.get("view_family")
    if family in GRAPH_FAMILIES:
        score += 8
    elif family in {"artifact_review", "document"}:
        score += 4
    if row.get("view_id") in {"rootNavigator", "codemap", "topology", "graph", "history"}:
        score += 4
    missing = set(_as_list(row.get("missing_vectors")))
    score += len(missing)
    if "view_quality_receipt" in missing:
        score += 2
    if "region_markers" in missing:
        score += 2
    return score


def _calibration_priority_score(row: Mapping[str, Any]) -> int:
    score = 0
    if row.get("view_family") in GRAPH_FAMILIES:
        score += 8
    if row.get("view_id") in {"rootNavigator", "codemap", "graph", "topology"}:
        score += 4
    if row.get("metric_vector_available") and not row.get("geometry_vector_available"):
        score += 3
    if row.get("measurement_tier") == "measured_watch_generic":
        score += 2
    if (
        row.get("view_id") == "rootNavigator"
        and row.get("metric_vector_available")
        and not row.get("geometry_vector_available")
    ):
        score += 2
    if row.get("calibration_status") == "screenshot_pending":
        score += 1
    if row.get("calibration_status") in {"geometry_watch", "calibrated_watch"}:
        score += 1
    if row.get("calibration_status") == "calibrated_pass":
        score -= 2
    return score


def _calibration_next_owner_shape(row: Mapping[str, Any]) -> str:
    resolution_next_owner_shape = _watch_resolution_next_owner_shape(
        [_as_dict(item) for item in _as_list(row.get("calibrated_watch_resolutions"))]
    )
    if resolution_next_owner_shape:
        return resolution_next_owner_shape
    if row.get("geometry_vector_available"):
        if row.get("calibration_status") == "calibrated_pass":
            return "second_surface_geometry_transfer"
        if row.get("calibration_status") == "calibrated_watch":
            return "threshold_or_scene_review"
        return "live_geometry_currentness_review"
    if row.get("metric_vector_available"):
        return "metric_vector_capture_calibration"
    return "metric_receipt_upgrade"


def _geometry_summary_rows(payload: Any) -> list[Mapping[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    if isinstance(payload.get("summaries"), list):
        return [row for row in payload["summaries"] if isinstance(row, Mapping)]
    if isinstance(payload.get("rows"), list):
        return [row for row in payload["rows"] if isinstance(row, Mapping)]
    return [payload]


def _read_geometry_summaries(paths: list[Path] | None) -> dict[str, Mapping[str, Any]]:
    summaries: dict[str, Mapping[str, Any]] = {}
    for path in paths or []:
        payload = _read_json(path)
        for row in _geometry_summary_rows(payload):
            view_id = str(row.get("view_id") or "")
            if view_id:
                summaries[view_id] = row
    return summaries


def _resolve_repo_path(value: Any) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else REPO_ROOT / path


def _geometry_summary_paths_from_render_load_index(
    render_load_index: Mapping[str, Any] | None,
) -> list[Path]:
    views = _as_dict((render_load_index or {}).get("views"))
    paths: list[Path] = []
    seen: set[Path] = set()
    for row in views.values():
        row = _as_dict(row)
        candidates: list[Any] = [
            row.get("latest_geometry_summary_path"),
            _as_dict(row.get("latest")).get("geometry_summary_path"),
            _as_dict(row.get("latest_attempt")).get("geometry_summary_path"),
            _as_dict(row.get("latest_promoted")).get("geometry_summary_path"),
        ]
        for candidate in candidates:
            path = _resolve_repo_path(candidate)
            if path is None or path in seen or not path.exists():
                continue
            paths.append(path)
            seen.add(path)
            break
    return paths


def build_from_paths(
    *,
    navigation_graph_path: Path = DEFAULT_NAVIGATION_GRAPH,
    station_views_path: Path = DEFAULT_STATION_VIEWS,
    render_load_index_path: Path = DEFAULT_RENDER_LOAD_INDEX,
    geometry_summary_paths: list[Path] | None = None,
    view_ids: list[str] | None = None,
    include_all: bool = False,
    changed_paths: list[str] | None = None,
) -> dict[str, Any]:
    render_load_index = _read_optional_json(render_load_index_path)
    geometry_summaries = _read_geometry_summaries(
        _geometry_summary_paths_from_render_load_index(render_load_index)
    )
    geometry_summaries.update(_read_geometry_summaries(geometry_summary_paths))
    return build_view_quality_census(
        _read_json(navigation_graph_path),
        _read_json(station_views_path),
        view_ids=view_ids,
        include_all=include_all,
        geometry_summaries=geometry_summaries,
        render_load_index=render_load_index,
        changed_paths=changed_paths,
    )


def _packet_markdown(packet: Mapping[str, Any]) -> str:
    scene = _as_dict(packet.get("scene_record"))
    quality = _as_dict(packet.get("quality_census"))
    screenshot = _as_dict(packet.get("screenshot_ledger"))
    latest = _as_dict(screenshot.get("latest_screenshot"))
    visual_delta = _as_dict(packet.get("latest_visual_delta"))
    principles = ", ".join(str(row.get("id")) for row in _as_list(packet.get("design_principles_applied")))
    visible = "\n".join(f"- `{item}`" for item in _as_list(packet.get("what_agent_should_see"))) or "- none"
    refresh_command = screenshot.get("refresh_command") or "not_bound_to_station_render"
    return "\n".join(
        [
            f"# {packet.get('title') or packet.get('view_id')}",
            "",
            "_Generated projection from view quality census; JSON packet is authority._",
            "",
            f"- view_id: `{packet.get('view_id')}`",
            f"- route: `{packet.get('route')}`",
            f"- capture_slug: `{packet.get('capture_slug')}`",
            f"- scene_species: `{scene.get('scene_species')}`",
            f"- dominant_artifact: `{scene.get('dominant_artifact')}`",
            f"- grade: `{quality.get('grade')}` / `{quality.get('measurement_tier')}`",
            f"- screenshot_status: `{screenshot.get('status')}`",
            f"- refresh_due: `{screenshot.get('refresh_due')}`",
            f"- latest_screenshot: `{latest.get('output_path')}`",
            f"- visual_delta_status: `{visual_delta.get('status')}`",
            f"- visual_delta_receipt: `{visual_delta.get('receipt_path')}`",
            f"- refresh_command: `{refresh_command}`",
            f"- principles: `{principles}`",
            "",
            "## Teleology",
            "",
            str(_as_dict(scene.get("teleology")).get("purpose") or ""),
            "",
            "## What Agent Should See",
            "",
            visible,
            "",
        ]
    )


def write_view_observation_packets(
    census: Mapping[str, Any],
    *,
    packet_dir: Path = DEFAULT_VIEW_PACKET_DIR,
    index_path: Path = DEFAULT_VIEW_PACKET_INDEX,
    markdown_index_path: Path = DEFAULT_VIEW_PACKET_INDEX_MD,
) -> dict[str, Any]:
    packet_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for row in _as_list(census.get("rows")):
        if not isinstance(row, Mapping):
            continue
        packet = _as_dict(row.get("view_observation_packet"))
        view_id = str(packet.get("view_id") or row.get("view_id") or "")
        if not view_id:
            continue
        json_path = packet_dir / f"{view_id}.json"
        md_path = packet_dir / f"{view_id}.md"
        json_path.write_text(json.dumps(packet, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        md_path.write_text(_packet_markdown(packet), encoding="utf-8")
        screenshot = _as_dict(packet.get("screenshot_ledger"))
        visual_delta = _as_dict(packet.get("latest_visual_delta"))
        rows.append(
            {
                "view_id": view_id,
                "route": packet.get("route"),
                "capture_slug": packet.get("capture_slug"),
                "packet_path": _rel(json_path),
                "markdown_path": _rel(md_path),
                "screenshot_status": screenshot.get("status"),
                "refresh_due": screenshot.get("refresh_due"),
                "latest_screenshot": _as_dict(screenshot.get("latest_screenshot")).get("output_path"),
                "visual_delta_status": visual_delta.get("status"),
                "visual_delta_receipt_path": visual_delta.get("receipt_path"),
                "visual_delta_changed_percent": visual_delta.get("changed_percent"),
                "refresh_command": screenshot.get("refresh_command"),
                "open_view_card": _view_memory_discoverability(view_id)["open_view_card"],
            }
        )

    index = {
        "schema": VIEW_OBSERVATION_INDEX_SCHEMA_V0,
        "generated_at": census.get("generated_at") or _utc_now(),
        "authority_boundary": "generated_projection_over_frontend_view_quality_census",
        "discoverability": _view_memory_discoverability(),
        "packet_dir": _rel(packet_dir),
        "row_count": len(rows),
        "refresh_due_count": sum(1 for row in rows if row.get("refresh_due")),
        "rows": rows,
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(json.dumps(index, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_index_path.write_text(_observation_index_markdown(index), encoding="utf-8")
    return index


def _observation_index_markdown(index: Mapping[str, Any]) -> str:
    lines = [
        "# Frontend View Observation Index",
        "",
        "_Generated projection. JSON packets under `state/observability/view_quality/views/` are the per-view contract surface._",
        "",
        f"- row_count: `{index.get('row_count')}`",
        f"- refresh_due_count: `{index.get('refresh_due_count')}`",
        "- discoverability: `./repo-python kernel.py --docs-route \"screenshot ledger\"`",
        "- browse: `./repo-python kernel.py --option-surface frontend_views --band cluster_flag`",
        "",
        "| View | Route | Screenshot | Visual delta | Packet | Refresh due |",
        "|---|---|---|---|---|---|",
    ]
    for row in _as_list(index.get("rows")):
        if not isinstance(row, Mapping):
            continue
        lines.append(
            "| `{}` | `{}` | `{}` | `{}` | `{}` | `{}` |".format(
                row.get("view_id"),
                row.get("route"),
                row.get("screenshot_status"),
                row.get("visual_delta_status"),
                row.get("packet_path"),
                row.get("refresh_due"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _visual_settlement_status(row: Mapping[str, Any]) -> str:
    screenshot = _as_dict(row.get("screenshot_ledger"))
    delta = _as_dict(row.get("latest_visual_delta"))
    screenshot_status = str(screenshot.get("status") or "unknown")
    delta_status = str(delta.get("status") or "missing_delta_receipt")
    capture_slug = str(row.get("capture_slug") or screenshot.get("capture_slug") or "")

    if not capture_slug or screenshot_status == "not_bound_to_station_render":
        return "unbound_to_station_render"
    if screenshot_status in {
        "missing_render",
        "latest_attempt_failed",
        "missing_screenshot_artifact",
        "stale_source_newer_than_screenshot",
    }:
        return "blocked_capture"
    if delta_status == "no_material_visual_delta":
        return "settled_no_material_delta"
    if delta_status == "expected_by_changed_path":
        return "settled_expected_delta"
    if delta_status == "baseline_pending":
        return "baseline_pending"
    if delta_status == "review_needed":
        return "review_needed"
    if screenshot_status == "due_changed_path":
        return "blocked_capture"
    if delta_status == "missing_delta_receipt":
        return "baseline_pending"
    return "review_needed"


def _include_visual_settlement_row(row: Mapping[str, Any], *, changed_paths: list[str]) -> bool:
    screenshot = _as_dict(row.get("screenshot_ledger"))
    delta = _as_dict(row.get("latest_visual_delta"))
    coupling = _as_dict(screenshot.get("changed_path_coupling"))
    if changed_paths:
        return coupling.get("status") == "affected"
    return bool(delta.get("raw_status") or delta.get("review_status") or delta.get("receipt_path"))


def _visual_settlement_row(row: Mapping[str, Any]) -> dict[str, Any]:
    screenshot = _as_dict(row.get("screenshot_ledger"))
    latest = _as_dict(screenshot.get("latest_screenshot"))
    delta = _as_dict(row.get("latest_visual_delta"))
    frame = _as_dict(delta.get("constitution_frame"))
    status = _visual_settlement_status(row)
    packet = _as_dict(row.get("view_observation_packet"))
    packet_path = str(row.get("observation_packet_ref") or "")
    view_id = str(row.get("view_id") or "")
    markdown_path = (
        f"state/observability/view_quality/views/{view_id}.md"
        if view_id
        else None
    )
    return {
        "schema": "frontend_visual_settlement_row_v0",
        "view_id": view_id,
        "route": row.get("route"),
        "capture_slug": row.get("capture_slug"),
        "settlement_status": status,
        "requires_review": status in VISUAL_SETTLEMENT_REVIEW_STATUSES,
        "screenshot_status": screenshot.get("status"),
        "screenshot_refresh_due": screenshot.get("refresh_due"),
        "refresh_command": screenshot.get("refresh_command"),
        "changed_path_coupling": screenshot.get("changed_path_coupling"),
        "latest_screenshot": latest.get("output_path"),
        "latest_visual_delta": {
            "schema": delta.get("schema"),
            "status": delta.get("status"),
            "raw_status": delta.get("raw_status"),
            "review_status": delta.get("review_status"),
            "receipt_path": delta.get("receipt_path"),
            "diff_output_path": delta.get("diff_output_path"),
            "changed_percent": delta.get("changed_percent"),
            "threshold_changed_percent": delta.get("threshold_changed_percent"),
        },
        "constitution_frame": {
            "purpose": frame.get("purpose"),
            "dominant_artifact": frame.get("dominant_artifact"),
            "expected_landmarks": frame.get("expected_landmarks"),
            "design_principle_ids": frame.get("design_principle_ids"),
        },
        "view_quality": {
            "grade": row.get("grade"),
            "measurement_tier": row.get("measurement_tier"),
            "calibration_status": row.get("calibration_status"),
            "next_owner_shape": row.get("next_owner_shape"),
        },
        "refs": {
            "packet_path": packet_path,
            "markdown_path": markdown_path,
            "open_view_card": f"./repo-python kernel.py --option-surface frontend_views --band card --ids {view_id}",
            "render_receipt_path": latest.get("receipt_path"),
            "visual_delta_receipt_path": delta.get("receipt_path"),
        },
        "discoverability": _view_memory_discoverability(view_id),
        "settlement_rule": (
            "Close the frontend change only after affected rows are settled, "
            "baseline-pending rows have an accepted first capture, or review_needed rows "
            "are explicitly accepted/reworked against the view purpose and principles."
        ),
        "packet_teleology": _as_dict(_as_dict(packet.get("scene_record")).get("teleology")),
    }


def build_frontend_visual_settlement(census: Mapping[str, Any]) -> dict[str, Any]:
    changed_paths = _normalize_changed_paths(
        [str(path) for path in _as_list(_as_dict(census.get("summary")).get("changed_paths"))]
    )
    rows = [
        _visual_settlement_row(row)
        for row in _as_list(census.get("rows"))
        if isinstance(row, Mapping)
        and _include_visual_settlement_row(row, changed_paths=changed_paths)
    ]
    status_counts = Counter(str(row.get("settlement_status") or "unknown") for row in rows)
    review_rows = [
        row for row in rows if row.get("settlement_status") in VISUAL_SETTLEMENT_REVIEW_STATUSES
    ]
    refresh_commands = sorted(
        {
            str(row.get("refresh_command"))
            for row in rows
            if row.get("refresh_command") and row.get("screenshot_refresh_due")
        }
    )
    return {
        "schema": FRONTEND_VISUAL_SETTLEMENT_SCHEMA_V0,
        "generated_at": census.get("generated_at") or _utc_now(),
        "authority_boundary": "generated_projection_over_view_observation_packets_not_visual_quality_authority",
        "inputs": {
            "census_schema": census.get("schema"),
            "view_observation_index": str(DEFAULT_VIEW_PACKET_INDEX.relative_to(REPO_ROOT)),
            "render_load_index": str(DEFAULT_RENDER_LOAD_INDEX.relative_to(REPO_ROOT)),
            "changed_paths": changed_paths,
        },
        "discoverability": _view_memory_discoverability(),
        "selection": {
            "changed_path_scoped": bool(changed_paths),
            "include_rule": (
                "changed-path affected views"
                if changed_paths
                else "views with station_render visual-delta receipt context"
            ),
        },
        "summary": {
            "row_count": len(rows),
            "status_counts": dict(sorted(status_counts.items())),
            "review_queue_count": len(review_rows),
            "settled_count": sum(
                count
                for status, count in status_counts.items()
                if status in {"settled_no_material_delta", "settled_expected_delta"}
            ),
            "blocked_capture_count": status_counts.get("blocked_capture", 0),
            "baseline_pending_count": status_counts.get("baseline_pending", 0),
            "changed_paths": changed_paths,
            "refresh_commands": refresh_commands,
        },
        "review_queue": review_rows[:20],
        "rows": rows,
    }


def write_frontend_visual_settlement(
    census: Mapping[str, Any],
    *,
    out_path: Path = DEFAULT_VISUAL_SETTLEMENT,
) -> dict[str, Any]:
    settlement = build_frontend_visual_settlement(census)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(settlement, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return settlement


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--navigation-graph", type=Path, default=DEFAULT_NAVIGATION_GRAPH)
    parser.add_argument("--station-views", type=Path, default=DEFAULT_STATION_VIEWS)
    parser.add_argument("--render-load-index", type=Path, default=DEFAULT_RENDER_LOAD_INDEX)
    parser.add_argument(
        "--geometry-summary",
        action="append",
        type=Path,
        default=[],
        help="DOM/capture geometry summary JSON to merge into matching view rows; repeatable.",
    )
    parser.add_argument(
        "--changed-path",
        action="append",
        dest="changed_paths",
        default=[],
        help="Frontend path edited in this change; repeatable. Marks coupled view screenshots refresh-due.",
    )
    parser.add_argument("--view-id", action="append", dest="view_ids", help="View id to include; repeatable.")
    parser.add_argument("--all", action="store_true", help="Census every frontend view from the navigation graph.")
    parser.add_argument("--out", type=Path, default=None, help=f"Write receipt JSON, for example {DEFAULT_OUT}.")
    parser.add_argument(
        "--write-view-packets",
        action="store_true",
        help="Write per-view observation JSON/Markdown packets and a packet index under state/observability/view_quality.",
    )
    parser.add_argument("--view-packet-dir", type=Path, default=DEFAULT_VIEW_PACKET_DIR)
    parser.add_argument("--view-packet-index", type=Path, default=DEFAULT_VIEW_PACKET_INDEX)
    parser.add_argument("--view-packet-index-md", type=Path, default=DEFAULT_VIEW_PACKET_INDEX_MD)
    parser.add_argument(
        "--write-visual-settlement",
        action="store_true",
        help="Write the frontend visual-settlement receipt over changed-path affected view packets.",
    )
    parser.add_argument("--visual-settlement-out", type=Path, default=DEFAULT_VISUAL_SETTLEMENT)
    parser.add_argument("--print", action="store_true", dest="print_json", help="Print receipt JSON to stdout.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(list(argv or sys.argv[1:]))
    receipt = build_from_paths(
        navigation_graph_path=args.navigation_graph,
        station_views_path=args.station_views,
        render_load_index_path=args.render_load_index,
        geometry_summary_paths=args.geometry_summary,
        view_ids=args.view_ids,
        include_all=args.all,
        changed_paths=args.changed_paths,
    )
    encoded = json.dumps(receipt, indent=2, sort_keys=True)
    if args.print_json or args.out is None:
        print(encoded)
    out_path = args.out
    if out_path is not None:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(encoded + "\n", encoding="utf-8")
    if args.write_view_packets:
        write_view_observation_packets(
            receipt,
            packet_dir=args.view_packet_dir,
            index_path=args.view_packet_index,
            markdown_index_path=args.view_packet_index_md,
        )
    if args.write_visual_settlement:
        write_frontend_visual_settlement(receipt, out_path=args.visual_settlement_out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
