"""Regression tests for the frontend-wide View Quality Census."""

from __future__ import annotations

import json
from pathlib import Path

import sys


REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT))

from tools.meta.observability.view_quality_census import (  # noqa: E402
    CALIBRATED_WATCH_RESOLUTION_ROLLUP_SCHEMA_V1,
    CALIBRATED_WATCH_RESOLUTION_SCHEMA_V1,
    FRONTEND_VISUAL_SETTLEMENT_SCHEMA_V0,
    FRONTEND_VISUAL_MEMORY_DISCOVERY_SCHEMA_V0,
    GEOMETRY_CALIBRATION_REVIEW_SCHEMA_V1,
    GRAPH_SURFACE_CONTRACT_SCHEMA,
    MEASURE_REGISTRY_SCHEMA,
    SCREENSHOT_LEDGER_SCHEMA_V0,
    VIEW_OBSERVATION_INDEX_SCHEMA_V0,
    VIEW_OBSERVATION_PACKET_SCHEMA_V0,
    VIEW_OBSERVATION_VISUAL_DELTA_SCHEMA_V1,
    VIEW_QUALITY_ACTION_MAP_SCHEMA_V1,
    VIEW_QUALITY_HOT_ACTION_ROLLUP_SCHEMA_V1,
    VIEW_QUALITY_CENSUS_SCHEMA,
    VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1,
    VIEW_QUALITY_RESOLUTION_ACTION_ROLLUP_SCHEMA_V1,
    build_frontend_visual_settlement,
    build_view_quality_census,
    build_from_paths,
    classify_view_family,
    default_measure_registry,
    write_frontend_visual_settlement,
    write_view_observation_packets,
)

ROOT_NAV_GEOMETRY_FIXTURE = (
    REPO_ROOT
    / "tools/meta/observability/fixtures/view_quality/root_navigator_geometry_pass.json"
)
WATCH_RESOLUTION_FIXTURE_DIR = REPO_ROOT / "tools/meta/observability/fixtures/view_quality"


def _synthetic_navigation_graph() -> dict:
    return {
        "views": [
            {
                "id": "station",
                "label": "Station",
                "route": "/station",
                "purpose": "Surface Atlas graph of every view.",
                "capture": {
                    "slug": "home",
                    "capture_group": "station_runtime",
                    "ready_selector": "[data-zenith-station-surface-atlas=\"ready\"]",
                    "load_timing": {"latest_status": "captured"},
                },
                "surface_audit": {
                    "primary_component_name": "StationSurfaceAtlas",
                    "evidence_refs": [
                        "system/server/ui/src/components/world/home/StationSurfaceAtlas.tsx",
                    ],
                },
            },
            {
                "id": "rootNavigator",
                "label": "Root Navigator",
                "route": "/station/root-navigator",
                "purpose": "Unified graph/code-map canvas.",
                "capture": {
                    "slug": "root_navigator",
                    "capture_group": "station_reference",
                    "ready_selector": "[data-zenith-root-unified-graph-canvas=\"visible\"]",
                    "load_timing": {"latest_status": "captured"},
                },
                "surface_audit": {
                    "primary_component_name": "RootNavigator",
                    "evidence_refs": [
                        "system/server/ui/src/pages/RootNavigator.tsx",
                    ],
                },
            },
            {
                "id": "history",
                "label": "Archives",
                "route": "/history",
                "purpose": "Historical runs, evidence, and replay.",
                "capture": {
                    "slug": "history",
                    "capture_group": "secondary",
                    "ready_selector": "[data-zenith-history-surface=\"ready\"]",
                    "load_timing": {"latest_status": "captured"},
                },
                "surface_audit": {
                    "primary_component_name": "History",
                    "evidence_refs": [],
                },
            },
            {
                "id": "graph",
                "label": "System Graph",
                "route": "/station/graph",
                "purpose": "Control graph surface with graph-first canvas.",
                "capture": {
                    "slug": "graph",
                    "capture_group": "station_reference",
                    "ready_selector": "[data-zenith-system-graph-surface=\"ready\"]",
                    "load_timing": {"latest_status": "captured"},
                },
                "surface_audit": {
                    "primary_component_name": "SystemGraph",
                    "evidence_refs": [
                        "system/server/ui/src/components/world/SystemGraph.tsx",
                    ],
                },
            },
        ]
    }


def _synthetic_station_views() -> dict:
    return {
        "views": [
            {
                "slug": "home",
                "route": "/station",
                "ready_selector": "[data-zenith-station-surface-atlas=\"ready\"]",
                "capture_group": "station_runtime",
            },
            {
                "slug": "root_navigator",
                "route": "/station/root-navigator",
                "ready_selector": "[data-zenith-root-unified-graph-canvas=\"visible\"]",
                "capture_group": "station_reference",
            },
            {
                "slug": "history",
                "route": "/history",
                "ready_selector": "[data-zenith-history-surface=\"ready\"]",
                "capture_group": "secondary",
            },
            {
                "slug": "graph",
                "route": "/station/graph",
                "ready_selector": "[data-zenith-system-graph-surface=\"ready\"]",
                "capture_group": "station_reference",
            },
        ]
    }


def _synthetic_render_load_index() -> dict:
    return {
        "views": {
            "home": {
                "latest": {
                    "recorded_at": "2026-05-21T04:00:00+00:00",
                    "run_stamp": "run-home",
                    "receipt_ref": "run-home:chromium:home:fhd_landscape",
                    "receipt_path": "state/observability/renders/run-home/manifest.json",
                    "engine": "chromium",
                    "viewport_slug": "fhd_landscape",
                    "route": "/station",
                    "status": "captured",
                    "output_path": "state/observability/renders/run-home/chromium/home/fhd_landscape.png",
                },
                "latest_required_engine_coverage": {
                    "complete": True,
                    "captured": 1,
                    "failed": 0,
                    "engines": ["chromium"],
                    "viewports": ["fhd_landscape"],
                },
            },
            "root_navigator": {
                "latest": {
                    "recorded_at": "2026-05-21T04:00:00+00:00",
                    "run_stamp": "run-root",
                    "receipt_ref": "run-root:chromium:root_navigator:fhd_landscape",
                    "receipt_path": "state/observability/renders/run-root/manifest.json",
                    "engine": "chromium",
                    "viewport_slug": "fhd_landscape",
                    "route": "/station/root-navigator",
                    "status": "captured",
                    "output_path": "state/observability/renders/run-root/chromium/root_navigator/fhd_landscape.png",
                    "readiness_attrs": {"data-zenith-root-navigator-primary-surface": "universal_graph"},
                },
                "latest_required_engine_coverage": {
                    "complete": True,
                    "captured": 1,
                    "failed": 0,
                    "engines": ["chromium"],
                    "viewports": ["fhd_landscape"],
                },
            },
            "graph": {
                "latest": {
                    "recorded_at": "2026-05-21T04:00:00+00:00",
                    "run_stamp": "run-graph",
                    "receipt_ref": "run-graph:chromium:graph:fhd_landscape",
                    "receipt_path": "state/observability/renders/run-graph/manifest.json",
                    "engine": "chromium",
                    "viewport_slug": "fhd_landscape",
                    "route": "/station/graph",
                    "status": "captured",
                    "output_path": "state/observability/renders/run-graph/chromium/graph/fhd_landscape.png",
                    "readiness_attrs": {"data-zenith-system-graph-surface": "ready"},
                },
                "latest_required_engine_coverage": {
                    "complete": True,
                    "captured": 1,
                    "failed": 0,
                    "engines": ["chromium"],
                    "viewports": ["fhd_landscape"],
                },
            },
        }
    }


def _fresh_root_render_index(tmp_path: Path) -> dict:
    screenshot = tmp_path / "root_navigator.png"
    screenshot.write_bytes(b"png")
    render_index = _synthetic_render_load_index()
    latest = render_index["views"]["root_navigator"]["latest"]
    latest["recorded_at"] = "2999-01-01T00:00:00+00:00"
    latest["output_path"] = str(screenshot)
    latest["geometry_summary_path"] = str(tmp_path / "root_navigator_geometry.json")
    latest["geometry_summary_schema"] = "root_navigator_capture_summary_v1"
    return render_index


def _fresh_graph_render_index(tmp_path: Path) -> dict:
    screenshot = tmp_path / "graph.png"
    screenshot.write_bytes(b"png")
    render_index = _synthetic_render_load_index()
    latest = render_index["views"]["graph"]["latest"]
    latest["recorded_at"] = "2999-01-01T00:00:00+00:00"
    latest["output_path"] = str(screenshot)
    latest["geometry_summary_path"] = str(tmp_path / "graph_geometry.json")
    latest["geometry_summary_schema"] = "view_geometry_capture_summary_v1"
    return render_index


def _root_geometry_summary(
    *,
    evidence_kind: str | None = None,
    graph_area: float = 0.54,
    axis_area: float = 0.14,
    inspector_area: float = 0.22,
    node_count: int = 177,
    edge_count: int = 208,
    label_coverage: float = 0.85,
) -> dict:
    summary = {
        "schema": "root_navigator_capture_summary_v1",
        "view_id": "rootNavigator",
        "mode": "graph_first",
        "capture_context": {
            "route": "/station/root-navigator",
            "viewport": {"width": 1920, "height": 1080},
        },
        "regions": {
            "dominant_artifact": {"role": "root_unified_graph_canvas", "area_ratio": graph_area},
            "axis_rail": {"role": "axis_rail", "area_ratio": axis_area},
            "inspector": {"role": "right_inspector", "area_ratio": inspector_area},
        },
        "graph_metrics": {
            "node_rect_count": node_count,
            "edge_path_count": edge_count,
            "node_union_to_graph_region": 0.43,
            "visible_label_count": int(round(node_count * label_coverage)),
            "visible_label_coverage": label_coverage,
            "edge_density": round(edge_count / node_count, 4) if node_count else None,
        },
    }
    if evidence_kind is not None:
        summary["evidence_kind"] = evidence_kind
    return summary


def _graph_geometry_summary(
    *,
    evidence_kind: str | None = "live_dom_capture",
    graph_area: float = 0.9139,
    node_count: int = 1,
    edge_count: int = 0,
    label_coverage: float = 1.0,
) -> dict:
    summary = {
        "schema": "view_geometry_capture_summary_v1",
        "view_id": "graph",
        "mode": "graph_first",
        "capture_context": {
            "route": "/station/graph",
            "viewport": {"width": 1920, "height": 1080},
        },
        "regions": {
            "dominant_artifact": {"role": "system_graph_canvas", "area_ratio": graph_area},
            "rails": [],
        },
        "graph_metrics": {
            "node_rect_count": node_count,
            "edge_path_count": edge_count,
            "node_union_to_graph_region": 0.02,
            "visible_label_count": int(round(node_count * label_coverage)),
            "visible_label_coverage": label_coverage,
            "edge_density": round(edge_count / node_count, 4) if node_count else None,
        },
    }
    if evidence_kind is not None:
        summary["evidence_kind"] = evidence_kind
    return summary


def test_measure_registry_contains_graph_and_divergence_families() -> None:
    registry = default_measure_registry()
    family_ids = {family["id"] for family in registry["families"]}

    assert registry["schema"] == MEASURE_REGISTRY_SCHEMA
    assert "graph_readability" in family_ids
    assert "implementation_divergence" in family_ids
    assert "measured_watch_geometry" in registry["measurement_tiers"]
    assert "calibrated_watch" in registry["calibration_statuses"]
    assert "calibrated_pass" in registry["calibration_statuses"]
    assert registry["resolution_action_receipt_schema"] == VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1
    assert registry["view_quality_action_map_schema"] == VIEW_QUALITY_ACTION_MAP_SCHEMA_V1
    assert "measurement_contract_gap" in registry["view_quality_action_classes"]
    assert "diagnosed_quality_gap" in registry["view_quality_action_classes"]
    assert set(registry["calibrated_watch_resolution_classes"]) == {
        "extractor_gap",
        "scene_policy_gap",
        "threshold_profile_gap",
        "acceptable_by_constitution",
    }
    assert registry["calibrated_watch_resolution_actions"]["extractor_gap"]["action"] == "extractor_patch"
    assert (
        registry["calibrated_watch_resolution_actions"]["scene_policy_gap"]["action"]
        == "scene_policy_resolution"
    )


def test_calibrated_watch_resolution_fixtures_cover_all_resolution_classes() -> None:
    fixture_paths = sorted(WATCH_RESOLUTION_FIXTURE_DIR.glob("calibrated_watch_resolution_*.json"))
    fixtures = [json.loads(path.read_text(encoding="utf-8")) for path in fixture_paths]

    assert {fixture["schema"] for fixture in fixtures} == {"calibrated_watch_resolution_fixture_v1"}
    assert {fixture["resolution_class"] for fixture in fixtures} == {
        "extractor_gap",
        "scene_policy_gap",
        "threshold_profile_gap",
        "acceptable_by_constitution",
    }
    assert all(fixture["expected_next_owner_shape"] for fixture in fixtures)


def test_resolution_action_fixtures_route_all_resolution_classes() -> None:
    fixture_paths = sorted(WATCH_RESOLUTION_FIXTURE_DIR.glob("resolution_action_*.json"))
    fixtures = [json.loads(path.read_text(encoding="utf-8")) for path in fixture_paths]

    assert {fixture["schema"] for fixture in fixtures} == {"view_quality_resolution_action_fixture_v1"}
    by_class = {fixture["resolution_class"]: fixture for fixture in fixtures}
    assert set(by_class) == {
        "extractor_gap",
        "scene_policy_gap",
        "threshold_profile_gap",
        "acceptable_by_constitution",
    }
    assert by_class["extractor_gap"]["expected_action"] == "extractor_patch"
    assert by_class["scene_policy_gap"]["expected_action"] == "scene_policy_resolution"
    assert by_class["threshold_profile_gap"]["expected_action"] == "threshold_profile_review"
    assert by_class["acceptable_by_constitution"]["expected_action"] == "constitution_acceptance_record"
    assert all(fixture["expected_closure_mode"] for fixture in fixtures)


def test_synthetic_census_grades_surface_atlas_and_generic_quality_markers() -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=_synthetic_render_load_index(),
        view_ids=["station", "rootNavigator", "history"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    assert census["schema"] == VIEW_QUALITY_CENSUS_SCHEMA
    assert census["measure_registry"]["schema"] == MEASURE_REGISTRY_SCHEMA
    assert census["graph_surface_contract"]["schema"] == GRAPH_SURFACE_CONTRACT_SCHEMA

    rows = {row["view_id"]: row for row in census["rows"]}
    assert rows["station"]["view_family"] == "atlas_map"
    assert rows["station"]["graph_surface_signature"]["emits_quality_receipt"] is True
    assert rows["station"]["grade"] == "measured_pass"

    assert rows["rootNavigator"]["view_family"] == "graph_surface"
    assert rows["rootNavigator"]["grade"] == "measured_watch"
    assert rows["rootNavigator"]["measurement_tier"] == "measured_watch_metric"
    assert rows["rootNavigator"]["metric_vector_available"] is True
    assert rows["rootNavigator"]["geometry_vector_available"] is False
    assert rows["rootNavigator"]["calibration_status"] == "screenshot_pending"
    assert rows["rootNavigator"]["graph_surface_signature"]["quality_receipt_source"] == "metric_quality_receipt_v1"
    assert rows["rootNavigator"]["metric_vector"]["dominant_artifact_geometry_present"] is True
    assert rows["rootNavigator"]["missing_vectors"] == []
    assert rows["rootNavigator"]["next_owner_shape"] == "candidate_metric_calibration"
    assert rows["rootNavigator"]["screenshot_ledger"]["schema"] == SCREENSHOT_LEDGER_SCHEMA_V0
    assert rows["rootNavigator"]["view_observation_packet"]["schema"] == VIEW_OBSERVATION_PACKET_SCHEMA_V0
    assert rows["rootNavigator"]["view_observation_packet"]["scene_record"]["teleology"]["done_when"]
    assert (
        rows["rootNavigator"]["view_observation_packet"]["discoverability"]["schema"]
        == FRONTEND_VISUAL_MEMORY_DISCOVERY_SCHEMA_V0
    )
    assert (
        rows["rootNavigator"]["view_observation_packet"]["discoverability"]["docs_route"]
        == './repo-python kernel.py --docs-route "screenshot ledger"'
    )
    assert "P10" in {
        principle["id"]
        for principle in rows["rootNavigator"]["view_observation_packet"]["design_principles_applied"]
    }

    assert rows["history"]["view_family"] == "artifact_review"
    assert rows["history"]["grade"] == "measured_watch"


def test_changed_path_marks_coupled_view_screenshot_refresh_due() -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=_synthetic_render_load_index(),
        view_ids=["rootNavigator"],
        changed_paths=["system/server/ui/src/pages/RootNavigator.tsx"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    ledger = row["screenshot_ledger"]
    assert ledger["refresh_due"] is True
    assert ledger["changed_path_coupling"]["status"] == "affected"
    assert ledger["refresh_command"].endswith(
        "station_render render --view root_navigator --engine chromium --viewport fhd_landscape"
    )
    assert census["summary"]["screenshot_refresh_due_count"] == 1


def test_visual_delta_receipt_is_framed_by_view_packet_constitution(tmp_path: Path) -> None:
    render_index = _fresh_root_render_index(tmp_path)
    latest = render_index["views"]["root_navigator"]["latest"]
    latest.update(
        {
            "visual_delta_schema": "station_render_view_observation_visual_delta_v1",
            "visual_delta_status": "material_visual_delta",
            "visual_delta_review_status": "review_needed",
            "visual_delta_receipt_path": str(tmp_path / "visual_deltas" / "manifest.json"),
            "visual_delta_prior_output_path": str(tmp_path / "prior.png"),
            "visual_delta_diff_output_path": str(tmp_path / "diff.png"),
            "visual_delta_changed_pixels": 42,
            "visual_delta_changed_percent": 3.25,
            "visual_delta_threshold_percent": 0.01,
        }
    )

    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=render_index,
        view_ids=["rootNavigator"],
        changed_paths=["system/server/ui/src/pages/RootNavigator.tsx"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    delta = row["latest_visual_delta"]
    packet_delta = row["view_observation_packet"]["latest_visual_delta"]

    assert delta["schema"] == VIEW_OBSERVATION_VISUAL_DELTA_SCHEMA_V1
    assert delta["status"] == "expected_by_changed_path"
    assert delta["raw_status"] == "material_visual_delta"
    assert delta["changed_percent"] == 3.25
    assert delta["constitution_frame"]["dominant_artifact"] == "graph_canvas"
    assert "P10" in delta["constitution_frame"]["design_principle_ids"]
    assert packet_delta == delta
    assert census["summary"]["visual_delta_status_counts"]["expected_by_changed_path"] == 1


def test_frontend_visual_settlement_classifies_changed_path_expected_delta(tmp_path: Path) -> None:
    render_index = _fresh_root_render_index(tmp_path)
    latest = render_index["views"]["root_navigator"]["latest"]
    latest.update(
        {
            "visual_delta_schema": "station_render_view_observation_visual_delta_v1",
            "visual_delta_status": "material_visual_delta",
            "visual_delta_review_status": "review_needed",
            "visual_delta_receipt_path": str(tmp_path / "visual_deltas" / "manifest.json"),
            "visual_delta_prior_output_path": str(tmp_path / "prior.png"),
            "visual_delta_diff_output_path": str(tmp_path / "diff.png"),
            "visual_delta_changed_pixels": 42,
            "visual_delta_changed_percent": 3.25,
            "visual_delta_threshold_percent": 0.01,
        }
    )
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=render_index,
        view_ids=["rootNavigator"],
        changed_paths=["system/server/ui/src/pages/RootNavigator.tsx"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    settlement = write_frontend_visual_settlement(
        census,
        out_path=tmp_path / "frontend_visual_settlement_v0.json",
    )

    assert settlement["schema"] == FRONTEND_VISUAL_SETTLEMENT_SCHEMA_V0
    assert settlement["summary"]["status_counts"] == {"settled_expected_delta": 1}
    assert settlement["summary"]["review_queue_count"] == 0
    row = settlement["rows"][0]
    assert row["view_id"] == "rootNavigator"
    assert row["settlement_status"] == "settled_expected_delta"
    assert row["requires_review"] is False
    assert row["latest_visual_delta"]["receipt_path"].endswith("visual_deltas/manifest.json")
    assert row["constitution_frame"]["dominant_artifact"] == "graph_canvas"
    assert row["refs"]["packet_path"].endswith("views/rootNavigator.json")
    assert (tmp_path / "frontend_visual_settlement_v0.json").exists()


def test_frontend_visual_settlement_blocks_changed_path_without_capture() -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=_synthetic_render_load_index(),
        view_ids=["rootNavigator"],
        changed_paths=["system/server/ui/src/pages/RootNavigator.tsx"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    settlement = build_frontend_visual_settlement(census)

    assert settlement["summary"]["row_count"] == 1
    assert settlement["summary"]["status_counts"] == {"blocked_capture": 1}
    assert settlement["summary"]["review_queue_count"] == 1
    assert settlement["summary"]["refresh_commands"] == [
        "./repo-python -m tools.meta.observability.station_render render --view root_navigator --engine chromium --viewport fhd_landscape"
    ]
    row = settlement["review_queue"][0]
    assert row["view_id"] == "rootNavigator"
    assert row["settlement_status"] == "blocked_capture"
    assert row["changed_path_coupling"]["status"] == "affected"


def test_write_view_observation_packets_emits_json_markdown_and_index(tmp_path: Path) -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=_synthetic_render_load_index(),
        view_ids=["station", "rootNavigator"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    index = write_view_observation_packets(
        census,
        packet_dir=tmp_path / "views",
        index_path=tmp_path / "frontend_view_observation_index_v0.json",
        markdown_index_path=tmp_path / "frontend_view_observation_index_v0.md",
    )

    assert index["schema"] == VIEW_OBSERVATION_INDEX_SCHEMA_V0
    assert index["discoverability"]["schema"] == FRONTEND_VISUAL_MEMORY_DISCOVERY_SCHEMA_V0
    assert "screenshot ledger" in index["discoverability"]["alias_terms"]
    assert index["row_count"] == 2
    assert index["rows"][0]["open_view_card"].startswith(
        "./repo-python kernel.py --option-surface frontend_views --band card --ids "
    )
    assert (tmp_path / "views" / "rootNavigator.json").exists()
    assert (tmp_path / "views" / "rootNavigator.md").exists()
    assert "Root Navigator" in (tmp_path / "views" / "rootNavigator.md").read_text(encoding="utf-8")
    assert (tmp_path / "frontend_view_observation_index_v0.md").exists()


def test_root_navigator_geometry_summary_promotes_metric_row_to_geometry_tier() -> None:
    geometry_summary = _root_geometry_summary()
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["rootNavigator"],
        geometry_summaries={"rootNavigator": geometry_summary},
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    assert row["measurement_tier"] == "measured_watch_geometry"
    assert row["metric_vector_available"] is True
    assert row["geometry_vector_available"] is True
    assert row["calibration_status"] == "geometry_watch"
    assert row["geometry_calibration"]["schema"] == GEOMETRY_CALIBRATION_REVIEW_SCHEMA_V1
    assert "synthetic_or_unreviewed_geometry" in row["geometry_calibration"]["violations"]
    assert row["hard_gates"]["dominant_artifact_visible"] == "pass"
    assert row["hard_gates"]["graph_first_not_rail_dominated"] == "pass"
    assert row["metric_vector"]["source"] == "static_marker_contract_plus_dom_capture_summary"
    assert row["metric_vector"]["graph_region_area_ratio"] == 0.54
    assert row["metric_vector"]["node_rect_count"] == 177
    assert row["metric_vector"]["edge_path_count"] == 208
    assert row["metric_vector"]["visible_label_coverage"] == 0.85
    assert row["geometry_vector"]["dominant_artifact_salience_rank"] == 1


def test_root_navigator_live_geometry_needs_threshold_review_before_pass(tmp_path: Path) -> None:
    geometry_summary = _root_geometry_summary(
        evidence_kind="live_dom_capture",
        graph_area=0.3827,
        axis_area=0.1222,
        inspector_area=0.2771,
        node_count=8,
        edge_count=0,
        label_coverage=1.0,
    )
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["rootNavigator"],
        geometry_summaries={"rootNavigator": geometry_summary},
        render_load_index=_fresh_root_render_index(tmp_path),
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    review = row["geometry_calibration"]
    assert row["measurement_tier"] == "measured_watch_geometry"
    assert row["calibration_status"] == "calibrated_watch"
    assert review["status"] == "calibrated_watch"
    assert review["edge_path_count"]["interpretation"] == "extractor_pending"
    assert "competing_regions_rival_dominant_artifact" in review["violations"]
    assert "edge_geometry_ambiguous" in review["violations"]
    resolutions = {
        item["violation"]: item
        for item in review["watch_resolutions"]
    }
    assert resolutions["edge_geometry_ambiguous"]["schema"] == CALIBRATED_WATCH_RESOLUTION_SCHEMA_V1
    assert resolutions["edge_geometry_ambiguous"]["resolution_class"] == "extractor_gap"
    assert resolutions["competing_regions_rival_dominant_artifact"]["resolution_class"] == "threshold_profile_gap"
    assert row["calibrated_watch_resolutions"] == review["watch_resolutions"]
    assert row["next_owner_shape"] == "extractor_resolution"
    assert census["summary"]["calibrated_watch_resolution_counts"]["extractor_gap"] == 1
    assert census["calibrated_watch_resolution_rollup"]["schema"] == CALIBRATED_WATCH_RESOLUTION_ROLLUP_SCHEMA_V1
    actions = {item["input_violation"]: item for item in row["resolution_action_receipts"]}
    assert actions["edge_geometry_ambiguous"]["schema"] == VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1
    assert actions["edge_geometry_ambiguous"]["action"] == "extractor_patch"
    assert actions["edge_geometry_ambiguous"]["action_lane"] == "measurement_harness"
    assert actions["competing_regions_rival_dominant_artifact"]["action"] == "threshold_profile_review"
    assert census["summary"]["resolution_action_counts"] == {
        "extractor_patch": 1,
        "threshold_profile_review": 1,
    }
    assert census["resolution_action_rollup"]["schema"] == VIEW_QUALITY_RESOLUTION_ACTION_ROLLUP_SCHEMA_V1


def test_view_quality_action_map_covers_every_census_row() -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        render_load_index=_synthetic_render_load_index(),
        view_ids=["station", "rootNavigator", "history", "graph"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    action_map = census["view_quality_action_map"]
    rows = {row["view_id"]: row for row in census["rows"]}
    actions = {row["view_id"]: row for row in action_map["rows"]}

    assert action_map["schema"] == VIEW_QUALITY_ACTION_MAP_SCHEMA_V1
    assert action_map["view_count"] == 4
    assert action_map["census_row_count"] == 4
    assert set(actions) == set(rows)
    assert all(row["view_quality_action"]["schema"] == "view_quality_action_row_v1" for row in rows.values())
    assert actions["station"]["action_label"] == "monitor_regression_guard"
    assert actions["rootNavigator"]["action_label"] == "geometry_capture_bridge"
    assert actions["graph"]["action_label"] == "geometry_capture_bridge"
    assert census["hot_action_rollup"]["schema"] == VIEW_QUALITY_HOT_ACTION_ROLLUP_SCHEMA_V1


def test_missing_requested_view_gets_census_binding_action() -> None:
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["missingView"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    action_map = census["view_quality_action_map"]
    action = action_map["rows"][0]
    assert census["summary"]["missing_requested_view_ids"] == ["missingView"]
    assert action_map["view_count"] == 1
    assert action["view_id"] == "missingView"
    assert action["measurement_tier"] == "not_yet_in_census"
    assert action["action_class"] == "census_binding_gap"
    assert action["action_label"] == "add_to_census_or_bind_capture"


def test_partial_unmeasured_rows_get_contract_marker_actions() -> None:
    graph = _synthetic_navigation_graph()
    graph["views"].append(
        {
            "id": "unmarkedGraph",
            "label": "Unmarked Graph",
            "route": "/station/unmarked-graph",
            "purpose": "Graph surface without quality markers.",
            "capture": {
                "slug": "unmarked_graph",
                "capture_group": "station_reference",
                "ready_selector": "[data-zenith-unmarked-graph=\"ready\"]",
                "load_timing": {"latest_status": "captured"},
            },
            "surface_audit": {
                "primary_component_name": "UnmarkedGraph",
                "evidence_refs": [],
            },
        }
    )
    station_views = _synthetic_station_views()
    station_views["views"].append(
        {
            "slug": "unmarked_graph",
            "route": "/station/unmarked-graph",
            "ready_selector": "[data-zenith-unmarked-graph=\"ready\"]",
            "capture_group": "station_reference",
        }
    )
    census = build_view_quality_census(
        graph,
        station_views,
        view_ids=["unmarkedGraph"],
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    action = row["view_quality_action"]
    assert row["measurement_tier"] == "partial_unmeasured"
    assert action["action_class"] == "measurement_contract_gap"
    assert action["action_label"] == "contract_marker_patch"
    assert "missing_vectors" in action["source_ref"]


def test_root_navigator_live_geometry_close_competing_area_routes_to_threshold_profile_review(tmp_path: Path) -> None:
    geometry_summary = _root_geometry_summary(
        evidence_kind="live_dom_capture",
        graph_area=0.3827,
        axis_area=0.1222,
        inspector_area=0.2771,
        node_count=8,
        edge_count=7,
        label_coverage=1.0,
    )
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["rootNavigator"],
        geometry_summaries={"rootNavigator": geometry_summary},
        render_load_index=_fresh_root_render_index(tmp_path),
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    review = row["geometry_calibration"]
    resolutions = {
        item["violation"]: item
        for item in review["watch_resolutions"]
    }
    assert row["calibration_status"] == "calibrated_watch"
    assert review["edge_path_count"]["interpretation"] == "measured_visible_edges"
    assert list(resolutions) == ["competing_regions_rival_dominant_artifact"]
    assert resolutions["competing_regions_rival_dominant_artifact"]["resolution_class"] == "threshold_profile_gap"
    assert resolutions["competing_regions_rival_dominant_artifact"]["interpretation"] == "close_margin_combined_chrome_area"
    assert row["next_owner_shape"] == "threshold_profile_review"
    assert census["summary"]["calibrated_watch_resolution_counts"] == {"threshold_profile_gap": 1}
    actions = {item["input_violation"]: item for item in row["resolution_action_receipts"]}
    action = actions["competing_regions_rival_dominant_artifact"]
    assert action["action"] == "threshold_profile_review"
    assert action["decision"] == "threshold_refinement_pending"
    assert action["status"] == "open"
    assert "salience-weighted thresholds" in action["closure_condition"]
    assert census["summary"]["resolution_action_counts"] == {"threshold_profile_review": 1}
    assert census["resolution_action_rollup"]["class_actions"]["threshold_profile_gap"][0]["view_id"] == "rootNavigator"


def test_graph_zero_edge_live_geometry_routes_to_scene_policy_gap(tmp_path: Path) -> None:
    geometry_summary = _graph_geometry_summary()
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["graph"],
        geometry_summaries={"graph": geometry_summary},
        render_load_index=_fresh_graph_render_index(tmp_path),
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    review = row["geometry_calibration"]
    assert row["measurement_tier"] == "measured_watch_geometry"
    assert row["calibration_status"] == "calibrated_watch"
    assert row["next_owner_shape"] == "scene_policy_resolution"
    assert review["edge_path_count"]["interpretation"] == "true_zero_or_not_applicable_by_constitution"
    assert review["watch_resolutions"][0]["violation"] == "edge_geometry_ambiguous"
    assert review["watch_resolutions"][0]["resolution_class"] == "scene_policy_gap"
    assert review["watch_resolutions"][0]["interpretation"] == "sparse_graph_scene_despite_dominant_canvas"
    assert census["calibrated_watch_resolution_rollup"]["class_counts"] == {"scene_policy_gap": 1}
    action = row["resolution_action_receipts"][0]
    assert action["schema"] == VIEW_QUALITY_RESOLUTION_ACTION_RECEIPT_SCHEMA_V1
    assert action["action"] == "scene_policy_resolution"
    assert action["decision"] == "scene_policy_resolution_pending"
    assert action["action_lane"] == "scene_policy"
    assert "data_state_gap" in action["closure_condition"]
    assert (
        action["refactor_intelligence"]["component_unification_gate"]
        == "Do not promote a graph surface as a shared parent while its default scene is unresolved."
    )
    assert census["summary"]["resolution_action_counts"] == {"scene_policy_resolution": 1}
    assert census["resolution_action_rollup"]["class_actions"]["scene_policy_gap"][0]["view_id"] == "graph"
    action = row["view_quality_action"]
    assert action["action_class"] == "diagnosed_quality_gap"
    assert action["action_label"] == "scene_policy_resolution"
    assert action["hot"] is True
    assert census["view_quality_action_map"]["action_counts"]["scene_policy_resolution"] == 1
    assert census["hot_action_rollup"]["rows"][0]["view_id"] == "graph"


def test_hot_action_rollup_projects_resolution_actions_from_all_view_map(tmp_path: Path) -> None:
    root_geometry = _root_geometry_summary(
        evidence_kind="live_dom_capture",
        graph_area=0.3827,
        axis_area=0.1222,
        inspector_area=0.2771,
        node_count=8,
        edge_count=7,
        label_coverage=1.0,
    )
    graph_geometry = _graph_geometry_summary()
    render_index = _fresh_root_render_index(tmp_path)
    graph_screenshot = tmp_path / "graph.png"
    graph_screenshot.write_bytes(b"png")
    render_index["views"]["graph"]["latest"].update(
        {
            "recorded_at": "2999-01-01T00:00:00+00:00",
            "output_path": str(graph_screenshot),
            "geometry_summary_path": str(tmp_path / "graph_geometry.json"),
            "geometry_summary_schema": "view_geometry_capture_summary_v1",
        }
    )
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["rootNavigator", "graph"],
        geometry_summaries={
            "rootNavigator": root_geometry,
            "graph": graph_geometry,
        },
        render_load_index=render_index,
        generated_at="2026-05-21T00:00:00+00:00",
    )

    actions = {
        row["view_id"]: row
        for row in census["view_quality_action_map"]["rows"]
    }
    hot = {
        row["view_id"]: row
        for row in census["hot_action_rollup"]["rows"]
    }
    assert census["view_quality_action_map"]["view_count"] == 2
    assert actions["rootNavigator"]["action_label"] == "threshold_profile_review"
    assert actions["graph"]["action_label"] == "scene_policy_resolution"
    assert actions["rootNavigator"]["hot"] is True
    assert actions["graph"]["hot"] is True
    assert set(hot) == {"rootNavigator", "graph"}
    assert census["summary"]["view_quality_hot_action_count"] == 2


def test_root_navigator_live_geometry_can_calibrate_pass_after_thresholds(tmp_path: Path) -> None:
    geometry_summary = _root_geometry_summary(evidence_kind="live_dom_capture")
    census = build_view_quality_census(
        _synthetic_navigation_graph(),
        _synthetic_station_views(),
        view_ids=["rootNavigator"],
        geometry_summaries={"rootNavigator": geometry_summary},
        render_load_index=_fresh_root_render_index(tmp_path),
        generated_at="2026-05-21T00:00:00+00:00",
    )

    row = census["rows"][0]
    review = row["geometry_calibration"]
    assert row["measurement_tier"] == "measured_watch_geometry"
    assert row["calibration_status"] == "calibrated_pass"
    assert review["watch_gates"] == []
    assert review["failed_gates"] == []
    assert review["edge_path_count"]["interpretation"] == "measured_visible_edges"
    assert row["next_owner_shape"] == "second_surface_geometry_transfer"
    assert row["view_quality_action"]["action_class"] == "monitor"
    assert row["view_quality_action"]["action_label"] == "monitor_regression_guard"


def test_family_classifier_keeps_non_graph_surfaces_out_of_graph_contract() -> None:
    view = {
        "id": "history",
        "label": "Archives",
        "route": "/history",
        "purpose": "Historical runs, evidence, and replay.",
        "surface_audit": {"primary_component_name": "History"},
    }

    assert classify_view_family(view) == "artifact_review"


def test_live_census_seed_smoke_includes_requested_views() -> None:
    census = build_from_paths(view_ids=["station", "rootNavigator", "codemap", "topology", "graph", "history"])
    rows = {row["view_id"]: row for row in census["rows"]}

    assert census["schema"] == VIEW_QUALITY_CENSUS_SCHEMA
    assert census["summary"]["missing_requested_view_ids"] == []
    assert {"station", "rootNavigator", "codemap", "topology", "graph", "history"}.issubset(rows)
    assert rows["station"]["view_family"] == "atlas_map"
    assert rows["rootNavigator"]["view_family"] == "graph_surface"
    assert rows["rootNavigator"]["grade"] == "measured_watch"
    assert rows["rootNavigator"]["measurement_tier"] in {
        "measured_watch_metric",
        "measured_watch_geometry",
    }
    assert rows["rootNavigator"]["metric_vector_available"] is True
    if rows["rootNavigator"]["measurement_tier"] == "measured_watch_geometry":
        assert rows["rootNavigator"]["geometry_vector_available"] is True
    assert rows["codemap"]["grade"] == "measured_watch"
    assert rows["graph"]["grade"] == "measured_watch"
    assert rows["graph"]["measurement_tier"] in {"measured_watch_metric", "measured_watch_geometry"}
    assert rows["graph"]["metric_vector_available"] is True
    if rows["graph"]["measurement_tier"] == "measured_watch_geometry":
        assert rows["graph"]["geometry_vector_available"] is True
    assert rows["graph"]["missing_vectors"] == []
    assert rows["topology"]["missing_vectors"] == ["edge_paths", "node_rects"]
    assert rows["history"]["view_family"] == "artifact_review"
    assert rows["history"]["grade"] == "measured_watch"


def test_live_all_census_tracks_coverage_and_calibration_ladders() -> None:
    census = build_from_paths(include_all=True)

    grade_counts = census["summary"]["grade_counts"]
    tier_counts = census["summary"]["measurement_tier_counts"]
    missing_counts = census["summary"]["missing_vector_counts"]

    assert grade_counts["measured_watch"] >= 4
    assert grade_counts["partial_unmeasured"] <= 38
    assert (
        tier_counts.get("measured_watch_metric", 0)
        + tier_counts.get("measured_watch_geometry", 0)
    ) >= 2
    assert missing_counts["region_markers"] <= 7
    assert missing_counts["view_quality_receipt"] <= 44
    rows = {row["view_id"]: row for row in census["rows"]}
    if rows["rootNavigator"]["geometry_vector_available"]:
        assert census["calibration_priority"][0]["view_id"] != "rootNavigator"
    else:
        assert census["calibration_priority"][0]["view_id"] == "rootNavigator"
    assert census["coverage_expansion_priority"][0]["view_id"] != "graph"


def test_live_all_census_with_root_geometry_advances_next_calibration_priority() -> None:
    census = build_from_paths(include_all=True, geometry_summary_paths=[ROOT_NAV_GEOMETRY_FIXTURE])
    rows = {row["view_id"]: row for row in census["rows"]}

    assert rows["rootNavigator"]["measurement_tier"] == "measured_watch_geometry"
    assert rows["rootNavigator"]["geometry_vector_available"] is True
    assert rows["rootNavigator"]["metric_vector"]["node_rect_count"] == 177
    assert rows["rootNavigator"]["calibration_status"] in {"geometry_watch", "calibrated_pass", "calibrated_watch"}
    assert census["calibration_priority"][0]["view_id"] != "rootNavigator"


def test_build_from_paths_discovers_geometry_summary_from_render_load_index(tmp_path: Path) -> None:
    geometry_path = tmp_path / "root_navigator_geometry.json"
    geometry_path.write_text(ROOT_NAV_GEOMETRY_FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
    nav_path = tmp_path / "navigation_graph.json"
    station_views_path = tmp_path / "station_views.json"
    render_index_path = tmp_path / "render_load_index.json"
    nav_path.write_text(json.dumps(_synthetic_navigation_graph()), encoding="utf-8")
    station_views_path.write_text(json.dumps(_synthetic_station_views()), encoding="utf-8")
    render_index = _synthetic_render_load_index()
    render_index["views"]["root_navigator"]["latest"]["geometry_summary_path"] = str(geometry_path)
    render_index["views"]["root_navigator"]["latest"]["geometry_summary_schema"] = (
        "root_navigator_capture_summary_v1"
    )
    render_index_path.write_text(json.dumps(render_index), encoding="utf-8")

    census = build_from_paths(
        navigation_graph_path=nav_path,
        station_views_path=station_views_path,
        render_load_index_path=render_index_path,
        view_ids=["rootNavigator"],
    )

    row = census["rows"][0]
    assert row["measurement_tier"] == "measured_watch_geometry"
    assert row["geometry_vector_available"] is True
    assert row["screenshot_ledger"]["latest_screenshot"]["geometry_summary_path"] == str(geometry_path)
