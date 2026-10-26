"""Public-safe read-only helper-process pressure inventory.

This module is a source-faithful public refactor of the read-only pressure
inventory path from ``tools/meta/control/orphan_reaper.py``. It accepts an
injected synthetic process table, classifies helper processes, reconstructs the
owner status through parent process rows, and emits pressure groups for active
owners that should release their own helper leases.

The body deliberately has no host-process actuator: no live process table read,
no process signalling, and no host mutation. Public rows carry only a digest of
the synthetic command token.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any


PASS = "pass"
DETACHED_OWNER_STATUS = "launchd_detached"
SAFE_CLOSE_DECISION = "candidate_safe_close"
OWNER_CHECK_DECISION = "requires_owner_check"
KEEP_DECISION = "keep"
DEFAULT_MIN_AGE_SECONDS = 300
ACTIVE_OWNER_STATUS_VALUES = frozenset(
    {"active_session_chain", "active_parent_process", "active_owner_chain"}
)


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str) and item]


def _rows(payload: object, key: str) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get(key, [])
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _parse_etime_to_seconds(etime: str) -> int:
    parts = etime.strip().split("-")
    days = 0
    rest = parts[0]
    if len(parts) == 2:
        days = int(parts[0])
        rest = parts[1]
    segments = rest.split(":")
    if len(segments) == 3:
        hours, minutes, seconds = (int(part) for part in segments)
    elif len(segments) == 2:
        hours = 0
        minutes, seconds = (int(part) for part in segments)
    else:
        hours = 0
        minutes = 0
        seconds = int(segments[0])
    return days * 86400 + hours * 3600 + minutes * 60 + seconds


def _parse_process_rows(ps_text: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in ps_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            pid_s, ppid_s, etime, cpu_s, rss_s, cmd = line.split(None, 5)
            pid = int(pid_s)
            ppid = int(ppid_s)
            age_s = _parse_etime_to_seconds(etime)
            cpu_pct = float(cpu_s)
            rss_kb = int(rss_s)
        except ValueError:
            continue
        rows.append(
            {
                "pid": pid,
                "ppid": ppid,
                "age_s": age_s,
                "cpu_pct": cpu_pct,
                "rss_kb": rss_kb,
                "cmd": cmd,
            }
        )
    return rows


def _kind_specs(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return _rows(policy, "kinds")


def _process_kind(cmd: str, kind_specs: list[dict[str, Any]]) -> str | None:
    for spec in kind_specs:
        if any(token in cmd for token in _strings(spec.get("match_substrings"))):
            kind = spec.get("kind")
            return kind if isinstance(kind, str) and kind else None
    return None


def _owner_hint_from_command(cmd: str, owner_classes: dict[str, Any]) -> str:
    for hint in _rows(owner_classes, "owner_hints"):
        token = str(hint.get("substring") or "")
        if token and token in cmd:
            return str(hint.get("status") or "active_parent_process")
    return "active_parent_process"


def _owner_status_for_process(
    *,
    kind: str,
    ppid: int,
    process_table: dict[int, dict[str, Any]],
    owner_classes: dict[str, Any],
    keep_status_by_kind: dict[str, str],
) -> str:
    if kind in keep_status_by_kind:
        return keep_status_by_kind[kind]
    if ppid == 1:
        return DETACHED_OWNER_STATUS
    current = ppid
    seen: set[int] = set()
    last_status = "unknown_parent_process"
    for _ in range(8):
        if current in seen:
            return last_status
        seen.add(current)
        parent = process_table.get(current)
        if parent is None:
            return last_status
        last_status = _owner_hint_from_command(str(parent.get("cmd", "")), owner_classes)
        if last_status != "active_parent_process":
            return last_status
        next_ppid = parent.get("ppid")
        if not isinstance(next_ppid, int) or next_ppid == 1:
            return last_status
        current = next_ppid
    return last_status


def _inventory_owner_and_decision(
    *,
    kind: str,
    ppid: int,
    age_s: int,
    allowlist_matched: bool,
    owner_status: str,
    min_age_seconds: int,
    keep_kinds: set[str],
    active_owner_status_values: frozenset[str],
) -> tuple[str, str, str]:
    if kind in keep_kinds:
        return owner_status, KEEP_DECISION, "runtime_not_helper_cleanup"
    if ppid == 1 and allowlist_matched and age_s >= min_age_seconds:
        return (
            DETACHED_OWNER_STATUS,
            SAFE_CLOSE_DECISION,
            "strict_orphan_allowlist_age_threshold_met",
        )
    if ppid == 1:
        return (
            DETACHED_OWNER_STATUS,
            OWNER_CHECK_DECISION,
            "detached_process_not_in_safe_close_predicate",
        )
    if owner_status in active_owner_status_values:
        return (
            owner_status,
            OWNER_CHECK_DECISION,
            "active_parent_chain_requires_owner_check",
        )
    return owner_status, OWNER_CHECK_DECISION, "parent_owner_not_resolved"


def _command_hash(cmd: str) -> str:
    return hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]


def _owner_release_target(owner_status: str, owner_classes: dict[str, Any]) -> str | None:
    targets = owner_classes.get("owner_release_targets")
    if isinstance(targets, dict) and owner_status in targets:
        return str(targets[owner_status])
    return None


def _owner_release_request_for_group(
    group: dict[str, Any], owner_classes: dict[str, Any]
) -> dict[str, Any]:
    owner_status = str(group.get("owner_status") or "unknown").strip() or "unknown"
    return {
        "schema": "helper_owner_release_request_v1",
        "process_kind": str(group.get("process_kind") or ""),
        "owner_status": owner_status,
        "target_owner": _owner_release_target(owner_status, owner_classes),
        "pressure_mode": "degraded",
        "process_count": int(group.get("count") or 0),
        "excess_count": int(group.get("excess_count") or 0),
        "permitted_action": "ask_owner_to_release",
        "requested_action": "release_tool_lease",
        "result": "requested",
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_closed": True,
            "no_active_session_terminated": True,
            "owner_must_release_own_helper": True,
        },
    }


def _active_owner_pressure_groups(
    rows: list[dict[str, Any]],
    *,
    budget_by_kind: dict[str, int],
    owner_classes: dict[str, Any],
    active_owner_status_values: frozenset[str],
) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        kind = str(row.get("process_kind") or "")
        owner_status = str(row.get("owner_status") or "")
        budget = budget_by_kind.get(kind)
        if budget is None or owner_status not in active_owner_status_values:
            continue
        key = (kind, owner_status)
        bucket = buckets.setdefault(
            key,
            {"process_kind": kind, "owner_status": owner_status, "budget": budget, "count": 0},
        )
        bucket["count"] += 1

    groups: list[dict[str, Any]] = []
    for bucket in buckets.values():
        count = int(bucket["count"])
        budget = int(bucket["budget"])
        excess_count = max(0, count - budget)
        if excess_count <= 0:
            continue
        bucket["excess_count"] = excess_count
        bucket["recommended_action"] = "request_owner_release"
        bucket["safety"] = {
            "no_process_signal_sent": True,
            "owner_must_release_own_helper": True,
        }
        bucket["owner_release_request"] = _owner_release_request_for_group(
            bucket, owner_classes
        )
        groups.append(bucket)
    return sorted(groups, key=lambda item: int(item["excess_count"]), reverse=True)


def build_tool_server_pressure_inventory(
    ps_text: str,
    *,
    policy: dict[str, Any],
    owner_classes: dict[str, Any],
) -> dict[str, Any]:
    """Classify an injected process table without reading or mutating the host."""
    kind_specs = _kind_specs(policy)
    min_age_seconds = int(policy.get("min_age_seconds") or DEFAULT_MIN_AGE_SECONDS)
    keep_kinds = set(_strings(policy.get("keep_kinds")))
    keep_status_by_kind = {
        str(spec.get("kind")): str(spec.get("keep_owner_status") or "runtime")
        for spec in kind_specs
        if str(spec.get("kind")) in keep_kinds
    }
    allowlisted_kinds = {
        str(spec.get("kind")) for spec in kind_specs if spec.get("allowlisted") is True
    }
    budget_by_kind = {
        str(spec.get("kind")): int(spec["budget"])
        for spec in kind_specs
        if isinstance(spec.get("budget"), int)
    }
    active_owner_status_values = frozenset(
        _strings(owner_classes.get("active_owner_status_values"))
    ) or ACTIVE_OWNER_STATUS_VALUES
    process_rows = _parse_process_rows(ps_text)
    process_table = {int(row["pid"]): row for row in process_rows}

    inventory_rows: list[dict[str, Any]] = []
    for process in process_rows:
        cmd = str(process["cmd"])
        kind = _process_kind(cmd, kind_specs)
        if kind is None:
            continue
        ppid = int(process["ppid"])
        age_s = int(process["age_s"])
        owner_status = _owner_status_for_process(
            kind=kind,
            ppid=ppid,
            process_table=process_table,
            owner_classes=owner_classes,
            keep_status_by_kind=keep_status_by_kind,
        )
        owner, decision, reason = _inventory_owner_and_decision(
            kind=kind,
            ppid=ppid,
            age_s=age_s,
            allowlist_matched=kind in allowlisted_kinds,
            owner_status=owner_status,
            min_age_seconds=min_age_seconds,
            keep_kinds=keep_kinds,
            active_owner_status_values=active_owner_status_values,
        )
        inventory_rows.append(
            {
                "pid": int(process["pid"]),
                "ppid": ppid,
                "process_kind": kind,
                "owner": owner,
                "owner_status": owner_status,
                "decision": decision,
                "reason": reason,
                "age_s": age_s,
                "cpu_pct": process["cpu_pct"],
                "allowlist_matched": kind in allowlisted_kinds,
                "command_hash": _command_hash(cmd),
            }
        )

    decision_counts: dict[str, int] = defaultdict(int)
    kind_counts: dict[str, int] = defaultdict(int)
    owner_status_counts: dict[str, int] = defaultdict(int)
    for row in inventory_rows:
        decision_counts[str(row["decision"])] += 1
        kind_counts[str(row["process_kind"])] += 1
        owner_status_counts[str(row["owner_status"])] += 1
    groups = _active_owner_pressure_groups(
        inventory_rows,
        budget_by_kind=budget_by_kind,
        owner_classes=owner_classes,
        active_owner_status_values=active_owner_status_values,
    )
    return {
        "schema": "tool_server_pressure_inventory_v1",
        "policy": {
            "no_unknown_owner_closed": True,
            "no_process_signal_sent": True,
            "inventory_is_not_actuation_list": True,
            "safe_close_predicate": "ppid==1 and allowlisted kind and age>=min_age_seconds",
            "min_age_seconds": min_age_seconds,
        },
        "summary": {
            "process_count": len(inventory_rows),
            "candidate_safe_close_count": decision_counts[SAFE_CLOSE_DECISION],
            "requires_owner_check_count": decision_counts[OWNER_CHECK_DECISION],
            "keep_count": decision_counts[KEEP_DECISION],
            "active_owner_release_request_count": sum(
                int(group.get("excess_count") or 0) for group in groups
            ),
            "active_owner_pressure_group_count": len(groups),
            "active_owner_pressure_groups": groups,
            "kind_counts": dict(kind_counts),
            "decision_counts": dict(decision_counts),
            "owner_status_counts": dict(owner_status_counts),
        },
        "rows": inventory_rows,
    }


def build_pressure_hygiene_relief_receipt(
    ps_text: str,
    *,
    policy: dict[str, Any],
    owner_classes: dict[str, Any],
) -> dict[str, Any]:
    """Summarize pressure without closing processes or mutating host state."""
    inventory = build_tool_server_pressure_inventory(
        ps_text, policy=policy, owner_classes=owner_classes
    )
    summary = inventory["summary"]
    candidate = int(summary.get("candidate_safe_close_count", 0))
    owner_check = int(summary.get("requires_owner_check_count", 0))
    active_release = int(summary.get("active_owner_release_request_count", 0))
    if candidate:
        action_status, verdict = "safe_action_available", "pending_safe_close_action"
    elif active_release:
        action_status, verdict = (
            "owner_release_request_available",
            "pending_owner_release_request",
        )
    elif owner_check:
        action_status, verdict = "owner_check_required", "no_safe_action"
    else:
        action_status, verdict = "no_action", "no_safe_action"
    return {
        "schema": "pressure_hygiene_relief_receipt_v1",
        "before": {"inventory_summary": summary},
        "action": {
            "status": action_status,
            "safe_close_action_count": 0,
            "safe_close_candidate_count": candidate,
            "requires_owner_check_count": owner_check,
            "active_owner_release_request_count": active_release,
            "no_process_signal_sent": True,
        },
        "after": None,
        "verdict": verdict,
        "status": PASS,
    }
