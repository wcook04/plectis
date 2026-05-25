"""
[PURPOSE]
- Teleology: Runtime enforcement helper for the work ledger. Own Claude-session
  bootstrap, read receipts, activity tracking, stale-session detection, and the
  ephemeral runtime_status signal consumed by hooks, reactions, and attention surfaces.
- Mechanism: Persist a rebuildable session-status projection under
  state/work_ledger/runtime_status.json and keep the hook path thin.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import subprocess
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

from system.lib import work_ledger


WORK_LEDGER_RUNTIME_SCHEMA = "work_ledger_runtime_status_v1"
RUNTIME_STATUS_REL = Path("state/work_ledger/runtime_status.json")
RUNTIME_LOCK_REL = Path("state/work_ledger/.runtime_status.lock")
ACTIVE_CLAIMS_SNAPSHOT_REL = Path("state/work_ledger/active_claims_snapshot.json")
BOOTSTRAP_SLICE_LIMIT = 8
SESSION_COHORT_OVERVIEW_SCHEMA = "work_ledger_session_cohort_overview_v1"
HEARTBEAT_PARTICIPATION_SCHEMA = "work_ledger_heartbeat_participation_v0"
CONCURRENCY_REPAIR_ROW_SCHEMA = "work_ledger_concurrency_repair_row_v0"
DIRTY_TREE_BANKRUPTCY_PRESSURE_SCHEMA = "dirty_tree_bankruptcy_pressure_v0"
DIRTY_TREE_RESCUE_REF_PREFIX = "refs/aiw/rescue/dirty-tree"
DIRTY_TREE_RESCUE_MANIFEST_PREFIX = "rescue_manifests"
SESSION_COHORT_OVERVIEW_LIMIT = 12
ACTIVE_SESSION_ORPHAN_AFTER = timedelta(hours=4)
SESSION_TITLE_LIMIT = 180
SESSION_METADATA_TEXT_LIMIT = 240
PASS_HEARTBEAT_SCHEMA = "runtime_pass_heartbeat_v0"
PASS_HEARTBEAT_PREFIX = "wlp_"
PASS_CURRENT_LINE_LIMIT = 180
PASS_RESULT_LINE_LIMIT = 220
PASS_SCOPE_REF_LIMIT = 12
PASS_HEARTBEAT_STATES = {
    "orienting",
    "inspecting",
    "editing",
    "validating",
    "blocked",
    "closing",
    "idle",
    "done",
}
PASS_HEARTBEAT_SOURCES = {
    "manual_cli",
    "codex_import",
    "hook",
    "projected_unknown",
}
EXPLICIT_HEARTBEAT_SOURCES = {"manual_cli", "hook"}
MISSION_FOCUS_STOPWORDS = {
    "about",
    "active",
    "agent",
    "agents",
    "also",
    "and",
    "are",
    "because",
    "can",
    "codex",
    "come",
    "conversation",
    "could",
    "doing",
    "export",
    "extended",
    "from",
    "have",
    "just",
    "like",
    "mission",
    "model",
    "only",
    "please",
    "pro",
    "prompt",
    "prompt_context",
    "read",
    "responses",
    "run",
    "same",
    "session",
    "system",
    "that",
    "the",
    "thing",
    "things",
    "think",
    "this",
    "thread",
    "through",
    "todo",
    "want",
    "what",
    "when",
    "with",
    "work",
    "working",
    "would",
    "you",
}

# A claim is a forward-looking lease on a td_* or repo-relative path that gives
# other agents a coordination primitive BEFORE they start work, not just after. The
# `touched_td_ids` list on a session is historical ("I have touched X"); a
# claim is intentional ("I hold X until <leased_until>"). Claim lifecycle is
# bi-temporal in the Graphiti sense (pattern transferred 2026-04-21 from
# annexes/graphiti/annex_notes.json n004 and from std_raw_seed_reversal_link.json):
# released_at / expired_at are set explicitly so a crash leaves a visible
# "was-claimed-but-never-released" trail instead of silent deletion.
WORK_LEDGER_CLAIM_PREFIX = "wlc_"
ACTIVE_CLAIM_LEASE_DEFAULT = timedelta(minutes=30)
ACTIVE_CLAIM_LEASE_MAX = timedelta(hours=12)
CLAIM_SCOPE_THREAD = "td_id"
CLAIM_SCOPE_PATH = "path"
CLAIM_SCOPE_WORK_ITEM = "work_item_id"
CLAIM_SCOPE_KINDS = {CLAIM_SCOPE_THREAD, CLAIM_SCOPE_PATH, CLAIM_SCOPE_WORK_ITEM}
WORK_ITEM_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]*$")

# Orphan cleanup policy. ORPHAN_HIDE_AFTER (=ACTIVE_SESSION_ORPHAN_AFTER, 4h)
# only hides a session from live-contention math. ORPHAN_SWEEP_AFTER is the
# more conservative threshold at which an orphan is auto-finalized so its
# held claims (if any) release and its `ended_at` reflects the sweep. 24h
# gives plenty of margin for long-running tasks; an operator can still call
# `session-sweep --orphan-after-hours <N>` explicitly for faster cleanup.
ACTIVE_SESSION_ORPHAN_SWEEP_AFTER = timedelta(hours=24)

# Bounded log of recent sweep events (orphan + claim-expiry) so the operator
# and reactions engine can observe cleanup pressure without reading the full
# sessions map. Deterministic, rebuildable; capped.
RECENT_SWEEP_EVENTS_LIMIT = 50
RECENT_SWEEP_EVENT_PREFIX = "wls_"


def mint_read_receipt_id() -> str:
    return f"wlr_{uuid.uuid4().hex[:16]}"


def mint_pass_id() -> str:
    return f"{PASS_HEARTBEAT_PREFIX}{uuid.uuid4().hex[:16]}"


def _runtime_status_path(repo_root: Path) -> Path:
    return repo_root / RUNTIME_STATUS_REL


def _runtime_lock_path(repo_root: Path) -> Path:
    return repo_root / RUNTIME_LOCK_REL


def _active_claims_snapshot_path(repo_root: Path) -> Path:
    return repo_root / ACTIVE_CLAIMS_SNAPSHOT_REL


def _atomic_write_runtime_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write rebuildable Work Ledger runtime projections without ledger-grade fsync cost."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        tmp_path.write_text(data, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _default_status() -> Dict[str, Any]:
    return {
        "schema": WORK_LEDGER_RUNTIME_SCHEMA,
        "generated_at": work_ledger.utc_now(),
        "sessions": {},
        "stale_sessions": [],
        "recent_sweep_events": [],
        "cohort_overview": {
            "schema": SESSION_COHORT_OVERVIEW_SCHEMA,
            "generated_at": work_ledger.utc_now(),
            "counts": {},
            "active_sessions": [],
            "stale_sessions": [],
            "actors": {},
            "phases": {},
            "contention": {
                "risk_level": "clear",
                "signals": [],
                "td_id_collisions": [],
                "unknown_scope_active_sessions": [],
                "unclaimed_touched_sessions": [],
                "orphaned_active_sessions": [],
                "claim_collisions": [],
            },
            "active_claims": [],
            "monitor_cards": [],
            "recommended_landing_lane": "claim_then_scoped_landing",
            "heartbeat_participation": {
                "schema": HEARTBEAT_PARTICIPATION_SCHEMA,
                "scope": "effective_active_sessions",
                "status": "none_active",
                "effective_active_sessions": 0,
                "explicit_current_pass_count": 0,
                "projected_unknown_count": 0,
                "missing_current_pass_count": 0,
                "participation_ratio": 0.0,
                "source_counts": {},
                "freshness_counts": {},
                "explicit_session_ids": [],
                "projected_unknown_session_ids": [],
                "first_contact": {
                    "first_card_session_id": None,
                    "explicit_heartbeat_visible_first": False,
                    "first_explicit_heartbeat_index": None,
                    "first_projected_unknown_index": None,
                },
                "policy": {
                    "projected_unknown_is_truthful_fallback": True,
                    "no_transcript_summarization": True,
                },
            },
            "recent_sweep_events": [],
            "recommended_actions": [],
        },
        "counts": {
            "sessions_total": 0,
            "active_sessions": 0,
            "stale_sessions": 0,
            "sessions_with_activity": 0,
            "sessions_with_ledger_append": 0,
            "open_todos_touched_this_session": 0,
            "session_had_no_ledger_append": 0,
        },
        "triggers": {
            "stale_session_ready": False,
            "multi_agent_coordination_ready": False,
        },
    }


def load_runtime_status(repo_root: Path, *, rebuild: bool = True) -> Dict[str, Any]:
    path = _runtime_status_path(repo_root)
    if not path.exists():
        return _default_status()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_status()
    if not isinstance(payload, dict):
        return _default_status()
    if not rebuild:
        return payload
    return rebuild_runtime_status(payload)


def _load_runtime_status_for_session_scan(repo_root: Path) -> Dict[str, Any]:
    """Load session rows without rebuilding derived counters.

    Mutation paths call `_write_runtime_status`, which rebuilds the derived
    projection exactly once before persisting. Session-only scans can use the
    same raw payload because claim and receipt checks do not consume derived
    counters, cohort summaries, or compacted session projections.
    """
    return load_runtime_status(repo_root, rebuild=False)


def _session_sort_key(session: Mapping[str, Any]) -> str:
    return str(
        session.get("last_activity_at")
        or session.get("last_append_at")
        or session.get("last_query_at")
        or session.get("bootstrapped_at")
        or session.get("ended_at")
        or ""
    )


def _parse_iso_datetime(value: object) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _compact_text(value: object, *, limit: int) -> tuple[str | None, bool, int]:
    text = str(value or "").strip()
    if not text:
        return None, False, 0
    normalized = " ".join(text.split())
    if len(normalized) <= limit:
        return normalized, False, len(normalized)
    if limit <= 3:
        return normalized[:limit], True, len(normalized)
    return f"{normalized[: limit - 3]}...", True, len(normalized)


def _public_pass_line(value: object, *, limit: int, field_name: str) -> str | None:
    text, truncated, full_chars = _compact_text(value, limit=limit)
    if not text:
        return None
    if truncated:
        raise ValueError(f"{field_name} must be <= {limit} chars; got {full_chars}")
    return text


def _normalize_pass_state(value: object) -> str:
    state = str(value or "").strip().lower().replace("-", "_")
    if not state:
        return "inspecting"
    if state not in PASS_HEARTBEAT_STATES:
        allowed = ", ".join(sorted(PASS_HEARTBEAT_STATES))
        raise ValueError(f"pass_state must be one of: {allowed}")
    return state


def _normalize_pass_source(value: object) -> str:
    source = str(value or "").strip() or "manual_cli"
    if source not in PASS_HEARTBEAT_SOURCES:
        allowed = ", ".join(sorted(PASS_HEARTBEAT_SOURCES))
        raise ValueError(f"source must be one of: {allowed}")
    return source


def _normalize_scope_refs(scope_refs: Sequence[object] | None) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in scope_refs or []:
        kind = "ref"
        ref = ""
        if isinstance(item, Mapping):
            kind = str(item.get("kind") or "ref").strip() or "ref"
            ref = str(item.get("ref") or item.get("path") or item.get("id") or "").strip()
        else:
            ref = str(item or "").strip()
        if not ref:
            continue
        ref_text = _public_pass_line(ref, limit=SESSION_METADATA_TEXT_LIMIT, field_name="scope_ref")
        if not ref_text:
            continue
        key = (kind, ref_text)
        if key in seen:
            continue
        seen.add(key)
        rows.append({"kind": kind, "ref": ref_text})
        if len(rows) >= PASS_SCOPE_REF_LIMIT:
            break
    return rows


def _compact_pass_heartbeat(
    session: Mapping[str, Any],
    *,
    now: datetime | None,
    orphaned_active: bool,
) -> Dict[str, Any]:
    raw = session.get("pass_heartbeat")
    heartbeat = dict(raw) if isinstance(raw, Mapping) else {}
    active = not bool(session.get("ended_at"))
    if not heartbeat:
        return {
            "schema": PASS_HEARTBEAT_SCHEMA,
            "status": "unknown_current_pass",
            "freshness_state": "orphaned" if orphaned_active else ("ended" if not active else "unknown"),
            "source": "projected_unknown",
            "current_pass_line": None,
            "last_pass_result_line": None,
        }

    expires_at = _parse_iso_datetime(heartbeat.get("expires_at"))
    freshness = "live"
    if not active:
        freshness = "ended"
    elif orphaned_active:
        freshness = "orphaned"
    elif expires_at is not None and now is not None and expires_at < now:
        freshness = "expired"

    current_line = _compact_text(
        heartbeat.get("current_pass_line"),
        limit=PASS_CURRENT_LINE_LIMIT,
    )[0]
    result_line = _compact_text(
        heartbeat.get("last_pass_result_line"),
        limit=PASS_RESULT_LINE_LIMIT,
    )[0]
    return {
        "schema": PASS_HEARTBEAT_SCHEMA,
        "status": "available" if current_line or result_line else "unknown_current_pass",
        "pass_id": heartbeat.get("pass_id"),
        "pass_seq": int(heartbeat.get("pass_seq") or 0),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": current_line,
        "last_pass_result_line": result_line,
        "scope_refs": _normalize_scope_refs(heartbeat.get("scope_refs") or []),
        "updated_at": heartbeat.get("updated_at"),
        "expires_at": heartbeat.get("expires_at"),
        "current_pass_updated_at": heartbeat.get("current_pass_updated_at"),
        "last_pass_completed_at": heartbeat.get("last_pass_completed_at"),
        "freshness_state": freshness,
        "source": heartbeat.get("source") or "manual_cli",
    }


def _session_last_signal_at(session: Mapping[str, Any]) -> datetime | None:
    for key in ("last_activity_at", "last_append_at", "last_query_at", "bootstrapped_at"):
        parsed = _parse_iso_datetime(session.get(key))
        if parsed is not None:
            return parsed
    return None


def _is_orphaned_active_session(
    session: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> bool:
    if session.get("ended_at"):
        return False
    last_signal = _session_last_signal_at(session)
    if last_signal is None:
        return True
    return now - last_signal > orphan_after


def _compact_external_metadata(metadata: Mapping[str, Any]) -> Dict[str, Any]:
    compact: Dict[str, Any] = {}
    for key, value in metadata.items():
        if key == "rollout_activity" and isinstance(value, Mapping):
            recent_commands = []
            for command in list(value.get("recent_commands") or [])[-5:]:
                compacted, _, _ = _compact_text(command, limit=SESSION_METADATA_TEXT_LIMIT)
                if compacted:
                    recent_commands.append(compacted)
            compact[key] = {
                "schema": value.get("schema"),
                "available": bool(value.get("available")),
                "tail_event_count": int(value.get("tail_event_count") or 0),
                "parsed_event_count": int(value.get("parsed_event_count") or 0),
                "recent_tool_names": list(value.get("recent_tool_names") or [])[-8:],
                "recent_commands": recent_commands,
                "recent_referenced_paths": list(value.get("recent_referenced_paths") or [])[-12:],
                "recent_mutation_paths": list(value.get("recent_mutation_paths") or [])[-12:],
            }
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            if isinstance(value, str):
                compact[key] = _compact_text(value, limit=SESSION_METADATA_TEXT_LIMIT)[0]
            else:
                compact[key] = value
            continue
        if isinstance(value, list):
            rows = []
            for item in list(value)[-8:]:
                if isinstance(item, str):
                    rows.append(_compact_text(item, limit=SESSION_METADATA_TEXT_LIMIT)[0])
                else:
                    rows.append(item)
            compact[key] = rows
    return compact


def _compact_session(
    session: Mapping[str, Any],
    *,
    now: datetime | None = None,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> Dict[str, Any]:
    touched_td_ids = [
        str(item)
        for item in session.get("touched_td_ids") or []
        if str(item).strip()
    ]
    touched_work_item_ids = [
        str(item)
        for item in session.get("touched_work_item_ids") or []
        if str(item).strip()
    ]
    active = not bool(session.get("ended_at"))
    last_signal = _session_last_signal_at(session)
    idle_seconds = None
    if active and last_signal is not None and now is not None:
        idle_seconds = max(0, int((now - last_signal).total_seconds()))
    orphaned_active = (
        _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
        if active and now is not None
        else False
    )
    active_claims = (
        [_compact_claim(claim) for claim in _session_active_claims(session, now=now)]
        if now is not None
        else []
    )
    claimed_td_ids = {
        str(claim.get("td_id") or "").strip()
        for claim in active_claims
        if str(claim.get("td_id") or "").strip()
    }
    claimed_work_item_ids = {
        str(claim.get("work_item_id") or "").strip()
        for claim in active_claims
        if str(claim.get("work_item_id") or "").strip()
    }
    unclaimed_touched_td_ids = [
        td_id
        for td_id in touched_td_ids
        if td_id and td_id not in claimed_td_ids
    ] if now is not None else []
    unclaimed_touched_work_item_ids = [
        work_item_id
        for work_item_id in touched_work_item_ids
        if work_item_id and work_item_id not in claimed_work_item_ids
    ] if now is not None else []
    external_title, title_truncated, title_full_chars = _compact_text(
        session.get("external_title"),
        limit=SESSION_TITLE_LIMIT,
    )
    pass_heartbeat = _compact_pass_heartbeat(
        session,
        now=now,
        orphaned_active=orphaned_active,
    )
    return {
        "session_id": str(session.get("session_id") or ""),
        "actor": session.get("actor"),
        "phase_id": session.get("phase_id"),
        "family_id": session.get("family_id"),
        "read_receipt_id": session.get("read_receipt_id"),
        "bootstrapped_at": session.get("bootstrapped_at"),
        "last_activity_at": session.get("last_activity_at"),
        "last_query_at": session.get("last_query_at"),
        "last_append_at": session.get("last_append_at"),
        "last_signal_at": last_signal.isoformat() if last_signal is not None else None,
        "idle_seconds": idle_seconds,
        "ended_at": session.get("ended_at"),
        "end_action": session.get("end_action"),
        "has_activity": bool(session.get("has_activity")),
        "touched_work": bool(session.get("touched_work")),
        "touched_td_ids": touched_td_ids,
        "touched_work_item_ids": touched_work_item_ids,
        "queries": int(session.get("queries") or 0),
        "writes": int(session.get("writes") or 0),
        "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
        "append_exempt": bool(session.get("append_exempt")),
        "append_exempt_reason": session.get("append_exempt_reason"),
        "append_exempt_refs": list(session.get("append_exempt_refs") or []),
        "append_exempted_at": session.get("append_exempted_at"),
        "stale": bool(session.get("stale")),
        "stale_reason": session.get("stale_reason"),
        "orphaned_active": orphaned_active,
        "orphaned_reason": (
            f"no activity for more than {int(orphan_after.total_seconds() // 3600)}h"
            if orphaned_active and last_signal is not None
            else ("missing activity timestamp" if orphaned_active else None)
        ),
        "external_observed": bool(session.get("external_observed")),
        "external_source": session.get("external_source"),
        "external_title": external_title,
        "external_title_truncated": title_truncated,
        "external_title_full_chars": title_full_chars,
        "external_metadata": _compact_external_metadata(dict(session.get("external_metadata") or {})),
        "pass_heartbeat": pass_heartbeat,
        "active_claims": active_claims,
        "unclaimed_touched_td_ids": unclaimed_touched_td_ids,
        "unclaimed_touched_work_item_ids": unclaimed_touched_work_item_ids,
        "open_todos_touched_this_session": int(
            session.get("open_todos_touched_this_session") or 0
        ),
    }


def _increment_bucket(
    buckets: Dict[str, Dict[str, Any]],
    key: str,
    *,
    active: bool,
    effective_active: bool,
    stale: bool,
    wrote: bool,
    unknown_scope: bool,
    orphaned_active: bool,
) -> None:
    token = str(key or "unknown").strip() or "unknown"
    bucket = buckets.setdefault(
        token,
        {
            "sessions": 0,
            "active_sessions": 0,
            "effective_active_sessions": 0,
            "stale_sessions": 0,
            "sessions_with_ledger_append": 0,
            "unknown_scope_active_sessions": 0,
            "orphaned_active_sessions": 0,
        },
    )
    bucket["sessions"] += 1
    if active:
        bucket["active_sessions"] += 1
    if effective_active:
        bucket["effective_active_sessions"] += 1
    if stale:
        bucket["stale_sessions"] += 1
    if wrote:
        bucket["sessions_with_ledger_append"] += 1
    if unknown_scope:
        bucket["unknown_scope_active_sessions"] += 1
    if orphaned_active:
        bucket["orphaned_active_sessions"] += 1


def _monitor_status(*, blocked: bool = False, watch: bool = False) -> str:
    if blocked:
        return "blocked"
    if watch:
        return "watch"
    return "clear"


def _monitor_risk_band(status: str) -> str:
    if status in {"blocked", "hard_stop"}:
        return "blocked"
    if status == "contention":
        return "review"
    if status == "watch":
        return "watch"
    return "clear"


def _quote_cli(value: Any) -> str:
    token = str(value or "").strip()
    return shlex.quote(token) if token else "<missing>"


def _wl_command(command: str, *args: str) -> str:
    suffix = " ".join(arg for arg in args if arg)
    base = f"./repo-python tools/meta/factory/work_ledger.py {command}"
    return f"{base} {suffix}".strip()


def _mission_command(*args: str) -> str:
    suffix = " ".join(arg for arg in args if arg)
    base = "./repo-python tools/meta/control/mission_transaction_preflight.py"
    return f"{base} {suffix}".strip()


def _residual_capture_command(tag: str = "concurrency_actionability") -> str:
    return (
        "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
        "--created-by codex --confidence 0.85 "
        f"--tag {shlex.quote(tag)} --tag work_ledger --summary <residual>"
    )


def _repair_row(
    *,
    row_id: str,
    failure_class: str,
    status: str,
    why_blocked: str,
    owning_surface: str,
    safe_next_command: str,
    proof_route: str,
    residual_capture_route: str,
    details: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "schema": CONCURRENCY_REPAIR_ROW_SCHEMA,
        "row_id": row_id,
        "failure_class": failure_class,
        "status": status,
        "why_blocked": why_blocked,
        "owning_surface": owning_surface,
        "safe_next_command": safe_next_command,
        "proof_route": proof_route,
        "residual_capture_route": residual_capture_route,
    }
    if details:
        row["details"] = dict(details)
    return row


def _compact_claim_collision_preview(
    claim_collisions: List[Dict[str, Any]],
    *,
    limit: int = 3,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit))
    items: List[Dict[str, Any]] = []
    for collision in claim_collisions[:safe_limit]:
        active_claims = [
            {
                "claim_id": claim.get("claim_id"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "scope_kind": claim.get("scope_kind"),
                "td_id": claim.get("td_id"),
                "path": claim.get("path"),
                "leased_until": claim.get("leased_until"),
            }
            for claim in (collision.get("active_claims") or [])[:safe_limit]
            if isinstance(claim, Mapping)
        ]
        items.append(
            {
                "scope_kind": collision.get("scope_kind"),
                "scope_id": collision.get("scope_id"),
                "td_id": collision.get("td_id"),
                "path": collision.get("path"),
                "claim_count": collision.get("claim_count"),
                "actors": list(collision.get("actors") or []),
                "active_claims_preview": active_claims,
            }
        )
    return {
        "collision_count": len(claim_collisions),
        "preview_limit": safe_limit,
        "truncated": len(claim_collisions) > safe_limit,
        "items": items,
    }


def _session_explicit_work_ids(session: Mapping[str, Any]) -> List[str]:
    ids: List[str] = []
    for key in ("touched_td_ids", "touched_work_item_ids"):
        for item in session.get(key) or []:
            token = str(item or "").strip()
            if token:
                ids.append(token)
    for claim in session.get("active_claims") or []:
        if not isinstance(claim, Mapping):
            continue
        for key in ("td_id", "work_item_id"):
            token = str(claim.get(key) or "").strip()
            if token:
                ids.append(token)
    return sorted(set(ids))


def _path_focus_root(path: str) -> str:
    token = str(path or "").strip().strip("/")
    if not token:
        return ""
    parts = [part for part in token.split("/") if part]
    if not parts:
        return ""
    basename = parts[-1]
    stem = basename.rsplit(".", 1)[0]
    if stem.startswith("test_"):
        stem = stem[5:]
    stem_tokens = [item for item in re.split(r"[^A-Za-z0-9]+", stem.lower()) if item]
    if len(stem_tokens) >= 2:
        return "_".join(stem_tokens[:2])
    if stem_tokens:
        return stem_tokens[0]
    if len(parts) == 1:
        return parts[0]
    return "/".join(parts[:2])


def _mission_focus_tokens(text: str) -> List[str]:
    tokens: List[str] = []
    for raw in re.findall(r"[A-Za-z][A-Za-z0-9_:-]{2,}", str(text or "").lower()):
        for token in re.split(r"[_:-]+", raw):
            if len(token) < 4 or token in MISSION_FOCUS_STOPWORDS:
                continue
            if token not in tokens:
                tokens.append(token)
            if len(tokens) >= 8:
                return tokens
    return tokens


def _mission_focus_keys_from_text(text: str) -> List[str]:
    tokens = _mission_focus_tokens(text)
    if len(tokens) < 2:
        return []
    keys: List[str] = []
    window = tokens[:5]
    for index, left in enumerate(window):
        for right in window[index + 1 :]:
            key = "+".join(sorted((left, right)))
            if key not in keys:
                keys.append(key)
            if len(keys) >= 6:
                return keys
    return keys


def _session_claim_path_roots(session: Mapping[str, Any]) -> List[str]:
    roots: List[str] = []
    for claim in session.get("active_claims") or []:
        if not isinstance(claim, Mapping):
            continue
        root = _path_focus_root(str(claim.get("path") or ""))
        if root:
            roots.append(root)
    return sorted(set(roots))


def _session_text_focus_keys(session: Mapping[str, Any]) -> List[str]:
    keys: List[str] = []
    title = str(session.get("external_title") or "").strip()
    for key in _mission_focus_keys_from_text(title):
        if key not in keys:
            keys.append(key)
    for claim in session.get("active_claims") or []:
        if not isinstance(claim, Mapping):
            continue
        note = str(claim.get("note") or "").strip()
        for key in _mission_focus_keys_from_text(note):
            if key not in keys:
                keys.append(key)
    return keys


def _session_is_mission_focus_candidate(session: Mapping[str, Any]) -> bool:
    try:
        open_todos_touched = int(session.get("open_todos_touched_this_session") or 0)
    except (TypeError, ValueError):
        open_todos_touched = 0
    return bool(
        session.get("external_observed")
        or session.get("touched_work")
        or open_todos_touched > 0
        or _session_claim_path_roots(session)
    )


def _compact_focus_session(session: Mapping[str, Any]) -> Dict[str, Any]:
    title = str(session.get("external_title") or "").strip()
    return {
        "session_id": session.get("session_id"),
        "actor": session.get("actor"),
        "phase_id": session.get("phase_id"),
        "family_id": session.get("family_id"),
        "idle_seconds": session.get("idle_seconds"),
        "touched_work": bool(session.get("touched_work")),
        "explicit_work_ids": _session_explicit_work_ids(session),
        "claim_path_roots": _session_claim_path_roots(session),
        "title": title if title else None,
    }


def _build_mission_focus_pressure_groups(
    effective_active_sessions: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    by_text_focus: Dict[tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    by_path_root: Dict[tuple[str, str], List[Mapping[str, Any]]] = defaultdict(list)
    for session in effective_active_sessions:
        phase_id = str(session.get("phase_id") or "unknown").strip() or "unknown"
        explicit_ids = _session_explicit_work_ids(session)
        if not explicit_ids and _session_is_mission_focus_candidate(session):
            for key in _session_text_focus_keys(session):
                by_text_focus[(phase_id, key)].append(session)
        for root in _session_claim_path_roots(session):
            by_path_root[(phase_id, root)].append(session)

    safe_limit = max(0, int(limit or 0))
    groups: List[Dict[str, Any]] = []
    for (phase_id, focus_key), sessions in by_text_focus.items():
        if len(sessions) <= 1:
            continue
        groups.append(
            {
                "group_id": f"title_focus:{phase_id}:{focus_key}",
                "pressure_kind": "unbound_topic_focus",
                "phase_id": phase_id,
                "focus_key": focus_key,
                "session_count": len(sessions),
                "actors": sorted({str(session.get("actor") or "unknown") for session in sessions}),
                "why": (
                    "Multiple live sessions share title/note focus tokens without any td/work_item binding. "
                    "They may be working the same mission while Work Ledger cannot prove ownership."
                ),
                "required_next_action": (
                    "Bind each continuing session with session-preflight --td-id/--work-item-id "
                    "or claim disjoint paths before mutation."
                ),
                "sessions": [
                    _compact_focus_session(session)
                    for session in sorted(sessions, key=_session_sort_key, reverse=True)[:safe_limit]
                ],
            }
        )

    for (phase_id, root), sessions in by_path_root.items():
        if len(sessions) <= 1:
            continue
        groups.append(
            {
                "group_id": f"path_root:{phase_id}:{root}",
                "pressure_kind": "shared_path_module",
                "phase_id": phase_id,
                "path_root": root,
                "session_count": len(sessions),
                "actors": sorted({str(session.get("actor") or "unknown") for session in sessions}),
                "why": "Multiple live sessions have path claims in the same module without a shared WorkItem binding.",
                "required_next_action": (
                    "Confirm the sessions are deliberately split, or bind them to one WorkItem/td "
                    "so mission status and closeout cannot drift apart."
                ),
                "sessions": [
                    _compact_focus_session(session)
                    for session in sorted(sessions, key=_session_sort_key, reverse=True)[:safe_limit]
                ],
            }
        )

    groups.sort(
        key=lambda row: (
            -int(row.get("session_count") or 0),
            str(row.get("pressure_kind") or ""),
            str(row.get("group_id") or ""),
        )
    )
    return groups


def _build_monitor_cards(
    *,
    risk_level: str,
    signals: List[str],
    counts: Mapping[str, Any],
    unknown_scope_count: int,
    unclaimed_touched_count: int,
    claim_collision_count: int,
    td_collision_count: int,
    claim_collision_preview: Mapping[str, Any],
    mission_focus_group_count: int = 0,
) -> List[Dict[str, Any]]:
    effective_active = int(counts.get("effective_active_sessions") or 0)
    orphaned_active = int(counts.get("orphaned_active_sessions") or 0)
    active_claims = int(counts.get("active_claims") or 0)
    stale_sessions = int(counts.get("stale_sessions") or 0)
    cohort_status = risk_level
    claims_status = _monitor_status(
        blocked=claim_collision_count > 0 or td_collision_count > 0,
        watch=active_claims > 0,
    )
    scope_hygiene_status = _monitor_status(
        blocked=unknown_scope_count > 1,
        watch=unknown_scope_count > 0 or unclaimed_touched_count > 0,
    )
    mission_focus_status = _monitor_status(watch=mission_focus_group_count > 0)
    orphaned_status = _monitor_status(watch=orphaned_active > 0)
    stale_status = _monitor_status(watch=stale_sessions > 0)
    return [
        {
            "card_id": "cohort",
            "label": "Active Session Cohort",
            "status": cohort_status,
            "risk_band": _monitor_risk_band(cohort_status),
            "count": effective_active,
            "summary": f"{effective_active} effective active sessions; signals={signals}",
            "details": {"signals": signals},
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit 12",
        },
        {
            "card_id": "claims",
            "label": "Claims And Collisions",
            "status": claims_status,
            "risk_band": _monitor_risk_band(claims_status),
            "count": active_claims,
            "summary": (
                f"{active_claims} active claims; "
                f"{claim_collision_count} claim collisions; {td_collision_count} touched-td collisions"
            ),
            "details": {
                "claim_collision_preview": dict(claim_collision_preview),
                "td_collision_count": td_collision_count,
            },
            "drilldown": "./repo-python tools/meta/control/mission_transaction_preflight.py --subject-id <id> --owned-path <path>",
        },
        {
            "card_id": "scope_hygiene",
            "label": "Scope Hygiene",
            "status": scope_hygiene_status,
            "risk_band": _monitor_risk_band(scope_hygiene_status),
            "count": unknown_scope_count + unclaimed_touched_count,
            "summary": (
                f"{unknown_scope_count} unknown-scope active sessions; "
                f"{unclaimed_touched_count} sessions touched work without live claims"
            ),
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit 12",
        },
        {
            "card_id": "mission_focus",
            "label": "Mission Focus Binding",
            "status": mission_focus_status,
            "risk_band": _monitor_risk_band(mission_focus_status),
            "count": mission_focus_group_count,
            "summary": (
                f"{mission_focus_group_count} live topic/module focus groups lack a shared WorkItem binding"
            ),
            "details": {
                "signal": "unbound_mission_focus_parallelism",
                "binding_rule": "same title/note focus or module work should claim td/work_item identity before mutation",
            },
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
        },
        {
            "card_id": "orphaned_sessions",
            "label": "Orphaned Sessions",
            "status": orphaned_status,
            "risk_band": _monitor_risk_band(orphaned_status),
            "count": orphaned_active,
            "summary": f"{orphaned_active} active sessions are older than the orphan visibility threshold",
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-sweep --dry-run",
        },
        {
            "card_id": "stale_append_obligations",
            "label": "Stale Append Obligations",
            "status": stale_status,
            "risk_band": _monitor_risk_band(stale_status),
            "count": stale_sessions,
            "summary": f"{stale_sessions} sessions have stale Work Ledger append obligations",
            "drilldown": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --limit 12",
        },
    ]


def _recommended_landing_lane(
    *,
    claim_collision_count: int,
    td_collision_count: int,
    unknown_scope_count: int,
    unclaimed_touched_count: int,
    orphaned_active_count: int,
    active_claim_count: int,
) -> str:
    if claim_collision_count or td_collision_count:
        return "resolve_claim_or_td_collision_before_landing"
    if unknown_scope_count > 1 or unclaimed_touched_count:
        return "claim_or_finalize_unknown_scope_before_landing"
    if orphaned_active_count:
        return "sweep_or_refresh_orphans_then_scoped_landing"
    if active_claim_count:
        return "scoped_landing_with_full_index_inspection"
    return "claim_then_scoped_landing"


def _awareness_claim_refs(compact: Mapping[str, Any]) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for claim in compact.get("active_claims") or []:
        if not isinstance(claim, Mapping):
            continue
        refs.append(
            {
                "claim_id": claim.get("claim_id"),
                "scope_kind": claim.get("scope_kind"),
                "td_id": claim.get("td_id"),
                "work_item_id": claim.get("work_item_id"),
                "path": claim.get("path"),
                "leased_until": claim.get("leased_until"),
            }
        )
        if len(refs) >= PASS_SCOPE_REF_LIMIT:
            break
    return refs


def _session_heartbeat_repair_row(card: Mapping[str, Any]) -> Dict[str, Any] | None:
    session_id = str(card.get("session_id") or "").strip()
    if not session_id:
        return None
    source = str(card.get("source") or "").strip()
    freshness = str(card.get("freshness_state") or "").strip()
    if source != "projected_unknown" and freshness not in {"unknown", "expired"}:
        return None
    quoted_session = _quote_cli(session_id)
    return _repair_row(
        row_id=f"heartbeat_adoption:{session_id}",
        failure_class="projected_unknown_heartbeat",
        status="watch",
        why_blocked=(
            "This live session has no explicit current-pass heartbeat, so the "
            "cohort card cannot tell whether to adopt it, wait for it, or ignore it."
        ),
        owning_surface="work_ledger.session_heartbeat",
        safe_next_command=_wl_command(
            "session-heartbeat",
            f"--session-id {quoted_session}",
            "--state orienting",
            "--now '<current pass line>'",
            "--scope-ref <work_item_or_path>",
        ),
        proof_route=_wl_command("session-status", f"--session-id {quoted_session} --full"),
        residual_capture_route=_residual_capture_command("projected_unknown_session"),
        details={
            "session_id": session_id,
            "source": source or "unknown",
            "freshness_state": freshness or "unknown",
        },
    )


def _session_lifecycle_repair_rows(card: Mapping[str, Any]) -> List[Dict[str, Any]]:
    session_id = str(card.get("session_id") or "").strip()
    if not session_id:
        return []
    quoted_session = _quote_cli(session_id)
    rows: List[Dict[str, Any]] = []
    if card.get("orphaned_active"):
        rows.append(
            _repair_row(
                row_id=f"orphaned_session:{session_id}",
                failure_class="orphaned_active_session",
                status="watch",
                why_blocked=(
                    "This session is still active past the orphan threshold; leave it "
                    "visible until session-sweep proves whether it should refresh or finalize."
                ),
                owning_surface="work_ledger.session_sweep",
                safe_next_command=_wl_command("session-sweep", "--dry-run"),
                proof_route=_wl_command("session-status", f"--session-id {quoted_session} --full"),
                residual_capture_route=_residual_capture_command("orphaned_session"),
                details={"session_id": session_id},
            )
        )
    if str(card.get("freshness_state") or "").strip() == "stale":
        rows.append(
            _repair_row(
                row_id=f"stale_session:{session_id}",
                failure_class="stale_heartbeat_or_append_obligation",
                status="watch",
                why_blocked=(
                    "This session is stale; close it with a normal finalize when the "
                    "ledger append exists, or use append-exempt finalize only for "
                    "commit/projection-only evidence."
                ),
                owning_surface="work_ledger.session_finalize",
                safe_next_command=_wl_command("session-finalize", f"--session-id {quoted_session}"),
                proof_route=_wl_command("session-status", f"--session-id {quoted_session} --full"),
                residual_capture_route=_residual_capture_command("stale_session"),
                details={"session_id": session_id},
            )
        )
    return rows


def _claim_ref_repair_rows(card: Mapping[str, Any]) -> List[Dict[str, Any]]:
    session_id = str(card.get("session_id") or "").strip()
    rows: List[Dict[str, Any]] = []
    for claim in card.get("claim_refs") or []:
        if not isinstance(claim, Mapping):
            continue
        path = str(claim.get("path") or "").strip()
        td_id = str(claim.get("td_id") or "").strip()
        work_item_id = str(claim.get("work_item_id") or "").strip()
        if path:
            proof = _wl_command("mutation-check", f"--path {_quote_cli(path)} --require-exclusive")
        elif work_item_id:
            proof = _mission_command(f"--subject-id {_quote_cli(work_item_id)}", "--control-summary")
        elif td_id:
            proof = _mission_command(f"--subject-id {_quote_cli(td_id)}", "--control-summary")
        else:
            proof = _wl_command("session-claims", "--limit 12 --full")
        rows.append(
            _repair_row(
                row_id=f"active_claim:{claim.get('claim_id') or session_id}",
                failure_class="active_claim_visibility",
                status="watch",
                why_blocked=(
                    "This session holds an active lease; prove the exact path or "
                    "WorkItem scope before another agent mutates nearby state."
                ),
                owning_surface="work_ledger.claims",
                safe_next_command=proof,
                proof_route=proof,
                residual_capture_route=_residual_capture_command("active_claim_visibility"),
                details={
                    "session_id": session_id,
                    "claim_id": claim.get("claim_id"),
                    "scope_kind": claim.get("scope_kind"),
                    "td_id": td_id,
                    "path": path,
                    "work_item_id": work_item_id,
                    "leased_until": claim.get("leased_until"),
                },
            )
        )
    return rows


def _awareness_card(compact: Mapping[str, Any]) -> Dict[str, Any]:
    heartbeat = (
        dict(compact.get("pass_heartbeat") or {})
        if isinstance(compact.get("pass_heartbeat"), Mapping)
        else {}
    )
    card = {
        "session_id": compact.get("session_id"),
        "actor": compact.get("actor"),
        "phase_id": compact.get("phase_id"),
        "freshness_state": heartbeat.get("freshness_state"),
        "idle_seconds": compact.get("idle_seconds"),
        "orphaned_active": bool(compact.get("orphaned_active")),
        "pass_id": heartbeat.get("pass_id"),
        "pass_seq": heartbeat.get("pass_seq"),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": heartbeat.get("current_pass_line"),
        "last_pass_result_line": heartbeat.get("last_pass_result_line"),
        "source": heartbeat.get("source"),
        "updated_at": heartbeat.get("updated_at"),
        "scope_refs": list(heartbeat.get("scope_refs") or []),
        "claim_refs": _awareness_claim_refs(compact),
        "touched_td_ids": list(compact.get("touched_td_ids") or []),
        "touched_work_item_ids": list(compact.get("touched_work_item_ids") or []),
    }
    repair_rows: List[Dict[str, Any]] = []
    heartbeat_row = _session_heartbeat_repair_row(card)
    if heartbeat_row:
        repair_rows.append(heartbeat_row)
    repair_rows.extend(_session_lifecycle_repair_rows(card))
    repair_rows.extend(_claim_ref_repair_rows(card))
    if repair_rows:
        card["repair_rows"] = repair_rows
    return card


def _awareness_card_sort_key(card: Mapping[str, Any]) -> tuple[Any, ...]:
    freshness_rank = {
        "live": 0,
        "idle": 1,
        "unknown": 2,
        "stale": 3,
        "expired": 4,
        "orphaned": 5,
        "ended": 6,
    }
    source = str(card.get("source") or "").strip()
    freshness = str(card.get("freshness_state") or "").strip()
    has_public_line = bool(str(card.get("current_pass_line") or "").strip())
    explicit_public = has_public_line and source in EXPLICIT_HEARTBEAT_SOURCES
    updated = _parse_iso_datetime(card.get("updated_at"))
    updated_rank = -updated.timestamp() if updated is not None else 0.0
    return (
        0 if explicit_public else (1 if has_public_line else 2),
        freshness_rank.get(freshness, 7),
        1 if card.get("orphaned_active") else 0,
        updated_rank,
        str(card.get("session_id") or ""),
    )


def _build_awareness_cards(
    *,
    effective_active_compacts: Sequence[Mapping[str, Any]],
    orphaned_active_compacts: Sequence[Mapping[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    safe_limit = max(0, int(limit or 0))
    if safe_limit == 0:
        return []
    rows: List[Dict[str, Any]] = []
    for compact in list(effective_active_compacts) + list(orphaned_active_compacts):
        rows.append(_awareness_card(compact))
    rows.sort(key=_awareness_card_sort_key)
    return rows[:safe_limit]


def _heartbeat_participation_summary(
    *,
    effective_active_compacts: Sequence[Mapping[str, Any]],
    awareness_cards: Sequence[Mapping[str, Any]],
    limit: int,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    effective_cards = [_awareness_card(compact) for compact in effective_active_compacts]
    source_counts: Dict[str, int] = defaultdict(int)
    freshness_counts: Dict[str, int] = defaultdict(int)
    explicit_session_ids: List[str] = []
    projected_unknown_session_ids: List[str] = []

    for card in effective_cards:
        source = str(card.get("source") or "unknown").strip() or "unknown"
        freshness = str(card.get("freshness_state") or "unknown").strip() or "unknown"
        session_id = str(card.get("session_id") or "").strip()
        has_current_line = bool(str(card.get("current_pass_line") or "").strip())
        source_counts[source] += 1
        freshness_counts[freshness] += 1
        if has_current_line and source in EXPLICIT_HEARTBEAT_SOURCES:
            explicit_session_ids.append(session_id)
        if source == "projected_unknown":
            projected_unknown_session_ids.append(session_id)

    total = len(effective_cards)
    explicit_count = len(explicit_session_ids)
    projected_unknown_count = len(projected_unknown_session_ids)
    missing_current_pass_count = max(0, total - explicit_count)
    if total == 0:
        status = "none_active"
    elif explicit_count == total:
        status = "complete"
    elif explicit_count == 0 and projected_unknown_count == total:
        status = "unknown_only"
    else:
        status = "partial"

    first_explicit_index: int | None = None
    first_projected_unknown_index: int | None = None
    for index, card in enumerate(awareness_cards):
        source = str(card.get("source") or "").strip()
        has_current_line = bool(str(card.get("current_pass_line") or "").strip())
        if (
            first_explicit_index is None
            and has_current_line
            and source in EXPLICIT_HEARTBEAT_SOURCES
        ):
            first_explicit_index = index
        if first_projected_unknown_index is None and source == "projected_unknown":
            first_projected_unknown_index = index

    return {
        "schema": HEARTBEAT_PARTICIPATION_SCHEMA,
        "scope": "effective_active_sessions",
        "status": status,
        "effective_active_sessions": total,
        "explicit_current_pass_count": explicit_count,
        "projected_unknown_count": projected_unknown_count,
        "missing_current_pass_count": missing_current_pass_count,
        "participation_ratio": round(explicit_count / total, 3) if total else 0.0,
        "source_counts": dict(sorted(source_counts.items())),
        "freshness_counts": dict(sorted(freshness_counts.items())),
        "explicit_session_ids": explicit_session_ids[:safe_limit],
        "projected_unknown_session_ids": projected_unknown_session_ids[:safe_limit],
        "first_contact": {
            "first_card_session_id": (
                str(awareness_cards[0].get("session_id") or "")
                if awareness_cards
                else None
            ),
            "explicit_heartbeat_visible_first": first_explicit_index == 0,
            "first_explicit_heartbeat_index": first_explicit_index,
            "first_projected_unknown_index": first_projected_unknown_index,
        },
        "policy": {
            "projected_unknown_is_truthful_fallback": True,
            "no_transcript_summarization": True,
        },
    }


def _claim_collision_safe_command(collision: Mapping[str, Any]) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = sorted({str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")})
    claim_ids = [str(claim.get("claim_id") or "") for claim in claims if claim.get("claim_id")]
    scope_kind = str(collision.get("scope_kind") or "").strip()
    path = str(collision.get("path") or "").strip()
    work_item_id = str(collision.get("work_item_id") or "").strip()
    td_id = str(collision.get("td_id") or "").strip()
    if len(sessions) == 1 and len(claim_ids) > 1:
        return _wl_command(
            "session-release-claim",
            f"--session-id {_quote_cli(sessions[0])}",
            f"--claim-id {_quote_cli(claim_ids[-1])}",
            "--reason duplicate_same_session_claim",
        )
    if path:
        return _wl_command("mutation-check", f"--path {_quote_cli(path)} --require-exclusive")
    if work_item_id:
        return _mission_command(f"--subject-id {_quote_cli(work_item_id)}", "--control-summary")
    if td_id:
        return _mission_command(f"--subject-id {_quote_cli(td_id)}", "--control-summary")
    return _wl_command("session-claims", f"--limit 12 --full # scope_kind={_quote_cli(scope_kind)}")


def _claim_collision_failure_class(collision: Mapping[str, Any]) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
    if len(sessions) == 1 and len(claims) > 1:
        return "duplicate_same_session_claim"
    if collision.get("path"):
        return "path_claim_collision"
    if collision.get("work_item_id"):
        return "work_item_claim_collision"
    if collision.get("td_id"):
        return "td_claim_collision"
    return "claim_collision"


def _claim_collision_repair_rows(
    claim_collisions: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for collision in list(claim_collisions)[: max(0, int(limit or 0))]:
        if not isinstance(collision, Mapping):
            continue
        failure_class = _claim_collision_failure_class(collision)
        safe_command = _claim_collision_safe_command(collision)
        rows.append(
            _repair_row(
                row_id=f"{failure_class}:{collision.get('scope_id') or len(rows)}",
                failure_class=failure_class,
                status="blocked" if failure_class != "duplicate_same_session_claim" else "watch",
                why_blocked=(
                    "More than one active Work Ledger lease covers the same mutation scope; "
                    "a writer must prove exclusivity or release/supersede duplicate claims before editing."
                ),
                owning_surface="work_ledger.claims",
                safe_next_command=safe_command,
                proof_route=safe_command,
                residual_capture_route=_residual_capture_command(failure_class),
                details={
                    "scope_kind": collision.get("scope_kind"),
                    "scope_id": collision.get("scope_id"),
                    "claim_count": collision.get("claim_count"),
                    "actors": list(collision.get("actors") or []),
                },
            )
        )
    return rows


def _td_collision_repair_rows(
    td_id_collisions: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for collision in list(td_id_collisions)[: max(0, int(limit or 0))]:
        if not isinstance(collision, Mapping):
            continue
        td_id = str(collision.get("td_id") or "").strip()
        proof = _mission_command(f"--subject-id {_quote_cli(td_id)}", "--control-summary")
        rows.append(
            _repair_row(
                row_id=f"td_contention:{td_id}",
                failure_class="td_id_contention",
                status="blocked",
                why_blocked=(
                    "Multiple active sessions touched the same Work Ledger td_id; "
                    "choose one owner or append a progress/close event before parallel mutation."
                ),
                owning_surface="work_ledger.thread_claims",
                safe_next_command=proof,
                proof_route=_wl_command("session-status", "--overview --with-session-cards --limit 12"),
                residual_capture_route=_residual_capture_command("td_id_contention"),
                details={
                    "td_id": td_id,
                    "session_count": collision.get("session_count"),
                    "actors": list(collision.get("actors") or []),
                },
            )
        )
    return rows


def _unclaimed_touched_repair_rows(
    sessions: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for session in list(sessions)[: max(0, int(limit or 0))]:
        if not isinstance(session, Mapping):
            continue
        session_id = str(session.get("session_id") or "").strip()
        td_ids = [str(item) for item in session.get("unclaimed_touched_td_ids") or [] if item]
        work_item_ids = [
            str(item) for item in session.get("unclaimed_touched_work_item_ids") or [] if item
        ]
        if td_ids:
            safe = _wl_command(
                "session-claim",
                f"--session-id {_quote_cli(session_id)}",
                f"--td-id {_quote_cli(td_ids[0])}",
                "--lease-minutes 30",
                "--require-exclusive",
            )
            proof = safe
            subject = td_ids[0]
        elif work_item_ids:
            safe = (
                "./repo-python tools/meta/control/work_landing.py begin "
                f"--subject-id {_quote_cli(work_item_ids[0])} --session-id {_quote_cli(session_id)}"
            )
            proof = _mission_command(f"--subject-id {_quote_cli(work_item_ids[0])}", "--control-summary")
            subject = work_item_ids[0]
        else:
            safe = _wl_command("session-status", f"--session-id {_quote_cli(session_id)} --full")
            proof = safe
            subject = ""
        rows.append(
            _repair_row(
                row_id=f"unclaimed_touched_work:{session_id}:{subject}",
                failure_class="unclaimed_touched_work",
                status="watch",
                why_blocked=(
                    "This active session touched Work Ledger work without a live claim; "
                    "claim the touched td/work-item before mutation or finalize stale work."
                ),
                owning_surface="work_ledger.session_claims",
                safe_next_command=safe,
                proof_route=proof,
                residual_capture_route=_residual_capture_command("unclaimed_touched_work"),
                details={
                    "session_id": session_id,
                    "unclaimed_touched_td_ids": td_ids,
                    "unclaimed_touched_work_item_ids": work_item_ids,
                },
            )
        )
    return rows


def _overview_repair_rows(
    *,
    claim_collisions: Sequence[Mapping[str, Any]],
    td_id_collisions: Sequence[Mapping[str, Any]],
    unclaimed_touched_sessions: Sequence[Mapping[str, Any]],
    mission_focus_groups: Sequence[Mapping[str, Any]],
    orphaned_active_sessions: Sequence[Mapping[str, Any]],
    stale_sessions: Sequence[Mapping[str, Any]],
    heartbeat_participation: Mapping[str, Any],
    limit: int,
) -> List[Dict[str, Any]]:
    safe_limit = max(0, int(limit or 0))
    row_limit = max(1, safe_limit)
    rows: List[Dict[str, Any]] = []
    rows.extend(_claim_collision_repair_rows(claim_collisions, limit=row_limit))
    rows.extend(_td_collision_repair_rows(td_id_collisions, limit=row_limit))
    rows.extend(_unclaimed_touched_repair_rows(unclaimed_touched_sessions, limit=row_limit))
    projected_unknown_count = int(heartbeat_participation.get("projected_unknown_count") or 0)
    if projected_unknown_count:
        rows.append(
            _repair_row(
                row_id="heartbeat_projected_unknown",
                failure_class="projected_unknown_heartbeat",
                status="watch",
                why_blocked=(
                    f"{projected_unknown_count} effective active session(s) have no explicit "
                    "current-pass heartbeat; agents should adopt/refresh them before assuming "
                    "they are safe parallel peers."
                ),
                owning_surface="work_ledger.session_heartbeat",
                safe_next_command=_wl_command(
                    "session-heartbeat",
                    "--session-id <session_id>",
                    "--state orienting",
                    "--now '<current pass line>'",
                    "--scope-ref <work_item_or_path>",
                ),
                proof_route=_wl_command("session-status", "--overview --cards-only --limit 12"),
                residual_capture_route=_residual_capture_command("projected_unknown_session"),
                details={
                    "sample_session_ids": list(
                        heartbeat_participation.get("projected_unknown_session_ids") or []
                    )[:row_limit],
                    "participation_ratio": heartbeat_participation.get("participation_ratio"),
                },
            )
        )
    if mission_focus_groups:
        rows.append(
            _repair_row(
                row_id="mission_focus_binding",
                failure_class="unbound_mission_focus_parallelism",
                status="watch",
                why_blocked=(
                    "Multiple live sessions appear to share topic/module focus without a "
                    "shared WorkItem claim; bind them or split path claims before mutation."
                ),
                owning_surface="work_ledger.session_preflight",
                safe_next_command=_wl_command(
                    "session-preflight",
                    "--session-id <session_id>",
                    "--td-id <work_item_id>",
                    "--claim-path <path>",
                ),
                proof_route=_wl_command("session-status", "--overview --with-session-cards --limit 12"),
                residual_capture_route=_residual_capture_command("mission_focus_binding"),
                details={
                    "group_count": len(mission_focus_groups),
                    "sample_group_ids": [
                        str(row.get("group_id") or "") for row in list(mission_focus_groups)[:row_limit]
                    ],
                },
            )
        )
    if orphaned_active_sessions:
        rows.append(
            _repair_row(
                row_id="orphaned_session_sweep",
                failure_class="orphaned_active_session",
                status="watch",
                why_blocked=(
                    "One or more active sessions are older than the orphan visibility threshold; "
                    "sweep or refresh them before treating the active count as live coordination pressure."
                ),
                owning_surface="work_ledger.session_sweep",
                safe_next_command=_wl_command("session-sweep", "--dry-run"),
                proof_route=_wl_command("session-status", "--overview --with-session-cards --limit 12"),
                residual_capture_route=_residual_capture_command("orphaned_session"),
                details={"session_count": len(orphaned_active_sessions)},
            )
        )
    if stale_sessions:
        first_stale = next((item for item in stale_sessions if isinstance(item, Mapping)), {})
        session_id = str(first_stale.get("session_id") or "<session_id>")
        rows.append(
            _repair_row(
                row_id="stale_append_or_finalize",
                failure_class="stale_append_or_finalize",
                status="watch",
                why_blocked=(
                    "Stale sessions may still owe Work Ledger append/finalize work; close "
                    "normal sessions with session-finalize, and use append-exempt finalize "
                    "only for commit/projection-only evidence."
                ),
                owning_surface="work_ledger.session_finalize",
                safe_next_command=_wl_command("session-finalize", f"--session-id {_quote_cli(session_id)}"),
                proof_route=_wl_command("session-status", "--overview --with-session-cards --limit 12"),
                residual_capture_route=_residual_capture_command("stale_append_obligation"),
                details={"session_count": len(stale_sessions), "sample_session_id": session_id},
            )
        )
    return rows[:row_limit]


def _attach_monitor_repair_rows(
    cards: Sequence[Mapping[str, Any]],
    repair_rows: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    by_card: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for row in repair_rows:
        if not isinstance(row, Mapping):
            continue
        failure_class = str(row.get("failure_class") or "").strip()
        if failure_class in {
            "claim_collision",
            "duplicate_same_session_claim",
            "path_claim_collision",
            "work_item_claim_collision",
            "td_claim_collision",
            "td_id_contention",
        }:
            by_card["claims"].append(dict(row))
        elif failure_class in {"unclaimed_touched_work"}:
            by_card["scope_hygiene"].append(dict(row))
        elif failure_class in {"projected_unknown_heartbeat"}:
            by_card["cohort"].append(dict(row))
        elif failure_class in {"unbound_mission_focus_parallelism"}:
            by_card["mission_focus"].append(dict(row))
        elif failure_class in {"orphaned_active_session"}:
            by_card["orphaned_sessions"].append(dict(row))
        elif failure_class in {"stale_append_or_finalize"}:
            by_card["stale_append_obligations"].append(dict(row))
    enriched: List[Dict[str, Any]] = []
    for card in cards:
        row = dict(card)
        card_id = str(row.get("card_id") or "")
        if by_card.get(card_id):
            row["repair_rows"] = by_card[card_id]
        enriched.append(row)
    return enriched


def build_session_cohort_overview(
    status: Mapping[str, Any],
    *,
    limit: int = SESSION_COHORT_OVERVIEW_LIMIT,
    now: datetime | None = None,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> Dict[str, Any]:
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    sessions = [dict(raw) for raw in sessions_payload.values() if isinstance(raw, Mapping)]
    active_sessions = [session for session in sessions if not session.get("ended_at")]
    orphaned_active_sessions = [
        session
        for session in active_sessions
        if _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
    ]
    effective_active_sessions = [
        session
        for session in active_sessions
        if not _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
    ]
    stale_sessions = [session for session in sessions if bool(session.get("stale"))]
    active_sessions.sort(key=_session_sort_key, reverse=True)
    effective_active_sessions.sort(key=_session_sort_key, reverse=True)
    orphaned_active_sessions.sort(key=_session_sort_key, reverse=True)
    stale_sessions.sort(key=_session_sort_key, reverse=True)

    actors: Dict[str, Dict[str, Any]] = {}
    phases: Dict[str, Dict[str, Any]] = {}
    td_active_sessions: Dict[str, List[Dict[str, Any]]] = {}
    unknown_scope_active: List[Dict[str, Any]] = []
    unclaimed_touched_sessions: List[Dict[str, Any]] = []
    active_claims_flat: List[Dict[str, Any]] = []
    effective_active_compacts: List[Dict[str, Any]] = []

    for session in sessions:
        active = not bool(session.get("ended_at"))
        orphaned_active = (
            _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
            if active
            else False
        )
        effective_active = active and not orphaned_active
        compact: Dict[str, Any] | None = None
        if effective_active:
            compact = _compact_session(session, now=now, orphan_after=orphan_after)
            effective_active_compacts.append(compact)
            for claim in compact.get("active_claims") or []:
                claim_row = dict(claim)
                claim_row["session_id"] = compact["session_id"]
                claim_row["actor"] = compact["actor"]
                active_claims_flat.append(claim_row)
        unknown_scope = (
            effective_active
            and compact is not None
            and bool(session.get("touched_work"))
            and not compact["touched_td_ids"]
            and not compact["touched_work_item_ids"]
            and not compact.get("active_claims")
        )
        _increment_bucket(
            actors,
            str(session.get("actor") or "unknown"),
            active=active,
            effective_active=effective_active,
            stale=bool(session.get("stale")),
            wrote=bool(session.get("session_had_ledger_append")),
            unknown_scope=unknown_scope,
            orphaned_active=orphaned_active,
        )
        _increment_bucket(
            phases,
            str(session.get("phase_id") or "unknown"),
            active=active,
            effective_active=effective_active,
            stale=bool(session.get("stale")),
            wrote=bool(session.get("session_had_ledger_append")),
            unknown_scope=unknown_scope,
            orphaned_active=orphaned_active,
        )
        if not effective_active:
            continue
        if compact is None:
            continue
        if unknown_scope:
            unknown_scope_active.append(compact)
        if compact.get("unclaimed_touched_td_ids") or compact.get("unclaimed_touched_work_item_ids"):
            unclaimed_touched_sessions.append(compact)
        for td_id in compact["touched_td_ids"]:
            td_active_sessions.setdefault(td_id, []).append(compact)

    td_id_collisions = [
        {
            "td_id": td_id,
            "session_count": len(items),
            "actors": sorted({str(item.get("actor") or "unknown") for item in items}),
            "active_sessions": sorted(items, key=_session_sort_key, reverse=True),
        }
        for td_id, items in td_active_sessions.items()
        if len(items) > 1
    ]
    td_id_collisions.sort(key=lambda item: (-int(item["session_count"]), str(item["td_id"])))

    claim_collisions = _claim_collision_rows(active_claims_flat)
    mission_focus_groups = _build_mission_focus_pressure_groups(
        effective_active_compacts,
        limit=max(0, int(limit or 0)),
    )

    signals: List[str] = []
    if len(effective_active_sessions) > 1:
        signals.append("multiple_active_sessions")
    if mission_focus_groups:
        signals.append("unbound_mission_focus_parallelism")
    if len(unknown_scope_active) > 1:
        signals.append("unknown_scope_parallelism")
    if td_id_collisions:
        signals.append("td_id_contention")
    if claim_collisions:
        signals.append("claim_collision")
    if unclaimed_touched_sessions:
        signals.append("unclaimed_touched_work")
    if orphaned_active_sessions:
        signals.append("orphaned_active_sessions")
    if stale_sessions:
        signals.append("stale_session_backlog")

    risk_level = "clear"
    if td_id_collisions or claim_collisions or len(unknown_scope_active) > 1:
        risk_level = "contention"
    elif (
        len(effective_active_sessions) > 1
        or mission_focus_groups
        or unclaimed_touched_sessions
        or stale_sessions
        or orphaned_active_sessions
    ):
        risk_level = "watch"

    recommended_actions: List[str] = []
    if claim_collisions:
        recommended_actions.append(
            "Resolve claim collisions: two or more agents hold a live lease on the same td_* or path scope. "
            "Release one claim (`session-release-claim --td-id <td>` or `--path <path>`) or wait for the shorter lease to expire before continuing."
        )
    if len(unknown_scope_active) > 1:
        recommended_actions.append(
            "Ask active Type A agents to mark session-activity with --td-id before overlapping writes, "
            "or claim the slice explicitly via `session-claim --td-id <td> --lease-minutes <N>`."
        )
    if mission_focus_groups:
        recommended_actions.append(
            "Bind same-topic or same-module missions before resuming parallel work: rerun `session-preflight "
            "--td-id <work_item_id>` for each continuing mission, or split explicit path claims so the cohort "
            "overview can prove ownership instead of inferring focus from title, note, or module overlap."
        )
    if unclaimed_touched_sessions:
        recommended_actions.append(
            "One or more active sessions touched td_* work without a live claim. "
            "Use `session-claim --td-id <td> --lease-minutes <N>` before mutation, or release/finalize the session if the touch is stale."
        )
    if td_id_collisions:
        recommended_actions.append(
            "Resolve touched-thread contention by assigning one owner or appending a progress note before continuing."
        )
    if orphaned_active_sessions:
        recommended_actions.append(
            "Finalize or refresh orphaned active sessions (`session-sweep`) before treating the active count as live coordination pressure."
        )
    if stale_sessions:
        recommended_actions.append(
            "Close stale append obligations with explicit ledger progress or resolution events."
        )
    if len(effective_active_sessions) > 1 and not recommended_actions:
        recommended_actions.append(
            "Use the active session list as the shared coordinator view before starting another autonomous seed."
        )

    safe_limit = max(0, int(limit or 0))
    counts = dict(status.get("counts") or {})
    counts["effective_active_sessions"] = len(effective_active_sessions)
    counts["orphaned_active_sessions"] = len(orphaned_active_sessions)
    counts["active_claims"] = len(active_claims_flat)
    counts["claim_collisions"] = len(claim_collisions)
    counts["unclaimed_touched_sessions"] = len(unclaimed_touched_sessions)
    counts["mission_focus_pressure_groups"] = len(mission_focus_groups)
    recent_sweep_events = [
        dict(entry)
        for entry in (status.get("recent_sweep_events") or [])
        if isinstance(entry, Mapping)
    ][-safe_limit:]
    active_claims_flat.sort(key=lambda c: str(c.get("leased_until") or ""), reverse=True)
    claim_collision_preview = _compact_claim_collision_preview(claim_collisions)
    awareness_cards = _build_awareness_cards(
        effective_active_compacts=effective_active_compacts,
        orphaned_active_compacts=[
            _compact_session(session, now=now, orphan_after=orphan_after)
            for session in orphaned_active_sessions
        ],
        limit=safe_limit,
    )
    heartbeat_participation = _heartbeat_participation_summary(
        effective_active_compacts=effective_active_compacts,
        awareness_cards=awareness_cards,
        limit=safe_limit,
    )
    counts["heartbeat_explicit_current_pass_sessions"] = heartbeat_participation[
        "explicit_current_pass_count"
    ]
    counts["heartbeat_projected_unknown_sessions"] = heartbeat_participation[
        "projected_unknown_count"
    ]
    if heartbeat_participation["status"] in {"partial", "unknown_only"}:
        recommended_actions.append(
            "Participating live sessions that can write should publish `session-heartbeat` at long pass start, plan pivot, before validation, and closeout; imported or read-only sessions may truthfully remain projected_unknown."
        )
    repair_rows = _overview_repair_rows(
        claim_collisions=claim_collisions,
        td_id_collisions=td_id_collisions,
        unclaimed_touched_sessions=unclaimed_touched_sessions,
        mission_focus_groups=mission_focus_groups,
        orphaned_active_sessions=orphaned_active_sessions,
        stale_sessions=stale_sessions,
        heartbeat_participation=heartbeat_participation,
        limit=safe_limit,
    )
    monitor_cards = _build_monitor_cards(
        risk_level=risk_level,
        signals=signals,
        counts=counts,
        unknown_scope_count=len(unknown_scope_active),
        unclaimed_touched_count=len(unclaimed_touched_sessions),
        claim_collision_count=len(claim_collisions),
        td_collision_count=len(td_id_collisions),
        claim_collision_preview=claim_collision_preview,
        mission_focus_group_count=len(mission_focus_groups),
    )
    monitor_cards = _attach_monitor_repair_rows(monitor_cards, repair_rows)
    landing_lane = _recommended_landing_lane(
        claim_collision_count=len(claim_collisions),
        td_collision_count=len(td_id_collisions),
        unknown_scope_count=len(unknown_scope_active),
        unclaimed_touched_count=len(unclaimed_touched_sessions),
        orphaned_active_count=len(orphaned_active_sessions),
        active_claim_count=len(active_claims_flat),
    )
    return {
        "schema": SESSION_COHORT_OVERVIEW_SCHEMA,
        "generated_at": status.get("generated_at") or work_ledger.utc_now(),
        "orphan_after_seconds": int(orphan_after.total_seconds()),
        "counts": counts,
        "monitor_cards": monitor_cards,
        "awareness_cards": awareness_cards,
        "heartbeat_participation": heartbeat_participation,
        "repair_rows": repair_rows,
        "recommended_landing_lane": landing_lane,
        "active_sessions": [
            _compact_session(session, now=now, orphan_after=orphan_after)
            for session in active_sessions[:safe_limit]
        ],
        "effective_active_sessions": [
            _compact_session(session, now=now, orphan_after=orphan_after)
            for session in effective_active_sessions[:safe_limit]
        ],
        "orphaned_active_sessions": [
            _compact_session(session, now=now, orphan_after=orphan_after)
            for session in orphaned_active_sessions[:safe_limit]
        ],
        "stale_sessions": [
            _compact_session(session, now=now, orphan_after=orphan_after)
            for session in stale_sessions[:safe_limit]
        ],
        "actors": actors,
        "phases": phases,
        "contention": {
            "risk_level": risk_level,
            "signals": signals,
            "td_id_collisions": td_id_collisions[:safe_limit],
            "mission_focus_pressure_groups": mission_focus_groups[:safe_limit],
            "unknown_scope_active_sessions": unknown_scope_active[:safe_limit],
            "unclaimed_touched_sessions": unclaimed_touched_sessions[:safe_limit],
            "orphaned_active_sessions": [
                _compact_session(session, now=now, orphan_after=orphan_after)
                for session in orphaned_active_sessions[:safe_limit]
            ],
            "claim_collisions": claim_collisions[:safe_limit],
        },
        "active_claims": active_claims_flat[:safe_limit],
        "recent_sweep_events": recent_sweep_events,
        "recommended_actions": recommended_actions,
    }


def _session_sweep_preview_rows(
    status: Mapping[str, Any],
    *,
    now: datetime,
    orphan_sweep_after: timedelta,
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    for session_id, session in sessions_payload.items():
        if not isinstance(session, Mapping) or session.get("ended_at"):
            continue
        if not _is_orphaned_active_session(session, now=now, orphan_after=orphan_sweep_after):
            continue
        last_signal = _session_last_signal_at(session)
        rows.append(
            {
                "session_id": str(session_id),
                "actor": str(session.get("actor") or "unknown"),
                "phase_id": str(session.get("phase_id") or ""),
                "last_signal_at": last_signal.isoformat() if last_signal is not None else None,
                "idle_hours": (
                    round((now - last_signal).total_seconds() / 3600.0, 2)
                    if last_signal is not None
                    else None
                ),
                "touched_td_ids": list(session.get("touched_td_ids") or [])[:8],
                "touched_work_item_ids": list(session.get("touched_work_item_ids") or [])[:8],
                "active_claims": [
                    _compact_claim(claim)
                    for claim in _session_active_claims(session, now=now)
                ],
            }
        )
    rows.sort(key=lambda item: (item.get("idle_hours") is None, -(item.get("idle_hours") or 0.0), str(item.get("session_id") or "")))
    return rows[: max(0, limit)]


def _expired_claim_preview_rows(
    status: Mapping[str, Any],
    *,
    now: datetime,
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    for session_id, session in sessions_payload.items():
        if not isinstance(session, Mapping):
            continue
        claims = session.get("claims") if isinstance(session.get("claims"), list) else []
        for claim in claims:
            if not isinstance(claim, Mapping):
                continue
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            leased_until = _parse_iso_datetime(claim.get("leased_until"))
            if leased_until is not None and leased_until > now:
                continue
            row = _compact_claim(claim)
            row["session_id"] = str(session_id)
            row["actor"] = str(session.get("actor") or "unknown")
            row["phase_id"] = str(session.get("phase_id") or "")
            rows.append(row)
    rows.sort(key=lambda item: str(item.get("leased_until") or ""))
    return rows[: max(0, limit)]


def _active_claim_rows_for_pressure(
    status: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    for session_id, session in sessions_payload.items():
        if not isinstance(session, Mapping) or session.get("ended_at"):
            continue
        if _is_orphaned_active_session(session, now=now, orphan_after=orphan_after):
            continue
        for claim in _session_active_claims(session, now=now):
            row = _compact_claim(claim)
            row["session_id"] = str(session_id)
            row["actor"] = str(session.get("actor") or "unknown")
            row["phase_id"] = str(session.get("phase_id") or "")
            rows.append(row)
    rows.sort(key=lambda item: str(item.get("leased_until") or ""), reverse=True)
    return rows


def _claim_covers_dirty_path(claim: Mapping[str, Any], dirty_path: str) -> bool:
    scope_kind, scope_id = _normalize_claim_scope(claim)
    if scope_kind != CLAIM_SCOPE_PATH or not scope_id:
        return False
    try:
        return _path_scope_overlaps(scope_id, dirty_path)
    except Exception:
        return False


def _normalize_dirty_path(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    if text.startswith("./"):
        text = text[2:]
    text = text.replace("\\", "/")
    parts = [part for part in PurePosixPath(text).parts if part not in ("", ".")]
    if not parts or any(part == ".." for part in parts):
        return ""
    return PurePosixPath(*parts).as_posix()


def _dirty_path_owner_hint(path: str) -> Dict[str, str]:
    if path.startswith("state/task_ledger/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "task_ledger_projection",
            "recommended_action": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
        }
    if path.startswith("codex/ledger/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "work_ledger_projection",
            "recommended_action": "./repo-python tools/meta/factory/work_ledger.py project --phase-id 09_54 --family-id 09 --check",
        }
    if path.startswith("state/prompt_ledger/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "prompt_ledger_projection",
            "recommended_action": "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        }
    if path.startswith("state/system_atlas/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "system_atlas_projection",
            "recommended_action": "./repo-python kernel.py --facts --band cluster_flag",
        }
    if path.startswith("codex/doctrine/paper_modules/") and (
        path.endswith("_index.json")
        or path.endswith("_validation_report.json")
        or path.endswith("_route_coverage.json")
        or path.endswith("README.md")
    ):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "paper_module_index_projection",
            "recommended_action": "./repo-python tools/meta/factory/build_paper_module_index.py --check --report",
        }
    return {
        "class": "unclaimed_source_dirty",
        "owner_surface": "unknown_or_source_owner",
        "recommended_action": "./checkpoint --rescue-ref --dry-run --message \"rescue: dirty-tree finalizer preservation\"",
    }


def _dirty_path_rows_for_pressure(
    dirty_paths: List[str],
    *,
    active_claims: List[Dict[str, Any]],
    limit: int,
) -> tuple[List[Dict[str, Any]], Dict[str, int]]:
    rows: List[Dict[str, Any]] = []
    counts: Dict[str, int] = {}
    for path in sorted({_normalize_dirty_path(path) for path in dirty_paths}):
        if not path:
            continue
        matching_claims = [
            claim
            for claim in active_claims
            if _claim_covers_dirty_path(claim, path)
        ]
        if matching_claims:
            row = {
                "path": path,
                "class": "active_claim_dirty",
                "owner_surface": "active_work_ledger_claim",
                "recommended_action": "wait_for_claim_release_or_finalize_session_before_sweeping",
                "active_claims": matching_claims[:3],
            }
        else:
            row = {"path": path, **_dirty_path_owner_hint(path)}
        counts[row["class"]] = counts.get(row["class"], 0) + 1
        if len(rows) < max(0, limit):
            rows.append(row)
    return rows, counts


def _dirty_path_pressure_row(path: str, active_claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    matching_claims = [
        claim
        for claim in active_claims
        if _claim_covers_dirty_path(claim, path)
    ]
    if matching_claims:
        return {
            "path": path,
            "class": "active_claim_dirty",
            "owner_surface": "active_work_ledger_claim",
            "recommended_action": "wait_for_claim_release_or_finalize_session_before_sweeping",
            "active_claims": matching_claims[:3],
        }
    return {"path": path, **_dirty_path_owner_hint(path)}


def _drift_owner_hint(rows: List[Dict[str, Any]]) -> str:
    classes = {str(row.get("class") or "") for row in rows if row.get("class")}
    if not classes:
        return "unknown"
    if "active_claim_dirty" in classes:
        return "active_claim" if len(classes) == 1 else "mixed"
    if classes == {"generated_owner_dirty"}:
        return "generated_owner"
    if classes == {"unclaimed_source_dirty"}:
        return "unclaimed_writer"
    return "mixed"


def _drift_next_safe_action(owner_hint: str, *, reason: str) -> str:
    if reason == "base_head_mismatch":
        return "./repo-python tools/meta/control/closeout_executor.py plan --json --compact"
    if owner_hint == "active_claim":
        return "wait_for_claim_release_or_finalize_session_before_repeating_rescue"
    if owner_hint == "generated_owner":
        return "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --fast"
    if owner_hint == "unclaimed_writer":
        return "identify_or_claim_writer_before_repeating_rescue"
    if owner_hint == "mixed":
        return "run closeout plan and owner-lane classifier; do not repeat rescue until movement quiets"
    return "inspect rescue_coverage drift samples before repeating rescue"


def _drift_class_for(owner_hint: str, *, reason: str) -> str:
    if reason == "base_head_mismatch":
        return "head_moved_after_rescue"
    if owner_hint == "active_claim":
        return "active_claim_writer_moved"
    if owner_hint == "generated_owner":
        return "generated_owner_moved"
    if owner_hint == "unclaimed_writer":
        return "unclaimed_writer_drift"
    if owner_hint == "mixed":
        return "mixed_dirty_tree_movement"
    if reason == "content_differs_from_rescue_commit":
        return "dirty_content_moved_after_rescue"
    if reason == "dirty_pathset_mismatch":
        return "dirty_pathset_moved_after_rescue"
    return "moving_dirty_tree_during_escrow"


def _drift_annotations(
    paths: List[str],
    *,
    active_claims: List[Dict[str, Any]],
    reason: str,
    limit: int = 5,
) -> Dict[str, Any]:
    rows = [
        _dirty_path_pressure_row(path, active_claims)
        for path in sorted({_normalize_dirty_path(path) for path in paths if path})
    ]
    owner_hint = _drift_owner_hint(rows)
    return {
        "drift_class": _drift_class_for(owner_hint, reason=reason),
        "drift_owner_hint": owner_hint,
        "drift_samples": rows[: max(0, limit)],
        "drift_next_safe_action": _drift_next_safe_action(owner_hint, reason=reason),
    }


def _run_git_pressure_read(repo_root: Path, args: List[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=repo_root,
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError:
        return None


def _dirty_rescue_run_id(ref: str) -> str | None:
    prefix = f"{DIRTY_TREE_RESCUE_REF_PREFIX}/"
    if not ref.startswith(prefix):
        return None
    return ref[len(prefix) :]


def _dirty_pathset_fingerprint(*, base_head: str | None, paths: List[str]) -> str:
    payload = {
        "base_head": base_head or "",
        "paths": sorted({_normalize_dirty_path(path) for path in paths if path}),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _dirty_tree_rescue_manifest(
    repo_root: Path,
    *,
    ref: str,
    commit: str,
) -> Dict[str, Any]:
    run_id = _dirty_rescue_run_id(ref)
    if not run_id:
        return {"status": "unavailable", "reason": "unexpected_rescue_ref_shape"}
    manifest_path = f"{DIRTY_TREE_RESCUE_MANIFEST_PREFIX}/{run_id}/manifest.json"
    proc = _run_git_pressure_read(repo_root, ["show", f"{commit}:{manifest_path}"])
    if proc is None:
        return {"status": "unavailable", "reason": "git_show_unavailable"}
    if proc.returncode != 0:
        return {
            "status": "unavailable",
            "reason": "manifest_not_found_in_rescue_commit",
            "manifest_path": manifest_path,
        }
    try:
        manifest = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return {
            "status": "unavailable",
            "reason": "manifest_invalid_json",
            "manifest_path": manifest_path,
        }
    path_rows = manifest.get("path_classes") if isinstance(manifest.get("path_classes"), list) else []
    paths = sorted(
        {
            _normalize_dirty_path(str(row.get("path") or ""))
            for row in path_rows
            if isinstance(row, Mapping)
        }
    )
    return {
        "status": "available",
        "run_id": str(manifest.get("run_id") or run_id),
        "base_head": str(manifest.get("base_head") or ""),
        "dirty_path_count": int(manifest.get("dirty_path_count") or len(paths)),
        "payload_tree": manifest.get("payload_tree"),
        "manifest_path": str(manifest.get("manifest_path") or manifest_path),
        "dirty_path_fingerprint": _dirty_pathset_fingerprint(
            base_head=str(manifest.get("base_head") or ""),
            paths=paths,
        ),
        "paths": paths,
    }


def _recent_dirty_tree_rescue_refs(
    repo_root: Path,
    *,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    """Return recent dirty-tree rescue refs without making them authority."""
    proc = _run_git_pressure_read(
        repo_root,
        [
            "for-each-ref",
            "--sort=-creatordate",
            "--format=%(refname)%00%(objectname)%00%(creatordate:iso-strict)",
            DIRTY_TREE_RESCUE_REF_PREFIX,
        ],
    )
    if proc is None:
        return []
    if proc.returncode != 0:
        return []

    rows: List[Dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        if len(rows) >= max(0, limit):
            break
        parts = line.split("\0")
        if len(parts) != 3:
            continue
        ref, commit, created_at = parts
        if not ref or not commit:
            continue
        manifest = _dirty_tree_rescue_manifest(repo_root, ref=ref, commit=commit)
        row = {
            "ref": ref,
            "commit": commit,
            "created_at": created_at or None,
        }
        if manifest.get("status") == "available":
            row["manifest"] = {
                key: manifest.get(key)
                for key in (
                    "status",
                    "run_id",
                    "base_head",
                    "dirty_path_count",
                    "payload_tree",
                    "manifest_path",
                    "dirty_path_fingerprint",
                )
            }
        else:
            row["manifest"] = {
                "status": manifest.get("status", "unavailable"),
                "reason": manifest.get("reason"),
                "manifest_path": manifest.get("manifest_path"),
            }
        rows.append(row)
    return rows


def _blob_hash_in_tree(repo_root: Path, *, commit: str, path: str) -> str | None:
    proc = _run_git_pressure_read(repo_root, ["ls-tree", "-z", commit, "--", path])
    if proc is None or proc.returncode != 0 or not proc.stdout:
        return None
    # Format: "<mode> <type> <object>\t<path>\0". Paths may contain spaces.
    head = proc.stdout.split("\0", 1)[0]
    meta = head.split("\t", 1)[0].split()
    if len(meta) >= 3 and meta[1] == "blob":
        return meta[2]
    return None


def _worktree_blob_hash(repo_root: Path, path: str) -> str | None:
    full_path = repo_root / path
    if not full_path.exists():
        return None
    if not (full_path.is_file() or full_path.is_symlink()):
        return None
    proc = _run_git_pressure_read(repo_root, ["hash-object", "--", path])
    if proc is None or proc.returncode != 0:
        return None
    return proc.stdout.strip() or None


def _rescue_commit_matches_worktree_paths(
    repo_root: Path,
    *,
    commit: str,
    paths: List[str],
) -> Dict[str, Any]:
    mismatches: List[Dict[str, Any]] = []
    for path in paths:
        rescued_blob = _blob_hash_in_tree(repo_root, commit=commit, path=path)
        current_blob = _worktree_blob_hash(repo_root, path)
        if rescued_blob != current_blob:
            mismatches.append(
                {
                    "path": path,
                    "rescued_blob": rescued_blob,
                    "current_blob": current_blob,
                }
            )
    if mismatches:
        return {
            "status": "mismatched",
            "mismatch_count": len(mismatches),
            "mismatch_sample": mismatches[:5],
        }
    return {"status": "matched", "path_count": len(paths)}


def _dirty_tree_rescue_coverage(
    repo_root: Path,
    *,
    dirty_paths: List[str],
    dirty_scan_status: str,
    rescue_refs: List[Dict[str, Any]],
    active_claims: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    active_claim_rows = active_claims or []
    if dirty_scan_status not in ("git_status_porcelain_v1_z", "provided"):
        return {
            "status": "unknown",
            "reason": "dirty_scan_not_available_for_coverage",
            "basis": "coverage_requires_current_dirty_pathset",
        }
    current_paths = sorted({_normalize_dirty_path(path) for path in dirty_paths if path})
    if not current_paths:
        return {
            "status": "unavailable",
            "reason": "no_current_dirty_paths",
            "basis": "rescue_coverage_not_needed_for_clean_tree",
            "current_dirty_path_count": 0,
        }
    if not rescue_refs:
        return {
            "status": "unavailable",
            "reason": "no_dirty_tree_rescue_refs",
            "basis": "refs/aiw/rescue/dirty-tree",
            "current_dirty_path_count": len(current_paths),
        }

    latest = rescue_refs[0]
    latest_ref = str(latest.get("ref") or "")
    latest_commit = str(latest.get("commit") or "")
    manifest = _dirty_tree_rescue_manifest(
        repo_root,
        ref=latest_ref,
        commit=latest_commit,
    )
    current_head_proc = _run_git_pressure_read(repo_root, ["rev-parse", "HEAD"])
    current_head = (
        current_head_proc.stdout.strip()
        if current_head_proc is not None and current_head_proc.returncode == 0
        else None
    )
    current_fingerprint = _dirty_pathset_fingerprint(
        base_head=current_head,
        paths=current_paths,
    )
    base = {
        "latest_ref": latest_ref,
        "latest_commit": latest_commit,
        "current_base_head": current_head,
        "current_dirty_path_count": len(current_paths),
        "current_dirty_fingerprint": current_fingerprint,
    }
    if manifest.get("status") != "available":
        return {
            **base,
            "status": "unknown",
            "reason": manifest.get("reason", "rescue_manifest_unavailable"),
            "basis": "rescue_ref_manifest",
        }

    rescued_paths = list(manifest.get("paths") or [])
    rescued_set = set(rescued_paths)
    current_set = set(current_paths)
    rescued_fingerprint = str(manifest.get("dirty_path_fingerprint") or "")
    coverage = {
        **base,
        "rescued_base_head": manifest.get("base_head"),
        "rescued_dirty_path_count": manifest.get("dirty_path_count"),
        "rescued_dirty_fingerprint": rescued_fingerprint,
        "payload_tree": manifest.get("payload_tree"),
        "manifest_path": manifest.get("manifest_path"),
        "basis": "rescue_manifest_pathset_and_base_head",
    }
    if current_head and manifest.get("base_head") != current_head:
        return {
            **coverage,
            "status": "stale",
            "reason": "base_head_mismatch",
            **_drift_annotations([], active_claims=active_claim_rows, reason="base_head_mismatch"),
        }
    if current_set != rescued_set:
        moved_paths = sorted((current_set - rescued_set) or (rescued_set - current_set))
        return {
            **coverage,
            "status": "stale",
            "reason": "dirty_pathset_mismatch",
            "missing_from_rescue_count": len(current_set - rescued_set),
            "not_currently_dirty_count": len(rescued_set - current_set),
            "missing_from_rescue_sample": sorted(current_set - rescued_set)[:5],
            "not_currently_dirty_sample": sorted(rescued_set - current_set)[:5],
            **_drift_annotations(moved_paths, active_claims=active_claim_rows, reason="dirty_pathset_mismatch"),
        }
    if not latest_commit:
        return {**coverage, "status": "unknown", "reason": "missing_rescue_commit"}

    content_match = _rescue_commit_matches_worktree_paths(
        repo_root,
        commit=latest_commit,
        paths=current_paths,
    )
    coverage["basis"] = "rescue_manifest_pathset_and_blob_hash"
    if content_match.get("status") == "matched":
        return {
            **coverage,
            "status": "fresh",
            "reason": "latest_rescue_ref_matches_current_dirty_pathset_and_content",
        }
    if content_match.get("status") == "mismatched":
        mismatch_paths = [
            str(row.get("path") or "")
            for row in (content_match.get("mismatch_sample") or [])
            if isinstance(row, Mapping)
        ]
        return {
            **coverage,
            "status": "stale",
            "reason": "content_differs_from_rescue_commit",
            "content_mismatch_count": content_match.get("mismatch_count"),
            "content_mismatch_sample": content_match.get("mismatch_sample"),
            **_drift_annotations(mismatch_paths, active_claims=active_claim_rows, reason="content_differs_from_rescue_commit"),
        }
    return {
        **coverage,
        "status": "unknown",
        "reason": content_match.get("reason", "content_check_failed"),
    }


def build_dirty_tree_bankruptcy_pressure(
    repo_root: Path,
    status: Mapping[str, Any] | None = None,
    *,
    dirty_paths: Optional[List[str]] = None,
    dirty_scan_status: str = "not_scanned",
    bankruptcy_authorized: bool = False,
    now: datetime | None = None,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
    orphan_sweep_after: timedelta = ACTIVE_SESSION_ORPHAN_SWEEP_AFTER,
    limit: int = SESSION_COHORT_OVERVIEW_LIMIT,
) -> Dict[str, Any]:
    """Build an orientation-only card for lease-expired dirty-tree pressure.

    This is intentionally not a mutator and not a commit oracle. It composes
    Work Ledger lifecycle pressure with optional Git dirty-path evidence so an
    operator/controller can choose the correct owner lane: sweep expired
    sessions, preserve ambiguous work through a checkpoint rescue ref, or use
    scoped commits only when another owner has already proved validation.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    loaded_status = status if status is not None else load_runtime_status(repo_root)
    overview = build_session_cohort_overview(
        loaded_status,
        limit=limit,
        now=current,
        orphan_after=orphan_after,
    )
    counts = dict(overview.get("counts") or {})
    active_claims = _active_claim_rows_for_pressure(
        loaded_status,
        now=current,
        orphan_after=orphan_after,
    )
    sweep_preview = _session_sweep_preview_rows(
        loaded_status,
        now=current,
        orphan_sweep_after=orphan_sweep_after,
        limit=limit,
    )
    expired_claims = _expired_claim_preview_rows(
        loaded_status,
        now=current,
        limit=limit,
    )
    normalized_dirty_paths = [
        path
        for path in (_normalize_dirty_path(path) for path in (dirty_paths or []))
        if path
    ]
    dirty_rows, dirty_class_counts = _dirty_path_rows_for_pressure(
        normalized_dirty_paths,
        active_claims=active_claims,
        limit=limit,
    )
    active_claim_dirty_count = int(dirty_class_counts.get("active_claim_dirty") or 0)
    broad_checkpoint_command = './checkpoint --arbiter --message "bankruptcy: land dirty tree state"'
    rescue_ref_command = (
        './checkpoint --rescue-ref --dry-run --message "rescue: dirty-tree finalizer preservation"'
    )
    mainline_checkpoint_available = (
        bool(bankruptcy_authorized)
        and bool(normalized_dirty_paths)
        and active_claim_dirty_count == 0
        and dirty_scan_status in ("git_status_porcelain_v1_z", "provided")
    )
    operator_checkpoint: Dict[str, Any] = {
        "authorized": bool(bankruptcy_authorized),
        "status": "available" if mainline_checkpoint_available else "blocked",
        "command": broad_checkpoint_command,
        "conservative_fallback_command": rescue_ref_command,
        "requires_no_active_claim_dirty_paths": True,
        "active_claim_dirty_path_count": active_claim_dirty_count,
    }
    if not bankruptcy_authorized:
        operator_checkpoint["status"] = "not_authorized"
        operator_checkpoint["blocked_by"] = ["operator_bankruptcy_authorization_missing"]
    elif not normalized_dirty_paths:
        operator_checkpoint["blocked_by"] = ["clean_tree"]
    elif active_claim_dirty_count:
        operator_checkpoint["blocked_by"] = ["active_claim_dirty_paths"]
    elif dirty_scan_status not in ("git_status_porcelain_v1_z", "provided"):
        operator_checkpoint["blocked_by"] = ["dirty_path_scan_unavailable"]

    recent_sweeps = [
        dict(entry)
        for entry in (loaded_status.get("recent_sweep_events") or [])
        if isinstance(entry, Mapping)
    ]
    rescue_refs = _recent_dirty_tree_rescue_refs(repo_root)
    rescue_coverage = _dirty_tree_rescue_coverage(
        repo_root,
        dirty_paths=normalized_dirty_paths,
        dirty_scan_status=dirty_scan_status,
        rescue_refs=rescue_refs,
        active_claims=active_claims,
    )
    blocked_residuals: List[Dict[str, Any]] = []
    if active_claim_dirty_count:
        blocked_residuals.append(
            {
                "reason": "SessionLeaseActive",
                "dirty_path_count": active_claim_dirty_count,
                "next_safe_action": "wait_for_claim_release_or_finalize_session_before_sweeping",
            }
        )
    if dirty_scan_status not in ("git_status_porcelain_v1_z", "provided", "none"):
        blocked_residuals.append(
            {
                "reason": "DirtyPathScanUnavailable",
                "dirty_scan_status": dirty_scan_status,
                "next_safe_action": "run git status --porcelain=v1 -z or pass --dirty-path fixtures",
            }
        )
    if dirty_class_counts.get("unclaimed_source_dirty") and not mainline_checkpoint_available:
        blocked_residuals.append(
            {
                "reason": "UnclaimedDirtyWorkRequiresPrivateBackupOrOwnerClaim",
                "dirty_path_count": dirty_class_counts["unclaimed_source_dirty"],
                "next_safe_action": rescue_ref_command,
            }
        )

    if sweep_preview or expired_claims:
        next_safe_action = (
            "./repo-python tools/meta/factory/work_ledger.py session-sweep "
            "--dry-run --dirty-tree-pressure"
        )
    elif mainline_checkpoint_available:
        next_safe_action = broad_checkpoint_command
    elif normalized_dirty_paths:
        next_safe_action = rescue_ref_command
    else:
        next_safe_action = "./repo-python tools/meta/control/closeout_executor.py plan --json --compact"

    return {
        "schema": DIRTY_TREE_BANKRUPTCY_PRESSURE_SCHEMA,
        "authority_boundary": "orientation_overlay_not_safety_authority",
        "safety_authority": False,
        "bankruptcy_authorized": bool(bankruptcy_authorized),
        "operator_authorized_mainline_checkpoint": operator_checkpoint,
        "generated_at": work_ledger.utc_now(),
        "source_surfaces": [
            str(RUNTIME_STATUS_REL),
            "tools/meta/factory/work_ledger.py session-sweep",
            "./checkpoint --rescue-ref --dry-run --message \"rescue: dirty-tree finalizer preservation\"",
            "./checkpoint --private-backup --dry-run --json",
            "tools/meta/control/mission_transaction_preflight.py",
            "tools/meta/control/scoped_commit.py",
        ],
        "policy": {
            "primitive": "lease_expired_dirty_tree_finalizer",
            "age_alone_commits_to_main": False,
            "ambiguous_dirty_work_action": "checkpoint_rescue_ref_before_cleanup",
            "private_backup_scope": "remote_health_and_broad_emergency_checkpoint_not_default_finalizer",
            "mainline_commit_requires": [
                "known_path_owner",
                "no_conflicting_active_claim",
                "mission_transaction_preflight_safe",
                "validation_receipt",
                "scoped_commit_exact_pathspec",
            ],
        },
        "dirty_scan_status": dirty_scan_status,
        "dirty_total": len(normalized_dirty_paths) if dirty_paths is not None else None,
        "dirty_path_class_counts": dirty_class_counts,
        "dirty_path_rows": dirty_rows,
        "work_ledger_counts": {
            "sessions_total": counts.get("sessions_total", 0),
            "active_sessions": counts.get("active_sessions", 0),
            "effective_active_sessions": counts.get("effective_active_sessions", 0),
            "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
            "stale_append_obligations": counts.get("stale_sessions", 0),
            "active_claims": len(active_claims),
            "claim_collisions": counts.get("claim_collisions", 0),
        },
        "expired_sessions_needing_finalizer": len(sweep_preview),
        "expired_session_rows": sweep_preview,
        "expired_claims_needing_sweep": len(expired_claims),
        "expired_claim_rows": expired_claims,
        "last_finalizer_receipt_ref": (
            recent_sweeps[-1].get("event_id") if recent_sweeps else None
        ),
        "private_backup_refs": [],
        "rescue_refs": rescue_refs,
        "rescue_coverage": rescue_coverage,
        "mainline_commit_candidates": (
            [
                {
                    "reason": "OperatorAuthorizedDirtyTreeBankruptcy",
                    "command": broad_checkpoint_command,
                    "conservative_fallback_command": rescue_ref_command,
                    "dirty_path_count": len(normalized_dirty_paths),
                }
            ]
            if mainline_checkpoint_available
            else []
        ),
        "blocked_residuals": blocked_residuals,
        "next_safe_action": next_safe_action,
        "commands": {
            "sweep_dry_run": (
                "./repo-python tools/meta/factory/work_ledger.py session-sweep "
                "--dry-run --dirty-tree-pressure"
            ),
            "private_backup_dry_run": "./checkpoint --private-backup --dry-run --json",
            "rescue_ref_dry_run": rescue_ref_command,
            "operator_authorized_broad_checkpoint": broad_checkpoint_command,
            "closeout_plan": "./repo-python tools/meta/control/closeout_executor.py plan --json --compact",
        },
    }


def _runtime_status_receipt(repo_root: Path) -> Dict[str, Any]:
    path = _runtime_status_path(repo_root)
    if not path.exists():
        return {
            "path": str(RUNTIME_STATUS_REL),
            "exists": False,
            "mtime_ns": None,
            "size": 0,
        }
    stat = path.stat()
    return {
        "path": str(RUNTIME_STATUS_REL),
        "exists": True,
        "mtime_ns": stat.st_mtime_ns,
        "size": stat.st_size,
    }


def _claim_collision_rows(active_claims: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    scoped_claims: Dict[str, List[Dict[str, Any]]] = {}
    for claim in active_claims:
        scope_key = _claim_scope_key(claim)
        if scope_key:
            scoped_claims.setdefault(scope_key, []).append(claim)

    claim_collisions: List[Dict[str, Any]] = []
    scope_keys = sorted(scoped_claims)
    consumed_pairs: set[tuple[str, str]] = set()
    for index, left_key in enumerate(scope_keys):
        left_claims = scoped_claims[left_key]
        same_scope_collisions = list(left_claims) if len(left_claims) > 1 else []
        overlap_collisions: List[Dict[str, Any]] = []
        for right_key in scope_keys[index + 1 :]:
            pair_key = (left_key, right_key)
            if pair_key in consumed_pairs:
                continue
            if not _claim_scopes_overlap(left_claims[0], scoped_claims[right_key][0]):
                continue
            consumed_pairs.add(pair_key)
            overlap_collisions.extend(scoped_claims[right_key])
        claims = same_scope_collisions + overlap_collisions
        if not claims:
            continue
        claims_by_id = {str(claim.get("claim_id") or ""): claim for claim in (left_claims + claims)}
        compact_claims = sorted(
            claims_by_id.values(),
            key=lambda c: str(c.get("leased_until") or ""),
            reverse=True,
        )
        scope_kind, scope_id = _normalize_claim_scope(left_claims[0])
        claim_collisions.append(
            {
                "scope_kind": scope_kind,
                "scope_id": scope_id,
                "td_id": scope_id if scope_kind == CLAIM_SCOPE_THREAD else "",
                "path": scope_id if scope_kind == CLAIM_SCOPE_PATH else "",
                "work_item_id": scope_id if scope_kind == CLAIM_SCOPE_WORK_ITEM else "",
                "claim_count": len(compact_claims),
                "actors": sorted({str(claim.get("actor") or "unknown") for claim in compact_claims}),
                "active_claims": compact_claims,
            }
        )
    claim_collisions.sort(
        key=lambda item: (
            -int(item["claim_count"]),
            str(item.get("scope_kind") or ""),
            str(item.get("scope_id") or ""),
        )
    )
    return claim_collisions


def build_active_claims_snapshot(
    repo_root: Path,
    status: Mapping[str, Any],
    *,
    now: datetime | None = None,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> Dict[str, Any]:
    """Build the small Work Ledger claim snapshot used by pre-edit checks."""
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    sessions = [dict(raw) for raw in sessions_payload.values() if isinstance(raw, Mapping)]
    active_sessions = [session for session in sessions if not session.get("ended_at")]
    effective_active_sessions = [
        session
        for session in active_sessions
        if not _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
    ]
    orphaned_active_sessions = [
        session
        for session in active_sessions
        if _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
    ]
    active_claims: List[Dict[str, Any]] = []
    for session in effective_active_sessions:
        for claim in _session_active_claims(session, now=now):
            row = _compact_claim(claim)
            row["session_id"] = str(session.get("session_id") or "")
            row["actor"] = session.get("actor")
            row["phase_id"] = session.get("phase_id")
            active_claims.append(row)
    active_claims.sort(key=lambda c: str(c.get("leased_until") or ""), reverse=True)
    claim_collisions = _claim_collision_rows(active_claims)
    stable_payload = {
        "active_claims": active_claims,
        "claim_collisions": claim_collisions,
    }
    canonical = json.dumps(stable_payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return {
        "schema": "work_ledger_active_claims_snapshot_v1",
        "generated_at": work_ledger.utc_now(),
        "source_receipt": _runtime_status_receipt(repo_root),
        "source_hash": hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
        "counts": {
            "sessions_total": len(sessions),
            "active_sessions": len(active_sessions),
            "effective_active_sessions": len(effective_active_sessions),
            "orphaned_active_sessions": len(orphaned_active_sessions),
            "active_claims": len(active_claims),
            "claim_collisions": len(claim_collisions),
        },
        "active_claims": active_claims,
        "claim_collisions": claim_collisions,
        "refresh_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
    }


def active_claim_collisions_for_paths(
    repo_root: Path,
    paths: Iterable[str],
    *,
    status: Mapping[str, Any] | None = None,
    session_id: str | None = None,
) -> List[Dict[str, Any]]:
    """Return active Work Ledger path claims that overlap requested paths."""
    status_payload = status if status is not None else load_runtime_status(repo_root)
    snapshot = build_active_claims_snapshot(repo_root, status_payload)
    owner_session_id = str(session_id or "").strip()
    requested_paths: List[str] = []
    for path in paths:
        try:
            requested = _normalize_repo_claim_path(repo_root, str(path))
        except ValueError:
            requested = _normalize_dirty_path(path)
        if requested and requested not in requested_paths:
            requested_paths.append(requested)

    active_claims = [
        claim
        for claim in snapshot.get("active_claims") or []
        if isinstance(claim, Mapping) and _normalize_claim_scope(claim)[0] == CLAIM_SCOPE_PATH
    ]
    collisions: List[Dict[str, Any]] = []
    for requested in requested_paths:
        for claim in active_claims:
            if owner_session_id and str(claim.get("session_id") or "") == owner_session_id:
                continue
            claim_path = str(claim.get("path") or claim.get("scope_id") or "")
            if not claim_path or not _path_scope_overlaps(requested, claim_path):
                continue
            collisions.append(
                {
                    "requested_path": requested,
                    "session_id": claim.get("session_id"),
                    "actor": claim.get("actor"),
                    "claim_id": claim.get("claim_id"),
                    "claim_path": claim_path,
                    "leased_until": claim.get("leased_until"),
                }
            )
    return collisions


def write_active_claims_snapshot(repo_root: Path, status: Mapping[str, Any]) -> Dict[str, Any]:
    snapshot = build_active_claims_snapshot(repo_root, status)
    _atomic_write_runtime_json(_active_claims_snapshot_path(repo_root), snapshot)
    return snapshot


def _limit_claim_snapshot(snapshot: Mapping[str, Any], *, limit: int) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    active_claims = list(snapshot.get("active_claims") or [])
    claim_collisions = list(snapshot.get("claim_collisions") or [])
    payload = dict(snapshot)
    payload["active_claims"] = active_claims[:safe_limit] if safe_limit else []
    payload["claim_collisions"] = claim_collisions[:safe_limit] if safe_limit else []
    payload["truncation"] = {
        "limit": safe_limit,
        "active_claims_total": len(active_claims),
        "active_claims_emitted": len(payload["active_claims"]),
        "claim_collisions_total": len(claim_collisions),
        "claim_collisions_emitted": len(payload["claim_collisions"]),
    }
    payload["drilldown_commands"] = {
        "refresh": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
        "full_session_status": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
        "mutation_check": "./repo-python tools/meta/factory/work_ledger.py mutation-check --path <path> --require-exclusive",
    }
    return payload


def load_active_claims_snapshot(
    repo_root: Path,
    *,
    limit: int = SESSION_COHORT_OVERVIEW_LIMIT,
    allow_stale: bool = False,
) -> Dict[str, Any]:
    path = _active_claims_snapshot_path(repo_root)
    if not path.exists():
        return {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "status": "missing",
            "source_freshness": {
                "status": "missing_snapshot",
                "snapshot_path": str(ACTIVE_CLAIMS_SNAPSHOT_REL),
                "refresh_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
            },
            "counts": {},
            "active_claims": [],
            "claim_collisions": [],
        }
    try:
        snapshot = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "schema": "work_ledger_active_claims_snapshot_v1",
            "status": "unreadable",
            "source_freshness": {
                "status": "unreadable_snapshot",
                "snapshot_path": str(ACTIVE_CLAIMS_SNAPSHOT_REL),
                "refresh_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
            },
            "counts": {},
            "active_claims": [],
            "claim_collisions": [],
        }
    if not isinstance(snapshot, Mapping):
        snapshot = {}
    source_receipt = snapshot.get("source_receipt") if isinstance(snapshot.get("source_receipt"), Mapping) else {}
    current_receipt = _runtime_status_receipt(repo_root)
    fresh = (
        source_receipt.get("mtime_ns") == current_receipt.get("mtime_ns")
        and source_receipt.get("size") == current_receipt.get("size")
    )
    payload = _limit_claim_snapshot(snapshot, limit=limit)
    payload["status"] = "fresh" if fresh else ("stale_allowed" if allow_stale else "stale")
    payload["source_freshness"] = {
        "status": payload["status"],
        "snapshot_path": str(ACTIVE_CLAIMS_SNAPSHOT_REL),
        "source_receipt": dict(source_receipt),
        "current_source_receipt": current_receipt,
        "refresh_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
        "policy": "default read uses cached active-claims sidecar; --refresh rebuilds from runtime_status.json",
    }
    if fresh or allow_stale:
        return payload
    payload["active_claims"] = []
    payload["claim_collisions"] = []
    return payload


def rebuild_runtime_status(payload: Mapping[str, Any]) -> Dict[str, Any]:
    status = _default_status()
    sessions = payload.get("sessions") if isinstance(payload.get("sessions"), Mapping) else {}
    normalized_sessions: Dict[str, Dict[str, Any]] = {}
    stale_sessions: List[Dict[str, Any]] = []
    counts = {
        "sessions_total": 0,
        "active_sessions": 0,
        "stale_sessions": 0,
        "sessions_with_activity": 0,
        "sessions_with_ledger_append": 0,
        "open_todos_touched_this_session": 0,
        "session_had_no_ledger_append": 0,
    }
    for session_id, raw in sessions.items():
        if not isinstance(raw, Mapping):
            continue
        session = dict(raw)
        token = str(session_id)
        session["session_id"] = token
        session["read_receipt_id"] = str(session.get("read_receipt_id") or "").strip() or None
        session["bootstrap_slice_td_ids"] = [
            str(item) for item in session.get("bootstrap_slice_td_ids") or [] if str(item).strip()
        ]
        raw_touched_ids = [
            str(item) for item in session.get("touched_td_ids") or [] if str(item).strip()
        ]
        session["touched_td_ids"] = [
            item for item in raw_touched_ids if not _looks_like_work_item_id(item)
        ]
        touched_work_item_ids = [
            str(item) for item in session.get("touched_work_item_ids") or [] if str(item).strip()
        ]
        for item in raw_touched_ids:
            if _looks_like_work_item_id(item) and item not in touched_work_item_ids:
                touched_work_item_ids.append(item)
        session["touched_work_item_ids"] = touched_work_item_ids
        session["claims"] = [
            dict(claim)
            for claim in session.get("claims") or []
            if isinstance(claim, Mapping) and str(claim.get("claim_id") or "").strip()
        ]
        session["session_had_ledger_append"] = bool(session.get("session_had_ledger_append"))
        session["append_exempt"] = bool(session.get("append_exempt"))
        session["append_exempt_reason"] = session.get("append_exempt_reason")
        session["append_exempt_refs"] = [
            str(item) for item in session.get("append_exempt_refs") or [] if str(item).strip()
        ]
        session["append_exempted_at"] = session.get("append_exempted_at")
        session["has_activity"] = bool(session.get("has_activity"))
        session["touched_work"] = bool(session.get("touched_work"))
        session["stale"] = bool(session.get("stale"))
        session["open_todos_touched_this_session"] = int(
            session.get("open_todos_touched_this_session") or 0
        )
        normalized_sessions[token] = session
        counts["sessions_total"] += 1
        if not session.get("ended_at"):
            counts["active_sessions"] += 1
        if session["has_activity"]:
            counts["sessions_with_activity"] += 1
        if session["session_had_ledger_append"]:
            counts["sessions_with_ledger_append"] += 1
        if session["stale"]:
            stale_sessions.append(
                {
                    "session_id": token,
                    "actor": session.get("actor"),
                    "phase_id": session.get("phase_id"),
                    "family_id": session.get("family_id"),
                    "read_receipt_id": session.get("read_receipt_id"),
                    "last_activity_at": session.get("last_activity_at"),
                    "ended_at": session.get("ended_at"),
                    "stale_reason": session.get("stale_reason"),
                    "touched_td_ids": session.get("touched_td_ids") or [],
                    "touched_work_item_ids": session.get("touched_work_item_ids") or [],
                    "open_todos_touched_this_session": session["open_todos_touched_this_session"],
                }
            )
            counts["stale_sessions"] += 1
            if not session["session_had_ledger_append"]:
                counts["session_had_no_ledger_append"] += 1
        counts["open_todos_touched_this_session"] += session["open_todos_touched_this_session"]
    stale_sessions.sort(key=lambda item: str(item.get("last_activity_at") or item.get("ended_at") or ""), reverse=True)
    status["generated_at"] = work_ledger.utc_now()
    status["sessions"] = normalized_sessions
    status["stale_sessions"] = stale_sessions
    status["recent_sweep_events"] = [
        dict(entry)
        for entry in payload.get("recent_sweep_events") or []
        if isinstance(entry, Mapping)
    ][-RECENT_SWEEP_EVENTS_LIMIT:]
    status["counts"] = counts
    overview = build_session_cohort_overview(status)
    status["cohort_overview"] = overview
    status["triggers"] = {
        "stale_session_ready": counts["stale_sessions"] > 0 and counts["session_had_no_ledger_append"] > 0,
        "multi_agent_coordination_ready": overview["contention"]["risk_level"] != "clear",
    }
    stable_fields = {
        "triggers": status["triggers"],
        "counts": counts,
        "stale_session_ids": sorted(str(s.get("session_id") or "") for s in stale_sessions),
    }
    canonical = json.dumps(stable_fields, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    status["stable_signal_digest"] = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return status


def _write_runtime_status(repo_root: Path, status: Mapping[str, Any]) -> Dict[str, Any]:
    rebuilt = rebuild_runtime_status(status)
    _atomic_write_runtime_json(_runtime_status_path(repo_root), rebuilt)
    write_active_claims_snapshot(repo_root, rebuilt)
    return rebuilt


def observe_external_session(
    repo_root: Path,
    *,
    session_id: str,
    actor: str,
    phase_id: str | None = None,
    family_id: str | None = None,
    started_at: str | None = None,
    last_signal_at: str | None = None,
    title: str | None = None,
    source: str = "external_host_observation",
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """Upsert a host-observed agent session without minting a read receipt.

    Codex does not currently have the Claude hook path that calls
    bootstrap_session at SessionStart. This lets the repo track Codex threads
    discovered from the local host record plane while keeping ledger writes
    gated on explicit receipts.
    """
    rows = observe_external_sessions(
        repo_root,
        observations=[
            {
                "session_id": session_id,
                "actor": actor,
                "phase_id": phase_id,
                "family_id": family_id,
                "started_at": started_at,
                "last_signal_at": last_signal_at,
                "title": title,
                "source": source,
                "metadata": metadata,
            }
        ],
    )
    return rows[0]


def observe_external_sessions(
    repo_root: Path,
    *,
    observations: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Batch-upsert host-observed sessions with one runtime-status rebuild/write."""
    prepared: List[Dict[str, Any]] = []
    for observation in observations:
        token = str(observation.get("session_id") or "").strip()
        if not token:
            raise ValueError("session_id is required for external session observation")
        signal = _parse_iso_datetime(observation.get("last_signal_at")) or datetime.now(timezone.utc)
        started = _parse_iso_datetime(observation.get("started_at")) or signal
        prepared.append(
            {
                "session_id": token,
                "actor": str(observation.get("actor") or "").strip() or "unknown",
                "context": work_ledger.resolve_phase_context(
                    repo_root,
                    phase_id=str(observation.get("phase_id") or "") or None,
                    family_id=str(observation.get("family_id") or "") or None,
                ),
                "started_iso": started.isoformat(),
                "signal_iso": signal.isoformat(),
                "title": str(observation.get("title") or "").strip(),
                "source": str(observation.get("source") or "external_host_observation"),
                "metadata": dict(observation.get("metadata") or {}),
            }
        )
    if not prepared:
        return []
    observed_at = work_ledger.utc_now()
    results: List[Dict[str, Any]] = []
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        for row in prepared:
            token = row["session_id"]
            existing = dict(sessions.get(token) or {})
            created = not bool(existing)
            signal_iso = row["signal_iso"]
            existing_signal = _session_last_signal_at(existing) if existing else None
            parsed_signal = _parse_iso_datetime(signal_iso)
            if existing_signal is not None and (
                parsed_signal is None or existing_signal > parsed_signal
            ):
                signal_iso = existing_signal.isoformat()
            context = row["context"]
            session = {
                **existing,
                "session_id": token,
                "actor": row["actor"],
                "phase_id": context["phase_id"],
                "family_id": context["family_id"],
                "read_receipt_id": existing.get("read_receipt_id"),
                "bootstrapped_at": existing.get("bootstrapped_at") or row["started_iso"],
                "bootstrap_received": bool(existing.get("bootstrap_received")),
                "bootstrap_slice_td_ids": list(existing.get("bootstrap_slice_td_ids") or []),
                "bootstrap_slice_count": int(existing.get("bootstrap_slice_count") or 0),
                "has_activity": True,
                "touched_work": bool(existing.get("touched_work")),
                "touched_td_ids": list(existing.get("touched_td_ids") or []),
                "touched_work_item_ids": list(existing.get("touched_work_item_ids") or []),
                "claims": list(existing.get("claims") or []),
                "queries": int(existing.get("queries") or 0),
                "writes": int(existing.get("writes") or 0),
                "session_had_ledger_append": bool(existing.get("session_had_ledger_append")),
                "append_exempt": bool(existing.get("append_exempt")),
                "append_exempt_reason": existing.get("append_exempt_reason"),
                "append_exempt_refs": list(existing.get("append_exempt_refs") or []),
                "append_exempted_at": existing.get("append_exempted_at"),
                "last_activity_at": signal_iso,
                "last_query_at": existing.get("last_query_at"),
                "last_append_at": existing.get("last_append_at"),
                "ended_at": None,
                "end_action": None,
                "stale": bool(existing.get("stale")),
                "stale_reason": existing.get("stale_reason"),
                "open_todos_touched_this_session": int(
                    existing.get("open_todos_touched_this_session") or 0
                ),
                "external_observed": True,
                "external_source": row["source"],
                "external_title": row["title"] or str(existing.get("external_title") or "").strip(),
                "external_metadata": row["metadata"] or dict(existing.get("external_metadata") or {}),
                "pass_heartbeat": dict(existing.get("pass_heartbeat") or {})
                if isinstance(existing.get("pass_heartbeat"), Mapping)
                else None,
                "first_observed_at": existing.get("first_observed_at") or observed_at,
                "last_observed_at": observed_at,
            }
            sessions[token] = session
            results.append(
                {
                    "schema": "work_ledger_external_session_observation_v1",
                    "status": "created" if created else "updated",
                    "session_id": token,
                    "actor": row["actor"],
                    "phase_id": context["phase_id"],
                    "family_id": context["family_id"],
                    "last_activity_at": signal_iso,
                }
            )
        status["sessions"] = sessions
        saved = _write_runtime_status(repo_root, status)
    for result in results:
        result["generated_at"] = saved.get("generated_at")
    return results


def _render_open_card(card: Mapping[str, Any]) -> str:
    title = str(card.get("title") or card.get("td_id") or "untitled").strip()
    td_id = str(card.get("td_id") or "").strip()
    actor = str(card.get("last_actor") or "").strip()
    return f"- `{td_id}` — {title} (last actor: `{actor or 'unknown'}`)"


def format_bootstrap_context(payload: Mapping[str, Any]) -> str:
    family_open = payload.get("open_family_slice") if isinstance(payload.get("open_family_slice"), list) else []
    actor_open = payload.get("open_actor_slice") if isinstance(payload.get("open_actor_slice"), list) else []
    lines = [
        "## Work ledger bootstrap",
        f"- read_receipt_id: `{payload.get('read_receipt_id')}`",
        f"- phase_id: `{payload.get('phase_id')}`",
        f"- family_id: `{payload.get('family_id')}`",
        "- any mutating work-ledger command must present this read_receipt_id",
        "- pass heartbeat: publish a public now/done line at long pass start, plan pivot, before validation, and closeout",
        (
            "- heartbeat command: `./repo-python tools/meta/factory/work_ledger.py "
            f"session-heartbeat --session-id {payload.get('session_id')} --state <state> "
            "--now \"<public current pass>\" --done \"<public previous result>\" "
            "--scope-ref <path-or-claim>`"
        ),
        "- heartbeat boundary: runtime coordination only; do not summarize raw transcripts or hidden reasoning into now/done lines",
    ]
    lines.append("### Open work for this actor")
    if actor_open:
        lines.extend(_render_open_card(card) for card in actor_open)
    else:
        lines.append("- no actor-scoped open items in the current family view")
    lines.append("### Open work in family")
    if family_open:
        lines.extend(_render_open_card(card) for card in family_open)
    else:
        lines.append("- no family open items recorded")
    return "\n".join(lines)


def bootstrap_session(
    repo_root: Path,
    *,
    session_id: str,
    actor: str,
    phase_id: str | None = None,
    family_id: str | None = None,
    limit: int = BOOTSTRAP_SLICE_LIMIT,
    auto_sweep: bool = True,
    claim_scopes: Sequence[Mapping[str, Any]] | None = None,
    claim_lease_minutes: float = 30.0,
    claim_note: str | None = None,
    require_exclusive_claims: bool = False,
) -> Dict[str, Any]:
    context = work_ledger.resolve_phase_context(repo_root, phase_id=phase_id, family_id=family_id)
    projection = work_ledger.load_projection(
        repo_root,
        phase_id=context["phase_id"],
        family_id=context["family_id"],
    )
    actor_key = str(actor or "").strip() or "unknown"
    actor_slice = list((projection.get("open_by_actor") or {}).get(actor_key, []))[:limit]
    family_slice = list((projection.get("open_by_family") or {}).get(context["family_id"], []))[:limit]
    read_receipt_id = mint_read_receipt_id()
    claim_requests = _prepare_claim_scope_requests(repo_root, claim_scopes or [])
    claim_results: List[Dict[str, Any]] = []
    claimed_result_indexes: List[int] = []
    # Housekeeping: expire old leases, sweep crashed orphan sessions BEFORE
    # minting this session so the new seed sees a clean cohort view and never
    # sweeps itself. Both are folded into the bootstrap transaction so the hot
    # preflight path reads and rebuilds the runtime projection once.
    sweep_report: Dict[str, Any] = {"orphan_sweep": None, "claim_expiry": None}
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        if auto_sweep:
            current = datetime.now(timezone.utc)
            try:
                claim_details = _mark_expired_claims_in_status(status, current=current)
                sweep_report["claim_expiry"] = _expired_claim_sweep_report(
                    details=claim_details,
                    dry_run=False,
                    generated_at=status.get("generated_at"),
                )
            except Exception:
                sweep_report["claim_expiry"] = {"error": "sweep_expired_claims_failed"}
            try:
                orphan_details = _mark_orphan_sessions_in_status(
                    status,
                    current=current,
                    orphan_sweep_after=ACTIVE_SESSION_ORPHAN_SWEEP_AFTER,
                    exclude={session_id},
                )
                sweep_report["orphan_sweep"] = _orphan_session_sweep_report(
                    details=orphan_details,
                    dry_run=False,
                    orphan_sweep_after=ACTIVE_SESSION_ORPHAN_SWEEP_AFTER,
                    generated_at=status.get("generated_at"),
                )
            except Exception:
                sweep_report["orphan_sweep"] = {"error": "sweep_orphan_sessions_failed"}
        sessions = dict(status.get("sessions") or {})
        existing = dict(sessions.get(session_id) or {})
        sessions[session_id] = {
            "session_id": session_id,
            "actor": actor_key,
            "phase_id": context["phase_id"],
            "family_id": context["family_id"],
            "read_receipt_id": read_receipt_id,
            "bootstrapped_at": existing.get("bootstrapped_at") or work_ledger.utc_now(),
            "last_bootstrap_at": work_ledger.utc_now(),
            "bootstrap_received": True,
            "bootstrap_slice_td_ids": [
                str(card.get("td_id"))
                for card in family_slice
                if str(card.get("td_id") or "").strip()
            ],
            "bootstrap_slice_count": len(family_slice),
            "has_activity": bool(existing.get("has_activity")),
            "touched_work": bool(existing.get("touched_work")),
            "touched_td_ids": list(existing.get("touched_td_ids") or []),
            "touched_work_item_ids": list(existing.get("touched_work_item_ids") or []),
            "claims": list(existing.get("claims") or []),
            "queries": int(existing.get("queries") or 0),
            "writes": int(existing.get("writes") or 0),
            "session_had_ledger_append": bool(existing.get("session_had_ledger_append")),
            "append_exempt": bool(existing.get("append_exempt")),
            "append_exempt_reason": existing.get("append_exempt_reason"),
            "append_exempt_refs": list(existing.get("append_exempt_refs") or []),
            "append_exempted_at": existing.get("append_exempted_at"),
            "last_activity_at": existing.get("last_activity_at"),
            "last_query_at": existing.get("last_query_at"),
            "last_append_at": existing.get("last_append_at"),
            "pass_heartbeat": dict(existing.get("pass_heartbeat") or {})
            if isinstance(existing.get("pass_heartbeat"), Mapping)
            else None,
            "ended_at": None,
            "stale": (
                False
                if existing.get("session_had_ledger_append") or existing.get("append_exempt")
                else bool(existing.get("stale"))
            ),
            "stale_reason": (
                None
                if existing.get("session_had_ledger_append") or existing.get("append_exempt")
                else existing.get("stale_reason")
            ),
            "open_todos_touched_this_session": int(
                existing.get("open_todos_touched_this_session") or 0
            ),
        }
        status["sessions"] = sessions
        if claim_requests:
            lease = _clamp_lease(timedelta(minutes=float(claim_lease_minutes or 0)))
            now = datetime.now(timezone.utc)
            claim_results, claimed_result_indexes = _apply_claim_scope_requests_to_status(
                status,
                session_id=session_id,
                requests=claim_requests,
                now=now,
                leased_until=(now + lease).isoformat(),
                note=claim_note,
                require_exclusive=require_exclusive_claims,
            )
        saved = _write_runtime_status(repo_root, status)
        for result_index in claimed_result_indexes:
            claim_results[result_index]["generated_at"] = saved.get("generated_at")
        if auto_sweep:
            for report in sweep_report.values():
                if isinstance(report, dict) and report.get("generated_at") is None:
                    report["generated_at"] = saved.get("generated_at")
    payload = {
        "schema": "work_ledger_bootstrap_v1",
        "generated_at": saved.get("generated_at"),
        "session_id": session_id,
        "actor": actor_key,
        "phase_id": context["phase_id"],
        "family_id": context["family_id"],
        "read_receipt_id": read_receipt_id,
        "open_actor_slice": actor_slice,
        "open_family_slice": family_slice,
        "auto_sweep": sweep_report,
        "claims": claim_results,
        "cohort_overview": saved.get("cohort_overview"),
    }
    payload["additional_context"] = format_bootstrap_context(payload)
    return payload


def validate_read_receipt(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str | None = None,
    allow_ended: bool = False,
) -> Dict[str, Any]:
    receipt = str(read_receipt_id or "").strip()
    if not receipt:
        raise ValueError("read_receipt_id is required")
    status = _load_runtime_status_for_session_scan(repo_root)
    for key, session in (status.get("sessions") or {}).items():
        if str(session.get("read_receipt_id") or "").strip() != receipt:
            continue
        if session_id and str(key) != str(session_id):
            raise ValueError("read_receipt_id does not match actor_session_id")
        if session.get("ended_at") and not allow_ended:
            raise ValueError("read_receipt_id belongs to an ended session")
        return dict(session)
    raise ValueError("read_receipt_id is not valid")


def mark_session_activity(
    repo_root: Path,
    *,
    session_id: str,
    action: str,
    td_id: str | None = None,
) -> Dict[str, Any]:
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(session_id) or {})
        if not session:
            return status
        session["has_activity"] = True
        session["last_activity_at"] = work_ledger.utc_now()
        session["last_activity_action"] = str(action or "").strip() or None
        if session.get("bootstrap_received") or td_id:
            session["touched_work"] = True
        touched_ids = list(session.get("touched_td_ids") or [])
        touched_work_item_ids = list(session.get("touched_work_item_ids") or [])
        target_id = str(td_id or "").strip()
        if target_id:
            if _looks_like_work_item_id(target_id):
                if target_id not in touched_work_item_ids:
                    touched_work_item_ids.append(target_id)
            elif target_id not in touched_ids:
                touched_ids.append(target_id)
        session["touched_td_ids"] = touched_ids
        session["touched_work_item_ids"] = touched_work_item_ids
        touched_count = len(touched_ids) + len(touched_work_item_ids)
        if touched_count == 0 and session.get("touched_work"):
            touched_count = max(int(session.get("bootstrap_slice_count") or 0), 1)
        session["open_todos_touched_this_session"] = touched_count
        sessions[session_id] = session
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def mark_session_pass_heartbeat(
    repo_root: Path,
    *,
    session_id: str,
    pass_state: str = "inspecting",
    current_pass_line: str | None = None,
    last_pass_result_line: str | None = None,
    td_id: str | None = None,
    scope_refs: Sequence[object] | None = None,
    pass_id: str | None = None,
    source: str = "manual_cli",
) -> Dict[str, Any]:
    current_line = _public_pass_line(
        current_pass_line,
        limit=PASS_CURRENT_LINE_LIMIT,
        field_name="current_pass_line",
    )
    result_line = _public_pass_line(
        last_pass_result_line,
        limit=PASS_RESULT_LINE_LIMIT,
        field_name="last_pass_result_line",
    )
    state = _normalize_pass_state(pass_state)
    source_token = _normalize_pass_source(source)
    incoming_scope_refs = _normalize_scope_refs(scope_refs)
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(session_id) or {})
        if not session:
            return status
        now_dt = datetime.now(timezone.utc)
        now = now_dt.isoformat()
        existing = (
            dict(session.get("pass_heartbeat") or {})
            if isinstance(session.get("pass_heartbeat"), Mapping)
            else {}
        )
        previous_line = str(existing.get("current_pass_line") or "").strip()
        pass_seq = int(existing.get("pass_seq") or 0)
        resolved_pass_id = str(pass_id or existing.get("pass_id") or "").strip()
        if current_line and current_line != previous_line:
            pass_seq += 1
            resolved_pass_id = str(pass_id or "").strip() or mint_pass_id()
        elif not resolved_pass_id:
            pass_seq += 1
            resolved_pass_id = mint_pass_id()

        merged_scope_refs = _normalize_scope_refs(
            list(existing.get("scope_refs") or []) + incoming_scope_refs
        )
        heartbeat: Dict[str, Any] = {
            "schema": PASS_HEARTBEAT_SCHEMA,
            "session_id": session_id,
            "actor": session.get("actor"),
            "phase_id": session.get("phase_id"),
            "family_id": session.get("family_id"),
            "pass_id": resolved_pass_id,
            "pass_seq": pass_seq,
            "pass_state": state,
            "current_pass_line": (
                current_line if current_line is not None else existing.get("current_pass_line")
            ),
            "last_pass_result_line": (
                result_line if result_line is not None else existing.get("last_pass_result_line")
            ),
            "scope_refs": merged_scope_refs,
            "updated_at": now,
            "expires_at": (now_dt + ACTIVE_SESSION_ORPHAN_AFTER).isoformat(),
            "current_pass_updated_at": (
                now if current_line is not None else existing.get("current_pass_updated_at")
            ),
            "last_pass_completed_at": (
                now if result_line is not None else existing.get("last_pass_completed_at")
            ),
            "source": source_token,
        }
        session["pass_heartbeat"] = heartbeat
        session["has_activity"] = True
        session["last_activity_at"] = now
        session["last_activity_action"] = "session-heartbeat"
        touched_ids = list(session.get("touched_td_ids") or [])
        touched_work_item_ids = list(session.get("touched_work_item_ids") or [])
        target_id = str(td_id or "").strip()
        if target_id:
            session["touched_work"] = True
            if _looks_like_work_item_id(target_id):
                if target_id not in touched_work_item_ids:
                    touched_work_item_ids.append(target_id)
            elif target_id not in touched_ids:
                touched_ids.append(target_id)
        session["touched_td_ids"] = touched_ids
        session["touched_work_item_ids"] = touched_work_item_ids
        touched_count = len(touched_ids) + len(touched_work_item_ids)
        if touched_count:
            session["open_todos_touched_this_session"] = touched_count
        sessions[session_id] = session
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def mark_ledger_query(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str | None = None,
    td_id: str | None = None,
) -> Dict[str, Any]:
    session = validate_read_receipt(repo_root, read_receipt_id=read_receipt_id, session_id=session_id)
    token = str(session.get("session_id") or session_id or "").strip()
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        current = dict(sessions.get(token) or session)
        current["queries"] = int(current.get("queries") or 0) + 1
        now = work_ledger.utc_now()
        current["last_query_at"] = now
        current["has_activity"] = True
        current["last_activity_at"] = now
        if current.get("bootstrap_received") or td_id:
            current["touched_work"] = True
        touched_ids = list(current.get("touched_td_ids") or [])
        touched_work_item_ids = list(current.get("touched_work_item_ids") or [])
        target_id = str(td_id or "").strip()
        if target_id:
            if _looks_like_work_item_id(target_id):
                if target_id not in touched_work_item_ids:
                    touched_work_item_ids.append(target_id)
            elif target_id not in touched_ids:
                touched_ids.append(target_id)
        current["touched_td_ids"] = touched_ids
        current["touched_work_item_ids"] = touched_work_item_ids
        touched_count = len(touched_ids) + len(touched_work_item_ids)
        if touched_count == 0 and current.get("touched_work"):
            touched_count = max(int(current.get("bootstrap_slice_count") or 0), 1)
        current["open_todos_touched_this_session"] = touched_count
        sessions[token] = current
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def mark_ledger_append(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str | None = None,
    td_ids: Optional[List[str]] = None,
    work_item_ids: Optional[List[str]] = None,
    event_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    session = validate_read_receipt(repo_root, read_receipt_id=read_receipt_id, session_id=session_id)
    token = str(session.get("session_id") or session_id or "").strip()
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        current = dict(sessions.get(token) or session)
        current["writes"] = int(current.get("writes") or 0) + 1
        current["session_had_ledger_append"] = True
        current["last_append_at"] = work_ledger.utc_now()
        current["stale"] = False
        current["stale_reason"] = None
        touched = list(current.get("touched_td_ids") or [])
        touched_work_items = list(current.get("touched_work_item_ids") or [])
        if td_ids:
            for td_id in td_ids:
                item_token = str(td_id or "").strip()
                if not item_token:
                    continue
                if _looks_like_work_item_id(item_token):
                    if item_token not in touched_work_items:
                        touched_work_items.append(item_token)
                elif item_token not in touched:
                    touched.append(item_token)
        if work_item_ids:
            for work_item_id in work_item_ids:
                item_token = str(work_item_id or "").strip()
                if item_token and item_token not in touched_work_items:
                    touched_work_items.append(item_token)
        current["touched_td_ids"] = touched
        current["touched_work_item_ids"] = touched_work_items
        current["open_todos_touched_this_session"] = max(
            int(current.get("open_todos_touched_this_session") or 0),
            len(touched) + len(touched_work_items),
        )
        if event_ids:
            current["last_event_ids"] = [str(item) for item in event_ids]
        sessions[token] = current
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def mark_session_append_exempt(
    repo_root: Path,
    *,
    read_receipt_id: str,
    session_id: str | None = None,
    reason: str,
    evidence_refs: Optional[List[str]] = None,
    td_ids: Optional[List[str]] = None,
    work_item_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    session = validate_read_receipt(
        repo_root,
        read_receipt_id=read_receipt_id,
        session_id=session_id,
        allow_ended=True,
    )
    token = str(session.get("session_id") or session_id or "").strip()
    reason_token = str(reason or "").strip()
    if not reason_token:
        raise ValueError("append-exempt reason is required")
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        current = dict(sessions.get(token) or session)
        current["append_exempt"] = True
        current["append_exempt_reason"] = reason_token
        current["append_exempt_refs"] = [
            str(item).strip() for item in evidence_refs or [] if str(item).strip()
        ]
        current["append_exempted_at"] = work_ledger.utc_now()
        current["has_activity"] = True
        current["last_activity_at"] = current["append_exempted_at"]
        current["stale"] = False
        current["stale_reason"] = None
        touched = list(current.get("touched_td_ids") or [])
        touched_work_items = list(current.get("touched_work_item_ids") or [])
        for td_id in td_ids or []:
            item_token = str(td_id or "").strip()
            if item_token and item_token not in touched:
                touched.append(item_token)
        for work_item_id in work_item_ids or []:
            item_token = str(work_item_id or "").strip()
            if item_token and item_token not in touched_work_items:
                touched_work_items.append(item_token)
        current["touched_td_ids"] = touched
        current["touched_work_item_ids"] = touched_work_items
        current["open_todos_touched_this_session"] = max(
            int(current.get("open_todos_touched_this_session") or 0),
            len(touched) + len(touched_work_items),
        )
        sessions[token] = current
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def finalize_session(
    repo_root: Path,
    *,
    session_id: str,
    action: str,
    release_claims: bool = False,
    release_reason: str | None = None,
) -> Dict[str, Any]:
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(session_id) or {})
        if not session:
            return status
        now = work_ledger.utc_now()
        if not session.get("ended_at"):
            session["ended_at"] = now
        if not session.get("end_action"):
            session["end_action"] = action
        if release_claims:
            reason = str(release_reason or action or "session_finalized").strip() or "session_finalized"
            claims = [
                dict(claim)
                for claim in session.get("claims") or []
                if isinstance(claim, Mapping)
            ]
            for claim in claims:
                if claim.get("released_at") or claim.get("expired_at"):
                    continue
                claim["released_at"] = now
                claim["release_reason"] = reason
            session["claims"] = claims
        append_satisfied = bool(session.get("session_had_ledger_append")) or bool(
            session.get("append_exempt")
        )
        if session.get("touched_work") and not append_satisfied:
            session["stale"] = True
            session["stale_reason"] = (
                "session touched work after bootstrap but ended without a work-ledger append"
            )
        elif append_satisfied:
            session["stale"] = False
            session["stale_reason"] = None
        sessions[session_id] = session
        status["sessions"] = sessions
        return _write_runtime_status(repo_root, status)


def mint_claim_id() -> str:
    return f"{WORK_LEDGER_CLAIM_PREFIX}{uuid.uuid4().hex[:16]}"


def mint_sweep_event_id() -> str:
    return f"{RECENT_SWEEP_EVENT_PREFIX}{uuid.uuid4().hex[:16]}"


def _is_claim_active(claim: Mapping[str, Any], *, now: datetime) -> bool:
    if claim.get("released_at") or claim.get("expired_at"):
        return False
    leased_until = _parse_iso_datetime(claim.get("leased_until"))
    if leased_until is None:
        # No lease window -> treat as stale; sweep will expire it.
        return False
    return leased_until > now


def _normalize_claim_scope(claim: Mapping[str, Any]) -> tuple[str, str]:
    scope_kind = str(claim.get("scope_kind") or "").strip()
    scope_id = str(claim.get("scope_id") or "").strip()
    if not scope_kind:
        if str(claim.get("td_id") or "").strip():
            scope_id = str(claim.get("td_id") or "").strip()
            scope_kind = CLAIM_SCOPE_WORK_ITEM if _looks_like_work_item_id(scope_id) else CLAIM_SCOPE_THREAD
        elif str(claim.get("path") or "").strip():
            scope_kind = CLAIM_SCOPE_PATH
            scope_id = str(claim.get("path") or "").strip()
        elif str(claim.get("work_item_id") or "").strip():
            scope_kind = CLAIM_SCOPE_WORK_ITEM
            scope_id = str(claim.get("work_item_id") or "").strip()
    if scope_kind == CLAIM_SCOPE_THREAD and not scope_id:
        scope_id = str(claim.get("td_id") or "").strip()
    if scope_kind == CLAIM_SCOPE_THREAD and _looks_like_work_item_id(scope_id):
        scope_kind = CLAIM_SCOPE_WORK_ITEM
    if scope_kind == CLAIM_SCOPE_PATH and not scope_id:
        scope_id = str(claim.get("path") or "").strip()
    if scope_kind == CLAIM_SCOPE_WORK_ITEM and not scope_id:
        scope_id = str(claim.get("work_item_id") or claim.get("td_id") or "").strip()
    return scope_kind, scope_id


def _looks_like_work_item_id(value: object) -> bool:
    token = str(value or "").strip()
    return bool(token and not token.startswith("td_") and WORK_ITEM_ID_RE.fullmatch(token))


def _normalize_repo_claim_path(repo_root: Path, value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        raise ValueError("path is required for a path claim")
    candidate = Path(raw)
    if candidate.is_absolute():
        try:
            rel = candidate.resolve(strict=False).relative_to(repo_root.resolve(strict=False))
        except ValueError as exc:
            raise ValueError("path claim must target a path inside the repository") from exc
    else:
        rel = candidate
    parts: List[str] = []
    for part in rel.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError("path claim may not escape the repository with '..'")
        parts.append(part)
    if not parts:
        raise ValueError("path claim may not target the repository root")
    return PurePosixPath(*parts).as_posix()


def _claim_scope_key(claim: Mapping[str, Any]) -> str:
    scope_kind, scope_id = _normalize_claim_scope(claim)
    return f"{scope_kind}:{scope_id}" if scope_kind and scope_id else ""


def _path_scope_overlaps(left: str, right: str) -> bool:
    left_path = PurePosixPath(left)
    right_path = PurePosixPath(right)
    left_parts = left_path.parts
    right_parts = right_path.parts
    if left_parts == right_parts:
        return True
    if len(left_parts) < len(right_parts):
        return right_parts[: len(left_parts)] == left_parts
    return left_parts[: len(right_parts)] == right_parts


def _claim_scopes_overlap(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_kind, left_id = _normalize_claim_scope(left)
    right_kind, right_id = _normalize_claim_scope(right)
    if not left_kind or not left_id or not right_kind or not right_id:
        return False
    if left_kind != right_kind:
        return False
    if left_kind == CLAIM_SCOPE_PATH:
        return _path_scope_overlaps(left_id, right_id)
    return left_id == right_id


def _compact_claim(claim: Mapping[str, Any]) -> Dict[str, Any]:
    scope_kind, scope_id = _normalize_claim_scope(claim)
    td_id = str(claim.get("td_id") or "").strip()
    path = str(claim.get("path") or "").strip()
    work_item_id = str(claim.get("work_item_id") or "").strip()
    return {
        "claim_id": str(claim.get("claim_id") or ""),
        "scope_kind": scope_kind or None,
        "scope_id": scope_id or None,
        "td_id": "" if scope_kind == CLAIM_SCOPE_WORK_ITEM else td_id or (scope_id if scope_kind == CLAIM_SCOPE_THREAD else ""),
        "path": path or (scope_id if scope_kind == CLAIM_SCOPE_PATH else ""),
        "work_item_id": work_item_id or (scope_id if scope_kind == CLAIM_SCOPE_WORK_ITEM else ""),
        "claimed_at": claim.get("claimed_at"),
        "leased_until": claim.get("leased_until"),
        "released_at": claim.get("released_at"),
        "expired_at": claim.get("expired_at"),
        "note": str(claim.get("note") or "").strip() or None,
        "release_reason": claim.get("release_reason"),
    }


def _session_active_claims(
    session: Mapping[str, Any],
    *,
    now: datetime,
) -> List[Dict[str, Any]]:
    claims = session.get("claims") if isinstance(session.get("claims"), list) else []
    return [dict(claim) for claim in claims if isinstance(claim, Mapping) and _is_claim_active(claim, now=now)]


def active_thread_claim(
    repo_root: Path,
    *,
    session_id: str,
    td_id: str,
) -> Dict[str, Any] | None:
    """Return the current active td_id claim owned by session_id, if any."""
    token = str(session_id or "").strip()
    target = str(td_id or "").strip()
    if not token or not target:
        return None
    status = _load_runtime_status_for_session_scan(repo_root)
    session = (status.get("sessions") or {}).get(token)
    if not isinstance(session, Mapping) or session.get("ended_at"):
        return None
    now = datetime.now(timezone.utc)
    for claim in _session_active_claims(session, now=now):
        scope_kind, scope_id = _normalize_claim_scope(claim)
        if scope_kind == CLAIM_SCOPE_THREAD and scope_id == target:
            return _compact_claim(claim)
    return None


def active_work_item_claim(
    repo_root: Path,
    *,
    session_id: str,
    work_item_id: str,
) -> Dict[str, Any] | None:
    """Return the current active Task Ledger WorkItem claim, if any."""
    token = str(session_id or "").strip()
    target = str(work_item_id or "").strip()
    if not token or not target:
        return None
    status = _load_runtime_status_for_session_scan(repo_root)
    session = (status.get("sessions") or {}).get(token)
    if not isinstance(session, Mapping) or session.get("ended_at"):
        return None
    now = datetime.now(timezone.utc)
    for claim in _session_active_claims(session, now=now):
        scope_kind, scope_id = _normalize_claim_scope(claim)
        if scope_kind == CLAIM_SCOPE_WORK_ITEM and scope_id == target:
            return _compact_claim(claim)
    return None


def require_active_thread_claim(
    repo_root: Path,
    *,
    session_id: str,
    td_id: str,
    operation: str,
) -> Dict[str, Any]:
    """Require an active td_id claim as a fencing token for a mutation."""
    claim = active_thread_claim(repo_root, session_id=session_id, td_id=td_id)
    if claim is None:
        raise ValueError(
            f"{operation} requires an active td_id claim for {td_id!r} owned by session {session_id!r}; "
            "run session-claim --td-id before mutating this WorkItem, or use the explicit "
            "low-blast no-claim note mode when available."
        )
    return claim


def require_active_work_item_claim(
    repo_root: Path,
    *,
    session_id: str,
    work_item_id: str,
    operation: str,
) -> Dict[str, Any]:
    """Require an active Task Ledger WorkItem claim as a fencing token."""
    claim = active_work_item_claim(repo_root, session_id=session_id, work_item_id=work_item_id)
    if claim is None:
        raise ValueError(
            f"{operation} requires an active work_item_id claim for {work_item_id!r} "
            f"owned by session {session_id!r}; run session-claim --td-id <work_item_id> "
            "or session-preflight with the WorkItem id before appending a WorkItem progress receipt."
        )
    return claim


def _clamp_lease(lease: timedelta) -> timedelta:
    if lease.total_seconds() <= 0:
        return ACTIVE_CLAIM_LEASE_DEFAULT
    if lease > ACTIVE_CLAIM_LEASE_MAX:
        return ACTIVE_CLAIM_LEASE_MAX
    return lease


def _append_sweep_event(
    status: Dict[str, Any],
    *,
    kind: str,
    swept_count: int,
    details: List[Dict[str, Any]],
) -> None:
    recent = list(status.get("recent_sweep_events") or [])
    recent.append(
        {
            "event_id": mint_sweep_event_id(),
            "kind": kind,
            "swept_at": work_ledger.utc_now(),
            "swept_count": int(swept_count),
            "details": details[:RECENT_SWEEP_EVENTS_LIMIT],
        }
    )
    status["recent_sweep_events"] = recent[-RECENT_SWEEP_EVENTS_LIMIT:]


def _expired_claim_sweep_report(
    *,
    details: List[Dict[str, Any]],
    dry_run: bool,
    generated_at: str | None = None,
) -> Dict[str, Any]:
    report = {
        "schema": "work_ledger_sweep_result_v1",
        "kind": "expired_claims",
        "dry_run": dry_run,
        "swept_count": len(details),
        "details": details,
    }
    if not dry_run:
        report["generated_at"] = generated_at
    return report


def _orphan_session_sweep_report(
    *,
    details: List[Dict[str, Any]],
    dry_run: bool,
    orphan_sweep_after: timedelta,
    generated_at: str | None = None,
) -> Dict[str, Any]:
    report = {
        "schema": "work_ledger_sweep_result_v1",
        "kind": "orphan_sessions",
        "dry_run": dry_run,
        "orphan_sweep_after_hours": orphan_sweep_after.total_seconds() / 3600.0,
        "swept_count": len(details),
        "details": details,
    }
    if not dry_run:
        report["generated_at"] = generated_at
    return report


def _mark_expired_claims_in_status(
    status: Dict[str, Any],
    *,
    current: datetime,
) -> List[Dict[str, Any]]:
    sessions = dict(status.get("sessions") or {})
    swept_details: List[Dict[str, Any]] = []
    for session_id, raw in sessions.items():
        if not isinstance(raw, Mapping):
            continue
        session = dict(raw)
        claims = [dict(claim) for claim in session.get("claims") or [] if isinstance(claim, Mapping)]
        mutated = False
        for claim in claims:
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            leased_until = _parse_iso_datetime(claim.get("leased_until"))
            if leased_until is None or leased_until > current:
                continue
            claim["expired_at"] = claim.get("leased_until")
            claim["release_reason"] = "lease_expired"
            mutated = True
            swept_details.append(
                {
                    "session_id": str(session_id),
                    "claim_id": str(claim.get("claim_id") or ""),
                    "td_id": str(claim.get("td_id") or ""),
                    "leased_until": claim.get("leased_until"),
                }
            )
        if mutated:
            session["claims"] = claims
            sessions[str(session_id)] = session
    if swept_details:
        _append_sweep_event(
            status,
            kind="claim_expiry",
            swept_count=len(swept_details),
            details=swept_details,
        )
        status["sessions"] = sessions
    return swept_details


def _mark_orphan_sessions_in_status(
    status: Dict[str, Any],
    *,
    current: datetime,
    orphan_sweep_after: timedelta,
    exclude: set[str],
) -> List[Dict[str, Any]]:
    sessions = dict(status.get("sessions") or {})
    swept_details: List[Dict[str, Any]] = []
    for session_id, raw in list(sessions.items()):
        if not isinstance(raw, Mapping):
            continue
        token = str(session_id)
        if token in exclude:
            continue
        session = dict(raw)
        if session.get("ended_at"):
            continue
        if not _is_orphaned_active_session(session, now=current, orphan_after=orphan_sweep_after):
            continue
        last_signal = _session_last_signal_at(session)
        claims = [dict(claim) for claim in session.get("claims") or [] if isinstance(claim, Mapping)]
        released_claims: List[Dict[str, Any]] = []
        for claim in claims:
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            claim["released_at"] = current.isoformat()
            claim["release_reason"] = "session_auto_swept"
            released_claims.append(_compact_claim(claim))
        session["claims"] = claims
        session["ended_at"] = current.isoformat()
        session["end_action"] = "auto_orphan_sweep"
        if session.get("touched_work") and not session.get("session_had_ledger_append"):
            session["stale"] = True
            session["stale_reason"] = (
                "auto-swept after "
                f"{int(orphan_sweep_after.total_seconds() // 3600)}h of inactivity; "
                "session touched work after bootstrap but never appended to the ledger"
            )
        else:
            session["stale"] = bool(session.get("stale"))
        sessions[token] = session
        swept_details.append(
            {
                "session_id": token,
                "actor": str(session.get("actor") or "unknown"),
                "phase_id": str(session.get("phase_id") or ""),
                "last_signal_at": last_signal.isoformat() if last_signal is not None else None,
                "idle_hours": (
                    round((current - last_signal).total_seconds() / 3600.0, 2)
                    if last_signal is not None
                    else None
                ),
                "released_claims": released_claims,
                "stale_reason": session.get("stale_reason"),
            }
        )
    if swept_details:
        _append_sweep_event(
            status,
            kind="orphan_sweep",
            swept_count=len(swept_details),
            details=swept_details,
        )
        status["sessions"] = sessions
    return swept_details


def _prepare_claim_scope_requests(
    repo_root: Path,
    scopes: Sequence[Mapping[str, Any]],
) -> List[Dict[str, str]]:
    requests: List[Dict[str, str]] = []
    for scope in scopes:
        scope_kind_token = str(scope.get("scope_kind") or "").strip()
        if scope_kind_token not in CLAIM_SCOPE_KINDS:
            raise ValueError(f"scope_kind must be one of {sorted(CLAIM_SCOPE_KINDS)}")
        scope_token = str(
            scope.get("scope_id")
            or scope.get("td_id")
            or scope.get("path")
            or scope.get("work_item_id")
            or ""
        ).strip()
        if scope_kind_token == CLAIM_SCOPE_THREAD and _looks_like_work_item_id(scope_token):
            scope_kind_token = CLAIM_SCOPE_WORK_ITEM
        if scope_kind_token == CLAIM_SCOPE_PATH:
            scope_token = _normalize_repo_claim_path(repo_root, scope_token)
        if not scope_token:
            raise ValueError("scope_id is required for session-claim")
        if scope_kind_token == CLAIM_SCOPE_WORK_ITEM and not _looks_like_work_item_id(scope_token):
            raise ValueError("work_item_id claim requires a Task Ledger WorkItem-shaped id")
        requests.append(
            {
                "scope_kind": scope_kind_token,
                "scope_id": scope_token,
                "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
                "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
                "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
            }
        )
    return requests


def _apply_claim_scope_requests_to_status(
    status: Dict[str, Any],
    *,
    session_id: str,
    requests: Sequence[Mapping[str, str]],
    now: datetime,
    leased_until: str,
    note: str | None = None,
    require_exclusive: bool = False,
) -> tuple[List[Dict[str, Any]], List[int]]:
    token = str(session_id or "").strip()
    sessions = dict(status.get("sessions") or {})
    session = dict(sessions.get(token) or {})
    if not session:
        raise ValueError(f"session_id {token!r} is not registered in the work ledger runtime")
    if session.get("ended_at"):
        raise ValueError(f"session_id {token!r} has already ended; re-bootstrap before claiming")

    now_iso = now.isoformat()
    results: List[Dict[str, Any]] = []
    claimed_result_indexes: List[int] = []
    claims = list(session.get("claims") or [])
    for target_claim in requests:
        collisions: List[Dict[str, Any]] = []
        for other_id, other in sessions.items():
            if not isinstance(other, Mapping) or str(other_id) == token:
                continue
            if other.get("ended_at"):
                continue
            for claim in _session_active_claims(other, now=now):
                if not _claim_scopes_overlap(target_claim, claim):
                    continue
                collisions.append(
                    {
                        "session_id": str(other_id),
                        "actor": str(other.get("actor") or "unknown"),
                        "claim": _compact_claim(claim),
                    }
                )
        if collisions and require_exclusive:
            results.append(
                {
                    "schema": "work_ledger_claim_result_v1",
                    "status": "refused",
                    "reason": "exclusive_claim_refused_due_to_collision",
                    "session_id": token,
                    "scope_kind": target_claim["scope_kind"],
                    "scope_id": target_claim["scope_id"],
                    "td_id": target_claim["td_id"],
                    "path": target_claim["path"],
                    "work_item_id": target_claim["work_item_id"],
                    "collisions": collisions,
                }
            )
            continue

        claim_record = {
            "claim_id": mint_claim_id(),
            "scope_kind": target_claim["scope_kind"],
            "scope_id": target_claim["scope_id"],
            "td_id": target_claim["td_id"],
            "path": target_claim["path"],
            "work_item_id": target_claim["work_item_id"],
            "claimed_at": now_iso,
            "leased_until": leased_until,
            "released_at": None,
            "expired_at": None,
            "note": str(note or "").strip() or None,
            "release_reason": None,
            "require_exclusive": bool(require_exclusive),
        }
        claims.append(claim_record)
        claimed_result_indexes.append(len(results))
        results.append(
            {
                "schema": "work_ledger_claim_result_v1",
                "status": "claimed" if not collisions else "claimed_with_collision",
                "session_id": token,
                "scope_kind": target_claim["scope_kind"],
                "scope_id": target_claim["scope_id"],
                "td_id": target_claim["td_id"],
                "path": target_claim["path"],
                "work_item_id": target_claim["work_item_id"],
                "claim": _compact_claim(claim_record),
                "collisions": collisions,
            }
        )

    if not claimed_result_indexes:
        return results, claimed_result_indexes

    session["claims"] = claims
    touched_td_ids = list(session.get("touched_td_ids") or [])
    touched_work_item_ids = list(session.get("touched_work_item_ids") or [])
    for result_index in claimed_result_indexes:
        result = results[result_index]
        if result.get("scope_kind") == CLAIM_SCOPE_THREAD:
            scope_id = str(result.get("scope_id") or "")
            if scope_id and scope_id not in touched_td_ids:
                touched_td_ids.append(scope_id)
        if result.get("scope_kind") == CLAIM_SCOPE_WORK_ITEM:
            scope_id = str(result.get("scope_id") or "")
            if scope_id and scope_id not in touched_work_item_ids:
                touched_work_item_ids.append(scope_id)
    session["touched_td_ids"] = touched_td_ids
    session["touched_work_item_ids"] = touched_work_item_ids
    session["touched_work"] = True
    session["has_activity"] = True
    session["last_activity_at"] = work_ledger.utc_now()
    sessions[token] = session
    status["sessions"] = sessions
    return results, claimed_result_indexes


def claim_work_scope(
    repo_root: Path,
    *,
    session_id: str,
    scope_kind: str,
    scope_id: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
) -> Dict[str, Any]:
    """Record a forward-looking lease on a td_* or repo-relative path.

    The claim is soft by default: a collision (another effective-active
    session holding an overlapping unexpired claim) is returned in
    the response but does not block the claim. With `require_exclusive`
    the claim is refused when a collision is detected. In both cases the
    session gets a fresh activity timestamp so cohort_overview stops treating
    the work as unknown-scope.
    """
    token = str(session_id or "").strip()
    scope_kind_token = str(scope_kind or "").strip()
    if scope_kind_token not in CLAIM_SCOPE_KINDS:
        raise ValueError(f"scope_kind must be one of {sorted(CLAIM_SCOPE_KINDS)}")
    scope_token = str(scope_id or "").strip()
    if scope_kind_token == CLAIM_SCOPE_PATH:
        scope_token = _normalize_repo_claim_path(repo_root, scope_token)
    if not token or not scope_token:
        raise ValueError("session_id and scope_id are required for session-claim")
    lease = _clamp_lease(timedelta(minutes=float(lease_minutes or 0)))
    now = datetime.now(timezone.utc)
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(token) or {})
        if not session:
            raise ValueError(f"session_id {token!r} is not registered in the work ledger runtime")
        if session.get("ended_at"):
            raise ValueError(f"session_id {token!r} has already ended; re-bootstrap before claiming")

        if scope_kind_token == CLAIM_SCOPE_WORK_ITEM and not _looks_like_work_item_id(scope_token):
            raise ValueError("work_item_id claim requires a Task Ledger WorkItem-shaped id")

        target_claim = {
            "scope_kind": scope_kind_token,
            "scope_id": scope_token,
            "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
            "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
            "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
        }
        collisions: List[Dict[str, Any]] = []
        for other_id, other in sessions.items():
            if not isinstance(other, Mapping) or str(other_id) == token:
                continue
            if other.get("ended_at"):
                continue
            for claim in _session_active_claims(other, now=now):
                if not _claim_scopes_overlap(target_claim, claim):
                    continue
                collisions.append(
                    {
                        "session_id": str(other_id),
                        "actor": str(other.get("actor") or "unknown"),
                        "claim": _compact_claim(claim),
                    }
                )
        if collisions and require_exclusive:
            return {
                "schema": "work_ledger_claim_result_v1",
                "status": "refused",
                "reason": "exclusive_claim_refused_due_to_collision",
                "session_id": token,
                "scope_kind": scope_kind_token,
                "scope_id": scope_token,
                "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
                "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
                "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
                "collisions": collisions,
            }

        claim_record = {
            "claim_id": mint_claim_id(),
            "scope_kind": scope_kind_token,
            "scope_id": scope_token,
            "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
            "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
            "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
            "claimed_at": now.isoformat(),
            "leased_until": (now + lease).isoformat(),
            "released_at": None,
            "expired_at": None,
            "note": str(note or "").strip() or None,
            "release_reason": None,
            "require_exclusive": bool(require_exclusive),
        }
        claims = list(session.get("claims") or [])
        claims.append(claim_record)
        session["claims"] = claims
        if scope_kind_token == CLAIM_SCOPE_THREAD:
            touched = list(session.get("touched_td_ids") or [])
            if scope_token not in touched:
                touched.append(scope_token)
            session["touched_td_ids"] = touched
        if scope_kind_token == CLAIM_SCOPE_WORK_ITEM:
            touched_work_items = list(session.get("touched_work_item_ids") or [])
            if scope_token not in touched_work_items:
                touched_work_items.append(scope_token)
            session["touched_work_item_ids"] = touched_work_items
        session["touched_work"] = True
        session["has_activity"] = True
        session["last_activity_at"] = work_ledger.utc_now()
        sessions[token] = session
        status["sessions"] = sessions
        saved = _write_runtime_status(repo_root, status)
    return {
        "schema": "work_ledger_claim_result_v1",
        "status": "claimed" if not collisions else "claimed_with_collision",
        "session_id": token,
        "scope_kind": scope_kind_token,
        "scope_id": scope_token,
        "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
        "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
        "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
        "claim": _compact_claim(claim_record),
        "collisions": collisions,
        "generated_at": saved.get("generated_at"),
    }


def claim_work_scopes(
    repo_root: Path,
    *,
    session_id: str,
    scopes: Sequence[Mapping[str, Any]],
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
) -> List[Dict[str, Any]]:
    """Record multiple forward-looking leases with one runtime-status rebuild/write."""
    token = str(session_id or "").strip()
    if not token:
        raise ValueError("session_id is required for session-claim")
    requests = _prepare_claim_scope_requests(repo_root, scopes)
    if not requests:
        return []

    lease = _clamp_lease(timedelta(minutes=float(lease_minutes or 0)))
    now = datetime.now(timezone.utc)
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        results, claimed_result_indexes = _apply_claim_scope_requests_to_status(
            status,
            session_id=token,
            requests=requests,
            now=now,
            leased_until=(now + lease).isoformat(),
            note=note,
            require_exclusive=require_exclusive,
        )
        if not claimed_result_indexes:
            return results
        saved = _write_runtime_status(repo_root, status)
    for result_index in claimed_result_indexes:
        results[result_index]["generated_at"] = saved.get("generated_at")
    return results


def claim_work_thread(
    repo_root: Path,
    *,
    session_id: str,
    td_id: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
) -> Dict[str, Any]:
    """Record a forward-looking lease on a td_*.

    Compatibility wrapper for the original td_id-only claim API.
    """
    if _looks_like_work_item_id(td_id):
        return claim_work_item(
            repo_root,
            session_id=session_id,
            work_item_id=td_id,
            lease_minutes=lease_minutes,
            note=note,
            require_exclusive=require_exclusive,
        )
    return claim_work_scope(
        repo_root,
        session_id=session_id,
        scope_kind=CLAIM_SCOPE_THREAD,
        scope_id=td_id,
        lease_minutes=lease_minutes,
        note=note,
        require_exclusive=require_exclusive,
    )


def claim_work_item(
    repo_root: Path,
    *,
    session_id: str,
    work_item_id: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
) -> Dict[str, Any]:
    """Record a forward-looking lease on a Task Ledger WorkItem id."""
    return claim_work_scope(
        repo_root,
        session_id=session_id,
        scope_kind=CLAIM_SCOPE_WORK_ITEM,
        scope_id=work_item_id,
        lease_minutes=lease_minutes,
        note=note,
        require_exclusive=require_exclusive,
    )


def claim_work_path(
    repo_root: Path,
    *,
    session_id: str,
    path: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
) -> Dict[str, Any]:
    """Record a forward-looking lease on a repo-relative file or directory path."""
    return claim_work_scope(
        repo_root,
        session_id=session_id,
        scope_kind=CLAIM_SCOPE_PATH,
        scope_id=path,
        lease_minutes=lease_minutes,
        note=note,
        require_exclusive=require_exclusive,
    )


def release_claim(
    repo_root: Path,
    *,
    session_id: str,
    claim_id: str | None = None,
    td_id: str | None = None,
    path: str | None = None,
    reason: str | None = None,
) -> Dict[str, Any]:
    """Release an active claim by claim_id, td_id, or path on the current session.

    If only `td_id` or `path` is given, all the session's active claims on
    that scope are released (usually one).
    """
    token = str(session_id or "").strip()
    if not token:
        raise ValueError("session_id is required for release-claim")
    claim_token = str(claim_id or "").strip()
    td_token = str(td_id or "").strip()
    path_token = str(path or "").strip()
    if path_token:
        path_token = _normalize_repo_claim_path(repo_root, path_token)
    if not claim_token and not td_token and not path_token:
        raise ValueError("release-claim requires --claim-id, --td-id, or --path")
    release_reason = str(reason or "released_by_operator").strip() or "released_by_operator"
    now = datetime.now(timezone.utc)
    released: List[Dict[str, Any]] = []
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(token) or {})
        if not session:
            raise ValueError(f"session_id {token!r} is not registered in the work ledger runtime")
        claims = [dict(claim) for claim in session.get("claims") or [] if isinstance(claim, Mapping)]
        matched = False
        for claim in claims:
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            if claim_token and str(claim.get("claim_id") or "").strip() != claim_token:
                continue
            scope_kind, scope_id = _normalize_claim_scope(claim)
            if td_token and not (scope_kind == CLAIM_SCOPE_THREAD and scope_id == td_token):
                continue
            if path_token and not (scope_kind == CLAIM_SCOPE_PATH and scope_id == path_token):
                continue
            claim["released_at"] = now.isoformat()
            claim["release_reason"] = release_reason
            matched = True
            released.append(_compact_claim(claim))
        if not matched:
            return {
                "schema": "work_ledger_claim_result_v1",
                "status": "noop",
                "reason": "no_matching_active_claim",
                "session_id": token,
                "claim_id": claim_token or None,
                "td_id": td_token or None,
                "path": path_token or None,
            }
        session["claims"] = claims
        sessions[token] = session
        status["sessions"] = sessions
        saved = _write_runtime_status(repo_root, status)
    return {
        "schema": "work_ledger_claim_result_v1",
        "status": "released",
        "session_id": token,
        "released": released,
        "generated_at": saved.get("generated_at"),
    }


def sweep_expired_claims(
    repo_root: Path,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Mark any claim with leased_until < now as `expired_at=leased_until`.

    Idempotent. Expired claims are preserved (not deleted) so a crashed
    holder leaves a visible audit trail; sweep just makes the expiry
    explicit so cohort_overview stops flagging the claim as live.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    swept_details: List[Dict[str, Any]] = []
    if dry_run:
        status = _load_runtime_status_for_session_scan(repo_root)
        for session_id, session in (status.get("sessions") or {}).items():
            if not isinstance(session, Mapping):
                continue
            for claim in session.get("claims") or []:
                if not isinstance(claim, Mapping):
                    continue
                if claim.get("released_at") or claim.get("expired_at"):
                    continue
                leased_until = _parse_iso_datetime(claim.get("leased_until"))
                if leased_until is None or leased_until > current:
                    continue
                swept_details.append(
                    {
                        "session_id": str(session_id),
                        "claim_id": str(claim.get("claim_id") or ""),
                        "td_id": str(claim.get("td_id") or ""),
                        "leased_until": claim.get("leased_until"),
                    }
                )
        return _expired_claim_sweep_report(details=swept_details, dry_run=True)
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        swept_details = _mark_expired_claims_in_status(status, current=current)
        if not swept_details:
            return _expired_claim_sweep_report(
                details=[],
                dry_run=False,
                generated_at=status.get("generated_at"),
            )
        saved = _write_runtime_status(repo_root, status)
    return _expired_claim_sweep_report(
        details=swept_details,
        dry_run=False,
        generated_at=saved.get("generated_at"),
    )


def sweep_orphan_sessions(
    repo_root: Path,
    *,
    now: datetime | None = None,
    orphan_sweep_after: timedelta = ACTIVE_SESSION_ORPHAN_SWEEP_AFTER,
    dry_run: bool = False,
    exclude_session_ids: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Auto-finalize active sessions with no signal older than the sweep threshold.

    An orphaned session is one that claims to be active but has not emitted
    any lifecycle signal (hook heartbeat, CLI activity) for longer than
    `orphan_sweep_after`. Sweeping sets `ended_at` with `end_action =
    auto_orphan_sweep` and releases any active claims held by the session
    (release_reason=session_auto_swept). This is non-destructive: the
    session row, its touched_td_ids, its claim history, and any stale flag
    remain in place so a future audit can see what the crashed agent was
    doing. `exclude_session_ids` protects the in-flight bootstrapping
    session from sweeping itself.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    exclude = {str(sid).strip() for sid in (exclude_session_ids or []) if str(sid).strip()}
    swept_details: List[Dict[str, Any]] = []
    if dry_run:
        status = _load_runtime_status_for_session_scan(repo_root)
        for session_id, session in (status.get("sessions") or {}).items():
            if not isinstance(session, Mapping):
                continue
            if str(session_id) in exclude or session.get("ended_at"):
                continue
            if not _is_orphaned_active_session(session, now=current, orphan_after=orphan_sweep_after):
                continue
            last_signal = _session_last_signal_at(session)
            swept_details.append(
                {
                    "session_id": str(session_id),
                    "actor": str(session.get("actor") or "unknown"),
                    "phase_id": str(session.get("phase_id") or ""),
                    "last_signal_at": last_signal.isoformat() if last_signal is not None else None,
                    "idle_hours": (
                        round((current - last_signal).total_seconds() / 3600.0, 2)
                        if last_signal is not None
                        else None
                    ),
                    "active_claims": [
                        _compact_claim(claim)
                        for claim in _session_active_claims(session, now=current)
                    ],
                }
            )
        return _orphan_session_sweep_report(
            details=swept_details,
            dry_run=True,
            orphan_sweep_after=orphan_sweep_after,
        )
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        swept_details = _mark_orphan_sessions_in_status(
            status,
            current=current,
            orphan_sweep_after=orphan_sweep_after,
            exclude=exclude,
        )
        if not swept_details:
            return _orphan_session_sweep_report(
                details=[],
                dry_run=False,
                orphan_sweep_after=orphan_sweep_after,
                generated_at=status.get("generated_at"),
            )
        saved = _write_runtime_status(repo_root, status)
    return _orphan_session_sweep_report(
        details=swept_details,
        dry_run=False,
        orphan_sweep_after=orphan_sweep_after,
        generated_at=saved.get("generated_at"),
    )


def handle_hook_event(repo_root: Path, action: str, payload: Mapping[str, Any]) -> str:
    session_id = str(payload.get("session_id") or "").strip()
    if not session_id:
        return ""
    if action == "session-start":
        bootstrap = bootstrap_session(
            repo_root,
            session_id=session_id,
            actor="claude_code",
        )
        return str(bootstrap.get("additional_context") or "")
    if action in {"post-tool", "user-prompt"}:
        mark_session_activity(repo_root, session_id=session_id, action=action)
        return ""
    if action in {"session-end", "stop"}:
        finalize_session(repo_root, session_id=session_id, action=action)
        return ""
    return ""
