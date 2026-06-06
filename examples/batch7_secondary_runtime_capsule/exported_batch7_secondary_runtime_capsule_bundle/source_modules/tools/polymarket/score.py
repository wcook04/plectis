"""
[PURPOSE]
- Teleology: Apply the Polymarket scanner's four-lens scoring model to normalized market rows.
- Mechanism: Reuse the existing Hot Seat / Newsbreaker / God Mode / Scout physics with stricter resolved and zombie gating.
"""

from __future__ import annotations

import math
from typing import Any, Dict

from tools.polymarket.models import NormalizedMarket


def _num(value: Any, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def calculate_lenses(market: NormalizedMarket, tuning: Dict[str, Any]) -> Dict[str, float]:
    p = market.p
    vol = market.v
    chg = abs(market.c)
    uncertainty = max(0.0, 1.0 - abs(p - 0.5) * 2.0)

    hot = math.log10(vol) * uncertainty if vol > 10 else 0.0

    zombie_cfg = tuning.get("zombie", {}) if isinstance(tuning.get("zombie"), dict) else {}
    news_cfg = tuning.get("newsbreaker", {}) if isinstance(tuning.get("newsbreaker"), dict) else {}
    god_cfg = tuning.get("god_mode", {}) if isinstance(tuning.get("god_mode"), dict) else {}
    scout_cfg = tuning.get("scout", {}) if isinstance(tuning.get("scout"), dict) else {}

    is_zombie = market.p >= _num(zombie_cfg.get("price_floor"), 0.95) and chg <= _num(
        zombie_cfg.get("max_velocity"), 0.015
    )
    resolved_ceiling = _num(news_cfg.get("resolved_ceiling"), 0.95)
    resolved_floor = _num(news_cfg.get("resolved_floor"), 0.05)
    min_volume = _num(news_cfg.get("min_volume"), 0.0)
    min_uncertainty = _num(news_cfg.get("min_uncertainty"), 0.0)
    max_abs_change = _num(news_cfg.get("max_abs_change"), 1.0)
    uncertainty_power = max(0.0, _num(news_cfg.get("uncertainty_power"), 0.0))

    is_resolved = market.status == "resolved" or p >= resolved_ceiling or p <= resolved_floor
    is_low_volume = vol < min_volume
    is_low_uncertainty = uncertainty < min_uncertainty
    is_outlier_velocity = chg > max_abs_change

    if is_zombie or is_resolved or is_low_volume or is_low_uncertainty or is_outlier_velocity:
        news = 0.0
    else:
        news = vol * chg
        if uncertainty_power > 0:
            news *= uncertainty**uncertainty_power

    god = (
        vol * chg
        if _num(god_cfg.get("min_price"), 0.2) <= p <= _num(god_cfg.get("max_price"), 0.8)
        else 0.0
    )
    scout = vol * uncertainty if vol < _num(scout_cfg.get("max_volume"), 50000.0) else 0.0

    return {
        "HOT SEAT": hot,
        "NEWSBREAKER": news,
        "GOD MODE": god,
        "SCOUT": scout,
    }
