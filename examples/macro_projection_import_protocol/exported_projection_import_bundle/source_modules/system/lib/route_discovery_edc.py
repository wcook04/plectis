"""
Normalize route discovery proposals with an EDC-shaped loop.

[PURPOSE]
- Teleology: Let route workers invent useful edges without letting those edges
  bypass schema discipline.
- Mechanism: Extract proposal fields, define a concise relation pattern, and
  canonicalize it to the nearest Rosetta verb or a proposed-new-pattern status.
- Non-goal: This module does not accept proposals into the canonical graph.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence


# Exact-alias table for common LLM inflection drift (singular/infinitive → canonical form).
# Applied before synonym search so trivial variants resolve without fuzzy matching.
VERB_INFLECTION_ALIASES: dict[str, str] = {
    "populate": "populates",
    "govern": "governs",
    "evidence": "evidences",
    "feed": "feeds",
    "audit": "audits",
    "block": "blocks",
    "compress": "compresses",
    "route": "routes_to",
    "invalidate": "invalidates",
    "supersede": "supersedes",
    "route_to": "routes_to",
    "routed_to": "routes_to",
}

DEFAULT_VERB_SYNONYMS: dict[str, tuple[str, ...]] = {
    "governs": ("governs", "constrains", "requires", "declares", "authority", "standard", "must obey"),
    "evidences": ("evidences", "proves", "shows", "demonstrates", "receipt", "example"),
    "feeds": ("feeds", "consumed by", "input", "provider", "api", "runtime consumes"),
    "populates": ("populates", "writes", "fills", "emits", "generates rows", "creates artifact"),
    "compresses": ("compresses", "projects", "summarizes", "distills", "rosetta", "smaller"),
    "routes_to": ("routes", "points", "directs", "next context", "navigation", "manifest"),
    "invalidates": ("invalidates", "stale", "superseded", "wrong", "newer default"),
    "audits": ("audits", "checks", "scores", "validates", "review", "gate"),
    "blocks": ("blocks", "blocked", "missing proof", "prevents", "not ready", "caveat"),
    "supersedes": ("supersedes", "replaces", "new authority", "successor"),
}


def _words(value: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", value)}


def _pattern_cluster(source: str, target: str, definition: str) -> str:
    text = f"{source} {target} {definition}".lower()
    if "/standards/" in source or "std_" in source:
        if "check" in target or "validator" in target or "audit" in target:
            return "standard_to_checker_enforcement"
        return "standard_to_artifact_authority"
    if "/paper_modules/" in source and (target.endswith(".py") or target.startswith("system/")):
        return "paper_module_to_runtime_constraint"
    if target.startswith("state/") or "receipt" in target:
        return "artifact_to_receipt_evidence"
    if "compress" in text or "rosetta" in text:
        return "compression_projection"
    return "unclustered_route_pattern"


def canonicalize_verb(
    *,
    raw_relation_phrase: str,
    definition: str,
    proposed_verb: str,
    allowed_verbs: Sequence[str],
) -> tuple[str, float, str]:
    allowed = {str(verb) for verb in allowed_verbs}
    if proposed_verb in allowed:
        return proposed_verb, 0.78, "mapped_to_existing_verb"

    normalized = VERB_INFLECTION_ALIASES.get(proposed_verb.lower().strip(), proposed_verb)
    if normalized != proposed_verb and normalized in allowed:
        return normalized, 0.75, "mapped_to_existing_verb"

    haystack = f"{raw_relation_phrase} {definition} {proposed_verb}".lower()
    best_verb = ""
    best_score = 0
    for verb, synonyms in DEFAULT_VERB_SYNONYMS.items():
        if verb not in allowed:
            continue
        score = sum(1 for needle in synonyms if needle in haystack)
        if score > best_score:
            best_verb = verb
            best_score = score
    if best_verb:
        confidence = min(0.9, 0.52 + (0.08 * best_score))
        return best_verb, round(confidence, 3), "mapped_to_existing_verb"
    return proposed_verb or "proposed_new_relation_pattern", 0.35, "proposed_new_relation_pattern"


def edge_fingerprint(source: str, target: str, verb: str, definition: str) -> str:
    return hashlib.sha1(f"{source}\0{target}\0{verb}\0{definition}".encode("utf-8")).hexdigest()[:16]


def existing_edge_index(rows: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str, str], str]:
    index: dict[tuple[str, str, str], str] = {}
    for row in rows:
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        verb = str(row.get("verb") or row.get("connector_verb") or "")
        if source and target and verb:
            index[(source, target, verb)] = str(row.get("proposal_id") or row.get("edge_id") or "")
    return index


def canonicalize_discovery_edge(
    edge: Mapping[str, Any],
    *,
    allowed_verbs: Sequence[str],
    existing_rows: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    source = str(edge.get("source") or edge.get("source_path") or "").strip()
    target = str(edge.get("target") or edge.get("target_path") or "").strip()
    proposed_verb = str(edge.get("connector_verb") or edge.get("verb") or "").strip()
    evidence = edge.get("evidence_set") or edge.get("evidence_phrases") or []
    definition = str(edge.get("definition") or "").strip()
    raw_relation_phrase = str(edge.get("raw_relation_phrase") or definition or proposed_verb).strip()
    nearest_verb, confidence, status = canonicalize_verb(
        raw_relation_phrase=raw_relation_phrase,
        definition=definition,
        proposed_verb=proposed_verb,
        allowed_verbs=allowed_verbs,
    )
    duplicate_key = (source, target, nearest_verb)
    duplicate_of = existing_edge_index(existing_rows).get(duplicate_key)
    return {
        "source": source,
        "target": target,
        "raw_relation_phrase": raw_relation_phrase,
        "proposed_verb": proposed_verb,
        "nearest_canonical_verb": nearest_verb,
        "canonicalization_confidence": confidence,
        "canonicalization_status": status if not duplicate_of else "duplicate_candidate",
        "duplicate_of": duplicate_of,
        "schema_pattern_cluster": _pattern_cluster(source, target, definition),
        "definition": definition,
        "evidence": evidence,
        "evidence_terms": sorted(_words(" ".join(str(item) for item in evidence)))[:12],
    }
