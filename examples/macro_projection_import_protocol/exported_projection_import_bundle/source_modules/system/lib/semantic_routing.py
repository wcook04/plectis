"""
[PURPOSE]
- Teleology: Build and serve the Activation Ledger V1 semantic-routing plane on top of the faceted embedding substrate. The route graph is a sparse, derived adjacency surface over embedding rows; append-only route evidence is the only durable authored state and can only reorder existing edges within a capped boost.
- Mechanism: Load `std_semantic_routing.json`, current embedding cache rows, and evidence summary; normalize each facet into a canonical axis family; build bounded row-level adjacency lists; detect incremental invalidation from id/content/schema drift; materialize route graph, status, and drift projections under `state/semantic_routing/`; append/read evidence under `codex/ledger/semantic_routing/route_evidence.jsonl`.

[INTERFACE]
- Exports: refresh_routes, route_drift_snapshot_digest, load_route_graph, load_route_status, load_route_drift, load_route_evidence_summary, query_routes, describe_route_node, confirm_route, append_operation_route_evidence, default_activation_ladder.
- Reads: `codex/standards/std_semantic_routing.json`, `state/embeddings/<kind>.json`, optional current source adapters for staleness checks, and `codex/ledger/semantic_routing/route_evidence.jsonl`.
- Writes: `state/semantic_routing/route_graph.json`, `state/semantic_routing/route_status.json`, `state/semantic_routing/route_drift.json`, `state/semantic_routing/route_evidence_summary.json`, and append-only `codex/ledger/semantic_routing/route_evidence.jsonl`.

[FLOW]
- refresh_routes(): optionally refresh stale embedding kinds -> compute changed ids / impacted neighbors -> rebuild sparse adjacency -> write graph + status + drift.
- query_routes(): find query-relevant seed rows from the embedding substrate -> expand through persisted adjacency when fresh -> fall back to live ladder search only for stale or missing nodes.
- confirm_route(): resolve source/target artifacts to an existing edge -> append evidence -> project updated evidence summary; never mutate the route graph itself.
- append_operation_route_evidence(): ingest operation-emitted route evidence rows into the same append-only ledger without inventing new edges.
- When-needed: Open when wiring kernel route surfaces, refreshing the semantic-routing plane, or debugging why a persisted route/diff surface drifted from embeddings.
- Escalates-to: `system.lib.embedding_substrate`, `system.lib.embedding_sources`, `codex/standards/std_semantic_routing.json`.

[DEPENDENCIES]
- Required:
  - `system.lib.embedding_substrate`
  - `system.lib.embedding_sources`
  - `json`, `hashlib`, `math`, `tempfile`, `time`, `pathlib`, `dataclasses`, `typing`

[CONSTRAINTS]
- Guarantee: route graph, status, and drift artifacts are fully rebuildable from embeddings + standard + evidence; evidence never creates an edge; adjacency remains bounded by the configured per-kind caps.
- Non-goal: This module does not replace embeddings, does not mutate authoritative doctrine/paper/code artifacts, and does not write evidence on read-only route queries.
- Orders: Deterministic ordering everywhere — row keys, artifact tokens, changed-id lists, and adjacency lists sort stably by score then key.

Rosetta routing header (std_navigation_rosetta_grammar.json::noun_shape):
  kind: python_module
  role: activation-ledger / semantic-routing-plane builder; derives a sparse bounded route graph from the embedding cache, tracks incremental drift, and serves append-only route evidence — the rung between raw embedding similarity and Rosetta-grade kind/row navigation.
  depends_on:
    - system/lib/embedding_substrate.py: feeds_when_fresh - the substrate cache is the source of every routable row; route refresh consumes EmbeddingSubstrate.refresh + adjacency.
    - system/lib/embedding_sources.py: feeds - per-source adapters provide the row IDs whose facets become routing nodes.
    - codex/standards/std_semantic_routing.json: governs - the routing standard owns canonical axis-family normalization, per-kind adjacency caps, and evidence schema.
    - codex/doctrine/paper_modules/semantic_routing_plane.md: evidences - paper-module roof for this subsystem.
    - codex/ledger/semantic_routing/route_evidence.jsonl: populates_then_requires_receipt - confirm_route appends evidence rows here; reads do not write; the ledger is the only durable authored state.
    - state/semantic_routing/route_graph.json: populates - this module materializes the derived route graph projection (NOT source authority — content-hash + adjacency rebuild restores it).
  governed_by:
    - codex/standards/std_semantic_routing.json
    - codex/doctrine/paper_modules/semantic_routing_plane.md
  code_loci:
    - refresh_routes: top-level refresh entrypoint; refreshes stale embedding kinds + computes changed ids + impacted neighbors + rebuilds adjacency + writes graph/status/drift.
    - query_routes: lookup-time entrypoint; finds query-relevant seed rows + expands through persisted adjacency when fresh, falls back to live ladder search only on stale/missing nodes.
    - confirm_route: append-only evidence write; resolves source/target to an existing edge before append; never mutates the route graph itself.
    - append_operation_route_evidence: ingest operation-emitted evidence rows into the same append-only ledger.
    - default_activation_ladder: the canonical facet ladder for activation-gradient search.
    - route_drift_snapshot_digest: drift-detection projection; consumers read this to know whether the persisted graph is fresh enough to trust.
  evidence_command: ./repo-python kernel.py --route-graph (graph snapshot); ./repo-python kernel.py --route-query "<query>" (live route lookup with adjacency).
  source_authority: codex/standards/std_semantic_routing.json for axis families and adjacency policy; codex/ledger/semantic_routing/route_evidence.jsonl for confirmed-route history (append-only); embeddings + adapters reconstruct the rest.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import tempfile
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

try:
    import numpy as np
except Exception:  # pragma: no cover - fallback only when numpy is unavailable
    np = None  # type: ignore[assignment]

from system.lib.embedding_sources import SOURCE_ADAPTERS, build_adapter
from system.lib.embedding_substrate import EmbeddingSubstrate

STANDARD_PATH = "codex/standards/std_semantic_routing.json"
STATE_DIR = "state/semantic_routing"
GRAPH_PATH = f"{STATE_DIR}/route_graph.json"
STATUS_PATH = f"{STATE_DIR}/route_status.json"
DRIFT_PATH = f"{STATE_DIR}/route_drift.json"
EVIDENCE_SUMMARY_PATH = f"{STATE_DIR}/route_evidence_summary.json"
EVIDENCE_LEDGER_PATH = "codex/ledger/semantic_routing/route_evidence.jsonl"
_TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")
LARGE_INCREMENTAL_ROW_THRESHOLD = 1000
ROUTE_REFRESH_MIN_FREE_BYTES = int(
    os.environ.get("SEMANTIC_ROUTE_REFRESH_MIN_FREE_BYTES", str(256 * 1024 * 1024))
)
ROUTE_REFRESH_EXISTING_GRAPH_MULTIPLIER = float(
    os.environ.get("SEMANTIC_ROUTE_REFRESH_EXISTING_GRAPH_MULTIPLIER", "5.0")
)


@dataclass(frozen=True)
class RouteRow:
    row_key: str
    artifact_token: str
    source_kind: str
    artifact_id: str
    facet: str
    axis_family: str
    source_path: str
    content_hash: str
    row_fingerprint: str
    vector: tuple[float, ...]
    metadata: dict[str, Any]
    text_preview: str


@dataclass(frozen=True)
class AxisIndex:
    axis_family: str
    rows: tuple[RouteRow, ...]
    index_by_row_key: dict[str, int]
    matrix: Any | None
    source_kinds: tuple[str, ...]


@dataclass(frozen=True)
class FacetIndex:
    source_kind: str
    facet: str
    rows: tuple[RouteRow, ...]
    matrix: Any | None


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            node = json.loads(line)
            if isinstance(node, dict):
                rows.append(node)
    return rows


def _cosine(u: Sequence[float], v: Sequence[float]) -> float:
    if not u or not v or len(u) != len(v):
        return 0.0
    dot = 0.0
    nu = 0.0
    nv = 0.0
    for a, b in zip(u, v):
        dot += a * b
        nu += a * a
        nv += b * b
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return dot / (math.sqrt(nu) * math.sqrt(nv))


def _edge_key(source_row_key: str, target_row_key: str) -> str:
    return f"{source_row_key}||{target_row_key}"


def _row_key(source_kind: str, artifact_id: str, facet: str) -> str:
    return f"{source_kind}:{artifact_id}:{facet}"


def _artifact_token(source_kind: str, artifact_id: str) -> str:
    return f"{source_kind}:{artifact_id}"


def _score_sort_key(item: Mapping[str, Any], score_key: str = "semantic_score") -> tuple[float, str]:
    score = float(item.get(score_key) or 0.0)
    target = str(item.get("target_row_key") or item.get("row_key") or "")
    return (-score, target)


def _stable_digest(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _canonical_drift_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _canonical_drift_value(raw)
            for key, raw in sorted(value.items(), key=lambda item: str(item[0]))
            if str(key) not in {"adjusted_score", "target_source_path"}
        }
    if isinstance(value, list):
        return [_canonical_drift_value(item) for item in value]
    return value


def _canonical_drift_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    keep_keys = {
        "bridge_id",
        "source_row_key",
        "source_kind",
        "source_id",
        "source_facet",
        "target_kind",
        "expected_target_facets",
        "min_score",
        "best_match",
        "drift_reason",
    }
    return {
        key: _canonical_drift_value(entry.get(key))
        for key in sorted(keep_keys)
        if key in entry
    }


def route_drift_snapshot_digest(drift: Mapping[str, Any]) -> str:
    """Digest the drift work set, excluding timestamp and evidence-output churn."""
    raw_drifts = [entry for entry in (drift.get("drifts") or []) if isinstance(entry, Mapping)]
    canonical_drifts = [_canonical_drift_entry(entry) for entry in raw_drifts]
    canonical_drifts.sort(key=lambda entry: json.dumps(entry, sort_keys=True, separators=(",", ":")))
    return _stable_digest(
        {
            "schema_version": drift.get("schema_version"),
            "axis_registry_hash": drift.get("axis_registry_hash"),
            "drift_count": drift.get("drift_count"),
            "drifts": canonical_drifts,
        }
    )


def _changed_sources_preview(changed_sources: Mapping[str, Sequence[str]], *, limit: int = 50) -> dict[str, Any]:
    counts: dict[str, int] = {}
    preview: dict[str, list[str]] = {}
    truncated: dict[str, bool] = {}
    for kind, ids in sorted(changed_sources.items()):
        values = list(ids)
        counts[kind] = len(values)
        preview[kind] = values[:limit]
        truncated[kind] = len(values) > limit
    return {
        "counts": counts,
        "preview_limit": limit,
        "preview": preview,
        "truncated": truncated,
    }


def _graph_fingerprint(nodes: Mapping[str, Any]) -> str:
    material = []
    for key in sorted(nodes.keys()):
        node = nodes[key]
        material.append(
            {
                "row_key": key,
                "same_kind": [
                    (
                        edge["target_row_key"],
                        round(float(edge["semantic_score"]), 6),
                    )
                    for edge in node.get("same_kind_neighbors", [])
                ],
                "cross_kind": {
                    target_kind: [
                        (
                            edge["target_row_key"],
                            round(float(edge["semantic_score"]), 6),
                        )
                        for edge in edges
                    ]
                    for target_kind, edges in sorted(node.get("neighbors_by_target_kind", {}).items())
                },
            }
        )
    return _stable_digest(material)


def _summary_fingerprint(summary: Mapping[str, Any]) -> str:
    if not summary:
        return _sha_text("")
    edges = summary.get("edges", {})
    material = []
    if isinstance(edges, Mapping):
        for key in sorted(edges.keys()):
            node = edges[key]
            material.append(
                (
                    key,
                    node.get("counts", {}),
                    round(float(node.get("boost_fraction") or 0.0), 6),
                    node.get("last_recorded_at"),
                )
            )
    return _stable_digest(material)


def default_activation_ladder(source_kind: str) -> list[str]:
    if source_kind == "python_holographic":
        return ["teleology", "mechanism", "constraints"]
    if source_kind == "paper_modules":
        return ["title", "tldr", "shape"]
    if source_kind == "raw_seed_paragraphs":
        return ["section_heading", "keywords", "mechanisms", "body"]
    if source_kind == "raw_seed_shards":
        return ["clarified", "gestures", "voice_anchor"]
    if source_kind == "raw_seed_navigation":
        return ["title", "gloss", "compression", "graph_context", "lineage"]
    if source_kind == "archaeology_shards":
        return ["clarified", "gestures", "new_dimension"]
    if source_kind == "standards_json":
        return ["title", "schema_intent", "constraints"]
    if source_kind == "annex_notes":
        return ["title", "pattern_intent", "local_translation"]
    if source_kind == "skills":
        return ["title", "summary", "description"]
    return ["title", "statement", "tags"]


def _load_standard(repo_root: Path) -> dict[str, Any]:
    path = repo_root / STANDARD_PATH
    payload = _read_json(path, default={})
    if not isinstance(payload, dict):
        raise RuntimeError(f"invalid semantic routing standard: {path}")
    return payload


def _included_source_kinds(standard: Mapping[str, Any]) -> list[str]:
    items = standard.get("included_source_kinds") or []
    return [str(item) for item in items if str(item)]


def _axis_registry_hash(standard: Mapping[str, Any]) -> str:
    relevant = {
        "axis_families": standard.get("axis_families", []),
        "facet_to_axis_family": standard.get("facet_to_axis_family", {}),
        "expected_bridge_families": standard.get("expected_bridge_families", []),
        "adjacency_limits": standard.get("adjacency_limits", {}),
        "evidence_contract": standard.get("evidence_contract", {}),
    }
    return _stable_digest(relevant)


def _axis_family_for(
    standard: Mapping[str, Any],
    *,
    source_kind: str,
    facet: str,
) -> str | None:
    mappings = standard.get("facet_to_axis_family") or {}
    family = ((mappings.get(source_kind) or {}) if isinstance(mappings, Mapping) else {}).get(facet)
    token = str(family or "").strip()
    return token or None


def _resolve_paths(repo_root: Path) -> dict[str, Path]:
    return {
        "graph": repo_root / GRAPH_PATH,
        "status": repo_root / STATUS_PATH,
        "drift": repo_root / DRIFT_PATH,
        "evidence_summary": repo_root / EVIDENCE_SUMMARY_PATH,
        "evidence_ledger": repo_root / EVIDENCE_LEDGER_PATH,
    }


def _existing_parent(path: Path) -> Path:
    cursor = path
    while not cursor.exists() and cursor != cursor.parent:
        cursor = cursor.parent
    return cursor


def route_refresh_disk_headroom(repo_root: Path) -> dict[str, Any]:
    """Return whether the route projection directory has enough write headroom."""
    repo_root = Path(repo_root)
    paths = _resolve_paths(repo_root)
    graph_path = paths["graph"]
    usage_path = _existing_parent(graph_path.parent)
    usage = shutil.disk_usage(str(usage_path))
    try:
        current_graph_bytes = graph_path.stat().st_size
    except OSError:
        current_graph_bytes = 0
    required_bytes = max(
        ROUTE_REFRESH_MIN_FREE_BYTES,
        int(current_graph_bytes * ROUTE_REFRESH_EXISTING_GRAPH_MULTIPLIER),
    )
    return {
        "ok": int(usage.free) >= required_bytes,
        "free_bytes": int(usage.free),
        "required_bytes": int(required_bytes),
        "current_graph_bytes": int(current_graph_bytes),
        "min_free_bytes": int(ROUTE_REFRESH_MIN_FREE_BYTES),
        "existing_graph_multiplier": ROUTE_REFRESH_EXISTING_GRAPH_MULTIPLIER,
        "usage_path": str(usage_path),
        "graph_path": str(graph_path),
    }


def load_route_graph(repo_root: Path) -> dict[str, Any]:
    return _read_json(_resolve_paths(repo_root)["graph"], default={}) or {}


def load_route_status(repo_root: Path) -> dict[str, Any]:
    return _read_json(_resolve_paths(repo_root)["status"], default={}) or {}


def load_route_drift(repo_root: Path) -> dict[str, Any]:
    return _read_json(_resolve_paths(repo_root)["drift"], default={}) or {}


def load_route_evidence_summary(repo_root: Path) -> dict[str, Any]:
    return _read_json(_resolve_paths(repo_root)["evidence_summary"], default={}) or {}


def current_route_staleness(
    repo_root: Path,
    *,
    source_kinds: Sequence[str] | None = None,
    fast: bool = True,
) -> dict[str, dict[str, Any]]:
    standard = _load_standard(repo_root)
    kinds = [kind for kind in (source_kinds or _included_source_kinds(standard)) if kind in SOURCE_ADAPTERS]
    substrate = EmbeddingSubstrate(repo_root)
    staleness: dict[str, dict[str, Any]] = {}
    for source_kind in kinds:
        adapter = build_adapter(source_kind, repo_root)
        status = substrate.status(adapter, fast=fast)
        stale = status.record_count == 0 or status.stale_or_missing > 0
        reason_counts = dict(getattr(status, "stale_reason_counts", {}) or {})
        expected_row_count = getattr(status, "expected_row_count", None)
        total_rows = expected_row_count if expected_row_count is not None else status.record_count
        source_status = {
            "stale": stale,
            "status": "stale" if stale else "fresh",
            "record_count": status.record_count,
            "total_rows": total_rows,
            "missing_rows": int(reason_counts.get("missing") or 0),
            "removed_rows": int(reason_counts.get("removed") or 0),
            "hash_changed_rows": int(reason_counts.get("hash_changed") or 0),
            "schema_changed_rows": int(reason_counts.get("schema_changed") or 0),
            "stale_or_missing": status.stale_or_missing,
            "path": status.path,
            "schema_hash": status.schema_hash,
            "last_refresh_at": getattr(status, "last_refresh_at", None),
            "stale_reason_counts": reason_counts,
        }
        stale_preview = getattr(status, "stale_preview", None)
        if stale_preview:
            source_status["stale_preview"] = list(stale_preview)
        if bool(getattr(status, "stale_preview_truncated", False)):
            source_status["stale_preview_truncated"] = True
        if bool(getattr(status, "stale_or_missing_is_estimate", False)):
            source_status["stale_or_missing_is_estimate"] = True
        staleness[source_kind] = source_status
    return staleness


def _build_route_status_payload(
    *,
    axis_registry_hash: str,
    route_graph_fingerprint: str,
    evidence_summary_fingerprint: str,
    refresh_mode: str,
    source: str,
    refreshed_row_count: int,
    impacted_row_count: int,
    changed_sources: Mapping[str, Sequence[str]],
    embedding_refresh: Mapping[str, Any],
    post_refresh_staleness: Mapping[str, Mapping[str, Any]],
    source_state: Mapping[str, Mapping[str, Any]],
    included_kinds: Sequence[str],
    statistics: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "kind": "semantic_route_status",
        "schema_version": "semantic_route_status_v1",
        "generated_at": _now_iso(),
        "axis_registry_hash": axis_registry_hash,
        "route_graph_fingerprint": route_graph_fingerprint,
        "evidence_summary_fingerprint": evidence_summary_fingerprint,
        "refresh_mode": refresh_mode,
        "requested_source": source,
        "refresh_ledger_path": "state/embeddings/refresh_ledger.jsonl",
        "pending_refresh_path": "state/embeddings/pending_refresh.jsonl",
        "refreshed_row_count": refreshed_row_count,
        "impacted_row_count": impacted_row_count,
        "changed_sources": {
            str(source_kind): list(ids)
            for source_kind, ids in changed_sources.items()
        },
        "embedding_refresh": dict(embedding_refresh),
        "stale_sources": [
            source_kind
            for source_kind, info in post_refresh_staleness.items()
            if bool(info.get("stale"))
        ],
        "embedding_staleness": dict(post_refresh_staleness),
        "source_kinds": {
            kind: dict(source_state.get(kind, {}))
            for kind in included_kinds
        },
        "statistics": dict(statistics),
    }


def _tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN_RE.finditer(str(text or "")) if len(match.group(0)) > 1]


def _preview_text(text: str, *, limit: int = 400) -> str:
    compact = " ".join(str(text or "").split())
    if len(compact) <= limit:
        return compact
    return compact[: max(0, limit - 3)].rstrip() + "..."


def _bm25_lite_score(
    *,
    query_tokens: Sequence[str],
    doc_tokens: Sequence[str],
    doc_freq: Mapping[str, int],
    total_docs: int,
    avg_doc_len: float,
    k1: float = 1.2,
    b: float = 0.75,
) -> float:
    if not query_tokens or not doc_tokens or total_docs <= 0:
        return 0.0
    term_freq = Counter(doc_tokens)
    doc_len = float(len(doc_tokens) or 1)
    score = 0.0
    for token in dict.fromkeys(query_tokens):
        freq = term_freq.get(token, 0)
        if freq <= 0:
            continue
        df = max(1, int(doc_freq.get(token, 0)))
        idf = math.log(1.0 + ((total_docs - df + 0.5) / (df + 0.5)))
        denom = freq + k1 * (1.0 - b + b * (doc_len / max(avg_doc_len, 1.0)))
        score += idf * ((freq * (k1 + 1.0)) / max(denom, 1e-9))
    return score


def _lexical_fallback_hits(
    repo_root: Path,
    *,
    query: str,
    source_kinds: Sequence[str],
    top_k: int,
) -> list[dict[str, Any]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []

    documents: list[dict[str, Any]] = []
    doc_freq: Counter[str] = Counter()

    for source_kind in source_kinds:
        if source_kind not in SOURCE_ADAPTERS:
            continue
        if source_kind == "raw_seed_paragraphs":
            documents.extend(_raw_seed_paragraph_index_hits(repo_root, query=query, top_k=top_k))
            continue
        ladder = default_activation_ladder(source_kind)
        facet_rank = {facet: index for index, facet in enumerate(ladder)}
        try:
            adapter = build_adapter(source_kind, repo_root)
        except Exception:
            continue
        for item in adapter.iter_items():
            metadata_text = json.dumps(item.metadata, ensure_ascii=False, sort_keys=True)
            metadata_tokens = set(_tokenize(f"{item.source_path} {metadata_text}"))
            for facet, text in item.non_empty_facets().items():
                doc_tokens = _tokenize(text)
                if not doc_tokens:
                    continue
                documents.append(
                    {
                        "id": item.id,
                        "facet": facet,
                        "source_kind": source_kind,
                        "source_path": item.source_path,
                        "preview": _preview_text(text),
                        "tokens": doc_tokens,
                        "metadata_tokens": metadata_tokens,
                        "facet_rank": facet_rank.get(facet, len(ladder)),
                    }
                )
                doc_freq.update(set(doc_tokens))

    if not documents:
        return []

    # pattern: field-weighted lexical retrieval, inspired by understand-anything:p003.
    indexed_hits = [doc for doc in documents if "score" in doc and "match_backend" in doc]
    docs_for_bm25 = [doc for doc in documents if "tokens" in doc]
    ranked: list[dict[str, Any]] = list(indexed_hits)
    if not docs_for_bm25:
        ranked.sort(key=lambda item: (-float(item["score"]), str(item["source_kind"]), str(item["id"]), str(item["facet"])))
        return ranked[:top_k]

    avg_doc_len = sum(len(doc["tokens"]) for doc in docs_for_bm25) / float(len(docs_for_bm25))
    query_token_set = set(query_tokens)
    for doc in docs_for_bm25:
        score = _bm25_lite_score(
            query_tokens=query_tokens,
            doc_tokens=doc["tokens"],
            doc_freq=doc_freq,
            total_docs=len(docs_for_bm25),
            avg_doc_len=avg_doc_len,
        )
        if score <= 0.0:
            continue
        metadata_overlap = len(query_token_set & set(doc["metadata_tokens"]))
        if metadata_overlap:
            score += 0.12 * metadata_overlap
        rung_weight = max(0.55, 1.0 - (0.08 * float(doc["facet_rank"])))
        score *= rung_weight
        ranked.append(
            {
                "id": doc["id"],
                "facet": doc["facet"],
                "source_kind": doc["source_kind"],
                "source_path": doc["source_path"],
                "score": round(float(score), 6),
                "preview": doc["preview"],
                "match_backend": "lexical_bm25_lite",
            }
        )

    ranked.sort(key=lambda item: (-float(item["score"]), str(item["source_kind"]), str(item["id"]), str(item["facet"])))
    return ranked[:top_k]


def _raw_seed_paragraph_index_hits(
    repo_root: Path,
    *,
    query: str,
    top_k: int,
) -> list[dict[str, Any]]:
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    obsidian_root = repo_root / "obsidian"
    if not obsidian_root.exists():
        return []

    weights = {
        "section_heading": 4,
        "keywords": 4,
        "mechanisms": 4,
        "body": 1,
    }
    rows: list[dict[str, Any]] = []
    for marker in sorted(obsidian_root.rglob("phase_family.json")):
        family_payload = _read_json(marker, default={}) or {}
        if not isinstance(family_payload, Mapping):
            continue
        raw_seed_json_rel = str(family_payload.get("raw_seed_json_path") or "").strip()
        if not raw_seed_json_rel:
            continue
        raw_seed_payload = _read_json(repo_root / raw_seed_json_rel, default={}) or {}
        if not isinstance(raw_seed_payload, Mapping):
            continue
        raw_seed_path = str(
            raw_seed_payload.get("raw_seed_path")
            or family_payload.get("raw_seed_path")
            or raw_seed_json_rel
        ).strip()
        family_number = str(raw_seed_payload.get("family_number") or family_payload.get("family_number") or "").strip()
        sections_by_id = {
            str(section.get("id") or "").strip(): dict(section)
            for section in (raw_seed_payload.get("sections") or [])
            if isinstance(section, Mapping) and str(section.get("id") or "").strip()
        }
        for paragraph in (raw_seed_payload.get("paragraphs") or []):
            if not isinstance(paragraph, Mapping):
                continue
            paragraph_id = str(paragraph.get("id") or "").strip()
            if not paragraph_id:
                continue
            section = sections_by_id.get(str(paragraph.get("section_id") or "").strip()) or {}
            field_texts = {
                "section_heading": str(section.get("heading") or "").strip(),
                "keywords": " | ".join(str(item).strip() for item in (paragraph.get("keyword_hints") or []) if str(item).strip()),
                "mechanisms": " | ".join(str(item).strip() for item in (paragraph.get("mechanism_hints") or []) if str(item).strip()),
                "body": str(paragraph.get("plain_text") or "").strip(),
            }
            matched_terms: set[str] = set()
            matched_fields: set[str] = set()
            score = 0.0
            for token in query_tokens:
                for field_name, text in field_texts.items():
                    if token and token in text.casefold():
                        score += float(weights[field_name])
                        matched_terms.add(token)
                        matched_fields.add(field_name)
            if score <= 0.0:
                continue
            facet = sorted(
                matched_fields,
                key=lambda field_name: (-weights[field_name], field_name),
            )[0]
            preview_source = field_texts.get(facet) or field_texts["body"]
            rows.append(
                {
                    "id": paragraph_id,
                    "facet": facet,
                    "source_kind": "raw_seed_paragraphs",
                    "source_path": raw_seed_path,
                    "score": round(score, 6),
                    "preview": _preview_text(preview_source),
                    "match_backend": "raw_seed_index_lexical",
                    "family_number": family_number or None,
                    "matched_terms": sorted(matched_terms),
                    "matched_fields": sorted(matched_fields),
                }
            )

    rows.sort(key=lambda item: (-float(item["score"]), str(item.get("family_number") or ""), str(item["id"]), str(item["facet"])))
    return rows[:top_k]


def _embedding_fallback_hits(
    substrate: EmbeddingSubstrate,
    *,
    query: str,
    source_kinds: Sequence[str],
    top_k: int,
) -> list[dict[str, Any]]:
    if not source_kinds:
        return []
    hits: list[dict[str, Any]] = []
    for hit in substrate.search(query, source_kinds=list(source_kinds), top_k=top_k):
        hits.append(
            {
                "id": hit.record.id,
                "facet": hit.record.facet,
                "source_kind": hit.record.source_kind,
                "source_path": hit.record.source_path,
                "score": round(float(hit.score), 6),
                "preview": hit.record.text_preview,
                "match_backend": "embedding",
            }
        )
    return hits


def _build_rows(
    repo_root: Path,
    standard: Mapping[str, Any],
    *,
    source_kinds: Sequence[str],
) -> tuple[dict[str, RouteRow], dict[str, dict[str, Any]]]:
    rows: dict[str, RouteRow] = {}
    source_state: dict[str, dict[str, Any]] = {}
    substrate = EmbeddingSubstrate(repo_root)

    for source_kind in source_kinds:
        path = repo_root / "state" / "embeddings" / f"{source_kind}.json"
        data = substrate.load(source_kind)
        if not isinstance(data, dict):
            continue

        records = data.get("records") or []
        distinct_ids = {str(record.get("id") or "") for record in records if str(record.get("id") or "")}
        distinct_facets = {str(record.get("facet") or "body") for record in records}
        id_hash_material: dict[str, list[str]] = {}
        rows_for_kind = 0

        for raw in records:
            artifact_id = str(raw.get("id") or "").strip()
            facet = str(raw.get("facet") or "body").strip()
            if not artifact_id or not facet:
                continue
            axis_family = _axis_family_for(standard, source_kind=source_kind, facet=facet)
            if not axis_family:
                continue
            vector_raw = raw.get("vector") or []
            if not isinstance(vector_raw, list) or not vector_raw:
                continue
            source_path = str(raw.get("source_path") or "").strip()
            content_hash = str(raw.get("content_hash") or "").strip()
            row_fingerprint = _sha_text(
                json.dumps(
                    {
                        "source_kind": source_kind,
                        "id": artifact_id,
                        "facet": facet,
                        "axis_family": axis_family,
                        "content_hash": content_hash,
                    },
                    sort_keys=True,
                )
            )
            token = _artifact_token(source_kind, artifact_id)
            key = _row_key(source_kind, artifact_id, facet)
            metadata = dict(raw.get("metadata") or {})
            row = RouteRow(
                row_key=key,
                artifact_token=token,
                source_kind=source_kind,
                artifact_id=artifact_id,
                facet=facet,
                axis_family=axis_family,
                source_path=source_path,
                content_hash=content_hash,
                row_fingerprint=row_fingerprint,
                vector=tuple(float(v) for v in vector_raw),
                metadata=metadata,
                text_preview=str(raw.get("text_preview") or ""),
            )
            rows[key] = row
            id_hash_material.setdefault(artifact_id, []).append(f"{facet}:{content_hash}")
            rows_for_kind += 1

        id_fingerprints = {
            artifact_id: _sha_text("|".join(sorted(parts)))
            for artifact_id, parts in sorted(id_hash_material.items())
        }
        source_state[source_kind] = {
            "embedding_path": str(path.relative_to(repo_root)),
            "record_count": rows_for_kind,
            "distinct_ids": len(distinct_ids),
            "facet_count": len(distinct_facets),
            "model": data.get("model"),
            "dims": data.get("dims"),
            "embedding_schema_hash": data.get("schema_hash"),
            "last_refresh_at": data.get("last_refresh_at"),
            "id_fingerprints": id_fingerprints,
            "source_fingerprint": _stable_digest(
                {
                    "model": data.get("model"),
                    "dims": data.get("dims"),
                    "embedding_schema_hash": data.get("schema_hash"),
                    "ids": id_fingerprints,
                }
            ),
        }
    return rows, source_state


def _build_artifact_index(rows: Mapping[str, RouteRow]) -> dict[str, dict[str, Any]]:
    artifacts: dict[str, dict[str, Any]] = {}
    by_plain_id: dict[str, set[str]] = {}
    for row in rows.values():
        token = row.artifact_token
        entry = artifacts.setdefault(
            token,
            {
                "artifact_token": token,
                "source_kind": row.source_kind,
                "artifact_id": row.artifact_id,
                "source_path": row.source_path,
                "row_keys": [],
                "facets": [],
            },
        )
        entry["row_keys"].append(row.row_key)
        entry["facets"].append(row.facet)
        by_plain_id.setdefault(row.artifact_id, set()).add(token)
    for entry in artifacts.values():
        entry["row_keys"] = sorted(set(entry["row_keys"]))
        entry["facets"] = sorted(set(entry["facets"]))
    return {
        "artifacts": {key: artifacts[key] for key in sorted(artifacts.keys())},
        "by_plain_id": {key: sorted(value) for key, value in sorted(by_plain_id.items())},
    }


def _current_adapter_schema_hash(repo_root: Path, source_kind: str) -> str | None:
    if source_kind not in SOURCE_ADAPTERS:
        return None
    adapter = build_adapter(source_kind, repo_root)
    return adapter.schema_hash()


def _ensure_embeddings_current(
    repo_root: Path,
    *,
    source_kinds: Sequence[str],
    auto_refresh: bool,
    progress: Callable[[str], None] | None,
) -> dict[str, Any]:
    substrate = EmbeddingSubstrate(repo_root)
    refreshed: dict[str, Any] = {}
    for source_kind in source_kinds:
        if source_kind not in SOURCE_ADAPTERS:
            continue
        adapter = build_adapter(source_kind, repo_root)
        status = substrate.status(adapter)
        needs_refresh = status.record_count == 0 or status.stale_or_missing > 0
        if not needs_refresh:
            continue
        if not auto_refresh:
            refreshed[source_kind] = {
                "refreshed": False,
                "reason": "stale_or_missing_embeddings",
                "stale_or_missing": status.stale_or_missing,
            }
            continue
        if progress:
            progress(f"refreshing embeddings for {source_kind}")
        report = substrate.refresh(adapter, progress=progress)
        refreshed[source_kind] = {
            "refreshed": True,
            "report": report,
        }
    return refreshed


def _candidate_groups(rows: Mapping[str, RouteRow]) -> dict[tuple[str, str], list[RouteRow]]:
    groups: dict[tuple[str, str], list[RouteRow]] = {}
    for row in rows.values():
        groups.setdefault((row.axis_family, row.source_kind), []).append(row)
    for key in groups:
        groups[key] = sorted(groups[key], key=lambda item: item.row_key)
    return groups


def _candidate_by_axis(rows: Mapping[str, RouteRow]) -> dict[str, list[RouteRow]]:
    groups: dict[str, list[RouteRow]] = {}
    for row in rows.values():
        groups.setdefault(row.axis_family, []).append(row)
    for key in groups:
        groups[key] = sorted(groups[key], key=lambda item: item.row_key)
    return groups


def _normalized_matrix(rows: Sequence[RouteRow]) -> Any | None:
    if np is None or not rows:
        return None
    matrix = np.asarray([row.vector for row in rows], dtype=np.float32)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0.0, 1.0, norms)
    normalized = matrix / norms
    return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0)


def _build_axis_indexes(rows: Mapping[str, RouteRow]) -> dict[str, AxisIndex]:
    by_axis = _candidate_by_axis(rows)
    indexes: dict[str, AxisIndex] = {}
    for axis_family, axis_rows in sorted(by_axis.items()):
        ordered_rows = tuple(axis_rows)
        indexes[axis_family] = AxisIndex(
            axis_family=axis_family,
            rows=ordered_rows,
            index_by_row_key={row.row_key: idx for idx, row in enumerate(ordered_rows)},
            matrix=_normalized_matrix(ordered_rows),
            source_kinds=tuple(sorted({row.source_kind for row in ordered_rows})),
        )
    return indexes


def _build_facet_indexes(rows: Mapping[str, RouteRow]) -> dict[tuple[str, str], FacetIndex]:
    grouped: dict[tuple[str, str], list[RouteRow]] = {}
    for row in rows.values():
        grouped.setdefault((row.source_kind, row.facet), []).append(row)
    indexes: dict[tuple[str, str], FacetIndex] = {}
    for key, facet_rows in sorted(grouped.items()):
        ordered_rows = tuple(sorted(facet_rows, key=lambda item: item.row_key))
        indexes[key] = FacetIndex(
            source_kind=key[0],
            facet=key[1],
            rows=ordered_rows,
            matrix=_normalized_matrix(ordered_rows),
        )
    return indexes


def _normalized_row_vector(row: RouteRow, axis_indexes: Mapping[str, AxisIndex]) -> Any | None:
    axis_index = axis_indexes.get(row.axis_family)
    if axis_index is None or axis_index.matrix is None:
        return None
    row_idx = axis_index.index_by_row_key.get(row.row_key)
    if row_idx is None:
        return None
    return axis_index.matrix[row_idx]


def _select_top_edges(
    source: RouteRow,
    *,
    axis_indexes: Mapping[str, AxisIndex],
    limits: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    same_kind_limit = int((limits.get("same_kind") or 3))
    cross_kind_limit = int((limits.get("cross_kind_per_target") or 5))

    same_kind: list[dict[str, Any]] = []
    cross_kind: dict[str, list[dict[str, Any]]] = {}

    axis_index = axis_indexes.get(source.axis_family)
    if axis_index is None:
        return same_kind, cross_kind
    cross_target_kinds = [kind for kind in axis_index.source_kinds if kind != source.source_kind]

    def _buckets_full() -> bool:
        same_full = same_kind_limit <= 0 or len(same_kind) >= same_kind_limit
        cross_full = cross_kind_limit <= 0 or all(
            len(cross_kind.get(kind) or []) >= cross_kind_limit
            for kind in cross_target_kinds
        )
        return same_full and cross_full

    if axis_index.matrix is not None and np is not None:
        source_idx = axis_index.index_by_row_key.get(source.row_key)
        if source_idx is not None:
            with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
                scores = axis_index.matrix @ axis_index.matrix[source_idx]
            scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
            order = np.argsort(-scores, kind="stable")
            for candidate_idx in order.tolist():
                candidate = axis_index.rows[candidate_idx]
                if candidate.row_key == source.row_key:
                    continue
                if candidate.artifact_token == source.artifact_token:
                    continue
                if candidate.source_kind == source.source_kind:
                    if len(same_kind) >= same_kind_limit:
                        continue
                    target_bucket = same_kind
                else:
                    bucket = cross_kind.setdefault(candidate.source_kind, [])
                    if len(bucket) >= cross_kind_limit:
                        continue
                    target_bucket = bucket
                target_bucket.append(
                    {
                        "target_row_key": candidate.row_key,
                        "target_kind": candidate.source_kind,
                        "target_id": candidate.artifact_id,
                        "target_facet": candidate.facet,
                        "target_axis_family": candidate.axis_family,
                        "target_source_path": candidate.source_path,
                        "semantic_score": round(float(scores[candidate_idx]), 6),
                    }
                )
                if _buckets_full():
                    break
            same_kind.sort(key=_score_sort_key)
            pruned_cross_kind = {
                target_kind: sorted(edges, key=_score_sort_key)
                for target_kind, edges in sorted(cross_kind.items())
            }
            return same_kind, pruned_cross_kind

    for candidate in axis_index.rows:
        if candidate.row_key == source.row_key:
            continue
        if candidate.artifact_token == source.artifact_token:
            continue
        if candidate.source_kind == source.source_kind:
            if len(same_kind) >= same_kind_limit:
                continue
            target_bucket = same_kind
        else:
            bucket = cross_kind.setdefault(candidate.source_kind, [])
            if len(bucket) >= cross_kind_limit:
                continue
            target_bucket = bucket
        target_bucket.append(
            {
                "target_row_key": candidate.row_key,
                "target_kind": candidate.source_kind,
                "target_id": candidate.artifact_id,
                "target_facet": candidate.facet,
                "target_axis_family": candidate.axis_family,
                "target_source_path": candidate.source_path,
                "semantic_score": round(_cosine(source.vector, candidate.vector), 6),
            }
        )
        if _buckets_full():
            break

    same_kind.sort(key=_score_sort_key)
    same_kind = same_kind[:same_kind_limit]

    pruned_cross_kind: dict[str, list[dict[str, Any]]] = {}
    for target_kind, edges in sorted(cross_kind.items()):
        edges.sort(key=_score_sort_key)
        pruned_cross_kind[target_kind] = edges[:cross_kind_limit]
    return same_kind, pruned_cross_kind


def _build_node_payload(
    row: RouteRow,
    *,
    axis_indexes: Mapping[str, AxisIndex],
    limits: Mapping[str, Any],
) -> dict[str, Any]:
    same_kind, cross_kind = _select_top_edges(row, axis_indexes=axis_indexes, limits=limits)
    return {
        "row_key": row.row_key,
        "artifact_token": row.artifact_token,
        "source_kind": row.source_kind,
        "artifact_id": row.artifact_id,
        "facet": row.facet,
        "axis_family": row.axis_family,
        "source_path": row.source_path,
        "content_hash": row.content_hash,
        "row_fingerprint": row.row_fingerprint,
        "title": row.metadata.get("title"),
        "same_kind_neighbors": same_kind,
        "neighbors_by_target_kind": cross_kind,
    }


def _neighbor_thresholds(node: Mapping[str, Any]) -> tuple[float, dict[str, float]]:
    same = node.get("same_kind_neighbors") or []
    same_threshold = 0.0
    if same:
        same_threshold = min(float(edge.get("semantic_score") or 0.0) for edge in same)
    cross: dict[str, float] = {}
    for target_kind, edges in (node.get("neighbors_by_target_kind") or {}).items():
        if not edges:
            continue
        cross[str(target_kind)] = min(float(edge.get("semantic_score") or 0.0) for edge in edges)
    return same_threshold, cross


def _compute_impacted_row_keys(
    *,
    current_rows: Mapping[str, RouteRow],
    previous_graph_nodes: Mapping[str, Any],
    changed_row_keys: set[str],
) -> set[str]:
    if not changed_row_keys or not previous_graph_nodes:
        return set()

    impacted: set[str] = set()
    rows_by_axis = _candidate_by_axis(current_rows)

    for changed_key in sorted(changed_row_keys):
        changed_row = current_rows.get(changed_key)
        if changed_row is None:
            for node_key, node in previous_graph_nodes.items():
                same = node.get("same_kind_neighbors") or []
                cross = node.get("neighbors_by_target_kind") or {}
                if any(edge.get("target_row_key") == changed_key for edge in same):
                    impacted.add(node_key)
                    continue
                for edges in cross.values():
                    if any(edge.get("target_row_key") == changed_key for edge in edges):
                        impacted.add(node_key)
                        break
            continue

        candidates = rows_by_axis.get(changed_row.axis_family, [])
        for candidate in candidates:
            if candidate.row_key == changed_key:
                continue
            prev_node = previous_graph_nodes.get(candidate.row_key) or {}
            same_threshold, cross_thresholds = _neighbor_thresholds(prev_node)
            score = _cosine(changed_row.vector, candidate.vector)
            if candidate.source_kind == changed_row.source_kind:
                if score >= same_threshold or any(
                    edge.get("target_row_key") == changed_key
                    for edge in (prev_node.get("same_kind_neighbors") or [])
                ):
                    impacted.add(candidate.row_key)
            else:
                prev_edges = (prev_node.get("neighbors_by_target_kind") or {}).get(changed_row.source_kind) or []
                threshold = cross_thresholds.get(changed_row.source_kind, 0.0)
                if score >= threshold or any(edge.get("target_row_key") == changed_key for edge in prev_edges):
                    impacted.add(candidate.row_key)
    return impacted


def _bridge_score(
    source: RouteRow,
    target: RouteRow,
    *,
    evidence_summary: Mapping[str, Any],
) -> tuple[float, float]:
    semantic = round(_cosine(source.vector, target.vector), 6)
    summary = ((evidence_summary.get("edges") or {}) if isinstance(evidence_summary, Mapping) else {}).get(
        _edge_key(source.row_key, target.row_key)
    ) or {}
    boost = float(summary.get("boost_fraction") or 0.0)
    adjusted = round(semantic * (1.0 + boost), 6)
    return semantic, adjusted


def _build_drift_report(
    *,
    standard: Mapping[str, Any],
    rows: Mapping[str, RouteRow],
    evidence_summary: Mapping[str, Any],
    axis_registry_hash: str,
) -> dict[str, Any]:
    drifts: list[dict[str, Any]] = []
    bridge_families = standard.get("expected_bridge_families") or []
    rows_by_kind_and_facet: dict[tuple[str, str], list[RouteRow]] = {}
    axis_indexes = _build_axis_indexes(rows)
    facet_indexes = _build_facet_indexes(rows)
    for row in rows.values():
        rows_by_kind_and_facet.setdefault((row.source_kind, row.facet), []).append(row)

    for bridge in bridge_families:
        source_def = bridge.get("source") or {}
        source_kind = str(source_def.get("source_kind") or "").strip()
        source_facets = [str(item) for item in (source_def.get("source_facets") or []) if str(item)]
        bridge_id = str(bridge.get("bridge_id") or "").strip() or "bridge"
        targets = bridge.get("targets") or []
        for source_facet in source_facets:
            for source_row in rows_by_kind_and_facet.get((source_kind, source_facet), []):
                source_vector = _normalized_row_vector(source_row, axis_indexes)
                for target_def in targets:
                    target_kind = str(target_def.get("target_kind") or "").strip()
                    target_facets = [str(item) for item in (target_def.get("target_facets") or []) if str(item)]
                    min_score = float(target_def.get("min_score") or 0.0)
                    best_match: dict[str, Any] | None = None
                    for target_facet in target_facets:
                        target_index = facet_indexes.get((target_kind, target_facet))
                        if target_index is None:
                            continue
                        if target_index.matrix is not None and source_vector is not None and np is not None:
                            with np.errstate(invalid="ignore", over="ignore", divide="ignore"):
                                semantic_scores = target_index.matrix @ source_vector
                            semantic_scores = np.nan_to_num(
                                semantic_scores, nan=0.0, posinf=0.0, neginf=0.0
                            )
                            boosts = np.asarray(
                                [
                                    float(
                                        (
                                            (evidence_summary.get("edges") or {})
                                            .get(_edge_key(source_row.row_key, target_row.row_key), {})
                                            .get("boost_fraction")
                                        )
                                        or 0.0
                                    )
                                    for target_row in target_index.rows
                                ],
                                dtype=np.float32,
                            )
                            adjusted_scores = semantic_scores * (1.0 + boosts)
                            best_idx = int(np.argmax(adjusted_scores))
                            target_row = target_index.rows[best_idx]
                            semantic = round(float(semantic_scores[best_idx]), 6)
                            adjusted = round(float(adjusted_scores[best_idx]), 6)
                            candidate = {
                                "target_row_key": target_row.row_key,
                                "target_kind": target_row.source_kind,
                                "target_id": target_row.artifact_id,
                                "target_facet": target_row.facet,
                                "target_source_path": target_row.source_path,
                                "semantic_score": semantic,
                                "adjusted_score": adjusted,
                            }
                            if best_match is None or adjusted > float(best_match.get("adjusted_score") or 0.0):
                                best_match = candidate
                            continue

                        for target_row in target_index.rows:
                            semantic, adjusted = _bridge_score(
                                source_row,
                                target_row,
                                evidence_summary=evidence_summary,
                            )
                            candidate = {
                                "target_row_key": target_row.row_key,
                                "target_kind": target_row.source_kind,
                                "target_id": target_row.artifact_id,
                                "target_facet": target_row.facet,
                                "target_source_path": target_row.source_path,
                                "semantic_score": semantic,
                                "adjusted_score": adjusted,
                            }
                            if best_match is None or adjusted > float(best_match.get("adjusted_score") or 0.0):
                                best_match = candidate
                    if best_match is None or float(best_match.get("adjusted_score") or 0.0) < min_score:
                        drifts.append(
                            {
                                "bridge_id": bridge_id,
                                "source_row_key": source_row.row_key,
                                "source_kind": source_row.source_kind,
                                "source_id": source_row.artifact_id,
                                "source_facet": source_row.facet,
                                "target_kind": target_kind,
                                "expected_target_facets": target_facets,
                                "min_score": min_score,
                                "best_match": best_match,
                                "drift_reason": "missing_target" if best_match is None else "below_threshold",
                            }
                        )
    drifts.sort(
        key=lambda item: (
            item["bridge_id"],
            item["source_row_key"],
            item["target_kind"],
        )
    )
    return {
        "kind": "semantic_route_drift",
        "schema_version": "semantic_route_drift_v1",
        "generated_at": _now_iso(),
        "axis_registry_hash": axis_registry_hash,
        "evidence_summary_fingerprint": _summary_fingerprint(evidence_summary),
        "drift_count": len(drifts),
        "drifts": drifts,
    }


def refresh_routes(
    repo_root: Path,
    *,
    source: str = "all",
    force: bool = False,
    auto_refresh_embeddings: bool = True,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    standard = _load_standard(repo_root)
    included_kinds = _included_source_kinds(standard)
    if source != "all" and source not in included_kinds:
        raise ValueError(f"unknown semantic routing source kind: {source}")

    paths = _resolve_paths(repo_root)
    disk_headroom = route_refresh_disk_headroom(repo_root)
    if not bool(disk_headroom.get("ok")):
        if progress:
            progress(
                "route refresh skipped: low disk headroom "
                f"free={disk_headroom.get('free_bytes')} required={disk_headroom.get('required_bytes')}"
            )
        return {
            "kind": "kernel.route_refresh",
            "status": "skipped_low_disk_headroom",
            "source": source,
            "refresh_mode": "skipped",
            "graph_path": str(paths["graph"].relative_to(repo_root)),
            "status_path": str(paths["status"].relative_to(repo_root)),
            "drift_path": str(paths["drift"].relative_to(repo_root)),
            "evidence_summary_path": str(paths["evidence_summary"].relative_to(repo_root)),
            "route_drift_digest": None,
            "stable_signal_digest": None,
            "disk_headroom": disk_headroom,
            "changed_sources": {},
            "changed_sources_summary": _changed_sources_preview({}),
            "embedding_refresh": {},
            "post_refresh_staleness": {},
            "result_summary": {
                "refreshed_rows": 0,
                "changed_source_count": 0,
                "node_count": 0,
                "edge_count": 0,
                "drift_count": 0,
                "refresh_mode": "skipped",
                "post_refresh_stale_source_count": 0,
                "route_refreshed": False,
                "skip_reason": "low_disk_headroom",
            },
        }

    target_kinds = included_kinds if source == "all" else [source]
    if progress:
        progress(
            f"route refresh start: source={source}, target_kinds={','.join(target_kinds)}, "
            f"auto_refresh_embeddings={auto_refresh_embeddings}"
        )
        progress("checking target embedding freshness")
    embedding_refresh = _ensure_embeddings_current(
        repo_root,
        source_kinds=target_kinds,
        auto_refresh=auto_refresh_embeddings,
        progress=progress,
    )

    if progress:
        progress("loading route rows and source fingerprints")
    rows, current_source_state = _build_rows(repo_root, standard, source_kinds=included_kinds)
    if progress:
        progress(f"route rows loaded: {len(rows)} rows across {len(included_kinds)} source kinds")
    artifact_index = _build_artifact_index(rows)
    previous_status = load_route_status(repo_root)
    previous_graph = load_route_graph(repo_root)
    evidence_summary = load_route_evidence_summary(repo_root)

    axis_registry_hash = _axis_registry_hash(standard)
    previous_axis_hash = str(previous_status.get("axis_registry_hash") or "")
    previous_source_state = previous_status.get("source_kinds") or {}
    previous_nodes = previous_graph.get("nodes") or {}

    full_rebuild = force or not previous_nodes or previous_axis_hash != axis_registry_hash
    changed_sources: dict[str, list[str]] = {}
    changed_row_keys: set[str] = set()
    removed_row_keys: set[str] = set()

    for source_kind in included_kinds:
        current = current_source_state.get(source_kind) or {}
        previous = previous_source_state.get(source_kind) or {}
        current_schema = current.get("embedding_schema_hash")
        previous_schema = previous.get("embedding_schema_hash")
        current_model = current.get("model")
        previous_model = previous.get("model")
        current_adapter_schema = _current_adapter_schema_hash(repo_root, source_kind)
        current["adapter_schema_hash"] = current_adapter_schema
        previous_adapter_schema = previous.get("adapter_schema_hash")

        if source_kind in target_kinds and (
            current_schema != previous_schema
            or current_model != previous_model
            or current_adapter_schema != previous_adapter_schema
        ):
            full_rebuild = True

        current_ids = current.get("id_fingerprints") or {}
        previous_ids = previous.get("id_fingerprints") or {}
        changed_ids = sorted(
            {
                artifact_id
                for artifact_id in set(current_ids.keys()) | set(previous_ids.keys())
                if current_ids.get(artifact_id) != previous_ids.get(artifact_id)
            }
        )
        if source != "all" and source_kind != source:
            changed_ids = []
        if changed_ids:
            changed_sources[source_kind] = changed_ids
            for row in rows.values():
                if row.source_kind == source_kind and row.artifact_id in changed_ids:
                    changed_row_keys.add(row.row_key)
        current_keys = {
            _row_key(row.source_kind, row.artifact_id, row.facet)
            for row in rows.values()
            if row.source_kind == source_kind
        }
        previous_kind_keys = {
            str(node_key)
            for node_key, node in previous_nodes.items()
            if str((node or {}).get("source_kind") or "") == source_kind
        }
        added_row_keys = current_keys - previous_kind_keys
        if source == "all" or source_kind == source:
            if added_row_keys:
                changed_row_keys |= added_row_keys
                added_ids = {
                    rows[row_key].artifact_id
                    for row_key in added_row_keys
                    if row_key in rows
                }
                changed_sources[source_kind] = sorted(
                    set(changed_sources.get(source_kind, [])) | added_ids
                )
        if previous_ids:
            removed_row_keys |= previous_kind_keys - current_keys

    evidence_summary_fingerprint = _summary_fingerprint(evidence_summary)
    embedding_changed = any(bool((info or {}).get("refreshed")) for info in embedding_refresh.values())
    if (
        not full_rebuild
        and not embedding_changed
        and not changed_sources
        and not changed_row_keys
        and not removed_row_keys
        and previous_graph
        and previous_status
        and str(previous_status.get("evidence_summary_fingerprint") or "") == evidence_summary_fingerprint
    ):
        if progress:
            progress("route graph already current; using cached projections")
        previous_stats = (previous_graph.get("statistics") or {})
        previous_drift = load_route_drift(repo_root)
        route_drift_digest = route_drift_snapshot_digest(previous_drift)
        stable_signal_digest = route_drift_digest
        post_refresh_staleness = current_route_staleness(repo_root, source_kinds=included_kinds)
        status = _build_route_status_payload(
            axis_registry_hash=axis_registry_hash,
            route_graph_fingerprint=str(previous_status.get("route_graph_fingerprint") or _graph_fingerprint(previous_nodes)),
            evidence_summary_fingerprint=evidence_summary_fingerprint,
            refresh_mode="incremental",
            source=source,
            refreshed_row_count=0,
            impacted_row_count=0,
            changed_sources={},
            embedding_refresh=embedding_refresh,
            post_refresh_staleness=post_refresh_staleness,
            source_state=current_source_state,
            included_kinds=included_kinds,
            statistics=previous_stats,
        )
        _atomic_write_json(paths["status"], status)
        return {
            "kind": "kernel.route_refresh",
            "source": source,
            "refresh_mode": "incremental",
            "graph_path": str(paths["graph"].relative_to(repo_root)),
            "status_path": str(paths["status"].relative_to(repo_root)),
            "drift_path": str(paths["drift"].relative_to(repo_root)),
            "evidence_summary_path": str(paths["evidence_summary"].relative_to(repo_root)),
            "route_drift_digest": route_drift_digest,
            "result_summary": {
                "refreshed_rows": 0,
                "changed_source_count": 0,
                "node_count": int(previous_stats.get("node_count") or 0),
                "edge_count": int(previous_stats.get("edge_count") or 0),
                "drift_count": int(previous_drift.get("drift_count") or 0),
                "refresh_mode": "incremental",
                "post_refresh_stale_source_count": sum(
                    1 for info in post_refresh_staleness.values() if bool(info.get("stale"))
                ),
            },
            "stable_signal_digest": stable_signal_digest,
            "changed_sources": {},
            "changed_sources_summary": _changed_sources_preview({}),
            "embedding_refresh": embedding_refresh,
            "post_refresh_staleness": post_refresh_staleness,
        }

    if full_rebuild:
        refreshed_row_keys = sorted(rows.keys())
        impacted_row_keys: set[str] = set()
        refresh_mode = "full"
    else:
        invalidated_row_count = len(changed_row_keys | removed_row_keys)
        if invalidated_row_count >= LARGE_INCREMENTAL_ROW_THRESHOLD:
            full_rebuild = True
            refreshed_row_keys = sorted(rows.keys())
            impacted_row_keys = set()
            refresh_mode = "full"
            if progress:
                progress(
                    "large route invalidation promoted to full rebuild: "
                    f"{invalidated_row_count} changed/removed rows >= {LARGE_INCREMENTAL_ROW_THRESHOLD}"
                )
        else:
            if progress and invalidated_row_count:
                progress(f"computing impacted route rows: {invalidated_row_count} changed/removed rows")
            impacted_row_keys = _compute_impacted_row_keys(
                current_rows=rows,
                previous_graph_nodes=previous_nodes,
                changed_row_keys=changed_row_keys | removed_row_keys,
            )
            refreshed_row_keys = sorted((changed_row_keys | impacted_row_keys) & set(rows.keys()))
            refresh_mode = "incremental"

    if progress:
        progress(f"building axis indexes for {len(rows)} route rows")
    axis_indexes = _build_axis_indexes(rows)
    nodes: dict[str, Any] = {}

    def _progress_nodes(index: int, total: int) -> None:
        if not progress or total <= 0:
            return
        step = max(1, total // 10)
        if index == 1 or index == total or index % step == 0:
            pct = int(round((index / total) * 100))
            progress(
                f"building route nodes {index}/{total} ({pct}%, mode={refresh_mode}, source={source})"
            )

    if full_rebuild:
        for index, row_key in enumerate(refreshed_row_keys, start=1):
            nodes[row_key] = _build_node_payload(
                rows[row_key],
                axis_indexes=axis_indexes,
                limits=standard["adjacency_limits"],
            )
            _progress_nodes(index, len(refreshed_row_keys))
    else:
        for row_key, node in previous_nodes.items():
            if row_key in removed_row_keys:
                continue
            if row_key not in refreshed_row_keys and row_key in rows:
                nodes[row_key] = node
        for index, row_key in enumerate(refreshed_row_keys, start=1):
            nodes[row_key] = _build_node_payload(
                rows[row_key],
                axis_indexes=axis_indexes,
                limits=standard["adjacency_limits"],
            )
            _progress_nodes(index, len(refreshed_row_keys))

    # Re-sort nodes and clear any stale references produced by incremental merge.
    normalized_nodes: dict[str, Any] = {}
    valid_row_keys = set(rows.keys())
    for row_key in sorted(nodes.keys()):
        node = dict(nodes[row_key])
        same = [
            edge for edge in (node.get("same_kind_neighbors") or [])
            if str(edge.get("target_row_key") or "") in valid_row_keys
        ]
        same.sort(key=_score_sort_key)
        cross_kind: dict[str, list[dict[str, Any]]] = {}
        for target_kind, edges in sorted((node.get("neighbors_by_target_kind") or {}).items()):
            valid_edges = [
                edge for edge in edges
                if str(edge.get("target_row_key") or "") in valid_row_keys
            ]
            valid_edges.sort(key=_score_sort_key)
            cross_kind[str(target_kind)] = valid_edges
        node["same_kind_neighbors"] = same
        node["neighbors_by_target_kind"] = cross_kind
        normalized_nodes[row_key] = node

    graph = {
        "kind": "semantic_route_graph",
        "schema_version": "semantic_route_graph_v1",
        "generated_at": _now_iso(),
        "axis_registry_hash": axis_registry_hash,
        "refresh_mode": refresh_mode,
        "requested_source": source,
        "evidence_summary_fingerprint": evidence_summary_fingerprint,
        "adjacency_limits": dict(standard.get("adjacency_limits") or {}),
        "artifacts": artifact_index["artifacts"],
        "artifacts_by_id": artifact_index["by_plain_id"],
        "nodes": normalized_nodes,
        "statistics": {
            "node_count": len(normalized_nodes),
            "artifact_count": len(artifact_index["artifacts"]),
            "edge_count": sum(
                len(node.get("same_kind_neighbors") or [])
                + sum(len(edges) for edges in (node.get("neighbors_by_target_kind") or {}).values())
                for node in normalized_nodes.values()
            ),
        },
    }
    route_graph_fingerprint = _graph_fingerprint(normalized_nodes)

    post_refresh_staleness = current_route_staleness(repo_root, source_kinds=included_kinds)
    status = _build_route_status_payload(
        axis_registry_hash=axis_registry_hash,
        route_graph_fingerprint=route_graph_fingerprint,
        evidence_summary_fingerprint=evidence_summary_fingerprint,
        refresh_mode=refresh_mode,
        source=source,
        refreshed_row_count=len(refreshed_row_keys),
        impacted_row_count=len(impacted_row_keys),
        changed_sources=changed_sources,
        embedding_refresh=embedding_refresh,
        post_refresh_staleness=post_refresh_staleness,
        source_state=current_source_state,
        included_kinds=included_kinds,
        statistics=graph["statistics"],
    )

    if progress:
        progress("building route drift report")
    drift = _build_drift_report(
        standard=standard,
        rows=rows,
        evidence_summary=evidence_summary,
        axis_registry_hash=axis_registry_hash,
    )

    if progress:
        progress(
            "writing route projections: "
            f"nodes={graph['statistics']['node_count']}, edges={graph['statistics']['edge_count']}, "
            f"drift={drift['drift_count']}"
        )
    _atomic_write_json(paths["graph"], graph)
    _atomic_write_json(paths["status"], status)
    _atomic_write_json(paths["drift"], drift)

    route_drift_digest = route_drift_snapshot_digest(drift)
    stable_signal_digest = route_drift_digest
    return {
        "kind": "kernel.route_refresh",
        "source": source,
        "refresh_mode": refresh_mode,
        "graph_path": str(paths["graph"].relative_to(repo_root)),
        "status_path": str(paths["status"].relative_to(repo_root)),
        "drift_path": str(paths["drift"].relative_to(repo_root)),
        "evidence_summary_path": str(paths["evidence_summary"].relative_to(repo_root)),
        "route_drift_digest": route_drift_digest,
        "result_summary": {
            "refreshed_rows": len(refreshed_row_keys),
            "changed_source_count": len(changed_sources),
            "node_count": graph["statistics"]["node_count"],
            "edge_count": graph["statistics"]["edge_count"],
            "drift_count": drift["drift_count"],
            "refresh_mode": refresh_mode,
            "post_refresh_stale_source_count": sum(
                1 for info in post_refresh_staleness.values() if bool(info.get("stale"))
            ),
        },
        "stable_signal_digest": stable_signal_digest,
        "changed_sources": _changed_sources_preview(changed_sources)["preview"],
        "changed_sources_summary": _changed_sources_preview(changed_sources),
        "embedding_refresh": embedding_refresh,
        "post_refresh_staleness": post_refresh_staleness,
    }


def _resolve_artifact_token(
    graph: Mapping[str, Any],
    token: str,
) -> list[str]:
    artifacts = graph.get("artifacts") or {}
    artifacts_by_id = graph.get("artifacts_by_id") or {}
    raw = str(token or "").strip()
    if not raw:
        return []
    if raw in artifacts:
        return [raw]
    if ":" in raw:
        source_kind, artifact_id = raw.split(":", 1)
        composed = _artifact_token(source_kind, artifact_id)
        return [composed] if composed in artifacts else []
    matches = artifacts_by_id.get(raw) or []
    return [str(item) for item in matches]


def _apply_edge_evidence(
    edge: Mapping[str, Any],
    *,
    source_row_key: str,
    evidence_summary: Mapping[str, Any],
) -> dict[str, Any]:
    payload = dict(edge)
    summary = ((evidence_summary.get("edges") or {}) if isinstance(evidence_summary, Mapping) else {}).get(
        _edge_key(source_row_key, str(edge.get("target_row_key") or ""))
    ) or {}
    boost = float(summary.get("boost_fraction") or 0.0)
    payload["evidence_boost_fraction"] = round(boost, 6)
    payload["evidence_counts"] = dict(summary.get("counts") or {})
    payload["adjusted_score"] = round(float(edge.get("semantic_score") or 0.0) * (1.0 + boost), 6)
    return payload


def expand_route_rows(
    repo_root: Path,
    *,
    query: str,
    row_keys: Sequence[str],
    source_kinds: Sequence[str] | None = None,
    top_k: int = 10,
) -> dict[str, Any]:
    graph = load_route_graph(repo_root)
    status = load_route_status(repo_root)
    evidence_summary = load_route_evidence_summary(repo_root)
    nodes = graph.get("nodes") or {}
    allowed_target_kinds = {str(kind) for kind in (source_kinds or []) if str(kind).strip()}
    persisted_staleness = status.get("embedding_staleness") if isinstance(status.get("embedding_staleness"), Mapping) else {}
    stale_source_kinds = {
        kind
        for kind, info in persisted_staleness.items()
        if (not allowed_target_kinds or kind in allowed_target_kinds) and isinstance(info, Mapping) and bool(info.get("stale"))
    }
    seed_hits: list[dict[str, Any]] = []
    route_hits: list[dict[str, Any]] = []
    missing_rows: list[str] = []

    for row_key in dict.fromkeys(str(item).strip() for item in row_keys if str(item).strip()):
        node = nodes.get(row_key)
        if not isinstance(node, Mapping):
            missing_rows.append(row_key)
            continue
        seed_hits.append(
            {
                "id": node.get("artifact_id"),
                "facet": node.get("facet"),
                "source_kind": node.get("source_kind"),
                "source_path": node.get("source_path"),
                "score": 1.0,
                "preview": node.get("title") or node.get("text_preview"),
                "row_key": row_key,
            }
        )
        edges = list(node.get("same_kind_neighbors") or [])
        for target_edges in (node.get("neighbors_by_target_kind") or {}).values():
            edges.extend(list(target_edges or []))
        for edge in edges:
            if not isinstance(edge, Mapping):
                continue
            target_kind = str(edge.get("target_kind") or "").strip()
            if allowed_target_kinds and target_kind not in allowed_target_kinds:
                continue
            enriched = _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
            adjusted_score = round(float(enriched.get("adjusted_score") or enriched.get("semantic_score") or 0.0), 6)
            route_hits.append(
                {
                    "seed_row_key": row_key,
                    "seed_source_kind": node.get("source_kind"),
                    "seed_id": node.get("artifact_id"),
                    "seed_facet": node.get("facet"),
                    "seed_score": 1.0,
                    "combined_score": adjusted_score,
                    **enriched,
                }
            )

    route_hits.sort(key=lambda item: (-float(item.get("combined_score") or 0.0), str(item.get("target_row_key") or "")))
    return {
        "kind": "kernel.route_query",
        "query": query,
        "source_kinds": list(source_kinds or []),
        "graph_path": GRAPH_PATH,
        "seed_hits": seed_hits[:top_k],
        "route_hits": route_hits[:top_k],
        "fallback_hits": [],
        "stale_source_kinds": sorted(stale_source_kinds),
        "stale_or_missing_rows": sorted(set(missing_rows)),
        "staleness_source": "persisted_route_status_snapshot",
        "expansion_mode": "persisted_preflight_row_expansion",
    }


def query_routes(
    repo_root: Path,
    *,
    query: str,
    source_kinds: Sequence[str] | None = None,
    top_k: int = 10,
    check_live_staleness: bool = True,
) -> dict[str, Any]:
    standard = _load_standard(repo_root)
    included_kinds = _included_source_kinds(standard)
    kinds = [kind for kind in (source_kinds or included_kinds) if kind in included_kinds]
    graph = load_route_graph(repo_root)
    status = load_route_status(repo_root)
    evidence_summary = load_route_evidence_summary(repo_root)
    substrate = EmbeddingSubstrate(repo_root)
    if check_live_staleness:
        stale_status = current_route_staleness(repo_root, source_kinds=kinds)
        staleness_source = "live_adapter_check"
    else:
        persisted_staleness = status.get("embedding_staleness") if isinstance(status.get("embedding_staleness"), Mapping) else {}
        stale_status = {
            kind: dict(persisted_staleness.get(kind) or {})
            for kind in kinds
            if isinstance(persisted_staleness.get(kind), Mapping)
        }
        staleness_source = "persisted_route_status_snapshot"
    stale_source_kinds = {
        source_kind
        for source_kind, info in stale_status.items()
        if bool(info.get("stale"))
    }
    fresh_source_kinds = [kind for kind in kinds if kind not in stale_source_kinds]

    if not kinds:
        return {
            "kind": "kernel.route_query",
            "query": query,
            "error": "no_supported_source_kinds",
        }

    seed_hits = substrate.search(query, source_kinds=fresh_source_kinds, top_k=max(top_k, 12)) if fresh_source_kinds else []
    route_hits: dict[str, dict[str, Any]] = {}
    fallback_hits: list[dict[str, Any]] = []
    stale_or_missing_rows: list[str] = []

    graph_nodes = graph.get("nodes") or {}
    status_sources = status.get("source_kinds") or {}

    for seed in seed_hits:
        row_key = _row_key(seed.record.source_kind, seed.record.id, seed.record.facet)
        row_status = status_sources.get(seed.record.source_kind) or {}
        source_fingerprint = row_status.get("source_fingerprint")
        node = graph_nodes.get(row_key)
        if node is None or not source_fingerprint or seed.record.source_kind in stale_source_kinds:
            stale_or_missing_rows.append(row_key)
            continue

        for edge in node.get("same_kind_neighbors", []):
            enriched = _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
            combined_score = round((0.6 * float(seed.score)) + (0.4 * float(enriched["adjusted_score"])), 6)
            existing = route_hits.get(enriched["target_row_key"])
            if existing is None or combined_score > float(existing["combined_score"]):
                route_hits[enriched["target_row_key"]] = {
                    "seed_row_key": row_key,
                    "seed_source_kind": seed.record.source_kind,
                    "seed_id": seed.record.id,
                    "seed_facet": seed.record.facet,
                    "seed_score": round(float(seed.score), 6),
                    "combined_score": combined_score,
                    **enriched,
                }
        for edges in (node.get("neighbors_by_target_kind") or {}).values():
            for edge in edges:
                enriched = _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
                combined_score = round((0.6 * float(seed.score)) + (0.4 * float(enriched["adjusted_score"])), 6)
                existing = route_hits.get(enriched["target_row_key"])
                if existing is None or combined_score > float(existing["combined_score"]):
                    route_hits[enriched["target_row_key"]] = {
                        "seed_row_key": row_key,
                        "seed_source_kind": seed.record.source_kind,
                        "seed_id": seed.record.id,
                        "seed_facet": seed.record.facet,
                        "seed_score": round(float(seed.score), 6),
                        "combined_score": combined_score,
                        **enriched,
                    }

    should_fallback = bool(stale_source_kinds) or (bool(stale_or_missing_rows) and not route_hits)
    if should_fallback:
        fallback_hits.extend(
            _embedding_fallback_hits(
                substrate,
                query=query,
                source_kinds=fresh_source_kinds,
                top_k=top_k,
            )
        )
        fallback_hits.extend(
            _lexical_fallback_hits(
                repo_root,
                query=query,
                source_kinds=sorted(stale_source_kinds),
                top_k=max(top_k, 12),
            )
        )
        fallback_hits.sort(key=lambda item: (-float(item["score"]), str(item["source_kind"]), str(item["id"]), str(item["facet"])))

    ranked_routes = sorted(route_hits.values(), key=lambda item: (-float(item["combined_score"]), item["target_row_key"]))
    return {
        "kind": "kernel.route_query",
        "query": query,
        "source_kinds": kinds,
        "graph_path": GRAPH_PATH,
        "seed_hits": [
            {
                "id": hit.record.id,
                "facet": hit.record.facet,
                "source_kind": hit.record.source_kind,
                "source_path": hit.record.source_path,
                "score": round(float(hit.score), 6),
                "preview": hit.record.text_preview,
            }
            for hit in seed_hits[:top_k]
        ],
        "route_hits": ranked_routes[:top_k],
        "fallback_hits": fallback_hits[:top_k],
        "stale_source_kinds": sorted(stale_source_kinds),
        "stale_or_missing_rows": sorted(set(stale_or_missing_rows)),
        "staleness_source": staleness_source,
    }


def describe_route_node(repo_root: Path, *, artifact_token: str) -> dict[str, Any]:
    graph = load_route_graph(repo_root)
    status = load_route_status(repo_root)
    evidence_summary = load_route_evidence_summary(repo_root)
    matches = _resolve_artifact_token(graph, artifact_token)
    if not matches:
        return {
            "kind": "kernel.route_node",
            "requested": artifact_token,
            "error": "artifact_not_found",
        }
    if len(matches) > 1:
        return {
            "kind": "kernel.route_node",
            "requested": artifact_token,
            "error": "ambiguous_artifact_id",
            "candidates": matches,
        }
    token = matches[0]
    artifact = (graph.get("artifacts") or {}).get(token) or {}
    nodes = graph.get("nodes") or {}
    source_status = ((status.get("source_kinds") or {}).get(artifact.get("source_kind") or "")) or {}
    row_payloads = []
    for row_key in artifact.get("row_keys") or []:
        node = dict(nodes.get(row_key) or {})
        if not node:
            continue
        node["same_kind_neighbors"] = [
            _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
            for edge in node.get("same_kind_neighbors", [])
        ]
        node["neighbors_by_target_kind"] = {
            target_kind: [
                _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
                for edge in edges
            ]
            for target_kind, edges in sorted((node.get("neighbors_by_target_kind") or {}).items())
        }
        row_payloads.append(node)
    return {
        "kind": "kernel.route_node",
        "requested": artifact_token,
        "artifact": artifact,
        "source_status": {
            "source_fingerprint": source_status.get("source_fingerprint"),
            "embedding_schema_hash": source_status.get("embedding_schema_hash"),
            "adapter_schema_hash": source_status.get("adapter_schema_hash"),
            "last_refresh_at": source_status.get("last_refresh_at"),
        },
        "rows": row_payloads,
    }


def _load_evidence_summary_or_default(repo_root: Path, standard: Mapping[str, Any]) -> dict[str, Any]:
    summary = load_route_evidence_summary(repo_root)
    if summary:
        return summary
    contract = standard.get("evidence_contract") or {}
    return {
        "kind": "semantic_route_evidence_summary",
        "schema_version": "semantic_route_evidence_summary_v1",
        "generated_at": _now_iso(),
        "boost_cap_fraction": float(contract.get("boost_cap_fraction") or 0.1),
        "edges": {},
    }


def _update_evidence_summary(
    summary: dict[str, Any],
    *,
    source_row_key: str,
    target_row_key: str,
    evidence_kind: str,
    standard: Mapping[str, Any],
) -> dict[str, Any]:
    contract = standard.get("evidence_contract") or {}
    weights = contract.get("boost_formula") or {}
    cap = float(contract.get("boost_cap_fraction") or 0.1)
    edges = summary.setdefault("edges", {})
    edge_key = _edge_key(source_row_key, target_row_key)
    entry = edges.setdefault(
        edge_key,
        {
            "source_row_key": source_row_key,
            "target_row_key": target_row_key,
            "counts": {"confirmation": 0, "rejected": 0, "operation_success": 0},
            "boost_fraction": 0.0,
            "last_recorded_at": None,
        },
    )
    counts = entry.setdefault("counts", {"confirmation": 0, "rejected": 0, "operation_success": 0})
    counts[evidence_kind] = int(counts.get(evidence_kind) or 0) + 1
    signed = 0.0
    for kind, weight in (weights.items() if isinstance(weights, Mapping) else []):
        signed += float(weight or 0.0) * int(counts.get(str(kind)) or 0)
    entry["boost_fraction"] = round(max(0.0, min(cap, signed)), 6)
    entry["last_recorded_at"] = _now_iso()
    summary["generated_at"] = _now_iso()
    summary["boost_cap_fraction"] = cap
    return summary


def _best_edge_between_artifacts(
    graph: Mapping[str, Any],
    *,
    source_token: str,
    target_token: str,
    evidence_summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    artifacts = graph.get("artifacts") or {}
    source = artifacts.get(source_token) or {}
    target = artifacts.get(target_token) or {}
    source_rows = source.get("row_keys") or []
    target_rows = set(target.get("row_keys") or [])
    nodes = graph.get("nodes") or {}
    best: dict[str, Any] | None = None
    for row_key in source_rows:
        node = nodes.get(row_key) or {}
        for edge in (node.get("same_kind_neighbors") or []):
            if edge.get("target_row_key") in target_rows:
                enriched = _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
                payload = {"source_row_key": row_key, **enriched}
                if best is None or float(payload["adjusted_score"]) > float(best["adjusted_score"]):
                    best = payload
        for edges in (node.get("neighbors_by_target_kind") or {}).values():
            for edge in edges:
                if edge.get("target_row_key") in target_rows:
                    enriched = _apply_edge_evidence(edge, source_row_key=row_key, evidence_summary=evidence_summary)
                    payload = {"source_row_key": row_key, **enriched}
                    if best is None or float(payload["adjusted_score"]) > float(best["adjusted_score"]):
                        best = payload
    return best


def confirm_route(
    repo_root: Path,
    *,
    source_token: str,
    target_token: str,
    evidence_kind: str = "confirmation",
    actor_id: str = "kernel.route_confirm",
    note: str | None = None,
    operation_id: str | None = None,
) -> dict[str, Any]:
    standard = _load_standard(repo_root)
    allowed = {str(item) for item in (standard.get("evidence_contract", {}).get("allowed_kinds") or [])}
    if evidence_kind not in allowed:
        raise ValueError(f"unsupported route evidence kind: {evidence_kind}")

    graph = load_route_graph(repo_root)
    evidence_summary = _load_evidence_summary_or_default(repo_root, standard)

    source_matches = _resolve_artifact_token(graph, source_token)
    target_matches = _resolve_artifact_token(graph, target_token)
    if not source_matches:
        return {"kind": "kernel.route_confirm", "error": "source_not_found", "requested_source": source_token}
    if not target_matches:
        return {"kind": "kernel.route_confirm", "error": "target_not_found", "requested_target": target_token}
    if len(source_matches) > 1:
        return {"kind": "kernel.route_confirm", "error": "ambiguous_source", "candidates": source_matches}
    if len(target_matches) > 1:
        return {"kind": "kernel.route_confirm", "error": "ambiguous_target", "candidates": target_matches}

    resolved_source = source_matches[0]
    resolved_target = target_matches[0]
    best_edge = _best_edge_between_artifacts(
        graph,
        source_token=resolved_source,
        target_token=resolved_target,
        evidence_summary=evidence_summary,
    )
    if best_edge is None:
        return {
            "kind": "kernel.route_confirm",
            "error": "edge_not_found",
            "source": resolved_source,
            "target": resolved_target,
        }

    evidence_id = f"rte_{_sha_text('|'.join([resolved_source, resolved_target, evidence_kind, _now_iso()]))[:12]}"
    record = {
        "kind": "semantic_route_evidence",
        "schema_version": "semantic_route_evidence_v1",
        "evidence_id": evidence_id,
        "recorded_at": _now_iso(),
        "evidence_kind": evidence_kind,
        "actor_id": actor_id,
        "operation_id": operation_id,
        "note": note or "",
        "source_artifact_token": resolved_source,
        "target_artifact_token": resolved_target,
        "source_row_key": best_edge["source_row_key"],
        "target_row_key": best_edge["target_row_key"],
        "source_kind": resolved_source.split(":", 1)[0],
        "source_id": resolved_source.split(":", 1)[1],
        "source_facet": best_edge["source_row_key"].split(":")[-1],
        "target_kind": best_edge["target_kind"],
        "target_id": best_edge["target_id"],
        "target_facet": best_edge["target_facet"],
        "semantic_score": best_edge["semantic_score"],
    }
    paths = _resolve_paths(repo_root)
    _append_jsonl(paths["evidence_ledger"], record)
    summary = _update_evidence_summary(
        evidence_summary,
        source_row_key=best_edge["source_row_key"],
        target_row_key=best_edge["target_row_key"],
        evidence_kind=evidence_kind,
        standard=standard,
    )
    _atomic_write_json(paths["evidence_summary"], summary)
    edge_summary = ((summary.get("edges") or {}).get(_edge_key(best_edge["source_row_key"], best_edge["target_row_key"])) or {})
    return {
        "kind": "kernel.route_confirm",
        "ledger_path": str(paths["evidence_ledger"].relative_to(repo_root)),
        "evidence_summary_path": str(paths["evidence_summary"].relative_to(repo_root)),
        "record": record,
        "edge_summary": edge_summary,
    }


def append_operation_route_evidence(
    repo_root: Path,
    *,
    evidence_rows: Sequence[Mapping[str, Any]],
    actor_id: str = "operation.success",
    operation_id: str | None = None,
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for row in evidence_rows:
        source = str(row.get("source_artifact") or row.get("source") or "").strip()
        target = str(row.get("target_artifact") or row.get("target") or "").strip()
        if not source or not target:
            continue
        evidence_kind = str(row.get("evidence_kind") or "operation_success").strip() or "operation_success"
        note = str(row.get("note") or "").strip() or None
        result = confirm_route(
            repo_root,
            source_token=source,
            target_token=target,
            evidence_kind=evidence_kind,
            actor_id=actor_id,
            note=note,
            operation_id=operation_id,
        )
        results.append(result)
    return results
