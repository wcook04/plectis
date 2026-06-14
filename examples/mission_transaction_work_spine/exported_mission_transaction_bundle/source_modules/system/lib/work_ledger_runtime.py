"""
[PURPOSE]
- Teleology: Runtime enforcement helper for the work ledger. Own Claude-session
  bootstrap, read receipts, activity tracking, stale-session detection, and the
  ephemeral runtime_status signal consumed by hooks, reactions, and attention surfaces.
- Mechanism: Persist a rebuildable session-status projection under
  state/work_ledger/runtime_status.json and keep the hook path thin.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import uuid
from bisect import bisect_left
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence
from urllib.parse import urlencode

from system.lib import work_ledger


WORK_LEDGER_RUNTIME_SCHEMA = "work_ledger_runtime_status_v1"
SHARED_SUBSTRATE_CONTENTION_ENVELOPE_SCHEMA = "shared_substrate_contention_envelope_v1"
RUNTIME_STATUS_REL = Path("state/work_ledger/runtime_status.json")
RUNTIME_LOCK_REL = Path("state/work_ledger/.runtime_status.lock")
ACTIVE_CLAIMS_SNAPSHOT_REL = Path("state/work_ledger/active_claims_snapshot.json")
_REBUILD_RUNTIME_STATUS_REPO_ROOT: Path | None = None
BOOTSTRAP_SLICE_LIMIT = 8
SESSION_COHORT_OVERVIEW_SCHEMA = "work_ledger_session_cohort_overview_v1"
HEARTBEAT_PARTICIPATION_SCHEMA = "work_ledger_heartbeat_participation_v0"
CONCURRENCY_REPAIR_ROW_SCHEMA = "work_ledger_concurrency_repair_row_v0"
DIRTY_TREE_BANKRUPTCY_PRESSURE_SCHEMA = "dirty_tree_bankruptcy_pressure_v0"
DIRTY_TREE_PRESSURE_ALIAS_SCHEMA = "dirty_tree_pressure_alias_v0"
DUPLICATE_CLAIM_DEDUPE_SCHEMA = "work_ledger_duplicate_same_session_claim_dedupe_v1"
RESIDENT_THREAD_GOVERNOR_SCHEMA = "work_ledger_resident_thread_governor_v0"
DIRTY_TREE_RESCUE_REF_PREFIX = "refs/aiw/rescue/dirty-tree"
DIRTY_TREE_RESCUE_MANIFEST_PREFIX = "rescue_manifests"
SESSION_COHORT_OVERVIEW_LIMIT = 12
SEED_SPEED_SNAPSHOT_OVERVIEW_LIMIT = 100
ACTIVE_SESSION_ORPHAN_AFTER = timedelta(hours=4)
RESIDENT_THREAD_WARM_AFTER = timedelta(minutes=10)
RESIDENT_THREAD_TERMINATE_AFTER = timedelta(minutes=30)
SESSION_TITLE_LIMIT = 180
SESSION_METADATA_TEXT_LIMIT = 240
ENDED_SESSION_CLAIM_COMPACTION_THRESHOLD = 2
ENDED_SESSION_SCOPE_REF_PREVIEW_LIMIT = 3
# --- Ended-session retention (keeps runtime_status.json from growing unbounded) ---
# runtime_status.json is the PRIMARY store of session runtime state — it is not
# reconstructable from the append-only work_ledger.jsonl — so old ended sessions
# are ARCHIVED to a sidecar before being dropped from the live file, never
# silently deleted. Retention only runs once the evictable (long-ended, no live
# claim, non-stale) count crosses the high-water mark, so every normal write and
# every small test fixture is a strict no-op. All values are env-overridable.
RUNTIME_STATUS_SESSIONS_ARCHIVE_REL = Path("state/work_ledger/runtime_status_sessions_archive.jsonl")
ENDED_SESSION_RETENTION_HIGH_WATER = 2000
# keep_max is the real bound: the most-recent N ended sessions stay in the hot
# file. min_age_days is a small safety floor (never evict a just-ended session);
# it must stay well below keep_max's churn-window or the file tracks the age
# window instead of the count. This repo ends hundreds of sessions/day, so 2
# days keeps the bound at ~keep_max rather than ~14 days of churn.
ENDED_SESSION_RETENTION_MAX = 1500
ENDED_SESSION_RETENTION_MIN_AGE_DAYS = 2
ENDED_SESSION_RETENTION_HIGH_WATER_ENV = "AIW_WORK_LEDGER_ENDED_RETENTION_HIGH_WATER"
ENDED_SESSION_RETENTION_MAX_ENV = "AIW_WORK_LEDGER_ENDED_RETENTION_MAX"
ENDED_SESSION_RETENTION_MIN_AGE_DAYS_ENV = "AIW_WORK_LEDGER_ENDED_RETENTION_MIN_AGE_DAYS"
# The archive is cold storage (only read on explicit drilldown), so it can grow
# slowly without hurting the hot path — but to avoid merely relocating unbounded
# growth, it rotates: once the live archive crosses the cap it is renamed to a
# single ".1" generation and a fresh file starts. Total on-disk archive is thus
# bounded at ~2x the cap; the oldest generation is the only thing ever dropped.
ENDED_SESSION_ARCHIVE_MAX_BYTES = 32 * 1024 * 1024
ENDED_SESSION_ARCHIVE_MAX_BYTES_ENV = "AIW_WORK_LEDGER_ARCHIVE_MAX_BYTES"
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
CLAIM_INTENT_HARD_MUTATION = "hard_mutation"
CLAIM_INTENT_SOFT_SIBLING = "soft_sibling"
CLAIM_INTENT_READ_ACCEPTANCE = "read_acceptance"
CLAIM_INTENT_APPEND_ONLY_LEDGER = "append_only_ledger"
CLAIM_INTENT_GENERATED_PROJECTION_REFRESH = "generated_projection_refresh"
CLAIM_INTENT_CLOSEOUT_FINALIZER = "closeout_finalizer"
CLAIM_INTENT_MERGE_COORDINATOR = "merge_coordinator"
CLAIM_INTENT_RUNTIME_RESOURCE_LEASE = "runtime_resource_lease"
CLAIM_INTENTS = {
    CLAIM_INTENT_HARD_MUTATION,
    CLAIM_INTENT_SOFT_SIBLING,
    CLAIM_INTENT_READ_ACCEPTANCE,
    CLAIM_INTENT_APPEND_ONLY_LEDGER,
    CLAIM_INTENT_GENERATED_PROJECTION_REFRESH,
    CLAIM_INTENT_CLOSEOUT_FINALIZER,
    CLAIM_INTENT_MERGE_COORDINATOR,
    CLAIM_INTENT_RUNTIME_RESOURCE_LEASE,
}
BLOCKING_CLAIM_INTENTS = {
    CLAIM_INTENT_HARD_MUTATION,
    CLAIM_INTENT_CLOSEOUT_FINALIZER,
    CLAIM_INTENT_MERGE_COORDINATOR,
}
CLAIM_CONFLICT_SCOPE_KINDS = set(CLAIM_SCOPE_KINDS) | {
    "hunk",
    "semantic_surface",
    "projection_owner",
    "ledger_row_family",
    "resource_fingerprint",
    "validation_receipt",
    "trace_hud_projection",
}
SESSION_WORKFLOW_MESSAGE_SCHEMA = "session_message_v1"
SESSION_WORKFLOW_MESSAGE_BUS_SCHEMA = "session_workflow_message_bus_v1"
SESSION_MESSAGE_INBOX_SURFACE_SCHEMA = "session_message_inbox_surface_v1"
SESSION_WORKFLOW_MESSAGE_ID_PREFIX = "smsg_"
SESSION_MESSAGE_SUBJECT_LIMIT = 160
SESSION_MESSAGE_BODY_LIMIT = 1200
SESSION_MESSAGE_REF_LIMIT = 12
RUNTIME_DISK_PRESSURE_RECEIPT_SCHEMA = "work_ledger_runtime_disk_pressure_receipt_v1"
RUNTIME_DISK_PRESSURE_ENV = "AIW_WORK_LEDGER_RUNTIME_MIN_FREE_BYTES"
RUNTIME_DISK_PRESSURE_MIN_FREE_BYTES = 100 * 1024 * 1024
SESSION_WORKFLOW_MESSAGE_TYPES = (
    "query_state",
    "query_claim_owner",
    "signal_blocker",
    "signal_release",
    "signal_resource_lease",
    "update_settlement_offer",
    "update_projection_handoff",
    "update_cap_claim",
    "acknowledge_merge_group",
)
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
GENERATED_SURFACE_CLAIM_LENS_SCHEMA = "generated_surface_claim_lens_v1"
CONCURRENCY_CLOSURE_STATE_LENS_SCHEMA = "concurrency_closure_state_lens_v1"
CAS_RETRY_HANDOFF_LENS_SCHEMA = "work_ledger_seed_speed_cas_retry_handoff_lens_v0"
MICROCOSM_GENERATED_ENTRY_SURFACES = (
    "microcosm-substrate/ORGANS.md",
    "microcosm-substrate/ARCHITECTURE.md",
    "microcosm-substrate/AGENT_ROUTES.md",
    "microcosm-substrate/atlas/agent_task_routes.json",
)


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


def _runtime_status_sessions_archive_path(repo_root: Path) -> Path:
    return repo_root / RUNTIME_STATUS_SESSIONS_ARCHIVE_REL


class RuntimeDiskPressureError(RuntimeError):
    """Raised before Work Ledger runtime writes when free disk space is below floor."""

    def __init__(self, receipt: Mapping[str, Any]) -> None:
        self.receipt = dict(receipt)
        super().__init__(str(self.receipt.get("message") or "work ledger runtime disk pressure"))


def _runtime_disk_pressure_min_free_bytes() -> int:
    raw = os.environ.get(RUNTIME_DISK_PRESSURE_ENV)
    if raw is None or not str(raw).strip():
        return RUNTIME_DISK_PRESSURE_MIN_FREE_BYTES
    try:
        parsed = int(str(raw).strip())
    except ValueError:
        return RUNTIME_DISK_PRESSURE_MIN_FREE_BYTES
    return max(parsed, 0)


def _existing_disk_probe_path(path: Path) -> Path:
    probe = path if path.exists() else path.parent
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def build_runtime_disk_pressure_receipt(
    path: Path,
    *,
    min_free_bytes: int | None = None,
) -> Dict[str, Any]:
    """Return a typed disk-floor receipt for Work Ledger runtime writes."""

    required = (
        _runtime_disk_pressure_min_free_bytes()
        if min_free_bytes is None
        else max(int(min_free_bytes), 0)
    )
    target = Path(path)
    probe_path = _existing_disk_probe_path(target)
    base: Dict[str, Any] = {
        "schema": RUNTIME_DISK_PRESSURE_RECEIPT_SCHEMA,
        "target_path": str(target),
        "probe_path": str(probe_path),
        "required_free_bytes": required,
        "floor_source": RUNTIME_DISK_PRESSURE_ENV
        if os.environ.get(RUNTIME_DISK_PRESSURE_ENV) is not None
        else "default",
        "separate_from_host_pressure": True,
    }
    try:
        usage = shutil.disk_usage(probe_path)
    except OSError as exc:
        base.update(
            {
                "status": "unavailable",
                "decision": "allow",
                "should_block_run": False,
                "reason": "disk_usage_unavailable",
                "error_class": type(exc).__name__,
                "message": str(exc),
            }
        )
        return base

    free = int(usage.free)
    should_block = free < required
    decision = "queue_until_disk_pressure_clears" if should_block else "allow"
    base.update(
        {
            "status": "blocked" if should_block else "clear",
            "decision": decision,
            "should_block_run": should_block,
            "reason": "free_space_below_work_ledger_runtime_floor"
            if should_block
            else "free_space_meets_work_ledger_runtime_floor",
            "total_bytes": int(usage.total),
            "used_bytes": int(usage.used),
            "free_bytes": free,
            "recommendation": "clear_disk_space_before_work_ledger_runtime_write"
            if should_block
            else "no_disk_pressure_action_required",
            "message": (
                "Work Ledger runtime write blocked: free disk space is below the runtime write floor."
                if should_block
                else "Work Ledger runtime write disk floor passed."
            ),
        }
    )
    return base


def _assert_runtime_disk_headroom(path: Path) -> Dict[str, Any]:
    receipt = build_runtime_disk_pressure_receipt(path)
    if receipt.get("should_block_run"):
        raise RuntimeDiskPressureError(receipt)
    return receipt


def _atomic_write_runtime_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Write rebuildable Work Ledger runtime projections without ledger-grade fsync cost."""
    _assert_runtime_disk_headroom(path)
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
        "archived_ended_sessions_total": 0,
        "stale_sessions": [],
        "recent_sweep_events": [],
        "cohort_overview": {
            "schema": SESSION_COHORT_OVERVIEW_SCHEMA,
            "generated_at": work_ledger.utc_now(),
            "counts": {},
            "active_sessions": [],
            "passive_external_observed_sessions": [],
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
            "archived_ended_sessions": 0,
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
    return _rebuild_runtime_status_with_repo_root(payload, repo_root)


def _rebuild_runtime_status_with_repo_root(
    payload: Mapping[str, Any],
    repo_root: Path,
) -> Dict[str, Any]:
    global _REBUILD_RUNTIME_STATUS_REPO_ROOT
    previous = _REBUILD_RUNTIME_STATUS_REPO_ROOT
    _REBUILD_RUNTIME_STATUS_REPO_ROOT = repo_root
    try:
        return rebuild_runtime_status(payload)
    finally:
        _REBUILD_RUNTIME_STATUS_REPO_ROOT = previous


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


def _apply_pass_heartbeat_to_session(
    session: Dict[str, Any],
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
    return heartbeat


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


def _external_mutation_path_count(session: Mapping[str, Any]) -> int:
    metadata = session.get("external_metadata")
    if not isinstance(metadata, Mapping):
        return 0
    rollout = metadata.get("rollout_activity")
    if not isinstance(rollout, Mapping):
        return 0
    mutation_paths = rollout.get("recent_mutation_paths")
    if isinstance(mutation_paths, Sequence) and not isinstance(mutation_paths, (str, bytes)):
        return len([path for path in mutation_paths if str(path or "").strip()])
    try:
        return int(rollout.get("recent_mutation_path_count") or 0)
    except (TypeError, ValueError):
        return 0


def _session_has_live_explicit_pass_heartbeat(
    session: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> bool:
    orphaned_active = _is_orphaned_active_session(
        session,
        now=now,
        orphan_after=orphan_after,
    )
    heartbeat = _compact_pass_heartbeat(
        session,
        now=now,
        orphaned_active=orphaned_active,
    )
    source = str(heartbeat.get("source") or "").strip()
    freshness = str(heartbeat.get("freshness_state") or "").strip()
    has_public_line = bool(
        str(heartbeat.get("current_pass_line") or "").strip()
        or str(heartbeat.get("last_pass_result_line") or "").strip()
    )
    return freshness == "live" and source in EXPLICIT_HEARTBEAT_SOURCES and has_public_line


def _session_has_coordination_signal(
    session: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> bool:
    try:
        open_todos_touched = int(session.get("open_todos_touched_this_session") or 0)
    except (TypeError, ValueError):
        open_todos_touched = 0
    try:
        write_count = int(session.get("writes") or 0)
    except (TypeError, ValueError):
        write_count = 0
    return bool(
        _session_active_claims(session, now=now)
        or session.get("touched_work")
        or session.get("touched_td_ids")
        or session.get("touched_work_item_ids")
        or open_todos_touched > 0
        or write_count > 0
        or session.get("session_had_ledger_append")
        or session.get("append_exempt")
        or _external_mutation_path_count(session) > 0
        or _session_has_live_explicit_pass_heartbeat(
            session,
            now=now,
            orphan_after=orphan_after,
        )
    )


def _session_claim_scope_kinds(session: Mapping[str, Any]) -> set[str]:
    kinds: set[str] = set()
    for raw in session.get("claims") or []:
        if not isinstance(raw, Mapping):
            continue
        scope_kind, scope_id = _normalize_claim_scope(raw)
        if scope_kind and scope_id:
            kinds.add(scope_kind)
    compacted_scope_counts = session.get("claims_compacted_scope_counts")
    if isinstance(compacted_scope_counts, Mapping):
        for scope_kind, count in compacted_scope_counts.items():
            try:
                count_int = int(count or 0)
            except (TypeError, ValueError):
                count_int = 0
            if str(scope_kind or "").strip() and count_int > 0:
                kinds.add(str(scope_kind))
    return kinds


def _session_requires_append_evidence(session: Mapping[str, Any]) -> bool:
    if session.get("session_had_ledger_append") or session.get("append_exempt"):
        return False
    try:
        open_todos_touched = int(session.get("open_todos_touched_this_session") or 0)
    except (TypeError, ValueError):
        open_todos_touched = 0
    try:
        write_count = int(session.get("writes") or 0)
    except (TypeError, ValueError):
        write_count = 0
    if (
        session.get("touched_td_ids")
        or session.get("touched_work_item_ids")
        or open_todos_touched > 0
        or write_count > 0
        or _external_mutation_path_count(session) > 0
    ):
        return True
    if not session.get("touched_work"):
        return False
    claim_kinds = _session_claim_scope_kinds(session)
    if not claim_kinds:
        return True
    return bool(claim_kinds - {CLAIM_SCOPE_PATH})


def _session_has_completed_nonblocking_pass(session: Mapping[str, Any]) -> bool:
    heartbeat = session.get("pass_heartbeat")
    if not isinstance(heartbeat, Mapping):
        return False
    pass_state = str(heartbeat.get("pass_state") or "").strip()
    if pass_state not in {"blocked", "done", "idle"}:
        return False
    return bool(
        str(heartbeat.get("last_pass_completed_at") or "").strip()
        or str(heartbeat.get("last_pass_result_line") or "").strip()
    )


def _is_passive_external_observed_session(
    session: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> bool:
    return bool(session.get("external_observed")) and not _session_has_coordination_signal(
        session,
        now=now,
        orphan_after=orphan_after,
    )


def _is_effective_active_session(
    session: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> bool:
    if session.get("ended_at"):
        return False
    if _is_orphaned_active_session(session, now=now, orphan_after=orphan_after):
        return False
    return not _is_passive_external_observed_session(
        session,
        now=now,
        orphan_after=orphan_after,
    )


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


def _compact_inactive_external_session_payload(session: Dict[str, Any]) -> None:
    if not session.get("external_observed") or not session.get("ended_at"):
        return
    title = str(session.get("external_title") or "")
    if not title:
        return
    compacted, truncated, full_chars = _compact_text(title, limit=SESSION_TITLE_LIMIT)
    prior_full_chars = int(session.get("external_title_full_chars") or 0)
    if truncated or session.get("external_title_truncated"):
        session["external_title"] = compacted
        session["external_title_truncated"] = True
        session["external_title_full_chars"] = max(full_chars, prior_full_chars)


def _compact_ended_released_claims(session: Dict[str, Any]) -> None:
    if not session.get("ended_at"):
        return
    claims = [
        dict(claim)
        for claim in session.get("claims") or []
        if isinstance(claim, Mapping)
    ]
    if len(claims) <= ENDED_SESSION_CLAIM_COMPACTION_THRESHOLD:
        return
    if any(not claim.get("released_at") and not claim.get("expired_at") for claim in claims):
        return

    scope_counts: dict[str, int] = {}
    release_reason_counts: dict[str, int] = {}
    released_count = 0
    expired_count = 0
    for claim in claims:
        scope_kind, _scope_id = _normalize_claim_scope(claim)
        if scope_kind:
            scope_counts[scope_kind] = scope_counts.get(scope_kind, 0) + 1
        if claim.get("expired_at"):
            expired_count += 1
        else:
            released_count += 1
            reason = str(claim.get("release_reason") or "released_without_reason").strip()
            release_reason_counts[reason] = release_reason_counts.get(reason, 0) + 1

    session["claims"] = []
    session["claims_compacted"] = True
    session["claims_compacted_profile"] = "ended_released_claims_v0"
    session["claims_compacted_threshold"] = ENDED_SESSION_CLAIM_COMPACTION_THRESHOLD
    session["claims_compacted_count"] = len(claims)
    session["claims_compacted_released_count"] = released_count
    session["claims_compacted_expired_count"] = expired_count
    session["claims_compacted_scope_counts"] = dict(sorted(scope_counts.items()))
    session["claims_compacted_release_reason_counts"] = dict(sorted(release_reason_counts.items()))


def _compact_ended_external_metadata(session: Dict[str, Any]) -> None:
    if not session.get("ended_at") or not session.get("external_observed"):
        return
    metadata = session.get("external_metadata")
    if not isinstance(metadata, Mapping) or not metadata:
        return
    compacted = _compact_external_metadata(metadata)
    if compacted == metadata:
        return
    session["external_metadata"] = compacted
    session["external_metadata_compacted"] = True
    session["external_metadata_compacted_profile"] = "ended_external_metadata_v0"


def _compact_ended_pass_heartbeat(session: Dict[str, Any]) -> None:
    if not session.get("ended_at"):
        return
    heartbeat = session.get("pass_heartbeat")
    if not isinstance(heartbeat, Mapping):
        return
    scope_refs = _normalize_scope_refs(heartbeat.get("scope_refs") or [])
    current_line = _compact_text(
        heartbeat.get("current_pass_line"),
        limit=PASS_CURRENT_LINE_LIMIT,
    )[0]
    result_line = _compact_text(
        heartbeat.get("last_pass_result_line"),
        limit=PASS_RESULT_LINE_LIMIT,
    )[0]
    session["pass_heartbeat"] = {
        "schema": heartbeat.get("schema") or PASS_HEARTBEAT_SCHEMA,
        "session_id": heartbeat.get("session_id") or session.get("session_id"),
        "actor": heartbeat.get("actor") or session.get("actor"),
        "phase_id": heartbeat.get("phase_id") or session.get("phase_id"),
        "family_id": heartbeat.get("family_id") or session.get("family_id"),
        "pass_id": heartbeat.get("pass_id"),
        "pass_seq": int(heartbeat.get("pass_seq") or 0),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": current_line,
        "last_pass_result_line": result_line,
        "scope_ref_count": len(scope_refs),
        "scope_refs_preview": scope_refs[:ENDED_SESSION_SCOPE_REF_PREVIEW_LIMIT],
        "updated_at": heartbeat.get("updated_at"),
        "expires_at": heartbeat.get("expires_at"),
        "current_pass_updated_at": heartbeat.get("current_pass_updated_at"),
        "last_pass_completed_at": heartbeat.get("last_pass_completed_at"),
        "source": heartbeat.get("source") or "manual_cli",
        "compacted_profile": "ended_pass_heartbeat_v0",
    }
    session["pass_heartbeat_compacted"] = True
    session["pass_heartbeat_scope_ref_count"] = len(scope_refs)


def _compact_session(
    session: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
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
    claimed_paths = {
        str(claim.get("path") or "").strip()
        for claim in active_claims
        if str(claim.get("path") or "").strip()
    }
    unclaimed_touched_td_ids: List[str] = []
    unclaimed_touched_path_ids: List[str] = []
    if now is not None:
        for td_id in touched_td_ids:
            if not td_id:
                continue
            if _looks_like_repo_path_token(td_id):
                if not _path_token_claimed_by_path_claim(
                    td_id,
                    claimed_paths,
                    repo_root=repo_root,
                ):
                    unclaimed_touched_path_ids.append(td_id)
                continue
            if td_id not in claimed_td_ids:
                unclaimed_touched_td_ids.append(td_id)
    unclaimed_touched_work_item_ids = [
        work_item_id
        for work_item_id in touched_work_item_ids
        if work_item_id
        and not _touched_work_item_claimed_by_alias(
            work_item_id,
            claimed_work_item_ids,
        )
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
        "unclaimed_touched_path_ids": unclaimed_touched_path_ids,
        "unclaimed_touched_work_item_ids": unclaimed_touched_work_item_ids,
        "open_todos_touched_this_session": int(
            session.get("open_todos_touched_this_session") or 0
        ),
    }


def _touched_work_item_claimed_by_alias(
    touched_work_item_id: str,
    claimed_work_item_ids: Iterable[str],
) -> bool:
    """Return whether this same session has claimed a canonical child of an alias.

    This is deliberately narrower than arbitrary prefix matching: an active
    claim for `foo_bar` can cover touched bridge alias `foo`, but `foobar` cannot.
    The signal answers "does this session have a live owner lane?" and does not
    create cross-session WorkItem equivalence.
    """
    touched = str(touched_work_item_id or "").strip()
    if not touched:
        return False
    for claimed_item in claimed_work_item_ids:
        claimed = str(claimed_item or "").strip()
        if not claimed:
            continue
        if claimed == touched:
            return True
        if claimed.startswith(f"{touched}_"):
            return True
    return False


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


def coordination_count_semantics(
    counts: Mapping[str, Any],
    *,
    heartbeat: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    heartbeat_counts = heartbeat if isinstance(heartbeat, Mapping) else {}

    def _count(key: str, default: int = 0) -> int:
        value = counts.get(key)
        if value is None:
            value = heartbeat_counts.get(key)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    raw_active = _count("active_sessions")
    effective_active = _count("effective_active_sessions")
    passive_external = _count("passive_external_observed_sessions")
    orphaned_active = _count("orphaned_active_sessions")
    unclassified = max(
        0,
        raw_active - effective_active - passive_external - orphaned_active,
    )
    return {
        "schema": "work_ledger_coordination_count_semantics_v0",
        "live_coordination_count_field": "effective_active_sessions",
        "raw_active_sessions_field": "active_sessions",
        "active_sessions_role": "raw_open_runtime_rows_not_live_agent_count",
        "effective_active_sessions_role": (
            "claim_or_heartbeat_backed_live_coordination_sessions"
        ),
        "passive_external_observed_sessions_role": (
            "host_imported_thread_rows_not_live_coordination_pressure"
        ),
        "orphaned_active_sessions_role": (
            "unfinalized_runtime_rows_requiring_sweep_not_live_agent_count"
        ),
        "raw_active_sessions_counted_as_live_agents": False,
        "live_coordination_count": effective_active,
        "raw_active_session_count": raw_active,
        "passive_external_observed_session_count": passive_external,
        "orphaned_active_session_count": orphaned_active,
        "unclassified_active_session_count": unclassified,
    }


def _resident_thread_pressure_active(pressure_mode: str) -> bool:
    return str(pressure_mode or "").strip() in {
        "degraded",
        "relief_window",
        "recovery_monitoring",
    }


def _resident_thread_claim_refs(
    active_claims: Sequence[Mapping[str, Any]],
    *,
    limit: int = 4,
) -> List[Dict[str, Any]]:
    refs: List[Dict[str, Any]] = []
    for claim in list(active_claims)[: max(0, int(limit or 0))]:
        refs.append(
            {
                "claim_id": claim.get("claim_id"),
                "scope_kind": claim.get("scope_kind"),
                "scope_id": claim.get("scope_id"),
                "path": claim.get("path"),
                "td_id": claim.get("td_id"),
                "work_item_id": claim.get("work_item_id"),
                "leased_until": claim.get("leased_until"),
            }
        )
    return refs


def _resident_thread_action_command(
    *,
    session_id: str,
    action: str,
    pressure_mode: str,
    idle_seconds: int | None,
    active_claim_count: int,
    warm_after: timedelta,
    terminate_after: timedelta,
) -> str:
    quoted_session = _quote_cli(session_id)
    idle_arg = str(float(idle_seconds or 0))
    if action == "yield_request":
        return _wl_command(
            "session-yield-request",
            f"--target-session-id {quoted_session}",
            "--target-class low_progress_session",
            "--requested-action yield",
            "--owner-status quiet_active_claim",
            f"--pressure-mode {_quote_cli(pressure_mode)}",
            f"--idle-age-s {idle_arg}",
            f"--last-heartbeat-age-s {idle_arg}",
            f"--active-claim-count {active_claim_count}",
            "--result-note 'resident-thread-governor: claim is quiet beyond warm threshold'",
            "--dry-run",
        )
    if action == "nap":
        return _wl_command(
            "session-yield-request",
            f"--target-session-id {quoted_session}",
            "--target-class idle_session",
            "--requested-action yield",
            "--owner-status idle_unclaimed",
            f"--pressure-mode {_quote_cli(pressure_mode)}",
            f"--idle-age-s {idle_arg}",
            "--result-note 'resident-thread-governor: unclaimed idle thread can downshift'",
            "--dry-run",
        )
    if action == "stale_claim_sweep":
        return _wl_command("session-status", f"--session-id {quoted_session} --full")
    if action == "terminate_grace":
        minutes = int(terminate_after.total_seconds() // 60)
        return _wl_command(
            "session-status",
            f"--session-id {quoted_session} --full # verify still unclaimed before {minutes}m host-grace termination",
        )
    if action == "archive_only":
        hours = max(0.01, terminate_after.total_seconds() / 3600.0)
        return _wl_command("session-sweep", f"--dry-run --orphan-after-hours {hours:.3f}")
    if action == "keep":
        minutes = int(warm_after.total_seconds() // 60)
        return _wl_command(
            "session-status",
            f"--session-id {quoted_session} --full # recheck after {minutes}m warm threshold",
        )
    return _wl_command("session-status", f"--session-id {quoted_session} --full")


def _resident_thread_row(
    session: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
    now: datetime,
    warm_after: timedelta,
    terminate_after: timedelta,
    pressure_mode: str,
) -> Dict[str, Any]:
    compact = _compact_session(
        session,
        repo_root=repo_root,
        now=now,
        orphan_after=ACTIVE_SESSION_ORPHAN_AFTER,
    )
    session_id = str(compact.get("session_id") or "").strip()
    active_claims = [
        claim for claim in compact.get("active_claims") or [] if isinstance(claim, Mapping)
    ]
    active_claim_count = len(active_claims)
    idle_seconds_raw = compact.get("idle_seconds")
    try:
        idle_seconds = int(idle_seconds_raw) if idle_seconds_raw is not None else None
    except (TypeError, ValueError):
        idle_seconds = None
    comparable_idle = idle_seconds
    if comparable_idle is None:
        comparable_idle = int(terminate_after.total_seconds()) + 1
    warm_seconds = int(warm_after.total_seconds())
    terminate_seconds = int(terminate_after.total_seconds())
    pressure_active = _resident_thread_pressure_active(pressure_mode)
    heartbeat = (
        dict(compact.get("pass_heartbeat") or {})
        if isinstance(compact.get("pass_heartbeat"), Mapping)
        else {}
    )

    if active_claim_count:
        protected = True
        safe_to_nap = False
        safe_to_terminate = False
        if comparable_idle >= terminate_seconds:
            state = "idle_claim_stale"
            action = "stale_claim_sweep"
            reason = (
                "active claim is quiet beyond terminate threshold; demote or release the "
                "claim through Work Ledger before any host-level termination"
            )
        elif comparable_idle >= warm_seconds:
            state = "warm_claim_quiet"
            action = "yield_request"
            reason = "active claim is quiet beyond warm threshold; ask owner to yield or refresh"
        else:
            state = "hot_active_claim"
            action = "keep"
            reason = "active claim still inside warm threshold"
    else:
        protected = False
        if bool(compact.get("orphaned_active")) and comparable_idle >= terminate_seconds:
            state = "archived_dead"
            action = "archive_only"
            reason = "runtime row is orphaned and unclaimed; sweep/archive before counting as live"
        elif comparable_idle >= terminate_seconds:
            state = "terminating_grace" if pressure_active else "suspended_resume_ready"
            action = "terminate_grace" if pressure_active else "archive_only"
            reason = (
                "unclaimed session is quiet beyond terminate threshold"
                if pressure_active
                else "unclaimed session is quiet beyond terminate threshold but host pressure is not active"
            )
        elif comparable_idle >= warm_seconds:
            state = "idle_unclaimed"
            action = "nap" if pressure_active else "keep"
            reason = (
                "unclaimed session is quiet beyond warm threshold and host pressure is active"
                if pressure_active
                else "unclaimed session is quiet beyond warm threshold; keep warm without pressure"
            )
        else:
            state = "idle_unclaimed"
            action = "keep"
            reason = "unclaimed session is still inside warm threshold"
        safe_to_nap = action == "nap"
        safe_to_terminate = action == "terminate_grace"

    return {
        "schema": "work_ledger_resident_thread_governor_row_v0",
        "session_id": session_id,
        "actor": compact.get("actor"),
        "phase_id": compact.get("phase_id"),
        "state": state,
        "recommended_action": action,
        "reason": reason,
        "idle_seconds": idle_seconds,
        "idle_minutes": round((idle_seconds or 0) / 60.0, 2) if idle_seconds is not None else None,
        "last_signal_at": compact.get("last_signal_at"),
        "last_activity_at": compact.get("last_activity_at"),
        "external_observed": bool(compact.get("external_observed")),
        "external_source": compact.get("external_source"),
        "freshness_state": heartbeat.get("freshness_state"),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": heartbeat.get("current_pass_line"),
        "active_claim_count": active_claim_count,
        "active_claim_refs": _resident_thread_claim_refs(active_claims),
        "protected_by_active_claim": protected,
        "safe_to_nap": safe_to_nap,
        "safe_to_terminate_after_grace": safe_to_terminate,
        "blocked_by_dirty_claim": active_claim_count > 0 and comparable_idle >= terminate_seconds,
        "drilldown_command": _wl_command("session-status", f"--session-id {_quote_cli(session_id)} --full"),
        "safe_next_command": _resident_thread_action_command(
            session_id=session_id,
            action=action,
            pressure_mode=pressure_mode,
            idle_seconds=idle_seconds,
            active_claim_count=active_claim_count,
            warm_after=warm_after,
            terminate_after=terminate_after,
        ),
    }


def build_resident_thread_governor(
    status: Mapping[str, Any],
    *,
    now: datetime | None = None,
    warm_after: timedelta = RESIDENT_THREAD_WARM_AFTER,
    terminate_after: timedelta = RESIDENT_THREAD_TERMINATE_AFTER,
    pressure_mode: str = "degraded",
    limit: int = SESSION_COHORT_OVERVIEW_LIMIT,
) -> Dict[str, Any]:
    """Build a read-only triage packet for resident thread pressure.

    This surface intentionally stops at classification and owner-visible request
    commands. It never treats an active claim as killable host pressure.
    """
    now = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    if warm_after <= timedelta(seconds=0):
        warm_after = RESIDENT_THREAD_WARM_AFTER
    if terminate_after <= warm_after:
        terminate_after = max(
            warm_after + timedelta(minutes=1),
            RESIDENT_THREAD_TERMINATE_AFTER,
        )
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    active_sessions = [
        dict(session)
        for session in sessions_payload.values()
        if isinstance(session, Mapping) and not session.get("ended_at")
    ]
    rows = [
        _resident_thread_row(
            session,
            now=now,
            warm_after=warm_after,
            terminate_after=terminate_after,
            pressure_mode=pressure_mode,
        )
        for session in active_sessions
    ]
    action_rank = {
        "stale_claim_sweep": 0,
        "terminate_grace": 1,
        "nap": 2,
        "yield_request": 3,
        "archive_only": 4,
        "keep": 5,
    }
    rows.sort(
        key=lambda row: (
            action_rank.get(str(row.get("recommended_action") or ""), 99),
            -(int(row.get("idle_seconds") or 0)),
            str(row.get("session_id") or ""),
        )
    )
    state_counts: Dict[str, int] = defaultdict(int)
    action_counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        state_counts[str(row.get("state") or "unknown")] += 1
        action_counts[str(row.get("recommended_action") or "unknown")] += 1
    safe_limit = max(0, int(limit or 0))
    limited_rows = rows[:safe_limit] if safe_limit else []
    return {
        "schema": RESIDENT_THREAD_GOVERNOR_SCHEMA,
        "generated_at": now.isoformat(),
        "pressure_mode": pressure_mode,
        "dry_run": True,
        "thresholds": {
            "warm_after_seconds": int(warm_after.total_seconds()),
            "terminate_after_seconds": int(terminate_after.total_seconds()),
            "warm_after_minutes": round(warm_after.total_seconds() / 60.0, 3),
            "terminate_after_minutes": round(terminate_after.total_seconds() / 60.0, 3),
        },
        "counts": {
            "resident_threads": len(rows),
            "hot_active_claims": state_counts.get("hot_active_claim", 0),
            "warm_claim_quiet": state_counts.get("warm_claim_quiet", 0),
            "idle_unclaimed_over_10m": sum(
                1
                for row in rows
                if not row.get("protected_by_active_claim")
                and (row.get("idle_seconds") or 0) >= int(warm_after.total_seconds())
            ),
            "idle_unclaimed_over_30m": sum(
                1
                for row in rows
                if not row.get("protected_by_active_claim")
                and (row.get("idle_seconds") or 0) >= int(terminate_after.total_seconds())
            ),
            "safe_to_nap": sum(1 for row in rows if row.get("safe_to_nap")),
            "safe_to_terminate_after_grace": sum(
                1 for row in rows if row.get("safe_to_terminate_after_grace")
            ),
            "blocked_by_dirty_claim": sum(1 for row in rows if row.get("blocked_by_dirty_claim")),
        },
        "state_counts": dict(sorted(state_counts.items())),
        "action_counts": dict(sorted(action_counts.items())),
        "rows": limited_rows,
        "rows_omitted": max(0, len(rows) - len(limited_rows)),
        "policy": {
            "active_claim_blocks_host_termination": True,
            "claim_state_demoted_before_process_termination": True,
            "terminate_grace_requires_unclaimed_session": True,
            "yield_request_is_owner_visible_not_signal": True,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_claim_terminated": True,
        },
        "drilldown_commands": {
            "session_status": _wl_command("session-status", "--overview --cards-only --limit 12"),
            "session_claims": _wl_command(
                "session-claims",
                "--refresh --session-summary --limit 12 --cards-only",
            ),
            "resident_pressure_relief": _wl_command("resident-pressure-relief", "--help"),
        },
    }


def mint_session_message_id() -> str:
    return f"{SESSION_WORKFLOW_MESSAGE_ID_PREFIX}{uuid.uuid4().hex[:16]}"


def _bounded_session_message_text(value: Any, *, limit: int) -> str:
    text = str(value or "").strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _bounded_session_message_refs(values: Sequence[Any] | str | None) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        raw_values: Sequence[Any] = [values]
    else:
        raw_values = values
    refs: list[str] = []
    for value in raw_values:
        token = str(value or "").strip()
        if token:
            refs.append(token)
        if len(refs) >= SESSION_MESSAGE_REF_LIMIT:
            break
    return refs


def _session_message_receipt(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("session_message")
    if isinstance(nested, Mapping):
        return dict(nested)
    if row.get("schema") == SESSION_WORKFLOW_MESSAGE_SCHEMA:
        return dict(row)
    return {}


def build_session_message_receipt(
    *,
    from_session_id: str,
    to_session_id: str,
    message_type: str = "signal_blocker",
    body: str,
    subject: str | None = None,
    message_id: str | None = None,
    related_paths: Sequence[Any] | str | None = (),
    related_request_id: str | None = None,
    reply_to_message_id: str | None = None,
    requires_ack: bool = False,
    issued_at: str | None = None,
) -> dict[str, Any]:
    """Build a bounded append-only Work Ledger session message."""
    from_id = str(from_session_id or "").strip() or "unknown"
    to_id = str(to_session_id or "").strip() or "unknown"
    msg_type = str(message_type or "signal_blocker").strip().lower()
    if msg_type not in SESSION_WORKFLOW_MESSAGE_TYPES:
        expected = ", ".join(SESSION_WORKFLOW_MESSAGE_TYPES)
        raise ValueError(f"session message type must be one of: {expected}")
    msg_id = str(message_id or "").strip() or mint_session_message_id()
    body_text = _bounded_session_message_text(body, limit=SESSION_MESSAGE_BODY_LIMIT)
    if not body_text:
        raise ValueError("session message body is required")
    subject_text = _bounded_session_message_text(
        subject or msg_type.replace("_", " "),
        limit=SESSION_MESSAGE_SUBJECT_LIMIT,
    )
    related = _bounded_session_message_refs(related_paths)
    target_arg = _quote_cli(to_id)
    from_arg = _quote_cli(from_id)
    ack_command = None
    if from_id != "unknown":
        ack_command = _wl_command(
            "session-message",
            f"--from-session-id {target_arg}",
            f"--to-session-id {from_arg}",
            "--message-type acknowledge_merge_group",
            f"--reply-to-message-id {_quote_cli(msg_id)}",
            "--subject 'ack'",
            "--body '<acknowledgement>'",
        )
    return {
        "schema": SESSION_WORKFLOW_MESSAGE_SCHEMA,
        "message_id": msg_id,
        "issued_at": issued_at or datetime.now(timezone.utc).isoformat(),
        "from_session_id": from_id,
        "to_session_id": to_id,
        "message_type": msg_type,
        "subject": subject_text,
        "body": body_text,
        "related_paths": related,
        "related_request_id": str(related_request_id or "").strip() or None,
        "reply_to_message_id": str(reply_to_message_id or "").strip() or None,
        "requires_ack": bool(requires_ack),
        "ack_command": ack_command,
        "reply_command": ack_command,
        "inbox_command": _wl_command(
            "session-message-inbox",
            f"--session-id {target_arg}",
            "--limit 12",
        ),
        "sender_inbox_command": _wl_command(
            "session-message-inbox",
            f"--session-id {from_arg}",
            "--include-sent --limit 12",
        ),
        "transport_boundary": {
            "authority": "state/work_ledger/session_messages.jsonl",
            "codex_thread_interrupts": "optional_convenience_not_authority",
            "claude_code_delivery": "poll_disk_backed_inbox_or_shell_command",
            "no_process_signal_sent": True,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _session_message_inbox_api_url(
    *,
    session_id: str,
    limit: int,
    include_sent: bool = False,
) -> str:
    params: dict[str, Any] = {
        "session_id": str(session_id or "").strip() or "unknown",
        "limit": max(1, int(limit or 1)),
    }
    if include_sent:
        params["include_sent"] = "true"
    return f"/api/agent-observability/session-message-inbox?{urlencode(params)}"


def build_session_message_inbox_surface(
    *,
    session_id: str,
    message_events: Sequence[Mapping[str, Any]] = (),
    limit: int = 12,
    include_sent: bool = False,
) -> dict[str, Any]:
    """Return a session-filtered inbox over the append-only message bus."""
    target_session_id = str(session_id or "").strip() or "unknown"
    bounded_limit = max(1, int(limit or 1))
    messages = [
        receipt
        for row in message_events or []
        if (receipt := _session_message_receipt(row))
    ]
    replies_by_parent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for message in messages:
        parent_id = str(message.get("reply_to_message_id") or "").strip()
        if parent_id:
            replies_by_parent[parent_id].append(message)

    inbox_rows: list[dict[str, Any]] = []
    pending_rows: list[dict[str, Any]] = []
    sent_rows: list[dict[str, Any]] = []
    for message in messages:
        to_id = str(message.get("to_session_id") or "").strip()
        from_id = str(message.get("from_session_id") or "").strip()
        inbound = to_id == target_session_id
        outbound = from_id == target_session_id
        if not inbound and not (include_sent and outbound):
            continue
        message_id = str(message.get("message_id") or "").strip()
        replies = replies_by_parent.get(message_id, [])
        row = dict(message)
        row["schema"] = "session_message_inbox_row_v1"
        row["direction"] = "inbound" if inbound else "sent"
        row["reply_count"] = len(replies)
        row["latest_reply"] = dict(replies[-1]) if replies else None
        row["acknowledged"] = bool(replies)
        row["pending"] = bool(inbound and message.get("requires_ack") and not replies)
        row["message_inbox_command"] = _wl_command(
            "session-message-inbox",
            f"--session-id {_quote_cli(target_session_id)}",
            f"--limit {bounded_limit}",
        )
        if row["direction"] == "sent":
            sent_rows.append(row)
        else:
            inbox_rows.append(row)
            if row["pending"]:
                pending_rows.append(row)

    latest_inbound = list(reversed(inbox_rows))
    latest_pending = list(reversed(pending_rows))
    latest_sent = list(reversed(sent_rows))
    inbox_api_url = _session_message_inbox_api_url(
        session_id=target_session_id,
        limit=bounded_limit,
    )
    include_sent_api_url = _session_message_inbox_api_url(
        session_id=target_session_id,
        limit=bounded_limit,
        include_sent=True,
    )
    for row in latest_inbound + latest_pending + latest_sent:
        row["agent_observability_inbox_url"] = (
            include_sent_api_url if row["direction"] == "sent" else inbox_api_url
        )
    return {
        "schema": SESSION_MESSAGE_INBOX_SURFACE_SCHEMA,
        "session_id": target_session_id,
        "latest_messages": latest_inbound[:bounded_limit],
        "pending_messages": latest_pending[:bounded_limit],
        "sent_messages": latest_sent[:bounded_limit] if include_sent else [],
        "counts": {
            "message_event_count": len(messages),
            "inbox_message_count": len(inbox_rows),
            "pending_message_count": len(pending_rows),
            "sent_message_count": len(sent_rows) if include_sent else 0,
            "reply_event_count": sum(1 for message in messages if message.get("reply_to_message_id")),
        },
        "recommended_commands": {
            "poll_inbox": _wl_command(
                "session-message-inbox",
                f"--session-id {_quote_cli(target_session_id)}",
                f"--limit {bounded_limit}",
            ),
            "send_message_template": _wl_command(
                "session-message",
                "--from-session-id '<requesting session>'",
                f"--to-session-id {_quote_cli(target_session_id)}",
                "--message-type signal_blocker",
                "--subject '<short subject>'",
                "--body '<message>'",
            ),
            "ack_first_pending": latest_pending[0].get("ack_command") if latest_pending else None,
        },
        "recommended_surfaces": {
            "agent_observability_inbox": inbox_api_url,
            "agent_observability_with_sent": include_sent_api_url,
        },
        "transport_boundary": {
            "authority": "state/work_ledger/session_messages.jsonl",
            "codex_thread_interrupts": "optional_convenience_not_authority",
            "claude_code_delivery": "poll_disk_backed_inbox_or_shell_command",
            "agent_observability_endpoint": "/api/agent-observability/session-message-inbox",
            "no_process_signal_sent": True,
        },
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }


def _duration_hours_token(duration: timedelta) -> str:
    hours = duration.total_seconds() / 3600.0
    if hours.is_integer():
        return str(int(hours))
    return f"{hours:.3f}".rstrip("0").rstrip(".")


def _orphan_visibility_sweep_command(orphan_after: timedelta, *args: str) -> str:
    return _wl_command(
        "session-sweep",
        "--dry-run",
        f"--orphan-after-hours {_duration_hours_token(orphan_after)}",
        *args,
    )


def _stale_append_repair_route(session: Mapping[str, Any]) -> Dict[str, Any]:
    session_id = str(session.get("session_id") or "<session_id>")
    session_arg = _quote_cli(session_id)
    ended = bool(session.get("ended_at"))
    has_append = bool(session.get("session_had_ledger_append"))
    append_exempt = bool(session.get("append_exempt"))
    if ended and not has_append and not append_exempt:
        read_receipt_id = str(session.get("read_receipt_id") or "").strip()
        details: Dict[str, Any] = {
            "sample_repair_state": "ended_without_append_or_exemption",
            "triage_reason": (
                "session is already ended; inspect durable evidence before recording "
                "append-exempt closeout"
            ),
        }
        if read_receipt_id:
            details["append_exempt_template_command"] = _wl_command(
                "session-finalize",
                f"--session-id {session_arg}",
                "--action append_exempt_closeout",
                f"--read-receipt-id {_quote_cli(read_receipt_id)}",
                "--append-exempt-reason <commit-or-projection-closeout>",
                "--append-exempt-ref <commit-or-receipt-ref>",
            )
        return {
            "why_blocked": (
                "Stale session is already ended without Work Ledger append or "
                "append-exempt evidence; inspect the session before recording an "
                "evidence-backed append-exempt closeout."
            ),
            "owning_surface": "work_ledger.session_status",
            "safe_next_command": _wl_command(
                "session-status",
                f"--session-id {session_arg}",
                "--full",
            ),
            "details": details,
        }
    return {
        "why_blocked": (
            "Stale sessions may still owe Work Ledger append/finalize work; close "
            "normal sessions with session-finalize, and use append-exempt finalize "
            "only for commit/projection-only evidence."
        ),
        "owning_surface": "work_ledger.session_finalize",
        "safe_next_command": _wl_command("session-finalize", f"--session-id {session_arg}"),
        "details": {"sample_repair_state": "active_or_finalizable_stale_session"},
    }


def _mission_command(*args: str) -> str:
    suffix = " ".join(arg for arg in args if arg)
    base = "./repo-python tools/meta/control/mission_transaction_preflight.py"
    return f"{base} {suffix}".strip()


def _residual_capture_command(tag: str = "concurrency_actionability") -> str:
    title = f"Work Ledger residual: {tag}"
    return (
        "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
        "--created-by codex --confidence 0.85 "
        f"--tag {shlex.quote(tag)} --tag work_ledger "
        f"--title {shlex.quote(title)} --statement {shlex.quote('<residual>')}"
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
        session.get("touched_work")
        or open_todos_touched > 0
        or str(session.get("external_title") or "").strip()
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
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> List[Dict[str, Any]]:
    effective_active = int(counts.get("effective_active_sessions") or 0)
    orphaned_active = int(counts.get("orphaned_active_sessions") or 0)
    active_claims = int(counts.get("active_claims") or 0)
    stale_sessions = int(counts.get("stale_sessions") or 0)
    stale_append_obligations = int(
        counts.get("stale_append_obligations", stale_sessions) or 0
    )
    stale_claim_only = int(
        counts.get(
            "stale_claim_only_sessions",
            max(0, stale_sessions - stale_append_obligations),
        )
        or 0
    )
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
    stale_status = _monitor_status(watch=stale_append_obligations > 0)
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
            "drilldown": _wl_command("session-status", "--seed-speed --limit 12"),
        },
        {
            "card_id": "orphaned_sessions",
            "label": "Orphaned Sessions",
            "status": orphaned_status,
            "risk_band": _monitor_risk_band(orphaned_status),
            "count": orphaned_active,
            "summary": (
                f"{orphaned_active} active sessions are older than the orphan visibility threshold; "
                "run the thresholded dry-run before any mutating sweep"
            ),
            "details": {
                "visibility_threshold_hours": _duration_hours_token(orphan_after),
                "auto_sweep_threshold_hours": _duration_hours_token(
                    ACTIVE_SESSION_ORPHAN_SWEEP_AFTER
                ),
                "dry_run_command": _orphan_visibility_sweep_command(orphan_after),
                "mutation_rule": (
                    "Only run a mutating sweep when the thresholded dry-run names rows. "
                    "The default session-sweep threshold is intentionally more conservative."
                ),
            },
            "drilldown": _orphan_visibility_sweep_command(orphan_after),
        },
        {
            "card_id": "stale_append_obligations",
            "label": "Stale Append Obligations",
            "status": stale_status,
            "risk_band": _monitor_risk_band(stale_status),
            "count": stale_append_obligations,
            "summary": (
                f"{stale_append_obligations} sessions have stale Work Ledger append "
                f"obligations; {stale_claim_only} claim-only stale sessions are demoted"
            ),
            "details": {
                "stale_sessions": stale_sessions,
                "stale_append_obligations": stale_append_obligations,
                "stale_claim_only_sessions": stale_claim_only,
            },
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
    if unknown_scope_count > 1:
        return "claim_or_finalize_unknown_scope_before_landing"
    if unclaimed_touched_count:
        return "claim_touched_work_before_landing"
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
            "--current-pass-line '<current pass line>'",
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


def _session_lifecycle_repair_rows(
    card: Mapping[str, Any],
    *,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> List[Dict[str, Any]]:
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
                safe_next_command=_orphan_visibility_sweep_command(orphan_after),
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


def _awareness_card(
    compact: Mapping[str, Any],
    *,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> Dict[str, Any]:
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
    repair_rows.extend(_session_lifecycle_repair_rows(card, orphan_after=orphan_after))
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
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
) -> List[Dict[str, Any]]:
    safe_limit = max(0, int(limit or 0))
    if safe_limit == 0:
        return []
    rows: List[Dict[str, Any]] = []
    for compact in list(effective_active_compacts) + list(orphaned_active_compacts):
        rows.append(_awareness_card(compact, orphan_after=orphan_after))
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
                proof_route=_wl_command("session-status", "--seed-speed --limit 12"),
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
        raw_td_ids = [
            str(item) for item in session.get("unclaimed_touched_td_ids") or [] if item
        ]
        path_ids = [
            str(item) for item in session.get("unclaimed_touched_path_ids") or [] if item
        ]
        path_ids.extend(
            item for item in raw_td_ids if _looks_like_repo_path_token(item)
        )
        path_ids = list(dict.fromkeys(path_ids))
        td_ids = [
            item for item in raw_td_ids if not _looks_like_repo_path_token(item)
        ]
        work_item_ids = [
            str(item) for item in session.get("unclaimed_touched_work_item_ids") or [] if item
        ]
        if path_ids:
            safe = _wl_command(
                "session-claim-path",
                f"--session-id {_quote_cli(session_id)}",
                f"--path {_quote_cli(path_ids[0])}",
                "--lease-minutes 30",
                "--require-exclusive",
            )
            proof = safe
            subject = path_ids[0]
        elif td_ids:
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
            safe = _wl_command(
                "session-claim",
                f"--session-id {_quote_cli(session_id)}",
                f"--td-id {_quote_cli(work_item_ids[0])}",
                "--conflict-scope-kind work_item_id",
                "--lease-minutes 30",
                "--require-exclusive",
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
                    "unclaimed_touched_path_ids": path_ids,
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
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
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
                    "--current-pass-line '<current pass line>'",
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
                proof_route=_wl_command("session-status", "--seed-speed --limit 12"),
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
        orphan_dry_run = _orphan_visibility_sweep_command(orphan_after)
        rows.append(
            _repair_row(
                row_id="orphaned_session_sweep",
                failure_class="orphaned_active_session",
                status="watch",
                why_blocked=(
                    "One or more active sessions are older than the orphan visibility threshold; "
                    "run the thresholded dry-run and only sweep when it names rows. "
                    "The default sweep uses a more conservative auto-sweep threshold."
                ),
                owning_surface="work_ledger.session_sweep",
                safe_next_command=orphan_dry_run,
                proof_route=_wl_command("session-status", "--overview --cards-only --limit 12"),
                residual_capture_route=_residual_capture_command("orphaned_session"),
                details={
                    "session_count": len(orphaned_active_sessions),
                    "visibility_threshold_hours": _duration_hours_token(orphan_after),
                    "auto_sweep_threshold_hours": _duration_hours_token(
                        ACTIVE_SESSION_ORPHAN_SWEEP_AFTER
                    ),
                    "dry_run_command": orphan_dry_run,
                    "mutation_rule": "mutate only after dry-run reports sweepable rows",
                },
            )
        )
    if stale_sessions:
        first_stale = next(
            (
                item
                for item in stale_sessions
                if isinstance(item, Mapping) and not item.get("ended_at")
            ),
            next((item for item in stale_sessions if isinstance(item, Mapping)), {}),
        )
        session_id = str(first_stale.get("session_id") or "<session_id>")
        stale_repair = _stale_append_repair_route(first_stale)
        rows.append(
            _repair_row(
                row_id="stale_append_or_finalize",
                failure_class="stale_append_or_finalize",
                status="watch",
                why_blocked=str(stale_repair["why_blocked"]),
                owning_surface=str(stale_repair["owning_surface"]),
                safe_next_command=str(stale_repair["safe_next_command"]),
                proof_route=_wl_command("session-status", "--overview --cards-only --limit 12"),
                residual_capture_route=_residual_capture_command("stale_append_obligation"),
                details={
                    "session_count": len(stale_sessions),
                    "sample_session_id": session_id,
                    **dict(stale_repair["details"]),
                },
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
    repo_root: Path | None = None,
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
    passive_external_observed_sessions = [
        session
        for session in active_sessions
        if not _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
        and _is_passive_external_observed_session(
            session,
            now=now,
            orphan_after=orphan_after,
        )
    ]
    effective_active_sessions = [
        session
        for session in active_sessions
        if _is_effective_active_session(session, now=now, orphan_after=orphan_after)
    ]
    stale_sessions = [session for session in sessions if bool(session.get("stale"))]
    stale_append_sessions = [
        session for session in stale_sessions if _session_requires_append_evidence(session)
    ]
    stale_claim_only_sessions = [
        session for session in stale_sessions if not _session_requires_append_evidence(session)
    ]
    active_sessions.sort(key=_session_sort_key, reverse=True)
    effective_active_sessions.sort(key=_session_sort_key, reverse=True)
    passive_external_observed_sessions.sort(key=_session_sort_key, reverse=True)
    orphaned_active_sessions.sort(key=_session_sort_key, reverse=True)
    stale_sessions.sort(key=_session_sort_key, reverse=True)
    stale_append_sessions.sort(key=_session_sort_key, reverse=True)
    stale_claim_only_sessions.sort(key=_session_sort_key, reverse=True)

    actors: Dict[str, Dict[str, Any]] = {}
    phases: Dict[str, Dict[str, Any]] = {}
    td_active_sessions: Dict[str, List[Dict[str, Any]]] = {}
    unknown_scope_active: List[Dict[str, Any]] = []
    unclaimed_touched_sessions: List[Dict[str, Any]] = []
    validated_uncommitted_closeout_sessions: List[Dict[str, Any]] = []
    active_claims_flat: List[Dict[str, Any]] = []
    effective_active_compacts: List[Dict[str, Any]] = []

    for session in sessions:
        active = not bool(session.get("ended_at"))
        orphaned_active = (
            _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
            if active
            else False
        )
        effective_active = active and _is_effective_active_session(
            session,
            now=now,
            orphan_after=orphan_after,
        )
        compact: Dict[str, Any] | None = None
        if effective_active:
            compact = _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
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
            and not _session_has_completed_nonblocking_pass(session)
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
        closeout_row = _validated_uncommitted_closeout_session_row(
            session,
            now=now,
            repo_root=repo_root,
            orphan_after=orphan_after,
        )
        if closeout_row is not None:
            validated_uncommitted_closeout_sessions.append(closeout_row)
        if not effective_active:
            continue
        if compact is None:
            continue
        if unknown_scope:
            unknown_scope_active.append(compact)
        if (
            not _session_has_completed_nonblocking_pass(session)
            and (
                compact.get("unclaimed_touched_td_ids")
                or compact.get("unclaimed_touched_path_ids")
                or compact.get("unclaimed_touched_work_item_ids")
            )
        ):
            unclaimed_touched_sessions.append(compact)
        for td_id in compact["touched_td_ids"]:
            if _looks_like_repo_path_token(td_id):
                continue
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
    validated_uncommitted_closeout_sessions.sort(
        key=lambda row: (
            str(row.get("append_exempted_at") or row.get("ended_at") or ""),
            str(row.get("session_id") or ""),
        ),
        reverse=True,
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
    historical_signals: List[str] = []
    if stale_append_sessions:
        historical_signals.append("stale_session_backlog")

    risk_level = "clear"
    if td_id_collisions or claim_collisions or len(unknown_scope_active) > 1:
        risk_level = "contention"
    elif (
        len(effective_active_sessions) > 1
        or mission_focus_groups
        or unclaimed_touched_sessions
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
            "One or more active sessions touched td/path/WorkItem work without a live claim. "
            "Use `session-claim --td-id <td>`, `session-claim-path --path <path>`, "
            "or session-preflight before mutation; release/finalize stale touches."
        )
    if td_id_collisions:
        recommended_actions.append(
            "Resolve touched-thread contention by assigning one owner or appending a progress note before continuing."
        )
    if orphaned_active_sessions:
        recommended_actions.append(
            "Run the thresholded orphan dry-run "
            f"(`{_orphan_visibility_sweep_command(orphan_after)}`) before treating old active "
            "sessions as mutable cleanup; only run a mutating sweep when that dry-run names rows."
        )
    if stale_append_sessions:
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
    counts["passive_external_observed_sessions"] = len(passive_external_observed_sessions)
    counts["orphaned_active_sessions"] = len(orphaned_active_sessions)
    counts["active_claims"] = len(active_claims_flat)
    counts["claim_collisions"] = len(claim_collisions)
    counts["unclaimed_touched_sessions"] = len(unclaimed_touched_sessions)
    counts["mission_focus_pressure_groups"] = len(mission_focus_groups)
    counts["stale_append_obligations"] = len(stale_append_sessions)
    counts["stale_claim_only_sessions"] = len(stale_claim_only_sessions)
    counts["validated_uncommitted_closeout_sessions"] = len(
        validated_uncommitted_closeout_sessions
    )
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
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in orphaned_active_sessions
        ],
        limit=safe_limit,
        orphan_after=orphan_after,
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
        stale_sessions=stale_append_sessions,
        heartbeat_participation=heartbeat_participation,
        limit=safe_limit,
        orphan_after=orphan_after,
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
        orphan_after=orphan_after,
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
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in active_sessions[:safe_limit]
        ],
        "effective_active_sessions": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in effective_active_sessions[:safe_limit]
        ],
        "passive_external_observed_sessions": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in passive_external_observed_sessions[:safe_limit]
        ],
        "orphaned_active_sessions": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in orphaned_active_sessions[:safe_limit]
        ],
        "stale_sessions": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in stale_sessions[:safe_limit]
        ],
        "stale_append_obligations": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in stale_append_sessions[:safe_limit]
        ],
        "stale_claim_only_sessions": [
            _compact_session(
                session,
                repo_root=repo_root,
                now=now,
                orphan_after=orphan_after,
            )
            for session in stale_claim_only_sessions[:safe_limit]
        ],
        "actors": actors,
        "phases": phases,
        "contention": {
            "risk_level": risk_level,
            "signals": signals,
            "historical_signals": historical_signals,
            "historical_signal_policy": "stale ended-session append obligations stay as repair cards, not live coordination risk",
            "td_id_collisions": td_id_collisions[:safe_limit],
            "mission_focus_pressure_groups": mission_focus_groups[:safe_limit],
            "unknown_scope_active_sessions": unknown_scope_active[:safe_limit],
            "unclaimed_touched_sessions": unclaimed_touched_sessions[:safe_limit],
            "orphaned_active_sessions": [
                _compact_session(
                    session,
                    repo_root=repo_root,
                    now=now,
                    orphan_after=orphan_after,
                )
                for session in orphaned_active_sessions[:safe_limit]
            ],
            "claim_collisions": claim_collisions[:safe_limit],
        },
        "validated_uncommitted_closeout_sessions": (
            validated_uncommitted_closeout_sessions[:safe_limit]
        ),
        "validated_uncommitted_closeout_sessions_omitted": max(
            0, len(validated_uncommitted_closeout_sessions) - safe_limit
        ),
        "active_claims": active_claims_flat[:safe_limit],
        "recent_sweep_events": recent_sweep_events,
        "recommended_actions": recommended_actions,
    }


def _seed_speed_scope_ref(card: Mapping[str, Any]) -> str:
    for key in ("paths_preview", "work_item_ids_preview", "td_ids_preview"):
        rows = card.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            text = str(row or "").strip()
            if text:
                return text
    return "<path-or-claim>"


CAS_RETRY_HANDOFF_TERMS: tuple[str, ...] = (
    "cas retry budget",
    "retry budget exhausted",
    "head-cas retry",
    "parent-cas retry",
    "private-index cas",
    "head advanced",
    "scoped_commit stopped",
)


def _seed_speed_cas_retry_handoff_row(card: Mapping[str, Any]) -> Dict[str, Any] | None:
    current_line = str(card.get("current_pass_line") or "").strip()
    last_result = str(card.get("last_pass_result_line") or "").strip()
    append_exempt_reason = str(card.get("append_exempt_reason") or "").strip()
    append_exempt_refs = [
        str(item).strip()
        for item in list(card.get("append_exempt_refs") or [])
        if str(item).strip()
    ]
    haystack = "\n".join(
        [
            current_line,
            last_result,
            append_exempt_reason,
            *append_exempt_refs,
        ]
    ).lower()
    matched_terms = [term for term in CAS_RETRY_HANDOFF_TERMS if term in haystack]
    if append_exempt_reason == "validated_uncommitted_git_metadata_blocked":
        matched_terms.append(append_exempt_reason)
    if not matched_terms:
        return None
    session_id = str(card.get("session_id") or "").strip()
    scope_ref = _seed_speed_scope_ref(card)
    read_only_drilldown = _wl_command(
        "session-status",
        f"--session-id {_quote_cli(session_id)} --full",
    )
    return {
        "schema": "work_ledger_seed_speed_cas_retry_handoff_row_v0",
        "session_id": session_id,
        "actor": card.get("actor"),
        "phase_id": card.get("phase_id"),
        "pass_state": card.get("pass_state"),
        "freshness_state": card.get("freshness_state"),
        "active_claim_count": card.get("active_claim_count"),
        "append_exempt_reason": append_exempt_reason or None,
        "append_exempt_refs": append_exempt_refs[:3],
        "append_exempt_refs_omitted": max(0, len(append_exempt_refs) - 3),
        "handoff_origin": card.get("handoff_origin") or "active_claim_session",
        "scope_ref": scope_ref,
        "current_pass_line": current_line,
        "matched_terms": matched_terms,
        "classification": "parent_cas_retry_budget_exhausted_landing_handoff",
        "safe_next_action": "inspect_handoff_then_reenter_from_fresh_landing_evidence_root",
        "blocked_action": "third_ref_mutation_from_the_same_scoped_commit_evidence_root",
        "read_only_drilldown": read_only_drilldown,
        "reentry_contract": {
            "schema": "cas_retry_landing_reentry_contract_v0",
            "required_checks": [
                "refresh HEAD",
                "inspect intervening commits for owned-path overlap",
                "rerun or explicitly refresh validation assumptions",
                "run mission_transaction_preflight for the exact owned paths",
                "attempt a new scoped commit from a fresh evidence root",
            ],
            "forbidden_actions": [
                "unbounded scoped_commit retries",
                "third ref mutation after the same refreshed CAS retry loses",
                "broad staging of unrelated dirty paths",
            ],
        },
    }


def _validated_uncommitted_closeout_session_row(
    session: Mapping[str, Any],
    *,
    now: datetime,
    repo_root: Path | None,
    orphan_after: timedelta,
) -> Dict[str, Any] | None:
    if not session.get("ended_at"):
        return None
    if not bool(session.get("append_exempt")):
        return None
    append_exempt_reason = str(session.get("append_exempt_reason") or "").strip()
    append_exempt_refs = [
        str(item).strip()
        for item in list(session.get("append_exempt_refs") or [])
        if str(item).strip()
    ]
    if (
        append_exempt_reason != "validated_uncommitted_git_metadata_blocked"
        and not any("scoped-commit-head-cas-retry-packet:" in ref for ref in append_exempt_refs)
    ):
        return None

    compact = _compact_session(
        session,
        repo_root=repo_root,
        now=now,
        orphan_after=orphan_after,
    )
    heartbeat = (
        dict(compact.get("pass_heartbeat") or {})
        if isinstance(compact.get("pass_heartbeat"), Mapping)
        else {}
    )
    released_paths: List[str] = []
    for claim in list(session.get("claims") or []):
        if not isinstance(claim, Mapping):
            continue
        scope_kind, scope_id = _normalize_claim_scope(claim)
        path = str(claim.get("path") or "").strip()
        if not path and scope_kind == CLAIM_SCOPE_PATH:
            path = scope_id
        if path and path not in released_paths:
            released_paths.append(path)
    for ref in list(heartbeat.get("scope_refs_preview") or []):
        if not isinstance(ref, Mapping):
            continue
        text = str(ref.get("ref") or "").strip()
        if text and _looks_like_repo_path_token(text) and text not in released_paths:
            released_paths.append(text)

    session_id = str(compact.get("session_id") or "").strip()
    return {
        "schema": "work_ledger_validated_uncommitted_closeout_session_v0",
        "session_id": session_id,
        "actor": compact.get("actor"),
        "phase_id": compact.get("phase_id"),
        "family_id": compact.get("family_id"),
        "freshness_state": "ended_append_exempt",
        "pass_state": heartbeat.get("pass_state") or "closed",
        "active_claim_count": 0,
        "path_claim_count": 0,
        "paths_preview": released_paths[:3],
        "path_count": len(released_paths),
        "paths_omitted": max(0, len(released_paths) - 3),
        "current_pass_line": heartbeat.get("current_pass_line"),
        "last_pass_result_line": heartbeat.get("last_pass_result_line"),
        "ended_at": compact.get("ended_at"),
        "end_action": compact.get("end_action"),
        "read_receipt_id": compact.get("read_receipt_id"),
        "append_exempt_reason": append_exempt_reason,
        "append_exempted_at": compact.get("append_exempted_at"),
        "append_exempt_refs": append_exempt_refs[:3],
        "append_exempt_refs_omitted": max(0, len(append_exempt_refs) - 3),
        "handoff_origin": "ended_append_exempt_validated_uncommitted_closeout",
        "read_only_drilldown": _wl_command(
            "session-status",
            f"--session-id {_quote_cli(session_id)} --full",
        ),
        "reentry_condition": [
            "verify the released paths are still dirty and wanted",
            "refresh HEAD and inspect intervening commits for owned-path overlap",
            "rerun mission_transaction_preflight for the exact path set",
            "refresh focused validation after latest HEAD movement",
            "start a new scoped_commit attempt from a fresh evidence root",
        ],
    }


def _seed_speed_cas_retry_handoff_lens(
    rows: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    typed_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
    first = typed_rows[0] if typed_rows else {}
    first_command = str(first.get("read_only_drilldown") or "").strip() or None
    return {
        "schema": CAS_RETRY_HANDOFF_LENS_SCHEMA,
        "surface_role": "seed_speed_cas_retry_handoff_lens",
        "authority_boundary": (
            "Heartbeat and Work Ledger prose classify a landing handoff candidate; "
            "Git HEAD, owned paths, validation, Task Ledger receipts, and "
            "scoped_commit remain the authority before mutation."
        ),
        "status": "present" if typed_rows else "clear",
        "handoff_count": len(typed_rows),
        "first_safe_command": first_command,
        "rows": typed_rows[:safe_limit],
        "rows_omitted": max(0, len(typed_rows) - safe_limit),
        "policy": (
            "Parent-CAS retry exhaustion is a serialized reentry problem, not a "
            "reason to keep mutating refs. Reenter through the handoff row with "
            "fresh HEAD, overlap, validation, preflight, and a new evidence root."
        ),
    }


def _seed_speed_heartbeat_gap_row(card: Mapping[str, Any]) -> Dict[str, Any]:
    session_id = str(card.get("session_id") or "").strip()
    scope_ref = _seed_speed_scope_ref(card)
    read_only_alternative_command = _wl_command(
        "session-status",
        f"--session-id {_quote_cli(session_id)} --full",
    )
    return {
        "session_id": session_id,
        "actor": card.get("actor"),
        "phase_id": card.get("phase_id"),
        "active_claim_count": card.get("active_claim_count"),
        "heartbeat_source": card.get("heartbeat_source"),
        "freshness_state": card.get("freshness_state"),
        "scope_ref": scope_ref,
        "heartbeat_command": _wl_command(
            "session-heartbeat",
            f"--session-id {_quote_cli(session_id)}",
            "--state inspecting",
            "--current-pass-line '<public current pass>'",
            "--last-pass-result-line '<public previous result>'",
            f"--scope-ref {_quote_cli(scope_ref)}",
        ),
        "read_only_alternative_command": read_only_alternative_command,
    }


def _seed_speed_unclaimed_touched_row(
    session: Mapping[str, Any],
    *,
    awareness_by_session: Mapping[str, Mapping[str, Any]],
) -> Dict[str, Any]:
    session_id = str(session.get("session_id") or "").strip()
    raw_td_ids = [
        str(item)
        for item in session.get("unclaimed_touched_td_ids") or []
        if item
    ]
    path_ids = [
        str(item)
        for item in session.get("unclaimed_touched_path_ids") or []
        if item
    ]
    path_ids.extend(
        item for item in raw_td_ids if _looks_like_repo_path_token(item)
    )
    path_ids = list(dict.fromkeys(path_ids))
    td_ids = [
        item for item in raw_td_ids if not _looks_like_repo_path_token(item)
    ]
    work_item_ids = [
        str(item) for item in session.get("unclaimed_touched_work_item_ids") or [] if item
    ]
    awareness = awareness_by_session.get(session_id) or {}
    heartbeat = (
        session.get("pass_heartbeat")
        if isinstance(session.get("pass_heartbeat"), Mapping)
        else {}
    )
    read_only_drilldown = _wl_command(
        "session-status",
        f"--session-id {_quote_cli(session_id)} --full",
    )
    owner_claim_command = None
    if path_ids:
        owner_claim_command = _wl_command(
            "session-claim-path",
            f"--session-id {_quote_cli(session_id)}",
            f"--path {_quote_cli(path_ids[0])}",
            "--lease-minutes 30",
            "--require-exclusive",
        )
    elif td_ids:
        owner_claim_command = _wl_command(
            "session-claim",
            f"--session-id {_quote_cli(session_id)}",
            f"--td-id {_quote_cli(td_ids[0])}",
            "--lease-minutes 30",
            "--require-exclusive",
        )
    elif work_item_ids:
        owner_claim_command = _wl_command(
            "session-claim",
            f"--session-id {_quote_cli(session_id)}",
            f"--td-id {_quote_cli(work_item_ids[0])}",
            "--conflict-scope-kind work_item_id",
            "--lease-minutes 30",
            "--require-exclusive",
        )
    coordination_pointer = {
        "schema": "unclaimed_touched_session_coordination_packet_pointer_v1",
        "output_profile": "compact_pointer",
        "session_id": session_id,
        "coordination_state": "unclaimed_touched_work",
        "authority_boundary": "owner_or_explicit_coordinator_only",
        "drilldown": read_only_drilldown,
        "owner_repair_ref": "parent.owner_claim_command",
        "omission_ref": "seed_speed.omission_receipt",
    }
    return {
        "session_id": session_id,
        "actor": session.get("actor"),
        "phase_id": session.get("phase_id"),
        "freshness_state": awareness.get("freshness_state")
        or heartbeat.get("freshness_state"),
        "pass_state": awareness.get("pass_state") or heartbeat.get("pass_state"),
        "current_pass_line": awareness.get("current_pass_line")
        or heartbeat.get("current_pass_line"),
        "heartbeat_source": awareness.get("source") or heartbeat.get("source"),
        **(
            {
                "unclaimed_touched_path_ids": path_ids[:3],
                "unclaimed_touched_path_ids_omitted": max(0, len(path_ids) - 3),
            }
            if path_ids
            else {}
        ),
        "unclaimed_touched_td_ids": td_ids[:3],
        "unclaimed_touched_td_ids_omitted": max(0, len(td_ids) - 3),
        "unclaimed_touched_work_item_ids": work_item_ids[:3],
        "unclaimed_touched_work_item_ids_omitted": max(0, len(work_item_ids) - 3),
        "read_only_drilldown": read_only_drilldown,
        "read_only_alternative_command": read_only_drilldown,
        "owner_claim_command": owner_claim_command,
        "session_coordination_packet": coordination_pointer,
        "policy": (
            "Inspect the session first; only that owner or an explicit coordinator "
            "should claim the touched work before mutation."
        ),
    }


def _seed_speed_no_heartbeat_gap_summary(
    heartbeat_gap_claim_sessions: Sequence[Mapping[str, Any]],
    *,
    limit: int,
) -> Dict[str, Any]:
    rows = [row for row in heartbeat_gap_claim_sessions if isinstance(row, Mapping)]
    if not rows:
        return {
            "schema": "work_ledger_seed_speed_no_heartbeat_gap_summary_v0",
            "status": "clear",
            "heartbeat_gap_count": 0,
            "write_actions_suppressed": True,
            "first_gap_session_id": None,
            "first_read_only_alternative_command": None,
            "gap_sessions_preview": [],
            "gap_sessions_omitted": 0,
            "policy": (
                "No-heartbeat mode reports heartbeat gaps as coordination debt; "
                "it does not publish heartbeat writes."
            ),
        }

    preview = [
        {
            "session_id": row.get("session_id"),
            "scope_ref": row.get("scope_ref"),
            "read_only_alternative_command": row.get(
                "read_only_alternative_command"
            ),
        }
        for row in rows[:limit]
    ]
    first = rows[0]
    return {
        "schema": "work_ledger_seed_speed_no_heartbeat_gap_summary_v0",
        "status": "heartbeat_gaps_deferred",
        "heartbeat_gap_count": len(rows),
        "write_actions_suppressed": True,
        "first_gap_session_id": first.get("session_id"),
        "first_read_only_alternative_command": first.get(
            "read_only_alternative_command"
        ),
        "gap_sessions_preview": preview,
        "gap_sessions_omitted": max(0, len(rows) - len(preview)),
        "policy": (
            "No-heartbeat mode reports heartbeat gaps as coordination debt; inspect "
            "the gap session read-only or choose a disjoint lane instead of "
            "publishing heartbeat from this packet."
        ),
    }


def _seed_speed_claim_collision_failure_class(collision: Mapping[str, Any]) -> str:
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


def _seed_speed_claim_collision_command(
    collision: Mapping[str, Any],
    *,
    failure_class: str,
) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = sorted({str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")})
    claim_ids = [str(claim.get("claim_id") or "") for claim in claims if claim.get("claim_id")]
    path = str(collision.get("path") or "").strip()
    work_item_id = str(collision.get("work_item_id") or "").strip()
    td_id = str(collision.get("td_id") or "").strip()
    scope_kind = str(collision.get("scope_kind") or "").strip()
    if failure_class == "duplicate_same_session_claim" and sessions and claim_ids:
        return _wl_command(
            "session-release-claim",
            f"--session-id {_quote_cli(sessions[0])}",
            f"--claim-id {_quote_cli(claim_ids[-1])}",
            "--reason duplicate_same_session_claim",
        )
    if path:
        return _wl_command("mutation-check", f"--path {_quote_cli(path)} --require-exclusive")
    if work_item_id:
        return _mission_command(f"--subject-id {_quote_cli(work_item_id)} --control-summary")
    if td_id:
        return _mission_command(f"--subject-id {_quote_cli(td_id)} --control-summary")
    return _wl_command(
        "session-claims",
        f"--refresh --limit 12 --full # scope_kind={_quote_cli(scope_kind)}",
    )


def _seed_speed_claim_collision_action_row(collision: Mapping[str, Any]) -> Dict[str, Any]:
    failure_class = _seed_speed_claim_collision_failure_class(collision)
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    row = {
        "failure_class": failure_class,
        "scope_kind": collision.get("scope_kind"),
        "scope_id": collision.get("scope_id"),
        "td_id": collision.get("td_id"),
        "path": collision.get("path"),
        "work_item_id": collision.get("work_item_id"),
        "claim_count": collision.get("claim_count"),
        "actors": list(collision.get("actors") or []),
        "session_ids": sorted(
            {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
        ),
        "active_claims_preview": [
            {
                "claim_id": claim.get("claim_id"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "phase_id": claim.get("phase_id"),
                "scope_kind": claim.get("scope_kind"),
                "path": claim.get("path"),
                "work_item_id": claim.get("work_item_id"),
                "td_id": claim.get("td_id"),
                "leased_until": claim.get("leased_until"),
            }
            for claim in claims[:3]
        ],
        "safe_next_command": _seed_speed_claim_collision_command(
            collision,
            failure_class=failure_class,
        ),
    }
    if failure_class == "duplicate_same_session_claim":
        row["auto_release_supported"] = True
        row["auto_release_policy"] = (
            "same-session duplicate only; keeps newest lease and releases older "
            "duplicate claims"
        )
        row["auto_release_command"] = _wl_command(
            "session-sweep",
            "--dedupe-duplicate-claims",
        )
        row["auto_release_dry_run_command"] = _wl_command(
            "session-sweep",
            "--dry-run --dedupe-duplicate-claims",
        )
    return row


def _seed_speed_claim_collision_cleanup_summary(
    claim_collision_actions: Sequence[Mapping[str, Any]],
) -> Dict[str, Any] | None:
    actions = [row for row in claim_collision_actions if isinstance(row, Mapping)]
    if not actions:
        return None

    failure_class_counts: Dict[str, int] = {}
    auto_supported_count = 0
    first_manual_command = None
    first_auto_dry_run_command = None
    first_auto_release_command = None
    auto_release_policy = None

    for row in actions:
        failure_class = str(row.get("failure_class") or "claim_collision")
        failure_class_counts[failure_class] = failure_class_counts.get(failure_class, 0) + 1
        if bool(row.get("auto_release_supported")):
            auto_supported_count += 1
            if first_auto_dry_run_command is None:
                first_auto_dry_run_command = (
                    str(row.get("auto_release_dry_run_command") or "").strip()
                    or None
                )
            if first_auto_release_command is None:
                first_auto_release_command = (
                    str(row.get("auto_release_command") or "").strip()
                    or None
                )
            if auto_release_policy is None:
                auto_release_policy = str(row.get("auto_release_policy") or "").strip() or None
        elif first_manual_command is None:
            first_manual_command = str(row.get("safe_next_command") or "").strip() or None

    collision_count = len(actions)
    manual_required_count = collision_count - auto_supported_count
    if auto_supported_count == collision_count:
        status = "auto_release_available"
        first_safe_command = first_auto_dry_run_command or first_auto_release_command
        recommended_action = (
            "Run duplicate-claim dedupe dry-run, then the dedupe command if the "
            "preview only releases older same-session duplicate claims."
        )
    elif auto_supported_count:
        status = "mixed_auto_and_manual"
        first_safe_command = first_manual_command or first_auto_dry_run_command
        recommended_action = (
            "Resolve manual claim collisions first; same-session duplicates can "
            "use the duplicate-claim dedupe lane after manual blockers clear."
        )
    else:
        status = "manual_resolution_required"
        first_safe_command = first_manual_command
        recommended_action = (
            "Inspect and release or re-scope the first colliding owner claim before "
            "starting or widening seed work."
        )

    return {
        "schema": "work_ledger_seed_speed_claim_collision_cleanup_summary_v0",
        "status": status,
        "collision_count": collision_count,
        "auto_release_supported_count": auto_supported_count,
        "manual_resolution_required_count": manual_required_count,
        "failure_class_counts": failure_class_counts,
        "safe_to_auto_release_all": manual_required_count == 0,
        "first_safe_command": first_safe_command,
        "first_mutation_command": (
            first_auto_release_command
            if manual_required_count == 0
            else first_manual_command
        ),
        "auto_release_dry_run_command": first_auto_dry_run_command,
        "auto_release_command": first_auto_release_command,
        "auto_release_policy": auto_release_policy,
        "recommended_action": recommended_action,
        "checkpoint_policy": (
            "Claim collisions block broad checkpointing. Same-session duplicate "
            "claims may use the dedupe lane; cross-session or mixed-scope "
            "collisions still require owner-scoped resolution."
        ),
    }


def _seed_speed_choose_disjoint_lane_action(
    seed_claim_sessions: Sequence[Mapping[str, Any]],
    *,
    prefer_explicit_current: bool,
) -> Dict[str, Any]:
    candidates = list(seed_claim_sessions)
    if prefer_explicit_current:
        explicit_candidates = [
            card
            for card in candidates
            if str(card.get("heartbeat_source") or "") in EXPLICIT_HEARTBEAT_SOURCES
        ]
        if explicit_candidates:
            candidates = explicit_candidates
    if candidates:
        command = _wl_command(
            "session-claims",
            "--refresh --session-summary --limit 12 --cards-only",
        )
        return {
            "kind": "choose_disjoint_write_lane",
            "action": "Use the seed claim session cards to choose the disjoint write lane.",
            "command": command,
            "ref": "fast_paths.claim_session_summary",
        }
    return {
        "kind": "dirty_tree_pressure",
        "action": "Use dirty-tree pressure to pick a claimable path or settlement lane.",
        "command": _wl_command("session-sweep", "--dry-run --dirty-tree-pressure"),
        "ref": "fast_paths.dirty_tree_pressure",
    }


def _seed_speed_no_active_claims_action() -> Dict[str, Any]:
    return {
        "kind": "no_active_claims",
        "action": (
            "No active Work Ledger claims; run task entry for the intended task, "
            "then claim owned paths before editing."
        ),
        "command": './repo-python kernel.py --entry "<task>" --context-budget 12000',
        "ref": "entry.control_replacement.task_ledger",
    }


def _seed_speed_session_coordination_packet(
    card: Mapping[str, Any],
    *,
    heartbeat_gap: bool,
) -> Dict[str, Any]:
    session_id = str(card.get("session_id") or "").strip()
    scope_ref = _seed_speed_scope_ref(card)
    query_command = _wl_command(
        "session-status",
        f"--session-id {_quote_cli(session_id)} --full",
    )
    pointer = {
        "schema": "session_coordination_packet_pointer_v1",
        "output_profile": "compact_pointer",
        "session_id": session_id,
        "coordination_state": "heartbeat_gap" if heartbeat_gap else "queryable",
        "drilldown": query_command,
        "omission_ref": "seed_speed.omission_receipt",
    }
    if heartbeat_gap:
        pointer["primary_signal_commands"] = {
            "publish_heartbeat": _wl_command(
                "session-heartbeat",
                f"--session-id {_quote_cli(session_id)}",
                "--state inspecting",
                "--current-pass-line '<public current pass>'",
                "--last-pass-result-line '<public previous result>'",
                f"--scope-ref {_quote_cli(scope_ref)}",
            ),
        }
    return pointer


def _seed_speed_dirty_pressure_focus(
    dirty_tree_pressure: Mapping[str, Any] | None,
    *,
    session_coordination: Mapping[str, Mapping[str, Any]] | None = None,
    heartbeat_gap_session_ids: Iterable[str] | None = None,
    observed_at: str | None = None,
) -> Dict[str, Any] | None:
    if not isinstance(dirty_tree_pressure, Mapping):
        return None

    def _parse_iso_datetime(value: Any) -> datetime | None:
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

    observed_at_text = str(observed_at or "").strip() or None
    observed_at_dt = _parse_iso_datetime(observed_at_text)

    coordination_by_session = {
        str(session_id): card
        for session_id, card in dict(session_coordination or {}).items()
        if str(session_id).strip() and isinstance(card, Mapping)
    }
    heartbeat_gap_ids = {
        str(session_id).strip()
        for session_id in list(heartbeat_gap_session_ids or [])
        if str(session_id).strip()
    }

    checkpoint = dirty_tree_pressure.get("operator_authorized_mainline_checkpoint")
    checkpoint = checkpoint if isinstance(checkpoint, Mapping) else {}
    unclaimed_checkpoint = dirty_tree_pressure.get(
        "operator_authorized_unclaimed_checkpoint"
    )
    unclaimed_checkpoint = (
        unclaimed_checkpoint if isinstance(unclaimed_checkpoint, Mapping) else {}
    )
    group_packet = checkpoint.get("blocking_active_claim_session_groups")
    group_packet = group_packet if isinstance(group_packet, Mapping) else {}
    groups = [
        group
        for group in list(group_packet.get("groups") or [])
        if isinstance(group, Mapping)
    ]
    first_group = groups[0] if groups else {}
    active_claim_dirty_path_count = int(
        checkpoint.get("active_claim_dirty_path_count") or 0
    )
    claim_collision_count = int(checkpoint.get("claim_collision_count") or 0)
    checkpoint_status = str(checkpoint.get("status") or "").strip() or "unknown"
    unclaimed_checkpoint_status = (
        str(unclaimed_checkpoint.get("status") or "").strip() or "unknown"
    )
    first_action_kind = None
    first_action = None
    first_action_command = None
    first_action_ref = None
    status = "dirty_pressure_observed"
    promote_for_no_heartbeat = False

    if checkpoint_status == "available":
        first_action_kind = "operator_authorized_broad_checkpoint"
        first_action = "Run the operator-authorized broad checkpoint after a final pressure recheck."
        first_action_command = str(checkpoint.get("command") or "").strip() or None
        first_action_ref = (
            "dirty_tree_pressure.operator_authorized_mainline_checkpoint.command"
        )
        status = "checkpoint_available"
    elif unclaimed_checkpoint_status == "available":
        first_action_kind = "operator_authorized_unclaimed_checkpoint"
        first_action = (
            "Run the operator-authorized unclaimed-path checkpoint after a final "
            "pressure recheck; active claimed paths remain excluded."
        )
        first_action_command = (
            str(unclaimed_checkpoint.get("command") or "").strip() or None
        )
        first_action_ref = (
            "dirty_tree_pressure.operator_authorized_unclaimed_checkpoint.command"
        )
        status = "unclaimed_checkpoint_available"
        promote_for_no_heartbeat = bool(first_action_command)
    elif claim_collision_count:
        collision_cleanup = checkpoint.get("blocking_claim_collision_cleanup")
        collision_cleanup = (
            collision_cleanup if isinstance(collision_cleanup, Mapping) else {}
        )
        first_action_kind = "claim_collision"
        first_action = "Resolve claim collisions before using dirty-tree checkpoint lanes."
        first_action_command = (
            str(
                checkpoint.get("first_claim_collision_cleanup_command")
                or collision_cleanup.get("auto_release_dry_run_command")
                or collision_cleanup.get("first_action_command")
                or ""
            ).strip()
            or None
        )
        first_action_ref = (
            "dirty_tree_pressure.operator_authorized_mainline_checkpoint."
            "first_claim_collision_cleanup_command"
        )
        status = "checkpoint_blocked_by_claim_collisions"
    elif active_claim_dirty_path_count and first_group:
        first_action_kind = "settle_checkpoint_blocking_claim_session"
        first_action = (
            "Open the session whose claimed dirty paths block the dirty-tree checkpoint; "
            "that owner must land or release claims before broad checkpointing."
        )
        first_action_command = (
            str(
                first_group.get("safe_next_command")
                or first_group.get("session_status_command")
                or checkpoint.get("first_blocking_claim_command")
                or ""
            ).strip()
            or None
        )
        first_action_ref = (
            "dirty_tree_pressure.operator_authorized_mainline_checkpoint."
            "blocking_active_claim_session_groups.groups[0].safe_next_command"
        )
        status = "checkpoint_blocked_by_active_claims"

    def _bounded_owner_surfaces(
        row: Mapping[str, Any],
        *,
        source_key: str = "owner_surfaces_preview",
        omitted_key: str | None = None,
    ) -> tuple[list[Any], int]:
        owner_surfaces = list(row.get(source_key) or [])
        preview = owner_surfaces[:4]
        if omitted_key is None:
            omitted_key = source_key.replace("_preview", "_omitted")
        upstream_omitted = int(row.get(omitted_key) or 0)
        return (
            preview,
            upstream_omitted + max(0, len(owner_surfaces) - len(preview)),
        )

    def _blocking_session_row(group: Mapping[str, Any]) -> Dict[str, Any]:
        session_id = str(group.get("session_id") or "").strip()
        coordination = coordination_by_session.get(session_id) or {}
        lease_info = _blocking_session_lease_info(group)
        row = {
            "session_id": group.get("session_id"),
            "dirty_path_count": group.get("dirty_path_count"),
            "leased_until_max": group.get("leased_until_max"),
            "lease_state": lease_info["lease_state"],
            "lease_seconds_remaining": lease_info["lease_seconds_remaining"],
            "lease_expired": lease_info["lease_expired"],
            "paths_preview": list(group.get("paths_preview") or [])[:3],
            "paths_omitted": group.get("paths_omitted"),
            "session_status_command": group.get("session_status_command"),
            "safe_next_command": group.get("safe_next_command")
            or group.get("session_status_command"),
        }
        for source_key, target_key in (
            ("freshness_state", "freshness_state"),
            ("pass_state", "pass_state"),
            ("current_pass_line", "current_pass_line"),
            ("heartbeat_source", "heartbeat_source"),
        ):
            value = coordination.get(source_key)
            if value in (None, "", {}, []):
                value = group.get(source_key)
            if value not in (None, "", {}, []):
                row[target_key] = value
        if session_id in heartbeat_gap_ids:
            row["heartbeat_gap"] = True
        elif coordination:
            row["heartbeat_gap"] = False
        for source_key, target_key in (
            ("actor", "actor"),
            ("phase_id", "phase_id"),
            ("recommended_action", "recommended_action"),
            (
                "underlying_dirty_path_class_counts",
                "underlying_dirty_path_class_counts",
            ),
            ("first_underlying_path", "first_underlying_path"),
            ("first_underlying_owner_surface", "first_underlying_owner_surface"),
            (
                "first_underlying_recommended_action",
                "first_underlying_recommended_action",
            ),
        ):
            value = group.get(source_key)
            if value not in (None, "", {}, []):
                row[target_key] = value
        owner_surfaces, owner_surfaces_omitted = _bounded_owner_surfaces(
            group, source_key="underlying_owner_surfaces_preview"
        )
        if owner_surfaces or owner_surfaces_omitted:
            row["underlying_owner_surfaces_preview"] = owner_surfaces
            row["underlying_owner_surfaces_omitted"] = owner_surfaces_omitted
        return row

    def _blocking_session_lease_info(group: Mapping[str, Any]) -> Dict[str, Any]:
        leased_until = _parse_iso_datetime(group.get("leased_until_max"))
        if observed_at_dt is None or leased_until is None:
            return {
                "lease_state": "unknown",
                "lease_seconds_remaining": None,
                "lease_expired": None,
            }
        seconds_remaining = int((leased_until - observed_at_dt).total_seconds())
        return {
            "lease_state": "expired" if seconds_remaining < 0 else "active",
            "lease_seconds_remaining": seconds_remaining,
            "lease_expired": seconds_remaining < 0,
        }

    def _blocking_session_coordination_summary() -> Dict[str, Any] | None:
        if not groups:
            return None

        heartbeat_gap_group_count = 0
        live_group_count = 0
        unknown_group_count = 0
        first_heartbeat_gap_session_id = None
        first_heartbeat_gap_read_only_command = None
        first_live_session_id = None
        first_live_session_read_only_command = None
        first_unknown_session_id = None
        first_unknown_session_read_only_command = None
        heartbeat_source_counts: Dict[str, int] = {}

        for group in groups:
            session_id = str(group.get("session_id") or "").strip()
            coordination = coordination_by_session.get(session_id) or {}
            read_only_command = (
                str(
                    group.get("safe_next_command")
                    or group.get("session_status_command")
                    or ""
                ).strip()
                or None
            )
            source = str(coordination.get("heartbeat_source") or "missing").strip()
            heartbeat_source_counts[source] = heartbeat_source_counts.get(source, 0) + 1
            if session_id in heartbeat_gap_ids:
                heartbeat_gap_group_count += 1
                if first_heartbeat_gap_session_id is None:
                    first_heartbeat_gap_session_id = session_id
                    first_heartbeat_gap_read_only_command = read_only_command
            freshness_state = str(coordination.get("freshness_state") or "").strip()
            if freshness_state == "live":
                live_group_count += 1
                if first_live_session_id is None:
                    first_live_session_id = session_id
                    first_live_session_read_only_command = read_only_command
            if not coordination or freshness_state in {"", "unknown"}:
                unknown_group_count += 1
                if first_unknown_session_id is None:
                    first_unknown_session_id = session_id
                    first_unknown_session_read_only_command = read_only_command

        return {
            "schema": "dirty_tree_blocking_session_coordination_summary_v0",
            "session_group_count": len(groups),
            "heartbeat_gap_group_count": heartbeat_gap_group_count,
            "live_group_count": live_group_count,
            "unknown_group_count": unknown_group_count,
            "heartbeat_source_counts": heartbeat_source_counts,
            "first_heartbeat_gap_session_id": first_heartbeat_gap_session_id,
            "first_heartbeat_gap_read_only_command": (
                first_heartbeat_gap_read_only_command
            ),
            "first_live_session_id": first_live_session_id,
            "first_live_session_read_only_command": first_live_session_read_only_command,
            "first_unknown_session_id": first_unknown_session_id,
            "first_unknown_session_read_only_command": (
                first_unknown_session_read_only_command
            ),
            "no_heartbeat_policy": (
                "No-heartbeat mode defers heartbeat writes; inspect the blocking "
                "session or wait for the owner to land or release claims before "
                "broad checkpointing."
            ),
        }

    def _blocking_session_lease_summary() -> Dict[str, Any] | None:
        if not groups:
            return None

        active_lease_group_count = 0
        expired_lease_group_count = 0
        unknown_lease_group_count = 0
        first_expired_session_id = None
        earliest_active_session_id = None
        earliest_active_lease_until = None
        earliest_active_lease_dt: datetime | None = None

        for group in groups:
            session_id = str(group.get("session_id") or "").strip() or None
            lease_info = _blocking_session_lease_info(group)
            lease_state = lease_info["lease_state"]
            if lease_state == "active":
                active_lease_group_count += 1
                leased_until = str(group.get("leased_until_max") or "").strip() or None
                leased_until_dt = _parse_iso_datetime(leased_until)
                if (
                    leased_until is not None
                    and leased_until_dt is not None
                    and (
                        earliest_active_lease_dt is None
                        or leased_until_dt < earliest_active_lease_dt
                    )
                ):
                    earliest_active_lease_until = leased_until
                    earliest_active_lease_dt = leased_until_dt
                    earliest_active_session_id = session_id
            elif lease_state == "expired":
                expired_lease_group_count += 1
                if first_expired_session_id is None:
                    first_expired_session_id = session_id
            else:
                unknown_lease_group_count += 1

        return {
            "schema": "dirty_tree_blocking_session_lease_summary_v0",
            "session_group_count": len(groups),
            "active_lease_group_count": active_lease_group_count,
            "expired_lease_group_count": expired_lease_group_count,
            "unknown_lease_group_count": unknown_lease_group_count,
            "first_expired_session_id": first_expired_session_id,
            "earliest_active_session_id": earliest_active_session_id,
            "earliest_active_lease_until": earliest_active_lease_until,
            "observed_at": observed_at_text,
            "checkpoint_policy": (
                "Lease expiry is advisory; active claims remain broad-checkpoint "
                "blockers until the owner session lands, releases, finalizes, "
                "or an owner sweep removes expired claims."
            ),
        }

    def _owner_surfaces_preview(row: Mapping[str, Any]) -> tuple[list[Any], int]:
        return _bounded_owner_surfaces(row)

    def _active_claim_underlying_summary() -> Dict[str, Any] | None:
        if not groups:
            return None

        class_counts: Dict[str, int] = {}
        owner_surfaces: List[Any] = []
        owner_surfaces_omitted = 0
        first_underlying_path = None
        first_underlying_owner_surface = None
        first_underlying_recommended_action = None
        first_underlying_session_id = None

        for group in groups:
            raw_counts = group.get("underlying_dirty_path_class_counts")
            if isinstance(raw_counts, Mapping):
                for class_id, count in raw_counts.items():
                    class_key = str(class_id or "").strip()
                    if not class_key:
                        continue
                    class_counts[class_key] = class_counts.get(class_key, 0) + int(
                        count or 0
                    )
            for owner_surface in list(
                group.get("underlying_owner_surfaces_preview") or []
            ):
                if owner_surface and owner_surface not in owner_surfaces:
                    owner_surfaces.append(owner_surface)
            owner_surfaces_omitted += int(
                group.get("underlying_owner_surfaces_omitted") or 0
            )
            group_first_path = group.get("first_underlying_path")
            if group_first_path and first_underlying_path is None:
                first_underlying_path = group_first_path
                first_underlying_owner_surface = group.get(
                    "first_underlying_owner_surface"
                )
                first_underlying_recommended_action = group.get(
                    "first_underlying_recommended_action"
                )
                first_underlying_session_id = group.get("session_id")

        owner_preview = owner_surfaces[:4]
        if not class_counts and not owner_preview and first_underlying_path is None:
            return None
        return {
            "schema": "dirty_tree_active_claim_underlying_summary_v0",
            "session_group_count": len(groups),
            "dirty_path_class_counts": class_counts,
            "owner_surfaces_preview": owner_preview,
            "owner_surfaces_omitted": owner_surfaces_omitted
            + max(0, len(owner_surfaces) - len(owner_preview)),
            "first_underlying_session_id": first_underlying_session_id,
            "first_underlying_path": first_underlying_path,
            "first_underlying_owner_surface": first_underlying_owner_surface,
            "first_underlying_recommended_action": (
                first_underlying_recommended_action
            ),
            "checkpoint_policy": (
                "Active claims remain the broad-checkpoint blocker; underlying "
                "classes describe the owner lane to expect after the session "
                "lands or releases its claims."
            ),
        }

    def _path_class_preview(row: Any) -> Dict[str, Any] | None:
        if not isinstance(row, Mapping):
            return None
        owner_surfaces, owner_surfaces_omitted = _owner_surfaces_preview(row)
        return {
            "class": row.get("class"),
            "path_count": row.get("path_count"),
            "first_path": row.get("first_path"),
            "first_path_owner_surface": row.get("first_path_owner_surface"),
            "first_path_recommended_action": row.get(
                "first_path_recommended_action"
            ),
            "first_path_preflight_command": row.get("first_path_preflight_command"),
            "owner_surfaces_preview": owner_surfaces,
            "owner_surfaces_omitted": owner_surfaces_omitted,
        }

    def _first_owner_settlement_action(row: Any) -> Dict[str, Any] | None:
        if not isinstance(row, Mapping):
            return None
        owner_surfaces, owner_surfaces_omitted = _owner_surfaces_preview(row)
        return {
            "kind": row.get("kind"),
            "path_class": row.get("path_class"),
            "first_path": row.get("first_path"),
            "first_path_owner_surface": row.get("first_path_owner_surface"),
            "first_path_recommended_action": row.get(
                "first_path_recommended_action"
            ),
            "first_path_preflight_command": row.get("first_path_preflight_command"),
            "owner_surfaces_preview": owner_surfaces,
            "owner_surfaces_omitted": owner_surfaces_omitted,
        }

    def _after_active_claims_clear_preview() -> Dict[str, Any] | None:
        after_clear = checkpoint.get("after_active_claims_clear")
        if not isinstance(after_clear, Mapping):
            return None
        return {
            "status": after_clear.get("status"),
            "operator_authorized": bool(after_clear.get("operator_authorized")),
            "remaining_dirty_path_classes": dict(
                after_clear.get("remaining_dirty_path_classes") or {}
            ),
            "checkpoint_guard": after_clear.get("checkpoint_guard"),
            "recheck_command": after_clear.get("recheck_command"),
            "first_owner_settlement_action": _first_owner_settlement_action(
                after_clear.get("first_owner_settlement_action")
            ),
            "generated_owner_dirty": _path_class_preview(
                after_clear.get("included_generated_owner_dirty")
            ),
            "unclaimed_source_dirty": _path_class_preview(
                after_clear.get("included_unclaimed_source_dirty")
            ),
        }

    blocking_session = _blocking_session_row(first_group) if first_group else None
    blocking_sessions_preview = [
        _blocking_session_row(group) for group in groups[:4]
    ]
    after_active_claims_clear = _after_active_claims_clear_preview()

    commands = dirty_tree_pressure.get("commands")
    commands = commands if isinstance(commands, Mapping) else {}
    recheck_command = checkpoint.get("recheck_command") or commands.get("sweep_dry_run")
    checkpoint_guard = {
        "status": checkpoint_status,
        "authorized": bool(checkpoint.get("authorized")),
        "command": checkpoint.get("command"),
        "conservative_fallback_command": checkpoint.get(
            "conservative_fallback_command"
        ),
        "blocked_by": list(checkpoint.get("blocked_by") or []),
        "available_after": checkpoint.get("available_after"),
        "recheck_command": recheck_command,
    }

    def _post_active_claim_settlement_summary() -> Dict[str, Any]:
        policy = (
            "Active claim clearance is not broad-checkpoint clearance; run the "
            "dirty-pressure recheck and settle generated-owner or unclaimed "
            "dirty classes before invoking checkpoint."
        )
        if not isinstance(after_active_claims_clear, Mapping):
            return {
                "schema": "dirty_tree_post_active_claim_settlement_summary_v0",
                "status": "no_preview_available",
                "remaining_dirty_path_count": 0,
                "remaining_dirty_path_classes": {},
                "generated_owner_dirty_count": 0,
                "unclaimed_source_dirty_count": 0,
                "first_settlement_kind": None,
                "first_settlement_path_class": None,
                "first_settlement_path": None,
                "first_settlement_command": None,
                "recheck_command": recheck_command,
                "checkpoint_after_active_claims_policy": policy,
            }

        raw_counts = after_active_claims_clear.get("remaining_dirty_path_classes")
        raw_counts = raw_counts if isinstance(raw_counts, Mapping) else {}
        remaining_counts: Dict[str, int] = {}
        for class_id, count in raw_counts.items():
            class_key = str(class_id or "").strip()
            if not class_key:
                continue
            try:
                remaining_counts[class_key] = int(count or 0)
            except (TypeError, ValueError):
                remaining_counts[class_key] = 0

        owner_action = after_active_claims_clear.get("first_owner_settlement_action")
        owner_action = owner_action if isinstance(owner_action, Mapping) else None
        remaining_dirty_path_count = sum(remaining_counts.values())
        if remaining_dirty_path_count > 0 or owner_action:
            settlement_status = "settlement_required_after_active_claims"
        else:
            settlement_status = "checkpoint_recheck_only"

        return {
            "schema": "dirty_tree_post_active_claim_settlement_summary_v0",
            "status": settlement_status,
            "remaining_dirty_path_count": remaining_dirty_path_count,
            "remaining_dirty_path_classes": remaining_counts,
            "generated_owner_dirty_count": remaining_counts.get(
                "generated_owner_dirty", 0
            ),
            "unclaimed_source_dirty_count": remaining_counts.get(
                "unclaimed_source_dirty", 0
            ),
            "first_settlement_kind": (
                owner_action.get("kind") if owner_action else None
            ),
            "first_settlement_path_class": (
                owner_action.get("path_class") if owner_action else None
            ),
            "first_settlement_path": (
                owner_action.get("first_path") if owner_action else None
            ),
            "first_settlement_command": (
                owner_action.get("first_path_recommended_action")
                if owner_action
                else None
            ),
            "recheck_command": recheck_command,
            "checkpoint_after_active_claims_policy": policy,
        }

    def _no_heartbeat_blocking_claim_summary() -> Dict[str, Any] | None:
        if not isinstance(blocking_session, Mapping):
            return None

        heartbeat_gap_blocker_count = 0
        projected_unknown_blocker_count = 0
        live_blocker_count = 0
        for group in groups:
            session_id = str(group.get("session_id") or "").strip()
            coordination = coordination_by_session.get(session_id) or {}
            if session_id in heartbeat_gap_ids:
                heartbeat_gap_blocker_count += 1
            freshness_state = str(coordination.get("freshness_state") or "").strip()
            if freshness_state == "live":
                live_blocker_count += 1
            if not coordination or freshness_state in {"", "unknown"}:
                projected_unknown_blocker_count += 1

        heartbeat_gap = bool(blocking_session.get("heartbeat_gap"))
        if heartbeat_gap:
            summary_status = "heartbeat_gap_claims_block_checkpoint"
        elif live_blocker_count:
            summary_status = "live_claims_block_checkpoint"
        else:
            summary_status = "claims_block_checkpoint"

        read_only_command = (
            str(
                blocking_session.get("safe_next_command")
                or blocking_session.get("session_status_command")
                or first_action_command
                or ""
            ).strip()
            or None
        )
        paths_preview = list(blocking_session.get("paths_preview") or [])
        return {
            "schema": "dirty_tree_no_heartbeat_blocking_claim_summary_v0",
            "status": summary_status,
            "blocking_session_group_count": len(groups),
            "heartbeat_gap_blocking_session_count": heartbeat_gap_blocker_count,
            "projected_unknown_blocking_session_count": projected_unknown_blocker_count,
            "live_blocking_session_count": live_blocker_count,
            "first_blocking_session_id": blocking_session.get("session_id"),
            "first_blocking_session_actor": blocking_session.get("actor"),
            "first_blocking_session_heartbeat_gap": heartbeat_gap,
            "first_blocking_session_freshness_state": blocking_session.get(
                "freshness_state"
            ),
            "first_blocking_session_pass_state": blocking_session.get("pass_state"),
            "first_blocking_session_current_pass_line": blocking_session.get(
                "current_pass_line"
            ),
            "first_blocking_session_recommended_action": blocking_session.get(
                "recommended_action"
            ),
            "first_read_only_alternative_command": read_only_command,
            "first_claimed_dirty_path": paths_preview[0] if paths_preview else None,
            "first_underlying_dirty_path": blocking_session.get(
                "first_underlying_path"
            ),
            "lease_state": blocking_session.get("lease_state"),
            "lease_seconds_remaining": blocking_session.get(
                "lease_seconds_remaining"
            ),
            "leased_until": blocking_session.get("leased_until_max"),
            "heartbeat_action_allowed_by_this_packet": False,
            "recheck_after_owner_release_command": recheck_command,
            "checkpoint_policy": (
                "No-heartbeat mode must not publish heartbeat writes for blocking "
                "claim sessions; inspect the session read-only or wait for the "
                "owner to land, release, or finalize, then re-run dirty-tree "
                "pressure before checkpointing."
            ),
        }

    def _scoped_work_continuation_summary() -> Dict[str, Any]:
        raw_blocked_by = list(checkpoint.get("blocked_by") or [])
        blocked_by = [str(item) for item in raw_blocked_by if str(item).strip()]
        remaining_counts: Dict[str, int] = {}
        if isinstance(after_active_claims_clear, Mapping):
            raw_counts = after_active_claims_clear.get("remaining_dirty_path_classes")
            raw_counts = raw_counts if isinstance(raw_counts, Mapping) else {}
            for class_id, count in raw_counts.items():
                class_key = str(class_id or "").strip()
                if not class_key:
                    continue
                try:
                    remaining_counts[class_key] = int(count or 0)
                except (TypeError, ValueError):
                    remaining_counts[class_key] = 0

        if claim_collision_count:
            first_broad_checkpoint_blocker = "claim_collisions"
        elif active_claim_dirty_path_count:
            first_broad_checkpoint_blocker = "active_claim_dirty_paths"
        elif remaining_counts.get("generated_owner_dirty", 0) > 0:
            first_broad_checkpoint_blocker = "generated_owner_dirty"
        elif remaining_counts.get("unclaimed_source_dirty", 0) > 0:
            first_broad_checkpoint_blocker = "unclaimed_source_dirty"
        elif checkpoint_status == "available":
            first_broad_checkpoint_blocker = "none"
        else:
            first_broad_checkpoint_blocker = "dirty_pressure_recheck_required"

        if checkpoint_status == "available":
            continuation_status = (
                "broad_checkpoint_available_recheck_before_scoped_work"
            )
        elif checkpoint_status == "unknown":
            continuation_status = "scoped_work_requires_dirty_pressure_recheck"
        else:
            continuation_status = "scoped_work_allowed_while_checkpoint_blocked"

        read_only_blocker_command = None
        active_claim_blocking_session_id = None
        if isinstance(blocking_session, Mapping):
            active_claim_blocking_session_id = blocking_session.get("session_id")
            read_only_blocker_command = (
                str(
                    blocking_session.get("safe_next_command")
                    or blocking_session.get("session_status_command")
                    or ""
                ).strip()
                or None
            )

        return {
            "schema": "dirty_tree_scoped_work_continuation_summary_v0",
            "status": continuation_status,
            "scoped_work_policy": (
                "Dirty-tree pressure blocks broad checkpoint, not scoped "
                "commits for newly claimed disjoint owned paths."
            ),
            "scoped_work_gate": "claim_owned_paths_then_scoped_commit",
            "scoped_commit_lane_allowed": True,
            "broad_checkpoint_status": checkpoint_status,
            "broad_checkpoint_command": checkpoint.get("command"),
            "broad_checkpoint_blocked_by": blocked_by,
            "first_broad_checkpoint_blocker": first_broad_checkpoint_blocker,
            "claim_collision_count": claim_collision_count,
            "active_claim_dirty_path_count": active_claim_dirty_path_count,
            "active_claim_blocking_session_id": active_claim_blocking_session_id,
            "read_only_blocker_command": read_only_blocker_command,
            "remaining_dirty_path_classes_after_claims": remaining_counts,
            "claim_first_command_template": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-slug <slug> --path <owned-path> --require-exclusive"
            ),
            "preflight_command_template": (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                "--subject-id <id> --session-id <session-id> "
                "--owned-path <owned-path> --fail-on-status blocked"
            ),
            "scoped_commit_command_template": (
                "./repo-python tools/meta/control/scoped_commit.py full-paths "
                "--path <owned-path> --expected-parent <HEAD> "
                "--work-ledger-session-id <session-id> "
                "--allow-multi-hunk-full-paths --message \"<message>\""
            ),
            "must_not_do": [
                "git add -A",
                "git commit -am",
                "git stash",
                "git reset --hard",
                "broad checkpoint until checkpoint_guard.status == available",
            ],
            "safe_next_action_when_not_owning_blocker": (
                "Choose a disjoint owned path, claim it with session-preflight, "
                "run mission transaction preflight for that path, and land only "
                "that scoped path; do not wait for global tree cleanliness."
            ),
            "heartbeat_action_allowed_by_this_packet": False,
            "recheck_command": recheck_command,
        }

    def _checkpoint_clearance_ladder() -> Dict[str, Any]:
        collision_cleanup = checkpoint.get("blocking_claim_collision_cleanup")
        collision_cleanup = (
            collision_cleanup if isinstance(collision_cleanup, Mapping) else {}
        )
        collision_command = (
            str(
                checkpoint.get("first_claim_collision_cleanup_command")
                or collision_cleanup.get("auto_release_dry_run_command")
                or collision_cleanup.get("first_action_command")
                or ""
            ).strip()
            or None
        )
        active_claim_blocked = bool(active_claim_dirty_path_count and blocking_session)
        prior_blocked = bool(claim_collision_count or active_claim_blocked)
        active_claim_command = None
        if isinstance(blocking_session, Mapping):
            active_claim_command = (
                str(
                    blocking_session.get("safe_next_command")
                    or blocking_session.get("session_status_command")
                    or first_action_command
                    or ""
                ).strip()
                or None
            )

        owner_action = None
        if isinstance(after_active_claims_clear, Mapping):
            owner_action = after_active_claims_clear.get(
                "first_owner_settlement_action"
            )
            owner_action = owner_action if isinstance(owner_action, Mapping) else None
        owner_command = None
        if owner_action:
            owner_command = (
                str(owner_action.get("first_path_recommended_action") or "").strip()
                or None
            )

        if claim_collision_count:
            current_blocker = "claim_collisions"
        elif active_claim_blocked:
            current_blocker = "active_claim_dirty_paths"
        elif checkpoint_status == "available":
            current_blocker = "checkpoint_available"
        elif after_active_claims_clear:
            current_blocker = "recheck_required_before_checkpoint"
        else:
            current_blocker = "dirty_pressure_observed"

        active_step_status = "clear"
        if claim_collision_count:
            active_step_status = "waiting_on_prior_step"
        elif active_claim_blocked:
            active_step_status = "blocked"

        recheck_step_status = "ready"
        if prior_blocked:
            recheck_step_status = "waiting_on_prior_step"
        elif checkpoint_status == "available":
            recheck_step_status = "clear"

        owner_step_status = "not_applicable"
        if prior_blocked:
            owner_step_status = "waiting_on_prior_step"
        elif owner_action:
            owner_step_status = "ready"

        checkpoint_step_status = "blocked"
        if checkpoint_status == "available" and checkpoint.get("command"):
            checkpoint_step_status = "available"

        ordered_steps: List[Dict[str, Any]] = [
            {
                "step": "resolve_claim_collisions",
                "status": "blocked" if claim_collision_count else "clear",
                "command": collision_command,
                "why": (
                    "Claim collisions block broad checkpointing before active-claim "
                    "or owner-settlement work."
                    if claim_collision_count
                    else "No claim collisions are currently blocking the checkpoint."
                ),
            },
            {
                "step": "settle_active_claim_session",
                "status": active_step_status,
                "session_id": (
                    blocking_session.get("session_id")
                    if isinstance(blocking_session, Mapping)
                    else None
                ),
                "heartbeat_gap": (
                    blocking_session.get("heartbeat_gap")
                    if isinstance(blocking_session, Mapping)
                    else None
                ),
                "lease_state": (
                    blocking_session.get("lease_state")
                    if isinstance(blocking_session, Mapping)
                    else None
                ),
                "command": active_claim_command,
                "heartbeat_action_allowed_by_this_packet": False,
                "why": (
                    "Active claimed dirty paths block broad checkpointing; inspect "
                    "the owner session and wait for it to land, release, or finalize."
                    if active_claim_blocked
                    else "No active-claim dirty paths are currently blocking the checkpoint."
                ),
            },
            {
                "step": "recheck_after_active_claims",
                "status": recheck_step_status,
                "command": recheck_command,
                "why": (
                    "Re-run dirty-tree pressure after claim blockers clear before "
                    "trusting any checkpoint recommendation."
                ),
            },
            {
                "step": "settle_remaining_owner_dirty",
                "status": owner_step_status,
                "path_class": owner_action.get("path_class") if owner_action else None,
                "first_path": owner_action.get("first_path") if owner_action else None,
                "command": owner_command,
                "why": (
                    "After active claims clear, settle generated-owner or unclaimed "
                    "dirty classes before broad checkpointing."
                    if owner_action
                    else "No post-claim owner-settlement preview is available."
                ),
            },
            {
                "step": "operator_authorized_checkpoint",
                "status": checkpoint_step_status,
                "command": checkpoint.get("command"),
                "why": (
                    "Broad checkpoint is available only after the dirty-pressure "
                    "guard returns available."
                ),
            },
        ]

        first_blocking_step = None
        first_blocking_command = None
        for step in ordered_steps:
            if step["status"] == "blocked":
                first_blocking_step = step["step"]
                first_blocking_command = step.get("command")
                break

        return {
            "schema": "dirty_tree_checkpoint_clearance_ladder_v0",
            "status": status,
            "current_blocker": current_blocker,
            "no_heartbeat_mode_safe": True,
            "first_blocking_step": first_blocking_step,
            "first_blocking_command": first_blocking_command,
            "ordered_steps": ordered_steps,
            "checkpoint_policy": (
                "Broad checkpoint stays blocked until claim collisions and "
                "active-claim dirty paths are clear, then the pressure recheck "
                "returns available."
            ),
        }

    def _agent_decision_summary(
        scoped_work: Mapping[str, Any],
        ladder: Mapping[str, Any],
        blocking_claim_summary: Mapping[str, Any] | None,
        post_claim_summary: Mapping[str, Any],
        lease_summary: Mapping[str, Any] | None,
        coordination_summary: Mapping[str, Any] | None,
    ) -> Dict[str, Any]:
        blocking_claim_summary = blocking_claim_summary or {}
        lease_summary = lease_summary or {}
        coordination_summary = coordination_summary or {}
        checkpoint_available = checkpoint_status == "available"
        dirty_class_counts = dict(
            dirty_tree_pressure.get("dirty_path_class_counts")
            or dirty_tree_pressure.get("class_counts")
            or {}
        )
        open_lanes = ["scoped_owned_path_commit"]
        if first_action_kind == "claim_collision" and first_action_command:
            open_lanes.insert(0, "claim_collision_cleanup_dry_run")
        if checkpoint_available:
            open_lanes.append("broad_checkpoint_after_recheck")

        blocked_lanes = [] if checkpoint_available else ["broad_checkpoint"]
        if checkpoint_available:
            status_for_agent = "checkpoint_available_recheck_before_broad_save"
            decision = "recheck_then_checkpoint_or_continue_scoped_work"
            headline = (
                "Broad checkpoint may be available; run the dirty-pressure "
                "recheck before broad save."
            )
        else:
            status_for_agent = "do_not_broad_checkpoint_continue_scoped_work"
            decision = "continue_scoped_owned_path_work"
            headline = (
                "Broad checkpoint is blocked; continue only with claimed-path "
                "scoped commits or read-only blocker inspection."
            )

        return {
            "schema": "dirty_tree_agent_decision_summary_v0",
            "status": status_for_agent,
            "decision": decision,
            "headline": headline,
            "open_lanes": open_lanes,
            "blocked_lanes": blocked_lanes,
            "suppressed_lanes": ["heartbeat_write"],
            "checkpoint_blocker": scoped_work.get("first_broad_checkpoint_blocker"),
            "checkpoint_unblock_step": ladder.get("first_blocking_step"),
            "checkpoint_unblock_command": ladder.get("first_blocking_command"),
            "dirty_total": dirty_tree_pressure.get("dirty_total"),
            "dirty_path_class_counts": dirty_class_counts,
            "active_claim_dirty_path_count": scoped_work.get(
                "active_claim_dirty_path_count"
            ),
            "broad_checkpoint_status": scoped_work.get("broad_checkpoint_status"),
            "broad_checkpoint_command": scoped_work.get("broad_checkpoint_command"),
            "broad_checkpoint_blocked_by": scoped_work.get(
                "broad_checkpoint_blocked_by"
            ),
            "blocking_claim_session_count": blocking_claim_summary.get(
                "blocking_session_group_count"
            ),
            "heartbeat_gap_blocking_session_count": blocking_claim_summary.get(
                "heartbeat_gap_blocking_session_count"
            ),
            "projected_unknown_blocking_session_count": blocking_claim_summary.get(
                "projected_unknown_blocking_session_count"
            ),
            "live_blocking_session_count": blocking_claim_summary.get(
                "live_blocking_session_count"
            ),
            "blocking_claim_first_heartbeat_gap_session_id": coordination_summary.get(
                "first_heartbeat_gap_session_id"
            ),
            "blocking_claim_first_heartbeat_gap_read_only_command": (
                coordination_summary.get("first_heartbeat_gap_read_only_command")
            ),
            "blocking_claim_first_unknown_session_id": coordination_summary.get(
                "first_unknown_session_id"
            ),
            "blocking_claim_first_unknown_read_only_command": coordination_summary.get(
                "first_unknown_session_read_only_command"
            ),
            "blocking_claim_first_live_session_id": coordination_summary.get(
                "first_live_session_id"
            ),
            "blocking_claim_first_live_read_only_command": coordination_summary.get(
                "first_live_session_read_only_command"
            ),
            "blocking_claim_no_heartbeat_policy": coordination_summary.get(
                "no_heartbeat_policy"
            ),
            "first_blocking_session_id": blocking_claim_summary.get(
                "first_blocking_session_id"
            ),
            "first_blocking_session_actor": blocking_claim_summary.get(
                "first_blocking_session_actor"
            ),
            "first_blocking_session_freshness_state": blocking_claim_summary.get(
                "first_blocking_session_freshness_state"
            ),
            "first_blocking_session_pass_state": blocking_claim_summary.get(
                "first_blocking_session_pass_state"
            ),
            "first_blocking_session_current_pass_line": blocking_claim_summary.get(
                "first_blocking_session_current_pass_line"
            ),
            "first_blocking_session_recommended_action": blocking_claim_summary.get(
                "first_blocking_session_recommended_action"
            ),
            "first_blocking_session_heartbeat_gap": blocking_claim_summary.get(
                "first_blocking_session_heartbeat_gap"
            ),
            "first_blocking_session_lease_state": blocking_claim_summary.get(
                "lease_state"
            ),
            "first_blocking_session_lease_seconds_remaining": blocking_claim_summary.get(
                "lease_seconds_remaining"
            ),
            "first_blocking_session_leased_until": blocking_claim_summary.get(
                "leased_until"
            ),
            "first_claimed_dirty_path": blocking_claim_summary.get(
                "first_claimed_dirty_path"
            ),
            "first_underlying_dirty_path": blocking_claim_summary.get(
                "first_underlying_dirty_path"
            ),
            "first_blocking_session_read_only_command": blocking_claim_summary.get(
                "first_read_only_alternative_command"
            ),
            "recheck_after_owner_release_command": blocking_claim_summary.get(
                "recheck_after_owner_release_command"
            ),
            "post_claim_settlement_status": post_claim_summary.get("status"),
            "post_claim_remaining_dirty_path_count": post_claim_summary.get(
                "remaining_dirty_path_count"
            ),
            "post_claim_remaining_dirty_path_classes": post_claim_summary.get(
                "remaining_dirty_path_classes"
            ),
            "post_claim_generated_owner_dirty_count": post_claim_summary.get(
                "generated_owner_dirty_count"
            ),
            "post_claim_unclaimed_source_dirty_count": post_claim_summary.get(
                "unclaimed_source_dirty_count"
            ),
            "post_claim_first_settlement_kind": post_claim_summary.get(
                "first_settlement_kind"
            ),
            "post_claim_first_settlement_path_class": post_claim_summary.get(
                "first_settlement_path_class"
            ),
            "post_claim_first_settlement_path": post_claim_summary.get(
                "first_settlement_path"
            ),
            "post_claim_first_settlement_command": post_claim_summary.get(
                "first_settlement_command"
            ),
            "post_claim_recheck_command": post_claim_summary.get("recheck_command"),
            "post_claim_checkpoint_policy": post_claim_summary.get(
                "checkpoint_after_active_claims_policy"
            ),
            "blocking_claim_active_lease_session_count": lease_summary.get(
                "active_lease_group_count"
            ),
            "blocking_claim_expired_lease_session_count": lease_summary.get(
                "expired_lease_group_count"
            ),
            "blocking_claim_unknown_lease_session_count": lease_summary.get(
                "unknown_lease_group_count"
            ),
            "blocking_claim_first_expired_session_id": lease_summary.get(
                "first_expired_session_id"
            ),
            "blocking_claim_earliest_active_lease_session_id": lease_summary.get(
                "earliest_active_session_id"
            ),
            "blocking_claim_earliest_active_lease_until": lease_summary.get(
                "earliest_active_lease_until"
            ),
            "blocking_claim_lease_observed_at": lease_summary.get("observed_at"),
            "blocking_claim_lease_policy": lease_summary.get("checkpoint_policy"),
            "global_first_action_kind": first_action_kind,
            "global_first_action_command": first_action_command,
            "local_work_first_action": "claim_disjoint_owned_path",
            "local_work_first_action_command_template": scoped_work.get(
                "claim_first_command_template"
            ),
            "scoped_commit_lane_allowed": scoped_work.get(
                "scoped_commit_lane_allowed"
            ),
            "heartbeat_action_allowed_by_this_packet": False,
            "operator_wait_required_for_disjoint_scoped_work": False,
            "policy": (
                "Dirty-tree pressure is a broad-checkpoint blocker and a "
                "coordination signal; it is not a reason to stop disjoint "
                "claimed-path scoped work."
            ),
        }

    scoped_work_continuation_summary = _scoped_work_continuation_summary()
    checkpoint_clearance_ladder = _checkpoint_clearance_ladder()
    no_heartbeat_blocking_claim_summary = _no_heartbeat_blocking_claim_summary()
    post_active_claim_settlement_summary = _post_active_claim_settlement_summary()
    blocking_session_lease_summary = _blocking_session_lease_summary()
    blocking_session_coordination_summary = _blocking_session_coordination_summary()

    focus: Dict[str, Any] = {
        "schema": "work_ledger_seed_speed_dirty_pressure_focus_v0",
        "status": status,
        "checkpoint_status": checkpoint_status,
        "checkpoint_authorized": bool(checkpoint.get("authorized")),
        "checkpoint_guard": checkpoint_guard,
        "agent_decision_summary": _agent_decision_summary(
            scoped_work_continuation_summary,
            checkpoint_clearance_ladder,
            no_heartbeat_blocking_claim_summary,
            post_active_claim_settlement_summary,
            blocking_session_lease_summary,
            blocking_session_coordination_summary,
        ),
        "after_active_claims_clear": after_active_claims_clear,
        "post_active_claim_settlement_summary": post_active_claim_settlement_summary,
        "no_heartbeat_blocking_claim_summary": no_heartbeat_blocking_claim_summary,
        "scoped_work_continuation_summary": scoped_work_continuation_summary,
        "checkpoint_clearance_ladder": checkpoint_clearance_ladder,
        "dirty_total": dirty_tree_pressure.get("dirty_total"),
        "dirty_path_class_counts": dict(
            dirty_tree_pressure.get("dirty_path_class_counts")
            or dirty_tree_pressure.get("class_counts")
            or {}
        ),
        "active_claim_dirty_path_count": active_claim_dirty_path_count,
        "active_claim_underlying_dirty_summary": _active_claim_underlying_summary(),
        "claim_collision_count": claim_collision_count,
        "blocking_session": blocking_session,
        "blocking_session_coordination_summary": blocking_session_coordination_summary,
        "blocking_session_lease_summary": blocking_session_lease_summary,
        "blocking_session_group_count": group_packet.get("group_count"),
        "blocking_sessions_preview": blocking_sessions_preview,
        "blocking_sessions_omitted": max(0, len(groups) - len(blocking_sessions_preview)),
        "first_action_kind": first_action_kind,
        "first_action": first_action,
        "first_action_command": first_action_command,
        "first_action_ref": first_action_ref,
        "promote_for_no_heartbeat": promote_for_no_heartbeat,
        "recheck_command": recheck_command,
    }
    return focus


def _seed_speed_dirty_pressure_action(
    dirty_tree_pressure_focus: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(dirty_tree_pressure_focus, Mapping):
        return None
    if not bool(dirty_tree_pressure_focus.get("promote_for_no_heartbeat")):
        return None
    command = str(dirty_tree_pressure_focus.get("first_action_command") or "").strip()
    if not command:
        return None
    return {
        "kind": dirty_tree_pressure_focus.get("first_action_kind"),
        "action": dirty_tree_pressure_focus.get("first_action"),
        "command": command,
        "ref": dirty_tree_pressure_focus.get("first_action_ref"),
    }


def _seed_speed_generated_surface_claim_lens(
    *,
    active_claims: Sequence[Mapping[str, Any]],
    seed_claim_sessions: Sequence[Mapping[str, Any]],
    claim_collision_actions: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Project generated-entry surface ownership from the seed-speed claim packet."""

    cards_by_session = {
        str(card.get("session_id") or "").strip(): card
        for card in seed_claim_sessions
        if isinstance(card, Mapping) and str(card.get("session_id") or "").strip()
    }
    claims_by_path: Dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for claim in active_claims:
        if not isinstance(claim, Mapping):
            continue
        path = str(claim.get("path") or claim.get("scope_id") or "").strip()
        if path:
            claims_by_path[path].append(claim)
    collision_paths = {
        str(row.get("path") or "").strip()
        for row in claim_collision_actions
        if isinstance(row, Mapping) and str(row.get("path") or "").strip()
    }

    rows: list[dict[str, Any]] = []
    for path in MICROCOSM_GENERATED_ENTRY_SURFACES:
        claims = claims_by_path.get(path, [])
        first_claim = claims[0] if claims else {}
        session_id = str(first_claim.get("session_id") or "").strip()
        card = cards_by_session.get(session_id) or {}
        freshness = str(
            card.get("freshness_state")
            or first_claim.get("freshness_state")
            or "unclaimed"
        )
        has_collision = path in collision_paths
        if has_collision:
            classification = "claim_collision"
            allowed_action = "run_mutation_check_before_regeneration"
            reentry_condition = "collision cleanup summary clears this path"
        elif claims and freshness == "live":
            classification = "owned_live"
            allowed_action = "do_not_patch_from_sibling_lane"
            reentry_condition = "owner session lands, releases, or records handoff"
        elif claims:
            classification = "owned_stale"
            allowed_action = "release_or_supersede_owner_claim_then_regenerate"
            reentry_condition = "claim is released or superseded through Work Ledger"
        else:
            classification = "unowned"
            allowed_action = "claim_builder_lane_before_regenerating_if_drift_observed"
            reentry_condition = "generator owner claim exists before rebuild"

        rows.append(
            {
                "path": path,
                "classification": classification,
                "owner_session_id": session_id or None,
                "claim_id": str(first_claim.get("claim_id") or "").strip() or None,
                "claim_scope": str(first_claim.get("scope_kind") or "path"),
                "freshness_state": freshness,
                "claim_count": len(claims),
                "allowed_action": allowed_action,
                "reentry_condition": reentry_condition,
            }
        )

    return {
        "schema": GENERATED_SURFACE_CLAIM_LENS_SCHEMA,
        "surface_role": "seed_speed_generated_surface_claim_lens",
        "authority_boundary": (
            "Work Ledger claim ownership projection only; generated-file drift "
            "truth remains with the owning builder/check command."
        ),
        "drift_input_status": "not_run_by_seed_speed",
        "tracked_surface_count": len(MICROCOSM_GENERATED_ENTRY_SURFACES),
        "tracked_surfaces": list(MICROCOSM_GENERATED_ENTRY_SURFACES),
        "surface_owner_rows": rows,
        "classification_contract": {
            "owned_live": "live owner owns the surface; hand off instead of patching",
            "owned_stale": "owner claim exists but freshness is not live; release or supersede first",
            "unowned": "claim a builder lane before regenerating when drift is observed",
            "claim_collision": "resolve collision before regeneration or mutation",
        },
    }


def _seed_speed_blocked_continuation_options(
    *,
    blocked_owner_rows: Sequence[Mapping[str, Any]],
    first_action_command: str | None,
) -> list[dict[str, Any]]:
    owner_session_ids = sorted(
        {
            str(row.get("owner_session_id") or "").strip()
            for row in blocked_owner_rows
            if str(row.get("owner_session_id") or "").strip()
        }
    )
    held_paths = [
        str(row.get("path") or "").strip()
        for row in blocked_owner_rows
        if str(row.get("path") or "").strip()
    ]
    first_owner = owner_session_ids[0] if owner_session_ids else "<owner-session-id>"
    first_path = held_paths[0] if held_paths else "<held-path>"
    owner_fan_in_command = _wl_command(
        "session-yield-request",
        f"--target-session-id {_quote_cli(first_owner)}",
        "--target-class settlement_obligation_owner",
        "--requested-action release_after_landing",
        "--result requested",
        "--coordination-brief",
        "--requester-label '<requesting thread>'",
        "--blocked-on '<blocking condition>'",
        "--validation-status '<current validation state>'",
        f"--held-path {_quote_cli(first_path)}",
        "--avoid-session-id '<sibling session id>'",
    )
    return [
        {
            "lane": "owner_fan_in",
            "allowed": bool(owner_session_ids),
            "command": owner_fan_in_command,
            "requires": [
                "held path",
                "desired result",
                "validation state",
                "ack or release predicate",
            ],
        },
        {
            "lane": "companion_surface_lane",
            "allowed": True,
            "command": _wl_command(
                "session-preflight",
                "--session-id <your-session-id>",
                "--path <disjoint-companion-surface>",
                "--require-exclusive",
                "--heartbeat-current-pass-line '<public current pass>'",
            ),
            "requires": [
                "disjoint path",
                "same rule or proof surface",
                "fresh mutation-check before editing",
            ],
        },
        {
            "lane": "patch_handoff_artifact",
            "artifact_class": "pending_diff_signoff",
            "default_status": "pending_review",
            "allowed": True,
            "command": (
                "./repo-python tools/meta/factory/claim_settlement_continuation.py "
                "record --payload-file <candidate.json>"
            ),
            "requires": [
                "base commit / base_rev",
                "per-path hashes",
                "allowed paths",
                "forbidden paths",
                "hunk, symbol, selector, or generated-source touchpoints",
                "unified diff or equivalent patch payload",
                "validation receipts before block",
                "active claim context",
                "fresh adjudication checks",
            ],
            "signoff_policy": (
                "Any capable agent may approve when recent diffs, timestamps, "
                "thread provenance, active claims, generated/source relationships, "
                "and validation receipts show clean non-interference."
            ),
        },
        {
            "lane": "validation_substitution",
            "allowed": True,
            "evidence_floor": (
                "Use the cheapest relevant proof ladder, then record full validation "
                "as queued or substituted rather than failed."
            ),
        },
        {
            "lane": "cas_retry",
            "allowed": True,
            "condition": (
                "Only after re-reading HEAD, scoped diff, path ownership, and "
                "validation assumptions."
            ),
        },
        {
            "lane": "residual_capture",
            "allowed": True,
            "command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
                "--created-by <agent_id> --rebuild --confidence 0.85 "
                "--title '<blocked continuation>' --statement '<owner, blocker, proof, re-entry>'"
            ),
            "condition": "Only when fan-in, disjoint lane, and patch handoff are unavailable.",
        },
        {
            "lane": "nothing_to_refine",
            "allowed": True,
            "condition": (
                "Only when current cards/tests already prove active alternatives and "
                "no owner surface needs mutation."
            ),
        },
    ]


def _seed_speed_concurrency_closure_state_lens(
    *,
    generated_surface_claim_lens: Mapping[str, Any],
    dirty_tree_pressure_focus: Mapping[str, Any] | None,
    counts: Mapping[str, Any],
    first_action_kind: str,
    first_action: str,
    first_action_command: str | None,
) -> Dict[str, Any]:
    """Expose closure-state inputs without pretending seed-speed ran validation."""

    surface_rows = [
        row
        for row in list(generated_surface_claim_lens.get("surface_owner_rows") or [])
        if isinstance(row, Mapping)
    ]
    live_owner_rows = [
        row for row in surface_rows if row.get("classification") == "owned_live"
    ]
    stale_owner_rows = [
        row for row in surface_rows if row.get("classification") == "owned_stale"
    ]
    collision_rows = [
        row for row in surface_rows if row.get("classification") == "claim_collision"
    ]
    blocked_owner_rows = [*collision_rows, *live_owner_rows, *stale_owner_rows]
    active_claim_count = int(counts.get("active_claims") or 0)
    dirty_focus_status = (
        str(dirty_tree_pressure_focus.get("status") or "").strip()
        if isinstance(dirty_tree_pressure_focus, Mapping)
        else "not_present"
    )

    if collision_rows:
        current_state = "owned_live_handoff"
        current_reason = "generated-surface claim collision requires owner coordination"
        next_safe_action = "select_blocked_continuation_option"
    elif live_owner_rows:
        current_state = "owned_live_handoff"
        current_reason = "a live owner holds at least one generated public-entry surface"
        next_safe_action = "select_blocked_continuation_option"
    elif stale_owner_rows:
        current_state = "owned_stale_reentry"
        current_reason = "a stale owner claim remains on a generated public-entry surface"
        next_safe_action = "select_blocked_continuation_option"
    elif active_claim_count:
        current_state = "active_not_closed"
        current_reason = "seed-speed sees active claims; closure classification needs the lane receipt"
        next_safe_action = first_action_kind or "choose_disjoint_write_lane"
    else:
        current_state = "no_active_closure_lane"
        current_reason = "seed-speed does not see active claims in this snapshot"
        next_safe_action = "reenter_when_a_lane_receipt_or_drift_check_exists"

    include_blocked_options = current_state in {
        "owned_live_handoff",
        "owned_stale_reentry",
    }
    if include_blocked_options:
        blocked_continuation_options = _seed_speed_blocked_continuation_options(
            blocked_owner_rows=blocked_owner_rows,
            first_action_command=first_action_command,
        )
        blocked_continuation_option_count = len(blocked_continuation_options)
        blocked_continuation_options_omitted = 0
        blocked_continuation_options_ref = None
    else:
        blocked_continuation_options = []
        blocked_continuation_option_count = 7
        blocked_continuation_options_omitted = blocked_continuation_option_count
        blocked_continuation_options_ref = "concurrency_closure_state_lens.compact_omission"

    return {
        "schema": CONCURRENCY_CLOSURE_STATE_LENS_SCHEMA,
        "surface_role": "seed_speed_concurrency_closure_state_lens",
        "authority_boundary": (
            "Work Ledger seed-speed closure projection only; generator drift truth, "
            "validation sufficiency, scoped commit attribution, and Task Ledger "
            "residual closure remain with their owning checks and receipts."
        ),
        "current_state": current_state,
        "current_reason": current_reason,
        "next_safe_action": next_safe_action,
        "next_safe_action_command": first_action_command,
        "blocked_continuation_options": blocked_continuation_options,
        "blocked_continuation_option_count": blocked_continuation_option_count,
        "blocked_continuation_options_omitted": blocked_continuation_options_omitted,
        "blocked_continuation_options_ref": blocked_continuation_options_ref,
        "first_action": first_action,
        "input_status": {
            "generated_surface_owner_lens": "available",
            "generator_drift_check": str(
                generated_surface_claim_lens.get("drift_input_status") or "not_run_by_seed_speed"
            ),
            "validation_quote": "not_run_by_seed_speed",
            "scoped_commit_attribution": dirty_focus_status,
            "task_ledger_residual_truth": "not_evaluated_by_seed_speed",
        },
        "tracked_generated_surface_owner_state_counts": {
            "owned_live": len(live_owner_rows),
            "owned_stale": len(stale_owner_rows),
            "claim_collision": len(collision_rows),
        },
        "compact_omission": (
            {
                "omitted": [
                    "owner_fan_in option command",
                    "companion_surface_lane command",
                    "patch_handoff_artifact command",
                    "validation_substitution detail",
                    "cas_retry detail",
                    "residual_capture command",
                    "nothing_to_refine condition",
                ],
                "reason": (
                    "No generated-surface owner handoff or collision is active; "
                    "seed-speed keeps the first action and omits generic "
                    "continuation recipes."
                ),
                "restore_condition": (
                    "Full blocked_continuation_options are emitted when the lens "
                    "state is owned_live_handoff or owned_stale_reentry."
                ),
            }
            if not include_blocked_options
            else None
        ),
        "closure_state_contract": {
            "closed_and_committed": (
                "source/product landed, validation floor complete, and scoped commit attribution is clean"
            ),
            "closed_uncommitted_authority": (
                "event authority is clean but shared append/generated files are unsafe to stage"
            ),
            "closed_validation_deferred": (
                "product/generator smoke is clean while heavier validation is blocked or queued"
            ),
            "owned_live_handoff": (
                "fresh owner claim controls the target surface; use blocked_continuation_options "
                "to fan in, preserve a patch handoff, choose a disjoint lane, substitute "
                "validation, retry CAS, capture a residual, or prove no refinement"
            ),
            "owned_stale_reentry": (
                "stale owner claim must be released or superseded before re-entry"
            ),
            "unowned_generated_drift": (
                "generated drift exists and no live owner holds the builder lane"
            ),
            "false_residual_stale": (
                "an old residual remains open after current owner/generator evidence disconfirms it"
            ),
        },
    }


def _seed_speed_compact_dirty_pressure_focus(
    dirty_tree_pressure_focus: Mapping[str, Any] | None,
    *,
    limit: int,
) -> Dict[str, Any] | None:
    if not isinstance(dirty_tree_pressure_focus, Mapping):
        return None
    safe_limit = max(0, int(limit or 0))

    def _compact_blocking_session(row: Any) -> Dict[str, Any] | None:
        if not isinstance(row, Mapping):
            return None
        keep_keys = (
            "session_id",
            "actor",
            "phase_id",
            "dirty_path_count",
            "leased_until_max",
            "lease_state",
            "lease_seconds_remaining",
            "lease_expired",
            "paths_preview",
            "paths_omitted",
            "session_status_command",
            "safe_next_command",
            "freshness_state",
            "pass_state",
            "current_pass_line",
            "heartbeat_source",
            "heartbeat_gap",
            "recommended_action",
            "first_underlying_path",
            "first_underlying_owner_surface",
            "first_underlying_recommended_action",
        )
        stable_null_keys = {"lease_seconds_remaining", "lease_expired"}
        return {
            key: row.get(key)
            for key in keep_keys
            if key in stable_null_keys or row.get(key) not in (None, "", {}, [])
        }

    def _compact_clearance_summary(row: Any) -> Dict[str, Any] | None:
        if not isinstance(row, Mapping):
            return None
        return {
            "schema": "dirty_tree_checkpoint_clearance_summary_v0",
            "status": row.get("status"),
            "current_blocker": row.get("current_blocker"),
            "no_heartbeat_mode_safe": row.get("no_heartbeat_mode_safe"),
            "first_blocking_step": row.get("first_blocking_step"),
            "first_blocking_command": row.get("first_blocking_command"),
            "checkpoint_policy": row.get("checkpoint_policy"),
        }

    compact: Dict[str, Any] = {
        "schema": dirty_tree_pressure_focus.get("schema"),
        "projection_mode": "compact_first_contact",
        "status": dirty_tree_pressure_focus.get("status"),
        "checkpoint_status": dirty_tree_pressure_focus.get("checkpoint_status"),
        "checkpoint_authorized": dirty_tree_pressure_focus.get(
            "checkpoint_authorized"
        ),
        "checkpoint_guard": dirty_tree_pressure_focus.get("checkpoint_guard"),
        "dirty_total": dirty_tree_pressure_focus.get("dirty_total"),
        "dirty_path_class_counts": dict(
            dirty_tree_pressure_focus.get("dirty_path_class_counts") or {}
        ),
        "active_claim_dirty_path_count": dirty_tree_pressure_focus.get(
            "active_claim_dirty_path_count"
        ),
        "claim_collision_count": dirty_tree_pressure_focus.get(
            "claim_collision_count"
        ),
        "blocking_session_group_count": dirty_tree_pressure_focus.get(
            "blocking_session_group_count"
        ),
        "blocking_session_lease_summary": dirty_tree_pressure_focus.get(
            "blocking_session_lease_summary"
        ),
        "no_heartbeat_blocking_claim_summary": dirty_tree_pressure_focus.get(
            "no_heartbeat_blocking_claim_summary"
        ),
        "scoped_work_continuation_summary": dirty_tree_pressure_focus.get(
            "scoped_work_continuation_summary"
        ),
        "checkpoint_clearance_summary": _compact_clearance_summary(
            dirty_tree_pressure_focus.get("checkpoint_clearance_ladder")
        ),
        "first_action_kind": dirty_tree_pressure_focus.get("first_action_kind"),
        "first_action": dirty_tree_pressure_focus.get("first_action"),
        "first_action_command": dirty_tree_pressure_focus.get(
            "first_action_command"
        ),
        "first_action_ref": dirty_tree_pressure_focus.get("first_action_ref"),
        "promote_for_no_heartbeat": dirty_tree_pressure_focus.get(
            "promote_for_no_heartbeat"
        ),
        "recheck_command": dirty_tree_pressure_focus.get("recheck_command"),
    }

    compact["blocking_session"] = _compact_blocking_session(
        dirty_tree_pressure_focus.get("blocking_session")
    )
    raw_preview = [
        row
        for row in list(
            dirty_tree_pressure_focus.get("blocking_sessions_preview") or []
        )
        if isinstance(row, Mapping)
    ]
    preview = [
        row
        for row in (
            _compact_blocking_session(row) for row in raw_preview[:safe_limit]
        )
        if row
    ]
    compact["blocking_sessions_preview"] = preview
    compact["blocking_sessions_omitted"] = (
        int(dirty_tree_pressure_focus.get("blocking_sessions_omitted") or 0)
        + max(0, len(raw_preview) - len(preview))
    )

    omitted = [
        "agent_decision_summary",
        "after_active_claims_clear",
        "post_active_claim_settlement_summary",
        "checkpoint_clearance_ladder",
        "active_claim_underlying_dirty_summary",
        "blocking_session_coordination_summary",
    ]
    compact["omission_receipt"] = {
        "schema": "work_ledger_seed_speed_dirty_pressure_focus_omission_v0",
        "omitted": omitted,
        "reason": (
            "dirty_tree_pressure_focus is a first-contact seed-speed surface; "
            "bulky settlement diagnostics stay behind owner drilldowns."
        ),
        "preserved": [
            "first action",
            "checkpoint guard",
            "blocker counts",
            "first blocking session handle",
            "blocking lease summary",
            "scoped work continuation summary",
        ],
        "drilldowns": {
            "dirty_tree_pressure": _wl_command(
                "session-sweep", "--dry-run --dirty-tree-pressure"
            ),
            "runtime_full": _wl_command("session-status", "--full"),
            "claim_sessions": _wl_command(
                "session-claims",
                "--refresh --session-summary --limit 12 --cards-only",
            ),
        },
    }
    return compact


def build_seed_speed_status(
    overview: Mapping[str, Any],
    *,
    limit: int,
    prefer_non_heartbeat: bool = False,
    dirty_tree_pressure: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    heartbeat = (
        overview.get("heartbeat_participation")
        if isinstance(overview.get("heartbeat_participation"), Mapping)
        else {}
    )
    awareness_by_session = {
        str(card.get("session_id")): card
        for card in list(overview.get("awareness_cards") or [])
        if isinstance(card, Mapping) and card.get("session_id")
    }
    grouped: Dict[str, Dict[str, Any]] = {}
    for claim in list(overview.get("active_claims") or []):
        if not isinstance(claim, Mapping):
            continue
        session_id = str(claim.get("session_id") or "").strip()
        if not session_id:
            continue
        card = grouped.setdefault(
            session_id,
            {
                "session_id": session_id,
                "actor": claim.get("actor"),
                "phase_id": claim.get("phase_id"),
                "active_claim_count": 0,
                "path_claim_count": 0,
                "td_claim_count": 0,
                "work_item_claim_count": 0,
                "paths_preview": [],
                "td_ids_preview": [],
                "work_item_ids_preview": [],
                "lease_until_max": None,
            },
        )
        card["active_claim_count"] = int(card["active_claim_count"]) + 1
        scope_kind = str(claim.get("scope_kind") or "")
        path = str(claim.get("path") or "").strip()
        td_id = str(claim.get("td_id") or "").strip()
        work_item_id = str(claim.get("work_item_id") or "").strip()
        if scope_kind == "path" or path:
            card["path_claim_count"] = int(card["path_claim_count"]) + 1
            if path and path not in card["paths_preview"] and len(card["paths_preview"]) < 3:
                card["paths_preview"].append(path)
        if scope_kind == "td_id" or td_id:
            card["td_claim_count"] = int(card["td_claim_count"]) + 1
            if td_id and td_id not in card["td_ids_preview"] and len(card["td_ids_preview"]) < 3:
                card["td_ids_preview"].append(td_id)
        if scope_kind == "work_item_id" or work_item_id:
            card["work_item_claim_count"] = int(card["work_item_claim_count"]) + 1
            if (
                work_item_id
                and work_item_id not in card["work_item_ids_preview"]
                and len(card["work_item_ids_preview"]) < 3
            ):
                card["work_item_ids_preview"].append(work_item_id)
        leased_until = str(claim.get("leased_until") or "").strip()
        if leased_until and (not card["lease_until_max"] or leased_until > card["lease_until_max"]):
            card["lease_until_max"] = leased_until

    for session_id, card in grouped.items():
        awareness = awareness_by_session.get(session_id) or {}
        if not card.get("actor"):
            card["actor"] = awareness.get("actor")
        if not card.get("phase_id"):
            card["phase_id"] = awareness.get("phase_id")
        card["freshness_state"] = awareness.get("freshness_state")
        card["pass_state"] = awareness.get("pass_state")
        card["current_pass_line"] = awareness.get("current_pass_line")
        card["heartbeat_source"] = awareness.get("source")
        card["drilldown"] = _wl_command(
            "session-status",
            f"--session-id {_quote_cli(session_id)} --full",
        )

    seed_claim_sessions = sorted(
        grouped.values(),
        key=lambda card: (-int(card.get("active_claim_count") or 0), str(card.get("session_id") or "")),
    )
    heartbeat_gap_claim_sessions = [
        _seed_speed_heartbeat_gap_row(card)
        for card in seed_claim_sessions
        if str(card.get("heartbeat_source") or "") not in EXPLICIT_HEARTBEAT_SOURCES
    ]
    session_coordination = {
        str(card.get("session_id") or "").strip(): card
        for card in seed_claim_sessions
        if str(card.get("session_id") or "").strip()
    }
    heartbeat_gap_session_ids = {
        str(card.get("session_id") or "").strip()
        for card in heartbeat_gap_claim_sessions
        if str(card.get("session_id") or "").strip()
    }
    for card in seed_claim_sessions:
        session_id = str(card.get("session_id") or "").strip()
        card["session_coordination_packet"] = _seed_speed_session_coordination_packet(
            card,
            heartbeat_gap=session_id in heartbeat_gap_session_ids,
        )
    validated_uncommitted_closeout_sessions = [
        dict(row)
        for row in list(overview.get("validated_uncommitted_closeout_sessions") or [])
        if isinstance(row, Mapping)
    ]
    cas_retry_source_cards = [
        *seed_claim_sessions,
        *validated_uncommitted_closeout_sessions,
    ]
    unclaimed_touched_source = [
        row
        for row in list(contention.get("unclaimed_touched_sessions") or [])
        if isinstance(row, Mapping)
    ]
    unclaimed_touched_sessions = [
        _seed_speed_unclaimed_touched_row(
            row,
            awareness_by_session=awareness_by_session,
        )
        for row in unclaimed_touched_source
    ]
    claim_collision_rows = [
        row
        for row in list(contention.get("claim_collisions") or [])
        if isinstance(row, Mapping)
    ]
    claim_collision_actions = [
        _seed_speed_claim_collision_action_row(row)
        for row in claim_collision_rows
    ]
    claim_collision_cleanup_summary = _seed_speed_claim_collision_cleanup_summary(
        claim_collision_actions
    )
    claim_collision_count = len(claim_collision_rows)
    projected_unknown_count = int(heartbeat.get("projected_unknown_count") or 0)
    dirty_tree_pressure_focus_full = _seed_speed_dirty_pressure_focus(
        dirty_tree_pressure,
        session_coordination=session_coordination,
        heartbeat_gap_session_ids=heartbeat_gap_session_ids,
        observed_at=str(overview.get("generated_at") or "").strip() or None,
    )
    dirty_tree_pressure_action = _seed_speed_dirty_pressure_action(
        dirty_tree_pressure_focus_full
    )
    dirty_tree_pressure_focus = _seed_speed_compact_dirty_pressure_focus(
        dirty_tree_pressure_focus_full,
        limit=safe_limit,
    )
    cas_retry_handoff_rows = [
        row
        for row in (
            _seed_speed_cas_retry_handoff_row(card) for card in cas_retry_source_cards
        )
        if row is not None
    ]
    first_action_kind: str
    first_action_command: str | None = None
    first_action_ref: str | None = None
    if claim_collision_count:
        first_action_kind = "claim_collision"
        first_action = (
            "Resolve active claim collisions using claim_collision_cleanup_summary "
            "before starting or widening a seed."
        )
        first_action_command = str(
            (claim_collision_cleanup_summary or {}).get("first_safe_command")
            or (claim_collision_actions[0] if claim_collision_actions else {}).get(
                "safe_next_command"
            )
            or ""
        ).strip() or None
        first_action_ref = "claim_collision_cleanup_summary.first_safe_command"
    elif unclaimed_touched_sessions:
        first_unclaimed = unclaimed_touched_sessions[0]
        first_action_kind = "unclaimed_touched_owner_repair"
        first_action = (
            "Inspect the unclaimed touched session and have the owner or explicit "
            "coordinator claim the touched work before mutation."
        )
        first_action_command = (
            str(first_unclaimed.get("read_only_drilldown") or "").strip() or None
        )
        first_action_ref = "unclaimed_touched_sessions[0].read_only_drilldown"
    elif cas_retry_handoff_rows:
        first_action_kind = "cas_retry_landing_handoff"
        first_action = (
            "Inspect CAS retry exhausted handoff sessions before choosing new work; "
            "do not perform a third ref mutation from the same evidence root."
        )
        first_action_command = (
            str(cas_retry_handoff_rows[0].get("read_only_drilldown") or "").strip()
            or None
        )
        first_action_ref = "cas_retry_handoff_lens.rows[0].read_only_drilldown"
    elif heartbeat_gap_claim_sessions:
        first_action_kind = "heartbeat_gap"
        first_action = "Publish heartbeat for claim-owning seed sessions listed in heartbeat_gap_claim_sessions."
        first_action_command = str(
            heartbeat_gap_claim_sessions[0].get("heartbeat_command") or ""
        ).strip() or None
        first_action_ref = "heartbeat_gap_claim_sessions[0].heartbeat_command"
    elif seed_claim_sessions:
        first_action_kind = "choose_disjoint_write_lane"
        first_action = "Use the seed claim session cards to choose the disjoint write lane."
        first_action_command = _wl_command(
            "session-claims",
            "--refresh --session-summary --limit 12 --cards-only",
        )
        first_action_ref = "fast_paths.claim_session_summary"
    elif projected_unknown_count:
        first_action_kind = "projected_unknown_heartbeat"
        first_action = "Publish session-heartbeat for participating live seeds that can write."
        first_action_command = _wl_command(
            "session-heartbeat",
            "--session-id <id>",
            "--state inspecting",
            "--current-pass-line '<public current pass>'",
            "--last-pass-result-line '<public previous result>'",
            "--scope-ref <path-or-claim>",
        )
        first_action_ref = "fast_paths.heartbeat"
    else:
        no_claims_action = _seed_speed_no_active_claims_action()
        first_action_kind = str(no_claims_action.get("kind") or "no_active_claims")
        first_action = str(no_claims_action.get("action") or "")
        first_action_command = str(no_claims_action.get("command") or "").strip() or None
        first_action_ref = str(no_claims_action.get("ref") or "").strip() or None

    heartbeat_first_action: Dict[str, Any] | None = None

    def _deferred_heartbeat_action(
        *,
        deferred_by_no_heartbeat_mode: bool,
    ) -> Dict[str, Any]:
        read_only_command = None
        read_only_ref = None
        if heartbeat_gap_claim_sessions:
            read_only_command = (
                str(
                    heartbeat_gap_claim_sessions[0].get(
                        "read_only_alternative_command"
                    )
                    or ""
                ).strip()
                or None
            )
            read_only_ref = "heartbeat_gap_claim_sessions[0].read_only_alternative_command"
        if not read_only_command:
            read_only_command = (
                str(non_heartbeat_first_action.get("command") or "").strip() or None
            )
            read_only_ref = "non_heartbeat_first_action.command"
        action = {
            "kind": first_action_kind,
            "action": first_action,
            "command": read_only_command,
            "command_role": "read_only_alternative",
            "ref": read_only_ref,
            "deferred_heartbeat_command": first_action_command,
            "deferred_heartbeat_ref": first_action_ref,
            "write_command_suppressed": True,
        }
        if deferred_by_no_heartbeat_mode:
            action["deferred_by_no_heartbeat_mode"] = True
        else:
            action["deferred_by_authority_boundary"] = True
        return action

    if first_action_kind in {"heartbeat_gap", "projected_unknown_heartbeat"}:
        non_heartbeat_first_action = _seed_speed_choose_disjoint_lane_action(
            seed_claim_sessions,
            prefer_explicit_current=True,
        )
        non_heartbeat_first_action["same_as_first_action"] = False
        non_heartbeat_first_action["heartbeat_action_deferred"] = True
        non_heartbeat_first_action["why"] = (
            "Use when the operator or lane says not to publish heartbeat in this pass."
        )
    else:
        non_heartbeat_first_action = {
            "kind": first_action_kind,
            "action": first_action,
            "command": first_action_command,
            "ref": first_action_ref,
            "same_as_first_action": True,
            "heartbeat_action_deferred": False,
            "why": "The primary first action is already a non-heartbeat action.",
        }

    coordination_mode = "no_heartbeat" if prefer_non_heartbeat else "standard"
    first_action_source = "computed_first_action"
    if (
        not prefer_non_heartbeat
        and first_action_kind in {"heartbeat_gap", "projected_unknown_heartbeat"}
    ):
        heartbeat_first_action = _deferred_heartbeat_action(
            deferred_by_no_heartbeat_mode=False,
        )
        first_action_kind = str(
            non_heartbeat_first_action.get("kind") or first_action_kind
        )
        first_action = str(
            non_heartbeat_first_action.get("action") or first_action
        )
        first_action_command = (
            str(non_heartbeat_first_action.get("command") or "").strip() or None
        )
        first_action_ref = (
            str(non_heartbeat_first_action.get("ref") or "").strip() or None
        )
        non_heartbeat_first_action["same_as_first_action"] = True
        non_heartbeat_first_action["why"] = (
            "Promoted because default seed-speed guidance is read-only across "
            "session boundaries; heartbeat writes require explicit owner or "
            "lane authority."
        )
        first_action_source = "authority_safe_non_heartbeat_first_action"
    if (
        prefer_non_heartbeat
        and dirty_tree_pressure_action
        and first_action_kind != "claim_collision"
    ):
        if first_action_kind in {"heartbeat_gap", "projected_unknown_heartbeat"}:
            heartbeat_first_action = _deferred_heartbeat_action(
                deferred_by_no_heartbeat_mode=True,
            )
        first_action_kind = str(
            dirty_tree_pressure_action.get("kind") or first_action_kind
        )
        first_action = str(
            dirty_tree_pressure_action.get("action") or first_action
        )
        first_action_command = (
            str(dirty_tree_pressure_action.get("command") or "").strip() or None
        )
        first_action_ref = (
            str(dirty_tree_pressure_action.get("ref") or "").strip() or None
        )
        non_heartbeat_first_action = {
            **dirty_tree_pressure_action,
            "same_as_first_action": True,
            "heartbeat_action_deferred": heartbeat_first_action is not None,
            "why": (
                "Promoted because no-heartbeat mode was requested and dirty-tree "
                "pressure names the checkpoint-blocking claim session."
            ),
        }
        first_action_source = "dirty_tree_pressure_focus"
    elif prefer_non_heartbeat and first_action_kind in {
        "heartbeat_gap",
        "projected_unknown_heartbeat",
    }:
        heartbeat_first_action = _deferred_heartbeat_action(
            deferred_by_no_heartbeat_mode=True,
        )
        first_action_kind = str(
            non_heartbeat_first_action.get("kind") or first_action_kind
        )
        first_action = str(
            non_heartbeat_first_action.get("action") or first_action
        )
        first_action_command = (
            str(non_heartbeat_first_action.get("command") or "").strip() or None
        )
        first_action_ref = (
            str(non_heartbeat_first_action.get("ref") or "").strip() or None
        )
        non_heartbeat_first_action["same_as_first_action"] = True
        non_heartbeat_first_action["why"] = (
            "Promoted because no-heartbeat mode was requested for this pass."
        )
        first_action_source = "non_heartbeat_first_action"

    no_heartbeat_gap_summary = (
        _seed_speed_no_heartbeat_gap_summary(
            heartbeat_gap_claim_sessions,
            limit=safe_limit,
        )
        if prefer_non_heartbeat
        else None
    )
    generated_surface_claim_lens = _seed_speed_generated_surface_claim_lens(
        active_claims=[
            row
            for row in list(overview.get("active_claims") or [])
            if isinstance(row, Mapping)
        ],
        seed_claim_sessions=seed_claim_sessions,
        claim_collision_actions=claim_collision_actions,
    )
    cas_retry_handoff_lens = _seed_speed_cas_retry_handoff_lens(
        cas_retry_handoff_rows,
        limit=safe_limit,
    )
    concurrency_closure_state_lens = _seed_speed_concurrency_closure_state_lens(
        generated_surface_claim_lens=generated_surface_claim_lens,
        dirty_tree_pressure_focus=dirty_tree_pressure_focus,
        counts=counts,
        first_action_kind=first_action_kind,
        first_action=first_action,
        first_action_command=first_action_command,
    )

    return {
        "schema": "work_ledger_seed_speed_status_v1",
        "generated_at": overview.get("generated_at"),
        "mode": "seed_speed_status",
        "coordination_mode": coordination_mode,
        "counts": {
            "effective_active_sessions": counts.get("effective_active_sessions"),
            "active_claims": counts.get("active_claims"),
            "active_claim_session_count": len(seed_claim_sessions),
            "claim_session_heartbeat_gap_count": len(heartbeat_gap_claim_sessions),
            "cas_retry_handoff_count": len(cas_retry_handoff_rows),
            "explicit_current_pass_sessions": heartbeat.get("explicit_current_pass_count", 0),
            "projected_unknown_sessions": projected_unknown_count,
            "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
            "claim_collisions": claim_collision_count,
            "unclaimed_touched_sessions": counts.get("unclaimed_touched_sessions"),
            "validated_uncommitted_closeout_sessions": len(
                validated_uncommitted_closeout_sessions
            ),
        },
        "count_semantics": coordination_count_semantics(counts, heartbeat=heartbeat),
        "risk": {
            "risk_level": contention.get("risk_level"),
            "signals": list(contention.get("signals") or []),
        },
        "generated_surface_claim_lens": generated_surface_claim_lens,
        "cas_retry_handoff_lens": cas_retry_handoff_lens,
        "concurrency_closure_state_lens": concurrency_closure_state_lens,
        "first_action": first_action,
        "first_action_kind": first_action_kind,
        "first_action_command": first_action_command,
        "first_action_ref": first_action_ref,
        "first_action_source": first_action_source,
        "heartbeat_first_action": heartbeat_first_action,
        "non_heartbeat_first_action": non_heartbeat_first_action,
        "no_heartbeat_gap_summary": no_heartbeat_gap_summary,
        "dirty_tree_pressure_focus": dirty_tree_pressure_focus,
        "claim_collision_cleanup_summary": claim_collision_cleanup_summary,
        "claim_collision_actions": claim_collision_actions[:safe_limit],
        "claim_collision_actions_omitted": max(0, len(claim_collision_actions) - safe_limit),
        "unclaimed_touched_sessions": unclaimed_touched_sessions[:safe_limit],
        "unclaimed_touched_sessions_omitted": max(
            0,
            max(
                len(unclaimed_touched_sessions),
                int(counts.get("unclaimed_touched_sessions") or 0),
            )
            - safe_limit,
        ),
        "validated_uncommitted_closeout_sessions": (
            validated_uncommitted_closeout_sessions[:safe_limit]
        ),
        "validated_uncommitted_closeout_sessions_omitted": max(
            0, len(validated_uncommitted_closeout_sessions) - safe_limit
        ),
        "seed_claim_sessions": seed_claim_sessions[:safe_limit],
        "seed_claim_sessions_omitted": max(0, len(seed_claim_sessions) - safe_limit),
        "heartbeat_gap_claim_sessions": heartbeat_gap_claim_sessions[:safe_limit],
        "heartbeat_gap_claim_sessions_omitted": max(
            0, len(heartbeat_gap_claim_sessions) - safe_limit
        ),
        "fast_paths": {
            "claims": _wl_command("session-claims", "--refresh --limit 50 --cards-only"),
            "claim_session_summary": _wl_command(
                "session-claims",
                "--refresh --session-summary --limit 12 --cards-only",
            ),
            "overview_cards": _wl_command(
                "session-status",
                f"--overview --cards-only --limit {safe_limit}",
            ),
            "unclaimed_touched_overview": _wl_command(
                "session-status",
                f"--overview --limit {safe_limit}",
            ),
            "seed_speed_no_heartbeat": _wl_command(
                "session-status",
                f"--seed-speed --no-heartbeat --limit {safe_limit}",
            ),
            "duplicate_claim_dedupe": _wl_command(
                "session-sweep",
                "--dedupe-duplicate-claims",
            ),
            "duplicate_claim_dedupe_dry_run": _wl_command(
                "session-sweep",
                "--dry-run --dedupe-duplicate-claims",
            ),
            "dirty_tree_pressure": _wl_command(
                "session-sweep",
                "--dry-run --dirty-tree-pressure",
            ),
            "heartbeat": _wl_command(
                "session-heartbeat",
                "--session-id <id>",
                "--state inspecting",
                "--current-pass-line '<public current pass>'",
                "--last-pass-result-line '<public previous result>'",
                "--scope-ref <path-or-claim>",
            ),
            "full_runtime": _wl_command("session-status", "--full"),
        },
        "omission_receipt": {
            "omitted": [
                "monitor_cards",
                "awareness_cards",
                "repair_rows",
                "recommended_actions",
                "full active claim rows",
                "full unclaimed touched session rows",
                "full per-session coordination command maps",
                "per-row coordination inbox/message/send commands",
                "per-row coordination omission receipts",
                "session workflow message bus detail",
                "full session rows",
            ],
            "reason": "seed-speed status is the first-contact active-seed lane; it keeps only claim-session, heartbeat, and contention scalars.",
            "drilldown": _wl_command(
                "session-status",
                f"--overview --cards-only --limit {safe_limit}",
            ),
        },
    }


def _compact_awareness_card_for_cards_only(row: Mapping[str, Any]) -> Dict[str, Any]:
    card = dict(row)
    card.pop("claim_refs", None)
    repair_rows = [
        dict(item) for item in list(row.get("repair_rows") or []) if isinstance(item, Mapping)
    ]
    if repair_rows:
        card.pop("repair_rows", None)
        kinds = Counter(str(item.get("kind") or "unknown") for item in repair_rows)
        card["repair_summary"] = {
            "row_count": len(repair_rows),
            "kinds": dict(sorted(kinds.items())),
            "top_action": repair_rows[0].get("safe_next_command"),
            "top_message": repair_rows[0].get("message"),
        }
        if row.get("drilldown"):
            card["repair_summary"]["drilldown"] = row.get("drilldown")
    return card


def _compact_monitor_card_for_cards_only(row: Mapping[str, Any]) -> Dict[str, Any]:
    card = dict(row)
    repair_rows = [
        dict(item) for item in list(row.get("repair_rows") or []) if isinstance(item, Mapping)
    ]
    if repair_rows:
        card.pop("repair_rows", None)
        kinds = Counter(str(item.get("kind") or "unknown") for item in repair_rows)
        card["repair_summary"] = {
            "row_count": len(repair_rows),
            "kinds": dict(sorted(kinds.items())),
            "top_action": repair_rows[0].get("safe_next_command"),
            "top_message": repair_rows[0].get("message"),
        }
        if row.get("drilldown"):
            card["repair_summary"]["drilldown"] = row.get("drilldown")
    return card


def _cohort_speed_summary_for_cards_only(
    overview: Mapping[str, Any],
    *,
    awareness_cards: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    heartbeat = (
        overview.get("heartbeat_participation")
        if isinstance(overview.get("heartbeat_participation"), Mapping)
        else {}
    )
    active_claim_session_ids = sorted(
        {
            str(card.get("session_id"))
            for card in awareness_cards
            if card.get("session_id")
            and (
                card.get("claim_refs")
                or (
                    isinstance(card.get("claim_summary"), Mapping)
                    and int(card["claim_summary"].get("claim_count") or 0) > 0
                )
            )
        }
    )
    return {
        "effective_active_sessions": counts.get(
            "effective_active_sessions", heartbeat.get("effective_active_sessions")
        ),
        "active_claims": counts.get("active_claims"),
        "active_claim_session_count": len(active_claim_session_ids),
        "active_claim_session_ids": active_claim_session_ids[:8],
        "explicit_current_pass_sessions": heartbeat.get("explicit_current_pass_count", 0),
        "projected_unknown_sessions": heartbeat.get("projected_unknown_count", 0),
        "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        "first_action": (
            "Use session-level claim summaries for write-active lanes, then publish "
            "session-heartbeat for participating live seeds that can write."
        ),
        "claims_fast_path": _wl_command(
            "session-claims",
            "--refresh --session-summary --limit 12 --cards-only",
        ),
        "heartbeat_fast_path": _wl_command(
            "session-heartbeat",
            "--session-id <id>",
            "--state inspecting",
            "--current-pass-line '<public current pass>'",
            "--last-pass-result-line '<public previous result>'",
            "--scope-ref <path-or-claim>",
        ),
    }


def build_session_cohort_cards_only_overview(
    overview: Mapping[str, Any],
    *,
    limit: int,
) -> Dict[str, Any]:
    """Build the default cards-only cohort packet without session row arrays."""
    safe_limit = max(0, int(limit or 0))
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    awareness_cards = [
        _compact_awareness_card_for_cards_only(row)
        for row in list(overview.get("awareness_cards") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    repair_rows = [
        dict(row)
        for row in list(overview.get("repair_rows") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    return {
        "schema": overview.get("schema"),
        "generated_at": overview.get("generated_at"),
        "mode": "cards_only_overview",
        "orphan_after_seconds": overview.get("orphan_after_seconds"),
        "counts": overview.get("counts") or {},
        "count_semantics": coordination_count_semantics(
            overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {},
            heartbeat=overview.get("heartbeat_participation")
            if isinstance(overview.get("heartbeat_participation"), Mapping)
            else {},
        ),
        "monitor_cards": [
            _compact_monitor_card_for_cards_only(row)
            for row in list(overview.get("monitor_cards") or [])
            if isinstance(row, Mapping)
        ],
        "awareness_cards": awareness_cards,
        "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
        "repair_rows": repair_rows,
        "cohort_speed_summary": _cohort_speed_summary_for_cards_only(
            overview,
            awareness_cards=awareness_cards,
        ),
        "recommended_landing_lane": overview.get("recommended_landing_lane"),
        "contention": {
            "risk_level": contention.get("risk_level"),
            "signals": list(contention.get("signals") or []),
            "td_id_collision_count": len(contention.get("td_id_collisions") or []),
            "claim_collision_count": len(contention.get("claim_collisions") or []),
            "unknown_scope_active_session_count": len(contention.get("unknown_scope_active_sessions") or []),
            "unclaimed_touched_session_count": len(contention.get("unclaimed_touched_sessions") or []),
            "orphaned_active_session_count": len(contention.get("orphaned_active_sessions") or []),
        },
        "recommended_actions": list(overview.get("recommended_actions") or [])[:safe_limit],
        "drilldown_commands": {
            "seed_speed": _wl_command("session-status", "--seed-speed --limit 12"),
            "overview_cards": _wl_command(
                "session-status",
                f"--overview --cards-only --limit {safe_limit}",
            ),
            "full_runtime": _wl_command("session-status", "--full"),
        },
        "omission_receipt": {
            "omitted": [
                "active_session_rows",
                "effective_active_session_rows",
                "orphaned_active_session_rows",
                "monitor_card_repair_rows",
                "per_awareness_card_repair_rows",
                "per_awareness_card_claim_refs",
            ],
            "reason": (
                "cards-only overview preserves monitor cards, awareness cards, "
                "repair summaries, and counts for routine status checks; row "
                "evidence remains behind drilldowns."
            ),
            "drilldown": _wl_command(
                "session-status",
                f"--overview --limit {safe_limit}",
            ),
        },
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


def _work_ledger_index_target_only_command(path: str) -> str:
    posix = PurePosixPath(path)
    parts = posix.parts
    if len(parts) < 4 or parts[0] != "codex" or parts[1] != "ledger":
        return "./repo-python tools/meta/factory/work_ledger.py project --check --all"
    phase_id = parts[2]
    path_name = posix.name
    family_id = phase_id.split("_", 1)[0]
    prefix = "work_ledger_index."
    if path_name.startswith(prefix) and path_name.endswith(".json"):
        family_id = path_name[len(prefix) : -len(".json")] or family_id
    return (
        "./repo-python tools/meta/factory/work_ledger.py project "
        f"--phase-id {phase_id} --family-id {family_id} --check --target-only"
    )


PHASE_PIPELINE_RUNTIME_FILENAMES = {
    "continuation_packet.json",
    "pipeline_attention.json",
    "pipeline_attention.md",
    "pipeline_resume.json",
    "pipeline_resume.md",
    "pipeline_state.json",
    "raw_seed_digest.json",
    "system_view.json",
    "task_backlog.json",
}
ROOT_AUTONOMOUS_SEED_PREFIX = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, "
    "and Fresh Execution Spine/autonomous_seed."
)
ROOT_AUTONOMOUS_SEED_JSON = (
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, "
    "and Fresh Execution Spine/autonomous_seed.json"
)


def _is_phase_pipeline_runtime_path(path: str) -> bool:
    token = str(path or "").strip("/")
    if not token.startswith("obsidian/okay lets do this/"):
        return False
    name = PurePosixPath(token).name
    return (
        name in PHASE_PIPELINE_RUNTIME_FILENAMES
        or "/.pipeline_recovery/" in token
        or "/cycle_" in token
    )


def _dirty_path_owner_hint(path: str) -> Dict[str, str]:
    path_name = PurePosixPath(path).name
    if path in {
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "CODEX.md",
        "codex/doctrine/agent_bootstrap_injection_strip.json",
        "codex/doctrine/agent_bootstrap_live.json",
    }:
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "agent_bootstrap_projection",
            "recommended_action": "./repo-python tools/meta/factory/check_agent_bootstrap_projection.py",
        }
    if path.startswith("state/task_ledger/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "task_ledger_projection",
            "recommended_action": "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check",
        }
    if path.startswith("codex/ledger/"):
        if path_name == "work_ledger.jsonl":
            return {
                "class": "generated_owner_dirty",
                "owner_surface": "work_ledger_source_event_log",
                "recommended_action": (
                    "./repo-python tools/meta/control/generated_state_drainer.py "
                    "settlement-plan --owner-id work_ledger_index_projection"
                ),
            }
        if path_name.startswith("work_ledger_index") and path_name.endswith(".json"):
            return {
                "class": "generated_owner_dirty",
                "owner_surface": "work_ledger_index_projection",
                "recommended_action": _work_ledger_index_target_only_command(path),
            }
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "work_ledger_ledger_state",
            "recommended_action": (
                "./repo-python tools/meta/control/generated_state_drainer.py "
                "settlement-plan --owner-id work_ledger_index_projection"
            ),
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
    if path == "state/observability/render_load_index.json":
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "station_render_load_index_projection",
            "recommended_action": "./repo-python -m tools.meta.observability.station_render timings --limit 20",
        }
    if path.startswith("state/observability/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "observability_runtime_state",
            "recommended_action": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
        }
    if path.startswith(ROOT_AUTONOMOUS_SEED_PREFIX):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "autonomous_seed_state",
            "recommended_action": (
                "./repo-python kernel.py --validate-seed-continuity "
                f"{shlex.quote(ROOT_AUTONOMOUS_SEED_JSON)}"
            ),
        }
    if path.startswith("annexes/") and path_name in {
        "annex_sync_digest.json",
        "annex_sync_digest.md",
        "annex_sync_digest_run_state.json",
    }:
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "annex_sync_digest_projection",
            "recommended_action": "./repo-python annex_import.py digest --run --quiet --stale-days 7 --limit 8",
        }
    if _is_phase_pipeline_runtime_path(path):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "phase_pipeline_runtime_state",
            "recommended_action": "./repo-python tools/meta/control/phase_convergence_doctor.py --compact",
        }
    if path.startswith("microcosm-substrate/receipts/runtime_shell/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "microcosm_runtime_receipt_state",
            "recommended_action": (
                "cd microcosm-substrate && "
                "PYTHONPATH=src .venv/bin/python -m microcosm_core.runtime_shell --help"
            ),
        }
    if path.startswith("receipts/"):
        return {
            "class": "generated_owner_dirty",
            "owner_surface": "receipt_artifact_state",
            "recommended_action": "./repo-python tools/meta/control/git_state_snapshot.py --diff-review --compact",
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
            underlying_owner_hint = _dirty_path_owner_hint(path)
            row = {
                "path": path,
                "class": "active_claim_dirty",
                "owner_surface": "active_work_ledger_claim",
                "recommended_action": "wait_for_claim_release_or_finalize_session_before_sweeping",
                "underlying_dirty_class": underlying_owner_hint.get("class"),
                "underlying_owner_surface": underlying_owner_hint.get("owner_surface"),
                "underlying_recommended_action": underlying_owner_hint.get(
                    "recommended_action"
                ),
                "active_claims": matching_claims[:3],
            }
        else:
            row = {"path": path, **_dirty_path_owner_hint(path)}
        counts[row["class"]] = counts.get(row["class"], 0) + 1
        if len(rows) < max(0, limit):
            rows.append(row)
    return rows, counts


def _dirty_path_class_preview(
    dirty_rows: Sequence[Mapping[str, Any]],
    *,
    class_id: str,
    total_count: int,
    limit: int,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    class_rows = [
        row
        for row in dirty_rows
        if row.get("class") == class_id and row.get("path")
    ]
    paths = [str(row.get("path") or "") for row in class_rows]
    first_path = paths[0] if paths else None
    first_row = class_rows[0] if class_rows else {}
    owner_surfaces_preview: List[str] = []
    for row in class_rows[:safe_limit]:
        owner_surface = str(row.get("owner_surface") or "").strip()
        if owner_surface and owner_surface not in owner_surfaces_preview:
            owner_surfaces_preview.append(owner_surface)
    return {
        "schema": "dirty_tree_path_class_preview_v0",
        "class": class_id,
        "path_count": int(total_count or 0),
        "paths_preview": paths[:safe_limit],
        "paths_omitted": max(0, int(total_count or 0) - len(paths[:safe_limit])),
        "first_path": first_path,
        "first_path_owner_surface": (
            str(first_row.get("owner_surface") or "").strip() or None
        ),
        "first_path_recommended_action": (
            str(first_row.get("recommended_action") or "").strip() or None
        ),
        "owner_surfaces_preview": owner_surfaces_preview,
        "first_path_preflight_command": (
            _mission_command(
                f"--owned-path {_quote_cli(first_path)}",
                "--fail-on-status blocked",
            )
            if first_path
            else None
        ),
    }


def _dirty_path_class_preview_for_pressure(
    dirty_paths: Sequence[str],
    *,
    active_claims: List[Dict[str, Any]],
    class_id: str,
    total_count: int,
    limit: int,
) -> Dict[str, Any]:
    """Build a class preview from the full dirty set, not the compact row slice."""

    safe_limit = max(0, int(limit or 0))
    rows: List[Dict[str, Any]] = []
    minimum_rows = max(1, safe_limit)
    for path in sorted({_normalize_dirty_path(path) for path in dirty_paths if path}):
        row = _dirty_path_pressure_row(path, active_claims)
        if row.get("class") != class_id:
            continue
        rows.append(row)
        if len(rows) >= minimum_rows:
            break
    return _dirty_path_class_preview(
        rows,
        class_id=class_id,
        total_count=total_count,
        limit=limit,
    )


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


def _active_claim_dirty_session_groups(
    dirty_paths: List[str],
    *,
    active_claims: List[Dict[str, Any]],
    limit: int,
    path_limit: int = 6,
) -> Dict[str, Any]:
    groups: Dict[str, Dict[str, Any]] = {}
    for path in sorted({_normalize_dirty_path(path) for path in dirty_paths if path}):
        matching_claims = [
            claim
            for claim in active_claims
            if _claim_covers_dirty_path(claim, path)
        ]
        for claim in matching_claims:
            session_id = str(claim.get("session_id") or "unknown_session")
            group = groups.setdefault(
                session_id,
                {
                    "session_id": session_id,
                    "actor": claim.get("actor"),
                    "phase_id": claim.get("phase_id"),
                    "dirty_path_count": 0,
                    "_paths": set(),
                    "_claim_ids": set(),
                    "leased_until_max": None,
                    "recommended_action": "owner_session_lands_or_releases_claim_then_replan",
                    "session_status_command": (
                        "./repo-python tools/meta/factory/work_ledger.py "
                        f"session-status --session-id {shlex.quote(session_id)} --full"
                    ),
                    "_underlying_class_counts": {},
                    "_underlying_owner_surfaces": [],
                    "_first_underlying_path": None,
                    "_first_underlying_owner_surface": None,
                    "_first_underlying_recommended_action": None,
                },
            )
            group["safe_next_command"] = group["session_status_command"]
            paths = group["_paths"]
            if isinstance(paths, set) and path not in paths:
                paths.add(path)
                group["dirty_path_count"] = int(group.get("dirty_path_count") or 0) + 1
                underlying_owner_hint = _dirty_path_owner_hint(path)
                underlying_class = str(underlying_owner_hint.get("class") or "").strip()
                if underlying_class:
                    class_counts = group.get("_underlying_class_counts")
                    if isinstance(class_counts, dict):
                        class_counts[underlying_class] = (
                            int(class_counts.get(underlying_class) or 0) + 1
                        )
                underlying_owner_surface = str(
                    underlying_owner_hint.get("owner_surface") or ""
                ).strip()
                owner_surfaces = group.get("_underlying_owner_surfaces")
                if (
                    isinstance(owner_surfaces, list)
                    and underlying_owner_surface
                    and underlying_owner_surface not in owner_surfaces
                ):
                    owner_surfaces.append(underlying_owner_surface)
                first_underlying_path = group.get("_first_underlying_path")
                if not first_underlying_path or path < str(first_underlying_path):
                    group["_first_underlying_path"] = path
                    group["_first_underlying_owner_surface"] = (
                        underlying_owner_surface or None
                    )
                    group["_first_underlying_recommended_action"] = (
                        str(underlying_owner_hint.get("recommended_action") or "").strip()
                        or None
                    )
            claim_ids = group["_claim_ids"]
            claim_id = str(claim.get("claim_id") or "")
            if isinstance(claim_ids, set) and claim_id:
                claim_ids.add(claim_id)
            leased_until = str(claim.get("leased_until") or "")
            if leased_until and (
                not group.get("leased_until_max")
                or leased_until > str(group.get("leased_until_max") or "")
            ):
                group["leased_until_max"] = leased_until

    sorted_groups = sorted(
        groups.values(),
        key=lambda row: (-int(row.get("dirty_path_count") or 0), str(row.get("session_id") or "")),
    )
    rows: List[Dict[str, Any]] = []
    for group in sorted_groups[: max(0, limit)]:
        paths = sorted(str(path) for path in group.pop("_paths", set()))
        claim_ids = sorted(str(claim_id) for claim_id in group.pop("_claim_ids", set()))
        underlying_class_counts = dict(group.pop("_underlying_class_counts", {}))
        underlying_owner_surfaces = list(group.pop("_underlying_owner_surfaces", []))
        first_underlying_path = group.pop("_first_underlying_path", None)
        first_underlying_owner_surface = group.pop(
            "_first_underlying_owner_surface", None
        )
        first_underlying_recommended_action = group.pop(
            "_first_underlying_recommended_action", None
        )
        rows.append(
            {
                **group,
                "paths_preview": paths[: max(0, path_limit)],
                "paths_omitted": max(0, len(paths) - max(0, path_limit)),
                "claim_ids_preview": claim_ids[: max(0, path_limit)],
                "claim_ids_omitted": max(0, len(claim_ids) - max(0, path_limit)),
                "underlying_dirty_path_class_counts": underlying_class_counts,
                "underlying_owner_surfaces_preview": underlying_owner_surfaces[
                    : max(0, path_limit)
                ],
                "underlying_owner_surfaces_omitted": max(
                    0, len(underlying_owner_surfaces) - max(0, path_limit)
                ),
                "first_underlying_path": first_underlying_path,
                "first_underlying_owner_surface": first_underlying_owner_surface,
                "first_underlying_recommended_action": (
                    first_underlying_recommended_action
                ),
            }
        )
    return {
        "schema": "dirty_tree_active_claim_session_groups_v0",
        "group_count": len(sorted_groups),
        "groups_omitted": max(0, len(sorted_groups) - len(rows)),
        "groups": rows,
    }


def _first_active_claim_dirty_group_command(
    active_claim_session_groups: Mapping[str, Any],
) -> Optional[str]:
    groups = active_claim_session_groups.get("groups")
    if not isinstance(groups, list):
        return None
    for group in groups:
        if not isinstance(group, Mapping):
            continue
        command = str(
            group.get("safe_next_command")
            or group.get("session_status_command")
            or ""
        ).strip()
        if command:
            return command
    return None


def _dirty_tree_scoped_work_unblock(
    *,
    dirty_total: int,
    active_claim_dirty_count: int,
    generated_owner_dirty_count: int,
    unclaimed_source_dirty_count: int,
    mainline_checkpoint_available: bool,
    rescue_repeat_policy: Mapping[str, Any],
) -> Dict[str, Any]:
    blocked_lanes: List[str] = []
    if dirty_total:
        blocked_lanes.append("clean_global_closeout")
    if active_claim_dirty_count:
        blocked_lanes.append("broad_mainline_checkpoint")
    if generated_owner_dirty_count or unclaimed_source_dirty_count:
        blocked_lanes.append("blind_cleanup_or_revert")
    if not mainline_checkpoint_available:
        blocked_lanes.append("operator_authorized_broad_checkpoint_until_guard_available")

    open_lanes = [
        "claim_owned_paths",
        "mission_transaction_preflight_for_owned_paths",
        "private_index_scoped_commit",
    ]
    if generated_owner_dirty_count:
        open_lanes.append("generated_owner_settlement")
    if unclaimed_source_dirty_count:
        if rescue_repeat_policy.get("repeat_rescue_now") is False:
            open_lanes.append("owner_classify_then_rescue_when_stable")
        else:
            open_lanes.append("rescue_ref_then_owner_classify")

    return {
        "schema": "dirty_tree_scoped_work_unblock_v0",
        "status": "scoped_work_open" if dirty_total else "clean",
        "one_line_rule": (
            "Ambient dirty paths block clean closeout and broad accidental staging, "
            "not validated owned-path work."
        ),
        "open_lanes": open_lanes,
        "blocked_lanes": blocked_lanes,
        "counts": {
            "dirty_total": dirty_total,
            "active_claim_dirty": active_claim_dirty_count,
            "generated_owner_dirty": generated_owner_dirty_count,
            "unclaimed_source_dirty": unclaimed_source_dirty_count,
        },
        "commands": {
            "claim_owned_paths": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-slug <slug> --path <owned-path> --require-exclusive"
            ),
            "mission_preflight_owned_path": (
                "./repo-python tools/meta/control/mission_transaction_preflight.py "
                "--subject-id <id> --owned-path <path> --fail-on-status blocked"
            ),
            "scoped_commit": (
                "./repo-python tools/meta/control/scoped_commit.py full-paths "
                "--path <owned-path> --expected-parent $(git rev-parse HEAD) "
                "--message \"<scope>: <what landed>\""
            ),
        },
    }


def _dirty_tree_unclaimed_checkpoint(
    *,
    bankruptcy_authorized: bool,
    dirty_scan_status: str,
    dirty_class_counts: Mapping[str, int],
    active_claim_dirty_count: int,
    generated_owner_dirty: Mapping[str, Any],
    unclaimed_source_dirty: Mapping[str, Any],
    command: str,
) -> Dict[str, Any]:
    included_counts: Dict[str, int] = {}
    for class_id in ("generated_owner_dirty", "unclaimed_source_dirty"):
        count = int(dirty_class_counts.get(class_id) or 0)
        if count:
            included_counts[class_id] = count
    included_count = sum(included_counts.values())
    scan_available = dirty_scan_status in ("git_status_porcelain_v1_z", "provided")
    available = bool(bankruptcy_authorized) and scan_available and included_count > 0

    if not bankruptcy_authorized:
        status = "not_authorized"
        blocked_by = ["operator_bankruptcy_authorization_missing"]
    elif not scan_available:
        status = "blocked"
        blocked_by = ["dirty_path_scan_unavailable"]
    elif included_count <= 0:
        status = "blocked"
        blocked_by = ["no_unclaimed_dirty_paths"]
    else:
        status = "available"
        blocked_by = []

    packet: Dict[str, Any] = {
        "schema": "dirty_tree_unclaimed_checkpoint_v0",
        "authorized": bool(bankruptcy_authorized),
        "status": status,
        "command": command,
        "scope": "non_active_claim_dirty_paths",
        "included_dirty_path_count": included_count,
        "included_dirty_path_classes": included_counts,
        "excluded_active_claim_dirty_path_count": int(active_claim_dirty_count or 0),
        "blocked_by": blocked_by,
        "path_selection_policy": (
            "Use Work Ledger dirty-path classification to include generated-owner "
            "and unclaimed-source dirty paths while excluding any dirty path covered "
            "by an active path claim."
        ),
        "requires_dirty_path_scan": True,
        "requires_operator_bankruptcy_authorization": True,
    }
    if included_counts.get("generated_owner_dirty"):
        packet["included_generated_owner_dirty"] = dict(generated_owner_dirty)
    if included_counts.get("unclaimed_source_dirty"):
        packet["included_unclaimed_source_dirty"] = dict(unclaimed_source_dirty)
    if active_claim_dirty_count:
        packet["active_claim_boundary"] = (
            "Active claimed dirty paths are excluded, not swept; owner sessions "
            "must land or release those paths separately."
        )
    if available and active_claim_dirty_count:
        packet["coordination_warning"] = (
            "This clears only unclaimed/non-actively-claimed paths. Re-run dirty-tree "
            "pressure afterward; active claimed paths remain dirty by design."
        )
    return packet


def _dirty_tree_after_active_claims_clear_preview(
    *,
    bankruptcy_authorized: bool,
    dirty_class_counts: Mapping[str, int],
    generated_owner_dirty: Mapping[str, Any],
    unclaimed_source_dirty: Mapping[str, Any],
    recheck_command: str,
) -> Dict[str, Any]:
    remaining_counts: Dict[str, int] = {}
    for class_id in ("generated_owner_dirty", "unclaimed_source_dirty"):
        count = int(dirty_class_counts.get(class_id) or 0)
        if count:
            remaining_counts[class_id] = count

    first_owner_action: Optional[Dict[str, Any]] = None
    if remaining_counts.get("generated_owner_dirty"):
        first_owner_action = {
            "kind": "settle_generated_owner_dirty",
            "path_class": "generated_owner_dirty",
            "first_path": generated_owner_dirty.get("first_path"),
            "first_path_owner_surface": generated_owner_dirty.get(
                "first_path_owner_surface"
            ),
            "first_path_recommended_action": generated_owner_dirty.get(
                "first_path_recommended_action"
            ),
            "first_path_preflight_command": generated_owner_dirty.get(
                "first_path_preflight_command"
            ),
            "owner_surfaces_preview": list(
                generated_owner_dirty.get("owner_surfaces_preview") or []
            ),
            "why": (
                "Generated or ledger state remains after claimed paths clear; "
                "validate with the owner tool before landing it outside the "
                "operator-authorized bankruptcy lane."
            ),
        }
    elif remaining_counts.get("unclaimed_source_dirty"):
        first_owner_action = {
            "kind": "claim_or_rescue_unclaimed_source_dirty",
            "path_class": "unclaimed_source_dirty",
            "first_path": unclaimed_source_dirty.get("first_path"),
            "first_path_owner_surface": unclaimed_source_dirty.get(
                "first_path_owner_surface"
            ),
            "first_path_recommended_action": unclaimed_source_dirty.get(
                "first_path_recommended_action"
            ),
            "first_path_preflight_command": unclaimed_source_dirty.get(
                "first_path_preflight_command"
            ),
            "owner_surfaces_preview": list(
                unclaimed_source_dirty.get("owner_surfaces_preview") or []
            ),
            "why": (
                "Source-looking dirt remains without a live claim; preserve it, "
                "claim an owner, validate, then land exact pathspecs."
            ),
        }

    preview: Dict[str, Any] = {
        "schema": "dirty_tree_after_active_claims_clear_preview_v0",
        "status": "recheck_required_before_checkpoint",
        "operator_authorized": bool(bankruptcy_authorized),
        "remaining_dirty_path_classes": remaining_counts,
        "remaining_classes_checkpoint_policy": (
            "After active claimed paths clear, rerun the pressure card. If the "
            "operator-authorized checkpoint guard becomes available, the broad "
            "checkpoint may include the remaining classes inside the "
            "operator-authorized bankruptcy lane; otherwise settle them by "
            "owner route."
        ),
        "checkpoint_guard": "operator_authorized_mainline_checkpoint.status == available",
        "recheck_command": recheck_command,
        "first_owner_settlement_action": first_owner_action,
    }
    if remaining_counts.get("generated_owner_dirty"):
        preview["included_generated_owner_dirty"] = dict(generated_owner_dirty)
    if remaining_counts.get("unclaimed_source_dirty"):
        preview["included_unclaimed_source_dirty"] = dict(unclaimed_source_dirty)
    return preview


def _dirty_tree_containment_plan(
    *,
    dirty_total: int,
    active_claim_dirty_count: int,
    generated_owner_dirty_count: int,
    unclaimed_source_dirty_count: int,
    mainline_checkpoint_available: bool,
    unclaimed_checkpoint_available: bool,
    rescue_coverage: Mapping[str, Any],
    rescue_repeat_policy: Mapping[str, Any],
    active_claim_session_groups: Mapping[str, Any],
    broad_checkpoint_command: str,
    unclaimed_checkpoint_command: str,
    rescue_ref_command: str,
) -> Dict[str, Any]:
    steps: List[Dict[str, Any]] = []
    active_claim_blocker_command = (
        _first_active_claim_dirty_group_command(active_claim_session_groups)
        or "wait_for_claim_release_or_finalize_session_before_sweeping"
    )
    rescue_status = str(rescue_coverage.get("status") or "unknown")
    if dirty_total and rescue_status != "fresh":
        if rescue_repeat_policy.get("repeat_rescue_now"):
            steps.append(
                {
                    "step_id": "preserve_current_dirty_tree_snapshot",
                    "status": "recommended",
                    "why": "current dirty tree is not fully covered by the latest rescue ref",
                    "preview_command": rescue_ref_command,
                    "write_command": rescue_ref_command.replace(" --dry-run", ""),
                }
            )
        else:
            steps.append(
                {
                    "step_id": "defer_repeated_rescue_until_movement_quiets",
                    "status": "deferred",
                    "why": (
                        rescue_repeat_policy.get("reason")
                        or "rescue coverage indicates active dirty-tree movement"
                    ),
                    "next_safe_action": rescue_repeat_policy.get("next_safe_action"),
                    "quiet_window": rescue_repeat_policy.get("quiet_window"),
                }
            )
    if active_claim_dirty_count:
        steps.append(
            {
                "step_id": "defer_active_claimed_paths",
                "status": "blocked_for_broad_checkpoint",
                "dirty_path_count": active_claim_dirty_count,
                "why": "active Work Ledger leases still own dirty paths",
                "next_safe_action": active_claim_blocker_command,
                "first_blocking_claim_command": active_claim_blocker_command,
                "owner_session_groups": active_claim_session_groups,
            }
        )
    if unclaimed_source_dirty_count and not unclaimed_checkpoint_available:
        steps.append(
            {
                "step_id": "classify_or_claim_unclaimed_source_dirty",
                "status": "needs_owner_route",
                "dirty_path_count": unclaimed_source_dirty_count,
                "why": "source-looking dirt without a live claim must be preserved, claimed, validated, then landed with exact pathspecs",
                "commands": [
                    rescue_ref_command,
                    (
                        "./repo-python tools/meta/control/mission_transaction_preflight.py "
                        "--subject-id <id> --owned-path <path> --fail-on-status blocked"
                    ),
                ],
            }
        )
    if generated_owner_dirty_count:
        steps.append(
            {
                "step_id": "settle_generated_owner_dirty",
                "status": "owner_tool_required",
                "dirty_path_count": generated_owner_dirty_count,
                "why": "generated or ledger state should be checked by its owner before landing",
                "commands": [
                    "./repo-python tools/meta/factory/task_ledger_apply.py validate",
                    "./repo-python tools/meta/control/closeout_executor.py plan --json --compact",
                ],
            }
        )
    if mainline_checkpoint_available:
        steps.append(
            {
                "step_id": "operator_authorized_mainline_checkpoint",
                "status": "available",
                "command": broad_checkpoint_command,
            }
        )
    elif unclaimed_checkpoint_available:
        steps.append(
            {
                "step_id": "operator_authorized_unclaimed_checkpoint",
                "status": "available",
                "command": unclaimed_checkpoint_command,
                "why": (
                    "Operator-authorized bankruptcy can clear unclaimed and "
                    "generated-owner dirty paths while excluding active claimed "
                    "paths."
                ),
            }
        )
    elif dirty_total:
        steps.append(
            {
                "step_id": "mainline_checkpoint_guard",
                "status": "blocked",
                "why": "broad mainline checkpoint remains unavailable until the pressure card reports operator_authorized_mainline_checkpoint.status == available",
            }
        )

    if not steps:
        status = "clean"
    elif mainline_checkpoint_available:
        status = "mainline_checkpoint_available"
    elif unclaimed_checkpoint_available:
        status = "unclaimed_checkpoint_available"
    elif active_claim_dirty_count:
        status = "active_claims_block_broad_checkpoint"
    else:
        status = "owner_routes_required"

    generic_closeout_plan_command = (
        "./repo-python tools/meta/control/closeout_executor.py plan --json --compact"
    )
    rescue_next_safe_action = str(
        rescue_repeat_policy.get("next_safe_action") or ""
    ).strip()
    first_action = steps[0] if steps else None
    if mainline_checkpoint_available:
        first_action = next(
            (
                step
                for step in steps
                if step.get("step_id") == "operator_authorized_mainline_checkpoint"
            ),
            first_action,
        )
    elif unclaimed_checkpoint_available:
        first_action = next(
            (
                step
                for step in steps
                if step.get("step_id") == "operator_authorized_unclaimed_checkpoint"
            ),
            first_action,
        )
    elif active_claim_dirty_count and (
        not rescue_next_safe_action
        or rescue_next_safe_action == generic_closeout_plan_command
    ):
        first_action = next(
            (
                step
                for step in steps
                if step.get("step_id") == "defer_active_claimed_paths"
            ),
            first_action,
        )

    return {
        "schema": "dirty_tree_containment_plan_v0",
        "status": status,
        "first_action": first_action,
        "steps": steps,
    }


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


def _rescue_coverage_drift_next_safe_action(rescue_coverage: Mapping[str, Any]) -> str | None:
    if rescue_coverage.get("status") != "stale":
        return None
    action = str(rescue_coverage.get("drift_next_safe_action") or "").strip()
    return action or None


def _dirty_tree_rescue_repeat_policy(
    *,
    dirty_total: int,
    dirty_scan_status: str,
    rescue_coverage: Mapping[str, Any],
) -> Dict[str, Any]:
    rescue_status = str(rescue_coverage.get("status") or "unknown")
    reason = str(rescue_coverage.get("reason") or "").strip()
    drift_next_safe_action = _rescue_coverage_drift_next_safe_action(rescue_coverage)
    quiet_window = "wait_until_dirty_pathset_stable_or_owner_lanes_land"

    if dirty_total <= 0 and dirty_scan_status in ("git_status_porcelain_v1_z", "provided", "none"):
        return {
            "schema": "dirty_tree_rescue_repeat_policy_v0",
            "status": "clean_tree",
            "repeat_rescue_now": False,
            "rescue_coverage_status": rescue_status,
            "reason": "no_dirty_paths",
            "next_safe_action": "./repo-python tools/meta/control/closeout_executor.py plan --json --compact",
        }
    if dirty_total <= 0:
        return {
            "schema": "dirty_tree_rescue_repeat_policy_v0",
            "status": "repeat_unavailable",
            "repeat_rescue_now": False,
            "rescue_coverage_status": rescue_status,
            "reason": "dirty_path_scan_unavailable",
            "next_safe_action": "refresh_dirty_path_scan_and_rescue_coverage",
        }
    if rescue_status == "fresh":
        return {
            "schema": "dirty_tree_rescue_repeat_policy_v0",
            "status": "fresh",
            "repeat_rescue_now": False,
            "rescue_coverage_status": rescue_status,
            "reason": "latest_rescue_ref_covers_current_dirty_tree",
            "next_safe_action": "./repo-python tools/meta/control/closeout_executor.py plan --json --compact",
        }
    if rescue_status == "stale" and drift_next_safe_action:
        return {
            "schema": "dirty_tree_rescue_repeat_policy_v0",
            "status": "repeat_deferred_moving_tree",
            "repeat_rescue_now": False,
            "rescue_coverage_status": rescue_status,
            "reason": reason or "rescue_ref_stale_due_dirty_tree_movement",
            "drift_class": rescue_coverage.get("drift_class"),
            "drift_owner_hint": rescue_coverage.get("drift_owner_hint"),
            "next_safe_action": drift_next_safe_action,
            "quiet_window": quiet_window,
        }
    if rescue_status == "unknown" and reason in {
        "dirty_scan_not_available_for_coverage",
        "content_check_failed",
    }:
        return {
            "schema": "dirty_tree_rescue_repeat_policy_v0",
            "status": "repeat_unavailable",
            "repeat_rescue_now": False,
            "rescue_coverage_status": rescue_status,
            "reason": reason or "rescue_repeat_unavailable",
            "next_safe_action": "refresh_dirty_path_scan_and_rescue_coverage",
        }
    return {
        "schema": "dirty_tree_rescue_repeat_policy_v0",
        "status": "repeat_recommended",
        "repeat_rescue_now": True,
        "rescue_coverage_status": rescue_status,
        "reason": reason or "current_dirty_tree_not_covered_by_rescue_ref",
        "next_safe_action": './checkpoint --rescue-ref --dry-run --message "rescue: dirty-tree finalizer preservation"',
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


def _path_covers_path(container: str, path: str) -> bool:
    container_path = _normalize_dirty_path(container)
    target_path = _normalize_dirty_path(path)
    if not container_path or not target_path:
        return False
    if container_path == target_path:
        return True
    return target_path.startswith(f"{container_path.rstrip('/')}/")


def _coverage_index(paths: Iterable[str]) -> Dict[str, Any]:
    normalized = sorted({_normalize_dirty_path(path) for path in paths if path})
    exact = set(normalized)
    covered_descendant_prefixes: set[str] = set()
    for path in normalized:
        parts = path.split("/")
        for index in range(1, len(parts)):
            covered_descendant_prefixes.add("/".join(parts[:index]))
    return {
        "paths": normalized,
        "exact": exact,
        "covered_descendant_prefixes": covered_descendant_prefixes,
    }


def _path_has_descendant_in_index(path: str, index: Mapping[str, Any]) -> bool:
    paths = list(index.get("paths") or [])
    if not paths:
        return False
    prefix = f"{path.rstrip('/')}/"
    position = bisect_left(paths, prefix)
    return position < len(paths) and str(paths[position]).startswith(prefix)


def _path_covered_by_index(path: str, index: Mapping[str, Any]) -> bool:
    normalized = _normalize_dirty_path(path)
    if not normalized:
        return False
    exact = set(index.get("exact") or set())
    if normalized in exact:
        return True
    parts = normalized.split("/")
    return any("/".join(parts[:i]) in exact for i in range(1, len(parts)))


def _path_overlaps_index(path: str, index: Mapping[str, Any]) -> bool:
    normalized = _normalize_dirty_path(path)
    if not normalized:
        return False
    exact = set(index.get("exact") or set())
    if normalized in exact:
        return True
    if _path_covered_by_index(normalized, index):
        return True
    if normalized in set(index.get("covered_descendant_prefixes") or set()):
        return True
    return _path_has_descendant_in_index(normalized, index)


def _path_overlaps_pathset(path: str, pathset: set[str]) -> bool:
    normalized = _normalize_dirty_path(path)
    if not normalized:
        return False
    return _path_overlaps_index(normalized, _coverage_index(pathset))


def _pathset_delta_with_directory_coverage(
    *,
    current_paths: List[str],
    rescued_paths: List[str],
) -> Dict[str, List[str]]:
    current_set = {_normalize_dirty_path(path) for path in current_paths if path}
    rescued_set = {_normalize_dirty_path(path) for path in rescued_paths if path}
    current_index = _coverage_index(current_set)
    rescued_index = _coverage_index(rescued_set)
    missing_from_rescue = sorted(
        path for path in current_set if not _path_overlaps_index(path, rescued_index)
    )
    not_currently_dirty = sorted(
        path for path in rescued_set if not _path_overlaps_index(path, current_index)
    )
    return {
        "missing_from_rescue": missing_from_rescue,
        "not_currently_dirty": not_currently_dirty,
    }


def _rescue_content_check_paths(
    *,
    current_paths: List[str],
    rescued_paths: List[str],
) -> List[str]:
    current_set = {_normalize_dirty_path(path) for path in current_paths if path}
    rescued_set = {_normalize_dirty_path(path) for path in rescued_paths if path}
    current_index = _coverage_index(current_set)
    covered_rescued_paths = sorted(
        path
        for path in rescued_set
        if _path_covered_by_index(path, current_index)
    )
    return covered_rescued_paths


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
    pathset_delta = _pathset_delta_with_directory_coverage(
        current_paths=current_paths,
        rescued_paths=rescued_paths,
    )
    missing_from_rescue = pathset_delta["missing_from_rescue"]
    not_currently_dirty = pathset_delta["not_currently_dirty"]
    content_check_paths = _rescue_content_check_paths(
        current_paths=current_paths,
        rescued_paths=rescued_paths,
    )
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
    if missing_from_rescue or not_currently_dirty:
        moved_paths = sorted(missing_from_rescue or not_currently_dirty)
        return {
            **coverage,
            "status": "stale",
            "reason": "dirty_pathset_mismatch",
            "missing_from_rescue_count": len(missing_from_rescue),
            "not_currently_dirty_count": len(not_currently_dirty),
            "missing_from_rescue_sample": missing_from_rescue[:5],
            "not_currently_dirty_sample": not_currently_dirty[:5],
            "pathset_comparison_mode": "directory_prefix_coverage",
            **_drift_annotations(moved_paths, active_claims=active_claim_rows, reason="dirty_pathset_mismatch"),
        }
    if not latest_commit:
        return {**coverage, "status": "unknown", "reason": "missing_rescue_commit"}

    content_match = _rescue_commit_matches_worktree_paths(
        repo_root,
        commit=latest_commit,
        paths=content_check_paths,
    )
    coverage["basis"] = "rescue_manifest_pathset_and_blob_hash"
    coverage["pathset_comparison_mode"] = "directory_prefix_coverage"
    coverage["content_check_path_count"] = len(content_check_paths)
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
        repo_root=repo_root,
        limit=limit,
        now=current,
        orphan_after=orphan_after,
    )
    counts = dict(overview.get("counts") or {})
    contention = (
        overview.get("contention")
        if isinstance(overview.get("contention"), Mapping)
        else {}
    )
    claim_collision_rows = [
        row
        for row in list(contention.get("claim_collisions") or [])
        if isinstance(row, Mapping)
    ]
    claim_collision_actions = [
        _seed_speed_claim_collision_action_row(row) for row in claim_collision_rows
    ]
    safe_limit = max(0, int(limit or 0))
    duplicate_claim_cleanup_supported = bool(claim_collision_actions) and all(
        bool(row.get("auto_release_supported")) for row in claim_collision_actions
    )
    claim_collision_cleanup = {
        "status": (
            "auto_dedupe_available"
            if duplicate_claim_cleanup_supported
            else "manual_resolution_required" if claim_collision_actions else "none"
        ),
        "collision_count": len(claim_collision_actions),
        "auto_release_supported": duplicate_claim_cleanup_supported,
        "auto_release_command": (
            _wl_command("session-sweep", "--dedupe-duplicate-claims")
            if duplicate_claim_cleanup_supported
            else None
        ),
        "auto_release_dry_run_command": (
            _wl_command("session-sweep", "--dry-run --dedupe-duplicate-claims")
            if duplicate_claim_cleanup_supported
            else None
        ),
        "first_action_command": str(
            (claim_collision_actions[0] if claim_collision_actions else {}).get(
                "safe_next_command"
            )
            or ""
        ).strip()
        or None,
        "action_rows_omitted": max(0, len(claim_collision_actions) - safe_limit),
    }
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
    unclaimed_checkpoint_command = (
        './checkpoint --arbiter --unclaimed --message '
        '"bankruptcy: land unclaimed dirty tree state"'
    )
    rescue_ref_command = (
        './checkpoint --rescue-ref --dry-run --message "rescue: dirty-tree finalizer preservation"'
    )
    operator_recheck_command = _wl_command(
        "session-sweep",
        (
            "--dry-run --dirty-tree-pressure --bankruptcy-authorized"
            if bankruptcy_authorized
            else "--dry-run --dirty-tree-pressure"
        ),
    )
    mainline_checkpoint_available = (
        bool(bankruptcy_authorized)
        and bool(normalized_dirty_paths)
        and not claim_collision_actions
        and active_claim_dirty_count == 0
        and dirty_scan_status in ("git_status_porcelain_v1_z", "provided")
    )
    operator_checkpoint: Dict[str, Any] = {
        "authorized": bool(bankruptcy_authorized),
        "status": "available" if mainline_checkpoint_available else "blocked",
        "command": broad_checkpoint_command,
        "conservative_fallback_command": rescue_ref_command,
        "requires_no_claim_collisions": True,
        "claim_collision_count": len(claim_collision_actions),
        "requires_no_active_claim_dirty_paths": True,
        "active_claim_dirty_path_count": active_claim_dirty_count,
    }
    if not bankruptcy_authorized:
        operator_checkpoint["status"] = "not_authorized"
        operator_checkpoint["blocked_by"] = ["operator_bankruptcy_authorization_missing"]
    elif not normalized_dirty_paths:
        operator_checkpoint["blocked_by"] = ["clean_tree"]
    else:
        checkpoint_blockers: List[str] = []
        if claim_collision_actions:
            checkpoint_blockers.append("claim_collisions")
        if active_claim_dirty_count:
            checkpoint_blockers.append("active_claim_dirty_paths")
        if dirty_scan_status not in ("git_status_porcelain_v1_z", "provided"):
            checkpoint_blockers.append("dirty_path_scan_unavailable")
        if checkpoint_blockers:
            operator_checkpoint["blocked_by"] = checkpoint_blockers

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
    rescue_drift_next_safe_action = _rescue_coverage_drift_next_safe_action(rescue_coverage)
    generated_owner_dirty_count = int(dirty_class_counts.get("generated_owner_dirty") or 0)
    unclaimed_source_dirty_count = int(dirty_class_counts.get("unclaimed_source_dirty") or 0)
    generated_owner_dirty = _dirty_path_class_preview_for_pressure(
        normalized_dirty_paths,
        active_claims=active_claims,
        class_id="generated_owner_dirty",
        total_count=generated_owner_dirty_count,
        limit=limit,
    )
    unclaimed_source_dirty = _dirty_path_class_preview_for_pressure(
        normalized_dirty_paths,
        active_claims=active_claims,
        class_id="unclaimed_source_dirty",
        total_count=unclaimed_source_dirty_count,
        limit=limit,
    )
    active_claim_session_groups = _active_claim_dirty_session_groups(
        normalized_dirty_paths,
        active_claims=active_claims,
        limit=limit,
    )
    active_claim_blocker_command = (
        _first_active_claim_dirty_group_command(active_claim_session_groups)
        or "wait_for_claim_release_or_finalize_session_before_sweeping"
    )
    unclaimed_checkpoint = _dirty_tree_unclaimed_checkpoint(
        bankruptcy_authorized=bool(bankruptcy_authorized),
        dirty_scan_status=dirty_scan_status,
        dirty_class_counts=dirty_class_counts,
        active_claim_dirty_count=active_claim_dirty_count,
        generated_owner_dirty=generated_owner_dirty,
        unclaimed_source_dirty=unclaimed_source_dirty,
        command=unclaimed_checkpoint_command,
    )
    unclaimed_checkpoint_available = (
        str(unclaimed_checkpoint.get("status") or "") == "available"
    )
    rescue_repeat_policy = _dirty_tree_rescue_repeat_policy(
        dirty_total=len(normalized_dirty_paths),
        dirty_scan_status=dirty_scan_status,
        rescue_coverage=rescue_coverage,
    )
    scoped_work_unblock = _dirty_tree_scoped_work_unblock(
        dirty_total=len(normalized_dirty_paths),
        active_claim_dirty_count=active_claim_dirty_count,
        generated_owner_dirty_count=generated_owner_dirty_count,
        unclaimed_source_dirty_count=unclaimed_source_dirty_count,
        mainline_checkpoint_available=mainline_checkpoint_available,
        rescue_repeat_policy=rescue_repeat_policy,
    )
    if mainline_checkpoint_available:
        operator_checkpoint["included_dirty_path_classes"] = dict(dirty_class_counts)
        operator_checkpoint["included_generated_owner_dirty"] = generated_owner_dirty
        operator_checkpoint["included_unclaimed_source_dirty"] = unclaimed_source_dirty
        operator_checkpoint["inclusion_warning"] = (
            "Broad checkpoint will include generated-owner and unclaimed source dirty paths; "
            "use only inside the operator-authorized bankruptcy lane."
        )
    if active_claim_dirty_count:
        operator_checkpoint["blocking_active_claim_session_groups"] = (
            active_claim_session_groups
        )
        operator_checkpoint["first_blocking_claim_command"] = active_claim_blocker_command
        operator_checkpoint["blocked_dirty_path_classes"] = dict(dirty_class_counts)
        operator_checkpoint["after_active_claims_clear"] = (
            _dirty_tree_after_active_claims_clear_preview(
                bankruptcy_authorized=bool(bankruptcy_authorized),
                dirty_class_counts=dirty_class_counts,
                generated_owner_dirty=generated_owner_dirty,
                unclaimed_source_dirty=unclaimed_source_dirty,
                recheck_command=operator_recheck_command,
            )
        )
        operator_checkpoint["available_after"] = (
            "active_claim_dirty_path_count == 0"
        )
    if claim_collision_actions:
        operator_checkpoint["blocking_claim_collision_cleanup"] = claim_collision_cleanup
        operator_checkpoint["first_claim_collision_cleanup_command"] = (
            claim_collision_cleanup.get("auto_release_dry_run_command")
            or claim_collision_cleanup.get("first_action_command")
            or _wl_command("session-status", "--seed-speed --limit 12")
        )
        operator_checkpoint["available_after"] = (
            "claim_collision_count == 0 && active_claim_dirty_path_count == 0"
            if active_claim_dirty_count
            else "claim_collision_count == 0"
        )
    operator_checkpoint["recheck_command"] = operator_recheck_command
    containment_plan = _dirty_tree_containment_plan(
        dirty_total=len(normalized_dirty_paths),
        active_claim_dirty_count=active_claim_dirty_count,
        generated_owner_dirty_count=generated_owner_dirty_count,
        unclaimed_source_dirty_count=unclaimed_source_dirty_count,
        mainline_checkpoint_available=mainline_checkpoint_available,
        rescue_coverage=rescue_coverage,
        rescue_repeat_policy=rescue_repeat_policy,
        active_claim_session_groups=active_claim_session_groups,
        broad_checkpoint_command=broad_checkpoint_command,
        unclaimed_checkpoint_command=unclaimed_checkpoint_command,
        unclaimed_checkpoint_available=unclaimed_checkpoint_available,
        rescue_ref_command=rescue_ref_command,
    )
    blocked_residuals: List[Dict[str, Any]] = []
    if claim_collision_actions:
        blocked_residuals.append(
            {
                "reason": "ClaimCollision",
                "collision_count": len(claim_collision_actions),
                "auto_release_supported": duplicate_claim_cleanup_supported,
                "next_safe_action": (
                    claim_collision_cleanup.get("auto_release_dry_run_command")
                    or claim_collision_cleanup.get("first_action_command")
                    or _wl_command("session-status", "--seed-speed --limit 12")
                ),
            }
        )
    if active_claim_dirty_count:
        blocked_residuals.append(
            {
                "reason": "SessionLeaseActive",
                "dirty_path_count": active_claim_dirty_count,
                "owner_group_count": active_claim_session_groups.get("group_count"),
                "next_safe_action": active_claim_blocker_command,
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
    if (
        dirty_class_counts.get("unclaimed_source_dirty")
        and not mainline_checkpoint_available
        and not unclaimed_checkpoint_available
    ):
        unclaimed_next_safe_action = (
            rescue_ref_command
            if rescue_repeat_policy.get("repeat_rescue_now")
            else rescue_repeat_policy.get("next_safe_action")
            or "identify_or_claim_writer_before_repeating_rescue"
        )
        blocked_residuals.append(
            {
                "reason": "UnclaimedDirtyWorkRequiresPrivateBackupOrOwnerClaim",
                "dirty_path_count": dirty_class_counts["unclaimed_source_dirty"],
                "path_sample": unclaimed_source_dirty["paths_preview"],
                "path_sample_omitted": unclaimed_source_dirty["paths_omitted"],
                "first_path_preflight_command": unclaimed_source_dirty[
                    "first_path_preflight_command"
                ],
                "next_safe_action": unclaimed_next_safe_action,
            }
        )

    generic_closeout_plan_command = (
        "./repo-python tools/meta/control/closeout_executor.py plan --json --compact"
    )
    if mainline_checkpoint_available:
        next_safe_action = broad_checkpoint_command
    elif unclaimed_checkpoint_available:
        next_safe_action = unclaimed_checkpoint_command
    elif claim_collision_actions:
        next_safe_action = (
            claim_collision_cleanup.get("auto_release_dry_run_command")
            or claim_collision_cleanup.get("first_action_command")
            or _wl_command("session-status", "--seed-speed --limit 12")
        )
    elif sweep_preview or expired_claims:
        next_safe_action = (
            "./repo-python tools/meta/factory/work_ledger.py session-sweep "
            "--dry-run --dirty-tree-pressure"
        )
    elif active_claim_dirty_count and (
        not rescue_drift_next_safe_action
        or rescue_drift_next_safe_action == generic_closeout_plan_command
    ):
        next_safe_action = active_claim_blocker_command
    elif rescue_drift_next_safe_action:
        next_safe_action = rescue_drift_next_safe_action
    elif rescue_repeat_policy.get("next_safe_action") and not rescue_repeat_policy.get(
        "repeat_rescue_now"
    ):
        next_safe_action = str(rescue_repeat_policy["next_safe_action"])
    elif normalized_dirty_paths:
        next_safe_action = rescue_ref_command
    else:
        next_safe_action = generic_closeout_plan_command

    return {
        "schema": DIRTY_TREE_BANKRUPTCY_PRESSURE_SCHEMA,
        "authority_boundary": "orientation_overlay_not_safety_authority",
        "safety_authority": False,
        "bankruptcy_authorized": bool(bankruptcy_authorized),
        "operator_authorized_mainline_checkpoint": operator_checkpoint,
        "operator_authorized_unclaimed_checkpoint": unclaimed_checkpoint,
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
        "class_counts": dirty_class_counts,
        "dirty_path_rows": dirty_rows,
        "generated_owner_dirty": generated_owner_dirty,
        "unclaimed_source_dirty": unclaimed_source_dirty,
        "active_claim_session_groups": active_claim_session_groups,
        "rescue_repeat_policy": rescue_repeat_policy,
        "repeat_policy": rescue_repeat_policy,
        "scoped_work_unblock": scoped_work_unblock,
        "containment_plan": containment_plan,
        "work_ledger_counts": {
            "sessions_total": counts.get("sessions_total", 0),
            "active_sessions": counts.get("active_sessions", 0),
            "effective_active_sessions": counts.get("effective_active_sessions", 0),
            "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
            "stale_append_obligations": counts.get(
                "stale_append_obligations",
                counts.get("stale_sessions", 0),
            ),
            "stale_claim_only_sessions": counts.get("stale_claim_only_sessions", 0),
            "active_claims": len(active_claims),
            "claim_collisions": counts.get("claim_collisions", 0),
        },
        "claim_collision_cleanup": claim_collision_cleanup,
        "claim_collision_actions": claim_collision_actions[:safe_limit],
        "claim_collision_actions_omitted": claim_collision_cleanup["action_rows_omitted"],
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
            else (
                [
                    {
                        "reason": "OperatorAuthorizedUnclaimedDirtyTreeBankruptcy",
                        "command": unclaimed_checkpoint_command,
                        "conservative_fallback_command": rescue_ref_command,
                        "dirty_path_count": unclaimed_checkpoint.get(
                            "included_dirty_path_count"
                        ),
                        "excluded_active_claim_dirty_path_count": (
                            unclaimed_checkpoint.get(
                                "excluded_active_claim_dirty_path_count"
                            )
                        ),
                    }
                ]
                if unclaimed_checkpoint_available
                else []
            )
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
            "operator_authorized_unclaimed_checkpoint": unclaimed_checkpoint_command,
            "closeout_plan": "./repo-python tools/meta/control/closeout_executor.py plan --json --compact",
        },
    }


def _compact_dirty_path_class_preview(row: Mapping[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(row, Mapping):
        return None
    return {
        key: row.get(key)
        for key in (
            "schema",
            "class",
            "path_count",
            "paths_preview",
            "paths_omitted",
            "first_path",
            "first_path_owner_surface",
            "first_path_recommended_action",
            "owner_surfaces_preview",
            "owner_surfaces_omitted",
            "first_path_preflight_command",
        )
        if row.get(key) not in (None, "", [], {})
    }


def _compact_active_claim_session_groups(
    groups: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(groups, Mapping):
        return None
    compact_groups: List[Dict[str, Any]] = []
    for row in list(groups.get("groups") or [])[:2]:
        if not isinstance(row, Mapping):
            continue
        compact_groups.append(
            {
                key: row.get(key)
                for key in (
                    "session_id",
                    "actor",
                    "phase_id",
                    "dirty_path_count",
                    "leased_until_max",
                    "recommended_action",
                    "safe_next_command",
                    "paths_preview",
                    "paths_omitted",
                    "first_underlying_path",
                    "first_underlying_owner_surface",
                    "first_underlying_recommended_action",
                )
                if row.get(key) not in (None, "", [], {})
            }
        )
    return {
        "schema": groups.get("schema"),
        "group_count": groups.get("group_count"),
        "groups": compact_groups,
        "groups_omitted": max(0, int(groups.get("group_count") or 0) - len(compact_groups)),
    }


def _compact_dirty_tree_checkpoint(
    checkpoint: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(checkpoint, Mapping):
        return None
    compact = {
        key: checkpoint.get(key)
        for key in (
            "schema",
            "authorized",
            "status",
            "command",
            "conservative_fallback_command",
            "requires_no_claim_collisions",
            "claim_collision_count",
            "requires_no_active_claim_dirty_paths",
            "active_claim_dirty_path_count",
            "blocked_by",
            "available_after",
            "recheck_command",
            "first_blocking_claim_command",
            "included_dirty_path_count",
            "included_dirty_path_classes",
            "excluded_active_claim_dirty_path_count",
            "path_selection_policy",
            "requires_dirty_path_scan",
            "requires_operator_bankruptcy_authorization",
            "active_claim_boundary",
        )
        if checkpoint.get(key) not in (None, "", [], {})
    }
    groups = _compact_active_claim_session_groups(
        checkpoint.get("blocking_active_claim_session_groups")
    )
    if groups:
        compact["blocking_active_claim_session_groups"] = groups
    after_claims_clear = checkpoint.get("after_active_claims_clear")
    if isinstance(after_claims_clear, Mapping):
        compact["after_active_claims_clear"] = {
            key: after_claims_clear.get(key)
            for key in (
                "schema",
                "status",
                "operator_authorized",
                "remaining_dirty_path_classes",
                "remaining_classes_checkpoint_policy",
                "checkpoint_guard",
                "recheck_command",
                "first_owner_settlement_action",
            )
            if after_claims_clear.get(key) not in (None, "", [], {})
        }
    for source_key in ("included_generated_owner_dirty", "included_unclaimed_source_dirty"):
        preview = _compact_dirty_path_class_preview(checkpoint.get(source_key))
        if preview:
            compact[source_key] = preview
    return compact


def _compact_dirty_tree_containment_plan(
    plan: Mapping[str, Any] | None,
) -> Dict[str, Any] | None:
    if not isinstance(plan, Mapping):
        return None
    compact_steps: List[Dict[str, Any]] = []
    for row in list(plan.get("steps") or []):
        if not isinstance(row, Mapping):
            continue
        compact_steps.append(
            {
                key: row.get(key)
                for key in (
                    "step_id",
                    "status",
                    "why",
                    "dirty_path_count",
                    "next_safe_action",
                    "first_blocking_claim_command",
                    "commands",
                    "command",
                    "quiet_window",
                )
                if row.get(key) not in (None, "", [], {})
            }
        )
    first_action = plan.get("first_action") if isinstance(plan.get("first_action"), Mapping) else {}
    return {
        key: value
        for key, value in {
            "schema": plan.get("schema"),
            "status": plan.get("status"),
            "first_action": {
                key: first_action.get(key)
                for key in (
                    "step_id",
                    "status",
                    "why",
                    "dirty_path_count",
                    "next_safe_action",
                    "first_blocking_claim_command",
                    "command",
                )
                if first_action.get(key) not in (None, "", [], {})
            },
            "steps": compact_steps,
        }.items()
        if value not in (None, "", [], {})
    }


def _compact_dirty_tree_repeat_policy(policy: Mapping[str, Any] | None) -> Dict[str, Any] | None:
    if not isinstance(policy, Mapping):
        return None
    return {
        key: policy.get(key)
        for key in (
            "schema",
            "status",
            "repeat_rescue_now",
            "rescue_coverage_status",
            "reason",
            "drift_class",
            "drift_owner_hint",
            "next_safe_action",
            "quiet_window",
        )
        if policy.get(key) not in (None, "", [], {})
    }


def compact_dirty_tree_pressure_card(card: Mapping[str, Any]) -> Dict[str, Any]:
    """Return the agent-facing dirty-tree pressure card.

    The full bankruptcy card intentionally carries repeated nested evidence for
    machine consumers. The CLI first-action route needs the same decision handles
    without replaying every nested preview into active context.
    """
    class_counts = card.get("class_counts") or card.get("dirty_path_class_counts") or {}
    repeat_policy = card.get("repeat_policy") or card.get("rescue_repeat_policy")
    compact = {
        "schema": card.get("schema") or DIRTY_TREE_BANKRUPTCY_PRESSURE_SCHEMA,
        "output_profile": "compact",
        "authority_boundary": card.get("authority_boundary"),
        "safety_authority": card.get("safety_authority"),
        "bankruptcy_authorized": card.get("bankruptcy_authorized"),
        "dirty_scan_status": card.get("dirty_scan_status"),
        "dirty_total": card.get("dirty_total"),
        "dirty_path_class_counts": class_counts,
        "class_counts": class_counts,
        "operator_authorized_mainline_checkpoint": _compact_dirty_tree_checkpoint(
            card.get("operator_authorized_mainline_checkpoint")
        ),
        "operator_authorized_unclaimed_checkpoint": _compact_dirty_tree_checkpoint(
            card.get("operator_authorized_unclaimed_checkpoint")
        ),
        "policy": card.get("policy"),
        "generated_owner_dirty": _compact_dirty_path_class_preview(
            card.get("generated_owner_dirty")
        ),
        "unclaimed_source_dirty": _compact_dirty_path_class_preview(
            card.get("unclaimed_source_dirty")
        ),
        "active_claim_session_groups": _compact_active_claim_session_groups(
            card.get("active_claim_session_groups")
        ),
        "scoped_work_unblock": card.get("scoped_work_unblock"),
        "containment_plan": _compact_dirty_tree_containment_plan(
            card.get("containment_plan")
        ),
        "work_ledger_counts": card.get("work_ledger_counts"),
        "claim_collision_cleanup": card.get("claim_collision_cleanup"),
        "claim_collision_actions": card.get("claim_collision_actions"),
        "claim_collision_actions_omitted": card.get("claim_collision_actions_omitted"),
        "repeat_policy": _compact_dirty_tree_repeat_policy(repeat_policy),
        "rescue_repeat_policy": _compact_dirty_tree_repeat_policy(repeat_policy),
        "blocked_residuals": card.get("blocked_residuals"),
        "mainline_commit_candidates": card.get("mainline_commit_candidates"),
        "next_safe_action": card.get("next_safe_action"),
        "commands": card.get("commands"),
        "full_card_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-sweep --dry-run --dirty-tree-pressure --full"
        ),
        "omission_receipt": {
            "omitted": [
                "dirty_path_rows",
                "full rescue refs and coverage",
                "repeated nested generated-owner previews",
                "full active-claim group payloads",
            ],
            "reason": "Default dirty-tree pressure output is a first-action coordination card; use --full for machine evidence.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                "session-sweep --dry-run --dirty-tree-pressure --full"
            ),
        },
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [], {})}


def dirty_tree_pressure_alias(card: Mapping[str, Any]) -> Dict[str, Any]:
    """Return a compact stable alias for the dirty-tree pressure readback.

    The older full-card key is intentionally named for the bankruptcy lane. The
    operator-facing CLI flag is broader (`--dirty-tree-pressure`), so this alias
    gives agents a stable, short root for common jq probes without duplicating
    the full card payload.
    """

    compact = compact_dirty_tree_pressure_card(card)
    class_counts = compact.get("class_counts") or compact.get("dirty_path_class_counts") or {}
    repeat_policy = compact.get("repeat_policy") or compact.get("rescue_repeat_policy") or {}

    def alias_checkpoint(name: str) -> Dict[str, Any] | None:
        checkpoint = compact.get(name)
        if not isinstance(checkpoint, Mapping):
            return None
        return {
            key: checkpoint.get(key)
            for key in (
                "schema",
                "authorized",
                "status",
                "command",
                "blocked_by",
                "claim_collision_count",
                "active_claim_dirty_path_count",
                "included_dirty_path_count",
                "included_dirty_path_classes",
                "excluded_active_claim_dirty_path_count",
                "first_blocking_claim_command",
                "recheck_command",
            )
            if checkpoint.get(key) not in (None, "", [], {})
        }

    groups = compact.get("active_claim_session_groups")
    active_claim_summary = None
    if isinstance(groups, Mapping):
        active_claim_summary = {
            key: groups.get(key)
            for key in ("schema", "group_count", "groups_omitted")
            if groups.get(key) not in (None, "", [], {})
        }
        first_group = next(
            (row for row in list(groups.get("groups") or []) if isinstance(row, Mapping)),
            None,
        )
        if first_group:
            active_claim_summary["first_group"] = {
                key: first_group.get(key)
                for key in (
                    "session_id",
                    "dirty_path_count",
                    "safe_next_command",
                    "first_underlying_path",
                    "first_underlying_owner_surface",
                )
                if first_group.get(key) not in (None, "", [], {})
            }

    containment = compact.get("containment_plan")
    containment_summary = None
    if isinstance(containment, Mapping):
        containment_summary = {
            "schema": containment.get("schema"),
            "status": containment.get("status"),
            "first_action": containment.get("first_action"),
            "step_count": len(
                [row for row in list(containment.get("steps") or []) if isinstance(row, Mapping)]
            ),
        }
    return {
        "schema": DIRTY_TREE_PRESSURE_ALIAS_SCHEMA,
        "alias_of": "dirty_tree_bankruptcy_pressure",
        "output_profile": compact.get("output_profile"),
        "authority_boundary": compact.get("authority_boundary"),
        "safety_authority": compact.get("safety_authority"),
        "bankruptcy_authorized": compact.get("bankruptcy_authorized"),
        "dirty_scan_status": compact.get("dirty_scan_status"),
        "dirty_total": compact.get("dirty_total"),
        "class_counts": class_counts,
        "dirty_path_class_counts": class_counts,
        "operator_authorized_mainline_checkpoint": alias_checkpoint(
            "operator_authorized_mainline_checkpoint"
        ),
        "operator_authorized_unclaimed_checkpoint": alias_checkpoint(
            "operator_authorized_unclaimed_checkpoint"
        ),
        "active_claim_session_groups": active_claim_summary,
        "scoped_work_unblock": {
            key: (compact.get("scoped_work_unblock") or {}).get(key)
            for key in ("schema", "status", "one_line_rule", "counts")
            if isinstance(compact.get("scoped_work_unblock"), Mapping)
            and (compact.get("scoped_work_unblock") or {}).get(key) not in (None, "", [], {})
        },
        "containment_plan": containment_summary,
        "generated_owner_dirty": _compact_dirty_path_class_preview(
            compact.get("generated_owner_dirty")
        ),
        "unclaimed_source_dirty": _compact_dirty_path_class_preview(
            compact.get("unclaimed_source_dirty")
        ),
        "claim_collision_cleanup": compact.get("claim_collision_cleanup"),
        "claim_collision_actions": compact.get("claim_collision_actions"),
        "claim_collision_actions_omitted": compact.get("claim_collision_actions_omitted"),
        "repeat_policy": repeat_policy,
        "rescue_repeat_policy": repeat_policy,
        "blocked_residual_count": len(
            [row for row in list(compact.get("blocked_residuals") or []) if isinstance(row, Mapping)]
        ),
        "next_safe_action": compact.get("next_safe_action"),
        "commands": compact.get("commands"),
        "full_card_command": compact.get("full_card_command"),
        "omission_receipt": compact.get("omission_receipt"),
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
        same_scope_collisions: List[Dict[str, Any]] = []
        if len(left_claims) > 1:
            anchor = left_claims[0]
            same_scope_collisions = [
                claim
                for claim in left_claims[1:]
                if _claim_scopes_conflict(anchor, claim)
            ]
        overlap_collisions: List[Dict[str, Any]] = []
        for right_key in scope_keys[index + 1 :]:
            pair_key = (left_key, right_key)
            if pair_key in consumed_pairs:
                continue
            if not _claim_scopes_conflict(left_claims[0], scoped_claims[right_key][0]):
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
        if _is_effective_active_session(session, now=now, orphan_after=orphan_after)
    ]
    passive_external_observed_sessions = [
        session
        for session in active_sessions
        if not _is_orphaned_active_session(session, now=now, orphan_after=orphan_after)
        and _is_passive_external_observed_session(
            session,
            now=now,
            orphan_after=orphan_after,
        )
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
    seed_speed_overview = build_session_cohort_overview(
        status,
        repo_root=repo_root,
        limit=SEED_SPEED_SNAPSHOT_OVERVIEW_LIMIT,
        now=now,
        orphan_after=orphan_after,
    )
    seed_speed_hint = build_seed_speed_status(
        seed_speed_overview,
        limit=SESSION_COHORT_OVERVIEW_LIMIT,
    )
    overview_cards_hint = build_session_cohort_cards_only_overview(
        build_session_cohort_overview(
            status,
            repo_root=repo_root,
            limit=SESSION_COHORT_OVERVIEW_LIMIT,
            now=now,
            orphan_after=orphan_after,
        ),
        limit=SESSION_COHORT_OVERVIEW_LIMIT,
    )
    stable_payload = {
        "active_claims": active_claims,
        "claim_collisions": claim_collisions,
        "seed_speed_hint": {
            "counts": seed_speed_hint.get("counts") or {},
            "first_action_kind": seed_speed_hint.get("first_action_kind"),
            "first_action_command": seed_speed_hint.get("first_action_command"),
            "heartbeat_gap_claim_sessions": seed_speed_hint.get("heartbeat_gap_claim_sessions") or [],
        },
        "overview_cards_hint": {
            "counts": overview_cards_hint.get("counts") or {},
            "monitor_card_count": len(overview_cards_hint.get("monitor_cards") or []),
            "awareness_card_count": len(overview_cards_hint.get("awareness_cards") or []),
            "repair_row_count": len(overview_cards_hint.get("repair_rows") or []),
        },
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
            "passive_external_observed_sessions": len(passive_external_observed_sessions),
            "orphaned_active_sessions": len(orphaned_active_sessions),
            "active_claims": len(active_claims),
            "claim_collisions": len(claim_collisions),
        },
        "active_claims": active_claims,
        "claim_collisions": claim_collisions,
        "seed_speed_hint": seed_speed_hint,
        "overview_cards_hint": overview_cards_hint,
        "refresh_command": "./repo-python tools/meta/factory/work_ledger.py session-claims --refresh",
    }


def _duplicate_same_session_claim_dedupe_actions(
    status: Mapping[str, Any],
    *,
    now: datetime,
    orphan_after: timedelta = ACTIVE_SESSION_ORPHAN_AFTER,
    limit: int | None = SESSION_COHORT_OVERVIEW_LIMIT,
) -> List[Dict[str, Any]]:
    sessions_payload = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    active_claims: List[Dict[str, Any]] = []
    for session_id, session in sessions_payload.items():
        if not isinstance(session, Mapping) or session.get("ended_at"):
            continue
        if _is_orphaned_active_session(session, now=now, orphan_after=orphan_after):
            continue
        for claim in _session_active_claims(session, now=now):
            row = _compact_claim(claim)
            row["session_id"] = str(session_id)
            row["actor"] = session.get("actor")
            row["phase_id"] = session.get("phase_id")
            active_claims.append(row)
    active_claims.sort(key=lambda c: str(c.get("leased_until") or ""), reverse=True)

    action_limit = None if limit is None else max(0, int(limit or 0))
    if action_limit == 0:
        return []

    actions: List[Dict[str, Any]] = []
    scheduled_release_keys: set[tuple[str, str]] = set()
    for collision in _claim_collision_rows(active_claims):
        if _claim_collision_failure_class(collision) != "duplicate_same_session_claim":
            continue
        claims = [
            dict(claim)
            for claim in collision.get("active_claims") or []
            if isinstance(claim, Mapping) and str(claim.get("claim_id") or "").strip()
        ]
        session_ids = sorted(
            {str(claim.get("session_id") or "").strip() for claim in claims if claim.get("session_id")}
        )
        if len(session_ids) != 1 or len(claims) < 2:
            continue
        session_id = session_ids[0]
        keep_claim = claims[0]
        keep_key = (session_id, str(keep_claim.get("claim_id") or ""))
        if keep_key in scheduled_release_keys:
            continue
        release_claims = [
            claim
            for claim in claims[1:]
            if (session_id, str(claim.get("claim_id") or "")) not in scheduled_release_keys
        ]
        if not release_claims:
            continue
        for claim in release_claims:
            scheduled_release_keys.add((session_id, str(claim.get("claim_id") or "")))
        actions.append(
            {
                "failure_class": "duplicate_same_session_claim",
                "scope_kind": collision.get("scope_kind"),
                "scope_id": collision.get("scope_id"),
                "td_id": collision.get("td_id"),
                "path": collision.get("path"),
                "work_item_id": collision.get("work_item_id"),
                "session_id": session_id,
                "claim_count": collision.get("claim_count"),
                "kept_claim_id": keep_claim.get("claim_id"),
                "kept_claim_lease_until": keep_claim.get("leased_until"),
                "release_claim_ids": [claim.get("claim_id") for claim in release_claims],
                "release_count": len(release_claims),
                "release_claims_preview": [
                    {
                        "claim_id": claim.get("claim_id"),
                        "scope_kind": claim.get("scope_kind"),
                        "scope_id": claim.get("scope_id"),
                        "td_id": claim.get("td_id"),
                        "path": claim.get("path"),
                        "work_item_id": claim.get("work_item_id"),
                        "leased_until": claim.get("leased_until"),
                    }
                    for claim in release_claims[:3]
                ],
                "policy": (
                    "same-session duplicate only; keeps newest lease and releases older "
                    "duplicate claims"
                ),
                "release_commands": [
                    _wl_command(
                        "session-release-claim",
                        f"--session-id {_quote_cli(session_id)}",
                        f"--claim-id {_quote_cli(str(claim.get('claim_id') or ''))}",
                        "--reason duplicate_same_session_claim_dedupe",
                    )
                    for claim in release_claims
                ],
            }
        )
        if action_limit is not None and len(actions) >= action_limit:
            break
    return actions


def _duplicate_claim_release_keys(actions: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    return {
        (str(action.get("session_id") or ""), str(claim_id or ""))
        for action in actions
        for claim_id in action.get("release_claim_ids") or []
        if str(action.get("session_id") or "") and str(claim_id or "")
    }


def _mark_duplicate_claims_released(
    status: Dict[str, Any],
    release_keys: set[tuple[str, str]],
    *,
    current: datetime,
    release_reason: str,
) -> List[Dict[str, Any]]:
    released: List[Dict[str, Any]] = []
    if not release_keys:
        return released

    sessions = dict(status.get("sessions") or {})
    for session_id, session in list(sessions.items()):
        if not isinstance(session, Mapping):
            continue
        claims = [
            dict(claim)
            for claim in session.get("claims") or []
            if isinstance(claim, Mapping)
        ]
        changed = False
        for claim in claims:
            claim_id = str(claim.get("claim_id") or "")
            if (str(session_id), claim_id) not in release_keys:
                continue
            if claim.get("released_at") or claim.get("expired_at"):
                continue
            claim["released_at"] = current.isoformat()
            claim["release_reason"] = release_reason
            released_claim = _compact_claim(claim)
            released_claim["session_id"] = str(session_id)
            released.append(released_claim)
            changed = True
        if changed:
            session = dict(session)
            session["claims"] = claims
            sessions[str(session_id)] = session
    status["sessions"] = sessions
    return released


def _dedupe_duplicate_claims_to_fixed_point(
    status: Dict[str, Any],
    *,
    current: datetime,
    release_reason: str,
) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    all_actions: List[Dict[str, Any]] = []
    all_released: List[Dict[str, Any]] = []
    iteration_count = 0
    for _ in range(100):
        iteration_count += 1
        actions = _duplicate_same_session_claim_dedupe_actions(
            status,
            now=current,
            limit=None,
        )
        if not actions:
            iteration_count -= 1
            break
        released = _mark_duplicate_claims_released(
            status,
            _duplicate_claim_release_keys(actions),
            current=current,
            release_reason=release_reason,
        )
        if not released:
            break
        all_actions.extend(actions)
        all_released.extend(released)
    return all_actions, all_released, iteration_count


def dedupe_duplicate_same_session_claims(
    repo_root: Path,
    *,
    now: datetime | None = None,
    dry_run: bool = False,
    reason: str | None = None,
    limit: int = SESSION_COHORT_OVERVIEW_LIMIT,
) -> Dict[str, Any]:
    """Release older same-session duplicate claims while preserving true contention.

    This is intentionally narrower than the general collision repair surface:
    different-session claim collisions still require coordination, while a single
    session that accidentally leased the same scope multiple times can be
    normalized by keeping the newest lease.
    """
    current = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    release_reason = str(reason or "duplicate_same_session_claim_dedupe").strip()
    safe_limit = max(0, int(limit or 0))

    if dry_run:
        status = _load_runtime_status_for_session_scan(repo_root)
        actions, would_release, iteration_count = _dedupe_duplicate_claims_to_fixed_point(
            copy.deepcopy(dict(status)),
            current=current,
            release_reason=release_reason,
        )
        preview_actions = actions[:safe_limit] if safe_limit else []
        return {
            "schema": DUPLICATE_CLAIM_DEDUPE_SCHEMA,
            "status": "would_release" if would_release else "clean",
            "dry_run": True,
            "generated_at": current.isoformat(),
            "release_reason": release_reason,
            "duplicate_collision_count": len(actions),
            "released_count": 0,
            "would_release_count": len(would_release),
            "actions": preview_actions,
            "actions_omitted": max(0, len(actions) - len(preview_actions)),
            "dedupe_iteration_count": iteration_count,
            "policy": (
                "same-session duplicate only; keeps newest lease and releases older "
                "duplicate claims"
            ),
        }

    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = dict(_load_runtime_status_for_session_scan(repo_root))
        actions, released, iteration_count = _dedupe_duplicate_claims_to_fixed_point(
            status,
            current=current,
            release_reason=release_reason,
        )
        preview_actions = actions[:safe_limit] if safe_limit else []
        if released:
            event = {
                "event_id": mint_sweep_event_id(),
                "kind": "duplicate_claim_dedupe",
                "at": current.isoformat(),
                "released_count": len(released),
                "duplicate_collision_count": len(actions),
            }
            status["recent_sweep_events"] = [
                dict(entry)
                for entry in status.get("recent_sweep_events") or []
                if isinstance(entry, Mapping)
            ][-(RECENT_SWEEP_EVENTS_LIMIT - 1) :] + [event]
            saved = _write_runtime_status(repo_root, status)
            generated_at = saved.get("generated_at")
        else:
            generated_at = status.get("generated_at") or current.isoformat()

    return {
        "schema": DUPLICATE_CLAIM_DEDUPE_SCHEMA,
        "status": "released" if released else "clean",
        "dry_run": False,
        "generated_at": generated_at,
        "release_reason": release_reason,
        "duplicate_collision_count": len(actions),
        "released_count": len(released),
        "would_release_count": 0,
        "actions": preview_actions,
        "actions_omitted": max(0, len(actions) - len(preview_actions)),
        "dedupe_iteration_count": iteration_count,
        "released": released,
        "policy": (
            "same-session duplicate only; keeps newest lease and releases older "
            "duplicate claims"
        ),
    }


def active_claim_collisions_for_paths(
    repo_root: Path,
    paths: Iterable[str],
    *,
    status: Mapping[str, Any] | None = None,
    session_id: str | None = None,
    now: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Return active Work Ledger path claims that overlap requested paths."""
    status_payload = status if status is not None else load_runtime_status(repo_root)
    snapshot = build_active_claims_snapshot(repo_root, status_payload, now=now)
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
                    "claim_intent": claim.get("claim_intent"),
                    "conflict_scope_kind": claim.get("conflict_scope_kind"),
                    "conflict_mode": claim.get("conflict_mode"),
                    "leased_until": claim.get("leased_until"),
                }
            )
    return collisions


def active_path_claims_for_paths(
    repo_root: Path,
    paths: Iterable[str],
    *,
    status: Mapping[str, Any] | None = None,
    session_id: str | None = None,
    now: datetime | None = None,
) -> List[Dict[str, Any]]:
    """Return active Work Ledger path claims that overlap requested paths.

    Unlike ``active_claim_collisions_for_paths``, this is not a blocker scan:
    callers may filter to the requesting session to prove same-owner mutation
    authority before interpreting a clear collision result as edit permission.
    """
    status_payload = status if status is not None else load_runtime_status(repo_root)
    snapshot = build_active_claims_snapshot(repo_root, status_payload, now=now)
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
    matches: List[Dict[str, Any]] = []
    for requested in requested_paths:
        for claim in active_claims:
            claim_session_id = str(claim.get("session_id") or "").strip()
            if owner_session_id and claim_session_id != owner_session_id:
                continue
            claim_path = str(claim.get("path") or claim.get("scope_id") or "")
            if not claim_path or not _path_scope_overlaps(requested, claim_path):
                continue
            matches.append(
                {
                    "requested_path": requested,
                    "session_id": claim.get("session_id"),
                    "actor": claim.get("actor"),
                    "claim_id": claim.get("claim_id"),
                    "claim_path": claim_path,
                    "claim_intent": claim.get("claim_intent"),
                    "conflict_scope_kind": claim.get("conflict_scope_kind"),
                    "conflict_mode": claim.get("conflict_mode"),
                    "leased_until": claim.get("leased_until"),
                }
            )
    return matches


def _unique_nonempty(values: Iterable[Any]) -> List[str]:
    seen: List[str] = []
    for value in values:
        token = str(value or "").strip()
        if token and token not in seen:
            seen.append(token)
    return seen


def _write_profile_names(write_profiles: Iterable[Any]) -> List[str]:
    names: List[str] = []
    for profile in write_profiles:
        if isinstance(profile, Mapping):
            value = profile.get("profile") or profile.get("name")
        else:
            value = profile
        token = str(value or "").strip()
        if token and token not in names:
            names.append(token)
    return names


def _contention_collision_claim_path(collision: Mapping[str, Any]) -> str:
    claim = collision.get("claim") if isinstance(collision.get("claim"), Mapping) else {}
    return str(
        collision.get("claim_path")
        or collision.get("path")
        or claim.get("path")
        or claim.get("scope_id")
        or ""
    ).strip()


def _contention_collision_claim_id(collision: Mapping[str, Any]) -> str:
    claim = collision.get("claim") if isinstance(collision.get("claim"), Mapping) else {}
    return str(collision.get("claim_id") or claim.get("claim_id") or "").strip()


def _contention_collision_lease(collision: Mapping[str, Any]) -> str:
    claim = collision.get("claim") if isinstance(collision.get("claim"), Mapping) else {}
    return str(collision.get("leased_until") or claim.get("leased_until") or "").strip()


def _contention_collision_requested_surface(collision: Mapping[str, Any]) -> str:
    claim = collision.get("claim") if isinstance(collision.get("claim"), Mapping) else {}
    return str(
        collision.get("requested_path")
        or collision.get("path")
        or collision.get("scope_id")
        or claim.get("path")
        or claim.get("scope_id")
        or claim.get("td_id")
        or claim.get("work_item_id")
        or ""
    ).strip()


def _path_claim_matches_surface(surface: str, claim: Mapping[str, Any]) -> bool:
    claim_path = str(claim.get("claim_path") or claim.get("path") or claim.get("scope_id") or "")
    if not surface or not claim_path:
        return False
    return _path_scope_overlaps(surface, claim_path)


def _session_preflight_command_for_mutation_route(
    *,
    explicit_paths: Sequence[Any] | None = None,
    write_profiles: Sequence[Any] | None = None,
    requester_session_id: str | None = None,
) -> str:
    parts: List[str] = []
    requester = str(requester_session_id or "").strip()
    if requester:
        parts.append(f"--session-id {_quote_cli(requester)}")
    else:
        parts.append("--session-slug <slug>")
    for profile in _unique_nonempty(write_profiles or []):
        parts.append(f"--write-profile {_quote_cli(profile)}")
    for path in _unique_nonempty(explicit_paths or []):
        parts.append(f"--path {_quote_cli(path)}")
    parts.append("--require-exclusive")
    return _wl_command("session-preflight", *parts)


def build_pre_mutation_route_selector(
    *,
    requested_paths: Sequence[Any] | None = None,
    explicit_paths: Sequence[Any] | None = None,
    write_profiles: Sequence[Any] | None = None,
    collisions: Sequence[Mapping[str, Any]] | None = None,
    source_input_paths: Sequence[Any] | None = None,
    source_input_collisions: Sequence[Mapping[str, Any]] | None = None,
    same_session_claims: Sequence[Mapping[str, Any]] | None = None,
    requester_session_id: str | None = None,
    require_exclusive: bool = True,
) -> Dict[str, Any]:
    """Classify the legal pre-mutation lane for requested Work Ledger scopes."""
    requested_surfaces = _unique_nonempty(requested_paths or [])
    explicit_surfaces = _unique_nonempty(explicit_paths or requested_surfaces)
    profiles = _write_profile_names(write_profiles or [])
    collision_rows = [row for row in list(collisions or []) if isinstance(row, Mapping)]
    source_collision_rows = [
        row for row in list(source_input_collisions or []) if isinstance(row, Mapping)
    ]
    owner_claim_rows = [
        row for row in list(same_session_claims or []) if isinstance(row, Mapping)
    ]
    owned_requested_surfaces = [
        surface
        for surface in requested_surfaces
        if any(_path_claim_matches_surface(surface, claim) for claim in owner_claim_rows)
    ]
    unclaimed_requested_surfaces = [
        surface for surface in requested_surfaces if surface not in owned_requested_surfaces
    ]
    requester = str(requester_session_id or "").strip()
    preflight_command = _session_preflight_command_for_mutation_route(
        explicit_paths=explicit_surfaces,
        write_profiles=profiles,
        requester_session_id=requester,
    )

    if (collision_rows or source_collision_rows) and require_exclusive:
        decision = (
            "source_input_owner_coordination_required"
            if source_collision_rows and not collision_rows
            else "owner_coordination_required"
        )
        required_next_lane = "coordinate_with_owner_or_switch_disjoint"
        required_next_command = "contention_envelope.owner_sessions[].coordination_brief_command"
        mutation_allowed_now = False
    elif collision_rows or source_collision_rows:
        decision = "watch_owner_claims_before_mutation"
        required_next_lane = "rerun_with_require_exclusive_or_claim_scope"
        required_next_command = _wl_command(
            "mutation-check",
            *[f"--path {_quote_cli(path)}" for path in explicit_surfaces],
            *[f"--write-profile {_quote_cli(profile)}" for profile in profiles],
            "--require-exclusive",
        )
        mutation_allowed_now = False
    elif not requested_surfaces and not profiles:
        decision = "read_only_or_no_mutation_scope"
        required_next_lane = "no_mutation_claim_needed"
        required_next_command = None
        mutation_allowed_now = False
    elif not requester:
        decision = "session_preflight_required_before_mutation"
        required_next_lane = "session_preflight"
        required_next_command = preflight_command
        mutation_allowed_now = False
    elif profiles and not requested_surfaces:
        decision = "claim_required_before_mutation"
        required_next_lane = "claim_current_session"
        required_next_command = preflight_command
        mutation_allowed_now = False
    elif unclaimed_requested_surfaces:
        decision = "claim_required_before_mutation"
        required_next_lane = "claim_current_session"
        required_next_command = preflight_command
        mutation_allowed_now = False
    else:
        decision = "same_owner_continuation"
        required_next_lane = "proceed_with_claimed_mutation"
        required_next_command = None
        mutation_allowed_now = True
    mutation_check_parts = [
        *[f"--path {_quote_cli(path)}" for path in explicit_surfaces],
        *[f"--write-profile {_quote_cli(profile)}" for profile in profiles],
        "--require-exclusive",
    ]
    if requester:
        mutation_check_parts.append(f"--session-id {_quote_cli(requester)}")

    return {
        "schema": "work_ledger_pre_mutation_route_selector_v1",
        "decision": decision,
        "mutation_allowed_now": mutation_allowed_now,
        "required_next_lane": required_next_lane,
        "required_next_command": required_next_command,
        "rule": (
            "A clear claim scan means no active foreign owner collision; it is not "
            "edit authority by itself. Mutating actors need same-session claim "
            "coverage or must run session-preflight before the first write."
        ),
        "requested_path_count": len(requested_surfaces),
        "requested_paths": requested_surfaces,
        "explicit_path_count": len(explicit_surfaces),
        "write_profiles": profiles,
        "foreign_collision_count": len(collision_rows),
        "source_input_path_count": len(_unique_nonempty(source_input_paths or [])),
        "source_input_collision_count": len(source_collision_rows),
        "same_session_claim_count": len(owner_claim_rows),
        "same_session_claims": owner_claim_rows,
        "unclaimed_requested_path_count": len(unclaimed_requested_surfaces),
        "unclaimed_requested_paths": unclaimed_requested_surfaces,
        "commands": {
            "session_preflight": preflight_command,
            "mutation_check": _wl_command("mutation-check", *mutation_check_parts),
        },
        "source_input_policy": (
            "source inputs with active foreign claims block generated/source-coupled mutation; "
            "when clear, still prove source inputs are committed, same-session-owned, or "
            "clean-snapshot documented before landing generated outputs"
            if source_input_paths
            else "not_declared_for_selected_profiles"
        ),
        "allowed_parallel_lanes": [
            "same_owner_continuation",
            "owner_acknowledged_handoff_or_release",
            "claimed_disjoint_companion_surface",
            "append_only_or_commutative_ledger_lane",
            "blocked_receipt_with_exact_owner_and_reentry_condition",
        ],
    }


def build_shared_substrate_contention_envelope(
    *,
    requested_paths: Sequence[Any] | None = None,
    collisions: Sequence[Mapping[str, Any]] | None = None,
    requester_session_id: str | None = None,
    require_exclusive: bool = True,
) -> Dict[str, Any]:
    """Build the first responder packet for claimed shared-substrate contention.

    A live claim should block unsafe mutation, but it should also expose the
    existing owner surface and the legal coordination moves. This envelope keeps
    agents from stopping at "file is claimed" prose.
    """
    collision_rows = [row for row in list(collisions or []) if isinstance(row, Mapping)]
    requested_surfaces = _unique_nonempty(
        list(requested_paths or [])
        + [_contention_collision_requested_surface(row) for row in collision_rows]
    )
    requester = str(requester_session_id or "").strip()
    owner_map: Dict[str, Dict[str, Any]] = {}
    for row in collision_rows:
        session_id = str(row.get("session_id") or "unknown").strip() or "unknown"
        owner = owner_map.setdefault(
            session_id,
            {
                "session_id": session_id,
                "actor": row.get("actor"),
                "held_paths": [],
                "requested_paths": [],
                "claim_ids": [],
                "leased_until_max": None,
            },
        )
        claim_path = _contention_collision_claim_path(row)
        if claim_path and claim_path not in owner["held_paths"]:
            owner["held_paths"].append(claim_path)
        requested = _contention_collision_requested_surface(row)
        if requested and requested not in owner["requested_paths"]:
            owner["requested_paths"].append(requested)
        claim_id = _contention_collision_claim_id(row)
        if claim_id and claim_id not in owner["claim_ids"]:
            owner["claim_ids"].append(claim_id)
        leased_until = _contention_collision_lease(row)
        if leased_until and (
            not owner["leased_until_max"] or leased_until > owner["leased_until_max"]
        ):
            owner["leased_until_max"] = leased_until
        if not owner.get("actor") and row.get("actor"):
            owner["actor"] = row.get("actor")

    owner_sessions: List[Dict[str, Any]] = []
    for session_id, owner in sorted(owner_map.items()):
        held_paths = list(owner.get("held_paths") or [])
        first_held = held_paths[0] if held_paths else "<held-path-or-surface>"
        claim_ids = list(owner.get("claim_ids") or [])
        release_selector = (
            f"--claim-id {_quote_cli(claim_ids[0])}"
            if claim_ids
            else "--path <held-path-or-surface>"
        )
        brief_parts = [
            f"--target-session-id {_quote_cli(session_id)}",
            "--target-class settlement_obligation_owner",
            "--requested-action release_after_landing",
            "--result requested",
            "--coordination-brief",
            "--requester-label '<requesting thread>'",
            "--blocked-on '<blocking condition or missing companion contract>'",
            "--validation-status '<current validation state>'",
            f"--held-path {_quote_cli(first_held)}",
        ]
        if requester:
            brief_parts.insert(5, f"--requester-session-id {_quote_cli(requester)}")
        owner_sessions.append(
            {
                **owner,
                "read_full_session_command": _wl_command(
                    "session-status",
                    f"--session-id {_quote_cli(session_id)} --full",
                ),
                "existing_surface_readback": {
                    "rule": (
                        "Treat the owner session as the current surface for this "
                        "shared substrate slice before creating a parallel surface "
                        "or recutting the same path elsewhere."
                    ),
                    "command": _wl_command(
                        "session-status",
                        f"--session-id {_quote_cli(session_id)} --full",
                    ),
                    "held_surface": first_held,
                    "reentry_condition": (
                        "owner releases the claim, lands the held surface, or accepts "
                        "a handoff/fan-in request for the named held surface"
                    ),
                },
                "coordination_brief_command": _wl_command(
                    "session-yield-request",
                    *brief_parts,
                ),
                "handoff_or_release_request": {
                    "command": _wl_command(
                        "session-yield-request",
                        *brief_parts,
                    ),
                    "use_when": (
                        "your validation or landing is blocked by this live owner "
                        "claim and the remaining work cannot be split onto a "
                        "genuinely disjoint path"
                    ),
                },
                "release_claim_command_template": _wl_command(
                    "session-release-claim",
                    f"--session-id {_quote_cli(session_id)}",
                    release_selector,
                    "--reason handoff_or_landed_elsewhere",
                ),
            }
        )

    mutation_check_args = [
        f"--path {_quote_cli(path)}"
        for path in requested_surfaces
        if path and not path.startswith("td_")
    ]
    claim_session_filter_args = [
        f"--path {_quote_cli(path)}"
        for path in requested_surfaces
        if path and not path.startswith("td_")
    ]
    if require_exclusive:
        mutation_check_args.append("--require-exclusive")
    if requester:
        mutation_check_args.append(f"--session-id {_quote_cli(requester)}")

    status = "blocked_by_live_owner_claims" if collision_rows and require_exclusive else (
        "watch_live_owner_claims" if collision_rows else "clear"
    )
    return {
        "schema": SHARED_SUBSTRATE_CONTENTION_ENVELOPE_SCHEMA,
        "status": status,
        "requested_surfaces": requested_surfaces,
        "collision_count": len(collision_rows),
        "owner_session_count": len(owner_sessions),
        "owner_sessions": owner_sessions,
        "first_response_rule": (
            "A live owner claim blocks direct mutation, not discovery or coordination. "
            "Read the owner session, reuse or wait for its existing surface, send a "
            "coordination brief, or switch only to a genuinely disjoint claimed lane."
        ),
        "failure_response_floor": (
            "Do not report only 'I did not edit because the path was claimed'. Include "
            "the owner session, held surface, lease, blocking condition, coordination "
            "request command, and re-entry condition."
        ),
        "blocked_frontier_contract": {
            "schema": "shared_substrate_blocked_frontier_contract_v0",
            "status": "active" if owner_sessions else "no_live_owner_frontier",
            "rule": (
                "A live claim on the same shared substrate is a merge frontier, not "
                "a terminal no-op and not permission to clone the surface. Read the "
                "owner session, reuse its current surface, request release or handoff "
                "when fan-in is blocked, or split only truly disjoint companion paths."
            ),
            "accepted_parallelism": [
                "same_owner_continuation",
                "owner_acknowledged_handoff_or_release",
                "claimed_disjoint_companion_surface",
                "blocked_receipt_with_exact_owner_and_reentry_condition",
            ],
            "invalid_parallelism": [
                "parallel_unclaimed_edit_to_the_same_path",
                "new_parallel_surface_created_only_because_owner_path_is_claimed",
                "CAP_or_chat_only_closeout_when_a_disjoint_owner_lane_exists",
            ],
            "required_blocked_receipt_fields": [
                "owner_session_id",
                "held_surface",
                "leased_until",
                "blocking_condition",
                "coordination_request_command",
                "reentry_condition",
            ],
        },
        "surface_discovery_commands": {
            "claim_session_cards": _wl_command(
                "session-claims",
                "--refresh --session-summary --limit 12 --cards-only",
                *claim_session_filter_args,
            ),
            "mutation_check": _wl_command("mutation-check", *mutation_check_args),
        },
        "safe_continuation_lanes": [
            {
                "lane": "read_existing_owner_surface",
                "allowed": True,
                "command_field": "owner_sessions[].read_full_session_command",
            },
            {
                "lane": "request_land_release_or_handoff",
                "allowed": bool(owner_sessions),
                "command_field": "owner_sessions[].coordination_brief_command",
            },
            {
                "lane": "claim_disjoint_sibling_surface",
                "allowed": True,
                "command": _wl_command(
                    "session-preflight",
                    "--session-id <your-session-id>",
                    "--path <disjoint-path>",
                    "--heartbeat-current-pass-line '<public current pass>'",
                ),
            },
            {
                "lane": "capture_blocked_residual",
                "allowed": True,
                "condition": (
                    "Only when owner-surface coordination cannot proceed and the "
                    "blocked contract needs a durable re-entry condition."
                ),
            },
        ],
    }


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
        "seed_speed_status": "./repo-python tools/meta/factory/work_ledger.py session-status --seed-speed --limit 12",
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


def rebuild_runtime_status(
    payload: Mapping[str, Any],
    *,
    repo_root: Path | None = None,
) -> Dict[str, Any]:
    effective_repo_root = repo_root or _REBUILD_RUNTIME_STATUS_REPO_ROOT
    status = _default_status()
    # Carry the cumulative count of ended sessions retired to the archive sidecar
    # so display surfaces can still report a true all-time total even though the
    # live sessions map only holds the retained (recent) window.
    status["archived_ended_sessions_total"] = int(payload.get("archived_ended_sessions_total") or 0)
    sessions = payload.get("sessions") if isinstance(payload.get("sessions"), Mapping) else {}
    normalized_sessions: Dict[str, Dict[str, Any]] = {}
    stale_sessions: List[Dict[str, Any]] = []
    counts = {
        "sessions_total": 0,
        "active_sessions": 0,
        "stale_sessions": 0,
        "stale_append_obligations": 0,
        "stale_claim_only_sessions": 0,
        "sessions_with_activity": 0,
        "sessions_with_ledger_append": 0,
        "open_todos_touched_this_session": 0,
        "session_had_no_ledger_append": 0,
        "archived_ended_sessions": int(payload.get("archived_ended_sessions_total") or 0),
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
        _compact_inactive_external_session_payload(session)
        _compact_ended_released_claims(session)
        _compact_ended_external_metadata(session)
        _compact_ended_pass_heartbeat(session)
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
            if _session_requires_append_evidence(session):
                counts["stale_append_obligations"] += 1
            else:
                counts["stale_claim_only_sessions"] += 1
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
    overview = build_session_cohort_overview(status, repo_root=effective_repo_root)
    status["cohort_overview"] = overview
    status["triggers"] = {
        "stale_session_ready": counts["stale_append_obligations"] > 0,
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


def _retention_int_env(name: str, default: int) -> int:
    raw = os.environ.get(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return max(int(str(raw).strip()), 0)
    except ValueError:
        return default


def _ended_session_retention_config() -> tuple[int, int, int]:
    """(high_water, keep_max, min_age_days) for ended-session retention."""
    return (
        _retention_int_env(ENDED_SESSION_RETENTION_HIGH_WATER_ENV, ENDED_SESSION_RETENTION_HIGH_WATER),
        _retention_int_env(ENDED_SESSION_RETENTION_MAX_ENV, ENDED_SESSION_RETENTION_MAX),
        _retention_int_env(ENDED_SESSION_RETENTION_MIN_AGE_DAYS_ENV, ENDED_SESSION_RETENTION_MIN_AGE_DAYS),
    )


def _session_is_retention_evictable(session: Mapping[str, Any]) -> bool:
    """Only long-ended, non-stale sessions holding no live claim may be evicted.

    Active sessions, stale rows (they still drive attention surfaces), and any
    session still holding an unreleased/unexpired claim are never eligible.
    """
    if not isinstance(session, Mapping):
        return False
    if not session.get("ended_at"):
        return False
    if bool(session.get("stale")):
        return False
    for claim in session.get("claims") or []:
        if isinstance(claim, Mapping) and not (claim.get("released_at") or claim.get("expired_at")):
            return False
    return True


def _append_archived_sessions(
    repo_root: Path,
    rows: Sequence[tuple[str, Mapping[str, Any]]],
) -> None:
    """Append evicted ended sessions to the append-only archive sidecar.

    One JSON object per line ({session_id, archived_at, session}). The live file
    stays the hot read surface; the sidecar preserves the full record for
    forensics and explicit session-id drilldown via load_archived_session().
    """
    if not rows:
        return
    path = _runtime_status_sessions_archive_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    archived_at = work_ledger.utc_now()
    payload = "".join(
        json.dumps(
            {"session_id": str(session_id), "archived_at": archived_at, "session": session},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for session_id, session in rows
    )
    with path.open("a", encoding="utf-8") as handle:
        handle.write(payload)
    # Rotate cold storage so the archive itself cannot grow without bound: once
    # over the cap, the live archive becomes the single ".1" generation and the
    # next append starts fresh. O(1) rename — no full-file read.
    max_bytes = _retention_int_env(ENDED_SESSION_ARCHIVE_MAX_BYTES_ENV, ENDED_SESSION_ARCHIVE_MAX_BYTES)
    try:
        if max_bytes > 0 and path.stat().st_size > max_bytes:
            os.replace(path, path.with_name(path.name + ".1"))
    except OSError:
        pass


def _apply_ended_session_retention(repo_root: Path, status: Dict[str, Any]) -> Dict[str, Any]:
    """Archive + drop old ended sessions so runtime_status.json stays bounded.

    No-op unless the evictable ended-session count exceeds the high-water mark.
    Keeps all active sessions, every stale session, every session holding a live
    claim, all ended sessions newer than the min-age window, and the most-recent
    ``keep_max`` ended sessions by ``ended_at``. Evicted sessions are appended to
    the archive sidecar and removed from ``status['sessions']``; a cumulative
    counter preserves the all-time total. Must be called under the runtime lock.
    Returns a receipt describing the action.
    """
    high_water, keep_max, min_age_days = _ended_session_retention_config()
    sessions = status.get("sessions")
    if not isinstance(sessions, Mapping):
        return {"applied": False, "reason": "no_sessions"}
    evictable = [
        (str(session_id), session)
        for session_id, session in sessions.items()
        if _session_is_retention_evictable(session)
    ]
    if len(evictable) <= high_water:
        return {
            "applied": False,
            "reason": "below_high_water",
            "evictable": len(evictable),
            "high_water": high_water,
        }
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(min_age_days, 0))
    # Freshest ended sessions first, so the first ``keep_max`` indices are the
    # most recent by ended_at (falling back to last activity for missing stamps).
    evictable.sort(
        key=lambda item: str(item[1].get("ended_at") or item[1].get("last_activity_at") or ""),
        reverse=True,
    )
    evict_ids: set[str] = set()
    evict_rows: List[tuple[str, Mapping[str, Any]]] = []
    for index, (session_id, session) in enumerate(evictable):
        ended_dt = _parse_iso_datetime(session.get("ended_at"))
        within_age = ended_dt is not None and ended_dt >= cutoff
        within_keep_window = index < keep_max
        if within_age or within_keep_window:
            continue
        evict_ids.add(session_id)
        evict_rows.append((session_id, session))
    if not evict_rows:
        return {"applied": False, "reason": "nothing_beyond_window", "evictable": len(evictable)}
    _append_archived_sessions(repo_root, evict_rows)
    status["sessions"] = {
        session_id: session
        for session_id, session in sessions.items()
        if str(session_id) not in evict_ids
    }
    status["archived_ended_sessions_total"] = (
        int(status.get("archived_ended_sessions_total") or 0) + len(evict_rows)
    )
    return {
        "applied": True,
        "evicted": len(evict_rows),
        "kept_ended": len(evictable) - len(evict_rows),
        "archived_ended_sessions_total": status["archived_ended_sessions_total"],
        "archive_path": str(RUNTIME_STATUS_SESSIONS_ARCHIVE_REL),
    }


def load_archived_session(repo_root: Path, session_id: str) -> Optional[Dict[str, Any]]:
    """Return the most-recently-archived record for ``session_id`` or None.

    Lets an explicit drilldown for a long-ended (evicted) session still resolve
    from the append-only archive sidecar. O(file), but drilldowns are rare and
    the per-line substring pre-filter skips JSON parsing for non-matches.
    """
    token = str(session_id or "").strip()
    if not token:
        return None
    base = _runtime_status_sessions_archive_path(repo_root)
    # Newest generation first; the rotated ".1" holds older evictions.
    for path in (base, base.with_name(base.name + ".1")):
        if not path.exists():
            continue
        found: Optional[Dict[str, Any]] = None
        try:
            with path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped or token not in stripped:
                        continue
                    try:
                        row = json.loads(stripped)
                    except ValueError:
                        continue
                    if str(row.get("session_id") or "") == token:
                        found = row  # keep scanning this file; last write wins
        except OSError:
            continue
        if found is not None:
            return found
    return None


def compact_runtime_status_sessions(repo_root: Path) -> Dict[str, Any]:
    """One-shot: archive + drop old ended sessions from the live file now.

    Acquires the runtime lock and rewrites runtime_status.json through the same
    retention path every write uses. Safe to run repeatedly (idempotent once the
    evictable set is below the high-water mark). Returns the retention receipt.
    """
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = dict(load_runtime_status(repo_root, rebuild=False))
        receipt = _apply_ended_session_retention(repo_root, status)
        if receipt.get("applied"):
            rebuilt = _rebuild_runtime_status_with_repo_root(status, repo_root)
            _atomic_write_runtime_json(_runtime_status_path(repo_root), rebuilt)
            write_active_claims_snapshot(repo_root, rebuilt)
        return receipt


def _write_runtime_status(repo_root: Path, status: Mapping[str, Any]) -> Dict[str, Any]:
    # Copy the top-level mapping so retention can swap in a pruned sessions dict
    # without mutating the caller's object; retention is a no-op below the
    # high-water mark, so normal writes pay only a cheap count.
    status = dict(status)
    _apply_ended_session_retention(repo_root, status)
    rebuilt = _rebuild_runtime_status_with_repo_root(status, repo_root)
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


def _prepare_external_session_observations(
    repo_root: Path,
    *,
    observations: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
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
    return prepared


def _apply_external_session_observations_to_status(
    status: Dict[str, Any],
    *,
    prepared: Sequence[Mapping[str, Any]],
    observed_at: str,
) -> List[Dict[str, Any]]:
    if not prepared:
        return []
    sessions = dict(status.get("sessions") or {})
    results: List[Dict[str, Any]] = []
    for row in prepared:
        token = str(row["session_id"])
        existing = dict(sessions.get(token) or {})
        created = not bool(existing)
        signal_iso = str(row["signal_iso"])
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
    return results


def observe_external_sessions(
    repo_root: Path,
    *,
    observations: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    """Batch-upsert host-observed sessions with one runtime-status rebuild/write."""
    prepared = _prepare_external_session_observations(repo_root, observations=observations)
    if not prepared:
        return []
    observed_at = work_ledger.utc_now()
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        results = _apply_external_session_observations_to_status(
            status,
            prepared=prepared,
            observed_at=observed_at,
        )
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
            f"session-heartbeat --session-id {payload.get('session_id')} --state inspecting "
            "--current-pass-line \"<public current pass>\" "
            "--last-pass-result-line \"<public previous result>\" "
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
    pass_heartbeat: Mapping[str, Any] | None = None,
    external_observations: Sequence[Mapping[str, Any]] | None = None,
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
    initial_pass_heartbeat = None
    prepared_external_observations = _prepare_external_session_observations(
        repo_root,
        observations=external_observations or [],
    )
    external_observation_results: List[Dict[str, Any]] = []
    # Housekeeping: expire old leases, sweep crashed orphan sessions BEFORE
    # minting this session so the new seed sees a clean cohort view and never
    # sweeps itself. Both are folded into the bootstrap transaction so the hot
    # preflight path reads and rebuilds the runtime projection once.
    sweep_report: Dict[str, Any] = {"orphan_sweep": None, "claim_expiry": None}
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        if prepared_external_observations:
            external_observation_results = _apply_external_session_observations_to_status(
                status,
                prepared=prepared_external_observations,
                observed_at=work_ledger.utc_now(),
            )
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
            sessions = dict(status.get("sessions") or {})
        if isinstance(pass_heartbeat, Mapping):
            session = dict(sessions.get(session_id) or {})
            initial_pass_heartbeat = _apply_pass_heartbeat_to_session(
                session,
                session_id=session_id,
                pass_state=str(pass_heartbeat.get("pass_state") or "inspecting"),
                current_pass_line=pass_heartbeat.get("current_pass_line"),
                last_pass_result_line=pass_heartbeat.get("last_pass_result_line"),
                td_id=pass_heartbeat.get("td_id"),
                scope_refs=pass_heartbeat.get("scope_refs") or [],
                pass_id=pass_heartbeat.get("pass_id"),
                source=str(pass_heartbeat.get("source") or "manual_cli"),
            )
            sessions[session_id] = session
            status["sessions"] = sessions
        saved = _write_runtime_status(repo_root, status)
        for result in external_observation_results:
            result["generated_at"] = saved.get("generated_at")
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
        "pass_heartbeat": initial_pass_heartbeat or {},
        "external_observations": external_observation_results,
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
    with work_ledger.file_lock(_runtime_lock_path(repo_root)):
        status = _load_runtime_status_for_session_scan(repo_root)
        sessions = dict(status.get("sessions") or {})
        session = dict(sessions.get(session_id) or {})
        if not session:
            return status
        _apply_pass_heartbeat_to_session(
            session,
            session_id=session_id,
            pass_state=pass_state,
            current_pass_line=current_pass_line,
            last_pass_result_line=last_pass_result_line,
            td_id=td_id,
            scope_refs=scope_refs,
            pass_id=pass_id,
            source=source,
        )
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


def _normalize_claim_intent(value: Any) -> str:
    token = str(value or CLAIM_INTENT_HARD_MUTATION).strip()
    if token not in CLAIM_INTENTS:
        return CLAIM_INTENT_HARD_MUTATION
    return token


def _normalize_claim_conflict_scope_kind(value: Any, fallback: str | None = None) -> str | None:
    token = str(value or fallback or "").strip()
    if not token:
        return None
    if token not in CLAIM_CONFLICT_SCOPE_KINDS:
        return fallback if fallback in CLAIM_CONFLICT_SCOPE_KINDS else None
    return token


def _claim_conflict_mode(claim: Mapping[str, Any]) -> str:
    intent = _normalize_claim_intent(claim.get("claim_intent"))
    if intent in BLOCKING_CLAIM_INTENTS:
        return "blocking"
    return "cooperative"


def _looks_like_work_item_id(value: object) -> bool:
    token = str(value or "").strip()
    return bool(token and not token.startswith("td_") and WORK_ITEM_ID_RE.fullmatch(token))


def _looks_like_repo_path_token(value: object) -> bool:
    token = str(value or "").strip()
    if not token:
        return False
    if token.startswith("td_") or _looks_like_work_item_id(token):
        return False
    return token.startswith("/") or "/" in token


def _normalize_path_token_for_claim_overlap(
    path_token: str,
    *,
    repo_root: Path | None = None,
) -> str:
    token = str(path_token or "").strip()
    if not token:
        return ""
    if repo_root is not None:
        try:
            return _normalize_repo_claim_path(repo_root, token)
        except ValueError:
            pass
    if token.startswith("./"):
        return token[2:]
    return token


def _path_token_claimed_by_path_claim(
    path_token: str,
    claimed_paths: Iterable[str],
    *,
    repo_root: Path | None = None,
) -> bool:
    token = _normalize_path_token_for_claim_overlap(path_token, repo_root=repo_root)
    if not token:
        return False
    for claimed in claimed_paths:
        claim_token = _normalize_path_token_for_claim_overlap(
            str(claimed or ""),
            repo_root=repo_root,
        )
        if not claim_token:
            continue
        try:
            if _path_scope_overlaps(claim_token, token):
                return True
        except (TypeError, ValueError):
            if claim_token == token:
                return True
    return False


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


def _active_same_scope_claim_index(
    claims: Sequence[Any],
    target_claim: Mapping[str, Any],
    *,
    now: datetime,
) -> int | None:
    target_key = _claim_scope_key(target_claim)
    if not target_key:
        return None
    for index, claim in enumerate(claims):
        if not isinstance(claim, Mapping):
            continue
        if not _is_claim_active(claim, now=now):
            continue
        if _claim_scope_key(claim) == target_key:
            return index
    return None


def _extend_claim_record(
    claim: Mapping[str, Any],
    *,
    leased_until: str,
    note: str | None,
    require_exclusive: bool,
    claim_intent: str | None = None,
    conflict_scope_kind: str | None = None,
) -> tuple[Dict[str, Any], bool]:
    updated = dict(claim)
    changed = False
    incoming_lease = _parse_iso_datetime(leased_until)
    current_lease = _parse_iso_datetime(updated.get("leased_until"))
    if incoming_lease is not None and (current_lease is None or incoming_lease > current_lease):
        updated["leased_until"] = leased_until
        changed = True
    note_token = str(note or "").strip()
    if note_token and note_token != str(updated.get("note") or "").strip():
        updated["note"] = note_token
        changed = True
    if require_exclusive and not bool(updated.get("require_exclusive")):
        updated["require_exclusive"] = True
        changed = True
    incoming_intent = _normalize_claim_intent(claim_intent)
    existing_intent = _normalize_claim_intent(updated.get("claim_intent"))
    if incoming_intent != existing_intent and (
        existing_intent != CLAIM_INTENT_HARD_MUTATION
        or incoming_intent == CLAIM_INTENT_HARD_MUTATION
    ):
        updated["claim_intent"] = incoming_intent
        changed = True
    if "claim_intent" not in updated:
        updated["claim_intent"] = existing_intent
        changed = True
    scope_kind, _ = _normalize_claim_scope(updated)
    incoming_conflict_scope = _normalize_claim_conflict_scope_kind(conflict_scope_kind, scope_kind)
    existing_conflict_scope = _normalize_claim_conflict_scope_kind(
        updated.get("conflict_scope_kind"),
        scope_kind,
    )
    if incoming_conflict_scope and incoming_conflict_scope != existing_conflict_scope:
        updated["conflict_scope_kind"] = incoming_conflict_scope
        changed = True
    elif "conflict_scope_kind" not in updated and existing_conflict_scope:
        updated["conflict_scope_kind"] = existing_conflict_scope
        changed = True
    return updated, changed


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


def _claim_scopes_conflict(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if not _claim_scopes_overlap(left, right):
        return False
    return "blocking" in {_claim_conflict_mode(left), _claim_conflict_mode(right)}


def _compact_claim(claim: Mapping[str, Any]) -> Dict[str, Any]:
    scope_kind, scope_id = _normalize_claim_scope(claim)
    td_id = str(claim.get("td_id") or "").strip()
    path = str(claim.get("path") or "").strip()
    work_item_id = str(claim.get("work_item_id") or "").strip()
    claim_intent = _normalize_claim_intent(claim.get("claim_intent"))
    conflict_scope_kind = _normalize_claim_conflict_scope_kind(
        claim.get("conflict_scope_kind"),
        scope_kind,
    )
    return {
        "claim_id": str(claim.get("claim_id") or ""),
        "scope_kind": scope_kind or None,
        "scope_id": scope_id or None,
        "claim_intent": claim_intent,
        "conflict_scope_kind": conflict_scope_kind,
        "conflict_mode": _claim_conflict_mode(claim),
        "require_exclusive": bool(claim.get("require_exclusive")),
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


def _collision_has_existing_exclusive_claim(collisions: Sequence[Mapping[str, Any]]) -> bool:
    for collision in collisions:
        if not isinstance(collision, Mapping):
            continue
        claim = collision.get("claim")
        if isinstance(claim, Mapping) and bool(claim.get("require_exclusive")):
            return True
    return False


def _claim_collision_refusal_reason(
    *,
    require_exclusive: bool,
    collisions: Sequence[Mapping[str, Any]],
) -> str | None:
    if not collisions:
        return None
    if require_exclusive:
        return "exclusive_claim_refused_due_to_collision"
    if _collision_has_existing_exclusive_claim(collisions):
        return "claim_refused_due_to_existing_exclusive_claim"
    return None


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
) -> List[Dict[str, Any]]:
    requests: List[Dict[str, Any]] = []
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
        claim_intent = _normalize_claim_intent(scope.get("claim_intent"))
        conflict_scope_kind = _normalize_claim_conflict_scope_kind(
            scope.get("conflict_scope_kind"),
            scope_kind_token,
        )
        requests.append(
            {
                "scope_kind": scope_kind_token,
                "scope_id": scope_token,
                "claim_intent": claim_intent,
                "conflict_scope_kind": conflict_scope_kind,
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
    requests: Sequence[Mapping[str, Any]],
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
                if not _claim_scopes_conflict(target_claim, claim):
                    continue
                collisions.append(
                    {
                        "session_id": str(other_id),
                        "actor": str(other.get("actor") or "unknown"),
                        "claim": _compact_claim(claim),
                    }
                )
        refusal_reason = _claim_collision_refusal_reason(
            require_exclusive=require_exclusive,
            collisions=collisions,
        )
        if refusal_reason is not None:
            contention_envelope = build_shared_substrate_contention_envelope(
                requested_paths=[
                    target_claim["path"]
                    or target_claim["td_id"]
                    or target_claim["work_item_id"]
                    or target_claim["scope_id"]
                ],
                collisions=collisions,
                requester_session_id=token,
                require_exclusive=True,
            )
            results.append(
                {
                    "schema": "work_ledger_claim_result_v1",
                    "status": "refused",
                    "reason": refusal_reason,
                    "session_id": token,
                    "scope_kind": target_claim["scope_kind"],
                    "scope_id": target_claim["scope_id"],
                    "td_id": target_claim["td_id"],
                    "path": target_claim["path"],
                    "work_item_id": target_claim["work_item_id"],
                    "collisions": collisions,
                    "contention_envelope": contention_envelope,
                }
            )
            continue

        existing_index = _active_same_scope_claim_index(claims, target_claim, now=now)
        if existing_index is not None:
            updated_claim, changed = _extend_claim_record(
                dict(claims[existing_index]),
                leased_until=leased_until,
                note=note,
                require_exclusive=require_exclusive,
                claim_intent=str(target_claim.get("claim_intent") or ""),
                conflict_scope_kind=str(target_claim.get("conflict_scope_kind") or ""),
            )
            claims[existing_index] = updated_claim
            claimed_result_indexes.append(len(results))
            base_status = "extended" if changed else "already_claimed"
            results.append(
                {
                    "schema": "work_ledger_claim_result_v1",
                    "status": base_status if not collisions else f"{base_status}_with_collision",
                    "session_id": token,
                    "scope_kind": target_claim["scope_kind"],
                    "scope_id": target_claim["scope_id"],
                    "td_id": target_claim["td_id"],
                    "path": target_claim["path"],
                    "work_item_id": target_claim["work_item_id"],
                    "claim": _compact_claim(updated_claim),
                    "collisions": collisions,
                    **(
                        {
                            "contention_envelope": build_shared_substrate_contention_envelope(
                                requested_paths=[
                                    target_claim["path"]
                                    or target_claim["td_id"]
                                    or target_claim["work_item_id"]
                                    or target_claim["scope_id"]
                                ],
                                collisions=collisions,
                                requester_session_id=token,
                                require_exclusive=False,
                            )
                        }
                        if collisions
                        else {}
                    ),
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
            "claim_intent": target_claim.get("claim_intent"),
            "conflict_scope_kind": target_claim.get("conflict_scope_kind"),
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
                **(
                    {
                        "contention_envelope": build_shared_substrate_contention_envelope(
                            requested_paths=[
                                target_claim["path"]
                                or target_claim["td_id"]
                                or target_claim["work_item_id"]
                                or target_claim["scope_id"]
                            ],
                            collisions=collisions,
                            requester_session_id=token,
                            require_exclusive=False,
                        )
                    }
                    if collisions
                    else {}
                ),
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
    claim_intent: str = CLAIM_INTENT_HARD_MUTATION,
    conflict_scope_kind: str | None = None,
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
    normalized_claim_intent = _normalize_claim_intent(claim_intent)
    normalized_conflict_scope_kind = _normalize_claim_conflict_scope_kind(
        conflict_scope_kind,
        scope_kind_token,
    )
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
            "claim_intent": normalized_claim_intent,
            "conflict_scope_kind": normalized_conflict_scope_kind,
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
                if not _claim_scopes_conflict(target_claim, claim):
                    continue
                collisions.append(
                    {
                        "session_id": str(other_id),
                        "actor": str(other.get("actor") or "unknown"),
                        "claim": _compact_claim(claim),
                    }
                )
        refusal_reason = _claim_collision_refusal_reason(
            require_exclusive=require_exclusive,
            collisions=collisions,
        )
        if refusal_reason is not None:
            return {
                "schema": "work_ledger_claim_result_v1",
                "status": "refused",
                "reason": refusal_reason,
                "session_id": token,
                "scope_kind": scope_kind_token,
                "scope_id": scope_token,
                "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
                "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
                "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
                "collisions": collisions,
                "contention_envelope": build_shared_substrate_contention_envelope(
                    requested_paths=[scope_token],
                    collisions=collisions,
                    requester_session_id=token,
                    require_exclusive=True,
                ),
            }

        claims = list(session.get("claims") or [])
        existing_index = _active_same_scope_claim_index(claims, target_claim, now=now)
        if existing_index is not None:
            updated_claim, changed = _extend_claim_record(
                dict(claims[existing_index]),
                leased_until=(now + lease).isoformat(),
                note=note,
                require_exclusive=require_exclusive,
                claim_intent=normalized_claim_intent,
                conflict_scope_kind=normalized_conflict_scope_kind,
            )
            claims[existing_index] = updated_claim
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
            base_status = "extended" if changed else "already_claimed"
            return {
                "schema": "work_ledger_claim_result_v1",
                "status": base_status if not collisions else f"{base_status}_with_collision",
                "session_id": token,
                "scope_kind": scope_kind_token,
                "scope_id": scope_token,
                "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
                "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
                "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
                "claim": _compact_claim(updated_claim),
                "collisions": collisions,
                "generated_at": saved.get("generated_at"),
                **(
                    {
                        "contention_envelope": build_shared_substrate_contention_envelope(
                            requested_paths=[scope_token],
                            collisions=collisions,
                            requester_session_id=token,
                            require_exclusive=False,
                        )
                    }
                    if collisions
                    else {}
                ),
            }

        claim_record = {
            "claim_id": mint_claim_id(),
            "scope_kind": scope_kind_token,
            "scope_id": scope_token,
            "td_id": scope_token if scope_kind_token == CLAIM_SCOPE_THREAD else "",
            "path": scope_token if scope_kind_token == CLAIM_SCOPE_PATH else "",
            "work_item_id": scope_token if scope_kind_token == CLAIM_SCOPE_WORK_ITEM else "",
            "claim_intent": normalized_claim_intent,
            "conflict_scope_kind": normalized_conflict_scope_kind,
            "claimed_at": now.isoformat(),
            "leased_until": (now + lease).isoformat(),
            "released_at": None,
            "expired_at": None,
            "note": str(note or "").strip() or None,
            "release_reason": None,
            "require_exclusive": bool(require_exclusive),
        }
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
        **(
            {
                "contention_envelope": build_shared_substrate_contention_envelope(
                    requested_paths=[scope_token],
                    collisions=collisions,
                    requester_session_id=token,
                    require_exclusive=False,
                )
            }
            if collisions
            else {}
        ),
    }


def claim_work_scopes(
    repo_root: Path,
    *,
    session_id: str,
    scopes: Sequence[Mapping[str, Any]],
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
    claim_intent: str = CLAIM_INTENT_HARD_MUTATION,
    conflict_scope_kind: str | None = None,
) -> List[Dict[str, Any]]:
    """Record multiple forward-looking leases with one runtime-status rebuild/write."""
    token = str(session_id or "").strip()
    if not token:
        raise ValueError("session_id is required for session-claim")
    scope_rows: list[dict[str, Any]] = []
    for scope in scopes:
        row = dict(scope)
        row.setdefault("claim_intent", claim_intent)
        if conflict_scope_kind is not None:
            row.setdefault("conflict_scope_kind", conflict_scope_kind)
        scope_rows.append(row)
    requests = _prepare_claim_scope_requests(repo_root, scope_rows)
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
    claim_intent: str = CLAIM_INTENT_HARD_MUTATION,
    conflict_scope_kind: str | None = None,
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
            claim_intent=claim_intent,
            conflict_scope_kind=conflict_scope_kind,
        )
    return claim_work_scope(
        repo_root,
        session_id=session_id,
        scope_kind=CLAIM_SCOPE_THREAD,
        scope_id=td_id,
        lease_minutes=lease_minutes,
        note=note,
        require_exclusive=require_exclusive,
        claim_intent=claim_intent,
        conflict_scope_kind=conflict_scope_kind,
    )


def claim_work_item(
    repo_root: Path,
    *,
    session_id: str,
    work_item_id: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
    claim_intent: str = CLAIM_INTENT_HARD_MUTATION,
    conflict_scope_kind: str | None = None,
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
        claim_intent=claim_intent,
        conflict_scope_kind=conflict_scope_kind,
    )


def claim_work_path(
    repo_root: Path,
    *,
    session_id: str,
    path: str,
    lease_minutes: float = 30.0,
    note: str | None = None,
    require_exclusive: bool = False,
    claim_intent: str = CLAIM_INTENT_HARD_MUTATION,
    conflict_scope_kind: str | None = None,
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
        claim_intent=claim_intent,
        conflict_scope_kind=conflict_scope_kind,
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
