"""
[PURPOSE]
- Teleology: Project the market-evidence fusion spine into a refusal-first
  readiness gate before any Lab, Oracle, or Station consumer turns raw feed
  presence into cross-feed interpretation.
- Mechanism: Deterministic lane rows and candidate situation gates over the
  seven feed lanes, using the three mature lifecycle specimens as evidence
  while keeping relation/Oracle gaps explicit.
- Non-goal: This is not a MarketEvidenceObject runtime schema and not an
  operator-facing divergence card generator.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Literal, Mapping, Sequence


SCHEMA_VERSION = "cross_feed_measurement_readiness_gate_v0"
DEFAULT_OUTPUT_PATH = Path(
    "state/reports/market_feeds/cross_feed_measurement_readiness_gate_v0.json"
)

SafeUseLevel = Literal[
    "feed_observation_only",
    "derived_observation_only",
    "lane_measurement_guarded",
    "refuse_cross_feed_claim",
]
GateDecision = Literal["allow", "refuse"]

LANE_ALIASES: Mapping[str, str] = {
    "STOCK": "global_stock_feed",
    "GLOBAL_STOCK_FEED": "global_stock_feed",
    "ETF": "global_etf_feed",
    "GLOBAL_ETF_FEED": "global_etf_feed",
    "MACRO": "global_macro_feed",
    "GLOBAL_MACRO_FEED": "global_macro_feed",
    "NEWS": "global_news_feed",
    "GLOBAL_NEWS_FEED": "global_news_feed",
    "POLY": "global_polymarket_feed",
    "POLYMARKET": "global_polymarket_feed",
    "GLOBAL_POLYMARKET_FEED": "global_polymarket_feed",
    "STOCKGRID": "global_stockgrid_feed",
    "GLOBAL_STOCKGRID_FEED": "global_stockgrid_feed",
    "CALC": "global_calculator_feed",
    "CALCULATOR": "global_calculator_feed",
    "GLOBAL_CALCULATOR_FEED": "global_calculator_feed",
}


@dataclass(frozen=True)
class LaneReadiness:
    lane_id: str
    source_authority_state: str
    identity_state: str
    lifecycle_state: str
    measurement_evidence_state: str
    freshness_quality_state: str
    provenance_as_of_state: str
    oracle_attach_state: str
    cross_feed_relation_state: str
    safe_use_level: SafeUseLevel
    refusal_reasons: tuple[str, ...]
    next_gap_refs: tuple[str, ...]
    sidecar_keys: tuple[str, ...] = ()
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class CandidateSituationGate:
    situation_id: str
    title: str
    attempted_claim: str
    lanes: tuple[str, ...]
    decision: GateDecision
    safe_use_level: SafeUseLevel
    refusal_reasons: tuple[str, ...]
    required_before_allowed: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ConsumerClaimPreflight:
    consumer_name: str
    claim_id: str
    situation_id: str
    attempted_claim: str
    lanes: tuple[str, ...]
    decision: GateDecision
    safe_use_level: SafeUseLevel
    refusal_reasons: tuple[str, ...]
    required_before_allowed: tuple[str, ...]
    evidence_refs: tuple[str, ...] = ()


LANE_READINESS: tuple[LaneReadiness, ...] = (
    LaneReadiness(
        lane_id="global_stock_feed",
        source_authority_state="shipped",
        identity_state="shipped",
        lifecycle_state="shipped_half_built",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="shipped_truth_diff_equity",
        cross_feed_relation_state="present_not_measurement_conditioned",
        safe_use_level="lane_measurement_guarded",
        refusal_reasons=(
            "equity_expected_return_event_window_missing",
            "halt_corporate_action_provider_gap",
            "lab_relation_edges_not_measurement_conditioned",
        ),
        next_gap_refs=(
            "equity_provider_gap_v0_1",
            "fusion_readiness_gate_consumption_hooks_v0",
        ),
        sidecar_keys=("equity_lifecycle_snapshot",),
        evidence_refs=(
            "tools/stock/lifecycle.py",
            "tools/stock/stock.py",
            "tools/oracle/truth_diff_equity.py",
        ),
    ),
    LaneReadiness(
        lane_id="global_etf_feed",
        source_authority_state="shipped",
        identity_state="shipped",
        lifecycle_state="shipped_half_built",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="shipped_truth_diff_equity",
        cross_feed_relation_state="present_not_measurement_conditioned",
        safe_use_level="lane_measurement_guarded",
        refusal_reasons=(
            "etf_nav_provider_gap",
            "etf_basket_rebalance_provider_gap",
            "premium_discount_posture_unavailable_v0",
            "lab_relation_edges_not_measurement_conditioned",
        ),
        next_gap_refs=(
            "equity_provider_gap_v0_1",
            "fusion_readiness_gate_consumption_hooks_v0",
        ),
        sidecar_keys=("equity_lifecycle_snapshot",),
        evidence_refs=(
            "tools/stock/lifecycle.py",
            "tools/stock/stock.py",
            "tools/oracle/truth_diff_equity.py",
        ),
    ),
    LaneReadiness(
        lane_id="global_macro_feed",
        source_authority_state="shipped",
        identity_state="shipped",
        lifecycle_state="shipped_half_built",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="shipped_truth_diff_macro",
        cross_feed_relation_state="present_not_measurement_conditioned",
        safe_use_level="lane_measurement_guarded",
        refusal_reasons=(
            "macro_release_calendar_archive_missing",
            "macro_vintagedates_superseded_value_ledger_missing",
            "lab_relation_edges_not_measurement_conditioned",
        ),
        next_gap_refs=(
            "macro_release_calendar_archive_v0",
            "fusion_readiness_gate_consumption_hooks_v0",
        ),
        sidecar_keys=("macro_lifecycle_snapshot",),
        evidence_refs=(
            "tools/macro/lifecycle.py",
            "tools/macro/macro.py",
            "tools/oracle/truth_diff_macro.py",
        ),
    ),
    LaneReadiness(
        lane_id="global_news_feed",
        source_authority_state="shipped",
        identity_state="half_built_article_url_only",
        lifecycle_state="half_built",
        measurement_evidence_state="shipped_article_rows",
        freshness_quality_state="half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="half_built_explanatory_truth_miner",
        cross_feed_relation_state="present_not_claim_cluster_conditioned",
        safe_use_level="feed_observation_only",
        refusal_reasons=(
            "news_claim_event_identity_missing",
            "correction_retraction_syndication_lifecycle_missing",
            "deterministic_claim_truth_diff_missing",
        ),
        next_gap_refs=("news_claim_event_identity_lifecycle_v0",),
        evidence_refs=("tools/news/news.py", "codex/nodes/oracle/oracle_truth_news.json"),
    ),
    LaneReadiness(
        lane_id="global_polymarket_feed",
        source_authority_state="shipped",
        identity_state="shipped",
        lifecycle_state="shipped",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="contracted_resolved_archive_candidate_sidecar_not_target_paired",
        cross_feed_relation_state="papered_blocked",
        safe_use_level="lane_measurement_guarded",
        refusal_reasons=(
            "polymarket_resolved_archive_target_pairing_missing",
            "target_alignment_relation_confidence_missing",
            "oracle_attach_consumes_candidates_but_no_deterministic_pairing_yet",
        ),
        next_gap_refs=(
            "polymarket_oracle_target_pairing_v0",
            "fusion_readiness_gate_consumption_hooks_v0",
        ),
        sidecar_keys=(
            "polymarket_market_identity_snapshot",
            "polymarket_clob_snapshot",
            "polymarket_resolved_archive_candidates",
        ),
        evidence_refs=(
            "tools/polymarket/identity.py",
            "tools/polymarket/lifecycle.py",
            "tools/polymarket/clob_snapshot.py",
            "tools/polymarket/resolved_archive.py",
            "codex/nodes/oracle/oracle_truth_poly.json",
        ),
    ),
    LaneReadiness(
        lane_id="global_stockgrid_feed",
        source_authority_state="shipped",
        identity_state="half_built_provider_ids_not_normalized",
        lifecycle_state="half_built",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="half_built_explanatory_truth_miner",
        cross_feed_relation_state="present_not_regime_conditioned",
        safe_use_level="feed_observation_only",
        refusal_reasons=(
            "stockgrid_provider_identity_normalization_missing",
            "sector_rotation_concentration_dispersion_lifecycle_missing",
            "deterministic_flow_truth_diff_missing",
        ),
        next_gap_refs=("stockgrid_regime_flow_lifecycle_v0",),
        evidence_refs=(
            "tools/stockgrid/stockgrid.py",
            "codex/nodes/oracle/oracle_truth_stockgrid.json",
        ),
    ),
    LaneReadiness(
        lane_id="global_calculator_feed",
        source_authority_state="shipped",
        identity_state="derived_from_upstream_rows",
        lifecycle_state="half_built_upstream_readiness_only",
        measurement_evidence_state="shipped",
        freshness_quality_state="shipped_half_built",
        provenance_as_of_state="shipped",
        oracle_attach_state="half_built_explanatory_truth_miner",
        cross_feed_relation_state="present_but_upstream_limited",
        safe_use_level="derived_observation_only",
        refusal_reasons=(
            "calculator_is_not_source_lane_root",
            "upstream_dependency_scope_stock_macro_etf_only",
            "proper_scoring_calibration_missing",
        ),
        next_gap_refs=("calculator_computed_state_lifecycle_v0",),
        evidence_refs=(
            "tools/calculator/calculator.py",
            "codex/nodes/oracle/oracle_truth_calc.json",
        ),
    ),
)


CANDIDATE_SITUATION_GATES: tuple[CandidateSituationGate, ...] = (
    CandidateSituationGate(
        situation_id="macro_event_x_equity_response",
        title="Macro event x equity response",
        attempted_claim="A macro event explains or validates an equity response.",
        lanes=("global_macro_feed", "global_stock_feed"),
        decision="refuse",
        safe_use_level="refuse_cross_feed_claim",
        refusal_reasons=(
            "macro_release_calendar_archive_missing",
            "equity_expected_return_event_window_missing",
            "cross_feed_relation_edges_not_measurement_conditioned",
        ),
        required_before_allowed=(
            "macro release timing and revision posture",
            "equity expected-return or event-window context",
            "measurement-conditioned Lab relation edge",
        ),
        evidence_refs=(
            "tools/macro/lifecycle.py",
            "tools/stock/lifecycle.py",
            "codex/nodes/lab/cross_corr_v2.json",
        ),
    ),
    CandidateSituationGate(
        situation_id="etf_price_move_x_nav_basket_claim",
        title="ETF price move x NAV/basket claim",
        attempted_claim="An ETF price move implies NAV, basket, creation/redemption, or rebalance pressure.",
        lanes=("global_etf_feed",),
        decision="refuse",
        safe_use_level="refuse_cross_feed_claim",
        refusal_reasons=(
            "etf_nav_provider_gap",
            "etf_basket_rebalance_provider_gap",
            "premium_discount_posture_unavailable_v0",
        ),
        required_before_allowed=(
            "NAV or premium-discount provider posture",
            "basket or creation/redemption evidence",
            "rebalance lifecycle evidence when the claim depends on rebalance timing",
        ),
        evidence_refs=("tools/stock/lifecycle.py",),
    ),
    CandidateSituationGate(
        situation_id="polymarket_expectation_x_macro_equity_situation",
        title="Polymarket expectation x macro/equity situation",
        attempted_claim="Prediction-market expectation diverges from or validates a macro/equity situation.",
        lanes=("global_polymarket_feed", "global_macro_feed", "global_stock_feed"),
        decision="refuse",
        safe_use_level="refuse_cross_feed_claim",
        refusal_reasons=(
            "polymarket_resolved_archive_target_pairing_missing",
            "target_alignment_relation_confidence_missing",
            "cross_feed_relation_edges_not_measurement_conditioned",
        ),
        required_before_allowed=(
            "Polymarket resolved-archive target pairing",
            "target-swarm identity alignment across lanes",
            "relation-edge confidence and Oracle attach status",
        ),
        evidence_refs=(
            "tools/polymarket/lifecycle.py",
            "tools/polymarket/clob_snapshot.py",
            "tools/polymarket/resolved_archive.py",
            "codex/nodes/oracle/oracle_truth_poly.json",
        ),
    ),
)


def _dict_rows(rows: Iterable[Any]) -> list[dict[str, Any]]:
    return [asdict(row) for row in rows]


def _count_by_safe_use(rows: Sequence[LaneReadiness]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in rows:
        counts[row.safe_use_level] = counts.get(row.safe_use_level, 0) + 1
    return dict(sorted(counts.items()))


def normalize_lane_id(lane: str) -> str:
    token = str(lane or "").strip()
    if not token:
        return ""
    if token.startswith("global_") and token.endswith("_feed"):
        return token
    return LANE_ALIASES.get(token.upper(), token)


def _normalize_lanes(lanes: Sequence[Any]) -> tuple[str, ...]:
    normalized = tuple(
        lane_id
        for lane_id in (normalize_lane_id(str(lane)) for lane in lanes)
        if lane_id
    )
    return tuple(dict.fromkeys(normalized))


def _candidate_gate_by_id(situation_id: str) -> CandidateSituationGate | None:
    normalized = str(situation_id or "").strip()
    if not normalized:
        return None
    for row in CANDIDATE_SITUATION_GATES:
        if row.situation_id == normalized:
            return row
    return None


def _candidate_gate_by_lanes(lanes: Sequence[str]) -> CandidateSituationGate | None:
    lane_set = set(_normalize_lanes(lanes))
    if not lane_set:
        return None
    for row in CANDIDATE_SITUATION_GATES:
        if set(row.lanes) == lane_set:
            return row
    return None


def preflight_candidate_situation(
    *,
    situation_id: str | None = None,
    lanes: Sequence[str] = (),
    attempted_claim: str = "",
    consumer_name: str = "unknown_consumer",
    claim_id: str | None = None,
) -> dict[str, Any]:
    """
    Evaluate a consumer's attempted cross-feed claim against the readiness gate.

    Unknown candidate situations fail closed until a gate row explicitly allows them.
    """

    gate = _candidate_gate_by_id(situation_id or "") or _candidate_gate_by_lanes(lanes)
    normalized_lanes = _normalize_lanes(lanes)
    if gate is None:
        preflight = ConsumerClaimPreflight(
            consumer_name=consumer_name,
            claim_id=claim_id or situation_id or "unknown_claim",
            situation_id=situation_id or "unknown_candidate_situation",
            attempted_claim=attempted_claim,
            lanes=normalized_lanes,
            decision="refuse",
            safe_use_level="refuse_cross_feed_claim",
            refusal_reasons=("candidate_situation_gate_missing",),
            required_before_allowed=(
                "add an explicit candidate situation gate row before emission",
            ),
        )
        return asdict(preflight)

    preflight = ConsumerClaimPreflight(
        consumer_name=consumer_name,
        claim_id=claim_id or gate.situation_id,
        situation_id=gate.situation_id,
        attempted_claim=attempted_claim or gate.attempted_claim,
        lanes=normalized_lanes or gate.lanes,
        decision=gate.decision,
        safe_use_level=gate.safe_use_level,
        refusal_reasons=gate.refusal_reasons,
        required_before_allowed=gate.required_before_allowed,
        evidence_refs=gate.evidence_refs,
    )
    return asdict(preflight)


def preflight_consumer_claims(
    claims_payload: Any,
    *,
    default_consumer_name: str = "unknown_consumer",
) -> list[dict[str, Any]]:
    """
    Preflight a consumer claim list without requiring the consumer to import dataclasses.

    Accepted payloads are either a list of claim dicts or a dict containing `claims`,
    `candidate_situation_claims`, or `cross_feed_claims`.
    """

    if isinstance(claims_payload, dict):
        consumer_name = str(
            claims_payload.get("consumer_name")
            or claims_payload.get("consumer")
            or default_consumer_name
        )
        raw_claims = (
            claims_payload.get("claims")
            or claims_payload.get("candidate_situation_claims")
            or claims_payload.get("cross_feed_claims")
            or []
        )
    else:
        consumer_name = default_consumer_name
        raw_claims = claims_payload

    if not isinstance(raw_claims, list):
        return [
            preflight_candidate_situation(
                situation_id="malformed_claim_payload",
                attempted_claim="malformed claim payload",
                consumer_name=consumer_name,
                claim_id="malformed_claim_payload",
            )
        ]

    preflights: list[dict[str, Any]] = []
    for index, claim in enumerate(raw_claims):
        if not isinstance(claim, dict):
            preflights.append(
                preflight_candidate_situation(
                    situation_id="malformed_claim",
                    attempted_claim="malformed claim",
                    consumer_name=consumer_name,
                    claim_id=f"claim_{index + 1}",
                )
            )
            continue
        claim_consumer = str(claim.get("consumer_name") or claim.get("consumer") or consumer_name)
        preflights.append(
            preflight_candidate_situation(
                situation_id=claim.get("situation_id"),
                lanes=claim.get("lanes") if isinstance(claim.get("lanes"), list) else (),
                attempted_claim=str(
                    claim.get("attempted_claim")
                    or claim.get("attempted_claim_class")
                    or ""
                ),
                consumer_name=claim_consumer,
                claim_id=str(claim.get("claim_id") or claim.get("id") or f"claim_{index + 1}"),
            )
        )
    return preflights


def build_readiness_gate() -> dict[str, Any]:
    """Build the deterministic readiness/refusal report."""

    lane_rows = LANE_READINESS
    candidate_rows = CANDIDATE_SITUATION_GATES
    return {
        "schema_version": SCHEMA_VERSION,
        "artifact_id": "cross_feed_measurement_readiness_gate_v0",
        "authority_boundary": {
            "projection_not_authority": True,
            "source_authority": "codex/doctrine/paper_modules/market_evidence_fusion_spine.md",
            "not_a_runtime_schema": "MarketEvidenceObject_not_built",
            "not_operator_facing_cards": True,
        },
        "source_surfaces": [
            "codex/doctrine/paper_modules/market_evidence_fusion_spine.md",
            "codex/doctrine/paper_modules/data_feed_lanes.md",
            "codex/doctrine/paper_modules/lab_oracle_evolve_pipeline.md",
            "codex/nodes/lab/cross_corr_v1.json",
            "codex/nodes/lab/cross_corr_v2.json",
            "codex/nodes/oracle/",
            "system/lib/feed_envelope.py",
            "system/lib/feed_quality.py",
        ],
        "sidecar_conventions": {
            "global_stock_feed": ["metadata.sidecars.equity_lifecycle_snapshot"],
            "global_etf_feed": ["metadata.sidecars.equity_lifecycle_snapshot"],
            "global_macro_feed": ["metadata.sidecars.macro_lifecycle_snapshot"],
            "global_polymarket_feed": [
                "metadata.sidecars.polymarket_market_identity_snapshot",
                "metadata.sidecars.polymarket_clob_snapshot",
                "metadata.sidecars.polymarket_resolved_archive_candidates",
            ],
        },
        "trust_level_definitions": {
            "feed_observation_only": "Feed rows may be inspected as observations, but not used for high-trust measurement interpretation or cross-feed claims.",
            "derived_observation_only": "Derived rows may be inspected as computations over upstream lanes, but do not establish source-lane authority.",
            "lane_measurement_guarded": "Lane-native identity/lifecycle/measurement evidence exists, but cross-feed situation claims still require relation and Oracle gates.",
            "refuse_cross_feed_claim": "The attempted claim collapses at least one required trust level and must be refused.",
        },
        "lane_readiness": _dict_rows(lane_rows),
        "candidate_situation_gates": _dict_rows(candidate_rows),
        "consumer_hook_state": {
            "lab_cross_corr_v1": {
                "path": "codex/nodes/lab/cross_corr_v1.json",
                "state": "prompt_surface_without_direct_measurement_readiness_gate",
                "required_before_cards": "consume lane_readiness and candidate_situation_gates before emitting actionable divergence cards",
            },
            "lab_cross_corr_v2": {
                "path": "codex/nodes/lab/cross_corr_v2.json",
                "state": "prompt_surface_without_direct_measurement_readiness_gate",
                "required_before_cards": "consume lane_readiness and candidate_situation_gates before emitting target-swarm claims",
            },
            "lab_contract_audit": {
                "path": "system/lib/lab_contract_audit.py",
                "state": "consumer_preflight_boundary",
                "required_before_cards": "candidate cross-feed claim artifacts or embedded candidate_situation_claims fail closed through the readiness gate",
            },
        },
        "summary": {
            "lane_count": len(lane_rows),
            "sidecar_mature_lane_count": sum(
                1 for row in lane_rows if row.safe_use_level == "lane_measurement_guarded"
            ),
            "safe_use_level_counts": _count_by_safe_use(lane_rows),
            "candidate_situation_count": len(candidate_rows),
            "candidate_refusal_count": sum(
                1 for row in candidate_rows if row.decision == "refuse"
            ),
            "production_divergence_cards_allowed": False,
            "market_evidence_object_built": False,
        },
    }


def render_report(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_readiness_gate(output_path: Path = DEFAULT_OUTPUT_PATH) -> dict[str, Any]:
    payload = build_readiness_gate()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_report(payload), encoding="utf-8")
    return payload
