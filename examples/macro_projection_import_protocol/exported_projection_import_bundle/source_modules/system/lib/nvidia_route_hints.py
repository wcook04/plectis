"""
NVIDIA retrieval hints for bounded route-worker packets.

[PURPOSE]
- Teleology: Use hosted retrieval models to rank candidate pairs without
  pretending embeddings or rerankers can decide typed route truth.
- Mechanism: Build doc-shaped query/passages from node cards and relation cards,
  call NVIDIA embeddings for cosine relatedness, and optionally call NVIDIA
  reranking when the endpoint is available.
- Non-goal: This module does not classify connector verbs or mutate routes.
"""

from __future__ import annotations

from math import sqrt
from typing import Any, Mapping, Sequence

from system.lib import model_profile_registry, nvidia_nim, route_candidate_builder


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def route_pair_query() -> str:
    return (
        "Instruct: Retrieve source-target file pairs that deserve symbolic route-edge judgment "
        "in a typed software/doctrine graph. Prefer governance, implementation, evidence, "
        "dependency, audit, compression, navigation, stale-default, and runtime-control "
        "relationships over mere topical similarity. Exclude reversed or same-topic-only pairs.\n"
        "Query: directed semantic route candidate from source file to target file"
    )


def _card_by_path(node_cards: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(card.get("path")): card for card in node_cards if card.get("path")}


def pair_passages(
    node_cards: Sequence[Mapping[str, Any]],
    candidate_pairs: Sequence[Mapping[str, Any]],
) -> tuple[list[str], list[Mapping[str, Any]]]:
    by_path = _card_by_path(node_cards)
    passages: list[str] = []
    kept_pairs: list[Mapping[str, Any]] = []
    for pair in candidate_pairs:
        source = by_path.get(str(pair.get("source") or ""))
        target = by_path.get(str(pair.get("target") or ""))
        if not source or not target:
            continue
        passages.append(route_candidate_builder.candidate_pair_passage(pair, source, target))
        kept_pairs.append(pair)
    return passages, kept_pairs


def embedding_pair_hints(
    node_cards: Sequence[Mapping[str, Any]],
    candidate_pairs: Sequence[Mapping[str, Any]],
    *,
    model_profile_id: str = "embed_general",
    timeout_s: int = 45,
) -> dict[str, Any]:
    passages, kept_pairs = pair_passages(node_cards, candidate_pairs)
    if not passages:
        return {"status": "empty", "reason": "No candidate pair passages available."}
    model = model_profile_registry.nvidia_model_id(model_profile_id, fallback=nvidia_nim.DEFAULT_EMBED_MODEL)
    try:
        query_vectors = nvidia_nim.embed_texts(
            [route_pair_query()],
            config={"model": model, "input_type": "query", "timeout_s": timeout_s},
        )
        passage_vectors = nvidia_nim.embed_texts(
            passages,
            config={"model": model, "input_type": "passage", "timeout_s": timeout_s},
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "provider": "nvidia_nim",
            "model_profile": model_profile_id,
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }
    query_vector = query_vectors[0]
    ranked = []
    for pair, vector in zip(kept_pairs, passage_vectors):
        ranked.append(
            {
                "pair_id": pair.get("pair_id"),
                "source": pair.get("source"),
                "target": pair.get("target"),
                "embedding_score": round(_cosine(query_vector, vector), 6),
                "hint_role": "candidate_selection_only",
            }
        )
    ranked.sort(key=lambda row: float(row.get("embedding_score") or 0.0), reverse=True)
    return {
        "status": "ok",
        "provider": "nvidia_nim",
        "model_profile": model_profile_id,
        "model": model,
        "prompt_shape": "nv_embed_instruct_query_vs_neutral_pair_passages_v3",
        "advisory_only": True,
        "interpretation": "Ranks pairs for symbolic inspection. Does not decide edge truth, direction, or verb.",
        "pair_relatedness_rank": ranked,
    }


def rerank_pair_hints(
    node_cards: Sequence[Mapping[str, Any]],
    candidate_pairs: Sequence[Mapping[str, Any]],
    *,
    model_profile_id: str = "rerank_pairs",
    timeout_s: int = 45,
) -> dict[str, Any]:
    passages, kept_pairs = pair_passages(node_cards, candidate_pairs)
    if not passages:
        return {"status": "empty", "reason": "No candidate pair passages available."}
    model = model_profile_registry.nvidia_model_id(model_profile_id, fallback=nvidia_nim.DEFAULT_RERANK_MODEL)
    try:
        rows = nvidia_nim.rerank_passages(
            route_pair_query(),
            passages,
            config={"model": model, "timeout_s": timeout_s},
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "provider": "nvidia_nim",
            "model_profile": model_profile_id,
            "model": model,
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }
    ranked = []
    for row in rows:
        index = int(row.get("index") or 0)
        if index < 0 or index >= len(kept_pairs):
            continue
        pair = kept_pairs[index]
        ranked.append(
            {
                "pair_id": pair.get("pair_id"),
                "source": pair.get("source"),
                "target": pair.get("target"),
                "rerank_score": round(float(row.get("score") or 0.0), 6),
                "hint_role": "candidate_selection_only",
            }
        )
    return {
        "status": "ok",
        "provider": "nvidia_nim",
        "model_profile": model_profile_id,
        "model": model,
        "endpoint": nvidia_nim.DEFAULT_RERANKINGS_URL,
        "advisory_only": True,
        "interpretation": "Reranks pairs for symbolic inspection. Does not decide edge truth, direction, or verb.",
        "pair_rerank_rank": ranked,
    }


def build_route_hints(
    node_cards: Sequence[Mapping[str, Any]],
    candidate_pairs: Sequence[Mapping[str, Any]],
    *,
    enabled: bool,
    include_rerank: bool = False,
    embedding_model_profile_id: str = "embed_general",
) -> dict[str, Any]:
    if not enabled:
        return {
            "status": "disabled",
            "reason": "Retrieval hints disabled for this compression level/run.",
            "policy": "Route worker may still use deterministic node cards and candidate-pair signals.",
        }
    hints = {
        "status": "ok",
        "policy": "Retrieval hints select pairs for inspection only. The route judge must still apply symbolic verb and evidence rules.",
        "embedding": embedding_pair_hints(
            node_cards,
            candidate_pairs,
            model_profile_id=embedding_model_profile_id,
        ),
    }
    if include_rerank:
        hints["rerank"] = rerank_pair_hints(node_cards, candidate_pairs)
    else:
        hints["rerank"] = {
            "status": "disabled",
            "reason": "Rerank endpoint is optional until account/endpoint availability is proven.",
        }
    return hints
