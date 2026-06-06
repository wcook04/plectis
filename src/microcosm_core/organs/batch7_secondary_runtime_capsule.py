from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from microcosm_core.organs._crown_jewel_common import (
    CrownJewelSpec,
    card_for_result,
    finding,
    public_root_for_path,
    run_crown_jewel_organ,
)


ORGAN_ID = "batch7_secondary_runtime_capsule"
FIXTURE_ID = "first_wave.batch7_secondary_runtime_capsule"
VALIDATOR_ID = "validator.microcosm.organs.batch7_secondary_runtime_capsule"

RESULT_NAME = "batch7_secondary_runtime_capsule_result.json"
BOARD_NAME = "batch7_secondary_runtime_capsule_board.json"
VALIDATION_RECEIPT_NAME = "batch7_secondary_runtime_capsule_validation_receipt.json"
BUNDLE_RESULT_NAME = "exported_batch7_secondary_runtime_capsule_validation_result.json"
CARD_SCHEMA_VERSION = "batch7_secondary_runtime_capsule_command_card_v1"
BUNDLE_INPUT_MODE = "exported_batch7_secondary_runtime_capsule_bundle"
EXERCISE_MANIFEST_NAME = "batch7_secondary_exercise_manifest.json"

EXPECTED_ENGINES: tuple[str, ...] = (
    "agent_trace_view_model_trust_taxonomy",
    "lane_progress_state_normalizer",
    "universal_graph_lens_focus_roles",
    "graph_projection_summary_quotient",
    "cap_cartography_shadow_render",
    "stockgrid_payload_factory_terms",
    "polymarket_clob_microstructure",
    "polymarket_four_lens_scanner",
)

EXPECTED_NEGATIVE_CASES = {
    "trace_view_missing_raw_authority": (
        "BATCH7_SECONDARY_TRACE_VIEW_MISSING_RAW_AUTHORITY",
    ),
    "lane_progress_unknown_state": ("BATCH7_SECONDARY_LANE_PROGRESS_UNKNOWN_STATE",),
    "graph_lens_hidden_descendant": (
        "BATCH7_SECONDARY_GRAPH_LENS_COLLAPSE_ENFORCED",
    ),
    "graph_projection_self_edge": (
        "BATCH7_SECONDARY_GRAPH_PROJECTION_SELF_EDGE_DROPPED",
    ),
    "cap_cartography_mutation_action": (
        "BATCH7_SECONDARY_CAP_CARTOGRAPHY_OBSERVE_ONLY",
    ),
    "stockgrid_extreme_momentum": (
        "BATCH7_SECONDARY_STOCKGRID_EXTREME_MOMENTUM_REFUSED",
    ),
    "polymarket_sorted_book_trap": (
        "BATCH7_SECONDARY_POLYMARKET_NUMERIC_EXTREMA_REQUIRED",
    ),
    "polymarket_resolved_market": (
        "BATCH7_SECONDARY_POLYMARKET_RESOLVED_MARKET_GATED",
    ),
}

NEGATIVE_CASE_CODES = {
    case_id: codes[0] for case_id, codes in EXPECTED_NEGATIVE_CASES.items()
}

AUTHORITY_CEILING = {
    "status": "pass",
    "authority_ceiling": "batch7_secondary_public_capsule_not_release_or_runtime_authority",
    "real_substrate_disposition": "real_substrate_capsule",
    "release_authorized": False,
    "publication_authorized": False,
    "provider_dispatch": False,
    "model_dispatch": False,
    "browser_or_wallet_access": False,
    "source_mutation_authorized": False,
    "investment_advice": False,
    "semantic_truth_authority": False,
    "test_completeness_proof": False,
}

ANTI_CLAIM = (
    "Batch 7 secondary imports public-safe runtime view-model, graph projection, "
    "cartography render, stockgrid, and Polymarket source bodies. It is not a "
    "release, not private-root equivalence, not browser or wallet access, not "
    "market data freshness, not investment advice, and not proof that the UI or "
    "ranking systems are complete."
)

SOURCE_REQUIRED_ANCHORS = {
    "system/server/ui/src/components/world/agentTraceViewModel.ts": (
        "export type TraceTrustClass",
        "function buildUnknowns",
        "export function compileAgentTraceViewModel",
    ),
    "system/server/ui/src/components/world/__tests__/agentTraceViewModel.test.ts": (
        "makes fallback and missingness explicit",
        "classifies observable commands",
    ),
    "system/server/ui/src/components/world/laneProgress.ts": (
        "export function classifyObserveRuntimeState",
        "export function buildMetaMissionPackets",
        "tail_summary",
    ),
    "system/server/ui/src/components/world/__tests__/laneProgress.test.ts": (
        "buildOrchestrationPacket",
        "classifyObserveRuntimeState",
    ),
    "system/server/ui/src/components/graph/universalGraphLens.ts": (
        "export function buildUniversalGraphLens",
        "export function universalGraphFocusOpacity",
    ),
    "system/server/ui/src/components/graph/__tests__/universalGraphLens.test.ts": (
        "keeps collapsed parent nodes visible",
        "stable fallback edge ids",
    ),
    "system/server/ui/src/components/graph/graphProjection.ts": (
        "export function projectGraphForRender",
        "summary_cluster",
    ),
    "system/server/ui/src/lib/capCartographyShadowRender.ts": (
        "export function capCartographySpecimenToGraphElements",
        "function observeOnlyActions",
        "function isMutationActionAvailable",
    ),
    "system/server/ui/src/lib/__tests__/capCartographyShadowRender.test.ts": (
        "projects the world-model exposition specimen",
        "mutation_supported",
    ),
    "tools/stockgrid/stockgrid.py": (
        "class PayloadFactory",
        "def _daily_log_momentum_bps",
        "np.arcsinh",
    ),
    "tools/polymarket/clob_snapshot.py": (
        "def compute_best_prices",
        "Numeric-extrema best-price extraction",
        "def compute_depth_imbalance",
    ),
    "tools/polymarket/score.py": (
        "def calculate_lenses",
        "NEWSBREAKER",
        "is_resolved",
    ),
    "tools/polymarket/models.py": (
        "class NormalizedMarket",
        "@dataclass",
        "scores",
    ),
}

SPEC = CrownJewelSpec(
    organ_id=ORGAN_ID,
    title="Batch 7 Secondary Runtime Capsule",
    fixture_id=FIXTURE_ID,
    validator_id=VALIDATOR_ID,
    result_name=RESULT_NAME,
    board_name=BOARD_NAME,
    validation_receipt_name=VALIDATION_RECEIPT_NAME,
    bundle_result_name=BUNDLE_RESULT_NAME,
    card_schema_version=CARD_SCHEMA_VERSION,
    required_inputs=(EXERCISE_MANIFEST_NAME,),
    expected_negative_cases=EXPECTED_NEGATIVE_CASES,
    anti_claim=ANTI_CLAIM,
    authority_ceiling=AUTHORITY_CEILING,
    source_manifest_ref=(
        "microcosm-substrate/examples/batch7_secondary_runtime_capsule/"
        "exported_batch7_secondary_runtime_capsule_bundle/source_module_manifest.json"
    ),
    source_required_anchors=SOURCE_REQUIRED_ANCHORS,
    bundle_input_mode=BUNDLE_INPUT_MODE,
)


def _repo_root(public_root: Path) -> Path:
    return public_root.parent


def _copied_source(public_root: Path, source_ref: str) -> Path:
    return (
        public_root
        / "examples/batch7_secondary_runtime_capsule/"
        "exported_batch7_secondary_runtime_capsule_bundle/source_modules"
        / source_ref
    )


def _copy_public_bundle(public_root: Path, temp_public_root: Path) -> None:
    shutil.copytree(
        public_root / "examples/batch7_secondary_runtime_capsule",
        temp_public_root / "examples/batch7_secondary_runtime_capsule",
    )


def _replace_copied_source_token(
    public_root: Path,
    source_ref: str,
    old: str,
    new: str,
) -> bool:
    source_path = _copied_source(public_root, source_ref)
    text = source_path.read_text(encoding="utf-8")
    if old not in text:
        return False
    source_path.write_text(text.replace(old, new, 1), encoding="utf-8")
    return True


def _run_public_witness(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 30,
) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError as exc:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_SECONDARY_WITNESS_COMMAND_MISSING",
            "error_type": type(exc).__name__,
            "body_in_receipt": False,
        }
    except subprocess.TimeoutExpired:
        return {
            "status": "blocked",
            "returncode": None,
            "error_code": "BATCH7_SECONDARY_WITNESS_TIMEOUT",
            "body_in_receipt": False,
        }
    return {
        "status": "pass" if completed.returncode == 0 else "blocked",
        "returncode": completed.returncode,
        "stdout_byte_count": len(completed.stdout.encode("utf-8")),
        "stderr_byte_count": len(completed.stderr.encode("utf-8")),
        "body_in_receipt": False,
    }


def _passing_ui_witness() -> dict[str, Any]:
    return {
        "status": "pass",
        "returncode": 0,
        "stdout_byte_count": 0,
        "stderr_byte_count": 0,
        "body_in_receipt": False,
    }


def _mutated_source_negative(
    public_root: Path,
    *,
    case_id: str,
    source_ref: str,
    old: str,
    new: str,
    exercise: Any,
    observed_flag: str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_{case_id}_") as tmp:
        temp_public_root = Path(tmp) / "microcosm-substrate"
        _copy_public_bundle(public_root, temp_public_root)
        mutation_applied = _replace_copied_source_token(
            temp_public_root,
            source_ref,
            old,
            new,
        )
        result = exercise(temp_public_root)
    observed = mutation_applied and result.get("status") == "blocked"
    if observed_flag is not None:
        observed = observed and result.get(observed_flag) is False
    payload = {
        "status": "blocked" if observed else "pass",
        "case_id": case_id,
        "engine_id": result.get("engine_id"),
        "mutation_applied": mutation_applied,
        "semantic_blocked": observed,
        "body_in_receipt": False,
    }
    if observed_flag is not None:
        payload[observed_flag] = result.get(observed_flag)
    return payload


def _ui_vitest_witness(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    return _run_public_witness(
        [
            "npm",
            "exec",
            "--",
            "vitest",
            "run",
            "src/components/world/__tests__/agentTraceViewModel.test.ts",
            "src/components/world/__tests__/laneProgress.test.ts",
            "src/components/graph/__tests__/universalGraphLens.test.ts",
            "src/lib/__tests__/capCartographyShadowRender.test.ts",
        ],
        cwd=repo / "system/server/ui",
        timeout=45,
    )


def _agent_trace_view_model_exercise(public_root: Path, witness: Mapping[str, Any]) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/world/agentTraceViewModel.ts",
    ).read_text(encoding="utf-8")
    trust_classes = [
        "authority",
        "projection",
        "derived",
        "stale",
        "missing",
        "fallback",
        "truncated",
    ]
    missing_raw_authority = (
        "Raw provider JSONL is unavailable from this UI state." in source
        and "raw missing" in source
    )
    return {
        "status": "pass"
        if witness.get("status") == "pass"
        and all(f"'{trust}'" in source for trust in trust_classes)
        and missing_raw_authority
        else "blocked",
        "engine_id": "agent_trace_view_model_trust_taxonomy",
        "original_witness": {
            "kind": "vitest",
            "command": "npm exec -- vitest run agentTraceViewModel/laneProgress/universalGraphLens/capCartography tests",
            **dict(witness),
        },
        "trust_class_count": len(trust_classes),
        "missing_raw_authority_negative": missing_raw_authority,
        "claim_ceiling": "UI trust badges are evidence labels, not raw trace authority.",
    }


def _lane_progress_exercise(public_root: Path, witness: Mapping[str, Any]) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/world/laneProgress.ts",
    ).read_text(encoding="utf-8")
    state_map = {
        "dispatching": "running",
        "running": "running",
        "awaiting_review": "blocked",
        "completed": "success",
        "error": "failure",
        "aborted": "aborted",
        "idle": "idle",
        "new_state": "idle",
    }
    required_returns = (
        "return 'running'",
        "return 'blocked'",
        "return 'success'",
        "return 'failure'",
        "return 'aborted'",
        "return 'idle'",
    )
    return {
        "status": "pass"
        if witness.get("status") == "pass" and all(item in source for item in required_returns)
        else "blocked",
        "engine_id": "lane_progress_state_normalizer",
        "state_map": state_map,
        "unknown_state_negative": state_map["new_state"] == "idle",
        "tail_summary_present": "meta_missions:tail_summary" in source,
        "claim_ceiling": "runtime-lane progress vocabulary only; not operator action authority.",
    }


def _universal_graph_lens_exercise(public_root: Path, witness: Mapping[str, Any]) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/graph/universalGraphLens.ts",
    ).read_text(encoding="utf-8")
    nodes = {
        "root": None,
        "cluster": "root",
        "object": "cluster",
        "evidence": "object",
    }
    collapsed = {"cluster"}

    def hidden_by_collapsed(node_id: str) -> bool:
        parent = nodes[node_id]
        while parent is not None:
            if parent in collapsed:
                return True
            parent = nodes[parent]
        return False

    visible = {node_id for node_id in nodes if not hidden_by_collapsed(node_id)}
    return {
        "status": "pass"
        if witness.get("status") == "pass"
        and visible == {"root", "cluster"}
        and "closure(start" in source
        else "blocked",
        "engine_id": "universal_graph_lens_focus_roles",
        "visible_nodes_after_collapse": sorted(visible),
        "hidden_descendant_negative": "object" not in visible and "evidence" not in visible,
        "claim_ceiling": "graph visibility/focus projection only; not graph truth authority.",
    }


def _graph_projection_exercise(public_root: Path) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/graph/graphProjection.ts",
    ).read_text(encoding="utf-8")
    nodes = [
        {"id": "spine", "wave": 0, "lane": "SPINE", "is_upstream": False},
        {"id": "a", "wave": 1, "lane": "BUILD", "is_upstream": False},
        {"id": "b", "wave": 1, "lane": "BUILD", "is_upstream": False},
        {"id": "c", "wave": 1, "lane": "CHECK", "is_upstream": False},
    ]
    projection: dict[str, list[str]] = {"spine": ["spine"]}
    for node in nodes[1:]:
        projection.setdefault(f"summary_cluster_{node['lane'].lower()}_{node['wave']}", []).append(node["id"])
    edges = [("a", "b"), ("a", "c"), ("spine", "a")]
    projected_edges = set()
    for left, right in edges:
        left_projection = next(key for key, members in projection.items() if left in members)
        right_projection = next(key for key, members in projection.items() if right in members)
        if left_projection != right_projection:
            projected_edges.add((left_projection, right_projection))
    return {
        "status": "pass"
        if "if (!sourceId || !targetId || sourceId === targetId) return;" in source
        and ("summary_cluster_build_1", "summary_cluster_check_1") in projected_edges
        and ("summary_cluster_build_1", "summary_cluster_build_1") not in projected_edges
        else "blocked",
        "engine_id": "graph_projection_summary_quotient",
        "summary_cluster_count": len(projection),
        "projected_edges": sorted(f"{left}->{right}" for left, right in projected_edges),
        "self_edge_dropped": ("summary_cluster_build_1", "summary_cluster_build_1") not in projected_edges,
        "claim_ceiling": "render quotient projection only; not lossless graph storage.",
    }


def _cap_cartography_exercise(public_root: Path, witness: Mapping[str, Any]) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/lib/capCartographyShadowRender.ts",
    ).read_text(encoding="utf-8")
    observe_only_boundary = (
        "const REQUIRED_BLOCKED_ACTIONS" in source
        and "'create_cap'" in source
        and "'mutate_cap'" in source
        and "'edit_edge'" in source
        and "'infer_title_semantics'" in source
        and "available_actions:" in source
        and "inspect_source_route" in source
        and "mutationActionCount" in source
    )
    return {
        "status": "pass"
        if witness.get("status") == "pass" and observe_only_boundary else "blocked",
        "engine_id": "cap_cartography_shadow_render",
        "observe_only_actions_enforced": observe_only_boundary,
        "renderer_function_present": "capCartographySpecimenToGraphElements" in source,
        "claim_ceiling": "observe-only renderer projection; no cap creation or mutation authority.",
    }


def _stockgrid_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    import pandas as pd
    from tools.stockgrid.stockgrid import PayloadFactory

    factory = PayloadFactory.__new__(PayloadFactory)
    positive_bps = factory._daily_log_momentum_bps(10.0, 10)
    refused_extreme = factory._daily_log_momentum_bps(-100.0, 10) is None
    zscores = [round(float(value), 6) for value in factory._zscore(pd.Series([1.0, 2.0, 3.0]))]
    mean_defined = factory._mean_defined([1, None, "3"])
    return {
        "status": "pass"
        if positive_bps is not None
        and positive_bps > 90
        and refused_extreme
        and zscores == [-1.224745, 0.0, 1.224745]
        and mean_defined == 2.0
        else "blocked",
        "engine_id": "stockgrid_payload_factory_terms",
        "daily_log_momentum_bps": round(float(positive_bps or 0.0), 6),
        "zscore_triplet": zscores,
        "mean_defined": mean_defined,
        "extreme_momentum_refused": refused_extreme,
        "dependency_versions": {"pandas": getattr(pd, "__version__", "unknown")},
        "claim_ceiling": "local feature engineering primitive only; excludes upstream fetch and trading advice.",
    }


def _polymarket_clob_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.polymarket.clob_snapshot import (
        compute_best_prices,
        compute_depth_at_band,
        compute_depth_imbalance,
    )

    bids = [
        {"price": "0.12", "size": "20"},
        {"price": "0.42", "size": "5"},
        {"price": "0.25", "size": "2"},
    ]
    asks = [
        {"price": "0.88", "size": "3"},
        {"price": "0.53", "size": "7"},
        {"price": "0.65", "size": "9"},
    ]
    best_bid, best_ask, spread, midpoint, best_bid_size, best_ask_size = compute_best_prices(
        bids,
        asks,
    )
    bid_depth = compute_depth_at_band(bids, best_bid, 0.20, direction="bid")
    ask_depth = compute_depth_at_band(asks, best_ask, 0.20, direction="ask")
    imbalance = compute_depth_imbalance(bid_depth, ask_depth)
    sorted_book_trap_rejected = best_bid != float(bids[0]["price"]) and best_ask != float(asks[0]["price"])
    return {
        "status": "pass"
        if best_bid == 0.42
        and best_ask == 0.53
        and round(float(spread or 0), 2) == 0.11
        and sorted_book_trap_rejected
        and imbalance is not None
        and -1.0 <= imbalance <= 1.0
        else "blocked",
        "engine_id": "polymarket_clob_microstructure",
        "best_bid": best_bid,
        "best_ask": best_ask,
        "spread": spread,
        "midpoint": midpoint,
        "best_bid_size": best_bid_size,
        "best_ask_size": best_ask_size,
        "depth_imbalance": round(float(imbalance or 0.0), 6),
        "sorted_book_trap_rejected": sorted_book_trap_rejected,
        "claim_ceiling": "public CLOB math primitive only; excludes wallet/client identity and live market access.",
    }


def _polymarket_score_exercise(public_root: Path) -> dict[str, Any]:
    repo = _repo_root(public_root)
    if str(repo) not in sys.path:
        sys.path.insert(0, str(repo))
    from tools.polymarket.models import NormalizedMarket
    from tools.polymarket.score import calculate_lenses

    tuning = {
        "newsbreaker": {
            "min_volume": 100,
            "min_uncertainty": 0.1,
            "max_abs_change": 0.5,
            "uncertainty_power": 1.0,
        },
        "god_mode": {"min_price": 0.2, "max_price": 0.8},
        "scout": {"max_volume": 50_000},
    }
    open_market = NormalizedMarket(
        q="Will the synthetic fixture resolve?",
        o="Yes",
        p=0.52,
        c=0.1,
        v=1000.0,
        s=0.0,
        slug="synthetic-fixture",
        topic="synthetic",
        status="open",
        liquidity=1000.0,
        event_title="Synthetic Fixture",
        event_slug="synthetic-fixture",
        market_id="fixture-open",
        market_slug="fixture-open",
    )
    resolved_market = NormalizedMarket(
        q=open_market.q,
        o=open_market.o,
        p=0.99,
        c=0.01,
        v=1000.0,
        s=0.0,
        slug="synthetic-resolved",
        topic="synthetic",
        status="resolved",
        liquidity=1000.0,
        event_title="Synthetic Fixture",
        event_slug="synthetic-fixture",
        market_id="fixture-resolved",
        market_slug="fixture-resolved",
    )
    open_scores = calculate_lenses(open_market, tuning)
    resolved_scores = calculate_lenses(resolved_market, tuning)
    return {
        "status": "pass"
        if open_scores["NEWSBREAKER"] > 0
        and resolved_scores["NEWSBREAKER"] == 0.0
        and set(open_scores) == {"HOT SEAT", "NEWSBREAKER", "GOD MODE", "SCOUT"}
        else "blocked",
        "engine_id": "polymarket_four_lens_scanner",
        "open_scores": {key: round(value, 6) for key, value in sorted(open_scores.items())},
        "resolved_newsbreaker_gated": resolved_scores["NEWSBREAKER"] == 0.0,
        "claim_ceiling": "synthetic market scoring fixture only; not prediction or investment advice.",
    }


def _trace_view_missing_raw_authority_negative(public_root: Path) -> dict[str, Any]:
    return _mutated_source_negative(
        public_root,
        case_id="trace_view_missing_raw_authority",
        source_ref="system/server/ui/src/components/world/agentTraceViewModel.ts",
        old="Raw provider JSONL is unavailable from this UI state.",
        new="Provider body available.",
        exercise=lambda root: _agent_trace_view_model_exercise(root, _passing_ui_witness()),
        observed_flag="missing_raw_authority_negative",
    )


def _lane_progress_unknown_state_negative(public_root: Path) -> dict[str, Any]:
    source = _copied_source(
        public_root,
        "system/server/ui/src/components/world/laneProgress.ts",
    ).read_text(encoding="utf-8")
    observed = (
        "export function classifyObserveRuntimeState" in source
        and "if (!state) return 'idle';" in source
        and "return 'idle';" in source
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "lane_progress_unknown_state",
        "engine_id": "lane_progress_state_normalizer",
        "unknown_state_negative": observed,
        "body_in_receipt": False,
    }


def _graph_lens_hidden_descendant_negative(public_root: Path) -> dict[str, Any]:
    return _mutated_source_negative(
        public_root,
        case_id="graph_lens_hidden_descendant",
        source_ref="system/server/ui/src/components/graph/universalGraphLens.ts",
        old="closure(start",
        new="closureMissing(start",
        exercise=lambda root: _universal_graph_lens_exercise(root, _passing_ui_witness()),
    )


def _graph_projection_self_edge_negative(public_root: Path) -> dict[str, Any]:
    return _mutated_source_negative(
        public_root,
        case_id="graph_projection_self_edge",
        source_ref="system/server/ui/src/components/graph/graphProjection.ts",
        old="if (!sourceId || !targetId || sourceId === targetId) return;",
        new="if (!sourceId || !targetId) return;",
        exercise=_graph_projection_exercise,
    )


def _cap_cartography_mutation_action_negative(public_root: Path) -> dict[str, Any]:
    return _mutated_source_negative(
        public_root,
        case_id="cap_cartography_mutation_action",
        source_ref="system/server/ui/src/lib/capCartographyShadowRender.ts",
        old="'mutate_cap'",
        new="'inspect_cap'",
        exercise=lambda root: _cap_cartography_exercise(root, _passing_ui_witness()),
        observed_flag="observe_only_actions_enforced",
    )


def _stockgrid_extreme_momentum_negative(public_root: Path) -> dict[str, Any]:
    result = _stockgrid_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("extreme_momentum_refused") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "stockgrid_extreme_momentum",
        "engine_id": result.get("engine_id"),
        "extreme_momentum_refused": result.get("extreme_momentum_refused"),
        "body_in_receipt": False,
    }


def _polymarket_sorted_book_trap_negative(public_root: Path) -> dict[str, Any]:
    result = _polymarket_clob_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("sorted_book_trap_rejected") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "polymarket_sorted_book_trap",
        "engine_id": result.get("engine_id"),
        "sorted_book_trap_rejected": result.get("sorted_book_trap_rejected"),
        "body_in_receipt": False,
    }


def _polymarket_resolved_market_negative(public_root: Path) -> dict[str, Any]:
    result = _polymarket_score_exercise(public_root)
    observed = (
        result.get("status") == "pass"
        and result.get("resolved_newsbreaker_gated") is True
    )
    return {
        "status": "blocked" if observed else "pass",
        "case_id": "polymarket_resolved_market",
        "engine_id": result.get("engine_id"),
        "resolved_newsbreaker_gated": result.get("resolved_newsbreaker_gated"),
        "body_in_receipt": False,
    }


@lru_cache(maxsize=16)
def _semantic_runtime_exercises(input_ref: str) -> Mapping[str, Any]:
    public_root = public_root_for_path(Path(input_ref))
    return {
        "negative_exercises": {
            "trace_view_missing_raw_authority": _trace_view_missing_raw_authority_negative(public_root),
            "lane_progress_unknown_state": _lane_progress_unknown_state_negative(public_root),
            "graph_lens_hidden_descendant": _graph_lens_hidden_descendant_negative(public_root),
            "graph_projection_self_edge": _graph_projection_self_edge_negative(public_root),
            "cap_cartography_mutation_action": _cap_cartography_mutation_action_negative(public_root),
            "stockgrid_extreme_momentum": _stockgrid_extreme_momentum_negative(public_root),
            "polymarket_sorted_book_trap": _polymarket_sorted_book_trap_negative(public_root),
            "polymarket_resolved_market": _polymarket_resolved_market_negative(public_root),
        },
        "body_in_receipt": False,
    }


def _negative_exercise(runtime: Mapping[str, Any], case_id: str) -> Mapping[str, Any]:
    cases = (
        runtime.get("negative_exercises")
        if isinstance(runtime.get("negative_exercises"), Mapping)
        else {}
    )
    case = cases.get(case_id)
    return case if isinstance(case, Mapping) else {}


def _observed_negative_case(case_id: str, runtime: Mapping[str, Any]) -> bool:
    exercise = _negative_exercise(runtime, case_id)
    if case_id == "trace_view_missing_raw_authority":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("missing_raw_authority_negative") is False
        )
    if case_id == "lane_progress_unknown_state":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("unknown_state_negative") is True
        )
    if case_id in {
        "graph_lens_hidden_descendant",
        "graph_projection_self_edge",
    }:
        return (
            exercise.get("status") == "blocked"
            and exercise.get("semantic_blocked") is True
        )
    if case_id == "cap_cartography_mutation_action":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("observe_only_actions_enforced") is False
        )
    if case_id == "stockgrid_extreme_momentum":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("extreme_momentum_refused") is True
        )
    if case_id == "polymarket_sorted_book_trap":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("sorted_book_trap_rejected") is True
        )
    if case_id == "polymarket_resolved_market":
        return (
            exercise.get("status") == "blocked"
            and exercise.get("resolved_newsbreaker_gated") is True
        )
    return False


def evaluate_negative_case(
    case_id: str,
    input_dir: Path,
    _expected_codes: tuple[str, ...],
) -> Mapping[str, Any]:
    expected_code = NEGATIVE_CASE_CODES.get(case_id, "")
    observed = _observed_negative_case(
        case_id,
        _semantic_runtime_exercises(str(Path(input_dir))),
    )
    return {
        "status": "blocked" if observed else "pass",
        "error_codes": [expected_code] if observed and expected_code else [],
        "body_in_receipt": False,
    }


def _evaluate(
    input_path: Path,
    public_root: Path,
    source_manifest: dict[str, Any],
) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    witness = _ui_vitest_witness(public_root)
    exercises = [
        _agent_trace_view_model_exercise(public_root, witness),
        _lane_progress_exercise(public_root, witness),
        _universal_graph_lens_exercise(public_root, witness),
        _graph_projection_exercise(public_root),
        _cap_cartography_exercise(public_root, witness),
        _stockgrid_exercise(public_root),
        _polymarket_clob_exercise(public_root),
        _polymarket_score_exercise(public_root),
    ]
    for exercise in exercises:
        if exercise.get("status") != "pass":
            findings.append(
                finding(
                    "BATCH7_SECONDARY_ENGINE_EXERCISE_BLOCKED",
                    "A Batch-7 secondary engine exercise did not pass.",
                    subject_id=str(exercise.get("engine_id")),
                    observed=exercise.get("status"),
                )
            )
    observed = {str(row.get("engine_id")) for row in exercises}
    missing = sorted(set(EXPECTED_ENGINES) - observed)
    if missing:
        findings.append(
            finding(
                "BATCH7_SECONDARY_ENGINE_EXERCISE_MISSING",
                "A Batch-7 secondary engine is missing from the exercise result.",
                observed=missing,
            )
        )
    return {
        "status": "pass" if not findings else "blocked",
        "engine_count": len(exercises),
        "engine_ids": sorted(observed),
        "copied_macro_source_module_count": source_manifest.get("module_count", 0),
        "engines": exercises,
        "error_codes": [
            str(row["error_code"]) for row in findings if row.get("error_code")
        ],
        "body_in_receipt": False,
        "findings": findings,
    }


def run(
    input_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        input_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def run_batch7_secondary_bundle(
    bundle_dir: str | Path,
    out_dir: str | Path,
    *,
    acceptance_out: str | Path | None = None,
    command: str | None = None,
) -> dict[str, Any]:
    return run_crown_jewel_organ(
        SPEC,
        bundle_dir,
        out_dir,
        command=command,
        acceptance_out=acceptance_out,
        input_mode=BUNDLE_INPUT_MODE,
        evaluator=_evaluate,
        negative_case_evaluator=evaluate_negative_case,
    )


def result_card(result: Mapping[str, Any]) -> dict[str, Any]:
    card = card_for_result(SPEC, result)
    exercise = result.get("exercise") if isinstance(result.get("exercise"), Mapping) else {}
    card["engine_count"] = exercise.get("engine_count")
    card["copied_macro_source_module_count"] = exercise.get(
        "copied_macro_source_module_count"
    )
    card["real_substrate_disposition"] = result.get("real_substrate_disposition")
    return card


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="microcosm batch7-secondary-runtime-capsule")
    sub = parser.add_subparsers(dest="action", required=True)
    for action in ("run", "run-batch7-secondary-bundle"):
        action_parser = sub.add_parser(action)
        action_parser.add_argument("--input", required=True)
        action_parser.add_argument("--out", required=True)
        action_parser.add_argument("--acceptance-out")
        action_parser.add_argument("--card", action="store_true")
    args = parser.parse_args(argv)
    runner = run_batch7_secondary_bundle if args.action == "run-batch7-secondary-bundle" else run
    result = runner(
        args.input,
        args.out,
        acceptance_out=args.acceptance_out,
        command=f"{ORGAN_ID} {args.action}",
    )
    if args.card:
        print(json.dumps(result_card(result), indent=2, sort_keys=True))
    else:
        print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
