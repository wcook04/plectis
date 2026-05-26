#!/usr/bin/env python3
"""
Run and score bounded routing-pilot packets against a hidden manual baseline.

[PURPOSE]
- Teleology: Test whether a low-cost/tool-capable worker can emit useful route
  edges from a compressed Rosetta-style surface before any continuous runtime
  or doctrine mutation exists.
- Mechanism: Build a manifest-level prompt, dispatch it through the existing
  tool_agent_harness, extract the candidate JSON, score it against the manual
  09.45 baseline, and persist score receipts.
- Non-goal: This script does not apply route edges or promote provider output.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
import uuid
from collections import Counter
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from typing import Any, Mapping


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import (  # noqa: E402
    model_profile_registry,
    nvidia_nim,
    nvidia_route_hints,
    route_candidate_builder,
    route_discovery_edc,
    route_graph_candidate_ranker,
    route_node_card_builder,
    route_operator_court,
    route_verb_correction,
    tool_agent_harness,
)
from system.lib.repo_env import maybe_reexec_into_repo_python  # noqa: E402


if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)


PHASE_DIR = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/"
    "09.45 - Phase 09.45 - Routing-First Micro-Metabolism and NVIDIA Type A Harness"
)
SCOPE_MANIFEST_REL = f"{PHASE_DIR}/scope_manifest.json"
BASELINE_REL = "state/raw_seed_routing_pilot/09_45_manual_baseline/routing_review.manual.json"
GRAMMAR_REL = "codex/standards/std_navigation_rosetta_grammar.json"
STATE_ROOT_REL = "state/raw_seed_routing_pilot/09_45_route_packet_bench"
SCOREBOARD_REL = "state/raw_seed_routing_pilot/routing_scoreboard.jsonl"
PROPOSED_EDGES_REL = "state/raw_seed_routing_pilot/proposed_edges.jsonl"
ACCEPTED_EDGES_REL = "state/raw_seed_routing_pilot/accepted_edges.jsonl"
OPERATOR_COURT_APPEALS_REL = "state/raw_seed_routing_pilot/operator_court_appeals.jsonl"
BENCH_SCHEMA_VERSION = "routing_pilot_bench_v0"
SCORE_SCHEMA_VERSION = "routing_pilot_score_v0"
ROUTE_WORKER_PACKET_SCHEMA_VERSION = "route_worker_packet_v2"
ROUTE_BROWSE_SCOUT_PACKET_SCHEMA_VERSION = "route_browse_scout_packet_v1"
MICRO_CORE_PATHS = [
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json",
    "codex/doctrine/paper_modules/navigation_hologram_theory.md",
    "codex/standards/std_navigation_rosetta_grammar.json",
    "codex/doctrine/paper_modules/inference_tier_ladder.md",
    "docs/nvidia_nim_backend.md",
    "system/lib/nvidia_nim.py",
    "system/lib/type_a_worker_harness.py",
]
MICRO_COMMAND_TREE_PATHS = [
    *MICRO_CORE_PATHS,
    "opencode.json",
    f"{PHASE_DIR}/scope_manifest.json",
    f"{PHASE_DIR}/synth_seed.json",
    f"{PHASE_DIR}/opencode_nvidia_type_a_annex.md",
]
METADATA_ENRICHED_LEVELS = {"micro_metadata_slate", "micro_relation_embedding_slate"}
PAIR_SLATE_LEVELS = {"micro_pair_slate", "micro_metadata_slate", "micro_relation_embedding_slate", "micro_routing_skill_slate"}
CORE_LEVELS = {
    "micro_core_rosetta",
    "micro_pair_slate",
    "micro_metadata_slate",
    "micro_relation_embedding_slate",
    "micro_routing_skill_slate",
    "L0_tool_browse",
    "L1_node_card",
    "L2_relation_card",
    "L3_rosetta_only",
}
PAIR_SLATE_LEVELS |= {"L0_tool_browse", "L2_relation_card"}
COMPRESSION_LEVEL_ALIASES = {
    "l0": "L0_tool_browse",
    "l0_tool_browse": "L0_tool_browse",
    "tool-browse": "L0_tool_browse",
    "tool_browse": "L0_tool_browse",
    "l1": "L1_node_card",
    "l1_node_card": "L1_node_card",
    "node-card": "L1_node_card",
    "node_card": "L1_node_card",
    "l2": "L2_relation_card",
    "l2_relation_card": "L2_relation_card",
    "relation-card": "L2_relation_card",
    "relation_card": "L2_relation_card",
    "l3": "L3_rosetta_only",
    "l3_rosetta_only": "L3_rosetta_only",
    "rosetta-only": "L3_rosetta_only",
    "rosetta_only": "L3_rosetta_only",
}
STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "also",
    "because",
    "before",
    "being",
    "between",
    "could",
    "from",
    "have",
    "into",
    "like",
    "more",
    "must",
    "only",
    "other",
    "path",
    "phase",
    "repo",
    "route",
    "routing",
    "seed",
    "should",
    "source",
    "state",
    "system",
    "target",
    "than",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "what",
    "when",
    "where",
    "which",
    "with",
    "worker",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical_compression_level(value: str | None) -> str:
    token = str(value or "scope_manifest_rosetta").strip()
    return COMPRESSION_LEVEL_ALIASES.get(token.lower(), token)


def _month_slug(value: str | None = None) -> str:
    return (value or _utc_now())[:7]


def _read_json(rel_path: str | Path) -> dict[str, Any]:
    path = Path(rel_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"Expected JSON object at {path}")
    return dict(payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")


def _append_operator_court_appeals(rows: list[Mapping[str, Any]]) -> str | None:
    if not rows:
        return None
    path = REPO_ROOT / OPERATOR_COURT_APPEALS_REL
    for row in rows:
        _append_jsonl(path, row)
    return _rel(path)


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _state_path(bucket: str, artifact_id: str, *, suffix: str = ".json", created_at: str | None = None) -> Path:
    return REPO_ROOT / STATE_ROOT_REL / bucket / _month_slug(created_at) / f"{artifact_id}{suffix}"


def _decode_text(value: Any) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value or "")


def _route_universe(baseline: Mapping[str, Any], scope_manifest: Mapping[str, Any]) -> list[str]:
    paths: set[str] = set()
    for row in scope_manifest.get("files") or []:
        if isinstance(row, Mapping) and row.get("path"):
            paths.add(str(row["path"]))
    for edge in baseline.get("routing_decisions") or []:
        if not isinstance(edge, Mapping):
            continue
        if edge.get("source"):
            paths.add(str(edge["source"]))
        if edge.get("target"):
            paths.add(str(edge["target"]))
    return sorted(paths)


def _route_universe_for_level(
    baseline: Mapping[str, Any],
    scope_manifest: Mapping[str, Any],
    compression_level: str,
) -> list[str]:
    compression_level = _canonical_compression_level(compression_level)
    if compression_level == "L3_rosetta_only":
        return list(MICRO_CORE_PATHS)
    if compression_level in {"L0_tool_browse", "L1_node_card", "L2_relation_card"}:
        return list(MICRO_COMMAND_TREE_PATHS)
    if compression_level in CORE_LEVELS:
        return list(MICRO_CORE_PATHS)
    if compression_level == "micro_command_tree":
        return list(MICRO_COMMAND_TREE_PATHS)
    return _route_universe(baseline, scope_manifest)


def _pair_slate_for_level(
    baseline: Mapping[str, Any],
    scope_manifest: Mapping[str, Any],
    compression_level: str,
) -> list[dict[str, str]]:
    compression_level = _canonical_compression_level(compression_level)
    if compression_level not in PAIR_SLATE_LEVELS:
        return []
    universe = set(_route_universe_for_level(baseline, scope_manifest, compression_level))
    baseline_pairs = [
        {
            "source": str(edge.get("source")),
            "target": str(edge.get("target")),
            "pair_id": f"baseline_like_{idx:02d}",
        }
        for idx, edge in enumerate(baseline.get("routing_decisions") or [], start=1)
        if isinstance(edge, Mapping)
        and str(edge.get("source")) in universe
        and str(edge.get("target")) in universe
    ]
    distractors = [
        {
            "pair_id": "distractor_01",
            "source": "system/lib/type_a_worker_harness.py",
            "target": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
        },
        {
            "pair_id": "distractor_02",
            "source": "docs/nvidia_nim_backend.md",
            "target": "codex/standards/std_navigation_rosetta_grammar.json",
        },
        {
            "pair_id": "distractor_03",
            "source": "system/lib/nvidia_nim.py",
            "target": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/system_axiom_candidates.json",
        },
        {
            "pair_id": "distractor_04",
            "source": "codex/doctrine/paper_modules/inference_tier_ladder.md",
            "target": "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json",
        },
    ]
    return baseline_pairs + distractors


def _scope_projection(scope_manifest: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "kind": scope_manifest.get("kind"),
        "phase_id": scope_manifest.get("phase_id"),
        "selection_rule": scope_manifest.get("selection_rule"),
        "sight_boundaries": scope_manifest.get("sight_boundaries"),
        "minimum_success": scope_manifest.get("minimum_success"),
        "files": [
            {
                "id": row.get("id"),
                "path": row.get("path"),
                "kind": row.get("kind"),
                "role": row.get("role"),
                "open_for": row.get("open_for"),
            }
            for row in scope_manifest.get("files") or []
            if isinstance(row, Mapping)
        ],
    }


def _file_rows(scope_manifest: Mapping[str, Any], route_universe: list[str]) -> list[dict[str, Any]]:
    by_path = {
        str(row.get("path")): row
        for row in scope_manifest.get("files") or []
        if isinstance(row, Mapping) and row.get("path")
    }
    rows: list[dict[str, Any]] = []
    for index, path in enumerate(route_universe, start=1):
        row = by_path.get(path, {})
        rows.append(
            {
                "node_id": f"n{index:02d}",
                "path": path,
                "kind": row.get("kind") or _path_kind(path),
                "role": row.get("role") or _path_role_hint(path),
                "open_for": row.get("open_for") or [],
            }
        )
    return rows


def _read_text_sample(path: str, *, max_chars: int = 24000) -> str:
    full_path = REPO_ROOT / path
    try:
        return full_path.read_text(encoding="utf-8", errors="replace")[:max_chars]
    except OSError:
        return ""


def _path_tokens(path: str) -> list[str]:
    return _top_terms(path.replace("/", " ").replace("_", " ").replace("-", " "), limit=10)


def _json_key_sample(text: str, *, limit: int = 18) -> list[str]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    keys: list[str] = []

    def walk(value: Any) -> None:
        if len(keys) >= limit:
            return
        if isinstance(value, Mapping):
            for key, child in value.items():
                if len(keys) >= limit:
                    return
                key_text = str(key)
                if key_text not in keys:
                    keys.append(key_text)
                walk(child)
        elif isinstance(value, list):
            for child in value[:4]:
                walk(child)

    walk(payload)
    return keys[:limit]


def _markdown_heading_sample(text: str, *, limit: int = 10) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        match = re.match(r"^#{1,4}\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(1).strip())
        if len(headings) >= limit:
            break
    return headings


def _python_symbol_sample(text: str, *, limit: int = 16) -> list[str]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return []
    symbols: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            symbols.append(node.name)
        if len(symbols) >= limit:
            break
    return symbols


def _top_terms(text: str, *, limit: int = 16) -> list[str]:
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}", text)
        if word.lower() not in STOPWORDS and len(word) <= 36
    ]
    counts = Counter(words)
    return [word for word, _count in counts.most_common(limit)]


def _domain_tags(path: str, text: str) -> list[str]:
    haystack = f"{path}\n{text[:12000]}".lower()
    tag_rules = {
        "authority": ["principle", "axiom", "governs", "authority", "doctrine"],
        "routing_grammar": ["connector", "verb", "route", "rosetta", "edge"],
        "navigation_theory": ["navigation", "hologram", "option surface", "reverse read"],
        "nvidia_provider": ["nvidia", "nim", "deepseek", "glm", "provider"],
        "embedding": ["embedding", "semantic", "vector", "retrieval", "nv-embed"],
        "runtime_harness": ["harness", "worker", "agent", "opencode", "claude"],
        "state_receipts": ["receipt", "state/", "candidate", "score", "raw_output"],
        "json_contract": ["schema_version", "json", "contract", "machine"],
        "python_runtime": ["def ", "class ", "subprocess", "requests", "argparse"],
    }
    tags = [tag for tag, needles in tag_rules.items() if any(needle in haystack for needle in needles)]
    return tags[:8]


def _node_metadata(row: Mapping[str, Any]) -> dict[str, Any]:
    path = str(row.get("path") or "")
    text = _read_text_sample(path)
    structural_keys: list[str] = []
    if path.endswith(".json"):
        structural_keys = _json_key_sample(text)
    elif path.endswith(".md"):
        structural_keys = _markdown_heading_sample(text)
    elif path.endswith(".py"):
        structural_keys = _python_symbol_sample(text)
    return {
        "node_id": row.get("node_id"),
        "path_fingerprint": hashlib.sha1(path.encode("utf-8")).hexdigest()[:12],
        "path_tokens": _path_tokens(path),
        "structural_keys": structural_keys,
        "top_terms": _top_terms(text, limit=18),
        "domain_tags": _domain_tags(path, text),
        "semantic_summary_line": _semantic_summary_line(row, structural_keys),
    }


def _semantic_summary_line(row: Mapping[str, Any], structural_keys: list[str]) -> str:
    bits = [
        str(row.get("role") or ""),
        f"kind={row.get('kind')}",
    ]
    open_for = row.get("open_for")
    if isinstance(open_for, list) and open_for:
        bits.append("open_for=" + "; ".join(str(item) for item in open_for[:3]))
    if structural_keys:
        bits.append("keys=" + ", ".join(structural_keys[:6]))
    return " | ".join(bit for bit in bits if bit)


def _metadata_for_node(metadata_index: Mapping[str, Any], node_id: str) -> dict[str, Any]:
    for node in metadata_index.get("node_metadata") or []:
        if isinstance(node, Mapping) and str(node.get("node_id")) == node_id:
            return dict(node)
    return {}


def _compact_node_text(row: Mapping[str, Any], metadata: Mapping[str, Any]) -> str:
    return " | ".join(
        part
        for part in [
            f"path={row.get('path')}",
            f"kind={row.get('kind')}",
            f"role={row.get('role')}",
            "open_for=" + "; ".join(str(item) for item in row.get("open_for")[:3])
            if isinstance(row.get("open_for"), list)
            else "",
            "domain_tags=" + ", ".join(str(item) for item in metadata.get("domain_tags") or []),
            "structural_keys=" + ", ".join(str(item) for item in metadata.get("structural_keys") or []),
            "top_terms=" + ", ".join(str(item) for item in metadata.get("top_terms") or []),
        ]
        if part
    )


def _metadata_index(file_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    nodes = [_node_metadata(row) for row in file_rows]
    tag_index: dict[str, list[str]] = {}
    term_index: dict[str, list[str]] = {}
    for node in nodes:
        node_id = str(node.get("node_id"))
        for tag in node.get("domain_tags") or []:
            tag_index.setdefault(str(tag), []).append(node_id)
        for term in node.get("top_terms") or []:
            ids = term_index.setdefault(str(term), [])
            if len(ids) < 5:
                ids.append(node_id)
    return {
        "extraction_method": "deterministic_path_structure_terms_v0",
        "node_metadata": nodes,
        "domain_tag_index": {key: value for key, value in sorted(tag_index.items())},
        "shared_term_index_sample": {
            key: value
            for key, value in sorted(term_index.items())
            if len(value) >= 2
        },
    }


def _cosine(left: list[float], right: list[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _nvidia_embedding_hints(
    *,
    file_rows: list[Mapping[str, Any]],
    metadata_index: Mapping[str, Any],
    pair_slate: list[dict[str, str]],
    verbs: list[str],
    enabled: bool,
) -> dict[str, Any]:
    if not enabled:
        return {
            "status": "disabled",
            "reason": "Set compression_level=micro_metadata_slate or --include-embedding-hints to request hosted NVIDIA embedding hints.",
        }
    by_path = {str(row.get("path")): idx for idx, row in enumerate(file_rows)}
    del verbs
    passages: list[str] = []
    passage_pairs: list[dict[str, str]] = []
    for pair in pair_slate:
        source_idx = by_path.get(str(pair.get("source")))
        target_idx = by_path.get(str(pair.get("target")))
        if source_idx is None or target_idx is None:
            continue
        source = file_rows[source_idx]
        target = file_rows[target_idx]
        source_meta = _metadata_for_node(metadata_index, str(source.get("node_id")))
        target_meta = _metadata_for_node(metadata_index, str(target.get("node_id")))
        passages.append(_route_pair_passage(pair, source, target, source_meta, target_meta))
        passage_pairs.append(
            {
                "pair_id": pair.get("pair_id"),
                "source": pair.get("source"),
                "target": pair.get("target"),
            }
        )
    if not passages:
        return {
            "status": "empty",
            "provider": "nvidia_nim",
            "reason": "No pair passages were available.",
        }
    try:
        query_vectors = nvidia_nim.embed_texts(
            [_route_pair_retrieval_query()],
            config={"input_type": "query", "timeout_s": 45},
        )
        passage_vectors = nvidia_nim.embed_texts(
            passages,
            config={"input_type": "passage", "timeout_s": 45},
        )
    except Exception as exc:
        return {
            "status": "unavailable",
            "provider": "nvidia_nim",
            "error_type": type(exc).__name__,
            "error": str(exc)[:500],
        }
    relation_scores = []
    query_vector = query_vectors[0]
    for pair, passage_vector in zip(passage_pairs, passage_vectors):
        relation_scores.append(
            {
                **pair,
                "relatedness_score": round(_cosine(query_vector, passage_vector), 6),
                "why_available": "NV-Embed retrieval says this source-target passage is worth symbolic route inspection.",
            }
        )
    relation_scores.sort(key=lambda row: float(row.get("relatedness_score") or 0), reverse=True)
    return {
        "status": "ok",
        "provider": "nvidia_nim",
        "model": nvidia_nim.DEFAULT_EMBED_MODEL,
        "advisory_only": True,
        "embedding_prompt_shape": "nv_embed_instruct_query_vs_unprefixed_pair_passages_v2",
        "model_usage_note": "NV-Embed docs say query embeddings should use input_type=query and task-specific instructions; indexed documents/passages should use input_type=passage. The packet follows that shape.",
        "interpretation": "Scores rank whether a directed source->target pair is worth symbolic inspection. They are retrieval hints only, not truth labels or verb predictions.",
        "pair_relatedness_rank": relation_scores,
    }


def _routing_skill_packet() -> dict[str, Any]:
    return {
        "kind": "semantic_route_judge_skill",
        "schema_version": "semantic_route_judge_skill_v1",
        "core_definition": {
            "semantic_route_edge": "A directed, typed information-flow claim: reading the source should materially change how a worker understands, validates, configures, generates, navigates to, or distrusts the target.",
            "not_a_route_edge": "A pair is not valid merely because both files share words, live in the same phase, mention NVIDIA, or feel topically adjacent.",
            "direction_test": "Ask: if I open SOURCE first, what specifically becomes clearer, possible, constrained, stale, or blocked about TARGET?",
        },
        "two_lane_contract": {
            "route_edges": "Scored slate answers. Use only for candidate_pair_slate rows that pass the gates in the listed direction.",
            "discovery_edges": "Invented or unexpected edges that may be useful to the graph but are not being claimed as answers to the hidden benchmark. These require definitions and promotion requirements.",
            "no_answer_edges": "Slate rows rejected or too uncertain under the current packet.",
        },
        "decision_procedure": [
            "1. Path gate: source and target must both be listed, distinct, and in the candidate slate when a slate exists.",
            "2. Slate-direction gate: if candidate_pair_slate is present, treat source->target as locked. Do not reverse it. If only target->source works, ABSTAIN for the listed pair.",
            "3. Slate-accounting gate: each pair_id may appear at most once total, either route_edges or no_answer_edges. Never emit a route edge for a pair_id you abstained.",
            "4. Evidence gate: identify at least two concrete evidence anchors from role, open_for, structural_keys, top_terms, domain_tags, or explicit path purpose.",
            "5. Direction gate: write a one-sentence reverse_gloss in the form 'TARGET reads SOURCE because ...'. If this sentence is vague, ABSTAIN.",
            "6. Specific verb gate: test lifecycle/dataflow/navigation verbs before generic proof/authority verbs.",
            "7. Confidence gate: emit only if a skeptical reviewer would agree the edge helps a future worker route between files. Otherwise ABSTAIN.",
        ],
        "verb_ladder": [
            {
                "verb": "invalidates",
                "test": "Does SOURCE contain newer code/config/default/status that makes TARGET stale or wrong?",
                "positive_shape": "runtime code default -> older backend doc, status note, or config prose",
                "negative_shape": "two files merely disagree in topic or level",
            },
            {
                "verb": "blocks",
                "test": "Does SOURCE state a missing proof/auth/smoke/caveat that prevents TARGET from being used or promoted?",
                "positive_shape": "backend caveat/status note -> unproven harness config",
                "negative_shape": "SOURCE is just more authoritative than TARGET",
            },
            {
                "verb": "routes_to",
                "test": "Is SOURCE a navigation surface, theory of navigation, phase plan, index, or option surface that points work toward TARGET?",
                "positive_shape": "navigation theory or phase plan -> scope manifest or baseline work item",
                "negative_shape": "SOURCE merely discusses routing as a topic",
            },
            {
                "verb": "compresses",
                "test": "Is one side a smaller projection/receipt/axiom layer distilled from a broader source?",
                "positive_shape": "broad axiom/theory layer -> smaller candidate clauses or durable route receipt",
                "negative_shape": "a short file and a long file on the same topic",
            },
            {
                "verb": "populates",
                "test": "Does SOURCE provide fields, vocabulary, generated rows, or write logic that fills TARGET?",
                "positive_shape": "grammar/schema -> synth/work item fields; runner -> state artifact",
                "negative_shape": "SOURCE is merely referenced by TARGET",
            },
            {
                "verb": "feeds",
                "test": "Does TARGET consume SOURCE at runtime as data/config/API/model/input?",
                "positive_shape": "provider client -> worker harness; config -> runtime client",
                "negative_shape": "documentation explains implementation",
            },
            {
                "verb": "audits",
                "test": "Does SOURCE check, review, verify, score, or bound TARGET?",
                "positive_shape": "annex caveat/promotion rule -> config it evaluates",
                "negative_shape": "SOURCE merely contains evidence about TARGET",
            },
            {
                "verb": "evidences",
                "test": "Does SOURCE prove or exemplify TARGET without controlling it?",
                "positive_shape": "backend doc lists functions implemented by runtime module; theory motivates grammar",
                "negative_shape": "SOURCE actually constrains TARGET, feeds TARGET, or marks TARGET stale",
            },
            {
                "verb": "governs",
                "test": "Does SOURCE function as an authority/constraint that TARGET must obey?",
                "positive_shape": "principle/doctrine/standard -> implementation, backend note, manifest, or harness",
                "negative_shape": "SOURCE is simply more abstract or earlier in history",
            },
        ],
        "anti_patterns": [
            {
                "name": "slate_reversal",
                "bad_reason": "The listed pair is SOURCE -> TARGET, but the model emits TARGET -> SOURCE because the reverse seems more natural.",
                "fix": "In slate mode, never reverse. Emit the listed direction or ABSTAIN.",
            },
            {
                "name": "same_topic_is_not_a_route",
                "bad_reason": "Both files mention NVIDIA/routing/worker.",
                "fix": "Require a concrete material effect: consumes, constrains, verifies, fills, routes, invalidates, blocks.",
            },
            {
                "name": "generic_governs_collapse",
                "bad_reason": "A theory or principle is upstream of everything.",
                "fix": "Use governs only when the target must obey the source. If the source merely motivates or proves, use evidences.",
            },
            {
                "name": "generic_evidences_collapse",
                "bad_reason": "The source says something true about the target.",
                "fix": "Check if a narrower verb applies first: feeds, populates, compresses, routes_to, invalidates, blocks, audits.",
            },
            {
                "name": "reverse_edge_error",
                "bad_reason": "TARGET helps explain SOURCE but the emitted edge says SOURCE -> TARGET.",
                "fix": "Use the reverse_gloss. If 'TARGET reads SOURCE because...' sounds backwards, ABSTAIN or reverse the pair if allowed.",
            },
            {
                "name": "embedding_overtrust",
                "bad_reason": "High relatedness score means valid edge.",
                "fix": "Embedding only suggests inspection priority. It never supplies direction, verb, or truth.",
            },
            {
                "name": "quota_filling",
                "bad_reason": "The model emits weak/distractor edges to reach edge_budget after abstaining hard true pairs.",
                "fix": "edge_budget is a maximum, not a quota. Emit fewer edges rather than decorative edges.",
            },
            {
                "name": "abstain_then_emit",
                "bad_reason": "The same pair_id appears in no_answer_edges and route_edges.",
                "fix": "A pair_id is either accepted or abstained, never both.",
            },
        ],
        "synthetic_examples": [
            {
                "source_role": "standard defining JSON fields",
                "target_role": "phase synth that fills those fields",
                "best_verb": "populates",
                "why": "The source supplies field vocabulary; it is more specific than governs.",
            },
            {
                "source_role": "new runtime default in code",
                "target_role": "older prose describing the previous default",
                "best_verb": "invalidates",
                "why": "The code makes the doc stale unless the doc is updated.",
            },
            {
                "source_role": "provider client module",
                "target_role": "worker harness that calls providers",
                "best_verb": "feeds",
                "why": "The target consumes the source at runtime.",
            },
            {
                "source_role": "annex with caveats and promotion rule",
                "target_role": "external harness config",
                "best_verb": "audits",
                "why": "The source evaluates/bounds use of the target.",
            },
            {
                "source_role": "raw principles",
                "target_role": "backend note adapting an external provider",
                "best_verb": "governs",
                "why": "The note must obey the principle boundary between verified substrate and aspiration.",
            },
            {
                "source_role": "candidate axiom layer",
                "target_role": "larger theory paper",
                "best_verb": "compresses",
                "why": "The source is a smaller constitutional projection of a broader theory posture.",
            },
            {
                "source_role": "two runtime files sharing keywords but no consume/write/audit/staleness relation",
                "target_role": "same topic runtime file",
                "best_verb": "ABSTAIN",
                "why": "Topical similarity alone is not a route edge.",
            },
        ],
        "required_output_posture": [
            "Favor abstention over decorative edges.",
            "Use low confidence when direction is plausible but not proven.",
            "In evidence_phrases, cite the actual anchors that made the edge pass the gates.",
            "If an unscored edge seems genuinely useful, put it in discovery_edges instead of route_edges.",
            "Never claim hidden baseline knowledge.",
        ],
    }


def _route_pair_retrieval_query() -> str:
    return (
        "Instruct: Given metadata for source and target files in a software knowledge graph, "
        "retrieve directed candidate pairs where the source meaningfully affects the target. "
        "Valid route relations include source governs target, evidences target, feeds target, "
        "populates target, compresses into target, routes to target, invalidates target, audits target, "
        "or blocks target. Exclude unrelated distractors and reversed relations.\n"
        "Query: valid directed semantic route edge from source file to target file"
    )


def _route_pair_passage(
    pair: Mapping[str, str],
    source: Mapping[str, Any],
    target: Mapping[str, Any],
    source_meta: Mapping[str, Any],
    target_meta: Mapping[str, Any],
) -> str:
    return (
        f"Pair id: {pair.get('pair_id')}.\n"
        f"Source file metadata: {_compact_node_text(source, source_meta)}.\n"
        f"Target file metadata: {_compact_node_text(target, target_meta)}."
    )


def _path_kind(path: str) -> str:
    if path.endswith(".py"):
        return "python_runtime"
    if path.endswith(".md"):
        return "paper_or_annex_note"
    if path.endswith(".json"):
        return "json_contract"
    return "artifact"


def _path_role_hint(path: str) -> str:
    if "raw_seed_principles" in path:
        return "principle authority source"
    if "system_axiom_candidates" in path:
        return "candidate axiom compression layer"
    if "navigation_hologram_theory" in path:
        return "navigation and routing theory"
    if "inference_tier_ladder" in path:
        return "model tier and authority boundary doctrine"
    if "std_navigation_rosetta" in path:
        return "legal route verb and edge grammar"
    if "nvidia_nim_backend" in path:
        return "NVIDIA provider backend note"
    if "nvidia_nim.py" in path:
        return "NVIDIA runtime client"
    if "type_a_worker_harness" in path:
        return "bounded provider worker harness"
    if path == "opencode.json":
        return "external harness provider config"
    if "scope_manifest" in path:
        return "bounded routing test manifest"
    if "synth_seed" in path:
        return "phase synthesis seed"
    if "opencode_nvidia_type_a_annex" in path:
        return "external harness annex and caveats"
    return "routeable artifact"


def _relevant_tree(file_rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    groups = {
        "operator_seed": ["raw_seed/raw_seed_principles.json", "raw_seed/system_axiom_candidates.json"],
        "routing_theory": ["navigation_hologram_theory.md", "std_navigation_rosetta_grammar.json"],
        "compute_boundary": ["inference_tier_ladder.md", "nvidia_nim_backend.md"],
        "runtime_surfaces": ["system/lib/nvidia_nim.py", "system/lib/type_a_worker_harness.py"],
        "external_harness": ["opencode.json", "opencode_nvidia_type_a_annex.md"],
        "phase_artifacts": ["scope_manifest.json", "synth_seed.json"],
    }
    return {
        group: [
            {
                "node_id": str(row.get("node_id")),
                "path": str(row.get("path")),
                "role": str(row.get("role")),
            }
            for row in file_rows
            if any(needle in str(row.get("path")) for needle in needles)
        ]
        for group, needles in groups.items()
    }


def _command_packet(
    *,
    compression_level: str,
    route_universe: list[str],
    scope_manifest: Mapping[str, Any],
    pair_slate: list[dict[str, str]],
    verbs: list[str],
    include_embedding_hints: bool = False,
) -> dict[str, Any]:
    compression_level = _canonical_compression_level(compression_level)
    file_rows = _file_rows(scope_manifest, route_universe)
    metadata_index = _metadata_index(file_rows)
    node_cards = route_node_card_builder.build_node_cards(
        REPO_ROOT,
        route_universe,
        manifest_rows=[
            row
            for row in scope_manifest.get("files") or []
            if isinstance(row, Mapping)
        ],
    )
    slate_relation_cards = route_candidate_builder.build_candidate_pairs(
        node_cards,
        slate_pairs=pair_slate,
        max_pairs=24,
    )
    deterministic_relation_cards = route_candidate_builder.build_candidate_pairs(
        node_cards,
        max_pairs=24,
        max_pairs_per_source=4,
    )
    relation_cards = slate_relation_cards if pair_slate else deterministic_relation_cards
    graph_candidate_ranks = route_graph_candidate_ranker.build_graph_candidate_ranks(
        node_cards,
        deterministic_relation_cards,
        accepted_edges_path=REPO_ROOT / ACCEPTED_EDGES_REL,
        proposed_edges_path=REPO_ROOT / PROPOSED_EDGES_REL,
        top_k=8,
    )
    graph_rank_lookup: dict[tuple[str, str], dict[str, Any]] = {}
    for source, rows in (graph_candidate_ranks.get("ranked_by_source") or {}).items():
        if not isinstance(rows, list):
            continue
        for rank_index, row in enumerate(rows, start=1):
            if isinstance(row, Mapping):
                graph_rank_lookup[(str(source), str(row.get("target") or ""))] = {
                    "rank": rank_index,
                    "score": row.get("score"),
                    "rank_source": row.get("rank_source"),
                }
    relation_cards = [
        {
            **dict(card),
            "graph_rank_hint": graph_rank_lookup.get((str(card.get("source")), str(card.get("target")))),
        }
        for card in relation_cards
    ]
    embedding_hints_enabled = include_embedding_hints or compression_level in METADATA_ENRICHED_LEVELS
    route_hints = nvidia_route_hints.build_route_hints(
        node_cards,
        relation_cards,
        enabled=embedding_hints_enabled,
        include_rerank=include_embedding_hints and compression_level == "L2_relation_card",
        embedding_model_profile_id="embed_code" if compression_level == "L2_relation_card" else "embed_general",
    )
    if compression_level == "L3_rosetta_only":
        packet_node_cards = [route_node_card_builder.slim_node_card(card) for card in node_cards]
        packet_relation_cards: list[dict[str, Any]] = []
    else:
        packet_node_cards = node_cards
        packet_relation_cards = relation_cards
    route_worker_packet_v2 = {
        "kind": "route_worker_packet",
        "schema_version": ROUTE_WORKER_PACKET_SCHEMA_VERSION,
        "mode": "benchmark_with_discovery",
        "compression_level": compression_level,
        "worker_contract": {
            "primary_goal": "classify typed directed information-flow edges",
            "not_goal": "topical similarity, vague association, quota filling, or canonical graph mutation",
            "allowed_commands": [
                "LIST_TREE",
                "READ_NODE_CARD",
                "CONSIDER_PAIR",
                "EMIT_ROUTE_EDGE",
                "ABSTAIN",
                "PROPOSE_DISCOVERY_EDGE",
                "REPORT_BLOCKER",
            ],
            "apply_mode": "no_apply",
        },
        "job_separation": {
            "candidate_discovery": "Which target files might matter?",
            "edge_judgment": "Does this directed source->target edge exist?",
            "verb_classification": "Which connector verb best describes the typed flow?",
            "metabolic_discovery": "What useful new edge, term, standard refinement, or compression artifact should be proposed without applying it?",
        },
        "node_cards": packet_node_cards,
        "candidate_pairs": packet_relation_cards,
        "candidate_surfacing": {
            "deterministic_relation_cards": "candidate_pairs",
            "graph_ppr_hints": graph_candidate_ranks,
            "retrieval_hints": "retrieval_hints",
            "interpretation": "Candidate surfacing ranks what deserves inspection; it does not decide truth or verb.",
        },
        "retrieval_hints": route_hints,
        "retrieval_confidence_gates": {
            "safe_to_judge": "source_evidence + target_evidence + bridge_evidence are present or strongly implied by node/relation cards",
            "needs_more_browse": "source/target look related but bridge evidence is missing",
            "must_abstain": "candidate rests only on shared topic, shared phase, or retrieval rank",
        },
        "evidence_set_contract": {
            "source_evidence": "literal or card-backed evidence from SOURCE",
            "target_evidence": "literal or card-backed evidence from TARGET",
            "bridge_evidence": "why SOURCE affects TARGET in the listed direction",
            "rule": "Route edges should include evidence_set. evidence_phrases remains accepted for backward compatibility.",
        },
        "browse_scout_packet_v1": {
            "kind": "route_browse_scout_packet",
            "schema_version": ROUTE_BROWSE_SCOUT_PACKET_SCHEMA_VERSION,
            "role": "evidence acquisition, not final routing",
            "allowed_tools": ["Glob", "Grep", "Read"],
            "forbidden_tools": ["Edit", "Write", "Bash unless explicitly enabled"],
            "max_reads": 12,
            "max_tool_calls": 20,
            "allowed_tree": route_universe,
            "required_output": {
                "kind": "route_browse_scout_output",
                "schema_version": "route_browse_scout_output_v1",
                "evidence_cards": [],
                "candidate_pairs": [],
                "discovery_edges": [],
                "browse_trace": [],
                "blockers": [],
            },
        },
        "verb_ladder": _routing_skill_packet()["verb_ladder"],
        "output_lanes": {
            "route_edges": "scored slate answers only",
            "no_answer_edges": "candidate slate abstentions or insufficient evidence",
            "discovery_edges": "useful graph expansion proposals with definition and promotion requirements",
        },
        "promotion_protocol": {
            "target_ledger": PROPOSED_EDGES_REL,
            "requirements": [
                "valid source and target paths",
                "allowed connector verb",
                "concrete evidence phrases",
                "EDC canonicalization: extract raw relation, define pattern, canonicalize to Rosetta verb or proposed-new-pattern status",
                "non-duplication check",
                "independent worker confirmation or controller review",
                "suggested standard/routing update when the pattern recurs",
            ],
        },
    }
    is_ladder_level = compression_level in {"L0_tool_browse", "L1_node_card", "L2_relation_card", "L3_rosetta_only"}
    legacy_metadata = (
        {
            "extraction_method": "superseded_by_route_worker_packet_v2",
            "node_count": len(node_cards),
            "drilldown": "worker_command_packet.route_worker_packet_v2.node_cards",
        }
        if is_ladder_level
        else metadata_index
    )
    legacy_skill = (
        {
            "kind": "semantic_route_judge_skill",
            "schema_version": "semantic_route_judge_skill_v1_pointer",
            "drilldown": "worker_command_packet.route_worker_packet_v2.verb_ladder and output_lanes",
        }
        if is_ladder_level
        else _routing_skill_packet()
    )
    return {
        "kind": "routing_worker_command_packet",
        "schema_version": "routing_worker_command_packet_v2",
        "compression_level": compression_level,
        "operating_mode": {
            "can_mutate": False,
            "can_use_unlisted_paths": False,
            "can_claim_hidden_baseline": False,
            "read_surface": "Use provided node rows/tree. In claude_code_free runs, an exact Read(path) may be used only for listed paths; in nvidia_nim_direct runs, READ_NODE means inspect the supplied row summary only.",
        },
        "commands": [
            {
                "name": "LIST_TREE",
                "args": [],
                "effect": "Inspect relevant_tree groups and node IDs.",
            },
            {
                "name": "READ_NODE",
                "args": ["node_id"],
                "effect": "Use the supplied node row: path, kind, role, open_for. Does not authorize external paths.",
            },
            {
                "name": "INSPECT_METADATA",
                "args": ["node_id"],
                "effect": "Inspect deterministic metadata: path tokens, structural keys/headings/symbols, top terms, and domain tags.",
            },
            {
                "name": "CONSIDER_PAIR",
                "args": ["source_node_id", "target_node_id"],
                "effect": "Ask whether one legal connector verb explains semantic flow from source to target.",
            },
            {
                "name": "RANK_WITH_EMBEDDING_HINT",
                "args": ["pair_id"],
                "effect": "Use NVIDIA embedding relatedness as an advisory retrieval signal only. It may suggest which pairs deserve inspection, never the connector verb.",
            },
            {
                "name": "CHOOSE_VERB",
                "args": ["source_node_id", "target_node_id"],
                "effect": "Choose the connector verb by authority/direction rules, not by cosine alone.",
            },
            {
                "name": "EMIT_EDGE",
                "args": ["source_path", "target_path", "connector_verb", "confidence", "evidence_phrases", "reverse_gloss"],
                "effect": "Write one candidate route edge in route_edges.",
            },
            {
                "name": "DISCOVER_EDGE",
                "args": ["source_path", "target_path", "connector_verb", "definition", "why_new", "promotion_requirements"],
                "effect": "Write one invented-but-plausible route candidate in discovery_edges. Discovery edges are not scored as slate answers.",
            },
            {
                "name": "ABSTAIN",
                "args": ["source_path", "target_path", "reason", "needed_evidence"],
                "effect": "Write one no_answer_edges item when the packet is too compressed or the pair is not justified.",
            },
        ],
        "file_nodes": file_rows if not is_ladder_level else [],
        "relevant_tree": _relevant_tree(file_rows),
        "metadata_index": legacy_metadata,
        "route_worker_packet_v2": route_worker_packet_v2,
        "routing_skill_packet": legacy_skill,
        "nvidia_embedding_hints": route_hints,
        "candidate_pair_slate": pair_slate,
        "verb_decision_tests": {
            "governs": "Use when source is an authority/constraint that target must obey.",
            "evidences": "Use when source provides proof, status, implementation, smoke result, or example for target.",
            "feeds": "Use when source data/config/runtime output is consumed by target.",
            "populates": "Use when source writes or fills target state/config/artifacts.",
            "compresses": "Use when target is a smaller projection or abstraction of source.",
            "routes_to": "Use when source is an option surface/navigation entry that points toward target.",
            "invalidates": "Use when source makes target stale, wrong, superseded, or unsafe.",
            "audits": "Use when source checks/verifies target rather than configuring or governing it.",
            "blocks": "Use when source is a prerequisite/blocker preventing target from being promoted.",
        },
        "verb_disambiguation": {
            "specificity_order": [
                "invalidates",
                "blocks",
                "routes_to",
                "compresses",
                "populates",
                "feeds",
                "audits",
                "evidences",
                "governs",
            ],
            "rule": "Test specific lifecycle/dataflow/navigation verbs before generic authority/proof verbs. Use governs/evidences only after the narrower verbs fail.",
            "common_confusions": [
                {
                    "avoid": "governs",
                    "prefer": "evidences",
                    "when": "source is theory/status/prose that supports a standard or implementation, but does not constrain it as authority.",
                },
                {
                    "avoid": "evidences",
                    "prefer": "invalidates",
                    "when": "source is a code/config/default change and target is older prose that may be stale.",
                },
                {
                    "avoid": "evidences",
                    "prefer": "routes_to",
                    "when": "source is an option surface, scope manifest, phase plan, or navigation theory pointing toward a target artifact.",
                },
                {
                    "avoid": "evidences",
                    "prefer": "compresses",
                    "when": "source/target are projection layers and one is explicitly a smaller abstraction of the other.",
                },
                {
                    "avoid": "governs",
                    "prefer": "blocks",
                    "when": "source says a target must not be promoted/used yet because a smoke/auth/status condition is missing.",
                },
                {
                    "avoid": "feeds",
                    "prefer": "populates",
                    "when": "source supplies schema fields or writes durable artifact state rather than merely being consumed at runtime.",
                },
            ],
        },
        "routing_rules": [
            "Do not infer from filename alone if role/open_for contradicts it.",
            "When candidate_pair_slate is present, source and target direction are locked. Do not emit reversed pairs. If the reverse is the only plausible route, ABSTAIN.",
            "Apply routing_skill_packet.decision_procedure before emitting or abstaining.",
            "First inspect metadata_index for both nodes, then inspect relevant_tree, then choose a verb.",
            "Use shared terms/domain tags to identify candidate relatedness; use role/open_for/structural keys to decide direction and verb.",
            "NVIDIA embedding hints are pair-retrieval hints only. A high relatedness score can justify considering a pair, but cannot by itself justify EMIT_EDGE or choose the connector verb.",
            "Never infer connector_verb from embedding rank. Use verb_disambiguation.specificity_order and symbolic node evidence for verbs.",
            "Prefer governs for authority constraints, evidences for implementation/prose proof, feeds for runtime consumption, compresses for smaller projection artifacts, routes_to for option-surface traversal, invalidates for stale/default conflicts.",
            "If candidate_pair_slate is present, only emit edges for slate pairs. Reject distractors with ABSTAIN.",
            "For candidate_pair_slate, each pair_id must appear at most once across route_edges and no_answer_edges. Do not emit replacement edges to fill edge_budget.",
            "If you see a plausible edge that is not a slate answer, put it in discovery_edges with a concise definition and promotion requirements.",
            "Every edge must cite at least two evidence phrases drawn from role/open_for, structural_keys, top_terms, or domain_tags.",
        ],
    }


def _base_verbs(grammar: Mapping[str, Any], baseline: Mapping[str, Any]) -> list[str]:
    verbs = grammar.get("relation_verb_shape", {}).get("base_verbs")
    if not isinstance(verbs, list):
        verbs = baseline.get("connector_verb_allowlist") or []
    return [str(verb) for verb in verbs]


def build_prompt(compression_level: str = "scope_manifest_rosetta", *, include_embedding_hints: bool = False) -> str:
    compression_level = _canonical_compression_level(compression_level)
    scope_manifest = _read_json(SCOPE_MANIFEST_REL)
    baseline = _read_json(BASELINE_REL)
    grammar = _read_json(GRAMMAR_REL)
    verbs = _base_verbs(grammar, baseline)
    route_universe = _route_universe_for_level(baseline, scope_manifest, compression_level)
    edge_budget = (
        7
        if compression_level in PAIR_SLATE_LEVELS or compression_level == "micro_command_tree"
        else 6
        if compression_level in {"micro_core_rosetta", "L3_rosetta_only"}
        else 12
    )
    pair_slate = _pair_slate_for_level(baseline, scope_manifest, compression_level)
    command_packet = _command_packet(
        compression_level=compression_level,
        route_universe=route_universe,
        scope_manifest=scope_manifest,
        pair_slate=pair_slate,
        verbs=verbs,
        include_embedding_hints=include_embedding_hints,
    )
    payload = {
        "bench_schema_version": BENCH_SCHEMA_VERSION,
        "phase_id": "09_45",
        "compression_level": compression_level,
        "task": "Emit candidate semantic route edges for this bounded 09.45 corpus using the command packet.",
        "edge_budget": edge_budget,
        "routeable_path_universe": route_universe,
        "connector_verb_allowlist": verbs,
        "hidden_baseline_note": "A manual baseline exists but is not included. Do not invent claims of having seen it.",
        "worker_command_packet": command_packet,
        "output_schema": {
            "kind": "routing_pilot_candidate",
            "schema_version": "routing_pilot_candidate_v0",
            "phase_id": "09_45",
            "run_id": "string",
            "compression_level": compression_level,
            "route_edges": [
                {
                    "pair_id": "pair_id from candidate_pair_slate when present",
                    "source": "path from routeable_path_universe",
                    "target": "path from routeable_path_universe",
                    "connector_verb": "one allowlisted verb",
                    "confidence": "number from 0 to 1",
                    "evidence_phrases": ["short evidence strings from the compressed surface"],
                    "evidence_set": {
                        "source_evidence": [{"path": "source path", "text": "literal or card-backed evidence"}],
                        "target_evidence": [{"path": "target path", "text": "literal or card-backed evidence"}],
                        "bridge_evidence": [{"text": "why source affects target in this direction"}],
                    },
                    "retrieval_confidence": "safe_to_judge|needs_more_browse|must_abstain",
                    "reverse_gloss": "one sentence explaining how target reads source",
                    "self_doubt": "optional uncertainty note",
                }
            ],
            "no_answer_edges": [
                {
                    "pair_id": "pair_id from candidate_pair_slate when present",
                    "source": "path or null",
                    "target": "path or null",
                    "reason": "why the compressed surface is insufficient",
                    "needed_evidence": "what file or detail would resolve it",
                }
            ],
            "discovery_edges": [
                {
                    "source": "path from routeable_path_universe",
                    "target": "path from routeable_path_universe",
                    "connector_verb": "one allowlisted verb",
                    "confidence": "number from 0 to 1",
                    "raw_relation_phrase": "short natural-language relation phrase before canonicalization",
                    "definition": "concise definition of what this proposed edge means",
                    "nearest_canonical_verb": "canonical Rosetta verb or proposed_new_relation_pattern",
                    "canonicalization_status": "mapped_to_existing_verb|proposed_new_relation_pattern|duplicate_candidate",
                    "why_new": "why this belongs in discovery_edges instead of the scored slate lane",
                    "evidence_phrases": ["short evidence strings from the compressed surface"],
                    "evidence_set": {
                        "source_evidence": [],
                        "target_evidence": [],
                        "bridge_evidence": [],
                    },
                    "promotion_requirements": ["what should be verified before this edge enters the baseline/graph"],
                    "suggested_updates": ["optional concise updates to node metadata, route universe, or verb guidance"],
                }
            ],
            "_summary": {
                "teleology": "string",
                "edge_count": "integer",
                "discovery_edge_count": "integer",
                "confidence": "LOW|MEDIUM|HIGH",
            },
        },
    }
    return (
        "You are a bounded routing benchmark worker. You may reason, but output JSON only.\n"
        "Do not mutate files. Do not use paths outside routeable_path_universe. Do not use verbs outside connector_verb_allowlist.\n"
        "Use worker_command_packet as your command grammar, relevant tree, routing skill, metadata index, and optional retrieval hints. Treat commands as the only legal affordances.\n"
        "A route edge is typed information flow, not topical similarity. Apply routing_skill_packet before every edge.\n"
        "Metadata and embedding hints help decide what to inspect; they are not authority. Direction and connector verb must come from role/open_for/structural evidence.\n"
        "If worker_command_packet.candidate_pair_slate is non-empty, emit route_edges only for pairs from that slate and put rejected/uncertain pairs in no_answer_edges.\n"
        "Use discovery_edges for useful invented edges, candidate universe expansion, or new concise edge definitions. Discovery edges are encouraged when well-evidenced, but they are separate from scored route_edges.\n"
        f"Use {edge_budget} as a maximum, not a quota. Never fill the budget with weak or decorative edges. Include no_answer_edges for missing evidence or uncertain edges.\n"
        "Your job is to test whether the compressed Rosetta/scope surface is enough for useful routing.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}"
    )


def build_verb_correction_prompt(prior_candidate: Mapping[str, Any]) -> str:
    """Build a focused verb-correction prompt for already-confirmed directed pairs.

    Takes the prior run's route_edges, filters to pairs that appear in the baseline,
    and asks the model only to pick the correct Rosetta verb — pair direction is
    treated as settled and is not re-judged.
    """
    baseline = _read_json(BASELINE_REL)
    grammar = _read_json(GRAMMAR_REL)
    scope_manifest = _read_json(SCOPE_MANIFEST_REL)

    universe: set[str] = set(_route_universe(baseline, scope_manifest))
    baseline_edges: list[Any] = baseline.get("routing_decisions") or []
    prior_edges: list[Any] = prior_candidate.get("route_edges") or []

    correction_pairs = route_verb_correction.extract_verb_correction_pairs(
        prior_edges, baseline_edges, universe
    )

    verbs: list[str] = (
        grammar.get("relation_verb_shape", {}).get("base_verbs") or _base_verbs()
    )

    _SCHEMA_PLACEHOLDERS = frozenset(
        {"bridge_evidence", "source_evidence", "target_evidence", "evidence_phrase", "evidence"}
    )

    def _clean_evidence(raw: list[Any]) -> list[str]:
        return [str(e) for e in (raw or []) if str(e).strip() not in _SCHEMA_PLACEHOLDERS]

    verb_semantics = {
        "governs": "A is an authority surface (policy, standard, principle) that constrains what B may contain or do. A→B: 'A governs B'.",
        "populates": "A writes concrete content/data into B as a data source. A→B: 'A populates B'.",
        "feeds": "A provides runtime input that B directly consumes during execution. A→B: 'A feeds B'.",
        "evidences": "A contains evidence, citations, or documented observations that inform understanding of B. A→B: 'A evidences B'.",
        "audits": "A checks, validates, or monitors the operational state of B. A→B: 'A audits B'.",
        "blocks": "A is a prerequisite gate; B cannot proceed until A is satisfied. A→B: 'A blocks B'.",
        "compresses": "A is a higher-fidelity artifact that B summarises or encodes at lower resolution. A→B: 'A compresses B'.",
        "routes_to": "A is a navigation surface that points workers toward B as a destination. A→B: 'A routes_to B'.",
        "invalidates": "A contains a change that makes B stale or incorrect. A→B: 'A invalidates B'.",
        "supersedes": "A is a newer version that replaces B entirely. A→B: 'A supersedes B'.",
    }

    files = list({str(e.get("source") or "") for e in correction_pairs} | {str(e.get("target") or "") for e in correction_pairs})
    try:
        node_cards = route_node_card_builder.build_node_cards(REPO_ROOT, files)
        plane_by_path = {card["path"]: card.get("authority_plane", "") for card in node_cards}
    except Exception:
        plane_by_path = {}

    confirmed_pairs = [
        {
            "pair_id": edge.get("pair_id") or f"vc_{i:03d}",
            "source": edge.get("source"),
            "source_plane": plane_by_path.get(str(edge.get("source") or ""), ""),
            "target": edge.get("target"),
            "target_plane": plane_by_path.get(str(edge.get("target") or ""), ""),
            "evidence_set": _clean_evidence(edge.get("evidence_set") or []),
        }
        for i, edge in enumerate(correction_pairs)
    ]

    payload: dict[str, Any] = {
        "task": "verb_correction",
        "instruction": (
            "For each confirmed_pair below, source→target direction is already settled and correct. "
            "Your only job is to pick the single best connector_verb from connector_verb_allowlist. "
            "Use verb_semantics to distinguish subtle cases (governs vs populates vs evidences vs audits). "
            "Plane hints: raw_seed_projection=operator-authority-surface (prefer governs), paper_module=authored-knowledge (prefer evidences), standard=shared-grammar, runtime=execution-code, annex_review=external-validation-notes (prefer audits). "
            "Do NOT anchor on any prior — reason from filenames, planes, and evidence_set only. "
            "Return ONLY JSON: {\"verb_corrections\": [{\"pair_id\": ..., \"source\": ..., \"target\": ..., \"connector_verb\": ..., \"reasoning\": \"one sentence\"}]}"
        ),
        "connector_verb_allowlist": verbs,
        "verb_semantics": verb_semantics,
        "confirmed_pairs": confirmed_pairs,
    }
    return (
        "You are a verb-correction worker. Output JSON only. Do not re-judge direction.\n"
        "Use verb_semantics carefully: governs=authority/policy, populates=data-source, evidences=observation-record, audits=validation-check.\n"
        "source_plane/target_plane: raw_seed_projection=authority (governs), paper_module=evidence (evidences), standard=grammar, runtime=execution (feeds), annex_review=validation-notes (audits).\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)}"
    )


def _score_verb_correction(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Score a verb-correction or operator-court candidate against the manual baseline.

    Delegates to ``route_operator_court.score_operator_court_output`` so legacy
    ``verb_corrections`` payloads and new ``relation_label_decisions`` payloads
    flow through one scorer. Returns legacy-shape top-level keys
    (``correction_count``, ``pair_match_count``, ``verb_accuracy_given_pair``,
    ``valid_verb_rate``, ``exact_match_count``) plus the full operator-court
    metrics under ``operator_court_metrics``.
    """

    baseline = _read_json(BASELINE_REL)
    grammar = _read_json(GRAMMAR_REL)

    metrics = route_operator_court.score_operator_court_output(
        candidate,
        baseline.get("routing_decisions") or [],
        grammar,
    )

    return {
        "task": "verb_correction",
        "correction_count": metrics["decision_count"],
        "pair_match_count": metrics["pair_match_count"],
        "exact_match_count": metrics["exact_match_count"],
        "verb_accuracy_given_pair": metrics["verb_accuracy_given_pair"],
        "valid_verb_rate": metrics["valid_verb_rate"],
        "operator_court_metrics": metrics,
    }


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", stripped, flags=re.DOTALL)
    return fenced.group(1).strip() if fenced else stripped


def _candidate_json_from_text(text: str) -> dict[str, Any]:
    direct = _strip_code_fence(text)
    try:
        payload = json.loads(direct)
        return dict(payload) if isinstance(payload, Mapping) else {}
    except json.JSONDecodeError:
        pass
    start = direct.find("{")
    end = direct.rfind("}")
    if start >= 0 and end > start:
        try:
            payload = json.loads(direct[start : end + 1])
            return dict(payload) if isinstance(payload, Mapping) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def extract_candidate(raw_output_path: str | Path) -> dict[str, Any]:
    path = Path(raw_output_path)
    if not path.is_absolute():
        path = REPO_ROOT / path
    result_text = ""
    assistant_texts: list[str] = []
    raw_text = path.read_text(encoding="utf-8")
    if raw_text.startswith("b'") or raw_text.startswith('b"'):
        try:
            raw_text = raw_text.encode("utf-8").decode("unicode_escape")
        except UnicodeDecodeError:
            pass
    for line in raw_text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "result" and isinstance(event.get("result"), str):
            result_text = event["result"]
        message = event.get("message")
        if isinstance(message, Mapping) and message.get("role") == "assistant":
            for block in message.get("content") or []:
                if isinstance(block, Mapping) and block.get("type") == "text":
                    assistant_texts.append(str(block.get("text") or ""))
    for text in [result_text, *reversed(assistant_texts)]:
        candidate = _candidate_json_from_text(text)
        if candidate:
            return candidate
    return {}


def _edge_triple(edge: Mapping[str, Any]) -> tuple[str, str, str]:
    source = str(edge.get("source") or edge.get("source_path") or "").strip()
    target = str(edge.get("target") or edge.get("target_path") or "").strip()
    verb = str(edge.get("connector_verb") or edge.get("verb_id") or "").strip()
    return source, target, verb


def _edge_has_literal_evidence(edge: Mapping[str, Any]) -> bool:
    source, target, _verb = _edge_triple(edge)
    phrases = list(edge.get("evidence_phrases") or [])
    evidence_set = edge.get("evidence_set")
    if isinstance(evidence_set, Mapping):
        for value in evidence_set.values():
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, Mapping):
                        phrases.append(str(item.get("text") or ""))
                    else:
                        phrases.append(str(item))
    if not isinstance(phrases, list) or not phrases:
        return False
    haystack = "\n".join([_read_text_sample(source, max_chars=20000), _read_text_sample(target, max_chars=20000)]).lower()
    if not haystack:
        return False
    for phrase in phrases:
        token = str(phrase or "").strip().lower()
        if token and token in haystack:
            return True
    return False


def _evidence_set(edge: Mapping[str, Any]) -> Mapping[str, Any]:
    evidence_set = edge.get("evidence_set")
    return evidence_set if isinstance(evidence_set, Mapping) else {}


def _evidence_bucket_nonempty(evidence_set: Mapping[str, Any], bucket: str) -> bool:
    value = evidence_set.get(bucket)
    if isinstance(value, list):
        return any(str(item.get("text") if isinstance(item, Mapping) else item).strip() for item in value)
    return bool(str(value or "").strip())


def _edge_has_complete_evidence_set(edge: Mapping[str, Any]) -> bool:
    evidence_set = _evidence_set(edge)
    return all(
        _evidence_bucket_nonempty(evidence_set, bucket)
        for bucket in ("source_evidence", "target_evidence", "bridge_evidence")
    )


def _edge_has_bridge_evidence(edge: Mapping[str, Any]) -> bool:
    return _evidence_bucket_nonempty(_evidence_set(edge), "bridge_evidence")


def _score(
    candidate: Mapping[str, Any],
    *,
    raw_output_path: str | None = None,
    compression_level: str | None = None,
) -> dict[str, Any]:
    scope_manifest = _read_json(SCOPE_MANIFEST_REL)
    baseline = _read_json(BASELINE_REL)
    grammar = _read_json(GRAMMAR_REL)
    active_level = _canonical_compression_level(
        compression_level or str(candidate.get("compression_level") or "scope_manifest_rosetta")
    )
    universe = set(_route_universe_for_level(baseline, scope_manifest, active_level))
    verbs = set(_base_verbs(grammar, baseline))
    baseline_edges = [
        _edge_triple(edge)
        for edge in baseline.get("routing_decisions") or []
        if isinstance(edge, Mapping)
    ]
    baseline_edges = [
        (source, target, verb)
        for source, target, verb in baseline_edges
        if source in universe and target in universe
    ]
    baseline_triples = set(baseline_edges)
    baseline_pairs = {(source, target) for source, target, _verb in baseline_edges}
    route_edges = candidate.get("route_edges") or candidate.get("routing_decisions") or []
    candidate_edges = [edge for edge in route_edges if isinstance(edge, Mapping)]
    candidate_triples = [_edge_triple(edge) for edge in candidate_edges]
    candidate_triple_set = set(candidate_triples)
    candidate_pair_set = {(source, target) for source, target, _verb in candidate_triples}
    valid_verb_count = sum(1 for _source, _target, verb in candidate_triples if verb in verbs)
    in_universe_count = sum(
        1
        for source, target, _verb in candidate_triples
        if source in universe and target in universe
    )
    exact_matches = sorted(candidate_triple_set & baseline_triples)
    pair_matches = sorted(candidate_pair_set & baseline_pairs)
    duplicate_count = max(0, len(candidate_triples) - len(candidate_triple_set))
    required_verbs = set(scope_manifest.get("minimum_success", {}).get("required_verbs") or [])
    if active_level in {"micro_core_rosetta", "micro_command_tree"}:
        required_verbs = {verb for _source, _target, verb in baseline_edges}
    emitted_verbs = {verb for _source, _target, verb in candidate_triples if verb}
    precision = len(exact_matches) / len(candidate_triple_set) if candidate_triple_set else 0.0
    recall = len(exact_matches) / len(baseline_triples) if baseline_triples else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    pair_precision = len(pair_matches) / len(candidate_pair_set) if candidate_pair_set else 0.0
    pair_recall = len(pair_matches) / len(baseline_pairs) if baseline_pairs else 0.0
    exact_match_set = set(exact_matches)
    pair_match_set = set(pair_matches)
    verb_accuracy_given_pair = (
        sum(1 for source, target, verb in candidate_triples if (source, target) in pair_match_set and (source, target, verb) in exact_match_set)
        / len(pair_match_set)
        if pair_match_set
        else 0.0
    )
    no_answer_edges = candidate.get("no_answer_edges") or candidate.get("abstentions") or []
    if not isinstance(no_answer_edges, list):
        no_answer_edges = []
    discovery_edges = candidate.get("discovery_edges") or candidate.get("proposed_edges") or []
    discovery_candidates = [edge for edge in discovery_edges if isinstance(edge, Mapping)]
    discovery_triples = [_edge_triple(edge) for edge in discovery_candidates]
    discovery_valid_verb_count = sum(1 for _source, _target, verb in discovery_triples if verb in verbs)
    discovery_in_universe_count = sum(
        1
        for source, target, _verb in discovery_triples
        if source in universe and target in universe
    )
    discovery_with_definition_count = sum(
        1
        for edge in discovery_candidates
        if str(edge.get("definition") or "").strip()
    )
    evidence_edge_count = sum(
        1 for edge in candidate_edges if _edge_has_literal_evidence(edge)
    )
    evidence_set_complete_count = sum(1 for edge in candidate_edges if _edge_has_complete_evidence_set(edge))
    bridge_evidence_count = sum(1 for edge in candidate_edges if _edge_has_bridge_evidence(edge))
    retrieval_confidence_counts = Counter(
        str(edge.get("retrieval_confidence") or "unspecified")
        for edge in candidate_edges
    )
    pair_slate = _pair_slate_for_level(baseline, scope_manifest, active_level)
    slate_by_pair_id = {str(pair.get("pair_id")): pair for pair in pair_slate if pair.get("pair_id")}
    route_pair_ids = [str(edge.get("pair_id") or "") for edge in candidate_edges if edge.get("pair_id")]
    no_answer_pair_ids = [
        str(edge.get("pair_id") or "")
        for edge in no_answer_edges
        if isinstance(edge, Mapping) and edge.get("pair_id")
    ]
    slate_route_edge_count = 0
    for edge in candidate_edges:
        pair_id = str(edge.get("pair_id") or "")
        pair = slate_by_pair_id.get(pair_id)
        if pair and str(edge.get("source")) == str(pair.get("source")) and str(edge.get("target")) == str(pair.get("target")):
            slate_route_edge_count += 1
    duplicate_pair_id_count = max(0, len(route_pair_ids + no_answer_pair_ids) - len(set(route_pair_ids + no_answer_pair_ids)))
    edge_budget = (
        7
        if active_level == "micro_command_tree" or active_level in PAIR_SLATE_LEVELS
        else 6
        if active_level == "micro_core_rosetta"
        else int(scope_manifest.get("minimum_success", {}).get("manual_edges") or 18)
    )
    slate_decision_pair_id_count = len(set(route_pair_ids + no_answer_pair_ids))
    abstain_correct_count = 0
    abstain_checked_count = 0
    for edge in no_answer_edges:
        if not isinstance(edge, Mapping):
            continue
        pair_id = str(edge.get("pair_id") or "")
        pair = slate_by_pair_id.get(pair_id)
        if not pair:
            continue
        abstain_checked_count += 1
        if (str(pair.get("source")), str(pair.get("target"))) not in baseline_pairs:
            abstain_correct_count += 1
    discovery_well_formed_count = sum(
        1
        for edge in discovery_candidates
        if (
            _edge_triple(edge)[0] in universe
            and _edge_triple(edge)[1] in universe
            and _edge_triple(edge)[2] in verbs
            and str(edge.get("definition") or "").strip()
            and isinstance(edge.get("promotion_requirements"), list)
            and bool(edge.get("promotion_requirements"))
        )
    )
    return {
        "kind": "routing_pilot_score",
        "schema_version": SCORE_SCHEMA_VERSION,
        "phase_id": "09_45",
        "scored_at": _utc_now(),
        "baseline_ref": BASELINE_REL,
        "scope_manifest_ref": SCOPE_MANIFEST_REL,
        "raw_output_ref": raw_output_path,
        "candidate_metadata": {
            "kind": candidate.get("kind"),
            "schema_version": candidate.get("schema_version"),
            "run_id": candidate.get("run_id"),
            "compression_level": active_level,
        },
        "metrics": {
            "candidate_edge_count": len(candidate_edges),
            "baseline_edge_count": len(baseline_triples),
            "duplicate_edge_count": duplicate_count,
            "valid_verb_ratio": valid_verb_count / len(candidate_triples) if candidate_triples else 0.0,
            "in_universe_ratio": in_universe_count / len(candidate_triples) if candidate_triples else 0.0,
            "exact_triple_match_count": len(exact_matches),
            "exact_triple_precision": precision,
            "exact_triple_recall": recall,
            "exact_triple_f1": f1,
            "pair_match_count": len(pair_matches),
            "pair_precision": pair_precision,
            "pair_recall": pair_recall,
            "direction_accuracy": pair_precision,
            "verb_accuracy_given_pair": verb_accuracy_given_pair,
            "evidence_substring_rate": evidence_edge_count / len(candidate_edges) if candidate_edges else 0.0,
            "evidence_set_completeness_rate": evidence_set_complete_count / len(candidate_edges) if candidate_edges else 0.0,
            "bridge_evidence_rate": bridge_evidence_count / len(candidate_edges) if candidate_edges else 0.0,
            "retrieval_confidence_safe_to_judge_rate": (
                retrieval_confidence_counts.get("safe_to_judge", 0) / len(candidate_edges)
                if candidate_edges
                else 0.0
            ),
            "retrieval_confidence_needs_more_browse_count": retrieval_confidence_counts.get("needs_more_browse", 0),
            "retrieval_confidence_must_abstain_count": retrieval_confidence_counts.get("must_abstain", 0),
            "required_verb_coverage": sorted(required_verbs & emitted_verbs),
            "required_verb_missing": sorted(required_verbs - emitted_verbs),
            "no_answer_edge_count": len(no_answer_edges),
            "abstain_precision": abstain_correct_count / abstain_checked_count if abstain_checked_count else 0.0,
            "abstain_checked_count": abstain_checked_count,
            "discovery_edge_count": len(discovery_candidates),
            "discovery_valid_verb_ratio": discovery_valid_verb_count / len(discovery_triples) if discovery_triples else 0.0,
            "discovery_in_universe_ratio": discovery_in_universe_count / len(discovery_triples) if discovery_triples else 0.0,
            "discovery_with_definition_count": discovery_with_definition_count,
            "discovery_well_formed_rate": discovery_well_formed_count / len(discovery_candidates) if discovery_candidates else 1.0,
            "slate_route_edge_count": slate_route_edge_count,
            "slate_decision_pair_id_count": slate_decision_pair_id_count,
            "duplicate_pair_id_count": duplicate_pair_id_count,
        },
        "matches": {
            "exact_triples": [
                {"source": source, "target": target, "connector_verb": verb}
                for source, target, verb in exact_matches
            ],
            "pairs": [
                {"source": source, "target": target}
                for source, target in pair_matches
            ],
        },
        "validity": {
            "valid_json": bool(candidate),
            "minimum_edge_count_met": bool(candidate_edges) if active_level in PAIR_SLATE_LEVELS else len(candidate_edges) >= edge_budget,
            "edge_budget_respected": len(candidate_edges) <= edge_budget,
            "slate_decision_coverage_met": (
                slate_decision_pair_id_count >= min(len(pair_slate), edge_budget)
                if active_level in PAIR_SLATE_LEVELS
                else True
            ),
            "minimum_in_scope_ratio_met": (
                (in_universe_count / len(candidate_triples)) if candidate_triples else 0.0
            )
            >= float(scope_manifest.get("minimum_success", {}).get("minimum_in_scope_ratio") or 0.5),
            "must_emit_no_answer_capacity_met": bool(no_answer_edges) or active_level not in PAIR_SLATE_LEVELS,
            "discovery_edges_well_formed": (
                not discovery_candidates
                or (
                    discovery_valid_verb_count == len(discovery_triples)
                    and discovery_in_universe_count == len(discovery_triples)
                    and discovery_with_definition_count == len(discovery_candidates)
                )
            ),
        },
    }


def _proposal_fingerprint(edge: Mapping[str, Any]) -> str:
    source, target, verb = _edge_triple(edge)
    definition = str(edge.get("definition") or "").strip()
    return hashlib.sha1(f"{source}\0{target}\0{verb}\0{definition}".encode("utf-8")).hexdigest()[:16]


def _existing_proposal_fingerprints(path: Path) -> set[str]:
    if not path.exists():
        return set()
    fingerprints: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        fingerprint = str(row.get("fingerprint") or "").strip()
        if fingerprint:
            fingerprints.add(fingerprint)
    return fingerprints


def append_discovery_edges(
    candidate: Mapping[str, Any],
    *,
    run_id: str,
    candidate_ref: str,
    score_ref: str | None,
) -> dict[str, Any]:
    path = REPO_ROOT / PROPOSED_EDGES_REL
    accepted_path = REPO_ROOT / ACCEPTED_EDGES_REL
    accepted_path.parent.mkdir(parents=True, exist_ok=True)
    accepted_path.touch(exist_ok=True)
    existing = _existing_proposal_fingerprints(path)
    allowed_verbs = _base_verbs(_read_json(GRAMMAR_REL), _read_json(BASELINE_REL))
    existing_rows: list[dict[str, Any]] = []
    for ledger_path in (path, accepted_path):
        if ledger_path.exists():
            for line in ledger_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, Mapping):
                    existing_rows.append(dict(row))
    appended = 0
    skipped_duplicate = 0
    for edge in candidate.get("discovery_edges") or candidate.get("proposed_edges") or []:
        if not isinstance(edge, Mapping):
            continue
        edc = route_discovery_edc.canonicalize_discovery_edge(
            edge,
            allowed_verbs=allowed_verbs,
            existing_rows=existing_rows,
        )
        source = str(edc.get("source") or "")
        target = str(edc.get("target") or "")
        verb = str(edc.get("nearest_canonical_verb") or _edge_triple(edge)[2])
        fingerprint = route_discovery_edc.edge_fingerprint(
            source,
            target,
            verb,
            str(edge.get("definition") or ""),
        )
        if fingerprint in existing:
            skipped_duplicate += 1
            continue
        row = {
            "kind": "route_discovery_edge_proposal",
            "schema_version": "route_discovery_edge_proposal_v2",
            "proposal_id": f"pedge_{_utc_now().replace(':', '').replace('-', '')}_{fingerprint}",
            "fingerprint": fingerprint,
            "source": source,
            "target": target,
            "verb": verb,
            "raw_relation_phrase": edc.get("raw_relation_phrase"),
            "nearest_canonical_verb": edc.get("nearest_canonical_verb"),
            "canonicalization_confidence": edc.get("canonicalization_confidence"),
            "canonicalization_status": edc.get("canonicalization_status"),
            "duplicate_of": edc.get("duplicate_of"),
            "schema_pattern_cluster": edc.get("schema_pattern_cluster"),
            "definition": str(edge.get("definition") or "").strip(),
            "why_new": str(edge.get("why_new") or "").strip(),
            "evidence": edge.get("evidence_set") or edge.get("evidence_phrases") or [],
            "promotion_requirements": edge.get("promotion_requirements") or [],
            "suggested_updates": edge.get("suggested_updates") or [],
            "proposed_by": run_id,
            "candidate_ref": candidate_ref,
            "score_ref": score_ref,
            "status": "pending_confirmation",
            "created_at": _utc_now(),
        }
        _append_jsonl(path, row)
        existing.add(fingerprint)
        existing_rows.append(row)
        appended += 1
    return {
        "proposed_edges_ref": PROPOSED_EDGES_REL,
        "accepted_edges_ref": ACCEPTED_EDGES_REL,
        "appended": appended,
        "skipped_duplicate": skipped_duplicate,
    }


def append_scoreboard_row(
    *,
    run_id: str,
    backend: str,
    provider_status: str | None,
    provider_model: str | None,
    prompt_ref: str,
    raw_ref: str | None,
    candidate_ref: str,
    score_ref: str,
    score: Mapping[str, Any],
) -> str:
    metrics = dict(score.get("metrics") or {})
    validity = dict(score.get("validity") or {})
    row = {
        "kind": "routing_scoreboard_row",
        "schema_version": "routing_scoreboard_v1",
        "run_id": run_id,
        "phase_id": "09_45",
        "created_at": _utc_now(),
        "backend": backend,
        "provider_status": provider_status,
        "provider_model": provider_model,
        "compression_level": score.get("candidate_metadata", {}).get("compression_level"),
        "schema_valid": validity.get("valid_json"),
        "path_validity": metrics.get("in_universe_ratio"),
        "pair_precision": metrics.get("pair_precision"),
        "direction_accuracy": metrics.get("direction_accuracy"),
        "verb_accuracy_given_pair": metrics.get("verb_accuracy_given_pair"),
        "exact_edge_precision": metrics.get("exact_triple_precision"),
        "exact_edge_recall": metrics.get("exact_triple_recall"),
        "abstain_precision": metrics.get("abstain_precision"),
        "evidence_substring_rate": metrics.get("evidence_substring_rate"),
        "evidence_set_completeness_rate": metrics.get("evidence_set_completeness_rate"),
        "bridge_evidence_rate": metrics.get("bridge_evidence_rate"),
        "retrieval_confidence_safe_to_judge_rate": metrics.get("retrieval_confidence_safe_to_judge_rate"),
        "discovery_well_formed_rate": metrics.get("discovery_well_formed_rate"),
        "discovery_edge_count": metrics.get("discovery_edge_count"),
        "timeout_or_error": provider_status not in {None, "ok"},
        "prompt_ref": prompt_ref,
        "raw_output_ref": raw_ref,
        "candidate_ref": candidate_ref,
        "score_ref": score_ref,
    }
    _append_jsonl(REPO_ROOT / SCOREBOARD_REL, row)
    return SCOREBOARD_REL


def write_prompt_artifact(prompt: str, run_id: str, created_at: str) -> str:
    path = _state_path("prompts", run_id, suffix=".txt", created_at=created_at)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(prompt, encoding="utf-8")
    return _rel(path)


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    created_at = _utc_now()
    run_id = args.run_id or f"rpb_{uuid.uuid4().hex[:16]}"
    prompt = build_prompt(
        compression_level=args.compression_level,
        include_embedding_hints=bool(getattr(args, "include_embedding_hints", False)),
    )
    prompt_ref = write_prompt_artifact(prompt, run_id, created_at)
    if args.backend == "nvidia_nim_direct":
        model = args.model or model_profile_registry.nvidia_model_id("default_worker", fallback="z-ai/glm-5.1")
        raw_path = _state_path("raw_outputs", run_id, suffix=".jsonl", created_at=created_at)
        started_at = _utc_now()
        try:
            result_text = nvidia_nim.chat_completion(
                prompt,
                config={
                    "model": model,
                    "max_tokens": int(args.max_tokens),
                    "temperature": 0,
                    "timeout_s": int(args.max_seconds),
                },
            )
            provider_status = "ok"
            error = None
        except Exception as exc:
            result_text = ""
            provider_status = "provider_error"
            error = f"{type(exc).__name__}: {exc}"
        raw_event = {
            "type": "result",
            "subtype": provider_status,
            "provider": "nvidia_nim",
            "model": model,
            "started_at": started_at,
            "ended_at": _utc_now(),
            "result": result_text,
            "error": error,
        }
        _write_text(raw_path, json.dumps(raw_event, ensure_ascii=False, sort_keys=True) + "\n")
        raw_ref = _rel(raw_path)
        candidate = extract_candidate(raw_ref)
        candidate_path = _state_path("candidates", run_id, created_at=created_at)
        _write_json(candidate_path, candidate or {"parse_error": "candidate_json_not_found"})
        score = _score(candidate, raw_output_path=raw_ref, compression_level=args.compression_level)
        score["run_id"] = run_id
        score["provider_status"] = provider_status
        score["provider_model"] = model
        score["candidate_ref"] = _rel(candidate_path)
        score_path = _state_path("scores", run_id, created_at=created_at)
        _write_json(score_path, score)
        score_ref = _rel(score_path)
        proposal_summary = append_discovery_edges(
            candidate,
            run_id=run_id,
            candidate_ref=_rel(candidate_path),
            score_ref=score_ref,
        )
        scoreboard_ref = append_scoreboard_row(
            run_id=run_id,
            backend=args.backend,
            provider_status=provider_status,
            provider_model=model,
            prompt_ref=prompt_ref,
            raw_ref=raw_ref,
            candidate_ref=_rel(candidate_path),
            score_ref=score_ref,
            score=score,
        )
        return {
            "kind": "routing_pilot_run",
            "run_id": run_id,
            "backend": args.backend,
            "provider_status": provider_status,
            "provider_model": model,
            "prompt_ref": prompt_ref,
            "raw_output_ref": raw_ref,
            "candidate_ref": _rel(candidate_path),
            "score_ref": score_ref,
            "scoreboard_ref": scoreboard_ref,
            "proposal_summary": proposal_summary,
            "metrics": score["metrics"],
            "validity": score["validity"],
        }

    job = tool_agent_harness.build_job(
        REPO_ROOT,
        prompt=prompt,
        backend=args.backend,
        mode="plan",
        title=args.title or f"routing_pilot_{args.compression_level}",
        source_paths=[SCOPE_MANIFEST_REL, GRAMMAR_REL],
        max_seconds=int(args.max_seconds),
        allow_writes=False,
        created_by="routing_pilot_harness",
    )
    job["routing_pilot"] = {
        "run_id": run_id,
        "compression_level": args.compression_level,
        "prompt_ref": prompt_ref,
        "baseline_hidden": BASELINE_REL,
    }
    written_job = tool_agent_harness.write_job(REPO_ROOT, job)
    if args.dry_run:
        return {"kind": "routing_pilot_run", "run_id": run_id, "job": written_job, "prompt_ref": prompt_ref, "dry_run": True}
    harness_result = tool_agent_harness.run_job(REPO_ROOT, job_path=written_job["artifact_path"])
    raw_ref = harness_result.artifact_refs.get("raw_output")
    candidate = extract_candidate(raw_ref)
    candidate_path = _state_path("candidates", run_id, created_at=created_at)
    _write_json(candidate_path, candidate or {"parse_error": "candidate_json_not_found"})
    score = _score(candidate, raw_output_path=raw_ref, compression_level=args.compression_level)
    score["run_id"] = run_id
    score["tool_agent_receipt_ref"] = harness_result.artifact_refs.get("receipt")
    score["candidate_ref"] = _rel(candidate_path)
    score_path = _state_path("scores", run_id, created_at=created_at)
    _write_json(score_path, score)
    score_ref = _rel(score_path)
    proposal_summary = append_discovery_edges(
        candidate,
        run_id=run_id,
        candidate_ref=_rel(candidate_path),
        score_ref=score_ref,
    )
    scoreboard_ref = append_scoreboard_row(
        run_id=run_id,
        backend=args.backend,
        provider_status=str(harness_result.receipt.get("status")),
        provider_model=str(harness_result.receipt.get("model") or ""),
        prompt_ref=prompt_ref,
        raw_ref=raw_ref,
        candidate_ref=_rel(candidate_path),
        score_ref=score_ref,
        score=score,
    )
    return {
        "kind": "routing_pilot_run",
        "run_id": run_id,
        "job_ref": written_job["artifact_path"],
        "prompt_ref": prompt_ref,
        "tool_agent_receipt_ref": harness_result.artifact_refs.get("receipt"),
        "raw_output_ref": raw_ref,
        "candidate_ref": _rel(candidate_path),
        "score_ref": score_ref,
        "scoreboard_ref": scoreboard_ref,
        "proposal_summary": proposal_summary,
        "tool_agent_status": harness_result.receipt.get("status"),
        "metrics": score["metrics"],
        "validity": score["validity"],
    }


def score_raw(args: argparse.Namespace) -> dict[str, Any]:
    candidate = extract_candidate(args.raw_output)
    score = _score(candidate, raw_output_path=args.raw_output, compression_level=args.compression_level)
    if args.write:
        run_id = args.run_id or f"rps_{uuid.uuid4().hex[:16]}"
        path = _state_path("scores", run_id)
        _write_json(path, score)
        score["score_ref"] = _rel(path)
    return score


def run_verb_correction(args: argparse.Namespace) -> dict[str, Any]:
    """Dispatch a verb-correction run against a prior candidate and score the result."""
    created_at = _utc_now()
    run_id = args.run_id or f"rpvc_{uuid.uuid4().hex[:12]}"

    prior_path = Path(args.prior_candidate)
    if not prior_path.is_absolute():
        prior_path = REPO_ROOT / prior_path
    prior_candidate: dict[str, Any] = json.loads(prior_path.read_text(encoding="utf-8"))

    prompt = build_verb_correction_prompt(prior_candidate)
    prompt_ref = write_prompt_artifact(prompt, run_id, created_at)

    if getattr(args, "dry_run", False):
        return {
            "kind": "routing_pilot_verb_correction_dry_run",
            "run_id": run_id,
            "prompt_ref": prompt_ref,
            "prior_candidate": str(prior_path),
            "packet_mode": route_operator_court.PACKET_MODE,
            "packet_variant": route_operator_court.LEGACY_VERB_CORRECTION_VARIANT,
        }

    model = args.model or model_profile_registry.nvidia_model_id("default_worker", fallback="z-ai/glm-5.1")
    raw_path = _state_path("raw_outputs", run_id, suffix=".jsonl", created_at=created_at)
    started_at = _utc_now()
    try:
        result_text = nvidia_nim.chat_completion(
            prompt,
            config={
                "model": model,
                "max_tokens": int(args.max_tokens),
                "temperature": 0,
                "timeout_s": int(args.max_seconds),
            },
        )
        provider_status = "ok"
        error = None
    except Exception as exc:
        result_text = ""
        provider_status = "provider_error"
        error = f"{type(exc).__name__}: {exc}"

    raw_event = {
        "type": "result",
        "subtype": provider_status,
        "provider": "nvidia_nim",
        "model": model,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "result": result_text,
        "error": error,
    }
    _write_text(raw_path, json.dumps(raw_event, ensure_ascii=False, sort_keys=True) + "\n")
    raw_ref = _rel(raw_path)

    vc_candidate = extract_candidate(raw_ref)
    candidate_path = _state_path("candidates", run_id, created_at=created_at)
    _write_json(candidate_path, vc_candidate or {"parse_error": "candidate_json_not_found"})

    vc_score = _score_verb_correction(vc_candidate)

    score_wrap: dict[str, Any] = {
        "run_id": run_id,
        "provider_status": provider_status,
        "provider_model": model,
        "candidate_ref": _rel(candidate_path),
        "candidate_metadata": {"compression_level": "L4_verb_correction"},
        "metrics": {
            "verb_accuracy_given_pair": vc_score["verb_accuracy_given_pair"],
            "valid_verb_ratio": vc_score["valid_verb_rate"],
            "pair_match_count": vc_score["pair_match_count"],
            "correction_count": vc_score["correction_count"],
        },
        "validity": {"valid_json": bool(vc_candidate)},
        **vc_score,
    }
    score_path = _state_path("scores", run_id, created_at=created_at)
    _write_json(score_path, score_wrap)
    score_ref = _rel(score_path)
    score_wrap["score_ref"] = score_ref

    scoreboard_ref = append_scoreboard_row(
        run_id=run_id,
        backend="nvidia_nim_direct",
        provider_status=provider_status,
        provider_model=model,
        prompt_ref=prompt_ref,
        raw_ref=raw_ref,
        candidate_ref=_rel(candidate_path),
        score_ref=score_ref,
        score=score_wrap,
    )

    return {
        "kind": "routing_pilot_verb_correction_run",
        "run_id": run_id,
        "backend": "nvidia_nim_direct",
        "provider_status": provider_status,
        "provider_model": model,
        "prompt_ref": prompt_ref,
        "raw_output_ref": raw_ref,
        "candidate_ref": _rel(candidate_path),
        "score_ref": score_ref,
        "scoreboard_ref": scoreboard_ref,
        "prior_candidate": str(prior_path),
        **vc_score,
    }


def _build_operator_court_packet(
    prior_candidate: Mapping[str, Any],
    *,
    packet_variant: str,
    include_prior_guess: bool,
) -> dict[str, Any]:
    """Build a Rosetta Operator Court v1 prompt + cases for the given packet variant.

    Reads the manual baseline, scope manifest, and grammar; computes confirmed
    pairs by intersecting the prior run's ``route_edges`` with the baseline's
    ``routing_decisions``; builds deterministic source/target/relation cards;
    and dispatches to ``route_operator_court.build_operator_court_prompt``.
    """

    baseline = _read_json(BASELINE_REL)
    grammar = _read_json(GRAMMAR_REL)
    scope_manifest = _read_json(SCOPE_MANIFEST_REL)

    universe: set[str] = set(_route_universe(baseline, scope_manifest))
    baseline_edges: list[Any] = baseline.get("routing_decisions") or []
    prior_edges: list[Any] = prior_candidate.get("route_edges") or []

    correction_pairs = route_verb_correction.extract_verb_correction_pairs(
        prior_edges, baseline_edges, universe
    )
    confirmed_pairs: list[dict[str, Any]] = []
    for index, edge in enumerate(correction_pairs):
        if not isinstance(edge, Mapping):
            continue
        confirmed_pairs.append(
            {
                "pair_id": str(edge.get("pair_id") or f"oc_{index:03d}"),
                "source": str(edge.get("source") or ""),
                "target": str(edge.get("target") or ""),
                "connector_verb": edge.get("connector_verb"),
                "evidence_set": list(edge.get("evidence_set") or []),
            }
        )

    files = sorted(
        {pair["source"] for pair in confirmed_pairs}
        | {pair["target"] for pair in confirmed_pairs}
    )
    node_cards: list[dict[str, Any]] = []
    relation_cards: list[dict[str, Any]] = []
    if files:
        try:
            node_cards = route_node_card_builder.build_node_cards(REPO_ROOT, files)
        except Exception:
            node_cards = []
        if node_cards:
            try:
                slate = [
                    {"pair_id": pair["pair_id"], "source": pair["source"], "target": pair["target"]}
                    for pair in confirmed_pairs
                ]
                relation_cards = route_candidate_builder.build_candidate_pairs(
                    node_cards, slate_pairs=slate
                )
            except Exception:
                relation_cards = []

    deterministic_cases = route_operator_court.build_deterministic_operator_cases(
        confirmed_pairs,
        node_cards,
        relation_cards,
        grammar,
        include_prior_guess=include_prior_guess,
    )

    cases_for_prompt = (
        deterministic_cases
        if packet_variant
        in {"operator_court_deterministic_cards", "prior_guess_adversarial"}
        else None
    )
    prompt = route_operator_court.build_operator_court_prompt(
        confirmed_pairs,
        grammar=grammar,
        packet_variant=packet_variant,
        include_prior_guess=include_prior_guess,
        deterministic_cases=cases_for_prompt,
    )

    return {
        "prompt": prompt,
        "confirmed_pairs": confirmed_pairs,
        "deterministic_cases": deterministic_cases,
        "node_cards": node_cards,
        "relation_cards": relation_cards,
        "grammar": grammar,
        "baseline": baseline,
    }


def run_operator_court(args: argparse.Namespace) -> dict[str, Any]:
    """Dispatch a Rosetta Operator Court v1 run against a prior candidate.

    Build prompt for the chosen ``--packet-variant`` (one of the five experiment
    variants), optionally short-circuit on ``--dry-run``, dispatch to NVIDIA NIM,
    extract the candidate, score under the operator-court failure ladder, and
    persist prompt / raw / candidate / score / scoreboard artifacts.
    """

    created_at = _utc_now()
    run_id = args.run_id or f"rpoc_{uuid.uuid4().hex[:12]}"
    packet_variant = str(args.packet_variant)
    if packet_variant not in route_operator_court.PACKET_VARIANTS:
        raise SystemExit(
            f"unknown --packet-variant {packet_variant!r}; "
            f"expected one of {route_operator_court.PACKET_VARIANTS}"
        )
    include_prior_guess = bool(getattr(args, "include_prior_guess", False)) or (
        packet_variant == "prior_guess_adversarial"
    )

    prior_path = Path(args.prior_candidate)
    if not prior_path.is_absolute():
        prior_path = REPO_ROOT / prior_path
    prior_candidate: dict[str, Any] = json.loads(prior_path.read_text(encoding="utf-8"))

    packet = _build_operator_court_packet(
        prior_candidate,
        packet_variant=packet_variant,
        include_prior_guess=include_prior_guess,
    )
    prompt = packet["prompt"]
    grammar = packet["grammar"]
    baseline = packet["baseline"]

    leakage = route_operator_court.detect_baseline_leakage(
        prompt,
        baseline,
        deterministic_cases=packet["deterministic_cases"],
        full_node_cards=packet.get("node_cards"),
    )

    metadata: dict[str, Any] = {
        "packet_mode": route_operator_court.PACKET_MODE,
        "packet_variant": packet_variant,
        "include_prior_guess": include_prior_guess,
        "dominance_context": route_operator_court.DOMINANCE_CONTEXT_PRIMARY,
        "case_count": len(packet["deterministic_cases"]),
        "confirmed_pair_count": len(packet["confirmed_pairs"]),
        "leakage_check": leakage,
    }

    prompt_ref = write_prompt_artifact(prompt, run_id, created_at)

    if getattr(args, "dry_run", False):
        return {
            "kind": "operator_court_dry_run",
            "run_id": run_id,
            "prompt_ref": prompt_ref,
            "prior_candidate": str(prior_path),
            **metadata,
        }

    model = args.model or model_profile_registry.nvidia_model_id(
        "default_worker", fallback="z-ai/glm-5.1"
    )
    raw_path = _state_path("raw_outputs", run_id, suffix=".jsonl", created_at=created_at)
    started_at = _utc_now()
    try:
        result_text = nvidia_nim.chat_completion(
            prompt,
            config={
                "model": model,
                "max_tokens": int(args.max_tokens),
                "temperature": 0,
                "timeout_s": int(args.max_seconds),
            },
        )
        provider_status = "ok"
        error = None
    except Exception as exc:
        result_text = ""
        provider_status = "provider_error"
        error = f"{type(exc).__name__}: {exc}"

    raw_event = {
        "type": "result",
        "subtype": provider_status,
        "provider": "nvidia_nim",
        "model": model,
        "started_at": started_at,
        "ended_at": _utc_now(),
        "result": result_text,
        "error": error,
    }
    _write_text(raw_path, json.dumps(raw_event, ensure_ascii=False, sort_keys=True) + "\n")
    raw_ref = _rel(raw_path)

    candidate = extract_candidate(raw_ref)
    candidate_path = _state_path("candidates", run_id, created_at=created_at)
    _write_json(candidate_path, candidate or {"parse_error": "candidate_json_not_found"})

    metrics = route_operator_court.score_operator_court_output(
        candidate,
        baseline.get("routing_decisions") or [],
        grammar,
    )

    score_wrap: dict[str, Any] = {
        "run_id": run_id,
        "provider_status": provider_status,
        "provider_model": model,
        "candidate_ref": _rel(candidate_path),
        "candidate_metadata": {
            "compression_level": "L4_operator_court",
            "packet_variant": packet_variant,
        },
        "metrics": metrics,
        "validity": {"valid_json": bool(candidate)},
        **metadata,
    }
    score_path = _state_path("scores", run_id, created_at=created_at)
    _write_json(score_path, score_wrap)
    score_ref = _rel(score_path)
    score_wrap["score_ref"] = score_ref

    evidence_refs = {
        "prompt_ref": prompt_ref,
        "raw_output_ref": raw_ref,
        "candidate_ref": _rel(candidate_path),
        "score_ref": score_ref,
    }
    appeals = route_operator_court.build_operator_court_appeals(
        candidate,
        baseline.get("routing_decisions") or [],
        grammar,
        run_id=run_id,
        packet_variant=packet_variant,
        provider_model=model,
        evidence_refs=evidence_refs,
    )
    leakage_appeal = route_operator_court.build_leakage_appeal(
        run_id=run_id,
        packet_variant=packet_variant,
        provider_model=model,
        leakage_check=leakage,
        evidence_refs=evidence_refs,
    )
    if leakage_appeal is not None:
        appeals.append(leakage_appeal)
    appeals_ref = _append_operator_court_appeals(appeals)
    score_wrap["appeal_count"] = len(appeals)
    score_wrap["appeals_ref"] = appeals_ref
    _write_json(score_path, score_wrap)

    scoreboard_ref = append_scoreboard_row(
        run_id=run_id,
        backend="nvidia_nim_direct",
        provider_status=provider_status,
        provider_model=model,
        prompt_ref=prompt_ref,
        raw_ref=raw_ref,
        candidate_ref=_rel(candidate_path),
        score_ref=score_ref,
        score=score_wrap,
    )

    return {
        "kind": "operator_court_run",
        "run_id": run_id,
        "backend": "nvidia_nim_direct",
        "provider_status": provider_status,
        "provider_model": model,
        "prompt_ref": prompt_ref,
        "raw_output_ref": raw_ref,
        "candidate_ref": _rel(candidate_path),
        "score_ref": score_ref,
        "scoreboard_ref": scoreboard_ref,
        "prior_candidate": str(prior_path),
        **metadata,
        "appeal_count": len(appeals),
        "appeals_ref": appeals_ref,
        "metrics": metrics,
    }


def _operator_court_variant_label(variant: str) -> str:
    labels = {
        "allowlist_only": "A",
        "definitions_only": "B",
        "definitions_dominance": "C",
        "operator_court_deterministic_cards": "D",
        "prior_guess_adversarial": "E",
    }
    return labels.get(variant, variant[:1].upper() or "X")


def _parse_operator_court_variants(raw: str | None) -> list[str]:
    if not raw:
        return list(route_operator_court.PACKET_VARIANTS)
    aliases = {
        "a": "allowlist_only",
        "b": "definitions_only",
        "c": "definitions_dominance",
        "d": "operator_court_deterministic_cards",
        "e": "prior_guess_adversarial",
    }
    variants: list[str] = []
    for item in re.split(r"[\s,]+", raw.strip()):
        if not item:
            continue
        variant = aliases.get(item.lower(), item)
        if variant not in route_operator_court.PACKET_VARIANTS:
            raise SystemExit(
                f"unknown operator-court matrix variant {item!r}; "
                f"expected A-E or one of {route_operator_court.PACKET_VARIANTS}"
            )
        if variant not in variants:
            variants.append(variant)
    return variants


def _matrix_success_gate(results: list[Mapping[str, Any]]) -> dict[str, Any]:
    d_result = next(
        (
            row for row in results
            if row.get("packet_variant") == route_operator_court.DEFAULT_PACKET_VARIANT
        ),
        None,
    )
    if not d_result or d_result.get("kind") == "operator_court_dry_run":
        return {
            "variant": route_operator_court.DEFAULT_PACKET_VARIANT,
            "evaluated": False,
            "passed": False,
            "reason": "D variant was not run live.",
        }
    metrics = d_result.get("metrics") if isinstance(d_result.get("metrics"), Mapping) else {}
    passed = (
        float(metrics.get("dominant_operator_accuracy") or 0.0) >= 0.8
        and float(metrics.get("valid_verb_rate") or 0.0) == 1.0
        and isinstance(metrics.get("failure_level_counts"), Mapping)
    )
    return {
        "variant": route_operator_court.DEFAULT_PACKET_VARIANT,
        "evaluated": True,
        "passed": passed,
        "dominant_operator_accuracy": metrics.get("dominant_operator_accuracy"),
        "valid_verb_rate": metrics.get("valid_verb_rate"),
        "failure_level_counts": metrics.get("failure_level_counts"),
    }


def run_operator_court_matrix(args: argparse.Namespace) -> dict[str, Any]:
    """Run the A-E operator-court ladder over one prior candidate."""

    created_at = _utc_now()
    matrix_id = args.run_id or f"rpocm_{uuid.uuid4().hex[:12]}"
    variants = _parse_operator_court_variants(args.variants)
    results: list[dict[str, Any]] = []
    leakage_violations: list[dict[str, Any]] = []

    for variant in variants:
        label = _operator_court_variant_label(variant).lower()
        child_args = argparse.Namespace(
            prior_candidate=args.prior_candidate,
            packet_mode=route_operator_court.PACKET_MODE,
            packet_variant=variant,
            include_prior_guess=bool(getattr(args, "include_prior_guess", False)) or variant == "prior_guess_adversarial",
            dry_run=bool(getattr(args, "dry_run", False)),
            model=args.model,
            run_id=f"{matrix_id}_{label}",
            max_seconds=args.max_seconds,
            max_tokens=args.max_tokens,
        )
        result = run_operator_court(child_args)
        results.append(result)
        leakage = result.get("leakage_check") if isinstance(result.get("leakage_check"), Mapping) else {}
        if variant != "prior_guess_adversarial" and (
            leakage.get("leaked_verbs") or leakage.get("leaked_evidence")
        ):
            leakage_violations.append(
                {
                    "packet_variant": variant,
                    "run_id": result.get("run_id"),
                    "leakage_check": leakage,
                }
            )

    receipt = {
        "kind": "operator_court_matrix_run",
        "schema_version": "operator_court_matrix_v1",
        "matrix_id": matrix_id,
        "created_at": created_at,
        "prior_candidate": args.prior_candidate,
        "provider_model": args.model,
        "dry_run": bool(getattr(args, "dry_run", False)),
        "packet_mode": route_operator_court.PACKET_MODE,
        "variants": variants,
        "run_count": len(results),
        "leakage_ok": not leakage_violations,
        "leakage_violations": leakage_violations,
        "variant_d_gate": _matrix_success_gate(results),
        "runs": results,
    }
    receipt_path = _state_path("operator_court_matrices", matrix_id, created_at=created_at)
    _write_json(receipt_path, receipt)
    receipt["receipt_ref"] = _rel(receipt_path)
    _write_json(receipt_path, receipt)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    prompt = sub.add_parser("prompt", help="Print the benchmark prompt")
    prompt.add_argument("--compression-level", default="scope_manifest_rosetta")
    prompt.add_argument("--include-embedding-hints", action="store_true")
    prompt.set_defaults(
        func=lambda args: {
            "prompt": build_prompt(
                args.compression_level,
                include_embedding_hints=args.include_embedding_hints,
            )
        }
    )

    run = sub.add_parser("run", help="Create a job, run it, extract candidate JSON, and score it")
    run.add_argument("--backend", default="claude_code_free", choices=["claude_code_free", "cursor_agent", "nvidia_nim_direct"])
    run.add_argument("--compression-level", default="scope_manifest_rosetta")
    run.add_argument("--max-seconds", type=int, default=240)
    run.add_argument("--max-tokens", type=int, default=4096)
    run.add_argument("--model", default=None)
    run.add_argument("--run-id", default=None)
    run.add_argument("--title", default=None)
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--include-embedding-hints", action="store_true")
    run.set_defaults(func=run_benchmark)

    score = sub.add_parser("score", help="Score an existing raw output JSONL")
    score.add_argument("--raw-output", required=True)
    score.add_argument("--run-id", default=None)
    score.add_argument("--compression-level", default=None)
    score.add_argument("--write", action="store_true")
    score.set_defaults(func=score_raw)

    vc = sub.add_parser(
        "verb-correction",
        help=(
            "Legacy back-compat: dispatch a verb-correction run against a prior "
            "candidate (delegates to operator_court_v1 scoring with the legacy "
            "prompt shape)."
        ),
    )
    vc.add_argument("--prior-candidate", required=True, help="Path to prior candidate JSON (relative to repo root or absolute)")
    vc.add_argument("--model", default=None)
    vc.add_argument("--run-id", default=None)
    vc.add_argument("--max-seconds", type=int, default=120)
    vc.add_argument("--max-tokens", type=int, default=2048)
    vc.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompt and write the prompt artifact, but do not dispatch the provider.",
    )
    vc.set_defaults(func=run_verb_correction)

    oc = sub.add_parser(
        "operator-court",
        help=(
            "Dispatch a Rosetta Operator Court v1 run (verb adjudication via "
            "graph-operator semantics, relation families, and dominance rules)."
        ),
    )
    oc.add_argument("--prior-candidate", required=True, help="Path to prior candidate JSON (relative to repo root or absolute)")
    oc.add_argument(
        "--packet-mode",
        default=route_operator_court.PACKET_MODE,
        choices=[route_operator_court.PACKET_MODE],
        help="Identifies the adjudication packet contract version. Pinned to operator_court_v1 for now.",
    )
    oc.add_argument(
        "--packet-variant",
        default=route_operator_court.DEFAULT_PACKET_VARIANT,
        choices=list(route_operator_court.PACKET_VARIANTS),
        help=(
            "Experiment-ladder variant: allowlist_only (A), definitions_only (B), "
            "definitions_dominance (C), operator_court_deterministic_cards (D), "
            "prior_guess_adversarial (E)."
        ),
    )
    oc.add_argument(
        "--include-prior-guess",
        action="store_true",
        help=(
            "Surface the prior connector_verb under the explicit untrusted field "
            "'previous_model_guess_may_be_wrong'. Implied by --packet-variant=prior_guess_adversarial."
        ),
    )
    oc.add_argument(
        "--dry-run",
        action="store_true",
        help="Build the prompt and write its artifact, but do not dispatch the provider or score.",
    )
    oc.add_argument("--model", default=None)
    oc.add_argument("--run-id", default=None)
    oc.add_argument("--max-seconds", type=int, default=120)
    oc.add_argument("--max-tokens", type=int, default=2048)
    oc.set_defaults(func=run_operator_court)

    ocm = sub.add_parser(
        "operator-court-matrix",
        help="Run the bounded A-E Operator Court packet-variant ladder over one prior candidate.",
    )
    ocm.add_argument("--prior-candidate", required=True, help="Path to prior candidate JSON (relative to repo root or absolute)")
    ocm.add_argument(
        "--variants",
        default=None,
        help="Comma/space list of variants to run. Defaults to A-E. Accepts A,B,C,D,E or packet variant names.",
    )
    ocm.add_argument(
        "--include-prior-guess",
        action="store_true",
        help="Force prior-guess field where supported. The E variant always includes it.",
    )
    ocm.add_argument(
        "--dry-run",
        action="store_true",
        help="Build prompt artifacts for each variant, but do not dispatch providers.",
    )
    ocm.add_argument("--model", default="z-ai/glm4.7")
    ocm.add_argument("--run-id", default=None)
    ocm.add_argument("--max-seconds", type=int, default=120)
    ocm.add_argument("--max-tokens", type=int, default=2048)
    ocm.set_defaults(func=run_operator_court_matrix)

    args = parser.parse_args(argv)
    payload = args.func(args)
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
