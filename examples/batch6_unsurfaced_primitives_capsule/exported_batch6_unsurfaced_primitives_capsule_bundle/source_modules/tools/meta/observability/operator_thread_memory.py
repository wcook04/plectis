#!/usr/bin/env python3
"""Private event-sourced memory for Operator ChatGPT tabs.

Operator Thread Memory records observed ChatGPT tab state as append-only
private events, then materializes per-thread JSON projections and a safe
metadata index. The event log is the authority. Thread files and indexes are
runtime read models under ignored ``state/operator_bridge/thread_memory``.

Raw user/assistant text is intentionally confined to this ignored directory
and to explicit CLI output requested by the operator.

Use ``--thread-progress`` for the operator-facing progression lens: it pairs
each operator addition with the assistant response(s), receipt cues, prompt
slots, and response anatomy without requiring a full transcript paste.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
THREAD_MEMORY_ROOT = REPO_ROOT / "state" / "operator_bridge" / "thread_memory"
EVENTS_PATH = THREAD_MEMORY_ROOT / "events.jsonl"
INDEX_PATH = THREAD_MEMORY_ROOT / "index.json"
THREADS_DIR = THREAD_MEMORY_ROOT / "threads"
THREAD_PROGRESS_JSON_PATH = THREAD_MEMORY_ROOT / "thread_progress.json"
THREAD_PROGRESS_MARKDOWN_PATH = THREAD_MEMORY_ROOT / "thread_progress.md"

EVENT_SCHEMA_VERSION = "operator_thread_memory_event_v1"
THREAD_SCHEMA_VERSION = "operator_thread_memory_thread_v1"
INDEX_SCHEMA_VERSION = "operator_thread_memory_index_v1"
BINDINGS_SCHEMA_VERSION = "operator_thread_memory_bindings_v1"
LESSON_CANDIDATES_SCHEMA_VERSION = "operator_thread_memory_lesson_candidates_v1"
LESSON_CANDIDATE_INDEX_SCHEMA_VERSION = "operator_thread_memory_lesson_candidate_index_v1"
CONTINUATION_CARD_SCHEMA_VERSION = "operator_thread_continuation_card_v0"
THREAD_PROGRESS_SCHEMA_VERSION = "operator_thread_progress_v0"
THREAD_PROGRESS_INDEX_SCHEMA_VERSION = "operator_thread_progress_index_v0"
TYPE_B_HANDOFF_PACKET_SCHEMA_VERSION = "operator_thread_type_b_handoff_packet_v0"
TYPE_B_HANDOFF_MARKDOWN_PROFILE = "operator_thread_type_b_handoff_markdown_v0"
TYPE_B_HANDOFF_EXPORT_PROFILE = "operator_approved_external_type_b_handoff_v0"
THREAD_SNAPSHOT_REF_SCHEMA_VERSION = "operator_thread_snapshot_ref_v1"
RETENTION_STATUS_SCHEMA_VERSION = "operator_thread_memory_retention_status_v0"
RETENTION_EVENT_LOG_WATCH_BYTES = 256 * 1024 * 1024

CONVERSATION_ID_RE = re.compile(r"/c/([^/?#]+)")
PROMPT_RECEIVED_RE = re.compile(r"\bprompt_received\s*:\s*([A-Z0-9.:-]+)", re.IGNORECASE)
SLOT_RE = re.compile(r"\b(A0|A2|B1|B2(?:\.[12])?|B3|B4|B5|B6|B7(?:\.1)?)\b", re.IGNORECASE)
WHITESPACE_RE = re.compile(r"\s+")
TIMESTAMP_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}[T ][0-9:.+-Z]+\b")
THOUGHT_RE = re.compile(r"\bthought\s+for\s+\d+\s*(?:s|sec|secs|seconds|m|min|mins|minutes)\b", re.IGNORECASE)
CAP_ID_RE = re.compile(r"\bcap_[a-z0-9_]{8,}\b")
TASK_LEDGER_EVENT_RE = re.compile(r"\bwie_\d{8}T\d{6}Z_[a-f0-9]{8}\b")
MISSION_TRANSACTION_RE = re.compile(r"\bmtx_[a-z0-9_]{16,}\b")
COMMIT_HASH_RE = re.compile(r"\b[0-9a-f]{40}\b")

RAW_EVENT_TYPES = {
    "thread_created",
    "thread_updated",
    "thread_alias_promoted",
}

PRIVATE_PAYLOAD_KEYS = {
    "turns",
    "text",
    "short_title_or_excerpt",
    "private_matches",
    "private_excerpt",
    "evidence_private_excerpt",
    "private_preview",
    "private_title",
}

PROGRESS_RECEIPT_BLOCK_TYPES = (
    "validation_receipt",
    "commit_receipt",
    "workitem_binding_receipt",
    "conversation_control_event",
    "substrate_progress_receipt",
    "type_a_execution_trace",
    "implementation_summary",
    "code_review_diff_projection",
    "ambient_dirty_boundary",
)

TYPE_B_HANDOFF_FORBIDDEN_MARKERS = (
    "private_preview",
    "private_title",
    "raw_turn_text",
    "raw_response_body",
    "raw_user_text",
    "raw_assistant_text",
    "private_payload",
    "SENTINEL_",
    "/" + "Users" + "/willcook",
)

try:
    import operator_turn_stack_projection as turn_projection_mod  # noqa: E402
except Exception:  # noqa: BLE001 - thread memory must still work without semantic projection helpers
    turn_projection_mod = None  # type: ignore[assignment]


def _utc_now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _now_iso() -> str:
    return _utc_now().isoformat(timespec="seconds")


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _safe_id(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_.-]+", "_", value.strip())
    return cleaned[:120] or "unknown"


def _read_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _human_bytes(num: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    value = float(max(num, 0))
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B":
                return f"{int(value)}B"
            return f"{value:.1f}{unit}"
        value /= 1024
    return f"{num}B"


def _safe_stat_size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _safe_mtime_iso(path: Path) -> str | None:
    try:
        return _dt.datetime.fromtimestamp(path.stat().st_mtime, tz=_dt.timezone.utc).isoformat()
    except OSError:
        return None


def _tree_size(path: Path) -> tuple[int, int]:
    if not path.exists():
        return 0, 0
    if path.is_file():
        return _safe_stat_size(path), 1
    total = 0
    count = 0
    for child in path.rglob("*"):
        if not child.is_file():
            continue
        total += _safe_stat_size(child)
        count += 1
    return total, count


def _latest_compaction_receipt(root: Path) -> dict[str, Any] | None:
    receipts = sorted(
        root.glob("compaction_receipt_*.json"),
        key=lambda item: _safe_mtime_iso(item) or "",
        reverse=True,
    )
    for receipt in receipts:
        payload = _read_json(receipt, None)
        if isinstance(payload, dict):
            return {
                "path": _display_path(receipt),
                "schema_version": payload.get("schema_version"),
                "before_bytes": payload.get("before_bytes"),
                "after_bytes": payload.get("after_bytes"),
                "rows_seen": payload.get("rows_seen"),
                "rows_compacted": payload.get("rows_compacted"),
                "snapshot_refs_written": payload.get("snapshot_refs_written"),
                "snapshot_events_bytes": payload.get("snapshot_events_bytes"),
                "net_reclaimed_bytes_after_snapshot_events": payload.get(
                    "net_reclaimed_bytes_after_snapshot_events"
                ),
                "mtime": _safe_mtime_iso(receipt),
            }
    return None


def build_retention_status(root: Path | None = None) -> dict[str, Any]:
    """Return metadata-only retention pressure for private operator thread memory."""
    memory_root = root or THREAD_MEMORY_ROOT
    events_path = memory_root / "events.jsonl"
    snapshot_dir = memory_root / "snapshot_events"
    threads_dir = memory_root / "threads"
    events_bytes = _safe_stat_size(events_path)
    snapshot_bytes, snapshot_file_count = _tree_size(snapshot_dir)
    threads_bytes, thread_file_count = _tree_size(threads_dir)
    index_bytes = _safe_stat_size(memory_root / "index.json")
    progress_bytes = _safe_stat_size(memory_root / "thread_progress.json") + _safe_stat_size(
        memory_root / "thread_progress.md"
    )
    latest_receipt = _latest_compaction_receipt(memory_root)
    if events_bytes >= RETENTION_EVENT_LOG_WATCH_BYTES:
        status = "event_log_growth_watch"
    elif latest_receipt:
        status = "compacted_snapshot_sidecars_present"
    elif events_path.exists():
        status = "active_event_log_no_compaction_receipt"
    else:
        status = "thread_memory_missing_waiting_for_writer"

    return {
        "kind": "operator_thread_memory_retention_status",
        "schema_version": RETENTION_STATUS_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "status": status,
        "owner_surface": "tools/meta/observability/operator_thread_memory.py",
        "privacy_boundary": (
            "Retention status uses filesystem metadata and compaction receipts only; it does not read "
            "thread transcripts or raw event bodies."
        ),
        "event_log": {
            "path": _display_path(events_path),
            "exists": events_path.exists(),
            "bytes": events_bytes,
            "human_size": _human_bytes(events_bytes),
            "mtime": _safe_mtime_iso(events_path),
            "watch_bytes": RETENTION_EVENT_LOG_WATCH_BYTES,
            "watch_human": _human_bytes(RETENTION_EVENT_LOG_WATCH_BYTES),
        },
        "sidecars": {
            "snapshot_events": {
                "path": _display_path(snapshot_dir),
                "exists": snapshot_dir.exists(),
                "bytes": snapshot_bytes,
                "human_size": _human_bytes(snapshot_bytes),
                "file_count": snapshot_file_count,
            },
            "threads": {
                "path": _display_path(threads_dir),
                "exists": threads_dir.exists(),
                "bytes": threads_bytes,
                "human_size": _human_bytes(threads_bytes),
                "file_count": thread_file_count,
            },
            "index_bytes": index_bytes,
            "index_human": _human_bytes(index_bytes),
            "progress_bytes": progress_bytes,
            "progress_human": _human_bytes(progress_bytes),
        },
        "latest_compaction_receipt": latest_receipt,
        "next_actions": {
            "status_command": "./repo-python tools/meta/observability/operator_thread_memory.py --retention-status",
            "privacy_check": "./repo-python tools/meta/observability/operator_thread_memory.py --check",
            "metadata_index": "./repo-python tools/meta/observability/operator_thread_memory.py --index",
            "project_read_models": "./repo-python tools/meta/observability/operator_thread_memory.py --project",
            "storage_doctor_card": "./repo-python -m tools.meta.storage_doctor scan --top 12 --format card",
            "mutation_policy": "Do not delete private thread memory by size; use owner checks and compaction receipts.",
        },
    }


def _append_history(history: list[dict[str, Any]], key: str, value: str, at: str) -> list[dict[str, Any]]:
    if not value:
        return history[-20:]
    for item in history:
        if item.get(key) == value:
            item["last_seen_at"] = at
            item["seen_count"] = int(item.get("seen_count") or 1) + 1
            return history[-20:]
    history.append({key: value, "first_seen_at": at, "last_seen_at": at, "seen_count": 1})
    return history[-20:]


def parse_conversation_id(url: str) -> str | None:
    match = CONVERSATION_ID_RE.search(url or "")
    return match.group(1) if match else None


def thread_id_for_conversation(conversation_id: str) -> str:
    return f"chatgpt_{_safe_id(conversation_id.lower())}"


def provisional_thread_id(target_id: str, transcript_hash: str, at: str) -> str:
    basis = "|".join([target_id or "unknown", transcript_hash or "empty", at])
    return f"provisional_{_sha256(basis)[:16]}"


def _normalize_text(value: str) -> str:
    text = value or ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _normalized_prompt_text(value: str) -> str:
    text = _normalize_text(value).lower()
    text = TIMESTAMP_RE.sub("<timestamp>", text)
    text = THOUGHT_RE.sub("thought for <duration>", text)
    text = WHITESPACE_RE.sub(" ", text)
    return text.strip()


def _safe_excerpt(value: str, limit: int = 240) -> str:
    text = WHITESPACE_RE.sub(" ", _normalize_text(value))
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _turn_text(turn: dict[str, Any]) -> str:
    return _normalize_text(str(turn.get("text") or ""))


def normalize_turns(turns: list[dict[str, Any]] | None, *, seen_at: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, turn in enumerate(turns or []):
        if not isinstance(turn, dict):
            continue
        role = str(turn.get("role") or "").strip().lower()
        if role not in {"user", "assistant", "system", "tool"}:
            role = "unknown"
        text = _turn_text(turn)
        text_sha = _sha256(text)
        out.append({
            "turn_index": index,
            "role": role,
            "message_id": turn.get("message_id"),
            "ordinal": turn.get("ordinal"),
            "text": text,
            "text_sha256": text_sha,
            "text_sha16": text_sha[:16],
            "char_count": len(text),
            "first_seen_at": seen_at,
            "last_seen_at": seen_at,
        })
    return out


def transcript_hash(turns: list[dict[str, Any]]) -> str:
    parts = [f"{turn.get('role')}:{turn.get('text_sha256')}" for turn in turns]
    return _sha256("\n".join(parts))


def transcript_turn_hashes(turns: list[dict[str, Any]]) -> list[str]:
    return [f"{turn.get('role')}:{turn.get('text_sha256')}" for turn in turns]


def transcript_suffix_hash(turn_hashes: list[str], window: int = 6) -> str:
    return _sha256("\n".join(turn_hashes[-window:]))


def _turn_hash_key(turn: dict[str, Any]) -> str:
    return f"{turn.get('role')}:{turn.get('text_sha256')}"


def _turn_identity_key(turn: dict[str, Any]) -> str:
    role = str(turn.get("role") or "").strip().lower()
    message_id = str(turn.get("message_id") or "").strip()
    if message_id:
        return f"{role}:id:{message_id}"
    ordinal = turn.get("ordinal")
    if ordinal is not None:
        return f"{role}:ordinal:{ordinal}"
    turn_index = turn.get("turn_index")
    if turn_index is not None:
        return f"{role}:index:{turn_index}"
    return f"{role}:text:{turn.get('text_sha256')}"


def _contiguous_window_index(haystack: list[str], needle: list[str]) -> int:
    if not needle:
        return 0
    if len(needle) > len(haystack):
        return -1
    last_start = len(haystack) - len(needle)
    for start in range(last_start + 1):
        if haystack[start:start + len(needle)] == needle:
            return start
    return -1


def _suffix_prefix_overlap(left: list[str], right: list[str]) -> int:
    limit = min(len(left), len(right))
    for size in range(limit, 0, -1):
        if left[-size:] == right[:size]:
            return size
    return 0


def _reindex_turns(turns: list[dict[str, Any]], *, now: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for index, turn in enumerate(turns):
        row = dict(turn)
        row["turn_index"] = index
        row.setdefault("first_seen_at", now)
        row["last_seen_at"] = str(row.get("last_seen_at") or now)
        out.append(row)
    return out


def _observed_updates_streaming_tail(
    existing: list[dict[str, Any]],
    observed: list[dict[str, Any]],
) -> bool:
    if len(existing) != len(observed) or not existing:
        return False
    if len(existing) > 1:
        existing_prefix = [_turn_hash_key(turn) for turn in existing[:-1]]
        observed_prefix = [_turn_hash_key(turn) for turn in observed[:-1]]
        if existing_prefix != observed_prefix:
            return False
    old_tail = existing[-1]
    new_tail = observed[-1]
    if str(old_tail.get("role") or "") != str(new_tail.get("role") or ""):
        return False
    old_ordinal = old_tail.get("ordinal")
    new_ordinal = new_tail.get("ordinal")
    same_position = (
        old_ordinal is not None
        and new_ordinal is not None
        and old_ordinal == new_ordinal
    )
    if not same_position and _turn_identity_key(old_tail) != _turn_identity_key(new_tail):
        return False
    return int(new_tail.get("char_count") or 0) >= int(old_tail.get("char_count") or 0)


def _replace_streaming_tail(
    existing: list[dict[str, Any]],
    observed: list[dict[str, Any]],
    *,
    now: str,
) -> list[dict[str, Any]]:
    merged = [dict(turn) for turn in observed]
    old_tail = existing[-1]
    merged[-1]["first_seen_at"] = str(old_tail.get("first_seen_at") or now)
    merged[-1]["last_seen_at"] = now
    return _reindex_turns(merged, now=now)


def merge_observed_turn_window(
    existing_turns: list[dict[str, Any]] | None,
    observed_turns: list[dict[str, Any]] | None,
    *,
    now: str,
) -> tuple[list[dict[str, Any]], str]:
    """Merge a visible ChatGPT DOM window into private thread memory.

    ChatGPT can expose only the visible tail of a long thread. The event log
    should not shrink the thread projection just because the current DOM window
    is shorter than an earlier observation.
    """
    existing = [turn for turn in (existing_turns or []) if isinstance(turn, dict)]
    observed = [turn for turn in (observed_turns or []) if isinstance(turn, dict)]
    if not existing:
        return _reindex_turns(observed, now=now), "observed_initial"
    if not observed:
        return _reindex_turns(existing, now=now), "preserved_existing_empty_observation"

    existing_hashes = [_turn_hash_key(turn) for turn in existing]
    observed_hashes = [_turn_hash_key(turn) for turn in observed]
    if existing_hashes == observed_hashes:
        merged = _reindex_turns(existing, now=now)
        for row in merged:
            row["last_seen_at"] = now
        return merged, "observed_exact"
    if _observed_updates_streaming_tail(existing, observed):
        return _replace_streaming_tail(existing, observed, now=now), "observed_updated_streaming_tail"

    observed_start = _contiguous_window_index(existing_hashes, observed_hashes)
    if observed_start >= 0:
        merged = _reindex_turns(existing, now=now)
        for offset in range(len(observed_hashes)):
            merged[observed_start + offset]["last_seen_at"] = now
        return merged, "observed_window_within_memory"

    existing_start = _contiguous_window_index(observed_hashes, existing_hashes)
    if existing_start >= 0:
        return _reindex_turns(observed, now=now), "observed_fuller_window"

    append_overlap = _suffix_prefix_overlap(existing_hashes, observed_hashes)
    if append_overlap:
        return _reindex_turns(existing + observed[append_overlap:], now=now), "observed_appended_tail"

    prepend_overlap = _suffix_prefix_overlap(observed_hashes, existing_hashes)
    if prepend_overlap:
        return _reindex_turns(observed + existing[prepend_overlap:], now=now), "observed_prepended_head"

    if len(observed) > len(existing):
        return _reindex_turns(observed, now=now), "observed_longer_no_overlap"
    return _reindex_turns(existing, now=now), "preserved_existing_no_overlap"


def _strong_turn_overlap(old_hashes: list[str], new_hashes: list[str]) -> bool:
    if not old_hashes or not new_hashes:
        return False
    if old_hashes == new_hashes:
        return True
    old_set = set(old_hashes)
    new_set = set(new_hashes)
    shared = len(old_set & new_set)
    if shared >= min(3, len(old_set), len(new_set)):
        return True
    if len(old_hashes) >= 2 and new_hashes[: len(old_hashes)] == old_hashes:
        return True
    if len(new_hashes) >= 2 and old_hashes[-len(new_hashes):] == new_hashes:
        return True
    if old_hashes[-2:] == new_hashes[-2:]:
        return True
    return False


def _bindings(bindings: dict[str, Any] | None) -> dict[str, Any]:
    data = bindings if isinstance(bindings, dict) else {}
    data.setdefault("schema_version", BINDINGS_SCHEMA_VERSION)
    data.setdefault("tabs", {})
    data.setdefault("aliases", {})
    data.setdefault("vanish_candidates", {})
    return data


def _thread_path(thread_id: str) -> Path:
    return THREADS_DIR / f"{_safe_id(thread_id)}.json"


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def load_thread(thread_id: str) -> dict[str, Any] | None:
    data = _read_json(_thread_path(thread_id), None)
    return data if isinstance(data, dict) else None


def save_thread(record: dict[str, Any]) -> None:
    _write_json(_thread_path(str(record.get("thread_id") or "unknown")), record)


def load_thread_index() -> dict[str, Any]:
    data = _read_json(INDEX_PATH, {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("schema_version", INDEX_SCHEMA_VERSION)
    data.setdefault("threads", [])
    return data


def append_event(event: dict[str, Any], *, events_path: Path | None = None) -> dict[str, Any]:
    """Append one private event as JSON Lines and return the persisted row."""
    at = str(event.get("observed_at") or event.get("created_at") or _now_iso())
    payload = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "created_at": at,
        **event,
    }
    basis = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    payload.setdefault("event_id", f"otm_{at.replace(':', '').replace('+', 'Z')}_{_sha256(basis)[:12]}")
    events_path = events_path or EVENTS_PATH
    events_path.parent.mkdir(parents=True, exist_ok=True)
    with events_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")
    return payload


def read_events(*, events_path: Path | None = None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    events_path = events_path or EVENTS_PATH
    try:
        with events_path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(row, dict):
                    rows.append(row)
    except OSError:
        return []
    return rows


def classify_prompt(text: str) -> dict[str, Any]:
    normalized = _normalized_prompt_text(text)
    labels: list[str] = []
    slots: list[str] = []

    if normalized == "continue":
        labels.append("continue_exact")
    if "continue" in normalized or "prompt_received: b2" in normalized:
        labels.append("continue")
    if "instantiate" in normalized or "starting cold" in normalized or "prompt_received: b1" in normalized:
        labels.append("instantiate")
    if "compact" in normalized or "compaction" in normalized or "packets" in normalized and "restartable" in normalized:
        labels.append("compact")
    if "deliverable_type" in normalized or "authority_boundary" in normalized or "integration_target" in normalized:
        labels.append("type_b_packet_like")
    if "type a" in normalized and "type b" in normalized:
        labels.append("type_a_type_b_axis")
    if "copied" in normalized or "show less" in normalized or "thought for <duration>" in normalized:
        labels.append("chatgpt_transcript_artifact")
    if "prompt_received" in normalized:
        labels.append("prompt_received_marker")
    if "research" in normalized or "citations" in normalized or "public evidence" in normalized:
        labels.append("research")

    prompt_received = PROMPT_RECEIVED_RE.search(text or "")
    if prompt_received:
        slots.append(prompt_received.group(1).upper())
    for slot in SLOT_RE.findall(text or ""):
        upper = slot.upper()
        if upper not in slots:
            slots.append(upper)

    if slots:
        labels.append("prompt_shelf_slot")

    ordered_labels = sorted(set(labels))
    exact_hash = _sha256(_normalize_text(text))
    normalized_hash = _sha256(normalized)
    if ordered_labels:
        structural_basis = "|".join(ordered_labels + slots[:4])
    else:
        tokens = normalized.split()
        structural_basis = " ".join(tokens[:24] + tokens[-16:])
    structural_hash = _sha256(structural_basis)
    return {
        "pattern_labels": ordered_labels,
        "slots": slots,
        "exact_hash": exact_hash,
        "exact_sha16": exact_hash[:16],
        "normalized_hash": normalized_hash,
        "normalized_sha16": normalized_hash[:16],
        "structural_hash": structural_hash,
        "structural_sha16": structural_hash[:16],
        "structural_basis": structural_basis,
    }


def build_thread_prompt_catalog(
    turns: list[dict[str, Any]],
    *,
    include_private_excerpts: bool = True,
    existing_index: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    prompts: list[dict[str, Any]] = []
    exact_counts: dict[str, int] = {}
    normalized_counts: dict[str, int] = {}
    structural_counts: dict[str, int] = {}
    for turn in turns:
        if turn.get("role") != "user":
            continue
        prompt = classify_prompt(str(turn.get("text") or ""))
        exact_counts[prompt["exact_hash"]] = exact_counts.get(prompt["exact_hash"], 0) + 1
        normalized_counts[prompt["normalized_hash"]] = normalized_counts.get(prompt["normalized_hash"], 0) + 1
        structural_counts[prompt["structural_hash"]] = structural_counts.get(prompt["structural_hash"], 0) + 1

    global_sources = _prompt_repeat_sources(existing_index)
    seen_exact: dict[str, int] = {}
    seen_normalized: dict[str, int] = {}
    seen_structural: dict[str, int] = {}
    for turn in turns:
        if turn.get("role") != "user":
            continue
        text = str(turn.get("text") or "")
        prompt = classify_prompt(text)
        exact_hash = prompt["exact_hash"]
        normalized_hash = prompt["normalized_hash"]
        structural_hash = prompt["structural_hash"]
        seen_exact[exact_hash] = seen_exact.get(exact_hash, 0) + 1
        seen_normalized[normalized_hash] = seen_normalized.get(normalized_hash, 0) + 1
        seen_structural[structural_hash] = seen_structural.get(structural_hash, 0) + 1
        repeat_levels = []
        if exact_counts.get(exact_hash, 0) > 1 or global_sources.get(("exact", exact_hash)):
            repeat_levels.append("exact_repeat")
        if normalized_counts.get(normalized_hash, 0) > 1 or global_sources.get(("normalized", normalized_hash)):
            repeat_levels.append("normalized_repeat")
        if structural_counts.get(structural_hash, 0) > 1 or global_sources.get(("structural", structural_hash)):
            repeat_levels.append("structural_repeat")
        row = {
            "prompt_id": f"prompt_{int(turn.get('turn_index') or 0):04d}_{prompt['exact_sha16']}",
            "turn_index": turn.get("turn_index"),
            "first_seen_at": turn.get("first_seen_at"),
            "last_seen_at": turn.get("last_seen_at"),
            "char_count": len(text),
            "hash": exact_hash,
            "sha16": prompt["exact_sha16"],
            "normalized_sha16": prompt["normalized_sha16"],
            "structural_sha16": prompt["structural_sha16"],
            "pattern_labels": prompt["pattern_labels"],
            "slots": prompt["slots"],
            "repeat_levels": repeat_levels,
            "repeat_count_thread": exact_counts.get(exact_hash, 0),
            "repeat_sources": _repeat_sources_for_prompt(prompt, global_sources),
        }
        if include_private_excerpts:
            row["short_title_or_excerpt"] = _safe_excerpt(text)
        prompts.append(row)
    return prompts


def _prompt_repeat_sources(index: dict[str, Any] | None) -> dict[tuple[str, str], list[str]]:
    sources: dict[tuple[str, str], list[str]] = {}
    for thread in ((index or {}).get("threads") or []):
        if not isinstance(thread, dict):
            continue
        thread_id = str(thread.get("thread_id") or "")
        for prompt in thread.get("thread_prompt_catalog") or []:
            if not isinstance(prompt, dict):
                continue
            if prompt.get("hash"):
                sources.setdefault(("exact", str(prompt["hash"])), []).append(thread_id)
            if prompt.get("normalized_hash"):
                sources.setdefault(("normalized", str(prompt["normalized_hash"])), []).append(thread_id)
            if prompt.get("structural_hash"):
                sources.setdefault(("structural", str(prompt["structural_hash"])), []).append(thread_id)
    return sources


def _repeat_sources_for_prompt(prompt: dict[str, Any], sources: dict[tuple[str, str], list[str]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level, key in (
        ("exact_repeat", "exact_hash"),
        ("normalized_repeat", "normalized_hash"),
        ("structural_repeat", "structural_hash"),
    ):
        thread_ids = sorted(set(sources.get((level.split("_", 1)[0], str(prompt.get(key) or "")), [])))
        if thread_ids:
            rows.append({"level": level, "thread_ids": thread_ids[:8], "count": len(thread_ids)})
    return rows


def classify_thread(record: dict[str, Any], hud_payload: dict[str, Any] | None = None) -> list[str]:
    prompt_labels = {
        label
        for prompt in record.get("thread_prompt_catalog") or []
        for label in (prompt.get("pattern_labels") or [])
    }
    hud_payload = hud_payload or {}
    title = " ".join([
        str(record.get("title") or ""),
        str(hud_payload.get("thread_label") or ""),
        str(hud_payload.get("operator_prompt_label") or ""),
    ]).lower()
    labels: list[str] = []
    if "compact" in prompt_labels or "compact" in title or "compaction" in title:
        labels.append("compaction_sidecar")
    if "type_b_packet_like" in prompt_labels or "type_a_type_b_axis" in prompt_labels:
        labels.append("type_b_packet_thread")
    if "prompt_shelf_slot" in prompt_labels or hud_payload.get("matched_slot") or hud_payload.get("packet_slot"):
        labels.append("prompt_shelf_capture_thread")
    if "research" in prompt_labels or "research" in title:
        labels.append("research_thread")
    try:
        tab_order = int(hud_payload.get("tab_order") or 0)
    except (TypeError, ValueError):
        tab_order = 0
    if (
        ("continue" in prompt_labels or "instantiate" in prompt_labels or "type_b_packet_like" in prompt_labels)
        and (tab_order <= 2 or "main" in title or "shuttle" in title)
    ):
        labels.append("main_shuttle_thread")
    if not labels and record.get("user_turn_count"):
        labels.append("manual_chat")
    if not labels:
        labels.append("unknown")
    return sorted(set(labels))


def _record_base(thread_id: str, *, now: str) -> dict[str, Any]:
    return {
        "schema_version": THREAD_SCHEMA_VERSION,
        "projection_authority": "events.jsonl",
        "thread_id": thread_id,
        "conversation_id": None,
        "provisional_ids": [],
        "aliases": [],
        "tab_target_ids_seen": [],
        "url_history": [],
        "title_history": [],
        "first_seen_at": now,
        "last_seen_at": now,
        "last_nonempty_seen_at": None,
        "status": "active",
        "labels": ["unknown"],
        "turns": [],
        "thread_prompt_catalog": [],
        "turn_stack_catalog": [],
        "response_skeleton_catalog": [],
        "thread_semantic_summary": {},
        "content_hashes": {},
        "turn_count": 0,
        "user_turn_count": 0,
        "assistant_turn_count": 0,
        "char_counts": {"total": 0, "user": 0, "assistant": 0},
        "classification": {},
        "vanish_recovery_state": "nonempty_observed",
        "thread_memory_merge_state": "observed_initial",
        "latest_observed_window": {},
        "source_observer_version": None,
    }


def _build_semantic_turn_projections(turns: list[dict[str, Any]]) -> dict[str, Any]:
    if turn_projection_mod is None:
        return {
            "turn_stack_catalog": [],
            "response_skeleton_catalog": [],
            "thread_semantic_summary": {
                "schema_version": "operator_thread_semantic_summary_unavailable_v0",
                "payload_policy": "metadata_only",
                "raw_text_stored": False,
                "turn_count": len(turns or []),
                "turn_stack_count": 0,
                "response_skeleton_count": 0,
                "projection_status": "unavailable",
            },
        }
    return turn_projection_mod.build_thread_turn_projections(
        turns,
        include_private_previews=True,
    )


def _metadata_thread_semantic_summary(record: dict[str, Any]) -> dict[str, Any]:
    summary = record.get("thread_semantic_summary")
    if not isinstance(summary, dict):
        summary = {}
    return {
        "schema_version": summary.get("schema_version"),
        "payload_policy": "metadata_only",
        "raw_text_stored": False,
        "turn_count": summary.get("turn_count") or 0,
        "turn_stack_count": summary.get("turn_stack_count") or 0,
        "response_skeleton_count": summary.get("response_skeleton_count") or 0,
        "block_type_counts": summary.get("block_type_counts") or {},
        "slot_counts": summary.get("slot_counts") or {},
        "response_decision_anatomy_counts": summary.get("response_decision_anatomy_counts") or {},
    }


def _metadata_top_terms(record: dict[str, Any], *, limit: int = 12) -> list[dict[str, Any]]:
    summary = record.get("thread_semantic_summary")
    if not isinstance(summary, dict):
        return []
    terms: list[dict[str, Any]] = []
    for row in summary.get("assistant_top_terms") or []:
        if not isinstance(row, dict):
            continue
        terms.append({
            "term": row.get("term"),
            "score": row.get("score"),
            "count": row.get("count"),
            "df": row.get("df"),
            "cf": row.get("cf"),
            "source": row.get("source"),
        })
        if len(terms) >= limit:
            break
    return terms


def _compact_turn_stack_item(item: dict[str, Any]) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    for block in item.get("blocks") or []:
        if not isinstance(block, dict):
            continue
        row = {
            "block_type": block.get("block_type"),
            "label": block.get("label"),
            "slot": block.get("slot"),
            "line_start": block.get("line_start"),
            "line_end": block.get("line_end"),
            "char_count": block.get("char_count"),
            "sha16": block.get("sha16"),
            "source": block.get("source"),
            "nested_projection": bool(block.get("nested_projection")),
        }
        blocks.append({key: value for key, value in row.items() if value not in (None, False)})
    return {
        "turn_index": item.get("turn_index"),
        "text_sha16": item.get("text_sha16"),
        "char_count": item.get("char_count"),
        "block_count": item.get("block_count"),
        "block_type_counts": item.get("block_type_counts") or {},
        "slot_counts": item.get("slot_counts") or {},
        "blocks": blocks,
    }


def _compact_response_skeleton_item(item: dict[str, Any]) -> dict[str, Any]:
    anatomy = item.get("decision_anatomy") if isinstance(item.get("decision_anatomy"), dict) else {}
    true_anatomy = sorted(str(key) for key, enabled in anatomy.items() if enabled)
    return {
        "turn_index": item.get("turn_index"),
        "text_sha16": item.get("text_sha16"),
        "char_count": item.get("char_count"),
        "heading_count": item.get("heading_count") or 0,
        "question_axis_count": item.get("question_axis_count") or 0,
        "path_ref_count": item.get("path_ref_count") or 0,
        "command_ref_count": item.get("command_ref_count") or 0,
        "decision_anatomy_true": true_anatomy,
    }


def _unique_sorted_limited(values: list[str], *, limit: int = 12) -> list[str]:
    return sorted({value for value in values if value})[:limit]


def _safe_reference_ids(record: dict[str, Any]) -> dict[str, list[str]]:
    texts = [
        str(turn.get("text") or "")
        for turn in (record.get("turns") or [])
        if isinstance(turn, dict)
    ]
    joined = "\n".join(texts)
    return {
        "cap_ids": _unique_sorted_limited(CAP_ID_RE.findall(joined)),
        "task_ledger_event_ids": _unique_sorted_limited(TASK_LEDGER_EVENT_RE.findall(joined)),
        "transaction_ids": _unique_sorted_limited(MISSION_TRANSACTION_RE.findall(joined)),
        "commit_hashes": _unique_sorted_limited(COMMIT_HASH_RE.findall(joined)),
    }


def build_thread_continuation_card(thread_id: str, *, recent_limit: int = 5) -> dict[str, Any]:
    record = load_thread(thread_id)
    if not record:
        return {
            "schema_version": CONTINUATION_CARD_SCHEMA_VERSION,
            "thread_id": thread_id,
            "status": "missing",
            "payload_policy": "metadata_only",
            "raw_text_stored": False,
            "mutation_allowed": False,
        }
    turn_stacks = [
        item for item in (record.get("turn_stack_catalog") or [])
        if isinstance(item, dict)
    ]
    response_skeletons = [
        item for item in (record.get("response_skeleton_catalog") or [])
        if isinstance(item, dict)
    ]
    recent_turn_stacks = sorted(
        turn_stacks,
        key=lambda item: int(item.get("turn_index") or 0),
    )[-recent_limit:]
    recent_responses = sorted(
        response_skeletons,
        key=lambda item: int(item.get("turn_index") or 0),
    )[-recent_limit:]
    block_counts = _metadata_thread_semantic_summary(record).get("block_type_counts") or {}
    receipt_types = [
        block_type for block_type in (
            "validation_receipt",
            "commit_receipt",
            "workitem_binding_receipt",
            "conversation_control_event",
            "substrate_progress_receipt",
            "code_review_diff_projection",
            "ambient_dirty_boundary",
        )
        if int(block_counts.get(block_type) or 0) > 0
    ]
    return {
        "schema_version": CONTINUATION_CARD_SCHEMA_VERSION,
        "thread_id": record.get("thread_id"),
        "conversation_id": record.get("conversation_id"),
        "status": record.get("status") or "unknown",
        "labels": record.get("labels") or [],
        "payload_policy": "metadata_only",
        "raw_text_stored": False,
        "explicit_private_material_included": False,
        "mutation_allowed": False,
        "thread_path": _display_path(_thread_path(str(record.get("thread_id") or thread_id))),
        "turn_count": record.get("turn_count") or 0,
        "user_turn_count": record.get("user_turn_count") or 0,
        "assistant_turn_count": record.get("assistant_turn_count") or 0,
        "content_hashes": {
            "transcript_sha16": (record.get("content_hashes") or {}).get("transcript_sha16"),
            "suffix_sha16": (record.get("content_hashes") or {}).get("suffix_sha16"),
        },
        "thread_semantic_summary": _metadata_thread_semantic_summary(record),
        "assistant_top_terms": _metadata_top_terms(record),
        "detected_receipt_types": receipt_types,
        "safe_reference_ids": _safe_reference_ids(record),
        "recent_turn_stacks": [_compact_turn_stack_item(item) for item in recent_turn_stacks],
        "recent_response_skeletons": [_compact_response_skeleton_item(item) for item in recent_responses],
        "continuation_use": {
            "can_continue_without_raw_transcript": True,
            "primary_use": "inspect recent semantic block structure, response decision anatomy, and receipt ownership signals",
            "raw_transcript_drilldown": "--turn-projection --include-private-previews",
        },
    }


def _turn_index_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _turn_rows_by_index(rows: list[dict[str, Any]] | None) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        turn_index = _turn_index_int(row.get("turn_index"))
        if turn_index is None:
            continue
        indexed[turn_index] = row
    return indexed


def _compact_progress_block(block: dict[str, Any], *, include_private_previews: bool) -> dict[str, Any]:
    row = {
        "block_type": block.get("block_type"),
        "label": block.get("label"),
        "slot": block.get("slot"),
        "char_count": block.get("char_count"),
        "line_start": block.get("line_start"),
        "line_end": block.get("line_end"),
        "sha16": block.get("sha16"),
        "source": block.get("source"),
        "nested_projection": bool(block.get("nested_projection")),
    }
    if include_private_previews and block.get("private_preview"):
        row["private_preview"] = block.get("private_preview")
    return {key: value for key, value in row.items() if value not in (None, False, [], {})}


def _truthy_decision_anatomy(skeleton: dict[str, Any]) -> list[str]:
    anatomy = skeleton.get("decision_anatomy") if isinstance(skeleton.get("decision_anatomy"), dict) else {}
    return sorted(str(key) for key, enabled in anatomy.items() if enabled)


def _compact_contract_fields(skeleton: dict[str, Any]) -> dict[str, Any]:
    fields = skeleton.get("contract_fields") if isinstance(skeleton.get("contract_fields"), dict) else {}
    keep = ("deliverable_type", "depth_floor", "authority_boundary", "integration_target")
    return {key: fields.get(key) for key in keep if fields.get(key)}


def _operator_progress_row(
    turn: dict[str, Any],
    *,
    prompt: dict[str, Any] | None,
    turn_stack: dict[str, Any] | None,
    include_private_previews: bool,
) -> dict[str, Any]:
    prompt = prompt or {}
    turn_stack = turn_stack or {}
    blocks = [block for block in (turn_stack.get("blocks") or []) if isinstance(block, dict)]
    live_blocks = [block for block in blocks if block.get("block_type") == "operator_live_addendum"]
    block_types = {
        str(block_type): int(count or 0)
        for block_type, count in (turn_stack.get("block_type_counts") or {}).items()
    }
    receipt_cues = [
        block_type for block_type in PROGRESS_RECEIPT_BLOCK_TYPES
        if int(block_types.get(block_type) or 0) > 0
    ]
    row = {
        "turn_index": turn.get("turn_index"),
        "text_sha16": turn.get("text_sha16"),
        "char_count": turn.get("char_count") or 0,
        "first_seen_at": turn.get("first_seen_at"),
        "last_seen_at": turn.get("last_seen_at"),
        "prompt_id": prompt.get("prompt_id"),
        "prompt_sha16": prompt.get("sha16"),
        "slots": prompt.get("slots") or sorted((turn_stack.get("slot_counts") or {}).keys()),
        "pattern_labels": prompt.get("pattern_labels") or [],
        "repeat_levels": prompt.get("repeat_levels") or [],
        "block_type_counts": block_types,
        "slot_counts": turn_stack.get("slot_counts") or {},
        "operator_live_addendum": {
            "detected": bool(live_blocks),
            "count": len(live_blocks),
            "blocks": [
                _compact_progress_block(block, include_private_previews=include_private_previews)
                for block in live_blocks
            ],
        },
        "receipt_cues": receipt_cues,
    }
    if include_private_previews:
        row["private_preview"] = _safe_excerpt(str(turn.get("text") or ""), limit=360)
        if prompt.get("short_title_or_excerpt"):
            row["private_prompt_excerpt"] = prompt.get("short_title_or_excerpt")
    return {key: value for key, value in row.items() if value not in (None, [], {})}


def _assistant_progress_row(
    turn: dict[str, Any],
    *,
    skeleton: dict[str, Any] | None,
    include_private_previews: bool,
) -> dict[str, Any]:
    skeleton = skeleton or {}
    anatomy = _truthy_decision_anatomy(skeleton)
    row = {
        "turn_index": turn.get("turn_index"),
        "text_sha16": turn.get("text_sha16"),
        "char_count": turn.get("char_count") or 0,
        "first_seen_at": turn.get("first_seen_at"),
        "last_seen_at": turn.get("last_seen_at"),
        "decision_anatomy_true": anatomy,
        "contract_fields": _compact_contract_fields(skeleton),
        "heading_count": skeleton.get("heading_count") or 0,
        "path_ref_count": skeleton.get("path_ref_count") or 0,
        "command_ref_count": skeleton.get("command_ref_count") or 0,
        "question_axis_count": skeleton.get("question_axis_count") or 0,
    }
    if include_private_previews:
        row["private_preview"] = _safe_excerpt(str(turn.get("text") or ""), limit=360)
    return {key: value for key, value in row.items() if value not in (None, [], {})}


def _progress_cues(operator_row: dict[str, Any], assistant_rows: list[dict[str, Any]]) -> list[str]:
    cues: set[str] = set()
    if (operator_row.get("operator_live_addendum") or {}).get("detected"):
        cues.add("operator_live_addendum_detected")
    for slot in operator_row.get("slots") or []:
        cues.add(f"slot:{slot}")
    for receipt in operator_row.get("receipt_cues") or []:
        cues.add(f"receipt:{receipt}")
    for label in operator_row.get("pattern_labels") or []:
        if label in {"continue", "compact", "instantiate", "research", "type_b_packet_like"}:
            cues.add(f"prompt:{label}")
    for row in assistant_rows:
        for anatomy in row.get("decision_anatomy_true") or []:
            cues.add(f"response:{anatomy}")
        if row.get("contract_fields"):
            cues.add("response:contract_fields")
    return sorted(cues)


def build_thread_progress(
    thread_id: str,
    *,
    recent_limit: int = 0,
    include_private_previews: bool = False,
) -> dict[str, Any]:
    """Build a per-thread operator/assistant progression lens.

    The thread record remains the raw private authority. This projection pairs
    each operator/user turn with assistant responses until the next user turn,
    exposing enough structure to see how a tab progressed without re-opening the
    full transcript. Private snippets are opt-in and intended for local operator
    inspection only.
    """
    record = load_thread(thread_id)
    if not record:
        return {
            "schema_version": THREAD_PROGRESS_SCHEMA_VERSION,
            "thread_id": thread_id,
            "status": "missing",
            "payload_policy": "metadata_only",
            "raw_text_stored": False,
            "mutation_allowed": False,
        }

    turns = [turn for turn in (record.get("turns") or []) if isinstance(turn, dict)]
    prompt_by_turn = _turn_rows_by_index(record.get("thread_prompt_catalog") or [])
    stack_by_turn = _turn_rows_by_index(record.get("turn_stack_catalog") or [])
    skeleton_by_turn = _turn_rows_by_index(record.get("response_skeleton_catalog") or [])
    user_positions = [
        (position, turn)
        for position, turn in enumerate(turns)
        if str(turn.get("role") or "") == "user"
    ]
    selected_positions = user_positions[-recent_limit:] if recent_limit and recent_limit > 0 else user_positions
    timeline: list[dict[str, Any]] = []
    for sequence, (position, user_turn) in enumerate(user_positions, start=1):
        if (position, user_turn) not in selected_positions:
            continue
        user_turn_index = _turn_index_int(user_turn.get("turn_index"))
        assistant_turns: list[dict[str, Any]] = []
        for following in turns[position + 1:]:
            role = str(following.get("role") or "")
            if role == "user":
                break
            if role == "assistant":
                assistant_turns.append(following)
        operator_row = _operator_progress_row(
            user_turn,
            prompt=prompt_by_turn.get(user_turn_index if user_turn_index is not None else -1),
            turn_stack=stack_by_turn.get(user_turn_index if user_turn_index is not None else -1),
            include_private_previews=include_private_previews,
        )
        assistant_rows: list[dict[str, Any]] = []
        for assistant_turn in assistant_turns:
            assistant_index = _turn_index_int(assistant_turn.get("turn_index"))
            assistant_rows.append(_assistant_progress_row(
                assistant_turn,
                skeleton=skeleton_by_turn.get(assistant_index if assistant_index is not None else -1),
                include_private_previews=include_private_previews,
            ))
        timeline.append({
            "step_number": sequence,
            "operator_turn_index": user_turn.get("turn_index"),
            "assistant_turn_indexes": [
                row.get("turn_index") for row in assistant_rows if row.get("turn_index") is not None
            ],
            "observed_at": user_turn.get("last_seen_at") or user_turn.get("first_seen_at"),
            "operator_addition": operator_row,
            "assistant_responses": assistant_rows,
            "progress_cues": _progress_cues(operator_row, assistant_rows),
        })

    return {
        "schema_version": THREAD_PROGRESS_SCHEMA_VERSION,
        "thread_id": record.get("thread_id") or thread_id,
        "conversation_id": record.get("conversation_id"),
        "status": record.get("status") or "unknown",
        "labels": record.get("labels") or [],
        "payload_policy": "explicit_private_preview" if include_private_previews else "metadata_only",
        "raw_text_stored": False,
        "private_preview_included": bool(include_private_previews),
        "mutation_allowed": False,
        "thread_path": _display_path(_thread_path(str(record.get("thread_id") or thread_id))),
        "first_seen_at": record.get("first_seen_at"),
        "last_seen_at": record.get("last_seen_at"),
        "last_nonempty_seen_at": record.get("last_nonempty_seen_at"),
        "turn_count": record.get("turn_count") or 0,
        "user_turn_count": record.get("user_turn_count") or 0,
        "assistant_turn_count": record.get("assistant_turn_count") or 0,
        "content_hashes": {
            "transcript_sha16": (record.get("content_hashes") or {}).get("transcript_sha16"),
            "suffix_sha16": (record.get("content_hashes") or {}).get("suffix_sha16"),
        },
        "thread_semantic_summary": _metadata_thread_semantic_summary(record),
        "safe_reference_ids": _safe_reference_ids(record),
        "progression": timeline,
        "progression_count": len(timeline),
        "continuation_card_command": (
            "./repo-python tools/meta/observability/operator_thread_memory.py "
            f"--continuation-card --thread {record.get('thread_id') or thread_id}"
        ),
        "private_drilldown_command": (
            "./repo-python tools/meta/observability/operator_thread_memory.py "
            f"--thread-progress --thread {record.get('thread_id') or thread_id} "
            "--include-private-previews"
        ),
    }


def build_thread_progress_index(
    *,
    limit: int = 20,
    recent_limit: int = 3,
    thread_ids: list[str] | None = None,
    include_private_previews: bool = False,
) -> dict[str, Any]:
    records = _all_thread_records()
    requested = {thread_id for thread_id in (thread_ids or []) if thread_id}
    if requested:
        records = [
            record for record in records
            if str(record.get("thread_id") or "") in requested
        ]
    records = sorted(
        records,
        key=lambda record: str(record.get("last_nonempty_seen_at") or record.get("last_seen_at") or ""),
        reverse=True,
    )
    if limit and limit > 0:
        records = records[:limit]
    threads = [
        build_thread_progress(
            str(record.get("thread_id") or ""),
            recent_limit=recent_limit,
            include_private_previews=include_private_previews,
        )
        for record in records
        if record.get("thread_id")
    ]
    return {
        "schema_version": THREAD_PROGRESS_INDEX_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "source_root": _display_path(THREAD_MEMORY_ROOT),
        "projection_authority": "events.jsonl",
        "payload_policy": "explicit_private_preview" if include_private_previews else "metadata_only",
        "raw_text_stored": False,
        "private_preview_included": bool(include_private_previews),
        "thread_count": len(threads),
        "recent_limit_per_thread": recent_limit,
        "threads": threads,
        "commands": {
            "metadata_index": "./repo-python tools/meta/observability/operator_thread_memory.py --thread-progress --progress-format markdown",
            "private_thread_drilldown": "./repo-python tools/meta/observability/operator_thread_memory.py --thread-progress --thread <thread_id> --include-private-previews",
            "refresh_authority": "./repo-python tools/meta/observability/operator_thread_memory.py --project",
        },
    }


def _md_join(values: list[Any] | tuple[Any, ...] | None) -> str:
    normalized = [str(value) for value in (values or []) if value not in (None, "")]
    return ", ".join(f"`{value}`" for value in normalized) if normalized else "`none`"


def _render_progress_thread_markdown(payload: dict[str, Any], *, heading_level: int = 1) -> list[str]:
    h = "#" * max(1, heading_level)
    lines = [
        f"{h} Thread {payload.get('thread_id')}",
        "",
        f"- conversation_id: `{payload.get('conversation_id')}`",
        f"- status: `{payload.get('status')}`",
        f"- labels: {_md_join(payload.get('labels') or [])}",
        f"- turns: `{payload.get('turn_count')}` total / `{payload.get('user_turn_count')}` operator / `{payload.get('assistant_turn_count')}` assistant",
        f"- payload_policy: `{payload.get('payload_policy')}`",
        f"- last_seen_at: `{payload.get('last_seen_at')}`",
        f"- continuation_card: `{payload.get('continuation_card_command')}`",
        "",
    ]
    for step in payload.get("progression") or []:
        if not isinstance(step, dict):
            continue
        operator_row = step.get("operator_addition") if isinstance(step.get("operator_addition"), dict) else {}
        live = operator_row.get("operator_live_addendum") if isinstance(operator_row.get("operator_live_addendum"), dict) else {}
        lines.extend([
            f"{h}# Step {step.get('step_number')} - operator turn {step.get('operator_turn_index')}",
            "",
            f"- observed_at: `{step.get('observed_at')}`",
            f"- assistant_turns: {_md_join(step.get('assistant_turn_indexes') or [])}",
            f"- slots: {_md_join(operator_row.get('slots') or [])}",
            f"- prompt_labels: {_md_join(operator_row.get('pattern_labels') or [])}",
            f"- operator_chars: `{operator_row.get('char_count')}`; live_addendum: `{bool(live.get('detected'))}`; receipt_cues: {_md_join(operator_row.get('receipt_cues') or [])}",
            f"- block_type_counts: `{json.dumps(operator_row.get('block_type_counts') or {}, sort_keys=True)}`",
            f"- progress_cues: {_md_join(step.get('progress_cues') or [])}",
        ])
        if operator_row.get("private_preview"):
            lines.append(f"- operator_private_preview: {operator_row.get('private_preview')}")
        for block in live.get("blocks") or []:
            if isinstance(block, dict) and block.get("private_preview"):
                lines.append(f"- live_addendum_preview: {block.get('private_preview')}")
        responses = [row for row in (step.get("assistant_responses") or []) if isinstance(row, dict)]
        if responses:
            lines.append("- assistant_responses:")
            for response in responses:
                lines.append(
                    f"  - turn `{response.get('turn_index')}` chars `{response.get('char_count')}` "
                    f"anatomy {_md_join(response.get('decision_anatomy_true') or [])} "
                    f"contract `{json.dumps(response.get('contract_fields') or {}, sort_keys=True)}`"
                )
                if response.get("private_preview"):
                    lines.append(f"    preview: {response.get('private_preview')}")
        lines.append("")
    return lines


def render_thread_progress_markdown(payload: dict[str, Any]) -> str:
    if payload.get("schema_version") == THREAD_PROGRESS_INDEX_SCHEMA_VERSION:
        lines = [
            "# Operator Thread Progress",
            "",
            f"- generated_at: `{payload.get('generated_at')}`",
            f"- source_root: `{payload.get('source_root')}`",
            f"- payload_policy: `{payload.get('payload_policy')}`",
            f"- thread_count: `{payload.get('thread_count')}`",
            f"- recent_limit_per_thread: `{payload.get('recent_limit_per_thread')}`",
            "",
        ]
        for thread in payload.get("threads") or []:
            if isinstance(thread, dict):
                lines.extend(_render_progress_thread_markdown(thread, heading_level=2))
        return "\n".join(lines).rstrip() + "\n"
    return "\n".join(_render_progress_thread_markdown(payload, heading_level=1)).rstrip() + "\n"


def write_thread_progress_projection(payload: dict[str, Any]) -> dict[str, str]:
    if payload.get("private_preview_included"):
        raise ValueError("refusing to write private-preview thread progress projection")
    _write_json(THREAD_PROGRESS_JSON_PATH, payload)
    THREAD_PROGRESS_MARKDOWN_PATH.parent.mkdir(parents=True, exist_ok=True)
    THREAD_PROGRESS_MARKDOWN_PATH.write_text(render_thread_progress_markdown(payload), encoding="utf-8")
    return {
        "json_path": _display_path(THREAD_PROGRESS_JSON_PATH),
        "markdown_path": _display_path(THREAD_PROGRESS_MARKDOWN_PATH),
    }


def _repo_head_sha() -> str | None:
    git_path = REPO_ROOT / ".git"
    git_dir = git_path
    if git_path.is_file():
        text = git_path.read_text(encoding="utf-8", errors="replace").strip()
        if text.startswith("gitdir:"):
            raw = text.split(":", 1)[1].strip()
            git_dir = (REPO_ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
    head_path = git_dir / "HEAD"
    try:
        head = head_path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not head.startswith("ref:"):
        return head[:40] if head else None
    ref = head.split(" ", 1)[1].strip()
    try:
        return (git_dir / ref).read_text(encoding="utf-8").strip()[:40]
    except OSError:
        packed_refs = git_dir / "packed-refs"
        try:
            for line in packed_refs.read_text(encoding="utf-8").splitlines():
                if line.startswith("#") or not line.strip():
                    continue
                sha, _, packed_ref = line.partition(" ")
                if packed_ref.strip() == ref:
                    return sha[:40]
        except OSError:
            return None
    return None


def _card_fingerprint(card: dict[str, Any]) -> str:
    return _sha256(json.dumps(card, sort_keys=True, ensure_ascii=True))[:24]


def _response_anatomy_flags(card: dict[str, Any]) -> list[str]:
    flags: set[str] = set()
    summary = card.get("thread_semantic_summary") if isinstance(card.get("thread_semantic_summary"), dict) else {}
    counts = (
        summary.get("response_decision_anatomy_counts")
        if isinstance(summary.get("response_decision_anatomy_counts"), dict)
        else {}
    )
    flags.update(str(key) for key, count in counts.items() if int(count or 0) > 0)
    for item in card.get("recent_response_skeletons") or []:
        if not isinstance(item, dict):
            continue
        values = item.get("decision_anatomy_true") or item.get("anatomy_flags") or []
        if isinstance(values, list):
            flags.update(str(value) for value in values if value)
    return sorted(flags)


def _compact_recent_turns_for_handoff(card: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in card.get("recent_turn_stacks") or []:
        if not isinstance(item, dict):
            continue
        rows.append({
            "turn_index": item.get("turn_index"),
            "text_sha16": item.get("text_sha16"),
            "char_count": item.get("char_count"),
            "block_count": item.get("block_count"),
            "block_type_counts": item.get("block_type_counts") or {},
            "slot_counts": item.get("slot_counts") or {},
        })
    return rows


def _compact_recent_responses_for_handoff(card: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in card.get("recent_response_skeletons") or []:
        if not isinstance(item, dict):
            continue
        rows.append({
            "turn_index": item.get("turn_index"),
            "text_sha16": item.get("text_sha16"),
            "char_count": item.get("char_count"),
            "decision_anatomy_true": item.get("decision_anatomy_true") or item.get("anatomy_flags") or [],
        })
    return rows


def _handoff_packet_privacy_scan(packet: dict[str, Any]) -> dict[str, Any]:
    body = json.dumps(packet, sort_keys=True, ensure_ascii=True)
    findings = [marker for marker in TYPE_B_HANDOFF_FORBIDDEN_MARKERS if marker in body]
    return {
        "status": "clean" if not findings else "blocked",
        "checked_marker_count": len(TYPE_B_HANDOFF_FORBIDDEN_MARKERS),
        "finding_count": len(findings),
        "findings": findings,
        "raw_payload_included": False if not findings else None,
    }


def build_type_b_handoff_packet(thread_id: str, *, recent_limit: int = 5) -> dict[str, Any]:
    card = build_thread_continuation_card(thread_id, recent_limit=recent_limit)
    card_fingerprint = _card_fingerprint(card)
    summary = card.get("thread_semantic_summary") if isinstance(card.get("thread_semantic_summary"), dict) else {}
    safe_refs = card.get("safe_reference_ids") if isinstance(card.get("safe_reference_ids"), dict) else {}
    receipt_types = card.get("detected_receipt_types") or []
    anatomy_flags = _response_anatomy_flags(card)
    continuation_use = card.get("continuation_use") if isinstance(card.get("continuation_use"), dict) else {}
    can_continue = continuation_use.get("can_continue_without_raw_transcript") is True
    sufficiency_missing: list[str] = []
    if not can_continue:
        sufficiency_missing.append("continuation_use_contract")
    if not receipt_types:
        sufficiency_missing.append("receipt_types")
    if not anatomy_flags:
        sufficiency_missing.append("response_anatomy_flags")
    sufficiency_status = (
        "sufficient_for_type_b_next_move"
        if not sufficiency_missing
        else "needs_type_a_drilldown"
    )
    packet = {
        "schema_version": TYPE_B_HANDOFF_PACKET_SCHEMA_VERSION,
        "profile": TYPE_B_HANDOFF_MARKDOWN_PROFILE,
        "export_profile": TYPE_B_HANDOFF_EXPORT_PROFILE,
        "status": "available" if card.get("status") != "missing" else "missing_thread",
        "generated_at": _now_iso(),
        "source_thread": {
            "thread_id": card.get("thread_id") or thread_id,
            "conversation_id": card.get("conversation_id"),
            "thread_status": card.get("status"),
            "labels": card.get("labels") or [],
            "turn_count": card.get("turn_count") or 0,
            "user_turn_count": card.get("user_turn_count") or 0,
            "assistant_turn_count": card.get("assistant_turn_count") or 0,
            "content_hashes": card.get("content_hashes") or {},
            "card_schema_version": card.get("schema_version"),
            "card_fingerprint": card_fingerprint,
            "card_command": (
                "./repo-python tools/meta/observability/operator_thread_memory.py "
                f"--continuation-card --thread {thread_id}"
            ),
        },
        "freshness_receipt": {
            "repo_head": _repo_head_sha(),
            "head_verification_command": "./repo-git rev-parse HEAD",
            "thread_memory_check_command": (
                "./repo-python tools/meta/observability/operator_thread_memory.py --check"
            ),
            "context_pack_command": (
                "./repo-python kernel.py --context-pack "
                f"\"Type B grounding packet for operator thread {thread_id} continuation card\" "
                "--context-budget 12000"
            ),
        },
        "authority_boundary": {
            "type_b_can_decide_from_packet": [
                "the next architecture or continuation move implied by receipt types, block counts, and response anatomy",
                "whether raw trace paste is unnecessary for routine continuation",
                "which ASK_TYPE_A handles would be needed for private source evidence",
            ],
            "type_a_must_verify_privately": [
                "current HEAD and commit ancestry before mutation",
                "raw transcript or private previews if exact wording would change the answer",
                "WorkItem/CAP receipt state in Task Ledger",
                "privacy/export policy for any broader publication surface",
            ],
            "source_authority_order": "private repo/source events > continuation card > this rendered handoff packet > Type B inference",
        },
        "export_policy": {
            "metadata_only": True,
            "public_release_safe": False,
            "intended_surface": "operator_approved_external_type_b_session",
            "operator_approval_required": True,
            "raw_bodies_omitted": True,
            "external_upload_boundary": (
                "Safe only as a bounded operator-approved Type B continuation packet; "
                "not a general public-release artifact."
            ),
            "forbidden_payload": [
                "raw captured transcript bodies",
                "assistant response bodies",
                "private preview/title fields",
                "host paths, secrets, credentials, or provider/browser internals",
            ],
        },
        "omission_receipt": {
            "omitted": [
                "raw user turns",
                "raw assistant turns",
                "private projection previews",
                "full code-review/diff text",
            ],
            "reason": (
                "Type B needs the control state, receipt classes, hashes, and ASK_TYPE_A handles; "
                "raw evidence remains in the private thread-memory drilldown lane."
            ),
            "drilldown": (
                "./repo-python tools/meta/observability/operator_thread_memory.py "
                f"--turn-projection --thread {thread_id} --include-private-previews"
            ),
        },
        "card_summary": {
            "payload_policy": card.get("payload_policy"),
            "can_continue_without_raw_transcript": can_continue,
            "detected_receipt_types": receipt_types,
            "block_type_counts": summary.get("block_type_counts") or {},
            "slot_counts": summary.get("slot_counts") or {},
            "response_anatomy_flags": anatomy_flags,
            "recent_turns": _compact_recent_turns_for_handoff(card),
            "recent_responses": _compact_recent_responses_for_handoff(card),
        },
        "ownership_refs": {
            "safe_reference_ids": safe_refs,
            "workitem_binding_detected": "workitem_binding_receipt" in (card.get("detected_receipt_types") or []),
            "receipt_binding_policy": "ids_only_no_raw_receipt_text",
        },
        "card_only_sufficiency": {
            "status": sufficiency_status,
            "same_next_move_as_raw_trace": not sufficiency_missing,
            "expected_next_move": (
                "Use the continuation card as the default shuttle evidence object through a "
                "Type B-safe render packet; do not add recognizers unless the card misses a "
                "decision-critical field."
            ),
            "missing": sufficiency_missing,
        },
        "type_b_instruction": {
            "deliverable": "continuation delta or next-phase integration plan from this packet plus the operator's fresh addendum",
            "must_not": [
                "invent private repo state",
                "ask the operator to run repo commands",
                "treat metadata-only as public-release safe",
                "request raw transcript unless a decision-critical exact source fact is missing",
            ],
            "ask_type_a_handles": [
                "verify HEAD/ancestry and scoped dirt before code mutation",
                "verify Task Ledger/CAP receipt state by id",
                "drill down to private turn projection only if exact wording changes the decision",
            ],
        },
    }
    packet["privacy_scan"] = _handoff_packet_privacy_scan(packet)
    return packet


def render_type_b_handoff_markdown(packet: dict[str, Any]) -> str:
    source = packet.get("source_thread") if isinstance(packet.get("source_thread"), dict) else {}
    card_summary = packet.get("card_summary") if isinstance(packet.get("card_summary"), dict) else {}
    ownership = packet.get("ownership_refs") if isinstance(packet.get("ownership_refs"), dict) else {}
    safe_refs = ownership.get("safe_reference_ids") if isinstance(ownership.get("safe_reference_ids"), dict) else {}
    freshness = packet.get("freshness_receipt") if isinstance(packet.get("freshness_receipt"), dict) else {}
    privacy = packet.get("privacy_scan") if isinstance(packet.get("privacy_scan"), dict) else {}
    export_policy = packet.get("export_policy") if isinstance(packet.get("export_policy"), dict) else {}
    sufficiency = packet.get("card_only_sufficiency") if isinstance(packet.get("card_only_sufficiency"), dict) else {}
    lines = [
        "# Operator Thread Type B Handoff Packet",
        "",
        "`deliverable_type=continuation delta`; `authority_boundary=Type B reasons from this metadata-only packet; Type A verifies live substrate before mutation`; `integration_target=Operator Thread Memory continuation-card shuttle`.",
        "",
        "## Freshness",
        "",
        f"- thread_id: `{source.get('thread_id')}`",
        f"- conversation_id: `{source.get('conversation_id')}`",
        f"- card_fingerprint: `{source.get('card_fingerprint')}`",
        f"- repo_head_at_render: `{freshness.get('repo_head')}`",
        f"- privacy_scan: `{privacy.get('status')}`",
        f"- export_profile: `{packet.get('export_profile')}`",
        f"- public_release_safe: `{export_policy.get('public_release_safe')}`",
        "",
        "## Continuation State",
        "",
        f"- detected_receipt_types: `{', '.join(card_summary.get('detected_receipt_types') or [])}`",
        f"- response_anatomy_flags: `{', '.join(card_summary.get('response_anatomy_flags') or [])}`",
        f"- block_type_counts: `{json.dumps(card_summary.get('block_type_counts') or {}, sort_keys=True)}`",
        "",
        "## Ownership Refs",
        "",
        f"- cap_ids: `{', '.join(safe_refs.get('cap_ids') or [])}`",
        f"- task_ledger_event_ids: `{', '.join(safe_refs.get('task_ledger_event_ids') or [])}`",
        f"- transaction_ids: `{', '.join(safe_refs.get('transaction_ids') or [])}`",
        f"- commit_hashes: `{', '.join(safe_refs.get('commit_hashes') or [])}`",
        "",
        "## Omission Receipt",
        "",
        "- Raw user turns, raw assistant turns, private previews, and full diff/code text are omitted.",
        "- Drilldown remains Type A-private through `operator_thread_memory.py --turn-projection --include-private-previews`.",
        "",
        "## Type B Task",
        "",
        f"- card_only_sufficiency: `{sufficiency.get('status')}`",
        f"- expected_next_move: {sufficiency.get('expected_next_move')}",
        "- If an exact private fact would change the answer, emit an ASK_TYPE_A handle instead of inventing it.",
    ]
    return "\n".join(lines).rstrip() + "\n"


def _sanitize_prompt_catalog(catalog: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for prompt in catalog:
        if not isinstance(prompt, dict):
            continue
        rows.append({
            "prompt_id": prompt.get("prompt_id"),
            "turn_index": prompt.get("turn_index"),
            "first_seen_at": prompt.get("first_seen_at"),
            "last_seen_at": prompt.get("last_seen_at"),
            "char_count": prompt.get("char_count"),
            "hash": prompt.get("hash"),
            "sha16": prompt.get("sha16"),
            "normalized_sha16": prompt.get("normalized_sha16"),
            "structural_sha16": prompt.get("structural_sha16"),
            "pattern_labels": prompt.get("pattern_labels") or [],
            "slots": prompt.get("slots") or [],
            "repeat_levels": prompt.get("repeat_levels") or [],
            "repeat_count_thread": prompt.get("repeat_count_thread") or 0,
        })
    return rows


def _index_row(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": record.get("thread_id"),
        "conversation_id": record.get("conversation_id"),
        "status": record.get("status"),
        "labels": record.get("labels") or [],
        "first_seen_at": record.get("first_seen_at"),
        "last_seen_at": record.get("last_seen_at"),
        "last_nonempty_seen_at": record.get("last_nonempty_seen_at"),
        "turn_count": record.get("turn_count") or 0,
        "user_turn_count": record.get("user_turn_count") or 0,
        "assistant_turn_count": record.get("assistant_turn_count") or 0,
        "char_counts": record.get("char_counts") or {},
        "thread_memory_merge_state": record.get("thread_memory_merge_state"),
        "latest_observed_window": record.get("latest_observed_window") or {},
        "content_hashes": {
            "transcript_sha256": (record.get("content_hashes") or {}).get("transcript_sha256"),
            "transcript_sha16": (record.get("content_hashes") or {}).get("transcript_sha16"),
            "suffix_sha16": (record.get("content_hashes") or {}).get("suffix_sha16"),
        },
        "thread_prompt_count": len(record.get("thread_prompt_catalog") or []),
        "thread_prompt_catalog": _sanitize_prompt_catalog(record.get("thread_prompt_catalog") or []),
        "turn_stack_count": len(record.get("turn_stack_catalog") or []),
        "response_skeleton_count": len(record.get("response_skeleton_catalog") or []),
        "thread_semantic_summary": _metadata_thread_semantic_summary(record),
        "thread_path": _display_path(_thread_path(str(record.get("thread_id") or ""))),
        "payload_policy": "metadata_only",
        "raw_text_present": False,
    }


def write_index(records: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_index_row(record) for record in records]
    rows.sort(key=lambda item: str(item.get("last_seen_at") or ""), reverse=True)
    payload = {
        "schema_version": INDEX_SCHEMA_VERSION,
        "projection_authority": "events.jsonl",
        "generated_at": _now_iso(),
        "thread_count": len(rows),
        "payload_policy": "metadata_only",
        "raw_text_present": False,
        "threads": rows,
    }
    _write_json(INDEX_PATH, payload)
    return payload


def _all_thread_records() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        paths = sorted(THREADS_DIR.glob("*.json"))
    except OSError:
        return []
    for path in paths:
        data = _read_json(path, None)
        if isinstance(data, dict):
            records.append(data)
    return records


def _write_projection_index_for_current(record: dict[str, Any]) -> dict[str, Any]:
    records = [item for item in _all_thread_records() if item.get("thread_id") != record.get("thread_id")]
    records.append(record)
    return write_index(records)


def rebuild_projection_index() -> dict[str, Any]:
    """Refresh the metadata index from materialized thread records."""
    return write_index(_all_thread_records())


def _find_thread_by_fingerprint(index: dict[str, Any], transcript_sha: str, turn_hashes: list[str]) -> str | None:
    for row in index.get("threads") or []:
        if not isinstance(row, dict):
            continue
        hashes = row.get("content_hashes") or {}
        if hashes.get("transcript_sha256") == transcript_sha:
            return str(row.get("thread_id") or "") or None
    for row in index.get("threads") or []:
        record = load_thread(str(row.get("thread_id") or ""))
        if record and _strong_turn_overlap((record.get("content_hashes") or {}).get("turn_hashes") or [], turn_hashes):
            return str(record.get("thread_id") or "") or None
    return None


def _promote_thread_record(old_thread_id: str, new_thread_id: str, *, conversation_id: str, now: str) -> dict[str, Any] | None:
    if old_thread_id == new_thread_id:
        return load_thread(new_thread_id)
    old = load_thread(old_thread_id)
    new = load_thread(new_thread_id)
    if old is None and new is None:
        return None
    if new is None:
        new = old or _record_base(new_thread_id, now=now)
    if old:
        provisional_ids = set(new.get("provisional_ids") or [])
        provisional_ids.add(old_thread_id)
        aliases = set(new.get("aliases") or [])
        aliases.add(old_thread_id)
        new.update({
            "thread_id": new_thread_id,
            "conversation_id": conversation_id,
            "provisional_ids": sorted(provisional_ids),
            "aliases": sorted(aliases),
            "first_seen_at": min(str(new.get("first_seen_at") or now), str(old.get("first_seen_at") or now)),
        })
        if not new.get("turns") or len(old.get("turns") or []) > len(new.get("turns") or []):
            for key in (
                "turns", "thread_prompt_catalog", "content_hashes", "turn_count",
                "user_turn_count", "assistant_turn_count", "char_counts",
                "turn_stack_catalog", "response_skeleton_catalog", "thread_semantic_summary",
            ):
                new[key] = old.get(key)
        try:
            _thread_path(old_thread_id).unlink()
        except OSError:
            pass
    save_thread(new)
    return new


def _update_record_from_snapshot(
    record: dict[str, Any],
    *,
    turns: list[dict[str, Any]],
    snapshot: Any,
    tab: Any,
    hud_payload: dict[str, Any],
    now: str,
    observer_version: str | None,
    existing_index: dict[str, Any],
    vanish_state: str,
) -> dict[str, Any]:
    observed_turns = turns
    observed_turn_hashes = transcript_turn_hashes(observed_turns)
    observed_full_hash = transcript_hash(observed_turns)
    turns, merge_state = merge_observed_turn_window(
        record.get("turns") or [],
        observed_turns,
        now=now,
    )
    conversation_id = parse_conversation_id(str(getattr(snapshot, "url", "") or ""))
    if conversation_id:
        record["conversation_id"] = conversation_id
    target_id = str(getattr(tab, "target_id", "") or "")
    if target_id and target_id not in record.get("tab_target_ids_seen", []):
        record.setdefault("tab_target_ids_seen", []).append(target_id)
    record["url_history"] = _append_history(
        list(record.get("url_history") or []),
        "url",
        str(getattr(snapshot, "url", "") or ""),
        now,
    )
    record["title_history"] = _append_history(
        list(record.get("title_history") or []),
        "title",
        str(getattr(snapshot, "title", "") or ""),
        now,
    )
    record["last_seen_at"] = now
    if turns:
        record["last_nonempty_seen_at"] = now
    record["status"] = "active" if turns else "empty_candidate"
    record["latest_observed_window"] = {
        "observed_at": now,
        "turn_count": len(observed_turns),
        "user_turn_count": sum(1 for turn in observed_turns if turn.get("role") == "user"),
        "assistant_turn_count": sum(1 for turn in observed_turns if turn.get("role") == "assistant"),
        "transcript_sha16": observed_full_hash[:16],
        "suffix_sha16": transcript_suffix_hash(observed_turn_hashes)[:16],
    }
    record["thread_memory_merge_state"] = merge_state
    record["turns"] = turns
    prompt_catalog = build_thread_prompt_catalog(turns, include_private_excerpts=True, existing_index=existing_index)
    record["thread_prompt_catalog"] = prompt_catalog
    semantic_projection = _build_semantic_turn_projections(turns)
    record["turn_stack_catalog"] = semantic_projection.get("turn_stack_catalog") or []
    record["response_skeleton_catalog"] = semantic_projection.get("response_skeleton_catalog") or []
    record["thread_semantic_summary"] = semantic_projection.get("thread_semantic_summary") or {}
    turn_hashes = transcript_turn_hashes(turns)
    full_hash = transcript_hash(turns)
    record["content_hashes"] = {
        "transcript_sha256": full_hash,
        "transcript_sha16": full_hash[:16],
        "suffix_sha256": transcript_suffix_hash(turn_hashes),
        "suffix_sha16": transcript_suffix_hash(turn_hashes)[:16],
        "turn_hashes": turn_hashes,
    }
    record["turn_count"] = len(turns)
    record["user_turn_count"] = sum(1 for turn in turns if turn.get("role") == "user")
    record["assistant_turn_count"] = sum(1 for turn in turns if turn.get("role") == "assistant")
    user_chars = sum(int(turn.get("char_count") or 0) for turn in turns if turn.get("role") == "user")
    assistant_chars = sum(int(turn.get("char_count") or 0) for turn in turns if turn.get("role") == "assistant")
    record["char_counts"] = {
        "total": sum(int(turn.get("char_count") or 0) for turn in turns),
        "user": user_chars,
        "assistant": assistant_chars,
    }
    record["classification"] = {
        "prompt_label_counts": _label_counts(prompt_catalog),
        "slot_counts": _slot_counts(prompt_catalog),
    }
    record["vanish_recovery_state"] = vanish_state
    record["source_observer_version"] = observer_version or hud_payload.get("observer_version")
    record["labels"] = classify_thread(record, hud_payload)
    return record


def _label_counts(prompt_catalog: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for prompt in prompt_catalog:
        for label in prompt.get("pattern_labels") or []:
            counts[str(label)] = counts.get(str(label), 0) + 1
    return counts


def _slot_counts(prompt_catalog: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for prompt in prompt_catalog:
        for slot in prompt.get("slots") or []:
            counts[str(slot)] = counts.get(str(slot), 0) + 1
    return counts


def _raw_snapshot_event(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "thread_id": record.get("thread_id"),
        "conversation_id": record.get("conversation_id"),
        "labels": record.get("labels") or [],
        "turn_count": record.get("turn_count"),
        "user_turn_count": record.get("user_turn_count"),
        "assistant_turn_count": record.get("assistant_turn_count"),
        "content_hashes": record.get("content_hashes") or {},
        "turns": record.get("turns") or [],
        "thread_prompt_catalog": record.get("thread_prompt_catalog") or [],
        "turn_stack_catalog": record.get("turn_stack_catalog") or [],
        "response_skeleton_catalog": record.get("response_skeleton_catalog") or [],
        "thread_semantic_summary": record.get("thread_semantic_summary") or {},
    }


def _snapshot_events_dir(thread_id: str) -> Path:
    return THREAD_MEMORY_ROOT / "snapshot_events" / _safe_id(thread_id)


def _write_thread_snapshot_ref(
    record: dict[str, Any],
    *,
    event_type: str,
    observed_at: str,
) -> dict[str, Any]:
    """Persist a compressed raw snapshot and return a compact event-log ref."""
    snapshot = _raw_snapshot_event(record)
    snapshot_text = json.dumps(snapshot, sort_keys=True, ensure_ascii=False)
    snapshot_bytes = snapshot_text.encode("utf-8")
    snapshot_sha = hashlib.sha256(snapshot_bytes).hexdigest()
    thread_id = str(record.get("thread_id") or "unknown")
    path = (
        _snapshot_events_dir(thread_id)
        / f"{_safe_id(observed_at)}_{_safe_id(event_type)}_{snapshot_sha[:16]}.json.gz"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        with gzip.open(path, "wt", encoding="utf-8") as handle:
            handle.write(snapshot_text)
    hashes = record.get("content_hashes") if isinstance(record.get("content_hashes"), dict) else {}
    return {
        "schema_version": THREAD_SNAPSHOT_REF_SCHEMA_VERSION,
        "payload_policy": "compressed_private_snapshot_ref",
        "thread_id": thread_id,
        "event_type": event_type,
        "snapshot_path": _display_path(path),
        "snapshot_sha256": snapshot_sha,
        "snapshot_sha16": snapshot_sha[:16],
        "snapshot_bytes": len(snapshot_bytes),
        "snapshot_gzip_bytes": path.stat().st_size,
        "turn_count": record.get("turn_count") or 0,
        "user_turn_count": record.get("user_turn_count") or 0,
        "assistant_turn_count": record.get("assistant_turn_count") or 0,
        "transcript_sha16": hashes.get("transcript_sha16"),
        "suffix_sha16": hashes.get("suffix_sha16"),
    }


def _read_thread_snapshot_ref(ref: dict[str, Any]) -> dict[str, Any] | None:
    path_value = str(ref.get("snapshot_path") or "")
    if not path_value:
        return None
    path = Path(path_value)
    if not path.is_absolute():
        path = REPO_ROOT / path
    try:
        if path.suffix == ".gz":
            with gzip.open(path, "rt", encoding="utf-8") as handle:
                data = handle.read()
        else:
            data = path.read_text(encoding="utf-8")
    except OSError:
        return None
    expected_sha = str(ref.get("snapshot_sha256") or "")
    if expected_sha and hashlib.sha256(data.encode("utf-8")).hexdigest() != expected_sha:
        return None
    try:
        parsed = json.loads(data)
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _snapshot_from_event(event: dict[str, Any]) -> dict[str, Any] | None:
    snapshot = event.get("thread_snapshot")
    if isinstance(snapshot, dict):
        return snapshot
    ref = event.get("thread_snapshot_ref")
    if isinstance(ref, dict):
        return _read_thread_snapshot_ref(ref)
    return None


def _metadata_from_record(record: dict[str, Any], *, event_types: list[str] | None = None) -> dict[str, Any]:
    hashes = record.get("content_hashes") or {}
    return {
        "thread_memory_id": record.get("thread_id"),
        "thread_memory_status": record.get("status") or "unknown",
        "thread_memory_labels": record.get("labels") or [],
        "thread_prompt_count": len(record.get("thread_prompt_catalog") or []),
        "thread_turn_stack_count": len(record.get("turn_stack_catalog") or []),
        "thread_response_skeleton_count": len(record.get("response_skeleton_catalog") or []),
        "thread_semantic_summary": _metadata_thread_semantic_summary(record),
        "thread_memory_turn_count": record.get("turn_count") or 0,
        "thread_memory_user_turn_count": record.get("user_turn_count") or 0,
        "thread_memory_assistant_turn_count": record.get("assistant_turn_count") or 0,
        "thread_memory_merge_state": record.get("thread_memory_merge_state"),
        "latest_observed_window": record.get("latest_observed_window") or {},
        "thread_memory_transcript_sha16": hashes.get("transcript_sha16"),
        "thread_memory_suffix_sha16": hashes.get("suffix_sha16"),
        "thread_memory_event_types": event_types or [],
        "thread_memory_payload_policy": "metadata_only",
    }


def _empty_metadata(prior: dict[str, Any] | None, *, state: str, event_types: list[str]) -> dict[str, Any]:
    return {
        "thread_memory_id": (prior or {}).get("thread_id"),
        "thread_memory_status": state,
        "thread_memory_labels": [],
        "thread_prompt_count": 0,
        "thread_turn_stack_count": 0,
        "thread_response_skeleton_count": 0,
        "thread_semantic_summary": {
            "payload_policy": "metadata_only",
            "raw_text_stored": False,
            "turn_count": 0,
            "turn_stack_count": 0,
            "response_skeleton_count": 0,
        },
        "thread_memory_turn_count": 0,
        "thread_memory_user_turn_count": 0,
        "thread_memory_assistant_turn_count": 0,
        "thread_memory_transcript_sha16": (prior or {}).get("transcript_sha16"),
        "thread_memory_suffix_sha16": (prior or {}).get("suffix_sha16"),
        "thread_memory_event_types": event_types,
        "thread_memory_payload_policy": "metadata_only",
    }


def update_from_observer_snapshot(
    *,
    tab: Any,
    snapshot: Any,
    hud_payload: dict[str, Any] | None = None,
    bindings: dict[str, Any] | None = None,
    now: str | None = None,
    observer_version: str | None = None,
    write_projection_index: bool = True,
) -> dict[str, Any]:
    """Update private thread memory from one observer full snapshot.

    Returns a compact metadata-only dict suitable for HUD payloads.
    """
    now = now or _now_iso()
    hud_payload = hud_payload or {}
    state = _bindings(bindings)
    tabs = state["tabs"]
    vanish_candidates = state["vanish_candidates"]
    aliases = state["aliases"]
    target_id = str(getattr(tab, "target_id", "") or "")
    url = str(getattr(snapshot, "url", "") or getattr(tab, "url", "") or "")
    title = str(getattr(snapshot, "title", "") or getattr(tab, "title", "") or "")
    prior = tabs.get(target_id) if isinstance(tabs.get(target_id), dict) else {}
    raw_turns = getattr(snapshot, "turns", []) or []
    turns = normalize_turns(raw_turns, seen_at=now)
    nonempty = any(turn.get("text") for turn in turns)

    base_event = {
        "observed_at": now,
        "target_id": target_id,
        "url": url,
        "title": title,
        "conversation_id": parse_conversation_id(url),
        "observer_version": observer_version or hud_payload.get("observer_version"),
    }
    event_types: list[str] = []

    if not nonempty:
        empty_count = int(prior.get("empty_seen_count") or 0) + 1 if prior else 1
        vanish_state = "empty_candidate" if empty_count == 1 else "empty_confirmed"
        prior_thread_id = str(prior.get("thread_id") or "")
        if prior_thread_id:
            vanish_candidates[target_id] = {
                "thread_id": prior_thread_id,
                "last_transcript_sha256": prior.get("transcript_sha256"),
                "last_turn_hashes": prior.get("turn_hashes") or [],
                "first_empty_seen_at": prior.get("first_empty_seen_at") or now,
                "last_empty_seen_at": now,
                "empty_seen_count": empty_count,
            }
        tabs[target_id] = {
            **prior,
            "thread_id": prior_thread_id,
            "last_seen_at": now,
            "vanish_state": vanish_state,
            "empty_seen_count": empty_count,
            "first_empty_seen_at": prior.get("first_empty_seen_at") or now,
        }
        append_event({**base_event, "event_type": "tab_empty_seen", "vanish_state": vanish_state})
        event_types.append("tab_empty_seen")
        return _empty_metadata(tabs[target_id], state=vanish_state, event_types=event_types)

    turn_hashes = transcript_turn_hashes(turns)
    full_hash = transcript_hash(turns)
    conversation_id = parse_conversation_id(url)
    desired_thread_id = thread_id_for_conversation(conversation_id) if conversation_id else ""
    index = load_thread_index()
    vanish = vanish_candidates.get(target_id) if isinstance(vanish_candidates.get(target_id), dict) else {}
    prior_thread_id = str(prior.get("thread_id") or "")
    overlapped_prior = _strong_turn_overlap(prior.get("turn_hashes") or [], turn_hashes)
    overlapped_vanish = _strong_turn_overlap(vanish.get("last_turn_hashes") or [], turn_hashes)

    transition_event: str | None = None
    vanish_state = "nonempty_observed"
    if desired_thread_id:
        thread_id = desired_thread_id
        if prior_thread_id and prior_thread_id.startswith("provisional_") and (overlapped_prior or overlapped_vanish):
            _promote_thread_record(prior_thread_id, desired_thread_id, conversation_id=conversation_id or "", now=now)
            aliases[prior_thread_id] = desired_thread_id
            transition_event = "thread_alias_promoted"
        elif prior_thread_id and prior_thread_id != desired_thread_id and (overlapped_prior or overlapped_vanish):
            aliases[prior_thread_id] = desired_thread_id
            transition_event = "thread_alias_promoted"
    elif vanish and overlapped_vanish:
        thread_id = str(vanish.get("thread_id") or prior_thread_id)
        transition_event = "thread_reappeared_after_vanish"
        vanish_state = "reappeared_same_thread"
    elif vanish and not overlapped_vanish:
        thread_id = provisional_thread_id(target_id, full_hash, now)
        transition_event = "thread_rollover_after_blank"
        vanish_state = "rolled_over_new_thread"
    elif prior_thread_id and (overlapped_prior or not desired_thread_id):
        thread_id = prior_thread_id
    else:
        thread_id = _find_thread_by_fingerprint(index, full_hash, turn_hashes) or provisional_thread_id(target_id, full_hash, now)

    append_event({
        **base_event,
        "event_type": "tab_seen",
        "thread_id": thread_id,
        "turn_count": len(turns),
        "transcript_sha16": full_hash[:16],
    })
    event_types.append("tab_seen")
    append_event({
        **base_event,
        "event_type": "thread_candidate_seen",
        "thread_id": thread_id,
        "identity_basis": "conversation_id" if desired_thread_id else ("vanish_overlap" if overlapped_vanish else "provisional_or_fingerprint"),
        "turn_count": len(turns),
    })
    event_types.append("thread_candidate_seen")

    if transition_event:
        append_event({
            **base_event,
            "event_type": transition_event,
            "thread_id": thread_id,
            "previous_thread_id": prior_thread_id or vanish.get("thread_id"),
            "identity_basis": "conversation_id" if desired_thread_id else "transcript_overlap_or_blank_rollover",
        })
        event_types.append(transition_event)

    old_record = load_thread(thread_id)
    record = old_record or _record_base(thread_id, now=now)
    old_labels = list(record.get("labels") or [])
    old_hash = (record.get("content_hashes") or {}).get("transcript_sha256")
    record = _update_record_from_snapshot(
        record,
        turns=turns,
        snapshot=snapshot,
        tab=tab,
        hud_payload=hud_payload,
        now=now,
        observer_version=observer_version,
        existing_index=index,
        vanish_state=vanish_state,
    )
    new_hash = (record.get("content_hashes") or {}).get("transcript_sha256")
    record_event = "thread_created" if old_record is None else ("thread_updated" if old_hash != new_hash else "")
    if record_event:
        append_event({
            **base_event,
            "event_type": record_event,
            "thread_id": thread_id,
            "thread_snapshot_ref": _write_thread_snapshot_ref(
                record,
                event_type=record_event,
                observed_at=now,
            ),
        })
        event_types.append(record_event)
        for prompt in record.get("thread_prompt_catalog") or []:
            append_event({
                **base_event,
                "event_type": "prompt_hash_seen",
                "thread_id": thread_id,
                "prompt_id": prompt.get("prompt_id"),
                "turn_index": prompt.get("turn_index"),
                "sha16": prompt.get("sha16"),
                "normalized_sha16": prompt.get("normalized_sha16"),
                "structural_sha16": prompt.get("structural_sha16"),
            })
            event_types.append("prompt_hash_seen")
            if prompt.get("pattern_labels"):
                append_event({
                    **base_event,
                    "event_type": "prompt_pattern_classified",
                    "thread_id": thread_id,
                    "prompt_id": prompt.get("prompt_id"),
                    "turn_index": prompt.get("turn_index"),
                    "pattern_labels": prompt.get("pattern_labels"),
                    "slots": prompt.get("slots") or [],
                })
                event_types.append("prompt_pattern_classified")
    if old_labels and sorted(old_labels) != sorted(record.get("labels") or []):
        append_event({
            **base_event,
            "event_type": "thread_label_changed",
            "thread_id": thread_id,
            "old_labels": old_labels,
            "new_labels": record.get("labels") or [],
        })
        event_types.append("thread_label_changed")

    save_thread(record)
    if write_projection_index:
        _write_projection_index_for_current(record)
    vanish_candidates.pop(target_id, None)
    tabs[target_id] = {
        "thread_id": thread_id,
        "conversation_id": conversation_id,
        "last_seen_at": now,
        "last_nonempty_seen_at": now,
        "transcript_sha256": full_hash,
        "transcript_sha16": full_hash[:16],
        "turn_hashes": turn_hashes,
        "vanish_state": "nonempty_observed",
        "empty_seen_count": 0,
    }
    return _metadata_from_record(record, event_types=event_types)


def project_thread_records(*, events_path: Path | None = None) -> dict[str, Any]:
    """Rebuild thread projections and metadata index from the private event log."""
    records: dict[str, dict[str, Any]] = {}
    for event in read_events(events_path=events_path):
        if event.get("event_type") not in RAW_EVENT_TYPES:
            continue
        snapshot = _snapshot_from_event(event)
        if not isinstance(snapshot, dict):
            continue
        thread_id = str(snapshot.get("thread_id") or event.get("thread_id") or "")
        if not thread_id:
            continue
        record = _record_base(thread_id, now=str(event.get("created_at") or _now_iso()))
        for key, value in snapshot.items():
            record[key] = value
        record["schema_version"] = THREAD_SCHEMA_VERSION
        record["projection_authority"] = "events.jsonl"
        records[thread_id] = record
    for record in records.values():
        semantic_projection = _build_semantic_turn_projections(record.get("turns") or [])
        record["turn_stack_catalog"] = semantic_projection.get("turn_stack_catalog") or []
        record["response_skeleton_catalog"] = semantic_projection.get("response_skeleton_catalog") or []
        record["thread_semantic_summary"] = semantic_projection.get("thread_semantic_summary") or {}
        save_thread(record)
    return write_index(list(records.values()))


def search_threads(query: str, *, limit: int = 20) -> list[dict[str, Any]]:
    needle = _normalized_prompt_text(query)
    if not needle:
        return []
    rows: list[dict[str, Any]] = []
    for record in _all_thread_records():
        haystacks = [
            str(record.get("thread_id") or ""),
            str(record.get("conversation_id") or ""),
            " ".join(record.get("labels") or []),
            " ".join(str(item.get("title") or "") for item in record.get("title_history") or []),
        ]
        private_matches: list[dict[str, Any]] = []
        for prompt in record.get("thread_prompt_catalog") or []:
            text = str(prompt.get("short_title_or_excerpt") or "")
            haystacks.append(text)
            if needle in _normalized_prompt_text(text):
                private_matches.append({
                    "kind": "prompt",
                    "prompt_id": prompt.get("prompt_id"),
                    "turn_index": prompt.get("turn_index"),
                    "private_excerpt": text,
                })
        for turn in record.get("turns") or []:
            text = str(turn.get("text") or "")
            if needle in _normalized_prompt_text(text):
                private_matches.append({
                    "kind": str(turn.get("role") or "turn"),
                    "turn_index": turn.get("turn_index"),
                    "private_excerpt": _safe_excerpt(text),
                })
        if needle in _normalized_prompt_text(" ".join(haystacks)) or private_matches:
            rows.append({
                **_index_row(record),
                "private_matches": private_matches[:5],
            })
    rows.sort(key=lambda item: str(item.get("last_seen_at") or ""), reverse=True)
    return rows[:limit]


def _lesson_route_contract() -> dict[str, Any]:
    return {
        "advisory_source": True,
        "mutation_allowed": False,
        "adoption_owner": "Prompt Ledger",
        "owner_surface": "codex/standards/std_prompt_ledger.json::adoption_state_machine",
        "adoption_event_type": "prompt_trace.adoption_state_changed",
        "initial_adoption_state": "indexed",
        "point_of_use_surface": "state/prompt_ledger/views/adoption_posture.json",
        "required_before_owner_mutation": [
            "append or inspect Prompt Ledger adoption posture",
            "bind to Task Ledger/WorkItem when action is needed",
            "mutate the selected standard, skill, paper module, or runtime owner only after Type A verification",
        ],
    }


def _lesson_privacy_contract(*, include_private_excerpts: bool) -> dict[str, Any]:
    return {
        "privacy_class": "private_thread_metadata",
        "payload_policy": "metadata_only" if not include_private_excerpts else "explicit_private_excerpt",
        "raw_text_stored": False,
        "private_excerpt_included": bool(include_private_excerpts),
        "private_excerpt_default": False,
        "raw_thread_body_stored": False,
    }


def _candidate_evidence_ref(
    *,
    thread_id: str,
    prompt: dict[str, Any],
    catalog_index: int,
) -> dict[str, Any]:
    return {
        "kind": "private_thread_prompt_ref",
        "thread_id": thread_id,
        "prompt_id": prompt.get("prompt_id"),
        "source_turn_index": prompt.get("turn_index"),
        "thread_path": _display_path(_thread_path(thread_id)),
        "field_path": f"thread_prompt_catalog[{catalog_index}]",
        "hashes": {
            "prompt_sha16": prompt.get("sha16"),
            "normalized_prompt_sha16": prompt.get("normalized_sha16"),
            "structural_prompt_sha16": prompt.get("structural_sha16"),
        },
        "raw_text_stored": False,
        "private_excerpt_ref": "short_title_or_excerpt",
    }


def build_lesson_candidate_packet(
    thread_id: str,
    *,
    include_private_excerpts: bool = False,
) -> dict[str, Any]:
    record = load_thread(thread_id)
    if not record:
        return {
            "schema_version": LESSON_CANDIDATES_SCHEMA_VERSION,
            "thread_id": thread_id,
            "status": "missing",
            "candidates": [],
            "mutation_allowed": False,
            "privacy": _lesson_privacy_contract(include_private_excerpts=include_private_excerpts),
            "route_contract": _lesson_route_contract(),
        }
    labels = set(record.get("labels") or [])
    prompt_labels = set()
    for prompt in record.get("thread_prompt_catalog") or []:
        prompt_labels.update(prompt.get("pattern_labels") or [])
    suggested_routes: list[str] = ["Prompt Ledger"]
    if "prompt_shelf_capture_thread" in labels or "prompt_shelf_slot" in prompt_labels:
        suggested_routes.append("prompt_shelf_outbox")
    if "compaction_sidecar" in labels or "compact" in prompt_labels:
        suggested_routes.append("local_to_general_propagation")
    if "type_b_packet_thread" in labels or "type_b_packet_like" in prompt_labels:
        suggested_routes.extend(["WorkItem", "standard", "skill"])
    if "research_thread" in labels:
        suggested_routes.append("paper_module")
    if not suggested_routes:
        suggested_routes.append("Task Ledger")
    prompts = record.get("thread_prompt_catalog") or []
    interesting_pairs = [
        (index, prompt)
        for index, prompt in enumerate(prompts)
        if prompt.get("pattern_labels") or prompt.get("repeat_levels")
    ][:8]
    candidate_rows: list[dict[str, Any]] = []
    for catalog_index, prompt in interesting_pairs:
        candidate = {
            "candidate_id": f"otm_{_safe_id(thread_id)}_{prompt.get('prompt_id')}",
            "source_turn_index": prompt.get("turn_index"),
            "pattern_labels": prompt.get("pattern_labels") or [],
            "repeat_levels": prompt.get("repeat_levels") or [],
            "evidence_ref": _candidate_evidence_ref(
                thread_id=thread_id,
                prompt=prompt,
                catalog_index=catalog_index,
            ),
            "confidence": 0.7 if prompt.get("repeat_levels") else 0.55,
            "privacy": _lesson_privacy_contract(include_private_excerpts=include_private_excerpts),
            "point_of_use_surface": "state/prompt_ledger/views/adoption_posture.json",
            "owner_surface_candidates": [
                "codex/standards/std_prompt_ledger.json",
                "Task Ledger",
                "standard",
                "skill",
                "paper_module",
            ],
            "proposed_action": "index in Prompt Ledger adoption posture, then verify and bind to the selected owner surface before mutation",
            "required_type_a_verification": [
                "confirm the lesson recurs beyond this thread or is high severity",
                "choose the existing WorkItem, prompt outbox, skill, standard, or paper module before mutation",
                "preserve raw operator voice only through governed raw-seed lanes",
            ],
            "do_not_assimilate_risks": [
                "single-thread novelty",
                "model hallucination inside Type B response",
                "raw private transcript text leaking into tracked surfaces",
            ],
        }
        if include_private_excerpts:
            candidate["evidence_private_excerpt"] = prompt.get("short_title_or_excerpt")
        candidate_rows.append(candidate)
    return {
        "schema_version": LESSON_CANDIDATES_SCHEMA_VERSION,
        "thread_id": thread_id,
        "status": "advisory_only",
        "mutation_allowed": False,
        "privacy": _lesson_privacy_contract(include_private_excerpts=include_private_excerpts),
        "route_contract": _lesson_route_contract(),
        "source": {
            "thread_path": _display_path(_thread_path(thread_id)),
            "conversation_id": record.get("conversation_id"),
            "labels": record.get("labels") or [],
            "turn_count": record.get("turn_count") or 0,
            "thread_prompt_count": len(prompts),
            "content_hashes": {
                "transcript_sha16": (record.get("content_hashes") or {}).get("transcript_sha16"),
                "suffix_sha16": (record.get("content_hashes") or {}).get("suffix_sha16"),
            },
        },
        "why_interesting": sorted(prompt_labels | labels),
        "suggested_routes": sorted(set(suggested_routes)),
        "candidates": candidate_rows,
    }


def build_lesson_candidate_index(*, include_private_excerpts: bool = False) -> dict[str, Any]:
    packets = [
        packet
        for packet in (
            build_lesson_candidate_packet(
                str(record.get("thread_id") or ""),
                include_private_excerpts=include_private_excerpts,
            )
            for record in _all_thread_records()
            if record.get("thread_id")
        )
        if packet.get("candidates")
    ]
    return {
        "schema_version": LESSON_CANDIDATE_INDEX_SCHEMA_VERSION,
        "source_root": _display_path(THREAD_MEMORY_ROOT),
        "payload_policy": "metadata_only" if not include_private_excerpts else "explicit_private_excerpt",
        "raw_text_stored": False,
        "private_excerpt_included": bool(include_private_excerpts),
        "route_contract": _lesson_route_contract(),
        "packet_count": len(packets),
        "candidate_count": sum(len(packet.get("candidates") or []) for packet in packets),
        "packets": packets,
    }


def _forbidden_payload_key_paths(value: Any, *, path: str = "$") -> list[str]:
    findings: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}"
            if str(key) in PRIVATE_PAYLOAD_KEYS:
                findings.append(child_path)
            findings.extend(_forbidden_payload_key_paths(child, path=child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            findings.extend(_forbidden_payload_key_paths(child, path=f"{path}[{index}]"))
    return findings


def check_privacy_boundary() -> dict[str, Any]:
    index_payload = load_thread_index()
    candidate_index = build_lesson_candidate_index(include_private_excerpts=False)
    progress_index = build_thread_progress_index(limit=50, recent_limit=3, include_private_previews=False)
    index_findings = _forbidden_payload_key_paths(index_payload)
    candidate_findings = _forbidden_payload_key_paths(candidate_index)
    progress_findings = _forbidden_payload_key_paths(progress_index)
    threads = index_payload.get("threads") if isinstance(index_payload.get("threads"), list) else []
    return {
        "ok": not index_findings and not candidate_findings and not progress_findings,
        "schema_version": "operator_thread_memory_privacy_check_v1",
        "thread_index_payload_policy": index_payload.get("payload_policy", "metadata_only"),
        "thread_index_raw_text_present": bool(index_payload.get("raw_text_present")),
        "thread_count": len(threads),
        "lesson_candidate_count": candidate_index.get("candidate_count", 0),
        "lesson_candidate_payload_policy": candidate_index.get("payload_policy"),
        "thread_progress_count": progress_index.get("thread_count", 0),
        "thread_progress_payload_policy": progress_index.get("payload_policy"),
        "private_payload_key_findings": {
            "thread_index": index_findings,
            "lesson_candidates": candidate_findings,
            "thread_progress": progress_findings,
        },
        "route_contract": _lesson_route_contract(),
    }


def _main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect private Operator Thread Memory projections.")
    parser.add_argument("--index", action="store_true", help="print the metadata-only thread index")
    parser.add_argument("--project", action="store_true", help="rebuild projections from events.jsonl")
    parser.add_argument("--search", help="search private thread records")
    parser.add_argument("--thread", help="thread id for thread-specific commands")
    parser.add_argument(
        "--lesson-candidates",
        action="store_true",
        help="emit advisory lesson candidates; metadata-only index unless --thread is provided",
    )
    parser.add_argument(
        "--include-private-excerpts",
        action="store_true",
        help="include private prompt excerpts for --thread --lesson-candidates explicit inspection",
    )
    parser.add_argument(
        "--turn-projection",
        action="store_true",
        help="emit private turn-stack/response-skeleton projection for --thread",
    )
    parser.add_argument(
        "--continuation-card",
        action="store_true",
        help="emit compact metadata-only continuation card for --thread",
    )
    parser.add_argument(
        "--type-b-handoff-packet",
        action="store_true",
        help="emit a Type B-safe handoff packet rendered from the continuation card for --thread",
    )
    parser.add_argument(
        "--thread-progress",
        action="store_true",
        help="emit per-thread operator-addition/assistant-response progression; all recent threads unless --thread is supplied",
    )
    parser.add_argument(
        "--write-progress",
        action="store_true",
        help="write metadata-only thread progress JSON and markdown under state/operator_bridge/thread_memory",
    )
    parser.add_argument(
        "--retention-status",
        action="store_true",
        help="emit metadata-only retention/storage status; does not read private event bodies",
    )
    parser.add_argument(
        "--progress-format",
        choices=("json", "markdown"),
        default="json",
        help="output format for --thread-progress",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="max threads for --thread-progress without --thread",
    )
    parser.add_argument(
        "--recent-limit",
        type=int,
        default=3,
        help="max recent operator turns per thread for --thread-progress; 0 means all turns for one thread",
    )
    parser.add_argument(
        "--packet-format",
        choices=("json", "markdown"),
        default="json",
        help="output format for --type-b-handoff-packet",
    )
    parser.add_argument(
        "--include-private-previews",
        action="store_true",
        help="include private projection previews for --thread --turn-projection or --thread-progress explicit inspection",
    )
    parser.add_argument("--check", action="store_true", help="validate metadata-only index and lesson-candidate privacy boundaries")
    args = parser.parse_args(argv)

    if args.include_private_excerpts and not args.thread:
        raise SystemExit("--include-private-excerpts requires --thread")
    if args.include_private_previews and not args.thread:
        raise SystemExit("--include-private-previews requires --thread")
    if args.write_progress and args.include_private_previews:
        raise SystemExit("--write-progress refuses --include-private-previews")
    if args.retention_status:
        print(json.dumps(build_retention_status(), indent=2, sort_keys=True))
        return 0
    if args.project:
        print(json.dumps(project_thread_records(), indent=2, sort_keys=True))
        return 0
    if args.index:
        print(json.dumps(load_thread_index(), indent=2, sort_keys=True))
        return 0
    if args.check:
        result = check_privacy_boundary()
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["ok"] else 1
    if args.search:
        print(json.dumps(search_threads(args.search), indent=2, sort_keys=True))
        return 0
    if args.turn_projection:
        if not args.thread:
            raise SystemExit("--turn-projection requires --thread")
        record = load_thread(args.thread)
        if not record:
            print(json.dumps({
                "schema_version": "operator_thread_turn_projection_packet_v0",
                "thread_id": args.thread,
                "status": "missing",
                "mutation_allowed": False,
            }, indent=2, sort_keys=True))
            return 1
        projection = (
            turn_projection_mod.build_thread_turn_projections(
                record.get("turns") or [],
                include_private_previews=args.include_private_previews,
            )
            if turn_projection_mod is not None
            else _build_semantic_turn_projections(record.get("turns") or [])
        )
        print(json.dumps({
            "schema_version": "operator_thread_turn_projection_packet_v0",
            "thread_id": args.thread,
            "status": "available",
            "mutation_allowed": False,
            "thread_path": _display_path(_thread_path(args.thread)),
            "payload_policy": (
                "explicit_private_preview" if args.include_private_previews else "metadata_only"
            ),
            **projection,
        }, indent=2, sort_keys=True))
        return 0
    if args.continuation_card:
        if not args.thread:
            raise SystemExit("--continuation-card requires --thread")
        card = build_thread_continuation_card(args.thread)
        print(json.dumps(card, indent=2, sort_keys=True))
        return 0 if card.get("status") != "missing" else 1
    if args.type_b_handoff_packet:
        if not args.thread:
            raise SystemExit("--type-b-handoff-packet requires --thread")
        packet = build_type_b_handoff_packet(args.thread)
        if args.packet_format == "markdown":
            print(render_type_b_handoff_markdown(packet), end="")
        else:
            print(json.dumps(packet, indent=2, sort_keys=True))
        return 0 if packet.get("status") != "missing_thread" else 1
    if args.thread_progress or args.write_progress:
        if args.thread:
            payload = build_thread_progress(
                args.thread,
                recent_limit=args.recent_limit,
                include_private_previews=args.include_private_previews,
            )
            exit_code = 0 if payload.get("status") != "missing" else 1
        else:
            payload = build_thread_progress_index(
                limit=args.limit,
                recent_limit=args.recent_limit,
                include_private_previews=False,
            )
            exit_code = 0
        if args.write_progress:
            paths = write_thread_progress_projection(payload)
            print(json.dumps({
                "ok": True,
                "schema_version": "operator_thread_progress_write_receipt_v0",
                **paths,
            }, indent=2, sort_keys=True))
            return exit_code
        if args.progress_format == "markdown":
            print(render_thread_progress_markdown(payload), end="")
        else:
            print(json.dumps(payload, indent=2, sort_keys=True))
        return exit_code
    if args.lesson_candidates:
        if args.thread:
            print(json.dumps(
                build_lesson_candidate_packet(
                    args.thread,
                    include_private_excerpts=args.include_private_excerpts,
                ),
                indent=2,
                sort_keys=True,
            ))
        else:
            print(json.dumps(build_lesson_candidate_index(), indent=2, sort_keys=True))
        return 0
    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(_main())
