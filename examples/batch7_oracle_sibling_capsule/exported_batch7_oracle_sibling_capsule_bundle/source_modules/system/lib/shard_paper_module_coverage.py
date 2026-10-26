"""

[PURPOSE]
- Teleology: Build and read the shard-to-paper-module coverage sidecar so raw-seed shards are interpreted against the paper-module subsystem space before they are compressed or routed.
- Mechanism: Reuse existing `raw_seed_shards` clarified embeddings and paper-module TLDR embeddings, compute cosine top-k matches locally, write a generated sidecar, and expose a compact cross-section helper for shard packets.

[INTERFACE]
- Exports: `build_shard_paper_module_coverage`, `load_shard_paper_module_coverage`, `paper_module_cross_section_for_shards`, `default_sidecar_path`.
- Reads: `state/embeddings/raw_seed_shards.json`, `state/embeddings/paper_modules.json`, and `codex/doctrine/paper_modules/_index.json`.
- Writes: `codex/hologram/raw_seed_projection/shard_paper_module_coverage.json` when the builder is called with `write=True`.

[FLOW]
- Load clarified shard vectors and paper-module TLDR vectors -> normalize in numpy -> compute shard x module cosine -> persist top module candidates and module rollups -> shard packets aggregate the selected shard ids into a module cross-section.
- When-needed: Open when shard navigation needs subsystem context before route-review, paper-module refresh, or shard synthesis.
- Escalates-to: system/lib/embedding_substrate.py; system/lib/shard_browser.py.

[DEPENDENCIES]
- Couples: NumPy is loaded for vector normalization and cosine top-k computation; cached embeddings and the paper-module index supply shard/module identities.

[CONSTRAINTS]
- Guarantee: Uses only cached embeddings; it does not call NVIDIA or bridge.
- Non-goal: Does not mutate shard rows, paper modules, doctrine nodes, or routing decisions. Scores are triage hints, not apply authority.

"""
from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_VERSION = "shard_paper_module_coverage_v1"
CROSS_SECTION_SCHEMA_VERSION = "shard_paper_module_cross_section_v1"
DEFAULT_TOP_K = 3
DEFAULT_SIDECAR_RELATIVE_PATH = Path("codex/hologram/raw_seed_projection/shard_paper_module_coverage.json")
SHARD_EMBEDDINGS_RELATIVE_PATH = Path("state/embeddings/raw_seed_shards.json")
PAPER_MODULE_EMBEDDINGS_RELATIVE_PATH = Path("state/embeddings/paper_modules.json")
PAPER_MODULE_INDEX_RELATIVE_PATH = Path("codex/doctrine/paper_modules/_index.json")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _atomic_write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(obj, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _rel(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.relative_to(repo_root))
    except ValueError:
        return str(path)


def default_sidecar_path(repo_root: Path = REPO_ROOT) -> Path:
    return Path(repo_root) / DEFAULT_SIDECAR_RELATIVE_PATH


def _module_metadata(repo_root: Path) -> dict[str, dict[str, Any]]:
    index = _load_json(repo_root / PAPER_MODULE_INDEX_RELATIVE_PATH)
    modules = index.get("modules") if isinstance(index.get("modules"), list) else []
    out: dict[str, dict[str, Any]] = {}
    for module in modules:
        if not isinstance(module, Mapping):
            continue
        slug = str(module.get("slug") or "").strip()
        if not slug:
            continue
        out[slug] = {
            "slug": slug,
            "title": str(module.get("title") or slug).strip(),
            "file": str(module.get("file") or "").strip(),
            "status": str(module.get("status") or "").strip(),
            "recommended_action": str(module.get("recommended_action") or "").strip(),
        }
    return out


def _records_by_facet(path: Path, facet: str) -> list[dict[str, Any]]:
    payload = _load_json(path)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in payload.get("records") or []:
        if not isinstance(row, Mapping):
            continue
        row_id = str(row.get("id") or "").strip()
        if not row_id or row_id in seen or row.get("facet") != facet:
            continue
        vector = row.get("vector")
        if not isinstance(vector, list) or not vector:
            continue
        seen.add(row_id)
        rows.append(dict(row))
    rows.sort(key=lambda item: str(item.get("id") or ""))
    return rows


def _numpy():
    import numpy as np  # type: ignore

    return np


def _normalized_matrix(records: Sequence[Mapping[str, Any]]) -> Any:
    np = _numpy()
    matrix = np.asarray([row.get("vector") or [] for row in records], dtype=np.float64)
    if matrix.ndim != 2:
        return np.zeros((0, 0), dtype=np.float32)
    np.nan_to_num(matrix, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    valid = norms[:, 0] > 0
    if valid.any():
        matrix[valid] = matrix[valid] / norms[valid]
    if (~valid).any():
        matrix[~valid] = 0
    return matrix.astype(np.float32, copy=False)


def _confidence(score: float, margin: float) -> str:
    if score >= 0.45 and margin >= 0.02:
        return "high"
    if score >= 0.35 and margin >= 0.01:
        return "medium"
    if score >= 0.27:
        return "low"
    return "weak"


def _round_score(value: float) -> float:
    return round(float(value), 6)


def build_shard_paper_module_coverage(
    *,
    repo_root: Path = REPO_ROOT,
    top_k: int = DEFAULT_TOP_K,
    output_path: Path | None = None,
    write: bool = True,
) -> dict[str, Any]:
    """Build the generated shard->paper-module coverage sidecar from cached vectors."""
    repo_root = Path(repo_root)
    output_path = output_path or default_sidecar_path(repo_root)
    top_k = max(1, int(top_k or DEFAULT_TOP_K))

    shard_embedding_path = repo_root / SHARD_EMBEDDINGS_RELATIVE_PATH
    paper_embedding_path = repo_root / PAPER_MODULE_EMBEDDINGS_RELATIVE_PATH
    shard_rows = _records_by_facet(shard_embedding_path, "clarified")
    module_rows = _records_by_facet(paper_embedding_path, "tldr")
    module_meta = _module_metadata(repo_root)

    if not shard_rows or not module_rows:
        payload = {
            "kind": "shard_paper_module_coverage",
            "schema_version": SCHEMA_VERSION,
            "generated_at": _now_iso(),
            "source": {
                "shard_embeddings_path": _rel(shard_embedding_path, repo_root=repo_root),
                "paper_module_embeddings_path": _rel(paper_embedding_path, repo_root=repo_root),
                "paper_module_index_path": str(PAPER_MODULE_INDEX_RELATIVE_PATH),
                "shard_facet": "clarified",
                "paper_module_facet": "tldr",
                "scorer": "cached_nv_embed_cosine",
            },
            "summary": {
                "shard_count": len(shard_rows),
                "paper_module_count": len(module_rows),
                "covered_shard_count": 0,
                "top_k": top_k,
                "confidence_counts": {},
            },
            "paper_modules": {},
            "shards": {},
        }
        if write:
            _atomic_write_json(output_path, payload)
        return payload

    np = _numpy()
    shard_matrix = _normalized_matrix(shard_rows)
    module_matrix = _normalized_matrix(module_rows)
    if shard_matrix.shape[1] != module_matrix.shape[1]:
        raise ValueError(
            f"embedding dimension mismatch: raw_seed_shards={shard_matrix.shape[1]} "
            f"paper_modules={module_matrix.shape[1]}"
        )

    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        scores = shard_matrix @ module_matrix.T
    np.nan_to_num(scores, copy=False, nan=0.0, posinf=0.0, neginf=0.0)
    shard_payload: dict[str, dict[str, Any]] = {}
    module_rollup: dict[str, dict[str, Any]] = {}
    confidence_counts: dict[str, int] = {}
    total_top_score = 0.0
    covered_count = 0

    for shard_index, shard_row in enumerate(shard_rows):
        row_scores = scores[shard_index]
        candidate_count = min(top_k, len(module_rows))
        if candidate_count <= 0:
            continue
        if candidate_count < len(module_rows):
            candidate_indices = np.argpartition(row_scores, -candidate_count)[-candidate_count:]
            ordered_indices = candidate_indices[np.argsort(row_scores[candidate_indices])[::-1]]
        else:
            ordered_indices = np.argsort(row_scores)[::-1]

        top_score = float(row_scores[int(ordered_indices[0])])
        second_score = float(row_scores[int(ordered_indices[1])]) if len(ordered_indices) > 1 else 0.0
        margin = top_score - second_score
        top_confidence = _confidence(top_score, margin)
        confidence_counts[top_confidence] = confidence_counts.get(top_confidence, 0) + 1
        total_top_score += top_score
        covered_count += 1

        top_modules: list[dict[str, Any]] = []
        for rank, module_index in enumerate(ordered_indices, start=1):
            module_row = module_rows[int(module_index)]
            slug = str(module_row.get("id") or "").strip()
            meta = module_meta.get(slug, {"slug": slug, "title": slug, "file": str(module_row.get("source_path") or "")})
            score = float(row_scores[int(module_index)])
            row_confidence = top_confidence if rank == 1 else _confidence(score, 0.0)
            top_modules.append(
                {
                    "rank": rank,
                    "slug": slug,
                    "title": meta.get("title") or slug,
                    "file": meta.get("file") or str(module_row.get("source_path") or ""),
                    "score": _round_score(score),
                    "confidence": row_confidence,
                    "facet": "tldr",
                }
            )
            rollup = module_rollup.setdefault(
                slug,
                {
                    "slug": slug,
                    "title": meta.get("title") or slug,
                    "file": meta.get("file") or str(module_row.get("source_path") or ""),
                    "status": meta.get("status") or "",
                    "recommended_action": meta.get("recommended_action") or "",
                    "top1_shard_count": 0,
                    "confidence_counts": {},
                    "top_shards": [],
                },
            )
            if rank == 1:
                rollup["top1_shard_count"] = int(rollup.get("top1_shard_count") or 0) + 1
                counts = rollup.setdefault("confidence_counts", {})
                counts[top_confidence] = int(counts.get(top_confidence) or 0) + 1
                top_shards = rollup.setdefault("top_shards", [])
                top_shards.append(
                    {
                        "shard_id": shard_row.get("id"),
                        "score": _round_score(score),
                        "confidence": top_confidence,
                        "text_preview": str(shard_row.get("text_preview") or "")[:220],
                    }
                )

        shard_payload[str(shard_row.get("id"))] = {
            "shard_id": shard_row.get("id"),
            "source_path": shard_row.get("source_path"),
            "parent_paragraph_id": (shard_row.get("metadata") or {}).get("parent_paragraph_id"),
            "raw_paragraph_ids": (shard_row.get("metadata") or {}).get("raw_paragraph_ids") or [],
            "top_score": _round_score(top_score),
            "top_margin": _round_score(margin),
            "confidence": top_confidence,
            "top_modules": top_modules,
        }

    for rollup in module_rollup.values():
        rollup["top_shards"] = sorted(
            rollup.get("top_shards") or [],
            key=lambda item: (-float(item.get("score") or 0), str(item.get("shard_id") or "")),
        )[:8]

    module_payload = {
        slug: module_rollup[slug]
        for slug in sorted(module_rollup, key=lambda value: (-int(module_rollup[value].get("top1_shard_count") or 0), value))
    }
    payload = {
        "kind": "shard_paper_module_coverage",
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "source": {
            "shard_embeddings_path": _rel(shard_embedding_path, repo_root=repo_root),
            "paper_module_embeddings_path": _rel(paper_embedding_path, repo_root=repo_root),
            "paper_module_index_path": str(PAPER_MODULE_INDEX_RELATIVE_PATH),
            "shard_source_path": str(shard_rows[0].get("source_path") or "") if shard_rows else "",
            "shard_facet": "clarified",
            "paper_module_facet": "tldr",
            "scorer": "cached_nv_embed_cosine",
            "notes": [
                "This sidecar uses cached embeddings only; it does not call NVIDIA or bridge.",
                "Scores identify paper-module context for reading shards, not final routing decisions.",
            ],
        },
        "summary": {
            "shard_count": len(shard_rows),
            "paper_module_count": len(module_rows),
            "covered_shard_count": covered_count,
            "top_k": top_k,
            "confidence_counts": confidence_counts,
            "avg_top_score": _round_score(total_top_score / covered_count) if covered_count else 0.0,
            "module_top1_count": len(module_payload),
        },
        "paper_modules": module_payload,
        "shards": shard_payload,
    }
    if write:
        _atomic_write_json(output_path, payload)
    return payload


def load_shard_paper_module_coverage(
    *,
    repo_root: Path = REPO_ROOT,
    sidecar_path: Path | None = None,
) -> dict[str, Any]:
    path = sidecar_path or default_sidecar_path(repo_root)
    payload = _load_json(Path(path))
    return payload if payload.get("schema_version") == SCHEMA_VERSION else {}


def paper_module_cross_section_for_shards(
    shards: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path = REPO_ROOT,
    sidecar_path: Path | None = None,
    max_modules: int = 6,
    max_examples_per_module: int = 5,
) -> dict[str, Any]:
    """Aggregate sidecar rows for the selected shards into a packet-scale module cross-section."""
    payload = load_shard_paper_module_coverage(repo_root=repo_root, sidecar_path=sidecar_path)
    selected_ids = [
        str(shard.get("id") or shard.get("shard_id") or "").strip()
        for shard in shards
        if str(shard.get("id") or shard.get("shard_id") or "").strip()
    ]
    if not payload:
        return {
            "schema_version": CROSS_SECTION_SCHEMA_VERSION,
            "status": "missing_sidecar",
            "selected_shard_count": len(selected_ids),
            "covered_shard_count": 0,
            "sidecar_path": _rel(sidecar_path or default_sidecar_path(repo_root), repo_root=Path(repo_root)),
            "modules": [],
            "next_command": "./repo-python tools/meta/factory/build_shard_paper_module_coverage.py",
        }

    coverage_rows = payload.get("shards") if isinstance(payload.get("shards"), Mapping) else {}
    module_bins: dict[str, dict[str, Any]] = {}
    covered = 0
    for shard_id in selected_ids:
        coverage = coverage_rows.get(shard_id) if isinstance(coverage_rows, Mapping) else None
        if not isinstance(coverage, Mapping):
            continue
        top_modules = coverage.get("top_modules") if isinstance(coverage.get("top_modules"), list) else []
        if not top_modules:
            continue
        covered += 1
        for candidate in top_modules[:3]:
            if not isinstance(candidate, Mapping):
                continue
            slug = str(candidate.get("slug") or "").strip()
            if not slug:
                continue
            bucket = module_bins.setdefault(
                slug,
                {
                    "slug": slug,
                    "title": candidate.get("title") or slug,
                    "file": candidate.get("file") or "",
                    "candidate_count": 0,
                    "top1_count": 0,
                    "confidence_counts": {},
                    "best_score": 0.0,
                    "example_shards": [],
                },
            )
            bucket["candidate_count"] = int(bucket.get("candidate_count") or 0) + 1
            score = float(candidate.get("score") or 0.0)
            bucket["best_score"] = max(float(bucket.get("best_score") or 0.0), score)
            confidence = str(candidate.get("confidence") or "unknown")
            counts = bucket.setdefault("confidence_counts", {})
            counts[confidence] = int(counts.get(confidence) or 0) + 1
            if int(candidate.get("rank") or 0) == 1:
                bucket["top1_count"] = int(bucket.get("top1_count") or 0) + 1
            examples = bucket.setdefault("example_shards", [])
            if len(examples) < max_examples_per_module:
                examples.append(
                    {
                        "shard_id": shard_id,
                        "rank": candidate.get("rank"),
                        "score": candidate.get("score"),
                        "confidence": confidence,
                    }
                )

    modules = sorted(
        module_bins.values(),
        key=lambda item: (
            -int(item.get("top1_count") or 0),
            -int(item.get("candidate_count") or 0),
            -float(item.get("best_score") or 0.0),
            str(item.get("slug") or ""),
        ),
    )[: max(1, int(max_modules or 1))]
    for module in modules:
        module["best_score"] = _round_score(float(module.get("best_score") or 0.0))

    return {
        "schema_version": CROSS_SECTION_SCHEMA_VERSION,
        "status": "available",
        "selected_shard_count": len(selected_ids),
        "covered_shard_count": covered,
        "sidecar_path": _rel(sidecar_path or default_sidecar_path(repo_root), repo_root=Path(repo_root)),
        "source_generated_at": payload.get("generated_at"),
        "source_shard_facet": ((payload.get("source") or {}).get("shard_facet")),
        "source_paper_module_facet": ((payload.get("source") or {}).get("paper_module_facet")),
        "module_count": len(modules),
        "modules": modules,
        "guardrail": "Read these modules as system context for the selected shards before compressing; scores are context hints, not route-apply decisions.",
    }
