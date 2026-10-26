"""
[PURPOSE]
- Teleology: Capture a typed identity packet over the FULL raw Gamma market universe
  BEFORE any scanner kill-list / volume / liquidity / malformed / zombie / resolved /
  topicless gate runs, so a future measurement substrate (CLOB enrichment, resolved-
  market archive into Oracle, calibration) is fed evidence that does not inherit the
  scanner's interpretive selection bias.
- Mechanism: Walk events -> markets with the same iter shape `normalize_events` uses,
  decode the load-bearing identity fields (conditionId, clobTokenIds, outcomes,
  outcomePrices, enableOrderBook, feesEnabled, negRisk, negRiskMarketID, tickSize,
  endDate, resolutionSource, raw status flags) without applying any filter, then emit
  one PolymarketMarketIdentity row per raw market plus aggregate diagnostics.

[INTERFACE]
- `PolymarketMarketIdentity` — frozen dataclass; one row per raw Gamma market.
- `extract_market_identities(events) -> List[PolymarketMarketIdentity]`.
- `build_identity_snapshot(rows, *, max_embedded_rows=1000) -> Dict[str, Any]` — typed
  sidecar payload with schema_version, row_count, diagnostics block, sample/full rows.

[CONSTRAINTS]
- Substrate-only: no scanner logic, no kill-list, no topic routing, no scoring.
- Read-only: never mutates the event payloads it walks.
- Resilient: never raises on missing fields; missing -> identity row carries None and
  the snapshot's identity_field_presence aggregate counts it.
- Selection-bias safety: the row set MUST cover markets the scanner would drop
  (kill-list, low volume, zombie, resolved, malformed, topicless). That is the whole
  point of running this before normalize_events.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


_LOAD_BEARING_FIELDS: Tuple[str, ...] = (
    "condition_id",
    "clob_token_ids",
    "outcomes",
    "outcome_prices",
    "enable_order_book",
    "fees_enabled",
    "neg_risk",
    "tick_size",
    "end_date_iso",
    "resolution_source",
)


def _as_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "y", "on"}:
            return True
        if lowered in {"0", "false", "no", "n", "off"}:
            return False
    return None


def _parse_listish(value: Any) -> Optional[List[Any]]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except Exception:
            return None
        return list(parsed) if isinstance(parsed, list) else None
    return None


def _parse_float_list(value: Any) -> Optional[List[float]]:
    raw = _parse_listish(value)
    if raw is None:
        return None
    floats: List[float] = []
    for item in raw:
        try:
            floats.append(float(item))
        except (TypeError, ValueError):
            return None
    return floats


def _safe_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _tag_slugs(*blocks: Any) -> Tuple[str, ...]:
    seen: set = set()
    out: List[str] = []
    for block in blocks:
        if not isinstance(block, list):
            continue
        for tag in block:
            if isinstance(tag, dict):
                slug = tag.get("slug") or tag.get("name") or tag.get("label")
            else:
                slug = tag
            text = _as_str(slug)
            if not text:
                continue
            text = text.lower()
            if text in seen:
                continue
            seen.add(text)
            out.append(text)
    return tuple(out)


@dataclass(frozen=True)
class PolymarketMarketIdentity:
    """Raw identity packet per Gamma market — no scanner filters applied.

    The set of fields tracks what a measurement substrate needs to (a) route to a
    CLOB endpoint by stable id, (b) preserve resolved-market evidence for the
    calibration archive, and (c) audit which categories the downstream scanner is
    dropping and why.
    """

    # Event context
    event_id: Optional[str]
    event_slug: Optional[str]
    event_title: Optional[str]
    event_tag_slugs: Tuple[str, ...]

    # Market identity
    market_id: Optional[str]
    market_slug: Optional[str]
    market_question: Optional[str]
    market_tag_slugs: Tuple[str, ...]

    # CLOB routing identity
    condition_id: Optional[str]
    clob_token_ids: Optional[Tuple[str, ...]]

    # Outcome surface
    outcomes: Optional[Tuple[str, ...]]
    outcome_prices: Optional[Tuple[float, ...]]
    outcome_pair_count: int  # number of (label, parseable price) pairs

    # CLOB eligibility + fee posture
    enable_order_book: Optional[bool]
    fees_enabled: Optional[bool]
    accepting_orders: Optional[bool]

    # Neg-risk posture
    neg_risk: Optional[bool]
    neg_risk_market_id: Optional[str]

    # Microstructure-adjacent metadata
    tick_size: Optional[float]
    end_date_iso: Optional[str]
    resolution_source: Optional[str]

    # Raw status (no normalization; substrate keeps them all)
    raw_status_active: Optional[bool]
    raw_status_closed: Optional[bool]
    raw_status_resolved: Optional[bool]
    raw_status_archived: Optional[bool]

    # Observed magnitudes (raw, not gated)
    volume_24h: Optional[float]
    volume_total: Optional[float]
    liquidity: Optional[float]
    one_day_price_change: Optional[float]


def _iter_event_markets(event: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    markets = event.get("markets")
    if isinstance(markets, list):
        for market in markets:
            if isinstance(market, dict):
                yield market
        return
    if any(key in event for key in ("question", "outcomes", "outcomePrices")):
        yield event


def _identity_from_market(event: Dict[str, Any], market: Dict[str, Any]) -> PolymarketMarketIdentity:
    event_tags = _tag_slugs(event.get("tags"), event.get("categories"))
    market_tags = _tag_slugs(market.get("tags"), market.get("categories"))

    outcomes_raw = _parse_listish(market.get("outcomes"))
    outcomes_tuple: Optional[Tuple[str, ...]] = None
    if outcomes_raw is not None:
        outcomes_tuple = tuple(str(o) for o in outcomes_raw if o is not None)

    prices_raw = _parse_float_list(market.get("outcomePrices"))
    prices_tuple: Optional[Tuple[float, ...]] = tuple(prices_raw) if prices_raw is not None else None

    pair_count = 0
    if outcomes_tuple is not None and prices_tuple is not None:
        pair_count = min(len(outcomes_tuple), len(prices_tuple))

    token_ids_raw = _parse_listish(
        market.get("clobTokenIds") or market.get("clob_token_ids")
    )
    if token_ids_raw is None and market.get("clobTokenId") is not None:
        # Singular-form fallback (rare; Gamma usually emits the list)
        token_ids_raw = [market.get("clobTokenId")]
    token_ids_tuple: Optional[Tuple[str, ...]] = (
        tuple(str(t) for t in token_ids_raw if t is not None) if token_ids_raw is not None else None
    )

    return PolymarketMarketIdentity(
        event_id=_as_str(event.get("id")),
        event_slug=_as_str(event.get("slug")),
        event_title=_as_str(event.get("title") or event.get("name")),
        event_tag_slugs=event_tags,
        market_id=_as_str(market.get("id")),
        market_slug=_as_str(market.get("slug") or market.get("market_slug")),
        market_question=_as_str(market.get("question") or market.get("title")),
        market_tag_slugs=market_tags,
        condition_id=_as_str(market.get("conditionId") or market.get("condition_id")),
        clob_token_ids=token_ids_tuple,
        outcomes=outcomes_tuple,
        outcome_prices=prices_tuple,
        outcome_pair_count=pair_count,
        enable_order_book=_as_bool(market.get("enableOrderBook")),
        fees_enabled=_as_bool(market.get("feesEnabled")),
        accepting_orders=_as_bool(market.get("acceptingOrders")),
        neg_risk=_as_bool(market.get("negRisk")),
        neg_risk_market_id=_as_str(market.get("negRiskMarketID")),
        tick_size=_safe_float(market.get("tickSize") or market.get("orderPriceMinTickSize")),
        end_date_iso=_as_str(market.get("endDate") or market.get("end_date_iso")),
        resolution_source=_as_str(market.get("resolutionSource") or market.get("resolution_source")),
        raw_status_active=_as_bool(market.get("active")),
        raw_status_closed=_as_bool(market.get("closed") or event.get("closed")),
        raw_status_resolved=_as_bool(market.get("resolved") or market.get("isResolved") or event.get("resolved")),
        raw_status_archived=_as_bool(market.get("archived") or event.get("archived")),
        volume_24h=_safe_float(market.get("volume24hr")),
        volume_total=_safe_float(market.get("volume")),
        liquidity=_safe_float(
            market.get("liquidityClob", market.get("liquidityNum", market.get("liquidity")))
        ),
        one_day_price_change=_safe_float(
            market.get("oneDayPriceChange", market.get("priceChange24hr", market.get("price_change_24hr")))
        ),
    )


def extract_market_identities(events: Sequence[Dict[str, Any]]) -> List[PolymarketMarketIdentity]:
    """Walk events -> markets and emit one identity row per raw market.

    Applies zero scanner filters. Substrate-only.
    """
    rows: List[PolymarketMarketIdentity] = []
    for event in events:
        if not isinstance(event, dict):
            continue
        for market in _iter_event_markets(event):
            rows.append(_identity_from_market(event, market))
    return rows


def _tri_state_distribution(rows: Sequence[PolymarketMarketIdentity], attr: str) -> Dict[str, int]:
    dist = {"true": 0, "false": 0, "null": 0}
    for row in rows:
        value = getattr(row, attr)
        if value is True:
            dist["true"] += 1
        elif value is False:
            dist["false"] += 1
        else:
            dist["null"] += 1
    return dist


def _identity_field_presence(rows: Sequence[PolymarketMarketIdentity]) -> Dict[str, int]:
    presence: Dict[str, int] = {field: 0 for field in _LOAD_BEARING_FIELDS}
    for row in rows:
        if row.condition_id:
            presence["condition_id"] += 1
        if row.clob_token_ids:
            presence["clob_token_ids"] += 1
        if row.outcomes:
            presence["outcomes"] += 1
        if row.outcome_prices is not None:
            presence["outcome_prices"] += 1
        if row.enable_order_book is not None:
            presence["enable_order_book"] += 1
        if row.fees_enabled is not None:
            presence["fees_enabled"] += 1
        if row.neg_risk is not None:
            presence["neg_risk"] += 1
        if row.tick_size is not None:
            presence["tick_size"] += 1
        if row.end_date_iso:
            presence["end_date_iso"] += 1
        if row.resolution_source:
            presence["resolution_source"] += 1
    return presence


def _raw_status_breakdown(rows: Sequence[PolymarketMarketIdentity]) -> Dict[str, int]:
    """Mutually-non-exclusive raw status counts plus a multi-flag and unflagged bucket."""
    breakdown = {
        "active_true": 0,
        "closed_true": 0,
        "resolved_true": 0,
        "archived_true": 0,
        "multi_state_flagged": 0,
        "no_state_flagged": 0,
    }
    for row in rows:
        flags = [
            row.raw_status_active is True,
            row.raw_status_closed is True,
            row.raw_status_resolved is True,
            row.raw_status_archived is True,
        ]
        if row.raw_status_active is True:
            breakdown["active_true"] += 1
        if row.raw_status_closed is True:
            breakdown["closed_true"] += 1
        if row.raw_status_resolved is True:
            breakdown["resolved_true"] += 1
        if row.raw_status_archived is True:
            breakdown["archived_true"] += 1
        if sum(flags) > 1:
            breakdown["multi_state_flagged"] += 1
        if sum(flags) == 0:
            breakdown["no_state_flagged"] += 1
    return breakdown


def _event_count(rows: Sequence[PolymarketMarketIdentity]) -> int:
    seen: set = set()
    for row in rows:
        key = row.event_id or row.event_slug
        if key:
            seen.add(key)
    return len(seen)


def _row_to_dict(row: PolymarketMarketIdentity) -> Dict[str, Any]:
    payload = asdict(row)
    # Tuples -> lists for JSON friendliness
    for key in ("event_tag_slugs", "market_tag_slugs", "clob_token_ids", "outcomes", "outcome_prices"):
        value = payload.get(key)
        if isinstance(value, tuple):
            payload[key] = list(value)
    return payload


def build_identity_snapshot(
    rows: Sequence[PolymarketMarketIdentity],
    *,
    max_embedded_rows: int = 1000,
    lifecycle_classifications: Optional[Sequence[Any]] = None,
) -> Dict[str, Any]:
    """Typed identity-snapshot sidecar payload.

    Rows are embedded up to `max_embedded_rows`. If the raw count exceeds that, the
    payload sets `rows_truncated=True` and `embedded_row_count` < `row_count`. A
    later wave will graduate rows to a separate run-artifact file; this v0 stays
    self-contained inside the envelope's metadata.

    When `lifecycle_classifications` is provided (parallel to `rows`), each embedded
    row carries a `lifecycle` block with state/confidence/components/conflicts, and
    the snapshot diagnostics carry `lifecycle_state_distribution` over the FULL row
    universe (not just the embedded subset).
    """
    row_count = len(rows)
    embed_count = min(row_count, max_embedded_rows)

    if lifecycle_classifications is not None and len(lifecycle_classifications) != row_count:
        raise ValueError(
            "lifecycle_classifications length ("
            f"{len(lifecycle_classifications)}) must match identity row count ({row_count}). "
            "Both must come from the same extract_market_identities call to preserve order."
        )

    embedded_rows: List[Dict[str, Any]] = []
    for i in range(embed_count):
        row_dict = _row_to_dict(rows[i])
        if lifecycle_classifications is not None:
            cls = lifecycle_classifications[i]
            row_dict["lifecycle"] = {
                "state": cls.state,
                "confidence": cls.confidence,
                "components": cls.components,
                "conflicts": list(cls.conflicts),
            }
        embedded_rows.append(row_dict)

    diagnostics: Dict[str, Any] = {
        "raw_market_count": row_count,
        "raw_event_count": _event_count(rows),
        "identity_field_presence": _identity_field_presence(rows),
        "enable_order_book_distribution": _tri_state_distribution(rows, "enable_order_book"),
        "fees_enabled_distribution": _tri_state_distribution(rows, "fees_enabled"),
        "neg_risk_distribution": _tri_state_distribution(rows, "neg_risk"),
        "accepting_orders_distribution": _tri_state_distribution(rows, "accepting_orders"),
        "raw_status_breakdown": _raw_status_breakdown(rows),
        "clob_eligible_count": sum(1 for r in rows if r.enable_order_book is True),
        "clob_ineligible_count": sum(1 for r in rows if r.enable_order_book is False),
        "outcome_pair_parseable_count": sum(1 for r in rows if r.outcome_pair_count >= 2),
        "rows_truncated": embed_count < row_count,
        "embedded_row_count": embed_count,
    }

    if lifecycle_classifications is not None:
        from tools.polymarket.lifecycle import build_lifecycle_distribution

        diagnostics["lifecycle_state_distribution"] = build_lifecycle_distribution(
            lifecycle_classifications
        )

    return {
        "schema_version": "polymarket_market_identity_snapshot.0",
        "purpose": (
            "Pre-normalization identity packet over the FULL raw Gamma market universe. "
            "Substrate root for the polymarket_intelligence_spine measurement substrate; "
            "consumed by the (not-yet-built) CLOB snapshot sidecar and the resolved-market "
            "archive that feeds Oracle's hindsight engine."
        ),
        "row_count": row_count,
        "diagnostics": diagnostics,
        "rows": embedded_rows,
    }


def empty_identity_snapshot() -> Dict[str, Any]:
    """Stable empty sidecar shape for the failure envelope path."""
    return build_identity_snapshot([])
