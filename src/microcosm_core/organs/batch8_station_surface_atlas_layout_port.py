from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    load_json_object,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch8_station_surface_atlas_layout_port"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

TSX_SOURCE_REF = "system/server/ui/src/components/world/home/StationSurfaceAtlas.tsx"
TSX_SOURCE_SHA256 = "c6249a7c4208f52930e5df80b331c623038246c0b450f9121b94d81ae065aa5f"

COLUMN_GAP = 320
ROW_GAP = 132
COLUMN_HEADER_HEIGHT = 88
NODE_WIDTH = 280
LANE_GAP = 28
LANE_OFFSET = NODE_WIDTH + LANE_GAP
LAYOUT_LANE2_THRESHOLD = 5
LAYOUT_LANE3_THRESHOLD = 11
LAYOUT_BAND_TRIGGER = 5
BAND_GAP = 100

SHELL_GROUP_ORDER: tuple[str, ...] = (
    "operate",
    "missions",
    "data",
    "inspect",
    "map",
    "library",
    "unassigned",
)

MAP_PAIR_LAYOUT_ORDER = {
    "codemap": 0,
    "doctrine": 1,
    "ledger": 2,
    "reactions": 3,
    "timeline": 4,
    "assimilation": 5,
}

EXPECTED_CASES: tuple[str, ...] = (
    "banded_slack_reference",
    "map_pair_order_reference",
)

EXPECTED_NEGATIVE_CASES = {
    "station_layout_attention_sort_required": (
        "BATCH8_STATION_LAYOUT_ATTENTION_SORT_REQUIRED",
    ),
    "station_layout_slack_lane_spend_required": (
        "BATCH8_STATION_LAYOUT_SLACK_LANE_SPEND_REQUIRED",
    ),
    "station_layout_unknown_group_routed_unassigned": (
        "BATCH8_STATION_LAYOUT_UNKNOWN_GROUP_ROUTED_UNASSIGNED",
    ),
}

ALLOWED_DETACHED_PUBLIC_REFACTOR_RELATIONS = {
    "source_faithful_public_refactor",
    "source_faithful_public_light_edit",
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch8_station_surface_atlas_layout_python_port_not_ui_runtime_or_release_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "python_port": True,
    "react_runtime_started": False,
    "browser_render_authorized": False,
    "navigation_graph_authority": False,
    "repo_mutation_authorized": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
}

ANTI_CLAIM = (
    "Batch 8 StationSurfaceAtlas layout port validates a Python parity model "
    "of layoutNodes over public synthetic AtlasView rows and an exact copied "
    "non-secret TSX source reference. It is not React runtime evidence, not "
    "browser visual acceptance, not navigation_graph authority, not repository "
    "mutation authority, not publication authority, and not release approval."
)

SOURCE_REQUIRED_ANCHORS = {
    TSX_SOURCE_REF: (
        "function layoutNodes(views: AtlasView[])",
        "const COLUMN_GAP = 320",
        "while (maxBandWidth - bandWidths[band] >= LANE_OFFSET)",
        "const lanes: AtlasView[][] = Array.from({ length: laneCount }, () => []);",
        "fitViewOptions={{ padding: graphFirstDrawersActive ? 0.04 : 0.08, includeHiddenNodes: true, minZoom: 0.55 }}",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 8 StationSurfaceAtlas layoutNodes Port",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(PROBE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def capture_posture_sort_key(view: Mapping[str, Any]) -> int:
    status = view.get("captureLatestStatus")
    if status in {"failed", "readiness_timeout"}:
        return 0
    if view.get("captureSlug") and int(view.get("captureSampleCount") or 0) == 0:
        return 1
    if status == "captured":
        return 2
    return 3


def map_pair_layout_sort_key(view: Mapping[str, Any]) -> int | None:
    if view.get("shellGroup") != "map":
        return None
    view_id = str(view.get("id") or "")
    return MAP_PAIR_LAYOUT_ORDER.get(view_id)


def lane_count_for_group(count: int) -> int:
    if count >= LAYOUT_LANE3_THRESHOLD:
        return 3
    if count >= LAYOUT_LANE2_THRESHOLD:
        return 2
    return 1


def _view_id(view: Mapping[str, Any]) -> str:
    return str(view.get("id") or "")


def _group_for(view: Mapping[str, Any]) -> str:
    group = str(view.get("shellGroup") or "unassigned")
    return group if group in SHELL_GROUP_ORDER else "unassigned"


def _centrality(view: Mapping[str, Any]) -> int:
    return int(view.get("fanout") or 0) + int(view.get("fanin") or 0)


def _label(view: Mapping[str, Any]) -> str:
    return str(view.get("label") or "")


def _sorted_views_for_group(group: str, views: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    def key(view: Mapping[str, Any]) -> tuple[int, int, int, str]:
        pair = map_pair_layout_sort_key(view)
        if group == "map" and pair is not None:
            return (0, pair, 0, _label(view))
        if group == "map":
            return (0, 2**53 - 1, 0, _label(view))
        return (
            1,
            capture_posture_sort_key(view),
            -_centrality(view),
            _label(view),
        )

    return sorted(views, key=key)


def _grouped_views(views: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped = {group: [] for group in SHELL_GROUP_ORDER}
    for view in views:
        grouped[_group_for(view)].append(view)
    return grouped


def layout_nodes(views: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped = _grouped_views(views)
    populated = [group for group in SHELL_GROUP_ORDER if grouped[group]]
    band_count = 2 if len(populated) >= LAYOUT_BAND_TRIGGER else 1
    groups_per_band = (len(populated) + band_count - 1) // band_count if populated else 0

    group_band: dict[str, int] = {}
    final_lanes: dict[str, int] = {}
    band_widths = [0 for _ in range(band_count)]
    band_heights = [0 for _ in range(band_count)]

    cursors = [0 for _ in range(band_count)]
    for index, group in enumerate(populated):
        band_index = index // groups_per_band if groups_per_band else 0
        group_band[group] = band_index
        lane_count = lane_count_for_group(len(grouped[group]))
        final_lanes[group] = lane_count
        lane_span = 0 if lane_count == 1 else (lane_count - 1) * LANE_OFFSET
        band_widths[band_index] = cursors[band_index] + NODE_WIDTH + lane_span
        cursors[band_index] += COLUMN_GAP + lane_span

    max_band_width = max(band_widths, default=0)
    for band_index in range(band_count):
        while max_band_width - band_widths[band_index] >= LANE_OFFSET:
            tallest_group: str | None = None
            tallest_rows = 0
            for group in populated:
                if group_band[group] != band_index:
                    continue
                rows = (len(grouped[group]) + final_lanes[group] - 1) // final_lanes[group]
                if rows > tallest_rows:
                    tallest_rows = rows
                    tallest_group = group
            if tallest_group is None:
                break
            count = len(grouped[tallest_group])
            next_lane = final_lanes[tallest_group] + 1
            next_rows = (count + next_lane - 1) // next_lane
            if next_rows >= tallest_rows:
                break
            final_lanes[tallest_group] = next_lane
            band_widths[band_index] += LANE_OFFSET

    for group in populated:
        band_index = group_band[group]
        per_lane = (len(grouped[group]) + final_lanes[group] - 1) // final_lanes[group]
        column_height = COLUMN_HEADER_HEIGHT + per_lane * ROW_GAP
        band_heights[band_index] = max(band_heights[band_index], column_height)

    positions: dict[str, dict[str, int]] = {}
    columns: list[dict[str, Any]] = []
    cursor_x = 0
    current_band = 0
    group_in_band = 0
    band_y = 0

    for group in populated:
        if group_in_band >= groups_per_band:
            band_y += band_heights[current_band] + BAND_GAP
            current_band += 1
            cursor_x = 0
            group_in_band = 0

        sorted_group = _sorted_views_for_group(group, grouped[group])
        lane_count = final_lanes.get(group, lane_count_for_group(len(sorted_group)))
        width = 0 if lane_count == 1 else (lane_count - 1) * LANE_OFFSET
        columns.append(
            {
                "group": group,
                "x": cursor_x,
                "y": band_y,
                "count": len(sorted_group),
                "laneCount": lane_count,
                "width": width,
                "band": current_band,
            }
        )

        lanes: list[list[Mapping[str, Any]]] = [[] for _ in range(lane_count)]
        for index, view in enumerate(sorted_group):
            lanes[index % lane_count].append(view)
        for lane_index, lane in enumerate(lanes):
            lane_x = cursor_x + lane_index * LANE_OFFSET
            for row_index, view in enumerate(lane):
                positions[_view_id(view)] = {
                    "x": lane_x,
                    "y": band_y + COLUMN_HEADER_HEIGHT + row_index * ROW_GAP,
                }

        cursor_x += COLUMN_GAP + width
        group_in_band += 1

    total_used = len(views)
    column_counts = [int(column["count"]) for column in columns]
    max_column_height = max(column_counts, default=0)
    total_lane = max_column_height * max(len(column_counts), 1)
    blank_space_ratio = 1 - total_used / total_lane if total_lane > 0 else 0
    max_lane_height = max(
        ((int(c["count"]) + int(c["laneCount"]) - 1) // int(c["laneCount"]) for c in columns),
        default=0,
    )
    total_lanes = sum(int(c["laneCount"]) for c in columns)
    total_lane_slots = max_lane_height * max(total_lanes, 1)
    packed_blank_space_ratio = 1 - total_used / total_lane_slots if total_lane_slots > 0 else 0

    return {
        "positions": positions,
        "columns": columns,
        "layoutReceiptSummary": {
            "schema": "station_atlas_layout_receipt_python_port_v1",
            "layoutMode": "hybrid_shell_packer",
            "counts": {
                "nodes": len(views),
                "columns": len(columns),
                "totalLanes": total_lanes,
            },
            "columnGeometry": {
                "maxColumnHeight": max_column_height,
                "maxLaneHeight": max_lane_height,
                "blankSpaceRatio": round(blank_space_ratio, 3),
                "packedBlankSpaceRatio": round(packed_blank_space_ratio, 3),
                "perColumn": [
                    {
                        "group": c["group"],
                        "count": c["count"],
                        "laneCount": c["laneCount"],
                    }
                    for c in columns
                ],
            },
            "packingPolicy": {
                "lane2Threshold": LAYOUT_LANE2_THRESHOLD,
                "lane3Threshold": LAYOUT_LANE3_THRESHOLD,
                "laneOffsetPx": LANE_OFFSET,
                "columnGapPx": COLUMN_GAP,
                "rowGapPx": ROW_GAP,
                "sortKeys": [
                    "capture_posture",
                    "centrality_fanin_plus_fanout",
                    "label_alpha",
                ],
            },
        },
    }


def _generated_group_views(group_counts: Mapping[str, Any]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    for group in SHELL_GROUP_ORDER:
        count = int(group_counts.get(group) or 0)
        for index in range(count):
            views.append(
                {
                    "id": f"{group}_{index:02d}",
                    "label": f"{group.title()} {index:02d}",
                    "shellGroup": group,
                    "captureLatestStatus": "captured",
                    "captureSlug": f"{group}-{index:02d}",
                    "captureSampleCount": 1,
                    "fanout": 1,
                    "fanin": 1,
                }
            )
    return views


def _views_for_case(row: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    views = row.get("views")
    if isinstance(views, list):
        return [view for view in views if isinstance(view, Mapping)]
    counts = row.get("group_counts")
    if isinstance(counts, Mapping):
        return _generated_group_views(counts)
    return []


def _compare_expected_subset(
    observed: Any,
    expected: Any,
    *,
    code: str,
    message: str,
    case_id: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if isinstance(expected, list):
        if not isinstance(observed, list):
            return [finding(code, message, case_id=case_id, expected=expected, observed=observed)]
        for index, expected_row in enumerate(expected):
            actual_row = observed[index] if index < len(observed) else None
            if actual_row != expected_row:
                findings.append(
                    finding(
                        code,
                        message,
                        case_id=case_id,
                        expected=expected_row,
                        observed=actual_row,
                    )
                )
        return findings
    if isinstance(expected, Mapping):
        if not isinstance(observed, Mapping):
            return [finding(code, message, case_id=case_id, expected=expected, observed=observed)]
        for key, expected_value in expected.items():
            actual_value = observed.get(key)
            if actual_value != expected_value:
                findings.append(
                    finding(
                        code,
                        message,
                        case_id=case_id,
                        subject_id=str(key),
                        expected=expected_value,
                        observed=actual_value,
                    )
                )
        return findings
    return findings


def _case_rows(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("cases")
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _evaluate_reference_cases(probe: Mapping[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    case_results: list[dict[str, Any]] = []
    observed_ids: list[str] = []
    for row in _case_rows(probe):
        case_id = str(row.get("case_id") or "")
        layout = layout_nodes(_views_for_case(row))
        case_findings = []
        case_findings.extend(
            _compare_expected_subset(
                layout["columns"],
                row.get("expected_columns"),
                code="BATCH8_STATION_LAYOUT_COLUMN_MISMATCH",
                message="layoutNodes column geometry must match the public fixture expectation.",
                case_id=case_id,
            )
        )
        case_findings.extend(
            _compare_expected_subset(
                layout["positions"],
                row.get("expected_positions"),
                code="BATCH8_STATION_LAYOUT_POSITION_MISMATCH",
                message="layoutNodes positions must match the public fixture expectation.",
                case_id=case_id,
            )
        )
        receipt = layout["layoutReceiptSummary"]
        expected_receipt = row.get("expected_receipt_summary")
        if isinstance(expected_receipt, Mapping):
            for key, expected_value in expected_receipt.items():
                actual_value = receipt.get(key)
                if actual_value != expected_value:
                    case_findings.append(
                        finding(
                            "BATCH8_STATION_LAYOUT_RECEIPT_MISMATCH",
                            "layout receipt summary must match the public fixture expectation.",
                            case_id=case_id,
                            subject_id=str(key),
                            expected=expected_value,
                            observed=actual_value,
                        )
                    )
        observed_ids.append(case_id)
        findings.extend(case_findings)
        case_results.append(
            {
                "case_id": case_id,
                "status": "pass" if not case_findings else "blocked",
                "node_count": receipt["counts"]["nodes"],
                "column_count": receipt["counts"]["columns"],
                "total_lanes": receipt["counts"]["totalLanes"],
                "max_lane_height": receipt["columnGeometry"]["maxLaneHeight"],
                "packed_blank_space_ratio": receipt["columnGeometry"]["packedBlankSpaceRatio"],
                "body_in_receipt": False,
            }
        )

    for case_id in sorted(set(EXPECTED_CASES) - set(observed_ids)):
        findings.append(
            finding(
                "BATCH8_STATION_LAYOUT_REFERENCE_CASE_MISSING",
                "Station layout probe manifest is missing an expected reference case.",
                case_id=case_id,
            )
        )
    return case_results, findings


def _evaluate_negative_exercises(input_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings: list[dict[str, Any]] = []
    unknown_payload = load_json_object(
        input_path / "station_layout_unknown_group_routed_unassigned.json",
        findings,
        label="unknown group negative",
    )
    attention_payload = load_json_object(
        input_path / "station_layout_attention_sort_required.json",
        findings,
        label="attention sort negative",
    )
    slack_payload = load_json_object(
        input_path / "station_layout_slack_lane_spend_required.json",
        findings,
        label="slack lane negative",
    )

    unknown_layout = layout_nodes(
        [
            {
                "id": "future_surface",
                "label": "Future Surface",
                "shellGroup": "future_group",
                "captureLatestStatus": None,
                "captureSlug": None,
                "captureSampleCount": 0,
                "fanout": 0,
                "fanin": 0,
            }
        ]
    )
    unknown_group = unknown_layout["columns"][0]["group"] if unknown_layout["columns"] else None
    if unknown_group != "unassigned" or unknown_payload.get("expected_column_group") != "unassigned":
        findings.append(
            finding(
                "BATCH8_STATION_LAYOUT_UNKNOWN_GROUP_ROUTED_UNASSIGNED",
                "Unknown shell groups must route through the unassigned column.",
                expected="unassigned",
                observed=unknown_group,
            )
        )

    attention_layout = layout_nodes(
        [
            {
                "id": "high_centrality_captured",
                "label": "AAA High Centrality",
                "shellGroup": "operate",
                "captureLatestStatus": "captured",
                "captureSlug": "high",
                "captureSampleCount": 1,
                "fanout": 100,
                "fanin": 100,
            },
            {
                "id": "failed_low_centrality",
                "label": "ZZZ Failed",
                "shellGroup": "operate",
                "captureLatestStatus": "failed",
                "captureSlug": "failed",
                "captureSampleCount": 1,
                "fanout": 0,
                "fanin": 0,
            },
        ]
    )
    failed_y = attention_layout["positions"]["failed_low_centrality"]["y"]
    high_y = attention_layout["positions"]["high_centrality_captured"]["y"]
    if not failed_y < high_y or attention_payload.get("expected_first_id") != "failed_low_centrality":
        findings.append(
            finding(
                "BATCH8_STATION_LAYOUT_ATTENTION_SORT_REQUIRED",
                "Failed/readiness-timeout capture posture must sort above centrality.",
                expected={"failed_y_lt_high_y": True},
                observed={"failed_y": failed_y, "high_y": high_y},
            )
        )

    slack_layout = layout_nodes(
        _generated_group_views(
            {
                "operate": 7,
                "missions": 2,
                "data": 5,
                "inspect": 6,
                "map": 15,
                "library": 3,
                "unassigned": 1,
            }
        )
    )
    map_column = next((c for c in slack_layout["columns"] if c["group"] == "map"), {})
    if map_column.get("laneCount") != 5 or slack_payload.get("expected_map_lane_count") != 5:
        findings.append(
            finding(
                "BATCH8_STATION_LAYOUT_SLACK_LANE_SPEND_REQUIRED",
                "Narrow lower bands must spend horizontal slack on the tallest group.",
                expected=5,
                observed=map_column.get("laneCount"),
            )
        )

    return (
        {
            "unknown_group_column": unknown_group,
            "attention_failed_y": failed_y,
            "attention_high_y": high_y,
            "slack_map_lane_count": map_column.get("laneCount"),
            "status": "pass" if not findings else "blocked",
            "body_in_receipt": False,
        },
        findings,
    )


def _source_authority_binding_findings(
    source_manifest: Mapping[str, Any],
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    modules = source_manifest.get("modules")
    module_rows = (
        [row for row in modules if isinstance(row, Mapping)]
        if isinstance(modules, list)
        else []
    )
    for row in module_rows:
        source_ref = str(row.get("source_ref") or "")
        if source_ref != TSX_SOURCE_REF:
            continue
        relation = str(row.get("source_to_target_relation") or "")
        verification = str(row.get("source_ref_verification") or "")
        if (
            verification == "public_copy_target_digest_only"
            and relation not in ALLOWED_DETACHED_PUBLIC_REFACTOR_RELATIONS
            and row.get("sha256") != TSX_SOURCE_SHA256
        ):
            findings.append(
                finding(
                    "BATCH8_STATION_SOURCE_AUTHORITY_RELATION_REQUIRED",
                    (
                        "Detached StationSurfaceAtlas copied source modules must not prove "
                        "exact-copy authority from bundle-local rehashed digests alone; "
                        "use the component source digest floor, a live source_ref exact-copy "
                        "check, or an explicit public-safe refactor relation."
                    ),
                    subject_id=source_ref,
                    expected={
                        "source_sha256": TSX_SOURCE_SHA256,
                        "public_refactor_relations": sorted(
                            ALLOWED_DETACHED_PUBLIC_REFACTOR_RELATIONS
                        ),
                    },
                    observed={
                        "sha256": row.get("sha256"),
                        "source_ref_verification": verification,
                        "source_to_target_relation": relation,
                    },
                )
            )
    return findings


def evaluate_negative_case(
    case_id: str,
    _input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    if case_id == "station_layout_unknown_group_routed_unassigned":
        layout = layout_nodes(
            [
                {
                    "id": "future_surface",
                    "label": "Future Surface",
                    "shellGroup": "future_group",
                    "captureLatestStatus": None,
                    "captureSlug": None,
                    "captureSampleCount": 0,
                    "fanout": 0,
                    "fanin": 0,
                }
            ]
        )
        observed = layout["columns"][0]["group"] if layout["columns"] else None
        rejected = observed == "unassigned"
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STATION_LAYOUT_UNKNOWN_GROUP_ROUTED_UNASSIGNED"]
                if rejected
                else []
            ),
            "observed": {"unknown_group_column": observed},
            "derived_from": "layout_nodes_python_port",
            "body_in_receipt": False,
        }
    if case_id == "station_layout_attention_sort_required":
        layout = layout_nodes(
            [
                {
                    "id": "high_centrality_captured",
                    "label": "AAA High Centrality",
                    "shellGroup": "operate",
                    "captureLatestStatus": "captured",
                    "captureSlug": "high",
                    "captureSampleCount": 1,
                    "fanout": 100,
                    "fanin": 100,
                },
                {
                    "id": "failed_low_centrality",
                    "label": "ZZZ Failed",
                    "shellGroup": "operate",
                    "captureLatestStatus": "failed",
                    "captureSlug": "failed",
                    "captureSampleCount": 1,
                    "fanout": 0,
                    "fanin": 0,
                },
            ]
        )
        failed_y = layout["positions"]["failed_low_centrality"]["y"]
        high_y = layout["positions"]["high_centrality_captured"]["y"]
        rejected = failed_y < high_y
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STATION_LAYOUT_ATTENTION_SORT_REQUIRED"] if rejected else []
            ),
            "observed": {"failed_y": failed_y, "high_y": high_y},
            "derived_from": "layout_nodes_python_port",
            "body_in_receipt": False,
        }
    if case_id == "station_layout_slack_lane_spend_required":
        layout = layout_nodes(
            _generated_group_views(
                {
                    "operate": 7,
                    "missions": 2,
                    "data": 5,
                    "inspect": 6,
                    "map": 15,
                    "library": 3,
                    "unassigned": 1,
                }
            )
        )
        map_column = next((c for c in layout["columns"] if c["group"] == "map"), {})
        lane_count = map_column.get("laneCount")
        rejected = lane_count == 5
        return {
            "status": "blocked" if rejected else "pass",
            "case_id": case_id,
            "error_codes": (
                ["BATCH8_STATION_LAYOUT_SLACK_LANE_SPEND_REQUIRED"]
                if rejected
                else []
            ),
            "observed": {"slack_map_lane_count": lane_count},
            "derived_from": "layout_nodes_python_port",
            "body_in_receipt": False,
        }
    return {
        "status": "pass",
        "case_id": case_id,
        "error_codes": [],
        "body_in_receipt": False,
    }


def _layout_evaluator(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    del public_root
    probe = load_json_object(input_path / PROBE_MANIFEST_NAME, [], label=PROBE_MANIFEST_NAME)
    case_results, case_findings = _evaluate_reference_cases(probe)
    negative_results, negative_findings = _evaluate_negative_exercises(input_path)
    source_authority_findings = _source_authority_binding_findings(source_manifest)
    findings = [*case_findings, *negative_findings, *source_authority_findings]
    passed_case_count = sum(1 for row in case_results if row.get("status") == "pass")
    return {
        "status": "pass" if not findings else "blocked",
        "engine_id": "station_surface_atlas_layout_nodes_python_port",
        "source_language": "TypeScript React",
        "port_language": "Python",
        "source_ref": TSX_SOURCE_REF,
        "constants": {
            "columnGapPx": COLUMN_GAP,
            "rowGapPx": ROW_GAP,
            "columnHeaderHeightPx": COLUMN_HEADER_HEIGHT,
            "nodeWidthPx": NODE_WIDTH,
            "laneOffsetPx": LANE_OFFSET,
            "lane2Threshold": LAYOUT_LANE2_THRESHOLD,
            "lane3Threshold": LAYOUT_LANE3_THRESHOLD,
            "bandTrigger": LAYOUT_BAND_TRIGGER,
            "bandGapPx": BAND_GAP,
        },
        "reference_case_count": len(case_results),
        "passed_reference_case_count": passed_case_count,
        "expected_reference_cases": list(EXPECTED_CASES),
        "reference_cases": case_results,
        "negative_exercises": negative_results,
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "source_authority_binding": {
            "status": "pass" if not source_authority_findings else "blocked",
            "detached_bundle_exact_copy_requires_live_source": True,
            "allowed_detached_public_refactor_relations": sorted(
                ALLOWED_DETACHED_PUBLIC_REFACTOR_RELATIONS
            ),
            "body_in_receipt": False,
        },
        "error_codes": sorted(
            {
                "BATCH8_STATION_LAYOUT_ATTENTION_SORT_REQUIRED",
                "BATCH8_STATION_LAYOUT_SLACK_LANE_SPEND_REQUIRED",
                "BATCH8_STATION_LAYOUT_UNKNOWN_GROUP_ROUTED_UNASSIGNED",
            }
        ),
        "claim_ceiling": "Pure deterministic layoutNodes parity only; no React runtime, visual render, navigation graph, or release authority.",
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_layout_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch8_station_surface_atlas_layout_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_layout_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    source = (
        result.get("source_module_manifest")
        if isinstance(result.get("source_module_manifest"), Mapping)
        else {}
    )
    ceiling = (
        result.get("authority_ceiling")
        if isinstance(result.get("authority_ceiling"), Mapping)
        else {}
    )
    card["reference_case_count"] = exercise.get("reference_case_count")
    card["passed_reference_case_count"] = exercise.get("passed_reference_case_count")
    card["authority_floor"] = {
        "authority_ceiling": ceiling.get("authority_ceiling"),
        "real_substrate_disposition": ceiling.get("real_substrate_disposition"),
        "python_port": ceiling.get("python_port"),
        "react_runtime_started": ceiling.get("react_runtime_started"),
        "browser_render_authorized": ceiling.get("browser_render_authorized"),
        "navigation_graph_authority": ceiling.get("navigation_graph_authority"),
        "repo_mutation_authorized": ceiling.get("repo_mutation_authorized"),
        "source_mutation_authorized": ceiling.get("source_mutation_authorized"),
        "publication_authorized": ceiling.get("publication_authorized"),
        "release_authorized": ceiling.get("release_authorized"),
    }
    card["body_floor"] = {
        "body_in_receipt": result.get("body_in_receipt"),
        "source_module_body_in_receipt": source.get("body_in_receipt"),
        "receipt_body_scan_status": (
            result.get("receipt_body_scan", {}).get("status")
            if isinstance(result.get("receipt_body_scan"), Mapping)
            else None
        ),
        "source_bodies_in_card": False,
        "secret_scan_scope_in_card": False,
    }
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"microcosm {ORGAN_ID}")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "validate-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    result = run_crown_jewel_organ(
        SPEC,
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=(
            BUNDLE_INPUT_MODE
            if args.action == "validate-bundle"
            else "fixture_input"
        ),
        evaluator=_layout_evaluator,
        negative_case_evaluator=evaluate_negative_case,
    )
    print(
        json.dumps(
            result_card(result) if args.card else result,
            indent=2,
            sort_keys=True,
        )
    )
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
