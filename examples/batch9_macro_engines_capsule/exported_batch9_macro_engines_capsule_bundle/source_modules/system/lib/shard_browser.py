"""
[PURPOSE]
- Teleology: Provide the kernel-lib query surface for shard envelopes so agents can browse, filter, and resolve extracted shard records or family raw-seed shards without reading raw shard files and phase directories by hand.
- Mechanism: Discover candidate shard surfaces from orchestration, active-phase, and family raw-seed hints, resolve the preferred shard file, normalize the loaded envelope into one browse contract, and expose a queryable `ShardIndex` wrapper with filtering, ranked query neighborhoods, and browser-index projections.
- Non-goal: Generate shard receipts, mutate shard content, or run the CLI UX; those remain in adjacent factory or kernel surfaces.

[INTERFACE]
- Exports: `discover_shard_surfaces`, `resolve_shards_path`, `load_shards`, `find_default_shards_path`, and `ShardIndex`.
- Reads: `extracted_shards.json` files under active phase, family root, or recent phase directories plus `raw_seed/raw_seed_shards.json`, `raw_seed.json`, orchestration state, and explicit-active phase markers.
- Writes: None.
- Schema: `discover_shard_surfaces()` returns prioritized surface cards; `load_shards()` returns a `ShardIndex`; `ShardIndex` methods return shard lists, single shard dicts, ranked query payloads, or grouped index/summary projections.

[FLOW]
- Inspect orchestration and explicit-active phase markers -> assemble prioritized shard-surface candidates -> resolve the preferred shard file -> load and normalize the shard envelope -> expose list/search/neighborhood/index/query views over the loaded shards.
- When-needed: Open when shard browsing needs the library surface behind `kernel --shards` or the factory shard-browser CLI instead of reading raw shard envelopes and orchestration files separately.
- Escalates-to: tools/meta/factory/shard_browser.py; system/lib/phase_activation.py
- Couples: `tools/meta/factory/shard_browser.py`, `tools/meta/factory/materialize_shard_batches.py`, and kernel shard commands depend on this module's surface-discovery order and `ShardIndex` projection shapes.
- Navigation-group: kernel_lib

[DEPENDENCIES]
- json: Deserialize shard and orchestration envelopes.
- pathlib.Path: Resolve repo-relative family, phase, and shard-surface paths.
- typing.Mapping: Validate mapping-shaped orchestration and shard payloads.

[CONSTRAINTS]
- Guarantee: Missing or unreadable shard/orchestration files degrade to omitted surfaces or `None` instead of raising from the public browsing entrypoints.
- Orders: Surface ranking is deterministic for stable filesystem state because it sorts by existence, priority, mtime, and path.
- Fails: None for missing shard files on the public discovery/load path; callers receive `None` or empty summaries instead.
- Non-goal: This module does not validate shard semantics beyond the envelope and query helpers it exposes.
"""
from __future__ import annotations

import copy
import json
import re
import shlex
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from system.lib.shard_holographic_compression import holographic_compressions_for_shards
from system.lib.shard_paper_module_coverage import paper_module_cross_section_for_shards

REPO_ROOT = Path(__file__).resolve().parents[2]

# Discovery walks several candidate shard surfaces and parses each JSON to
# count shards — ~1.2s per call cold. Cache by repo_root+family_root; mtimes
# on the individual files are NOT re-checked inside the TTL. A short TTL keeps
# the "someone just extracted new shards" case responsive.
_DISCOVER_CACHE: dict[tuple[str, str], tuple[float, list[dict[str, Any]]]] = {}
_DISCOVER_CACHE_LOCK = threading.Lock()
_DISCOVER_CACHE_TTL_S = 20.0

EXTRACTED_SHARDS_FILENAME = "extracted_shards.json"
RAW_SEED_SHARDS_RELATIVE_PATH = Path("raw_seed") / "raw_seed_shards.json"
RAW_SEED_JSON_FILENAME = "raw_seed.json"
FAMILY_ROOT_DEFAULT_RELATIVE_PATH = (
    Path("obsidian/okay lets do this")
    / "09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine"
)
DEFAULT_SHARDS_RELATIVE_PATH = (
    FAMILY_ROOT_DEFAULT_RELATIVE_PATH / EXTRACTED_SHARDS_FILENAME
)
FAMILY_ROOT_DEFAULT = REPO_ROOT / FAMILY_ROOT_DEFAULT_RELATIVE_PATH
DEFAULT_SHARDS_PATH = REPO_ROOT / DEFAULT_SHARDS_RELATIVE_PATH
QUERY_RANKING_MODE = "multi_axis_deterministic_v1"
REVIEW_PLANE_HINT_SPECS: dict[str, dict[str, Any]] = {
    "paper_module": {
        "description": "Subsystem or browse-surface truth that should refresh or author a paper module.",
        "tokens": {
            "actual",
            "code",
            "current",
            "existing",
            "fact",
            "facts",
            "file",
            "files",
            "implemented",
            "module",
            "modules",
            "ontology",
            "paper",
            "subsystem",
            "system",
        },
        "weights": {"paper": 3, "module": 3, "modules": 3, "subsystem": 2, "facts": 2},
    },
    "principle": {
        "description": "General independent rule or invariant that should route through principle curation.",
        "tokens": {
            "general",
            "generalized",
            "generalised",
            "independent",
            "invariant",
            "policy",
            "principle",
            "principles",
            "rule",
            "rules",
        },
        "weights": {"principle": 3, "principles": 3, "independent": 2, "invariant": 2},
    },
    "skill": {
        "description": "Repeatable procedural move that should refine a skill or routing instruction.",
        "tokens": {
            "entry",
            "flow",
            "procedure",
            "process",
            "repeatable",
            "route",
            "routing",
            "runbook",
            "skill",
            "skills",
            "workflow",
        },
        "weights": {"skill": 3, "skills": 3, "repeatable": 2, "workflow": 2},
    },
    "standard": {
        "description": "Schema or contract rule that should route to a standard.",
        "tokens": {
            "contract",
            "json",
            "schema",
            "standard",
            "standards",
            "validator",
        },
        "weights": {"schema": 3, "standard": 3, "standards": 3, "contract": 2},
    },
    "annex_pattern": {
        "description": "External or annex-inspired pattern transfer, not imported substrate.",
        "tokens": {
            "annex",
            "annexes",
            "external",
            "github",
            "hermes",
            "inspiration",
            "pattern",
            "patterns",
            "socraticode",
            "steal",
            "upstream",
        },
        "weights": {"annex": 3, "annexes": 3, "pattern": 2, "patterns": 2, "steal": 2},
    },
    "raw_evidence": {
        "description": "Voice or paragraph evidence that should remain raw-seed-grounded before curation.",
        "tokens": {
            "anchor",
            "evidence",
            "paragraph",
            "paragraphs",
            "raw",
            "seed",
            "source",
            "voice",
        },
        "weights": {"raw": 2, "seed": 2, "voice": 2, "evidence": 2},
    },
}


def _load_json(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for value in values:
        token = _string(value)
        if token and token not in normalized:
            normalized.append(token)
    return normalized


def _mapping_list(values: Any) -> list[dict[str, Any]]:
    if not isinstance(values, list):
        return []
    normalized: list[dict[str, Any]] = []
    for value in values:
        if isinstance(value, Mapping):
            normalized.append(dict(value))
    return normalized


def _rel(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def _tokenize(text: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_]+", _string(text).lower())
        if token
    }


def _value_texts(values: Any) -> list[str]:
    if isinstance(values, Mapping):
        texts: list[str] = []
        for value in values.values():
            texts.extend(_value_texts(value))
        return texts
    if isinstance(values, list):
        texts: list[str] = []
        for value in values:
            texts.extend(_value_texts(value))
        return texts
    token = _string(values)
    return [token] if token else []


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _quote_cli(value: Any) -> str:
    return shlex.quote(_string(value))


def _review_plane_hints_from_tokens(tokens: set[str], *, limit: int = 4) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for plane, spec in REVIEW_PLANE_HINT_SPECS.items():
        plane_tokens = set(spec.get("tokens") or set())
        signals = sorted(tokens & plane_tokens)
        if not signals:
            continue
        weights = spec.get("weights") if isinstance(spec.get("weights"), Mapping) else {}
        score = sum(int(weights.get(signal, 1)) for signal in signals)
        hints.append(
            {
                "plane": plane,
                "score": score,
                "signals": signals[:8],
                "description": _string(spec.get("description")),
            }
        )
    hints.sort(key=lambda item: (-int(item.get("score") or 0), _string(item.get("plane"))))
    return hints[:limit] if limit > 0 else hints


def _review_plane_hints_for_shard(
    shard: Mapping[str, Any],
    *,
    matched_terms: list[str] | None = None,
) -> list[dict[str, Any]]:
    texts: list[str] = []
    for key in (
        "clarified_statement",
        "statement",
        "gloss",
        "text",
        "voice_anchor",
        "support_excerpt",
        "raw_seed_anchor",
        "routing_state",
        "coverage_state",
        "status",
    ):
        texts.extend(_value_texts(shard.get(key)))
    for key in (
        "gestures_towards",
        "idea_group_ids",
        "concept_ids",
        "mechanism_ids",
        "routing_targets",
        "relevant_files",
    ):
        texts.extend(_value_texts(shard.get(key)))
    tokens = _tokenize(" ".join(texts))
    for term in matched_terms or []:
        tokens.update(_tokenize(term))
    return _review_plane_hints_from_tokens(tokens)


def _merge_review_plane_hints(hints: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for hint in hints:
        if not isinstance(hint, Mapping):
            continue
        plane = _string(hint.get("plane"))
        if not plane:
            continue
        entry = merged.setdefault(
            plane,
            {
                "plane": plane,
                "score": 0,
                "signals": set(),
                "description": _string(hint.get("description")),
            },
        )
        entry["score"] += int(hint.get("score") or 0)
        if not entry.get("description"):
            entry["description"] = _string(hint.get("description"))
        for signal in hint.get("signals") or []:
            token = _string(signal)
            if token:
                entry["signals"].add(token)
    rows = [
        {
            "plane": plane,
            "score": int(entry.get("score") or 0),
            "signals": sorted(entry.get("signals") or [])[:10],
            "description": _string(entry.get("description")),
        }
        for plane, entry in merged.items()
    ]
    rows.sort(key=lambda item: (-int(item.get("score") or 0), _string(item.get("plane"))))
    return rows[:limit] if limit > 0 else rows


def _review_plane_summary_for_rows(rows: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    hints: list[dict[str, Any]] = []
    for row in rows:
        hints.extend([dict(hint) for hint in row.get("review_plane_hints") or [] if isinstance(hint, Mapping)])
    return _merge_review_plane_hints(hints, limit=limit)


SYNTHESIS_ROLES = {
    "evidence",
    "central_claim",
    "support",
    "tension",
    "open_question",
    "route_hint",
}


def _primary_review_plane_from_hints(hints: list[dict[str, Any]]) -> str:
    if hints:
        plane = _string(hints[0].get("plane"))
        if plane:
            return plane
    return "raw_evidence"


def _synthesis_role_for_shard(
    shard: Mapping[str, Any],
    *,
    review_plane_hints: list[dict[str, Any]] | None = None,
) -> str:
    explicit = _string(shard.get("synthesis_role"))
    if explicit in SYNTHESIS_ROLES:
        return explicit
    statement = _shard_statement_text(shard)
    lowered = " ".join(
        [
            statement,
            _string(shard.get("voice_anchor")),
            " ".join(_string_list(shard.get("gestures_towards"))),
        ]
    ).lower()
    top_plane = _primary_review_plane_from_hints(review_plane_hints or [])
    if "?" in statement or any(
        marker in lowered
        for marker in (
            "maybe",
            "unclear",
            "unknown",
            "figure out",
            "something like",
            "or something",
        )
    ):
        return "open_question"
    if any(
        marker in lowered
        for marker in (
            "not ",
            " instead",
            "but ",
            "however",
            "contradict",
            "wrong",
            "against",
        )
    ):
        return "tension"
    if top_plane != "raw_evidence" and (
        (_string(shard.get("routing_state")) or "pending") in {"pending", "needs_codex", "surface_to_codex"}
        or any(marker in lowered for marker in ("route", "routing", "should", "must", "need"))
    ):
        return "route_hint"
    if top_plane in {"principle", "paper_module", "skill", "standard", "annex_pattern"}:
        return "central_claim"
    if _string(shard.get("support_excerpt")):
        return "support"
    return "evidence"


def enrich_shard_routing_metadata(
    shard: Mapping[str, Any],
    *,
    matched_terms: list[str] | None = None,
) -> dict[str, Any]:
    row = dict(shard)
    hints = _review_plane_hints_for_shard(row, matched_terms=matched_terms)
    primary_plane = _primary_review_plane_from_hints(hints)
    row["review_plane_hints"] = hints
    row["primary_review_plane"] = primary_plane
    row["primary_review_plane_score"] = int(hints[0].get("score") or 0) if hints else 0
    row["synthesis_role"] = _synthesis_role_for_shard(row, review_plane_hints=hints)
    return row


def _group_next_actions(group_id: str) -> list[dict[str, Any]]:
    group_token = _quote_cli(group_id)
    return [
        {
            "action_id": f"expand_group:{group_id}",
            "kind": "deterministic_expand",
            "why": "Expand the grouped shard bin locally before spending model calls.",
            "command": f"python3 kernel.py --shards --shards-source family --shards-group {group_token} --shards-limit 12 --shards-packet",
        },
        {
            "action_id": f"prepare_group_compression:{group_id}",
            "kind": "bounded_compression_prep",
            "why": "Prepare the bounded local NVIDIA/bridge compression packet only if deterministic expansion is too thin.",
            "command": f"python3 kernel.py --raw-seed-navigation-prepare 09 --raw-seed-nav-group {group_token}",
        },
        {
            "action_id": f"open_runtime_group:{group_id}",
            "kind": "runtime_graph_reopen",
            "why": "Reopen the compressed raw-seed runtime graph around this group.",
            "command": f"python3 kernel.py --raw-seed-navigation-runtime 09 --raw-seed-nav-group {group_token}",
        },
    ]


def _plane_next_action(plane_hint: Mapping[str, Any], *, query: str) -> dict[str, Any] | None:
    plane = _string(plane_hint.get("plane"))
    if not plane:
        return None
    query_token = _quote_cli(query)
    specs: dict[str, dict[str, Any]] = {
        "paper_module": {
            "action_id": "route_plane:paper_module",
            "kind": "paper_module_truth_check",
            "why": "Paper modules describe verified subsystem facts; inspect or refresh the subsystem browse surface before changing doctrine.",
            "commands": [
                f"python3 kernel.py --paper-module {query_token}",
                "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
            ],
        },
        "principle": {
            "action_id": "route_plane:principle",
            "kind": "principle_curation",
            "why": "Principles should be independent general rules; route candidates through principle curation instead of hand-authoring doctrine.",
            "commands": [
                "python3 kernel.py --docs-route 'principles curation'",
                f"python3 kernel.py --shards --shards-source family --shards-query {query_token} --shards-packet",
            ],
        },
        "skill": {
            "action_id": "route_plane:skill",
            "kind": "skill_refinement",
            "why": "Repeatable procedure belongs in a skill or routing instruction.",
            "commands": [
                "python3 kernel.py --docs-route 'skill authoring'",
                "python3 kernel.py --docs-route 'shard neighborhood routing'",
            ],
        },
        "standard": {
            "action_id": "route_plane:standard",
            "kind": "standard_or_schema_review",
            "why": "Schema-grade constraints belong in standards, not in paper modules or session prose.",
            "commands": [
                "python3 kernel.py --docs-route 'standards'",
                "python3 kernel.py --docs-route 'extracted shards standard'",
            ],
        },
        "annex_pattern": {
            "action_id": "route_plane:annex_pattern",
            "kind": "annex_pattern_transfer",
            "why": "Annex inspiration should transfer as architecture patterns with provenance, not copied substrate.",
            "commands": [
                "python3 kernel.py --docs-route 'annex pattern transfer'",
                f"python3 kernel.py --route-query {query_token} --embed-kind annex_notes --embed-top-k 8",
            ],
        },
        "raw_evidence": {
            "action_id": "route_plane:raw_evidence",
            "kind": "raw_seed_evidence_pull",
            "why": "Keep voice evidence grounded in raw-seed paragraphs before any curation or apply lane.",
            "commands": [
                f"python3 kernel.py --raw-seed-browse 09 --query {query_token}",
                f"python3 kernel.py --raw-seed-query 09 --query {query_token}",
            ],
        },
    }
    spec = specs.get(plane)
    if spec is None:
        return None
    return {
        **spec,
        "plane": plane,
        "score": int(plane_hint.get("score") or 0),
        "signals": list(plane_hint.get("signals") or [])[:8],
    }


def _selector_arg_parts(selector: Mapping[str, Any] | None) -> list[str]:
    if not isinstance(selector, Mapping):
        return []
    flag_map = {
        "status": "--shards-status",
        "concept": "--shards-concept",
        "mechanism": "--shards-mechanism",
        "group": "--shards-group",
        "anchor": "--shards-anchor",
        "paragraph": "--shards-paragraph",
        "query": "--shards-query",
    }
    parts: list[str] = []
    for key, flag in flag_map.items():
        value = _string(selector.get(key))
        if value:
            parts.extend([flag, _quote_cli(value)])
    return parts


def _selector_label(selector: Mapping[str, Any] | None, *, fallback: str) -> str:
    if isinstance(selector, Mapping):
        for key in ("query", "group", "paragraph", "anchor", "concept", "mechanism", "status"):
            value = _string(selector.get(key))
            if value:
                return value if key == "query" else f"{key}:{value}"
    return _string(fallback)


def _build_next_action_graph(
    *,
    query: str,
    primary: list[dict[str, Any]],
    group_summaries: list[dict[str, Any]],
    review_plane_summary: list[dict[str, Any]],
    ungrouped_primary_count: int,
    selector: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    top_group_ids = [
        _string(group.get("group_id"))
        for group in group_summaries[:3]
        if _string(group.get("group_id"))
    ]
    top_primary_ids = [
        _string(row.get("shard_id"))
        for row in primary[:5]
        if _string(row.get("shard_id"))
    ]
    actions: list[dict[str, Any]] = []
    for plane_hint in review_plane_summary[:4]:
        action = _plane_next_action(plane_hint, query=query)
        if action:
            actions.append(action)
    if top_group_ids:
        for action in _group_next_actions(top_group_ids[0]):
            actions.append(
                {
                    **action,
                    "group_id": top_group_ids[0],
                    "priority": "first_group",
                }
            )
    selector_payload = {
        key: _string(value)
        for key, value in (selector or {"query": query}).items()
        if _string(value)
    }
    selector_parts = _selector_arg_parts(selector_payload)
    if selector_parts:
        selector_keys = {key for key, value in selector_payload.items() if value}
        actions.append(
            {
                "action_id": (
                    "materialize_query_shard_batch"
                    if selector_keys == {"query"}
                    else "materialize_shard_batch"
                ),
                "kind": "bounded_handoff_packet",
                "why": "Materialize the selected slice before asking a worker or smarter agent to route it.",
                "commands": [
                    " ".join(
                        [
                            "python3",
                            "kernel.py",
                            "--materialize-shard-batches",
                            "--shards-source",
                            "family",
                            *selector_parts,
                            "--shard-batch-skip-concept-catalog",
                        ]
                    )
                ],
            }
        )
    else:
        actions.append(
            {
                "action_id": "choose_bounded_selector",
                "kind": "selector_required",
                "why": "Choose a query, group, paragraph, or other bounded selector before materializing a handoff packet.",
                "commands": [
                    "python3 kernel.py --shards --shards-source family --shards-query '<topic>' --shards-packet"
                ],
            }
        )
    return {
        "schema_version": "shard_next_action_graph_v1",
        "basis": {
            "query": _string(query),
            "selector": selector_payload,
            "top_review_planes": [row.get("plane") for row in review_plane_summary[:4]],
            "top_group_ids": top_group_ids,
            "top_primary_shard_ids": top_primary_ids,
            "ungrouped_primary_count": int(ungrouped_primary_count),
        },
        "guardrails": [
            "Run deterministic group expansion before paying model calls.",
            "Treat review-plane actions as routing hints, not doctrine apply decisions.",
            "Use bounded compression prep when the local graph is too thin; do not make NVIDIA the only metabolism path.",
            "Escalate to smarter agents only with a materialized shard batch or prepared compression bundle.",
        ],
        "actions": actions,
    }


def _shard_statement_text(shard: Mapping[str, Any]) -> str:
    return _string(
        shard.get("clarified_statement")
        or shard.get("statement")
        or shard.get("gloss")
        or shard.get("text")
    )


def _clip_text(value: Any, *, limit: int = 220) -> str:
    text = _string(value)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def _humanize_group_id(group_id: str) -> str:
    token = _string(group_id)
    if token.startswith("grp_"):
        token = token[4:]
    token = token.replace("_", " ").strip()
    return token.title() if token else "Ungrouped Idea"


def _score_text_values(
    *,
    query_text: str,
    query_tokens: set[str],
    values: list[str],
) -> tuple[int, list[str]]:
    if not query_text and not query_tokens:
        return 1, []
    score = 0
    matched: set[str] = set()
    for value in values:
        lowered = _string(value).lower()
        if not lowered:
            continue
        if query_text and query_text in lowered:
            score += 8
            matched.update(query_tokens)
        overlap = query_tokens & _tokenize(lowered)
        if overlap:
            score += len(overlap) * 3
            matched.update(overlap)
    return score, sorted(matched)


def _paragraph_preview(paragraph: Mapping[str, Any], *, limit: int = 260) -> str:
    return _clip_text(
        paragraph.get("summary")
        or paragraph.get("plain_text")
        or paragraph.get("raw_markdown"),
        limit=limit,
    )


def _is_substantive_raw_seed_paragraph(paragraph: Mapping[str, Any]) -> bool:
    text = _string(paragraph.get("plain_text") or paragraph.get("raw_markdown"))
    if not text:
        return False
    if text.startswith("<!--") and text.endswith("-->"):
        return False
    return True


def _top_value_rows(
    shards: list[dict[str, Any]],
    field: str,
    *,
    label: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for shard in shards:
        token = _string(shard.get(field))
        if token:
            counts[token] = counts.get(token, 0) + 1
    return [
        {label: value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _top_gesture_rows(shards: list[dict[str, Any]], *, limit: int = 6) -> list[dict[str, Any]]:
    counts: dict[str, int] = {}
    for shard in shards:
        for gesture in _string_list(shard.get("gestures_towards")):
            counts[gesture] = counts.get(gesture, 0) + 1
    return [
        {"gesture": value, "count": count}
        for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:limit]
    ]


def _central_claim_rows(
    shards: list[dict[str, Any]],
    *,
    limit: int = 8,
    compression_by_shard_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shard in shards:
        enriched = enrich_shard_routing_metadata(shard)
        shard_id = _string(enriched.get("id") or enriched.get("shard_id"))
        statement = _shard_statement_text(enriched)
        if not shard_id or not statement:
            continue
        row = {
            "shard_id": shard_id,
            "statement": _clip_text(statement),
            "voice_anchor": _clip_text(enriched.get("voice_anchor"), limit=160),
            "parent_paragraph_id": _string(enriched.get("parent_paragraph_id")),
            "idea_group_ids": _shard_group_ids(enriched)[:4],
            "routing_state": _string(enriched.get("routing_state")),
            "coverage_state": _string(enriched.get("coverage_state")),
            "primary_review_plane": _string(enriched.get("primary_review_plane")),
            "synthesis_role": _string(enriched.get("synthesis_role")),
            "review_plane_hints": list(enriched.get("review_plane_hints") or [])[:3],
        }
        compression_row = (compression_by_shard_id or {}).get(shard_id)
        if isinstance(compression_row, Mapping):
            row["holographic_compression"] = {
                "method": _string(compression_row.get("method")),
                "layers": dict(compression_row.get("layers") or {}),
                "paper_module_context": list(compression_row.get("paper_module_context") or [])[:3],
            }
        rows.append(row)
        if len(rows) >= limit:
            break
    return rows


def _representative_idea_rows(shards: list[dict[str, Any]], *, limit: int = 4) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for shard in shards:
        enriched = enrich_shard_routing_metadata(shard)
        shard_id = _string(enriched.get("id") or enriched.get("shard_id"))
        statement = _shard_statement_text(enriched)
        if not shard_id or not statement:
            continue
        rows.append(
            {
                "shard_id": shard_id,
                "statement": _clip_text(statement, limit=240),
                "voice_anchor": _clip_text(enriched.get("voice_anchor"), limit=140),
                "parent_paragraph_id": _string(enriched.get("parent_paragraph_id")),
                "primary_review_plane": _string(enriched.get("primary_review_plane")),
                "synthesis_role": _string(enriched.get("synthesis_role")),
            }
        )
        if len(rows) >= limit:
            break
    return rows


def _synthesis_questions(
    *,
    review_plane_summary: list[dict[str, Any]],
    group_summaries: list[dict[str, Any]],
    ungrouped_count: int,
    routing_state_rows: list[dict[str, Any]],
) -> list[str]:
    questions: list[str] = []
    top_plane = _string((review_plane_summary[0] if review_plane_summary else {}).get("plane"))
    if top_plane == "paper_module":
        questions.append("Which present-tense subsystem fact does this evidence support, and is its paper module current?")
    elif top_plane == "principle":
        questions.append("Which independent rule survives after removing system-specific implementation detail?")
    elif top_plane == "skill":
        questions.append("Which repeatable move should the next agent be able to execute without rediscovery?")
    elif top_plane == "standard":
        questions.append("Which schema or validation contract should enforce this pattern?")
    elif top_plane == "annex_pattern":
        questions.append("Which external architectural pattern is being translated, and where is provenance recorded?")
    elif top_plane == "raw_evidence":
        questions.append("Which `par_*` evidence must stay attached before any curation or doctrine lift?")
    if group_summaries:
        questions.append("Should the top idea group be reviewed as one cluster before per-shard routing?")
    if ungrouped_count:
        questions.append("Do the ungrouped primary atoms need a new idea-group bin, or are they intentionally singleton evidence?")
    if any(row.get("routing_state") == "pending" for row in routing_state_rows):
        questions.append("Which pending atoms can be routed now, and which should remain evidence until a stronger plane is clear?")
    return _dedupe_strings(questions)[:6]


def _build_shard_synthesis(
    *,
    label: str,
    shards: list[dict[str, Any]],
    group_summaries: list[dict[str, Any]],
    review_plane_summary: list[dict[str, Any]],
    next_action_graph: Mapping[str, Any] | None = None,
    selector: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    selector_payload = {
        key: _string(value)
        for key, value in (selector or {}).items()
        if _string(value)
    }
    enriched_shards = [enrich_shard_routing_metadata(shard) for shard in shards]
    grouped_count = sum(1 for shard in enriched_shards if _shard_group_ids(shard))
    ungrouped_count = max(0, len(enriched_shards) - grouped_count)
    routing_state_rows = _top_value_rows(enriched_shards, "routing_state", label="routing_state", limit=6)
    coverage_state_rows = _top_value_rows(enriched_shards, "coverage_state", label="coverage_state", limit=6)
    primary_plane_rows = _top_value_rows(
        enriched_shards,
        "primary_review_plane",
        label="primary_review_plane",
        limit=6,
    )
    synthesis_role_rows = _top_value_rows(
        enriched_shards,
        "synthesis_role",
        label="synthesis_role",
        limit=6,
    )
    holographic_compressions = holographic_compressions_for_shards(
        enriched_shards,
        repo_root=REPO_ROOT,
    )
    compression_by_shard_id = {
        _string(item.get("shard_id")): item
        for item in holographic_compressions.get("items") or []
        if isinstance(item, Mapping) and _string(item.get("shard_id"))
    }
    central_claims = _central_claim_rows(
        enriched_shards,
        compression_by_shard_id=compression_by_shard_id,
    )
    strongest_groups = [
        {
            "group_id": _string(group.get("group_id")),
            "member_count": int(group.get("member_count") or group.get("matched_shard_count") or 0),
            "primary_result_count": int(group.get("primary_result_count") or 0),
            "review_plane_hints": list(group.get("review_plane_hints") or [])[:4],
            "representative_shard_ids": list(
                group.get("representative_shard_ids") or group.get("matched_shard_ids") or []
            )[:5],
        }
        for group in group_summaries[:6]
        if _string(group.get("group_id"))
    ]
    action_ids = [
        _string(action.get("action_id"))
        for action in ((next_action_graph or {}).get("actions") or [])
        if isinstance(action, Mapping) and _string(action.get("action_id"))
    ][:8]
    paper_module_cross_section = paper_module_cross_section_for_shards(
        enriched_shards,
        repo_root=REPO_ROOT,
    )
    return {
        "schema_version": "shard_synthesis_v1",
        "purpose": "Bounded conspectus over one selected shard neighborhood; a state-of-mind proxy, not a doctrine mutation.",
        "label": _string(label),
        "selector": selector_payload,
        "summary": {
            "selected_shard_count": len(enriched_shards),
            "grouped_shard_count": grouped_count,
            "ungrouped_shard_count": ungrouped_count,
            "top_review_planes": [row.get("plane") for row in review_plane_summary[:4]],
            "top_group_ids": [row.get("group_id") for row in strongest_groups[:4]],
            "primary_review_plane_counts": primary_plane_rows,
            "synthesis_role_counts": synthesis_role_rows,
            "routing_state_counts": routing_state_rows,
            "coverage_state_counts": coverage_state_rows,
        },
        "paper_module_cross_section": paper_module_cross_section,
        "holographic_compressions": holographic_compressions,
        "dominant_review_planes": review_plane_summary[:6],
        "strongest_groups": strongest_groups,
        "central_claims": central_claims,
        "top_gestures": _top_gesture_rows(shards),
        "latent_questions": _synthesis_questions(
            review_plane_summary=review_plane_summary,
            group_summaries=group_summaries,
            ungrouped_count=ungrouped_count,
            routing_state_rows=routing_state_rows,
        ),
        "action_ladder": action_ids,
        "guardrails": [
            "Read this as a compression over selected shards, not as a replacement for `par_*` evidence.",
            "Paper modules capture verified system facts; principles capture independent rules.",
            "Use group bins before per-shard routing when the group is coherent.",
            "Escalate to NVIDIA, bridge, or subagents only after this bounded local conspectus stops being enough.",
        ],
    }


def _status_summary(shards: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for shard in shards:
        status = _string(shard.get("status")) or "unknown"
        counts[status] = counts.get(status, 0) + 1
    return counts


def _increment_count(counts: dict[str, int], value: Any) -> None:
    token = _string(value)
    if not token:
        return
    counts[token] = counts.get(token, 0) + 1


def _sorted_counts(counts: dict[str, int]) -> dict[str, int]:
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _shard_group_ids(shard: Mapping[str, Any]) -> list[str]:
    groups = _string_list(shard.get("idea_group_ids"))
    for field in ("concept_group", "group"):
        token = _string(shard.get(field))
        if token and token not in groups:
            groups.append(token)
    return groups


def _family_root_for_shards_path(path: Path) -> Path:
    if path.name == EXTRACTED_SHARDS_FILENAME:
        return path.parent
    if (
        path.name == RAW_SEED_SHARDS_RELATIVE_PATH.name
        and path.parent.name == RAW_SEED_SHARDS_RELATIVE_PATH.parent.name
    ):
        return path.parent.parent
    return path.parent


def _default_family_root_relative_path(repo_root: Path = REPO_ROOT) -> Path:
    try:
        from system.lib.phase_lifecycle import resolve_preferred_phase_activation
    except Exception:
        return FAMILY_ROOT_DEFAULT_RELATIVE_PATH
    activation = resolve_preferred_phase_activation(repo_root, eligibility="routing") or {}
    family_dir = _string(activation.get("family_dir"))
    if family_dir:
        return Path(family_dir)
    return FAMILY_ROOT_DEFAULT_RELATIVE_PATH


def _surface_kind(payload: Mapping[str, Any] | None, *, path: Path) -> str:
    if isinstance(payload, Mapping):
        kind = _string(payload.get("kind"))
        if kind:
            return kind
        schema_version = _string(payload.get("schema_version") or payload.get("schema_version_family_shards"))
        if schema_version.startswith("raw_seed_shards"):
            return "raw_seed_shards"
        shards = payload.get("shards")
        if isinstance(shards, list) and shards:
            first = shards[0]
            if isinstance(first, Mapping):
                if _string(first.get("clarified_statement")) or _string(first.get("voice_anchor")):
                    return "extracted_shards"
                if _string(first.get("shard_id")) and not _string(first.get("clarified_statement")):
                    return "raw_seed_shards"
                if _string(first.get("segment_ordinal")) or _string(first.get("source_bin_id")):
                    return "extracted_shards"
    if path.name == RAW_SEED_SHARDS_RELATIVE_PATH.name:
        return "raw_seed_shards"
    return "extracted_shards"


def _load_family_raw_seed_payload(
    payload: Mapping[str, Any],
    *,
    path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    candidates: list[Path] = []
    source = payload.get("source")
    if isinstance(source, Mapping):
        source_path = _string(source.get("raw_seed_json_path"))
        if source_path:
            candidate = Path(source_path)
            if not candidate.is_absolute():
                candidate = repo_root / candidate
            candidates.append(candidate)
    candidates.append(_family_root_for_shards_path(path) / RAW_SEED_JSON_FILENAME)

    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        raw_seed = _load_json(candidate)
        if isinstance(raw_seed, Mapping) and isinstance(raw_seed.get("paragraphs"), list):
            return dict(raw_seed)
    return {}


def _normalize_routing_targets(values: Any) -> list[Any]:
    normalized: list[Any] = []
    if not isinstance(values, list):
        return normalized
    for value in values:
        if isinstance(value, Mapping):
            normalized.append(dict(value))
        else:
            token = _string(value)
            if token:
                normalized.append(token)
    return normalized


def _normalize_raw_seed_shards_payload(
    data: Mapping[str, Any],
    *,
    path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    raw_seed = _load_family_raw_seed_payload(data, path=path, repo_root=repo_root)
    paragraphs = [
        dict(item)
        for item in raw_seed.get("paragraphs", [])
        if isinstance(item, Mapping) and _string(item.get("id"))
    ]
    paragraphs_by_id = {
        _string(item.get("id")): item
        for item in paragraphs
        if _string(item.get("id"))
    }

    normalized_shards: list[dict[str, Any]] = []
    for shard in data.get("shards", []):
        if not isinstance(shard, Mapping):
            continue
        shard_id = _string(shard.get("id") or shard.get("shard_id"))
        if not shard_id:
            continue
        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        parent_paragraph = paragraphs_by_id.get(parent_paragraph_id, {})
        idea_group_ids = _string_list(shard.get("idea_group_ids")) or _string_list(
            parent_paragraph.get("idea_group_ids")
        )
        concept_group = _string(shard.get("concept_group") or shard.get("group"))
        if not concept_group and len(idea_group_ids) == 1:
            concept_group = idea_group_ids[0]

        normalized_shards.append(
            {
                **dict(shard),
                "id": shard_id,
                "shard_id": shard_id,
                "raw_seed_anchor": _string(shard.get("raw_seed_anchor")) or parent_paragraph_id,
                "raw_paragraph_ids": _string_list(shard.get("raw_paragraph_ids"))
                or ([parent_paragraph_id] if parent_paragraph_id else []),
                "concept_ids": _string_list(shard.get("concept_ids")),
                "concept_group": concept_group or None,
                "group": concept_group or None,
                "idea_group_ids": idea_group_ids,
                "mechanisms": _string_list(shard.get("mechanisms"))
                or _string_list(parent_paragraph.get("mechanism_hints")),
                "tags": _string_list(shard.get("tags"))
                or _string_list(parent_paragraph.get("tags")),
                "keyword_hints": _string_list(shard.get("keyword_hints"))
                or _string_list(parent_paragraph.get("keyword_hints")),
                "related_paragraph_ids": _string_list(parent_paragraph.get("related_paragraph_ids")),
                "text": _string(shard.get("text"))
                or _string(parent_paragraph.get("plain_text") or parent_paragraph.get("raw_markdown")),
                "gloss": _string(shard.get("gloss"))
                or _string(parent_paragraph.get("summary") or parent_paragraph.get("note")),
                "statement": _string(shard.get("statement"))
                or _string(parent_paragraph.get("summary") or parent_paragraph.get("plain_text")),
                "plain_text": _string(parent_paragraph.get("plain_text")),
                "paragraph_summary": _string(parent_paragraph.get("summary")),
                "note": _string(parent_paragraph.get("note")),
                "section_id": _string(parent_paragraph.get("section_id"))
                or _string(shard.get("section_id")),
                "section_path": _string(parent_paragraph.get("section_path"))
                or _string(shard.get("section_path")),
                "paragraph_fingerprint": _string(
                    shard.get("paragraph_fingerprint")
                    or parent_paragraph.get("paragraph_fingerprint")
                    or parent_paragraph.get("fingerprint")
                ),
                "routing_targets": _normalize_routing_targets(shard.get("routing_targets")),
                "relevant_files": _string_list(shard.get("relevant_files")),
                "gestures_towards": _string_list(shard.get("gestures_towards")),
            }
        )

    normalized = dict(data)
    normalized["kind"] = "raw_seed_shards"
    normalized["surface_kind"] = "raw_seed_shards"
    normalized["shards"] = normalized_shards
    normalized["raw_seed_json_path"] = _rel(
        _family_root_for_shards_path(path) / RAW_SEED_JSON_FILENAME,
        repo_root=repo_root,
    )
    return normalized


def _normalize_extracted_shards_payload(
    data: Mapping[str, Any],
    *,
    path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    normalized_shards: list[dict[str, Any]] = []
    for shard in data.get("shards", []):
        if not isinstance(shard, Mapping):
            continue
        shard_id = _string(shard.get("id") or shard.get("shard_id"))
        if not shard_id:
            continue

        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        raw_paragraph_ids = _string_list(shard.get("raw_paragraph_ids"))
        if parent_paragraph_id and parent_paragraph_id not in raw_paragraph_ids:
            raw_paragraph_ids.append(parent_paragraph_id)

        clarified_statement = _string(
            shard.get("clarified_statement")
            or shard.get("statement")
            or shard.get("text")
            or shard.get("gloss")
        )
        voice_anchor = _string(shard.get("voice_anchor"))
        support_excerpt = _string(shard.get("support_excerpt")) or voice_anchor
        idea_group_ids = _string_list(shard.get("idea_group_ids"))
        concept_group = _string(shard.get("concept_group") or shard.get("group"))
        if not concept_group and len(idea_group_ids) == 1:
            concept_group = idea_group_ids[0]

        routing_targets = _normalize_routing_targets(shard.get("routing_targets"))
        routing_target_texts = _dedupe_strings(_value_texts(routing_targets))

        normalized_shards.append(
            {
                **dict(shard),
                "id": shard_id,
                "shard_id": shard_id,
                "clarified_statement": clarified_statement,
                "statement": clarified_statement or _string(shard.get("statement")),
                "text": clarified_statement or _string(shard.get("text")),
                "gloss": clarified_statement or _string(shard.get("gloss")),
                "voice_anchor": voice_anchor,
                "support_excerpt": support_excerpt,
                "gestures_towards": _string_list(shard.get("gestures_towards")),
                "routing_state": _string(shard.get("routing_state")),
                "coverage_state": _string(shard.get("coverage_state")),
                "routing_targets": routing_targets,
                "routing_target_texts": routing_target_texts,
                "relevant_files": _string_list(shard.get("relevant_files")),
                "source_bin_id": _string(shard.get("source_bin_id")),
                "source_artifact": _string(shard.get("source_artifact")),
                "parent_paragraph_id": parent_paragraph_id or None,
                "raw_paragraph_ids": raw_paragraph_ids,
                "concept_ids": _string_list(shard.get("concept_ids")),
                "concept_group": concept_group or None,
                "group": concept_group or None,
                "idea_group_ids": idea_group_ids,
                "mechanisms": _string_list(shard.get("mechanisms")),
                "tags": _string_list(shard.get("tags")),
                "keyword_hints": _string_list(shard.get("keyword_hints")),
                "related_paragraph_ids": _string_list(shard.get("related_paragraph_ids")),
                "raw_seed_anchor": _string(shard.get("raw_seed_anchor")),
                "section_path": _string(shard.get("section_path")),
                "paragraph_summary": _string(shard.get("paragraph_summary")),
                "status": _string(shard.get("status")) or "unknown",
            }
        )

    normalized = dict(data)
    normalized["surface_kind"] = "extracted_shards"
    normalized["shards"] = normalized_shards
    if not normalized.get("kind"):
        normalized["kind"] = "extracted_shards"
    normalized["source_path"] = _rel(path, repo_root=repo_root)
    return normalized


def _normalize_shards_payload(
    data: Mapping[str, Any],
    *,
    path: Path,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    if _surface_kind(data, path=path) == "raw_seed_shards":
        return _normalize_raw_seed_shards_payload(data, path=path, repo_root=repo_root)
    return _normalize_extracted_shards_payload(data, path=path, repo_root=repo_root)


def _append_index(map_obj: dict[str, list[str]], key: str, shard_id: str) -> None:
    token = _string(key)
    if not token:
        return
    map_obj.setdefault(token, []).append(shard_id)


def _browser_index_for_shards(shards: list[dict[str, Any]]) -> dict[str, Any]:
    concept_map: dict[str, list[str]] = {}
    status_map: dict[str, list[str]] = {}
    mech_map: dict[str, list[str]] = {}
    group_map: dict[str, list[str]] = {}
    raw_anchor_map: dict[str, list[str]] = {}
    raw_paragraph_map: dict[str, list[str]] = {}
    routing_state_map: dict[str, list[str]] = {}
    coverage_state_map: dict[str, list[str]] = {}
    gesture_map: dict[str, list[str]] = {}
    parent_paragraph_map: dict[str, list[str]] = {}
    source_bin_map: dict[str, list[str]] = {}
    source_artifact_map: dict[str, list[str]] = {}
    relevant_file_map: dict[str, list[str]] = {}
    pending_ids: list[str] = []

    for shard in shards:
        shard_id = _string(shard.get("id")) or "?"
        for concept_id in shard.get("concept_ids") or []:
            _append_index(concept_map, _string(concept_id), shard_id)

        status = _string(shard.get("status")) or "unknown"
        _append_index(status_map, status, shard_id)
        if status == "pending":
            pending_ids.append(shard_id)

        for mechanism in shard.get("mechanisms") or []:
            _append_index(mech_map, _string(mechanism), shard_id)

        groups = _string_list(shard.get("idea_group_ids"))
        group = _string(shard.get("concept_group") or shard.get("group"))
        if group and group not in groups:
            groups.append(group)
        for group_id in groups:
            _append_index(group_map, group_id, shard_id)

        raw_anchor = _string(shard.get("raw_seed_anchor"))
        if raw_anchor:
            _append_index(raw_anchor_map, raw_anchor, shard_id)
        for paragraph_id in shard.get("raw_paragraph_ids") or []:
            _append_index(raw_paragraph_map, _string(paragraph_id), shard_id)

        routing_state = _string(shard.get("routing_state"))
        if routing_state:
            _append_index(routing_state_map, routing_state, shard_id)

        coverage_state = _string(shard.get("coverage_state"))
        if coverage_state:
            _append_index(coverage_state_map, coverage_state, shard_id)

        for gesture in shard.get("gestures_towards") or []:
            _append_index(gesture_map, _string(gesture), shard_id)

        parent_paragraph_id = _string(shard.get("parent_paragraph_id"))
        if parent_paragraph_id:
            _append_index(parent_paragraph_map, parent_paragraph_id, shard_id)

        source_bin_id = _string(shard.get("source_bin_id"))
        if source_bin_id:
            _append_index(source_bin_map, source_bin_id, shard_id)

        source_artifact = _string(shard.get("source_artifact"))
        if source_artifact:
            _append_index(source_artifact_map, source_artifact, shard_id)

        for relevant_file in shard.get("relevant_files") or []:
            _append_index(relevant_file_map, _string(relevant_file), shard_id)

    return {
        "total": len(shards),
        "concept_map": concept_map,
        "status_map": status_map,
        "mechanism_map": mech_map,
        "group_map": group_map,
        "raw_anchor_map": raw_anchor_map,
        "raw_paragraph_map": raw_paragraph_map,
        "routing_state_map": routing_state_map,
        "coverage_state_map": coverage_state_map,
        "gesture_map": gesture_map,
        "parent_paragraph_map": parent_paragraph_map,
        "source_bin_map": source_bin_map,
        "source_artifact_map": source_artifact_map,
        "relevant_file_map": relevant_file_map,
        "pending_ids": pending_ids,
        "pending_count": len(pending_ids),
    }


def _candidate_phase_dirs_from_orchestration(repo_root: Path) -> list[str]:
    state_path = repo_root / "tools" / "meta" / "control" / "orchestration_state.json"
    payload = _load_json(state_path) or {}
    phase_dirs: list[str] = []

    coordination = payload.get("coordination")
    if isinstance(coordination, Mapping):
        system_view = coordination.get("system_view")
        if isinstance(system_view, Mapping):
            system_view_path = _string(system_view.get("path"))
            if system_view_path.endswith("/system_view.json"):
                phase_dirs.append(str(Path(system_view_path).parent))

    source_snapshots = payload.get("source_snapshots")
    if isinstance(source_snapshots, Mapping):
        phase_pipeline = source_snapshots.get("phase_pipeline")
        if isinstance(phase_pipeline, Mapping):
            phase_dir = _string(phase_pipeline.get("phase_dir"))
            if phase_dir:
                phase_dirs.append(phase_dir)

    deduped: list[str] = []
    seen: set[str] = set()
    for phase_dir in phase_dirs:
        if not phase_dir or phase_dir in seen:
            continue
        seen.add(phase_dir)
        deduped.append(phase_dir)
    return deduped


def _candidate_phase_dirs_from_explicit_active(repo_root: Path) -> list[str]:
    try:
        from system.lib.phase_activation import load_explicit_active_phase
    except Exception:
        return []
    active = load_explicit_active_phase(repo_root)
    if not isinstance(active, Mapping):
        return []
    phase_dir = _string(active.get("phase_dir"))
    return [phase_dir] if phase_dir else []


def discover_shard_surfaces(
    *,
    repo_root: Path = REPO_ROOT,
    family_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    See `_uncached_discover_shard_surfaces` for the full contract. This wrapper
    adds a short-TTL process-local cache because every shard endpoint calls
    this before doing anything else, and the walk is ~1.2s per call cold.
    """
    resolved_family_root = family_root or (repo_root / _default_family_root_relative_path(repo_root))
    key = (str(repo_root.resolve()), str(resolved_family_root.resolve()))
    now = time.monotonic()
    with _DISCOVER_CACHE_LOCK:
        hit = _DISCOVER_CACHE.get(key)
        if hit is not None and now - hit[0] <= _DISCOVER_CACHE_TTL_S:
            # Return a shallow copy of the list so callers can append without
            # mutating the cached backing list. The inner dicts are treated as
            # read-only by existing callers.
            return list(hit[1])
    result = _uncached_discover_shard_surfaces(
        repo_root=repo_root,
        family_root=resolved_family_root,
    )
    with _DISCOVER_CACHE_LOCK:
        _DISCOVER_CACHE[key] = (now, result)
    return list(result)


def _uncached_discover_shard_surfaces(
    *,
    repo_root: Path = REPO_ROOT,
    family_root: Path | None = None,
) -> list[dict[str, Any]]:
    """
    [ACTION]
        - Teleology: Discover the candidate shard surfaces in the order a caller should try them, biased toward active and current-family contexts before historical backlogs.
        - Mechanism: Collect phase directories from orchestration and explicit-active markers, add active/family/recent-phase shard candidates plus the family raw-seed shard sidecar, inspect each file for existence and shard stats, and return the sorted surface cards.
        - Reads: `repo_root`, optional `family_root`, `tools/meta/control/orchestration_state.json`, explicit-active phase metadata, and candidate shard files.
    - Writes: None.
    - Guarantee: Returns a list of surface cards describing role, priority, path, existence, shard counts, and mtime for each unique candidate surface.
    - Fails: None; unreadable or missing source files simply produce missing/empty surface cards.
    - Orders: Sorts surfaces by existence, descending priority, descending mtime, then path for stable selection behavior.
    - When-needed: Open when a caller needs to understand which shard surface would win for active, family, or recent-phase browsing before actually loading shards.
    - Escalates-to: system/lib/shard_browser.py::resolve_shards_path; tools/meta/factory/shard_browser.py
    - Navigation-group: kernel_lib
    """
    resolved_family_root = family_root or (repo_root / _default_family_root_relative_path(repo_root))
    surfaces: list[dict[str, Any]] = []
    seen: set[str] = set()

    def add_surface(path: Path, *, role: str, source: str, priority: int) -> None:
        absolute = path if path.is_absolute() else repo_root / path
        absolute = absolute.resolve() if absolute.exists() else absolute
        key = str(absolute)
        if key in seen:
            return
        seen.add(key)

        payload = _load_json(absolute) if absolute.is_file() else None
        shards = payload.get("shards") if isinstance(payload, Mapping) and isinstance(payload.get("shards"), list) else []
        stats = _status_summary(shards)
        scope = "family" if _family_root_for_shards_path(absolute) == resolved_family_root else "phase"
        extracted_at = None
        if isinstance(payload, Mapping):
            extracted_at = _string(payload.get("extracted_at") or payload.get("generated_at")) or None

        try:
            mtime = absolute.stat().st_mtime
        except OSError:
            mtime = 0.0

        surfaces.append(
            {
                "role": role,
                "source": source,
                "scope": scope,
                "priority": priority,
                "surface_kind": _surface_kind(payload, path=absolute),
                "path": _rel(absolute, repo_root=repo_root),
                "exists": absolute.is_file(),
                "total": len(shards),
                "by_status": stats,
                "pending_count": stats.get("pending", 0),
                "extracted_at": extracted_at,
                "mtime": mtime,
            }
        )

    for phase_dir in _candidate_phase_dirs_from_orchestration(repo_root):
        add_surface(
            Path(phase_dir) / "extracted_shards.json",
            role="active_phase",
            source="orchestration_state",
            priority=400,
        )

    for phase_dir in _candidate_phase_dirs_from_explicit_active(repo_root):
        add_surface(
            Path(phase_dir) / "extracted_shards.json",
            role="explicit_active_phase",
            source="active_phase_marker",
            priority=350,
        )

    add_surface(
        resolved_family_root / EXTRACTED_SHARDS_FILENAME,
        role="family_root",
        source="family_default",
        priority=300,
    )
    add_surface(
        resolved_family_root / RAW_SEED_SHARDS_RELATIVE_PATH,
        role="family_raw_seed",
        source="family_raw_seed",
        priority=250,
    )

    if resolved_family_root.is_dir():
        recent_phase_paths = sorted(
            resolved_family_root.glob(f"*/{EXTRACTED_SHARDS_FILENAME}"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        for index, phase_path in enumerate(recent_phase_paths):
            role = "recent_phase"
            if ".pipeline_recovery" in phase_path.as_posix() or "/archives/" in phase_path.as_posix():
                role = "archived_phase"
            add_surface(
                phase_path,
                role=role,
                source="family_scan",
                priority=200 - min(index, 50),
            )

    surfaces.sort(
        key=lambda item: (
            0 if item.get("exists") else 1,
            -int(item.get("priority") or 0),
            -float(item.get("mtime") or 0.0),
            str(item.get("path") or ""),
        )
    )
    return surfaces


def resolve_shards_path(
    *,
    family_dir: Path | str | None = None,
    explicit_path: Path | str | None = None,
    source: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> Path | None:
    """
    [ACTION]
        - Teleology: Resolve the concrete shard path a caller should load for one browsing request.
        - Mechanism: Honor an explicit path first, then family-root defaults, then the prioritized shard-surface list filtered by the optional `source` token, and finally fall back to the first existing discovered surface.
    - Reads: `family_dir`, `explicit_path`, `source`, `repo_root`, and `discover_shard_surfaces()`.
    - Writes: None.
    - Guarantee: Returns the preferred shard path or `None` when no suitable surface exists.
    - Fails: None.
    - When-needed: Open when the next step is deciding which shard file should back a browse/query request before any JSON is loaded.
    - Escalates-to: system/lib/shard_browser.py::load_shards; tools/meta/factory/shard_browser.py
    - Navigation-group: kernel_lib
    """
    resolved_family_dir: Path | None = None
    if explicit_path:
        path = Path(explicit_path)
        return path if path.is_absolute() else repo_root / path
    if family_dir:
        resolved_family_dir = Path(family_dir)
        if not resolved_family_dir.is_absolute():
            resolved_family_dir = repo_root / resolved_family_dir
        default_family_path = resolved_family_dir / EXTRACTED_SHARDS_FILENAME
        default_raw_seed_path = resolved_family_dir / RAW_SEED_SHARDS_RELATIVE_PATH
        if not source:
            if default_family_path.exists():
                return default_family_path
            if default_raw_seed_path.exists():
                return default_raw_seed_path

    surfaces = discover_shard_surfaces(repo_root=repo_root, family_root=resolved_family_dir)
    token = _string(source).lower()
    if token in {"active", "active_phase"}:
        preferred_roles = {"active_phase", "explicit_active_phase"}
    elif token in {"family", "family_root"}:
        preferred_roles = {"family_root", "family_raw_seed"}
    elif token in {"phase", "recent_phase"}:
        preferred_roles = {"active_phase", "explicit_active_phase", "recent_phase"}
    elif token in {"raw", "raw_seed", "raw_seed_shards", "family_raw_seed"}:
        preferred_roles = {"family_raw_seed"}
    else:
        preferred_roles = set()

    if preferred_roles:
        for item in surfaces:
            if item.get("exists") and item.get("role") in preferred_roles:
                return repo_root / str(item["path"])

    for item in surfaces:
        if item.get("exists"):
            return repo_root / str(item["path"])
    return None


def _shared_groups(left: Mapping[str, Any], right: Mapping[str, Any]) -> list[str]:
    left_groups = set(_string_list(left.get("idea_group_ids")))
    right_groups = set(_string_list(right.get("idea_group_ids")))
    return sorted(left_groups & right_groups)


def _relation_payload(
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> list[dict[str, Any]]:
    relations: list[dict[str, Any]] = []

    left_parent = _string(left.get("parent_paragraph_id"))
    right_parent = _string(right.get("parent_paragraph_id"))
    if left_parent and left_parent == right_parent:
        relations.append({"kind": "same_parent", "value": left_parent})

    left_bin = _string(left.get("source_bin_id"))
    right_bin = _string(right.get("source_bin_id"))
    if left_bin and left_bin == right_bin:
        relations.append({"kind": "same_bin", "value": left_bin})

    left_artifact = _string(left.get("source_artifact"))
    right_artifact = _string(right.get("source_artifact"))
    if left_artifact and left_artifact == right_artifact:
        relations.append({"kind": "same_source_artifact", "value": left_artifact})

    shared_groups = _shared_groups(left, right)
    if shared_groups:
        relations.append({"kind": "shared_group", "value": shared_groups})

    return relations


def _relation_score(relations: list[dict[str, Any]]) -> int:
    weights = {
        "same_parent": 10,
        "same_bin": 9,
        "same_source_artifact": 6,
        "shared_group": 4,
    }
    score = 0
    for relation in relations:
        kind = _string(relation.get("kind"))
        score += weights.get(kind, 1)
        if kind == "shared_group":
            value = relation.get("value")
            if isinstance(value, list):
                score += max(0, len(value) - 1)
    return score


def _field_hit(
    *,
    axis: str,
    query_text: str,
    query_tokens: set[str],
    values: list[str],
    exact_bonus: int,
    overlap_weight: int,
    require_exact: bool = False,
) -> dict[str, Any] | None:
    if not values:
        return None

    lower_values = [_string(value).lower() for value in values if _string(value)]
    if not lower_values:
        return None

    exact_values = [value for value in lower_values if query_text and query_text == value]
    if exact_values:
        return {
            "axis": axis,
            "score": exact_bonus,
            "detail": "exact_match",
            "matched_terms": sorted(query_tokens) if query_tokens else [query_text],
        }

    phrase_values = [value for value in lower_values if query_text and query_text in value]
    if phrase_values and not require_exact:
        return {
            "axis": axis,
            "score": max(overlap_weight * 2, exact_bonus - 2),
            "detail": "phrase_match",
            "matched_terms": sorted(query_tokens),
        }

    best_overlap: set[str] = set()
    for value in lower_values:
        overlap = query_tokens & _tokenize(value)
        if len(overlap) > len(best_overlap):
            best_overlap = overlap
    if best_overlap and not require_exact:
        return {
            "axis": axis,
            "score": len(best_overlap) * overlap_weight,
            "detail": "token_overlap",
            "matched_terms": sorted(best_overlap),
        }
    return None


def _statement_hit(
    *,
    query_text: str,
    query_tokens: set[str],
    shard: Mapping[str, Any],
) -> dict[str, Any] | None:
    statement = _string(
        shard.get("clarified_statement")
        or shard.get("statement")
        or shard.get("text")
        or shard.get("gloss")
    )
    if not statement:
        return None
    statement_tokens = _tokenize(statement)
    overlap = query_tokens & statement_tokens
    if not overlap and not (query_text and query_text in statement.lower()):
        return None
    score = len(overlap) * 10
    detail = "token_overlap"
    if query_text and query_text in statement.lower():
        score += 8
        detail = "phrase_match"
    return {
        "axis": "statement",
        "score": score,
        "detail": detail,
        "matched_terms": sorted(overlap) if overlap else sorted(query_tokens),
    }


def _target_texts(shard: Mapping[str, Any]) -> list[str]:
    texts = _value_texts(shard.get("routing_targets"))
    texts.extend(_string_list(shard.get("routing_target_texts")))
    return _dedupe_strings(texts)


def _score_shard_match(
    shard: Mapping[str, Any],
    *,
    query_text: str,
    query_tokens: set[str],
) -> dict[str, Any] | None:
    matched_axes: list[dict[str, Any]] = []

    statement_hit = _statement_hit(query_text=query_text, query_tokens=query_tokens, shard=shard)
    if statement_hit:
        matched_axes.append(statement_hit)

    for axis_hit in (
        _field_hit(
            axis="voice_anchor",
            query_text=query_text,
            query_tokens=query_tokens,
            values=[_string(shard.get("voice_anchor"))],
            exact_bonus=13,
            overlap_weight=4,
        ),
        _field_hit(
            axis="gestures_towards",
            query_text=query_text,
            query_tokens=query_tokens,
            values=_string_list(shard.get("gestures_towards")),
            exact_bonus=12,
            overlap_weight=4,
        ),
        _field_hit(
            axis="idea_group_ids",
            query_text=query_text,
            query_tokens=query_tokens,
            values=_string_list(shard.get("idea_group_ids")),
            exact_bonus=8,
            overlap_weight=3,
        ),
        _field_hit(
            axis="routing_state",
            query_text=query_text,
            query_tokens=query_tokens,
            values=[_string(shard.get("routing_state"))],
            exact_bonus=7,
            overlap_weight=2,
            require_exact=True,
        ),
        _field_hit(
            axis="coverage_state",
            query_text=query_text,
            query_tokens=query_tokens,
            values=[_string(shard.get("coverage_state"))],
            exact_bonus=7,
            overlap_weight=2,
            require_exact=True,
        ),
        _field_hit(
            axis="routing_targets",
            query_text=query_text,
            query_tokens=query_tokens,
            values=_target_texts(shard),
            exact_bonus=7,
            overlap_weight=2,
        ),
        _field_hit(
            axis="relevant_files",
            query_text=query_text,
            query_tokens=query_tokens,
            values=_string_list(shard.get("relevant_files")),
            exact_bonus=6,
            overlap_weight=2,
        ),
    ):
        if axis_hit:
            matched_axes.append(axis_hit)

    if not matched_axes:
        return None

    score = sum(int(item.get("score") or 0) for item in matched_axes)
    matched_terms = sorted(
        {
            term
            for item in matched_axes
            for term in item.get("matched_terms") or []
            if _string(term)
        }
    )
    enriched_shard = enrich_shard_routing_metadata(shard, matched_terms=matched_terms)
    return {
        "shard_id": _string(shard.get("id")),
        "score": score,
        "matched_terms": matched_terms,
        "matched_axes": matched_axes,
        "review_plane_hints": list(enriched_shard.get("review_plane_hints") or []),
        "primary_review_plane": _string(enriched_shard.get("primary_review_plane")),
        "synthesis_role": _string(enriched_shard.get("synthesis_role")),
        "shard": enriched_shard,
    }


def _summarize_group_entries(
    entries: dict[str, dict[str, Any]],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for group_id, entry in entries.items():
        matched_shard_ids = [
            shard_id
            for shard_id in entry.get("matched_shard_ids", [])
            if _string(shard_id)
        ]
        primary_shard_ids = [
            shard_id
            for shard_id in entry.get("primary_shard_ids", [])
            if _string(shard_id)
        ]
        summaries.append(
            {
                "group_id": group_id,
                "score": int(entry.get("score") or 0),
                "max_shard_score": int(entry.get("max_shard_score") or 0),
                "matched_shard_count": len(matched_shard_ids),
                "primary_result_count": len(primary_shard_ids),
                "matched_terms": sorted(entry.get("matched_terms") or []),
                "review_plane_hints": _merge_review_plane_hints(
                    [dict(hint) for hint in entry.get("review_plane_hints") or [] if isinstance(hint, Mapping)]
                ),
                "next_actions": _group_next_actions(group_id),
                "representative_shard_ids": matched_shard_ids[:5],
                "representative_parent_paragraphs": sorted(entry.get("parent_paragraph_ids") or [])[:5],
                "routing_state_counts": _sorted_counts(entry.get("routing_state_counts") or {}),
                "coverage_state_counts": _sorted_counts(entry.get("coverage_state_counts") or {}),
            }
        )
    summaries.sort(
        key=lambda item: (
            -int(item.get("primary_result_count") or 0),
            -int(item.get("score") or 0),
            -int(item.get("matched_shard_count") or 0),
            _string(item.get("group_id")),
        )
    )
    if limit > 0:
        return summaries[:limit]
    return summaries


def _query_group_summaries(
    ranked: list[dict[str, Any]],
    *,
    primary_ids: set[str],
    limit: int = 12,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for row in ranked:
        shard = row.get("shard")
        if not isinstance(shard, Mapping):
            continue
        shard_id = _string(row.get("shard_id") or shard.get("id"))
        if not shard_id:
            continue
        for group_id in _shard_group_ids(shard):
            entry = groups.setdefault(
                group_id,
                {
                    "score": 0,
                    "max_shard_score": 0,
                    "matched_terms": set(),
                    "matched_shard_ids": [],
                    "primary_shard_ids": [],
                    "parent_paragraph_ids": set(),
                    "routing_state_counts": {},
                    "coverage_state_counts": {},
                    "review_plane_hints": [],
                },
            )
            row_score = int(row.get("score") or 0)
            entry["score"] += row_score
            entry["max_shard_score"] = max(int(entry.get("max_shard_score") or 0), row_score)
            for term in row.get("matched_terms") or []:
                token = _string(term)
                if token:
                    entry["matched_terms"].add(token)
            if shard_id not in entry["matched_shard_ids"]:
                entry["matched_shard_ids"].append(shard_id)
            if shard_id in primary_ids and shard_id not in entry["primary_shard_ids"]:
                entry["primary_shard_ids"].append(shard_id)
            parent_id = _string(shard.get("parent_paragraph_id"))
            if parent_id:
                entry["parent_paragraph_ids"].add(parent_id)
            _increment_count(entry["routing_state_counts"], shard.get("routing_state"))
            _increment_count(entry["coverage_state_counts"], shard.get("coverage_state"))
            entry["review_plane_hints"].extend(
                [dict(hint) for hint in row.get("review_plane_hints") or [] if isinstance(hint, Mapping)]
            )
    return _summarize_group_entries(groups, limit=limit)


def _shard_group_summaries(
    shards: list[dict[str, Any]],
    *,
    limit: int = 12,
) -> list[dict[str, Any]]:
    groups: dict[str, dict[str, Any]] = {}
    for shard in shards:
        shard_id = _string(shard.get("id") or shard.get("shard_id"))
        if not shard_id:
            continue
        for group_id in _shard_group_ids(shard):
            entry = groups.setdefault(
                group_id,
                {
                    "score": 0,
                    "max_shard_score": 0,
                    "matched_terms": set(),
                    "matched_shard_ids": [],
                    "primary_shard_ids": [],
                    "parent_paragraph_ids": set(),
                    "routing_state_counts": {},
                    "coverage_state_counts": {},
                    "review_plane_hints": [],
                },
            )
            entry["score"] += 1
            entry["max_shard_score"] = max(int(entry.get("max_shard_score") or 0), 1)
            if shard_id not in entry["matched_shard_ids"]:
                entry["matched_shard_ids"].append(shard_id)
            if shard_id not in entry["primary_shard_ids"]:
                entry["primary_shard_ids"].append(shard_id)
            parent_id = _string(shard.get("parent_paragraph_id"))
            if parent_id:
                entry["parent_paragraph_ids"].add(parent_id)
            _increment_count(entry["routing_state_counts"], shard.get("routing_state"))
            _increment_count(entry["coverage_state_counts"], shard.get("coverage_state"))
            entry["review_plane_hints"].extend(_review_plane_hints_for_shard(shard))
    return _summarize_group_entries(groups, limit=limit)


class ShardIndex:
    """[ROLE]
    - Teleology: In-memory query wrapper over one loaded shard envelope.
    - Mechanism: Stores the raw envelope, backing path, ordered shard list, and id index, then exposes convenience queries and summary/index projections.
    - Ownership: Created by `load_shards()`; consumed by kernel shard routes and the shard-browser CLI.
    - Mutability: Read-only by convention after construction; methods only derive projections from the loaded shard data.
    - Concurrency: Safe for concurrent reads as long as callers do not mutate the returned shard dicts in place.
    - When-needed: Open when one shard envelope is already loaded and the next question is how to query it by id, status, mechanism, concept, or neighborhood.
    - Escalates-to: tools/meta/factory/shard_browser.py; system/lib/shard_browser.py::load_shards
    """

    def __init__(self, data: dict[str, Any], path: Path) -> None:
        self._data = data
        self._path = path
        self._shards: list[dict[str, Any]] = [
            dict(item)
            for item in data.get("shards", [])
            if isinstance(item, Mapping) and _string(item.get("id"))
        ]
        self._by_id: dict[str, dict[str, Any]] = {
            _string(shard.get("id")): shard
            for shard in self._shards
            if _string(shard.get("id"))
        }

    @property
    def path(self) -> Path:
        return self._path

    @property
    def total(self) -> int:
        return len(self._shards)

    @property
    def envelope(self) -> dict[str, Any]:
        return {k: v for k, v in self._data.items() if k != "shards"}

    # ── Core queries ──────────────────────────────────────────────────────

    def get(self, shard_id: str) -> dict[str, Any] | None:
        return self._by_id.get(_string(shard_id))

    def list(
        self,
        *,
        status: str | None = None,
        concept_id: str | None = None,
        mechanism: str | None = None,
        group: str | None = None,
        raw_anchor: str | None = None,
        paragraph_id: str | None = None,
        query: str | None = None,
        limit: int = 0,
    ) -> list[dict[str, Any]]:
        """
        [ACTION]
        - Teleology: Return the filtered shard list for the common browse dimensions exposed by kernel and CLI surfaces.
        - Mechanism: Filter the loaded shard list by status, concept, mechanism, group, raw anchor, paragraph id, and optional text query, then enforce an optional limit.
        - Reads: The loaded shard list plus the filter arguments supplied by the caller.
        - Writes: None.
        - Guarantee: Returns a list of shard dicts that satisfy every provided filter in stable shard order.
        - Fails: None.
        - When-needed: Open when the shard browser needs the exact filtering semantics behind status/concept/mechanism/group/anchor/paragraph/query requests.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_list; system/lib/shard_browser.py::search
        - Navigation-group: kernel_lib
        """
        results = self._shards
        if status:
            results = [s for s in results if s.get("status") == status]
        if concept_id:
            results = [s for s in results if concept_id in (s.get("concept_ids") or [])]
        if mechanism:
            m_lower = mechanism.lower()
            results = [
                s
                for s in results
                if any(m_lower in (mec or "").lower() for mec in (s.get("mechanisms") or []))
            ]
        if group:
            g_lower = group.lower()
            results = [
                s
                for s in results
                if (s.get("concept_group") or "").lower() == g_lower
                or (s.get("group") or "").lower() == g_lower
                or g_lower in [item.lower() for item in _string_list(s.get("idea_group_ids"))]
            ]
        if raw_anchor:
            anchor = raw_anchor.lower()
            results = [
                s for s in results if anchor in _string(s.get("raw_seed_anchor")).lower()
            ]
        if paragraph_id:
            results = [
                s for s in results if paragraph_id in (s.get("raw_paragraph_ids") or [])
            ]
        if query:
            results = self.search(query, pool=results)
        if limit > 0:
            results = results[:limit]
        return results

    def by_concept(self, concept_id: str) -> list[dict[str, Any]]:
        return self.list(concept_id=concept_id)

    def by_status(self, status: str) -> list[dict[str, Any]]:
        return self.list(status=status)

    def by_mechanism(self, mech_tag: str) -> list[dict[str, Any]]:
        return self.list(mechanism=mech_tag)

    def neighbor_map(
        self,
        shard_ids: list[str],
        *,
        pool: list[dict[str, Any]] | None = None,
    ) -> dict[str, list[dict[str, Any]]]:
        src = pool if pool is not None else self._shards
        pool_by_id = {
            _string(shard.get("id")): shard
            for shard in src
            if _string(shard.get("id"))
        }
        selected_ids = [
            shard_id for shard_id in [_string(item) for item in shard_ids] if shard_id in pool_by_id
        ]
        selected_id_set = set(selected_ids)
        neighbor_map: dict[str, list[dict[str, Any]]] = {}
        for shard_id in selected_ids:
            shard = pool_by_id[shard_id]
            entries: list[dict[str, Any]] = []
            for other_id, other in pool_by_id.items():
                if other_id == shard_id or other_id not in selected_id_set:
                    continue
                relations = _relation_payload(shard, other)
                if not relations:
                    continue
                shared_group_values = []
                for relation in relations:
                    if _string(relation.get("kind")) == "shared_group":
                        value = relation.get("value")
                        if isinstance(value, list):
                            shared_group_values = value
                entries.append(
                    {
                        "shard_id": other_id,
                        "relation_kinds": sorted(
                            {_string(relation.get("kind")) for relation in relations if _string(relation.get("kind"))}
                        ),
                        "shared_groups": shared_group_values,
                    }
                )
            entries.sort(
                key=lambda item: (
                    -len(item.get("relation_kinds") or []),
                    item.get("shard_id") or "",
                )
            )
            neighbor_map[shard_id] = entries
        return neighbor_map

    def query_neighborhood(
        self,
        query: str,
        *,
        limit: int = 20,
        related_limit: int = 40,
        pool: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Rank shard matches and expand their nearby ideational neighborhood so callers can find relevant shards without falling back to grep or linearly rereading raw files.
        - Mechanism: Score the candidate shard pool across statement, voice-anchor, gesture, group, routing, target, and file axes, return ranked primary hits, then expand related neighbors by shared parent, source bin, source artifact, and idea-group relations.
        - Reads: The loaded shard list or the caller-supplied filtered pool plus the query text.
        - Writes: None.
        - Guarantee: Returns an explainable ranked payload with `matched_axes` for primary hits and `related_by` for expanded neighbors.
        - Fails: None.
        - When-needed: Open when a shard query needs ranked multi-axis retrieval and local neighborhood expansion rather than flat substring matching.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_list; tools/meta/factory/materialize_shard_batches.py
        """
        query_text = _string(query).lower()
        query_tokens = _tokenize(query_text)
        src = [dict(shard) for shard in (pool if pool is not None else self._shards)]
        if not query_text or not query_tokens:
            next_action_graph = _build_next_action_graph(
                query=query,
                primary=[],
                group_summaries=[],
                review_plane_summary=[],
                ungrouped_primary_count=0,
            )
            return {
                "query": _string(query),
                "ranking_mode": QUERY_RANKING_MODE,
                "matched": 0,
                "results": [],
                "related": [],
                "group_summaries": [],
                "group_summary_count": 0,
                "review_plane_summary": [],
                "next_action_graph": next_action_graph,
                "shard_synthesis": _build_shard_synthesis(
                    label=_string(query),
                    shards=[],
                    group_summaries=[],
                    review_plane_summary=[],
                    next_action_graph=next_action_graph,
                    selector={"query": query},
                ),
                "total_in_index": self.total,
                "total_in_pool": len(src),
            }

        ranked: list[dict[str, Any]] = []
        for shard in src:
            match = _score_shard_match(shard, query_text=query_text, query_tokens=query_tokens)
            if match:
                ranked.append(match)

        ranked.sort(
            key=lambda item: (
                -int(item.get("score") or 0),
                -(len(item.get("matched_axes") or [])),
                _string(item.get("shard_id")),
            )
        )
        primary = ranked[: max(0, int(limit or 0))] if limit > 0 else ranked
        primary_ids = {_string(item.get("shard_id")) for item in primary if _string(item.get("shard_id"))}
        group_summaries = _query_group_summaries(ranked, primary_ids=primary_ids)
        review_plane_summary = _merge_review_plane_hints(
            [
                dict(hint)
                for row in [*primary, *group_summaries]
                for hint in row.get("review_plane_hints") or []
                if isinstance(hint, Mapping)
            ]
        )
        ungrouped_match_count = sum(
            1
            for item in ranked
            if isinstance(item.get("shard"), Mapping)
            and not _shard_group_ids(item["shard"])
        )
        ungrouped_primary_count = sum(
            1
            for item in primary
            if isinstance(item.get("shard"), Mapping)
            and not _shard_group_ids(item["shard"])
        )
        next_action_graph = _build_next_action_graph(
            query=query,
            primary=primary,
            group_summaries=group_summaries,
            review_plane_summary=review_plane_summary,
            ungrouped_primary_count=ungrouped_primary_count,
        )
        shard_synthesis = _build_shard_synthesis(
            label=_string(query),
            shards=[dict(item.get("shard")) for item in primary if isinstance(item.get("shard"), Mapping)],
            group_summaries=group_summaries,
            review_plane_summary=review_plane_summary,
            next_action_graph=next_action_graph,
            selector={"query": query},
        )

        related_candidates: dict[str, dict[str, Any]] = {}
        for result in primary:
            result_shard = result.get("shard")
            if not isinstance(result_shard, Mapping):
                continue
            result_shard_id = _string(result.get("shard_id"))
            for candidate in src:
                candidate_id = _string(candidate.get("id"))
                if not candidate_id or candidate_id == result_shard_id or candidate_id in primary_ids:
                    continue
                relations = _relation_payload(result_shard, candidate)
                if not relations:
                    continue
                entry = related_candidates.setdefault(
                    candidate_id,
                    {
                        "shard_id": candidate_id,
                        "shard": dict(candidate),
                        "related_by": [],
                        "source_shard_ids": [],
                        "score": 0,
                    },
                )
                for relation in relations:
                    if relation not in entry["related_by"]:
                        entry["related_by"].append(relation)
                if result_shard_id and result_shard_id not in entry["source_shard_ids"]:
                    entry["source_shard_ids"].append(result_shard_id)
                entry["score"] = _relation_score(entry["related_by"])

        related = sorted(
            related_candidates.values(),
            key=lambda item: (
                -int(item.get("score") or 0),
                -len(item.get("source_shard_ids") or []),
                _string(item.get("shard_id")),
            ),
        )
        if related_limit > 0:
            related = related[:related_limit]

        return {
            "query": _string(query),
            "ranking_mode": QUERY_RANKING_MODE,
            "matched": len(primary),
            "results": primary,
            "related": related,
            "group_summaries": group_summaries,
            "group_summary_count": len(group_summaries),
            "review_plane_summary": review_plane_summary,
            "next_action_graph": next_action_graph,
            "shard_synthesis": shard_synthesis,
            "ungrouped_match_count": ungrouped_match_count,
            "ungrouped_primary_count": ungrouped_primary_count,
            "total_in_index": self.total,
            "total_in_pool": len(src),
        }

    def search(
        self,
        query: str,
        *,
        pool: list[dict[str, Any]] | None = None,
    ) -> list[dict[str, Any]]:
        """
        [ACTION]
        - Teleology: Run the module's broad query match across shard ids and descriptive fields when exact structural filters are not enough.
        - Mechanism: Delegate to the ranked neighborhood query and return only the primary matched shard records in ranked order.
        - Reads: `query`, optional `pool`, and the loaded shard list.
        - Writes: None.
        - Guarantee: Returns shard rows in deterministic ranked order for the query.
        - Fails: None.
        - When-needed: Open when shard browsing needs free-text narrowing over loaded shard records instead of only structural filters.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_list; system/lib/shard_browser.py::query_neighborhood
        """
        query_payload = self.query_neighborhood(query, limit=0, related_limit=0, pool=pool)
        return [
            dict(item.get("shard"))
            for item in query_payload.get("results") or []
            if isinstance(item, Mapping) and isinstance(item.get("shard"), Mapping)
        ]

    def neighborhood(self, shard_id: str, *, n: int = 3) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Return one shard together with its nearby siblings so callers can inspect local context without scanning the full shard list.
        - Mechanism: Locate the shard index by id, slice up to `n` entries before and after it, and return the before/target/after neighborhood envelope.
        - Reads: `shard_id`, `n`, and the loaded shard list.
        - Writes: None.
        - Guarantee: Returns a neighborhood dict with `found=False` when the shard id is absent, otherwise includes before/target/after slices and the target index metadata.
        - Fails: None.
        - When-needed: Open when a shard id has been resolved and the next question is what sits immediately around it in list order.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_id; system/lib/shard_browser.py::get
        """
        idx = next((i for i, s in enumerate(self._shards) if s.get("id") == shard_id), None)
        if idx is None:
            return {"found": False, "shard_id": shard_id}
        start = max(0, idx - n)
        end = min(len(self._shards), idx + n + 1)
        return {
            "found": True,
            "shard_id": shard_id,
            "index": idx,
            "total": len(self._shards),
            "before": self._shards[start:idx],
            "target": self._shards[idx],
            "after": self._shards[idx + 1:end],
        }

    # ── Index / summary views ─────────────────────────────────────────────

    def compact_table(self) -> list[dict[str, Any]]:
        return [
            {
                "id": s.get("id"),
                "status": s.get("status", "unknown"),
                "concept_ids": s.get("concept_ids") or [],
                "concept_group": s.get("concept_group"),
                "raw_seed_anchor": s.get("raw_seed_anchor"),
                "gloss": _first_80(s.get("gloss") or s.get("text") or s.get("statement") or ""),
                "mechanisms": s.get("mechanisms") or [],
            }
            for s in self._shards
        ]

    def browser_index(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Build the pre-grouped browse index that powers concept/status/mechanism/group/raw-anchor lookups over the loaded shard set.
        - Mechanism: Delegate to `_browser_index_for_shards()` over the loaded shard list and return the resulting concept/status/mechanism/group/raw-anchor maps.
        - Reads: The loaded shard list.
        - Writes: None.
        - Guarantee: Returns a dict containing total counts and the concept/status/mechanism/group/raw-anchor/paragraph maps plus pending ids.
        - Fails: None.
        - When-needed: Open when a caller needs the grouped browse index instead of repeated linear scans over shards.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_index; system/lib/shard_browser.py::list
        """
        return _browser_index_for_shards(self._shards)

    def status_summary(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for shard in self._shards:
            status = _string(shard.get("status")) or "unknown"
            counts[status] = counts.get(status, 0) + 1
        return counts

    def group_summaries(
        self,
        shards: list[dict[str, Any]] | None = None,
        *,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        return _shard_group_summaries(
            [dict(shard) for shard in (shards if shards is not None else self._shards)],
            limit=limit,
        )

    def review_plane_summary(
        self,
        shards: list[dict[str, Any]] | None = None,
        *,
        limit: int = 6,
    ) -> list[dict[str, Any]]:
        rows = [
            {
                "review_plane_hints": _review_plane_hints_for_shard(shard),
            }
            for shard in (shards if shards is not None else self._shards)
        ]
        return _review_plane_summary_for_rows(rows, limit=limit)

    def next_action_graph(
        self,
        *,
        query: str = "",
        shards: list[dict[str, Any]] | None = None,
        group_summaries: list[dict[str, Any]] | None = None,
        review_plane_summary: list[dict[str, Any]] | None = None,
        selector: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = [dict(shard) for shard in (shards if shards is not None else self._shards)]
        selected_groups = group_summaries if group_summaries is not None else self.group_summaries(selected)
        selected_planes = (
            review_plane_summary
            if review_plane_summary is not None
            else self.review_plane_summary(selected)
        )
        label = _selector_label(selector, fallback=query)
        primary = [
            {
                "shard_id": _string(shard.get("id") or shard.get("shard_id")),
                "shard": shard,
            }
            for shard in selected[:5]
            if _string(shard.get("id") or shard.get("shard_id"))
        ]
        ungrouped_primary_count = sum(1 for shard in selected if not _shard_group_ids(shard))
        return _build_next_action_graph(
            query=label,
            primary=primary,
            group_summaries=list(selected_groups),
            review_plane_summary=list(selected_planes),
            ungrouped_primary_count=ungrouped_primary_count,
            selector=selector,
        )

    def shard_synthesis(
        self,
        *,
        query: str = "",
        shards: list[dict[str, Any]] | None = None,
        group_summaries: list[dict[str, Any]] | None = None,
        review_plane_summary: list[dict[str, Any]] | None = None,
        next_action_graph: Mapping[str, Any] | None = None,
        selector: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        selected = [dict(shard) for shard in (shards if shards is not None else self._shards)]
        selected_groups = group_summaries if group_summaries is not None else self.group_summaries(selected)
        selected_planes = (
            review_plane_summary
            if review_plane_summary is not None
            else self.review_plane_summary(selected)
        )
        selected_actions = next_action_graph if next_action_graph is not None else self.next_action_graph(
            query=query,
            shards=selected,
            group_summaries=list(selected_groups),
            review_plane_summary=list(selected_planes),
            selector=selector,
        )
        label = _selector_label(selector, fallback=query)
        return _build_shard_synthesis(
            label=label,
            shards=selected,
            group_summaries=list(selected_groups),
            review_plane_summary=list(selected_planes),
            next_action_graph=selected_actions,
            selector=selector,
        )

    def raw_seed_idea_browser(
        self,
        *,
        query: str = "",
        limit: int = 12,
        recent_limit: int = 6,
    ) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Emit an ideas-first browse surface over raw-seed shards so agents can see the operator idea plane without reading full routing packets.
        - Mechanism: Reuse deterministic shard ranking and group summaries, compact each idea group into representative claims, then append recent raw-seed paragraphs that have not yet acquired shard/group metadata.
        - Reads: The loaded shard list plus the sibling family `raw_seed.json` when available.
        - Writes: None.
        - Guarantee: Returns compact idea-group cards and a small unprocessed-recent queue grounded by `par_*` ids.
        - Fails: Missing `raw_seed.json` simply yields an empty recent-unprocessed list.
        - When-needed: Open when the user asks to query raw seed for "ideas" rather than route one shard packet through doctrine machinery.
        - Escalates-to: tools/meta/factory/shard_browser.py::cmd_ideas; system/lib/kernel/commands/substrate.py::cmd_raw_seed_ideas
        """
        cap = max(1, int(limit or 12))
        recent_cap = max(0, int(recent_limit or 0))
        query_text = _string(query).lower()
        query_tokens = _tokenize(query_text)

        if query_text:
            query_payload = self.query_neighborhood(
                query,
                limit=max(cap * 3, cap),
                related_limit=0,
            )
            group_summaries = list(query_payload.get("group_summaries") or [])
            ranked_ids = [
                _string(row.get("shard_id"))
                for row in query_payload.get("results") or []
                if isinstance(row, Mapping) and _string(row.get("shard_id"))
            ]
            matched_count = int(query_payload.get("matched") or 0)
            ranking_mode = _string(query_payload.get("ranking_mode")) or QUERY_RANKING_MODE
        else:
            query_payload = {}
            group_summaries = self.group_summaries(limit=cap)
            ranked_ids = []
            matched_count = self.total
            ranking_mode = "group_summary_v1"

        group_cards: list[dict[str, Any]] = []
        used_group_ids: set[str] = set()
        for group in group_summaries:
            if not isinstance(group, Mapping):
                continue
            group_id = _string(group.get("group_id"))
            if not group_id or group_id in used_group_ids:
                continue
            used_group_ids.add(group_id)
            group_shards = [
                dict(shard)
                for shard in self._shards
                if group_id in _shard_group_ids(shard)
            ]
            if ranked_ids:
                rank = {shard_id: idx for idx, shard_id in enumerate(ranked_ids)}
                group_shards.sort(
                    key=lambda shard: (
                        rank.get(_string(shard.get("id") or shard.get("shard_id")), 10**9),
                        _string(shard.get("id") or shard.get("shard_id")),
                    )
                )
            parent_ids = sorted(
                {
                    _string(shard.get("parent_paragraph_id"))
                    for shard in group_shards
                    if _string(shard.get("parent_paragraph_id"))
                }
            )
            group_cards.append(
                {
                    "idea_id": group_id,
                    "kind": "idea_group",
                    "title": _humanize_group_id(group_id),
                    "score": int(group.get("score") or 0),
                    "matched_terms": list(group.get("matched_terms") or [])[:8],
                    "shard_count": len(group_shards),
                    "matched_shard_count": int(group.get("matched_shard_count") or 0),
                    "primary_result_count": int(group.get("primary_result_count") or 0),
                    "paragraph_count": len(parent_ids),
                    "representative_parent_paragraphs": parent_ids[:5],
                    "review_plane_hints": list(group.get("review_plane_hints") or [])[:4],
                    "representative_ideas": _representative_idea_rows(group_shards, limit=4),
                    "commands": {
                        "expand_shards": f"python3 kernel.py --shards --shards-source family --shards-group {_quote_cli(group_id)} --shards-limit 12 --shards-packet",
                        "open_runtime": f"python3 kernel.py --raw-seed-navigation-runtime 09 --raw-seed-nav-group {_quote_cli(group_id)}",
                    },
                }
            )
            if len(group_cards) >= cap:
                break

        raw_seed_path = _family_root_for_shards_path(self.path) / RAW_SEED_JSON_FILENAME
        raw_seed_payload = _load_json(raw_seed_path) or {}
        paragraphs = [
            dict(item)
            for item in raw_seed_payload.get("paragraphs") or []
            if isinstance(item, Mapping) and _string(item.get("id"))
        ]
        raw_seed_paragraph_ids = {
            _string(paragraph.get("id"))
            for paragraph in paragraphs
            if _string(paragraph.get("id"))
        }
        covered_paragraph_ids = {
            _string(paragraph_id)
            for shard in self._shards
            for paragraph_id in (
                list(shard.get("raw_paragraph_ids") or [])
                + ([_string(shard.get("parent_paragraph_id"))] if _string(shard.get("parent_paragraph_id")) else [])
            )
            if _string(paragraph_id)
        }
        recent_unprocessed: list[dict[str, Any]] = []
        for paragraph in paragraphs:
            if len(recent_unprocessed) >= recent_cap:
                break
            if not _is_substantive_raw_seed_paragraph(paragraph):
                continue
            paragraph_id = _string(paragraph.get("id"))
            has_projection = bool(
                _string(paragraph.get("summary"))
                or _string_list(paragraph.get("idea_group_ids"))
                or _string_list(paragraph.get("tags"))
            )
            missing_shards = paragraph_id not in covered_paragraph_ids
            missing_projection = not has_projection
            if not missing_shards and not missing_projection:
                continue
            score, matched_terms = _score_text_values(
                query_text=query_text,
                query_tokens=query_tokens,
                values=[
                    _string(paragraph.get("plain_text")),
                    _string(paragraph.get("summary")),
                    _string(paragraph.get("section_path")),
                    " ".join(_string_list(paragraph.get("tags"))),
                    " ".join(_string_list(paragraph.get("idea_group_ids"))),
                ],
            )
            if query_text and score <= 0:
                continue
            reason_parts = []
            if missing_shards:
                reason_parts.append("not_in_loaded_shards")
            if missing_projection:
                reason_parts.append("missing_summary_tags_or_groups")
            recent_unprocessed.append(
                {
                    "paragraph_id": paragraph_id,
                    "kind": "recent_raw_seed_paragraph",
                    "score": score,
                    "matched_terms": matched_terms[:8],
                    "reason": "+".join(reason_parts) or "needs_review",
                    "section_path": _string(paragraph.get("section_path")),
                    "line_start": paragraph.get("line_start"),
                    "line_end": paragraph.get("line_end"),
                    "preview": _paragraph_preview(paragraph),
                    "commands": {
                        "resolve": f"python3 kernel.py --resolve-raw-seed-ref 09 paragraph:{_quote_cli(paragraph_id)}",
                        "browse": f"python3 kernel.py --raw-seed-browse 09 --query {_quote_cli(query or paragraph_id)}",
                    },
                }
            )

        return {
            "kind": "raw_seed_idea_browser",
            "schema_version": "raw_seed_idea_browser_v1",
            "query": _string(query),
            "ranking_mode": ranking_mode,
            "source": {
                "shards_path": _rel(self.path),
                "raw_seed_json_path": _rel(raw_seed_path),
            },
            "counts": {
                "total_shards": self.total,
                "matched_shards": matched_count,
                "idea_group_cards": len(group_cards),
                "raw_seed_paragraphs": len(paragraphs),
                "loaded_shard_paragraph_refs": len(covered_paragraph_ids),
                "raw_seed_paragraphs_with_loaded_shards": len(raw_seed_paragraph_ids & covered_paragraph_ids),
                "recent_unprocessed": len(recent_unprocessed),
            },
            "idea_cards": group_cards,
            "recent_unprocessed": recent_unprocessed,
            "next_commands": {
                "query_more": "python3 kernel.py --raw-seed-ideas 09 --query '<topic>'",
                "full_shard_packet": "python3 kernel.py --shards --shards-source family --shards-query '<topic>' --shards-packet",
                "raw_paragraphs": "python3 kernel.py --raw-seed-browse 09 --query '<topic>'",
            },
            "notes": [
                "Idea cards are a browse surface over existing shard groups, not doctrine mutations.",
                "recent_unprocessed keeps fresh raw-seed paragraphs visible before the distillation loop catches up.",
            ],
        }


def _first_80(text: str) -> str:
    return text[:80] + ("…" if len(text) > 80 else "")


def load_shards(
    family_dir: Path | str | None = None,
    *,
    explicit_path: Path | str | None = None,
    source: str | None = None,
    repo_root: Path = REPO_ROOT,
) -> ShardIndex | None:
    """
    [ACTION]
    - Teleology: Load the preferred shard envelope and wrap it in `ShardIndex` so callers can browse extracted shards or family raw-seed shards through one stable interface.
    - Mechanism: Resolve the shard path from explicit/family/source hints, fall back to the default family shard file, parse and normalize the JSON envelope, and construct a `ShardIndex`.
    - Reads: Family/source selection inputs plus the resolved shard file and, for raw-seed shards, the sibling `raw_seed.json` payload.
    - Writes: None.
    - Guarantee: Returns a `ShardIndex` for a readable shard envelope or `None` when no readable shard file is available.
    - Fails: None.
    - When-needed: Open when shard browsing should move from path discovery to an actual loaded query surface.
    - Escalates-to: tools/meta/factory/shard_browser.py; system/lib/shard_browser.py::resolve_shards_path
    - Navigation-group: kernel_lib
    """
    path = resolve_shards_path(
        family_dir=family_dir,
        explicit_path=explicit_path,
        source=source,
        repo_root=repo_root,
    )
    if path is None:
        path = repo_root / _default_family_root_relative_path(repo_root) / EXTRACTED_SHARDS_FILENAME

    data = _load_json(path)
    if data is None:
        return None
    return ShardIndex(_normalize_shards_payload(data, path=path, repo_root=repo_root), path)


def find_default_shards_path(*, repo_root: Path = REPO_ROOT) -> Path | None:
    """
    [ACTION]
    - Teleology: Resolve the default shard path the system should prefer when no explicit family or path hint is provided.
    - Mechanism: Delegate to `resolve_shards_path(source="active")` so the most recently active pipeline or phase wins by default.
    - Reads: The active-source shard-surface discovery chain.
    - Writes: None.
    - Guarantee: Returns the active-default shard path or `None`.
    - Fails: None.
    - When-needed: Open when a caller wants the same default shard-selection behavior the CLI or kernel would choose automatically.
    - Escalates-to: system/lib/shard_browser.py::discover_shard_surfaces; tools/meta/factory/shard_browser.py
    """
    return resolve_shards_path(source="active", repo_root=repo_root)
