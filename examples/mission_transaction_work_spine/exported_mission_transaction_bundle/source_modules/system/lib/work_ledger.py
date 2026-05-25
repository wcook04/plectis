"""
[PURPOSE]
- Teleology: Own the repo-native event-sourced work ledger: append-only JSONL,
  deterministic reduction, projection building, and recipe-based retrieval.
- Mechanism: Serialize writes through per-family file locks, mint stable ids,
  validate lifecycle events, reduce event chains into thread state, and write
  authoritative per-phase projections under codex/ledger/<phase_id>/.
- Non-goal: Hook enforcement and session receipts. Those live in
  system/lib/work_ledger_runtime.py.
"""
from __future__ import annotations

import json
import os
import re
import uuid
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Mapping, Optional

try:
    import fcntl
except ImportError:  # pragma: no cover - non-posix fallback
    fcntl = None  # type: ignore[assignment]


WORK_LEDGER_SCHEMA = "work_ledger_v1"
WORK_LEDGER_INDEX_SCHEMA = "work_ledger_index_v1"
WORK_LEDGER_QUERY_RECIPES = (
    "open_in_family",
    "open_for_actor",
    "closed_this_session",
    "supersession_chain",
    "cross_agent_handoffs",
    "stale_open",
    "work_memory_items",
    "thread",
)
WORK_LEDGER_STANDARD_REL = Path("codex/standards/std_work_ledger.json")
WORK_LEDGER_ROOT_REL = Path("codex/ledger")
DEFAULT_STALE_OPEN_HOURS = 24
WORK_MEMORY_ITEM_LIMIT = 200

EVENT_KINDS = {
    "todo_open",
    "progress_note",
    "todo_close",
    "todo_supersede",
    "todo_reopen",
}
RESOLUTION_KINDS = {
    "git_commit",
    "orchestration_event",
    "raw_seed_paragraph",
    "artifact",
    "session",
}

TD_ID_RE = re.compile(r"^td_[a-z0-9]{10,}$")
EVENT_ID_RE = re.compile(r"^wle_[a-z0-9]{10,}$")

PHASE_FAMILY_ROOT = "obsidian/okay lets do this"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def mint_td_id() -> str:
    return f"td_{uuid.uuid4().hex[:16]}"


def mint_event_id() -> str:
    return f"wle_{uuid.uuid4().hex[:16]}"


def _normalize_phase_id(value: str | None) -> str:
    token = str(value or "").strip().replace(".", "_")
    if not token:
        raise ValueError("phase_id is required")
    return token


def _normalize_family_id(value: str | None) -> str:
    token = str(value or "").strip()
    if not token:
        raise ValueError("family_id is required")
    return token


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _list_family_dirs(repo_root: Path) -> List[Path]:
    root = repo_root / PHASE_FAMILY_ROOT
    if not root.exists() or not root.is_dir():
        return []
    return [child for child in root.iterdir() if child.is_dir()]


def resolve_active_phase_context(repo_root: Path) -> Dict[str, str]:
    latest: tuple[str, str, str] | None = None
    for family_dir in _list_family_dirs(repo_root):
        phase_family = _safe_read_json(family_dir / "phase_family.json")
        family_id = (
            str(phase_family.get("family_id") or phase_family.get("family_number") or "").strip()
            or None
        )
        phase_id = (
            str(phase_family.get("active_phase_id") or phase_family.get("active_phase_number") or "").strip()
            or None
        )
        changed_at = str(phase_family.get("active_phase_changed_at") or "").strip()
        if not family_id or not phase_id:
            continue
        normalized_phase = _normalize_phase_id(phase_id)
        candidate = (changed_at, family_id, normalized_phase)
        if latest is None or candidate > latest:
            latest = candidate
    if latest is None:
        raise ValueError("could not resolve active phase/family context")
    _, family_id, phase_id = latest
    return {"family_id": family_id, "phase_id": phase_id}


def _infer_family_from_bucket(repo_root: Path, phase_id: str) -> Optional[str]:
    raw_path = repo_root / WORK_LEDGER_ROOT_REL / phase_id / "work_ledger.jsonl"
    if raw_path.exists():
        for event in read_jsonl(raw_path):
            family_id = str(event.get("family_id") or "").strip()
            if family_id:
                return family_id
    index_path = repo_root / WORK_LEDGER_ROOT_REL / phase_id / "work_ledger_index.json"
    index = _safe_read_json(index_path)
    family_id = str(index.get("family_id") or "").strip()
    return family_id or None


def _phase_bucket_families(repo_root: Path, phase_id: str) -> List[str]:
    raw_path = repo_root / WORK_LEDGER_ROOT_REL / _normalize_phase_id(phase_id) / "work_ledger.jsonl"
    families: set[str] = set()
    for event in read_jsonl(raw_path):
        family_id = str(event.get("family_id") or "").strip()
        if family_id:
            families.add(family_id)
    return sorted(families)


def _safe_family_index_token(family_id: str) -> str:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(family_id or "").strip()).strip("._-")
    return token or "unknown"


def _projection_index_path(
    repo_root: Path,
    *,
    phase_id: str,
    family_id: str,
) -> tuple[Path, str]:
    normalized_phase = _normalize_phase_id(phase_id)
    normalized_family = _normalize_family_id(family_id)
    ledger_dir = repo_root / WORK_LEDGER_ROOT_REL / normalized_phase
    legacy_index_path = ledger_dir / "work_ledger_index.json"
    families = _phase_bucket_families(repo_root, normalized_phase)
    if len(families) > 1:
        primary_family = _infer_family_from_bucket(repo_root, normalized_phase)
        if primary_family and normalized_family != primary_family:
            token = _safe_family_index_token(normalized_family)
            return ledger_dir / f"work_ledger_index.{token}.json", "mixed_phase_family_scoped"
    return legacy_index_path, "legacy_phase_primary_family"


def resolve_phase_context(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, str]:
    if phase_id is None and family_id is None:
        return resolve_active_phase_context(repo_root)
    normalized_phase = _normalize_phase_id(phase_id) if phase_id else None
    normalized_family = _normalize_family_id(family_id) if family_id else None
    if normalized_phase and normalized_family:
        return {"phase_id": normalized_phase, "family_id": normalized_family}
    if normalized_phase and not normalized_family:
        inferred_family = _infer_family_from_bucket(repo_root, normalized_phase)
        if inferred_family:
            return {"phase_id": normalized_phase, "family_id": inferred_family}
        active = resolve_active_phase_context(repo_root)
        if active["phase_id"] == normalized_phase:
            return active
        raise ValueError(f"could not infer family_id for phase '{normalized_phase}'")
    if normalized_family:
        bucket_phase = _latest_family_phase_bucket(repo_root, normalized_family)
        if bucket_phase:
            return {"phase_id": bucket_phase, "family_id": normalized_family}
    active = resolve_active_phase_context(repo_root)
    return {"phase_id": active["phase_id"], "family_id": normalized_family or active["family_id"]}


def ledger_paths(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Path | str]:
    context = resolve_phase_context(repo_root, phase_id=phase_id, family_id=family_id)
    phase = context["phase_id"]
    family = context["family_id"]
    ledger_dir = repo_root / WORK_LEDGER_ROOT_REL / phase
    index_path, index_path_policy = _projection_index_path(
        repo_root,
        phase_id=phase,
        family_id=family,
    )
    return {
        "phase_id": phase,
        "family_id": family,
        "ledger_dir": ledger_dir,
        "raw_path": ledger_dir / "work_ledger.jsonl",
        "index_path": index_path,
        "legacy_index_path": ledger_dir / "work_ledger_index.json",
        "index_path_policy": index_path_policy,
        "lock_path": ledger_dir / ".work_ledger.lock",
    }


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if isinstance(item, dict):
            rows.append(item)
    return rows


def _bucket_raw_paths(repo_root: Path) -> List[Path]:
    root = repo_root / WORK_LEDGER_ROOT_REL
    if not root.exists() or not root.is_dir():
        return []
    return sorted(path / "work_ledger.jsonl" for path in root.iterdir() if path.is_dir())


def load_events(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
    td_id: str | None = None,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if phase_id:
        raw_path = repo_root / WORK_LEDGER_ROOT_REL / _normalize_phase_id(phase_id) / "work_ledger.jsonl"
        candidates = [raw_path]
    else:
        candidates = _bucket_raw_paths(repo_root)
    normalized_family = _normalize_family_id(family_id) if family_id else None
    target_td = str(td_id or "").strip() or None
    for path in candidates:
        for event in read_jsonl(path):
            if normalized_family and str(event.get("family_id") or "").strip() != normalized_family:
                continue
            if target_td and str(event.get("td_id") or "").strip() != target_td and str(event.get("supersedes_td_id") or "").strip() != target_td:
                continue
            rows.append(event)
    rows.sort(key=lambda event: (str(event.get("created_at") or ""), str(event.get("event_id") or "")))
    return rows


def _family_phase_buckets(repo_root: Path, family_id: str) -> List[str]:
    buckets: set[str] = set()
    for path in _bucket_raw_paths(repo_root):
        bucket_phase = path.parent.name
        for event in read_jsonl(path):
            if str(event.get("family_id") or "").strip() == family_id:
                buckets.add(bucket_phase)
                break
    return sorted(buckets)


def _family_raw_event_scan(repo_root: Path, family_id: str) -> tuple[int, List[str]]:
    buckets: set[str] = set()
    event_count = 0
    for path in _bucket_raw_paths(repo_root):
        bucket_phase = path.parent.name
        bucket_has_family_event = False
        for event in read_jsonl(path):
            if str(event.get("family_id") or "").strip() != family_id:
                continue
            event_count += 1
            bucket_has_family_event = True
        if bucket_has_family_event:
            buckets.add(bucket_phase)
    return event_count, sorted(buckets)


def _latest_family_phase_bucket(repo_root: Path, family_id: str) -> Optional[str]:
    buckets = _family_phase_buckets(repo_root, family_id)
    return buckets[-1] if buckets else None


def _require_identifier(value: str, pattern: re.Pattern[str], label: str) -> str:
    token = str(value or "").strip()
    if not pattern.match(token):
        raise ValueError(f"{label} '{token}' is invalid")
    return token


def _validate_resolution_episode(value: Mapping[str, Any] | None) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("resolution_episode is required")
    kind = str(value.get("kind") or "").strip()
    ref = str(value.get("ref") or "").strip()
    if kind not in RESOLUTION_KINDS:
        raise ValueError(f"resolution_episode.kind '{kind}' is not allowed")
    if not ref:
        raise ValueError("resolution_episode.ref is required")
    episode = {"kind": kind, "ref": ref}
    if value.get("label"):
        episode["label"] = str(value.get("label"))
    metadata = value.get("metadata")
    if isinstance(metadata, Mapping):
        episode["metadata"] = dict(metadata)
    return episode


def build_resolution_episode(
    kind: str,
    ref: str,
    *,
    label: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    episode: Dict[str, Any] = {"kind": kind, "ref": ref}
    if label:
        episode["label"] = label
    if metadata:
        episode["metadata"] = dict(metadata)
    return _validate_resolution_episode(episode)


def with_task_ledger_work_item_metadata(
    metadata: Mapping[str, Any] | None,
    work_item_id: str | None,
) -> Dict[str, Any]:
    """
    Stamp the canonical Task Ledger WorkItem id onto a Work Ledger thread's
    metadata dict so the workitem_cartography_v0 crosswalk can join queue
    rows back to atlas_marks without late-stage heuristics.

    Wave 1D.5 propagation invariant: a Work Ledger row that is about a
    Task Ledger WorkItem MUST carry that WorkItem's canonical id as data
    under `metadata.task_ledger_work_item_id`. This helper preserves any
    pre-existing metadata, refuses to silently overwrite a different
    existing value, and is idempotent: passing the same id twice is a
    no-op. `metadata.task_ledger_work_item_bridge.task_ledger_work_item_id`
    and `metadata.subject_id` are still accepted by the crosswalk
    (Tier-1 fallbacks) but new mutation lanes should set the canonical
    top-level field directly.
    """
    merged: Dict[str, Any] = dict(metadata or {})
    if not work_item_id:
        return merged
    canonical = str(work_item_id).strip()
    if not canonical:
        return merged
    existing = merged.get("task_ledger_work_item_id")
    if existing and str(existing).strip() != canonical:
        # Preserve the caller-supplied value but record the alternative so
        # future audits can see where the conflict came from. Do not
        # overwrite silently — the caller likely has bigger problems.
        # Tolerate malformed prior values: alternatives must always end as
        # a list, even if the field was previously a string/dict/None.
        alts_raw = merged.get("task_ledger_work_item_id_alternatives")
        if isinstance(alts_raw, list):
            alts = list(alts_raw)
        elif alts_raw in (None, "", {}):
            alts = []
        else:
            alts = [alts_raw]
        alts.append(canonical)
        merged["task_ledger_work_item_id_alternatives"] = alts
    else:
        merged["task_ledger_work_item_id"] = canonical
    return merged


def _thread_card(thread: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "td_id": thread.get("td_id"),
        "root_td_id": thread.get("root_td_id"),
        "title": thread.get("title"),
        "body": thread.get("body"),
        "status": thread.get("status"),
        "phase_id": thread.get("phase_id"),
        "family_id": thread.get("family_id"),
        "opened_at": thread.get("opened_at"),
        "current_valid_at": thread.get("current_valid_at"),
        "invalid_at": thread.get("invalid_at"),
        "last_event_at": thread.get("last_event_at"),
        "last_event_kind": thread.get("last_event_kind"),
        "last_actor": thread.get("last_actor"),
        "actors": list(thread.get("actors") or []),
        "successor_td_id": thread.get("successor_td_id"),
        "predecessor_td_id": thread.get("predecessor_td_id"),
        "resolution_episode": thread.get("resolution_episode"),
        "metadata": dict(thread.get("metadata") or {}),
    }


def _compact_summary(*parts: Any, max_chars: int = 320) -> str:
    text = " - ".join(str(part).strip() for part in parts if str(part or "").strip())
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    return f"{text[: max_chars - 3].rstrip()}..."


def _resolution_summary(event: Mapping[str, Any]) -> str:
    episode = event.get("resolution_episode")
    if not isinstance(episode, Mapping):
        return ""
    label = str(episode.get("label") or "").strip()
    kind = str(episode.get("kind") or "").strip()
    ref = str(episode.get("ref") or "").strip()
    if label:
        return f"{kind}:{ref} ({label})"
    return f"{kind}:{ref}" if kind and ref else ""


def _work_memory_item(thread: Mapping[str, Any], event: Mapping[str, Any]) -> Optional[Dict[str, Any]]:
    kind = str(event.get("event_kind") or "").strip()
    title = str(event.get("title") or thread.get("title") or "").strip()
    body = str(event.get("body") or "").strip()
    memory_type = ""
    role = ""
    summary = ""

    if kind == "todo_open":
        memory_type = "semantic"
        role = "work_claim"
        summary = _compact_summary("Open work", title, body)
    elif kind == "progress_note":
        memory_type = "episodic"
        role = "progress_update"
        summary = _compact_summary("Progress", title or thread.get("title"), body)
    elif kind == "todo_close":
        memory_type = "procedural"
        role = "resolution"
        summary = _compact_summary("Resolved work", title or thread.get("title"), body, _resolution_summary(event))
    elif kind == "todo_reopen":
        memory_type = "episodic"
        role = "reopen"
        summary = _compact_summary("Reopened work", title or thread.get("title"), body)
    elif kind == "todo_supersede":
        memory_type = "procedural"
        role = "supersession"
        summary = _compact_summary(
            "Superseded work",
            f"{event.get('supersedes_td_id')} -> {event.get('td_id')}",
            title,
            body,
            _resolution_summary(event),
        )
    if not summary:
        return None

    event_id = str(event.get("event_id") or "").strip()
    item: Dict[str, Any] = {
        "memory_id": f"wm_{event_id.removeprefix('wle_')}_{memory_type}",
        "memory_type": memory_type,
        "role": role,
        "source": "work_ledger",
        "td_id": event.get("td_id") or thread.get("td_id"),
        "event_id": event.get("event_id"),
        "event_kind": kind,
        "status": thread.get("status"),
        "title": title or thread.get("title"),
        "summary": summary,
        "actor": event.get("actor"),
        "actor_session_id": event.get("actor_session_id"),
        "phase_id": event.get("phase_id") or thread.get("phase_id"),
        "family_id": event.get("family_id") or thread.get("family_id"),
        "created_at": event.get("created_at"),
        "valid_at": event.get("valid_at"),
        "invalid_at": event.get("invalid_at"),
        "evidence_refs": list(event.get("evidence_refs") or []),
    }
    if event.get("resolution_episode"):
        item["resolution_episode"] = event.get("resolution_episode")
    if event.get("metadata"):
        item["metadata"] = dict(event.get("metadata") or {})
    if event.get("supersedes_td_id"):
        item["supersedes_td_id"] = event.get("supersedes_td_id")
    if thread.get("successor_td_id"):
        item["successor_td_id"] = thread.get("successor_td_id")
    if thread.get("predecessor_td_id"):
        item["predecessor_td_id"] = thread.get("predecessor_td_id")
    return item


def _build_work_memory_items(threads: Mapping[str, Mapping[str, Any]]) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    for thread in threads.values():
        for event in thread.get("events") or []:
            item = _work_memory_item(thread, event)
            if item is not None:
                items.append(item)
    items.sort(
        key=lambda item: (
            str(item.get("created_at") or ""),
            str(item.get("memory_id") or ""),
        ),
        reverse=True,
    )
    return items[:WORK_MEMORY_ITEM_LIMIT]


def _close_interval(thread: Dict[str, Any], event: Mapping[str, Any], *, status: str) -> None:
    intervals = thread.setdefault("intervals", [])
    if intervals and intervals[-1].get("invalid_at") is None:
        intervals[-1]["invalid_at"] = event.get("invalid_at") or event.get("created_at")
        intervals[-1]["closed_by_event_id"] = event.get("event_id")
        if event.get("resolution_episode"):
            intervals[-1]["resolution_episode"] = event.get("resolution_episode")
    thread["status"] = status
    thread["invalid_at"] = event.get("invalid_at") or event.get("created_at")
    thread["resolution_episode"] = event.get("resolution_episode")


def _open_interval(thread: Dict[str, Any], event: Mapping[str, Any]) -> None:
    intervals = thread.setdefault("intervals", [])
    intervals.append(
        {
            "opened_by_event_id": event.get("event_id"),
            "valid_at": event.get("valid_at"),
            "invalid_at": None,
            "opened_by_actor": event.get("actor"),
            "opened_by_session": event.get("actor_session_id"),
        }
    )
    thread["status"] = "open"
    thread["current_valid_at"] = event.get("valid_at")
    thread["invalid_at"] = None
    if not thread.get("opened_at"):
        thread["opened_at"] = event.get("valid_at")


def _new_thread(event: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "td_id": event.get("td_id"),
        "root_td_id": event.get("td_id"),
        "predecessor_td_id": None,
        "successor_td_id": None,
        "title": event.get("title"),
        "body": event.get("body"),
        "status": "unknown",
        "phase_id": event.get("phase_id"),
        "family_id": event.get("family_id"),
        "opened_at": None,
        "current_valid_at": None,
        "invalid_at": None,
        "expired_at": None,
        "last_event_id": None,
        "last_event_kind": None,
        "last_event_at": None,
        "last_actor": None,
        "last_actor_session_id": None,
        "actors": [],
        "actor_sessions": [],
        "intervals": [],
        "events": [],
        "metadata": {},
        "event_metadata": [],
        "notes": [],
        "evidence_refs": [],
        "resolution_episode": None,
    }


def _append_actor(thread: Dict[str, Any], actor: str, actor_session_id: str) -> None:
    if actor and actor not in thread["actors"]:
        thread["actors"].append(actor)
    if actor_session_id and actor_session_id not in thread["actor_sessions"]:
        thread["actor_sessions"].append(actor_session_id)


def build_projection(
    events: Iterable[Mapping[str, Any]],
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
    generated_at: str | None = None,
) -> Dict[str, Any]:
    event_list = [dict(event) for event in events]
    event_list.sort(key=lambda event: (str(event.get("created_at") or ""), str(event.get("event_id") or "")))
    threads: Dict[str, Dict[str, Any]] = {}
    recently_closed: List[Dict[str, Any]] = []
    cross_agent_handoffs: List[Dict[str, Any]] = []

    for event in event_list:
        td_id = str(event.get("td_id") or "").strip()
        if not td_id:
            continue
        thread = threads.setdefault(td_id, _new_thread(event))
        actor = str(event.get("actor") or "").strip()
        actor_session_id = str(event.get("actor_session_id") or "").strip()
        _append_actor(thread, actor, actor_session_id)
        if event.get("title"):
            thread["title"] = event.get("title")
        if event.get("body"):
            thread["body"] = event.get("body")
        if event.get("expired_at"):
            thread["expired_at"] = event.get("expired_at")
        metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
        if metadata:
            thread["metadata"] = {**dict(thread.get("metadata") or {}), **dict(metadata)}
            thread.setdefault("event_metadata", []).append(
                {
                    "event_id": event.get("event_id"),
                    "event_kind": event.get("event_kind"),
                    "created_at": event.get("created_at"),
                    "metadata": dict(metadata),
                }
            )
        for evidence in event.get("evidence_refs") or []:
            if evidence not in thread["evidence_refs"]:
                thread["evidence_refs"].append(evidence)
        thread["events"].append(dict(event))
        thread["last_event_id"] = event.get("event_id")
        thread["last_event_kind"] = event.get("event_kind")
        thread["last_event_at"] = event.get("created_at")
        thread["last_actor"] = actor
        thread["last_actor_session_id"] = actor_session_id
        thread["phase_id"] = event.get("phase_id") or thread.get("phase_id")
        thread["family_id"] = event.get("family_id") or thread.get("family_id")

        kind = str(event.get("event_kind") or "").strip()
        if kind == "todo_open":
            _open_interval(thread, event)
        elif kind == "progress_note":
            thread["notes"].append(
                {
                    "event_id": event.get("event_id"),
                    "created_at": event.get("created_at"),
                    "actor": actor,
                    "body": event.get("body"),
                    "title": event.get("title"),
                }
            )
            if thread["status"] == "unknown":
                thread["status"] = "open"
        elif kind == "todo_close":
            _close_interval(thread, event, status="closed")
            recently_closed.append(
                {
                    "td_id": td_id,
                    "title": thread.get("title"),
                    "closed_at": event.get("invalid_at") or event.get("created_at"),
                    "status": "closed",
                    "actor": actor,
                    "actor_session_id": actor_session_id,
                    "event_id": event.get("event_id"),
                    "resolution_episode": event.get("resolution_episode"),
                    "metadata": dict(metadata),
                }
            )
        elif kind == "todo_reopen":
            _open_interval(thread, event)
        elif kind == "todo_supersede":
            predecessor_id = str(event.get("supersedes_td_id") or "").strip()
            if predecessor_id:
                predecessor = threads.setdefault(predecessor_id, _new_thread({
                    "td_id": predecessor_id,
                    "phase_id": event.get("phase_id"),
                    "family_id": event.get("family_id"),
                }))
                predecessor["successor_td_id"] = td_id
                _close_interval(predecessor, event, status="superseded")
                recently_closed.append(
                    {
                        "td_id": predecessor_id,
                        "title": predecessor.get("title"),
                        "closed_at": event.get("created_at"),
                        "status": "superseded",
                        "actor": actor,
                        "actor_session_id": actor_session_id,
                        "event_id": event.get("event_id"),
                        "successor_td_id": td_id,
                        "resolution_episode": event.get("resolution_episode"),
                        "metadata": dict(metadata),
                    }
                )
                thread["predecessor_td_id"] = predecessor_id
                thread["root_td_id"] = predecessor.get("root_td_id") or predecessor_id
            _open_interval(thread, event)
            thread["resolution_episode"] = None

    for thread in threads.values():
        previous_actor: Optional[str] = None
        previous_event_id: Optional[str] = None
        for event in thread.get("events") or []:
            actor = str(event.get("actor") or "").strip()
            if previous_actor and actor and actor != previous_actor:
                cross_agent_handoffs.append(
                    {
                        "td_id": thread.get("td_id"),
                        "from_actor": previous_actor,
                        "to_actor": actor,
                        "event_id": event.get("event_id"),
                        "from_event_id": previous_event_id,
                        "event_kind": event.get("event_kind"),
                        "created_at": event.get("created_at"),
                        "title": thread.get("title"),
                    }
                )
            previous_actor = actor or previous_actor
            previous_event_id = str(event.get("event_id") or "") or previous_event_id

    now_dt = datetime.now(timezone.utc)
    open_by_actor: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    open_by_family: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    stale_open: List[Dict[str, Any]] = []
    open_threads = 0
    closed_threads = 0
    superseded_threads = 0

    for thread in threads.values():
        card = _thread_card(thread)
        status = str(thread.get("status") or "unknown")
        if status == "open":
            open_threads += 1
            actor_key = str(thread.get("last_actor") or "unknown")
            family_key = str(thread.get("family_id") or "unknown")
            open_by_actor[actor_key].append(card)
            open_by_family[family_key].append(card)
            last_event_at = str(thread.get("last_event_at") or "").strip()
            if last_event_at:
                try:
                    dt = datetime.fromisoformat(last_event_at.replace("Z", "+00:00"))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    age_seconds = int((now_dt - dt).total_seconds())
                    if age_seconds >= DEFAULT_STALE_OPEN_HOURS * 3600:
                        stale_open.append(card)
                except ValueError:
                    pass
        elif status == "closed":
            closed_threads += 1
        elif status == "superseded":
            superseded_threads += 1

    def _chain_for_root(root_id: str) -> Dict[str, Any]:
        chain: List[Dict[str, Any]] = []
        seen: set[str] = set()
        current = root_id
        while current and current not in seen and current in threads:
            seen.add(current)
            thread = threads[current]
            chain.append(
                {
                    "td_id": current,
                    "title": thread.get("title"),
                    "status": thread.get("status"),
                    "last_event_at": thread.get("last_event_at"),
                    "successor_td_id": thread.get("successor_td_id"),
                    "predecessor_td_id": thread.get("predecessor_td_id"),
                }
            )
            current = str(thread.get("successor_td_id") or "").strip()
        return {
            "root_td_id": root_id,
            "length": len(chain),
            "chain": chain,
        }

    roots = [
        td_id
        for td_id, thread in threads.items()
        if not str(thread.get("predecessor_td_id") or "").strip()
    ]
    supersession_chains = [
        _chain_for_root(root)
        for root in sorted(roots)
        if len(_chain_for_root(root)["chain"]) > 1
    ]

    recently_closed.sort(key=lambda item: str(item.get("closed_at") or ""), reverse=True)
    cross_agent_handoffs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    stale_open.sort(key=lambda item: str(item.get("last_event_at") or ""))
    for cards in open_by_actor.values():
        cards.sort(key=lambda item: str(item.get("last_event_at") or ""), reverse=True)
    for cards in open_by_family.values():
        cards.sort(key=lambda item: str(item.get("last_event_at") or ""), reverse=True)
    work_memory_items = _build_work_memory_items(threads)

    family_guess = family_id or next(
        (str(event.get("family_id") or "").strip() for event in event_list if str(event.get("family_id") or "").strip()),
        None,
    )

    return {
        "schema": WORK_LEDGER_INDEX_SCHEMA,
        "generated_at": generated_at or utc_now(),
        "phase_id": phase_id,
        "family_id": family_guess,
        "open_by_actor": dict(open_by_actor),
        "open_by_family": dict(open_by_family),
        "recently_closed": recently_closed[:50],
        "supersession_chains": supersession_chains,
        "cross_agent_handoffs": cross_agent_handoffs[:50],
        "stale_open": stale_open[:50],
        "work_memory_items": work_memory_items,
        "threads": threads,
        "counts": {
            "events": len(event_list),
            "threads": len(threads),
            "open_threads": open_threads,
            "closed_threads": closed_threads,
            "superseded_threads": superseded_threads,
            "recently_closed": len(recently_closed),
            "cross_agent_handoffs": len(cross_agent_handoffs),
            "stale_open": len(stale_open),
            "work_memory_items": len(work_memory_items),
            "open_by_actor": {key: len(value) for key, value in open_by_actor.items()},
            "open_by_family": {key: len(value) for key, value in open_by_family.items()},
        },
        "recipe_vocabulary": list(WORK_LEDGER_QUERY_RECIPES),
    }


def supported_query_recipes() -> tuple[str, ...]:
    return WORK_LEDGER_QUERY_RECIPES


def bootstrap_phase_bucket(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Any]:
    paths = ledger_paths(repo_root, phase_id=phase_id, family_id=family_id)
    raw_path = paths["raw_path"]
    index_path = paths["index_path"]
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    if not raw_path.exists():
        raw_path.write_text("", encoding="utf-8")
    if not index_path.exists():
        atomic_write_json(
            index_path,
            build_projection(
                [],
                phase_id=str(paths["phase_id"]),
                family_id=str(paths["family_id"]),
            ),
        )
    return {
        "ok": True,
        "phase_id": paths["phase_id"],
        "family_id": paths["family_id"],
        "raw_path": str(raw_path.relative_to(repo_root)),
        "index_path": str(index_path.relative_to(repo_root)),
    }


def _family_projection_targets(repo_root: Path, family_id: str, include_phase_id: str) -> List[str]:
    buckets = set(_family_phase_buckets(repo_root, family_id))
    buckets.add(_normalize_phase_id(include_phase_id))
    return sorted(buckets)


def write_family_projections(
    repo_root: Path,
    *,
    family_id: str,
    include_phase_id: str,
) -> List[Dict[str, Any]]:
    normalized_family = _normalize_family_id(family_id)
    events = load_events(repo_root, family_id=normalized_family)
    generated_at = utc_now()
    family_projection = build_projection(
        events,
        phase_id=None,
        family_id=normalized_family,
        generated_at=generated_at,
    )
    results: List[Dict[str, Any]] = []
    for bucket_phase in _family_projection_targets(repo_root, normalized_family, include_phase_id):
        target = ledger_paths(repo_root, phase_id=bucket_phase, family_id=normalized_family)
        index_path = Path(target["index_path"])
        existing = _safe_read_json(index_path)
        projection = {**family_projection, "phase_id": bucket_phase}
        fresh_existing = (
            bool(existing)
            and not _projection_has_legacy_volatile_fields(existing)
            and _projection_compare_payload(existing) == _projection_compare_payload(projection)
        )
        if fresh_existing:
            projection["generated_at"] = existing.get("generated_at")
        else:
            atomic_write_json(index_path, projection)
        results.append(
            {
                "phase_id": bucket_phase,
                "index_path": str(index_path.relative_to(repo_root)),
                "counts": projection.get("counts"),
            }
        )
    return results


def _projection_events_from_payload(payload: Mapping[str, Any]) -> Optional[List[Dict[str, Any]]]:
    threads = payload.get("threads")
    if not isinstance(threads, Mapping):
        counts = payload.get("counts")
        event_count = int(counts.get("events") or 0) if isinstance(counts, Mapping) else 0
        return [] if event_count == 0 else None
    events_by_id: Dict[str, Dict[str, Any]] = {}
    for thread in threads.values():
        if not isinstance(thread, Mapping):
            return None
        events = thread.get("events")
        if not isinstance(events, list):
            continue
        for event in events:
            if not isinstance(event, Mapping):
                return None
            event_id = str(event.get("event_id") or "").strip()
            if not event_id:
                return None
            events_by_id[event_id] = dict(event)
    events = list(events_by_id.values())
    events.sort(key=lambda event: (str(event.get("created_at") or ""), str(event.get("event_id") or "")))
    return events


def write_phase_projection(
    repo_root: Path,
    *,
    phase_id: str,
    family_id: str,
    events: List[Dict[str, Any]] | None = None,
    reason: str = "phase_projection_rebuild",
) -> Dict[str, Any]:
    normalized_phase = _normalize_phase_id(phase_id)
    normalized_family = _normalize_family_id(family_id)
    target = ledger_paths(repo_root, phase_id=normalized_phase, family_id=normalized_family)
    index_path = Path(target["index_path"])
    if events is None:
        events = load_events(repo_root, family_id=normalized_family)
    projection = build_projection(
        events,
        phase_id=normalized_phase,
        family_id=normalized_family,
    )
    atomic_write_json(index_path, projection)
    return {
        "phase_id": normalized_phase,
        "index_path": str(index_path.relative_to(repo_root)),
        "counts": projection.get("counts"),
        "mode": reason,
    }


def _deferred_family_projection_rows(
    repo_root: Path,
    *,
    family_id: str,
    updated_phase_id: str,
    buckets: List[str],
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    normalized_family = _normalize_family_id(family_id)
    normalized_updated_phase = _normalize_phase_id(updated_phase_id)
    for bucket_phase in sorted(set(buckets)):
        if bucket_phase == normalized_updated_phase:
            continue
        target = ledger_paths(repo_root, phase_id=bucket_phase, family_id=normalized_family)
        index_path = Path(target["index_path"])
        rows.append(
            {
                "phase_id": bucket_phase,
                "index_path": str(index_path.relative_to(repo_root)),
                "status": "deferred",
                "reason": "append_only_projection_mode",
                "freshness_check_command": (
                    "./repo-python tools/meta/factory/work_ledger.py project "
                    f"--phase-id {bucket_phase} --family-id {normalized_family} --check"
                ),
                "refresh_command": (
                    "./repo-python tools/meta/factory/work_ledger.py project "
                    f"--phase-id {bucket_phase} --family-id {normalized_family}"
                ),
            }
        )
    return rows


def write_append_projection(
    repo_root: Path,
    *,
    event: Mapping[str, Any],
) -> Dict[str, Any]:
    normalized_phase = _normalize_phase_id(str(event.get("phase_id") or ""))
    normalized_family = _normalize_family_id(str(event.get("family_id") or ""))
    target = ledger_paths(repo_root, phase_id=normalized_phase, family_id=normalized_family)
    index_path = Path(target["index_path"])
    family_event_count_after_append, family_buckets = _family_raw_event_scan(repo_root, normalized_family)
    existing = _safe_read_json(index_path)
    existing_counts = existing.get("counts") if isinstance(existing.get("counts"), Mapping) else {}
    existing_event_count = int(existing_counts.get("events") or 0)
    existing_events = _projection_events_from_payload(existing) if existing else None
    expected_existing_event_count = max(family_event_count_after_append - 1, 0)
    can_increment = (
        bool(existing)
        and not _projection_has_legacy_volatile_fields(existing)
        and existing_event_count == expected_existing_event_count
        and existing_events is not None
        and len(existing_events) == existing_event_count
        and str(event.get("event_id") or "") not in {str(row.get("event_id") or "") for row in existing_events}
    )
    if can_increment:
        projection_events = [*existing_events, dict(event)]
        row = write_phase_projection(
            repo_root,
            phase_id=normalized_phase,
            family_id=normalized_family,
            events=projection_events,
            reason="append_only_incremental",
        )
    else:
        row = write_phase_projection(
            repo_root,
            phase_id=normalized_phase,
            family_id=normalized_family,
            reason="append_only_target_rebuild",
        )
    row["family_event_count"] = family_event_count_after_append
    return {
        "projection_results": [row],
        "deferred_projection_results": _deferred_family_projection_rows(
            repo_root,
            family_id=normalized_family,
            updated_phase_id=normalized_phase,
            buckets=family_buckets or [normalized_phase],
        ),
    }


def _validate_event_shape(event: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(event)
    normalized["event_id"] = _require_identifier(str(event.get("event_id") or ""), EVENT_ID_RE, "event_id")
    normalized["td_id"] = _require_identifier(str(event.get("td_id") or ""), TD_ID_RE, "td_id")
    kind = str(event.get("event_kind") or "").strip()
    if kind not in EVENT_KINDS:
        raise ValueError(f"event_kind '{kind}' is not allowed")
    normalized["event_kind"] = kind
    normalized["phase_id"] = _normalize_phase_id(str(event.get("phase_id") or ""))
    normalized["family_id"] = _normalize_family_id(str(event.get("family_id") or ""))
    normalized["actor"] = str(event.get("actor") or "").strip() or "unknown"
    normalized["actor_session_id"] = str(event.get("actor_session_id") or "").strip()
    normalized["created_at"] = str(event.get("created_at") or "").strip() or utc_now()
    normalized["valid_at"] = str(event.get("valid_at") or "").strip() or normalized["created_at"]
    normalized["invalid_at"] = event.get("invalid_at")
    normalized["expired_at"] = event.get("expired_at")
    normalized["title"] = str(event.get("title") or "").strip() or None
    normalized["body"] = str(event.get("body") or "").strip() or None
    evidence_refs = event.get("evidence_refs") if isinstance(event.get("evidence_refs"), list) else []
    normalized["evidence_refs"] = [str(item) for item in evidence_refs if str(item).strip()]
    metadata = event.get("metadata")
    normalized["metadata"] = dict(metadata) if isinstance(metadata, Mapping) else {}
    if kind in {"todo_close", "todo_supersede"}:
        normalized["resolution_episode"] = _validate_resolution_episode(
            event.get("resolution_episode") if isinstance(event.get("resolution_episode"), Mapping) else None
        )
    elif event.get("resolution_episode") is not None and isinstance(event.get("resolution_episode"), Mapping):
        normalized["resolution_episode"] = _validate_resolution_episode(event.get("resolution_episode"))  # type: ignore[arg-type]
    else:
        normalized["resolution_episode"] = None
    if kind in {"todo_open", "todo_supersede"} and not normalized["title"]:
        raise ValueError(f"{kind} requires title")
    if kind == "progress_note" and not normalized["body"]:
        raise ValueError("progress_note requires body")
    if kind == "todo_supersede":
        predecessor = str(event.get("supersedes_td_id") or "").strip()
        normalized["supersedes_td_id"] = _require_identifier(predecessor, TD_ID_RE, "supersedes_td_id")
    elif event.get("supersedes_td_id") is not None:
        normalized["supersedes_td_id"] = str(event.get("supersedes_td_id"))
    if event.get("successor_td_id") is not None:
        normalized["successor_td_id"] = str(event.get("successor_td_id"))
    if event.get("read_receipt_id") is not None:
        normalized["read_receipt_id"] = str(event.get("read_receipt_id"))
    return normalized


def append_event(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    projection_mode: str = "append_event",
) -> Dict[str, Any]:
    normalized = _validate_event_shape(event)
    paths = ledger_paths(
        repo_root,
        phase_id=str(normalized["phase_id"]),
        family_id=str(normalized["family_id"]),
    )
    raw_path = Path(paths["raw_path"])
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = Path(paths["lock_path"])
    with file_lock(lock_path):
        with raw_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(normalized, ensure_ascii=False) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        if projection_mode in {"append_event", "append_open"}:
            projection_update = write_append_projection(repo_root, event=normalized)
        else:
            projection_update = {
                "projection_results": write_family_projections(
                    repo_root,
                    family_id=str(normalized["family_id"]),
                    include_phase_id=str(normalized["phase_id"]),
                ),
                "deferred_projection_results": [],
            }
    result = {
        "ok": True,
        "event": normalized,
        "projection_mode": projection_mode,
        "projection_results": projection_update["projection_results"],
        "raw_path": str(raw_path.relative_to(repo_root)),
    }
    if projection_update.get("deferred_projection_results"):
        result["deferred_projection_results"] = projection_update["deferred_projection_results"]
    return result


def load_projection(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Any]:
    context = resolve_phase_context(repo_root, phase_id=phase_id, family_id=family_id)
    normalized_phase = context["phase_id"]
    normalized_family = context["family_id"]
    target = ledger_paths(repo_root, phase_id=normalized_phase, family_id=normalized_family)
    index_path = Path(target["index_path"])
    payload = _safe_read_json(index_path)
    if payload:
        return payload
    events = load_events(repo_root, family_id=normalized_family)
    return build_projection(events, phase_id=normalized_phase, family_id=normalized_family)


def load_thread(
    repo_root: Path,
    td_id: str,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Optional[Dict[str, Any]]:
    target_td = _require_identifier(td_id, TD_ID_RE, "td_id")
    events = load_events(repo_root, phase_id=phase_id, family_id=family_id, td_id=target_td)
    projection = build_projection(events, phase_id=phase_id, family_id=family_id)
    return projection.get("threads", {}).get(target_td)


def _limit_rows(items: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    return items[: max(limit, 0)]


def query_recipe(
    repo_root: Path,
    *,
    recipe: str,
    phase_id: str | None = None,
    family_id: str | None = None,
    actor: str | None = None,
    actor_session_id: str | None = None,
    td_id: str | None = None,
    limit: int = 20,
) -> Dict[str, Any]:
    normalized_recipe = str(recipe or "").strip()
    if normalized_recipe not in WORK_LEDGER_QUERY_RECIPES:
        supported = ", ".join(WORK_LEDGER_QUERY_RECIPES)
        raise ValueError(f"unknown recipe '{normalized_recipe}' (supported: {supported})")
    projection = load_projection(repo_root, phase_id=phase_id, family_id=family_id)
    threads = projection.get("threads") if isinstance(projection.get("threads"), Mapping) else {}
    results: List[Dict[str, Any]]
    if normalized_recipe == "open_in_family":
        family_key = _normalize_family_id(
            family_id or projection.get("family_id") or resolve_phase_context(repo_root, phase_id=phase_id).get("family_id")
        )
        results = list((projection.get("open_by_family") or {}).get(family_key, []))
    elif normalized_recipe == "open_for_actor":
        actor_key = str(actor or "").strip()
        if not actor_key:
            raise ValueError("actor is required for open_for_actor")
        results = list((projection.get("open_by_actor") or {}).get(actor_key, []))
    elif normalized_recipe == "closed_this_session":
        session_key = str(actor_session_id or "").strip()
        if not session_key:
            raise ValueError("actor_session_id is required for closed_this_session")
        results = [
            row
            for row in projection.get("recently_closed") or []
            if str(row.get("actor_session_id") or "").strip() == session_key
        ]
    elif normalized_recipe == "supersession_chain":
        target_td = _require_identifier(str(td_id or ""), TD_ID_RE, "td_id")
        thread = threads.get(target_td)
        if thread is None:
            return {
                "schema": "work_ledger_query_v1",
                "generated_at": utc_now(),
                "recipe": normalized_recipe,
                "results": [],
                "matched": 0,
            }
        root_td_id = str(thread.get("root_td_id") or target_td)
        results = [
            chain
            for chain in projection.get("supersession_chains") or []
            if str(chain.get("root_td_id") or "") == root_td_id
        ]
    elif normalized_recipe == "cross_agent_handoffs":
        results = list(projection.get("cross_agent_handoffs") or [])
    elif normalized_recipe == "stale_open":
        results = list(projection.get("stale_open") or [])
    elif normalized_recipe == "work_memory_items":
        results = list(projection.get("work_memory_items") or [])
        if td_id:
            target_td = _require_identifier(str(td_id), TD_ID_RE, "td_id")
            results = [row for row in results if str(row.get("td_id") or "") == target_td]
        if actor:
            actor_key = str(actor).strip()
            results = [row for row in results if str(row.get("actor") or "") == actor_key]
        if actor_session_id:
            session_key = str(actor_session_id).strip()
            results = [row for row in results if str(row.get("actor_session_id") or "") == session_key]
    else:
        target_td = _require_identifier(str(td_id or ""), TD_ID_RE, "td_id")
        thread = threads.get(target_td)
        results = [thread] if thread else []
    return {
        "schema": "work_ledger_query_v1",
        "generated_at": utc_now(),
        "recipe": normalized_recipe,
        "phase_id": projection.get("phase_id"),
        "family_id": projection.get("family_id"),
        "filters": {
            "actor": actor,
            "actor_session_id": actor_session_id,
            "td_id": td_id,
            "limit": limit,
        },
        "matched": len(results),
        "results": _limit_rows(results, limit),
    }


def _current_thread_state(repo_root: Path, td_id: str, *, family_id: str) -> Optional[Dict[str, Any]]:
    return load_thread(repo_root, td_id, family_id=family_id)


def open_thread(
    repo_root: Path,
    *,
    actor: str,
    actor_session_id: str,
    phase_id: str,
    family_id: str,
    title: str,
    body: str | None = None,
    evidence_refs: Optional[List[str]] = None,
    read_receipt_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    task_ledger_work_item_id: str | None = None,
) -> Dict[str, Any]:
    created_at = utc_now()
    event = {
        "event_id": mint_event_id(),
        "td_id": mint_td_id(),
        "event_kind": "todo_open",
        "actor": actor,
        "actor_session_id": actor_session_id,
        "phase_id": phase_id,
        "family_id": family_id,
        "created_at": created_at,
        "valid_at": created_at,
        "invalid_at": None,
        "expired_at": None,
        "title": title,
        "body": body,
        "evidence_refs": evidence_refs or [],
        "read_receipt_id": read_receipt_id,
        "metadata": with_task_ledger_work_item_metadata(metadata, task_ledger_work_item_id),
    }
    return append_event(repo_root, event, projection_mode="append_event")


def progress_thread(
    repo_root: Path,
    *,
    td_id: str,
    actor: str,
    actor_session_id: str,
    phase_id: str,
    family_id: str,
    body: str,
    title: str | None = None,
    evidence_refs: Optional[List[str]] = None,
    read_receipt_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
    task_ledger_work_item_id: str | None = None,
) -> Dict[str, Any]:
    thread = _current_thread_state(repo_root, td_id, family_id=family_id)
    if thread is None:
        raise ValueError(f"thread '{td_id}' not found")
    created_at = utc_now()
    event = {
        "event_id": mint_event_id(),
        "td_id": td_id,
        "event_kind": "progress_note",
        "actor": actor,
        "actor_session_id": actor_session_id,
        "phase_id": phase_id,
        "family_id": family_id,
        "created_at": created_at,
        "valid_at": thread.get("current_valid_at") or created_at,
        "invalid_at": thread.get("invalid_at"),
        "expired_at": None,
        "title": title,
        "body": body,
        "evidence_refs": evidence_refs or [],
        "read_receipt_id": read_receipt_id,
        "metadata": with_task_ledger_work_item_metadata(metadata, task_ledger_work_item_id),
    }
    return append_event(repo_root, event)


def close_thread(
    repo_root: Path,
    *,
    td_id: str,
    actor: str,
    actor_session_id: str,
    phase_id: str,
    family_id: str,
    resolution_episode: Mapping[str, Any],
    body: str | None = None,
    evidence_refs: Optional[List[str]] = None,
    read_receipt_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    thread = _current_thread_state(repo_root, td_id, family_id=family_id)
    if thread is None:
        raise ValueError(f"thread '{td_id}' not found")
    if str(thread.get("status") or "") != "open":
        raise ValueError(f"thread '{td_id}' is not open")
    created_at = utc_now()
    event = {
        "event_id": mint_event_id(),
        "td_id": td_id,
        "event_kind": "todo_close",
        "actor": actor,
        "actor_session_id": actor_session_id,
        "phase_id": phase_id,
        "family_id": family_id,
        "created_at": created_at,
        "valid_at": thread.get("current_valid_at") or created_at,
        "invalid_at": created_at,
        "expired_at": None,
        "title": thread.get("title"),
        "body": body,
        "evidence_refs": evidence_refs or [],
        "resolution_episode": dict(resolution_episode),
        "read_receipt_id": read_receipt_id,
        "metadata": dict(metadata or {}),
    }
    return append_event(repo_root, event)


def reopen_thread(
    repo_root: Path,
    *,
    td_id: str,
    actor: str,
    actor_session_id: str,
    phase_id: str,
    family_id: str,
    body: str | None = None,
    title: str | None = None,
    evidence_refs: Optional[List[str]] = None,
    read_receipt_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    thread = _current_thread_state(repo_root, td_id, family_id=family_id)
    if thread is None:
        raise ValueError(f"thread '{td_id}' not found")
    if str(thread.get("status") or "") == "open":
        raise ValueError(f"thread '{td_id}' is already open")
    created_at = utc_now()
    event = {
        "event_id": mint_event_id(),
        "td_id": td_id,
        "event_kind": "todo_reopen",
        "actor": actor,
        "actor_session_id": actor_session_id,
        "phase_id": phase_id,
        "family_id": family_id,
        "created_at": created_at,
        "valid_at": created_at,
        "invalid_at": None,
        "expired_at": None,
        "title": title or thread.get("title"),
        "body": body,
        "evidence_refs": evidence_refs or [],
        "read_receipt_id": read_receipt_id,
        "metadata": dict(metadata or {}),
    }
    return append_event(repo_root, event)


def supersede_thread(
    repo_root: Path,
    *,
    td_id: str,
    actor: str,
    actor_session_id: str,
    phase_id: str,
    family_id: str,
    title: str,
    resolution_episode: Mapping[str, Any],
    body: str | None = None,
    evidence_refs: Optional[List[str]] = None,
    read_receipt_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    predecessor = _current_thread_state(repo_root, td_id, family_id=family_id)
    if predecessor is None:
        raise ValueError(f"thread '{td_id}' not found")
    if str(predecessor.get("status") or "") != "open":
        raise ValueError(f"thread '{td_id}' is not open")
    created_at = utc_now()
    successor_id = mint_td_id()
    event = {
        "event_id": mint_event_id(),
        "td_id": successor_id,
        "event_kind": "todo_supersede",
        "actor": actor,
        "actor_session_id": actor_session_id,
        "phase_id": phase_id,
        "family_id": family_id,
        "created_at": created_at,
        "valid_at": created_at,
        "invalid_at": None,
        "expired_at": None,
        "title": title,
        "body": body,
        "evidence_refs": evidence_refs or [],
        "resolution_episode": dict(resolution_episode),
        "supersedes_td_id": td_id,
        "read_receipt_id": read_receipt_id,
        "metadata": dict(metadata or {}),
    }
    result = append_event(repo_root, event)
    result["supersedes_td_id"] = td_id
    result["successor_td_id"] = successor_id
    return result


def project_phase(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Any]:
    context = resolve_phase_context(repo_root, phase_id=phase_id, family_id=family_id)
    results = write_family_projections(
        repo_root,
        family_id=context["family_id"],
        include_phase_id=context["phase_id"],
    )
    projection = load_projection(
        repo_root,
        phase_id=context["phase_id"],
        family_id=context["family_id"],
    )
    return {
        "ok": True,
        "phase_id": context["phase_id"],
        "family_id": context["family_id"],
        "projection": projection,
        "projection_results": results,
    }


def _normalize_projection_for_compare(value: Any) -> Any:
    if isinstance(value, Mapping):
        normalized = {
            str(key): _normalize_projection_for_compare(nested)
            for key, nested in value.items()
            if str(key) != "age_seconds"
        }
        return normalized
    if isinstance(value, list):
        return [_normalize_projection_for_compare(item) for item in value]
    return value


def _projection_has_legacy_volatile_fields(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            str(key) == "age_seconds" or _projection_has_legacy_volatile_fields(nested)
            for key, nested in value.items()
        )
    if isinstance(value, list):
        return any(_projection_has_legacy_volatile_fields(item) for item in value)
    return False


def _projection_compare_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(payload)
    normalized["generated_at"] = "<ignored>"
    return _normalize_projection_for_compare(normalized)


def _projection_freshness_row(
    repo_root: Path,
    *,
    phase_id: str,
    family_id: str,
    events: List[Dict[str, Any]],
) -> Dict[str, Any]:
    target = ledger_paths(repo_root, phase_id=phase_id, family_id=family_id)
    index_path = Path(target["index_path"])
    existing = _safe_read_json(index_path)
    expected = build_projection(
        events,
        phase_id=phase_id,
        family_id=family_id,
        generated_at=str(existing.get("generated_at") or "<check>"),
    )
    fresh = bool(existing) and _projection_compare_payload(existing) == _projection_compare_payload(expected)
    reason = "fresh" if fresh else ("missing_projection" if not index_path.exists() else "projection_stale")
    return {
        "phase_id": phase_id,
        "index_path": str(index_path.relative_to(repo_root)),
        "fresh": fresh,
        "exists": index_path.exists(),
        "reason": reason,
        "counts": expected.get("counts"),
    }


def _projection_fanout_diagnostic(
    repo_root: Path,
    *,
    family_id: str,
    projection_results: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    stale_rows = [row for row in projection_results if not bool(row.get("fresh"))]
    if len(stale_rows) < 2:
        return None
    fresh_count = len(projection_results) - len(stale_rows)
    normalized_family = _normalize_family_id(family_id)
    source_paths = []
    for phase_id in _family_projection_targets(
        repo_root,
        normalized_family,
        str(projection_results[-1].get("phase_id") or ""),
    ):
        raw_path = repo_root / WORK_LEDGER_ROOT_REL / phase_id / "work_ledger.jsonl"
        if raw_path.exists():
            source_paths.append(str(raw_path.relative_to(repo_root)))
    return {
        "diagnostic_id": "work_ledger_family_projection_fanout",
        "family_id": normalized_family,
        "stale_projection_count": len(stale_rows),
        "fresh_projection_count": fresh_count,
        "stale_phase_ids": [str(row.get("phase_id")) for row in stale_rows],
        "stale_index_paths": [str(row.get("index_path")) for row in stale_rows],
        "source_authority_paths": source_paths,
        "root_cause": "family_wide_source_authority_reused_by_phase_indexes",
        "why": (
            "One Work Ledger append can update the touched phase index while leaving "
            "older indexes stale because the family projection reads the family-wide "
            "event log across phase buckets."
        ),
        "repair_command": "./repo-python tools/meta/factory/work_ledger.py project --all",
        "check_command": "./repo-python tools/meta/factory/work_ledger.py project --check --all",
        "commit_scope": [str(row.get("index_path")) for row in stale_rows],
    }


def check_family_projections(
    repo_root: Path,
    *,
    family_id: str,
    include_phase_id: str,
) -> List[Dict[str, Any]]:
    normalized_family = _normalize_family_id(family_id)
    events = load_events(repo_root, family_id=normalized_family)
    return [
        _projection_freshness_row(
            repo_root,
            phase_id=bucket_phase,
            family_id=normalized_family,
            events=events,
        )
        for bucket_phase in _family_projection_targets(repo_root, normalized_family, include_phase_id)
    ]


def check_project_phase(
    repo_root: Path,
    *,
    phase_id: str | None = None,
    family_id: str | None = None,
) -> Dict[str, Any]:
    context = resolve_phase_context(repo_root, phase_id=phase_id, family_id=family_id)
    selected_phase_id = context["phase_id"]
    results = check_family_projections(
        repo_root,
        family_id=context["family_id"],
        include_phase_id=selected_phase_id,
    )
    selected_phase_row = next(
        (row for row in results if str(row.get("phase_id")) == selected_phase_id),
        None,
    )
    selected_phase_fresh = bool(selected_phase_row and selected_phase_row.get("fresh"))
    family_projection_fresh = all(row.get("fresh") for row in results)
    payload = {
        "ok": selected_phase_fresh,
        "mode": "check",
        "check_scope": "selected_phase",
        "phase_id": selected_phase_id,
        "family_id": context["family_id"],
        "selected_phase_fresh": selected_phase_fresh,
        "family_projection_fresh": family_projection_fresh,
        "projection_results": results,
    }
    diagnostic = _projection_fanout_diagnostic(
        repo_root,
        family_id=context["family_id"],
        projection_results=results,
    )
    if diagnostic:
        diagnostic["phase_scoped_disposition"] = "advisory"
        diagnostic["phase_scoped_ok"] = selected_phase_fresh
        diagnostic["broad_check_command"] = diagnostic.get("check_command")
        payload["projection_fanout_diagnostics"] = [diagnostic]
    return payload


def project_all(repo_root: Path) -> Dict[str, Any]:
    root = repo_root / WORK_LEDGER_ROOT_REL
    if not root.exists():
        return {"ok": True, "families": []}
    family_ids: set[str] = set()
    for path in _bucket_raw_paths(repo_root):
        for event in read_jsonl(path):
            family_id = str(event.get("family_id") or "").strip()
            if family_id:
                family_ids.add(family_id)
    family_results: List[Dict[str, Any]] = []
    for family_id in sorted(family_ids):
        buckets = _family_phase_buckets(repo_root, family_id)
        include_phase = buckets[-1] if buckets else resolve_active_phase_context(repo_root)["phase_id"]
        family_results.append(
            {
                "family_id": family_id,
                "projection_results": write_family_projections(
                    repo_root,
                    family_id=family_id,
                    include_phase_id=include_phase,
                ),
            }
        )
    return {"ok": True, "families": family_results}


def check_project_all(repo_root: Path) -> Dict[str, Any]:
    root = repo_root / WORK_LEDGER_ROOT_REL
    if not root.exists():
        return {"ok": True, "mode": "check", "families": []}
    family_ids: set[str] = set()
    for path in _bucket_raw_paths(repo_root):
        for event in read_jsonl(path):
            family_id = str(event.get("family_id") or "").strip()
            if family_id:
                family_ids.add(family_id)
    family_results: List[Dict[str, Any]] = []
    fanout_diagnostics: List[Dict[str, Any]] = []
    for family_id in sorted(family_ids):
        buckets = _family_phase_buckets(repo_root, family_id)
        include_phase = buckets[-1] if buckets else resolve_active_phase_context(repo_root)["phase_id"]
        projection_results = check_family_projections(
            repo_root,
            family_id=family_id,
            include_phase_id=include_phase,
        )
        diagnostic = _projection_fanout_diagnostic(
            repo_root,
            family_id=family_id,
            projection_results=projection_results,
        )
        if diagnostic:
            fanout_diagnostics.append(diagnostic)
        family_results.append(
            {
                "family_id": family_id,
                "ok": all(row.get("fresh") for row in projection_results),
                "projection_results": projection_results,
            }
        )
    payload = {
        "ok": all(row.get("ok") for row in family_results),
        "mode": "check",
        "families": family_results,
    }
    if fanout_diagnostics:
        payload["projection_fanout_diagnostics"] = fanout_diagnostics
    return payload
