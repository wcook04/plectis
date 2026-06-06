"""
[PURPOSE]
- Teleology: Name the internal Polymarket scanner packets so fetch, normalization, scoring, and emission pass structured data instead of loose dicts.
- Mechanism: Dataclasses for normalized event context and normalized market rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Tuple


@dataclass(frozen=True)
class EventContext:
    title: str
    slug: str
    tags: Tuple[str, ...]
    text_blob: str


@dataclass
class NormalizedMarket:
    q: str
    o: str
    p: float
    c: float
    v: float
    s: float
    slug: str
    topic: str
    status: str
    liquidity: float
    event_title: str
    event_slug: str
    market_id: str
    market_slug: str
    scores: Dict[str, float] = field(default_factory=dict)
