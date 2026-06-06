"""Standalone concurrency and git preflight guard for the release microcosm.

[PURPOSE]
Give clone-local agents a small, dependency-free way to claim paths, avoid
duplicate slow commands, and choose a git-safe landing lane without private
ai_workflow state.

[INTERFACE]
Exports preflight, claim renewal, command singleflight, status, release, and
finalize helpers consumed by the CLI.

[FLOW]
Replay a JSONL event log under `.idea_microcosm/concurrency`, evaluate active
leases and git state, then append claim, command, renew, or closeout events
under an atomic lock.

[DEPENDENCIES]
Uses only the Python standard library plus the local git executable when a
clone has git metadata available.

[CONSTRAINTS]
This is local clone coordination only. It is not a scheduler, not durable
workflow orchestration, and not hosted-public or publication evidence.
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import subprocess
import time
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


DEFAULT_STATE_DIR = ".idea_microcosm/concurrency"
SCHEMA_VERSION = "microcosm_concurrency_guard_v0"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _state_path(root: Path, state_dir: str) -> Path:
    root = root.resolve()
    return root / _normalize_path(root, state_dir)


def _events_path(root: Path, state_dir: str) -> Path:
    return _state_path(root, state_dir) / "events.jsonl"


def _snapshot_path(root: Path, state_dir: str) -> Path:
    return _state_path(root, state_dir) / "active_claims.json"


def _normalize_path(root: Path, value: str) -> str:
    root = root.resolve()
    raw = value.replace("\\", "/")
    if Path(raw).is_absolute():
        try:
            return Path(raw).resolve().relative_to(root).as_posix()
        except ValueError as exc:
            raise ValueError(f"path is outside microcosm root: {value}") from exc
    pure = PurePosixPath(raw)
    parts: list[str] = []
    for part in pure.parts:
        if part in ("", "."):
            continue
        if part == "..":
            raise ValueError(f"path must not escape microcosm root: {value}")
        parts.append(part)
    if not parts:
        raise ValueError("path must not be empty")
    return PurePosixPath(*parts).as_posix()


def _normalize_paths(root: Path, values: list[str]) -> list[str]:
    seen: set[str] = set()
    normalized: list[str] = []
    for value in values:
        path = _normalize_path(root, value)
        if path not in seen:
            seen.add(path)
            normalized.append(path)
    return normalized


def _paths_overlap(left: str, right: str) -> bool:
    return left == right or left.startswith(f"{right}/") or right.startswith(f"{left}/")


def _path_is_within(path: str, scope: str) -> bool:
    return path == scope or path.startswith(f"{scope}/")


def _event_hash(event: dict[str, Any]) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


@contextmanager
def _locked_events(root: Path, state_dir: str, *, wait_seconds: float = 2.0) -> Iterator[Path]:
    state = _state_path(root, state_dir)
    state.mkdir(parents=True, exist_ok=True)
    lock_path = state / "events.lock"
    deadline = time.monotonic() + wait_seconds
    fd: int | None = None
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(
                fd,
                json.dumps({"pid": os.getpid(), "locked_at": utc_now_iso()}, sort_keys=True).encode("utf-8"),
            )
            break
        except FileExistsError:
            try:
                age = time.time() - lock_path.stat().st_mtime
            except FileNotFoundError:
                continue
            if age > 300:
                lock_path.unlink(missing_ok=True)
                continue
            if time.monotonic() >= deadline:
                raise RuntimeError(f"concurrency event log is locked: {lock_path}")
            time.sleep(0.05)
    try:
        yield _events_path(root, state_dir)
    finally:
        if fd is not None:
            os.close(fd)
        lock_path.unlink(missing_ok=True)


def _read_events(root: Path, state_dir: str = DEFAULT_STATE_DIR) -> list[dict[str, Any]]:
    path = _events_path(root, state_dir)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid concurrency event JSON at {path}:{line_no}") from exc
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_event(root: Path, state_dir: str, event: dict[str, Any]) -> None:
    path = _events_path(root, state_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    event["event_hash"] = _event_hash(event)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


def _active_claim_state(
    root: Path,
    *,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    now = _parse_utc(at)
    active_by_claim: dict[str, dict[str, Any]] = {}
    released_sessions: set[str] = set()
    stale_claims: list[dict[str, Any]] = []
    for event in _read_events(root, state_dir):
        event_type = event.get("event_type")
        session_id = str(event.get("session_id", ""))
        if event_type == "claim":
            claim_id = str(event.get("claim_id") or event.get("event_id") or "")
            if claim_id:
                active_by_claim[claim_id] = dict(event)
            if session_id in released_sessions:
                released_sessions.remove(session_id)
        elif event_type == "renew":
            renewed_at_value = str(event.get("renewed_at") or "")
            lease_expires_at = str(event.get("lease_expires_at") or "")
            if not renewed_at_value or not lease_expires_at:
                continue
            renewed_at = _parse_utc(renewed_at_value)
            claim_ids = {str(claim_id) for claim_id in event.get("claim_ids", []) if claim_id}
            for claim_id, claim in list(active_by_claim.items()):
                if claim.get("session_id") != session_id:
                    continue
                if claim_ids and claim_id not in claim_ids:
                    continue
                previous_expires_at = _parse_utc(str(claim.get("lease_expires_at", "")))
                if previous_expires_at <= renewed_at:
                    continue
                claim["lease_expires_at"] = lease_expires_at
                claim["renewed_at"] = renewed_at_value
                claim["renewal_event_id"] = event.get("event_id")
                claim["renewal_count"] = int(claim.get("renewal_count") or 0) + 1
        elif event_type in {"release", "finalize"}:
            released_sessions.add(session_id)
            active_by_claim = {
                claim_id: claim
                for claim_id, claim in active_by_claim.items()
                if claim.get("session_id") != session_id
            }

    active_claims: list[dict[str, Any]] = []
    for claim in active_by_claim.values():
        expires_at = _parse_utc(str(claim.get("lease_expires_at", "")))
        if expires_at <= now:
            stale_claims.append(claim)
        else:
            active_claims.append(claim)
    return {
        "active_claims": sorted(active_claims, key=lambda row: str(row.get("claimed_at", ""))),
        "stale_claims": sorted(stale_claims, key=lambda row: str(row.get("lease_expires_at", ""))),
    }


def _command_run_state(
    root: Path,
    *,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    now = _parse_utc(at)
    active_by_run: dict[str, dict[str, Any]] = {}
    completed_runs: list[dict[str, Any]] = []
    for event in _read_events(root, state_dir):
        event_type = event.get("event_type")
        session_id = str(event.get("session_id", ""))
        if event_type == "command_start":
            run_id = str(event.get("run_id") or event.get("event_id") or "")
            if run_id:
                active_by_run[run_id] = dict(event)
        elif event_type == "command_finish":
            run_id = str(event.get("run_id") or "")
            started = active_by_run.pop(run_id, {})
            completed = {**started, **event} if started else dict(event)
            if run_id:
                completed_runs.append(completed)
        elif event_type in {"release", "finalize"}:
            active_by_run = {
                run_id: run
                for run_id, run in active_by_run.items()
                if run.get("session_id") != session_id
            }

    active_runs: list[dict[str, Any]] = []
    stale_runs: list[dict[str, Any]] = []
    for run in active_by_run.values():
        expires_at = _parse_utc(str(run.get("lease_expires_at", "")))
        if expires_at <= now:
            stale_runs.append(run)
        else:
            active_runs.append(run)
    return {
        "active_command_runs": sorted(active_runs, key=lambda row: str(row.get("started_at", ""))),
        "stale_command_runs": sorted(stale_runs, key=lambda row: str(row.get("lease_expires_at", ""))),
        "completed_command_runs": sorted(
            completed_runs,
            key=lambda row: str(row.get("finished_at", "")),
            reverse=True,
        ),
    }


def _write_active_snapshot(root: Path, state_dir: str, generated_at: str, state: dict[str, Any]) -> None:
    snapshot = {
        "kind": "microcosm_concurrency_active_claims",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "state_dir": state_dir,
        "active_claims": state["active_claims"],
        "stale_claims": state["stale_claims"],
    }
    _snapshot_path(root, state_dir).write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _run_git(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, check=False)


def _quote_paths(paths: list[str]) -> str:
    return " ".join(shlex.quote(path) for path in paths)


def _quote_arg(value: str) -> str:
    return shlex.quote(value)


def _git_status_rows(output: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        if not line:
            continue
        index_status = line[0] if len(line) > 0 else " "
        worktree_status = line[1] if len(line) > 1 else " "
        path = line[3:] if len(line) > 3 else line
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        rows.append({"index_status": index_status, "worktree_status": worktree_status, "path": path.strip()})
    return rows


def _git_root_prefix(root: Path) -> str:
    top = _run_git(root, ["rev-parse", "--show-toplevel"])
    if top.returncode != 0:
        return ""
    try:
        rel = root.resolve().relative_to(Path(top.stdout.strip()).resolve())
    except ValueError:
        return ""
    prefix = rel.as_posix()
    return "" if prefix == "." else prefix


def _status_path_relative_to_root(path: str, root_prefix: str) -> str | None:
    if not root_prefix:
        return path
    if path == root_prefix:
        return "."
    prefix = f"{root_prefix}/"
    if path.startswith(prefix):
        return path[len(prefix) :]
    return None


def _git_status(root: Path, owner_paths: list[str], *, state_dir: str = DEFAULT_STATE_DIR) -> dict[str, Any]:
    inside = _run_git(root, ["rev-parse", "--is-inside-work-tree"])
    if inside.returncode != 0 or inside.stdout.strip() != "true":
        return {
            "available": False,
            "status": "not_a_git_worktree",
            "scoped_path_commit_allowed": False,
            "broad_git_add_blocked": False,
            "normal_git_commit_blocked": False,
        }

    root_prefix = _git_root_prefix(root)
    status = _run_git(root, ["status", "--porcelain=v1", "--", "."])
    state_prefix = _normalize_path(root, state_dir)
    status_rows: list[dict[str, str]] = []
    for row in _git_status_rows(status.stdout):
        relative_path = _status_path_relative_to_root(row["path"], root_prefix)
        if relative_path is None:
            continue
        if relative_path == state_prefix or relative_path.startswith(f"{state_prefix}/"):
            continue
        status_rows.append({**row, "path": relative_path})
    dirty_paths = sorted({row["path"] for row in status_rows})
    staged_paths = sorted(
        {
            row["path"]
            for row in status_rows
            if row["index_status"] not in (" ", "?")
        }
    )

    def owned(path: str) -> bool:
        return any(_paths_overlap(path, owner_path) for owner_path in owner_paths)

    owner_dirty = sorted(path for path in dirty_paths if owned(path))
    owner_staged = sorted(path for path in staged_paths if owned(path))
    external_dirty = sorted(path for path in dirty_paths if not owned(path))
    external_staged = sorted(path for path in staged_paths if not owned(path))
    head = _run_git(root, ["rev-parse", "HEAD"])
    branch = _run_git(root, ["rev-parse", "--abbrev-ref", "HEAD"])
    upstream = _run_git(root, ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"])
    upstream_ref = upstream.stdout.strip() if upstream.returncode == 0 else None
    ahead = None
    behind = None
    if upstream_ref:
        counts = _run_git(root, ["rev-list", "--left-right", "--count", f"{upstream_ref}...HEAD"])
        if counts.returncode == 0:
            parts = counts.stdout.strip().split()
            if len(parts) == 2:
                behind = int(parts[0])
                ahead = int(parts[1])
    broad_add_blocked = bool(external_dirty)
    normal_commit_blocked = bool(external_staged)
    scoped_allowed = bool(owner_paths) and not normal_commit_blocked
    unsafe_commands = []
    if broad_add_blocked:
        unsafe_commands.extend(["git add -A", "git add .", "git commit -am <message>"])
    if normal_commit_blocked:
        unsafe_commands.append("git commit -m <message>")
    return {
        "available": True,
        "status": "ok",
        "head": head.stdout.strip() if head.returncode == 0 else None,
        "branch": branch.stdout.strip() if branch.returncode == 0 else None,
        "upstream": upstream_ref,
        "ahead": ahead,
        "behind": behind,
        "dirty_path_count": len(dirty_paths),
        "staged_path_count": len(staged_paths),
        "owner_path_count": len(owner_paths),
        "owner_dirty_path_count": len(owner_dirty),
        "owner_staged_path_count": len(owner_staged),
        "external_dirty_path_count": len(external_dirty),
        "external_staged_path_count": len(external_staged),
        "owner_dirty_paths_preview": owner_dirty[:20],
        "owner_staged_paths_preview": owner_staged[:20],
        "external_dirty_paths_preview": external_dirty[:20],
        "external_staged_paths_preview": external_staged[:20],
        "broad_git_add_blocked": broad_add_blocked,
        "normal_git_commit_blocked": normal_commit_blocked,
        "scoped_path_commit_allowed": scoped_allowed,
        "safe_landing_lane": "scoped_path_commit" if scoped_allowed else "hold_until_index_is_unmixed",
        "unsafe_commands": unsafe_commands,
        "safe_commands": [
            "git diff --cached --name-only",
            "git add -- " + _quote_paths(owner_paths),
            "git commit -m <message>",
        ]
        if scoped_allowed
        else ["git diff --cached --name-only"],
    }


def _active_claim_path_conflicts(
    active_claims: list[dict[str, Any]],
    requested_paths: list[str],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for active in active_claims:
        if session_id and active.get("session_id") == session_id:
            continue
        for requested in requested_paths:
            for active_path in active.get("owner_paths", []):
                if _paths_overlap(requested, str(active_path)):
                    conflicts.append(
                        {
                            "requested_path": requested,
                            "active_path": active_path,
                            "active_session_id": active.get("session_id"),
                            "claim_id": active.get("claim_id"),
                            "lease_expires_at": active.get("lease_expires_at"),
                        }
                    )
    return conflicts


def _active_command_run_path_conflicts(
    active_command_runs: list[dict[str, Any]],
    requested_paths: list[str],
    *,
    session_id: str | None = None,
) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for run in active_command_runs:
        if session_id and run.get("session_id") == session_id:
            continue
        for requested in requested_paths:
            for run_path in run.get("owner_paths", []):
                if _paths_overlap(requested, str(run_path)):
                    conflicts.append(
                        {
                            "requested_path": requested,
                            "active_path": run_path,
                            "active_session_id": run.get("session_id"),
                            "run_id": run.get("run_id"),
                            "command_key": run.get("command_key"),
                            "lease_expires_at": run.get("lease_expires_at"),
                        }
                    )
    return conflicts


def status_report(
    root: Path,
    *,
    owner_paths: list[str] | None = None,
    session_id: str | None = None,
    command_key: str | None = None,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    """Return a read-only report of active and stale clone-local claims."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths or []) if owner_paths else []
    state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
    command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
    active_claims = state["active_claims"]
    stale_claims = state["stale_claims"]

    def overlaps_requested_paths(claim: dict[str, Any]) -> bool:
        if not normalized_paths:
            return True
        return any(
            _paths_overlap(requested, str(active_path))
            for requested in normalized_paths
            for active_path in claim.get("owner_paths", [])
        )

    matching_active_claims = [
        claim
        for claim in active_claims
        if (not session_id or claim.get("session_id") == session_id)
        and (not command_key or claim.get("command_key") == command_key)
        and overlaps_requested_paths(claim)
    ]
    active_path_conflicts = _active_claim_path_conflicts(
        active_claims,
        normalized_paths,
        session_id=session_id,
    ) if normalized_paths else []
    active_command_run_conflicts = _active_command_run_path_conflicts(
        command_state["active_command_runs"],
        normalized_paths,
        session_id=session_id,
    ) if normalized_paths else []
    active_command_key_claims = [
        {
            "active_session_id": active.get("session_id"),
            "claim_id": active.get("claim_id"),
            "lease_expires_at": active.get("lease_expires_at"),
        }
        for active in active_claims
        if command_key and active.get("command_key") == command_key and active.get("session_id") != session_id
    ]

    def command_run_matches(run: dict[str, Any]) -> bool:
        if session_id and run.get("session_id") != session_id:
            return False
        if command_key and run.get("command_key") != command_key:
            return False
        if not normalized_paths:
            return True
        return any(
            _paths_overlap(requested, str(run_path))
            for requested in normalized_paths
            for run_path in run.get("owner_paths", [])
        )

    matching_active_command_runs = [
        run for run in command_state["active_command_runs"] if command_run_matches(run)
    ]
    matching_stale_command_runs = [
        run for run in command_state["stale_command_runs"] if command_run_matches(run)
    ]
    recent_completed_command_runs = [
        run for run in command_state["completed_command_runs"] if command_run_matches(run)
    ][:20]
    return {
        "kind": "microcosm_concurrency_status",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "command_key": command_key,
        "state_dir": state_dir,
        "owner_paths": normalized_paths,
        "active_claim_count": len(active_claims),
        "stale_claim_count": len(stale_claims),
        "active_command_run_count": len(command_state["active_command_runs"]),
        "stale_command_run_count": len(command_state["stale_command_runs"]),
        "completed_command_run_count": len(command_state["completed_command_runs"]),
        "matching_active_claim_count": len(matching_active_claims),
        "matching_active_command_run_count": len(matching_active_command_runs),
        "active_path_conflicts": active_path_conflicts,
        "active_command_run_conflicts": active_command_run_conflicts,
        "active_command_key_claims": active_command_key_claims,
        "matching_active_command_runs": matching_active_command_runs,
        "matching_stale_command_runs": matching_stale_command_runs,
        "recent_completed_command_runs": recent_completed_command_runs,
        "active_claims": active_claims,
        "stale_claims": stale_claims,
        "git": _git_status(root, normalized_paths, state_dir=state_dir),
        "next": [
            "Run concurrency-preflight --claim before mutation when no matching active claim exists.",
            "Run concurrency-command-start before slow validation or build commands with a shared command key.",
            "Run concurrency-command-finish with receipt evidence so other agents can reuse a completed command run.",
            "Run concurrency-renew during long edits or validation to keep a live lease from expiring.",
            "Treat stale claims as historical evidence only; do not renew them after expiry.",
        ],
        "authority_boundary": "standalone_clone_local_status_not_private_work_ledger_or_publication_evidence",
    }


def start_command(
    root: Path,
    *,
    session_id: str,
    command_key: str,
    command: str | None = None,
    owner_paths: list[str] | None = None,
    lease_minutes: int = 60,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
    allow_duplicate: bool = False,
) -> dict[str, Any]:
    """Reserve a clone-local command key so duplicate slow commands can attach."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths or []) if owner_paths else []
    normalized_key = command_key.strip()
    lease_expires_at = (
        _parse_utc(generated_at) + timedelta(minutes=max(1, lease_minutes))
    ).isoformat().replace("+00:00", "Z")

    with _locked_events(root, state_dir):
        claim_state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
        active_command_runs = [
            run for run in command_state["active_command_runs"] if run.get("command_key") == normalized_key
        ]
        active_path_conflicts = _active_claim_path_conflicts(
            claim_state["active_claims"],
            normalized_paths,
            session_id=session_id,
        ) if normalized_paths else []
        active_command_run_path_conflicts = _active_command_run_path_conflicts(
            command_state["active_command_runs"],
            normalized_paths,
        ) if normalized_paths else []
        active_command_key_claims = [
            claim
            for claim in claim_state["active_claims"]
            if normalized_key and claim.get("command_key") == normalized_key and claim.get("session_id") != session_id
        ]
        blockers: list[dict[str, Any]] = []
        if not normalized_key:
            blockers.append({"blocker": "missing_command_key"})
        if active_path_conflicts:
            blockers.append(
                {
                    "blocker": "active_path_conflict",
                    "conflicts": active_path_conflicts,
                    "why": "Another live claim owns a requested command path; wait, release, or choose a disjoint path.",
                }
            )
        if active_command_run_path_conflicts and not allow_duplicate:
            blockers.append(
                {
                    "blocker": "active_command_run_conflict",
                    "conflicts": active_command_run_path_conflicts,
                    "why": "A live command run already covers a requested path; attach or wait instead of overlapping it.",
                }
            )
        if active_command_runs and not allow_duplicate:
            blockers.append(
                {
                    "blocker": "active_command_key_singleflight",
                    "command_key": normalized_key,
                    "active_runs": [
                        {
                            "run_id": run.get("run_id"),
                            "session_id": run.get("session_id"),
                            "lease_expires_at": run.get("lease_expires_at"),
                            "command": run.get("command"),
                        }
                        for run in active_command_runs
                    ],
                    "attach_to_run_id": active_command_runs[0].get("run_id"),
                    "why": "A live command run already owns this command key; attach to its status instead of duplicating the command.",
                }
            )
        if active_command_key_claims:
            blockers.append(
                {
                    "blocker": "active_command_key_claim",
                    "command_key": normalized_key,
                    "active_claims": [
                        {
                            "claim_id": claim.get("claim_id"),
                            "session_id": claim.get("session_id"),
                            "lease_expires_at": claim.get("lease_expires_at"),
                        }
                        for claim in active_command_key_claims
                    ],
                    "why": "Another session already claimed this command key through concurrency-preflight.",
                }
            )
        if blockers:
            return {
                "kind": "microcosm_concurrency_command_start",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "command_key": normalized_key,
                "command": command,
                "owner_paths": normalized_paths,
                "state_dir": state_dir,
                "blockers": blockers,
                "active_command_run_count": len(command_state["active_command_runs"]),
                "stale_command_run_count": len(command_state["stale_command_runs"]),
                "active_path_conflict_count": len(active_path_conflicts),
                "active_command_run_conflict_count": len(active_command_run_path_conflicts),
                "authority_boundary": "standalone_clone_local_command_singleflight_not_private_work_ledger_or_scheduler",
            }

        git = _git_status(root, normalized_paths, state_dir=state_dir)
        run_id = f"run_{hashlib.sha256(f'{session_id}:{normalized_key}:{generated_at}:{normalized_paths}'.encode()).hexdigest()[:16]}"
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "command_start",
                "event_id": f"event_{hashlib.sha256(f'command-start:{run_id}'.encode()).hexdigest()[:16]}",
                "run_id": run_id,
                "session_id": session_id,
                "command_key": normalized_key,
                "command": command,
                "owner_paths": normalized_paths,
                "started_at": generated_at,
                "lease_expires_at": lease_expires_at,
                "expected_parent": git.get("head"),
                "authority_boundary": "command_run_start_is_clone_local_singleflight_evidence_only",
            },
        )
        refreshed = _command_run_state(root, state_dir=state_dir, at=generated_at)
    return {
        "kind": "microcosm_concurrency_command_start",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "command_key": normalized_key,
        "command": command,
        "owner_paths": normalized_paths,
        "state_dir": state_dir,
        "run_id": run_id,
        "lease_expires_at": lease_expires_at,
        "expected_parent": git.get("head"),
        "active_command_run_count": len(refreshed["active_command_runs"]),
        "stale_command_run_count": len(refreshed["stale_command_runs"]),
        "git": git,
        "authority_boundary": "standalone_clone_local_command_singleflight_not_private_work_ledger_or_scheduler",
    }


def finish_command(
    root: Path,
    *,
    session_id: str,
    run_id: str | None = None,
    command_key: str | None = None,
    status: str = "ok",
    exit_code: int | None = None,
    receipt_ref: str | None = None,
    validation_refs: list[str] | None = None,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    """Finish an active command run and bind receipt evidence for reuse."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    validation_refs = validation_refs or []
    normalized_key = command_key.strip() if command_key else None
    normalized_run_id = run_id.strip() if run_id else None

    with _locked_events(root, state_dir):
        command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
        matches = [
            run
            for run in command_state["active_command_runs"]
            if run.get("session_id") == session_id
            and (not normalized_run_id or run.get("run_id") == normalized_run_id)
            and (not normalized_key or run.get("command_key") == normalized_key)
        ]
        blockers: list[dict[str, Any]] = []
        if not normalized_run_id and not normalized_key:
            blockers.append({"blocker": "missing_command_identity"})
        if not matches:
            blockers.append(
                {
                    "blocker": "missing_active_command_run",
                    "run_id": normalized_run_id,
                    "command_key": normalized_key,
                    "why": "concurrency-command-finish only closes active same-session command runs.",
                }
            )
        if len(matches) > 1 and not normalized_run_id:
            blockers.append(
                {
                    "blocker": "ambiguous_active_command_run",
                    "command_key": normalized_key,
                    "run_ids": [run.get("run_id") for run in matches],
                }
            )
        if blockers:
            return {
                "kind": "microcosm_concurrency_command_finish",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "run_id": normalized_run_id,
                "command_key": normalized_key,
                "blockers": blockers,
                "active_command_run_count": len(command_state["active_command_runs"]),
                "stale_command_run_count": len(command_state["stale_command_runs"]),
                "authority_boundary": "standalone_clone_local_command_singleflight_not_private_work_ledger_or_scheduler",
            }

        run = matches[0]
        finished_run_id = str(run.get("run_id"))
        finished_key = str(run.get("command_key"))
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "command_finish",
                "event_id": f"event_{hashlib.sha256(f'command-finish:{finished_run_id}:{generated_at}'.encode()).hexdigest()[:16]}",
                "run_id": finished_run_id,
                "session_id": session_id,
                "command_key": finished_key,
                "finished_at": generated_at,
                "status": status,
                "exit_code": exit_code,
                "receipt_ref": receipt_ref,
                "validation_refs": validation_refs,
                "authority_boundary": "command_run_finish_is_clone_local_receipt_evidence_only",
            },
        )
        refreshed = _command_run_state(root, state_dir=state_dir, at=generated_at)
    return {
        "kind": "microcosm_concurrency_command_finish",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "run_id": finished_run_id,
        "command_key": finished_key,
        "finalized_status": status,
        "exit_code": exit_code,
        "receipt_ref": receipt_ref,
        "validation_refs": validation_refs,
        "active_command_run_count": len(refreshed["active_command_runs"]),
        "stale_command_run_count": len(refreshed["stale_command_runs"]),
        "completed_command_run_count": len(refreshed["completed_command_runs"]),
        "authority_boundary": "standalone_clone_local_command_singleflight_not_private_work_ledger_or_scheduler",
    }


def git_landing_plan(
    root: Path,
    *,
    owner_paths: list[str],
    session_id: str | None = None,
    commit_message: str = "<message>",
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    """Return a read-only scoped git landing plan for clone-local agents."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths)
    git = _git_status(root, normalized_paths, state_dir=state_dir)
    command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
    active_command_run_conflicts = _active_command_run_path_conflicts(
        command_state["active_command_runs"],
        normalized_paths,
    ) if normalized_paths else []
    blockers: list[dict[str, Any]] = []
    if not normalized_paths:
        blockers.append({"blocker": "missing_owner_paths"})
    if not git.get("available"):
        blockers.append({"blocker": "git_unavailable", "git_status": git.get("status")})
    if git.get("external_staged_path_count", 0):
        blockers.append(
            {
                "blocker": "external_staged_paths_present",
                "paths_preview": git.get("external_staged_paths_preview", []),
                "why": "Plain git commit would include another agent's staged paths.",
            }
        )
    if active_command_run_conflicts:
        blockers.append(
            {
                "blocker": "active_command_run_conflict",
                "conflicts": active_command_run_conflicts,
                "why": "Finish or wait for active command runs on owned paths before planning a commit.",
            }
        )

    status = "blocked" if blockers else "ok"
    preflight_parts = [
        "PYTHONPATH=src",
        "python3",
        "-m",
        "idea_microcosm.cli",
        "concurrency-preflight",
        "--root",
        ".",
    ]
    if session_id:
        preflight_parts.extend(["--session-id", session_id])
    else:
        preflight_parts.extend(["--session-id", "<session-id>"])
    for path in normalized_paths:
        preflight_parts.extend(["--path", path])
    preflight_parts.append("--claim")
    preflight_command = " ".join(_quote_arg(part) for part in preflight_parts)
    add_command = "git add -- " + _quote_paths(normalized_paths) if normalized_paths else "git add -- <owned-paths>"
    finalize_session_id = session_id or "<session-id>"
    finalize_command = (
        "PYTHONPATH=src python3 -m idea_microcosm.cli concurrency-finalize "
        f"--root . --session-id {_quote_arg(finalize_session_id)} "
        "--commit-ref \"$(git rev-parse HEAD)\""
    )
    plan_steps = [
        {
            "step_id": "inspect_shared_index",
            "command": "git diff --cached --name-only",
            "why": "Confirm no outside-path staged changes are present before any commit.",
        },
        {
            "step_id": "claim_paths",
            "command": preflight_command,
            "why": "Bind clone-local path and command claims before mutation or landing.",
        },
        {
            "step_id": "stage_owned_paths_only",
            "command": add_command,
            "why": "Stage only declared owner paths; never use broad add in a dirty shared clone.",
        },
        {
            "step_id": "verify_scoped_index",
            "command": "git diff --cached --name-only",
            "why": "The output should contain only the paths owned by this session.",
        },
        {
            "step_id": "commit_scoped_index",
            "command": "git commit -m " + _quote_arg(commit_message),
            "why": "Commit only after the shared index is scoped and HEAD still matches expected_parent.",
        },
        {
            "step_id": "finalize_clone_local_claim",
            "command": finalize_command,
            "why": "Release claims with commit evidence after validation and commit.",
        },
    ]
    return {
        "kind": "microcosm_concurrency_git_plan",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": status,
        "session_id": session_id,
        "state_dir": state_dir,
        "owner_paths": normalized_paths,
        "expected_parent": git.get("head"),
        "head_cas_rule": "Before commit, rerun git rev-parse HEAD; if it differs from expected_parent, rerun concurrency-git-plan.",
        "blockers": blockers,
        "active_command_run_conflicts": active_command_run_conflicts,
        "active_command_run_count": len(command_state["active_command_runs"]),
        "git": git,
        "unsafe_commands": git.get("unsafe_commands", []),
        "plan_steps": plan_steps if status == "ok" else plan_steps[:1],
        "authority_boundary": "standalone_clone_local_git_plan_not_private_scoped_commit_runtime_or_publication_evidence",
    }


def scoped_commit(
    root: Path,
    *,
    session_id: str,
    owner_paths: list[str],
    message: str,
    expected_parent: str | None = None,
    validation_refs: list[str] | None = None,
    receipt_ref: str | None = None,
    residual_refs: list[str] | None = None,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
    require_claim: bool = True,
) -> dict[str, Any]:
    """Stage, commit, and finalize only declared owner paths under the local guard."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths)
    validation_refs = validation_refs or []
    residual_refs = residual_refs or []
    commit_message = message.strip()

    def active_path_conflicts(active_claims: list[dict[str, Any]]) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        for active in active_claims:
            if active.get("session_id") == session_id:
                continue
            for requested in normalized_paths:
                for active_path in active.get("owner_paths", []):
                    if _paths_overlap(requested, str(active_path)):
                        conflicts.append(
                            {
                                "requested_path": requested,
                                "active_path": active_path,
                                "active_session_id": active.get("session_id"),
                                "claim_id": active.get("claim_id"),
                                "lease_expires_at": active.get("lease_expires_at"),
                            }
                        )
        return conflicts

    def missing_claim_paths(active_claims: list[dict[str, Any]]) -> list[str]:
        session_claims = [claim for claim in active_claims if claim.get("session_id") == session_id]
        missing: list[str] = []
        for requested in normalized_paths:
            covered = any(
                _path_is_within(requested, str(active_path))
                for claim in session_claims
                for active_path in claim.get("owner_paths", [])
            )
            if not covered:
                missing.append(requested)
        return missing

    with _locked_events(root, state_dir, wait_seconds=5.0):
        state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
        active_claims = state["active_claims"]
        blockers: list[dict[str, Any]] = []
        conflicts = active_path_conflicts(active_claims)
        if conflicts:
            blockers.append({"blocker": "active_path_conflict", "conflicts": conflicts})
        command_run_conflicts = _active_command_run_path_conflicts(
            command_state["active_command_runs"],
            normalized_paths,
        ) if normalized_paths else []
        if command_run_conflicts:
            blockers.append(
                {
                    "blocker": "active_command_run_conflict",
                    "conflicts": command_run_conflicts,
                    "why": "Finish or wait for active validation/build command runs on owned paths before committing.",
                }
            )
        if require_claim:
            missing = missing_claim_paths(active_claims)
            if missing:
                blockers.append(
                    {
                        "blocker": "missing_active_claim",
                        "paths": missing,
                        "why": "concurrency-scoped-commit requires this session to claim every owner path first.",
                    }
                )
        if not normalized_paths:
            blockers.append({"blocker": "missing_owner_paths"})
        if not commit_message:
            blockers.append({"blocker": "missing_commit_message"})

        git_before = _git_status(root, normalized_paths, state_dir=state_dir)
        if not git_before.get("available"):
            blockers.append({"blocker": "git_unavailable", "git_status": git_before.get("status")})
        if expected_parent and git_before.get("head") != expected_parent:
            blockers.append(
                {
                    "blocker": "head_changed",
                    "expected_parent": expected_parent,
                    "actual_head": git_before.get("head"),
                }
            )
        if git_before.get("external_staged_path_count", 0):
            blockers.append(
                {
                    "blocker": "external_staged_paths_present",
                    "paths_preview": git_before.get("external_staged_paths_preview", []),
                    "why": "Refusing to commit while another agent's paths are already staged.",
                }
            )
        if (
            git_before.get("available")
            and not git_before.get("owner_dirty_path_count", 0)
            and not git_before.get("owner_staged_path_count", 0)
        ):
            blockers.append({"blocker": "no_owned_changes_to_commit"})
        if blockers:
            return {
                "kind": "microcosm_concurrency_scoped_commit",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "state_dir": state_dir,
                "owner_paths": normalized_paths,
                "expected_parent": expected_parent,
                "blockers": blockers,
                "git_before": git_before,
                "active_command_run_conflicts": command_run_conflicts,
                "authority_boundary": "standalone_clone_local_scoped_commit_not_private_work_ledger_or_publication_evidence",
            }

        git_add = _run_git(root, ["add", "--", *normalized_paths])
        if git_add.returncode != 0:
            return {
                "kind": "microcosm_concurrency_scoped_commit",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "state_dir": state_dir,
                "owner_paths": normalized_paths,
                "expected_parent": expected_parent,
                "blockers": [
                    {
                        "blocker": "git_add_failed",
                        "stderr": git_add.stderr.strip()[:1000],
                    }
                ],
                "git_before": git_before,
                "authority_boundary": "standalone_clone_local_scoped_commit_not_private_work_ledger_or_publication_evidence",
            }

        git_after_add = _git_status(root, normalized_paths, state_dir=state_dir)
        after_add_blockers: list[dict[str, Any]] = []
        if expected_parent and git_after_add.get("head") != expected_parent:
            after_add_blockers.append(
                {
                    "blocker": "head_changed_after_add",
                    "expected_parent": expected_parent,
                    "actual_head": git_after_add.get("head"),
                }
            )
        if git_after_add.get("external_staged_path_count", 0):
            after_add_blockers.append(
                {
                    "blocker": "external_staged_paths_present_after_add",
                    "paths_preview": git_after_add.get("external_staged_paths_preview", []),
                    "why": "The shared index is no longer scoped to this session after staging.",
                }
            )
        if not git_after_add.get("owner_staged_path_count", 0):
            after_add_blockers.append({"blocker": "no_owned_staged_paths"})
        if after_add_blockers:
            return {
                "kind": "microcosm_concurrency_scoped_commit",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "state_dir": state_dir,
                "owner_paths": normalized_paths,
                "expected_parent": expected_parent,
                "blockers": after_add_blockers,
                "git_before": git_before,
                "git_after_add": git_after_add,
                "authority_boundary": "standalone_clone_local_scoped_commit_not_private_work_ledger_or_publication_evidence",
            }

        commit = _run_git(root, ["commit", "-m", commit_message])
        if commit.returncode != 0:
            return {
                "kind": "microcosm_concurrency_scoped_commit",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "state_dir": state_dir,
                "owner_paths": normalized_paths,
                "expected_parent": expected_parent,
                "blockers": [
                    {
                        "blocker": "git_commit_failed",
                        "stderr": commit.stderr.strip()[:1000],
                        "stdout": commit.stdout.strip()[:1000],
                    }
                ],
                "git_before": git_before,
                "git_after_add": git_after_add,
                "authority_boundary": "standalone_clone_local_scoped_commit_not_private_work_ledger_or_publication_evidence",
            }

        head = _run_git(root, ["rev-parse", "HEAD"])
        commit_ref = head.stdout.strip() if head.returncode == 0 else None
        before_finalize = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "finalize",
                "event_id": f"event_{hashlib.sha256(f'scoped-commit:{session_id}:{generated_at}'.encode()).hexdigest()[:16]}",
                "session_id": session_id,
                "finalized_at": generated_at,
                "status": "ok",
                "receipt_ref": receipt_ref,
                "commit_ref": commit_ref,
                "validation_refs": validation_refs,
                "residual_refs": residual_refs,
                "owner_paths": normalized_paths,
                "authority_boundary": "scoped_commit_finalizer_is_clone_local_coordination_evidence_only",
            },
        )
        after_finalize = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _write_active_snapshot(root, state_dir, generated_at, after_finalize)
        git_after_commit = _git_status(root, normalized_paths, state_dir=state_dir)

    return {
        "kind": "microcosm_concurrency_scoped_commit",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "state_dir": state_dir,
        "owner_paths": normalized_paths,
        "expected_parent": expected_parent,
        "previous_head": git_before.get("head"),
        "commit_ref": commit_ref,
        "commit_message": commit_message,
        "receipt_ref": receipt_ref,
        "validation_refs": validation_refs,
        "residual_refs": residual_refs,
        "released_claim_count": max(
            0,
            len(before_finalize["active_claims"]) - len(after_finalize["active_claims"]),
        ),
        "active_claim_count": len(after_finalize["active_claims"]),
        "git_before": git_before,
        "git_after_add": git_after_add,
        "git_after_commit": git_after_commit,
        "authority_boundary": "standalone_clone_local_scoped_commit_not_private_work_ledger_or_publication_evidence",
    }


def preflight(
    root: Path,
    *,
    session_id: str,
    owner_paths: list[str],
    command_key: str | None = None,
    parent_scope_id: str | None = None,
    claim_policy: str | None = None,
    finalizer_policy: str | None = None,
    residue_budget: str | None = None,
    lease_minutes: int = 60,
    claim: bool = False,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths)

    def evaluate_and_maybe_claim() -> dict[str, Any]:
        state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        command_state = _command_run_state(root, state_dir=state_dir, at=generated_at)
        active_claims = state["active_claims"]
        path_conflicts = _active_claim_path_conflicts(active_claims, normalized_paths, session_id=session_id)
        command_run_path_conflicts = _active_command_run_path_conflicts(
            command_state["active_command_runs"],
            normalized_paths,
            session_id=session_id,
        )

        command_claim_conflicts = [
            {
                "active_session_id": active.get("session_id"),
                "claim_id": active.get("claim_id"),
                "lease_expires_at": active.get("lease_expires_at"),
                "source": "claim",
            }
            for active in active_claims
            if command_key and active.get("command_key") == command_key and active.get("session_id") != session_id
        ]
        command_run_key_conflicts = [
            {
                "active_session_id": run.get("session_id"),
                "run_id": run.get("run_id"),
                "lease_expires_at": run.get("lease_expires_at"),
                "source": "command_run",
            }
            for run in command_state["active_command_runs"]
            if command_key and run.get("command_key") == command_key and run.get("session_id") != session_id
        ]
        command_conflicts = command_claim_conflicts + command_run_key_conflicts
        parent_missing = []
        if parent_scope_id:
            for field_name, value in (
                ("claim_policy", claim_policy),
                ("finalizer_policy", finalizer_policy),
                ("residue_budget", residue_budget),
            ):
                if not value:
                    parent_missing.append(field_name)

        blockers: list[dict[str, Any]] = []
        if path_conflicts:
            blockers.append({"blocker": "active_path_conflict", "conflicts": path_conflicts})
        if command_run_path_conflicts:
            blockers.append(
                {
                    "blocker": "active_command_run_conflict",
                    "conflicts": command_run_path_conflicts,
                    "why": "An active command run already covers a requested owner path.",
                }
            )
        if command_conflicts:
            blockers.append({"blocker": "active_command_key_singleflight", "conflicts": command_conflicts})
        if parent_missing:
            blockers.append(
                {
                    "blocker": "supervised_scope_missing_contract",
                    "parent_scope_id": parent_scope_id,
                    "missing": parent_missing,
                }
            )

        status = "blocked" if blockers else "ok"
        claim_ref = None
        if claim and not blockers:
            lease_expires_at = (
                _parse_utc(generated_at) + timedelta(minutes=max(1, lease_minutes))
            ).isoformat().replace("+00:00", "Z")
            claim_ref = f"claim_{hashlib.sha256(f'{session_id}:{generated_at}:{normalized_paths}'.encode()).hexdigest()[:16]}"
            _append_event(
                root,
                state_dir,
                {
                    "kind": "microcosm_concurrency_event",
                    "schema_version": SCHEMA_VERSION,
                    "event_type": "claim",
                    "event_id": f"event_{hashlib.sha256(f'claim:{claim_ref}'.encode()).hexdigest()[:16]}",
                    "claim_id": claim_ref,
                    "session_id": session_id,
                    "owner_paths": normalized_paths,
                    "command_key": command_key,
                    "parent_scope_id": parent_scope_id,
                    "claim_policy": claim_policy,
                    "finalizer_policy": finalizer_policy,
                    "residue_budget": residue_budget,
                    "claimed_at": generated_at,
                    "lease_expires_at": lease_expires_at,
                    "authority_boundary": "clone_local_coordination_not_private_work_ledger_or_scheduler",
                },
            )

        refreshed_state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _write_active_snapshot(root, state_dir, generated_at, refreshed_state)
        return {
            "kind": "microcosm_concurrency_preflight",
            "schema_version": SCHEMA_VERSION,
            "generated_at": generated_at,
            "status": status,
            "session_id": session_id,
            "claim_written": claim_ref is not None,
            "claim_id": claim_ref,
            "state_dir": state_dir,
            "owner_paths": normalized_paths,
            "command_key": command_key,
            "parent_scope_id": parent_scope_id,
            "blockers": blockers,
            "stale_claim_count": len(refreshed_state["stale_claims"]),
            "active_claim_count": len(refreshed_state["active_claims"]),
            "active_command_run_conflict_count": len(command_run_path_conflicts),
            "git": _git_status(root, normalized_paths, state_dir=state_dir),
            "authority_boundary": "standalone_clone_local_preflight_not_private_runtime_or_publication_evidence",
            "next": [
                "If status is ok, mutate only owner_paths and use the scoped git lane shown in git.safe_commands.",
                "If blocked by command_key, attach to or wait for the active session instead of spawning a duplicate slow command.",
                "Finalize with concurrency-finalize after validation and commit evidence exist.",
            ],
        }

    with _locked_events(root, state_dir):
        return evaluate_and_maybe_claim()


def renew_session(
    root: Path,
    *,
    session_id: str,
    owner_paths: list[str] | None = None,
    command_key: str | None = None,
    lease_minutes: int = 60,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
) -> dict[str, Any]:
    """Extend active claims for a live clone-local session without duplicating claims."""
    root = root.resolve()
    generated_at = at or utc_now_iso()
    normalized_paths = _normalize_paths(root, owner_paths or []) if owner_paths else []
    lease_expires_at = (
        _parse_utc(generated_at) + timedelta(minutes=max(1, lease_minutes))
    ).isoformat().replace("+00:00", "Z")

    with _locked_events(root, state_dir):
        state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        session_claims = [
            claim
            for claim in state["active_claims"]
            if claim.get("session_id") == session_id and (not command_key or claim.get("command_key") == command_key)
        ]
        selected_claim_ids: set[str] = set()
        missing_paths: list[str] = []
        if normalized_paths:
            for requested in normalized_paths:
                covering_claim_ids = [
                    str(claim.get("claim_id") or claim.get("event_id") or "")
                    for claim in session_claims
                    if any(_path_is_within(requested, str(active_path)) for active_path in claim.get("owner_paths", []))
                ]
                covering_claim_ids = [claim_id for claim_id in covering_claim_ids if claim_id]
                if covering_claim_ids:
                    selected_claim_ids.update(covering_claim_ids)
                else:
                    missing_paths.append(requested)
        else:
            selected_claim_ids = {
                str(claim.get("claim_id") or claim.get("event_id") or "")
                for claim in session_claims
                if claim.get("claim_id") or claim.get("event_id")
            }

        blockers: list[dict[str, Any]] = []
        if missing_paths or not selected_claim_ids:
            blockers.append(
                {
                    "blocker": "missing_active_claim",
                    "paths": missing_paths,
                    "command_key": command_key,
                    "why": "concurrency-renew only extends active same-session claims; expired or never-claimed paths must run preflight again.",
                }
            )
        if blockers:
            return {
                "kind": "microcosm_concurrency_renew",
                "schema_version": SCHEMA_VERSION,
                "generated_at": generated_at,
                "status": "blocked",
                "session_id": session_id,
                "state_dir": state_dir,
                "owner_paths": normalized_paths,
                "command_key": command_key,
                "lease_expires_at": lease_expires_at,
                "blockers": blockers,
                "active_claim_count": len(state["active_claims"]),
                "stale_claim_count": len(state["stale_claims"]),
                "authority_boundary": "standalone_clone_local_renewal_not_private_work_ledger_or_scheduler",
            }

        claim_ids = sorted(selected_claim_ids)
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "renew",
                "event_id": f"event_{hashlib.sha256(f'renew:{session_id}:{generated_at}:{claim_ids}'.encode()).hexdigest()[:16]}",
                "session_id": session_id,
                "claim_ids": claim_ids,
                "owner_paths": normalized_paths,
                "command_key": command_key,
                "renewed_at": generated_at,
                "lease_expires_at": lease_expires_at,
                "authority_boundary": "claim_renewal_is_clone_local_coordination_evidence_only",
            },
        )
        refreshed_state = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _write_active_snapshot(root, state_dir, generated_at, refreshed_state)
        renewed_claims = [
            claim for claim in refreshed_state["active_claims"] if str(claim.get("claim_id") or "") in selected_claim_ids
        ]
    return {
        "kind": "microcosm_concurrency_renew",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "state_dir": state_dir,
        "owner_paths": normalized_paths,
        "command_key": command_key,
        "claim_ids": claim_ids,
        "lease_expires_at": lease_expires_at,
        "renewed_claim_count": len(renewed_claims),
        "active_claim_count": len(refreshed_state["active_claims"]),
        "stale_claim_count": len(refreshed_state["stale_claims"]),
        "authority_boundary": "standalone_clone_local_renewal_not_private_work_ledger_or_scheduler",
    }


def release_session(
    root: Path,
    *,
    session_id: str,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
    reason: str = "manual_release",
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or utc_now_iso()
    with _locked_events(root, state_dir):
        before = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "release",
                "event_id": f"event_{hashlib.sha256(f'release:{session_id}:{generated_at}'.encode()).hexdigest()[:16]}",
                "session_id": session_id,
                "released_at": generated_at,
                "reason": reason,
            },
        )
        after = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _write_active_snapshot(root, state_dir, generated_at, after)
    return {
        "kind": "microcosm_concurrency_release",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "released_claim_count": max(0, len(before["active_claims"]) - len(after["active_claims"])),
        "active_claim_count": len(after["active_claims"]),
    }


def finalize_session(
    root: Path,
    *,
    session_id: str,
    receipt_ref: str | None = None,
    commit_ref: str | None = None,
    validation_refs: list[str] | None = None,
    residual_refs: list[str] | None = None,
    state_dir: str = DEFAULT_STATE_DIR,
    at: str | None = None,
    status: str = "ok",
) -> dict[str, Any]:
    root = root.resolve()
    generated_at = at or utc_now_iso()
    validation_refs = validation_refs or []
    residual_refs = residual_refs or []
    with _locked_events(root, state_dir):
        before = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _append_event(
            root,
            state_dir,
            {
                "kind": "microcosm_concurrency_event",
                "schema_version": SCHEMA_VERSION,
                "event_type": "finalize",
                "event_id": f"event_{hashlib.sha256(f'finalize:{session_id}:{generated_at}'.encode()).hexdigest()[:16]}",
                "session_id": session_id,
                "finalized_at": generated_at,
                "status": status,
                "receipt_ref": receipt_ref,
                "commit_ref": commit_ref,
                "validation_refs": validation_refs,
                "residual_refs": residual_refs,
                "authority_boundary": "finalizer_receipt_is_clone_local_coordination_evidence_only",
            },
        )
        after = _active_claim_state(root, state_dir=state_dir, at=generated_at)
        _write_active_snapshot(root, state_dir, generated_at, after)
    return {
        "kind": "microcosm_concurrency_finalize",
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "status": "ok",
        "session_id": session_id,
        "finalized_status": status,
        "receipt_ref": receipt_ref,
        "commit_ref": commit_ref,
        "validation_refs": validation_refs,
        "residual_refs": residual_refs,
        "released_claim_count": max(0, len(before["active_claims"]) - len(after["active_claims"])),
        "active_claim_count": len(after["active_claims"]),
    }
