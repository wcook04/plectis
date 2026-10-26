"""
SQLite-backed store for the always-on metabolism runtime.

[PURPOSE]
- Teleology: Provide one durable local store for metabolism events, jobs, runs,
  provider budgets, blackboard claims, heartbeats, and runtime settings so the
  daemon survives session loss and repeated hook firings.
- Mechanism: Own the SQLite schema, enable WAL mode, expose idempotent event/job
  insert helpers, and keep JSON payload handling consistent across daemon,
  hooks, and tests.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence


SCHEMA_VERSION = 4
_UNSET = object()
JOB_STATE_QUEUED = "queued"
JOB_STATE_CLAIMED = "claimed"
JOB_STATE_RUNNING = "running"
JOB_STATE_BLOCKED = "blocked"
JOB_STATE_COMPLETED = "completed"
JOB_STATE_FAILED = "failed"
JOB_STATE_RECOVERABLE = "recoverable"
JOB_STATE_PAUSED = "paused"
ACTIVE_JOB_STATES = frozenset(
    {
        JOB_STATE_QUEUED,
        JOB_STATE_CLAIMED,
        JOB_STATE_RUNNING,
        JOB_STATE_BLOCKED,
        JOB_STATE_RECOVERABLE,
        JOB_STATE_PAUSED,
    }
)
TERMINAL_JOB_STATES = frozenset({JOB_STATE_COMPLETED, JOB_STATE_FAILED})
DEFAULT_PROVIDER_BUDGETS: dict[str, dict[str, Any]] = {
    "chatgpt": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 300,
        "max_attempts": 5,
        "backoff_seconds": [300, 900, 1800],
    },
    "gemini": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 180,
        "max_attempts": 5,
        "backoff_seconds": [180, 600, 1200],
    },
    "claude": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 300,
        "max_attempts": 5,
        "backoff_seconds": [300, 900, 1800],
    },
    "codex": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 120,
        "max_attempts": 5,
        "backoff_seconds": [120, 600, 1200],
    },
    "nvidia": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 2,
        "max_attempts": 3,
        "backoff_seconds": [120, 600, 1200],
        "notes": "NVIDIA runtime owns request-level RPM pacing; metabolism gates batch concurrency.",
    },
    "openrouter_free": {
        "max_concurrent": 1,
        "min_seconds_between_dispatch": 1800,
        "max_attempts": 3,
        "backoff_seconds": [1800, 3600, 7200],
        "free_only": True,
        "notes": "Conservative free-default OpenRouter lane; explicit paid calls stay outside automatic metabolism unless separately gated.",
    },
    "local": {
        "max_concurrent": 2,
        "min_seconds_between_dispatch": 0,
        "backoff_seconds": [60, 300, 600],
    },
}
DEFAULT_SETTINGS: dict[str, Any] = {
    "scheduler": {
        "poll_seconds": 10,
        "scan_interval_seconds": 60,
        "claim_ttl_seconds": 900,
        "orphan_recovery_grace_seconds": 30,
        # Lowered from 14400s (4h) to 600s (10min) on 2026-04-28 per pri_133
        # ceremony-friction-audit. The previous TTL accumulated stale Claude
        # session claims across operator windows that read in the blackboard
        # as concurrent "active agents", causing downstream agents to defer
        # reversible additive work behind imaginary contention. Each Claude
        # session re-stamps its claim on every PreToolUse / PostToolUse via
        # metabolism_hooks.handle_claude_hook_event, so a 10-minute TTL is
        # ample for any actually-live session and lets dead claims fall off
        # within one operator-noticeable interval. See:
        #   - codex/doctrine/skills/doctrine/ceremony_friction_audit.md
        #   - obsidian raw_seed_principles.json::pri_133
        "blackboard_claim_ttl_seconds": 600,
    },
    "pause": {
        "paused": False,
        "paused_until": None,
        "reason": None,
    },
    "provider_budgets": DEFAULT_PROVIDER_BUDGETS,
    "quiet_hours": {
        "enabled": False,
        "start": "22:00",
        "end": "07:00",
        "providers": ["chatgpt", "gemini", "claude", "codex"],
    },
    "host_control": {
        "ui_occupied_until": None,
        "reason": None,
    },
    "raw_seed_intake": {
        "enabled": True,
        "watcher_enabled": True,
        "quiet_window_seconds": 300,
        "fast_settle_seconds": 5,
        "reopen_window_seconds": 1800,
        "min_resync_gap_seconds": 10,
        "forced_catchup_seconds": 900,
    },
    "scan_state": {},
}


@dataclass(frozen=True)
class MetabolismPaths:
    state_dir: Path
    db: Path
    status_json: Path
    blackboard_json: Path
    blackboard_md: Path
    raw_seed_entry_tracker_json: Path
    raw_seed_entry_timeline_jsonl: Path
    inbox_dir: Path
    inbox_archive_dir: Path
    logs_dir: Path


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def now_dt() -> datetime:
    return datetime.now(timezone.utc)


def metabolism_paths(repo_root: Path) -> MetabolismPaths:
    state_dir = repo_root / "state" / "metabolism"
    return MetabolismPaths(
        state_dir=state_dir,
        db=state_dir / "metabolism.sqlite",
        status_json=state_dir / "metabolism_status.json",
        blackboard_json=state_dir / "blackboard.json",
        blackboard_md=state_dir / "blackboard.md",
        raw_seed_entry_tracker_json=state_dir / "raw_seed_entry_tracker.json",
        raw_seed_entry_timeline_jsonl=state_dir / "raw_seed_entry_timeline.jsonl",
        inbox_dir=state_dir / "inbox",
        inbox_archive_dir=state_dir / "inbox" / "archive",
        logs_dir=state_dir / "logs",
    )


def json_dumps(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def json_loads(raw: str | None, default: Any) -> Any:
    text = str(raw or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def row_to_dict(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {}
    if isinstance(row, sqlite3.Row):
        return {key: row[key] for key in row.keys()}
    return dict(row)


def parse_job_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["params"] = json_loads(payload.get("params_json"), {})
    payload["summary"] = json_loads(payload.get("summary_json"), {})
    return payload


def parse_event_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["payload"] = json_loads(payload.get("payload_json"), {})
    return payload


def parse_run_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["summary"] = json_loads(payload.get("summary_json"), {})
    return payload


def parse_claim_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["files_touched"] = json_loads(payload.get("files_touched_json"), [])
    payload["blockers"] = json_loads(payload.get("blockers_json"), [])
    return payload


def parse_claim_event_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["source_refs"] = json_loads(payload.get("source_refs_json"), [])
    payload["contradicts"] = json_loads(payload.get("contradicts_json"), [])
    payload["payload"] = json_loads(payload.get("payload_json"), {})
    return payload


def parse_market_snapshot_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["error_summary"] = json_loads(payload.get("error_summary_json"), [])
    payload["payload"] = json_loads(payload.get("payload_json"), {})
    return payload


def parse_raw_seed_entry_session_row(row: sqlite3.Row | Mapping[str, Any] | None) -> dict[str, Any]:
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["stats"] = json_loads(payload.get("stats_json"), {})
    return payload


@contextmanager
def transaction(conn: sqlite3.Connection) -> Iterator[None]:
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


def connect(repo_root: Path) -> sqlite3.Connection:
    paths = metabolism_paths(repo_root)
    paths.state_dir.mkdir(parents=True, exist_ok=True)
    paths.inbox_dir.mkdir(parents=True, exist_ok=True)
    paths.inbox_archive_dir.mkdir(parents=True, exist_ok=True)
    paths.logs_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(paths.db, timeout=30, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    ensure_schema(conn)
    seed_defaults(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            kind TEXT NOT NULL,
            payload_json TEXT NOT NULL,
            stable_digest TEXT NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            processed_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            provider TEXT NOT NULL,
            params_json TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            state TEXT NOT NULL,
            priority INTEGER NOT NULL,
            not_before TEXT,
            claim_owner TEXT,
            claim_expires_at TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}',
            source_event_digest TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            returncode INTEGER,
            log_path TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS providers (
            provider TEXT PRIMARY KEY,
            state TEXT NOT NULL,
            cooldown_until TEXT,
            budget_json TEXT NOT NULL,
            last_interrupt_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS blackboard_claims (
            id TEXT PRIMARY KEY,
            agent_surface TEXT NOT NULL,
            session_id TEXT NOT NULL,
            transcript_path TEXT,
            cwd TEXT,
            objective TEXT,
            current_step TEXT,
            files_touched_json TEXT NOT NULL DEFAULT '[]',
            blockers_json TEXT NOT NULL DEFAULT '[]',
            suggested_next TEXT,
            claim_expires_at TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_heartbeat_at TEXT
        );

        CREATE TABLE IF NOT EXISTS blackboard_claim_events (
            event_id TEXT PRIMARY KEY,
            event_kind TEXT NOT NULL,
            assertion_event_id TEXT,
            claim_id TEXT NOT NULL,
            claim_type TEXT NOT NULL,
            subject_ref TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            episode_id TEXT NOT NULL,
            source_refs_json TEXT NOT NULL DEFAULT '[]',
            asserted_at TEXT NOT NULL,
            valid_at TEXT NOT NULL,
            invalid_at TEXT,
            expired_at TEXT,
            superseded_by TEXT,
            contradicts_json TEXT NOT NULL DEFAULT '[]',
            authority_ceiling TEXT NOT NULL,
            freshness_state TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS heartbeats (
            process_name TEXT NOT NULL,
            pid INTEGER NOT NULL,
            started_at TEXT NOT NULL,
            last_seen_at TEXT NOT NULL,
            payload_json TEXT NOT NULL DEFAULT '{}',
            PRIMARY KEY(process_name, pid)
        );

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value_json TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS market_snapshots (
            snapshot_key TEXT PRIMARY KEY,
            fire_point TEXT NOT NULL,
            market_date TEXT NOT NULL,
            market_timezone TEXT NOT NULL,
            target_time_market TEXT NOT NULL,
            target_time_utc TEXT NOT NULL,
            timeline_path TEXT,
            timeline_row_digest TEXT,
            capture_status TEXT NOT NULL,
            captured_at_utc TEXT,
            captured_at_operator_local TEXT,
            provider TEXT NOT NULL,
            source TEXT NOT NULL,
            universe_hash TEXT,
            universe_size INTEGER NOT NULL DEFAULT 0,
            ticker_success_count INTEGER NOT NULL DEFAULT 0,
            ticker_error_count INTEGER NOT NULL DEFAULT 0,
            error_summary_json TEXT NOT NULL DEFAULT '[]',
            payload_json TEXT NOT NULL DEFAULT '{}',
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS raw_seed_entry_sessions (
            entry_id TEXT PRIMARY KEY,
            family_number TEXT NOT NULL,
            family_dir TEXT NOT NULL,
            raw_seed_path TEXT NOT NULL,
            state TEXT NOT NULL,
            opened_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            settled_at TEXT,
            synced_at TEXT,
            reopened_count INTEGER NOT NULL DEFAULT 0,
            save_count INTEGER NOT NULL DEFAULT 0,
            boundary_kind TEXT,
            classification TEXT,
            raw_digest TEXT,
            semantic_digest TEXT,
            stats_json TEXT NOT NULL DEFAULT '{}'
        );
        """
    )
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_active_idempotency
        ON jobs(idempotency_key)
        WHERE state IN ('queued','claimed','running','blocked','recoverable','paused');
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_jobs_state_priority_created
        ON jobs(state, priority, created_at);
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_events_processed_id
        ON events(processed_at, id);
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_raw_seed_entry_sessions_family_updated
        ON raw_seed_entry_sessions(family_number, updated_at DESC, opened_at DESC);
        """
    )
    conn.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_raw_seed_entry_sessions_state
        ON raw_seed_entry_sessions(state, updated_at DESC);
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (SCHEMA_VERSION, utc_now()),
    )


def _claim_event_id() -> str:
    return f"tc_{uuid.uuid4().hex[:16]}"


def _claim_subject_ref(claim: Mapping[str, Any]) -> str:
    return f"{claim.get('agent_surface') or 'agent'}:{claim.get('session_id') or claim.get('id') or 'unknown'}"


def _claim_object(claim: Mapping[str, Any]) -> str:
    parts = [
        f"status={claim.get('status') or 'unknown'}",
        f"step={claim.get('current_step') or 'n/a'}",
        f"objective={claim.get('objective') or 'n/a'}",
    ]
    return " | ".join(parts)


def _claim_source_refs(claim: Mapping[str, Any]) -> list[str]:
    refs = []
    for key in ("transcript_path", "cwd"):
        value = str(claim.get(key) or "").strip()
        if value:
            refs.append(value)
    return refs


def _claim_payload(claim: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(claim)
    payload.pop("files_touched_json", None)
    payload.pop("blockers_json", None)
    return payload


def _insert_claim_event(
    conn: sqlite3.Connection,
    event: Mapping[str, Any],
    *,
    or_ignore: bool = False,
) -> None:
    verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
    conn.execute(
        f"""
        {verb} INTO blackboard_claim_events(
            event_id, event_kind, assertion_event_id, claim_id, claim_type, subject_ref,
            predicate, object, episode_id, source_refs_json, asserted_at, valid_at,
            invalid_at, expired_at, superseded_by, contradicts_json, authority_ceiling,
            freshness_state, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event["event_id"],
            event["event_kind"],
            event["assertion_event_id"],
            event["claim_id"],
            event["claim_type"],
            event["subject_ref"],
            event["predicate"],
            event["object"],
            event["episode_id"],
            json.dumps(event["source_refs"], ensure_ascii=False),
            event["asserted_at"],
            event["valid_at"],
            event["invalid_at"],
            event["expired_at"],
            event["superseded_by"],
            json.dumps(event["contradicts"], ensure_ascii=False),
            event["authority_ceiling"],
            event["freshness_state"],
            json.dumps(event["payload"], ensure_ascii=False),
            event["created_at"],
        ),
    )


def _latest_open_claim_assertion(conn: sqlite3.Connection, claim_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM blackboard_claim_events AS asserted
        WHERE asserted.claim_id = ?
          AND asserted.event_kind = 'claim_asserted'
          AND NOT EXISTS (
              SELECT 1 FROM blackboard_claim_events AS invalidation
              WHERE invalidation.assertion_event_id = asserted.event_id
                AND invalidation.event_kind IN ('claim_superseded', 'claim_expired', 'claim_contradicted')
          )
        ORDER BY asserted.created_at DESC, asserted.event_id DESC
        LIMIT 1
        """,
        (claim_id,),
    ).fetchone()
    return parse_claim_event_row(row)


def _append_claim_assertion_event(
    conn: sqlite3.Connection,
    claim: Mapping[str, Any],
    *,
    event_id: str | None = None,
) -> dict[str, Any]:
    stamp = str(claim.get("updated_at") or utc_now())
    claim_id = str(claim.get("id") or _claim_subject_ref(claim))
    event = {
        "event_id": event_id or _claim_event_id(),
        "event_kind": "claim_asserted",
        "assertion_event_id": None,
        "claim_id": claim_id,
        "claim_type": "active_agent_claim",
        "subject_ref": _claim_subject_ref(claim),
        "predicate": "asserts_session_currentness",
        "object": _claim_object(claim),
        "episode_id": f"metabolism_blackboard:{claim_id}",
        "source_refs": _claim_source_refs(claim),
        "asserted_at": stamp,
        "valid_at": str(claim.get("last_heartbeat_at") or claim.get("updated_at") or stamp),
        "invalid_at": None,
        "expired_at": None,
        "superseded_by": None,
        "contradicts": [],
        "authority_ceiling": "runtime_claim_not_source_authority",
        "freshness_state": "current" if str(claim.get("status") or "active") == "active" else str(claim.get("status")),
        "payload": _claim_payload(claim),
        "created_at": stamp,
    }
    _insert_claim_event(conn, event, or_ignore=True)
    return event


def _append_claim_invalidation_event(
    conn: sqlite3.Connection,
    claim: Mapping[str, Any],
    *,
    event_kind: str,
    assertion_event_id: str,
    invalid_at: str,
    expired_at: str | None = None,
    superseded_by: str | None = None,
    contradicts: Sequence[str] = (),
    freshness_state: str,
) -> dict[str, Any]:
    existing = conn.execute(
        """
        SELECT * FROM blackboard_claim_events
        WHERE assertion_event_id = ?
          AND event_kind = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (assertion_event_id, event_kind),
    ).fetchone()
    if existing is not None:
        return parse_claim_event_row(existing)
    claim_id = str(claim.get("id") or _claim_subject_ref(claim))
    event = {
        "event_id": _claim_event_id(),
        "event_kind": event_kind,
        "assertion_event_id": assertion_event_id,
        "claim_id": claim_id,
        "claim_type": "active_agent_claim",
        "subject_ref": _claim_subject_ref(claim),
        "predicate": "invalidates_session_currentness",
        "object": _claim_object(claim),
        "episode_id": f"metabolism_blackboard:{claim_id}",
        "source_refs": _claim_source_refs(claim),
        "asserted_at": invalid_at,
        "valid_at": invalid_at,
        "invalid_at": invalid_at,
        "expired_at": expired_at,
        "superseded_by": superseded_by,
        "contradicts": list(contradicts),
        "authority_ceiling": "runtime_claim_not_source_authority",
        "freshness_state": freshness_state,
        "payload": _claim_payload(claim),
        "created_at": invalid_at,
    }
    _insert_claim_event(conn, event)
    return event


def seed_defaults(conn: sqlite3.Connection) -> None:
    with transaction(conn):
        for key, value in DEFAULT_SETTINGS.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO settings(key, value_json, updated_at)
                VALUES (?, ?, ?)
                """,
                (key, json.dumps(value, ensure_ascii=False), utc_now()),
            )
        budgets = get_setting(conn, "provider_budgets", DEFAULT_PROVIDER_BUDGETS)
        now = utc_now()
        for provider, budget in budgets.items():
            conn.execute(
                """
                INSERT OR IGNORE INTO providers(
                    provider, state, cooldown_until, budget_json, last_interrupt_json, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    provider,
                    "available",
                    None,
                    json.dumps(budget, ensure_ascii=False),
                    "{}",
                    now,
                ),
            )


def get_setting(conn: sqlite3.Connection, key: str, default: Any = None) -> Any:
    row = conn.execute("SELECT value_json FROM settings WHERE key = ?", (key,)).fetchone()
    if row is None:
        return default
    return json_loads(row["value_json"], default)


def set_setting(conn: sqlite3.Connection, key: str, value: Any) -> None:
    conn.execute(
        """
        INSERT INTO settings(key, value_json, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
            value_json = excluded.value_json,
            updated_at = excluded.updated_at
        """,
        (key, json.dumps(value, ensure_ascii=False), utc_now()),
    )


def enqueue_event(
    conn: sqlite3.Connection,
    *,
    source: str,
    kind: str,
    payload: Mapping[str, Any],
    stable_digest: str,
    created_at: str | None = None,
) -> tuple[dict[str, Any], bool]:
    created = created_at or utc_now()
    inserted = False
    with transaction(conn):
        before = conn.total_changes
        conn.execute(
            """
            INSERT OR IGNORE INTO events(
                source, kind, payload_json, stable_digest, created_at, processed_at
            ) VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (source, kind, json.dumps(dict(payload), ensure_ascii=False), stable_digest, created),
        )
        inserted = conn.total_changes > before
    row = conn.execute("SELECT * FROM events WHERE stable_digest = ?", (stable_digest,)).fetchone()
    return parse_event_row(row), inserted


def fetch_unprocessed_events(conn: sqlite3.Connection, *, limit: int = 200) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT * FROM events
        WHERE processed_at IS NULL
        ORDER BY id ASC
        LIMIT ?
        """,
        (max(limit, 1),),
    ).fetchall()
    return [parse_event_row(row) for row in rows]


def count_unprocessed_events(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM events
        WHERE processed_at IS NULL
        """
    ).fetchone()
    if row is None:
        return 0
    return int(row["count"])


def mark_event_processed(conn: sqlite3.Connection, event_id: int) -> None:
    conn.execute(
        "UPDATE events SET processed_at = ? WHERE id = ?",
        (utc_now(), int(event_id)),
    )


def create_job(
    conn: sqlite3.Connection,
    *,
    kind: str,
    provider: str,
    params: Mapping[str, Any],
    idempotency_key: str,
    priority: int,
    not_before: str | None = None,
    source_event_digest: str | None = None,
    summary: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], bool]:
    created_at = utc_now()
    job_id = f"job_{uuid.uuid4().hex[:16]}"
    inserted = False
    with transaction(conn):
        try:
            conn.execute(
                """
                INSERT INTO jobs(
                    id, kind, provider, params_json, idempotency_key, state, priority,
                    not_before, claim_owner, claim_expires_at, attempts, last_error,
                    summary_json, source_event_digest, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, NULL, ?, ?, ?, ?)
                """,
                (
                    job_id,
                    kind,
                    provider,
                    json.dumps(dict(params), ensure_ascii=False),
                    idempotency_key,
                    JOB_STATE_QUEUED,
                    int(priority),
                    not_before,
                    json.dumps(dict(summary or {}), ensure_ascii=False),
                    source_event_digest,
                    created_at,
                    created_at,
                ),
            )
            inserted = True
        except sqlite3.IntegrityError:
            inserted = False
    row = conn.execute(
        """
        SELECT * FROM jobs
        WHERE idempotency_key = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (idempotency_key,),
    ).fetchone()
    return parse_job_row(row), inserted


def fetch_jobs(
    conn: sqlite3.Connection,
    *,
    states: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM jobs"
    params: list[Any] = []
    if states:
        placeholders = ",".join("?" for _ in states)
        sql += f" WHERE state IN ({placeholders})"
        params.extend(states)
    sql += " ORDER BY priority ASC, created_at ASC"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    return [parse_job_row(row) for row in rows]


def fetch_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    return parse_job_row(row)


def fetch_job_by_idempotency(conn: sqlite3.Connection, idempotency_key: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM jobs
        WHERE idempotency_key = ?
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (str(idempotency_key),),
    ).fetchone()
    return parse_job_row(row)


def update_job(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    state: str | None | object = _UNSET,
    claim_owner: str | None | object = _UNSET,
    claim_expires_at: str | None | object = _UNSET,
    attempts: int | None | object = _UNSET,
    last_error: str | None | object = _UNSET,
    not_before: str | None | object = _UNSET,
    summary: Mapping[str, Any] | None | object = _UNSET,
) -> None:
    current = fetch_job(conn, job_id)
    if not current:
        return
    payload = {
        "state": current.get("state") if state is _UNSET else state,
        "claim_owner": current.get("claim_owner") if claim_owner is _UNSET else claim_owner,
        "claim_expires_at": current.get("claim_expires_at") if claim_expires_at is _UNSET else claim_expires_at,
        "attempts": int(current.get("attempts") or 0) if attempts is _UNSET else int(attempts or 0),
        "last_error": current.get("last_error") if last_error is _UNSET else last_error,
        "not_before": current.get("not_before") if not_before is _UNSET else not_before,
        "summary_json": json.dumps(
            current.get("summary") or {}
            if summary is _UNSET
            else dict(summary or {}),
            ensure_ascii=False,
        ),
        "updated_at": utc_now(),
    }
    conn.execute(
        """
        UPDATE jobs
        SET state = ?, claim_owner = ?, claim_expires_at = ?, attempts = ?,
            last_error = ?, not_before = ?, summary_json = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            payload["state"],
            payload["claim_owner"],
            payload["claim_expires_at"],
            payload["attempts"],
            payload["last_error"],
            payload["not_before"],
            payload["summary_json"],
            payload["updated_at"],
            job_id,
        ),
    )


def requeue_expired_jobs(
    conn: sqlite3.Connection,
    *,
    now: str | None = None,
    message: str = "claim expired; requeued by metabolismd",
) -> int:
    stamp = now or utc_now()
    rows = conn.execute(
        """
        SELECT id, state FROM jobs
        WHERE state IN ('claimed','running')
          AND claim_expires_at IS NOT NULL
          AND claim_expires_at < ?
        """,
        (stamp,),
    ).fetchall()
    count = 0
    for row in rows:
        conn.execute(
            """
            UPDATE jobs
            SET state = ?, claim_owner = NULL, claim_expires_at = NULL,
                last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (JOB_STATE_RECOVERABLE, message, stamp, row["id"]),
        )
        count += 1
    return count


def insert_run(
    conn: sqlite3.Connection,
    *,
    job_id: str,
    log_path: str | None,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    run_id = f"run_{uuid.uuid4().hex[:16]}"
    now = utc_now()
    conn.execute(
        """
        INSERT INTO runs(id, job_id, started_at, completed_at, returncode, log_path, summary_json)
        VALUES (?, ?, ?, NULL, NULL, ?, ?)
        """,
        (
            run_id,
            job_id,
            now,
            log_path,
            json.dumps(dict(summary or {}), ensure_ascii=False),
        ),
    )
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return parse_run_row(row)


def complete_run(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    returncode: int,
    summary: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = parse_run_row(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())
    merged_summary = dict(current.get("summary") or {})
    merged_summary.update(dict(summary or {}))
    conn.execute(
        """
        UPDATE runs
        SET completed_at = ?, returncode = ?, summary_json = ?
        WHERE id = ?
        """,
        (
            utc_now(),
            int(returncode),
            json.dumps(merged_summary, ensure_ascii=False),
            run_id,
        ),
    )
    row = conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
    return parse_run_row(row)


def latest_run_for_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM runs
        WHERE job_id = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (job_id,),
    ).fetchone()
    return parse_run_row(row)


def ensure_provider(conn: sqlite3.Connection, provider: str) -> None:
    budgets = get_setting(conn, "provider_budgets", DEFAULT_PROVIDER_BUDGETS)
    budget = budgets.get(provider) or DEFAULT_PROVIDER_BUDGETS.get(provider) or budgets.get("local") or DEFAULT_PROVIDER_BUDGETS["local"]
    conn.execute(
        """
        INSERT OR IGNORE INTO providers(
            provider, state, cooldown_until, budget_json, last_interrupt_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (provider, "available", None, json.dumps(budget, ensure_ascii=False), "{}", utc_now()),
    )


def get_provider_row(conn: sqlite3.Connection, provider: str) -> dict[str, Any]:
    ensure_provider(conn, provider)
    row = conn.execute("SELECT * FROM providers WHERE provider = ?", (provider,)).fetchone()
    payload = row_to_dict(row)
    if not payload:
        return {}
    payload["budget"] = json_loads(payload.get("budget_json"), {})
    payload["last_interrupt"] = json_loads(payload.get("last_interrupt_json"), {})
    return payload


def list_provider_rows(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute("SELECT * FROM providers ORDER BY provider ASC").fetchall()
    return [get_provider_row(conn, row["provider"]) for row in rows]


def set_provider_row(
    conn: sqlite3.Connection,
    *,
    provider: str,
    state: str,
    cooldown_until: str | None,
    budget: Mapping[str, Any] | None = None,
    last_interrupt: Mapping[str, Any] | None = None,
) -> None:
    ensure_provider(conn, provider)
    current = get_provider_row(conn, provider)
    conn.execute(
        """
        UPDATE providers
        SET state = ?, cooldown_until = ?, budget_json = ?, last_interrupt_json = ?, updated_at = ?
        WHERE provider = ?
        """,
        (
            state,
            cooldown_until,
            json.dumps(dict(budget) if budget is not None else current.get("budget") or {}, ensure_ascii=False),
            json.dumps(dict(last_interrupt) if last_interrupt is not None else current.get("last_interrupt") or {}, ensure_ascii=False),
            utc_now(),
            provider,
        ),
    )


def upsert_blackboard_claim(
    conn: sqlite3.Connection,
    *,
    claim_id: str,
    agent_surface: str,
    session_id: str,
    transcript_path: str | None = None,
    cwd: str | None = None,
    objective: str | None = None,
    current_step: str | None = None,
    files_touched: Sequence[str] | None = None,
    blockers: Sequence[str] | None = None,
    suggested_next: str | None = None,
    claim_expires_at: str | None = None,
    status: str = "active",
    last_heartbeat_at: str | None = None,
) -> dict[str, Any]:
    existing = parse_claim_row(
        conn.execute("SELECT * FROM blackboard_claims WHERE id = ?", (claim_id,)).fetchone()
    )
    created_at = existing.get("created_at") or utc_now()
    merged_files = list(dict.fromkeys([*(existing.get("files_touched") or []), *(files_touched or [])]))
    merged_blockers = list(dict.fromkeys([*(existing.get("blockers") or []), *(blockers or [])]))
    conn.execute(
        """
        INSERT INTO blackboard_claims(
            id, agent_surface, session_id, transcript_path, cwd, objective, current_step,
            files_touched_json, blockers_json, suggested_next, claim_expires_at, status,
            created_at, updated_at, last_heartbeat_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            transcript_path = excluded.transcript_path,
            cwd = excluded.cwd,
            objective = excluded.objective,
            current_step = excluded.current_step,
            files_touched_json = excluded.files_touched_json,
            blockers_json = excluded.blockers_json,
            suggested_next = excluded.suggested_next,
            claim_expires_at = excluded.claim_expires_at,
            status = excluded.status,
            updated_at = excluded.updated_at,
            last_heartbeat_at = excluded.last_heartbeat_at
        """,
        (
            claim_id,
            agent_surface,
            session_id,
            transcript_path if transcript_path is not None else existing.get("transcript_path"),
            cwd if cwd is not None else existing.get("cwd"),
            objective if objective is not None else existing.get("objective"),
            current_step if current_step is not None else existing.get("current_step"),
            json.dumps(merged_files, ensure_ascii=False),
            json.dumps(merged_blockers, ensure_ascii=False),
            suggested_next if suggested_next is not None else existing.get("suggested_next"),
            claim_expires_at if claim_expires_at is not None else existing.get("claim_expires_at"),
            status if status is not None else existing.get("status") or "active",
            created_at,
            utc_now(),
            last_heartbeat_at or utc_now(),
        ),
    )
    row = conn.execute("SELECT * FROM blackboard_claims WHERE id = ?", (claim_id,)).fetchone()
    claim_row = parse_claim_row(row)
    assertion_event_id = _claim_event_id()
    previous = _latest_open_claim_assertion(conn, claim_id)
    if previous:
        _append_claim_invalidation_event(
            conn,
            claim_row,
            event_kind="claim_superseded",
            assertion_event_id=str(previous.get("event_id")),
            invalid_at=str(claim_row.get("updated_at") or utc_now()),
            superseded_by=assertion_event_id,
            freshness_state="superseded",
        )
    _append_claim_assertion_event(conn, claim_row, event_id=assertion_event_id)
    return claim_row


def fetch_raw_seed_entry_session(conn: sqlite3.Connection, entry_id: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM raw_seed_entry_sessions WHERE entry_id = ?",
        (entry_id,),
    ).fetchone()
    return parse_raw_seed_entry_session_row(row)


def list_raw_seed_entry_sessions(
    conn: sqlite3.Connection,
    *,
    family_number: str | None = None,
    states: Sequence[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM raw_seed_entry_sessions"
    clauses: list[str] = []
    params: list[Any] = []
    if family_number:
        clauses.append("family_number = ?")
        params.append(str(family_number))
    if states:
        placeholders = ",".join("?" for _ in states)
        clauses.append(f"state IN ({placeholders})")
        params.extend(str(state) for state in states)
    if clauses:
        sql += " WHERE " + " AND ".join(clauses)
    sql += " ORDER BY updated_at DESC, opened_at DESC, entry_id DESC"
    if limit:
        sql += " LIMIT ?"
        params.append(int(limit))
    rows = conn.execute(sql, params).fetchall()
    return [parse_raw_seed_entry_session_row(row) for row in rows]


def latest_raw_seed_entry_session(
    conn: sqlite3.Connection,
    *,
    family_number: str | None = None,
    states: Sequence[str] | None = None,
) -> dict[str, Any]:
    rows = list_raw_seed_entry_sessions(conn, family_number=family_number, states=states, limit=1)
    return rows[0] if rows else {}


def upsert_raw_seed_entry_session(
    conn: sqlite3.Connection,
    *,
    entry_id: str,
    family_number: str,
    family_dir: str,
    raw_seed_path: str,
    state: str,
    opened_at: str | None = None,
    updated_at: str | None = None,
    settled_at: str | None = None,
    synced_at: str | None = None,
    reopened_count: int | None = None,
    save_count: int | None = None,
    boundary_kind: str | None = None,
    classification: str | None = None,
    raw_digest: str | None = None,
    semantic_digest: str | None = None,
    stats: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = fetch_raw_seed_entry_session(conn, entry_id)
    opened = opened_at or current.get("opened_at") or utc_now()
    updated = updated_at or utc_now()
    row = {
        "entry_id": entry_id,
        "family_number": str(family_number),
        "family_dir": str(family_dir),
        "raw_seed_path": str(raw_seed_path),
        "state": str(state),
        "opened_at": opened,
        "updated_at": updated,
        "settled_at": settled_at if settled_at is not None else current.get("settled_at"),
        "synced_at": synced_at if synced_at is not None else current.get("synced_at"),
        "reopened_count": int(
            reopened_count
            if reopened_count is not None
            else current.get("reopened_count") or 0
        ),
        "save_count": int(
            save_count
            if save_count is not None
            else current.get("save_count") or 0
        ),
        "boundary_kind": boundary_kind if boundary_kind is not None else current.get("boundary_kind"),
        "classification": classification if classification is not None else current.get("classification"),
        "raw_digest": raw_digest if raw_digest is not None else current.get("raw_digest"),
        "semantic_digest": semantic_digest if semantic_digest is not None else current.get("semantic_digest"),
        "stats_json": json.dumps(
            dict(stats) if stats is not None else dict(current.get("stats") or {}),
            ensure_ascii=False,
        ),
    }
    conn.execute(
        """
        INSERT INTO raw_seed_entry_sessions(
            entry_id, family_number, family_dir, raw_seed_path, state, opened_at, updated_at,
            settled_at, synced_at, reopened_count, save_count, boundary_kind, classification,
            raw_digest, semantic_digest, stats_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(entry_id) DO UPDATE SET
            family_number = excluded.family_number,
            family_dir = excluded.family_dir,
            raw_seed_path = excluded.raw_seed_path,
            state = excluded.state,
            opened_at = excluded.opened_at,
            updated_at = excluded.updated_at,
            settled_at = excluded.settled_at,
            synced_at = excluded.synced_at,
            reopened_count = excluded.reopened_count,
            save_count = excluded.save_count,
            boundary_kind = excluded.boundary_kind,
            classification = excluded.classification,
            raw_digest = excluded.raw_digest,
            semantic_digest = excluded.semantic_digest,
            stats_json = excluded.stats_json
        """,
        (
            row["entry_id"],
            row["family_number"],
            row["family_dir"],
            row["raw_seed_path"],
            row["state"],
            row["opened_at"],
            row["updated_at"],
            row["settled_at"],
            row["synced_at"],
            row["reopened_count"],
            row["save_count"],
            row["boundary_kind"],
            row["classification"],
            row["raw_digest"],
            row["semantic_digest"],
            row["stats_json"],
        ),
    )
    return fetch_raw_seed_entry_session(conn, entry_id)


def mark_raw_seed_entry_sessions_synced(
    conn: sqlite3.Connection,
    *,
    family_number: str,
    synced_at: str | None = None,
    max_updated_at: str | None = None,
) -> list[dict[str, Any]]:
    stamp = synced_at or utc_now()
    clauses = [
        "family_number = ?",
        "state = 'settled'",
        "settled_at IS NOT NULL",
    ]
    params: list[Any] = [str(family_number)]
    if max_updated_at:
        clauses.append("updated_at <= ?")
        params.append(str(max_updated_at))
    rows = conn.execute(
        f"""
        SELECT entry_id FROM raw_seed_entry_sessions
        WHERE {" AND ".join(clauses)}
        ORDER BY updated_at ASC, opened_at ASC
        """,
        params,
    ).fetchall()
    if not rows:
        return []
    updated_rows: list[dict[str, Any]] = []
    for row in rows:
        conn.execute(
            """
            UPDATE raw_seed_entry_sessions
            SET state = 'synced', synced_at = ?, updated_at = ?
            WHERE entry_id = ?
            """,
            (stamp, stamp, row["entry_id"]),
        )
        updated_rows.append(fetch_raw_seed_entry_session(conn, str(row["entry_id"])))
    return updated_rows


def get_market_snapshot(conn: sqlite3.Connection, snapshot_key: str) -> dict[str, Any]:
    row = conn.execute(
        "SELECT * FROM market_snapshots WHERE snapshot_key = ?",
        (snapshot_key,),
    ).fetchone()
    return parse_market_snapshot_row(row)


def latest_market_snapshot(conn: sqlite3.Connection) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM market_snapshots
        ORDER BY COALESCE(captured_at_utc, updated_at) DESC, snapshot_key DESC
        LIMIT 1
        """
    ).fetchone()
    return parse_market_snapshot_row(row)


def upsert_market_snapshot(
    conn: sqlite3.Connection,
    *,
    snapshot_key: str,
    fire_point: str,
    market_date: str,
    market_timezone: str,
    target_time_market: str,
    target_time_utc: str,
    timeline_path: str | None = None,
    timeline_row_digest: str | None = None,
    capture_status: str,
    captured_at_utc: str | None = None,
    captured_at_operator_local: str | None = None,
    provider: str = "local",
    source: str = "yfinance",
    universe_hash: str | None = None,
    universe_size: int = 0,
    ticker_success_count: int = 0,
    ticker_error_count: int = 0,
    error_summary: Sequence[Mapping[str, Any]] | None = None,
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    current = get_market_snapshot(conn, snapshot_key)
    payload_json = json.dumps(
        dict(payload) if payload is not None else dict(current.get("payload") or {}),
        ensure_ascii=False,
    )
    error_summary_json = json.dumps(
        [dict(item) for item in error_summary or current.get("error_summary") or [] if isinstance(item, Mapping)],
        ensure_ascii=False,
    )
    conn.execute(
        """
        INSERT INTO market_snapshots(
            snapshot_key, fire_point, market_date, market_timezone,
            target_time_market, target_time_utc, timeline_path, timeline_row_digest,
            capture_status, captured_at_utc, captured_at_operator_local, provider, source,
            universe_hash, universe_size, ticker_success_count, ticker_error_count,
            error_summary_json, payload_json, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(snapshot_key) DO UPDATE SET
            fire_point = excluded.fire_point,
            market_date = excluded.market_date,
            market_timezone = excluded.market_timezone,
            target_time_market = excluded.target_time_market,
            target_time_utc = excluded.target_time_utc,
            timeline_path = excluded.timeline_path,
            timeline_row_digest = excluded.timeline_row_digest,
            capture_status = excluded.capture_status,
            captured_at_utc = excluded.captured_at_utc,
            captured_at_operator_local = excluded.captured_at_operator_local,
            provider = excluded.provider,
            source = excluded.source,
            universe_hash = excluded.universe_hash,
            universe_size = excluded.universe_size,
            ticker_success_count = excluded.ticker_success_count,
            ticker_error_count = excluded.ticker_error_count,
            error_summary_json = excluded.error_summary_json,
            payload_json = excluded.payload_json,
            updated_at = excluded.updated_at
        """,
        (
            snapshot_key,
            fire_point,
            market_date,
            market_timezone,
            target_time_market,
            target_time_utc,
            timeline_path if timeline_path is not None else current.get("timeline_path"),
            timeline_row_digest if timeline_row_digest is not None else current.get("timeline_row_digest"),
            capture_status,
            captured_at_utc,
            captured_at_operator_local,
            provider,
            source,
            universe_hash if universe_hash is not None else current.get("universe_hash"),
            int(universe_size if universe_size is not None else current.get("universe_size") or 0),
            int(ticker_success_count),
            int(ticker_error_count),
            error_summary_json,
            payload_json,
            utc_now(),
        ),
    )
    return get_market_snapshot(conn, snapshot_key)


def list_blackboard_claims(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM blackboard_claims ORDER BY updated_at DESC, created_at DESC"
    ).fetchall()
    return [parse_claim_row(row) for row in rows]


def list_temporal_blackboard_claims(
    conn: sqlite3.Connection,
    *,
    limit: int = 100,
) -> list[dict[str, Any]]:
    assertions = [
        parse_claim_event_row(row)
        for row in conn.execute(
            """
            SELECT * FROM blackboard_claim_events
            WHERE event_kind = 'claim_asserted'
            ORDER BY created_at DESC, event_id DESC
            LIMIT ?
            """,
            (max(1, int(limit or 100)),),
        ).fetchall()
    ]
    if not assertions:
        return []
    assertion_ids = [str(row.get("event_id")) for row in assertions]
    placeholders = ",".join("?" for _ in assertion_ids)
    invalidations_by_assertion: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        f"""
        SELECT * FROM blackboard_claim_events
        WHERE assertion_event_id IN ({placeholders})
          AND event_kind IN ('claim_superseded', 'claim_expired', 'claim_contradicted')
        ORDER BY created_at ASC, event_id ASC
        """,
        assertion_ids,
    ).fetchall():
        event = parse_claim_event_row(row)
        invalidations_by_assertion[str(event.get("assertion_event_id"))] = event

    temporal_claims: list[dict[str, Any]] = []
    for assertion in assertions:
        invalidation = invalidations_by_assertion.get(str(assertion.get("event_id")))
        freshness_state = str(assertion.get("freshness_state") or "current")
        invalid_at = None
        expired_at = None
        superseded_by = None
        contradicts: list[Any] = []
        if invalidation:
            freshness_state = str(invalidation.get("freshness_state") or freshness_state)
            invalid_at = invalidation.get("invalid_at")
            expired_at = invalidation.get("expired_at")
            superseded_by = invalidation.get("superseded_by")
            contradicts = list(invalidation.get("contradicts") or [])
        temporal_claims.append(
            {
                "claim_id": assertion.get("event_id"),
                "source_claim_id": assertion.get("claim_id"),
                "claim_type": assertion.get("claim_type"),
                "subject_ref": assertion.get("subject_ref"),
                "predicate": assertion.get("predicate"),
                "object": assertion.get("object"),
                "episode_id": assertion.get("episode_id"),
                "source_refs": list(assertion.get("source_refs") or []),
                "asserted_at": assertion.get("asserted_at"),
                "valid_at": assertion.get("valid_at"),
                "invalid_at": invalid_at,
                "expired_at": expired_at,
                "superseded_by": superseded_by,
                "contradicts": contradicts,
                "authority_ceiling": assertion.get("authority_ceiling"),
                "freshness_state": freshness_state,
                "source_payload": dict(assertion.get("payload") or {}),
            }
        )
    return temporal_claims


def touch_heartbeat(
    conn: sqlite3.Connection,
    *,
    process_name: str,
    pid: int,
    payload: Mapping[str, Any] | None = None,
    started_at: str | None = None,
) -> None:
    stamp = utc_now()
    conn.execute(
        """
        INSERT INTO heartbeats(process_name, pid, started_at, last_seen_at, payload_json)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(process_name, pid) DO UPDATE SET
            last_seen_at = excluded.last_seen_at,
            payload_json = excluded.payload_json
        """,
        (
            process_name,
            int(pid),
            started_at or stamp,
            stamp,
            json.dumps(dict(payload or {}), ensure_ascii=False),
        ),
    )


def list_heartbeats(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    rows = conn.execute(
        "SELECT * FROM heartbeats ORDER BY last_seen_at DESC, process_name ASC"
    ).fetchall()
    payloads: list[dict[str, Any]] = []
    for row in rows:
        item = row_to_dict(row)
        item["payload"] = json_loads(item.get("payload_json"), {})
        payloads.append(item)
    return payloads


def expire_old_claims(
    conn: sqlite3.Connection,
    *,
    now: str | None = None,
    max_age_seconds: int | None = None,
) -> int:
    """
    [ACTION]
    - Teleology: Mark stale blackboard claims expired so they stop rendering as
      active concurrent agents. Wave_003B retroactive deep-cause repair: the
      pre-fix 14400s (4h) TTL means existing rows have ``claim_expires_at``
      values hours in the future even after the new 600s default landed; the
      ``max_age_seconds`` path catches those rows by checking ``updated_at``
      against the live TTL, not the pre-stamped expiry.
    - Mechanism: Two passes. Pass 1 expires rows whose stored
      ``claim_expires_at`` has elapsed. Pass 2 (only when ``max_age_seconds``
      is provided) expires rows whose ``updated_at`` is older than the live
      TTL window — this is the retroactive part that pri_133
      ceremony_friction_audit names.
    """
    stamp = now or utc_now()
    before = conn.total_changes
    claim_rows_to_expire: dict[str, dict[str, Any]] = {}
    for row in conn.execute(
        """
        SELECT * FROM blackboard_claims
        WHERE claim_expires_at IS NOT NULL
          AND claim_expires_at < ?
          AND status NOT IN ('closed','expired')
        """,
        (stamp,),
    ).fetchall():
        claim = parse_claim_row(row)
        claim_rows_to_expire[str(claim.get("id"))] = claim
    conn.execute(
        """
        UPDATE blackboard_claims
        SET status = CASE
            WHEN status = 'closed' THEN 'closed'
            ELSE 'expired'
        END,
        updated_at = ?
        WHERE claim_expires_at IS NOT NULL
          AND claim_expires_at < ?
          AND status NOT IN ('closed','expired')
        """,
        (stamp, stamp),
    )
    if max_age_seconds is not None and max_age_seconds > 0:
        # Wave_004A hardening: derive the max-age cutoff from the supplied
        # `now` parameter when present so explicit-time tests are deterministic
        # and the SQL-update layer agrees with the projection-layer freshness
        # check in metabolism_blackboard.build_blackboard_projection.
        if now:
            try:
                base_dt = datetime.fromisoformat(str(now).replace("Z", "+00:00"))
                if base_dt.tzinfo is None:
                    base_dt = base_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                base_dt = now_dt()
        else:
            base_dt = now_dt()
        cutoff = (base_dt - timedelta(seconds=int(max_age_seconds))).isoformat()
        for row in conn.execute(
            """
            SELECT * FROM blackboard_claims
            WHERE (
                updated_at < ?
                OR (last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?)
            )
              AND status NOT IN ('closed','expired')
            """,
            (cutoff, cutoff),
        ).fetchall():
            claim = parse_claim_row(row)
            claim_rows_to_expire[str(claim.get("id"))] = claim
        conn.execute(
            """
            UPDATE blackboard_claims
            SET status = CASE
                WHEN status = 'closed' THEN 'closed'
                ELSE 'expired'
            END,
            updated_at = ?
            WHERE (
                updated_at < ?
                OR (last_heartbeat_at IS NOT NULL AND last_heartbeat_at < ?)
            )
              AND status NOT IN ('closed','expired')
            """,
            (stamp, cutoff, cutoff),
        )
    updated_count = conn.total_changes - before
    for claim in claim_rows_to_expire.values():
        claim_id = str(claim.get("id") or _claim_subject_ref(claim))
        assertion = _latest_open_claim_assertion(conn, claim_id)
        if not assertion:
            assertion = _append_claim_assertion_event(conn, claim)
        _append_claim_invalidation_event(
            conn,
            claim,
            event_kind="claim_expired",
            assertion_event_id=str(assertion.get("event_id")),
            invalid_at=stamp,
            expired_at=stamp,
            freshness_state="expired",
        )
    return updated_count


def bump_claim_expiry(seconds: int) -> str:
    return (now_dt() + timedelta(seconds=max(seconds, 1))).isoformat()
