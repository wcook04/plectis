"""
Rank route candidates with lightweight graph propagation.

[PURPOSE]
- Teleology: Add a graph-native candidate surfacing lane before asking a route
  judge to classify edge truth or verb.
- Mechanism: Build a small weighted graph from deterministic relation cards,
  accepted/proposed route ledgers, and run Personalized PageRank from each
  source node.
- Non-goal: This module does not decide route truth, connector verbs, or graph
  promotion. Scores are attention hints only.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, Mapping):
            rows.append(dict(payload))
    return rows


def _add_edge(
    graph: dict[str, dict[str, float]],
    source: str,
    target: str,
    weight: float,
    *,
    bidirectional_backoff: float = 0.0,
) -> None:
    if not source or not target or source == target or weight <= 0:
        return
    graph[source][target] = graph[source].get(target, 0.0) + weight
    if bidirectional_backoff > 0:
        graph[target][source] = graph[target].get(source, 0.0) + (weight * bidirectional_backoff)


def build_route_candidate_graph(
    node_cards: Sequence[Mapping[str, Any]],
    deterministic_pairs: Sequence[Mapping[str, Any]],
    *,
    accepted_edges_path: Path | None = None,
    proposed_edges_path: Path | None = None,
) -> dict[str, dict[str, float]]:
    graph: dict[str, dict[str, float]] = defaultdict(dict)
    known_paths = {str(card.get("path")) for card in node_cards if card.get("path")}
    for path in known_paths:
        graph[path] = graph.get(path, {})

    for pair in deterministic_pairs:
        source = str(pair.get("source") or "")
        target = str(pair.get("target") or "")
        if source not in known_paths or target not in known_paths:
            continue
        score = float(pair.get("deterministic_score") or 0.0)
        if score <= 0:
            continue
        weight = min(4.0, 0.4 + score)
        _add_edge(graph, source, target, weight, bidirectional_backoff=0.15)

    for row in _read_jsonl(accepted_edges_path) if accepted_edges_path else []:
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        if source in known_paths and target in known_paths:
            _add_edge(graph, source, target, 5.0, bidirectional_backoff=0.25)

    for row in _read_jsonl(proposed_edges_path) if proposed_edges_path else []:
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        if source in known_paths and target in known_paths:
            status = str(row.get("status") or "")
            weight = 1.2 if status == "pending_confirmation" else 0.7
            _add_edge(graph, source, target, weight, bidirectional_backoff=0.1)

    return {source: dict(targets) for source, targets in graph.items()}


def personalized_pagerank(
    graph: Mapping[str, Mapping[str, float]],
    source: str,
    *,
    alpha: float = 0.85,
    max_iter: int = 40,
    tolerance: float = 1e-8,
) -> dict[str, float]:
    nodes = sorted(set(graph.keys()) | {target for edges in graph.values() for target in edges})
    if source not in nodes:
        return {}
    ranks = {node: 0.0 for node in nodes}
    ranks[source] = 1.0
    teleport = {node: (1.0 if node == source else 0.0) for node in nodes}

    for _ in range(max_iter):
        next_ranks = {node: (1.0 - alpha) * teleport[node] for node in nodes}
        for node in nodes:
            edges = graph.get(node) or {}
            weight_total = sum(max(0.0, float(weight)) for weight in edges.values())
            if weight_total <= 0:
                next_ranks[source] += alpha * ranks[node]
                continue
            for target, weight in edges.items():
                next_ranks[target] += alpha * ranks[node] * (max(0.0, float(weight)) / weight_total)
        delta = sum(abs(next_ranks[node] - ranks[node]) for node in nodes)
        ranks = next_ranks
        if delta < tolerance:
            break
    return ranks


def rank_candidates_for_source(
    graph: Mapping[str, Mapping[str, float]],
    source: str,
    *,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    ranks = personalized_pagerank(graph, source)
    rows = [
        {
            "target": target,
            "rank_source": "personalized_pagerank",
            "score": round(score, 8),
        }
        for target, score in ranks.items()
        if target != source and score > 0
    ]
    rows.sort(key=lambda row: float(row.get("score") or 0.0), reverse=True)
    return rows[:top_k]


def build_graph_candidate_ranks(
    node_cards: Sequence[Mapping[str, Any]],
    deterministic_pairs: Sequence[Mapping[str, Any]],
    *,
    accepted_edges_path: Path | None = None,
    proposed_edges_path: Path | None = None,
    top_k: int = 8,
) -> dict[str, Any]:
    graph = build_route_candidate_graph(
        node_cards,
        deterministic_pairs,
        accepted_edges_path=accepted_edges_path,
        proposed_edges_path=proposed_edges_path,
    )
    sources = [str(card.get("path")) for card in node_cards if card.get("path")]
    return {
        "kind": "route_graph_candidate_ranks",
        "schema_version": "route_graph_candidate_ranks_v1",
        "method": "personalized_pagerank_over_deterministic_and_ledger_edges",
        "advisory_only": True,
        "ranked_by_source": {
            source: rank_candidates_for_source(graph, source, top_k=top_k)
            for source in sources
        },
    }
