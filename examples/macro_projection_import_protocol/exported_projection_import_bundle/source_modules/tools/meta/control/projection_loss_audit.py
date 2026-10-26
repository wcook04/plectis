#!/usr/bin/env python3
"""
Audit where route truth is lost across L0/L1/L2/L3 packet compression.

[PURPOSE]
- Teleology: Turn "Rosetta-only is too lossy" into a measurable route-edge
  projection-loss report.
- Mechanism: Compare hidden manual baseline edges against node-card,
  relation-card, and slim Rosetta surfaces and report which support survives.
- Non-goal: This script does not run models or promote graph edges.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import route_candidate_builder, route_node_card_builder  # noqa: E402
from system.lib.repo_env import maybe_reexec_into_repo_python  # noqa: E402
from tools.meta.control import routing_pilot_harness  # noqa: E402


if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)


STATE_REL = "state/raw_seed_routing_pilot/projection_loss_audits"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _edge_triple(edge: Mapping[str, Any]) -> tuple[str, str, str]:
    return (
        str(edge.get("source") or ""),
        str(edge.get("target") or ""),
        str(edge.get("connector_verb") or edge.get("verb_id") or ""),
    )


def _node_signal(card: Mapping[str, Any]) -> bool:
    return bool(
        card.get("compression_role")
        or card.get("exports_or_symbols")
        or card.get("json_keys_or_schema_terms")
        or card.get("headings")
        or card.get("evidence_snippets")
    )


def _relation_signal(pair_card: Mapping[str, Any] | None) -> bool:
    if not pair_card:
        return False
    return bool(pair_card.get("deterministic_signals") or pair_card.get("possible_verbs_from_signals"))


def _slim_signal(card: Mapping[str, Any]) -> bool:
    return bool(card.get("compression_role") or card.get("authority_plane") or card.get("domain_tags"))


def _verb_recoverable_from_slim(verb: str, source: Mapping[str, Any], target: Mapping[str, Any]) -> bool:
    text = " ".join(
        str(value or "").lower()
        for card in (source, target)
        for value in (
            card.get("compression_role"),
            card.get("authority_plane"),
            " ".join(str(item) for item in card.get("domain_tags") or []),
            " ".join(str(item) for item in card.get("verb_cues") or []),
        )
    )
    source_plane = str(source.get("authority_plane") or "")
    if verb == "governs":
        return source_plane in {"standard", "paper_module", "raw_seed_projection"} or any(
            token in text for token in ("principle", "authority", "standard", "doctrine")
        )
    if verb == "feeds":
        return any(token in text for token in ("provider", "client", "runtime", "harness", "input"))
    if verb == "compresses":
        return any(token in text for token in ("compression", "projection", "axiom", "rosetta", "smaller"))
    if verb == "routes_to":
        return any(token in text for token in ("navigation", "manifest", "option", "scope"))
    if verb == "populates":
        return any(token in text for token in ("schema", "fields", "synth", "generated", "rows"))
    if verb == "audits":
        return any(token in text for token in ("audit", "caveat", "check", "score", "verify"))
    if verb == "invalidates":
        return any(token in text for token in ("stale", "default", "newer", "invalidates", "wrong"))
    if verb == "blocks":
        return any(token in text for token in ("block", "missing", "caveat", "proof", "not ready"))
    if verb == "evidences":
        return any(token in text for token in ("evidence", "backend", "doc", "receipt", "implementation", "proof"))
    return _slim_signal(source) and _slim_signal(target)


def audit_projection_loss(levels: list[str] | None = None) -> dict[str, Any]:
    levels = levels or ["L1_node_card", "L2_relation_card", "L3_rosetta_only"]
    scope_manifest = routing_pilot_harness._read_json(routing_pilot_harness.SCOPE_MANIFEST_REL)
    baseline = routing_pilot_harness._read_json(routing_pilot_harness.BASELINE_REL)
    rows: list[dict[str, Any]] = []
    level_summaries: dict[str, dict[str, Any]] = {}

    for level in levels:
        route_universe = routing_pilot_harness._route_universe_for_level(baseline, scope_manifest, level)
        cards = route_node_card_builder.build_node_cards(REPO_ROOT, route_universe)
        cards_by_path = {str(card.get("path")): card for card in cards}
        baseline_pairs = [
            {"pair_id": f"gold_{idx:03d}", "source": source, "target": target}
            for idx, edge in enumerate(baseline.get("routing_decisions") or [], start=1)
            if isinstance(edge, Mapping)
            for source, target, _verb in [_edge_triple(edge)]
            if source in cards_by_path and target in cards_by_path
        ]
        pair_cards = route_candidate_builder.build_candidate_pairs(cards, slate_pairs=baseline_pairs)
        pair_by_key = {
            (str(pair.get("source")), str(pair.get("target"))): pair
            for pair in pair_cards
        }
        counts = {
            "gold_edges_in_level": 0,
            "source_target_cards_present": 0,
            "l1_evidence_preserved": 0,
            "l2_bridge_signal_preserved": 0,
            "l3_relation_type_recoverable": 0,
        }
        for edge in baseline.get("routing_decisions") or []:
            if not isinstance(edge, Mapping):
                continue
            source, target, verb = _edge_triple(edge)
            if source not in cards_by_path or target not in cards_by_path:
                continue
            counts["gold_edges_in_level"] += 1
            source_card = cards_by_path[source]
            target_card = cards_by_path[target]
            pair_card = pair_by_key.get((source, target))
            source_target_present = source in cards_by_path and target in cards_by_path
            l1_preserved = _node_signal(source_card) and _node_signal(target_card)
            l2_preserved = _relation_signal(pair_card)
            slim_source = route_node_card_builder.slim_node_card(source_card)
            slim_target = route_node_card_builder.slim_node_card(target_card)
            l3_recoverable = (
                _slim_signal(slim_source)
                and _slim_signal(slim_target)
                and _verb_recoverable_from_slim(verb, slim_source, slim_target)
            )
            counts["source_target_cards_present"] += int(source_target_present)
            counts["l1_evidence_preserved"] += int(l1_preserved)
            counts["l2_bridge_signal_preserved"] += int(l2_preserved)
            counts["l3_relation_type_recoverable"] += int(l3_recoverable)
            rows.append(
                {
                    "compression_level": level,
                    "source": source,
                    "target": target,
                    "connector_verb": verb,
                    "source_target_cards_present": source_target_present,
                    "l1_evidence_preserved": l1_preserved,
                    "l2_bridge_signal_preserved": l2_preserved,
                    "l3_relation_type_recoverable": l3_recoverable,
                    "loss_reason": "ok"
                    if l1_preserved and l2_preserved and l3_recoverable
                    else "missing_relation_card_signal"
                    if l1_preserved and not l2_preserved
                    else "missing_node_card_evidence"
                    if not l1_preserved
                    else "rosetta_summary_too_thin",
                }
            )
        denominator = max(1, counts["gold_edges_in_level"])
        level_summaries[level] = {
            **counts,
            "l1_evidence_preservation_rate": counts["l1_evidence_preserved"] / denominator,
            "l2_bridge_signal_preservation_rate": counts["l2_bridge_signal_preserved"] / denominator,
            "l3_relation_recoverability_rate": counts["l3_relation_type_recoverable"] / denominator,
        }

    return {
        "kind": "projection_loss_audit",
        "schema_version": "projection_loss_audit_v1",
        "generated_at": _utc_now(),
        "baseline_ref": routing_pilot_harness.BASELINE_REL,
        "levels": levels,
        "level_summaries": level_summaries,
        "edges": rows,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--levels", nargs="*", default=["L1_node_card", "L2_relation_card", "L3_rosetta_only"])
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--run-id", default=None)
    args = parser.parse_args(argv)

    payload = audit_projection_loss(args.levels)
    if args.write:
        run_id = args.run_id or f"pla_{uuid.uuid4().hex[:16]}"
        path = REPO_ROOT / STATE_REL / f"{run_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        payload["audit_ref"] = path.relative_to(REPO_ROOT).as_posix()
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
