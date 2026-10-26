"""
[PURPOSE]
- Teleology: Classify each pre-normalization PolymarketMarketIdentity row into a
  bet lifecycle state (DISCOVERY / OPEN_* / INFORMATION_SHOCK / CLOSING_WINDOW /
  EVENT_PASSED_UNRESOLVED / DE_FACTO_TERMINAL / FORMALLY_RESOLVED /
  ARCHIVED_OR_STALE / DATA_CONFLICT) so the CLOB enrichment lane, calibration
  layer, and divergence cards see lifecycle state, not raw flag salad. Operator
  reframe (2026-05-12): no_clob_book_published on a top-volume past-end
  rail-pinned market is a terminal-lifecycle signature, not a measurement
  failure.
- Mechanism: Single-shot classifier per (identity_row, as_of) computing the
  continuous components (past_end, time_to_end_seconds, railness, entropy,
  abs_one_day_change, status_conflict_kind), then collapsing through a
  priority-ordered rule cascade into one of ten typed states. Components are
  retained so calibration can later learn thresholds instead of inheriting v0
  heuristics.

[INTERFACE]
- `LIFECYCLE_STATES` — canonical ordered tuple of the 10 states.
- `CLOB_ENRICHMENT_ELIGIBLE_STATES` — frozenset of states where CLOB book
  publication is EXPECTED (OPEN_LIQUID/OPEN_THIN/INFORMATION_SHOCK/
  CLOSING_WINDOW). For other states, no_clob_book_published is the expected
  observation and CLOB enrichment should skip.
- `LifecycleClassification` — frozen dataclass: state, confidence, components,
  conflicts.
- `LifecycleOptions` — frozen dataclass: closing_window_seconds (24h default),
  information_shock_threshold (|Δp| 0.10 default), de_facto_rail_threshold
  (0.96 default), open_liquid_min_volume_24h (5000 default).
- `hydrate_lifecycle_options(raw_cfg)` — reads `lifecycle` block.
- `classify_lifecycle(row, *, as_of_iso, options)` — returns one
  LifecycleClassification.
- `classify_all_lifecycles(rows, *, as_of_iso, options)` — convenience wrapper.
- `build_lifecycle_distribution(classifications)` — aggregate count by state.

[CONSTRAINTS]
- Substrate-only: never mutates identity rows; never makes HTTP calls.
- Deterministic: same (row, as_of, options) -> same classification.
- Component-preserving: records WHY a row was labelled so the calibration layer
  can learn thresholds without re-deriving identity evidence.
- Priority-ordered: rule cascade is the canonical order; ties never silently
  break.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from tools.polymarket.identity import PolymarketMarketIdentity


LIFECYCLE_STATES: Tuple[str, ...] = (
    "DISCOVERY",
    "OPEN_THIN",
    "OPEN_LIQUID",
    "INFORMATION_SHOCK",
    "CLOSING_WINDOW",
    "EVENT_PASSED_UNRESOLVED",
    "DE_FACTO_TERMINAL",
    "FORMALLY_RESOLVED",
    "ARCHIVED_OR_STALE",
    "DATA_CONFLICT",
)


# States where a CLOB orderbook publication is EXPECTED. For any other state,
# no_clob_book_published is the expected observation; CLOB enrichment can skip.
CLOB_ENRICHMENT_ELIGIBLE_STATES: frozenset = frozenset(
    {"OPEN_LIQUID", "OPEN_THIN", "INFORMATION_SHOCK", "CLOSING_WINDOW"}
)


@dataclass(frozen=True)
class LifecycleClassification:
    state: str
    confidence: float
    components: Dict[str, Any]
    conflicts: Tuple[str, ...]


@dataclass(frozen=True)
class LifecycleOptions:
    closing_window_seconds: float
    information_shock_threshold: float
    de_facto_rail_threshold: float
    open_liquid_min_volume_24h: float


DEFAULT_LIFECYCLE_OPTIONS = LifecycleOptions(
    closing_window_seconds=24 * 3600.0,
    information_shock_threshold=0.10,
    de_facto_rail_threshold=0.96,
    open_liquid_min_volume_24h=5000.0,
)


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def hydrate_lifecycle_options(raw_cfg: Any) -> LifecycleOptions:
    block: Dict[str, Any] = {}
    if isinstance(raw_cfg, dict):
        candidate = raw_cfg.get("lifecycle")
        if isinstance(candidate, dict):
            block = candidate
    return LifecycleOptions(
        closing_window_seconds=max(
            0.0,
            _safe_float(
                block.get("closing_window_seconds"),
                DEFAULT_LIFECYCLE_OPTIONS.closing_window_seconds,
            ),
        ),
        information_shock_threshold=max(
            0.0,
            _safe_float(
                block.get("information_shock_threshold"),
                DEFAULT_LIFECYCLE_OPTIONS.information_shock_threshold,
            ),
        ),
        de_facto_rail_threshold=max(
            0.0,
            min(
                1.0,
                _safe_float(
                    block.get("de_facto_rail_threshold"),
                    DEFAULT_LIFECYCLE_OPTIONS.de_facto_rail_threshold,
                ),
            ),
        ),
        open_liquid_min_volume_24h=max(
            0.0,
            _safe_float(
                block.get("open_liquid_min_volume_24h"),
                DEFAULT_LIFECYCLE_OPTIONS.open_liquid_min_volume_24h,
            ),
        ),
    )


def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _top_probability(row: PolymarketMarketIdentity) -> Optional[float]:
    if not row.outcome_prices:
        return None
    candidate = max(row.outcome_prices)
    if not (0.0 <= candidate <= 1.0):
        return None
    return float(candidate)


def _components(
    row: PolymarketMarketIdentity,
    *,
    now: Optional[datetime],
) -> Dict[str, Any]:
    end_dt = _parse_iso(row.end_date_iso)
    if now is not None and end_dt is not None:
        time_to_end_seconds: Optional[float] = (end_dt - now).total_seconds()
        past_end = time_to_end_seconds < 0
    else:
        time_to_end_seconds = None
        past_end = False

    p_top = _top_probability(row)
    railness = abs(p_top - 0.5) * 2.0 if p_top is not None else None
    entropy = 1.0 - railness if railness is not None else None
    abs_change = abs(row.one_day_price_change) if row.one_day_price_change is not None else None

    return {
        "past_end": past_end,
        "time_to_end_seconds": time_to_end_seconds,
        "p_top": p_top,
        "railness": railness,
        "entropy": entropy,
        "abs_one_day_change": abs_change,
        "volume_24h": row.volume_24h,
        "accepting_orders": row.accepting_orders,
        "enable_order_book": row.enable_order_book,
        "raw_status_active": row.raw_status_active,
        "raw_status_closed": row.raw_status_closed,
        "raw_status_resolved": row.raw_status_resolved,
        "raw_status_archived": row.raw_status_archived,
        "has_condition_id": bool(row.condition_id),
        "has_token_ids": bool(row.clob_token_ids),
        "outcome_pair_count": row.outcome_pair_count,
    }


def _detect_conflicts(components: Dict[str, Any]) -> List[str]:
    out: List[str] = []
    if components["raw_status_active"] is True and components["raw_status_closed"] is True:
        out.append("active_and_closed_simultaneously")
    if components["raw_status_active"] is True and components["raw_status_archived"] is True:
        out.append("active_and_archived_simultaneously")
    if components["past_end"] is True and components["accepting_orders"] is True:
        out.append("past_end_but_still_accepting_orders")
    if components["raw_status_resolved"] is True and components["raw_status_active"] is True:
        out.append("resolved_and_active_simultaneously")
    return out


def _has_terminal_outcome_evidence(components: Dict[str, Any]) -> bool:
    """Closed=True AND the probability has rail-priced (one side near 0 or 1)."""
    if components["raw_status_closed"] is not True:
        return False
    railness = components.get("railness")
    return isinstance(railness, float) and railness >= 0.96


def classify_lifecycle(
    row: PolymarketMarketIdentity,
    *,
    as_of_iso: str,
    options: LifecycleOptions = DEFAULT_LIFECYCLE_OPTIONS,
) -> LifecycleClassification:
    """Single-shot lifecycle classification for one identity row.

    Priority-ordered cascade. Identity gates first, then explicit-terminal
    signals, then past-end variants, then in-flight refinements.
    """
    now = _parse_iso(as_of_iso)
    components = _components(row, now=now)
    conflicts = tuple(_detect_conflicts(components))

    has_identity = (
        components["has_condition_id"]
        and components["has_token_ids"]
        and components["outcome_pair_count"] >= 2
    )

    # 1. Missing identity → DISCOVERY (cannot classify further).
    if not has_identity:
        return LifecycleClassification(
            state="DISCOVERY",
            confidence=0.95,
            components=components,
            conflicts=conflicts,
        )

    # 2. Archived → terminal historical state.
    if components["raw_status_archived"] is True:
        return LifecycleClassification(
            state="ARCHIVED_OR_STALE",
            confidence=0.95,
            components=components,
            conflicts=conflicts,
        )

    # 3. Formally resolved → closed flag + rail-priced outcome.
    if _has_terminal_outcome_evidence(components):
        return LifecycleClassification(
            state="FORMALLY_RESOLVED",
            confidence=0.90,
            components=components,
            conflicts=conflicts,
        )

    # 4. De-facto terminal → past end date + rail pricing + not accepting orders.
    railness = components.get("railness")
    if (
        components["past_end"]
        and isinstance(railness, float)
        and railness >= options.de_facto_rail_threshold
        and components["accepting_orders"] is not True
    ):
        return LifecycleClassification(
            state="DE_FACTO_TERMINAL",
            confidence=0.85,
            components=components,
            conflicts=conflicts,
        )

    # 5. Event passed but not yet terminal-confirmed.
    if components["past_end"]:
        # If accepting orders is still True, that's a data conflict; surface it
        # rather than label as benign event-passed.
        if components["accepting_orders"] is True:
            return LifecycleClassification(
                state="DATA_CONFLICT",
                confidence=0.80,
                components=components,
                conflicts=conflicts,
            )
        return LifecycleClassification(
            state="EVENT_PASSED_UNRESOLVED",
            confidence=0.75,
            components=components,
            conflicts=conflicts,
        )

    # 6. Active+closed contradiction.
    if "active_and_closed_simultaneously" in conflicts:
        return LifecycleClassification(
            state="DATA_CONFLICT",
            confidence=0.85,
            components=components,
            conflicts=conflicts,
        )

    # 7. Closing window (event imminent and still accepting orders).
    time_to_end = components.get("time_to_end_seconds")
    if (
        isinstance(time_to_end, (int, float))
        and 0 <= time_to_end <= options.closing_window_seconds
        and components["accepting_orders"] is True
    ):
        return LifecycleClassification(
            state="CLOSING_WINDOW",
            confidence=0.75,
            components=components,
            conflicts=conflicts,
        )

    # 8. Information shock (large recent move; not past end).
    abs_change = components.get("abs_one_day_change")
    if (
        isinstance(abs_change, float)
        and abs_change >= options.information_shock_threshold
        and components["accepting_orders"] is not False
    ):
        return LifecycleClassification(
            state="INFORMATION_SHOCK",
            confidence=0.65,
            components=components,
            conflicts=conflicts,
        )

    # 9. Open and liquid (accepting orders + two-sided pricing + meaningful volume).
    if components["accepting_orders"] is True:
        volume = components.get("volume_24h") or 0.0
        if (
            volume >= options.open_liquid_min_volume_24h
            and isinstance(railness, float)
            and railness < 0.95
        ):
            return LifecycleClassification(
                state="OPEN_LIQUID",
                confidence=0.70,
                components=components,
                conflicts=conflicts,
            )
        return LifecycleClassification(
            state="OPEN_THIN",
            confidence=0.60,
            components=components,
            conflicts=conflicts,
        )

    # 10. Fallthrough: identity exists but no clear signal → DISCOVERY.
    return LifecycleClassification(
        state="DISCOVERY",
        confidence=0.40,
        components=components,
        conflicts=conflicts,
    )


def classify_all_lifecycles(
    rows: Sequence[PolymarketMarketIdentity],
    *,
    as_of_iso: str,
    options: LifecycleOptions = DEFAULT_LIFECYCLE_OPTIONS,
) -> List[LifecycleClassification]:
    return [classify_lifecycle(row, as_of_iso=as_of_iso, options=options) for row in rows]


def build_lifecycle_distribution(
    classifications: Sequence[LifecycleClassification],
) -> Dict[str, int]:
    """Count of classifications per state. All states included with zero counts."""
    out: Dict[str, int] = {state: 0 for state in LIFECYCLE_STATES}
    for cls in classifications:
        out[cls.state] = out.get(cls.state, 0) + 1
    return out


def is_clob_eligible(state: str) -> bool:
    return state in CLOB_ENRICHMENT_ELIGIBLE_STATES
