"""
[PURPOSE]
- Teleology: Generalised faceted-vector-field substrate for the plane. Every durable artifact (doctrine node, paper module, skill, raw-seed shard, archaeological shard, Python module under std_python.py) is described by a controlled vocabulary of typed fields; each field is a separate semantic axis with its own embedding row, so search, drift detection, and cross-artifact alignment respect the schema rather than collapsing it into one blob. The substrate is externalised cognition (par_phase_09…source_10_002) — reading it is activation along a graded ladder, not retrieval from a flat index.
- Mechanism: Per-source JSON files at state/embeddings/<kind>.json hold one record per (id, facet); refresh is content-hash-gated per row; search supports facet scoping plus an activation ladder (coarse facet first, escalate when the current rung leaves a named gap); alignment emits the cross-facet cosine matrix between two artifacts so doc/code drift becomes a number, not a vibe.

[INTERFACE]
- Exports: EmbeddingSubstrate, EmbeddingRecord, FacetedItem, SourceAdapter, SearchHit, SubstrateStatus, embed_texts_default, FACET_BODY.
- Reads: state/embeddings/<kind>.json; the per-source adapter items.
- Writes: state/embeddings/<kind>.json (atomic replace).

[FLOW]
- refresh(adapter): iterate FacetedItem -> for each (id, facet) compute content_hash -> queue stale/missing -> batch-embed -> merge -> atomic write.
- search(query, kinds, facets): embed query once -> cosine across matching records -> top-K SearchHit.
- search_ladder(query, kinds, ladder=[facet,...], k_per_rung=[...]): activation gradient — score by the cheapest facet first, narrow, then re-score on the next facet only over the survivors.
- alignment(id_a, id_b): pull every facet pair across the two ids, return a matrix of cosines so per-axis drift is visible.
- When-needed: Open this module when adding a new substrate adapter, wiring a kernel ladder/alignment flag, or debugging schema-vs-cache divergence.
- Escalates-to: system.lib.embedding_sources (per-source adapters), system.lib.nvidia_nim (default embedding provider).

[DEPENDENCIES]
- Required:
  - system.lib.nvidia_nim (default embedding provider)
  - json, hashlib, math, os, tempfile, time (std)
  - dataclasses, typing (std)

[CONSTRAINTS]
- Guarantee: a record with the same (source_kind, id, facet, content_hash, schema_hash, model) is never re-embedded; writes are atomic; search is deterministic given identical inputs.
- Non-goal: this module does not author the controlled vocabulary — it consumes whatever facet names an adapter chooses. The schema lives in std_python.py / std_voice_archaeology.json / paper-module conventions / etc.
- Scope: internal plane use only; no auth layer; rate-limiting delegated to the provider.

Rosetta routing header (std_navigation_rosetta_grammar.json::noun_shape):
  kind: python_module
  role: faceted-vector-field substrate primitive; one record per (source_kind, id, facet) under content/schema/model hash, atomic JSON cache, deterministic ladder search and pairwise alignment; the foundational layer below semantic_routing, voice_archaeology coverage_check, and any kind-aware activation gradient.
  depends_on:
    - system/lib/embedding_sources.py: feeds_when_fresh - per-source adapters yield FacetedItem rows that this substrate caches; refresh-stale flow is gated by adapter schema_hash.
    - system/lib/nvidia_nim.py: feeds - default embedding provider (nv-embed-v1, 4096-dim) supplies the vectors this substrate caches.
    - codex/standards/std_python.py: governs_without_populating - the controlled vocabulary for python_holographic facets is authoritative in std_python.py; this substrate never authors facet names.
    - codex/standards/voice_archaeology/std_voice_archaeology.json: governs_without_populating - the controlled vocabulary for archaeological-shard facets.
    - codex/doctrine/paper_modules/embedding_substrate.md: evidences - paper-module roof for this subsystem; cold readers route here first per --paper-module embedding_substrate.
    - system/lib/semantic_routing.py: routes_to - the activation-ledger / route-graph layer is the next compression rung above this substrate.
  governed_by:
    - codex/standards/std_python.py
    - codex/doctrine/paper_modules/embedding_substrate.md
  code_loci:
    - EmbeddingSubstrate: top-level class; owns refresh / search / search_ladder / alignment over a per-kind cache file at state/embeddings/<kind>.json.
    - EmbeddingRecord: single (source_kind, id, facet) cached vector with content_hash + schema_hash + model.
    - FacetedItem: in-memory shape an adapter yields per artifact.
    - SourceAdapter: abstract per-source iterator; embedding_sources.py provides the concrete adapters.
    - SearchHit: scored result row; search and search_ladder both emit these.
    - SubstrateStatus: cache freshness / counts projection.
    - embed_texts_default: default text-batch embed call; routed through nvidia_nim.
    - FACET_BODY: default facet name for single-axis adapters.
  evidence_command: ./repo-python kernel.py --embed-status (cache snapshot); ./repo-python kernel.py --semantic-search "<query>" --kind <kind> (deterministic search probe).
  source_authority: self for the cache shape and refresh/search/alignment contracts; codex/standards/std_python.py for python facet vocabulary; codex/standards/voice_archaeology/std_voice_archaeology.json for archaeology facet vocabulary.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import time
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence


DEFAULT_STATE_ROOT = "state/embeddings"
DEFAULT_BATCH_SIZE = 16
SCHEMA_VERSION = "embedding_substrate_v2_faceted"
OVERLAY_SCHEMA_VERSION = "embedding_substrate_overlay_v1"
OVERLAY_DIR_NAME = "_overlays"
LARGE_CACHE_OVERLAY_THRESHOLD_BYTES = int(os.environ.get("EMBEDDING_OVERLAY_THRESHOLD_BYTES", "50000000"))
FACET_BODY = "body"  # default facet name for single-axis adapters
MAX_EMBED_TEXT_CHARS = 6000
MAX_EMBED_TEXT_WORDS = 1200
_EMBED_TRIM_MARKER = "\n...\n"
_LENGTH_ERROR_MARKERS = (
    "maximum allowed token size",
    "input length",
    "context length",
    "maximum context length",
)


def _sha256_text(text: str) -> str:
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


def _cosine(u: Sequence[float], v: Sequence[float]) -> float:
    if not u or not v or len(u) != len(v):
        return 0.0
    dot = nu = nv = 0.0
    for a, b in zip(u, v):
        dot += a * b
        nu += a * a
        nv += b * b
    if nu == 0.0 or nv == 0.0:
        return 0.0
    return dot / (math.sqrt(nu) * math.sqrt(nv))


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _max_iso(*values: Any) -> str | None:
    tokens = [str(value) for value in values if str(value or "").strip()]
    return max(tokens) if tokens else None


def _drift_between(
    adapter_schema_hash: str | None,
    adapter_text_version: str | None,
    cached_schema_hash: str | None,
    cached_text_version: str | None,
) -> bool:
    """True iff adapter's schema_hash or text_version diverges from the cache.

    Conservative: if either side is None for a given gate, that gate is considered fresh.
    This preserves the historical schema_hash semantics — adapters that opt out of either
    drift signal (returning None) remain unaffected. Adapters that opt in by setting a
    non-None value can later force a clean re-embed by bumping it.
    """
    schema_drifted = (
        cached_schema_hash is not None
        and adapter_schema_hash is not None
        and cached_schema_hash != adapter_schema_hash
    )
    text_drifted = (
        cached_text_version is not None
        and adapter_text_version is not None
        and cached_text_version != adapter_text_version
    )
    return schema_drifted or text_drifted


def _clip_text_middle(text: str, *, max_chars: int) -> str:
    if len(text) <= max_chars:
        return text
    available = max(0, max_chars - len(_EMBED_TRIM_MARKER))
    head_chars = max(1, int(available * 0.75))
    tail_chars = max(0, available - head_chars)
    head = text[:head_chars].rstrip()
    tail = text[-tail_chars:].lstrip() if tail_chars else ""
    if not tail:
        return head[:max_chars]
    return f"{head}{_EMBED_TRIM_MARKER}{tail}"


def _prepare_embedding_text(
    text: str,
    *,
    max_chars: int = MAX_EMBED_TEXT_CHARS,
    max_words: int = MAX_EMBED_TEXT_WORDS,
) -> tuple[str, bool]:
    raw = str(text or "")
    if not raw:
        return "", False
    clipped = raw
    truncated = False
    words = raw.split()
    if len(words) > max_words:
        head_words = max(1, int(max_words * 0.75))
        tail_words = max(0, max_words - head_words)
        head = " ".join(words[:head_words]).strip()
        tail = " ".join(words[-tail_words:]).strip() if tail_words else ""
        clipped = head if not tail else f"{head}{_EMBED_TRIM_MARKER}{tail}"
        truncated = True
    if len(clipped) > max_chars:
        clipped = _clip_text_middle(clipped, max_chars=max_chars)
        truncated = True
    return clipped, truncated


def _is_length_error(exc: Exception) -> bool:
    message = str(exc or "").lower()
    return any(marker in message for marker in _LENGTH_ERROR_MARKERS)


@dataclass
class FacetedItem:
    """One artifact described by a controlled vocabulary of typed fields.

    `facets` maps each schema axis name (e.g. "purpose", "interface", "constraints"
    for std_python.py; "title", "statement", "tags" for doctrine; "tldr", "shape",
    "gap" for paper modules) to its text. Empty / None values are dropped at refresh.
    """

    id: str
    source_path: str
    facets: dict[str, str]
    metadata: dict = field(default_factory=dict)

    def non_empty_facets(self) -> dict[str, str]:
        return {k: v for k, v in self.facets.items() if v and v.strip()}


@dataclass
class EmbeddingRecord:
    id: str
    facet: str
    source_kind: str
    source_path: str
    content_hash: str
    text_preview: str
    metadata: dict
    vector: list
    model: str
    dims: int
    updated_at: str

    @property
    def composite_key(self) -> str:
        return f"{self.id}::{self.facet}"

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class SearchHit:
    record: EmbeddingRecord
    score: float

    def as_dict(self) -> dict:
        return {"score": round(self.score, 6), **self.record.as_dict()}


@dataclass
class LadderResult:
    final_hits: list[SearchHit]
    rung_trace: list[dict]

    def as_dict(self) -> dict:
        return {
            "final_hits": [h.as_dict() for h in self.final_hits],
            "rung_trace": self.rung_trace,
        }


@dataclass
class AlignmentEntry:
    facet_a: str
    facet_b: str
    score: float
    same_axis: bool


@dataclass
class SubstrateStatus:
    source_kind: str
    record_count: int
    facet_count: int
    distinct_ids: int
    model: str
    dims: int
    schema_hash: str | None
    last_refresh_at: str | None
    stale_or_missing: int
    path: str
    stale_preview: list[dict[str, str]] = field(default_factory=list)
    stale_preview_truncated: bool = False
    stale_or_missing_is_estimate: bool = False
    text_version: str | None = None
    expected_row_count: int | None = None
    stale_reason_counts: dict[str, int] = field(default_factory=dict)

    def as_dict(self) -> dict:
        return asdict(self)


class SourceAdapter:
    """Base class for embedding source adapters.

    Subclasses produce FacetedItem rows. A subclass that has no schema simply
    emits one facet keyed by FACET_BODY. Adapters that subclass should set
    `source_kind` and override `iter_items()`. `schema_hash()` returns a
    fingerprint of the shape contract governing this source so that schema
    changes (e.g. std_python.py edited) force a full re-embed.

    `text_version` is the per-adapter extraction-logic version constant. Bump it
    when iter_items()'s text-extraction semantics change (new facet added, an
    existing facet's join order rewritten, a section-mask refined, etc.) so the
    next refresh forces a clean re-embed of every (id, facet) row for this
    source without requiring an out-of-band --embed-refresh --force. None means
    "no version gate" (backward-compat default; matches schema_hash semantics).
    Anchor: gitnexus annex pattern p003 (`EMBEDDING_TEXT_VERSION = 'v2'` in
    annexes/gitnexus/repo/gitnexus/src/core/embeddings/embedding-pipeline.ts).
    """

    source_kind: str = "generic"
    text_version: str | None = None

    def iter_items(self) -> Iterator[FacetedItem]:
        raise NotImplementedError

    def schema_hash(self) -> str | None:
        return None


EmbedFn = Callable[[Sequence[str]], list[list[float]]]


def embed_texts_default(
    texts: Sequence[str],
    *,
    model: str | None = None,
    input_type: str = "passage",
) -> list[list[float]]:
    from system.lib import nvidia_nim

    config: dict[str, Any] = {"input_type": input_type}
    if model:
        config["model"] = model
    return nvidia_nim.embed_texts(list(texts), config=config)


class EmbeddingSubstrate:
    """Faceted on-disk embedding cache."""

    def __init__(
        self,
        repo_root: str | Path,
        *,
        state_root: str = DEFAULT_STATE_ROOT,
        embed_fn: EmbedFn | None = None,
        model: str | None = None,
        batch_size: int = DEFAULT_BATCH_SIZE,
    ) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.state_root = self.repo_root / state_root
        self.embed_fn = embed_fn or embed_texts_default
        self.model = model
        self.batch_size = max(1, int(batch_size))

    # ---------- storage ----------

    @staticmethod
    def _safe_source_name(source_kind: str) -> str:
        return source_kind.replace("/", "_").replace(" ", "_")

    def _path_for(self, source_kind: str) -> Path:
        return self.state_root / f"{self._safe_source_name(source_kind)}.json"

    def _overlay_path_for(self, source_kind: str) -> Path:
        return self.state_root / OVERLAY_DIR_NAME / f"{self._safe_source_name(source_kind)}.jsonl"

    def _overlay_state_path_for(self, source_kind: str) -> Path:
        return self.state_root / OVERLAY_DIR_NAME / f"{self._safe_source_name(source_kind)}.state.json"

    def _primary_cache_size_bytes(self, source_kind: str) -> int:
        path = self._path_for(source_kind)
        if not path.exists():
            return 0
        try:
            return path.stat().st_size
        except OSError:
            return 0

    def _should_use_overlay_refresh(self, source_kind: str, *, limit: int | None) -> bool:
        if limit is None:
            return False
        return self._primary_cache_size_bytes(source_kind) >= LARGE_CACHE_OVERLAY_THRESHOLD_BYTES

    def _load_overlay_state(self, source_kind: str) -> dict:
        path = self._overlay_state_path_for(source_kind)
        if not path.exists():
            return {}
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return dict(payload) if isinstance(payload, dict) else {}

    def overlay_state(self, source_kind: str) -> dict:
        return self._load_overlay_state(source_kind)

    def _load_overlay_records(self, source_kind: str) -> list[dict]:
        path = self._overlay_path_for(source_kind)
        if not path.exists():
            return []
        records: list[dict] = []
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    node = json.loads(line)
                    raw = node.get("record") if isinstance(node, dict) and "record" in node else node
                    if isinstance(raw, dict) and raw.get("id") and raw.get("facet"):
                        records.append(dict(raw))
        except (OSError, json.JSONDecodeError):
            return []
        return records

    def _overlay_records_by_key(self, source_kind: str) -> dict[str, dict]:
        out: dict[str, dict] = {}
        for record in self._load_overlay_records(source_kind):
            out[self._composite(str(record["id"]), str(record.get("facet", FACET_BODY)))] = record
        return out

    def _append_overlay_records(self, source_kind: str, records: Sequence[Mapping[str, Any]]) -> None:
        if not records:
            return
        path = self._overlay_path_for(source_kind)
        path.parent.mkdir(parents=True, exist_ok=True)
        now = _now_iso()
        with path.open("a", encoding="utf-8") as handle:
            for record in records:
                handle.write(
                    json.dumps(
                        {
                            "schema_version": OVERLAY_SCHEMA_VERSION,
                            "written_at": now,
                            "record": dict(record),
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    def _write_overlay_state(self, source_kind: str, payload: Mapping[str, Any]) -> None:
        _atomic_write_json(self._overlay_state_path_for(source_kind), dict(payload))

    def _clear_overlay(self, source_kind: str) -> None:
        for path in (self._overlay_path_for(source_kind), self._overlay_state_path_for(source_kind)):
            try:
                path.unlink()
            except FileNotFoundError:
                pass

    def _merge_overlay_records(self, source_kind: str, data: dict) -> dict:
        overlay_records = self._load_overlay_records(source_kind)
        if not overlay_records:
            return data
        merged: dict[str, dict] = {
            self._composite(str(record["id"]), str(record.get("facet", FACET_BODY))): dict(record)
            for record in data.get("records", [])
            if isinstance(record, Mapping) and record.get("id")
        }
        for record in overlay_records:
            merged[self._composite(str(record["id"]), str(record.get("facet", FACET_BODY)))] = dict(record)
        overlay_state = self._load_overlay_state(source_kind)
        data = dict(data)
        data["records"] = sorted(merged.values(), key=lambda r: (r["id"], r.get("facet", FACET_BODY)))
        data["last_refresh_at"] = _max_iso(
            data.get("last_refresh_at"),
            overlay_state.get("last_overlay_refresh_at"),
            overlay_state.get("cycle_completed_at"),
        )
        data["overlay"] = {
            "schema_version": OVERLAY_SCHEMA_VERSION,
            "record_count": len(overlay_records),
            "path": str(self._overlay_path_for(source_kind)),
            "state_path": str(self._overlay_state_path_for(source_kind)),
            "state": overlay_state,
        }
        return data

    def load(self, source_kind: str) -> dict:
        path = self._path_for(source_kind)
        if not path.exists():
            return self._merge_overlay_records(source_kind, {
                "schema_version": SCHEMA_VERSION,
                "source_kind": source_kind,
                "records": [],
                "model": self.model,
                "dims": None,
                "schema_hash": None,
                "last_refresh_at": None,
            })
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        data.setdefault("records", [])
        data.setdefault("source_kind", source_kind)
        data.setdefault("schema_version", SCHEMA_VERSION)
        return self._merge_overlay_records(source_kind, data)

    def save(self, source_kind: str, data: dict) -> None:
        _atomic_write_json(self._path_for(source_kind), data)
        self._clear_overlay(source_kind)

    @staticmethod
    def _composite(record_id: str, facet: str) -> str:
        return f"{record_id}::{facet}"

    def _embed_single_with_length_fallback(self, text: str) -> list[float]:
        budgets = [
            (MAX_EMBED_TEXT_CHARS, MAX_EMBED_TEXT_WORDS),
            (4500, 900),
            (3000, 600),
            (2000, 400),
            (1200, 250),
        ]
        last_exc: Exception | None = None
        for max_chars, max_words in budgets:
            prepared, _ = _prepare_embedding_text(text, max_chars=max_chars, max_words=max_words)
            try:
                vectors = self.embed_fn([prepared]) if prepared else []
            except RuntimeError as exc:
                if _is_length_error(exc):
                    last_exc = exc
                    continue
                raise
            if len(vectors) != 1:
                raise RuntimeError(
                    f"embed provider returned {len(vectors)} vectors for 1 input "
                    f"(prepared_chars={len(prepared)})"
                )
            return list(vectors[0])
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("embedding provider rejected the text after fallback clipping")

    def _embed_text_batch(self, texts: Sequence[str], *, source_kind: str) -> list[list[float]]:
        if not texts:
            return []
        try:
            vectors = self.embed_fn(list(texts))
        except RuntimeError as exc:
            if not _is_length_error(exc):
                raise
            return [self._embed_single_with_length_fallback(text) for text in texts]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"embed provider returned {len(vectors)} vectors for {len(texts)} inputs "
                f"(source_kind={source_kind})"
            )
        return vectors

    # ---------- refresh ----------

    def refresh(
        self,
        adapter: SourceAdapter,
        *,
        force: bool = False,
        limit: int | None = None,
        missing_only: bool = False,
        progress: Callable[[str], None] | None = None,
        overlay_if_large: bool = False,
        preferred_item_ids: Sequence[str] | None = None,
    ) -> dict:
        """Embed any row whose content hash changed and prune rows no longer emitted by the adapter."""
        source_kind = adapter.source_kind
        if overlay_if_large and self._should_use_overlay_refresh(source_kind, limit=limit):
            return self._refresh_limited_overlay(
                adapter,
                force=force,
                limit=limit,
                missing_only=missing_only,
                progress=progress,
                preferred_item_ids=preferred_item_ids,
            )
        data = self.load(source_kind)
        schema_hash = adapter.schema_hash()
        text_version = getattr(adapter, "text_version", None)

        existing: dict[str, dict] = {
            self._composite(r["id"], r.get("facet", FACET_BODY)): r
            for r in data.get("records", [])
        }
        schema_drifted = force or _drift_between(
            schema_hash,
            text_version,
            data.get("schema_hash"),
            data.get("text_version"),
        )
        if data.get("schema_version") != SCHEMA_VERSION:
            schema_drifted = True

        queued: list[tuple[str, str, FacetedItem, str, str, bool]] = []
        # (item_id, facet, item, original_text, embedding_text, truncated)
        kept: dict[str, dict] = {}
        seen_ids: set[str] = set()
        seen_keys: set[str] = set()

        for item in adapter.iter_items():
            if limit is not None and len(seen_ids) >= limit:
                break
            seen_ids.add(item.id)
            for facet, text in item.non_empty_facets().items():
                key = self._composite(item.id, facet)
                seen_keys.add(key)
                content_hash = _sha256_text(text)
                existing_rec = existing.get(key)
                needs_embed = (
                    schema_drifted
                    or force
                    or existing_rec is None
                    or existing_rec.get("content_hash") != content_hash
                    or (self.model and existing_rec.get("model") != self.model)
                )
                if missing_only and existing_rec is not None:
                    needs_embed = False
                if needs_embed:
                    embed_text, truncated = _prepare_embedding_text(text)
                    queued.append((item.id, facet, item, text, embed_text, truncated))
                else:
                    kept[key] = existing_rec

        # When limit or missing-only is applied, retain unrelated rows untouched.
        if limit is not None or missing_only:
            for key, rec in existing.items():
                if key not in seen_keys and key not in kept:
                    kept[key] = rec

        embedded = 0
        dims = data.get("dims")
        now = _now_iso()

        for batch_start in range(0, len(queued), self.batch_size):
            batch = queued[batch_start : batch_start + self.batch_size]
            texts = [embed_text for _, _, _, _, embed_text, _ in batch]
            if progress:
                progress(
                    f"embedding batch {batch_start // self.batch_size + 1} / "
                    f"{(len(queued) + self.batch_size - 1) // self.batch_size} "
                    f"({len(batch)} facets, kind={source_kind})"
                )
            vectors = self._embed_text_batch(texts, source_kind=source_kind)
            for (rec_id, facet, item, text, embed_text, truncated), vec in zip(batch, vectors):
                dims = dims or len(vec)
                key = self._composite(rec_id, facet)
                metadata = dict(item.metadata)
                if truncated:
                    metadata["embedding_text_truncated"] = True
                rec = EmbeddingRecord(
                    id=rec_id,
                    facet=facet,
                    source_kind=source_kind,
                    source_path=item.source_path,
                    content_hash=_sha256_text(text),
                    text_preview=embed_text[:400],
                    metadata=metadata,
                    vector=list(vec),
                    model=self.model or _infer_model_from_env(),
                    dims=len(vec),
                    updated_at=now,
                )
                kept[key] = rec.as_dict()
                embedded += 1

        data["records"] = sorted(kept.values(), key=lambda r: (r["id"], r.get("facet", FACET_BODY)))
        data["model"] = self.model or _infer_model_from_env()
        data["dims"] = dims
        data["schema_hash"] = schema_hash
        data["text_version"] = text_version
        data["last_refresh_at"] = now
        data["schema_version"] = SCHEMA_VERSION
        self.save(source_kind, data)

        removed = 0 if missing_only else len(set(existing.keys()) - seen_keys) if limit is None else 0
        facets_seen = sorted({r.get("facet", FACET_BODY) for r in kept.values()})
        return {
            "source_kind": source_kind,
            "embedded": embedded,
            "kept": len(kept) - embedded,
            "removed": removed,
            "total_records": len(kept),
            "distinct_ids": len(seen_ids) if seen_ids else len({r["id"] for r in kept.values()}),
            "facets_seen": facets_seen,
            "dims": dims,
            "schema_hash": schema_hash,
            "text_version": text_version,
            "missing_only": bool(missing_only),
        }

    def _refresh_limited_overlay(
        self,
        adapter: SourceAdapter,
        *,
        force: bool = False,
        limit: int | None = None,
        missing_only: bool = False,
        progress: Callable[[str], None] | None = None,
        preferred_item_ids: Sequence[str] | None = None,
    ) -> dict:
        """Refresh a bounded window into an overlay instead of rewriting a huge base cache."""
        source_kind = adapter.source_kind
        limit_value = max(1, int(limit or 1))
        items = list(adapter.iter_items())
        total_items = len(items)
        state = self._load_overlay_state(source_kind)
        offset = int(state.get("next_item_offset") or 0)
        if offset >= total_items:
            offset = 0
        preferred_ids = [str(item_id) for item_id in (preferred_item_ids or []) if str(item_id or "").strip()]
        selection_mode = "cursor"
        if preferred_ids:
            by_id = {item.id: item for item in items}
            window = [by_id[item_id] for item_id in preferred_ids if item_id in by_id][:limit_value]
            if window:
                selection_mode = "preferred_ids"
                next_offset = offset
                cycle_complete = bool(state.get("cycle_complete")) if state else False
            else:
                window = items[offset : offset + limit_value]
                next_offset = offset + len(window)
                cycle_complete = total_items == 0 or next_offset >= total_items
                if cycle_complete:
                    next_offset = 0
        else:
            window = items[offset : offset + limit_value]
            next_offset = offset + len(window)
            cycle_complete = total_items == 0 or next_offset >= total_items
            if cycle_complete:
                next_offset = 0

        schema_hash = adapter.schema_hash()
        text_version = getattr(adapter, "text_version", None)
        schema_drifted = force or _drift_between(
            schema_hash,
            text_version,
            state.get("schema_hash"),
            state.get("text_version"),
        )
        overlay_index = self._overlay_records_by_key(source_kind)

        queued: list[tuple[str, str, FacetedItem, str, str, bool]] = []
        kept = 0
        seen_keys: set[str] = set()
        facets_seen: set[str] = set()
        model = self.model or _infer_model_from_env()

        for item in window:
            for facet, text in item.non_empty_facets().items():
                facets_seen.add(facet)
                key = self._composite(item.id, facet)
                seen_keys.add(key)
                content_hash = _sha256_text(text)
                existing_rec = overlay_index.get(key)
                needs_embed = (
                    schema_drifted
                    or force
                    or existing_rec is None
                    or existing_rec.get("content_hash") != content_hash
                    or (self.model and existing_rec.get("model") != self.model)
                )
                if missing_only and existing_rec is not None:
                    needs_embed = False
                if needs_embed:
                    embed_text, truncated = _prepare_embedding_text(text)
                    queued.append((item.id, facet, item, text, embed_text, truncated))
                else:
                    kept += 1

        embedded = 0
        dims = int(state.get("dims") or 0) or None
        now = _now_iso()
        appended_records: list[dict[str, Any]] = []

        for batch_start in range(0, len(queued), self.batch_size):
            batch = queued[batch_start : batch_start + self.batch_size]
            texts = [embed_text for _, _, _, _, embed_text, _ in batch]
            if progress:
                progress(
                    f"embedding overlay batch {batch_start // self.batch_size + 1} / "
                    f"{(len(queued) + self.batch_size - 1) // self.batch_size} "
                    f"({len(batch)} facets, kind={source_kind})"
                )
            vectors = self._embed_text_batch(texts, source_kind=source_kind)
            for (rec_id, facet, item, text, embed_text, truncated), vec in zip(batch, vectors):
                dims = dims or len(vec)
                key = self._composite(rec_id, facet)
                metadata = dict(item.metadata)
                if truncated:
                    metadata["embedding_text_truncated"] = True
                metadata["embedding_overlay"] = True
                metadata["embedding_overlay_batch_offset"] = offset
                metadata["embedding_overlay_selection_mode"] = selection_mode
                rec = EmbeddingRecord(
                    id=rec_id,
                    facet=facet,
                    source_kind=source_kind,
                    source_path=item.source_path,
                    content_hash=_sha256_text(text),
                    text_preview=embed_text[:400],
                    metadata=metadata,
                    vector=list(vec),
                    model=model,
                    dims=len(vec),
                    updated_at=now,
                )
                raw = rec.as_dict()
                appended_records.append(raw)
                overlay_index[key] = raw
                embedded += 1

        self._append_overlay_records(source_kind, appended_records)

        previous_progress = int(state.get("cycle_progress_items") or 0)
        if offset == 0:
            previous_progress = 0
        if selection_mode == "preferred_ids":
            cycle_progress_items = previous_progress
            cycle_started_at = state.get("cycle_started_at") or now
        else:
            cycle_progress_items = total_items if cycle_complete else min(total_items, previous_progress + len(window))
            cycle_started_at = state.get("cycle_started_at") if offset != 0 else now
        overlay_state = {
            "schema_version": OVERLAY_SCHEMA_VERSION,
            "source_kind": source_kind,
            "updated_at": now,
            "last_overlay_refresh_at": now,
            "cycle_started_at": cycle_started_at,
            "cycle_completed_at": now if cycle_complete else state.get("cycle_completed_at"),
            "cycle_complete": cycle_complete,
            "cycle_progress_items": cycle_progress_items,
            "total_items_seen": total_items,
            "last_window_offset": offset,
            "last_window_item_count": len(window),
            "last_selection_mode": selection_mode,
            "last_preferred_item_ids": [item.id for item in window] if selection_mode == "preferred_ids" else [],
            "next_item_offset": next_offset,
            "overlay_record_count": len(overlay_index),
            "base_cache_size_bytes": self._primary_cache_size_bytes(source_kind),
            "model": model,
            "dims": dims,
            "schema_hash": schema_hash,
            "text_version": text_version,
        }
        self._write_overlay_state(source_kind, overlay_state)

        return {
            "source_kind": source_kind,
            "storage_mode": "overlay",
            "embedded": embedded,
            "kept": kept,
            "removed": 0,
            "total_records": len(overlay_index),
            "distinct_ids": len(window),
            "source_total_ids": total_items,
            "facets_seen": sorted(facets_seen),
            "dims": dims,
            "schema_hash": schema_hash,
            "text_version": text_version,
            "overlay_path": str(self._overlay_path_for(source_kind)),
            "overlay_state_path": str(self._overlay_state_path_for(source_kind)),
            "base_cache_size_bytes": self._primary_cache_size_bytes(source_kind),
            "window_offset": offset,
            "next_item_offset": next_offset,
            "cycle_complete": cycle_complete,
            "cycle_progress_items": cycle_progress_items,
            "selection_mode": selection_mode,
            "missing_only": bool(missing_only),
            "preferred_item_ids_requested": preferred_ids[:limit_value],
            "processed_ids_preview": [item.id for item in window[:10]],
        }

    # ---------- search ----------

    def search(
        self,
        query: str,
        *,
        source_kinds: Sequence[str] | None = None,
        facets: Sequence[str] | None = None,
        top_k: int = 10,
        metadata_filter: Mapping[str, Any] | None = None,
        candidate_ids: set[str] | None = None,
    ) -> list[SearchHit]:
        if source_kinds is None:
            source_kinds = self.list_source_kinds()
        if not source_kinds:
            return []

        query_text, _ = _prepare_embedding_text(query)
        vectors = self._embed_text_batch([query_text], source_kind="query")
        if not vectors:
            return []
        qvec = vectors[0]

        hits: list[SearchHit] = []
        for kind in source_kinds:
            data = self.load(kind)
            for raw in data.get("records", []):
                if facets and raw.get("facet", FACET_BODY) not in facets:
                    continue
                if candidate_ids is not None and raw["id"] not in candidate_ids:
                    continue
                if metadata_filter and not _match_metadata(raw.get("metadata", {}), metadata_filter):
                    continue
                score = _cosine(qvec, raw.get("vector", []))
                rec = EmbeddingRecord(
                    id=raw["id"],
                    facet=raw.get("facet", FACET_BODY),
                    source_kind=raw.get("source_kind", kind),
                    source_path=raw.get("source_path", ""),
                    content_hash=raw.get("content_hash", ""),
                    text_preview=raw.get("text_preview", ""),
                    metadata=raw.get("metadata", {}),
                    vector=raw.get("vector", []),
                    model=raw.get("model", ""),
                    dims=raw.get("dims", len(raw.get("vector", []))),
                    updated_at=raw.get("updated_at", ""),
                )
                hits.append(SearchHit(record=rec, score=score))

        hits.sort(key=lambda h: h.score, reverse=True)
        return hits[:top_k]

    def search_ladder(
        self,
        query: str,
        *,
        source_kinds: Sequence[str],
        ladder: Sequence[str],
        k_per_rung: Sequence[int],
        metadata_filter: Mapping[str, Any] | None = None,
    ) -> LadderResult:
        """Activation gradient: score by the cheapest facet first; on each escalation,
        re-score only the survivors against the next facet. The ladder mirrors Will's
        reread-substrate-at-each-compression-level rubric (par_phase_09…source_10_002).
        """
        if len(ladder) != len(k_per_rung):
            raise ValueError("ladder and k_per_rung must be same length")
        candidate_ids: set[str] | None = None
        rung_trace: list[dict] = []
        last_hits: list[SearchHit] = []
        for facet, k in zip(ladder, k_per_rung):
            hits = self.search(
                query,
                source_kinds=source_kinds,
                facets=[facet],
                top_k=k,
                metadata_filter=metadata_filter,
                candidate_ids=candidate_ids,
            )
            rung_trace.append(
                {
                    "facet": facet,
                    "k": k,
                    "hits": [
                        {
                            "id": h.record.id,
                            "score": round(h.score, 6),
                            "source_kind": h.record.source_kind,
                            "preview": h.record.text_preview[:160],
                        }
                        for h in hits
                    ],
                }
            )
            candidate_ids = {h.record.id for h in hits}
            last_hits = hits
            if not candidate_ids:
                break
        return LadderResult(final_hits=last_hits, rung_trace=rung_trace)

    # ---------- alignment ----------

    def alignment(
        self,
        id_a: str,
        id_b: str,
        *,
        source_kinds: Sequence[str] | None = None,
    ) -> list[AlignmentEntry]:
        """Per-facet cosine matrix between two artifacts.

        Use case: cosine(file.purpose, paper_module.tldr) reveals whether the
        documentation actually describes the code. Low same-axis scores between
        like-named facets are a drift alarm; high cross-axis scores can reveal
        unexpected structural alignment.
        """
        kinds = source_kinds or self.list_source_kinds()
        rows_a = self._gather_records(id_a, kinds)
        rows_b = self._gather_records(id_b, kinds)
        if not rows_a or not rows_b:
            return []
        out: list[AlignmentEntry] = []
        for ra in rows_a:
            for rb in rows_b:
                fa, fb = ra.get("facet", FACET_BODY), rb.get("facet", FACET_BODY)
                score = _cosine(ra.get("vector", []), rb.get("vector", []))
                out.append(AlignmentEntry(facet_a=fa, facet_b=fb, score=score, same_axis=fa == fb))
        out.sort(key=lambda e: e.score, reverse=True)
        return out

    def _gather_records(self, record_id: str, kinds: Sequence[str]) -> list[dict]:
        out = []
        for kind in kinds:
            data = self.load(kind)
            for raw in data.get("records", []):
                if raw.get("id") == record_id:
                    out.append(raw)
        return out

    # ---------- status ----------

    def list_source_kinds(self) -> list[str]:
        if not self.state_root.exists():
            return []
        return sorted(p.stem for p in self.state_root.glob("*.json") if p.is_file())

    def status(
        self,
        adapter: SourceAdapter | None = None,
        *,
        source_kind: str | None = None,
        fast: bool = False,
        stale_preview_limit: int = 10,
    ) -> SubstrateStatus:
        kind = adapter.source_kind if adapter else source_kind
        if kind is None:
            raise ValueError("status requires adapter or source_kind")
        data = self.load(kind)
        records = data.get("records", [])
        existing: dict[str, dict] = {
            self._composite(r["id"], r.get("facet", FACET_BODY)): r for r in records
        }
        stale = 0
        expected_row_count: int | None = None
        stale_reason_counts: Counter[str] = Counter()
        preview_limit = max(0, int(stale_preview_limit))
        stale_preview: list[dict[str, str]] = []
        stale_preview_truncated = False

        def _add_stale_preview(
            *,
            reason: str,
            item_id: str,
            facet: str,
            source_path: str = "",
            record_hash: str = "",
            current_hash: str = "",
        ) -> None:
            nonlocal stale_preview_truncated
            if len(stale_preview) >= preview_limit:
                stale_preview_truncated = True
                return
            row = {
                "reason": reason,
                "id": str(item_id),
                "facet": str(facet),
            }
            if source_path:
                row["source_path"] = str(source_path)
            if record_hash:
                row["record_hash"] = str(record_hash)
            if current_hash:
                row["current_hash"] = str(current_hash)
            stale_preview.append(row)

        if adapter is not None:
            if fast and not records:
                return SubstrateStatus(
                    source_kind=kind,
                    record_count=0,
                    facet_count=0,
                    distinct_ids=0,
                    model=data.get("model") or "",
                    dims=data.get("dims") or 0,
                    schema_hash=data.get("schema_hash"),
                    last_refresh_at=data.get("last_refresh_at"),
                    stale_or_missing=1,
                    path=str(self._path_for(kind)),
                    stale_preview=[
                        {
                            "reason": "cache_missing_or_empty_fast_estimate",
                            "id": "*",
                            "facet": "*",
                        }
                    ][:preview_limit],
                    stale_preview_truncated=False,
                    stale_or_missing_is_estimate=True,
                    text_version=data.get("text_version"),
                    expected_row_count=None,
                    stale_reason_counts={"cache_missing_or_empty_fast_estimate": 1},
                )
            schema_now = adapter.schema_hash()
            text_version_now = getattr(adapter, "text_version", None)
            schema_drifted = _drift_between(
                schema_now,
                text_version_now,
                data.get("schema_hash"),
                data.get("text_version"),
            )
            seen_keys: set[str] = set()
            expected_row_count = 0
            for item in adapter.iter_items():
                for facet, text in item.non_empty_facets().items():
                    expected_row_count += 1
                    key = self._composite(item.id, facet)
                    seen_keys.add(key)
                    rec = existing.get(key)
                    current_hash = _sha256_text(text)
                    if rec is None:
                        stale += 1
                        stale_reason_counts["missing"] += 1
                        _add_stale_preview(
                            reason="missing",
                            item_id=item.id,
                            facet=facet,
                            source_path=item.source_path,
                            current_hash=current_hash,
                        )
                    elif rec.get("content_hash") != current_hash:
                        stale += 1
                        stale_reason_counts["hash_changed"] += 1
                        _add_stale_preview(
                            reason="hash_changed",
                            item_id=item.id,
                            facet=facet,
                            source_path=item.source_path,
                            record_hash=str(rec.get("content_hash") or ""),
                            current_hash=current_hash,
                        )
                    elif schema_drifted:
                        stale += 1
                        stale_reason_counts["schema_changed"] += 1
                        _add_stale_preview(
                            reason="schema_changed",
                            item_id=item.id,
                            facet=facet,
                            source_path=item.source_path,
                            record_hash=str(rec.get("content_hash") or ""),
                            current_hash=current_hash,
                        )
            # pattern: staleness-gated graph rehydration, inspired by understand-anything:p004.
            removed_keys = set(existing.keys()) - seen_keys
            stale += len(removed_keys)
            if removed_keys:
                stale_reason_counts["removed"] += len(removed_keys)
            for key in sorted(removed_keys):
                rec = existing.get(key) or {}
                _add_stale_preview(
                    reason="removed",
                    item_id=str(rec.get("id") or key.rsplit("::", 1)[0]),
                    facet=str(rec.get("facet") or FACET_BODY),
                    source_path=str(rec.get("source_path") or ""),
                    record_hash=str(rec.get("content_hash") or ""),
                )
        facets = sorted({r.get("facet", FACET_BODY) for r in records})
        distinct_ids = len({r["id"] for r in records})
        return SubstrateStatus(
            source_kind=kind,
            record_count=len(records),
            facet_count=len(facets),
            distinct_ids=distinct_ids,
            model=data.get("model") or "",
            dims=data.get("dims") or 0,
            schema_hash=data.get("schema_hash"),
            last_refresh_at=data.get("last_refresh_at"),
            stale_or_missing=stale,
            path=str(self._path_for(kind)),
            stale_preview=stale_preview,
            stale_preview_truncated=stale_preview_truncated,
            text_version=data.get("text_version"),
            expected_row_count=expected_row_count,
            stale_reason_counts=dict(stale_reason_counts),
        )


def _infer_model_from_env() -> str:
    from system.lib import nvidia_nim as _nim

    return os.environ.get("NVIDIA_EMBED_MODEL", _nim.DEFAULT_EMBED_MODEL)


def _match_metadata(metadata: Mapping[str, Any], required: Mapping[str, Any]) -> bool:
    for key, expected in required.items():
        actual = metadata.get(key)
        if isinstance(expected, (list, tuple, set)):
            if actual not in expected:
                return False
        elif actual != expected:
            return False
    return True
