"""Rosetta Operator Court v1 — adjudicate the dominant graph operator for a directed edge.

The route graph cannot scale until verb selection is treated as **graph operator
adjudication**, not natural-language labeling. A single source\u2192target edge often
supports multiple plausible verbs (governs/populates/evidences); the canonical
edge stored in the graph is the operator that controls default traversal,
mutation safety, refresh priority, and downstream worker dependency behavior.

This module owns:

- grammar loaders for the operator-court layer of std_navigation_rosetta_grammar.json
  (relation_families, operator_semantics, dominance_rules, authority_plane_defaults,
  contrastive_boundaries, adjudication_output_shape, adjudication_failure_levels)
- deterministic case construction from confirmed pairs + node/relation cards
- the prompt builder with five experiment variants (allowlist_only \u2192
  prior_guess_adversarial)
- the scorer (failure ladder, per-verb confusion matrix, baseline-leakage detector)

Lower-tier provider output produced via this module writes prompts, candidates,
scores, and proposals only. It never mutates canonical doctrine or the route
graph.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


PACKET_MODE = "operator_court_v1"
PACKET_VARIANTS: tuple[str, ...] = (
    "allowlist_only",
    "definitions_only",
    "definitions_dominance",
    "operator_court_deterministic_cards",
    "prior_guess_adversarial",
)
DEFAULT_PACKET_VARIANT = "operator_court_deterministic_cards"
LEGACY_VERB_CORRECTION_VARIANT = "allowlist_only"
DOMINANCE_CONTEXT_PRIMARY = "default_route_graph_traversal_and_worker_dependency_behavior"
APPEAL_STATUS_PENDING = "pending_controller_review"
OPERATOR_COURT_APPEAL_SMELL_KINDS: tuple[str, ...] = (
    "baseline_challenge",
    "missing_dominance_rule",
    "authority_plane_gap",
    "verb_family_gap",
    "evidence_gap",
    "leakage_risk",
)

LEGAL_GRAPH_BEHAVIOR_KEYS: tuple[str, ...] = (
    "target_must_conform_to_source",
    "source_change_requires_target_review",
    "target_is_materialized_from_source",
    "source_supports_belief_in_target",
    "source_checks_target_readiness",
    "source_guides_navigation_to_target",
    "source_replaces_target",
    "source_invalidates_target",
    "source_blocks_target",
)

ADVERSARIAL_PRIOR_GUESS_FIELD = "previous_model_guess_may_be_wrong"

DEFAULT_BASE_VERBS: tuple[str, ...] = (
    "feeds",
    "blocks",
    "governs",
    "evidences",
    "populates",
    "invalidates",
    "compresses",
    "routes_to",
    "audits",
    "supersedes",
)


# ---------------------------------------------------------------------------
# grammar loaders
# ---------------------------------------------------------------------------


def base_verbs(grammar: Mapping[str, Any]) -> list[str]:
    verbs = grammar.get("relation_verb_shape", {}).get("base_verbs")
    if isinstance(verbs, list) and verbs:
        return [str(v) for v in verbs]
    return list(DEFAULT_BASE_VERBS)


def build_relation_families(grammar: Mapping[str, Any]) -> dict[str, list[str]]:
    raw = grammar.get("relation_families") or {}
    if not isinstance(raw, Mapping):
        return {}
    families: dict[str, list[str]] = {}
    for family, verbs in raw.items():
        if isinstance(verbs, list):
            families[str(family)] = [str(v) for v in verbs]
    return families


def family_for_verb(grammar: Mapping[str, Any], verb: str) -> str | None:
    for family, verbs in build_relation_families(grammar).items():
        if verb in verbs:
            return family
    return None


def build_operator_semantics(grammar: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    raw = grammar.get("operator_semantics") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {str(verb): dict(body) for verb, body in raw.items() if isinstance(body, Mapping)}


def build_verb_definitions(grammar: Mapping[str, Any]) -> dict[str, str]:
    raw = grammar.get("verb_definitions") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {
        str(verb): str(text)
        for verb, text in raw.items()
        if verb != "rule" and isinstance(text, str)
    }


def build_contrastive_boundaries(grammar: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = grammar.get("contrastive_boundaries") or []
    return [dict(row) for row in raw if isinstance(row, Mapping)]


def build_dominance_rules(grammar: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = grammar.get("dominance_rules") or []
    return [dict(row) for row in raw if isinstance(row, Mapping)]


def build_authority_plane_defaults(grammar: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw = grammar.get("authority_plane_defaults") or []
    return [dict(row) for row in raw if isinstance(row, Mapping)]


def build_adjudication_output_shape(grammar: Mapping[str, Any]) -> dict[str, Any]:
    raw = grammar.get("adjudication_output_shape") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def build_adjudication_failure_levels(grammar: Mapping[str, Any]) -> dict[str, str]:
    raw = grammar.get("adjudication_failure_levels") or {}
    if not isinstance(raw, Mapping):
        return {}
    return {str(level): str(text) for level, text in raw.items() if isinstance(text, str)}


def build_dominance_context(grammar: Mapping[str, Any]) -> dict[str, Any]:
    raw = grammar.get("dominance_context") or {}
    return dict(raw) if isinstance(raw, Mapping) else {}


def known_dominance_rule_ids(grammar: Mapping[str, Any]) -> set[str]:
    return {str(rule.get("id")) for rule in build_dominance_rules(grammar) if rule.get("id")}


# ---------------------------------------------------------------------------
# deterministic case construction
# ---------------------------------------------------------------------------


_SCHEMA_PLACEHOLDERS = frozenset(
    {"bridge_evidence", "source_evidence", "target_evidence", "evidence_phrase", "evidence"}
)


def _clean_evidence_set(values: Iterable[Any]) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in _SCHEMA_PLACEHOLDERS:
            cleaned.append(text)
    return cleaned


def _slim_card(card: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "path": card.get("path"),
        "path_kind": card.get("kind"),
        "authority_plane": card.get("authority_plane"),
        "compression_role": card.get("compression_role"),
        "domain_tags": list(card.get("domain_tags") or []),
        "verb_cues": list(card.get("verb_cues") or []),
        "headings": list(card.get("headings") or [])[:8],
        "json_keys": list(card.get("json_keys_or_schema_terms") or [])[:12],
        "symbols": list(card.get("exports_or_symbols") or [])[:12],
        "imports": list(card.get("imports_or_dependencies") or [])[:12],
        "top_terms": list(card.get("top_terms") or [])[:12],
        "exact_mentions": list(card.get("exact_mentions") or [])[:8],
        "evidence_snippets": list(card.get("evidence_snippets") or [])[:4],
    }


def _slim_relation_card(pair: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "deterministic_signals": list(pair.get("deterministic_signals") or []),
        "deterministic_score": pair.get("deterministic_score"),
        "possible_verbs_from_signals": list(pair.get("possible_verbs_from_signals") or []),
        "negative_warnings": list(pair.get("negative_warnings") or []),
    }


def authority_plane_delta(
    source_plane: str,
    target_plane: str,
    grammar: Mapping[str, Any],
) -> dict[str, Any]:
    """Look up the authority_plane_defaults row that matches the given source/target planes.

    Returns the matching row plus the source/target plane names. If no row matches,
    returns just the planes with empty bias fields. The caller can then expose this
    as a deterministic hint without inventing a default.
    """

    for row in build_authority_plane_defaults(grammar):
        if (
            str(row.get("source_authority_plane") or "") == str(source_plane or "")
            and str(row.get("target_authority_plane") or "") == str(target_plane or "")
        ):
            return {
                "source_authority_plane": str(source_plane or ""),
                "target_authority_plane": str(target_plane or ""),
                "default_relation_bias": row.get("default_relation_bias"),
                "secondary_biases": list(row.get("secondary_biases") or []),
                "forbidden_without_evidence": list(row.get("forbidden_without_evidence") or []),
            }
    return {
        "source_authority_plane": str(source_plane or ""),
        "target_authority_plane": str(target_plane or ""),
        "default_relation_bias": None,
        "secondary_biases": [],
        "forbidden_without_evidence": [],
    }


def candidate_dominance_rule_ids(
    candidate_latent_verbs: Iterable[str],
    grammar: Mapping[str, Any],
) -> list[str]:
    """Heuristically pick which dominance rules are plausibly applicable.

    A rule is a candidate if its `prefer` verb or its `prefer_family` overlaps the
    candidate latent verbs (or their families). This is *deterministic but
    advisory* — the model still consults the full dominance_rules list and may
    apply a rule whose preconditions match the evidence we did not surface.
    """

    latent = [str(v) for v in candidate_latent_verbs or []]
    families = build_relation_families(grammar)
    latent_families = {f for f, vs in families.items() for v in vs if v in latent}
    out: list[str] = []
    for rule in build_dominance_rules(grammar):
        rule_id = str(rule.get("id") or "")
        prefer = rule.get("prefer")
        prefer_family = rule.get("prefer_family")
        over = list(rule.get("over") or [])
        if prefer in latent or any(v in latent for v in over):
            out.append(rule_id)
            continue
        if isinstance(prefer_family, str) and prefer_family in latent_families:
            out.append(rule_id)
    return [rid for rid in out if rid]


def candidate_latent_verbs(
    plane_delta: Mapping[str, Any],
    relation_card: Mapping[str, Any],
    grammar: Mapping[str, Any],
) -> list[str]:
    """Union of plane-default biases and signal-derived possible verbs."""

    legal = set(base_verbs(grammar))
    seen: list[str] = []

    def _add(verb: Any) -> None:
        text = str(verb or "")
        if text and text in legal and text not in seen:
            seen.append(text)

    _add(plane_delta.get("default_relation_bias"))
    for v in plane_delta.get("secondary_biases") or []:
        _add(v)
    for v in relation_card.get("possible_verbs_from_signals") or []:
        _add(v)
    return seen


def build_deterministic_operator_cases(
    confirmed_pairs: Sequence[Mapping[str, Any]],
    node_cards: Sequence[Mapping[str, Any]],
    relation_cards: Sequence[Mapping[str, Any]],
    grammar: Mapping[str, Any],
    *,
    include_prior_guess: bool = False,
) -> list[dict[str, Any]]:
    """Build per-pair adjudication cases from confirmed pairs and pre-built cards.

    The returned dicts are deterministic projections — no baseline labels, no
    baseline evidence text, no prior model guesses by default. ``include_prior_guess``
    surfaces the prior `connector_verb` under the explicit
    ``previous_model_guess_may_be_wrong`` field for the adversarial variant only.
    """

    cards_by_path: dict[str, Mapping[str, Any]] = {
        str(card.get("path") or ""): card for card in node_cards if isinstance(card, Mapping)
    }
    pairs_by_endpoints: dict[tuple[str, str], Mapping[str, Any]] = {
        (str(pair.get("source") or ""), str(pair.get("target") or "")): pair
        for pair in relation_cards or []
        if isinstance(pair, Mapping)
    }

    cases: list[dict[str, Any]] = []
    for index, edge in enumerate(confirmed_pairs):
        if not isinstance(edge, Mapping):
            continue
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        pair_id = str(edge.get("pair_id") or f"oc_{index:03d}")
        source_card_full = cards_by_path.get(source) or {}
        target_card_full = cards_by_path.get(target) or {}
        source_plane = str(source_card_full.get("authority_plane") or "")
        target_plane = str(target_card_full.get("authority_plane") or "")
        plane_delta = authority_plane_delta(source_plane, target_plane, grammar)
        relation_card = pairs_by_endpoints.get((source, target)) or {}

        source_card = _slim_card(source_card_full) if source_card_full else {"path": source}
        target_card = _slim_card(target_card_full) if target_card_full else {"path": target}
        slim_relation = _slim_relation_card(relation_card)
        latent = candidate_latent_verbs(plane_delta, slim_relation, grammar)
        rule_ids = candidate_dominance_rule_ids(latent, grammar)

        case: dict[str, Any] = {
            "pair_id": pair_id,
            "source": source,
            "target": target,
            "direction_locked": True,
            "source_card": source_card,
            "target_card": target_card,
            "relation_card": slim_relation,
            "authority_plane_delta": plane_delta,
            "candidate_latent_verbs": latent,
            "candidate_dominance_rules": rule_ids,
            "deterministic_evidence_only": True,
        }
        if include_prior_guess and edge.get("connector_verb"):
            case[ADVERSARIAL_PRIOR_GUESS_FIELD] = str(edge.get("connector_verb"))
        cases.append(case)
    return cases


# ---------------------------------------------------------------------------
# prompt builder
# ---------------------------------------------------------------------------


_INSTRUCTION_CORE = (
    "Choose the dominant Rosetta verb for graph behavior, not every plausible "
    "natural-language relation. Direction is locked. Many verbs may be "
    "semantically plausible. List plausible latent verbs in latent_plausible_verbs, "
    "then choose exactly one dominant_rosetta_verb using the provided dominance_rules. "
    "The dominant verb is the operator that should control default route-graph "
    "traversal and downstream worker behavior."
)

_PRIOR_GUESS_DISCLAIMER = (
    "If you see a previous_model_guess_may_be_wrong field, treat it as untrusted. "
    "Prior model guesses are not evidence. Do not anchor on it."
)

_OUTPUT_INSTRUCTION = (
    "Return ONLY JSON of the shape "
    "{\"relation_label_decisions\": [...], \"ambiguous_cases\": [...]}. "
    "Each decision in relation_label_decisions must include: pair_id, source, "
    "target, latent_plausible_verbs, relation_family, dominant_rosetta_verb, "
    "dominance_rule_applied, graph_behavior, runner_up_verbs, why_not_runner_up, "
    "evidence_used, confidence, needs_more_evidence, needs_new_rule. Use the "
    "exact dominance_rule ids supplied; if no rule fits, set "
    "dominance_rule_applied to 'none' and needs_new_rule to true. If a pair is "
    "genuinely ambiguous, place it under ambiguous_cases with a reason and the "
    "candidate_verbs."
)


def _validate_packet_variant(variant: str) -> str:
    if variant not in PACKET_VARIANTS:
        raise ValueError(
            f"unknown packet_variant {variant!r}; expected one of {PACKET_VARIANTS}"
        )
    return variant


def build_operator_court_prompt(
    confirmed_pairs: Sequence[Mapping[str, Any]],
    *,
    grammar: Mapping[str, Any],
    packet_variant: str = DEFAULT_PACKET_VARIANT,
    include_prior_guess: bool = False,
    deterministic_cases: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Build an operator-court prompt for the given packet variant.

    The five variants form an experiment ladder:

    - allowlist_only: legal verbs + pair list. No definitions, no dominance rules,
      no prior guess. (Variant A — natural-language prior baseline.)
    - definitions_only: A + verb_definitions. (Variant B.)
    - definitions_dominance: B + contrastive_boundaries + dominance_rules +
      relation_families. (Variant C.)
    - operator_court_deterministic_cards: C + per-pair deterministic source/target
      cards, relation cards, authority_plane_delta, candidate dominance rules.
      (Variant D — the recommended production variant.)
    - prior_guess_adversarial: D + previous_model_guess_may_be_wrong per pair.
      (Variant E — anchoring stress test.)

    The prompt MUST NOT include baseline labels, baseline evidence text, or
    expected answers. It SHOULD only include `previous_model_guess_may_be_wrong`
    when ``include_prior_guess`` is true (auto-true for prior_guess_adversarial).
    """

    variant = _validate_packet_variant(packet_variant)
    legal_verbs = base_verbs(grammar)

    payload: dict[str, Any] = {
        "task": "operator_court_v1",
        "packet_mode": PACKET_MODE,
        "packet_variant": variant,
        "dominance_context": build_dominance_context(grammar),
        "instruction": _INSTRUCTION_CORE,
        "output_contract": _OUTPUT_INSTRUCTION,
        "connector_verb_allowlist": legal_verbs,
    }

    if variant in {"definitions_only", "definitions_dominance",
                   "operator_court_deterministic_cards", "prior_guess_adversarial"}:
        payload["verb_definitions"] = build_verb_definitions(grammar)
        payload["operator_semantics"] = build_operator_semantics(grammar)

    if variant in {"definitions_dominance", "operator_court_deterministic_cards",
                   "prior_guess_adversarial"}:
        payload["relation_families"] = build_relation_families(grammar)
        payload["contrastive_boundaries"] = build_contrastive_boundaries(grammar)
        payload["dominance_rules"] = build_dominance_rules(grammar)
        payload["authority_plane_defaults"] = build_authority_plane_defaults(grammar)

    if variant in {"operator_court_deterministic_cards", "prior_guess_adversarial"}:
        if deterministic_cases is None:
            raise ValueError(
                "operator_court_deterministic_cards / prior_guess_adversarial require "
                "deterministic_cases (build via build_deterministic_operator_cases)"
            )
        payload["adjudication_cases"] = [dict(case) for case in deterministic_cases]
        payload["adjudication_output_shape"] = build_adjudication_output_shape(grammar)
    else:
        payload["confirmed_pairs"] = [
            {
                "pair_id": str(edge.get("pair_id") or f"oc_{i:03d}"),
                "source": str(edge.get("source") or ""),
                "target": str(edge.get("target") or ""),
            }
            for i, edge in enumerate(confirmed_pairs)
            if isinstance(edge, Mapping)
        ]

    show_prior = include_prior_guess or variant == "prior_guess_adversarial"
    if not show_prior:
        _strip_prior_guess(payload)

    header = (
        "You are an operator-court worker. Output JSON only. Do not re-judge direction.\n"
        f"{_INSTRUCTION_CORE}\n"
        f"{_PRIOR_GUESS_DISCLAIMER}\n"
        "Evidence must come from deterministic cards (source_card, target_card, "
        "relation_card, authority_plane_delta) or, for low-evidence variants, the "
        "verb allowlist alone. If the boundary is unresolved, emit ambiguous_cases "
        "or set needs_more_evidence=true rather than guessing."
    )

    return f"{header}\n\n{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}"


def _strip_prior_guess(payload: dict[str, Any]) -> None:
    """Remove any prior-guess fields anywhere in the prompt payload (defensive).

    Keeps the contract that variants A-D never expose the
    `previous_model_guess_may_be_wrong` field, even if the case builder included it.
    """

    cases = payload.get("adjudication_cases")
    if isinstance(cases, list):
        for case in cases:
            if isinstance(case, dict):
                case.pop(ADVERSARIAL_PRIOR_GUESS_FIELD, None)
                case.pop("prior_connector_verb", None)
                case.pop("connector_verb", None)
    pairs = payload.get("confirmed_pairs")
    if isinstance(pairs, list):
        for pair in pairs:
            if isinstance(pair, dict):
                pair.pop(ADVERSARIAL_PRIOR_GUESS_FIELD, None)
                pair.pop("prior_connector_verb", None)
                pair.pop("connector_verb", None)


# ---------------------------------------------------------------------------
# leakage detection
# ---------------------------------------------------------------------------


_CARD_STRING_FIELDS_SLIM = (
    "headings",
    "json_keys",
    "symbols",
    "imports",
    "top_terms",
    "exact_mentions",
    "evidence_snippets",
    "verb_cues",
    "domain_tags",
    "path_tokens",
)
_CARD_STRING_FIELDS_FULL = (
    "headings",
    "json_keys_or_schema_terms",
    "exports_or_symbols",
    "imports_or_dependencies",
    "top_terms",
    "exact_mentions",
    "evidence_snippets",
    "verb_cues",
    "domain_tags",
    "path_tokens",
)


def _safe_strings_from_cases(
    deterministic_cases: Sequence[Mapping[str, Any]] | None,
    full_node_cards: Sequence[Mapping[str, Any]] | None = None,
) -> set[str]:
    """Collect strings legitimately surfaced by deterministic cards / full node cards.

    These come from the file itself (headings, symbols, imports, top_terms,
    evidence snippets, exact mentions, verb cues, domain tags, deterministic
    signals). If a baseline evidence string also appears in cards, the
    occurrence in the prompt is card-derived, not baseline-derived.

    The slim-card view in ``deterministic_cases`` is truncated for prompt
    economy (`headings[:8]`, `symbols[:12]`, etc.). ``full_node_cards`` are
    consulted unwrapped so safe-string filtering is not fooled by truncation.
    """

    safe: set[str] = set()

    def _absorb(values: Iterable[Any]) -> None:
        for value in values:
            if isinstance(value, Mapping):
                for inner_key in ("text", "phrase", "label", "snippet"):
                    inner = value.get(inner_key)
                    if isinstance(inner, str):
                        safe.add(inner.strip())
            else:
                safe.add(str(value).strip())

    for case in deterministic_cases or []:
        if not isinstance(case, Mapping):
            continue
        for card_key in ("source_card", "target_card"):
            card = case.get(card_key) or {}
            if not isinstance(card, Mapping):
                continue
            for field in _CARD_STRING_FIELDS_SLIM:
                values = card.get(field) or []
                if isinstance(values, list):
                    _absorb(values)
        relation = case.get("relation_card") or {}
        if isinstance(relation, Mapping):
            for field in ("deterministic_signals", "possible_verbs_from_signals", "negative_warnings"):
                _absorb(relation.get(field) or [])

    for card in full_node_cards or []:
        if not isinstance(card, Mapping):
            continue
        for field in _CARD_STRING_FIELDS_FULL:
            values = card.get(field) or []
            if isinstance(values, list):
                _absorb(values)

    safe.discard("")
    return safe


def detect_baseline_leakage(
    prompt_text: str,
    baseline: Mapping[str, Any],
    *,
    extra_sentinels: Iterable[str] = (),
    deterministic_cases: Sequence[Mapping[str, Any]] | None = None,
    full_node_cards: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, list[str]]:
    """Scan a built prompt for baseline label / evidence text leakage.

    Returns a dict with two lists:

    - ``leaked_evidence``: baseline evidence/evidence_phrase/rationale/notes
      strings that appear verbatim in the prompt **and** are not also surfaced
      by the deterministic cards (when provided). The deterministic-card
      filter prevents false positives where a baseline reviewer cited a real
      file heading or symbol that the prompt legitimately exposes.
    - ``leaked_verbs``: baseline ``connector_verb`` values that appear in the
      prompt on the same line as their own ``(source, target)`` endpoint
      (excluding the legal-verb allowlist line).

    ``extra_sentinels`` are scanned unconditionally — synthetic test sentinels
    bypass the safe-set so the leakage discipline test stays meaningful.
    """

    leaked_evidence: list[str] = []
    leaked_verbs: list[str] = []
    haystack = prompt_text or ""
    safe_strings = _safe_strings_from_cases(deterministic_cases, full_node_cards)
    safe_corpus = "\n".join(safe_strings)

    for snippet in extra_sentinels:
        text = str(snippet)
        if text and text in haystack:
            leaked_evidence.append(text)

    decisions = baseline.get("routing_decisions") if isinstance(baseline, Mapping) else None
    if isinstance(decisions, list):
        for decision in decisions:
            if not isinstance(decision, Mapping):
                continue
            for evidence_field in ("evidence_set", "evidence_phrases", "rationale", "notes"):
                values = decision.get(evidence_field)
                items: list[str] = []
                if isinstance(values, list):
                    items = [str(v).strip() for v in values]
                elif isinstance(values, str):
                    items = [values.strip()]
                for text in items:
                    if not text or text in _SCHEMA_PLACEHOLDERS:
                        continue
                    if len(text) < 8:
                        continue
                    if text in safe_strings or text in safe_corpus:
                        continue
                    if text in haystack:
                        leaked_evidence.append(text)
            verb = str(decision.get("connector_verb") or "")
            source = str(decision.get("source") or "")
            target = str(decision.get("target") or "")
            if verb and source and target and source in haystack and target in haystack:
                for line in haystack.splitlines():
                    if (source in line or target in line) and verb in line and "allowlist" not in line.lower():
                        leaked_verbs.append(f"{source}->{target}:{verb}")
                        break

    return {
        "leaked_verbs": sorted(set(leaked_verbs)),
        "leaked_evidence": sorted(set(leaked_evidence)),
    }


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------


_KNOWN_BOUNDARY_PAIRS: tuple[tuple[str, str], ...] = (
    ("governs", "populates"),
    ("governs", "evidences"),
    ("audits", "evidences"),
    ("feeds", "populates"),
    ("invalidates", "supersedes"),
    ("invalidates", "blocks"),
    ("supersedes", "blocks"),
    ("compresses", "evidences"),
    ("routes_to", "feeds"),
)


def _normalize_decision(entry: Mapping[str, Any]) -> dict[str, Any]:
    """Coerce either operator-court or legacy verb_correction shape into a normalized dict."""

    graph_behavior = entry.get("graph_behavior") or {}
    if not isinstance(graph_behavior, Mapping):
        graph_behavior = {}

    dominant = (
        entry.get("dominant_rosetta_verb")
        or entry.get("connector_verb")
        or entry.get("dominant_verb")
        or ""
    )
    latent = entry.get("latent_plausible_verbs") or []
    if not isinstance(latent, list):
        latent = []
    runners = entry.get("runner_up_verbs") or []
    if not isinstance(runners, list):
        runners = []
    return {
        "pair_id": str(entry.get("pair_id") or ""),
        "source": str(entry.get("source") or ""),
        "target": str(entry.get("target") or ""),
        "dominant_rosetta_verb": str(dominant),
        "latent_plausible_verbs": [str(v) for v in latent],
        "relation_family": str(entry.get("relation_family") or ""),
        "dominance_rule_applied": str(entry.get("dominance_rule_applied") or ""),
        "runner_up_verbs": [str(v) for v in runners],
        "needs_more_evidence": bool(entry.get("needs_more_evidence")),
        "needs_new_rule": bool(entry.get("needs_new_rule")),
        "graph_behavior": dict(graph_behavior),
    }


def classify_failure_level(
    decision: Mapping[str, Any],
    expected_verb: str,
    grammar: Mapping[str, Any],
) -> int:
    """Classify a single decision's failure level.

    Returns:
        0 — invalid verb (dominant not in allowlist)
        1 — expected verb absent from latent and dominant
        2 — expected verb latent but dominant family is wrong
        3 — expected verb latent, family right, dominance choice wrong
        4 — expected verb is the dominant verb
    """

    legal = set(base_verbs(grammar))
    families = build_relation_families(grammar)
    verb_to_family = {v: f for f, vs in families.items() for v in vs}

    normalized = _normalize_decision(decision)
    dominant = normalized["dominant_rosetta_verb"]
    latent = set(normalized["latent_plausible_verbs"])

    if dominant not in legal:
        return 0
    if expected_verb == dominant:
        return 4
    if expected_verb not in latent:
        return 1
    expected_family = verb_to_family.get(expected_verb)
    dominant_family = verb_to_family.get(dominant)
    if expected_family and dominant_family and expected_family != dominant_family:
        return 2
    return 3


def score_operator_court_output(
    output: Mapping[str, Any],
    baseline_decisions: Sequence[Mapping[str, Any]],
    grammar: Mapping[str, Any],
    *,
    prior_guesses: Mapping[tuple[str, str], str] | None = None,
) -> dict[str, Any]:
    """Score a worker output against the baseline.

    ``output`` may carry either ``relation_label_decisions`` (operator-court v1)
    or ``verb_corrections`` (legacy). Both are normalized.

    ``baseline_decisions`` is a list of {source, target, connector_verb} dicts —
    typically ``baseline['routing_decisions']``.

    Returns a dict containing every metric named in the plan, plus a
    confusion matrix and failure-level counts.
    """

    legal = set(base_verbs(grammar))
    families = build_relation_families(grammar)
    verb_to_family = {v: f for f, vs in families.items() for v in vs}
    rule_ids = known_dominance_rule_ids(grammar) | {"none"}

    raw_entries: list[Mapping[str, Any]] = []
    decisions = output.get("relation_label_decisions")
    if isinstance(decisions, list):
        raw_entries.extend(d for d in decisions if isinstance(d, Mapping))
    legacy = output.get("verb_corrections")
    if isinstance(legacy, list):
        raw_entries.extend(d for d in legacy if isinstance(d, Mapping))
    ambiguous = output.get("ambiguous_cases") or []
    if not isinstance(ambiguous, list):
        ambiguous = []

    baseline_index: dict[tuple[str, str], str] = {}
    for row in baseline_decisions or []:
        if not isinstance(row, Mapping):
            continue
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        verb = str(row.get("connector_verb") or "")
        if source and target and verb:
            baseline_index[(source, target)] = verb

    decision_count = len(raw_entries)
    pair_match_count = 0
    valid_verb_count = 0
    exact_match_count = 0
    dominant_correct = 0
    family_correct = 0
    rule_id_correct = 0
    expected_in_latent_or_dominant = 0
    runner_up_contains_expected = 0
    prior_agreement = 0
    abstain_count = 0
    needs_more_evidence_count = 0
    unknown_dominance_rule = 0
    boundary_confusion = 0
    failure_levels = {
        "0_invalid_verb": 0,
        "1_expected_absent_from_latent": 0,
        "2_wrong_family": 0,
        "3_expected_latent_wrong_dominant": 0,
        "4_expected_dominant": 0,
    }
    per_verb_confusion: dict[str, dict[str, int]] = {}

    for entry in raw_entries:
        normalized = _normalize_decision(entry)
        source = normalized["source"]
        target = normalized["target"]
        dominant = normalized["dominant_rosetta_verb"]
        latent = set(normalized["latent_plausible_verbs"])
        runner_ups = set(normalized["runner_up_verbs"])

        if dominant in legal:
            valid_verb_count += 1
        if normalized["needs_more_evidence"] or not dominant:
            abstain_count += 1
        if normalized["needs_more_evidence"]:
            needs_more_evidence_count += 1

        rule_applied = normalized["dominance_rule_applied"]
        if rule_applied and rule_applied not in rule_ids and not normalized["needs_new_rule"]:
            unknown_dominance_rule += 1

        if (source, target) not in baseline_index:
            continue
        pair_match_count += 1
        expected_verb = baseline_index[(source, target)]

        if dominant == expected_verb:
            exact_match_count += 1
            dominant_correct += 1

        expected_family = verb_to_family.get(expected_verb)
        dominant_family_value = verb_to_family.get(dominant)
        if expected_family and expected_family == normalized["relation_family"]:
            family_correct += 1

        if rule_applied and _expected_rule_for_pair(expected_verb, expected_family, grammar) == rule_applied:
            rule_id_correct += 1

        if expected_verb == dominant or expected_verb in latent:
            expected_in_latent_or_dominant += 1
        if expected_verb in runner_ups:
            runner_up_contains_expected += 1

        if prior_guesses is not None:
            prior = prior_guesses.get((source, target))
            if prior and prior == dominant:
                prior_agreement += 1

        if dominant and expected_verb and dominant != expected_verb:
            confusion_row = per_verb_confusion.setdefault(expected_verb, {})
            confusion_row[dominant] = confusion_row.get(dominant, 0) + 1
            if _is_known_boundary(expected_verb, dominant) or _is_known_boundary(dominant, expected_verb):
                boundary_confusion += 1
            if expected_family and dominant_family_value and expected_family != dominant_family_value:
                pass  # already accounted for in failure level

        level = classify_failure_level(entry, expected_verb, grammar)
        key = {
            0: "0_invalid_verb",
            1: "1_expected_absent_from_latent",
            2: "2_wrong_family",
            3: "3_expected_latent_wrong_dominant",
            4: "4_expected_dominant",
        }[level]
        failure_levels[key] += 1

    def _ratio(numer: int, denom: int) -> float:
        return round(numer / denom, 4) if denom else 0.0

    return {
        "decision_count": decision_count,
        "pair_match_count": pair_match_count,
        "exact_match_count": exact_match_count,
        "ambiguous_count": len(ambiguous),
        "abstain_count": abstain_count,
        "valid_verb_rate": _ratio(valid_verb_count, decision_count),
        "verb_accuracy_given_pair": _ratio(exact_match_count, pair_match_count),
        "dominant_operator_accuracy": _ratio(dominant_correct, pair_match_count),
        "relation_family_accuracy": _ratio(family_correct, pair_match_count),
        "dominance_rule_accuracy": _ratio(rule_id_correct, pair_match_count),
        "expected_in_latent_or_dominant_rate": _ratio(expected_in_latent_or_dominant, pair_match_count),
        "runner_up_contains_expected_rate": _ratio(runner_up_contains_expected, pair_match_count),
        "prior_agreement_rate": _ratio(prior_agreement, pair_match_count) if prior_guesses else 0.0,
        "needs_more_evidence_rate": _ratio(needs_more_evidence_count, decision_count),
        "boundary_confusion_rate": _ratio(boundary_confusion, pair_match_count),
        "unknown_dominance_rule_count": unknown_dominance_rule,
        "per_verb_confusion": per_verb_confusion,
        "failure_level_counts": failure_levels,
    }


def _is_known_boundary(verb_a: str, verb_b: str) -> bool:
    return (verb_a, verb_b) in _KNOWN_BOUNDARY_PAIRS


def _expected_rule_for_pair(
    expected_verb: str,
    expected_family: str | None,
    grammar: Mapping[str, Any],
) -> str | None:
    """Best-effort: find the dominance rule whose `prefer` matches the expected verb.

    Used for `dominance_rule_accuracy`. Heuristic — not all baseline answers must
    have a single matching rule; in that case rule_id_correct stays 0 for that
    pair, which is the honest answer.
    """

    for rule in build_dominance_rules(grammar):
        if str(rule.get("prefer") or "") == expected_verb:
            return str(rule.get("id") or "")
        if expected_family and str(rule.get("prefer_family") or "") == expected_family:
            return str(rule.get("id") or "")
    return None


# ---------------------------------------------------------------------------
# appeals / ontology smells
# ---------------------------------------------------------------------------


def _appeal_id(run_id: str, source: str, target: str, expected: str, dominant: str) -> str:
    digest = hashlib.sha1(
        f"{run_id}\0{source}\0{target}\0{expected}\0{dominant}".encode("utf-8")
    ).hexdigest()[:16]
    return f"oca_{digest}"


def _smell_kind_for_failure(
    normalized: Mapping[str, Any],
    expected_verb: str,
    failure_level: int,
) -> str:
    if normalized.get("needs_more_evidence") or not normalized.get("dominant_rosetta_verb"):
        return "evidence_gap"
    if normalized.get("needs_new_rule"):
        return "missing_dominance_rule"
    if failure_level == 3:
        return "missing_dominance_rule"
    if failure_level in {0, 2}:
        return "verb_family_gap"
    if failure_level == 1:
        return "authority_plane_gap"
    if not expected_verb:
        return "baseline_challenge"
    return "authority_plane_gap"


def _candidate_rule_patch(
    *,
    expected_verb: str,
    dominant_verb: str,
    smell_kind: str,
    grammar: Mapping[str, Any],
) -> dict[str, Any] | None:
    if smell_kind != "missing_dominance_rule" or not expected_verb:
        return None
    expected_family = family_for_verb(grammar, expected_verb)
    patch: dict[str, Any] = {
        "kind": "dominance_rule_candidate",
        "prefer": expected_verb,
        "reason": "Candidate generated from operator-court appeal; controller must review before statute mutation.",
    }
    if dominant_verb:
        patch["over"] = [dominant_verb]
    if expected_family:
        patch["prefer_family"] = expected_family
    return patch


def build_operator_court_appeals(
    output: Mapping[str, Any],
    baseline_decisions: Sequence[Mapping[str, Any]],
    grammar: Mapping[str, Any],
    *,
    run_id: str,
    packet_variant: str,
    provider_model: str,
    evidence_refs: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Build controller-review appeal rows for failed adjudication decisions.

    Appeals are diagnostic rows only. They do not mutate the Rosetta grammar,
    baseline, route graph, accepted edges, or doctrine.
    """

    baseline_index: dict[tuple[str, str], str] = {}
    for row in baseline_decisions or []:
        if not isinstance(row, Mapping):
            continue
        source = str(row.get("source") or "")
        target = str(row.get("target") or "")
        verb = str(row.get("connector_verb") or "")
        if source and target and verb:
            baseline_index[(source, target)] = verb

    raw_entries: list[Mapping[str, Any]] = []
    decisions = output.get("relation_label_decisions")
    if isinstance(decisions, list):
        raw_entries.extend(d for d in decisions if isinstance(d, Mapping))
    legacy = output.get("verb_corrections")
    if isinstance(legacy, list):
        raw_entries.extend(d for d in legacy if isinstance(d, Mapping))

    appeals: list[dict[str, Any]] = []
    for entry in raw_entries:
        normalized = _normalize_decision(entry)
        source = normalized["source"]
        target = normalized["target"]
        expected = baseline_index.get((source, target))
        if not expected:
            continue
        level = classify_failure_level(entry, expected, grammar)
        if level == 4:
            continue
        dominant = normalized["dominant_rosetta_verb"]
        smell_kind = _smell_kind_for_failure(normalized, expected, level)
        appeals.append(
            {
                "appeal_id": _appeal_id(run_id, source, target, expected, dominant),
                "run_id": run_id,
                "packet_variant": packet_variant,
                "provider_model": provider_model,
                "pair_id": normalized["pair_id"],
                "source": source,
                "target": target,
                "expected_verb": expected,
                "dominant_rosetta_verb": dominant,
                "latent_plausible_verbs": normalized["latent_plausible_verbs"],
                "failure_level": {
                    0: "0_invalid_verb",
                    1: "1_expected_absent_from_latent",
                    2: "2_wrong_family",
                    3: "3_expected_latent_wrong_dominant",
                }.get(level, str(level)),
                "dominance_rule_applied": normalized["dominance_rule_applied"],
                "smell_kind": smell_kind,
                "candidate_rule_patch": _candidate_rule_patch(
                    expected_verb=expected,
                    dominant_verb=dominant,
                    smell_kind=smell_kind,
                    grammar=grammar,
                ),
                "evidence_refs": dict(evidence_refs or {}),
                "status": APPEAL_STATUS_PENDING,
            }
        )
    return appeals


def build_leakage_appeal(
    *,
    run_id: str,
    packet_variant: str,
    provider_model: str,
    leakage_check: Mapping[str, Any],
    evidence_refs: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    leaked_verbs = list(leakage_check.get("leaked_verbs") or [])
    leaked_evidence = list(leakage_check.get("leaked_evidence") or [])
    if not leaked_verbs and not leaked_evidence:
        return None
    digest = hashlib.sha1(
        f"{run_id}\0{packet_variant}\0{leaked_verbs}\0{leaked_evidence}".encode("utf-8")
    ).hexdigest()[:16]
    return {
        "appeal_id": f"oca_{digest}",
        "run_id": run_id,
        "packet_variant": packet_variant,
        "provider_model": provider_model,
        "pair_id": "",
        "source": "",
        "target": "",
        "expected_verb": "",
        "dominant_rosetta_verb": "",
        "latent_plausible_verbs": [],
        "failure_level": "leakage_risk",
        "dominance_rule_applied": "",
        "smell_kind": "leakage_risk",
        "candidate_rule_patch": None,
        "evidence_refs": {
            **dict(evidence_refs or {}),
            "leaked_verbs": leaked_verbs,
            "leaked_evidence": leaked_evidence,
        },
        "status": APPEAL_STATUS_PENDING,
    }
