"""
Raw-seed intake tracker for the always-on metabolism runtime.

[PURPOSE]
- Teleology: Track family-root raw-seed drafting sessions durably so the
  always-on runtime can auto-sync only after a robust settle window instead of
  on every save.
- Mechanism: Discover authoritative family-root `raw_seed.md` files from
  `phase_family.json`, normalize away sync-marker churn, classify saves into
  entry sessions, and project live tracker state to JSON + JSONL surfaces.

[INTERFACE]
- Exports: FamilyRawSeedRoot, RawSeedWatcher, RawSeedIntakeCoordinator, family discovery and text normalization/statistics helpers.
- Reads: Family phase_family.json and authoritative family raw_seed.md files.
- Writes: Intake session rows in metabolism SQLite, tracker JSON and append-only timeline JSONL.

[FLOW]
- Mechanism: Strip generated sync markup, compare content hashes, open/reopen drafting sessions and settle them after the quiet window; project tracker state and mark completed syncs.

[DEPENDENCIES]
- Couples: metabolism_store owns durable intake session schema/settings and projection paths.

[CONSTRAINTS]
- Guarantee: Tracker observes operator raw seed without rewriting its content.
- Atomicity: Tracker JSON uses temporary-file replacement; SQLite and JSONL/projection updates are separate operations.
- Orders: Family discovery sorts marker paths; settle decisions depend on supplied/runtime time.
"""
from __future__ import annotations

import hashlib
import json
import threading
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from queue import Empty, Queue
from typing import Any, Iterable, Mapping, Sequence

from system.lib import metabolism_store as store

try:  # pragma: no cover - import availability is exercised via behavior tests.
    from watchfiles import watch as _watchfiles_watch
except Exception:  # pragma: no cover
    _watchfiles_watch = None


TRACKER_SCHEMA = "raw_seed_entry_tracker_v1"
TIMELINE_SCHEMA = "raw_seed_entry_timeline_v1"
WATCHER_MODE_DISABLED = "disabled"
WATCHER_MODE_WATCHFILES = "watchfiles"
WATCHER_MODE_SCAN_FALLBACK = "scan_fallback"
ACTIVE_ENTRY_STATES = frozenset({"drafting", "settling", "reopened"})
_GENERATED_MARKER_PREFIXES = ("<!-- RAW_SEED_", "<!-- AGENT_SEED_")


@dataclass(frozen=True)
class FamilyRawSeedRoot:
    family_number: str
    family_dir: str
    raw_seed_path: str
    phase_family_path: str


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _atomic_write(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f"{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False, sort_keys=True) + "\n")


def discover_family_raw_seed_roots(repo_root: Path) -> dict[str, FamilyRawSeedRoot]:
    roots: dict[str, FamilyRawSeedRoot] = {}
    obsidian_root = repo_root / "obsidian"
    if not obsidian_root.exists():
        return roots
    for phase_family_path in sorted(obsidian_root.rglob("phase_family.json")):
        try:
            payload = json.loads(phase_family_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        family_number = str(payload.get("family_number") or payload.get("family_id") or "").strip()
        family_dir = str(payload.get("family_dir") or "").strip()
        raw_seed_path = str(payload.get("raw_seed_path") or "").strip()
        if not family_number or not family_dir:
            continue
        if not raw_seed_path:
            raw_seed_path = f"{family_dir.rstrip('/')}/raw_seed.md"
        roots[raw_seed_path] = FamilyRawSeedRoot(
            family_number=family_number,
            family_dir=family_dir,
            raw_seed_path=raw_seed_path,
            phase_family_path=str(phase_family_path.relative_to(repo_root).as_posix()),
        )
    return roots


def strip_generated_raw_seed_markup(text: str) -> str:
    normalized = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    kept: list[str] = []
    for line in normalized.split("\n"):
        stripped = line.strip()
        if stripped.startswith(_GENERATED_MARKER_PREFIXES) and stripped.endswith("-->"):
            continue
        kept.append(line)
    return "\n".join(kept)


def _body_lines_outside_frontmatter(text: str) -> list[str]:
    lines = str(text or "").split("\n")
    if lines and lines[0].strip() == "---":
        for index in range(1, len(lines)):
            if lines[index].strip() == "---":
                return lines[index + 1 :]
    return lines


def _normalize_semantic_line(line: str) -> str:
    token = str(line or "").strip()
    if not token:
        return ""
    return " ".join(token.split())


def _sha1(text: str) -> str:
    return hashlib.sha1(str(text or "").encode("utf-8")).hexdigest()


def build_raw_seed_text_stats(text: str) -> dict[str, Any]:
    raw_text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    markerless_text = strip_generated_raw_seed_markup(raw_text)
    semantic_lines = [_normalize_semantic_line(line) for line in markerless_text.split("\n")]
    semantic_text = "\n".join(semantic_lines).strip("\n")
    body_lines = [_normalize_semantic_line(line) for line in _body_lines_outside_frontmatter(markerless_text)]
    trailing_blank_lines = 0
    for line in reversed(body_lines):
        if line:
            break
        trailing_blank_lines += 1
    nonempty_body = [line for line in body_lines if line]
    semantic_length = len(semantic_text)
    stats = {
        "raw_length": len(raw_text),
        "semantic_length": semantic_length,
        "line_count": len(raw_text.split("\n")),
        "body_nonempty_count": len(nonempty_body),
        "trailing_blank_lines": trailing_blank_lines,
        "explicit_boundary_count": sum(1 for line in body_lines if line == "---"),
        "tail_explicit_boundary": bool(nonempty_body and nonempty_body[-1] == "---"),
        "first_nonempty_line": nonempty_body[0] if nonempty_body else "",
        "last_nonempty_line": nonempty_body[-1] if nonempty_body else "",
        "tail_signature": _sha1("\n".join(nonempty_body[-8:])),
        "prefix_128_digest": _sha1(semantic_text[:128]),
        "prefix_512_digest": _sha1(semantic_text[:512]),
        "prefix_2048_digest": _sha1(semantic_text[:2048]),
        "suffix_128_digest": _sha1(semantic_text[-128:]),
        "suffix_512_digest": _sha1(semantic_text[-512:]),
        "suffix_2048_digest": _sha1(semantic_text[-2048:]),
        "semantic_digest": _sha1(semantic_text),
    }
    return stats


def _prefix_stable(previous: Mapping[str, Any], current: Mapping[str, Any]) -> bool:
    previous_length = int(previous.get("semantic_length") or 0)
    current_length = int(current.get("semantic_length") or 0)
    compared = 0
    for width in (128, 512, 2048):
        if min(previous_length, current_length) < width:
            continue
        compared += 1
        if previous.get(f"prefix_{width}_digest") != current.get(f"prefix_{width}_digest"):
            return False
    if compared:
        return True
    previous_first = str(previous.get("first_nonempty_line") or "").strip()
    current_first = str(current.get("first_nonempty_line") or "").strip()
    if previous_first and current_first:
        return previous_first == current_first
    return True


def _detect_boundary(previous: Mapping[str, Any] | None, current: Mapping[str, Any]) -> str | None:
    earlier = dict(previous or {})
    if int(current.get("explicit_boundary_count") or 0) > int(earlier.get("explicit_boundary_count") or 0):
        return "explicit_delimiter"
    current_blank_run = int(current.get("trailing_blank_lines") or 0)
    if (
        current_blank_run >= 2
        and current_blank_run > int(earlier.get("trailing_blank_lines") or 0)
        and int(current.get("body_nonempty_count") or 0) > 0
    ):
        return "tail_blank_run"
    return None


def _event_digest(payload: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(payload), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _session_public(session: Mapping[str, Any], *, due_at: str | None = None) -> dict[str, Any]:
    item = dict(session)
    stats = dict(item.get("stats") or {})
    return {
        "entry_id": item.get("entry_id"),
        "family_number": item.get("family_number"),
        "family_dir": item.get("family_dir"),
        "raw_seed_path": item.get("raw_seed_path"),
        "state": item.get("state"),
        "classification": item.get("classification"),
        "boundary_kind": item.get("boundary_kind"),
        "opened_at": item.get("opened_at"),
        "updated_at": item.get("updated_at"),
        "settled_at": item.get("settled_at"),
        "synced_at": item.get("synced_at"),
        "reopened_count": item.get("reopened_count"),
        "save_count": item.get("save_count"),
        "raw_digest": item.get("raw_digest"),
        "semantic_digest": item.get("semantic_digest"),
        "stats": {
            "semantic_length": stats.get("semantic_length"),
            "line_count": stats.get("line_count"),
            "trailing_blank_lines": stats.get("trailing_blank_lines"),
            "explicit_boundary_count": stats.get("explicit_boundary_count"),
            "last_observation_source": stats.get("last_observation_source"),
            "settle_window_seconds": stats.get("settle_window_seconds"),
            "forced_catchup_seconds": stats.get("forced_catchup_seconds"),
            "dirty_started_at": stats.get("dirty_started_at"),
        },
        "due_at": due_at,
    }


class RawSeedWatcher:
    def __init__(self, repo_root: Path, *, enabled: bool) -> None:
        self.repo_root = repo_root
        self.enabled = enabled
        self.mode = WATCHER_MODE_DISABLED if not enabled else (
            WATCHER_MODE_WATCHFILES if _watchfiles_watch is not None else WATCHER_MODE_SCAN_FALLBACK
        )
        self.error: str | None = None
        self._watched_dirs: tuple[str, ...] = ()
        self._target_paths: set[str] = set()
        self._queue: Queue[str] = Queue()
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    @property
    def watched_dirs(self) -> tuple[str, ...]:
        return self._watched_dirs

    def configure(self, roots: Mapping[str, FamilyRawSeedRoot]) -> None:
        if not self.enabled:
            self.mode = WATCHER_MODE_DISABLED
            return
        self._target_paths = {path for path in roots}
        if _watchfiles_watch is None:
            self.mode = WATCHER_MODE_SCAN_FALLBACK
            return
        watched_dirs = tuple(
            sorted(
                {
                    str((self.repo_root / root.raw_seed_path).parent)
                    for root in roots.values()
                }
            )
        )
        if watched_dirs == self._watched_dirs and self._thread and self._thread.is_alive():
            return
        self.close()
        self._stop_event = threading.Event()
        self._watched_dirs = watched_dirs
        if not watched_dirs:
            self.mode = WATCHER_MODE_WATCHFILES
            return

        def _run() -> None:
            try:
                for changes in _watchfiles_watch(*watched_dirs, stop_event=self._stop_event):
                    for _change, changed_path in changes:
                        candidate = Path(changed_path)
                        try:
                            rel = candidate.resolve().relative_to(self.repo_root.resolve()).as_posix()
                        except Exception:
                            try:
                                rel = candidate.relative_to(self.repo_root).as_posix()
                            except Exception:
                                continue
                        if rel in self._target_paths:
                            self._queue.put(rel)
            except Exception as exc:  # pragma: no cover - exercised through startup fallback.
                self.mode = WATCHER_MODE_SCAN_FALLBACK
                self.error = f"{type(exc).__name__}: {exc}"

        self._thread = threading.Thread(target=_run, name="raw-seed-watchfiles", daemon=True)
        self._thread.start()
        self.mode = WATCHER_MODE_WATCHFILES

    def drain(self) -> list[str]:
        drained: list[str] = []
        while True:
            try:
                drained.append(self._queue.get_nowait())
            except Empty:
                break
        deduped = list(dict.fromkeys(drained))
        return [path for path in deduped if path in self._target_paths]

    def close(self) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None


class RawSeedIntakeCoordinator:
    def __init__(self, repo_root: Path, conn, *, enable_watchers: bool = False) -> None:
        self.repo_root = repo_root
        self.conn = conn
        self.paths = store.metabolism_paths(repo_root)
        self.family_roots: dict[str, FamilyRawSeedRoot] = {}
        self._watchers_requested = bool(enable_watchers)
        self.watcher = RawSeedWatcher(repo_root, enabled=enable_watchers)
        self.refresh_family_roots()

    def close(self) -> None:
        self.watcher.close()

    def intake_settings(self) -> dict[str, Any]:
        settings = store.get_setting(self.conn, "raw_seed_intake", {}) or {}
        if not isinstance(settings, Mapping):
            settings = {}
        return {
            "enabled": bool(settings.get("enabled", True)),
            "watcher_enabled": bool(settings.get("watcher_enabled", True)),
            "quiet_window_seconds": int(settings.get("quiet_window_seconds") or 300),
            "fast_settle_seconds": int(settings.get("fast_settle_seconds") or 5),
            "reopen_window_seconds": int(settings.get("reopen_window_seconds") or 1800),
            "min_resync_gap_seconds": int(settings.get("min_resync_gap_seconds") or 10),
            "forced_catchup_seconds": int(settings.get("forced_catchup_seconds") or 900),
        }

    def refresh_family_roots(self) -> dict[str, FamilyRawSeedRoot]:
        self.family_roots = discover_family_raw_seed_roots(self.repo_root)
        settings = self.intake_settings()
        self.watcher.enabled = (
            self._watchers_requested
            and bool(settings.get("enabled"))
            and bool(settings.get("watcher_enabled"))
        )
        self.watcher.configure(self.family_roots)
        return self.family_roots

    def family_root_for_path(self, rel_path: str) -> FamilyRawSeedRoot | None:
        return self.family_roots.get(str(rel_path or "").replace("\\", "/"))

    def drain_watch_paths(self) -> list[str]:
        self.refresh_family_roots()
        return self.watcher.drain()

    def _timeline(self, kind: str, session: Mapping[str, Any], **extra: Any) -> None:
        payload = {
            "schema": TIMELINE_SCHEMA,
            "event_kind": kind,
            "recorded_at": _utc_now(),
            **_session_public(session),
            **{key: value for key, value in extra.items() if value is not None},
        }
        _append_jsonl(self.paths.raw_seed_entry_timeline_jsonl, payload)

    def observe_path(
        self,
        rel_path: str,
        *,
        source: str,
        observed_at: str | None = None,
    ) -> dict[str, Any] | None:
        settings = self.intake_settings()
        if not bool(settings.get("enabled")):
            return None
        root = self.family_root_for_path(rel_path)
        if root is None:
            return None
        path = self.repo_root / rel_path
        if not path.exists():
            return None
        stamp = observed_at or _utc_now()
        raw_text = path.read_text(encoding="utf-8", errors="replace")
        stats = build_raw_seed_text_stats(raw_text)
        raw_digest = _sha1(raw_text.replace("\r\n", "\n").replace("\r", "\n"))
        semantic_digest = str(stats.get("semantic_digest") or "")

        recent_sessions = store.list_raw_seed_entry_sessions(self.conn, family_number=root.family_number, limit=12)
        latest_session = recent_sessions[0] if recent_sessions else {}
        active_sessions = [row for row in recent_sessions if row.get("state") in ACTIVE_ENTRY_STATES]
        active_session = active_sessions[0] if active_sessions else {}

        if active_session and semantic_digest == str(active_session.get("semantic_digest") or ""):
            return None
        if not active_session and latest_session and semantic_digest == str(latest_session.get("semantic_digest") or ""):
            return None

        chosen = active_session if active_session and _prefix_stable(active_session.get("stats") or {}, stats) else {}
        reopened = False
        if not chosen and latest_session:
            updated_at = _to_dt(str(latest_session.get("updated_at") or ""))
            if (
                latest_session.get("state") in {"settled", "synced"}
                and updated_at is not None
                and (_to_dt(stamp) or datetime.now(timezone.utc)) - updated_at
                <= timedelta(seconds=int(settings["reopen_window_seconds"]))
                and _prefix_stable(latest_session.get("stats") or {}, stats)
            ):
                chosen = latest_session
                reopened = True

        previous_stats = dict(chosen.get("stats") or latest_session.get("stats") or {})
        boundary_kind = _detect_boundary(previous_stats, stats)
        settle_window_seconds = int(
            settings["fast_settle_seconds"] if boundary_kind else settings["quiet_window_seconds"]
        )
        dirty_started_at = stamp
        if chosen:
            dirty_started_at = str((chosen.get("stats") or {}).get("dirty_started_at") or stamp)
            if reopened:
                dirty_started_at = stamp
            session = store.upsert_raw_seed_entry_session(
                self.conn,
                entry_id=str(chosen["entry_id"]),
                family_number=root.family_number,
                family_dir=root.family_dir,
                raw_seed_path=root.raw_seed_path,
                state="settling" if boundary_kind else ("reopened" if reopened else "drafting"),
                opened_at=str(chosen.get("opened_at") or stamp),
                updated_at=stamp,
                settled_at=None,
                synced_at=None,
                reopened_count=int(chosen.get("reopened_count") or 0) + (1 if reopened else 0),
                save_count=int(chosen.get("save_count") or 0) + 1,
                boundary_kind=boundary_kind,
                classification=str(chosen.get("classification") or "tail_append"),
                raw_digest=raw_digest,
                semantic_digest=semantic_digest,
                stats={
                    **stats,
                    "dirty_started_at": dirty_started_at,
                    "last_observation_source": source,
                    "settle_window_seconds": settle_window_seconds,
                    "forced_catchup_seconds": int(settings["forced_catchup_seconds"]),
                },
            )
            self._timeline("raw_seed_entry_reopened" if reopened else "raw_seed_entry_observed", session)
            return session

        classification = "new_entry"
        if latest_session and not _prefix_stable(latest_session.get("stats") or {}, stats):
            classification = "mid_document_revision"
        session = store.upsert_raw_seed_entry_session(
            self.conn,
            entry_id=f"entry_{uuid.uuid4().hex[:16]}",
            family_number=root.family_number,
            family_dir=root.family_dir,
            raw_seed_path=root.raw_seed_path,
            state="settling" if boundary_kind else "drafting",
            opened_at=stamp,
            updated_at=stamp,
            settled_at=None,
            synced_at=None,
            reopened_count=0,
            save_count=1,
            boundary_kind=boundary_kind,
            classification=classification,
            raw_digest=raw_digest,
            semantic_digest=semantic_digest,
            stats={
                **stats,
                "dirty_started_at": stamp,
                "last_observation_source": source,
                "settle_window_seconds": settle_window_seconds,
                "forced_catchup_seconds": int(settings["forced_catchup_seconds"]),
            },
        )
        self._timeline("raw_seed_entry_opened", session)
        return session

    def _last_family_sync_at(self, family_number: str) -> datetime | None:
        latest = store.latest_raw_seed_entry_session(self.conn, family_number=family_number, states=["synced"])
        return _to_dt(str(latest.get("synced_at") or latest.get("updated_at") or ""))

    def _settle_due_at(self, session: Mapping[str, Any]) -> datetime | None:
        stats = dict(session.get("stats") or {})
        updated_at = _to_dt(str(session.get("updated_at") or ""))
        dirty_started_at = _to_dt(str(stats.get("dirty_started_at") or session.get("opened_at") or ""))
        if updated_at is None or dirty_started_at is None:
            return None
        quiet_window = int(stats.get("settle_window_seconds") or self.intake_settings()["quiet_window_seconds"])
        forced_window = int(stats.get("forced_catchup_seconds") or self.intake_settings()["forced_catchup_seconds"])
        quiet_due = updated_at + timedelta(seconds=quiet_window)
        forced_due = dirty_started_at + timedelta(seconds=forced_window)
        due_at = quiet_due if quiet_due <= forced_due else forced_due
        last_sync = self._last_family_sync_at(str(session.get("family_number") or ""))
        min_gap_seconds = int(self.intake_settings()["min_resync_gap_seconds"])
        if last_sync is not None:
            gap_due = last_sync + timedelta(seconds=min_gap_seconds)
            if gap_due > due_at:
                due_at = gap_due
        return due_at

    def settle_due_sessions(self, *, now: str | None = None) -> list[dict[str, Any]]:
        settings = self.intake_settings()
        if not bool(settings.get("enabled")):
            return []
        stamp = now or _utc_now()
        current_dt = _to_dt(stamp) or datetime.now(timezone.utc)
        emitted: list[dict[str, Any]] = []
        sessions = store.list_raw_seed_entry_sessions(
            self.conn,
            states=sorted(ACTIVE_ENTRY_STATES),
            limit=200,
        )
        for session in sessions:
            due_at = self._settle_due_at(session)
            if due_at is None or due_at > current_dt:
                continue
            updated = store.upsert_raw_seed_entry_session(
                self.conn,
                entry_id=str(session["entry_id"]),
                family_number=str(session["family_number"]),
                family_dir=str(session["family_dir"]),
                raw_seed_path=str(session["raw_seed_path"]),
                state="settled",
                opened_at=str(session.get("opened_at") or stamp),
                updated_at=stamp,
                settled_at=stamp,
                synced_at=None,
                reopened_count=int(session.get("reopened_count") or 0),
                save_count=int(session.get("save_count") or 0),
                boundary_kind=str(session.get("boundary_kind") or "") or None,
                classification=str(session.get("classification") or ""),
                raw_digest=str(session.get("raw_digest") or ""),
                semantic_digest=str(session.get("semantic_digest") or ""),
                stats=dict(session.get("stats") or {}),
            )
            self._timeline("raw_seed_entry_settled", updated)
            emitted.append(
                {
                    "source": "raw_seed_intake",
                    "kind": "raw_seed_entry_settled",
                    "payload": {
                        "family": updated.get("family_number"),
                        "family_dir": updated.get("family_dir"),
                        "raw_seed_path": updated.get("raw_seed_path"),
                        "entry_id": updated.get("entry_id"),
                        "state": updated.get("state"),
                        "classification": updated.get("classification"),
                        "boundary_kind": updated.get("boundary_kind"),
                        "settled_at": updated.get("settled_at"),
                    },
                    "stable_digest": _event_digest(
                        {
                            "kind": "raw_seed_entry_settled",
                            "family": updated.get("family_number"),
                            "entry_id": updated.get("entry_id"),
                            "settled_at": updated.get("settled_at"),
                        }
                    ),
                }
            )
        return emitted

    def mark_family_synced(self, family_number: str, *, synced_at: str | None = None) -> list[dict[str, Any]]:
        stamp = synced_at or _utc_now()
        updated_rows = store.mark_raw_seed_entry_sessions_synced(
            self.conn,
            family_number=family_number,
            synced_at=stamp,
            max_updated_at=stamp,
        )
        for session in updated_rows:
            self._timeline("raw_seed_entry_synced", session)
        return updated_rows

    def pending_settle_timers(self) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        pending: list[dict[str, Any]] = []
        for session in store.list_raw_seed_entry_sessions(self.conn, states=sorted(ACTIVE_ENTRY_STATES), limit=200):
            due_at = self._settle_due_at(session)
            if due_at is None:
                continue
            pending.append(
                {
                    "entry_id": session.get("entry_id"),
                    "family_number": session.get("family_number"),
                    "family_dir": session.get("family_dir"),
                    "state": session.get("state"),
                    "due_at": due_at.isoformat(),
                    "seconds_remaining": max(int((due_at - now).total_seconds()), 0),
                }
            )
        pending.sort(key=lambda item: (item.get("due_at") or "", item.get("entry_id") or ""))
        return pending

    def next_due_in_seconds(self) -> float | None:
        pending = self.pending_settle_timers()
        if not pending:
            return None
        return max(float(pending[0].get("seconds_remaining") or 0), 0.0)

    def _configured_watcher_mode(self) -> str:
        settings = self.intake_settings()
        if not bool(settings.get("enabled")) or not bool(settings.get("watcher_enabled")):
            return WATCHER_MODE_DISABLED
        return WATCHER_MODE_WATCHFILES if _watchfiles_watch is not None else WATCHER_MODE_SCAN_FALLBACK

    def _previous_tracker_projection(self) -> dict[str, Any]:
        try:
            payload = json.loads(self.paths.raw_seed_entry_tracker_json.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return payload if isinstance(payload, dict) else {}

    def _watcher_projection_state(self) -> dict[str, Any]:
        configured_mode = self._configured_watcher_mode()
        if configured_mode == WATCHER_MODE_DISABLED:
            return {
                "mode": WATCHER_MODE_DISABLED,
                "error": None,
                "source": "disabled_by_settings",
                "running_in_process": False,
                "config_enabled": False,
            }
        if self._watchers_requested:
            return {
                "mode": self.watcher.mode,
                "error": self.watcher.error,
                "source": "process",
                "running_in_process": self.watcher.mode != WATCHER_MODE_DISABLED,
                "config_enabled": True,
            }
        previous = self._previous_tracker_projection()
        previous_mode = str(previous.get("watcher_mode") or "").strip()
        if previous_mode in {WATCHER_MODE_WATCHFILES, WATCHER_MODE_SCAN_FALLBACK}:
            return {
                "mode": previous_mode,
                "error": previous.get("watcher_error"),
                "source": "previous_live_projection",
                "running_in_process": False,
                "config_enabled": True,
            }
        return {
            "mode": configured_mode,
            "error": None,
            "source": "configured_capability",
            "running_in_process": False,
            "config_enabled": True,
        }

    def build_projection(self) -> dict[str, Any]:
        self.refresh_family_roots()
        watcher_state = self._watcher_projection_state()
        sessions = store.list_raw_seed_entry_sessions(self.conn, limit=100)
        pending = self.pending_settle_timers()
        sessions_by_family: dict[str, list[dict[str, Any]]] = {}
        due_by_entry = {item["entry_id"]: item["due_at"] for item in pending}
        for session in sessions:
            sessions_by_family.setdefault(str(session.get("family_number") or ""), []).append(session)
        watched_families = [
            {
                "family_number": root.family_number,
                "family_dir": root.family_dir,
                "raw_seed_path": root.raw_seed_path,
            }
            for root in sorted(self.family_roots.values(), key=lambda item: item.family_number)
        ]
        latest_synced = store.latest_raw_seed_entry_session(self.conn, states=["synced"])
        families: list[dict[str, Any]] = []
        for root in sorted(self.family_roots.values(), key=lambda item: item.family_number):
            family_sessions = sessions_by_family.get(root.family_number, [])
            active_sessions = [row for row in family_sessions if row.get("state") in ACTIVE_ENTRY_STATES]
            latest_session = family_sessions[0] if family_sessions else {}
            families.append(
                {
                    "family_number": root.family_number,
                    "family_dir": root.family_dir,
                    "raw_seed_path": root.raw_seed_path,
                    "active_sessions": [
                        _session_public(session, due_at=due_by_entry.get(str(session.get("entry_id") or "")))
                        for session in active_sessions[:6]
                    ],
                    "latest_session": _session_public(
                        latest_session,
                        due_at=due_by_entry.get(str(latest_session.get("entry_id") or "")),
                    ) if latest_session else None,
                }
            )
        projection = {
            "schema": TRACKER_SCHEMA,
            "generated_at": _utc_now(),
            "watcher_mode": watcher_state["mode"],
            "watcher_error": watcher_state["error"],
            "watcher_projection_source": watcher_state["source"],
            "watcher_running_in_process": watcher_state["running_in_process"],
            "watcher_config_enabled": watcher_state["config_enabled"],
            "watched_families": watched_families,
            "active_draft_sessions": [
                _session_public(session, due_at=due_by_entry.get(str(session.get("entry_id") or "")))
                for session in sessions
                if session.get("state") in ACTIVE_ENTRY_STATES
            ],
            "pending_settle_timers": pending,
            "last_auto_sync": _session_public(latest_synced) if latest_synced else None,
            "families": families,
            "tracker_path": str(self.paths.raw_seed_entry_tracker_json.relative_to(self.repo_root)),
            "timeline_path": str(self.paths.raw_seed_entry_timeline_jsonl.relative_to(self.repo_root)),
        }
        return projection

    def write_projection(self) -> dict[str, Any]:
        projection = self.build_projection()
        _atomic_write(self.paths.raw_seed_entry_tracker_json, projection)
        return projection

    def list_entries(self, *, family_number: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        rows = store.list_raw_seed_entry_sessions(self.conn, family_number=family_number, limit=limit)
        due_by_entry = {item["entry_id"]: item["due_at"] for item in self.pending_settle_timers()}
        return [
            _session_public(row, due_at=due_by_entry.get(str(row.get("entry_id") or "")))
            for row in rows
        ]
