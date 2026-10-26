#!/usr/bin/env python3
"""Reap orphaned Claude Code descendants whose parent died.

Predicate: PPID == 1, command matches a strict allowlist, age > MIN_AGE_SECONDS.
Sends SIGTERM, logs to ~/Library/Logs/claude-orphan-reaper.log.
Designed for stdlib-only execution under launchd; do not import from the repo.
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

LOG_PATH = Path.home() / "Library" / "Logs" / "claude-orphan-reaper.log"
MIN_AGE_SECONDS = 300
INVENTORY_SCHEMA = "tool_server_pressure_inventory_v1"
RELIEF_RECEIPT_SCHEMA = "pressure_hygiene_relief_receipt_v1"
HELPER_OWNER_RELEASE_REQUEST_SCHEMA = "helper_owner_release_request_v1"

ACTIVE_OWNER_RELEASE_STATUSES = frozenset(
    {
        "active_codex_parent_chain",
        "active_claude_parent_chain",
        "active_parent_process",
    }
)

ACTIVE_OWNER_RELEASE_THRESHOLDS = {
    "playwright_mcp": 2,
    "chrome_devtools_mcp": 2,
    "codex_stdio_app_server": 4,
    "vite_dev_server": 1,
    "caffeinate": 1,
}

ALLOWLIST = re.compile(
    r"(?:^|/)caffeinate(?:$|\s)"
    r"|/\.claude/plugins/cache/.*?/mcp-server\.cjs"
    r"|/node_modules/\.bin/playwright-mcp"
    r"|(?:^|\s)(?:npm\s+exec|npx)\s+@playwright/mcp(?:@[\w.\-]+)?(?:$|\s)"
    r"|/chrome-devtools-mcp/build/src/"
)

PROCESS_KIND_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "playwright_mcp",
        re.compile(
            r"/node_modules/\.bin/playwright-mcp"
            r"|(?:^|\s)(?:npm\s+exec|npx)\s+@playwright/mcp(?:@[\w.\-]+)?(?:$|\s)"
        ),
    ),
    ("claude_mcp_server", re.compile(r"/\.claude/plugins/cache/.*?/mcp-server\.cjs")),
    ("chrome_devtools_mcp", re.compile(r"/chrome-devtools-mcp/build/src/")),
    (
        "codex_stdio_app_server",
        re.compile(r"/Applications/Codex\.app/.*/codex app-server --listen stdio://"),
    ),
    (
        "codex_app_server_main",
        re.compile(r"/Applications/Codex\.app/.*/codex app-server --analytics-default-enabled"),
    ),
    ("vite_dev_server", re.compile(r"/system/server/ui/node_modules/\.bin/vite")),
    ("run_server", re.compile(r"(?:^|\s)(?:\S*/)?run_server\.py(?:$|\s)")),
    ("caffeinate", re.compile(r"(?:^|/)caffeinate(?:$|\s)")),
)


def _parse_etime_to_seconds(etime: str) -> int:
    parts = etime.strip().split("-")
    days = 0
    rest = parts[0]
    if len(parts) == 2:
        days = int(parts[0])
        rest = parts[1]
    h, m, s = 0, 0, 0
    segments = rest.split(":")
    if len(segments) == 3:
        h, m, s = int(segments[0]), int(segments[1]), int(segments[2])
    elif len(segments) == 2:
        m, s = int(segments[0]), int(segments[1])
    else:
        s = int(segments[0])
    return days * 86400 + h * 3600 + m * 60 + s


def _process_kind(cmd: str) -> str | None:
    for kind, pattern in PROCESS_KIND_PATTERNS:
        if pattern.search(cmd):
            return kind
    return None


def _parse_float(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _parse_int(value: str) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _command_hash(cmd: str) -> str:
    return hashlib.sha256(cmd.encode("utf-8")).hexdigest()[:16]


def _inventory_owner_and_decision(
    *,
    kind: str,
    ppid: int,
    age_s: int,
    allowlist_matched: bool,
    owner_status: str,
) -> tuple[str, str, str]:
    if kind == "run_server":
        return "operator_backend", "keep", "backend_runtime_not_helper_cleanup"
    if kind == "codex_app_server_main":
        return "codex_app_runtime", "keep", "main_codex_runtime_not_helper_cleanup"
    if ppid == 1 and allowlist_matched and age_s >= MIN_AGE_SECONDS:
        return "launchd_detached", "candidate_safe_close", "strict_orphan_allowlist_age_threshold_met"
    if ppid == 1:
        return "launchd_detached", "requires_owner_check", "detached_process_not_in_safe_close_predicate"
    if owner_status.startswith("active_"):
        return owner_status, "requires_owner_check", "active_parent_chain_requires_owner_check"
    return owner_status, "requires_owner_check", "parent_owner_not_resolved"


def _parse_process_rows(ps_text: str) -> list[dict[str, Any]]:
    processes: list[dict[str, Any]] = []
    for line in ps_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_s, ppid_s, etime, cpu_s, rss_s, cmd = line.split(None, 5)
        except ValueError:
            try:
                pid_s, ppid_s, etime, cmd = line.split(None, 3)
            except ValueError:
                continue
            cpu_s = ""
            rss_s = ""
        pid = _parse_int(pid_s)
        ppid = _parse_int(ppid_s)
        if pid is None or ppid is None:
            continue
        try:
            age_s = _parse_etime_to_seconds(etime)
        except ValueError:
            continue
        processes.append(
            {
                "pid": pid,
                "ppid": ppid,
                "age_s": age_s,
                "cpu_s": cpu_s,
                "rss_s": rss_s,
                "cmd": cmd,
            }
        )
    return processes


def _owner_hint_from_command(cmd: str) -> str:
    if (
        "/Applications/Codex.app/" in cmd
        or "codex app-server" in cmd
        or "node_repl" in cmd
    ):
        return "active_codex_parent_chain"
    if "/Applications/Claude.app/" in cmd or "/.claude/" in cmd:
        return "active_claude_parent_chain"
    return "active_parent_process"


def _owner_status_for_process(
    *,
    kind: str,
    ppid: int,
    process_table: dict[int, dict[str, Any]],
) -> str:
    if kind == "run_server":
        return "operator_backend"
    if kind == "codex_app_server_main":
        return "codex_app_runtime"
    if ppid == 1:
        return "launchd_detached"
    current = ppid
    seen: set[int] = set()
    last_status = "unknown_parent_process"
    for _depth in range(8):
        if current in seen:
            return last_status
        seen.add(current)
        parent = process_table.get(current)
        if parent is None:
            return last_status
        cmd = str(parent.get("cmd", ""))
        last_status = _owner_hint_from_command(cmd)
        if last_status != "active_parent_process":
            return last_status
        next_ppid = parent.get("ppid")
        if not isinstance(next_ppid, int) or next_ppid == 1:
            return last_status
        current = next_ppid
    return last_status


def _parse_inventory_rows(ps_text: str) -> list[dict[str, Any]]:
    processes = _parse_process_rows(ps_text)
    process_table = {int(process["pid"]): process for process in processes}
    rows: list[dict[str, Any]] = []
    for process in processes:
        pid = int(process["pid"])
        ppid = int(process["ppid"])
        age_s = int(process["age_s"])
        cpu_s = str(process.get("cpu_s", ""))
        rss_s = str(process.get("rss_s", ""))
        cmd = str(process["cmd"])
        kind = _process_kind(cmd)
        if kind is None:
            continue
        cpu_pct = _parse_float(cpu_s)
        rss_kb = _parse_int(rss_s)
        rss_mb = round((rss_kb or 0) / 1024, 1) if rss_kb is not None else None
        allowlist_matched = bool(ALLOWLIST.search(cmd))
        owner_status = _owner_status_for_process(
            kind=kind,
            ppid=ppid,
            process_table=process_table,
        )
        owner, decision, reason = _inventory_owner_and_decision(
            kind=kind,
            ppid=ppid,
            age_s=age_s,
            allowlist_matched=allowlist_matched,
            owner_status=owner_status,
        )
        rows.append(
            {
                "pid": pid,
                "ppid": ppid,
                "process_kind": kind,
                "owner": owner,
                "owner_status": owner_status,
                "decision": decision,
                "reason": reason,
                "age_s": age_s,
                "cpu_pct": cpu_pct,
                "rss_mb": rss_mb,
                "allowlist_matched": allowlist_matched,
                "command_hash": _command_hash(cmd),
                "command_preview": cmd[:180],
            }
        )
    return rows


def _active_owner_pressure_groups(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[tuple[str, str], dict[str, Any]] = {}
    for row in rows:
        kind = str(row.get("process_kind") or "")
        owner_status = str(row.get("owner_status") or "")
        threshold = ACTIVE_OWNER_RELEASE_THRESHOLDS.get(kind)
        if threshold is None or owner_status not in ACTIVE_OWNER_RELEASE_STATUSES:
            continue
        key = (kind, owner_status)
        bucket = buckets.setdefault(
            key,
            {
                "process_kind": kind,
                "owner_status": owner_status,
                "budget": threshold,
                "count": 0,
                "rss_mb": 0.0,
                "ages_s": [],
            },
        )
        bucket["count"] += 1
        rss = row.get("rss_mb")
        if isinstance(rss, (int, float)):
            bucket["rss_mb"] = round(float(bucket["rss_mb"]) + float(rss), 1)
        age_s = row.get("age_s")
        if isinstance(age_s, int):
            bucket["ages_s"].append(age_s)

    groups: list[dict[str, Any]] = []
    for bucket in buckets.values():
        count = int(bucket["count"])
        budget = int(bucket["budget"])
        excess_count = max(0, count - budget)
        if excess_count <= 0:
            continue
        ages = [int(age) for age in bucket.pop("ages_s", [])]
        bucket.update(
            {
                "excess_count": excess_count,
                "oldest_age_s": max(ages) if ages else None,
                "newest_age_s": min(ages) if ages else None,
                "recommended_action": "request_owner_release",
                "safety": {
                    "no_process_signal_sent": True,
                    "owner_must_release_own_helper": True,
                },
            }
        )
        bucket["owner_release_request"] = _owner_release_request_for_group(bucket)
        groups.append(bucket)
    return sorted(
        groups,
        key=lambda item: (
            int(item.get("excess_count") or 0),
            float(item.get("rss_mb") or 0.0),
            int(item.get("count") or 0),
        ),
        reverse=True,
    )


def _owner_release_target(owner_status: str) -> str | None:
    if owner_status == "active_codex_parent_chain":
        return "codex_active_session"
    if owner_status == "active_claude_parent_chain":
        return "claude_active_session"
    if owner_status == "active_parent_process":
        return "active_parent_process"
    return None


def _owner_release_request_for_group(group: Mapping[str, Any]) -> dict[str, Any]:
    owner_status = str(group.get("owner_status") or "unknown").strip() or "unknown"
    return {
        "schema": HELPER_OWNER_RELEASE_REQUEST_SCHEMA,
        "process_kind": str(group.get("process_kind") or ""),
        "owner_status": owner_status,
        "target_owner": _owner_release_target(owner_status),
        "pressure_mode": "degraded",
        "process_count": int(group.get("count") or 0),
        "excess_count": int(group.get("excess_count") or 0),
        "rss_mb_total": group.get("rss_mb"),
        "permitted_action": "ask_owner_to_release",
        "requested_action": "release_tool_lease",
        "result": "requested",
        "owner_release_route": (
            "Owning app/session must release or reuse its helper lease; "
            "orphan_reaper must not signal active-owner descendants."
        ),
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
            "owner_must_release_own_helper": True,
        },
    }


def build_tool_server_pressure_inventory(ps_text: str | None = None) -> dict[str, Any]:
    if ps_text is None:
        ps_text = subprocess.check_output(
            ["ps", "-Ao", "pid=,ppid=,etime=,%cpu=,rss=,command="],
            text=True,
        )
    rows = _parse_inventory_rows(ps_text)
    kind_counts: dict[str, int] = {}
    decision_counts: dict[str, int] = {}
    owner_status_counts: dict[str, int] = {}
    rss_by_kind: dict[str, float] = {}
    rss_by_owner_status: dict[str, float] = {}
    for row in rows:
        kind = str(row["process_kind"])
        decision = str(row["decision"])
        owner_status = str(row["owner_status"])
        kind_counts[kind] = kind_counts.get(kind, 0) + 1
        decision_counts[decision] = decision_counts.get(decision, 0) + 1
        owner_status_counts[owner_status] = owner_status_counts.get(owner_status, 0) + 1
        rss = row.get("rss_mb")
        if isinstance(rss, (int, float)):
            rss_by_kind[kind] = round(rss_by_kind.get(kind, 0.0) + float(rss), 1)
            rss_by_owner_status[owner_status] = round(
                rss_by_owner_status.get(owner_status, 0.0) + float(rss),
                1,
            )
    candidate_rss = round(
        sum(
            float(row["rss_mb"])
            for row in rows
            if row.get("decision") == "candidate_safe_close"
            and isinstance(row.get("rss_mb"), (int, float))
        ),
        1,
    )
    owner_check_rss = round(
        sum(
            float(row["rss_mb"])
            for row in rows
            if row.get("decision") == "requires_owner_check"
            and isinstance(row.get("rss_mb"), (int, float))
        ),
        1,
    )
    total_rss = round(
        sum(
            float(row["rss_mb"])
            for row in rows
            if isinstance(row.get("rss_mb"), (int, float))
        ),
        1,
    )
    active_owner_pressure_groups = _active_owner_pressure_groups(rows)
    active_owner_release_request_count = sum(
        int(group.get("excess_count") or 0) for group in active_owner_pressure_groups
    )
    active_owner_release_rss = round(
        sum(float(group.get("rss_mb") or 0.0) for group in active_owner_pressure_groups),
        1,
    )
    return {
        "schema": INVENTORY_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "policy": {
            "no_unknown_owner_killed": True,
            "inventory_is_not_kill_list": True,
            "safe_close_predicate": "ppid==1 and allowlisted command and age>=MIN_AGE_SECONDS",
            "min_age_seconds": MIN_AGE_SECONDS,
        },
        "summary": {
            "process_count": len(rows),
            "total_rss_mb": total_rss,
            "candidate_safe_close_count": decision_counts.get("candidate_safe_close", 0),
            "candidate_safe_close_rss_mb": candidate_rss,
            "requires_owner_check_count": decision_counts.get("requires_owner_check", 0),
            "requires_owner_check_rss_mb": owner_check_rss,
            "active_owner_release_request_count": active_owner_release_request_count,
            "active_owner_release_rss_mb": active_owner_release_rss,
            "active_owner_pressure_group_count": len(active_owner_pressure_groups),
            "active_owner_pressure_groups": active_owner_pressure_groups[:10],
            "keep_count": decision_counts.get("keep", 0),
            "kind_counts": kind_counts,
            "decision_counts": decision_counts,
            "owner_status_counts": owner_status_counts,
            "rss_mb_by_kind": rss_by_kind,
            "rss_mb_by_owner_status": rss_by_owner_status,
        },
        "rows": rows,
    }


def build_pressure_hygiene_relief_receipt(ps_text: str | None = None) -> dict[str, Any]:
    inventory = build_tool_server_pressure_inventory(ps_text)
    summary = inventory["summary"]
    candidate_count = int(summary.get("candidate_safe_close_count", 0))
    owner_check_count = int(summary.get("requires_owner_check_count", 0))
    active_owner_release_count = int(summary.get("active_owner_release_request_count", 0))
    owner_release_requests = [
        dict(group.get("owner_release_request") or {})
        for group in summary.get("active_owner_pressure_groups") or []
        if isinstance(group, Mapping) and isinstance(group.get("owner_release_request"), Mapping)
    ]
    if candidate_count:
        action_status = "safe_action_available"
        verdict = "pending_safe_close_action"
        reason = "strict_safe_close_candidates_available_but_not_executed_by_receipt_mode"
    elif active_owner_release_count:
        action_status = "owner_release_request_available"
        verdict = "pending_owner_release_request"
        reason = "active_owner_helper_budget_exceeded_without_safe_orphan_close_candidates"
    elif owner_check_count:
        action_status = "owner_check_required"
        verdict = "no_safe_action"
        reason = "all_high_rss_helper_pressure_requires_owner_check"
    else:
        action_status = "no_action"
        verdict = "no_safe_action"
        reason = "no_helper_pressure_rows_available_for_safe_close"
    return {
        "schema": RELIEF_RECEIPT_SCHEMA,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "before": {
            "tool_server_pressure_inventory_schema": inventory["schema"],
            "inventory_summary": summary,
        },
        "action": {
            "status": action_status,
            "safe_close_action_count": 0,
            "safe_close_candidate_count": candidate_count,
            "requires_owner_check_count": owner_check_count,
            "active_owner_release_request_count": active_owner_release_count,
            "owner_release_requests": owner_release_requests,
            "reason": reason,
            "no_unknown_owner_killed": True,
        },
        "after": None,
        "verdict": verdict,
        "next_actions": [
            "run_strict_orphan_reaper_only_for_candidate_safe_close_rows",
            "request_active_owner_release_for_over_budget_helper_groups",
            "resolve_owner_state_before_closing_requires_owner_check_rows",
            "measure_host_pressure_after_any_actual_safe_close_action",
        ],
    }


def _list_orphans() -> list[tuple[int, int, int, str]]:
    out = subprocess.check_output(
        ["ps", "-Ao", "pid=,ppid=,etime=,command="],
        text=True,
    )
    rows: list[tuple[int, int, int, str]] = []
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            pid_s, ppid_s, etime, cmd = line.split(None, 3)
        except ValueError:
            continue
        try:
            pid = int(pid_s)
            ppid = int(ppid_s)
        except ValueError:
            continue
        if ppid != 1:
            continue
        if not ALLOWLIST.search(cmd):
            continue
        age = _parse_etime_to_seconds(etime)
        if age < MIN_AGE_SECONDS:
            continue
        rows.append((pid, ppid, age, cmd))
    return rows


def _log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with LOG_PATH.open("a") as fh:
        fh.write(f"{stamp} {message}\n")


def main() -> int:
    inventory_json = "--inventory-json" in sys.argv
    relief_receipt_json = "--relief-receipt-json" in sys.argv
    dry_run = "--dry-run" in sys.argv
    if inventory_json:
        print(json.dumps(build_tool_server_pressure_inventory(), indent=2, sort_keys=True))
        return 0
    if relief_receipt_json:
        print(json.dumps(build_pressure_hygiene_relief_receipt(), indent=2, sort_keys=True))
        return 0
    orphans = _list_orphans()
    if not orphans:
        _log("scan ok 0 reaped")
        return 0
    reaped, failed = 0, 0
    for pid, _ppid, age, cmd in orphans:
        short = cmd[:120]
        if dry_run:
            _log(f"would-reap pid={pid} age={age}s cmd={short}")
            continue
        try:
            os.kill(pid, signal.SIGTERM)
            reaped += 1
            _log(f"reaped pid={pid} age={age}s cmd={short}")
        except ProcessLookupError:
            pass
        except PermissionError as exc:
            failed += 1
            _log(f"failed pid={pid} err={exc} cmd={short}")
    if not dry_run and reaped:
        time.sleep(2)
        for pid, _ppid, _age, cmd in orphans:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                continue
            try:
                os.kill(pid, signal.SIGKILL)
                _log(f"sigkill pid={pid} cmd={cmd[:120]}")
            except ProcessLookupError:
                pass
    _log(f"scan ok {reaped} reaped, {failed} failed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
