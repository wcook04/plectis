"""Annex routing coverage audit for annex_patterns cluster quality.

Clusterability answers whether a high-cardinality surface can expose a bounded
contents page. This audit answers whether the selected annex_patterns cluster
key is semantically covered well enough, especially how much falls back to the
explicit ``unrouted`` bucket.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping


ANNEX_ROOT = Path("annexes")
ANNEX_CATALOG = ANNEX_ROOT / "annex_catalog.json"
ANNEX_NOTES_FILE_NAME = "annex_notes.json"
ANNEX_FAMILY_FILE_NAME = "annex_family.json"
ANNEX_CATALOG_STANDARD = Path("codex/standards/annex/std_annex_catalog.json")
ANNEX_ROUTING_VOCABULARY = Path("codex/standards/annex/annex_routing_vocabulary.json")
DEFAULT_UNROUTED_RATE_THRESHOLD = 0.10


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _relative(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _routing_list(value: Any) -> list[str]:
    return [str(item) for item in value if str(item).strip()] if isinstance(value, list) else []


def _catalog_by_slug(root: Path) -> dict[str, dict[str, Any]]:
    payload = _load_json(root / ANNEX_CATALOG)
    rows = payload.get("annexes")
    if not isinstance(rows, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        slug = str(row.get("slug") or "").strip()
        if slug:
            out[slug] = row
    return out


def _notes_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    annex_root = root / ANNEX_ROOT
    if not annex_root.exists():
        return entries
    for notes_path in sorted(annex_root.glob(f"*/{ANNEX_NOTES_FILE_NAME}")):
        payload = _load_json(notes_path)
        slug = str(payload.get("slug") or notes_path.parent.name).strip()
        notes = payload.get("notes")
        if not slug or not isinstance(notes, list):
            continue
        for note in notes:
            if not isinstance(note, dict):
                continue
            note_id = str(note.get("id") or "").strip()
            if not note_id:
                continue
            entries.append(
                {
                    "annex_slug": slug,
                    "note_id": note_id,
                    "notes_path": notes_path,
                }
            )
    return entries


def _catalog_routing(row: Mapping[str, Any] | None) -> Mapping[str, Any]:
    routing = row.get("routing_summary") if isinstance(row, Mapping) else {}
    return routing if isinstance(routing, Mapping) else {}


def _cluster_key(row: Mapping[str, Any] | None) -> str:
    routing = _catalog_routing(row)
    problem_spaces = _routing_list(routing.get("problem_spaces"))
    return problem_spaces[0] if problem_spaces else "unrouted"


def _source_kind(row: Mapping[str, Any] | None) -> str:
    return str(row.get("source_kind") or "unknown") if isinstance(row, Mapping) else "unknown"


def _repair_files(root: Path, slug: str) -> list[str]:
    annex_dir = root / ANNEX_ROOT / slug
    return [
        _relative(annex_dir / ANNEX_FAMILY_FILE_NAME, root),
        _relative(annex_dir / ANNEX_NOTES_FILE_NAME, root),
    ]


def build_annex_routing_coverage(
    repo_root: Path | str,
    *,
    context_budget: int = 12000,
    unrouted_rate_threshold: float = DEFAULT_UNROUTED_RATE_THRESHOLD,
    top_limit: int = 12,
) -> dict[str, Any]:
    root = Path(repo_root)
    budget = max(1000, int(context_budget or 12000))
    threshold = max(0.0, min(float(unrouted_rate_threshold), 1.0))
    catalog = _catalog_by_slug(root)
    entries = _notes_entries(root)

    cluster_counts: Counter[str] = Counter()
    unrouted_by_slug: Counter[str] = Counter()
    unrouted_source_kinds: Counter[str] = Counter()
    rows_by_slug: Counter[str] = Counter()
    missing_catalog_slugs: set[str] = set()

    for entry in entries:
        slug = str(entry.get("annex_slug") or "")
        rows_by_slug[slug] += 1
        catalog_row = catalog.get(slug)
        if catalog_row is None:
            missing_catalog_slugs.add(slug)
        key = _cluster_key(catalog_row)
        cluster_counts[key] += 1
        if key == "unrouted":
            unrouted_by_slug[slug] += 1
            unrouted_source_kinds[_source_kind(catalog_row)] += 1

    total_rows = len(entries)
    unrouted_rows = cluster_counts.get("unrouted", 0)
    routed_rows = max(0, total_rows - unrouted_rows)
    unrouted_rate = (unrouted_rows / total_rows) if total_rows else 0.0
    status = "debt" if unrouted_rate > threshold else "acceptable"

    largest_clusters = [
        {"cluster_id": cluster_id, "count": count}
        for cluster_id, count in cluster_counts.most_common(top_limit)
    ]
    largest_unrouted_annexes = []
    for slug, count in unrouted_by_slug.most_common(top_limit):
        row = catalog.get(slug)
        largest_unrouted_annexes.append(
            {
                "annex_slug": slug,
                "unrouted_rows": count,
                "total_rows": rows_by_slug.get(slug, count),
                "source_kind": _source_kind(row),
                "candidate_repair_files": _repair_files(root, slug),
            }
        )

    missing_problem_space_by_annex_slug = [
        {
            "annex_slug": slug,
            "missing_problem_space_rows": count,
            "candidate_repair_files": _repair_files(root, slug),
        }
        for slug, count in unrouted_by_slug.most_common(top_limit)
    ]

    debt_rows: list[dict[str, Any]] = []
    if status == "debt":
        debt_rows.append(
            {
                "debt_id": "routing_coverage:annex_patterns:unrouted",
                "debt_class": "routing_coverage_debt",
                "priority": 82,
                "title": "annex_patterns cluster key has too many unrouted rows",
                "evidence": (
                    f"unrouted_rows={unrouted_rows}; total_rows={total_rows}; "
                    f"unrouted_rate={unrouted_rate:.3f}; threshold={threshold:.3f}"
                ),
                "repair_class": "annex_routing_metadata_population",
                "artifact_kind": "annex_patterns",
                "target_files": [
                    "codex/standards/annex/std_annex_catalog.json",
                    "codex/standards/annex/annex_routing_vocabulary.json",
                    *[
                        path
                        for item in largest_unrouted_annexes[:5]
                        for path in item.get("candidate_repair_files", [])
                    ],
                ],
                "tests": [
                    "annex routing coverage reports unrouted_rate below threshold",
                    "annex_patterns.cluster_flag keeps the unrouted bucket visible until repaired",
                ],
                "source_surface": "--annex-routing-coverage",
                "safe_alternative": "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            }
        )

    return {
        "kind": "annex_routing_coverage",
        "schema_version": "annex_routing_coverage_v0",
        "generated_at": _utc_now(),
        "budget": {
            "context_budget_tokens": budget,
            "unrouted_rate_threshold": threshold,
        },
        "summary": {
            "total_annex_pattern_rows": total_rows,
            "clustered_rows": routed_rows,
            "routed_rows": routed_rows,
            "unrouted_rows": unrouted_rows,
            "unrouted_rate": round(unrouted_rate, 4),
            "coverage_status": status,
            "problem_space_cluster_count": len(cluster_counts),
            "unrouted_annex_count": len(unrouted_by_slug),
            "missing_catalog_slug_count": len(missing_catalog_slugs),
            "debt_count": len(debt_rows),
        },
        "cluster_key": {
            "field": "annex_pattern_cluster_key",
            "source": "annexes/annex_catalog.json::annexes[].routing_summary.problem_spaces[0]",
            "fallback": "unrouted",
            "standard_ref": str(ANNEX_CATALOG_STANDARD),
            "routing_vocabulary_ref": str(ANNEX_ROUTING_VOCABULARY),
        },
        "largest_clusters": largest_clusters,
        "source_kind_counts_for_unrouted": dict(sorted(unrouted_source_kinds.items())),
        "largest_unrouted_annexes": largest_unrouted_annexes,
        "missing_problem_space_by_annex_slug": missing_problem_space_by_annex_slug,
        "candidate_repair_files": sorted(
            {
                path
                for item in largest_unrouted_annexes
                for path in item.get("candidate_repair_files", [])
            }
        )[: top_limit * 2],
        "debt_rows": debt_rows,
        "next_commands": [
            "./repo-python kernel.py --option-surface annex_patterns --band cluster_flag",
            "./repo-python kernel.py --navigation-metabolism \"annex routing coverage\" --metabolism-profile full --context-budget 12000",
        ],
        "source_surfaces": [
            str(ANNEX_CATALOG),
            str(ANNEX_CATALOG_STANDARD),
            str(ANNEX_ROUTING_VOCABULARY),
            "annexes/*/annex_family.json",
            "annexes/*/annex_notes.json",
        ],
    }
