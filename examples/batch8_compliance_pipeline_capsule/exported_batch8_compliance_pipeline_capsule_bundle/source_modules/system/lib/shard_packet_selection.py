"""
[PURPOSE]
- Teleology: Centralize shard-selection, query-summary, group-summary, and
  shard-batch packet parsing so packetization and packet-consuming routing lanes
  share one deterministic contract.
- Mechanism: Reuse `ShardIndex` browse semantics for structural filters and
  ranked query hits, expose compact summary helpers used by shard-batch
  materialization, and validate one bounded `shard_batch_packet` batch file for
  packet-consuming routing flows.
- Non-goal: Mutate shard files, route doctrine proposals, or own CLI surfaces.

[INTERFACE]
- Exports: `build_selection_payload`, `selection_basis`, `filtered_pool`,
  `select_shards`, `query_summary`, `group_summaries`, `state_counts`,
  `shard_group_ids`, and `load_shard_batch_packet`.
- Reads: In-memory `ShardIndex` data plus one `shard_batch_packet` JSON file
  when packet loading is requested.
- Writes: None.

[FLOW]
- Build one selection payload from structural filters / exact shard ids /
  free-text query.
- Resolve the selected shard rows through the shared `ShardIndex`.
- Derive compact query, state, and group summaries for packet manifests; the
  materializer layers richer review-plane/action metadata on top before write.
- Validate one bounded `shard_batch_packet` batch file and expose its batch
  shard ids plus upstream selection metadata for downstream consumers.

[DEPENDENCIES]
- Couples: shard_browser.ShardIndex owns filtering/ranking semantics; shard_batch_packet JSON carries packet-consuming selection evidence.

[CONSTRAINTS]
- Selection order is deterministic: structural filters preserve shard order,
  exact shard ids preserve caller order, and query selection preserves ranked
  `ShardIndex.search()` order.
- Packet loading accepts exactly one `kind: shard_batch_packet` file; manifests
  or unrelated JSON files are rejected.
- This module never infers or materializes routing decisions.
"""
from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
from typing import Any, Mapping

from system.lib.shard_browser import ShardIndex


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


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


def _relative(path: Path, *, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def build_selection_payload(
    *,
    exact_shard_ids: list[str] | None = None,
    status: str | None = None,
    concept: str | None = None,
    mechanism: str | None = None,
    group: str | None = None,
    anchor: str | None = None,
    paragraph: str | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    selection: dict[str, Any] = {}
    if exact_shard_ids:
        selection["shard_ids"] = [str(item).strip() for item in exact_shard_ids if str(item).strip()]
    for key, value in (
        ("status", status),
        ("concept", concept),
        ("mechanism", mechanism),
        ("group", group),
        ("anchor", anchor),
        ("paragraph", paragraph),
        ("query", query),
    ):
        token = _string(value)
        if token:
            selection[key] = token
    return selection


def selection_basis(selection: Mapping[str, Any] | None) -> str:
    selection = selection or {}
    if not selection:
        return "full_index"
    if "shard_ids" in selection and len(selection) == 1:
        return "shard_ids"
    if "shard_ids" in selection:
        return "shard_ids+filters"
    return "filters"


def filtered_pool(
    index: ShardIndex,
    *,
    status: str | None = None,
    concept: str | None = None,
    mechanism: str | None = None,
    group: str | None = None,
    anchor: str | None = None,
    paragraph: str | None = None,
) -> list[dict[str, Any]]:
    return index.list(
        status=status or None,
        concept_id=concept or None,
        mechanism=mechanism or None,
        group=group or None,
        raw_anchor=anchor or None,
        paragraph_id=paragraph or None,
        query=None,
        limit=0,
    )


def select_shards(
    index: ShardIndex,
    *,
    status: str | None = None,
    concept: str | None = None,
    mechanism: str | None = None,
    group: str | None = None,
    anchor: str | None = None,
    paragraph: str | None = None,
    query: str | None = None,
    exact_shard_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    filtered = index.list(
        status=status or None,
        concept_id=concept or None,
        mechanism=mechanism or None,
        group=group or None,
        raw_anchor=anchor or None,
        paragraph_id=paragraph or None,
        query=query or None,
        limit=0,
    )
    if not exact_shard_ids:
        return filtered

    allowed_ids = {str(item.get("id") or "").strip() for item in filtered}
    ordered: list[dict[str, Any]] = []
    seen: set[str] = set()
    for shard_id in exact_shard_ids:
        shard = index.get(shard_id)
        if shard is None:
            continue
        token = _string(shard.get("id"))
        if not token or token in seen or token not in allowed_ids:
            continue
        seen.add(token)
        ordered.append(dict(shard))
    return ordered


def state_counts(shards: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for shard in shards:
        token = _string(shard.get(field))
        if token:
            counts[token] += 1
    return dict(sorted(counts.items(), key=lambda item: (-item[1], item[0])))


def _top_count_rows(
    counter: Counter[str],
    *,
    limit: int = 5,
    label: str = "value",
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]:
        rows.append({label: value, "count": count})
    return rows


def shard_group_ids(shard: Mapping[str, Any]) -> list[str]:
    groups = _string_list(shard.get("idea_group_ids"))
    for field in ("concept_group", "group"):
        token = _string(shard.get(field))
        if token and token not in groups:
            groups.append(token)
    return groups


def group_summaries(shards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for shard in shards:
        for group_id in shard_group_ids(shard):
            groups.setdefault(group_id, []).append(shard)

    summaries: list[dict[str, Any]] = []
    for group_id in sorted(groups):
        members = groups[group_id]
        gesture_counts: Counter[str] = Counter()
        parent_ids: set[str] = set()
        member_ids: list[str] = []
        for shard in members:
            shard_id = _string(shard.get("id"))
            if shard_id:
                member_ids.append(shard_id)
            parent_id = _string(shard.get("parent_paragraph_id"))
            if parent_id:
                parent_ids.add(parent_id)
            for gesture in shard.get("gestures_towards") or []:
                token = _string(gesture)
                if token:
                    gesture_counts[token] += 1
        summaries.append(
            {
                "group_id": group_id,
                "member_count": len(members),
                "representative_shard_ids": sorted(member_ids)[:5],
                "top_gestures_towards": _top_count_rows(gesture_counts, limit=5, label="gesture"),
                "routing_state_counts": state_counts(members, "routing_state"),
                "coverage_state_counts": state_counts(members, "coverage_state"),
                "representative_parent_paragraphs": sorted(parent_ids)[:5],
            }
        )
    return summaries


def query_summary(
    index: ShardIndex,
    *,
    query: str,
    selected_shards: list[dict[str, Any]],
    pool: list[dict[str, Any]],
    related_limit: int,
) -> dict[str, Any]:
    selected_ids = {
        _string(shard.get("id"))
        for shard in selected_shards
        if _string(shard.get("id"))
    }
    payload = index.query_neighborhood(
        query,
        limit=0,
        related_limit=max(0, int(related_limit or 0)),
        pool=pool,
    )
    results = [
        {
            "shard_id": row["shard_id"],
            "score": row["score"],
            "matched_terms": row["matched_terms"],
            "matched_axes": row["matched_axes"],
        }
        for row in payload.get("results") or []
        if row.get("shard_id") in selected_ids
    ]
    return {
        "query": payload["query"],
        "ranking_mode": payload["ranking_mode"],
        "related_limit": max(0, int(related_limit or 0)),
        "matched": len(results),
        "total_query_matches": payload["matched"],
        "results": results,
    }


def load_shard_batch_packet(
    packet_path: str | Path,
    *,
    repo_root: Path,
) -> dict[str, Any]:
    path = Path(packet_path)
    if not path.is_absolute():
        path = repo_root / path
    resolved = path.resolve()
    try:
        payload = json.loads(resolved.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Shard batch packet not found: {packet_path}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Shard batch packet is unreadable: {packet_path}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"Shard batch packet must be a JSON object: {packet_path}")
    if _string(payload.get("kind")) != "shard_batch_packet":
        raise ValueError(
            f"--packet-path must point to one shard_batch_packet batch file, not {resolved.name}"
        )

    packet_shards = [
        dict(shard)
        for shard in payload.get("shards") or []
        if isinstance(shard, Mapping) and _string(shard.get("id"))
    ]
    batch_shard_ids = [
        _string(shard.get("id"))
        for shard in packet_shards
        if _string(shard.get("id"))
    ]
    selection = dict(payload.get("selection") or {}) if isinstance(payload.get("selection"), Mapping) else {}
    query_meta = dict(payload.get("query_summary") or {}) if isinstance(payload.get("query_summary"), Mapping) else {}
    review_plane_summary = [
        dict(row)
        for row in payload.get("review_plane_summary") or []
        if isinstance(row, Mapping)
    ]
    next_action_graph = (
        dict(payload.get("next_action_graph"))
        if isinstance(payload.get("next_action_graph"), Mapping)
        else {}
    )
    shard_synthesis = (
        dict(payload.get("shard_synthesis"))
        if isinstance(payload.get("shard_synthesis"), Mapping)
        else {}
    )
    return {
        "path": resolved,
        "path_rel": _relative(resolved, repo_root=repo_root),
        "payload": dict(payload),
        "selection": selection,
        "selection_basis": _string(payload.get("selection_basis")) or selection_basis(selection),
        "query_summary": query_meta,
        "review_plane_summary": review_plane_summary,
        "next_action_graph": next_action_graph,
        "shard_synthesis": shard_synthesis,
        "batch_shard_ids": batch_shard_ids,
        "batch_shard_count": len(batch_shard_ids),
    }
