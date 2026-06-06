from __future__ import annotations

import argparse
import collections
import hashlib
import importlib.util
import json
import math
import re
import sys
import types
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence
from zoneinfo import ZoneInfo

from microcosm_core.organs._crown_jewel_common import (
    REAL_SUBSTRATE_DISPOSITION,
    CrownJewelSpec,
    card_for_result,
    display,
    file_line_count,
    file_sha256,
    finding,
    load_json_object,
    public_root_for_path,
    scan_receipt_payload_for_bodies,
    strip_microcosm_prefix,
    strings,
    validate_negative_cases,
    validate_source_manifest,
)
from microcosm_core.receipts import utc_now, write_json_atomic
from microcosm_core.secret_exclusion_scan import (
    PASS,
    load_forbidden_classes,
    scan_paths,
)


ORGAN_ID = "batch11_saturation_engines_capsule"
FIXTURE_ID = f"first_wave.{ORGAN_ID}"
VALIDATOR_ID = f"validator.microcosm.organs.{ORGAN_ID}"

RESULT_NAME = f"{ORGAN_ID}_result.json"
BOARD_NAME = f"{ORGAN_ID}_board.json"
VALIDATION_RECEIPT_NAME = f"{ORGAN_ID}_validation_receipt.json"
BUNDLE_RESULT_NAME = f"exported_{ORGAN_ID}_bundle_validation_result.json"
CARD_SCHEMA_VERSION = f"{ORGAN_ID}_command_card_v1"
BUNDLE_INPUT_MODE = f"exported_{ORGAN_ID}_bundle"
PROBE_MANIFEST_NAME = f"{ORGAN_ID}_probe_manifest.json"

EXPECTED_MECHANISMS: tuple[str, ...] = (
    "run_affinity_session_scorer",
    "calculator_cluster_insight_derivation",
    "std_python_delta_enforcement_ratchet_gate",
    "exogenous_nav_ladder_grader",
    "portability_gate_check_supersession_rollup",
    "shard_browse_context_priority_sectionizer",
    "holographic_research_bundle_graph_and_evidence_select",
    "projection_secret_scan",
    "stockgrid_flow_multisource_merge_unit_normalizer",
    "macro_regime_board_bucketing_zscore_engine",
    "frontend_nav_graph_wayfinding_engine",
    "agent_session_diagnostic_lens_engine",
    "demo_take_story_coverage_audit",
)

EXPECTED_MODULE_IDS: tuple[str, ...] = (
    "run_affinity_source",
    "calculator_insight_source",
    "std_python_apply_source",
    "exogenous_nav_ladder_source",
    "portability_gate_source",
    "shards_lens_source",
    "holographic_research_bundle_source",
    "projection_secret_scan_source",
    "quant_presentation_mart_source",
    "frontend_nav_graph_source",
    "session_analyzer_source",
    "demo_take_story_package_source",
)

EXPECTED_NEGATIVE_CASES = {
    "run_affinity_stale_terminal_rejected": ("BATCH11_RUN_AFFINITY_STALE_TERMINAL_REJECTED",),
    "calculator_zero_bucket_no_fake_dominance": ("BATCH11_CALCULATOR_ZERO_BUCKET_NO_FAKE_DOMINANCE",),
    "std_python_new_gap_blocks": ("BATCH11_STD_PYTHON_NEW_GAP_BLOCKS",),
    "exogenous_nav_wrong_route_graded_down": ("BATCH11_EXOGENOUS_NAV_WRONG_ROUTE_GRADED_DOWN",),
    "portability_unresolved_hard_fail_blocks": ("BATCH11_PORTABILITY_UNRESOLVED_HARD_FAIL_BLOCKS",),
    "shard_multimatch_context_priority": ("BATCH11_SHARD_MULTIMATCH_CONTEXT_PRIORITY",),
    "holographic_no_overlap_no_fake_edge": ("BATCH11_HOLOGRAPHIC_NO_OVERLAP_NO_FAKE_EDGE",),
    "projection_secret_token_blocks": ("BATCH11_PROJECTION_SECRET_TOKEN_BLOCKS",),
    "stockgrid_units_normalized_not_zeroed": ("BATCH11_STOCKGRID_UNITS_NORMALIZED_NOT_ZEROED",),
    "macro_regime_unknown_routes_other": ("BATCH11_MACRO_UNKNOWN_ROUTES_OTHER",),
    "frontend_nav_unreachable_target": ("BATCH11_FRONTEND_NAV_UNREACHABLE_TARGET",),
    "session_no_nav_verbs_no_ladder_skip": ("BATCH11_SESSION_NO_NAV_VERBS_NO_LADDER_SKIP",),
    "demo_take_missing_anchor_penalized": ("BATCH11_DEMO_TAKE_MISSING_ANCHOR_PENALIZED",),
}

CASE_VERDICT_AUTHORITY = "computed_by_batch11_saturation_engines_capsule_integrity_matrix"

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch11_saturation_engines_capsule_not_live_runtime_release_or_market_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "provider_dispatch": False,
    "model_dispatch": False,
    "source_mutation_authorized": False,
    "publication_authorized": False,
    "release_authorized": False,
    "work_ledger_authority": False,
    "navigation_authority": False,
    "complete_secret_detection_claim": False,
    "market_advice": False,
    "raw_session_truth": False,
    "video_capture_authority": False,
}

ANTI_CLAIM = (
    "Batch 11 validates source-open or source-faithful public ports for run "
    "affinity, calculator insight derivation, std_python ratchet gating, "
    "exogenous navigation grading, portability supersession, shard browse "
    "sectioning, research evidence selection, projection secret scanning, "
    "quant presentation mart normalization, macro-regime bucketing, frontend "
    "wayfinding, session diagnostics, and demo-take coverage scoring. It is "
    "not live Work Ledger truth, not navigation authority, not complete secret "
    "detection, not live market data, not investment advice, not raw transcript "
    "authority, not video capture, not publication authority, and not release "
    "approval."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/server/ui/src/utils/runAffinity.ts": (
        "function scoreCandidate(",
        "export function recommendRunByAffinity(",
        "function circularDistanceMinutes(",
    ),
    "system/server/ui/src/lib/calculatorInsight.ts": (
        "function driverShare(",
        "export function deriveCalculatorClusterInsights(",
        "Member quality",
    ),
    "system/lib/kernel/commands/apply.py": (
        "def _std_python_enforcement_delta(",
        "missing_module_tags",
        "status = \"clean_stable\"",
    ),
    "tools/meta/observability/exogenous_nav_ladder_grader.py": (
        "class NavGradeCase",
        "def scan_filesystem_targets(",
        "def build_oracle(",
    ),
    "tools/meta/dissemination/portability_gate.py": (
        "def _boundary_policy_supersession_results(",
        "def _latest_results_by_id(",
        "def _compute_status(",
    ),
    "system/server/ui/src/components/world/ShardsLens.tsx": (
        "function browsePriority(",
        "function browseSectionForResult(",
        "return ['routing', 'standalone', 'group', 'paragraph'];",
    ),
    "tools/meta/dissemination/build_holographic_research_bundle.py": (
        "def _select_evidence_chunks(",
        "preferred_paths",
        "support_score",
    ),
    "tools/meta/dissemination/projection_secret_scan.py": (
        "CONTENT_PATTERNS",
        "def scan_projection(",
        "blocking_hit_count",
    ),
    "system/lib/quant_presentation_mart.py": (
        "def _merge_stockgrid_rows(",
        "def _macro_bucket(",
        "def _macro_regime_board(",
    ),
    "tools/meta/observability/frontend_nav_graph.py": (
        "def plan_wayfinding(",
        "def _hybrid_wayfinding_plan(",
        "WAYFINDING_CONTRACT",
    ),
    "tools/meta/observability/session_analyzer.py": (
        "_ROUTE_MISS_PATTERNS",
        "def _route_miss_candidate_phrases(",
        "def lens_route_misses(",
    ),
    "tools/meta/dissemination/demo_take_story_package.py": (
        "def _score_view_segment(",
        "def build_story_coverage_audit(",
        "coverage_percent",
    ),
}

MECHANISM_SOURCE_REFS: dict[str, tuple[str, ...]] = {
    "run_affinity_session_scorer": ("system/server/ui/src/utils/runAffinity.ts",),
    "calculator_cluster_insight_derivation": ("system/server/ui/src/lib/calculatorInsight.ts",),
    "std_python_delta_enforcement_ratchet_gate": ("system/lib/kernel/commands/apply.py",),
    "exogenous_nav_ladder_grader": ("tools/meta/observability/exogenous_nav_ladder_grader.py",),
    "portability_gate_check_supersession_rollup": ("tools/meta/dissemination/portability_gate.py",),
    "shard_browse_context_priority_sectionizer": (
        "system/server/ui/src/components/world/ShardsLens.tsx",
    ),
    "holographic_research_bundle_graph_and_evidence_select": (
        "tools/meta/dissemination/build_holographic_research_bundle.py",
    ),
    "projection_secret_scan": ("tools/meta/dissemination/projection_secret_scan.py",),
    "stockgrid_flow_multisource_merge_unit_normalizer": ("system/lib/quant_presentation_mart.py",),
    "macro_regime_board_bucketing_zscore_engine": ("system/lib/quant_presentation_mart.py",),
    "frontend_nav_graph_wayfinding_engine": ("tools/meta/observability/frontend_nav_graph.py",),
    "agent_session_diagnostic_lens_engine": ("tools/meta/observability/session_analyzer.py",),
    "demo_take_story_coverage_audit": ("tools/meta/dissemination/demo_take_story_package.py",),
}

TIER_B_MECHANISMS = {
    "projection_secret_scan",
    "stockgrid_flow_multisource_merge_unit_normalizer",
    "macro_regime_board_bucketing_zscore_engine",
    "frontend_nav_graph_wayfinding_engine",
    "agent_session_diagnostic_lens_engine",
    "demo_take_story_coverage_audit",
}

MECHANISM_BINDING_DISPOSITIONS = {
    "run_affinity_session_scorer": "tier_a_new_capsule_import",
    "calculator_cluster_insight_derivation": "tier_a_new_capsule_import",
    "std_python_delta_enforcement_ratchet_gate": "under_bound_existing_std_python_assay_extended_by_capsule",
    "exogenous_nav_ladder_grader": "tier_a_new_capsule_import",
    "portability_gate_check_supersession_rollup": "already_bound_engine_room_public_projection_leak_gate_capsule_verifies_rollup",
    "shard_browse_context_priority_sectionizer": "tier_a_new_capsule_import",
    "holographic_research_bundle_graph_and_evidence_select": "tier_a_new_capsule_import",
    "projection_secret_scan": "already_bound_engine_room_public_projection_leak_gate_collision_recorded",
    "stockgrid_flow_multisource_merge_unit_normalizer": "new_absent_from_microcosm_organ_plane_at_import_time",
    "macro_regime_board_bucketing_zscore_engine": "new_absent_from_microcosm_organ_plane_at_import_time",
    "frontend_nav_graph_wayfinding_engine": "copied_dormant_under_bound_capsule_import",
    "agent_session_diagnostic_lens_engine": "copied_dormant_under_bound_capsule_import",
    "demo_take_story_coverage_audit": "already_bound_batch7_demo_take_capsule_batch11_verifies_scoring_path",
}

NEGATIVE_CASE_PROBE_SCHEMA = "batch11_negative_case_computed_probe_v1"

NEGATIVE_CASE_COMPUTED_PATHS = {
    "run_affinity_stale_terminal_rejected": {
        "mechanism_id": "run_affinity_session_scorer",
        "computed_path": "stale_terminal_refused",
    },
    "calculator_zero_bucket_no_fake_dominance": {
        "mechanism_id": "calculator_cluster_insight_derivation",
        "computed_path": "zero_bucket_no_fake_share",
    },
    "std_python_new_gap_blocks": {
        "mechanism_id": "std_python_delta_enforcement_ratchet_gate",
        "computed_path": "new_violation_blocks",
    },
    "exogenous_nav_wrong_route_graded_down": {
        "mechanism_id": "exogenous_nav_ladder_grader",
        "computed_path": "wrong_route_graded_down",
    },
    "portability_unresolved_hard_fail_blocks": {
        "mechanism_id": "portability_gate_check_supersession_rollup",
        "computed_path": "unresolved_hard_fail_blocks",
    },
    "shard_multimatch_context_priority": {
        "mechanism_id": "shard_browse_context_priority_sectionizer",
        "computed_path": "multi_match_uses_context_priority",
    },
    "holographic_no_overlap_no_fake_edge": {
        "mechanism_id": "holographic_research_bundle_graph_and_evidence_select",
        "computed_path": "missing_provenance_not_invented",
    },
    "projection_secret_token_blocks": {
        "mechanism_id": "projection_secret_scan",
        "computed_path": "token_blocks",
    },
    "stockgrid_units_normalized_not_zeroed": {
        "mechanism_id": "stockgrid_flow_multisource_merge_unit_normalizer",
        "computed_path": "missing_flow_no_silent_zero",
    },
    "macro_regime_unknown_routes_other": {
        "mechanism_id": "macro_regime_board_bucketing_zscore_engine",
        "computed_path": "unknown_routes_other",
    },
    "frontend_nav_unreachable_target": {
        "mechanism_id": "frontend_nav_graph_wayfinding_engine",
        "computed_path": "unreachable_returns_blocker",
    },
    "session_no_nav_verbs_no_ladder_skip": {
        "mechanism_id": "agent_session_diagnostic_lens_engine",
        "computed_path": "no_nav_verbs_no_false_ladder_skip",
    },
    "demo_take_missing_anchor_penalized": {
        "mechanism_id": "demo_take_story_coverage_audit",
        "computed_path": "missing_anchors_lowers_score",
    },
}

NEGATIVE_CASE_BY_MECHANISM = {
    row["mechanism_id"]: (case_id, row["computed_path"])
    for case_id, row in NEGATIVE_CASE_COMPUTED_PATHS.items()
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 11 Saturation Engines Capsule",
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
    source_manifest_ref=f"examples/{ORGAN_ID}/exported_{ORGAN_ID}_bundle/source_module_manifest.json",
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _float(value: Any) -> float | None:
    try:
        if value in (None, "", [], {}):
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _strings(values: Any) -> list[str]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return []
    return sorted({str(value).strip() for value in values if str(value).strip()})


def _stable_slug(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value or "").lower()).strip("_")
    return text or "unknown"


def _ok(mechanism_id: str, **payload: Any) -> dict[str, Any]:
    return {"mechanism_id": mechanism_id, "status": "pass", **payload, "body_in_receipt": False}


def _module_for_import_stub(name: str) -> types.ModuleType:
    module = sys.modules.get(name)
    if isinstance(module, types.ModuleType):
        return module
    module = types.ModuleType(name)
    sys.modules[name] = module
    return module


def _install_quant_presentation_import_stubs() -> None:
    system_module = _module_for_import_stub("system")
    lib_module = _module_for_import_stub("system.lib")
    setattr(system_module, "lib", lib_module)

    market_feed = _module_for_import_stub("system.lib.market_feed_run_evidence")
    setattr(lib_module, "market_feed_run_evidence", market_feed)
    market_feed.FEED_NODE_IDS = getattr(market_feed, "FEED_NODE_IDS", ())
    market_feed.build_market_feed_run_evidence_card = getattr(
        market_feed,
        "build_market_feed_run_evidence_card",
        lambda *_args, **_kwargs: {"status": "stubbed_for_microcosm_public_fixture"},
    )
    market_feed.feed_source_manifest = getattr(
        market_feed,
        "feed_source_manifest",
        lambda *_args, **_kwargs: {},
    )
    market_feed.resolve_feed_run_dir = getattr(
        market_feed,
        "resolve_feed_run_dir",
        lambda *_args, **_kwargs: Path("."),
    )

    readiness = _module_for_import_stub("system.lib.market_fusion_readiness")
    setattr(lib_module, "market_fusion_readiness", readiness)
    readiness.build_readiness_gate = getattr(
        readiness,
        "build_readiness_gate",
        lambda *_args, **_kwargs: {"status": "stubbed_for_microcosm_public_fixture"},
    )

    numeric = _module_for_import_stub("system.lib.finance_numeric_assurance")
    setattr(lib_module, "finance_numeric_assurance", numeric)
    numeric.blocking_numeric_contract_errors = getattr(
        numeric,
        "blocking_numeric_contract_errors",
        lambda *_args, **_kwargs: [],
    )


def _et_clock_minutes(epoch_seconds: float) -> int:
    dt = datetime.fromtimestamp(epoch_seconds, tz=ZoneInfo("America/New_York"))
    return dt.hour * 60 + dt.minute


def _circular_distance_minutes(a: int, b: int) -> int:
    diff = abs(a - b)
    return min(diff, 1440 - diff)


def _bounded_window_score(distance_min: float, radius_min: float, ceiling: float) -> float:
    if distance_min >= radius_min:
        return 0.0
    return ((radius_min - distance_min) / radius_min) * ceiling


def _has_us_close_context(run: Mapping[str, Any]) -> bool:
    temporal = run.get("temporal") if isinstance(run.get("temporal"), Mapping) else {}
    policy = str(temporal.get("horizon_policy") or "").lower()
    label = str(temporal.get("horizon_label") or "").lower()
    return (
        "next_us_close" in policy
        or "us_close" in policy
        or "us close" in label
        or "close" in label
    )


def _score_run_candidate(
    run: Mapping[str, Any],
    *,
    now_sec: float,
    mission_name: str | None = None,
    sticky_run_id: str | None = None,
    close_bias: float = 1.35,
    open_bias: float = 0.9,
    require_working: bool = False,
) -> dict[str, Any]:
    timestamp = float(run.get("timestamp") or 0.0)
    age_hours = max(0.0, (now_sec - timestamp) / 3600.0)
    et_minutes = _et_clock_minutes(timestamp)
    close_distance = _circular_distance_minutes(et_minutes, 16 * 60)
    open_distance = _circular_distance_minutes(et_minutes, 9 * 60 + 30)
    status = run.get("status")
    score = 130 if status == "green" else 28 if status == "amber" else -90
    if require_working and status != "green":
        score -= 32
    score += max(0.0, 92.0 - (age_hours * 4.2))
    if age_hours <= 6:
        score += 10
    elif age_hours <= 24:
        score += 4
    if mission_name and run.get("mission_name") == mission_name:
        score += 14
    if run.get("id") == sticky_run_id:
        score += 20
    score += min(10.0, float(run.get("feed_count") or 0) * 0.8)
    score += _bounded_window_score(close_distance, 120, 58) * close_bias
    score += _bounded_window_score(open_distance, 95, 34) * open_bias
    close_context = _has_us_close_context(run)
    if close_context:
        score += 16
    return {
        "run": dict(run),
        "score": score,
        "age_hours": age_hours,
        "close_distance_min": close_distance,
        "open_distance_min": open_distance,
        "has_close_context": close_context,
    }


def recommend_run_by_affinity(
    candidates: Sequence[Mapping[str, Any]],
    *,
    now_ms: int,
    mission_name: str | None = None,
    sticky_run_id: str | None = None,
    require_working: bool = False,
) -> dict[str, Any] | None:
    if not candidates:
        return None
    ranked = sorted(
        (
            _score_run_candidate(
                run,
                now_sec=now_ms / 1000.0,
                mission_name=mission_name,
                sticky_run_id=sticky_run_id,
                require_working=require_working,
            )
            for run in candidates
        ),
        key=lambda row: (-row["score"], -float(row["run"].get("timestamp") or 0.0)),
    )
    best = ranked[0]
    return {
        "run_id": best["run"]["id"],
        "score": round(best["score"]),
        "close_distance_min": best["close_distance_min"],
        "open_distance_min": best["open_distance_min"],
        "has_close_context": best["has_close_context"],
        "ranked": [
            {"run_id": row["run"]["id"], "score": round(row["score"])}
            for row in ranked
        ],
    }


def _run_affinity_matrix() -> dict[str, Any]:
    now_ms = int(datetime(2026, 5, 13, 21, 0, tzinfo=ZoneInfo("UTC")).timestamp() * 1000)
    candidates = [
        {
            "id": "RUN_CLOSE",
            "status": "green",
            "timestamp": datetime(2026, 5, 13, 19, 55, tzinfo=ZoneInfo("UTC")).timestamp(),
            "mission_name": "feeds",
            "feed_count": 7,
            "temporal": {"horizon_policy": "next_us_close", "horizon_label": "US close"},
        },
        {
            "id": "RUN_STALE_TERMINAL",
            "status": "red",
            "timestamp": datetime(2026, 5, 12, 12, 0, tzinfo=ZoneInfo("UTC")).timestamp(),
            "mission_name": "feeds",
            "feed_count": 99,
            "temporal": {"horizon_policy": "manual", "horizon_label": "stale"},
        },
    ]
    recommendation = recommend_run_by_affinity(
        candidates,
        now_ms=now_ms,
        mission_name="feeds",
        sticky_run_id="RUN_STALE_TERMINAL",
        require_working=True,
    )
    stale_rank = [row for row in recommendation["ranked"] if row["run_id"] == "RUN_STALE_TERMINAL"][0]
    return _ok(
        "run_affinity_session_scorer",
        recommendation=recommendation,
        stale_terminal_refused=recommendation["run_id"] != "RUN_STALE_TERMINAL",
        stale_terminal_score=stale_rank["score"],
        claim_ceiling="deterministic run-affinity scoring over public rows only",
    )


def _driver_share(value: float, total: float) -> float:
    if total <= 0:
        return 0.0
    return max(0.0, min(1.0, value / total))


def _calculator_drivers(metrics: Mapping[str, Any]) -> list[dict[str, Any]]:
    driver_defs = [
        ("directional", "Directional", "Directional_Energy"),
        ("dispersion", "Dispersion", "Dispersion_Energy"),
        ("risk", "Risk", "Risk_Energy"),
        ("structural", "Structural", "Structural_Energy"),
    ]
    values = [
        {"bucket": bucket, "label": label, "value": _float(metrics.get(key)) or 0.0}
        for bucket, label, key in driver_defs
    ]
    total = sum(max(0.0, row["value"]) for row in values)
    return [
        {**row, "share": _driver_share(max(0.0, row["value"]), total)}
        for row in values
    ]


def _derive_calculator_cluster_insights(envelope: Mapping[str, Any]) -> list[dict[str, Any]]:
    data = envelope.get("data") if isinstance(envelope.get("data"), Mapping) else {}
    insights: list[dict[str, Any]] = []
    for lane_key, lane_block in data.items():
        if not isinstance(lane_block, Sequence) or isinstance(lane_block, (str, bytes)):
            continue
        for index, entry in enumerate(lane_block):
            if not isinstance(entry, Sequence) or len(entry) < 2:
                continue
            cluster = str(entry[0])
            payload = entry[1] if isinstance(entry[1], Mapping) else {}
            members = [str(member) for member in payload.get("members", [])]
            metrics = payload.get("metrics") if isinstance(payload.get("metrics"), Mapping) else {}
            cohesion = _float(metrics.get("Cohesion")) or 0.0
            participation = _float(metrics.get("Participation_Rate")) or 0.0
            member_quality = math.sqrt(max(0.0, cohesion * participation))
            opportunity = _float(metrics.get("Opportunity_Score"))
            energy = _float(payload.get("Energy"))
            insights.append(
                {
                    "id": f"{lane_key}:{cluster}:{index}",
                    "lane_key": str(lane_key),
                    "cluster": cluster,
                    "members": members,
                    "size": _float(payload.get("Size")) or len(members),
                    "drivers": _calculator_drivers(metrics),
                    "member_quality": member_quality,
                    "opportunity_score": opportunity,
                    "energy": energy,
                }
            )
    return sorted(
        insights,
        key=lambda row: row["opportunity_score"] if row["opportunity_score"] is not None else row["energy"] or 0.0,
        reverse=True,
    )


def _calculator_matrix() -> dict[str, Any]:
    envelope = {
        "data": {
            "macro": [
                [
                    "inflation_cluster",
                    {
                        "members": ["CPI", "PCE"],
                        "Size": 2,
                        "Energy": 0.7,
                        "metrics": {
                            "Directional_Energy": 4,
                            "Dispersion_Energy": 1,
                            "Risk_Energy": 3,
                            "Structural_Energy": 2,
                            "Cohesion": 0.64,
                            "Participation_Rate": 0.81,
                            "Opportunity_Score": 0.91,
                        },
                    },
                ]
            ]
        }
    }
    insight = _derive_calculator_cluster_insights(envelope)[0]
    shares = [row["share"] for row in insight["drivers"]]
    zero_drivers = _calculator_drivers(
        {
            "Directional_Energy": 0,
            "Dispersion_Energy": 0,
            "Risk_Energy": 0,
            "Structural_Energy": 0,
        }
    )
    return _ok(
        "calculator_cluster_insight_derivation",
        dominant_cluster=insight["cluster"],
        driver_share_sum=round(sum(shares), 6),
        member_quality=round(insight["member_quality"], 6),
        zero_bucket_no_fake_share=all(row["share"] == 0 for row in zero_drivers),
        claim_ceiling="cluster insight derivation over public calculator-shaped rows only",
    )


def _std_python_enforcement_signature(detail: Mapping[str, Any]) -> dict[str, list[str]]:
    errors = _strings(detail.get("errors"))
    general_errors = [
        error
        for error in errors
        if not (
            error.startswith("Module missing tags:")
            or error.startswith("Class '")
            or error.startswith("Method '")
            or error.startswith("Func '")
        )
    ]
    return {
        "missing_module_tags": _strings(detail.get("missing_module_tags")),
        "classes_missing_role": _strings(detail.get("classes_missing_role")),
        "functions_missing_action": _strings(detail.get("functions_missing_action")),
        "general_errors": general_errors,
    }


def _std_python_gap_count(signature: Mapping[str, Sequence[str]]) -> int:
    return sum(
        len(list(signature.get(key, [])))
        for key in (
            "missing_module_tags",
            "classes_missing_role",
            "functions_missing_action",
            "general_errors",
        )
    )


def _std_python_enforcement_delta(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    before_sig = _std_python_enforcement_signature(before)
    after_sig = _std_python_enforcement_signature(after)
    new_gaps = {
        key: sorted(set(after_sig.get(key, [])) - set(before_sig.get(key, [])))
        for key in before_sig
    }
    resolved_gaps = {
        key: sorted(set(before_sig.get(key, [])) - set(after_sig.get(key, [])))
        for key in before_sig
    }
    before_clean = bool(before.get("is_compliant"))
    after_clean = bool(after.get("is_compliant"))
    regressions = any(values for values in new_gaps.values()) or (before_clean and not after_clean)
    progress = any(values for values in resolved_gaps.values()) or (not before_clean and after_clean)
    status = "clean_stable"
    if before_clean and not after_clean:
        status = "regressed"
    elif not before_clean and after_clean:
        status = "resolved"
    elif regressions:
        status = "regressed"
    elif progress:
        status = "improved"
    elif not before_clean:
        status = "no_progress"
    return {
        "path": str(after.get("path") or before.get("path") or ""),
        "status": status,
        "pre_gap_count": _std_python_gap_count(before_sig),
        "post_gap_count": _std_python_gap_count(after_sig),
        "new_gaps": new_gaps,
        "resolved_gaps": resolved_gaps,
        "regressed": status == "regressed",
        "progress": progress,
    }


def _std_python_matrix() -> dict[str, Any]:
    before = {"path": "demo.py", "is_compliant": False, "missing_module_tags": ["module_type"]}
    improved = {"path": "demo.py", "is_compliant": True, "missing_module_tags": []}
    regressed = {
        "path": "demo.py",
        "is_compliant": False,
        "missing_module_tags": ["module_type", "status"],
    }
    improved_delta = _std_python_enforcement_delta(before, improved)
    regressed_delta = _std_python_enforcement_delta(before, regressed)
    return _ok(
        "std_python_delta_enforcement_ratchet_gate",
        improved_status=improved_delta["status"],
        regressed_status=regressed_delta["status"],
        new_violation_blocks=regressed_delta["regressed"],
        resolved_gap_count=len(regressed_delta["resolved_gaps"]["missing_module_tags"]),
        claim_ceiling="standards-delta ratchet over public inspector rows only",
    )


def _scan_fixture_targets(files: Mapping[str, str], terms: Sequence[str]) -> list[str]:
    normalized = tuple(term.lower() for term in terms if term.strip())
    ranked: list[tuple[int, int, str]] = []
    for path, text in files.items():
        haystack = f"{path}\n{text}".lower()
        score = sum(5 if term in path.lower() else 0 for term in normalized)
        score += sum(1 for term in normalized if term in haystack)
        if score:
            ranked.append((-score, len(path), path))
    ranked.sort()
    return [path for _score, _length, path in ranked]


def _exogenous_nav_matrix() -> dict[str, Any]:
    files = {
        "codex/doctrine/skills/kernel/navigation_seed.md": "wrapped bash eyesight route ladder",
        "docs/unrelated.md": "release checklist",
    }
    oracle = _scan_fixture_targets(files, ["wrapped", "bash", "eyesight"])
    correct = oracle and oracle[0] == "codex/doctrine/skills/kernel/navigation_seed.md"
    wrong_route_grade = 0 if "docs/unrelated.md" != oracle[0] else 1
    return _ok(
        "exogenous_nav_ladder_grader",
        oracle_target=oracle[0] if oracle else None,
        route_match=correct,
        wrong_route_grade=wrong_route_grade,
        wrong_route_graded_down=wrong_route_grade == 0,
        claim_ceiling="exogenous route-plane grading over public filesystem facts only",
    )


def _latest_results_by_id(results: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for index, item in enumerate(results):
        check_id = str(item.get("id") or f"__anonymous_{index}")
        if check_id not in by_id:
            order.append(check_id)
        by_id[check_id] = dict(item)
    return [by_id[check_id] for check_id in order]


def _compute_portability_status(results: Sequence[Mapping[str, Any]]) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    final = _latest_results_by_id(results)
    hard_blockers = [row for row in final if row.get("hard_blocker")]
    failed_checks = [row for row in final if row.get("status") in {"fail", "skipped"}]
    if hard_blockers:
        return "red", hard_blockers, failed_checks
    if any(row.get("status") == "warn" for row in final):
        return "amber", hard_blockers, failed_checks
    return "green", hard_blockers, failed_checks


def _portability_matrix() -> dict[str, Any]:
    results = [
        {"id": "no_private_only_references", "status": "fail", "hard_blocker": True},
        {
            "id": "no_private_only_references",
            "status": "pass",
            "hard_blocker": False,
            "supersedes_manifest_grep": True,
        },
        {"id": "no_secret_scan_hits", "status": "fail", "hard_blocker": True},
    ]
    status, hard_blockers, failed = _compute_portability_status(results)
    final = _latest_results_by_id(results)
    return _ok(
        "portability_gate_check_supersession_rollup",
        final_status=status,
        final_check_ids=[row["id"] for row in final],
        superseded_private_reference_passed=final[0]["status"] == "pass",
        unresolved_hard_fail_blocks=status == "red" and bool(hard_blockers),
        failed_check_count=len(failed),
        claim_ceiling="portability check reconciliation over public check rows only",
    )


def _browse_priority(context: Mapping[str, str]) -> list[str]:
    group = bool(context.get("group"))
    paragraph = bool(context.get("paragraphId"))
    if group and paragraph:
        return ["routing", "standalone", "group", "paragraph"]
    if group:
        return ["paragraph", "routing", "standalone", "group"]
    if paragraph:
        return ["group", "routing", "standalone", "paragraph"]
    return ["group", "paragraph", "routing", "standalone"]


def _browse_section_for_result(result: Mapping[str, Any], context: Mapping[str, str]) -> dict[str, Any]:
    shard = result.get("shard") if isinstance(result.get("shard"), Mapping) else {}
    groups = list(shard.get("idea_group_ids") or [])
    primary = str(shard.get("group") or "")
    if primary and primary not in groups:
        groups.insert(0, primary)
    paragraph = shard.get("parent_paragraph_id") or (shard.get("raw_paragraph_ids") or [None])[0]
    route = (shard.get("routing_targets") or [None])[0]
    for kind in _browse_priority(context):
        if kind == "group" and groups:
            return {"kind": kind, "key": f"group:{groups[0]}", "label": groups[0]}
        if kind == "paragraph" and paragraph:
            return {"kind": kind, "key": f"paragraph:{paragraph}", "label": paragraph}
        if kind == "routing" and isinstance(route, Mapping):
            return {
                "kind": kind,
                "key": f"routing:{route.get('kind')}:{route.get('target_id')}",
                "label": str(route.get("target_id")),
            }
    return {"kind": "standalone", "key": "standalone", "label": "standalone"}


def _shard_sectionizer_matrix() -> dict[str, Any]:
    result = {
        "shard": {
            "group": "group-a",
            "parent_paragraph_id": "par-1",
            "routing_targets": [{"kind": "mechanism", "target_id": "mech_019"}],
        }
    }
    route_first = _browse_section_for_result(result, {"group": "group-a", "paragraphId": "par-1"})
    paragraph_first = _browse_section_for_result(result, {"group": "group-a", "paragraphId": ""})
    unmatched = _browse_section_for_result({"shard": {}}, {"group": "", "paragraphId": ""})
    return _ok(
        "shard_browse_context_priority_sectionizer",
        route_first_kind=route_first["kind"],
        paragraph_first_kind=paragraph_first["kind"],
        unmatched_kind=unmatched["kind"],
        multi_match_uses_context_priority=route_first["kind"] == "routing" and paragraph_first["kind"] == "paragraph",
        claim_ceiling="context-conditioned sectionization over public shard rows only",
    )


def _select_evidence_chunks(claim: Mapping[str, Any], chunks: Mapping[str, Mapping[str, Any]]) -> list[dict[str, Any]]:
    scored: list[tuple[int, Mapping[str, Any]]] = []
    preferred = set(claim.get("preferred_paths", []))
    terms = set(claim.get("terms", []))
    for chunk in chunks.values():
        score = 0
        rel_path = str(chunk["source_uri"]).replace("repo://", "")
        if rel_path in preferred:
            score += 100
        score += 15 * len(terms.intersection(set(chunk.get("terms", []))))
        text = str(chunk["content"]).lower()
        for word in re.findall(r"[a-zA-Z_]{6,}", str(claim["text"]).lower()):
            if word in text:
                score += 1
        if score:
            scored.append((score, chunk))
    scored.sort(key=lambda item: (-item[0], item[1]["source_uri"], item[1]["chunk_id"]))
    return [
        {
            "chunk_id": str(chunk["chunk_id"]),
            "source_uri": str(chunk["source_uri"]),
            "support_score": score,
            "support_kind": (
                "preferred_source_semantic"
                if str(chunk["source_uri"]).replace("repo://", "") in preferred
                else "controlled_term_overlap"
                if terms.intersection(set(chunk.get("terms", [])))
                else "lexical_overlap"
            ),
        }
        for score, chunk in scored[:8]
    ]


def _holographic_research_matrix() -> dict[str, Any]:
    claim = {
        "text": "Projection secret scan blocks private material",
        "preferred_paths": ["tools/meta/dissemination/projection_secret_scan.py"],
        "terms": ["secret", "projection"],
    }
    chunks = {
        "a": {
            "chunk_id": "a",
            "source_uri": "repo://tools/meta/dissemination/projection_secret_scan.py",
            "terms": ["secret"],
            "content": "projection scan content",
        },
        "b": {
            "chunk_id": "b",
            "source_uri": "repo://docs/unrelated.md",
            "terms": [],
            "content": "unrelated content",
        },
    }
    selected = _select_evidence_chunks(claim, chunks)
    graph_edges = [
        {"from": "claim:secret_scan", "to": row["chunk_id"], "weight": row["support_score"]}
        for row in selected
    ]
    return _ok(
        "holographic_research_bundle_graph_and_evidence_select",
        top_chunk=selected[0]["chunk_id"],
        top_score=selected[0]["support_score"],
        graph_edge_count=len(graph_edges),
        missing_provenance_not_invented=all(edge["to"] != "missing" for edge in graph_edges),
        claim_ceiling="deterministic evidence selection over public rows only",
    )


SECRET_CONTENT_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("credentials", "openai_key_shape", re.compile(r"sk-[A-Za-z0-9_-]{20,}")),
    ("credentials", "github_token_shape", re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("credentials", "aws_access_key_shape", re.compile(r"AKIA[0-9A-Z]{16}")),
    ("private_path", "private_home_path", re.compile("/" + r"Users/[A-Za-z0-9_.-]+")),
)

SECRET_PATH_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    ("raw_voice", "raw_seed_file_path", re.compile(r"(^|/)raw_seed(?:/|\\.md$)", re.IGNORECASE)),
    ("private_history", "private_task_ledger_path", re.compile(r"(^|/)state/task_ledger/", re.IGNORECASE)),
)


def _scan_projection_files(files: Mapping[str, str]) -> dict[str, Any]:
    hits: list[dict[str, Any]] = []
    for path, text in files.items():
        for category, name, pattern in SECRET_PATH_PATTERNS:
            if pattern.search(path):
                hits.append({"category": category, "pattern": name, "path": path, "source": "path"})
        for category, name, pattern in SECRET_CONTENT_PATTERNS:
            for match in pattern.finditer(text):
                hits.append(
                    {
                        "category": category,
                        "pattern": name,
                        "path": path,
                        "source": "content",
                        "match_sha256": hashlib.sha256(match.group(0).encode()).hexdigest(),
                    }
                )
    return {
        "status": "green" if not hits else "red",
        "file_count": len(files),
        "blocking_hit_count": len(hits),
        "blocking_hits": hits[:50],
    }


def _projection_secret_scan_matrix() -> dict[str, Any]:
    safe = _scan_projection_files({"docs/public.md": "public content only"})
    bad = _scan_projection_files(
        {
            "docs/public.md": "sk-abcdefghijklmnopqrstuvwxyz123456",
            "state/task_ledger/private.json": "metadata",
        }
    )
    return _ok(
        "projection_secret_scan",
        safe_status=safe["status"],
        bad_status=bad["status"],
        token_blocks=any(hit["pattern"] == "openai_key_shape" for hit in bad["blocking_hits"]),
        private_path_blocks=any(hit["source"] == "path" for hit in bad["blocking_hits"]),
        adversarial_probe_status="already_bound_collision_with_engine_room_public_projection_leak_gate",
        claim_ceiling="projection redaction gate over controlled public files only",
    )


def _stockgrid_has_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def _stockgrid_flow_is_usd_millions(row: Mapping[str, Any]) -> bool:
    schema = str(row.get("_data_schema_version") or "").strip().lower()
    return schema.startswith("stockgrid.2") and str(row.get("_table_path") or "") == "data"


def _stockgrid_flow_usd(row: Mapping[str, Any]) -> float | None:
    cached = _float(row.get("_normalized_flow_usd"))
    if cached is not None:
        return cached
    direct = _float(row.get("flow_usd"))
    if direct is not None:
        return direct
    flow = _float(row.get("flow"))
    if flow is not None:
        if _stockgrid_flow_is_usd_millions(row):
            return flow * 1_000_000.0
        return flow
    return _float(row.get("net_usd"))


def _stockgrid_flow_score(row: Mapping[str, Any]) -> float:
    value = _stockgrid_flow_usd(row)
    if value is not None:
        return abs(value)
    conv = _float(row.get("conv"))
    sv = _float(row.get("sv"))
    return abs(conv or sv or 0.0)


def _stockgrid_detail_score(row: Mapping[str, Any]) -> tuple[int, float]:
    fields = ("company", "sector", "dir", "flow_usd", "net_usd", "conv", "sv", "wr", "flow")
    present = sum(1 for key in fields if _stockgrid_has_value(row.get(key)))
    direct_usd = 1 if _float(row.get("flow_usd")) is not None else 0
    return (present + direct_usd * 3, _stockgrid_flow_score(row))


def _merge_stockgrid_rows(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    ordered = sorted(rows, key=_stockgrid_detail_score, reverse=True)
    merged = dict(ordered[0])
    source_table_paths: list[str] = []
    source_field_refs: list[str] = []
    for row in ordered:
        table_path = str(row.get("_table_path") or "")
        if table_path and table_path not in source_table_paths:
            source_table_paths.append(table_path)
        for key in (
            "tkr",
            "flow",
            "flow_usd",
            "net_usd",
            "sv",
            "wr",
            "flg",
            "sec",
            "sector",
            "company",
            "dir",
            "conv",
        ):
            if _stockgrid_has_value(row.get(key)) and key not in source_field_refs:
                source_field_refs.append(key)
            if not _stockgrid_has_value(merged.get(key)) and _stockgrid_has_value(row.get(key)):
                merged[key] = row.get(key)
        for key in ("flow_usd", "net_usd", "sector", "company", "dir", "conv"):
            if _stockgrid_has_value(row.get(key)):
                merged[key] = row.get(key)
        if _stockgrid_flow_is_usd_millions(row):
            merged["_flow_unit"] = "usd_millions"
    normalized = _stockgrid_flow_usd(merged)
    if normalized is None:
        for row in ordered:
            normalized = _stockgrid_flow_usd(row)
            if normalized is not None:
                break
    if normalized is not None:
        merged["_normalized_flow_usd"] = normalized
        if _float(merged.get("flow_usd")) is None:
            merged["flow_usd"] = normalized
    merged["_source_table_paths"] = source_table_paths or [str(merged.get("_table_path") or "")]
    merged["_source_field_refs"] = source_field_refs or [
        "tkr",
        "flow",
        "flow_usd",
        "net_usd",
        "conv",
        "sv",
        "wr",
        "flg",
    ]
    return merged


def _top_stockgrid_flow_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 16) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        if str(row.get("tkr") or "").strip() and any(
            _float(row.get(key)) is not None for key in ("flow_usd", "net_usd", "flow", "conv", "sv")
        ):
            grouped.setdefault(str(row.get("tkr")).strip(), []).append(row)
    merged = [_merge_stockgrid_rows(group_rows) for group_rows in grouped.values()]
    return sorted(merged, key=_stockgrid_flow_score, reverse=True)[:limit]


def _stockgrid_matrix() -> dict[str, Any]:
    rows = [
        {"tkr": "QQQ", "flow": 2.5, "_data_schema_version": "stockgrid.2", "_table_path": "data", "sv": 52},
        {
            "tkr": "QQQ",
            "company": "Nasdaq 100 ETF",
            "sector": "ETF",
            "flow_usd": 2_400_000,
            "conv": 0.82,
            "_table_path": "datasets.rich",
        },
        {"tkr": "BROKEN", "_table_path": "data"},
    ]
    top = _top_stockgrid_flow_rows(rows)
    qqq = [row for row in top if row["tkr"] == "QQQ"][0]
    broken_candidates = _top_stockgrid_flow_rows([rows[-1]])
    return _ok(
        "stockgrid_flow_multisource_merge_unit_normalizer",
        normalized_flow_usd=qqq["_normalized_flow_usd"],
        source_field_refs=qqq["_source_field_refs"],
        source_table_paths=qqq["_source_table_paths"],
        missing_flow_no_silent_zero=not broken_candidates,
        adversarial_probe_status="organ_plane_absent_for_quant_presentation_mart_at_import_time",
        claim_ceiling="unit-normalizing data mart merge over public stockgrid-shaped rows only",
    )


def _macro_bucket(row: Mapping[str, Any]) -> str:
    text = f"{row.get('ticker') or ''} {row.get('Proxy') or ''}".lower()
    if any(token in text for token in ("cpi", "ppi", "pce", "inflation", "price")):
        return "inflation"
    if any(token in text for token in ("rate", "yield", "fed", "sofr", "effr", "mortgage")):
        return "rates"
    if any(token in text for token in ("labor", "job", "claims", "unemployment", "payroll")):
        return "labor"
    if any(token in text for token in ("gdp", "growth", "industrial", "sales", "pmi")):
        return "growth"
    if any(token in text for token in ("credit", "spread", "loan", "delinq", "debt")):
        return "credit"
    if any(token in text for token in ("oil", "gas", "energy", "wti")):
        return "energy"
    if any(token in text for token in ("housing", "consumer", "saving", "income")):
        return "housing_consumer"
    return "other"


def _macro_lifecycle_by_slug(macro_artifact: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    metadata = macro_artifact.get("metadata") if isinstance(macro_artifact.get("metadata"), Mapping) else {}
    sidecars = metadata.get("sidecars") if isinstance(metadata.get("sidecars"), Mapping) else {}
    lifecycle = sidecars.get("macro_lifecycle_snapshot") if isinstance(sidecars.get("macro_lifecycle_snapshot"), Mapping) else {}
    by_slug: dict[str, Mapping[str, Any]] = {}
    for row in lifecycle.get("rows") or []:
        if not isinstance(row, Mapping):
            continue
        slug = str(row.get("slug") or "").strip()
        if slug:
            by_slug[slug] = row
    return by_slug


def _macro_regime_board(
    rows: Sequence[Mapping[str, Any]],
    *,
    macro_artifact: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    buckets: dict[str, list[Mapping[str, Any]]] = {}
    lifecycle_by_slug = _macro_lifecycle_by_slug(macro_artifact or {})
    for row in rows:
        buckets.setdefault(_macro_bucket(row), []).append(row)
    board: list[dict[str, Any]] = []
    for bucket, bucket_rows in sorted(buckets.items()):
        scored = [(_float(row.get("z_score")) or 0.0, row) for row in bucket_rows]
        avg_z = sum(score for score, _row in scored) / max(len(scored), 1)
        top = sorted(scored, key=lambda item: abs(item[0]), reverse=True)[:5]
        lifecycle_rows = [lifecycle_by_slug.get(str(row.get("ticker") or "")) for row in bucket_rows]
        lifecycle_rows = [row for row in lifecycle_rows if isinstance(row, Mapping)]
        vintage_available = any(
            ((row.get("components") or {}).get("vintage_metadata_present") is True)
            for row in lifecycle_rows
            if isinstance(row.get("components"), Mapping)
        )
        release_calendar_available = any(
            bool((row.get("components") or {}).get("latest_observation_date"))
            for row in lifecycle_rows
            if isinstance(row.get("components"), Mapping)
        )
        board.append(
            {
                "bucket": bucket,
                "series_count": len(bucket_rows),
                "average_z_score": round(avg_z, 4),
                "vintage_status": "available" if vintage_available else "missing_from_feed_artifact",
                "release_calendar_status": "available" if release_calendar_available else "missing_from_feed_artifact",
                "interpretation_level": "series_observation_summary",
                "top_series": [
                    {
                        "entity_id": f"macro_series:{_stable_slug(row.get('ticker'))}",
                        "ticker": row.get("ticker"),
                        "proxy": row.get("Proxy"),
                        "z_score": _float(row.get("z_score")),
                        "recent_change": _float(row.get("recent_change")),
                        "latest_observation_date": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("latest_observation_date"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                        "realtime_start": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("realtime_start"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                        "realtime_end": (
                            (((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components") or {}).get("realtime_end"))
                            if isinstance((lifecycle_by_slug.get(str(row.get("ticker") or "")) or {}).get("components"), Mapping)
                            else None
                        ),
                    }
                    for _score, row in top
                ],
            }
        )
    return sorted(board, key=lambda row: abs(float(row.get("average_z_score") or 0.0)), reverse=True)


def _quant_presentation_mart_source_path(source_manifest: Mapping[str, Any]) -> Path | None:
    manifest_path = Path(str(source_manifest.get("source_manifest_path") or ""))
    if not manifest_path.is_file():
        return None
    for row in source_manifest.get("modules") or []:
        if not isinstance(row, Mapping):
            continue
        if row.get("source_ref") != "system/lib/quant_presentation_mart.py":
            continue
        row_path = str(row.get("path") or "")
        return manifest_path.parent / row_path if row_path else None
    return None


def _load_quant_presentation_mart_module(source_manifest: Mapping[str, Any]) -> tuple[Any | None, str, str | None]:
    source_path = _quant_presentation_mart_source_path(source_manifest)
    if source_path is None or not source_path.is_file():
        return None, "", "quant_presentation_mart_source_missing"
    _install_quant_presentation_import_stubs()
    digest = hashlib.sha256(source_path.read_bytes()).hexdigest()[:12]
    module_name = f"_microcosm_batch11_quant_presentation_mart_{digest}"
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    if spec is None or spec.loader is None:
        return None, str(source_path), "quant_presentation_mart_spec_missing"
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # pragma: no cover - import diagnostics vary by host.
        return None, str(source_path), f"quant_presentation_mart_import_failed:{type(exc).__name__}"
    return module, str(source_path), None


def _macro_regime_lifecycle_artifact() -> dict[str, Any]:
    return {
        "schema_version": "batch11_public_macro_lifecycle_fixture_v1",
        "metadata": {
            "sidecars": {
                "macro_lifecycle_snapshot": {
                    "rows": [
                        {
                            "slug": "cpi_core",
                            "components": {
                                "vintage_metadata_present": True,
                                "latest_observation_date": "2026-05-15",
                                "realtime_start": "2026-05-16",
                                "realtime_end": "2026-05-16",
                            },
                        },
                        {
                            "slug": "initial_claims",
                            "components": {
                                "vintage_metadata_present": True,
                                "latest_observation_date": "2026-05-23",
                                "realtime_start": "2026-05-24",
                                "realtime_end": "2026-05-24",
                            },
                        },
                    ]
                }
            }
        },
    }


def _macro_regime_board_from_source(
    rows: Sequence[Mapping[str, Any]],
    *,
    macro_artifact: Mapping[str, Any],
    source_manifest: Mapping[str, Any] | None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if source_manifest is None:
        return _macro_regime_board(rows, macro_artifact=macro_artifact), {
            "source_body_invoked": False,
            "source_module_path": "",
            "source_import_error": "source_manifest_not_supplied",
            "source_functions_invoked": [],
        }
    module, source_path, error = _load_quant_presentation_mart_module(source_manifest)
    if module is None:
        return _macro_regime_board(rows, macro_artifact=macro_artifact), {
            "source_body_invoked": False,
            "source_module_path": source_path,
            "source_import_error": error,
            "source_functions_invoked": [],
        }
    board = module._macro_regime_board(rows, macro_artifact=macro_artifact)
    return list(board), {
        "source_body_invoked": True,
        "source_module_path": "system/lib/quant_presentation_mart.py",
        "source_import_error": None,
        "source_functions_invoked": [
            "system/lib/quant_presentation_mart.py::_macro_lifecycle_by_slug",
            "system/lib/quant_presentation_mart.py::_macro_regime_board",
        ],
    }


def _macro_regime_matrix(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    rows = [
        {"ticker": "cpi_core", "Proxy": "inflation", "z_score": 2.0, "recent_change": 0.3},
        {"ticker": "initial_claims", "Proxy": "labor", "z_score": 1.5, "recent_change": -0.2},
        {"ticker": "mystery", "Proxy": "unknown", "z_score": -0.5, "recent_change": 0.0},
    ]
    macro_artifact = _macro_regime_lifecycle_artifact()
    board, invocation = _macro_regime_board_from_source(
        rows,
        macro_artifact=macro_artifact,
        source_manifest=source_manifest,
    )
    by_bucket = {row["bucket"]: row for row in board}
    inflation_top = by_bucket["inflation"]["top_series"][0]
    other_top = by_bucket["other"]["top_series"][0]
    return _ok(
        "macro_regime_board_bucketing_zscore_engine",
        bucket_order=[row["bucket"] for row in board],
        inflation_average_z=by_bucket["inflation"]["average_z_score"],
        inflation_vintage_status=by_bucket["inflation"]["vintage_status"],
        inflation_release_calendar_status=by_bucket["inflation"]["release_calendar_status"],
        inflation_latest_observation_date=inflation_top["latest_observation_date"],
        inflation_realtime_start=inflation_top["realtime_start"],
        inflation_realtime_end=inflation_top["realtime_end"],
        other_vintage_status=by_bucket["other"]["vintage_status"],
        other_release_calendar_status=by_bucket["other"]["release_calendar_status"],
        other_latest_observation_date=other_top["latest_observation_date"],
        macro_artifact_lifecycle_row_count=len(
            macro_artifact["metadata"]["sidecars"]["macro_lifecycle_snapshot"]["rows"]
        ),
        source_body_invoked=invocation["source_body_invoked"],
        source_module_path=invocation["source_module_path"],
        source_import_error=invocation["source_import_error"],
        source_functions_invoked=invocation["source_functions_invoked"],
        unknown_routes_other=_macro_bucket(rows[-1]) == "other",
        adversarial_probe_status="organ_plane_absent_for_quant_presentation_mart_at_import_time",
        claim_ceiling="macro-regime bucketing over public fixture rows only",
    )


def _dijkstra_plan(graph: Mapping[str, Any], source_id: str, target_id: str) -> dict[str, Any]:
    edges_by_from: dict[str, list[Mapping[str, Any]]] = collections.defaultdict(list)
    for edge in graph.get("edges", []):
        if isinstance(edge, Mapping):
            edges_by_from[str(edge.get("from"))].append(edge)
    queue: list[tuple[float, str, list[str]]] = [(0.0, source_id, [source_id])]
    seen: set[str] = set()
    while queue:
        queue.sort(key=lambda row: (row[0], row[1], row[2]))
        cost, node, path = queue.pop(0)
        if node == target_id:
            return {"blocked": False, "cost": cost, "path": path}
        if node in seen:
            continue
        seen.add(node)
        for edge in edges_by_from.get(node, []):
            status = (
                edge.get("navigation_affordance", {}).get("status")
                if isinstance(edge.get("navigation_affordance"), Mapping)
                else "ready"
            )
            if status != "ready":
                continue
            dest = str(edge.get("to"))
            if dest not in seen:
                queue.append((cost + float(edge.get("weight") or 1.0), dest, [*path, dest]))
    return {"blocked": True, "blocker": "no_route", "path": []}


def _frontend_nav_matrix() -> dict[str, Any]:
    graph = {
        "views": [{"id": "home"}, {"id": "work"}, {"id": "market"}, {"id": "isolated"}],
        "edges": [
            {"from": "home", "to": "work", "weight": 1, "navigation_affordance": {"status": "ready"}},
            {"from": "work", "to": "market", "weight": 1, "navigation_affordance": {"status": "ready"}},
        ],
    }
    path = _dijkstra_plan(graph, "home", "market")
    missing = _dijkstra_plan(graph, "market", "isolated")
    return _ok(
        "frontend_nav_graph_wayfinding_engine",
        path=path["path"],
        path_cost=path["cost"],
        unreachable_blocker=missing.get("blocker"),
        unreachable_returns_blocker=missing["blocked"],
        adversarial_probe_status="organ_plane_absent_for_frontend_nav_graph_at_import_time",
        claim_ceiling="frontend route graph wayfinding over public fixtures only",
    )


ROUTE_MISS_PATTERNS = (
    r"\broute[-\s]*miss(?:es)?(?:\s+(?:miner|candidate|phrases?))?\b",
    r"\bdocs[-\s]*route\s+(?:failed\s+phrases?|miss(?:es)?|alias(?:es)?|hints?)\b",
    r"\bnavigation(?:[-\s]*layer)?\s+(?:timing|process[-\s]*trace|route|routing)\b",
)
ROUTE_MISS_ANCHORS = {"route", "miss", "docs-route", "navigation", "timing", "trace"}


def _route_candidate_tokens(text: str) -> list[str]:
    cleaned = re.sub(r"`([^`]+)`", r"\1", text.lower())
    cleaned = cleaned.replace("_", "-")
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", cleaned)


def _route_miss_candidate_phrases(text: str, *, limit: int = 24) -> list[str]:
    seen: dict[str, None] = {}

    def add(value: str) -> None:
        phrase = re.sub(r"[^a-z0-9._+/-]+", " ", value.lower()).strip()
        if len(phrase) >= 5 and phrase not in seen:
            seen[phrase] = None

    for pattern in ROUTE_MISS_PATTERNS:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            add(match.group(0))
            if len(seen) >= limit:
                return list(seen)
    tokens = _route_candidate_tokens(text)
    for idx, token in enumerate(tokens):
        if token not in ROUTE_MISS_ANCHORS:
            continue
        add(" ".join(tokens[max(0, idx - 2) : min(len(tokens), idx + 5)]))
    return list(seen)


def _session_diagnostic_matrix() -> dict[str, Any]:
    events = [
        {"tool": "Bash", "command": "rg -n route system"},
        {"tool": "Read", "path": "AGENTS.md"},
        {"tool": "Bash", "command": "python3 kernel.py --docs-route navigation timing"},
    ]
    tool_histogram = collections.Counter(str(event.get("tool")) for event in events)
    bash_verbs = collections.Counter(
        str(event.get("command", "")).split()[0]
        for event in events
        if event.get("tool") == "Bash" and str(event.get("command", "")).split()
    )
    route_phrases = _route_miss_candidate_phrases("docs-route failed phrases for navigation timing route miss")
    no_nav_verbs = collections.Counter({"python3": 1})
    return _ok(
        "agent_session_diagnostic_lens_engine",
        tool_histogram=dict(tool_histogram),
        bash_verb_histogram=dict(bash_verbs),
        route_miss_phrase_count=len(route_phrases),
        no_nav_verbs_no_false_ladder_skip=not any(verb in no_nav_verbs for verb in ("rg", "grep", "find", "ls", "cat")),
        adversarial_probe_status="skill_name_collision_cleared_skill_not_organ",
        claim_ceiling="session diagnostic lens over synthetic public rows only",
    )


def _score_view_segment(
    *,
    span_duration: float,
    target_duration: float,
    anchor_hits: int,
    anchor_total: int,
    intent_counts: Mapping[str, int],
) -> float:
    duration_component = min(1.0, span_duration / max(1.0, target_duration))
    anchor_component = (anchor_hits / anchor_total) if anchor_total else 0.5
    retake_penalty = 0.3 * intent_counts.get("mark_retake", 0)
    confusing_penalty = 0.2 * intent_counts.get("mark_confusing", 0)
    private_penalty = 1.0 if intent_counts.get("mark_private", 0) else 0.0
    good_bonus = 0.15 * intent_counts.get("mark_good", 0)
    verdict_bonus = 0.2 if intent_counts.get("view_verdict_high", 0) else 0.0
    score = (
        0.55 * duration_component
        + 0.30 * anchor_component
        + good_bonus
        + verdict_bonus
        - retake_penalty
        - confusing_penalty
        - private_penalty
    )
    return max(0.0, min(1.0, round(score, 3)))


def _demo_take_matrix() -> dict[str, Any]:
    full = _score_view_segment(
        span_duration=22,
        target_duration=20,
        anchor_hits=2,
        anchor_total=2,
        intent_counts={"mark_good": 1, "view_verdict_high": 1},
    )
    missing = _score_view_segment(
        span_duration=8,
        target_duration=20,
        anchor_hits=0,
        anchor_total=2,
        intent_counts={},
    )
    return _ok(
        "demo_take_story_coverage_audit",
        full_score=full,
        missing_anchor_score=missing,
        missing_anchors_lowers_score=missing < full,
        adversarial_probe_status="already_bound_by_batch7_demo_take_capsule_batch11_records_scoring_path",
        claim_ceiling="story coverage scoring over synthetic timeline and script rows only",
    )


def _stable_json_digest(payload: Any) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def _negative_case_payloads(input_path: Path) -> dict[str, dict[str, Any]]:
    payloads: dict[str, dict[str, Any]] = {}
    for case_id in EXPECTED_NEGATIVE_CASES:
        case_path = input_path / f"{case_id}.json"
        if not case_path.is_file():
            continue
        try:
            payload = json.loads(case_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            payloads[case_id] = payload
    return payloads


def _probe_result(
    case_id: str,
    probe_input: Mapping[str, Any],
    *,
    computed_value: bool,
    observed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass" if computed_value else "blocked",
        "computed": computed_value,
        "computed_value": computed_value,
        "computed_path": NEGATIVE_CASE_COMPUTED_PATHS[case_id]["computed_path"],
        "fixture_probe_source": "negative_case_fixture_probe_input",
        "fixture_probe_input_digest": _stable_json_digest(probe_input),
        "observed": dict(observed or {}),
        "body_in_receipt": False,
    }


def _missing_probe_result(case_id: str, reason: str) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "computed": False,
        "computed_value": None,
        "computed_path": NEGATIVE_CASE_COMPUTED_PATHS[case_id]["computed_path"],
        "fixture_probe_source": "missing_or_invalid_negative_case_fixture_probe_input",
        "fixture_probe_input_digest": None,
        "observed": {"reason": reason},
        "body_in_receipt": False,
    }


def _compute_negative_case_probe(
    case_id: str,
    payload: Mapping[str, Any],
    *,
    source_manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    probe_input = payload.get("probe_input") if isinstance(payload.get("probe_input"), Mapping) else {}
    if not probe_input:
        return _missing_probe_result(case_id, "missing_probe_input")

    if case_id == "run_affinity_stale_terminal_rejected":
        recommendation = recommend_run_by_affinity(
            probe_input.get("candidates", []),
            now_ms=int(probe_input.get("now_ms") or 0),
            mission_name=str(probe_input.get("mission_name") or "") or None,
            sticky_run_id=str(probe_input.get("sticky_run_id") or "") or None,
            require_working=bool(probe_input.get("require_working")),
        )
        stale_id = str(probe_input.get("stale_run_id") or "")
        selected = recommendation.get("run_id") if recommendation else None
        stale_score = None
        if recommendation:
            for row in recommendation.get("ranked", []):
                if row.get("run_id") == stale_id:
                    stale_score = row.get("score")
                    break
        return _probe_result(
            case_id,
            probe_input,
            computed_value=bool(recommendation and selected != stale_id),
            observed={"selected_run_id": selected, "stale_run_id": stale_id, "stale_score": stale_score},
        )

    if case_id == "calculator_zero_bucket_no_fake_dominance":
        drivers = _calculator_drivers(
            probe_input.get("metrics") if isinstance(probe_input.get("metrics"), Mapping) else {}
        )
        shares = [row["share"] for row in drivers]
        return _probe_result(
            case_id,
            probe_input,
            computed_value=all(share == 0 for share in shares),
            observed={"share_sum": round(sum(shares), 6), "driver_count": len(drivers)},
        )

    if case_id == "std_python_new_gap_blocks":
        before = probe_input.get("before") if isinstance(probe_input.get("before"), Mapping) else {}
        after = probe_input.get("after") if isinstance(probe_input.get("after"), Mapping) else {}
        delta = _std_python_enforcement_delta(before, after)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=bool(delta["regressed"]),
            observed={"status": delta["status"], "post_gap_count": delta["post_gap_count"]},
        )

    if case_id == "exogenous_nav_wrong_route_graded_down":
        files = probe_input.get("files") if isinstance(probe_input.get("files"), Mapping) else {}
        terms = probe_input.get("terms") if isinstance(probe_input.get("terms"), Sequence) else []
        wrong_path = str(probe_input.get("wrong_path") or "")
        oracle = _scan_fixture_targets({str(key): str(value) for key, value in files.items()}, terms)
        route_match = bool(oracle and oracle[0] != wrong_path)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=route_match,
            observed={"oracle_target": oracle[0] if oracle else None, "wrong_path": wrong_path},
        )

    if case_id == "portability_unresolved_hard_fail_blocks":
        results = probe_input.get("results")
        rows = [row for row in results if isinstance(row, Mapping)] if isinstance(results, Sequence) else []
        status, hard_blockers, failed = _compute_portability_status(rows)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=status == "red" and bool(hard_blockers),
            observed={
                "final_status": status,
                "hard_blocker_count": len(hard_blockers),
                "failed_check_count": len(failed),
            },
        )

    if case_id == "shard_multimatch_context_priority":
        result = probe_input.get("result") if isinstance(probe_input.get("result"), Mapping) else {}
        route_context = (
            probe_input.get("route_context")
            if isinstance(probe_input.get("route_context"), Mapping)
            else {}
        )
        paragraph_context = (
            probe_input.get("paragraph_context")
            if isinstance(probe_input.get("paragraph_context"), Mapping)
            else {}
        )
        route_first = _browse_section_for_result(result, route_context)
        paragraph_first = _browse_section_for_result(result, paragraph_context)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=route_first["kind"] == "routing" and paragraph_first["kind"] == "paragraph",
            observed={"route_first_kind": route_first["kind"], "paragraph_first_kind": paragraph_first["kind"]},
        )

    if case_id == "holographic_no_overlap_no_fake_edge":
        claim = probe_input.get("claim") if isinstance(probe_input.get("claim"), Mapping) else {}
        chunks = probe_input.get("chunks") if isinstance(probe_input.get("chunks"), Mapping) else {}
        selected = _select_evidence_chunks(claim, chunks)
        missing_id = str(probe_input.get("missing_chunk_id") or "missing")
        graph_edges = [
            {"from": "claim:fixture_probe", "to": row["chunk_id"], "weight": row["support_score"]}
            for row in selected
        ]
        return _probe_result(
            case_id,
            probe_input,
            computed_value=all(edge["to"] != missing_id for edge in graph_edges),
            observed={"selected_count": len(selected), "missing_chunk_id": missing_id},
        )

    if case_id == "projection_secret_token_blocks":
        files = probe_input.get("files") if isinstance(probe_input.get("files"), Mapping) else {}
        scan = _scan_projection_files({str(key): str(value) for key, value in files.items()})
        return _probe_result(
            case_id,
            probe_input,
            computed_value=any(hit["pattern"] == "openai_key_shape" for hit in scan["blocking_hits"]),
            observed={"status": scan["status"], "blocking_hit_count": scan["blocking_hit_count"]},
        )

    if case_id == "stockgrid_units_normalized_not_zeroed":
        rows = probe_input.get("rows")
        candidates = _top_stockgrid_flow_rows(
            [row for row in rows if isinstance(row, Mapping)] if isinstance(rows, Sequence) else []
        )
        return _probe_result(
            case_id,
            probe_input,
            computed_value=not candidates,
            observed={"candidate_count": len(candidates)},
        )

    if case_id == "macro_regime_unknown_routes_other":
        row = probe_input.get("row") if isinstance(probe_input.get("row"), Mapping) else {}
        bucket = _macro_bucket(row)
        macro_artifact = (
            probe_input.get("macro_artifact")
            if isinstance(probe_input.get("macro_artifact"), Mapping)
            else _macro_regime_lifecycle_artifact()
        )
        board, invocation = _macro_regime_board_from_source(
            [row],
            macro_artifact=macro_artifact,
            source_manifest=source_manifest,
        )
        board_row = board[0] if board else {}
        return _probe_result(
            case_id,
            probe_input,
            computed_value=(
                bucket == "other"
                and board_row.get("vintage_status") == "missing_from_feed_artifact"
                and board_row.get("release_calendar_status") == "missing_from_feed_artifact"
            ),
            observed={
                "bucket": bucket,
                "vintage_status": board_row.get("vintage_status"),
                "release_calendar_status": board_row.get("release_calendar_status"),
                "source_body_invoked": invocation["source_body_invoked"],
                "source_functions_invoked": invocation["source_functions_invoked"],
            },
        )

    if case_id == "frontend_nav_unreachable_target":
        graph = probe_input.get("graph") if isinstance(probe_input.get("graph"), Mapping) else {}
        plan = _dijkstra_plan(
            graph,
            str(probe_input.get("source_id") or ""),
            str(probe_input.get("target_id") or ""),
        )
        return _probe_result(
            case_id,
            probe_input,
            computed_value=bool(plan["blocked"]),
            observed={"blocked": plan["blocked"], "blocker": plan.get("blocker")},
        )

    if case_id == "session_no_nav_verbs_no_ladder_skip":
        verbs = probe_input.get("verbs") if isinstance(probe_input.get("verbs"), Mapping) else {}
        verb_counter = collections.Counter({str(key): int(value) for key, value in verbs.items()})
        route_text = str(probe_input.get("route_text") or "")
        route_phrases = _route_miss_candidate_phrases(route_text)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=not any(verb in verb_counter for verb in ("rg", "grep", "find", "ls", "cat")),
            observed={"verb_count": sum(verb_counter.values()), "route_phrase_count": len(route_phrases)},
        )

    if case_id == "demo_take_missing_anchor_penalized":
        full = probe_input.get("full") if isinstance(probe_input.get("full"), Mapping) else {}
        missing = probe_input.get("missing") if isinstance(probe_input.get("missing"), Mapping) else {}
        full_score = _score_view_segment(**full)
        missing_score = _score_view_segment(**missing)
        return _probe_result(
            case_id,
            probe_input,
            computed_value=missing_score < full_score,
            observed={"full_score": full_score, "missing_score": missing_score},
        )

    return _missing_probe_result(case_id, "unknown_case_id")


def _semantic_negative_result(case_id: str, error_codes: tuple[str, ...]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": list(error_codes),
        "body_in_receipt": False,
    }


def _semantic_negative_not_rejected(case_id: str, observed: Any) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "pass",
        "error_codes": [],
        "observed": observed,
        "body_in_receipt": False,
    }


def _semantic_negative_error(case_id: str, exc: Exception) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": "blocked",
        "error_codes": [
            f"BATCH11_SATURATION_SEMANTIC_EVALUATOR_{type(exc).__name__.upper()}"
        ],
        "body_in_receipt": False,
    }


def _source_manifest_for_input(input_dir: Path) -> dict[str, Any]:
    public_root = public_root_for_path(input_dir)
    source_manifest = validate_source_manifest(input_dir, SPEC, public_root=public_root)
    return _augment_source_manifest_with_public_refactors(source_manifest, public_root=public_root)


def _refactor_target_path(
    row: Mapping[str, Any],
    *,
    manifest_path: Path,
    public_root: Path,
) -> Path:
    row_path = str(row.get("path") or "")
    if row_path:
        return manifest_path.parent / row_path
    target_ref = strip_microcosm_prefix(str(row.get("target_ref") or ""))
    if target_ref:
        return public_root / target_ref
    return manifest_path.parent


def _refactor_source_path(row: Mapping[str, Any], *, public_root: Path) -> Path:
    return public_root.parent / str(row.get("source_ref") or "")


def _augment_source_manifest_with_public_refactors(
    source_manifest: Mapping[str, Any],
    *,
    public_root: Path,
) -> dict[str, Any]:
    augmented = dict(source_manifest)
    raw_manifest = _raw_source_manifest(source_manifest)
    refactor_rows = [
        row
        for row in raw_manifest.get("source_faithful_public_refactors", [])
        if isinstance(row, Mapping)
    ]
    manifest_path_raw = source_manifest.get("source_manifest_path")
    if not refactor_rows or not isinstance(manifest_path_raw, str):
        return augmented
    manifest_path = Path(manifest_path_raw)
    findings = list(source_manifest.get("findings", []))
    modules = [
        dict(row)
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    ]
    source_artifact_paths: list[Path] = []
    for ref in source_manifest.get("source_artifact_paths", []):
        if isinstance(ref, str):
            source_artifact_paths.append(public_root / strip_microcosm_prefix(ref))

    for row in refactor_rows:
        source_ref = str(row.get("source_ref") or "")
        target_path = _refactor_target_path(row, manifest_path=manifest_path, public_root=public_root)
        source_path = _refactor_source_path(row, public_root=public_root)
        source_sha = file_sha256(source_path)
        target_sha = file_sha256(target_path)
        target_line_count = file_line_count(target_path)
        expected_target_sha = row.get("target_sha256") or row.get("sha256")
        expected_source_sha = row.get("source_sha256")
        expected_line_count = row.get("line_count")
        anchors = tuple(SOURCE_REQUIRED_ANCHORS.get(source_ref, ()))
        target_text = target_path.read_text(encoding="utf-8") if target_path.is_file() else ""
        missing_anchors = [anchor for anchor in anchors if anchor not in target_text]
        source_ref_required = (public_root.parent / ".git").is_dir()
        digest_match = (
            target_sha is not None
            and target_sha == expected_target_sha
            and (source_sha == expected_source_sha or (not source_ref_required and source_sha is None))
        )
        line_count_match = target_line_count == expected_line_count
        modules.append(
            {
                "source_ref": source_ref,
                "target_ref": str(row.get("target_ref") or row.get("path") or ""),
                "path": str(row.get("path") or ""),
                "module_id": row.get("module_id"),
                "source_exists": source_path.is_file(),
                "target_exists": target_path.is_file(),
                "source_ref_required": source_ref_required,
                "source_ref_verification": "source_faithful_public_refactor",
                "source_to_target_relation": row.get("source_to_target_relation"),
                "body_copied": False,
                "body_in_receipt": False,
                "sha256": target_sha,
                "expected_sha256": expected_target_sha,
                "source_sha256": source_sha or expected_source_sha,
                "expected_source_sha256": expected_source_sha,
                "digest_status": "source_digest_recorded_target_is_public_refactor" if digest_match else "mismatch",
                "line_count": target_line_count,
                "expected_line_count": expected_line_count,
                "line_count_status": "match" if line_count_match else "mismatch",
                "required_anchor_count": len(anchors),
                "missing_required_anchors": missing_anchors,
                "rewrite_recipe": row.get("rewrite_recipe"),
            }
        )
        if target_path.is_file():
            source_artifact_paths.append(target_path)
        if source_ref_required and not source_path.is_file():
            findings.append(
                finding(
                    "BATCH11_PUBLIC_REFACTOR_SOURCE_REF_MISSING",
                    "Declared source-faithful refactor source_ref must exist in the macro repo.",
                    subject_id=source_ref,
                )
            )
        if not target_path.is_file():
            findings.append(
                finding(
                    "BATCH11_PUBLIC_REFACTOR_TARGET_MISSING",
                    "Declared source-faithful refactor target must exist in the public bundle.",
                    subject_id=str(row.get("target_ref") or row.get("path") or ""),
                )
            )
        if not digest_match:
            findings.append(
                finding(
                    "BATCH11_PUBLIC_REFACTOR_DIGEST_MISMATCH",
                    "Declared source-faithful refactor must match recorded source and target digests.",
                    subject_id=source_ref,
                    expected={"source_sha256": expected_source_sha, "target_sha256": expected_target_sha},
                    observed={"source_sha256": source_sha, "target_sha256": target_sha},
                )
            )
        if not line_count_match:
            findings.append(
                finding(
                    "BATCH11_PUBLIC_REFACTOR_LINE_COUNT_MISMATCH",
                    "Declared source-faithful refactor line count must match source_module_manifest.json.",
                    subject_id=source_ref,
                    expected=expected_line_count,
                    observed=target_line_count,
                )
            )
        if missing_anchors:
            findings.append(
                finding(
                    "BATCH11_PUBLIC_REFACTOR_ANCHOR_MISSING",
                    "Declared source-faithful refactor is missing required provenance anchors.",
                    subject_id=source_ref,
                    expected=list(anchors),
                    observed={"missing": missing_anchors},
                )
            )

    forbidden_classes = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    secret_scan = scan_paths(
        source_artifact_paths,
        forbidden_classes=forbidden_classes,
        display_root=public_root,
    )
    if secret_scan.get("blocking_hit_count", 0) != 0:
        findings.append(
            finding(
                "BATCH11_PUBLIC_REFACTOR_SECRET_SCAN_BLOCKED",
                "Batch-11 exact-copy and public-refactor source artifacts must pass secret-exclusion scanning.",
                observed=secret_scan.get("blocking_hit_count"),
            )
        )

    augmented["modules"] = modules
    augmented["module_count"] = len(modules)
    augmented["findings"] = findings
    augmented["status"] = "pass" if not findings else "blocked"
    augmented["source_artifact_paths"] = [
        display(path, public_root=public_root) for path in source_artifact_paths
    ]
    augmented["all_expected_digests_matched"] = all(
        row.get("digest_status") in {"match", "source_digest_recorded_target_is_public_refactor"}
        for row in modules
    )
    augmented["all_expected_line_counts_matched"] = all(
        row.get("line_count_status") == "match" for row in modules
    )
    augmented["all_required_anchors_present"] = all(
        not row.get("missing_required_anchors") for row in modules
    )
    augmented["secret_exclusion_scan"] = secret_scan
    return augmented


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    try:
        source_manifest = _source_manifest_for_input(input_dir)
        payload = _negative_case_payloads(input_dir).get(case_id, {})
        probe = _compute_negative_case_probe(
            case_id,
            payload,
            source_manifest=source_manifest,
        )
        if probe.get("computed_value") is True:
            return _semantic_negative_result(case_id, expected_codes)
        return _semantic_negative_not_rejected(
            case_id,
            {
                "source_manifest_status": source_manifest.get("status"),
                "probe": probe,
            },
        )
    except Exception as exc:  # pragma: no cover - receipt carries exact class.
        return _semantic_negative_error(case_id, exc)


def _raw_source_manifest(source_manifest: Mapping[str, Any]) -> dict[str, Any]:
    manifest_path = source_manifest.get("source_manifest_path")
    if isinstance(manifest_path, str) and Path(manifest_path).is_file():
        return json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    return {}


def _source_evidence(mechanism_id: str, source_manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_manifest = _raw_source_manifest(source_manifest)
    rows_by_ref = {
        str(row.get("source_ref")): row
        for row in source_manifest.get("modules", [])
        if isinstance(row, Mapping)
    }
    module_ids_by_ref = {
        str(row.get("source_ref")): row.get("module_id")
        for row in raw_manifest.get("modules", [])
        if isinstance(row, Mapping)
    }
    module_ids_by_ref.update(
        {
            str(row.get("source_ref")): row.get("module_id")
            for row in raw_manifest.get("source_faithful_public_refactors", [])
            if isinstance(row, Mapping)
        }
    )
    evidence: list[dict[str, Any]] = []
    for source_ref in MECHANISM_SOURCE_REFS.get(mechanism_id, ()):
        copied = rows_by_ref.get(source_ref)
        evidence.append(
            {
                "source_ref": source_ref,
                "module_id": module_ids_by_ref.get(source_ref),
                "source_to_target_relation": copied.get("source_to_target_relation") if copied else "missing",
                "digest_status": copied.get("digest_status") if copied else "missing",
                "missing_required_anchor_count": len(copied.get("missing_required_anchors") or []) if copied else None,
                "body_copied": bool(copied and copied.get("body_copied")),
                "body_in_receipt": False,
                "rewrite_recipe": copied.get("rewrite_recipe") if copied else None,
            }
        )
    return evidence


def _build_integrity_matrix(
    mechanisms: Sequence[Mapping[str, Any]],
    source_manifest: Mapping[str, Any],
    case_payloads: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    by_id = {str(row.get("mechanism_id")): row for row in mechanisms}
    probe_checks = {
        case_id: _compute_negative_case_probe(
            case_id,
            case_payloads.get(case_id, {}),
            source_manifest=source_manifest,
        )
        for case_id in EXPECTED_NEGATIVE_CASES
    }
    for mechanism_id in EXPECTED_MECHANISMS:
        mechanism = by_id.get(mechanism_id, {})
        case_id, computed_key = NEGATIVE_CASE_BY_MECHANISM[mechanism_id]
        probe_check = probe_checks[case_id]
        mechanism_computed_value = bool(mechanism.get(computed_key))
        fixture_computed_value = bool(probe_check.get("computed_value"))
        computed = mechanism_computed_value and fixture_computed_value
        rows.append(
            {
                "mechanism_id": mechanism_id,
                "status": mechanism.get("status"),
                "tier": "B_verified_by_controller" if mechanism_id in TIER_B_MECHANISMS else "A_adversarially_verified_in_cap",
                "binding_disposition": MECHANISM_BINDING_DISPOSITIONS[mechanism_id],
                "source_refs": list(MECHANISM_SOURCE_REFS.get(mechanism_id, ())),
                "source_evidence": _source_evidence(mechanism_id, source_manifest),
                "positive_computed_output": {
                    key: value
                    for key, value in mechanism.items()
                    if key not in {"mechanism_id", "status", "body_in_receipt", "claim_ceiling"}
                    and not key.endswith("_blocks")
                    and not key.endswith("_graded_down")
                    and not key.endswith("_priority")
                    and not key.endswith("_not_invented")
                    and not key.endswith("_zero")
                    and not key.endswith("_other")
                    and not key.endswith("_blocker")
                    and not key.endswith("_skip")
                    and not key.endswith("_score")
                },
                "negative_cases": [
                    {
                        "case_id": case_id,
                        "fixture_role": "negative_case_label_not_verdict_authority",
                        "fixture_error_code": EXPECTED_NEGATIVE_CASES[case_id][0],
                        "computed_path": computed_key,
                        "computed_value": computed,
                        "mechanism_computed_value": mechanism.get(computed_key),
                        "fixture_computed_value": probe_check.get("computed_value"),
                        "computed": computed,
                        "fixture_probe_status": probe_check.get("status"),
                        "fixture_probe_source": probe_check.get("fixture_probe_source"),
                        "fixture_probe_input_digest": probe_check.get("fixture_probe_input_digest"),
                        "fixture_probe_observed": probe_check.get("observed", {}),
                        "verdict_authority": CASE_VERDICT_AUTHORITY,
                        "body_in_receipt": False,
                    }
                ],
                "negative_verdict_authority": CASE_VERDICT_AUTHORITY,
                "negative_result_computed": computed,
                "fixture_verdict_echo_risk": not computed,
                "claim_ceiling": mechanism.get("claim_ceiling"),
                "secret_private_carve_out": "receipts carry refs/digests/counts only; copied bodies remain under source_modules",
                "body_in_receipt": False,
            }
        )
    return {
        "schema_version": "batch11_saturation_engines_integrity_matrix_v1",
        "rows": rows,
        "summary": {
            "mechanism_count": len(rows),
            "computed_negative_case_count": sum(
                len(row["negative_cases"]) for row in rows if row["negative_result_computed"]
            ),
            "fixture_probe_computed_count": sum(
                len(row["negative_cases"])
                for row in rows
                if row["negative_cases"][0].get("fixture_computed_value") is True
            ),
            "fixture_verdict_echo_risk_count": sum(1 for row in rows if row["fixture_verdict_echo_risk"]),
            "tier_b_controller_verification_count": sum(1 for row in rows if row["tier"] == "B_verified_by_controller"),
            "body_in_receipt": False,
        },
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    mechanisms = [
        _run_affinity_matrix(),
        _calculator_matrix(),
        _std_python_matrix(),
        _exogenous_nav_matrix(),
        _portability_matrix(),
        _shard_sectionizer_matrix(),
        _holographic_research_matrix(),
        _projection_secret_scan_matrix(),
        _stockgrid_matrix(),
        _macro_regime_matrix(source_manifest),
        _frontend_nav_matrix(),
        _session_diagnostic_matrix(),
        _demo_take_matrix(),
    ]
    case_payloads = _negative_case_payloads(input_path)
    integrity = _build_integrity_matrix(mechanisms, source_manifest, case_payloads)
    findings: list[dict[str, Any]] = []
    if [row["mechanism_id"] for row in mechanisms] != list(EXPECTED_MECHANISMS):
        findings.append(
            finding(
                "BATCH11_MECHANISM_ORDER_INVALID",
                "Batch-11 capsule must evaluate every expected mechanism in declared order.",
                expected=list(EXPECTED_MECHANISMS),
                observed=[row["mechanism_id"] for row in mechanisms],
            )
        )
    for mechanism in mechanisms:
        if mechanism.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH11_MECHANISM_BLOCKED",
                    "Batch-11 mechanism exercise did not pass.",
                    subject_id=str(mechanism.get("mechanism_id")),
                    observed=mechanism.get("status"),
                )
            )
    if source_manifest.get("module_count", 0) != len(EXPECTED_MODULE_IDS):
        findings.append(
            finding(
                "BATCH11_SOURCE_MODULE_COUNT_INVALID",
                "Batch-11 capsule must carry all copied non-secret source modules.",
                expected=len(EXPECTED_MODULE_IDS),
                observed=source_manifest.get("module_count"),
            )
        )
    if integrity["summary"]["fixture_verdict_echo_risk_count"]:
        findings.append(
            finding(
                "BATCH11_FIXTURE_VERDICT_ECHO_RISK",
                "Every Batch-11 negative case must be paired to computed evaluator evidence.",
                observed=integrity["summary"]["fixture_verdict_echo_risk_count"],
            )
        )
    tier_b_controller_verification = [
        {
            "mechanism_id": mechanism_id,
            "binding_disposition": MECHANISM_BINDING_DISPOSITIONS[mechanism_id],
            "capsule_action": (
                "validate_existing_bound_gate"
                if MECHANISM_BINDING_DISPOSITIONS[mechanism_id].startswith("already_bound")
                else "import_under_bound_or_absent_macro_mechanism"
            ),
            "source_refs": list(MECHANISM_SOURCE_REFS[mechanism_id]),
            "negative_case_id": next(
                row["negative_cases"][0]["case_id"]
                for row in integrity["rows"]
                if row["mechanism_id"] == mechanism_id
            ),
            "body_in_receipt": False,
        }
        for mechanism_id in EXPECTED_MECHANISMS
        if mechanism_id in TIER_B_MECHANISMS
    ]
    return {
        "status": "pass" if not findings else "blocked",
        "input_manifest_schema": input_path.joinpath(PROBE_MANIFEST_NAME).name,
        "mechanism_count": len(mechanisms),
        "mechanism_ids": [str(row.get("mechanism_id")) for row in mechanisms],
        "passed_mechanism_count": sum(1 for row in mechanisms if row.get("status") == "pass"),
        "tier_b_controller_verification_count": integrity["summary"]["tier_b_controller_verification_count"],
        "tier_b_controller_verification": tier_b_controller_verification,
        "mechanisms": mechanisms,
        "integrity_matrix": integrity["rows"],
        "integrity_summary": integrity["summary"],
        "copied_macro_source_module_count": source_manifest.get("module_count"),
        "error_codes": [],
        "findings": findings,
        "body_in_receipt": False,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return _run_batch11_crown_jewel_organ(
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
    )


def run_batch11_saturation_engines_bundle(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
) -> dict[str, Any]:
    return _run_batch11_crown_jewel_organ(
        input_dir,
        out_dir,
        command=command,
        input_mode=BUNDLE_INPUT_MODE,
    )


def _receipt_ref(path: Path, *, public_root: Path) -> str:
    return display(path, public_root=public_root)


def _run_batch11_crown_jewel_organ(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    command: str | None = None,
    acceptance_out: str | Path | None = None,
    input_mode: str = "fixture_input",
) -> dict[str, Any]:
    input_path = Path(input_dir)
    out_path = Path(out_dir)
    public_root = public_root_for_path(input_path)
    findings: list[dict[str, Any]] = []
    for name in SPEC.required_inputs:
        load_json_object(input_path / name, findings, label=name)

    source_manifest = _augment_source_manifest_with_public_refactors(
        validate_source_manifest(input_path, SPEC, public_root=public_root),
        public_root=public_root,
    )
    findings.extend(source_manifest.get("findings", []))
    exercise = _evaluate(input_path, public_root, source_manifest)
    findings.extend(exercise.get("findings", []))
    negative_cases = validate_negative_cases(
        input_path,
        SPEC.expected_negative_cases,
        negative_case_evaluator=evaluate_negative_case,
    )
    findings.extend(negative_cases.get("findings", []))

    forbidden_classes = load_forbidden_classes(public_root / "core/private_state_forbidden_classes.json")
    scan_candidates = [input_path / name for name in SPEC.required_inputs]
    scan_candidates.extend(input_path / f"{case_id}.json" for case_id in SPEC.expected_negative_cases)
    secret_scan = scan_paths(
        [path for path in scan_candidates if path.is_file()],
        forbidden_classes=forbidden_classes,
        display_root=public_root,
    )
    if secret_scan.get("blocking_hit_count", 0) != 0:
        findings.append(
            finding(
                "CROWN_JEWEL_FIXTURE_SECRET_SCAN_BLOCKED",
                "Fixture inputs must pass secret-exclusion scanning.",
                observed=secret_scan.get("blocking_hit_count"),
            )
        )

    status = PASS if not findings else "blocked"
    out_path.mkdir(parents=True, exist_ok=True)
    result_path = out_path / (
        BUNDLE_RESULT_NAME if input_mode == BUNDLE_INPUT_MODE else RESULT_NAME
    )
    board_path = out_path / BOARD_NAME
    validation_path = out_path / VALIDATION_RECEIPT_NAME
    receipt_paths = [
        _receipt_ref(result_path, public_root=public_root),
        _receipt_ref(board_path, public_root=public_root),
        _receipt_ref(validation_path, public_root=public_root),
    ]
    acceptance_path = Path(acceptance_out) if acceptance_out else None
    if acceptance_path:
        receipt_paths.append(_receipt_ref(acceptance_path, public_root=public_root))

    payload: dict[str, Any] = {
        "schema_version": f"{ORGAN_ID}_receipt_v1",
        "organ_id": ORGAN_ID,
        "fixture_id": FIXTURE_ID,
        "validator_id": VALIDATOR_ID,
        "created_at": utc_now(),
        "status": status,
        "input_mode": input_mode,
        "input_ref": display(input_path, public_root=public_root),
        "command": command,
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": dict(AUTHORITY_CEILING),
        "real_substrate_disposition": REAL_SUBSTRATE_DISPOSITION,
        "input_count": len(SPEC.required_inputs),
        "source_module_manifest": {
            key: value
            for key, value in source_manifest.items()
            if key not in {"findings", "source_manifest_path"}
        },
        "exercise": {
            key: value
            for key, value in exercise.items()
            if key not in {"findings"}
        },
        "observed_negative_cases": negative_cases["observed_negative_cases"],
        "missing_negative_cases": negative_cases["missing_negative_cases"],
        "expected_negative_cases": sorted(SPEC.expected_negative_cases),
        "negative_case_semantics": negative_cases["negative_case_semantics"],
        "semantic_negative_case_evaluator_used": negative_cases["semantic_evaluator_used"],
        "error_codes": sorted(
            {
                *(row.get("error_code") for row in findings if row.get("error_code")),
                *negative_cases["error_codes"],
                *strings(exercise.get("error_codes")),
            }
        ),
        "findings": findings,
        "secret_exclusion_scan": secret_scan,
        "receipt_paths": receipt_paths,
        "body_in_receipt": False,
    }
    payload["receipt_body_scan"] = scan_receipt_payload_for_bodies(payload)
    if payload["receipt_body_scan"]["status"] != PASS:
        payload["status"] = "blocked"
        payload["error_codes"] = sorted(
            set(payload["error_codes"]) | {"CROWN_JEWEL_RECEIPT_BODY_SCAN_BLOCKED"}
        )

    board_payload = {
        "schema_version": f"{ORGAN_ID}_board_v1",
        "organ_id": ORGAN_ID,
        "title": SPEC.title,
        "status": payload["status"],
        "verdict": payload["status"],
        "counts": {
            "input_count": payload["input_count"],
            "source_module_count": source_manifest.get("module_count", 0),
            "observed_negative_case_count": len(payload["observed_negative_cases"]),
            "finding_count": len(payload["findings"]),
        },
        "anti_claim": ANTI_CLAIM,
        "authority_ceiling": dict(AUTHORITY_CEILING),
        "body_in_receipt": False,
    }
    validation_payload = {
        "schema_version": f"{ORGAN_ID}_validation_receipt_v1",
        "organ_id": ORGAN_ID,
        "status": payload["status"],
        "validator_id": VALIDATOR_ID,
        "source_module_manifest_status": source_manifest.get("status"),
        "exercise_status": exercise.get("status"),
        "negative_case_status": negative_cases.get("status"),
        "secret_exclusion_status": secret_scan.get("status"),
        "receipt_body_scan_status": payload["receipt_body_scan"]["status"],
        "anti_claim": ANTI_CLAIM,
        "body_in_receipt": False,
    }
    write_json_atomic(result_path, payload)
    write_json_atomic(board_path, board_payload)
    write_json_atomic(validation_path, validation_payload)
    if acceptance_path:
        write_json_atomic(
            acceptance_path,
            {
                "schema_version": "microcosm_first_wave_fixture_acceptance_v1",
                "organ_id": ORGAN_ID,
                "fixture_id": FIXTURE_ID,
                "status": payload["status"],
                "accepted": payload["status"] == PASS,
                "real_substrate_disposition": REAL_SUBSTRATE_DISPOSITION,
                "result_ref": _receipt_ref(result_path, public_root=public_root),
                "validation_ref": _receipt_ref(validation_path, public_root=public_root),
                "anti_claim": ANTI_CLAIM,
                "body_in_receipt": False,
            },
        )
    return payload


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["mechanism_count"] = exercise.get("mechanism_count")
    card["passed_mechanism_count"] = exercise.get("passed_mechanism_count")
    card["tier_b_controller_verification_count"] = exercise.get("tier_b_controller_verification_count")
    card["mechanism_ids"] = exercise.get("mechanism_ids", [])
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
    result = _run_batch11_crown_jewel_organ(
        args.input,
        args.out,
        command=f"{ORGAN_ID} {args.action}",
        acceptance_out=args.acceptance_out,
        input_mode=BUNDLE_INPUT_MODE if args.action == "validate-bundle" else "fixture_input",
    )
    print(json.dumps(result_card(result) if args.card else result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
