"""Read-only Task Ledger priority surfacing for first-contact control packets.

Used by ``--entry`` (selected_workitem + top_ready), ``--pulse`` (TOP PRIORITY
block), and ``--phase`` warnings (focus drift WorkItem context).

Pure read. Never mutates ``state/task_ledger/events.jsonl`` or any view JSON;
ordinary phase/pulse/entry reads must remain side-effect-free per the
``provider_native_task_affordance_boundary`` reflex in
``codex/standards/std_task_ledger.json``. Mutation belongs to
``tools/meta/factory/task_ledger_apply.py``.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


_WORKITEM_ID_PATTERNS = (
    re.compile(r"\btask_\d+_[a-z0-9_]+\b", re.IGNORECASE),
    re.compile(r"\bcap_(?:quick_)?[a-z0-9_]+\b", re.IGNORECASE),
)
_PHASE_ID_PATTERN = re.compile(r"\b(\d{2}_\d+)\b")
_READY_BY_RANK = "state/task_ledger/views/ready_by_rank.json"
_SCHEDULABLE_BY_RANK = "state/task_ledger/views/schedulable_by_rank.json"
_EXECUTION_MENU_SCHEDULABLE = "state/task_ledger/views/execution_menu_schedulable.json"
_DEPENDENCY_BLOCKED = "state/task_ledger/views/dependency_blocked.json"
_UNLOCKS_BY_RANK = "state/task_ledger/views/unlocks_by_rank.json"
_LEDGER = "state/task_ledger/ledger.json"
_TOP_ROW_LIMIT = 3
_TERMINAL_STATES = {
    "done",
    "closed",
    "complete",
    "completed",
    "propagated",
    "retired",
    "satisfied",
    "superseded",
}


def _safe_load_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return None


def _view_items(repo_root: Path, rel_path: str) -> list[dict[str, Any]]:
    payload = _safe_load_json(repo_root / rel_path)
    if not isinstance(payload, Mapping):
        return []
    items = payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _non_terminal_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        item
        for item in items
        if not _is_terminal_state(item.get("state") or item.get("status"))
    ]


def _ready_items(repo_root: Path) -> list[dict[str, Any]]:
    return _non_terminal_items(_view_items(repo_root, _READY_BY_RANK))


def _schedulable_items(repo_root: Path) -> list[dict[str, Any]]:
    return _non_terminal_items(
        _view_items(repo_root, _EXECUTION_MENU_SCHEDULABLE)
    ) or _non_terminal_items(_view_items(repo_root, _SCHEDULABLE_BY_RANK))


def _schedulable_items_with_source(repo_root: Path) -> tuple[list[dict[str, Any]], str | None]:
    execution_menu_items = _non_terminal_items(
        _view_items(repo_root, _EXECUTION_MENU_SCHEDULABLE)
    )
    if execution_menu_items:
        return execution_menu_items, "execution_menu_schedulable"
    schedulable_items = _non_terminal_items(_view_items(repo_root, _SCHEDULABLE_BY_RANK))
    if schedulable_items:
        return schedulable_items, "schedulable_by_rank"
    return [], None


def _all_workitems(repo_root: Path) -> list[dict[str, Any]]:
    payload = _safe_load_json(repo_root / _LEDGER)
    if not isinstance(payload, Mapping):
        return []
    items = payload.get("work_items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def detect_workitem_ids(text: str | None) -> list[str]:
    """Return WorkItem ids referenced in free-form text, in first-occurrence order."""
    if not text:
        return []
    seen: dict[str, None] = {}
    for pattern in _WORKITEM_ID_PATTERNS:
        for match in pattern.findall(text):
            normalized = str(match).strip()
            if normalized and normalized not in seen:
                seen[normalized] = None
    return list(seen.keys())


def detect_phase_ids(text: str | None) -> list[str]:
    if not text:
        return []
    seen: dict[str, None] = {}
    for match in _PHASE_ID_PATTERN.findall(text):
        if match not in seen:
            seen[match] = None
    return list(seen.keys())


def top_ready_workitem(repo_root: Path) -> dict[str, Any] | None:
    items = _ready_items(repo_root)
    if not items:
        return None
    return _summarize(items[0])


def top_schedulable_workitem(repo_root: Path) -> dict[str, Any] | None:
    items, source_view = _schedulable_items_with_source(repo_root)
    if not items:
        return top_ready_workitem(repo_root)
    return _summarize(items[0], source_view=source_view)


def priority_constellation(repo_root: Path) -> dict[str, Any]:
    """Return a compact read-only WorkItem/blocker picture for startup surfaces.

    The point is not to replace ``organizer-report`` or Task Ledger cards. It is
    to make the at-entry blocker topology visible enough that a dormant phase
    anchor cannot hide actionable WorkItem pressure.
    """
    schedulable_items, schedulable_source = _schedulable_items_with_source(repo_root)
    ready_items = _ready_items(repo_root)
    blocked_items = _non_terminal_items(_view_items(repo_root, _DEPENDENCY_BLOCKED))
    unlock_items = _non_terminal_items(_view_items(repo_root, _UNLOCKS_BY_RANK))

    top_schedulable_rows = [
        _summarize(item, source_view=schedulable_source)
        for item in schedulable_items[:_TOP_ROW_LIMIT]
    ]
    top_schedulable_unlock_pressure = _rank_by_unlock_pressure(
        schedulable_items,
        source_view=schedulable_source,
        limit=_TOP_ROW_LIMIT,
    )
    top_blocked_rows = [
        _summarize(item, source_view="dependency_blocked")
        for item in blocked_items[:_TOP_ROW_LIMIT]
    ]
    top_global_unlock_pressure, unlock_pressure_count = _rank_by_unlock_pressure_with_count(
        unlock_items,
        source_view="unlocks_by_rank",
        limit=_TOP_ROW_LIMIT,
    )

    top_schedulable = (
        top_schedulable_rows[0]
        if top_schedulable_rows
        else (top_ready_workitem(repo_root) if ready_items else None)
    )
    top_ready = _summarize(ready_items[0], source_view="ready_by_rank") if ready_items else None
    top_blocked = top_blocked_rows[0] if top_blocked_rows else None
    top_unlock = top_global_unlock_pressure[0] if top_global_unlock_pressure else (
        _summarize(unlock_items[0], source_view="unlocks_by_rank")
        if unlock_items
        else None
    )
    highest_schedulable_pressure = (
        top_schedulable_unlock_pressure[0] if top_schedulable_unlock_pressure else None
    )
    highest_global_pressure = (
        top_global_unlock_pressure[0] if top_global_unlock_pressure else None
    )

    return {
        "schema_version": "task_ledger_priority_constellation_v1",
        "authority": {
            "source": "state/task_ledger/events.jsonl",
            "projection_paths": [
                _EXECUTION_MENU_SCHEDULABLE,
                _SCHEDULABLE_BY_RANK,
                _READY_BY_RANK,
                _DEPENDENCY_BLOCKED,
                _UNLOCKS_BY_RANK,
            ],
            "mutation_rule": "read-only startup surface; append Task Ledger events to change WorkItems",
        },
        "view_counts": {
            "execution_menu_schedulable": len(schedulable_items)
            if schedulable_source == "execution_menu_schedulable"
            else len(_view_items(repo_root, _EXECUTION_MENU_SCHEDULABLE)),
            "schedulable_by_rank": len(_view_items(repo_root, _SCHEDULABLE_BY_RANK)),
            "ready_by_rank": len(ready_items),
            "dependency_blocked": len(blocked_items),
            "unlocks_by_rank": len(unlock_items),
            "unlock_pressure": unlock_pressure_count,
        },
        "top_schedulable_workitem": top_schedulable,
        "top_ready_workitem": top_ready,
        "top_dependency_blocked_workitem": top_blocked,
        "top_unlock_workitem": top_unlock,
        "top_schedulable_workitems": top_schedulable_rows,
        "top_schedulable_unlock_pressure_workitems": top_schedulable_unlock_pressure,
        "top_dependency_blocked_workitems": top_blocked_rows,
        "top_global_unlock_pressure_workitems": top_global_unlock_pressure,
        "dynamic_focus": {
            "primary_action_id": top_schedulable.get("id")
            if isinstance(top_schedulable, Mapping)
            else None,
            "highest_schedulable_unlock_pressure_id": (
                highest_schedulable_pressure.get("id")
                if isinstance(highest_schedulable_pressure, Mapping)
                else None
            ),
            "highest_global_unlock_pressure_id": (
                highest_global_pressure.get("id")
                if isinstance(highest_global_pressure, Mapping)
                else None
            ),
            "top_dependency_blocked_id": (
                top_blocked.get("id") if isinstance(top_blocked, Mapping) else None
            ),
            "selection_rule": (
                "primary_action follows execution_menu_schedulable order; "
                "pressure rows are ranked by live downstream waiting/unsatisfied counts."
            ),
        },
        "selector_explanation": {
            "schedulable_now": (
                "Feasibility lane: rows already in execution_menu_schedulable or the "
                "schedulable fallback view. This lane is the executable next-action lane."
            ),
            "schedulable_unlock_pressure": (
                "Feasible pressure lane: only schedulable non-terminal rows, ranked by "
                "downstream waiting and unsatisfied dependency pressure."
            ),
            "global_unlock_pressure": (
                "Global pressure lane: non-terminal rows from unlocks_by_rank; these can "
                "explain hidden dependency topology but are not necessarily executable now."
            ),
            "dependency_blocked": (
                "Blocked lane: important rows whose hard dependencies are not yet satisfied; "
                "use this to unblock or classify, not as direct execution."
            ),
            "terminal_policy": (
                "Terminal states remain historical evidence in source views but cannot win "
                "pressure-ranked lanes."
            ),
        },
        "blocker_constellation": {
            "schedulable_count": len(schedulable_items),
            "ready_count": len(ready_items),
            "dependency_blocked_count": len(blocked_items),
            "unlock_pressure_count": unlock_pressure_count,
            "unlocks_by_rank_count": len(unlock_items),
            "highest_schedulable_unlock_pressure": highest_schedulable_pressure,
            "highest_global_unlock_pressure": highest_global_pressure,
            "top_dependency_blocked": top_blocked,
        },
        "drilldown_commands": {
            "organizer_report": "./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2",
            "task_ledger_cluster": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag",
            "top_schedulable_card": (
                top_schedulable.get("drilldown_command")
                if isinstance(top_schedulable, Mapping)
                else None
            ),
            "top_blocked_card": (
                top_blocked.get("drilldown_command")
                if isinstance(top_blocked, Mapping)
                else None
            ),
            "highest_schedulable_unlock_pressure_card": (
                highest_schedulable_pressure.get("drilldown_command")
                if isinstance(highest_schedulable_pressure, Mapping)
                else None
            ),
            "highest_global_unlock_pressure_card": (
                highest_global_pressure.get("drilldown_command")
                if isinstance(highest_global_pressure, Mapping)
                else None
            ),
        },
    }


def find_workitem_by_id(repo_root: Path, work_item_id: str) -> dict[str, Any] | None:
    if not work_item_id:
        return None
    for item in _ready_items(repo_root):
        if str(item.get("id") or "") == work_item_id:
            return _summarize(item)
    for item in _all_workitems(repo_root):
        if str(item.get("id") or "") == work_item_id:
            return _summarize(item)
    return None


def find_workitems_for_phase(repo_root: Path, phase_id: str | None) -> list[dict[str, Any]]:
    """Return ready WorkItems whose id, title, or statement names the phase id.

    Match is intentionally loose: accepts ``09_44`` or ``09.44`` mentions, since
    phase ids appear in WorkItem text in both forms.
    """
    if not phase_id:
        return []
    needle_underscore = phase_id
    needle_dot = phase_id.replace("_", ".")
    matches: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in _ready_items(repo_root):
        haystack = " ".join(
            str(item.get(field) or "") for field in ("id", "title", "statement")
        )
        if needle_underscore in haystack or needle_dot in haystack:
            wid = str(item.get("id") or "")
            if wid and wid not in seen:
                seen.add(wid)
                matches.append(_summarize(item))
    return matches


def _summarize(item: Mapping[str, Any], *, source_view: str | None = None) -> dict[str, Any]:
    wid = str(item.get("id") or "")
    summary = {
        "id": wid,
        "title": str(item.get("title") or "") or None,
        "rank": item.get("rank"),
        "state": str(item.get("state") or item.get("status") or "") or None,
        "work_item_type": str(item.get("work_item_type") or "") or None,
        "statement_snippet": _snippet(item.get("statement"), 240),
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface task_ledger --band card --ids {wid}"
            if wid
            else None
        ),
    }
    if source_view:
        summary["source_view"] = source_view
    dependency_status = _dependency_payload(item)
    if dependency_status:
        summary["dependency_status"] = dependency_status
        dependency_summary = _dependency_summary(dependency_status)
        summary["dependency_summary"] = dependency_summary
        priority_signal = _priority_signal(item, dependency_summary, source_view=source_view)
        if priority_signal:
            summary["priority_signal"] = priority_signal
    return summary


def _dependency_payload(item: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(item.get("dependency_status"), Mapping):
        return dict(item["dependency_status"])
    payload: dict[str, Any] = {}
    for key in (
        "downstream_unlock_ids",
        "downstream_unlock_edges",
        "downstream_count",
        "upstream_dependency_edges",
        "unsatisfied_dep_ids",
        "hard_dep_count",
    ):
        if key in item:
            payload[key] = item.get(key)
    return payload


def _dependency_summary(dependency_status: Mapping[str, Any]) -> dict[str, Any]:
    downstream_ids = [
        str(item)
        for item in (dependency_status.get("downstream_unlock_ids") or [])
        if str(item).strip()
    ]
    unsatisfied_ids = [
        str(item)
        for item in (dependency_status.get("unsatisfied_dep_ids") or [])
        if str(item).strip()
    ]
    downstream_edges = [
        edge
        for edge in (dependency_status.get("downstream_unlock_edges") or [])
        if isinstance(edge, Mapping)
    ]
    upstream_edges = [
        edge
        for edge in (dependency_status.get("upstream_dependency_edges") or [])
        if isinstance(edge, Mapping)
    ]
    compact_edges = [_compact_downstream_edge(edge) for edge in downstream_edges]
    compact_edges.sort(
        key=lambda edge: (
            not bool(edge.get("waiting_on_this")),
            -int(edge.get("downstream_unsatisfied_dep_count") or 0),
            str(edge.get("id") or ""),
        )
    )
    downstream_count = (
        _int_or_none(dependency_status.get("downstream_count"))
        or len(downstream_ids)
        or len(downstream_edges)
    )
    waiting_edges = [edge for edge in compact_edges if edge.get("waiting_on_this")]
    downstream_unsatisfied_total = sum(
        int(edge.get("downstream_unsatisfied_dep_count") or 0) for edge in waiting_edges
    )
    return {
        "schedulable": dependency_status.get("schedulable"),
        "hard_dep_count": dependency_status.get("hard_dep_count"),
        "unsatisfied_dep_count": len(unsatisfied_ids),
        "unsatisfied_dep_ids": unsatisfied_ids[:5],
        "downstream_unlock_count": downstream_count,
        "downstream_unlock_ids": downstream_ids[:5],
        "waiting_downstream_unlock_count": len(waiting_edges),
        "downstream_unsatisfied_dep_total": downstream_unsatisfied_total,
        "max_downstream_unsatisfied_dep_count": max(
            [int(edge.get("downstream_unsatisfied_dep_count") or 0) for edge in waiting_edges]
            or [0]
        ),
        "top_downstream_unlock_edges": compact_edges[:5],
        "upstream_dependency_count": len(upstream_edges),
    }


def _compact_downstream_edge(edge: Mapping[str, Any]) -> dict[str, Any]:
    downstream_unsatisfied = [
        str(item)
        for item in (edge.get("downstream_unsatisfied_dep_ids") or [])
        if str(item).strip()
    ]
    return {
        "id": str(edge.get("id") or "") or None,
        "title": _snippet(edge.get("title"), 96),
        "rank": edge.get("rank"),
        "state": str(edge.get("state") or "") or None,
        "waiting_on_this": bool(edge.get("waiting_on_this")),
        "downstream_schedulable": edge.get("downstream_schedulable"),
        "downstream_unsatisfied_dep_count": len(downstream_unsatisfied),
        "downstream_unsatisfied_dep_ids": downstream_unsatisfied[:5],
        "unlock_status": str(edge.get("unlock_status") or "") or None,
    }


def _rank_by_unlock_pressure(
    items: list[dict[str, Any]],
    *,
    source_view: str | None,
    limit: int,
) -> list[dict[str, Any]]:
    rows, _ = _rank_by_unlock_pressure_with_count(
        items,
        source_view=source_view,
        limit=limit,
    )
    return rows


def _rank_by_unlock_pressure_with_count(
    items: list[dict[str, Any]],
    *,
    source_view: str | None,
    limit: int,
) -> tuple[list[dict[str, Any]], int]:
    summarized = [_summarize(item, source_view=source_view) for item in items]
    pressured = [
        item
        for item in summarized
        if (
            isinstance(item.get("priority_signal"), Mapping)
            and int(item["priority_signal"].get("waiting_downstream_unlock_count") or 0) > 0
            and not bool(item["priority_signal"].get("terminal_state"))
        )
    ]
    pressured.sort(
        key=lambda item: (
            -int((item.get("priority_signal") or {}).get("unlock_pressure_score") or 0),
            _rank_sort_key(item.get("rank")),
            str(item.get("id") or ""),
        )
    )
    return pressured[:limit], len(pressured)


def _priority_signal(
    item: Mapping[str, Any],
    dependency_summary: Mapping[str, Any],
    *,
    source_view: str | None,
) -> dict[str, Any]:
    metrics = _unlock_pressure_metrics(dependency_summary)
    rank_bonus = max(0, 80 - _rank_sort_key(item.get("rank"))) if item.get("rank") is not None else 0
    terminal_penalty = 100 if _is_terminal_state(item.get("state") or item.get("status")) else 0
    source_bonus = {
        "execution_menu_schedulable": 75,
        "schedulable_by_rank": 60,
        "dependency_blocked": 50,
        "unlocks_by_rank": 25,
        "ready_by_rank": 10,
    }.get(str(source_view or ""), 0)
    unsatisfied_dep_count = int(dependency_summary.get("unsatisfied_dep_count") or 0)
    score = (
        metrics["waiting_downstream_unlock_count"] * 100
        + metrics["downstream_unsatisfied_dep_total"] * 10
        + metrics["downstream_unlock_count"] * 8
        + unsatisfied_dep_count * 60
        + rank_bonus
        + source_bonus
        - terminal_penalty
    )
    if score <= 0 and not any(metrics.values()):
        return {}
    return {
        "unlock_pressure_score": score,
        "waiting_downstream_unlock_count": metrics["waiting_downstream_unlock_count"],
        "downstream_unsatisfied_dep_total": metrics["downstream_unsatisfied_dep_total"],
        "max_downstream_unsatisfied_dep_count": metrics["max_downstream_unsatisfied_dep_count"],
        "downstream_unlock_count": metrics["downstream_unlock_count"],
        "source_view": source_view,
        "schedulable": dependency_summary.get("schedulable"),
        "pressure_basis": "dependency_status.downstream_unlock_edges",
        "score_components": {
            "waiting_downstream_unlock_count": metrics["waiting_downstream_unlock_count"],
            "downstream_unsatisfied_dep_total": metrics["downstream_unsatisfied_dep_total"],
            "downstream_unlock_count": metrics["downstream_unlock_count"],
            "unsatisfied_dep_count": unsatisfied_dep_count,
            "rank_bonus": rank_bonus,
            "source_bonus": source_bonus,
            "terminal_penalty": terminal_penalty,
        },
        "rank_sort_key": _rank_sort_key(item.get("rank")),
        "terminal_state": _is_terminal_state(item.get("state") or item.get("status")),
    }


def _unlock_pressure_metrics(dependency_summary: Mapping[str, Any]) -> dict[str, int]:
    return {
        "waiting_downstream_unlock_count": int(
            dependency_summary.get("waiting_downstream_unlock_count") or 0
        ),
        "downstream_unsatisfied_dep_total": int(
            dependency_summary.get("downstream_unsatisfied_dep_total") or 0
        ),
        "max_downstream_unsatisfied_dep_count": int(
            dependency_summary.get("max_downstream_unsatisfied_dep_count") or 0
        ),
        "downstream_unlock_count": int(dependency_summary.get("downstream_unlock_count") or 0),
    }


def _rank_sort_key(value: Any) -> int:
    rank = _int_or_none(value)
    return rank if rank is not None else 10_000


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _is_terminal_state(value: Any) -> bool:
    return str(value or "").strip().lower() in _TERMINAL_STATES


def _snippet(text: Any, limit: int) -> str | None:
    s = str(text or "").strip()
    if not s:
        return None
    if len(s) <= limit:
        return s
    return s[: limit - 1].rstrip() + "…"


__all__ = [
    "detect_workitem_ids",
    "detect_phase_ids",
    "top_ready_workitem",
    "top_schedulable_workitem",
    "priority_constellation",
    "find_workitem_by_id",
    "find_workitems_for_phase",
]
