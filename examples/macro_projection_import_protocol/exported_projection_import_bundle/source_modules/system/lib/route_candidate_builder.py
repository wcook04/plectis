"""
Build deterministic candidate relation cards for route-worker packets.

[PURPOSE]
- Teleology: Separate candidate discovery from edge judgment so workers do not
  have to infer both the universe and the verb from raw prose.
- Mechanism: Score source/target node-card pairs with cheap lexical,
  structural, import, authority, and path-neighborhood signals; emit relation
  cards with possible verbs and negative warnings.
- Non-goal: This module does not decide final truth. It proposes inspection
  targets for a route judge.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence


def _as_set(value: Any) -> set[str]:
    if not isinstance(value, list):
        return set()
    return {str(item).lower() for item in value if str(item).strip()}


def _path_module_token(path: str) -> str:
    token = path[:-3] if path.endswith(".py") else path
    return token.replace("/", ".").replace(".__init__", "").strip(".")


def _shared_terms(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    left = _as_set(source.get("top_terms")) | _as_set(source.get("path_tokens"))
    right = _as_set(target.get("top_terms")) | _as_set(target.get("path_tokens"))
    return sorted((left & right) - {"json", "markdown", "python"})[:10]


def _same_parent(source_path: str, target_path: str) -> bool:
    return Path(source_path).parent == Path(target_path).parent


def _deterministic_signals(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    signals: list[str] = []
    source_path = str(source.get("path") or "")
    target_path = str(target.get("path") or "")
    target_module = _path_module_token(target_path)
    imports = _as_set(source.get("imports_or_dependencies"))
    exact_mentions = _as_set(source.get("exact_mentions"))
    target_stem = Path(target_path).stem.lower()

    if target_module and any(target_module.endswith(token) or token.endswith(target_module) for token in imports):
        signals.append("source imports target module")
    if target_stem and target_stem in exact_mentions:
        signals.append("source exact-mentions target stem")
    if _same_parent(source_path, target_path):
        signals.append("source and target share parent directory")
    shared = _shared_terms(source, target)
    if len(shared) >= 2:
        signals.append("source and target share lexical/domain terms: " + ", ".join(shared[:5]))
    source_tags = _as_set(source.get("domain_tags"))
    target_tags = _as_set(target.get("domain_tags"))
    shared_tags = sorted(source_tags & target_tags)
    if shared_tags:
        signals.append("source and target share domain tags: " + ", ".join(shared_tags[:5]))

    source_plane = str(source.get("authority_plane") or "")
    target_plane = str(target.get("authority_plane") or "")
    if source_plane in {"standard", "paper_module", "raw_seed_projection"} and target_plane in {"runtime", "artifact", "state_receipt"}:
        signals.append("source is higher-authority plane over target plane")
    if source_plane == "runtime" and target_plane in {"runtime", "artifact"}:
        signals.append("source is runtime surface adjacent to target")
    if source_plane == "state_receipt" or target_plane == "state_receipt":
        signals.append("state receipt participates in candidate route")
    return signals


def _score_signals(signals: Sequence[str]) -> float:
    weights = {
        "source imports target module": 4.0,
        "source exact-mentions target stem": 2.2,
        "source and target share parent directory": 0.8,
        "source and target share lexical/domain terms": 1.0,
        "source and target share domain tags": 0.8,
        "source is higher-authority plane over target plane": 1.5,
        "source is runtime surface adjacent to target": 0.7,
        "state receipt participates in candidate route": 0.6,
    }
    total = 0.0
    for signal in signals:
        for prefix, weight in weights.items():
            if signal.startswith(prefix):
                total += weight
                break
    return round(total, 3)


def _possible_verbs(source: Mapping[str, Any], target: Mapping[str, Any], signals: Sequence[str]) -> list[str]:
    verbs: list[str] = []
    source_plane = str(source.get("authority_plane") or "")
    target_plane = str(target.get("authority_plane") or "")
    joined = " | ".join(signals).lower()
    source_path = str(source.get("path") or "")
    target_path = str(target.get("path") or "")

    if "imports target module" in joined:
        verbs.extend(["feeds", "evidences"])
    if source_plane in {"standard", "paper_module", "raw_seed_projection"} and target_plane in {"runtime", "artifact", "state_receipt"}:
        verbs.extend(["governs", "routes_to", "evidences"])
    if source_plane == "runtime" and target_plane == "state_receipt":
        verbs.extend(["populates", "compresses", "evidences"])
    if source_plane == "runtime" and target_path.endswith(".md"):
        verbs.extend(["invalidates", "evidences"])
    if source_path.endswith(".md") and target_plane == "runtime":
        verbs.extend(["evidences", "audits", "blocks"])
    if target_plane == "standard":
        verbs.extend(["evidences", "governs"])
    if "scope_manifest" in target_path or "synth_seed" in target_path:
        verbs.extend(["routes_to", "populates", "governs"])

    allowed_order = [
        "feeds",
        "populates",
        "compresses",
        "routes_to",
        "invalidates",
        "audits",
        "blocks",
        "evidences",
        "governs",
        "supersedes",
    ]
    deduped = []
    for verb in allowed_order:
        if verb in verbs and verb not in deduped:
            deduped.append(verb)
    return deduped or ["evidences"]


def _negative_warnings(source: Mapping[str, Any], target: Mapping[str, Any]) -> list[str]:
    warnings = [
        "Do not choose governs unless source is an authority that constrains target.",
        "Do not choose evidences if a narrower lifecycle/dataflow verb fits.",
        "Do not treat shared NVIDIA/routing vocabulary as an edge by itself.",
    ]
    if str(target.get("authority_plane") or "") in {"standard", "paper_module", "raw_seed_projection"}:
        warnings.append("If target is the authority and source is implementation, consider implements/depends_on or abstain.")
    return warnings


def _pair_id(source_path: str, target_path: str, index: int) -> str:
    digest = hashlib.sha1(f"{source_path}->{target_path}".encode("utf-8")).hexdigest()[:8]
    return f"P_{index:03d}_{digest}"


def relation_card(
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    *,
    pair_id: str,
) -> dict[str, Any]:
    signals = _deterministic_signals(source, target)
    return {
        "pair_id": pair_id,
        "source_node_id": source.get("node_id"),
        "target_node_id": target.get("node_id"),
        "source": source.get("path"),
        "target": target.get("path"),
        "deterministic_score": _score_signals(signals),
        "deterministic_signals": signals,
        "possible_verbs_from_signals": _possible_verbs(source, target, signals),
        "negative_warnings": _negative_warnings(source, target),
    }


def build_candidate_pairs(
    node_cards: Sequence[Mapping[str, Any]],
    *,
    slate_pairs: Sequence[Mapping[str, str]] | None = None,
    max_pairs: int = 20,
    max_pairs_per_source: int = 5,
) -> list[dict[str, Any]]:
    by_path = {str(card.get("path")): card for card in node_cards if card.get("path")}
    if slate_pairs:
        cards: list[dict[str, Any]] = []
        for index, pair in enumerate(slate_pairs, start=1):
            source = by_path.get(str(pair.get("source") or ""))
            target = by_path.get(str(pair.get("target") or ""))
            if not source or not target:
                continue
            cards.append(
                relation_card(
                    source,
                    target,
                    pair_id=str(pair.get("pair_id") or _pair_id(str(source.get("path")), str(target.get("path")), index)),
                )
            )
        return cards

    candidates: list[dict[str, Any]] = []
    per_source_counts: dict[str, int] = {}
    index = 1
    for source in node_cards:
        source_path = str(source.get("path") or "")
        if not source_path:
            continue
        scored: list[dict[str, Any]] = []
        for target in node_cards:
            target_path = str(target.get("path") or "")
            if not target_path or target_path == source_path:
                continue
            card = relation_card(source, target, pair_id=_pair_id(source_path, target_path, index))
            if float(card.get("deterministic_score") or 0.0) > 0.0:
                scored.append(card)
                index += 1
        scored.sort(key=lambda row: float(row.get("deterministic_score") or 0.0), reverse=True)
        for card in scored[:max_pairs_per_source]:
            count = per_source_counts.get(source_path, 0)
            if count >= max_pairs_per_source:
                break
            candidates.append(card)
            per_source_counts[source_path] = count + 1
    candidates.sort(key=lambda row: float(row.get("deterministic_score") or 0.0), reverse=True)
    return candidates[:max_pairs]


def candidate_pair_passage(pair_card: Mapping[str, Any], source: Mapping[str, Any], target: Mapping[str, Any]) -> str:
    return "\n".join(
        [
            f"pair_id={pair_card.get('pair_id')}",
            f"source_path={source.get('path')}",
            f"source_kind={source.get('kind')}",
            f"source_authority_plane={source.get('authority_plane')}",
            f"source_role={source.get('compression_role')}",
            "source_symbols=" + ", ".join(str(item) for item in source.get("exports_or_symbols") or []),
            "source_terms=" + ", ".join(str(item) for item in source.get("top_terms") or []),
            f"target_path={target.get('path')}",
            f"target_kind={target.get('kind')}",
            f"target_authority_plane={target.get('authority_plane')}",
            f"target_role={target.get('compression_role')}",
            "target_symbols=" + ", ".join(str(item) for item in target.get("exports_or_symbols") or []),
            "target_terms=" + ", ".join(str(item) for item in target.get("top_terms") or []),
            "deterministic_signals=" + "; ".join(str(item) for item in pair_card.get("deterministic_signals") or []),
        ]
    )
