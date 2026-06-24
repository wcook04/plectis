"""Public-safe metabolism runtime and reconciler capsule.

[PURPOSE]
Expose a runnable public capsule for the Engine Room metabolism queue, lease recovery, blackboard projection, and reconciliation taxonomy without exporting private runtime state.

[INTERFACE]
Provides SQLite-backed queue helpers, claim-event projection helpers, `ReconciliationFinding`, fixture evaluators, and the `evaluate-fixtures` CLI.

[FLOW]
Create a synthetic SQLite store, enqueue and lease jobs, record runs and claim events, project active blackboard claims, reconcile inconsistent job/run/log state, then report fixture receipts.

[DEPENDENCIES]
Uses only Python standard-library modules plus fixture JSON supplied by the public Plectis package; no private metabolism database, scheduler daemon, provider, or operator session state is read.

[CONSTRAINTS]
This capsule is source-faithful but public-bounded: it does not dispatch agents, does not call providers, does not auto-repair ambiguous runtime state, and does not claim distributed-database behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "engine_room_metabolism_runtime_v1"
ORGAN_ID = "engine_room_metabolism_runtime"
SOURCE_REFS = (
    "system/lib/metabolism_store.py",
    "system/lib/metabolism_scheduler.py",
    "system/lib/metabolism_blackboard.py",
    "system/lib/metabolism_reconciliation.py",
)
SOURCE_TO_TARGET_RELATION = "source_faithful_public_refactor"
CLAIM_CEILING = (
    "Synthetic SQLite capsule for durable queue, lease recovery, blackboard "
    "claim-event projection, and cold-start reconciliation taxonomy. It does "
    "not ship the private live metabolism database, does not dispatch agents "
    "or providers, does not auto-repair ambiguous runtime state, and is not a "
    "distributed database."
)
ANTI_CLAIMS = (
    "not_live_private_runtime_export",
    "not_agent_dispatcher",
    "not_provider_executor",
    "not_ambiguous_auto_repair",
    "not_distributed_database",
)

JOB_QUEUED = "queued"
JOB_CLAIMED = "claimed"
JOB_RUNNING = "running"
JOB_RECOVERABLE = "recoverable"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"
ACTIVE_STATES = (JOB_QUEUED, JOB_CLAIMED, JOB_RUNNING, JOB_RECOVERABLE)

RULE_RUNNING_JOB_NO_RUN_ROW = "running_job_no_run_row"
RULE_RUN_FINALIZED_BUT_JOB_RUNNING = "run_finalized_but_job_running"
RULE_RUNNING_JOB_STALE_LAUNCH_LOG = "running_job_stale_launch_log"
RULE_RUNNING_JOB_MISSING_LAUNCH_LOG = "running_job_missing_launch_log"
ACTION_OPERATOR_REVIEW_REQUIRED = "operator_review_required"


def utc_now() -> str:
    """
    [ACTION]
    - Teleology: Stamp synthetic metabolism receipts and rows with a normalized UTC timestamp.
    - Guarantee: Returns an ISO-8601 timestamp string without microseconds.
    - Fails: None; uses the local process clock only.
    """
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _to_dt(value: str | None) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _json_loads(raw: str | None, default: Any) -> Any:
    text = str(raw or "").strip()
    if not text:
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return default


def _sha1_token(value: str, *, prefix: str) -> str:
    return f"{prefix}_{hashlib.sha1(value.encode('utf-8')).hexdigest()[:16]}"


def connect(db_path: Path) -> sqlite3.Connection:
    """
    [ACTION]
    - Teleology: Open the synthetic SQLite store used by the public metabolism capsule.
    - Guarantee: Returns a connection with WAL, normal sync, foreign keys, row objects, and the expected schema installed.
    - Fails: Raises sqlite3 or filesystem errors when the database path cannot be created or opened.
    - Writes: Creates the parent directory and database files for the supplied path.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    ensure_schema(conn)
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    """
    [ACTION]
    - Teleology: Install the queue, run, and blackboard tables required by the capsule.
    - Guarantee: Required tables, indexes, and migration row version 1 exist after success.
    - Fails: Raises sqlite3.DatabaseError if schema DDL or migration insertion fails.
    - Writes: Mutates the supplied SQLite connection schema.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            kind TEXT NOT NULL,
            provider TEXT NOT NULL,
            params_json TEXT NOT NULL,
            idempotency_key TEXT NOT NULL,
            execution_fingerprint TEXT NOT NULL,
            state TEXT NOT NULL,
            priority INTEGER NOT NULL,
            not_before TEXT,
            claim_owner TEXT,
            claim_expires_at TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,
            last_error TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_active_idempotency
        ON jobs(idempotency_key)
        WHERE state IN ('queued','claimed','running','recoverable');

        CREATE INDEX IF NOT EXISTS idx_jobs_state_priority_created
        ON jobs(state, priority, created_at);

        CREATE TABLE IF NOT EXISTS runs (
            id TEXT PRIMARY KEY,
            job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            returncode INTEGER,
            log_path TEXT,
            summary_json TEXT NOT NULL DEFAULT '{}'
        );

        CREATE TABLE IF NOT EXISTS blackboard_claim_events (
            event_id TEXT PRIMARY KEY,
            event_kind TEXT NOT NULL,
            assertion_event_id TEXT,
            claim_id TEXT NOT NULL,
            subject_ref TEXT NOT NULL,
            predicate TEXT NOT NULL,
            object TEXT NOT NULL,
            episode_id TEXT NOT NULL,
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
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO schema_migrations(version, applied_at) VALUES (?, ?)",
        (1, utc_now()),
    )


def _row_to_dict(row: sqlite3.Row | None) -> dict[str, Any]:
    return {key: row[key] for key in row.keys()} if row is not None else {}


def parse_job(row: sqlite3.Row | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Convert one SQLite job row into a JSON-safe dict with decoded params.
    - Guarantee: Returns an empty dict for a missing row, otherwise includes `params` decoded from `params_json`.
    - Fails: None; malformed params JSON falls back to an empty dict through `_json_loads`.
    """
    payload = _row_to_dict(row)
    if payload:
        payload["params"] = _json_loads(payload.get("params_json"), {})
    return payload


def parse_run(row: sqlite3.Row | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Convert one SQLite run row into a JSON-safe dict with decoded summary payload.
    - Guarantee: Returns an empty dict for a missing row, otherwise includes `summary` decoded from `summary_json`.
    - Fails: None; malformed summary JSON falls back to an empty dict through `_json_loads`.
    """
    payload = _row_to_dict(row)
    if payload:
        payload["summary"] = _json_loads(payload.get("summary_json"), {})
    return payload


def parse_claim_event(row: sqlite3.Row | None) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Convert one blackboard claim-event row into a JSON-safe public event dict.
    - Guarantee: Returns decoded `contradicts` and `payload` fields when a row is present, else an empty dict.
    - Fails: None; malformed JSON fields fall back to empty list/dict defaults.
    """
    payload = _row_to_dict(row)
    if payload:
        payload["contradicts"] = _json_loads(payload.get("contradicts_json"), [])
        payload["payload"] = _json_loads(payload.get("payload_json"), {})
    return payload


def execution_fingerprint(kind: str, provider: str, params: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Derive the deterministic execution fingerprint for job kind/provider/params identity.
    - Guarantee: Returns the first 16 hex chars of a SHA-256 digest over normalized kind, provider, and params.
    - Fails: Raises only if params cannot be converted into a JSON-serializable mapping.
    - Orders: JSON keys are sorted before hashing.
    """
    payload = {
        "kind": str(kind or "").strip(),
        "provider": str(provider or "local").strip().lower() or "local",
        "params": dict(params or {}),
    }
    encoded = _json_dumps(payload).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def enqueue_job(
    conn: sqlite3.Connection,
    *,
    kind: str,
    provider: str = "local",
    params: Mapping[str, Any] | None = None,
    idempotency_key: str,
    priority: int = 100,
    not_before: str | None = None,
    now: str | None = None,
) -> tuple[dict[str, Any], bool]:
    """
    [ACTION]
    - Teleology: Insert or recover a synthetic queued job under an active idempotency key.
    - Guarantee: Returns `(job, inserted)` where `inserted` is False when the active idempotency uniqueness guard selected an existing job.
    - Fails: Propagates sqlite3 errors other than the handled active-idempotency collision.
    - Writes: Inserts one jobs row on a fresh idempotency key.
    """
    stamp = now or utc_now()
    job_id = _sha1_token(f"{idempotency_key}:{stamp}:{uuid.uuid4().hex}", prefix="job")
    fp = execution_fingerprint(kind, provider, params or {})
    inserted = False
    try:
        conn.execute(
            """
            INSERT INTO jobs(
                id, kind, provider, params_json, idempotency_key, execution_fingerprint,
                state, priority, not_before, claim_owner, claim_expires_at,
                attempts, last_error, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0, NULL, ?, ?)
            """,
            (
                job_id,
                kind,
                provider,
                _json_dumps(dict(params or {})),
                idempotency_key,
                fp,
                JOB_QUEUED,
                int(priority),
                not_before,
                stamp,
                stamp,
            ),
        )
        inserted = True
    except sqlite3.IntegrityError:
        inserted = False
    row = conn.execute(
        "SELECT * FROM jobs WHERE idempotency_key = ? ORDER BY created_at DESC LIMIT 1",
        (idempotency_key,),
    ).fetchone()
    return parse_job(row), inserted


def fetch_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Read one job by id through the public row parser.
    - Guarantee: Returns a parsed job dict or `{}` when no row exists.
    - Fails: Propagates sqlite3 query errors from the supplied connection.
    - Reads: jobs table.
    """
    return parse_job(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())


def fetch_jobs(conn: sqlite3.Connection, *, states: Sequence[str] | None = None) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: List jobs in deterministic priority/creation order for queue and reconciliation passes.
    - Guarantee: Returns parsed job dicts, optionally filtered to the supplied states.
    - Fails: Propagates sqlite3 query errors.
    - Orders: Results are ordered by priority ascending, then created_at ascending.
    """
    params: list[Any] = []
    sql = "SELECT * FROM jobs"
    if states:
        sql += " WHERE state IN ({})".format(",".join("?" for _ in states))
        params.extend(states)
    sql += " ORDER BY priority ASC, created_at ASC"
    return [parse_job(row) for row in conn.execute(sql, params).fetchall()]


def claim_next_job(
    conn: sqlite3.Connection,
    *,
    owner: str,
    lease_seconds: int = 60,
    now: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Lease the next queued or recoverable job to a public worker owner.
    - Guarantee: Returns the updated claimed job, or `{}` when no eligible job is ready.
    - Fails: Propagates sqlite3 write errors; invalid timestamp text falls back to current UTC for lease math.
    - Writes: Updates state, claim owner, expiry, attempts, and updated_at for the selected job.
    """
    stamp = now or utc_now()
    row = conn.execute(
        """
        SELECT * FROM jobs
        WHERE state IN ('queued','recoverable')
          AND (not_before IS NULL OR not_before <= ?)
        ORDER BY priority ASC, created_at ASC
        LIMIT 1
        """,
        (stamp,),
    ).fetchone()
    if row is None:
        return {}
    job = parse_job(row)
    expires = (_to_dt(stamp) or datetime.now(timezone.utc)) + timedelta(seconds=lease_seconds)
    conn.execute(
        """
        UPDATE jobs
        SET state = ?, claim_owner = ?, claim_expires_at = ?,
            attempts = attempts + 1, updated_at = ?
        WHERE id = ?
        """,
        (JOB_CLAIMED, owner, expires.isoformat(), stamp, job["id"]),
    )
    return fetch_job(conn, job["id"])


def update_job_state(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    state: str,
    last_error: str | None = None,
    now: str | None = None,
) -> None:
    """
    [ACTION]
    - Teleology: Apply one explicit state transition to a synthetic job row.
    - Guarantee: Returns None after updating state, last_error, and updated_at for the target id.
    - Fails: Propagates sqlite3 write errors.
    - Writes: jobs table for the requested job id.
    """
    conn.execute(
        "UPDATE jobs SET state = ?, last_error = ?, updated_at = ? WHERE id = ?",
        (state, last_error, now or utc_now(), job_id),
    )


def requeue_expired_jobs(
    conn: sqlite3.Connection,
    *,
    now: str | None = None,
    message: str = "claim expired; requeued by public metabolism runtime capsule",
) -> int:
    """
    [ACTION]
    - Teleology: Recover claimed/running jobs whose lease expired in the synthetic queue.
    - Guarantee: Returns the number of rows moved to `recoverable` with owner/lease cleared and a review message.
    - Fails: Propagates sqlite3 query/write errors.
    - Writes: jobs rows whose claim_expires_at is older than the supplied timestamp.
    """
    stamp = now or utc_now()
    rows = conn.execute(
        """
        SELECT id FROM jobs
        WHERE state IN ('claimed','running')
          AND claim_expires_at IS NOT NULL
          AND claim_expires_at < ?
        """,
        (stamp,),
    ).fetchall()
    for row in rows:
        conn.execute(
            """
            UPDATE jobs
            SET state = ?, claim_owner = NULL, claim_expires_at = NULL,
                last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (JOB_RECOVERABLE, message, stamp, row["id"]),
        )
    return len(rows)


def start_run(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    log_path: str | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Record the start of one synthetic execution run and mark its job running.
    - Guarantee: Returns the parsed run row with a generated run id and started_at timestamp.
    - Fails: Propagates sqlite3 write errors or job-state update failures.
    - Writes: runs table and the associated jobs row.
    """
    run_id = _sha1_token(f"{job_id}:{now or utc_now()}:{uuid.uuid4().hex}", prefix="run")
    stamp = now or utc_now()
    conn.execute(
        """
        INSERT INTO runs(id, job_id, started_at, completed_at, returncode, log_path, summary_json)
        VALUES (?, ?, ?, NULL, NULL, ?, '{}')
        """,
        (run_id, job_id, stamp, log_path),
    )
    update_job_state(conn, job_id, state=JOB_RUNNING, now=stamp)
    return parse_run(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())


def complete_run(
    conn: sqlite3.Connection,
    run_id: str,
    *,
    returncode: int,
    now: str | None = None,
    finalize_job: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Finalize a synthetic run and optionally propagate terminal state to the job.
    - Guarantee: Returns the parsed run row after completed_at and returncode are written.
    - Fails: Propagates sqlite3 write errors.
    - Writes: runs table, and jobs table when `finalize_job` is true.
    """
    stamp = now or utc_now()
    conn.execute(
        "UPDATE runs SET completed_at = ?, returncode = ? WHERE id = ?",
        (stamp, int(returncode), run_id),
    )
    run = parse_run(conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone())
    if finalize_job and run:
        update_job_state(
            conn,
            str(run["job_id"]),
            state=JOB_COMPLETED if returncode == 0 else JOB_FAILED,
            now=stamp,
        )
    return run


def latest_run_for_job(conn: sqlite3.Connection, job_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Fetch the newest run row attached to a job for reconciliation checks.
    - Guarantee: Returns the most recent parsed run dict or `{}` when the job has no runs.
    - Fails: Propagates sqlite3 query errors.
    - Reads: runs table ordered by started_at descending.
    """
    return parse_run(
        conn.execute(
            "SELECT * FROM runs WHERE job_id = ? ORDER BY started_at DESC LIMIT 1",
            (job_id,),
        ).fetchone()
    )


def append_claim_event(
    conn: sqlite3.Connection,
    *,
    event_kind: str,
    claim_id: str,
    subject_ref: str,
    predicate: str,
    object_value: str,
    assertion_event_id: str | None = None,
    contradicts: Sequence[str] = (),
    authority_ceiling: str = "runtime_claim_not_source_authority",
    freshness_state: str = "current",
    payload: Mapping[str, Any] | None = None,
    now: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Append one blackboard claim assertion or invalidation event to the synthetic public ledger.
    - Guarantee: Returns the parsed event row with stable decoded payload fields.
    - Fails: Propagates sqlite3 write/query errors.
    - Writes: blackboard_claim_events table; invalidation event kinds also stamp invalid/expired fields.
    """
    stamp = now or utc_now()
    event_id = _sha1_token(
        f"{event_kind}:{claim_id}:{subject_ref}:{predicate}:{object_value}:{stamp}:{uuid.uuid4().hex}",
        prefix="tc",
    )
    conn.execute(
        """
        INSERT INTO blackboard_claim_events(
            event_id, event_kind, assertion_event_id, claim_id, subject_ref,
            predicate, object, episode_id, asserted_at, valid_at, invalid_at,
            expired_at, superseded_by, contradicts_json, authority_ceiling,
            freshness_state, payload_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            event_id,
            event_kind,
            assertion_event_id,
            claim_id,
            subject_ref,
            predicate,
            object_value,
            f"metabolism_blackboard:{claim_id}",
            stamp,
            stamp,
            stamp if event_kind in {"claim_expired", "claim_superseded", "claim_contradicted"} else None,
            stamp if event_kind == "claim_expired" else None,
            None,
            _json_dumps(list(contradicts)),
            authority_ceiling,
            freshness_state,
            _json_dumps(dict(payload or {})),
            stamp,
        ),
    )
    return parse_claim_event(conn.execute("SELECT * FROM blackboard_claim_events WHERE event_id = ?", (event_id,)).fetchone())


def build_blackboard_projection(conn: sqlite3.Connection) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project current active public blackboard claims from the claim-event ledger.
    - Guarantee: Returns counts plus compact active-claim rows after removing contradicted, superseded, or expired assertions.
    - Fails: Propagates sqlite3 query errors.
    - Reads: blackboard_claim_events ordered by created_at.
    """
    rows = [parse_claim_event(row) for row in conn.execute("SELECT * FROM blackboard_claim_events ORDER BY created_at ASC").fetchall()]
    invalidated = {
        str(row.get("assertion_event_id"))
        for row in rows
        if row.get("assertion_event_id")
        and row.get("event_kind") in {"claim_expired", "claim_superseded", "claim_contradicted"}
    }
    active = [
        row
        for row in rows
        if row.get("event_kind") == "claim_asserted" and row.get("event_id") not in invalidated
    ]
    contradiction_rows = [row for row in rows if row.get("event_kind") == "claim_contradicted"]
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "active_claim_count": len(active),
        "claim_event_count": len(rows),
        "contradiction_count": len(contradiction_rows),
        "active_claims": [
            {
                "event_id": row.get("event_id"),
                "claim_id": row.get("claim_id"),
                "subject_ref": row.get("subject_ref"),
                "predicate": row.get("predicate"),
                "object": row.get("object"),
                "authority_ceiling": row.get("authority_ceiling"),
                "freshness_state": row.get("freshness_state"),
            }
            for row in active
        ],
    }


@dataclass
class ReconciliationFinding:
    """
    [ROLE]
    - Teleology: Carry one reconciliation defect as a serializable public review row.
    - Ownership: Owned by the reconciliation pass that constructs it; callers consume it as receipt data.
    - Mutability: Ordinary dataclass fields may be mutated by the owner before serialization; `detail` gets a fresh dict per instance.
    - Concurrency: Holds no shared handles and is safe to pass between local evaluation steps after construction.
    """
    rule: str
    object_kind: str
    object_id: str | None
    expected: str
    observed: str
    action: str = ACTION_OPERATOR_REVIEW_REQUIRED
    severity: str = "warning"
    detail: dict[str, Any] = field(default_factory=dict)

    @property
    def finding_id(self) -> str:
        """
        [ACTION]
        - Teleology: Derive a compact stable identifier for this finding's rule/object pair.
        - Guarantee: Returns the first 16 hex chars of a SHA-1 digest over rule and object id.
        - Fails: None; missing object ids are represented as an empty string.
        """
        return hashlib.sha1(f"{self.rule}:{self.object_id or ''}".encode("utf-8")).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """
        [ACTION]
        - Teleology: Serialize the reconciliation finding with its derived identifier.
        - Guarantee: Returns a dict containing all dataclass fields plus `finding_id`.
        - Fails: None for normal dataclass field values.
        """
        payload = asdict(self)
        payload["finding_id"] = self.finding_id
        return payload


def reconcile(
    conn: sqlite3.Connection,
    repo_root: Path,
    *,
    now: datetime | None = None,
    log_freshness_threshold_seconds: float = 600.0,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Detect public queue/run/log inconsistencies that require operator review instead of auto-repair.
    - Guarantee: Returns a bounded receipt with status `healthy` or `needs_review`, rule counts, findings, claim ceiling, and anti-claims.
    - Fails: Propagates sqlite3 query errors and filesystem stat errors for existing log paths.
    - Reads: jobs, runs, and repo-relative log paths referenced by active runs.
    """
    stamp = now or datetime.now(timezone.utc)
    findings: list[ReconciliationFinding] = []
    for job in fetch_jobs(conn, states=[JOB_CLAIMED, JOB_RUNNING]):
        job_id = str(job.get("id") or "")
        run = latest_run_for_job(conn, job_id)
        if not run:
            findings.append(
                ReconciliationFinding(
                    rule=RULE_RUNNING_JOB_NO_RUN_ROW,
                    object_kind="job",
                    object_id=job_id,
                    expected="claimed/running job has a run row",
                    observed="no runs row found",
                    detail={"state": job.get("state"), "claim_owner": job.get("claim_owner")},
                )
            )
            continue
        if run.get("completed_at") and job.get("state") in {JOB_CLAIMED, JOB_RUNNING}:
            findings.append(
                ReconciliationFinding(
                    rule=RULE_RUN_FINALIZED_BUT_JOB_RUNNING,
                    object_kind="job",
                    object_id=job_id,
                    expected="completed run implies terminal job state",
                    observed=f"run.completed_at={run.get('completed_at')}, job.state={job.get('state')}",
                    detail={"run_id": run.get("id"), "returncode": run.get("returncode")},
                )
            )
        log_rel = str(run.get("log_path") or "").strip()
        if log_rel and not run.get("completed_at"):
            log_path = repo_root / log_rel
            if not log_path.exists():
                findings.append(
                    ReconciliationFinding(
                        rule=RULE_RUNNING_JOB_MISSING_LAUNCH_LOG,
                        object_kind="run",
                        object_id=str(run.get("id") or ""),
                        expected="running run log exists",
                        observed=f"log missing: {log_rel}",
                        detail={"job_id": job_id, "log_path": log_rel},
                    )
                )
            else:
                age = stamp.timestamp() - log_path.stat().st_mtime
                if age > log_freshness_threshold_seconds:
                    findings.append(
                        ReconciliationFinding(
                            rule=RULE_RUNNING_JOB_STALE_LAUNCH_LOG,
                            object_kind="run",
                            object_id=str(run.get("id") or ""),
                            expected=f"log mtime within {log_freshness_threshold_seconds:.0f}s",
                            observed=f"log mtime is {age:.0f}s old",
                            detail={
                                "job_id": job_id,
                                "log_path": log_rel,
                                "age_seconds": age,
                                "threshold_seconds": log_freshness_threshold_seconds,
                            },
                        )
                    )
    rule_counts: dict[str, int] = {}
    for finding in findings:
        rule_counts[finding.rule] = rule_counts.get(finding.rule, 0) + 1
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "generated_at": utc_now(),
        "status": "needs_review" if findings else "healthy",
        "finding_count": len(findings),
        "rule_counts": rule_counts,
        "findings": [finding.to_dict() for finding in findings],
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
    }


def _case_queue_recovery(root: Path) -> dict[str, Any]:
    conn = connect(root / "metabolism.sqlite")
    first, inserted_first = enqueue_job(
        conn,
        kind="public_demo",
        provider="local",
        params={"demo": "lease"},
        idempotency_key="demo:lease",
    )
    _second, inserted_second = enqueue_job(
        conn,
        kind="public_demo",
        provider="local",
        params={"demo": "lease"},
        idempotency_key="demo:lease",
    )
    claimed = claim_next_job(conn, owner="worker:demo", lease_seconds=-1)
    requeued = requeue_expired_jobs(conn)
    final = fetch_job(conn, first["id"])
    return {
        "status": "pass" if inserted_first and not inserted_second and requeued == 1 and final["state"] == JOB_RECOVERABLE else "fail",
        "inserted_first": inserted_first,
        "inserted_second": inserted_second,
        "claimed_state": claimed.get("state"),
        "requeued_count": requeued,
        "final_state": final.get("state"),
        "journal_mode": conn.execute("PRAGMA journal_mode;").fetchone()[0],
    }


def _case_blackboard_projection(root: Path) -> dict[str, Any]:
    conn = connect(root / "metabolism.sqlite")
    asserted = append_claim_event(
        conn,
        event_kind="claim_asserted",
        claim_id="claim-demo",
        subject_ref="codex:demo",
        predicate="owns_path",
        object_value="public/demo.py",
    )
    append_claim_event(
        conn,
        event_kind="claim_contradicted",
        claim_id="claim-demo",
        assertion_event_id=str(asserted["event_id"]),
        subject_ref="codex:demo",
        predicate="invalidates_session_currentness",
        object_value="public/demo.py",
        contradicts=[str(asserted["event_id"])],
        freshness_state="contradicted",
    )
    projection = build_blackboard_projection(conn)
    return {
        "status": "pass" if projection["active_claim_count"] == 0 and projection["contradiction_count"] == 1 else "fail",
        "projection": projection,
    }


def _case_running_job_no_run_row(root: Path) -> dict[str, Any]:
    conn = connect(root / "metabolism.sqlite")
    job, _inserted = enqueue_job(
        conn,
        kind="public_demo",
        provider="local",
        params={},
        idempotency_key="demo:no-run",
    )
    claim_next_job(conn, owner="worker:demo")
    update_job_state(conn, job["id"], state=JOB_RUNNING)
    receipt = reconcile(conn, root)
    return {
        "status": "pass" if RULE_RUNNING_JOB_NO_RUN_ROW in receipt["rule_counts"] else "fail",
        "reconciliation": receipt,
    }


def _case_finalized_run_running_job(root: Path) -> dict[str, Any]:
    conn = connect(root / "metabolism.sqlite")
    job, _inserted = enqueue_job(
        conn,
        kind="public_demo",
        provider="local",
        params={},
        idempotency_key="demo:finalized",
    )
    claim_next_job(conn, owner="worker:demo")
    run = start_run(conn, job["id"], log_path="logs/demo.log")
    complete_run(conn, str(run["id"]), returncode=0, finalize_job=False)
    receipt = reconcile(conn, root)
    return {
        "status": "pass" if RULE_RUN_FINALIZED_BUT_JOB_RUNNING in receipt["rule_counts"] else "fail",
        "reconciliation": receipt,
    }


def _case_stale_log(root: Path) -> dict[str, Any]:
    conn = connect(root / "metabolism.sqlite")
    log_path = root / "logs/demo.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text("started\n", encoding="utf-8")
    old = datetime.now(timezone.utc) - timedelta(seconds=1200)
    os.utime(log_path, (old.timestamp(), old.timestamp()))
    job, _inserted = enqueue_job(
        conn,
        kind="public_demo",
        provider="local",
        params={},
        idempotency_key="demo:stale-log",
    )
    claim_next_job(conn, owner="worker:demo")
    start_run(conn, job["id"], log_path="logs/demo.log")
    receipt = reconcile(conn, root, log_freshness_threshold_seconds=60)
    return {
        "status": "pass" if RULE_RUNNING_JOB_STALE_LAUNCH_LOG in receipt["rule_counts"] else "fail",
        "reconciliation": receipt,
    }


CASE_RUNNERS = {
    "queue_recovery": _case_queue_recovery,
    "blackboard_projection": _case_blackboard_projection,
    "running_job_no_run_row": _case_running_job_no_run_row,
    "finalized_run_running_job": _case_finalized_run_running_job,
    "stale_log": _case_stale_log,
}


def evaluate_case(case: Mapping[str, Any], *, scratch: Path, path: str = "") -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute one public fixture case against an isolated synthetic metabolism scratch root.
    - Guarantee: Returns the observed receipt and whether it matched the expected status.
    - Fails: Raises ValueError for unknown case kinds; propagates runner/JSON/runtime errors.
    - Writes: Creates a per-case scratch directory under the supplied scratch root.
    """
    case_id = str(case.get("case_id") or Path(path).stem)
    case_kind = str(case.get("case_kind") or case_id)
    runner = CASE_RUNNERS.get(case_kind)
    if runner is None:
        raise ValueError(f"unknown metabolism fixture case kind: {case_kind}")
    root = scratch / case_id
    root.mkdir(parents=True, exist_ok=True)
    observed = runner(root)
    expected_status = str(case.get("expected_status") or "pass")
    return {
        "case_id": case_id,
        "case_kind": case_kind,
        "path": path,
        "expected_status": expected_status,
        "observed_status": observed["status"],
        "expectation_met": observed["status"] == expected_status,
        "receipt": observed,
    }


def evaluate_fixture_dir(input_dir: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Evaluate all public metabolism fixture JSON files as one receipt.
    - Guarantee: Returns pass only when at least one case exists and every case meets its expected status.
    - Fails: Raises ValueError for non-object fixture JSON and propagates JSON or runner failures.
    - Reads: `*.json` fixture files sorted by path.
    """
    cases: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=f"{ORGAN_ID}_fixtures_") as tmp:
        scratch = Path(tmp)
        for path in sorted(input_dir.glob("*.json")):
            payload = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError(f"{path} did not contain a JSON object")
            cases.append(evaluate_case(payload, scratch=scratch, path=str(path)))
    passed = sum(1 for case in cases if case["expectation_met"])
    return {
        "schema_version": SCHEMA_VERSION,
        "organ_id": ORGAN_ID,
        "source_refs": list(SOURCE_REFS),
        "source_to_target_relation": SOURCE_TO_TARGET_RELATION,
        "claim_ceiling": CLAIM_CEILING,
        "anti_claims": list(ANTI_CLAIMS),
        "case_count": len(cases),
        "passed_case_count": passed,
        "status": "pass" if cases and passed == len(cases) else "fail",
        "cases": cases,
    }


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Define the command-line interface for the public metabolism runtime capsule.
    - Guarantee: Returns an ArgumentParser with the required `evaluate-fixtures` subcommand.
    - Fails: None during parser construction.
    """
    parser = argparse.ArgumentParser(description="Engine Room metabolism runtime capsule.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    fixtures = subparsers.add_parser("evaluate-fixtures", help="Evaluate public fixture cases.")
    fixtures.add_argument("--input", required=True)
    fixtures.add_argument("--json", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Dispatch the public CLI, print fixture evaluation output, and translate pass/fail into a process exit code.
    - Guarantee: Returns 0 for passing fixture evaluation and 1 for failing fixture evaluation.
    - Fails: argparse raises SystemExit for invalid CLI input; AssertionError marks impossible command dispatch.
    """
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.command == "evaluate-fixtures":
        payload = evaluate_fixture_dir(Path(args.input))
        if args.json:
            print(json.dumps(payload, indent=2, sort_keys=True))
        else:
            print(f"{payload['organ_id']}: {payload['status']}")
        return 0 if payload["status"] == "pass" else 1
    raise AssertionError(args.command)


if __name__ == "__main__":
    raise SystemExit(main())
