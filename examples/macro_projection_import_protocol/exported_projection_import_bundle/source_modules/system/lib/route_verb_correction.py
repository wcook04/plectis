from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def extract_verb_correction_pairs(
    prior_route_edges: list[Any],
    baseline_edges: list[Any],
    route_universe: set[str],
) -> list[dict[str, Any]]:
    """Extract pairs from a prior run that match baseline (correct source→target pairs).

    Returns prior_route_edges entries whose (source, target) appears in the baseline,
    filtered to route_universe. Used to build a verb-correction prompt that asks only
    for connector_verb on already-confirmed directed pairs.

    The returned dicts preserve the prior run's evidence_set and prior connector_verb
    so the verb-correction prompt can show both to the LLM judge.
    """
    baseline_pairs: set[tuple[str, str]] = {
        (str(edge.get("source")), str(edge.get("target")))
        for edge in baseline_edges
        if isinstance(edge, Mapping)
        and str(edge.get("source")) in route_universe
        and str(edge.get("target")) in route_universe
    }
    return [
        dict(edge)
        for edge in prior_route_edges
        if isinstance(edge, Mapping)
        and (str(edge.get("source")), str(edge.get("target"))) in baseline_pairs
    ]
