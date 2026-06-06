"""
[PURPOSE]
- Teleology: Own the Task Ledger WorkItem event stream, deterministic
  projections, and validation rules for intended work.
- Mechanism: Append JSONL events under state/task_ledger/events.jsonl,
  preserve legacy task rows losslessly, validate disk-grounded integration
  contracts, and rebuild ledger/sign-off/view projections.
- Non-goal: Runtime session and path-claim ownership. That stays in the
  Work Ledger substrate and is referenced from WorkItem events.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import threading
import uuid
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, Iterator, List, Mapping, Optional, Sequence, Set

from system.lib import strict_json

try:
    import fcntl
except ImportError:  # pragma: no cover - non-posix fallback
    fcntl = None  # type: ignore[assignment]


_FILE_LOCK_LOCAL = threading.local()


TASK_LEDGER_ROOT_REL = Path("state/task_ledger")
EVENTS_REL = TASK_LEDGER_ROOT_REL / "events.jsonl"
EVENTS_AUDIT_REL = TASK_LEDGER_ROOT_REL / "events_audit.jsonl"
LOCK_REL = TASK_LEDGER_ROOT_REL / ".task_ledger.lock"
LEDGER_REL = TASK_LEDGER_ROOT_REL / "ledger.json"
SIGNOFFS_REL = TASK_LEDGER_ROOT_REL / "sign_offs.json"
PROJECTION_MANIFEST_REL = TASK_LEDGER_ROOT_REL / "projection_manifest.json"
VIEWS_REL = TASK_LEDGER_ROOT_REL / "views"
DISCOVERY_RECEIPTS_REL = TASK_LEDGER_ROOT_REL / "discovery_receipts"
TASK_LEDGER_INTAKE_ROOT_REL = Path("state/task_ledger_intake")
TASK_LEDGER_INTAKE_PENDING_REL = TASK_LEDGER_INTAKE_ROOT_REL / "pending"
TASK_LEDGER_INTAKE_APPLIED_REL = TASK_LEDGER_INTAKE_ROOT_REL / "applied"
TASK_LEDGER_INTAKE_BLOCKED_REL = TASK_LEDGER_INTAKE_ROOT_REL / "blocked"
WORK_LEDGER_RUNTIME_REL = Path("state/work_ledger/runtime_status.json")
MISSION_BLACKBOARD_REL = Path("state/mission_blackboard/board.json")
PROMPT_LEDGER_MISSION_TRACE_CURRENT_STATE_REL = Path(
    "state/prompt_ledger/views/mission_trace_current_state.json"
)
PROJECTION_MANIFEST_SOURCE_INPUT_RELS = (MISSION_BLACKBOARD_REL,)
PROJECTION_MANIFEST_SOURCE_INPUT_DEPENDENTS = {
    str(MISSION_BLACKBOARD_REL): (
        VIEWS_REL / "mission_operating_picture.json",
        VIEWS_REL / "cap_census.json",
        VIEWS_REL / "cap_cartography.json",
    ),
}
RAW_SEED_PRINCIPLES_REL = Path(
    "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed/raw_seed_principles.json"
)

TASK_LEDGER_EVENT_SCHEMA = "task_ledger_event_v1"
TASK_LEDGER_PROJECTION_SCHEMA = "task_ledger_v2"
TASK_SIGNOFF_PROJECTION_SCHEMA = "task_sign_off_ledger_v2"
TASK_LEDGER_PROJECTION_MANIFEST_SCHEMA = "task_ledger_projection_manifest_v0"
TASK_LEDGER_INTAKE_REQUEST_SCHEMA = "task_ledger_intake_request_v0"
OPERATOR_AUTHORIZATION_POLICY_SCHEMA = "operator_authorization_policy_v1"
TASK_LEDGER_REBUILD_COMMAND = "./repo-python tools/meta/factory/task_ledger_apply.py rebuild"
TASK_LEDGER_REBUILD_CHECK_COMMAND = "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check"
TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --status-only --quiet-progress"
)
TASK_LEDGER_REBUILD_QUIET_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --quiet-progress"
)
TASK_LEDGER_REBUILD_CHECK_QUIET_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py rebuild --check --quiet-progress"
)
TASK_LEDGER_DRAIN_DEFERRED_REBUILD_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1"
)
TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py drain-deferred-rebuilds --limit 1 --quiet-progress"
)
TaskLedgerProgressCallback = Callable[[Mapping[str, Any]], None]
TASK_LEDGER_MIN_FREE_BYTES_ENV = "AIW_TASK_LEDGER_MIN_FREE_BYTES"
TASK_LEDGER_MIN_FREE_BYTES_DEFAULT = 512 * 1024 * 1024
TASK_LEDGER_WRITE_ESTIMATE_FLOOR_BYTES = 64 * 1024 * 1024
TASK_LEDGER_WRITE_AMPLIFICATION = 3
TASK_LEDGER_AUTHORITY_STORAGE_SCHEMA = "task_ledger_authority_storage_pressure_v0"
TASK_LEDGER_EVENTS_MONOLITH_ATTENTION_BYTES_ENV = "AIW_TASK_LEDGER_EVENTS_MONOLITH_ATTENTION_BYTES"
TASK_LEDGER_EVENTS_MONOLITH_CRITICAL_BYTES_ENV = "AIW_TASK_LEDGER_EVENTS_MONOLITH_CRITICAL_BYTES"
TASK_LEDGER_AUTHORITY_TOTAL_ATTENTION_BYTES_ENV = "AIW_TASK_LEDGER_AUTHORITY_TOTAL_ATTENTION_BYTES"
TASK_LEDGER_AUTHORITY_TOTAL_CRITICAL_BYTES_ENV = "AIW_TASK_LEDGER_AUTHORITY_TOTAL_CRITICAL_BYTES"
TASK_LEDGER_ALLOW_MONOLITH_APPEND_ENV = "AIW_TASK_LEDGER_ALLOW_MONOLITH_APPEND"
TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES_ENV = "AIW_TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES"
TASK_LEDGER_EVENTS_MONOLITH_ATTENTION_BYTES_DEFAULT = 32 * 1024 * 1024
TASK_LEDGER_EVENTS_MONOLITH_CRITICAL_BYTES_DEFAULT = 40 * 1024 * 1024
TASK_LEDGER_AUTHORITY_TOTAL_ATTENTION_BYTES_DEFAULT = 64 * 1024 * 1024
TASK_LEDGER_AUTHORITY_TOTAL_CRITICAL_BYTES_DEFAULT = 96 * 1024 * 1024
TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES_DEFAULT = 8 * 1024 * 1024
TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL = TASK_LEDGER_ROOT_REL / "events"
TASK_LEDGER_AUTHORITY_SEGMENTS_REL = TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL / "segments"
TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL = TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL / "open" / "current.jsonl"
TASK_LEDGER_AUTHORITY_MANIFEST_REL = TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL / "manifest.json"
TASK_LEDGER_AUTHORITY_AUDIT_SEGMENTS_REL = TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL / "audit_segments"
TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL = (
    TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL / "audit_open" / "current.jsonl"
)
TASK_LEDGER_AUTHORITY_MANIFEST_SCHEMA = "task_ledger_authority_segment_manifest_v0"
TASK_LEDGER_AUTHORITY_MODE_LEGACY = "legacy_monolith"
TASK_LEDGER_AUTHORITY_MODE_PREPARED = "prepared_segmented"
TASK_LEDGER_AUTHORITY_MODE_ACTIVE = "active_segmented"
TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID = "valid"
TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_STALE = "stale"
TASK_LEDGER_AUTHORITY_MIGRATION_PLAN_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py authority-migration-plan"
)
TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py authority-migration-apply"
)
TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_COMMAND = (
    "./repo-python tools/meta/factory/task_ledger_apply.py authority-export-compatibility"
)
_JSONL_EVENT_ID_FIELD_RE = re.compile(rb'"event_id"\s*:\s*"((?:\\.|[^"\\])*)"')
_JSONL_EVENT_HASH_FIELD_RE = re.compile(rb'"event_hash"\s*:\s*"((?:\\.|[^"\\])*)"')


def _emit_progress(
    progress_callback: TaskLedgerProgressCallback | None,
    event: str,
    **fields: Any,
) -> None:
    if progress_callback is None:
        return
    payload: Dict[str, Any] = {
        "schema": "task_ledger_mutation_progress_v0",
        "surface": "task_ledger_events",
        "event": event,
        "privacy": "phase_names_counts_and_status_only_no_event_payloads",
    }
    payload.update(fields)
    progress_callback(payload)


def _projection_rebuild_priority(comparison: Mapping[str, Any] | None) -> Dict[str, Any]:
    delta = comparison.get("delta") if isinstance(comparison, Mapping) else None
    if isinstance(delta, int) and delta > 0:
        if delta <= 5:
            return {
                "schema": "task_ledger_projection_rebuild_priority_v0",
                "status": "low_active_authority_delta",
                "delta_event_count": delta,
                "threshold": 5,
                "recommended_action": (
                    "continue_with_authority_visible_receipts_unless_projection_or_card_visibility_is_required"
                ),
                "full_rebuild_required_for": [
                    "card_visibility",
                    "generated_view_freshness",
                    "operator_requested_projection_refresh",
                ],
                "authority_only_closeout_ok": True,
            }
        if delta <= 50:
            return {
                "schema": "task_ledger_projection_rebuild_priority_v0",
                "status": "medium_authority_delta",
                "delta_event_count": delta,
                "threshold": 50,
                "recommended_action": "run_owner_rebuild_when_projection_visibility_matters",
                "authority_only_closeout_ok": False,
            }
        return {
            "schema": "task_ledger_projection_rebuild_priority_v0",
            "status": "high_authority_delta",
            "delta_event_count": delta,
            "threshold": 50,
            "recommended_action": "run_owner_rebuild_or_drain_deferred_rebuild",
            "authority_only_closeout_ok": False,
        }
    return {
        "schema": "task_ledger_projection_rebuild_priority_v0",
        "status": "unknown_delta",
        "delta_event_count": delta,
        "recommended_action": "use_owner_rebuild_or_drain_route_before_trusting_generated_views",
        "authority_only_closeout_ok": False,
    }


def _projection_check_payload(
    mismatches: Sequence[str],
    *,
    projection_event_count: int | None = None,
    authority_event_count: int | None = None,
) -> Dict[str, Any]:
    mismatch_list = [str(path) for path in mismatches]
    comparison: Dict[str, Any] | None = None
    mismatch_status = "projection_rebuild_required"
    if projection_event_count is not None or authority_event_count is not None:
        delta = None
        comparison_status = "unknown"
        if projection_event_count is not None and authority_event_count is not None:
            delta = authority_event_count - projection_event_count
            if delta > 0:
                comparison_status = "projection_behind_authority"
                mismatch_status = comparison_status
            elif delta < 0:
                comparison_status = "projection_ahead_of_authority"
            else:
                comparison_status = "event_counts_match"
        comparison = {
            "schema": "task_ledger_projection_event_count_comparison_v0",
            "projection_event_count": projection_event_count,
            "authority_event_count": authority_event_count,
            "delta": delta,
            "status": comparison_status,
        }
    payload: Dict[str, Any] = {
        "ok": not mismatch_list,
        "checked": True,
        "status": "clean" if not mismatch_list else mismatch_status,
        "mismatches": mismatch_list,
        "mismatch_count": len(mismatch_list),
    }
    if comparison is not None:
        payload["event_count_comparison"] = comparison
    if mismatch_list:
        if mismatch_status == "projection_behind_authority":
            rebuild_priority = _projection_rebuild_priority(comparison)
            payload.update(
                {
                    "rebuild_priority": rebuild_priority,
                    "reason": (
                        "Task Ledger authority has newer events than the current deterministic "
                        "projection. This is normal under concurrent writers and should be "
                        "settled with the owner rebuild route, not treated as projector drift."
                    ),
                    "next_step": (
                        "Task Ledger deterministic projections are behind the authority log; "
                        "use the compact check/drain lane first, then run the full owner "
                        "rebuild route only when the projection-builder lane is admitted."
                    ),
                    "next_command": TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND,
                    "safe_next_command": TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND,
                    "verification_command": TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND,
                    "owner_route": TASK_LEDGER_REBUILD_COMMAND,
                    "full_rebuild_command": TASK_LEDGER_REBUILD_QUIET_COMMAND,
                    "deferred_rebuild_command": TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND,
                }
            )
            return payload
        payload.update(
            {
                "next_step": (
                    "Task Ledger deterministic projections are stale; run the owner rebuild "
                    "route before trusting generated views."
                ),
                "next_command": TASK_LEDGER_REBUILD_QUIET_COMMAND,
                "safe_next_command": TASK_LEDGER_REBUILD_QUIET_COMMAND,
                "verification_command": TASK_LEDGER_REBUILD_CHECK_QUIET_COMMAND,
                "owner_route": TASK_LEDGER_REBUILD_COMMAND,
            }
        )
    else:
        payload.update(
            {
                "next_step": "Task Ledger deterministic projections match event authority.",
                "verification_command": TASK_LEDGER_REBUILD_CHECK_QUIET_COMMAND,
            }
        )
    return payload


def _file_sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _projection_target_metadata(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "size_bytes": None,
            "mtime_ns": None,
            "ctime_ns": None,
        }
    if not path.is_file():
        return {
            "exists": True,
            "size_bytes": None,
            "mtime_ns": None,
            "ctime_ns": None,
        }
    stat = path.stat()
    return {
        "exists": True,
        "size_bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "ctime_ns": stat.st_ctime_ns,
    }


def _projection_manifest_source_input_hashes(repo_root: Path) -> Dict[str, str | None]:
    return {
        str(rel_path): _file_sha256(repo_root / rel_path)
        for rel_path in PROJECTION_MANIFEST_SOURCE_INPUT_RELS
    }


def _projection_manifest_source_input_metadata(repo_root: Path) -> Dict[str, Dict[str, Any]]:
    return {
        str(rel_path): _projection_target_metadata(repo_root / rel_path)
        for rel_path in PROJECTION_MANIFEST_SOURCE_INPUT_RELS
    }


def _projection_manifest_source_input_dependent_paths(source_inputs: Sequence[str]) -> List[str]:
    paths: List[str] = []
    for source_input in source_inputs:
        for rel_path in PROJECTION_MANIFEST_SOURCE_INPUT_DEPENDENTS.get(source_input, ()):
            text = str(rel_path)
            if text not in paths:
                paths.append(text)
    return paths or list(source_inputs)


def _projection_manifest_payload(
    repo_root: Path,
    targets: Mapping[Path, Mapping[str, Any]],
    *,
    authority_event_count: int,
    authority_tail_hash: str | None,
) -> Dict[str, Any]:
    target_hashes: List[Dict[str, Any]] = []
    for rel_path in sorted(targets, key=lambda path: str(path)):
        path = repo_root / rel_path
        metadata = _projection_target_metadata(path)
        target_hashes.append(
            {
                "path": str(rel_path),
                **metadata,
                "sha256": _file_sha256(path),
            }
        )
    return {
        "kind": "task_ledger_projection_manifest",
        "schema_version": TASK_LEDGER_PROJECTION_MANIFEST_SCHEMA,
        "generated_at": utc_now(),
        "authority_event_count": int(authority_event_count),
        "authority_tail_hash": authority_tail_hash,
        "source_input_hashes": _projection_manifest_source_input_hashes(repo_root),
        "source_input_metadata": _projection_manifest_source_input_metadata(repo_root),
        "target_count": len(target_hashes),
        "target_hashes": target_hashes,
        "projection_paths": [row["path"] for row in target_hashes],
    }


def _write_projection_manifest(
    repo_root: Path,
    targets: Mapping[Path, Mapping[str, Any]],
    *,
    authority_event_count: int,
    authority_tail_hash: str | None,
) -> Dict[str, Any]:
    manifest = _projection_manifest_payload(
        repo_root,
        targets,
        authority_event_count=authority_event_count,
        authority_tail_hash=authority_tail_hash,
    )
    atomic_write_json(repo_root / PROJECTION_MANIFEST_REL, manifest)
    return manifest


def _projection_manifest_fast_check(
    repo_root: Path,
    *,
    authority_event_count: int,
    authority_tail_hash: str | None,
) -> Dict[str, Any] | None:
    manifest_path = repo_root / PROJECTION_MANIFEST_REL
    manifest = _safe_read_json(manifest_path)
    if manifest.get("schema_version") != TASK_LEDGER_PROJECTION_MANIFEST_SCHEMA:
        return None
    projection_event_count = _optional_int(manifest.get("authority_event_count"))
    manifest_tail_hash = str(manifest.get("authority_tail_hash") or "").strip() or None
    target_rows = manifest.get("target_hashes")
    if not isinstance(target_rows, list):
        return None
    mismatches: List[str] = []
    authority_event_count_matches = projection_event_count == authority_event_count
    authority_tail_hash_matches = manifest_tail_hash == authority_tail_hash
    if not authority_event_count_matches or not authority_tail_hash_matches:
        mismatches.append(str(LEDGER_REL))
        payload = _projection_check_payload(
            sorted(set(mismatches)),
            projection_event_count=projection_event_count,
            authority_event_count=authority_event_count,
        )
        payload["projection_manifest_check"] = {
            "schema": "task_ledger_projection_manifest_check_v0",
            "status": "used",
            "manifest_path": str(PROJECTION_MANIFEST_REL),
            "target_count": len(target_rows),
            "target_hashes_checked": 0,
            "target_hash_check_skipped_reason": "authority_log_mismatch",
            "authority_tail_hash_matches": authority_tail_hash_matches,
            "authority_event_count_matches": authority_event_count_matches,
            "full_rebuild_skipped": False,
        }
        return payload
    manifest_source_hashes = manifest.get("source_input_hashes")
    if not isinstance(manifest_source_hashes, Mapping):
        return None
    manifest_source_metadata = (
        manifest.get("source_input_metadata")
        if isinstance(manifest.get("source_input_metadata"), Mapping)
        else {}
    )
    current_source_hashes: Dict[str, str | None] = {}
    source_input_metadata_checked = 0
    source_input_hashes_checked = 0
    source_input_hashes_skipped_by_metadata = 0
    for rel_path in PROJECTION_MANIFEST_SOURCE_INPUT_RELS:
        rel_text = str(rel_path)
        expected_metadata = manifest_source_metadata.get(rel_text)
        if isinstance(expected_metadata, Mapping):
            source_input_metadata_checked += 1
            if _projection_target_metadata(repo_root / rel_path) == dict(expected_metadata):
                current_source_hashes[rel_text] = manifest_source_hashes.get(rel_text)
                source_input_hashes_skipped_by_metadata += 1
                continue
        current_source_hashes[rel_text] = _file_sha256(repo_root / rel_path)
        source_input_hashes_checked += 1
    source_input_mismatches = sorted(
        rel_path
        for rel_path, current_hash in current_source_hashes.items()
        if manifest_source_hashes.get(rel_path) != current_hash
    )
    if source_input_mismatches:
        payload = _projection_check_payload(
            _projection_manifest_source_input_dependent_paths(source_input_mismatches),
            projection_event_count=projection_event_count,
            authority_event_count=authority_event_count,
        )
        payload["reason"] = "projection_source_input_mismatch"
        payload["source_input_mismatches"] = source_input_mismatches
        payload["projection_manifest_check"] = {
            "schema": "task_ledger_projection_manifest_check_v0",
            "status": "used",
            "manifest_path": str(PROJECTION_MANIFEST_REL),
            "target_count": len(target_rows),
            "target_hashes_checked": 0,
            "target_hash_check_skipped_reason": "source_input_mismatch",
            "source_input_metadata_checked": source_input_metadata_checked,
            "source_input_hashes_checked": source_input_hashes_checked,
            "source_input_hashes_skipped_by_metadata": source_input_hashes_skipped_by_metadata,
            "source_input_mismatch_count": len(source_input_mismatches),
            "source_input_mismatches": source_input_mismatches,
            "full_rebuild_skipped": False,
        }
        return payload
    target_metadata_checked = 0
    target_hashes_checked = 0
    target_hashes_skipped_by_metadata = 0
    for row in target_rows:
        if not isinstance(row, Mapping):
            return None
        rel_text = str(row.get("path") or "").strip()
        if not rel_text:
            return None
        path = repo_root / rel_text
        expected_metadata = {
            "exists": row.get("exists"),
            "size_bytes": row.get("size_bytes"),
            "mtime_ns": row.get("mtime_ns"),
            "ctime_ns": row.get("ctime_ns"),
        }
        if all(key in row for key in expected_metadata):
            target_metadata_checked += 1
            if _projection_target_metadata(path) == expected_metadata:
                target_hashes_skipped_by_metadata += 1
                continue
        expected = str(row.get("sha256") or "").strip() or None
        target_hashes_checked += 1
        current = _file_sha256(path)
        if current != expected:
            mismatches.append(rel_text)
    payload = _projection_check_payload(
        sorted(set(mismatches)),
        projection_event_count=projection_event_count,
        authority_event_count=authority_event_count,
    )
    payload["projection_manifest_check"] = {
        "schema": "task_ledger_projection_manifest_check_v0",
        "status": "used",
        "manifest_path": str(PROJECTION_MANIFEST_REL),
        "target_count": len(target_rows),
        "target_metadata_checked": target_metadata_checked,
        "target_hashes_checked": target_hashes_checked,
        "target_hashes_skipped_by_metadata": target_hashes_skipped_by_metadata,
        "target_hash_check_mode": "metadata_then_hash",
        "source_input_metadata_checked": source_input_metadata_checked,
        "source_input_hashes_checked": source_input_hashes_checked,
        "source_input_hashes_skipped_by_metadata": source_input_hashes_skipped_by_metadata,
        "authority_tail_hash_matches": manifest_tail_hash == authority_tail_hash,
        "authority_event_count_matches": projection_event_count == authority_event_count,
        "full_rebuild_skipped": not mismatches,
    }
    return payload


def _optional_int(value: object) -> int | None:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None


def _existing_parent(path: Path) -> Path:
    cursor = path
    while not cursor.exists() and cursor != cursor.parent:
        cursor = cursor.parent
    return cursor


def _configured_min_free_bytes() -> int:
    raw = os.environ.get(TASK_LEDGER_MIN_FREE_BYTES_ENV)
    if not raw:
        return TASK_LEDGER_MIN_FREE_BYTES_DEFAULT
    try:
        return max(0, int(raw))
    except ValueError:
        return TASK_LEDGER_MIN_FREE_BYTES_DEFAULT


def _configured_nonnegative_bytes(env_var: str, default: int) -> int:
    raw = os.environ.get(env_var)
    if not raw:
        return default
    try:
        return max(0, int(raw))
    except ValueError:
        return default


def _human_bytes(value: int | None) -> str | None:
    if value is None:
        return None
    amount = float(max(0, int(value)))
    units = ("bytes", "KiB", "MiB", "GiB", "TiB")
    unit = units[0]
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            break
        amount /= 1024
    if unit == "bytes":
        return f"{int(amount)} bytes"
    return f"{amount:.2f} {unit}"


def _rel_path_size(repo_root: Path, rel_path: Path) -> int:
    path = repo_root / rel_path
    if not path.exists():
        return 0
    if path.is_file():
        try:
            return int(path.stat().st_size)
        except OSError:
            return 0
    total = 0
    for child in path.rglob("*"):
        if child.is_file():
            try:
                total += int(child.stat().st_size)
            except OSError:
                continue
    return total


def _current_projection_rel_paths(repo_root: Path) -> list[Path]:
    rel_paths = [LEDGER_REL, SIGNOFFS_REL]
    views_root = repo_root / VIEWS_REL
    if views_root.exists():
        for path in sorted(views_root.glob("*.json")):
            try:
                rel_paths.append(path.relative_to(repo_root))
            except ValueError:
                rel_paths.append(VIEWS_REL / path.name)
    return rel_paths


def task_ledger_authority_storage_status(repo_root: Path) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    storage_state = task_ledger_authority_storage_state(repo_root)
    authority_mode = str(storage_state.get("mode") or TASK_LEDGER_AUTHORITY_MODE_LEGACY)
    active_segmented = authority_mode == TASK_LEDGER_AUTHORITY_MODE_ACTIVE
    event_bytes = _rel_path_size(repo_root, EVENTS_REL)
    audit_bytes = _rel_path_size(repo_root, EVENTS_AUDIT_REL)
    hot_event_rel = TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL if active_segmented else EVENTS_REL
    hot_audit_rel = TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL if active_segmented else EVENTS_AUDIT_REL
    hot_event_bytes = _rel_path_size(repo_root, hot_event_rel)
    hot_audit_bytes = _rel_path_size(repo_root, hot_audit_rel)
    projection_bytes = _rel_path_size(repo_root, LEDGER_REL)
    views_bytes = _rel_path_size(repo_root, VIEWS_REL)
    authority_bytes = hot_event_bytes + hot_audit_bytes
    attention_event_bytes = _configured_nonnegative_bytes(
        TASK_LEDGER_EVENTS_MONOLITH_ATTENTION_BYTES_ENV,
        TASK_LEDGER_EVENTS_MONOLITH_ATTENTION_BYTES_DEFAULT,
    )
    critical_event_bytes = _configured_nonnegative_bytes(
        TASK_LEDGER_EVENTS_MONOLITH_CRITICAL_BYTES_ENV,
        TASK_LEDGER_EVENTS_MONOLITH_CRITICAL_BYTES_DEFAULT,
    )
    attention_total_bytes = _configured_nonnegative_bytes(
        TASK_LEDGER_AUTHORITY_TOTAL_ATTENTION_BYTES_ENV,
        TASK_LEDGER_AUTHORITY_TOTAL_ATTENTION_BYTES_DEFAULT,
    )
    critical_total_bytes = _configured_nonnegative_bytes(
        TASK_LEDGER_AUTHORITY_TOTAL_CRITICAL_BYTES_ENV,
        TASK_LEDGER_AUTHORITY_TOTAL_CRITICAL_BYTES_DEFAULT,
    )
    critical_reasons: list[str] = []
    attention_reasons: list[str] = []
    if hot_event_bytes >= critical_event_bytes:
        critical_reasons.append(
            "events_open_tail_critical" if active_segmented else "events_jsonl_monolith_critical"
        )
    elif hot_event_bytes >= attention_event_bytes:
        attention_reasons.append(
            "events_open_tail_attention" if active_segmented else "events_jsonl_monolith_attention"
        )
    if authority_bytes >= critical_total_bytes:
        critical_reasons.append("authority_total_critical")
    elif authority_bytes >= attention_total_bytes:
        attention_reasons.append("authority_total_attention")
    size_pressure_status = (
        "critical"
        if critical_reasons
        else "attention"
        if attention_reasons
        else "ok"
    )
    status = size_pressure_status
    reasons = list(critical_reasons if critical_reasons else attention_reasons)
    hard_block_reasons: list[str] = []
    authority_health_summary: Dict[str, Any] | None = None
    if critical_reasons:
        try:
            authority_health = _authority_health_unlocked(repo_root)
            authority_health_summary = {
                "schema": "task_ledger_authority_health_summary_v0",
                "status": authority_health.get("status"),
                "ok": bool(authority_health.get("ok")),
                "authority_event_count": authority_health.get("authority_event_count"),
                "audit_event_count": authority_health.get("audit_event_count"),
                "lost_count": authority_health.get("lost_count"),
                "lost_event_ids_preview": list(authority_health.get("lost_event_ids") or [])[:8],
                "next_step": authority_health.get("next_step"),
            }
        except Exception as exc:
            authority_health_summary = {
                "schema": "task_ledger_authority_health_summary_v0",
                "status": "authority_health_check_failed",
                "ok": False,
                "error_type": type(exc).__name__,
                "error_preview": str(exc)[:240],
            }
        if authority_health_summary.get("status") == "clean":
            status = "attention"
            reasons = [
                *critical_reasons,
                *attention_reasons,
                "critical_size_pressure_demoted_by_clean_authority",
            ]
        else:
            status = "critical"
            reasons = [
                *critical_reasons,
                *attention_reasons,
                "authority_not_clean_under_critical_size_pressure",
            ]
            hard_block_reasons.append(
                str(authority_health_summary.get("status") or "authority_not_clean")
            )
    override = os.environ.get(TASK_LEDGER_ALLOW_MONOLITH_APPEND_ENV) == "1"
    append_allowed = status != "critical" or override
    if append_allowed:
        write_admission = "append_allowed_with_storage_pressure_receipt" if status != "ok" else "append_allowed"
    else:
        write_admission = "blocked_rotate_or_migrate_authority_before_append"
    if append_allowed:
        next_step = (
            "Task Ledger append admitted with a storage pressure receipt; run "
            f"{TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --activate to move ordinary "
            "appends to segmented open-tail authority."
            if status != "ok"
            else "Task Ledger append admitted by current storage threshold."
        )
    else:
        recovery_step = (
            authority_health_summary.get("next_step")
            if isinstance(authority_health_summary, Mapping)
            else None
        )
        next_step = (
            str(recovery_step)
            if recovery_step
            else (
                f"Run {TASK_LEDGER_AUTHORITY_MIGRATION_PLAN_COMMAND} before ordinary appends, "
                f"then {TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --activate, "
                f"or set {TASK_LEDGER_ALLOW_MONOLITH_APPEND_ENV}=1 only for an explicitly "
                "authorized emergency append."
            )
        )
    return {
        "schema": TASK_LEDGER_AUTHORITY_STORAGE_SCHEMA,
        "status": status,
        "ok": append_allowed,
        "append_allowed": append_allowed,
        "override_active": override,
        "write_admission": write_admission,
        "storage_state": storage_state,
        "authority_mode": authority_mode,
        "active_segmented": active_segmented,
        "size_pressure_status": size_pressure_status,
        "reasons": reasons,
        "critical_reasons": critical_reasons,
        "attention_reasons": attention_reasons,
        "hard_block_reasons": hard_block_reasons,
        "authority_health": authority_health_summary,
        "events_path": str(hot_event_rel),
        "events_bytes": hot_event_bytes,
        "events_human": _human_bytes(hot_event_bytes),
        "audit_path": str(hot_audit_rel),
        "audit_bytes": hot_audit_bytes,
        "audit_human": _human_bytes(hot_audit_bytes),
        "compatibility_export_path": str(EVENTS_REL),
        "compatibility_export_bytes": event_bytes,
        "compatibility_export_human": _human_bytes(event_bytes),
        "compatibility_audit_export_path": str(EVENTS_AUDIT_REL),
        "compatibility_audit_export_bytes": audit_bytes,
        "compatibility_audit_export_human": _human_bytes(audit_bytes),
        "authority_bytes": authority_bytes,
        "authority_human": _human_bytes(authority_bytes),
        "projection_bytes": projection_bytes,
        "projection_human": _human_bytes(projection_bytes),
        "views_bytes": views_bytes,
        "views_human": _human_bytes(views_bytes),
        "thresholds": {
            "events_attention_bytes": attention_event_bytes,
            "events_attention_human": _human_bytes(attention_event_bytes),
            "events_critical_bytes": critical_event_bytes,
            "events_critical_human": _human_bytes(critical_event_bytes),
            "authority_total_attention_bytes": attention_total_bytes,
            "authority_total_attention_human": _human_bytes(attention_total_bytes),
            "authority_total_critical_bytes": critical_total_bytes,
            "authority_total_critical_human": _human_bytes(critical_total_bytes),
        },
        "target_storage_model": {
            "segments_dir": str(TASK_LEDGER_AUTHORITY_SEGMENTS_REL),
            "open_tail": str(TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL),
            "manifest": str(TASK_LEDGER_AUTHORITY_MANIFEST_REL),
            "compatibility_export": str(EVENTS_REL),
            "policy": (
                "immutable closed segments plus one small open tail; events.jsonl becomes "
                "a compatibility export or pointer after the migration lane lands"
            ),
            "dry_run_plan_command": TASK_LEDGER_AUTHORITY_MIGRATION_PLAN_COMMAND,
            "prepare_command": f"{TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --prepare",
            "activate_command": f"{TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --activate",
            "compatibility_export_command": TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_COMMAND,
        },
        "next_step": next_step,
    }


def task_ledger_disk_write_headroom(
    repo_root: Path,
    *,
    operation: str,
    rel_paths: Sequence[Path] | None = None,
    min_free_bytes: int | None = None,
) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    rel_path_list = list(rel_paths or [])
    usage_path = _existing_parent(repo_root / TASK_LEDGER_ROOT_REL)
    usage = shutil.disk_usage(str(usage_path))
    existing_bytes = sum(_rel_path_size(repo_root, rel_path) for rel_path in rel_path_list)
    configured_floor = (
        _configured_min_free_bytes() if min_free_bytes is None else max(0, int(min_free_bytes))
    )
    authority_storage = task_ledger_authority_storage_status(repo_root)
    authority_append_touches = any(
        rel_path == EVENTS_REL or rel_path == EVENTS_AUDIT_REL for rel_path in rel_path_list
    )
    required_bytes = max(
        configured_floor,
        TASK_LEDGER_WRITE_ESTIMATE_FLOOR_BYTES
        + (existing_bytes * TASK_LEDGER_WRITE_AMPLIFICATION),
    )
    disk_ok = int(usage.free) >= int(required_bytes)
    authority_ok = not authority_append_touches or bool(authority_storage.get("append_allowed"))
    status = "ok"
    if not disk_ok:
        status = "insufficient_disk_headroom"
    elif not authority_ok:
        status = "authority_storage_bloat"
    return {
        "schema": "task_ledger_disk_write_headroom_v0",
        "ok": disk_ok and authority_ok,
        "status": status,
        "operation": operation,
        "usage_path": str(usage_path),
        "free_bytes": int(usage.free),
        "required_bytes": int(required_bytes),
        "configured_min_free_bytes": int(configured_floor),
        "estimated_existing_write_bytes": int(existing_bytes),
        "write_amplification": TASK_LEDGER_WRITE_AMPLIFICATION,
        "checked_paths": [str(path) for path in rel_path_list],
        "authority_storage": authority_storage,
        "next_step": (
            authority_storage.get("next_step")
            if not authority_ok
            else
            "Free disposable scratch space or lower "
            f"{TASK_LEDGER_MIN_FREE_BYTES_ENV} only for an explicitly safe emergency write."
        ),
    }


def _emit_disk_headroom_blocked(
    progress_callback: TaskLedgerProgressCallback | None,
    headroom: Mapping[str, Any],
) -> None:
    _emit_progress(
        progress_callback,
        "disk_headroom_blocked",
        operation=headroom.get("operation"),
        status=headroom.get("status") or "insufficient_disk_headroom",
        free_bytes=headroom.get("free_bytes"),
        required_bytes=headroom.get("required_bytes"),
        usage_path=headroom.get("usage_path"),
    )


def _disk_headroom_block_result(headroom: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "ok": False,
        "checked": False,
        "status": headroom.get("status") or "insufficient_disk_headroom",
        "disk_headroom": dict(headroom),
        "authority_storage": dict(headroom.get("authority_storage") or {}),
        "next_step": headroom.get("next_step"),
    }

EVENT_ID_RE = re.compile(r"^wie_[A-Za-z0-9_:-]+$")

PATHLIKE_SURFACE_SUFFIXES = (
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".jsx",
    ".toml",
    ".yaml",
    ".yml",
    ".txt",
)

EVENT_TYPES = {
    "work_item.legacy_bootstrapped",
    "work_item.captured",
    "work_item.triaged",
    "work_item.promoted",
    "work_item.shaped",
    "work_item.split",
    "work_item.claimed",
    "work_item.released",
    "work_item.state_transitioned",
    "work_item.blocked",
    "work_item.unblocked",
    "work_item.note_added",
    "work_item.rerank_proposed",
    "work_item.rerank_committed",
    "work_item.integration_discovered",
    "work_item.satisfaction_linked",
    "work_item.execution_profile_set",
    "work_item.bridge_delegated",
    "work_item.provider_job_created",
    "work_item.provider_job_completed",
    "work_item.execution_receipt_recorded",
    "work_item.evidence_attached",
    "work_item.reviewed",
    "work_item.signoff_recorded",
    "work_item.propagation_recorded",
    "work_item.followup_captured",
    "work_item.retired",
    "work_item.projection_rescue_recorded",
    "work_item.schema_migrated",
}

PROPAGATION_NEEDED_RECOMMENDED_ACTION = (
    "inspect the owner surface, patch or verify the reusable lesson, then append "
    "work_item.propagation_recorded; use explicit nothing_to_refine only after owner inspection"
)

STANDING_PRIVATE_INTERNAL_AUTHORIZATION_REF = (
    "operator_standing_private_internal_authorization_2026_05_28"
)
PUBLIC_RELEASE_FRESH_AUTHORIZATION_REQUIRED = (
    "fresh_explicit_public_release_authorization_required"
)
PUBLIC_RELEASE_BOUNDARY_MARKERS = (
    "public release",
    "publication",
    "publish",
    "public github",
    "github push",
    "push to github",
    "pull request",
    "remote sync",
    "deploy",
    "github pages",
    "external dissemination",
    "social posting",
    "twitter",
    "recipient send",
    "send externally",
    "public demo",
    "public upload",
)
NON_STANDING_SAFETY_BOUNDARY_MARKERS = (
    "destructive",
    "irreversible",
    "secret",
    "credential",
    "private disclosure",
    "reset --hard",
    "delete production",
)


def _operator_authorization_boundary_kind(value: str) -> str:
    lowered = value.lower()
    if any(marker in lowered for marker in PUBLIC_RELEASE_BOUNDARY_MARKERS):
        return "public_release"
    if any(marker in lowered for marker in NON_STANDING_SAFETY_BOUNDARY_MARKERS):
        return "safety_or_irreversible"
    return "private_internal"


def _standing_operator_authorization_policy(
    *,
    boundary_kind: str = "private_internal",
    requires_operator_review: bool = False,
) -> Dict[str, Any]:
    authorization_blocks_execution = boundary_kind != "private_internal"
    if boundary_kind == "public_release":
        status = "public_release_requires_explicit_operator_authorization"
        reason = PUBLIC_RELEASE_FRESH_AUTHORIZATION_REQUIRED
    elif boundary_kind == "safety_or_irreversible":
        status = "specific_safety_authorization_required"
        reason = "destructive_irreversible_secret_or_disclosure_boundary"
    else:
        status = "standing_private_internal_authorization_satisfied"
        reason = STANDING_PRIVATE_INTERNAL_AUTHORIZATION_REF
    review_semantics = (
        "operator_attention_or_priority_review_not_permission_gate"
        if requires_operator_review and not authorization_blocks_execution
        else "not_a_review_row"
        if not requires_operator_review
        else "specific_authorization_boundary"
    )
    return {
        "schema_version": OPERATOR_AUTHORIZATION_POLICY_SCHEMA,
        "standing_private_internal_authorization": "authorized",
        "standing_private_internal_authorization_ref": STANDING_PRIVATE_INTERNAL_AUTHORIZATION_REF,
        "private_internal_default": "yes_when_safe_scoped_and_reversible",
        "internal_authorization": (
            "satisfied" if boundary_kind == "private_internal" else "not_sufficient_for_boundary"
        ),
        "public_release_authorization": "not_authorized_by_operator",
        "public_release_boundary": PUBLIC_RELEASE_FRESH_AUTHORIZATION_REQUIRED,
        "boundary_kind": boundary_kind,
        "operator_authorization_status": status,
        "authorization_blocks_execution": authorization_blocks_execution,
        "authorization_block_reason": reason if authorization_blocks_execution else None,
        "requires_operator_review": requires_operator_review,
        "operator_review_semantics": review_semantics,
        "standing_authorization_limits": [
            "no public push, deploy, release toggle, social post, external send, or public upload",
            "no destructive, irreversible, secret, or disclosure boundary without task-specific authority",
            "repo gates, scoped ownership, validation, dirty-tree isolation, and safety checks still apply",
        ],
    }

WORK_ITEM_STATE_FLOW = [
    "captured",
    "triaged",
    "shaping",
    "ready",
    "claimed",
    "active",
    "blocked",
    "review",
    "signoff",
    "propagated",
    "done",
    "retired",
]
WORK_ITEM_STATES = set(WORK_ITEM_STATE_FLOW)

LEGACY_STATUS_TO_STATE = {
    "proposed": "captured",
    "accepted": "ready",
    "active": "active",
    "blocked": "blocked",
    "completed": "done",
    "retired": "retired",
}


class TaskLedgerError(ValueError):
    """Raised for invalid Task Ledger event or projection state."""


class DuplicateJsonKeyError(TaskLedgerError):
    """Raised when strict JSON parsing sees the same object key twice."""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def mint_event_id(now: str | None = None) -> str:
    stamp = (now or utc_now()).replace("+00:00", "Z").replace("-", "").replace(":", "")
    return f"wie_{stamp}_{uuid.uuid4().hex[:8]}"


def loads_json_strict(text: str, *, source: str = "<json>") -> Any:
    try:
        return strict_json.loads_json_strict(text, source=source)
    except strict_json.DuplicateJsonKeyError as exc:
        raise DuplicateJsonKeyError(str(exc)) from exc
    except strict_json.StrictJsonError as exc:
        raise TaskLedgerError(str(exc)) from exc


def read_json_strict(path: Path) -> Any:
    return loads_json_strict(path.read_text(encoding="utf-8"), source=str(path))


def _safe_read_json(path: Path) -> Dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = read_json_strict(path)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def atomic_write_json(path: Path, payload: Mapping[str, Any], *, compact: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as handle:
            if compact:
                handle.write(
                    json.dumps(
                        payload,
                        ensure_ascii=False,
                        sort_keys=False,
                        separators=(",", ":"),
                    )
                )
            else:
                json.dump(payload, handle, indent=2, ensure_ascii=False, sort_keys=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


@contextmanager
def file_lock(lock_path: Path) -> Iterator[None]:
    lock_path = Path(lock_path)
    lock_key = str(lock_path.absolute())
    depth_by_key = getattr(_FILE_LOCK_LOCAL, "depth_by_key", None)
    if depth_by_key is None:
        depth_by_key = {}
        _FILE_LOCK_LOCAL.depth_by_key = depth_by_key
    current_depth = int(depth_by_key.get(lock_key, 0))
    if current_depth > 0:
        depth_by_key[lock_key] = current_depth + 1
        try:
            yield
        finally:
            next_depth = int(depth_by_key.get(lock_key, 1)) - 1
            if next_depth > 0:
                depth_by_key[lock_key] = next_depth
            else:
                depth_by_key.pop(lock_key, None)
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        depth_by_key[lock_key] = 1
        try:
            yield
        finally:
            depth_by_key.pop(lock_key, None)
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _iter_jsonl_rows(path: Path) -> Iterator[Dict[str, Any]]:
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            item = loads_json_strict(line, source=f"{path}:{line_number}")
            if not isinstance(item, dict):
                raise TaskLedgerError(f"{path}:{line_number} is not a JSON object")
            yield item


def _decode_json_string_token(raw: bytes) -> str:
    try:
        value = json.loads(b'"' + raw + b'"')
    except json.JSONDecodeError:
        return raw.decode("utf-8", errors="replace")
    return str(value)


def _jsonl_string_field_from_raw_line(raw_line: bytes, pattern: re.Pattern[bytes]) -> str | None:
    matches = list(pattern.finditer(raw_line))
    if not matches:
        return None
    return _decode_json_string_token(matches[-1].group(1))


def _jsonl_row_from_raw_line(path: Path, line_number: int, raw_line: bytes) -> Dict[str, Any]:
    text = raw_line.decode("utf-8")
    item = loads_json_strict(text, source=f"{path}:{line_number}")
    if not isinstance(item, dict):
        raise TaskLedgerError(f"{path}:{line_number} is not a JSON object")
    return item


def _iter_jsonl_event_id_lines(path: Path) -> Iterator[tuple[int, str, bytes]]:
    if not path.exists():
        return
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            event_id = _jsonl_string_field_from_raw_line(stripped, _JSONL_EVENT_ID_FIELD_RE)
            if event_id is None:
                event_id = str(_jsonl_row_from_raw_line(path, line_number, stripped).get("event_id") or "")
            yield line_number, event_id, stripped


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in _iter_jsonl_rows(path):
        rows.append(item)
    return rows


def _authority_manifest_path(repo_root: Path) -> Path:
    return repo_root / TASK_LEDGER_AUTHORITY_MANIFEST_REL


def _read_authority_manifest(repo_root: Path) -> Dict[str, Any] | None:
    path = _authority_manifest_path(repo_root)
    if not path.exists() or not path.is_file():
        return None
    payload = read_json_strict(path)
    if not isinstance(payload, Mapping):
        raise TaskLedgerError(f"{TASK_LEDGER_AUTHORITY_MANIFEST_REL} must be a JSON object")
    manifest = dict(payload)
    schema = str(manifest.get("schema") or "").strip()
    if schema != TASK_LEDGER_AUTHORITY_MANIFEST_SCHEMA:
        raise TaskLedgerError(
            f"{TASK_LEDGER_AUTHORITY_MANIFEST_REL} schema {schema!r} is not "
            f"{TASK_LEDGER_AUTHORITY_MANIFEST_SCHEMA!r}"
        )
    return manifest


def _authority_manifest_mode(manifest: Mapping[str, Any] | None) -> str:
    if not manifest:
        return TASK_LEDGER_AUTHORITY_MODE_LEGACY
    mode = str(manifest.get("mode") or "").strip()
    if mode in {
        TASK_LEDGER_AUTHORITY_MODE_PREPARED,
        TASK_LEDGER_AUTHORITY_MODE_ACTIVE,
    }:
        return mode
    return TASK_LEDGER_AUTHORITY_MODE_LEGACY


def _active_authority_manifest(repo_root: Path) -> Dict[str, Any] | None:
    manifest = _read_authority_manifest(repo_root)
    if _authority_manifest_mode(manifest) != TASK_LEDGER_AUTHORITY_MODE_ACTIVE:
        return None
    return manifest


def _path_from_manifest(value: Any, fallback: Path) -> Path:
    token = ""
    if isinstance(value, Mapping):
        token = str(value.get("path") or "").strip()
    elif value is not None:
        token = str(value or "").strip()
    return Path(token) if token else fallback


def _manifest_open_tail_rel(manifest: Mapping[str, Any]) -> Path:
    storage_model = manifest.get("storage_model") if isinstance(manifest.get("storage_model"), Mapping) else {}
    return _path_from_manifest(
        manifest.get("open_tail"),
        _path_from_manifest(storage_model.get("open_tail"), TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL),
    )


def _manifest_audit_open_tail_rel(manifest: Mapping[str, Any]) -> Path:
    audit = manifest.get("audit_journal") if isinstance(manifest.get("audit_journal"), Mapping) else {}
    storage_model = manifest.get("storage_model") if isinstance(manifest.get("storage_model"), Mapping) else {}
    audit_model = (
        storage_model.get("audit_journal_model")
        if isinstance(storage_model.get("audit_journal_model"), Mapping)
        else {}
    )
    return _path_from_manifest(
        audit.get("open_tail") if isinstance(audit, Mapping) else None,
        _path_from_manifest(
            audit_model.get("open_tail") if isinstance(audit_model, Mapping) else None,
            TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL,
        ),
    )


def _manifest_segment_rels(manifest: Mapping[str, Any], *, audit: bool = False) -> list[Path]:
    if audit:
        audit_journal = manifest.get("audit_journal")
        segment_rows = (
            audit_journal.get("segments")
            if isinstance(audit_journal, Mapping) and isinstance(audit_journal.get("segments"), list)
            else []
        )
    else:
        segment_rows = manifest.get("segments") if isinstance(manifest.get("segments"), list) else []
    rows = [row for row in segment_rows if isinstance(row, Mapping)]
    rows.sort(key=lambda row: int(row.get("index") or 0))
    return [Path(str(row.get("path") or "")) for row in rows if str(row.get("path") or "").strip()]


def _authority_jsonl_rel_paths(repo_root: Path, *, audit: bool = False) -> list[Path]:
    manifest = _active_authority_manifest(repo_root)
    if manifest is None:
        return [EVENTS_AUDIT_REL if audit else EVENTS_REL]
    rel_paths = _manifest_segment_rels(manifest, audit=audit)
    rel_paths.append(_manifest_audit_open_tail_rel(manifest) if audit else _manifest_open_tail_rel(manifest))
    return rel_paths


def _authority_write_rel_paths(repo_root: Path) -> list[Path]:
    manifest = _active_authority_manifest(repo_root)
    if manifest is None:
        return [EVENTS_REL, EVENTS_AUDIT_REL]
    return [_manifest_open_tail_rel(manifest), _manifest_audit_open_tail_rel(manifest)]


def _read_authority_jsonl(repo_root: Path, *, audit: bool = False) -> List[Dict[str, Any]]:
    rows: list[Dict[str, Any]] = []
    for rel_path in _authority_jsonl_rel_paths(repo_root, audit=audit):
        rows.extend(read_jsonl(repo_root / rel_path))
    return rows


def read_authority_events(repo_root: Path) -> List[Dict[str, Any]]:
    return _read_authority_jsonl(repo_root, audit=False)


def read_authority_audit_events(repo_root: Path) -> List[Dict[str, Any]]:
    return _read_authority_jsonl(repo_root, audit=True)


def _iter_authority_event_id_lines(
    repo_root: Path,
    *,
    audit: bool = False,
) -> Iterator[tuple[Path, int, str, bytes]]:
    for rel_path in _authority_jsonl_rel_paths(repo_root, audit=audit):
        path = repo_root / rel_path
        for line_number, event_id, raw_line in _iter_jsonl_event_id_lines(path):
            yield path, line_number, event_id, raw_line


def _normalized_jsonl_file_summary(path: Path, *, rel_path: Path | None = None) -> Dict[str, Any]:
    digest = hashlib.sha256()
    event_count = 0
    byte_count = 0
    first_event_id = ""
    last_event_id = ""
    tail_raw_line: bytes | None = None
    for _line_number, event_id, normalized_line in _iter_normalized_jsonl_event_lines(path):
        digest.update(normalized_line)
        event_count += 1
        byte_count += len(normalized_line)
        if not first_event_id:
            first_event_id = event_id
        last_event_id = event_id
        tail_raw_line = normalized_line.rstrip(b"\r\n")
    payload: Dict[str, Any] = {
        "path": str(rel_path) if rel_path is not None else str(path),
        "exists": path.exists(),
        "event_count": event_count,
        "byte_count": byte_count,
        "byte_human": _human_bytes(byte_count),
        "sha256": "sha256:" + digest.hexdigest(),
        "first_event_id": first_event_id,
        "last_event_id": last_event_id,
        "tail_hash": _tail_hash_from_raw_event_line(path, tail_raw_line),
    }
    return payload


def _authority_mtime_ns(repo_root: Path) -> int:
    mtimes: list[int] = []
    manifest_path = _authority_manifest_path(repo_root)
    if manifest_path.exists():
        try:
            mtimes.append(int(manifest_path.stat().st_mtime_ns))
        except OSError:
            pass
    for rel_path in _authority_jsonl_rel_paths(repo_root):
        path = repo_root / rel_path
        if path.exists():
            try:
                mtimes.append(int(path.stat().st_mtime_ns))
            except OSError:
                continue
    return max(mtimes) if mtimes else 0


def task_ledger_authority_storage_state(repo_root: Path) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    manifest = _read_authority_manifest(repo_root)
    mode = _authority_manifest_mode(manifest)
    compatibility_export = (
        manifest.get("compatibility_export")
        if isinstance(manifest, Mapping) and isinstance(manifest.get("compatibility_export"), Mapping)
        else {}
    )
    return {
        "schema": "task_ledger_authority_storage_state_v0",
        "mode": mode,
        "manifest_path": str(TASK_LEDGER_AUTHORITY_MANIFEST_REL),
        "manifest_exists": manifest is not None,
        "active_segmented": mode == TASK_LEDGER_AUTHORITY_MODE_ACTIVE,
        "prepared_segmented": mode == TASK_LEDGER_AUTHORITY_MODE_PREPARED,
        "compatibility_export_status": str(compatibility_export.get("status") or "").strip()
        if compatibility_export
        else "",
        "authority_event_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root, audit=False)],
        "authority_audit_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root, audit=True)],
        "append_paths": [str(path) for path in _authority_write_rel_paths(repo_root)],
    }


def _strict_json_surface_paths(repo_root: Path) -> List[Path]:
    rel_paths = [
        Path("codex/standards/std_task_ledger.json"),
        Path("codex/standards/std_task_sign_off.json"),
        Path("codex/standards/std_strict_json_artifact.json"),
        RAW_SEED_PRINCIPLES_REL,
        LEDGER_REL,
        SIGNOFFS_REL,
        PROJECTION_MANIFEST_REL,
    ]
    paths = [repo_root / rel_path for rel_path in rel_paths if (repo_root / rel_path).exists()]
    for rel_root in [VIEWS_REL, DISCOVERY_RECEIPTS_REL]:
        root = repo_root / rel_root
        if root.exists():
            paths.extend(sorted(root.rglob("*.json")))
    deduped: List[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path not in seen:
            deduped.append(path)
            seen.add(path)
    return deduped


def validate_strict_json_surfaces(repo_root: Path) -> Dict[str, Any]:
    checked: List[str] = []
    for path in _strict_json_surface_paths(repo_root):
        read_json_strict(path)
        try:
            checked.append(str(path.relative_to(repo_root)))
        except ValueError:
            checked.append(str(path))
    return {"ok": True, "checked_count": len(checked), "paths": checked}


def event_log_path(repo_root: Path) -> Path:
    return repo_root / EVENTS_REL


def events_audit_path(repo_root: Path) -> Path:
    return repo_root / EVENTS_AUDIT_REL


def _append_audit_journal(audit_path: Path, line: str) -> None:
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def task_ledger_mutation_serialization_receipt(
    *,
    event_count: int,
    projection_rebuilt: bool,
    projection_rebuilt_under_same_lock: bool,
    projection_build_under_same_lock: bool | None = None,
    projection_write_under_same_lock: bool | None = None,
) -> Dict[str, Any]:
    build_under_lock = (
        bool(projection_rebuilt_under_same_lock)
        if projection_build_under_same_lock is None
        else bool(projection_build_under_same_lock)
    )
    write_under_lock = (
        bool(projection_rebuilt_under_same_lock)
        if projection_write_under_same_lock is None
        else bool(projection_write_under_same_lock)
    )
    return {
        "schema": "task_ledger_mutation_serialization_receipt_v0",
        "mode": "single_writer_file_lock",
        "lock_path": str(LOCK_REL),
        "event_count": int(event_count),
        "projection_rebuilt": bool(projection_rebuilt),
        "projection_rebuilt_under_same_lock": bool(projection_rebuilt_under_same_lock),
        "projection_build_under_same_lock": build_under_lock,
        "projection_write_under_same_lock": write_under_lock,
        "parallel_mutation_policy": (
            "Do not launch Task Ledger mutation commands in parallel; use the batch lane "
            "when multiple events belong to one logical closeout."
        ),
    }


def _event_summary(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": str(row.get("event_id") or ""),
        "subject_id": str(row.get("subject_id") or ""),
        "event_type": str(row.get("event_type") or ""),
        "created_at": str(row.get("created_at") or ""),
        "created_by": str(row.get("created_by") or ""),
    }


def _find_lost_audit_events_from_rows(
    repo_root: Path,
    authority_events: Sequence[Mapping[str, Any]],
    *,
    audit_events: Sequence[Mapping[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    audit_path = events_audit_path(repo_root)
    if audit_events is None and not audit_path.exists():
        return []
    main_ids = {str(row.get("event_id") or "") for row in authority_events}
    if audit_events is None:
        return _find_lost_audit_events_from_authority_ids(audit_path, main_ids)
    audit_rows = audit_events
    lost: List[Dict[str, Any]] = []
    for row in audit_rows:
        event_id = str(row.get("event_id") or "")
        if event_id and event_id not in main_ids:
            lost.append(dict(row))
    return lost


def _find_lost_audit_events_from_authority_ids(
    audit_path: Path,
    authority_event_ids: set[str],
) -> List[Dict[str, Any]]:
    lost: List[Dict[str, Any]] = []
    for line_number, event_id, raw_line in _iter_jsonl_event_id_lines(audit_path):
        if event_id and event_id not in authority_event_ids:
            lost.append(_jsonl_row_from_raw_line(audit_path, line_number, raw_line))
    return lost


def find_lost_audit_events(repo_root: Path) -> List[Dict[str, Any]]:
    """Return audit-journal events whose event_id is missing from events.jsonl.

    These are events the work_authority lost — typically because a `git checkout`,
    `git reset --hard`, or `git stash` rewrote events.jsonl from an older commit
    while the audit journal (under gitignored state/) survived. The append-only
    contract is restored by replaying these events through `append_event`.
    """
    return _find_lost_audit_events_from_rows(
        repo_root,
        read_authority_events(repo_root),
        audit_events=read_authority_audit_events(repo_root),
    )


def _projection_visibility_from_ledger(repo_root: Path, ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    ledger = _safe_read_json(repo_root / LEDGER_REL)
    items = ledger.get("work_items") if isinstance(ledger.get("work_items"), list) else []
    by_id = {
        str(item.get("id") or ""): item
        for item in items
        if isinstance(item, Mapping)
    }
    visibility: Dict[str, Dict[str, Any]] = {}
    for item_id in ids:
        row = by_id.get(str(item_id))
        visibility[str(item_id)] = {
            "visible": row is not None,
            "state": row.get("state") if isinstance(row, Mapping) else None,
            "source_event_ids": list(row.get("source_event_ids") or []) if isinstance(row, Mapping) else [],
        }
    return visibility


def _unchecked_projection_visibility(ids: Sequence[str]) -> Dict[str, Dict[str, Any]]:
    return {
        str(item_id): {
            "visible": False,
            "state": None,
            "source_event_ids": [],
        }
        for item_id in ids
    }


def _authority_health_unlocked(
    repo_root: Path,
    *,
    ids: Sequence[str] | None = None,
    event_ids: Sequence[str] | None = None,
) -> Dict[str, Any]:
    selected_ids = [str(item).strip() for item in (ids or []) if str(item).strip()]
    selected_event_ids = [str(item).strip() for item in (event_ids or []) if str(item).strip()]
    selected_event_visibility = {event_id: False for event_id in selected_event_ids}
    unresolved_selected_event_ids = set(selected_event_ids)
    authority_event_ids: set[str] = set()
    authority_event_count = 0
    authority_tail_raw_line: bytes | None = None
    authority_tail_path = event_log_path(repo_root)
    for path, _line_number, event_id, raw_line in _iter_authority_event_id_lines(repo_root):
        authority_event_count += 1
        if event_id:
            authority_event_ids.add(event_id)
            if event_id in unresolved_selected_event_ids:
                selected_event_visibility[event_id] = True
                unresolved_selected_event_ids.discard(event_id)
        authority_tail_path = path
        authority_tail_raw_line = raw_line
    audit_event_count = 0
    lost: List[Dict[str, Any]] = []
    for path, line_number, event_id, raw_line in _iter_authority_event_id_lines(repo_root, audit=True):
        audit_event_count += 1
        if event_id and event_id not in authority_event_ids:
            lost.append(_jsonl_row_from_raw_line(path, line_number, raw_line))
    lost_summaries = [_event_summary(row) for row in lost]
    lost_subject_ids = sorted({row["subject_id"] for row in lost_summaries if row["subject_id"]})
    lost_event_types = dict(Counter(row["event_type"] for row in lost_summaries if row["event_type"]))
    status = "authority_recovery_required" if lost else "clean"
    health: Dict[str, Any] = {
        "schema": "task_ledger_authority_health_v0",
        "ok": not lost,
        "status": status,
        "authority_event_count": authority_event_count,
        "audit_event_count": audit_event_count,
        "lost_count": len(lost),
        "lost_event_ids": [row["event_id"] for row in lost_summaries],
        "lost_subject_ids": lost_subject_ids,
        "lost_event_types": lost_event_types,
        "lost_events": lost_summaries,
        "paths": {
            "event_log": str(EVENTS_REL),
            "event_log_exists": event_log_path(repo_root).exists(),
            "authority_event_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root)],
            "audit_journal": str(EVENTS_AUDIT_REL),
            "audit_journal_exists": events_audit_path(repo_root).exists(),
            "authority_audit_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root, audit=True)],
            "projection": str(LEDGER_REL),
            "projection_exists": (repo_root / LEDGER_REL).exists(),
        },
        "tail_hash": _tail_hash_from_raw_event_line(authority_tail_path, authority_tail_raw_line),
        "storage_state": task_ledger_authority_storage_state(repo_root),
        "next_step": (
            "./repo-python tools/meta/factory/task_ledger_apply.py audit-recover --replay && "
            "./repo-python tools/meta/factory/task_ledger_apply.py rebuild"
            if lost
            else "events.jsonl covers every audit-journal event."
        ),
    }
    if selected_ids:
        visibility = _projection_visibility_from_ledger(repo_root, selected_ids)
        unrecovered = [item for item in selected_ids if item in set(lost_subject_ids)]
        health["selected_ids"] = selected_ids
        health["selected_card_visibility"] = visibility
        health["unrecovered_authority_gap_ids"] = unrecovered
    if selected_event_ids:
        health["selected_event_ids"] = selected_event_ids
        health["selected_event_visibility"] = selected_event_visibility
    return health


def authority_health(
    repo_root: Path,
    *,
    ids: Sequence[str] | None = None,
    event_ids: Sequence[str] | None = None,
    projection_check: bool = False,
) -> Dict[str, Any]:
    with file_lock(repo_root / LOCK_REL):
        health = _authority_health_unlocked(repo_root, ids=ids, event_ids=event_ids)
    if projection_check and health.get("status") == "clean":
        projection_result = _projection_manifest_fast_check(
            repo_root,
            authority_event_count=int(health.get("authority_event_count") or 0),
            authority_tail_hash=str(health.get("tail_hash") or "").strip() or None,
        )
        if projection_result is None:
            projection_result = rebuild_projections(repo_root, check=True)
        health["projection_check"] = projection_result
        if not bool(projection_result.get("ok")):
            health["projection_status"] = projection_result.get("status")
            health["next_step"] = str(projection_result.get("next_step") or "")
            health["safe_next_command"] = str(projection_result.get("safe_next_command") or "")
            health["projection_check_command"] = str(
                projection_result.get("verification_command") or TASK_LEDGER_REBUILD_CHECK_COMMAND
            )
    elif projection_check:
        health["projection_check"] = {
            "ok": False,
            "checked": False,
            "status": "authority_recovery_required",
            "reason": "projection check skipped until audit recovery replays lost events",
        }
    return health


def visibility_receipt(
    repo_root: Path,
    *,
    subject_ids: Sequence[str],
    event_ids: Sequence[str] | None = None,
    projection_rebuilt: bool = False,
    projection_result: Mapping[str, Any] | None = None,
    projection_rebuild_deferred: Mapping[str, Any] | None = None,
    authority_health_hint: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    selected_subject_ids = [str(item).strip() for item in subject_ids if str(item).strip()]
    selected_event_ids = [str(item).strip() for item in (event_ids or []) if str(item).strip()]
    check_projection_cards = bool(projection_rebuilt)
    if authority_health_hint and not check_projection_cards:
        health = dict(authority_health_hint)
    else:
        health = authority_health(
            repo_root,
            ids=selected_subject_ids if check_projection_cards else None,
            event_ids=selected_event_ids,
        )
    event_visibility = (
        health.get("selected_event_visibility")
        if isinstance(health.get("selected_event_visibility"), Mapping)
        else {event_id: False for event_id in selected_event_ids}
    )
    if check_projection_cards:
        card_visibility = (
            health.get("selected_card_visibility")
            if isinstance(health.get("selected_card_visibility"), Mapping)
            else {}
        )
    else:
        card_visibility = _unchecked_projection_visibility(selected_subject_ids)
    all_cards_visible = (
        all(bool((card_visibility.get(item) or {}).get("visible")) for item in selected_subject_ids)
        if selected_subject_ids
        else None
    )
    projection_status = "rebuilt"
    if not projection_rebuilt:
        projection_status = "stale_until_rebuild"
    elif projection_result and not projection_result.get("ok", True):
        projection_status = str(projection_result.get("status") or "rebuild_failed")
    deferred = (
        projection_rebuild_deferred
        if isinstance(projection_rebuild_deferred, Mapping)
        else {}
    )
    queued_work = deferred.get("queued_work") if isinstance(deferred.get("queued_work"), Mapping) else {}
    queue_id = str(queued_work.get("queue_id") or "").strip()
    authority_event_visible = (
        all(event_visibility.values()) if selected_event_ids else None
    )
    if projection_rebuilt and projection_result and not projection_result.get("ok", True):
        assimilation_status = "projection_rebuild_failed"
    elif projection_rebuilt:
        assimilation_status = "authority_and_projection_checked"
    elif deferred:
        assimilation_status = (
            "authority_appended_projection_rebuild_deferred"
            if deferred.get("authority_appended")
            else "projection_rebuild_deferred_without_authority_append"
        )
    else:
        assimilation_status = "authority_visible_projection_not_rebuilt"
    projection_visible = all_cards_visible if projection_rebuilt else False
    if projection_rebuilt:
        projection_card_visibility = "checked"
        next_safe_action = "continue from the selected Task Ledger projection card"
        receipt_condition = "authority and projection visibility checked"
    elif deferred:
        projection_card_visibility = "deferred_until_rebuild"
        next_safe_action = "drain the queued Task Ledger projection rebuild, then re-open the selected card"
        receipt_condition = "authority event visible; projection rebuild deferred and queued"
    else:
        projection_card_visibility = "not_checked_until_rebuild"
        next_safe_action = "run a Task Ledger projection rebuild before relying on card visibility"
        receipt_condition = "authority event visible; projection rebuild not requested or not run"
    assimilation_state: Dict[str, Any] = {
        "schema": "task_ledger_projection_assimilation_state_v1",
        "status": assimilation_status,
        "subject_ids": selected_subject_ids,
        "event_ids": selected_event_ids,
        "authority_status": health.get("status"),
        "authority_event_visible": authority_event_visible,
        "projection_rebuilt": bool(projection_rebuilt),
        "projection_status": projection_status,
        "projection_visible": projection_visible,
        "projection_card_visibility": projection_card_visibility,
        "queued_for_drain": bool(deferred.get("queued_for_drain")) if deferred else False,
        "receipt_condition": receipt_condition,
        "next_safe_action": next_safe_action,
    }
    if queue_id:
        assimilation_state["queue_id"] = queue_id
    if deferred:
        assimilation_state["deferred_status"] = deferred.get("status")
        assimilation_state["deferred_reason"] = deferred.get("reason")
        assimilation_state["reentry_condition"] = deferred.get("reentry_condition")
        if queued_work:
            assimilation_state["queued_work_status"] = queued_work.get("status")
    return {
        "schema": "task_ledger_visibility_receipt_v0",
        "authority_status": health.get("status"),
        "event_log_present": bool((health.get("paths") or {}).get("event_log_exists")),
        "audit_journal_present": bool((health.get("paths") or {}).get("audit_journal_exists")),
        "projection_status": projection_status,
        "projection_rebuilt": bool(projection_rebuilt),
        "selected_subject_ids": selected_subject_ids,
        "selected_event_ids": selected_event_ids,
        "event_ids_visible_in_authority": event_visibility,
        "selected_card_visibility": card_visibility,
        "all_selected_cards_visible": all_cards_visible if projection_rebuilt else None,
        "projection_assimilation_state": assimilation_state,
        "note": (
            "event appended to authority; projection/card visibility requires rebuild"
            if not projection_rebuilt
            else "event authority and projection visibility checked"
        ),
    }


def authority_health_hint_from_append_result(
    repo_root: Path,
    append_result: Mapping[str, Any],
    *,
    event_ids: Sequence[str] | None = None,
) -> Dict[str, Any] | None:
    """Build a narrow authority-health receipt from a just-serialized append."""
    if not append_result.get("ok", True):
        return None
    if append_result.get("status") not in {"appended", "duplicate_idempotent"}:
        return None
    event = append_result.get("event") if isinstance(append_result.get("event"), Mapping) else {}
    appended_event_id = str(event.get("event_id") or "").strip()
    selected_event_ids = [str(item).strip() for item in (event_ids or []) if str(item).strip()]
    selected_visibility = {
        event_id: bool(appended_event_id and event_id == appended_event_id)
        for event_id in selected_event_ids
    }
    if selected_event_ids and not all(selected_visibility.values()):
        return None
    return {
        "schema": "task_ledger_authority_health_v0",
        "ok": True,
        "status": "clean",
        "lost_count": 0,
        "lost_event_ids": [],
        "lost_subject_ids": [],
        "lost_event_types": {},
        "lost_events": [],
        "paths": {
            "event_log": str(EVENTS_REL),
            "event_log_exists": event_log_path(repo_root).exists(),
            "authority_event_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root)],
            "audit_journal": str(EVENTS_AUDIT_REL),
            "audit_journal_exists": events_audit_path(repo_root).exists(),
            "authority_audit_paths": [str(path) for path in _authority_jsonl_rel_paths(repo_root, audit=True)],
            "projection": str(LEDGER_REL),
            "projection_exists": (repo_root / LEDGER_REL).exists(),
        },
        "storage_state": task_ledger_authority_storage_state(repo_root),
        "selected_event_ids": selected_event_ids,
        "selected_event_visibility": selected_visibility,
        "next_step": "events.jsonl covers every audit-journal event.",
        "source": "append_event_and_rebuild.serialized_append_result",
    }


def _authority_recovery_error(lost: Sequence[Mapping[str, Any]]) -> str:
    ids = [str(row.get("event_id") or "") for row in lost[:5]]
    suffix = f"; first_lost_event_ids={ids}" if ids else ""
    return (
        "Task Ledger authority recovery required: events_audit.jsonl contains "
        f"{len(lost)} event(s) missing from events.jsonl{suffix}. Run "
        "./repo-python tools/meta/factory/task_ledger_apply.py audit-recover --replay "
        "before appending new Task Ledger events."
    )


def replay_lost_audit_events(repo_root: Path) -> Dict[str, Any]:
    """Re-append every audit event missing from events.jsonl.

    Replay drops the original `previous_event_hash` / `event_hash` so the chain
    rebinds against the current events.jsonl tail; identity is preserved via
    `event_id`, which `append_event` treats as idempotent.
    """
    lost = find_lost_audit_events(repo_root)
    replayed: List[Dict[str, Any]] = []
    duplicates: List[Dict[str, Any]] = []
    for event in lost:
        replay = {k: v for k, v in event.items() if k not in {"previous_event_hash", "event_hash"}}
        result = append_event(repo_root, replay, allow_authority_recovery=True)
        status = result.get("status")
        record = {"event_id": replay.get("event_id"), "status": status}
        if status == "duplicate_idempotent":
            duplicates.append(record)
        else:
            replayed.append(record)
    return {
        "ok": True,
        "lost_count": len(lost),
        "replayed_count": len(replayed),
        "duplicate_count": len(duplicates),
        "replayed": replayed,
        "duplicates": duplicates,
        "authority_health": authority_health(repo_root),
    }


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def compute_event_hash(event: Mapping[str, Any]) -> str:
    body = {key: value for key, value in event.items() if key != "event_hash"}
    return "sha256:" + hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()


def _tail_hash(events: List[Mapping[str, Any]]) -> str | None:
    if not events:
        return None
    return _tail_hash_from_event(events[-1])


def _tail_hash_from_event(event: Mapping[str, Any] | None) -> str | None:
    if event is None:
        return None
    value = str(event.get("event_hash") or "").strip()
    return value or compute_event_hash(event)


def _tail_hash_from_raw_event_line(path: Path, raw_line: bytes | None) -> str | None:
    if not raw_line:
        return None
    value = _jsonl_string_field_from_raw_line(raw_line, _JSONL_EVENT_HASH_FIELD_RE)
    if value:
        return value
    event = _jsonl_row_from_raw_line(path, 0, raw_line)
    return _tail_hash_from_event(event)


def _sha256_empty_jsonl() -> str:
    return "sha256:" + hashlib.sha256(b"").hexdigest()


def _configured_migration_segment_bytes(max_segment_bytes: int | None = None) -> int:
    if max_segment_bytes is not None:
        return max(1024, int(max_segment_bytes))
    return max(
        1024,
        _configured_nonnegative_bytes(
            TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES_ENV,
            TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES_DEFAULT,
        ),
    )


def _segment_path(base_rel: Path, stem: str, index: int) -> Path:
    return base_rel / f"{stem}-{index:06d}.jsonl"


def _hash_mapping(payload: Mapping[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _iter_normalized_jsonl_event_lines(path: Path) -> Iterator[tuple[int, str, bytes]]:
    if not path.exists():
        return
    with path.open("rb") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            if not raw_line.strip():
                continue
            stripped = raw_line.strip()
            event_id = _jsonl_string_field_from_raw_line(stripped, _JSONL_EVENT_ID_FIELD_RE)
            if event_id is None:
                event_id = str(
                    _jsonl_row_from_raw_line(path, line_number, stripped).get("event_id") or ""
                )
            yield line_number, event_id, raw_line.rstrip(b"\r\n") + b"\n"


def _jsonl_segment_plan(
    repo_root: Path,
    *,
    source_rel: Path,
    segment_dir_rel: Path,
    segment_stem: str,
    max_segment_bytes: int,
) -> Dict[str, Any]:
    source_path = repo_root / source_rel
    source_exists = source_path.exists()
    source_size = int(source_path.stat().st_size) if source_path.exists() and source_path.is_file() else 0
    source_digest = hashlib.sha256()
    segments: list[dict[str, Any]] = []
    previous_chain_hash: str | None = None
    current_digest = hashlib.sha256()
    current_count = 0
    current_bytes = 0
    current_start_line: int | None = None
    current_end_line: int | None = None
    current_first_event_id = ""
    current_last_event_id = ""
    event_count = 0
    normalized_bytes = 0
    first_event_id = ""
    last_event_id = ""
    tail_raw_line: bytes | None = None

    def flush_segment() -> None:
        nonlocal current_count
        nonlocal current_bytes
        nonlocal current_start_line
        nonlocal current_end_line
        nonlocal current_first_event_id
        nonlocal current_last_event_id
        nonlocal current_digest
        nonlocal previous_chain_hash
        if current_count <= 0:
            return
        index = len(segments) + 1
        row: dict[str, Any] = {
            "index": index,
            "path": str(_segment_path(segment_dir_rel, segment_stem, index)),
            "start_line": current_start_line,
            "end_line": current_end_line,
            "event_count": current_count,
            "byte_count": current_bytes,
            "sha256": "sha256:" + current_digest.hexdigest(),
            "first_event_id": current_first_event_id,
            "last_event_id": current_last_event_id,
            "previous_chain_hash": previous_chain_hash,
        }
        row["chain_hash"] = _hash_mapping(
            {
                "path": row["path"],
                "index": row["index"],
                "start_line": row["start_line"],
                "end_line": row["end_line"],
                "event_count": row["event_count"],
                "byte_count": row["byte_count"],
                "sha256": row["sha256"],
                "previous_chain_hash": row["previous_chain_hash"],
            }
        )
        previous_chain_hash = str(row["chain_hash"])
        segments.append(row)
        current_digest = hashlib.sha256()
        current_count = 0
        current_bytes = 0
        current_start_line = None
        current_end_line = None
        current_first_event_id = ""
        current_last_event_id = ""

    for line_number, event_id, normalized_line in _iter_normalized_jsonl_event_lines(source_path):
        line_bytes = len(normalized_line)
        if current_count > 0 and current_bytes + line_bytes > max_segment_bytes:
            flush_segment()
        if current_count == 0:
            current_start_line = line_number
            current_first_event_id = event_id
        source_digest.update(normalized_line)
        current_digest.update(normalized_line)
        event_count += 1
        normalized_bytes += line_bytes
        current_count += 1
        current_bytes += line_bytes
        current_end_line = line_number
        current_last_event_id = event_id
        if not first_event_id:
            first_event_id = event_id
        last_event_id = event_id
        tail_raw_line = normalized_line.rstrip(b"\r\n")
    flush_segment()
    source_hash = "sha256:" + source_digest.hexdigest()
    return {
        "source": {
            "path": str(source_rel),
            "exists": source_exists,
            "size_bytes": source_size,
            "size_human": _human_bytes(source_size),
            "normalized_jsonl_bytes": normalized_bytes,
            "normalized_jsonl_human": _human_bytes(normalized_bytes),
            "event_count": event_count,
            "first_event_id": first_event_id,
            "last_event_id": last_event_id,
            "tail_hash": _tail_hash_from_raw_event_line(source_path, tail_raw_line),
            "normalized_jsonl_sha256": source_hash,
        },
        "segments": segments,
        "segment_count": len(segments),
        "closed_segment_event_count": event_count,
        "closed_segment_bytes": normalized_bytes,
        "closed_segment_sha256": source_hash,
        "chain_tail_hash": previous_chain_hash,
    }


def _task_ledger_authority_migration_plan_unlocked(
    repo_root: Path,
    *,
    max_segment_bytes: int | None = None,
    include_audit: bool = True,
) -> Dict[str, Any]:
    """Return a reversible, read-only plan for migrating Task Ledger authority.

    The first landing deliberately does not rewrite events.jsonl or change the
    append writer. It creates the proof shape needed for a later under-lock
    cutover: closed historical segments, one empty open tail, manifest hash, and
    compatibility-export equivalence requirements.
    """
    repo_root = Path(repo_root)
    segment_bytes = _configured_migration_segment_bytes(max_segment_bytes)
    health = _authority_health_unlocked(repo_root)
    storage = task_ledger_authority_storage_status(repo_root)
    authority_plan = _jsonl_segment_plan(
        repo_root,
        source_rel=EVENTS_REL,
        segment_dir_rel=TASK_LEDGER_AUTHORITY_SEGMENTS_REL,
        segment_stem="events",
        max_segment_bytes=segment_bytes,
    )
    audit_plan = (
        _jsonl_segment_plan(
            repo_root,
            source_rel=EVENTS_AUDIT_REL,
            segment_dir_rel=TASK_LEDGER_AUTHORITY_AUDIT_SEGMENTS_REL,
            segment_stem="events_audit",
            max_segment_bytes=segment_bytes,
        )
        if include_audit
        else None
    )

    open_tail_hash = _sha256_empty_jsonl()
    proposed_model: Dict[str, Any] = {
        "schema": "task_ledger_authority_segmented_storage_model_v0",
        "segments_dir": str(TASK_LEDGER_AUTHORITY_SEGMENTS_REL),
        "open_tail": str(TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL),
        "manifest": str(TASK_LEDGER_AUTHORITY_MANIFEST_REL),
        "compatibility_export": str(EVENTS_REL),
        "policy": (
            "closed historical segments are immutable; exactly one open tail receives "
            "future appends after an explicit cutover; events.jsonl remains a generated "
            "compatibility export until dependents are migrated"
        ),
        "open_tail_initialization": {
            "status": "empty_tail_after_closed_history",
            "path": str(TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL),
            "event_count": 0,
            "byte_count": 0,
            "sha256": open_tail_hash,
        },
    }
    if audit_plan is not None:
        proposed_model["audit_journal_model"] = {
            "segments_dir": str(TASK_LEDGER_AUTHORITY_AUDIT_SEGMENTS_REL),
            "open_tail": str(TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL),
            "compatibility_export": str(EVENTS_AUDIT_REL),
            "policy": (
                "co-migrate audit history before writer cutover or keep the audit journal "
                "as explicitly monolithic compatibility authority with its own pressure receipt"
            ),
        }

    manifest_material: Dict[str, Any] = {
        "schema": "task_ledger_authority_segment_manifest_v0",
        "storage_model": proposed_model,
        "source_authority": authority_plan["source"],
        "segments": authority_plan["segments"],
        "open_tail": proposed_model["open_tail_initialization"],
        "compatibility_export": {
            "path": str(EVENTS_REL),
            "expected_normalized_jsonl_sha256": authority_plan["closed_segment_sha256"],
            "expected_event_count": authority_plan["closed_segment_event_count"],
        },
    }
    if audit_plan is not None:
        manifest_material["audit_journal"] = {
            "source": audit_plan["source"],
            "segments": audit_plan["segments"],
            "open_tail": {
                "path": str(TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL),
                "event_count": 0,
                "byte_count": 0,
                "sha256": open_tail_hash,
            },
            "compatibility_export": {
                "path": str(EVENTS_AUDIT_REL),
                "expected_normalized_jsonl_sha256": audit_plan["closed_segment_sha256"],
                "expected_event_count": audit_plan["closed_segment_event_count"],
            },
        }
    manifest_hash = _hash_mapping(manifest_material)
    source_hash = str(authority_plan["closed_segment_sha256"])
    equivalence_status = (
        "planned_segment_stream_matches_source"
        if authority_plan["closed_segment_event_count"] == authority_plan["source"]["event_count"]
        and authority_plan["closed_segment_sha256"] == authority_plan["source"]["normalized_jsonl_sha256"]
        else "planned_segment_stream_mismatch"
    )
    return {
        "schema": "task_ledger_authority_migration_plan_v0",
        "ok": bool(health.get("ok")) and equivalence_status == "planned_segment_stream_matches_source",
        "mode": "dry_run",
        "status": "plan_ready" if bool(health.get("ok")) else "authority_recovery_required_first",
        "cutover_allowed": False,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "segment_policy": {
            "max_segment_bytes": segment_bytes,
            "max_segment_human": _human_bytes(segment_bytes),
            "reason": "keep authority chunks below monolith pressure thresholds and host VCS warning sizes",
        },
        "authority_health": health,
        "authority_storage": storage,
        "source_authority": authority_plan["source"],
        "proposed_model": proposed_model,
        "segment_plan": {
            "segment_count": authority_plan["segment_count"],
            "closed_segment_event_count": authority_plan["closed_segment_event_count"],
            "closed_segment_bytes": authority_plan["closed_segment_bytes"],
            "closed_segment_human": _human_bytes(authority_plan["closed_segment_bytes"]),
            "closed_segment_sha256": source_hash,
            "chain_tail_hash": authority_plan["chain_tail_hash"],
            "segments": authority_plan["segments"],
        },
        "manifest_plan": {
            "path": str(TASK_LEDGER_AUTHORITY_MANIFEST_REL),
            "schema": "task_ledger_authority_segment_manifest_v0",
            "manifest_sha256": manifest_hash,
            "material": manifest_material,
        },
        "compatibility_export_plan": {
            "path": str(EVENTS_REL),
            "role": "generated_compatibility_export_after_cutover",
            "pre_cutover_status": "current_hot_append_authority_remains_unchanged",
            "expected_event_count": authority_plan["source"]["event_count"],
            "expected_normalized_jsonl_sha256": source_hash,
        },
        "projection_equivalence_plan": {
            "schema": "task_ledger_projection_equivalence_plan_v0",
            "status": equivalence_status,
            "source_replay_hash": source_hash,
            "planned_segment_replay_hash": authority_plan["closed_segment_sha256"],
            "expected_event_count": authority_plan["source"]["event_count"],
            "required_after_apply_commands": [
                TASK_LEDGER_AUTHORITY_MIGRATION_PLAN_COMMAND,
                TASK_LEDGER_REBUILD_CHECK_QUIET_COMMAND,
                "./repo-python tools/meta/factory/task_ledger_apply.py authority-health --projection-check",
            ],
            "cutover_gate": (
                "Before writer cutover, materialize segments under the Task Ledger lock, "
                "rebuild events.jsonl from segments plus open tail, verify the normalized "
                "compatibility-export hash equals source_replay_hash, then run projection checks."
            ),
        },
        "rollback_restore": {
            "status": "no_mutation_in_dry_run",
            "restore_route": (
                "If a later apply attempt fails before writer cutover, delete the new events/ "
                "segmented directory and keep the original events.jsonl/events_audit.jsonl. "
                "If it fails after writer cutover, restore events.jsonl and events_audit.jsonl "
                "from the compatibility exports/backups recorded in that apply receipt."
            ),
        },
        "audit_co_migration": (
            {
                "status": "included_in_dry_run_plan",
                "recommended_before_writer_cutover": True,
                "source": audit_plan["source"],
                "segment_plan": {
                    "segment_count": audit_plan["segment_count"],
                    "closed_segment_event_count": audit_plan["closed_segment_event_count"],
                    "closed_segment_bytes": audit_plan["closed_segment_bytes"],
                    "closed_segment_human": _human_bytes(audit_plan["closed_segment_bytes"]),
                    "closed_segment_sha256": audit_plan["closed_segment_sha256"],
                    "chain_tail_hash": audit_plan["chain_tail_hash"],
                    "segments": audit_plan["segments"],
                },
            }
            if audit_plan is not None
            else {
                "status": "not_included",
                "recommended_before_writer_cutover": True,
                "reason": "rerun without --skip-audit before cutover readiness",
            }
        ),
        "next_step": (
            f"Plan only. Run {TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --prepare "
            f"or {TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --activate after reviewing "
            "authority health and projection checks."
        ),
    }


def task_ledger_authority_migration_plan(
    repo_root: Path,
    *,
    max_segment_bytes: int | None = None,
    include_audit: bool = True,
) -> Dict[str, Any]:
    with file_lock(Path(repo_root) / LOCK_REL):
        return _task_ledger_authority_migration_plan_unlocked(
            repo_root,
            max_segment_bytes=max_segment_bytes,
            include_audit=include_audit,
        )


def _segment_staging_path(staging_root: Path, rel_path: Path) -> Path:
    try:
        under_events = rel_path.relative_to(TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL)
    except ValueError as exc:
        raise TaskLedgerError(
            f"segmented authority path {rel_path} is not under {TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL}"
        ) from exc
    return staging_root / under_events


def _write_segment_files_from_plan(
    repo_root: Path,
    *,
    source_rel: Path,
    segment_rows: Sequence[Mapping[str, Any]],
    staging_root: Path,
) -> None:
    rows = [dict(row) for row in segment_rows]
    rows.sort(key=lambda row: int(row.get("index") or 0))
    if not rows:
        return
    prepared_rows: list[tuple[Mapping[str, Any], Path, int, int, Path]] = []
    for row in rows:
        rel_path = Path(str(row.get("path") or ""))
        if not str(rel_path):
            raise TaskLedgerError("segment row missing path")
        start_line = int(row.get("start_line") or 0)
        end_line = int(row.get("end_line") or 0)
        if start_line <= 0 or end_line < start_line:
            raise TaskLedgerError(f"invalid segment line range for {rel_path}")
        path = _segment_staging_path(staging_root, rel_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        prepared_rows.append((row, rel_path, start_line, end_line, path))

    row_index = 0
    active_handle: Any = None
    active_end_line = 0
    try:
        for line_number, _event_id, normalized_line in _iter_normalized_jsonl_event_lines(
            repo_root / source_rel
        ):
            while row_index < len(prepared_rows) and line_number > prepared_rows[row_index][3]:
                row_index += 1
            if row_index >= len(prepared_rows):
                break
            _row, _rel_path, start_line, end_line, path = prepared_rows[row_index]
            if line_number < start_line:
                continue
            if active_handle is None:
                active_handle = path.open("wb")
                active_end_line = end_line
            active_handle.write(normalized_line)
            if line_number >= active_end_line:
                active_handle.flush()
                os.fsync(active_handle.fileno())
                active_handle.close()
                active_handle = None
                row_index += 1
        if active_handle is not None:
            active_handle.flush()
            os.fsync(active_handle.fileno())
            active_handle.close()
            active_handle = None
    finally:
        if active_handle is not None:
            active_handle.close()
    if row_index < len(prepared_rows):
        missing = prepared_rows[row_index][1]
        raise TaskLedgerError(f"source {source_rel} ended before segment {missing} was complete")

    for row, rel_path, _start_line, _end_line, path in prepared_rows:
        summary = _normalized_jsonl_file_summary(path, rel_path=rel_path)
        if summary["sha256"] != row.get("sha256"):
            raise TaskLedgerError(
                f"segment {rel_path} sha mismatch: {summary['sha256']} != {row.get('sha256')}"
            )
        if int(summary["event_count"]) != int(row.get("event_count") or 0):
            raise TaskLedgerError(
                f"segment {rel_path} event count mismatch: "
                f"{summary['event_count']} != {row.get('event_count')}"
            )
        if int(summary["byte_count"]) != int(row.get("byte_count") or 0):
            raise TaskLedgerError(
                f"segment {rel_path} byte count mismatch: "
                f"{summary['byte_count']} != {row.get('byte_count')}"
            )


def _manifest_material_for_apply(
    plan: Mapping[str, Any],
    *,
    mode: str,
) -> Dict[str, Any]:
    manifest_plan = plan.get("manifest_plan") if isinstance(plan.get("manifest_plan"), Mapping) else {}
    material = manifest_plan.get("material") if isinstance(manifest_plan.get("material"), Mapping) else None
    if material is None:
        raise TaskLedgerError("authority migration plan is missing manifest material")
    manifest = dict(material)
    now = utc_now()
    manifest["schema"] = TASK_LEDGER_AUTHORITY_MANIFEST_SCHEMA
    manifest["mode"] = mode
    manifest["created_at"] = now
    manifest["updated_at"] = now
    manifest["plan_generated_at"] = plan.get("generated_at")
    manifest["source_authority"] = dict(plan.get("source_authority") or manifest.get("source_authority") or {})
    open_tail = dict(manifest.get("open_tail") or {})
    open_tail["path"] = str(TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL)
    open_tail.setdefault("status", "empty_tail_after_closed_history")
    open_tail.setdefault("event_count", 0)
    open_tail.setdefault("byte_count", 0)
    open_tail.setdefault("sha256", _sha256_empty_jsonl())
    manifest["open_tail"] = open_tail
    manifest["open_tail_event_count"] = int(open_tail.get("event_count") or 0)
    manifest["authority_event_count"] = int(
        (manifest.get("source_authority") or {}).get("event_count") or 0
    )
    compat = dict(manifest.get("compatibility_export") or {})
    compat["path"] = str(EVENTS_REL)
    compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID
    compat["valid_at"] = now
    compat["role"] = "legacy_path_export_unchanged_at_cutover"
    manifest["compatibility_export"] = compat
    audit_journal = dict(manifest.get("audit_journal") or {})
    audit_open_tail = dict(audit_journal.get("open_tail") or {})
    audit_open_tail["path"] = str(TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL)
    audit_open_tail.setdefault("event_count", 0)
    audit_open_tail.setdefault("byte_count", 0)
    audit_open_tail.setdefault("sha256", _sha256_empty_jsonl())
    audit_journal["open_tail"] = audit_open_tail
    audit_journal["open_tail_event_count"] = int(audit_open_tail.get("event_count") or 0)
    audit_source = audit_journal.get("source") if isinstance(audit_journal.get("source"), Mapping) else {}
    audit_journal["audit_event_count"] = int(audit_source.get("event_count") or 0)
    audit_compat = dict(audit_journal.get("compatibility_export") or {})
    audit_compat["path"] = str(EVENTS_AUDIT_REL)
    audit_compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID
    audit_compat["valid_at"] = now
    audit_compat["role"] = "legacy_audit_export_unchanged_at_cutover"
    audit_journal["compatibility_export"] = audit_compat
    manifest["audit_journal"] = audit_journal
    manifest["apply_policy"] = {
        "writer_cutover_mode": mode,
        "closed_segments_immutable": True,
        "compatibility_export_updated_on_append": False,
        "compatibility_export_refresh_command": TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_COMMAND,
    }
    return manifest


def _touch_empty_jsonl(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as handle:
        handle.flush()
        os.fsync(handle.fileno())


def _materialize_authority_segments_from_plan(
    repo_root: Path,
    *,
    plan: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> Dict[str, Any]:
    final_root = repo_root / TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL
    if final_root.exists():
        existing = _read_authority_manifest(repo_root)
        if existing is None:
            raise TaskLedgerError(
                f"{TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL} already exists without a readable manifest"
            )
        expected_hash = str((plan.get("source_authority") or {}).get("normalized_jsonl_sha256") or "")
        existing_hash = str((existing.get("source_authority") or {}).get("normalized_jsonl_sha256") or "")
        if expected_hash and existing_hash and expected_hash != existing_hash:
            raise TaskLedgerError(
                "existing segmented authority manifest was prepared from a different source hash"
            )
        return {
            "status": "already_materialized",
            "root": str(TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL),
        }
    staging_root = repo_root / TASK_LEDGER_ROOT_REL / f".events_staging_{os.getpid()}_{uuid.uuid4().hex}"
    try:
        _write_segment_files_from_plan(
            repo_root,
            source_rel=EVENTS_REL,
            segment_rows=list(manifest.get("segments") or []),
            staging_root=staging_root,
        )
        audit = manifest.get("audit_journal") if isinstance(manifest.get("audit_journal"), Mapping) else {}
        _write_segment_files_from_plan(
            repo_root,
            source_rel=EVENTS_AUDIT_REL,
            segment_rows=list(audit.get("segments") or []) if isinstance(audit, Mapping) else [],
            staging_root=staging_root,
        )
        _touch_empty_jsonl(_segment_staging_path(staging_root, TASK_LEDGER_AUTHORITY_OPEN_TAIL_REL))
        _touch_empty_jsonl(_segment_staging_path(staging_root, TASK_LEDGER_AUTHORITY_AUDIT_OPEN_TAIL_REL))
        atomic_write_json(_segment_staging_path(staging_root, TASK_LEDGER_AUTHORITY_MANIFEST_REL), manifest)
        final_root.parent.mkdir(parents=True, exist_ok=True)
        os.replace(staging_root, final_root)
    finally:
        if staging_root.exists():
            shutil.rmtree(staging_root)
    return {
        "status": "materialized",
        "root": str(TASK_LEDGER_AUTHORITY_EVENTS_ROOT_REL),
    }


def _verify_authority_segment_material(repo_root: Path, manifest: Mapping[str, Any]) -> Dict[str, Any]:
    checked: list[str] = []
    for row in list(manifest.get("segments") or []):
        if not isinstance(row, Mapping):
            continue
        rel_path = Path(str(row.get("path") or ""))
        summary = _normalized_jsonl_file_summary(repo_root / rel_path, rel_path=rel_path)
        if summary["sha256"] != row.get("sha256"):
            raise TaskLedgerError(f"authority segment {rel_path} failed sha verification")
        checked.append(str(rel_path))
    audit = manifest.get("audit_journal") if isinstance(manifest.get("audit_journal"), Mapping) else {}
    for row in list(audit.get("segments") or []) if isinstance(audit, Mapping) else []:
        if not isinstance(row, Mapping):
            continue
        rel_path = Path(str(row.get("path") or ""))
        summary = _normalized_jsonl_file_summary(repo_root / rel_path, rel_path=rel_path)
        if summary["sha256"] != row.get("sha256"):
            raise TaskLedgerError(f"authority audit segment {rel_path} failed sha verification")
        checked.append(str(rel_path))
    return {
        "schema": "task_ledger_authority_segment_material_verification_v0",
        "status": "verified",
        "checked_count": len(checked),
        "paths": checked,
    }


def task_ledger_authority_migration_apply(
    repo_root: Path,
    *,
    activate: bool = False,
    max_segment_bytes: int | None = None,
    include_audit: bool = True,
) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    requested_mode = (
        TASK_LEDGER_AUTHORITY_MODE_ACTIVE if activate else TASK_LEDGER_AUTHORITY_MODE_PREPARED
    )
    with file_lock(repo_root / LOCK_REL):
        existing_manifest = _read_authority_manifest(repo_root)
        existing_mode = _authority_manifest_mode(existing_manifest)
        if existing_mode == TASK_LEDGER_AUTHORITY_MODE_ACTIVE:
            return {
                "schema": "task_ledger_authority_migration_apply_v0",
                "ok": True,
                "status": "already_active",
                "mode": TASK_LEDGER_AUTHORITY_MODE_ACTIVE,
                "storage_state": task_ledger_authority_storage_state(repo_root),
            }
        plan = _task_ledger_authority_migration_plan_unlocked(
            repo_root,
            max_segment_bytes=max_segment_bytes,
            include_audit=include_audit,
        )
        if not bool(plan.get("ok")):
            return {
                "schema": "task_ledger_authority_migration_apply_v0",
                "ok": False,
                "status": str(plan.get("status") or "migration_plan_not_ok"),
                "mode": existing_mode,
                "plan": plan,
            }
        manifest = _manifest_material_for_apply(plan, mode=requested_mode)
        materialized = _materialize_authority_segments_from_plan(
            repo_root,
            plan=plan,
            manifest=manifest,
        )
        current_manifest = _read_authority_manifest(repo_root) or manifest
        if activate and _authority_manifest_mode(current_manifest) != TASK_LEDGER_AUTHORITY_MODE_ACTIVE:
            activated = dict(current_manifest)
            activated["mode"] = TASK_LEDGER_AUTHORITY_MODE_ACTIVE
            activated["updated_at"] = utc_now()
            compat = dict(activated.get("compatibility_export") or {})
            compat.setdefault("path", str(EVENTS_REL))
            compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID
            compat["valid_at"] = utc_now()
            activated["compatibility_export"] = compat
            audit = dict(activated.get("audit_journal") or {})
            audit_compat = dict(audit.get("compatibility_export") or {})
            audit_compat.setdefault("path", str(EVENTS_AUDIT_REL))
            audit_compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID
            audit_compat["valid_at"] = compat["valid_at"]
            audit["compatibility_export"] = audit_compat
            activated["audit_journal"] = audit
            atomic_write_json(_authority_manifest_path(repo_root), activated)
            current_manifest = activated
        verification = _verify_authority_segment_material(repo_root, current_manifest)
        health = _authority_health_unlocked(repo_root)
        status = (
            "active_segmented_enabled"
            if _authority_manifest_mode(current_manifest) == TASK_LEDGER_AUTHORITY_MODE_ACTIVE
            else "prepared_segmented_materialized"
        )
        return {
            "schema": "task_ledger_authority_migration_apply_v0",
            "ok": bool(health.get("ok")),
            "status": status,
            "mode": _authority_manifest_mode(current_manifest),
            "materialization": materialized,
            "verification": verification,
            "authority_health": health,
            "storage_state": task_ledger_authority_storage_state(repo_root),
            "compatibility_export": current_manifest.get("compatibility_export"),
            "next_step": (
                "active segmented writer is enabled; ordinary appends now target the open tail"
                if status == "active_segmented_enabled"
                else f"run {TASK_LEDGER_AUTHORITY_MIGRATION_APPLY_COMMAND} --activate after validation"
            ),
        }


def _export_authority_stream_to_jsonl(repo_root: Path, *, dest_rel: Path, audit: bool = False) -> Dict[str, Any]:
    dest_path = repo_root / dest_rel
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = dest_path.with_name(f".{dest_path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("wb") as handle:
            for rel_path in _authority_jsonl_rel_paths(repo_root, audit=audit):
                for _line_number, _event_id, normalized_line in _iter_normalized_jsonl_event_lines(
                    repo_root / rel_path
                ):
                    handle.write(normalized_line)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, dest_path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()
    return _normalized_jsonl_file_summary(dest_path, rel_path=dest_rel)


def task_ledger_authority_export_compatibility(repo_root: Path) -> Dict[str, Any]:
    repo_root = Path(repo_root)
    with file_lock(repo_root / LOCK_REL):
        manifest = _active_authority_manifest(repo_root)
        if manifest is None:
            return {
                "schema": "task_ledger_authority_compatibility_export_v0",
                "ok": True,
                "status": "legacy_monolith_already_authority",
                "mode": TASK_LEDGER_AUTHORITY_MODE_LEGACY,
                "storage_state": task_ledger_authority_storage_state(repo_root),
            }
        event_export = _export_authority_stream_to_jsonl(repo_root, dest_rel=EVENTS_REL, audit=False)
        audit_export = _export_authority_stream_to_jsonl(repo_root, dest_rel=EVENTS_AUDIT_REL, audit=True)
        refreshed = dict(manifest)
        compat = dict(refreshed.get("compatibility_export") or {})
        compat.update(
            {
                "path": str(EVENTS_REL),
                "status": TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID,
                "valid_at": utc_now(),
                "normalized_jsonl_sha256": event_export["sha256"],
                "event_count": event_export["event_count"],
                "byte_count": event_export["byte_count"],
            }
        )
        refreshed["compatibility_export"] = compat
        audit = dict(refreshed.get("audit_journal") or {})
        audit_compat = dict(audit.get("compatibility_export") or {})
        audit_compat.update(
            {
                "path": str(EVENTS_AUDIT_REL),
                "status": TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_VALID,
                "valid_at": compat["valid_at"],
                "normalized_jsonl_sha256": audit_export["sha256"],
                "event_count": audit_export["event_count"],
                "byte_count": audit_export["byte_count"],
            }
        )
        audit["compatibility_export"] = audit_compat
        refreshed["audit_journal"] = audit
        refreshed["updated_at"] = utc_now()
        atomic_write_json(_authority_manifest_path(repo_root), refreshed)
        return {
            "schema": "task_ledger_authority_compatibility_export_v0",
            "ok": True,
            "status": "compatibility_export_refreshed",
            "mode": TASK_LEDGER_AUTHORITY_MODE_ACTIVE,
            "event_export": event_export,
            "audit_export": audit_export,
            "storage_state": task_ledger_authority_storage_state(repo_root),
        }


def _event_log_tail_state(repo_root: Path) -> tuple[str | None, int]:
    count = 0
    tail_raw_line: bytes | None = None
    tail_path = event_log_path(repo_root)
    for path, _line_number, _event_id, raw_line in _iter_authority_event_id_lines(repo_root):
        count += 1
        tail_path = path
        tail_raw_line = raw_line
    return _tail_hash_from_raw_event_line(tail_path, tail_raw_line), count


def _closed_segment_event_count(manifest: Mapping[str, Any], *, audit: bool = False) -> int:
    if audit:
        audit_journal = manifest.get("audit_journal")
        segments = (
            audit_journal.get("segments")
            if isinstance(audit_journal, Mapping) and isinstance(audit_journal.get("segments"), list)
            else []
        )
    else:
        segments = manifest.get("segments") if isinstance(manifest.get("segments"), list) else []
    return sum(
        int(row.get("event_count") or 0)
        for row in segments
        if isinstance(row, Mapping)
    )


def _active_append_targets(repo_root: Path) -> tuple[Path, Path, Dict[str, Any] | None]:
    manifest = _active_authority_manifest(repo_root)
    if manifest is None:
        return EVENTS_REL, EVENTS_AUDIT_REL, None
    return _manifest_open_tail_rel(manifest), _manifest_audit_open_tail_rel(manifest), manifest


def _refresh_active_authority_manifest_after_append_unlocked(repo_root: Path) -> None:
    manifest = _active_authority_manifest(repo_root)
    if manifest is None:
        return
    event_tail_rel = _manifest_open_tail_rel(manifest)
    audit_tail_rel = _manifest_audit_open_tail_rel(manifest)
    refreshed = dict(manifest)
    event_tail = _normalized_jsonl_file_summary(repo_root / event_tail_rel, rel_path=event_tail_rel)
    refreshed["open_tail"] = event_tail
    refreshed["open_tail_event_count"] = int(event_tail.get("event_count") or 0)
    refreshed["authority_event_count"] = _closed_segment_event_count(refreshed) + int(
        event_tail.get("event_count") or 0
    )
    compat = dict(refreshed.get("compatibility_export") or {})
    compat["path"] = str(EVENTS_REL)
    compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_STALE
    compat["stale_since"] = utc_now()
    compat["stale_reason"] = "active segmented append is not mirrored to compatibility export"
    refreshed["compatibility_export"] = compat
    audit_journal = dict(refreshed.get("audit_journal") or {})
    audit_tail = _normalized_jsonl_file_summary(repo_root / audit_tail_rel, rel_path=audit_tail_rel)
    audit_journal["open_tail"] = audit_tail
    audit_journal["open_tail_event_count"] = int(audit_tail.get("event_count") or 0)
    audit_journal["audit_event_count"] = _closed_segment_event_count(refreshed, audit=True) + int(
        audit_tail.get("event_count") or 0
    )
    audit_compat = dict(audit_journal.get("compatibility_export") or {})
    audit_compat["path"] = str(EVENTS_AUDIT_REL)
    audit_compat["status"] = TASK_LEDGER_AUTHORITY_COMPAT_EXPORT_STALE
    audit_compat["stale_since"] = compat["stale_since"]
    audit_compat["stale_reason"] = "active segmented audit append is not mirrored to compatibility export"
    audit_journal["compatibility_export"] = audit_compat
    refreshed["audit_journal"] = audit_journal
    refreshed["updated_at"] = utc_now()
    refreshed["last_append_storage_effect"] = "open_tail_appended_compatibility_export_marked_stale"
    atomic_write_json(_authority_manifest_path(repo_root), refreshed)


def _coerce_refs(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _coerce_payload(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TaskLedgerError("event.payload must be an object")
    return dict(value)


def _normalize_event(event: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(event)
    normalized.setdefault("schema_version", TASK_LEDGER_EVENT_SCHEMA)
    if normalized["schema_version"] != TASK_LEDGER_EVENT_SCHEMA:
        raise TaskLedgerError(f"unsupported event schema_version {normalized['schema_version']!r}")
    normalized["event_id"] = str(normalized.get("event_id") or mint_event_id()).strip()
    if not EVENT_ID_RE.match(normalized["event_id"]):
        raise TaskLedgerError(f"event_id {normalized['event_id']!r} must start with wie_")
    normalized["event_type"] = str(normalized.get("event_type") or "").strip()
    if normalized["event_type"] not in EVENT_TYPES:
        raise TaskLedgerError(f"event_type {normalized['event_type']!r} is not allowed")
    normalized["created_at"] = str(normalized.get("created_at") or utc_now()).strip()
    normalized["created_by"] = str(normalized.get("created_by") or "codex").strip()
    normalized["agent_run_id"] = str(normalized.get("agent_run_id") or "").strip() or None
    normalized["thread_id"] = str(normalized.get("thread_id") or "").strip() or None
    normalized["subject_id"] = str(normalized.get("subject_id") or "").strip()
    if not normalized["subject_id"]:
        raise TaskLedgerError("event.subject_id is required")
    normalized["subject_kind"] = str(normalized.get("subject_kind") or "work_item").strip()
    normalized["source"] = dict(normalized.get("source") or {})
    normalized["refs"] = _coerce_refs(normalized.get("refs"))
    normalized["payload"] = _coerce_payload(normalized.get("payload"))
    return normalized


def _has_historical_exists_receipt(entry: Mapping[str, Any]) -> bool:
    evidence = entry.get("evidence")
    return (
        isinstance(evidence, Mapping)
        and str(evidence.get("observed_result") or "").strip() == "exists"
        and bool(str(evidence.get("command") or "").strip())
    )


def _is_volatile_absolute_path(path_value: str) -> bool:
    path = Path(path_value)
    if not path.is_absolute():
        return False
    text = str(path)
    volatile_roots = {"/tmp", "/private/tmp", str(Path(tempfile.gettempdir()).resolve())}
    return any(text == root or text.startswith(f"{root}/") for root in volatile_roots)


def _is_local_absolute_path(path_value: str) -> bool:
    return bool(path_value) and Path(path_value).is_absolute()


def _surface_ref_looks_pathlike(surface: str) -> bool:
    value = surface.strip()
    if not value:
        return False
    if value.startswith(("/", "./", "../", "~")):
        return True
    if "/" in value or "\\" in value:
        return True
    return value.endswith(PATHLIKE_SURFACE_SUFFIXES)


def classify_surface_entry(entry: Mapping[str, Any]) -> Dict[str, Any]:
    """Classify exact surface evidence without weakening validation rules."""
    status = str(entry.get("status") or "exists").strip()
    path_value = str(entry.get("path") or "").strip()
    path = Path(path_value) if path_value else Path()
    if status == "exists":
        if path_value and _is_volatile_absolute_path(path_value):
            artifact_class = "ephemeral_local"
            validation_policy = "historical_observation_only"
            durable_proof = False
        elif path.is_absolute():
            artifact_class = "local_absolute_path"
            validation_policy = "append_current_existence_replay_historical_observation"
            durable_proof = False
        else:
            artifact_class = "repo_path_durable"
            validation_policy = "require_current_existence"
            durable_proof = True
    elif status == "missing":
        if path_value and not _surface_ref_looks_pathlike(path_value):
            artifact_class = "implied_surface"
            validation_policy = "legacy_logical_surface_ref_normalized"
        else:
            artifact_class = "missing_surface_receipt"
            validation_policy = "require_absence_evidence"
        durable_proof = False
    elif status == "command":
        artifact_class = "command_evidence"
        validation_policy = "require_evidence"
        durable_proof = True
    elif status == "schema":
        artifact_class = "schema_surface"
        validation_policy = "require_evidence"
        durable_proof = True
    elif status == "implied":
        artifact_class = "implied_surface"
        validation_policy = "require_evidence"
        durable_proof = False
    else:
        artifact_class = "unknown_surface"
        validation_policy = "invalid_status"
        durable_proof = False
    return {
        "schema": "task_ledger_exact_surface_classification_v0",
        "status": status,
        "artifact_class": artifact_class,
        "validation_policy": validation_policy,
        "durable_proof": durable_proof,
        "ephemeral_local": artifact_class == "ephemeral_local",
    }


def _validate_surface_entry(
    repo_root: Path,
    entry: Mapping[str, Any],
    *,
    allow_historical_local_absence: bool = False,
) -> None:
    status = str(entry.get("status") or "exists").strip()
    path_value = str(entry.get("path") or "").strip()
    evidence = entry.get("evidence")
    if status in {"exists", "missing"} and not path_value:
        raise TaskLedgerError("exact_surfaces_discovered entry requires path")
    if status == "exists":
        if (
            not (repo_root / path_value).exists()
            and not _has_historical_exists_receipt(entry)
            and not allow_historical_local_absence
        ):
            raise TaskLedgerError(
                f"exact_surfaces_discovered path {path_value!r} is marked exists but is absent"
            )
    elif status == "missing":
        if not isinstance(evidence, Mapping):
            raise TaskLedgerError(
                f"missing surface {path_value!r} requires an evidence object"
            )
    elif status in {"command", "schema", "implied"}:
        if not isinstance(evidence, Mapping):
            raise TaskLedgerError(f"{status} surface entry requires evidence")
    else:
        raise TaskLedgerError(f"surface status {status!r} is not allowed")


def validate_integration_contract(
    repo_root: Path,
    contract: Mapping[str, Any],
    *,
    allow_historical_local_absence: bool = False,
) -> None:
    exact = contract.get("exact_surfaces_discovered")
    if exact is None:
        return
    if not isinstance(exact, list):
        raise TaskLedgerError("integration_contract.exact_surfaces_discovered must be an array")
    for entry in exact:
        if not isinstance(entry, Mapping):
            raise TaskLedgerError("exact_surfaces_discovered entries must be objects")
        _validate_surface_entry(
            repo_root,
            entry,
            allow_historical_local_absence=allow_historical_local_absence,
        )


def _integration_contracts_from_payload(payload: Mapping[str, Any]) -> List[Mapping[str, Any]]:
    contracts: List[Mapping[str, Any]] = []
    maybe = payload.get("integration_contract")
    if isinstance(maybe, Mapping):
        contracts.append(maybe)
    legacy = _legacy_contracts_integration_contract(payload)
    if legacy:
        contracts.append(legacy)
    work_item = payload.get("work_item")
    if isinstance(work_item, Mapping) and isinstance(work_item.get("integration_contract"), Mapping):
        contracts.append(work_item["integration_contract"])  # type: ignore[index]
    return contracts


def validate_event(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    allow_historical_local_absence: bool = False,
) -> Dict[str, Any]:
    normalized = _normalize_event(event)
    for contract in _integration_contracts_from_payload(normalized["payload"]):
        validate_integration_contract(
            repo_root,
            contract,
            allow_historical_local_absence=allow_historical_local_absence,
        )
    return normalized


def _projected_state_after_candidates(
    repo_root: Path,
    existing_events: Sequence[Mapping[str, Any]],
    candidate_events: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Build the projection that would result from appending candidate events."""
    normalized_existing = [
        validate_event(
            repo_root,
            event,
            allow_historical_local_absence=True,
        )
        for event in existing_events
    ]
    normalized_candidates = [
        validate_event(repo_root, event)
        for event in candidate_events
    ]
    return build_projection(
        [*normalized_existing, *normalized_candidates],
        mission_blackboard=_safe_read_json(repo_root / MISSION_BLACKBOARD_REL),
        repo_root=repo_root,
    )


def _validate_projected_state_after_candidates(
    repo_root: Path,
    existing_events: Sequence[Mapping[str, Any]],
    candidate_events: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    """Reject candidate appends that would make deterministic projections invalid."""
    projection = _projected_state_after_candidates(repo_root, existing_events, candidate_events)
    _validate_projection_state(projection)
    return projection


def append_event(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    expected_previous_event_hash: str | None = None,
    allow_authority_recovery: bool = False,
    preflight_projection: bool = True,
) -> Dict[str, Any]:
    with file_lock(repo_root / LOCK_REL):
        return _append_event_unlocked(
            repo_root,
            event,
            expected_previous_event_hash=expected_previous_event_hash,
            allow_authority_recovery=allow_authority_recovery,
            preflight_projection=preflight_projection,
        )


def _append_event_unlocked(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    expected_previous_event_hash: str | None = None,
    allow_authority_recovery: bool = False,
    preflight_projection: bool = True,
    return_preflight_projection: bool = False,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    event_rel, audit_rel, active_manifest = _active_append_targets(repo_root)
    path = repo_root / event_rel
    events = read_authority_events(repo_root)
    if not allow_authority_recovery:
        lost = _find_lost_audit_events_from_rows(repo_root, events)
        if lost:
            raise TaskLedgerError(_authority_recovery_error(lost))
    existing_by_id = {str(row.get("event_id") or ""): row for row in events}
    normalized = validate_event(repo_root, event)
    if normalized["event_id"] in existing_by_id:
        existing = existing_by_id[normalized["event_id"]]
        incoming_hash = str(normalized.get("event_hash") or "").strip()
        existing_hash = str(existing.get("event_hash") or "").strip()
        if incoming_hash and incoming_hash != existing_hash:
            raise TaskLedgerError(
                f"duplicate event_id {normalized['event_id']} carries a different event_hash"
            )
        candidate = dict(normalized)
        candidate["previous_event_hash"] = existing.get("previous_event_hash")
        if compute_event_hash(candidate) != existing_hash:
            raise TaskLedgerError(
                f"duplicate event_id {normalized['event_id']} carries different event content"
            )
        return {"ok": True, "status": "duplicate_idempotent", "event": existing}
    tail = _tail_hash(events)
    expected = expected_previous_event_hash or normalized.pop("expected_previous_event_hash", None)
    if expected is not None and expected != tail:
        raise TaskLedgerError(
            f"expected_previous_event_hash {expected!r} does not match current tail {tail!r}"
        )
    _enforce_closeout_assurance_for_append(events, normalized)
    normalized["previous_event_hash"] = tail
    normalized["event_hash"] = compute_event_hash(normalized)
    preflight_projection_payload = None
    if preflight_projection:
        _emit_progress(
            progress_callback,
            "load_validate_start",
            check=False,
            mode="preflight_projection",
        )
        _emit_progress(
            progress_callback,
            "build_projection_start",
            check=False,
            mode="preflight_projection",
            event_count=len(events) + 1,
        )
        preflight_projection_payload = _validate_projected_state_after_candidates(repo_root, events, [normalized])
        _emit_progress(
            progress_callback,
            "build_projection_done",
            check=False,
            mode="preflight_projection",
            event_count=len(events) + 1,
            projection_path_count=len(_projection_targets(preflight_projection_payload)),
            work_item_count=len(preflight_projection_payload["ledger"].get("work_items") or []),
            signoff_count=len(preflight_projection_payload["sign_offs"].get("sign_offs") or []),
        )
        _emit_progress(
            progress_callback,
            "load_validate_done",
            check=False,
            mode="preflight_projection",
            event_count=len(events) + 1,
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    if not allow_authority_recovery:
        headroom = task_ledger_disk_write_headroom(
            repo_root,
            operation="append_event",
            rel_paths=[event_rel, audit_rel],
        )
        if not bool(headroom.get("ok")):
            raise TaskLedgerError(
                f"Task Ledger append blocked by {headroom.get('status')}: "
                f"{headroom.get('next_step')}"
            )
    line = json.dumps(normalized, ensure_ascii=False, sort_keys=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _append_audit_journal(repo_root / audit_rel, line)
    if active_manifest is not None:
        _refresh_active_authority_manifest_after_append_unlocked(repo_root)
    result: Dict[str, Any] = {"ok": True, "status": "appended", "event": normalized}
    if return_preflight_projection and preflight_projection_payload is not None:
        result["_preflight_projection"] = preflight_projection_payload
    return result


def _duplicate_append_result(
    normalized: Mapping[str, Any],
    existing: Mapping[str, Any],
) -> Dict[str, Any]:
    incoming_hash = str(normalized.get("event_hash") or "").strip()
    existing_hash = str(existing.get("event_hash") or "").strip()
    if incoming_hash and incoming_hash != existing_hash:
        raise TaskLedgerError(
            f"duplicate event_id {normalized['event_id']} carries a different event_hash"
        )
    candidate = dict(normalized)
    candidate["previous_event_hash"] = existing.get("previous_event_hash")
    if compute_event_hash(candidate) != existing_hash:
        raise TaskLedgerError(
            f"duplicate event_id {normalized['event_id']} carries different event content"
        )
    return {"ok": True, "status": "duplicate_idempotent", "event": dict(existing)}


def _prepare_event_append_candidate(
    repo_root: Path,
    event: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    *,
    expected_previous_event_hash: str | None = None,
    allow_authority_recovery: bool = False,
    build_preflight_projection: bool = True,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    if not allow_authority_recovery:
        lost = _find_lost_audit_events_from_rows(repo_root, events)
        if lost:
            raise TaskLedgerError(_authority_recovery_error(lost))
    existing_by_id = {str(row.get("event_id") or ""): row for row in events}
    normalized = validate_event(repo_root, event)
    event_id = str(normalized.get("event_id") or "")
    if event_id in existing_by_id:
        duplicate = _duplicate_append_result(normalized, existing_by_id[event_id])
        duplicate["authority_tail_hash"] = _tail_hash(events)
        duplicate["preflight_event_count"] = len(events)
        return duplicate
    tail = _tail_hash(events)
    expected = expected_previous_event_hash or normalized.pop("expected_previous_event_hash", None)
    if expected is not None and expected != tail:
        raise TaskLedgerError(
            f"expected_previous_event_hash {expected!r} does not match current tail {tail!r}"
        )
    _enforce_closeout_assurance_for_append(events, normalized)
    normalized["previous_event_hash"] = tail
    normalized["event_hash"] = compute_event_hash(normalized)
    preflight_projection_payload = None
    if build_preflight_projection:
        _emit_progress(
            progress_callback,
            "load_validate_start",
            check=False,
            mode="prelock_preflight_projection",
        )
        _emit_progress(
            progress_callback,
            "build_projection_start",
            check=False,
            mode="prelock_preflight_projection",
            event_count=len(events) + 1,
        )
        preflight_projection_payload = _validate_projected_state_after_candidates(
            repo_root, events, [normalized]
        )
        _emit_progress(
            progress_callback,
            "build_projection_done",
            check=False,
            mode="prelock_preflight_projection",
            event_count=len(events) + 1,
            projection_path_count=len(_projection_targets(preflight_projection_payload)),
            work_item_count=len(preflight_projection_payload["ledger"].get("work_items") or []),
            signoff_count=len(preflight_projection_payload["sign_offs"].get("sign_offs") or []),
        )
        _emit_progress(
            progress_callback,
            "load_validate_done",
            check=False,
            mode="prelock_preflight_projection",
            event_count=len(events) + 1,
        )
    return {
        "ok": True,
        "status": "prepared_append",
        "event": normalized,
        "authority_tail_hash": tail,
        "preflight_event_count": len(events),
        "_preflight_projection": preflight_projection_payload,
    }


def _prepare_fast_unique_capture_append_candidate(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    expected_previous_event_hash: str | None = None,
    allow_authority_recovery: bool = False,
) -> Dict[str, Any] | None:
    if expected_previous_event_hash is not None or allow_authority_recovery:
        return None
    normalized = validate_event(repo_root, event)
    if str(normalized.get("event_type") or "") != "work_item.captured":
        return None
    event_id = str(normalized.get("event_id") or "").strip()
    if not event_id:
        return None
    health = _authority_health_unlocked(repo_root, event_ids=[event_id])
    if health.get("status") != "clean":
        raise TaskLedgerError(_authority_recovery_error(health.get("lost_events") or []))
    selected_visibility = (
        health.get("selected_event_visibility")
        if isinstance(health.get("selected_event_visibility"), Mapping)
        else {}
    )
    if selected_visibility.get(event_id):
        return None
    tail = str(health.get("tail_hash") or "").strip() or None
    normalized["previous_event_hash"] = tail
    normalized["event_hash"] = compute_event_hash(normalized)
    return {
        "ok": True,
        "status": "prepared_append",
        "event": normalized,
        "authority_tail_hash": tail,
        "preflight_event_count": int(health.get("authority_event_count") or 0),
        "_preflight_projection": None,
        "_authority_health": health,
        "prepare_mode": "fast_unique_capture_append",
    }


def _append_normalized_event_unlocked(repo_root: Path, normalized: Mapping[str, Any]) -> Dict[str, Any]:
    event_rel, audit_rel, active_manifest = _active_append_targets(repo_root)
    path = repo_root / event_rel
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(normalized), ensure_ascii=False, sort_keys=False)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    _append_audit_journal(repo_root / audit_rel, line)
    if active_manifest is not None:
        _refresh_active_authority_manifest_after_append_unlocked(repo_root)
    return {"ok": True, "status": "appended", "event": dict(normalized)}


def _rebuild_projections_with_health_unlocked(
    repo_root: Path,
    *,
    check: bool = False,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    _emit_progress(progress_callback, "authority_health_start", check=bool(check))
    health = _authority_health_unlocked(repo_root)
    _emit_progress(
        progress_callback,
        "authority_health_done",
        check=bool(check),
        status=health.get("status"),
        ok=health.get("ok"),
        authority_event_count=health.get("authority_event_count"),
        audit_event_count=health.get("audit_event_count"),
        lost_count=health.get("lost_count"),
    )
    if health.get("status") != "clean":
        return {
            "ok": False,
            "checked": bool(check),
            "status": "authority_recovery_required",
            "authority_health": health,
        }
    fast_check = _projection_manifest_fast_check(
        repo_root,
        authority_event_count=int(health.get("authority_event_count") or 0),
        authority_tail_hash=str(health.get("tail_hash") or "").strip() or None,
    )
    if check and fast_check is not None:
        fast_check["authority_health"] = health
        return fast_check
    if not check and fast_check is not None and bool(fast_check.get("ok")):
        manifest_check = fast_check.get("projection_manifest_check")
        manifest_check = manifest_check if isinstance(manifest_check, Mapping) else {}
        manifest = _safe_read_json(repo_root / PROJECTION_MANIFEST_REL)
        target_rows = manifest.get("target_hashes") if isinstance(manifest, Mapping) else []
        projection_paths = [
            str(row.get("path"))
            for row in target_rows
            if isinstance(row, Mapping) and str(row.get("path") or "").strip()
        ]
        return {
            "ok": True,
            "checked": False,
            "status": "already_current",
            "event_count": health.get("authority_event_count"),
            "projection_paths": projection_paths,
            "projection_manifest": {
                "path": str(PROJECTION_MANIFEST_REL),
                "target_count": manifest_check.get("target_count")
                or len(projection_paths),
            },
            "projection_manifest_check": manifest_check,
            "authority_health": health,
            "rebuild_skipped": True,
            "skip_reason": "projection_manifest_current",
        }
    result = _rebuild_projections_unlocked(repo_root, check=check, progress_callback=progress_callback)
    result["authority_health"] = health
    return result


def _projection_targets(projection: Mapping[str, Any]) -> Dict[Path, Mapping[str, Any]]:
    targets: Dict[Path, Mapping[str, Any]] = {
        LEDGER_REL: projection["ledger"],
        SIGNOFFS_REL: projection["sign_offs"],
    }
    for name, payload in projection["views"].items():
        targets[VIEWS_REL / f"{name}.json"] = payload
    return targets


def _projection_result(
    projection: Mapping[str, Any],
    targets: Mapping[Path, Mapping[str, Any]],
) -> Dict[str, Any]:
    ledger = projection["ledger"]
    signoffs = projection["sign_offs"]
    views = projection["views"]
    return {
        "ok": True,
        "checked": False,
        "event_count": int(ledger.get("event_count") or 0),
        "projection_paths": [str(path) for path in targets],
        "counts": {
            "work_items": len(ledger.get("work_items") or []),
            "tasks": len(ledger.get("tasks") or []),
            "captures": views["capture_inbox"]["count"],
            "sign_offs": len(signoffs.get("sign_offs") or []),
        },
    }


def _write_projection_from_preflight_unlocked(
    repo_root: Path,
    projection: Mapping[str, Any],
    *,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    _emit_progress(progress_callback, "authority_health_start", check=False)
    health = _authority_health_unlocked(repo_root)
    _emit_progress(
        progress_callback,
        "authority_health_done",
        check=False,
        status=health.get("status"),
        ok=health.get("ok"),
        authority_event_count=health.get("authority_event_count"),
        audit_event_count=health.get("audit_event_count"),
        lost_count=health.get("lost_count"),
    )
    if health.get("status") != "clean":
        return {
            "ok": False,
            "checked": False,
            "status": "authority_recovery_required",
            "authority_health": health,
        }
    targets = _projection_targets(projection)
    headroom = task_ledger_disk_write_headroom(
        repo_root,
        operation="task_ledger_projection_write",
        rel_paths=[*list(targets), PROJECTION_MANIFEST_REL],
    )
    if not bool(headroom.get("ok")):
        _emit_disk_headroom_blocked(progress_callback, headroom)
        return _disk_headroom_block_result(headroom)
    _emit_progress(
        progress_callback,
        "projection_write_start",
        projection_path_count=len(targets),
    )
    for rel_path, payload in targets.items():
        atomic_write_json(repo_root / rel_path, payload, compact=True)
    manifest = _write_projection_manifest(
        repo_root,
        targets,
        authority_event_count=int(health.get("authority_event_count") or 0),
        authority_tail_hash=str(health.get("tail_hash") or "").strip() or None,
    )
    _emit_progress(
        progress_callback,
        "projection_write_done",
        projection_path_count=len(targets),
    )
    result = _projection_result(projection, targets)
    result["authority_health"] = health
    result["build_reuse"] = {
        "mode": "preflight_projection_reused",
        "saved_projection_rebuild": True,
    }
    result["projection_manifest"] = {
        "path": str(PROJECTION_MANIFEST_REL),
        "target_count": manifest.get("target_count"),
    }
    return result


def append_event_and_rebuild(
    repo_root: Path,
    event: Mapping[str, Any],
    *,
    expected_previous_event_hash: str | None = None,
    rebuild: bool = True,
    allow_authority_recovery: bool = False,
    progress_callback: TaskLedgerProgressCallback | None = None,
    fast_unique_capture_append: bool = False,
) -> Dict[str, Any]:
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        _emit_progress(
            progress_callback,
            "prelock_prepare_start",
            operation="append_event_and_rebuild",
            rebuild=bool(rebuild),
            event_count=1,
            attempt=attempt,
        )
        prepared = None
        if fast_unique_capture_append and not rebuild:
            prepared = _prepare_fast_unique_capture_append_candidate(
                repo_root,
                event,
                expected_previous_event_hash=expected_previous_event_hash,
                allow_authority_recovery=allow_authority_recovery,
            )
        if prepared is None:
            snapshot_events = read_authority_events(repo_root)
            prepared = _prepare_event_append_candidate(
                repo_root,
                event,
                snapshot_events,
                expected_previous_event_hash=expected_previous_event_hash,
                allow_authority_recovery=allow_authority_recovery,
                build_preflight_projection=bool(rebuild),
                progress_callback=progress_callback,
            )
        _emit_progress(
            progress_callback,
            "prelock_prepare_done",
            operation="append_event_and_rebuild",
            status=prepared.get("status"),
            rebuild=bool(rebuild),
            event_count=1,
            attempt=attempt,
        )
        _emit_progress(
            progress_callback,
            "lock_wait_start",
            operation="append_event_and_rebuild",
            rebuild=bool(rebuild),
            event_count=1,
            attempt=attempt,
        )
        with file_lock(repo_root / LOCK_REL):
            _emit_progress(
                progress_callback,
                "lock_acquired",
                operation="append_event_and_rebuild",
                rebuild=bool(rebuild),
                event_count=1,
                attempt=attempt,
            )
            current_tail, current_event_count = _event_log_tail_state(repo_root)
            prepared_tail = prepared.get("authority_tail_hash")
            if current_tail != prepared_tail:
                _emit_progress(
                    progress_callback,
                    "authority_snapshot_changed_retry",
                    operation="append_event_and_rebuild",
                    attempt=attempt,
                    max_attempts=max_attempts,
                    snapshot_event_count=prepared.get("preflight_event_count"),
                    current_event_count=current_event_count,
                )
                continue
            if prepared.get("status") == "duplicate_idempotent":
                result = {
                    "ok": True,
                    "status": "duplicate_idempotent",
                    "event": dict(prepared.get("event") or {}),
                }
                projection_result = None
            else:
                _emit_progress(
                    progress_callback,
                    "append_start",
                    operation="append_event_and_rebuild",
                    event_type=event.get("event_type"),
                    subject_id=event.get("subject_id"),
                )
                headroom_paths = _authority_write_rel_paths(repo_root)
                preflight_projection = prepared.get("_preflight_projection")
                if rebuild:
                    if isinstance(preflight_projection, Mapping):
                        headroom_paths.extend(_projection_targets(preflight_projection))
                    else:
                        headroom_paths.extend(_current_projection_rel_paths(repo_root))
                headroom = task_ledger_disk_write_headroom(
                    repo_root,
                    operation="append_event_and_rebuild",
                    rel_paths=headroom_paths,
                )
                if not bool(headroom.get("ok")):
                    _emit_disk_headroom_blocked(progress_callback, headroom)
                    blocked_result = _disk_headroom_block_result(headroom)
                    blocked_result["task_ledger_mutation_serialization"] = (
                        task_ledger_mutation_serialization_receipt(
                            event_count=0,
                            projection_rebuilt=False,
                            projection_rebuilt_under_same_lock=False,
                            projection_build_under_same_lock=False,
                            projection_write_under_same_lock=False,
                        )
                    )
                    _emit_progress(
                        progress_callback,
                        "done",
                        operation="append_event_and_rebuild",
                        status=blocked_result.get("status"),
                        rebuild=bool(rebuild),
                        projection_rebuilt=False,
                    )
                    return blocked_result
                result = _append_normalized_event_unlocked(
                    repo_root,
                    prepared["event"],
                )
                appended_event = result.get("event") if isinstance(result.get("event"), Mapping) else {}
                _emit_progress(
                    progress_callback,
                    "append_done",
                    operation="append_event_and_rebuild",
                    status=result.get("status"),
                    event_id=appended_event.get("event_id"),
                    subject_id=appended_event.get("subject_id"),
                )
                projection_result = None
                if rebuild:
                    _emit_progress(
                        progress_callback,
                        "rebuild_start",
                        operation="append_event_and_rebuild",
                        check=False,
                        mode="preflight_projection_write",
                    )
                    if isinstance(preflight_projection, Mapping):
                        projection_result = _write_projection_from_preflight_unlocked(
                            repo_root,
                            preflight_projection,
                            progress_callback=progress_callback,
                        )
                    else:
                        projection_result = _rebuild_projections_with_health_unlocked(
                            repo_root,
                            progress_callback=progress_callback,
                        )
                    _emit_progress(
                        progress_callback,
                        "rebuild_done",
                        operation="append_event_and_rebuild",
                        status=projection_result.get("status"),
                        ok=projection_result.get("ok"),
                        event_count=projection_result.get("event_count"),
                        projection_path_count=len(projection_result.get("projection_paths") or []),
                    )
                    result["projection"] = projection_result
            if rebuild and prepared.get("status") == "duplicate_idempotent":
                projection_result = _rebuild_projections_with_health_unlocked(
                    repo_root,
                    progress_callback=progress_callback,
                )
                result["projection"] = projection_result
            _emit_progress(
                progress_callback,
                "done",
                operation="append_event_and_rebuild",
                status=result.get("status"),
                rebuild=bool(rebuild),
                projection_rebuilt=bool(projection_result),
            )
            result["task_ledger_mutation_serialization"] = task_ledger_mutation_serialization_receipt(
                event_count=0 if result.get("status") == "duplicate_idempotent" else 1,
                projection_rebuilt=bool(projection_result),
                projection_rebuilt_under_same_lock=False,
                projection_build_under_same_lock=False,
                projection_write_under_same_lock=bool(projection_result),
            )
            return result
    return {
        "ok": False,
        "status": "authority_snapshot_changed_retry_required",
        "reason": (
            "Task Ledger authority changed during repeated append preflight attempts; "
            "rerun the append command so projection validation uses a fresh authority tail."
        ),
        "attempt_count": max_attempts,
        "task_ledger_mutation_serialization": task_ledger_mutation_serialization_receipt(
            event_count=0,
            projection_rebuilt=False,
            projection_rebuilt_under_same_lock=False,
            projection_build_under_same_lock=False,
            projection_write_under_same_lock=False,
        ),
    }


def append_events_and_rebuild(
    repo_root: Path,
    events: Sequence[Mapping[str, Any]],
    *,
    rebuild: bool = True,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    event_list = list(events)
    _emit_progress(
        progress_callback,
        "lock_wait_start",
        operation="append_events_and_rebuild",
        rebuild=bool(rebuild),
        event_count=len(event_list),
    )
    with file_lock(repo_root / LOCK_REL):
        _emit_progress(
            progress_callback,
            "lock_acquired",
            operation="append_events_and_rebuild",
            rebuild=bool(rebuild),
            event_count=len(event_list),
        )
        _emit_progress(
            progress_callback,
            "batch_preflight_start",
            operation="append_events_and_rebuild",
            event_count=len(event_list),
        )
        headroom_paths = _authority_write_rel_paths(repo_root)
        if rebuild:
            headroom_paths.extend(_current_projection_rel_paths(repo_root))
        headroom = task_ledger_disk_write_headroom(
            repo_root,
            operation="append_events_and_rebuild",
            rel_paths=headroom_paths,
        )
        if not bool(headroom.get("ok")):
            _emit_disk_headroom_blocked(progress_callback, headroom)
            blocked_result = _disk_headroom_block_result(headroom)
            blocked_result["task_ledger_mutation_serialization"] = (
                task_ledger_mutation_serialization_receipt(
                    event_count=0,
                    projection_rebuilt=False,
                    projection_rebuilt_under_same_lock=False,
                )
            )
            _emit_progress(
                progress_callback,
                "done",
                operation="append_events_and_rebuild",
                status=blocked_result.get("status"),
                rebuild=bool(rebuild),
                projection_rebuilt=False,
            )
            return blocked_result
        existing_events = read_authority_events(repo_root)
        normalized_events = [validate_event(repo_root, event) for event in event_list]
        _validate_projected_state_after_candidates(repo_root, existing_events, normalized_events)
        candidate_history: list[Mapping[str, Any]] = list(existing_events)
        prepared_results: list[Dict[str, Any]] = []
        for event in normalized_events:
            prepared = _prepare_event_append_candidate(
                repo_root,
                event,
                candidate_history,
                build_preflight_projection=False,
                progress_callback=progress_callback,
            )
            prepared_results.append(prepared)
            if prepared.get("status") == "prepared_append":
                candidate_history.append(dict(prepared.get("event") or {}))
        _emit_progress(
            progress_callback,
            "batch_preflight_done",
            operation="append_events_and_rebuild",
            existing_event_count=len(existing_events),
            event_count=len(normalized_events),
        )
        _emit_progress(
            progress_callback,
            "append_start",
            operation="append_events_and_rebuild",
            event_count=len(normalized_events),
        )
        append_results = []
        for prepared in prepared_results:
            if prepared.get("status") == "duplicate_idempotent":
                append_results.append(
                    {
                        "ok": True,
                        "status": "duplicate_idempotent",
                        "event": dict(prepared.get("event") or {}),
                    }
                )
                continue
            append_results.append(
                _append_normalized_event_unlocked(repo_root, prepared["event"])
            )
        _emit_progress(
            progress_callback,
            "append_done",
            operation="append_events_and_rebuild",
            event_count=len(append_results),
        )
        projection_result = None
        if rebuild and append_results:
            _emit_progress(
                progress_callback,
                "rebuild_start",
                operation="append_events_and_rebuild",
                check=False,
            )
            projection_result = _rebuild_projections_with_health_unlocked(
                repo_root,
                progress_callback=progress_callback,
            )
            _emit_progress(
                progress_callback,
                "rebuild_done",
                operation="append_events_and_rebuild",
                status=projection_result.get("status"),
                ok=projection_result.get("ok"),
                event_count=projection_result.get("event_count"),
                projection_path_count=len(projection_result.get("projection_paths") or []),
            )
        out: Dict[str, Any] = {
            "ok": True,
            "status": "batch_appended",
            "appended_count": len(append_results),
            "append_results": append_results,
            "task_ledger_mutation_serialization": task_ledger_mutation_serialization_receipt(
                event_count=len(append_results),
                projection_rebuilt=bool(projection_result),
                projection_rebuilt_under_same_lock=bool(projection_result),
            ),
        }
        if projection_result is not None:
            out["projection"] = projection_result
        _emit_progress(
            progress_callback,
            "done",
            operation="append_events_and_rebuild",
            status=out.get("status"),
            rebuild=bool(rebuild),
            projection_rebuilt=bool(projection_result),
        )
        return out


def _legacy_task_to_work_item(task: Mapping[str, Any]) -> Dict[str, Any]:
    status = str(task.get("status") or "proposed")
    work_item_type = "task"
    item: Dict[str, Any] = {
        "id": task.get("id"),
        "kind": "work_item",
        "work_item_type": work_item_type,
        "title": task.get("title"),
        "slug": task.get("slug"),
        "statement": task.get("statement"),
        "state": LEGACY_STATUS_TO_STATE.get(status, "captured"),
        "status": status,
        "rank": task.get("rank"),
        "confidence": task.get("confidence"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "author": task.get("author"),
        "compression_passport": task.get("compression_passport"),
        "satisfaction_contract": task.get("satisfaction_contract") or {},
        "integration_contract": task.get("integration_contract") or {},
        "depends_on": _coerce_id_list(task.get("depends_on")),
        "dependencies": _coerce_id_list(task.get("dependencies")),
        "authority": task.get("authority") or {},
        "execution": task.get("execution") or {},
        "completion": task.get("completion") or {},
        "closeout_assurance": task.get("closeout_assurance") or {},
        "propagation": task.get("propagation") or {},
        "lineage": task.get("lineage") or {},
        "provenance": {
            "legacy_task_id": task.get("id"),
            "evidence_refs": list(task.get("evidence_refs") or []),
        },
        "legacy_snapshot": dict(task),
        "rank_history": list(task.get("rank_history") or []),
        "notes": list(task.get("notes") or []),
        "event_history": [],
    }
    if task.get("owner"):
        item["owner"] = task.get("owner")
    if task.get("sign_off_id"):
        item["sign_off_id"] = task.get("sign_off_id")
    if task.get("tags"):
        item["tags"] = list(task.get("tags") or [])
    return item


def _work_item_created_by(work_item: Mapping[str, Any]) -> str | None:
    created_by = str(work_item.get("created_by") or "").strip()
    if created_by:
        return created_by
    event_history = work_item.get("event_history") if isinstance(work_item.get("event_history"), list) else []
    for row in event_history:
        if not isinstance(row, Mapping):
            continue
        if str(row.get("event_type") or "") not in {"work_item.captured", "work_item.legacy_bootstrapped"}:
            continue
        created_by = str(row.get("created_by") or "").strip()
        if created_by:
            return created_by
    for row in event_history:
        if not isinstance(row, Mapping):
            continue
        created_by = str(row.get("created_by") or "").strip()
        if created_by:
            return created_by
    return None


def _build_task_projection(work_item: Mapping[str, Any]) -> Dict[str, Any]:
    completeness = _projection_completeness(work_item)
    task = {
        "id": work_item.get("id"),
        "slug": work_item.get("slug"),
        "title": work_item.get("title"),
        "statement": work_item.get("statement"),
        "problem": work_item.get("problem"),
        "impact": work_item.get("impact"),
        "acceptance": work_item.get("acceptance"),
        "evidence": list(work_item.get("evidence") or []),
        "status": work_item.get("status") or work_item.get("state"),
        "state": work_item.get("state"),
        "work_item_type": work_item.get("work_item_type"),
        "candidate_work_item_type": work_item.get("candidate_work_item_type"),
        "rank": work_item.get("rank"),
        "confidence": work_item.get("confidence"),
        "rank_history": list(work_item.get("rank_history") or []),
        "compression_passport": work_item.get("compression_passport") or {},
        "created_at": work_item.get("created_at"),
        "created_by": _work_item_created_by(work_item),
        "updated_at": work_item.get("updated_at"),
        "author": work_item.get("author"),
        "evidence_refs": list(
            (work_item.get("provenance") or {}).get("evidence_refs") or work_item.get("evidence_refs") or []
        ),
        "depends_on": _coerce_id_list(work_item.get("depends_on")),
        "dependencies": _coerce_id_list(work_item.get("dependencies")),
        "dependency_resolutions": work_item.get("dependency_resolutions") or {},
        "owner": work_item.get("owner"),
        "tags": list(work_item.get("tags") or []),
        "notes": list(work_item.get("notes") or []),
        "completed_at": work_item.get("completed_at"),
        "sign_off_id": work_item.get("sign_off_id"),
        "satisfaction_contract": work_item.get("satisfaction_contract") or {},
        "integration_contract": work_item.get("integration_contract") or {},
        "authority": work_item.get("authority") or {},
        "execution": work_item.get("execution") or {},
        "execution_receipts": list(work_item.get("execution_receipts") or []),
        "latest_execution_receipt": work_item.get("latest_execution_receipt"),
        "evidence_attachments": list(work_item.get("evidence_attachments") or []),
        "latest_evidence_attachment": work_item.get("latest_evidence_attachment"),
        "work_ledger_refs": list(work_item.get("work_ledger_refs") or []),
        "commit_refs": list(work_item.get("commit_refs") or []),
        "receipt_refs": list(work_item.get("receipt_refs") or []),
        "transaction_state": work_item.get("transaction_state"),
        "completion": work_item.get("completion") or {},
        "closeout_assurance": work_item.get("closeout_assurance") or {},
        "propagation": work_item.get("propagation") or {},
        "lineage": work_item.get("lineage") or {},
        "provenance": work_item.get("provenance") or {},
        "legacy_snapshot": work_item.get("legacy_snapshot"),
        "source_event_ids": list(work_item.get("source_event_ids") or []),
        "event_history": list(work_item.get("event_history") or []),
        "source_event_types": [
            str(row.get("event_type") or "")
            for row in (work_item.get("event_history") or [])
            if isinstance(row, Mapping)
        ],
        "projection_completeness": completeness,
    }
    return {key: value for key, value in task.items() if value is not None}


def _nonempty_mapping(value: Any) -> bool:
    return isinstance(value, Mapping) and bool(value)


def _satisfaction_contract_from_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    contract = payload.get("satisfaction_contract")
    if isinstance(contract, Mapping):
        return dict(contract)
    legacy = _legacy_contracts_satisfaction_contract(payload)
    if legacy:
        return legacy
    served_outcome = str(payload.get("served_outcome") or "").strip()
    normalized: Dict[str, Any] = {}
    if served_outcome:
        normalized["served_outcome"] = served_outcome
    for key in (
        "non_satisfaction",
        "satisfaction_refs",
        "principle_refs",
        "axiom_refs",
        "imagined_state_refs",
        "raw_seed_refs",
        "operator_voice_refs",
        "satisfaction_evidence",
    ):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            normalized[key] = value
    return normalized


def _legacy_contracts_satisfaction_contract(payload: Mapping[str, Any]) -> Dict[str, Any]:
    contracts = payload.get("contracts")
    if not isinstance(contracts, Mapping):
        return {}
    normalized: Dict[str, Any] = {}
    for key in (
        "served_outcome",
        "definition_of_done",
        "non_satisfaction",
        "satisfaction_refs",
        "principle_refs",
        "axiom_refs",
        "imagined_state_refs",
        "raw_seed_refs",
        "operator_voice_refs",
        "satisfaction_evidence",
    ):
        value = contracts.get(key)
        if value not in (None, "", [], {}):
            normalized[key] = value
    return normalized


def _legacy_contracts_integration_contract(payload: Mapping[str, Any]) -> Dict[str, Any]:
    contracts = payload.get("contracts")
    if not isinstance(contracts, Mapping):
        return {}
    return _integration_contract_from_mapping(contracts, include_dependency_fields=True)


def _integration_contract_from_mapping(
    payload: Mapping[str, Any],
    *,
    include_dependency_fields: bool = False,
) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    raw_candidate_surfaces = payload.get("candidate_surfaces")
    candidate_surfaces = (
        list(raw_candidate_surfaces)
        if isinstance(raw_candidate_surfaces, list)
        else ([raw_candidate_surfaces] if raw_candidate_surfaces not in (None, "", [], {}) else [])
    )
    raw_integration_paths = payload.get("integration_paths")
    integration_paths = (
        list(raw_integration_paths)
        if isinstance(raw_integration_paths, list)
        else ([raw_integration_paths] if raw_integration_paths not in (None, "", [], {}) else [])
    )
    for value in integration_paths:
        if value not in candidate_surfaces:
            candidate_surfaces.append(value)
    if candidate_surfaces:
        normalized["candidate_surfaces"] = candidate_surfaces
    for key in (
        "exact_surfaces_discovered",
        "acceptance_checks",
        "proof_signal",
        "validation_commands",
        "owner_surfaces",
        "blockers",
    ):
        value = payload.get(key)
        if value not in (None, "", [], {}):
            normalized[key] = value
    if include_dependency_fields or normalized:
        for key in ("depends_on", "dependencies"):
            value = payload.get(key)
            if value not in (None, "", [], {}):
                normalized[key] = value
    return normalized


def _integration_contract_from_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    contract = payload.get("integration_contract")
    if isinstance(contract, Mapping):
        return dict(contract)
    top_level = _integration_contract_from_mapping(payload)
    if top_level:
        return top_level
    return _legacy_contracts_integration_contract(payload)


def _closeout_assurance_from_payload(payload: Mapping[str, Any]) -> Dict[str, Any]:
    candidates: list[Any] = [payload.get("closeout_assurance")]
    for key in ("work_item", "signoff", "propagation", "execution_receipt", "receipt"):
        nested = payload.get(key)
        if isinstance(nested, Mapping):
            candidates.append(nested.get("closeout_assurance"))
    for candidate in candidates:
        if isinstance(candidate, Mapping) and candidate:
            return _normalize_closeout_assurance(candidate)
    return {}


def _json_contains(value: Any, needle: str) -> bool:
    return needle in json.dumps(value or {}, ensure_ascii=False).lower()


def _integration_exact_surfaces_grounded(contract: Any) -> bool:
    if not isinstance(contract, Mapping):
        return False
    exact = contract.get("exact_surfaces_discovered")
    return isinstance(exact, list) and bool(exact)


def _surface_durability_summary(contract: Any) -> Dict[str, Any]:
    exact = contract.get("exact_surfaces_discovered") if isinstance(contract, Mapping) else None
    entries = [entry for entry in exact if isinstance(entry, Mapping)] if isinstance(exact, list) else []
    classifications = [classify_surface_entry(entry) for entry in entries]
    durable_count = sum(1 for row in classifications if row.get("durable_proof") is True)
    ephemeral_count = sum(1 for row in classifications if row.get("ephemeral_local") is True)
    return {
        "exact_surface_count": len(entries),
        "durable_exact_surface_count": durable_count,
        "ephemeral_exact_surface_count": ephemeral_count,
        "durable_exact_surfaces_grounded": durable_count > 0,
        "non_durable_exact_surface_count": max(0, len(entries) - durable_count),
    }


def _requires_signoff(item: Mapping[str, Any]) -> bool:
    if item.get("sign_off_id") or _has_terminal_execution_receipt(item):
        return False
    state = str(item.get("state") or item.get("status") or "")
    if state in {"review", "signoff", "done"}:
        return True
    completion = item.get("completion")
    if isinstance(completion, Mapping) and completion.get("signoff_required") is True:
        return True
    return False


def _nonempty_text(value: Any) -> bool:
    return bool(str(value or "").strip())


def _nonempty_list(value: Any) -> bool:
    return isinstance(value, list) and any(item not in (None, "", [], {}) for item in value)


_BLOCKED_PRIMARY_PRIVATE_KEYS = {
    "body",
    "clipboard_text",
    "debug",
    "debug_payload",
    "full_body",
    "private",
    "private_payload",
    "prompt",
    "prompt_text",
    "raw_cli_input",
    "raw_payload",
}
_BLOCKED_PRIMARY_CONTINUATION_FIELDS = (
    "schema",
    "status",
    "required",
    "standard_ref",
)
_BLOCKED_PRIMARY_RECEIPT_FIELDS = (
    "primary_target",
    "blocker_classification",
    "claim_or_collision_evidence",
    "selected_legal_continuation",
    "why_highest_yield_legal_move",
    "reentry_condition",
    "standard_ref",
    "receipt_id",
    "residual_id",
    "evidence_refs",
    "created_at",
    "source",
)
_BLOCKED_PRIMARY_REQUIREMENT_FIELDS = (
    "status",
    "failure_kind",
    "standard_ref",
    "primary_target",
    "blocker_classification",
    "valid_blocker_classifications",
    "valid_selected_legal_continuations",
    "required_receipt_fields",
)
_BLOCKED_PRIMARY_VALIDATION_FIELDS = (
    "schema",
    "status",
    "receipt_complete",
    "failure_kind",
    "missing_fields",
    "invalid_fields",
    "required_receipt_fields",
    "valid_selected_legal_continuations",
    "standard_ref",
)


def _safe_blocked_primary_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        cleaned: Dict[str, Any] = {}
        for key, raw in value.items():
            token = str(key or "").strip()
            lowered = token.lower()
            if not token or lowered.startswith("_") or lowered in _BLOCKED_PRIMARY_PRIVATE_KEYS:
                continue
            cleaned[token] = _safe_blocked_primary_value(raw)
        return cleaned
    if isinstance(value, list):
        return [_safe_blocked_primary_value(item) for item in value if item not in (None, "", [], {})]
    if isinstance(value, tuple):
        return [_safe_blocked_primary_value(item) for item in value if item not in (None, "", [], {})]
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _copy_blocked_primary_fields(source: Any, fields: Sequence[str]) -> Dict[str, Any]:
    if not isinstance(source, Mapping):
        return {}
    copied: Dict[str, Any] = {}
    for field in fields:
        if field not in source:
            continue
        value = source.get(field)
        if value in (None, "", [], {}):
            continue
        copied[field] = _safe_blocked_primary_value(value)
    return copied


def _sanitize_blocked_primary_continuation(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        return {}

    receipt_source = value.get("receipt") if isinstance(value.get("receipt"), Mapping) else value
    receipt = _copy_blocked_primary_fields(receipt_source, _BLOCKED_PRIMARY_RECEIPT_FIELDS)
    validation = _copy_blocked_primary_fields(value.get("validation"), _BLOCKED_PRIMARY_VALIDATION_FIELDS)
    requirement = _copy_blocked_primary_fields(value.get("requirement"), _BLOCKED_PRIMARY_REQUIREMENT_FIELDS)
    normalized = _copy_blocked_primary_fields(value, _BLOCKED_PRIMARY_CONTINUATION_FIELDS)
    if receipt:
        normalized["receipt"] = receipt
    if validation:
        normalized["validation"] = validation
    if requirement:
        normalized["requirement"] = requirement
    for field in (
        "primary_target",
        "blocker_classification",
        "selected_legal_continuation",
        "why_highest_yield_legal_move",
        "reentry_condition",
        "residual_id",
    ):
        if field in receipt and field not in normalized:
            normalized[field] = receipt[field]
    return normalized


def _normalize_closeout_assurance(value: Mapping[str, Any]) -> Dict[str, Any]:
    normalized = dict(value)
    continuation = normalized.get("blocked_primary_continuation")
    if not isinstance(continuation, Mapping):
        continuation = normalized.get("blocked_primary_continuation_receipt")
    sanitized = _sanitize_blocked_primary_continuation(continuation)
    normalized.pop("blocked_primary_continuation_receipt", None)
    if sanitized:
        normalized["blocked_primary_continuation"] = sanitized
    return normalized


def _blocked_primary_continuation_summary(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    continuation = value.get("blocked_primary_continuation")
    if not isinstance(continuation, Mapping) or not continuation:
        return {}
    receipt = continuation.get("receipt") if isinstance(continuation.get("receipt"), Mapping) else {}
    validation = continuation.get("validation") if isinstance(continuation.get("validation"), Mapping) else {}
    status = str(continuation.get("status") or validation.get("status") or "").strip()
    required = bool(continuation.get("required"))
    receipt_complete = validation.get("receipt_complete")
    complete = bool(receipt_complete is True or status == "complete" or (not required and status == "not_required"))
    selected = str(
        continuation.get("selected_legal_continuation")
        or receipt.get("selected_legal_continuation")
        or ""
    ).strip()
    reentry = str(continuation.get("reentry_condition") or receipt.get("reentry_condition") or "").strip()
    summary: Dict[str, Any] = {
        "has_blocked_primary_continuation": True,
        "blocked_primary_continuation_complete": complete,
    }
    if status:
        summary["blocked_primary_continuation_status"] = status
    validation_status = str(validation.get("status") or "").strip()
    if validation_status:
        summary["blocked_primary_validation_status"] = validation_status
    if selected:
        summary["blocked_primary_selected_legal_continuation"] = selected
    if reentry:
        summary["blocked_primary_reentry_condition"] = reentry
    standard_ref = str(
        continuation.get("standard_ref") or validation.get("standard_ref") or receipt.get("standard_ref") or ""
    ).strip()
    if standard_ref:
        summary["blocked_primary_standard_ref"] = standard_ref
    return summary


def _closeout_assurance_summary(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping) or not value:
        return {
            "has_closeout_assurance": False,
            "closeout_assurance_complete": False,
        }
    strength = str(value.get("corrective_action_strength") or "").strip()
    valid_strengths = {"weak", "medium", "strong", "very_strong"}
    owner_surface = (
        value.get("owner_surface")
        or value.get("owner_surface_ref")
        or value.get("owner_surface_absorbing_lesson")
        or value.get("propagation_target")
    )
    owner_surfaces_changed = value.get("owner_surfaces_changed")
    has_owner_surface = _nonempty_text(owner_surface) or _nonempty_list(owner_surfaces_changed)
    evidence_refs = value.get("evidence_refs")
    counterexample_checks = value.get("counterexample_checks")
    residuals = value.get("residuals")
    blocked_primary_summary = _blocked_primary_continuation_summary(value)
    blocked_primary_complete = (
        not blocked_primary_summary.get("has_blocked_primary_continuation")
        or blocked_primary_summary.get("blocked_primary_continuation_complete") is True
    )
    summary: Dict[str, Any] = {
        "has_closeout_assurance": True,
        "closeout_assurance_complete": (
            _nonempty_text(value.get("claim"))
            and _nonempty_list(evidence_refs)
            and strength in valid_strengths
            and _nonempty_list(counterexample_checks)
            and "residuals" in value
            and has_owner_surface
            and blocked_primary_complete
        ),
        "closeout_assurance_evidence_count": len(evidence_refs) if isinstance(evidence_refs, list) else 0,
        "counterexample_check_count": len(counterexample_checks) if isinstance(counterexample_checks, list) else 0,
        "residual_count": len(residuals) if isinstance(residuals, list) else 0,
        "corrective_action_strength_valid": strength in valid_strengths,
        **blocked_primary_summary,
    }
    if strength:
        summary["corrective_action_strength"] = strength
    if has_owner_surface:
        summary["closeout_owner_surface_present"] = True
    return summary


_CLOSEOUT_ASSURANCE_CLOSEOUT_STATES = {"done", "signoff", "propagated", "retired"}
_CLOSEOUT_ASSURANCE_CLOSEOUT_STATUS_TERMS = {
    "closed",
    "complete",
    "completed",
    "done",
    "landed",
    "no op",
    "noop",
    "passed",
    "propagated",
    "resolved",
    "retired",
    "satisfied",
    "signoff",
    "signed off",
    "success",
}
_CLOSEOUT_ASSURANCE_TRIGGER_TAGS = {
    "self_error",
    "operator_correction",
    "operator_corrected",
    "closeout_residual",
    "signoff_followup",
    "false_completion_or_proof",
}
_CLOSEOUT_ASSURANCE_TRIGGER_TYPES = {
    "self_error",
    "self error",
    "closeout_residual",
    "closeout residual",
    "signoff_followup",
    "signoff followup",
    "signoff follow-up",
}
_CLOSEOUT_ASSURANCE_TRIGGER_NEEDLES = (
    "ambition collapse",
    "ambition-collapse",
    "closeout underreach",
    "false completion",
    "false-completion",
    "false green",
    "false-green",
    "failure class",
    "operator corrected",
    "operator correction",
    "operator-corrected",
    "operator-correction",
    "overclaimed",
    "proof substituted",
    "reusable incident",
    "self error",
    "self-error",
    "settlement only underreach",
    "settlement-only",
)


def _normalized_closeout_text(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ").replace("-", " ")


def _closeout_status_matches(value: Any) -> bool:
    text = _normalized_closeout_text(value)
    if not text:
        return False
    return text in _CLOSEOUT_ASSURANCE_CLOSEOUT_STATUS_TERMS


def _iter_text_items(value: Any) -> Iterator[str]:
    if isinstance(value, (list, tuple, set)):
        values = value
    else:
        values = [value]
    for item in values:
        text = str(item or "").strip()
        if text:
            yield text


def _transition_target_state(payload: Mapping[str, Any]) -> str:
    for key in ("state", "to_state"):
        text = str(payload.get(key) or "").strip()
        if text:
            return text
    return ""


def _closeout_event_attempts_claim(event_type: str, payload: Mapping[str, Any]) -> bool:
    if event_type == "work_item.signoff_recorded":
        return True
    if event_type == "work_item.state_transitioned":
        state = _normalized_closeout_text(_transition_target_state(payload))
        status = _normalized_closeout_text(payload.get("status"))
        return state in _CLOSEOUT_ASSURANCE_CLOSEOUT_STATES or _closeout_status_matches(status)
    if event_type == "work_item.propagation_recorded":
        propagation = payload.get("propagation") if isinstance(payload.get("propagation"), Mapping) else {}
        values: list[Any] = [
            payload.get("state"),
            payload.get("status"),
            payload.get("result"),
            payload.get("closeout_state"),
            propagation.get("state"),
            propagation.get("status"),
            propagation.get("result"),
            propagation.get("closeout_state"),
            propagation.get("decision_state"),
            propagation.get("outcome"),
            propagation.get("resolution"),
        ]
        return any(_closeout_status_matches(value) for value in values)
    if event_type == "work_item.execution_receipt_recorded":
        receipt = payload.get("execution_receipt") or payload.get("receipt") or {}
        values: list[Any] = [
            payload.get("state"),
            payload.get("status"),
            payload.get("result"),
            payload.get("closeout_state"),
        ]
        if isinstance(receipt, Mapping):
            values.extend(
                [
                    receipt.get("state"),
                    receipt.get("status"),
                    receipt.get("result"),
                    receipt.get("closeout_state"),
                    receipt.get("decision_state"),
                    receipt.get("outcome"),
                    receipt.get("resolution"),
                ]
            )
        return any(_closeout_status_matches(value) for value in values)
    return False


def _closeout_assurance_required_reason(
    item: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> str | None:
    tags = {
        str(tag or "").strip().lower().replace("-", "_")
        for tag in (
            list(_iter_text_items(item.get("tags")))
            + list(_iter_text_items(payload.get("tags")))
        )
        if str(tag or "").strip()
    }
    for tag in sorted(tags):
        if tag in _CLOSEOUT_ASSURANCE_TRIGGER_TAGS:
            return f"tag {tag!r} is in closeout_assurance_contract.applies_when"

    for key in ("candidate_work_item_type", "work_item_type", "triage_status", "recommended_action"):
        text = _normalized_closeout_text(payload.get(key) or item.get(key))
        if text in _CLOSEOUT_ASSURANCE_TRIGGER_TYPES:
            return f"{key} {text!r} is in closeout_assurance_contract.applies_when"

    note_text = " ".join(
        str(note.get("note") or note.get("body") or "")
        for note in item.get("notes") or []
        if isinstance(note, Mapping)
    )
    blob = " ".join(
        str(value or "")
        for value in (
            item.get("title"),
            item.get("statement"),
            item.get("problem"),
            item.get("impact"),
            item.get("acceptance"),
            payload.get("title"),
            payload.get("statement"),
            payload.get("summary"),
            note_text,
        )
    ).lower()
    for needle in _CLOSEOUT_ASSURANCE_TRIGGER_NEEDLES:
        if needle in blob:
            return f"text marker {needle!r} is in closeout_assurance_contract.applies_when"
    return None


def _missing_closeout_assurance_fields(value: Any) -> List[str]:
    if not isinstance(value, Mapping) or not value:
        return [
            "claim",
            "evidence_refs",
            "corrective_action_strength",
            "counterexample_checks",
            "owner_surface/owner_surfaces_changed",
            "residuals",
        ]
    missing: List[str] = []
    strength = str(value.get("corrective_action_strength") or "").strip()
    if not _nonempty_text(value.get("claim")):
        missing.append("claim")
    if not _nonempty_list(value.get("evidence_refs")):
        missing.append("evidence_refs")
    if strength not in {"weak", "medium", "strong", "very_strong"}:
        missing.append("corrective_action_strength")
    if not _nonempty_list(value.get("counterexample_checks")):
        missing.append("counterexample_checks")
    if "residuals" not in value:
        missing.append("residuals")
    if not _closeout_assurance_summary(value).get("closeout_owner_surface_present"):
        missing.append("owner_surface/owner_surfaces_changed")
    blocked_primary_summary = _blocked_primary_continuation_summary(value)
    if (
        blocked_primary_summary.get("has_blocked_primary_continuation")
        and blocked_primary_summary.get("blocked_primary_continuation_complete") is not True
    ):
        missing.append("blocked_primary_continuation.complete")
    return missing


def _closeout_assurance_effective_value(
    item: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> Dict[str, Any]:
    submitted = _closeout_assurance_from_payload(payload)
    if submitted:
        return submitted
    existing = item.get("closeout_assurance")
    return dict(existing) if isinstance(existing, Mapping) else {}


def _enforce_closeout_assurance_for_append(
    events: Sequence[Mapping[str, Any]],
    event: Mapping[str, Any],
) -> None:
    event_type = str(event.get("event_type") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
    if not _closeout_event_attempts_claim(event_type, payload):
        return

    subject_id = str(event.get("subject_id") or "").strip()
    subject_events = [
        row
        for row in events
        if str(row.get("subject_id") or "").strip() == subject_id
    ]
    projection = build_projection(subject_events, generated_at="closeout_assurance_guard")
    ledger = projection.get("ledger") if isinstance(projection.get("ledger"), Mapping) else {}
    work_items = ledger.get("work_items") if isinstance(ledger.get("work_items"), list) else []
    item = next(
        (row for row in work_items if isinstance(row, Mapping) and row.get("id") == subject_id),
        {"id": subject_id},
    )
    reason = _closeout_assurance_required_reason(item, payload)
    if not reason:
        return

    closeout_assurance = _closeout_assurance_effective_value(item, payload)
    if _closeout_assurance_summary(closeout_assurance).get("closeout_assurance_complete") is True:
        return

    missing = _missing_closeout_assurance_fields(closeout_assurance)
    missing_text = ", ".join(missing) if missing else "unknown completeness field"
    raise TaskLedgerError(
        "closeout_assurance required for this WorkItem because "
        f"{reason}. Provide closeout_assurance with claim, evidence_refs, "
        "corrective_action_strength, counterexample_checks, "
        "owner_surface/owner_surfaces_changed, and residuals. "
        f"Missing or incomplete: {missing_text}."
    )


def _projection_completeness(item: Mapping[str, Any]) -> Dict[str, Any]:
    satisfaction = item.get("satisfaction_contract")
    integration = item.get("integration_contract")
    completion = item.get("completion")
    closeout_assurance = item.get("closeout_assurance")
    authority = item.get("authority")
    provenance = item.get("provenance")
    work_item_type = str(item.get("work_item_type") or "")
    has_prompt_ref = _json_contains(provenance, "prompt") or _json_contains(item.get("refs"), "prompt")
    surface_durability = _surface_durability_summary(integration)
    closeout_summary = _closeout_assurance_summary(closeout_assurance)
    return {
        "has_satisfaction_contract": _nonempty_mapping(satisfaction),
        "has_integration_contract": _nonempty_mapping(integration),
        "exact_surfaces_grounded": _integration_exact_surfaces_grounded(integration),
        **surface_durability,
        **closeout_summary,
        "has_authority": _nonempty_mapping(authority),
        "has_completion_contract": _nonempty_mapping(completion),
        "has_work_ledger_claim_ref": bool(item.get("work_ledger_refs")) or _json_contains(item.get("execution"), "work_ledger"),
        "has_prompt_trace_ref": has_prompt_ref,
        "needs_signoff": _requires_signoff(item),
        "legacy_snapshot_present": _nonempty_mapping(item.get("legacy_snapshot")),
        "unmodeled_fields_present": _nonempty_mapping(item.get("legacy_snapshot")),
        "capture_low_ceremony": work_item_type == "capture",
    }


def _ensure_item(items: Dict[str, Dict[str, Any]], subject_id: str, event: Mapping[str, Any]) -> Dict[str, Any]:
    item = items.setdefault(
        subject_id,
        {
            "id": subject_id,
            "kind": "work_item",
            "work_item_type": "capture",
            "title": subject_id,
            "state": "captured",
            "status": "captured",
            "created_at": event.get("created_at"),
            "updated_at": event.get("created_at"),
            "event_history": [],
            "source_event_ids": [],
            "rank_history": [],
            "notes": [],
        },
    )
    return item


def _coerce_id_list(value: Any) -> List[str]:
    if value in (None, "", [], ()):
        return []
    raw_values = value if isinstance(value, list) else [value]
    ids: List[str] = []
    for raw in raw_values:
        if isinstance(raw, Mapping):
            raw = raw.get("id") or raw.get("work_item_id") or raw.get("ref")
        text = str(raw or "").strip()
        if text and text not in ids:
            ids.append(text)
    return ids


def _merge_dependency_fields(item: Dict[str, Any], payload: Mapping[str, Any]) -> None:
    contracts = payload.get("contracts") if isinstance(payload.get("contracts"), Mapping) else {}
    if "depends_on" in payload:
        item["depends_on"] = _coerce_id_list(payload.get("depends_on"))
    elif "depends_on" in contracts:
        item["depends_on"] = _coerce_id_list(contracts.get("depends_on"))
    if "dependencies" in payload:
        item["dependencies"] = _coerce_id_list(payload.get("dependencies"))
    elif "dependencies" in contracts:
        item["dependencies"] = _coerce_id_list(contracts.get("dependencies"))
    if isinstance(payload.get("dependency_resolutions"), Mapping):
        existing = dict(item.get("dependency_resolutions") or {})
        existing.update(dict(payload["dependency_resolutions"]))
        item["dependency_resolutions"] = existing


def _merge_tag_fields(item: Dict[str, Any], payload: Mapping[str, Any]) -> None:
    if "tags" not in payload:
        return
    item["tags"] = _coerce_id_list(payload.get("tags"))


def _capture_would_downgrade_existing_item(item: Mapping[str, Any]) -> bool:
    state = str(item.get("state") or item.get("status") or "").strip()
    work_item_type = str(item.get("work_item_type") or "").strip()
    if item.get("rank") is not None:
        return True
    if work_item_type and work_item_type != "capture":
        return True
    return state in {"ready", "shaping", "active", "claimed", "blocked", "signoff", "done", "propagated"}


def _capture_overlay_from_event(event: Mapping[str, Any], payload: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "created_at": event.get("created_at"),
        "created_by": event.get("created_by"),
        "title": payload.get("title"),
        "statement": payload.get("statement") or payload.get("body"),
        "problem": payload.get("problem"),
        "impact": payload.get("impact"),
        "acceptance": payload.get("acceptance"),
        "evidence": payload.get("evidence"),
        "source": event.get("source") if isinstance(event.get("source"), Mapping) else {},
        "refs": event.get("refs") if isinstance(event.get("refs"), Mapping) else {},
    }


def _append_history(item: Dict[str, Any], event: Mapping[str, Any]) -> None:
    item.setdefault("event_history", []).append(
        {
            "event_id": event.get("event_id"),
            "event_type": event.get("event_type"),
            "created_at": event.get("created_at"),
            "created_by": event.get("created_by"),
        }
    )
    item.setdefault("source_event_ids", []).append(event.get("event_id"))
    item["updated_at"] = event.get("created_at")


def _receipt_transaction_id(receipt: Mapping[str, Any]) -> str:
    return str(receipt.get("transaction_id") or receipt.get("id") or "").strip()


def _receipt_commit_hash(receipt: Mapping[str, Any]) -> str:
    return str(receipt.get("commit_hash") or "").strip()


VALIDATED_UNCOMMITTED_CLOSEOUT_STATES = {
    "live_state_archived_validated",
    "validated_uncommitted_git_metadata_blocked",
}
DEFAULT_VALIDATED_UNCOMMITTED_CLOSEOUT_STATE = (
    "validated_uncommitted_git_metadata_blocked"
)


def _receipt_closeout_state(receipt: Mapping[str, Any]) -> str:
    return str(receipt.get("closeout_state") or receipt.get("status") or "").strip()


def _receipt_validation_refs(receipt: Mapping[str, Any]) -> list[str]:
    refs = receipt.get("validation_refs")
    if isinstance(refs, str):
        refs = [refs]
    return [str(ref or "").strip() for ref in list(refs or []) if str(ref or "").strip()]


def _receipt_no_commit_reason(receipt: Mapping[str, Any]) -> str:
    return str(receipt.get("no_commit_reason") or "").strip()


def _receipt_allows_missing_commit(receipt: Mapping[str, Any]) -> bool:
    return _receipt_closeout_state(receipt) in VALIDATED_UNCOMMITTED_CLOSEOUT_STATES


def _receipt_missing_fields(
    *,
    subject_id: str,
    receipt: Mapping[str, Any],
) -> list[str]:
    transaction_id = _receipt_transaction_id(receipt)
    commit_hash = _receipt_commit_hash(receipt)
    missing = [
        field
        for field, value in (
            ("subject_id", subject_id),
            ("transaction_id", transaction_id),
        )
        if not value
    ]
    if commit_hash:
        return missing
    if not _receipt_allows_missing_commit(receipt):
        missing.append("commit_hash")
        return missing
    if not _receipt_validation_refs(receipt):
        missing.append("validation_refs")
    if not _receipt_no_commit_reason(receipt):
        missing.append("no_commit_reason")
    return missing


def _receipt_missing_fields_repair_hint(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Return focused guidance for commitless receipts that almost used the fallback lane."""
    if _receipt_commit_hash(receipt):
        return {}
    closeout_state = _receipt_closeout_state(receipt)
    commitless_signals = [
        closeout_state,
        _receipt_no_commit_reason(receipt),
        _receipt_validation_refs(receipt),
        receipt.get("commit_blocker_refs"),
    ]
    if not any(commitless_signals):
        return {}
    allowed_states = sorted(VALIDATED_UNCOMMITTED_CLOSEOUT_STATES)
    suggested_state = (
        DEFAULT_VALIDATED_UNCOMMITTED_CLOSEOUT_STATE
        if DEFAULT_VALIDATED_UNCOMMITTED_CLOSEOUT_STATE in VALIDATED_UNCOMMITTED_CLOSEOUT_STATES
        else (allowed_states[0] if allowed_states else None)
    )
    return {
        "receipt_landing_mode": "git_commit_required",
        "diagnostic_hint": (
            "commit_hash is required unless closeout_state is an accepted "
            "validated-uncommitted fallback state."
        ),
        "accepted_validated_uncommitted_closeout_states": allowed_states,
        "validated_uncommitted_required_fields": [
            "transaction_id",
            "closeout_state",
            "validation_refs",
            "no_commit_reason",
        ],
        "suggested_closeout_state": suggested_state,
    }


def _receipt_identity_token(receipt: Mapping[str, Any]) -> str:
    commit_hash = _receipt_commit_hash(receipt)
    if commit_hash:
        return f"commit:{commit_hash}"
    closeout_state = _receipt_closeout_state(receipt)
    if _receipt_allows_missing_commit(receipt) and closeout_state:
        return f"validated_uncommitted:{closeout_state}"
    return ""


def execution_receipt_idempotency_key(
    *,
    subject_id: str,
    transaction_id: str,
    commit_hash: str,
    closeout_state: str | None = None,
    event_type: str = "work_item.execution_receipt_recorded",
) -> str:
    identity_token = str(commit_hash or "").strip()
    if not identity_token:
        identity_token = f"validated_uncommitted:{str(closeout_state or '').strip()}"
    return ":".join(
        [
            str(subject_id or "").strip(),
            str(event_type or "").strip(),
            str(transaction_id or "").strip(),
            identity_token,
        ]
    )


def mint_intake_request_id(*, idempotency_key: str | None = None, now: str | None = None) -> str:
    stamp = (now or utc_now()).replace("+00:00", "Z").replace("-", "").replace(":", "")
    digest = hashlib.sha256(str(idempotency_key or uuid.uuid4().hex).encode("utf-8")).hexdigest()[:12]
    return f"tlir_{stamp}_{digest}"


def _intake_status_rel(status: str) -> Path:
    status = str(status or "").strip()
    if status == "pending":
        return TASK_LEDGER_INTAKE_PENDING_REL
    if status == "applied":
        return TASK_LEDGER_INTAKE_APPLIED_REL
    if status == "blocked":
        return TASK_LEDGER_INTAKE_BLOCKED_REL
    raise TaskLedgerError(f"unknown Task Ledger intake status {status!r}")


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    atomic_write_json(path, payload)


def _safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _read_intake_request_at(repo_root: Path, *, status: str, request_id: str) -> dict[str, Any] | None:
    token = str(request_id or "").strip()
    if not token or "/" in token or "\\" in token:
        return None
    path = repo_root / _intake_status_rel(status) / f"{token}.json"
    request = _safe_read_json(path)
    if not request:
        return None
    request["_intake_status"] = status
    request["_intake_path"] = str(path.relative_to(repo_root))
    return request


def _task_ledger_intake_requests_for_ids(
    repo_root: Path,
    *,
    statuses: Sequence[str],
    request_ids: Sequence[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for request_id in sorted(_normalized_filter_values(request_ids)):
        for status in statuses:
            request = _read_intake_request_at(repo_root, status=status, request_id=request_id)
            if not request:
                continue
            key = (status, str(request.get("request_id") or "").strip())
            if key in seen:
                continue
            seen.add(key)
            rows.append(request)
    return rows


def task_ledger_intake_requests(
    repo_root: Path,
    *,
    statuses: Sequence[str] = ("pending", "applied", "blocked"),
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for status in statuses:
        root = repo_root / _intake_status_rel(status)
        if not root.is_dir():
            continue
        for path in sorted(root.glob("*.json")):
            request = _safe_read_json(path)
            if not request:
                continue
            request["_intake_status"] = status
            request["_intake_path"] = str(path.relative_to(repo_root))
            rows.append(request)
    return rows


def _normalized_filter_values(values: Sequence[str] | None) -> set[str]:
    return {str(value or "").strip() for value in values or [] if str(value or "").strip()}


def task_ledger_intake_request_for_key(repo_root: Path, idempotency_key: str) -> dict[str, Any] | None:
    key = str(idempotency_key or "").strip()
    if not key:
        return None
    for request in task_ledger_intake_requests(repo_root):
        if str(request.get("idempotency_key") or "").strip() == key:
            return request
    return None


def task_ledger_intake_status(
    repo_root: Path,
    *,
    request_ids: Sequence[str] | None = None,
    idempotency_keys: Sequence[str] | None = None,
    full: bool = False,
    limit: int = 20,
) -> Dict[str, Any]:
    request_id_filter = _normalized_filter_values(request_ids)
    idempotency_key_filter = _normalized_filter_values(idempotency_keys)
    requests = []
    if request_id_filter:
        source_requests = _task_ledger_intake_requests_for_ids(
            repo_root,
            statuses=("pending", "applied", "blocked"),
            request_ids=sorted(request_id_filter),
        )
        if idempotency_key_filter:
            covered_keys = {
                str(request.get("idempotency_key") or "").strip()
                for request in source_requests
                if str(request.get("idempotency_key") or "").strip()
            }
            missing_keys = idempotency_key_filter - covered_keys
            if missing_keys:
                seen = {
                    (
                        str(request.get("_intake_status") or "").strip(),
                        str(request.get("request_id") or "").strip(),
                    )
                    for request in source_requests
                }
                for request in task_ledger_intake_requests(repo_root):
                    request_key = str(request.get("idempotency_key") or "").strip()
                    if request_key not in missing_keys:
                        continue
                    dedupe_key = (
                        str(request.get("_intake_status") or "").strip(),
                        str(request.get("request_id") or "").strip(),
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    source_requests.append(request)
    else:
        source_requests = task_ledger_intake_requests(repo_root)
    for request in source_requests:
        request_id = str(request.get("request_id") or "").strip()
        idempotency_key = str(request.get("idempotency_key") or "").strip()
        if request_id_filter and request_id not in request_id_filter:
            continue
        if idempotency_key_filter and idempotency_key not in idempotency_key_filter:
            continue
        requests.append(request)
    counts = {status: 0 for status in ("pending", "applied", "blocked")}
    for request in requests:
        status = str(request.get("_intake_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    exact = bool(request_id_filter or idempotency_key_filter)
    payload: Dict[str, Any] = {
        "schema": "task_ledger_intake_status_v0",
        "root": str(TASK_LEDGER_INTAKE_ROOT_REL),
        "counts": counts,
        "scope": {
            "exact": exact,
            "request_ids": sorted(request_id_filter),
            "idempotency_keys": sorted(idempotency_key_filter),
        },
        "output_profile": "full_requests" if (full or exact) else "compact_cards",
    }
    if full or exact:
        payload["requests"] = requests
        return payload

    card_limit = max(0, int(limit))
    cards = [_intake_request_card(request) for request in requests[:card_limit]]
    payload.update(
        {
            "request_cards": cards,
            "request_count": len(requests),
            "request_cards_emitted": len(cards),
            "request_cards_omitted": max(0, len(requests) - len(cards)),
            "requests_omitted": True,
            "full_profile_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py intake-status --full"
            ),
            "omission_receipt": {
                "omitted": ["full intake request bodies"],
                "reason": (
                    "Default intake-status is a coordination counter/card surface; "
                    "full request payloads are available with --full or exact filters."
                ),
                "drilldown": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py intake-status --full"
                ),
            },
        }
    )
    return payload


def _intake_request_card(request: Mapping[str, Any]) -> Dict[str, Any]:
    payload = request.get("payload")
    payload_map = payload if isinstance(payload, Mapping) else {}
    raw_receipt = payload_map.get("execution_receipt")
    receipt = raw_receipt if isinstance(raw_receipt, Mapping) else {}
    return {
        "request_id": request.get("request_id"),
        "kind": request.get("kind"),
        "event_type": request.get("event_type"),
        "subject_id": request.get("subject_id"),
        "state": request.get("state"),
        "intake_status": request.get("_intake_status"),
        "created_at": request.get("created_at"),
        "created_by": request.get("created_by"),
        "transaction_id": receipt.get("transaction_id"),
        "closeout_state": receipt.get("closeout_state"),
        "commit_hash": receipt.get("commit_hash"),
        "request_path": request.get("_intake_path"),
    }


def _intake_request_hash(request: Mapping[str, Any]) -> str:
    public_request = {key: value for key, value in dict(request).items() if not str(key).startswith("_intake_")}
    return "sha256:" + hashlib.sha256(_canonical_json(public_request).encode("utf-8")).hexdigest()


def enqueue_task_ledger_intake_request(
    repo_root: Path,
    request: Mapping[str, Any],
    *,
    replace_pending: bool = False,
) -> Dict[str, Any]:
    kind = str(request.get("kind") or "").strip()
    if kind != "execution_receipt":
        raise TaskLedgerError("Task Ledger intake currently supports kind='execution_receipt'")
    subject_id = str(request.get("subject_id") or "").strip()
    payload = request.get("payload") if isinstance(request.get("payload"), Mapping) else {}
    receipt = payload.get("execution_receipt") if isinstance(payload.get("execution_receipt"), Mapping) else {}
    transaction_id = _receipt_transaction_id(receipt)
    commit_hash = _receipt_commit_hash(receipt)
    event_type = str(request.get("event_type") or "work_item.execution_receipt_recorded").strip()
    missing = _receipt_missing_fields(subject_id=subject_id, receipt=receipt)
    if missing:
        return {
            "ok": False,
            "status": "receipt_blocked_missing_fields",
            "missing_fields": missing,
        }
    key = str(request.get("idempotency_key") or "").strip() or execution_receipt_idempotency_key(
        subject_id=subject_id,
        transaction_id=transaction_id,
        commit_hash=commit_hash,
        closeout_state=_receipt_closeout_state(receipt),
        event_type=event_type,
    )
    existing = task_ledger_intake_request_for_key(repo_root, key)
    if existing:
        status = str(existing.get("_intake_status") or "pending")
        existing_request_id = str(existing.get("request_id") or "").strip()
        requested_request_id = str(request.get("request_id") or "").strip()
        if replace_pending:
            if status != "pending":
                return {
                    "ok": False,
                    "status": f"replace_pending_rejected_{status}",
                    "idempotency_key": key,
                    "request_id": existing.get("request_id"),
                    "request_path": existing.get("_intake_path"),
                    "request": existing,
                }
            if requested_request_id and requested_request_id != existing_request_id:
                return {
                    "ok": False,
                    "status": "replace_pending_request_id_mismatch",
                    "idempotency_key": key,
                    "request_id": existing_request_id,
                    "request_path": existing.get("_intake_path"),
                    "requested_request_id": requested_request_id,
                }
        else:
            return {
                "ok": True,
                "status": f"intake_already_{status}",
                "idempotency_key": key,
                "request_id": existing.get("request_id"),
                "request_path": existing.get("_intake_path"),
                "request": existing,
            }
    else:
        status = ""
        existing_request_id = ""
        requested_request_id = str(request.get("request_id") or "").strip()
    now = str(request.get("created_at") or utc_now())
    request_id = existing_request_id or requested_request_id or mint_intake_request_id(
        idempotency_key=key,
        now=now,
    )
    normalized = {
        "schema": TASK_LEDGER_INTAKE_REQUEST_SCHEMA,
        "request_id": request_id,
        "kind": kind,
        "event_type": event_type,
        "subject_id": subject_id,
        "idempotency_key": key,
        "created_at": now,
        "created_by": request.get("created_by") or "codex",
        "agent_run_id": request.get("agent_run_id"),
        "thread_id": request.get("thread_id"),
        "source": request.get("source") or {"kind": "task_ledger_intake", "refs": []},
        "refs": request.get("refs") if isinstance(request.get("refs"), Mapping) else {},
        "payload": dict(payload),
        "state": "pending",
    }
    if existing and replace_pending:
        normalized["intake_replacement"] = {
            "previous_request_hash": _intake_request_hash(existing),
            "previous_request_id": existing_request_id,
            "previous_request_path": existing.get("_intake_path"),
            "replaced_at": utc_now(),
        }
    normalized = {key_: value for key_, value in normalized.items() if value not in (None, {}, [])}
    path = repo_root / TASK_LEDGER_INTAKE_PENDING_REL / f"{request_id}.json"
    _write_json_atomic(path, normalized)
    return {
        "ok": True,
        "status": "intake_replaced_pending" if existing and replace_pending else "intake_queued",
        "idempotency_key": key,
        "request_id": request_id,
        "request_path": str(path.relative_to(repo_root)),
        "request": normalized,
    }


def _settle_intake_request(
    repo_root: Path,
    request: Mapping[str, Any],
    *,
    status: str,
    result: Mapping[str, Any],
) -> dict[str, Any]:
    request_id = str(request.get("request_id") or "").strip()
    if not request_id:
        raise TaskLedgerError("intake request missing request_id")
    current_path = repo_root / str(request.get("_intake_path") or TASK_LEDGER_INTAKE_PENDING_REL / f"{request_id}.json")
    target_path = repo_root / _intake_status_rel(status) / f"{request_id}.json"
    settled = {
        **{key: value for key, value in dict(request).items() if not str(key).startswith("_intake_")},
        "state": status,
        "settled_at": utc_now(),
        "settle_result": dict(result),
    }
    _write_json_atomic(target_path, settled)
    if current_path.exists() and current_path != target_path:
        current_path.unlink()
    return settled


def drain_task_ledger_intake(
    repo_root: Path,
    *,
    limit: int | None = None,
    created_by: str = "codex",
    rebuild: bool = True,
    request_ids: Sequence[str] = (),
    idempotency_keys: Sequence[str] = (),
) -> Dict[str, Any]:
    wanted_request_ids = {
        str(request_id or "").strip()
        for request_id in request_ids
        if str(request_id or "").strip()
    }
    wanted_idempotency_keys = {
        str(key or "").strip()
        for key in idempotency_keys
        if str(key or "").strip()
    }
    if wanted_request_ids:
        pending = _task_ledger_intake_requests_for_ids(
            repo_root,
            statuses=("pending",),
            request_ids=sorted(wanted_request_ids),
        )
        if wanted_idempotency_keys:
            covered_keys = {
                str(request.get("idempotency_key") or "").strip()
                for request in pending
                if str(request.get("idempotency_key") or "").strip()
            }
            missing_keys = wanted_idempotency_keys - covered_keys
            if missing_keys:
                seen = {
                    (
                        str(request.get("_intake_status") or "").strip(),
                        str(request.get("request_id") or "").strip(),
                    )
                    for request in pending
                }
                for request in task_ledger_intake_requests(repo_root, statuses=("pending",)):
                    request_key = str(request.get("idempotency_key") or "").strip()
                    if request_key not in missing_keys:
                        continue
                    dedupe_key = (
                        str(request.get("_intake_status") or "").strip(),
                        str(request.get("request_id") or "").strip(),
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    pending.append(request)
    else:
        pending = task_ledger_intake_requests(repo_root, statuses=("pending",))
    if wanted_request_ids or wanted_idempotency_keys:
        pending = [
            request
            for request in pending
            if (
                str(request.get("request_id") or "").strip() in wanted_request_ids
                or str(request.get("idempotency_key") or "").strip() in wanted_idempotency_keys
            )
        ]
    if limit is not None:
        pending = pending[: max(0, int(limit))]
    results: list[dict[str, Any]] = []
    appended_count = 0
    appended_event_ids: list[str] = []
    appended_subject_ids: list[str] = []
    for request in pending:
        kind = str(request.get("kind") or "").strip()
        payload = request.get("payload") if isinstance(request.get("payload"), Mapping) else {}
        receipt = payload.get("execution_receipt") if isinstance(payload.get("execution_receipt"), Mapping) else {}
        if kind != "execution_receipt":
            result = {"ok": False, "status": "intake_blocked_unsupported_kind", "kind": kind}
            _settle_intake_request(repo_root, request, status="blocked", result=result)
            results.append({"request_id": request.get("request_id"), "idempotency_key": request.get("idempotency_key"), **result})
            continue
        reconcile = execution_receipt_reconcile_state(
            repo_root,
            subject_id=str(request.get("subject_id") or ""),
            receipt=receipt,
        )
        reconcile_status = str(reconcile.get("status") or "")
        if reconcile_status == "receipt_already_recorded":
            result = {"ok": True, "status": "receipt_already_recorded", "receipt_reconcile": reconcile}
            _settle_intake_request(repo_root, request, status="applied", result=result)
            results.append({"request_id": request.get("request_id"), "idempotency_key": request.get("idempotency_key"), **result})
            continue
        if not reconcile.get("ok", True):
            result = {"ok": False, "status": reconcile_status or "receipt_reconcile_blocked", "receipt_reconcile": reconcile}
            _settle_intake_request(repo_root, request, status="blocked", result=result)
            results.append({"request_id": request.get("request_id"), "idempotency_key": request.get("idempotency_key"), **result})
            continue
        source = dict(request.get("source") if isinstance(request.get("source"), Mapping) else {"kind": "task_ledger_intake", "refs": []})
        source_refs = list(source.get("refs") or [])
        for ref in (request.get("request_id"), request.get("_intake_path")):
            token = str(ref or "").strip()
            if token and token not in source_refs:
                source_refs.append(token)
        source["refs"] = source_refs
        refs = request.get("refs") if isinstance(request.get("refs"), Mapping) else {}
        event = {
            "event_id": request.get("event_id"),
            "event_type": "work_item.execution_receipt_recorded",
            "created_at": utc_now(),
            "created_by": request.get("created_by") or created_by,
            "agent_run_id": request.get("agent_run_id"),
            "thread_id": request.get("thread_id"),
            "subject_id": request.get("subject_id"),
            "source": source,
            "refs": refs,
            "payload": payload,
        }
        event = {key: value for key, value in event.items() if value not in (None, {}, [])}
        append_result = append_event(repo_root, event, preflight_projection=bool(rebuild))
        appended_count += 1 if append_result.get("status") == "appended" else 0
        appended_event = append_result.get("event") if isinstance(append_result.get("event"), Mapping) else {}
        if appended_event.get("event_id"):
            appended_event_ids.append(str(appended_event.get("event_id")))
        if event.get("subject_id"):
            appended_subject_ids.append(str(event.get("subject_id")))
        result = {"ok": True, "status": "receipt_recorded", "append": append_result}
        _settle_intake_request(repo_root, request, status="applied", result=result)
        results.append({"request_id": request.get("request_id"), "idempotency_key": request.get("idempotency_key"), **result})
    projection = rebuild_projections(repo_root) if rebuild and appended_count else None
    processed_request_ids = {
        str(result.get("request_id") or "").strip()
        for result in results
        if str(result.get("request_id") or "").strip()
    }
    processed_idempotency_keys = {
        str(result.get("idempotency_key") or "").strip()
        for result in results
        if str(result.get("idempotency_key") or "").strip()
    }
    return {
        "ok": True,
        "schema": "task_ledger_intake_drain_result_v0",
        "scope": {
            "request_ids": sorted(wanted_request_ids),
            "idempotency_keys": sorted(wanted_idempotency_keys),
            "exact": bool(wanted_request_ids or wanted_idempotency_keys),
            "missing_request_ids": sorted(wanted_request_ids - processed_request_ids),
            "missing_idempotency_keys": sorted(wanted_idempotency_keys - processed_idempotency_keys),
        },
        "processed_count": len(results),
        "appended_count": appended_count,
        "results": results,
        "projection": projection,
        "visibility_receipt": visibility_receipt(
            repo_root,
            subject_ids=appended_subject_ids,
            event_ids=appended_event_ids,
            projection_rebuilt=projection is not None,
            projection_result=projection,
        ) if appended_subject_ids or appended_event_ids else None,
    }


def _receipt_same_identity(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_transaction = _receipt_transaction_id(left)
    right_transaction = _receipt_transaction_id(right)
    left_identity = _receipt_identity_token(left)
    right_identity = _receipt_identity_token(right)
    return bool(
        left_transaction
        and right_transaction
        and left_transaction == right_transaction
        and left_identity
        and right_identity
        and left_identity == right_identity
    )


def _project_receipt_event(item: Dict[str, Any], receipt: Dict[str, Any], event: Mapping[str, Any]) -> None:
    receipt_id = str(
        receipt.get("transaction_id")
        or receipt.get("id")
        or event.get("event_id")
        or f"receipt_{item.get('id')}"
    ).strip()
    receipt["id"] = receipt_id
    receipt["source_event_id"] = event.get("event_id")
    receipts = list(item.get("execution_receipts") or [])
    existing_index: int | None = None
    for index, existing in enumerate(receipts):
        if isinstance(existing, Mapping) and _receipt_same_identity(existing, receipt):
            existing_index = index
            break
    if existing_index is None:
        receipts.append(receipt)
        item["latest_execution_receipt"] = receipt
    else:
        existing = dict(receipts[existing_index])
        source_event_ids = list(existing.get("source_event_ids") or [])
        for source_event_id in (existing.get("source_event_id"), event.get("event_id")):
            token = str(source_event_id or "").strip()
            if token and token not in source_event_ids:
                source_event_ids.append(token)
        merged = {**existing, **receipt}
        if source_event_ids:
            merged["source_event_ids"] = source_event_ids
        receipts[existing_index] = merged
        item["latest_execution_receipt"] = merged
    item["execution_receipts"] = receipts


def _project_evidence_attachment_event(
    item: Dict[str, Any],
    payload: Mapping[str, Any],
    event: Mapping[str, Any],
) -> None:
    raw_attachment = payload.get("evidence_attachment")
    if isinstance(raw_attachment, Mapping):
        attachment = dict(raw_attachment)
    else:
        attachment = {key: value for key, value in payload.items() if key != "note"}

    promoted_receipt = (
        attachment.get("promoted_receipt")
        if isinstance(attachment.get("promoted_receipt"), Mapping)
        else {}
    )
    receipt_ref = str(
        attachment.get("receipt_ref")
        or promoted_receipt.get("receipt_ref")
        or event.get("event_id")
        or ""
    ).strip()
    receipt_path = str(
        attachment.get("receipt_path")
        or promoted_receipt.get("receipt_path")
        or ""
    ).strip()
    attachment_id = str(attachment.get("id") or receipt_ref or event.get("event_id") or "").strip()
    attachment["id"] = attachment_id
    attachment["source_event_id"] = event.get("event_id")
    if receipt_ref:
        attachment.setdefault("receipt_ref", receipt_ref)
    if receipt_path:
        attachment.setdefault("receipt_path", receipt_path)

    attachments = list(item.get("evidence_attachments") or [])
    existing_index: int | None = None
    for index, existing in enumerate(attachments):
        if not isinstance(existing, Mapping):
            continue
        if str(existing.get("id") or "").strip() == attachment_id:
            existing_index = index
            break
    if existing_index is None:
        attachments.append(attachment)
        item["latest_evidence_attachment"] = attachment
    else:
        existing = dict(attachments[existing_index])
        source_event_ids = list(existing.get("source_event_ids") or [])
        for source_event_id in (existing.get("source_event_id"), event.get("event_id")):
            token = str(source_event_id or "").strip()
            if token and token not in source_event_ids:
                source_event_ids.append(token)
        merged = {**existing, **attachment}
        if source_event_ids:
            merged["source_event_ids"] = source_event_ids
        attachments[existing_index] = merged
        item["latest_evidence_attachment"] = merged
    item["evidence_attachments"] = attachments

    refs = event.get("refs") if isinstance(event.get("refs"), Mapping) else {}
    for key in ("receipt_refs", "evidence_refs"):
        merged = list(item.get(key) or [])
        candidates = list(payload.get(key) or []) + list(refs.get(key) or [])
        if key == "receipt_refs" and receipt_ref:
            candidates.append(receipt_ref)
        if key == "evidence_refs" and receipt_path:
            candidates.append(receipt_path)
        for ref in candidates:
            if ref and ref not in merged:
                merged.append(ref)
        if merged:
            item[key] = merged


def _ledger_work_items(repo_root: Path) -> list[dict[str, Any]]:
    payload = _safe_read_json(repo_root / LEDGER_REL)
    rows = payload.get("work_items") if isinstance(payload, Mapping) else None
    if not isinstance(rows, list):
        ledger = payload.get("ledger") if isinstance(payload, Mapping) else {}
        rows = ledger.get("work_items") if isinstance(ledger, Mapping) else []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def execution_receipt_reconcile_state(
    repo_root: Path,
    *,
    subject_id: str,
    receipt: Mapping[str, Any],
) -> Dict[str, Any]:
    """Return idempotency/conflict state for a Task Ledger execution receipt."""
    subject = str(subject_id or "").strip()
    transaction_id = _receipt_transaction_id(receipt)
    commit_hash = _receipt_commit_hash(receipt)
    closeout_state = _receipt_closeout_state(receipt)
    landing_mode = "git_commit" if commit_hash else "validated_uncommitted"
    missing_fields = _receipt_missing_fields(subject_id=subject, receipt=receipt)
    if missing_fields:
        repair_hint = _receipt_missing_fields_repair_hint(receipt)
        return {
            "schema": "task_ledger_execution_receipt_reconcile_state_v0",
            "ok": False,
            "status": "receipt_blocked_missing_fields",
            "subject_id": subject or None,
            "transaction_id": transaction_id or None,
            "commit_hash": commit_hash or None,
            "closeout_state": closeout_state or None,
            "missing_fields": missing_fields,
            **repair_hint,
        }

    subject_rows = [
        row
        for row in _ledger_work_items(repo_root)
        if str(row.get("id") or "").strip() == subject
    ]
    receipts: list[dict[str, Any]] = []
    for row in subject_rows:
        for existing in row.get("execution_receipts") or []:
            if isinstance(existing, Mapping):
                receipts.append(dict(existing))

    same_transaction = [
        existing
        for existing in receipts
        if _receipt_transaction_id(existing) == transaction_id
    ]
    same_commit = [
        existing
        for existing in receipts
        if commit_hash and _receipt_commit_hash(existing) == commit_hash
    ]
    same_identity = [
        existing
        for existing in same_transaction
        if _receipt_same_identity(existing, receipt)
    ]
    if same_identity:
        return {
            "schema": "task_ledger_execution_receipt_reconcile_state_v0",
            "ok": True,
            "status": "receipt_already_recorded",
            "subject_id": subject,
            "transaction_id": transaction_id,
            "commit_hash": commit_hash,
            "closeout_state": closeout_state or None,
            "receipt_landing_mode": landing_mode,
            "existing_receipt": same_identity[-1],
        }

    transaction_conflicts = [
        existing
        for existing in same_transaction
        if (
            (_receipt_commit_hash(existing) and commit_hash and _receipt_commit_hash(existing) != commit_hash)
            or (_receipt_commit_hash(existing) and not commit_hash)
        )
    ]
    if transaction_conflicts:
        return {
            "schema": "task_ledger_execution_receipt_reconcile_state_v0",
            "ok": False,
            "status": "receipt_conflict",
            "conflict_kind": (
                "same_transaction_id_commit_presence_mismatch"
                if not commit_hash
                else "same_transaction_id_different_commit_hash"
            ),
            "subject_id": subject,
            "transaction_id": transaction_id,
            "commit_hash": commit_hash,
            "closeout_state": closeout_state or None,
            "conflicting_receipts": transaction_conflicts,
        }

    alias_receipts = [
        existing
        for existing in same_commit
        if _receipt_transaction_id(existing) and _receipt_transaction_id(existing) != transaction_id
    ]
    return {
        "schema": "task_ledger_execution_receipt_reconcile_state_v0",
        "ok": True,
        "status": "receipt_ready_to_record",
        "subject_id": subject,
        "transaction_id": transaction_id,
        "commit_hash": commit_hash,
        "closeout_state": closeout_state or None,
        "receipt_landing_mode": landing_mode,
        "alias_status": "same_commit_different_transaction_id" if alias_receipts else None,
        "alias_receipts": alias_receipts,
    }


def build_projection(
    events: Iterable[Mapping[str, Any]],
    *,
    generated_at: str | None = None,
    mission_blackboard: Mapping[str, Any] | None = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    event_list = [dict(event) for event in events]
    event_list.sort(key=lambda row: (str(row.get("created_at") or ""), str(row.get("event_id") or "")))
    generated = generated_at or utc_now()
    work_items: Dict[str, Dict[str, Any]] = {}
    signoffs: Dict[str, Dict[str, Any]] = {}

    for event in event_list:
        subject_id = str(event.get("subject_id") or "").strip()
        if not subject_id:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        event_type = str(event.get("event_type") or "")
        if event_type == "work_item.legacy_bootstrapped":
            legacy = payload.get("legacy_snapshot") if isinstance(payload.get("legacy_snapshot"), Mapping) else {}
            work_item = payload.get("work_item") if isinstance(payload.get("work_item"), Mapping) else {}
            item = _legacy_task_to_work_item(legacy) if legacy else dict(work_item)
            item["id"] = subject_id
            item.setdefault("kind", "work_item")
            item.setdefault("work_item_type", "task")
            item.setdefault("event_history", [])
            item.setdefault("source_event_ids", [])
            work_items[subject_id] = item
            _append_history(work_items[subject_id], event)
            continue

        existing_item = subject_id in work_items
        item = _ensure_item(work_items, subject_id, event)
        _append_history(item, event)

        if event_type == "work_item.captured":
            if existing_item and _capture_would_downgrade_existing_item(item):
                item.setdefault("capture_overlays", []).append(
                    _capture_overlay_from_event(event, payload)
                )
                _merge_tag_fields(item, payload)
                continue
            item.update(
                {
                    "work_item_type": payload.get("work_item_type") or payload.get("type") or "capture",
                    "candidate_work_item_type": payload.get("candidate_work_item_type") or item.get("candidate_work_item_type"),
                    "title": payload.get("title") or item.get("title"),
                    "statement": payload.get("statement") or payload.get("body") or item.get("statement"),
                    "problem": payload.get("problem") or item.get("problem"),
                    "impact": payload.get("impact") or item.get("impact"),
                    "acceptance": payload.get("acceptance") or item.get("acceptance"),
                    "evidence": _coerce_id_list(payload.get("evidence") or item.get("evidence")),
                    "state": "captured",
                    "status": "captured",
                    "confidence": payload.get("confidence", item.get("confidence")),
                    "satisfaction_contract": _satisfaction_contract_from_payload(payload)
                    or item.get("satisfaction_contract")
                    or {},
                    "integration_contract": _integration_contract_from_payload(payload)
                    or item.get("integration_contract")
                    or {},
                    "authority": payload.get("authority") or item.get("authority") or {},
                    "execution": payload.get("execution") or item.get("execution") or {},
                    "completion": payload.get("completion") or item.get("completion") or {},
                    "closeout_assurance": _closeout_assurance_from_payload(payload)
                    or item.get("closeout_assurance")
                    or {},
                    "propagation": payload.get("propagation") or item.get("propagation") or {},
                    "lineage": payload.get("lineage") or item.get("lineage") or {},
                    "provenance": payload.get("provenance") or item.get("provenance") or {},
                }
            )
            _merge_dependency_fields(item, payload)
            _merge_tag_fields(item, payload)
        elif event_type == "work_item.promoted":
            item["work_item_type"] = payload.get("work_item_type") or item.get("work_item_type") or "task"
            item["state"] = payload.get("state") or "ready"
            item["status"] = payload.get("status") or "ready"
            item["rank"] = payload.get("rank", item.get("rank"))
            item["rank_history"] = list(item.get("rank_history") or []) + list(payload.get("rank_history") or [])
            _merge_dependency_fields(item, payload)
        elif event_type == "work_item.shaped":
            item["state"] = payload.get("state") or "shaping"
            if _nonempty_text(payload.get("title")):
                item["title"] = payload["title"]
            if _nonempty_text(payload.get("candidate_work_item_type")):
                item["candidate_work_item_type"] = payload["candidate_work_item_type"]
            if _nonempty_text(payload.get("work_item_type")):
                item["work_item_type"] = payload["work_item_type"]
            shaped_statement = payload.get("statement") or payload.get("summary")
            if _nonempty_text(shaped_statement):
                item["statement"] = shaped_statement
            item["plan"] = payload.get("plan") or item.get("plan")
            item["confidence"] = payload.get("confidence", item.get("confidence"))
            satisfaction_contract = _satisfaction_contract_from_payload(payload)
            if satisfaction_contract:
                item["satisfaction_contract"] = satisfaction_contract
            integration_contract = _integration_contract_from_payload(payload)
            if integration_contract:
                item["integration_contract"] = integration_contract
            if isinstance(payload.get("completion"), Mapping):
                item["completion"] = payload["completion"]
            elif isinstance(payload.get("plan"), Mapping) and isinstance(
                payload["plan"].get("completion_contract"), Mapping
            ):
                item["completion"] = payload["plan"]["completion_contract"]
            closeout_assurance = _closeout_assurance_from_payload(payload)
            if closeout_assurance:
                item["closeout_assurance"] = closeout_assurance
            if isinstance(payload.get("authority"), Mapping):
                item["authority"] = payload["authority"]
            _merge_dependency_fields(item, payload)
        elif event_type == "work_item.claimed":
            item["state"] = payload.get("state") or "claimed"
            item["status"] = item["state"]
            item["owner"] = payload.get("owner") or event.get("created_by")
            item["execution"] = {**dict(item.get("execution") or {}), **dict(payload.get("execution") or {})}
            item["work_ledger_refs"] = list(payload.get("work_ledger_refs") or [])
        elif event_type == "work_item.released":
            item["state"] = payload.get("state") or "ready"
            item["status"] = item["state"]
            item["release_reason"] = payload.get("reason")
        elif event_type == "work_item.state_transitioned":
            state = _transition_target_state(payload)
            if state in WORK_ITEM_STATES:
                item["state"] = state
                item["status"] = payload.get("status") or state
            if _nonempty_text(payload.get("title")):
                item["title"] = payload["title"]
            transition_statement = payload.get("statement") or payload.get("summary")
            if _nonempty_text(transition_statement):
                item["statement"] = transition_statement
            closeout_assurance = _closeout_assurance_from_payload(payload)
            if closeout_assurance:
                item["closeout_assurance"] = closeout_assurance
            _merge_dependency_fields(item, payload)
        elif event_type == "work_item.blocked":
            item["state"] = "blocked"
            item["status"] = "blocked"
            item["blocker"] = payload.get("blocker") or payload.get("reason")
        elif event_type == "work_item.unblocked":
            item["state"] = payload.get("state") or "ready"
            item["status"] = item["state"]
            item.pop("blocker", None)
        elif event_type == "work_item.note_added":
            item.setdefault("notes", []).append(
                {
                    "at": event.get("created_at"),
                    "by": event.get("created_by"),
                    "note": payload.get("note") or payload.get("body"),
                    "event_id": event.get("event_id"),
                }
            )
        elif event_type == "work_item.rerank_proposed":
            item["proposed_rank"] = payload.get("rank")
        elif event_type == "work_item.rerank_committed":
            item["rank"] = payload.get("rank")
            item.setdefault("rank_history", []).append(
                {
                    "rank": payload.get("rank"),
                    "set_at": event.get("created_at"),
                    "set_by": event.get("created_by"),
                    "justification": payload.get("justification") or "",
                    "event_id": event.get("event_id"),
                }
            )
        elif event_type == "work_item.integration_discovered":
            contract = payload.get("integration_contract")
            if isinstance(contract, Mapping):
                item["integration_contract"] = contract
            _merge_dependency_fields(item, payload)
        elif event_type == "work_item.satisfaction_linked":
            contract = payload.get("satisfaction_contract")
            if isinstance(contract, Mapping):
                item["satisfaction_contract"] = contract
        elif event_type == "work_item.execution_profile_set":
            item["execution"] = {**dict(item.get("execution") or {}), **dict(payload.get("execution") or {})}
        elif event_type == "work_item.execution_receipt_recorded":
            receipt = dict(payload.get("execution_receipt") or payload.get("receipt") or payload)
            _project_receipt_event(item, receipt, event)
            closeout_assurance = _closeout_assurance_from_payload(payload) or _closeout_assurance_from_payload(receipt)
            if closeout_assurance:
                item["closeout_assurance"] = closeout_assurance
            if isinstance(payload.get("execution"), Mapping):
                item["execution"] = {**dict(item.get("execution") or {}), **dict(payload["execution"])}
            refs = event.get("refs") if isinstance(event.get("refs"), Mapping) else {}
            for key in ("work_ledger_refs", "commit_refs", "receipt_refs"):
                merged = list(item.get(key) or [])
                for ref in list(payload.get(key) or []) + list(refs.get(key) or []):
                    if ref and ref not in merged:
                        merged.append(ref)
                if merged:
                    item[key] = merged
            item["transaction_state"] = (
                receipt.get("closeout_state")
                or receipt.get("status")
                or item.get("transaction_state")
            )
        elif event_type == "work_item.evidence_attached":
            _project_evidence_attachment_event(item, payload, event)
            note = str(payload.get("note") or "").strip()
            if note:
                item.setdefault("notes", []).append(
                    {
                        "at": event.get("created_at"),
                        "by": event.get("created_by"),
                        "note": note,
                        "event_id": event.get("event_id"),
                    }
                )
        elif event_type in {"work_item.bridge_delegated", "work_item.provider_job_created"}:
            item["state"] = payload.get("state") or "active"
            item["status"] = item["state"]
            item["execution"] = {**dict(item.get("execution") or {}), **dict(payload.get("execution") or {})}
        elif event_type == "work_item.schema_migrated":
            item["state"] = payload.get("state") or item.get("state") or "shaping"
            item["status"] = item["state"]
            item["schema_migration"] = {
                **dict(item.get("schema_migration") or {}),
                **dict(payload.get("schema_migration") or payload),
                "source_event_id": event.get("event_id"),
                "migrated_at": event.get("created_at"),
            }
            item.pop("legacy_snapshot", None)
        elif event_type in {"work_item.reviewed", "work_item.provider_job_completed"}:
            item["state"] = payload.get("state") or "review"
            item["status"] = item["state"]
            item["review"] = payload.get("review") or payload
        elif event_type == "work_item.signoff_recorded":
            raw_signoff = payload.get("signoff")
            if isinstance(raw_signoff, Mapping):
                signoff = dict(raw_signoff)
            else:
                signoff = {
                    "id": f"signoff_{subject_id}",
                    "work_item_id": subject_id,
                    "result": str(raw_signoff or payload.get("result") or "recorded"),
                    "outcome_summary": str(
                        payload.get("summary")
                        or payload.get("outcome_summary")
                        or raw_signoff
                        or "signoff recorded"
                    ),
                    "evidence_refs": list(payload.get("evidence_refs") or []),
                    "legacy_payload_shape": (
                        "scalar_signoff_field"
                        if raw_signoff is not None
                        else "payload_as_signoff"
                    ),
                }
            signoff_id = str(signoff.get("id") or f"signoff_{subject_id}").strip()
            signoff["id"] = signoff_id
            signoff["work_item_id"] = signoff.get("work_item_id") or subject_id
            signoff["source_event_ids"] = list(signoff.get("source_event_ids") or []) + [event.get("event_id")]
            signoffs[signoff_id] = signoff
            item["sign_off_id"] = signoff_id
            item["state"] = payload.get("state") or "signoff"
            item["status"] = item["state"]
            closeout_assurance = _closeout_assurance_from_payload(payload) or _closeout_assurance_from_payload(signoff)
            if closeout_assurance:
                item["closeout_assurance"] = closeout_assurance
        elif event_type == "work_item.propagation_recorded":
            item["propagation"] = {**dict(item.get("propagation") or {}), **dict(payload.get("propagation") or {})}
            item["state"] = payload.get("state") or "propagated"
            item["status"] = item["state"]
            closeout_assurance = _closeout_assurance_from_payload(payload)
            if closeout_assurance:
                item["closeout_assurance"] = closeout_assurance
        elif event_type == "work_item.retired":
            item["state"] = "retired"
            item["status"] = "retired"
            item["retired_reason"] = payload.get("reason")

        _merge_dependency_fields(item, payload)

    tasks = [
        _build_task_projection(item)
        for item in work_items.values()
        if str(item.get("work_item_type") or "") != "capture"
    ]
    tasks.sort(key=lambda item: (item.get("rank") is None, item.get("rank") or 999999, str(item.get("id"))))
    work_item_rows = [_build_task_projection(item) for item in work_items.values()]
    work_item_rows.sort(key=lambda item: str(item.get("id") or ""))

    ledger = {
        "kind": "task_ledger",
        "schema_version": TASK_LEDGER_PROJECTION_SCHEMA,
        "ledger_id": "global",
        "generated_at": generated,
        "updated_at": generated,
        "authority": {
            "lifecycle": "event_sourced_projection",
            "event_log": str(EVENTS_REL),
            "execution_concurrency_substrate": [
                "codex/standards/std_work_ledger.json",
                "codex/ledger/<phase_id>/work_ledger.jsonl",
                str(WORK_LEDGER_RUNTIME_REL),
            ],
            "projection_rule": "rebuild from events; direct projection edits are rescue-only",
        },
        "expansion_contract": {
            "state_flow": WORK_ITEM_STATE_FLOW,
            "event_authority": "state/task_ledger/events.jsonl",
        },
        "tasks": tasks,
        "work_items": work_item_rows,
        "event_count": len(event_list),
    }
    signoff_projection = {
        "kind": "task_sign_off_ledger",
        "schema_version": TASK_SIGNOFF_PROJECTION_SCHEMA,
        "ledger_id": "global",
        "generated_at": generated,
        "updated_at": generated,
        "authority": {
            "lifecycle": "event_sourced_projection",
            "event_log": str(EVENTS_REL),
        },
        "sign_offs": sorted(signoffs.values(), key=lambda item: str(item.get("id") or "")),
    }
    return {
        "ledger": ledger,
        "sign_offs": signoff_projection,
        "views": build_views(
            work_item_rows,
            signoff_projection["sign_offs"],
            event_list,
            generated,
            mission_blackboard=mission_blackboard,
            repo_root=repo_root,
        ),
    }


def _rank_key(item: Mapping[str, Any]) -> tuple[Any, Any, str]:
    return (item.get("rank") is None, item.get("rank") or 999999, str(item.get("id") or ""))


CLOSED_WORK_ITEM_STATES = {"done", "propagated", "retired"}
DEPENDENCY_SATISFIED_STATES = {"done", "propagated"}
DEPENDENCY_RESOLUTION_SATISFIED_STATUSES = {"resolved", "satisfied", "waived", "superseded", "folded"}
EXECUTION_MENU_LIMIT = 7
EXECUTION_COMMITMENT_EVENT_TYPES = {
    "work_item.promoted",
    "work_item.claimed",
    "work_item.state_transitioned",
    "work_item.rerank_committed",
}
EXECUTION_MENU_RATIONALE = [
    "captures are the inbox, not the active work plan",
    "only explicit commitment-event evidence enters the execution menu",
    "shaped captures that are not yet promoted stay in promotion_candidates",
    "legacy rank_history is priority metadata, not execution commitment",
    "closed/signoff captures stay visible as audit facts, not retire/merge candidates or WIP",
    f"the menu is capped at {EXECUTION_MENU_LIMIT} to keep active WorkItem implementation small",
    "ranking prefers explicit rank, then deterministic WorkItem id order",
]
SEMANTIC_DUPLICATE_STOPWORDS = {
    "about",
    "after",
    "are",
    "agent",
    "agents",
    "before",
    "capture",
    "captures",
    "codex",
    "for",
    "from",
    "into",
    "ledger",
    "phase",
    "quick",
    "task",
    "tasks",
    "that",
    "the",
    "they",
    "this",
    "through",
    "type",
    "with",
    "work",
    "workitem",
    "workitems",
}
SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS = 5
SEMANTIC_DUPLICATE_MIN_OVERLAP = 0.70
SEMANTIC_DUPLICATE_MIN_JACCARD = 0.45
SEMANTIC_DUPLICATE_PAIRWISE_BUCKET_LIMIT = 160
SEMANTIC_DUPLICATE_MAX_TOKEN_POSTINGS = 30


def _compaction_governance_packet() -> Dict[str, Any]:
    return {
        "schema": "task_ledger_compaction_governance_v0",
        "owner_surface": str(VIEWS_REL / "merge_or_retire_candidates.json"),
        "owner_report": "task_ledger_apply.py organizer-report::merge_or_retire_diagnostic",
        "purpose": "Route duplicate, stale, closed, or superseded traces into supported Task Ledger event dispositions instead of adding more procedural prose.",
        "decision_ladder": [
            {
                "when": "closed_or_signoff_capture",
                "default_disposition": "leave_closed",
                "event_lane": "work_item.note_added only if a projection consumer still needs extra evidence",
            },
            {
                "when": "exact_duplicate_capture_group",
                "default_disposition": "retire duplicate rows or add a provenance note to the kept row",
                "event_lane": "work_item.retired or work_item.note_added",
            },
            {
                "when": "semantic_duplicate_capture_group",
                "default_disposition": "operator-review merge, supersede, retire, or link-as-evidence decision",
                "event_lane": "work_item.retired, work_item.note_added, or work_item.propagation_recorded",
            },
        ],
        "supported_event_lanes": [
            "work_item.retired",
            "work_item.note_added",
            "work_item.propagation_recorded",
            "work_item.shaped",
            "work_item.captured",
        ],
        "unsupported_as_direct_events": [
            "work_item.merged",
            "work_item.superseded",
        ],
        "proof_signals": [
            "candidate group carries item_ids and evidence",
            "organizer-report exposes counts_by_kind and semantic_conflict_detector",
            "semantic duplicate detection suppresses explicit hard dependency and shared downstream co-prerequisite pairs before grouping",
            "chosen disposition appends an event and preserves source histories",
        ],
        "operator_review_required_for": [
            "semantic_duplicate_capture_group",
            "retiring a row that is not already closed",
            "declaring one WorkItem canonical over another",
        ],
        "anti_accretion_rule": "Do not create another CAP or standards paragraph when merge_or_retire_candidates already carries the duplicate pressure; append a supported disposition event or record why review is required.",
    }


def _norm_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _semantic_duplicate_tokens(item: Mapping[str, Any]) -> set[str]:
    text = " ".join(
        [
            str(item.get("title") or ""),
            str(item.get("statement") or ""),
            str(item.get("candidate_work_item_type") or ""),
        ]
    ).lower()
    tokens = set()
    for token in re.findall(r"[a-z0-9]+", text):
        if len(token) < 3 or token in SEMANTIC_DUPLICATE_STOPWORDS:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.add(token)
    return tokens


def _iter_id_values(value: Any) -> Iterator[str]:
    if isinstance(value, str):
        candidate = value.strip()
        if candidate:
            yield candidate
        return
    if isinstance(value, Mapping):
        candidate = str(value.get("id") or value.get("work_item_id") or "").strip()
        if candidate:
            yield candidate
        return
    if isinstance(value, Iterable):
        for item in value:
            yield from _iter_id_values(item)


def _hard_dependency_ids(item: Mapping[str, Any]) -> set[str]:
    hard_ids: set[str] = set()
    hard_ids.update(_iter_id_values(item.get("depends_on")))

    contracts = item.get("contracts")
    if isinstance(contracts, Mapping):
        hard_ids.update(_iter_id_values(contracts.get("depends_on")))

    dependency_status = item.get("dependency_status")
    if isinstance(dependency_status, Mapping):
        for key in ("satisfied_dep_ids", "unsatisfied_dep_ids", "dangling_dep_ids"):
            hard_ids.update(_iter_id_values(dependency_status.get(key)))
        for edge_key in ("dependency_states", "upstream_dependency_edges"):
            for edge in dependency_status.get(edge_key) or []:
                if not isinstance(edge, Mapping):
                    continue
                if str(edge.get("relationship") or "") == "upstream_hard_dependency":
                    hard_ids.update(_iter_id_values(edge))
    return hard_ids


def _has_hard_dependency_edge(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_id = str(left.get("id") or "").strip()
    right_id = str(right.get("id") or "").strip()
    if not left_id or not right_id:
        return False
    return right_id in _hard_dependency_ids(left) or left_id in _hard_dependency_ids(right)


def _downstream_coprerequisite_ids(item: Mapping[str, Any]) -> Dict[str, set[str]]:
    item_id = str(item.get("id") or "").strip()
    dependency_status = item.get("dependency_status")
    if not isinstance(dependency_status, Mapping):
        return {}

    by_downstream: Dict[str, set[str]] = defaultdict(set)
    for edge in dependency_status.get("downstream_unlock_edges") or []:
        if not isinstance(edge, Mapping):
            continue
        downstream_id = str(edge.get("id") or edge.get("work_item_id") or "").strip()
        if not downstream_id:
            continue
        sibling_ids = set(_iter_id_values(edge.get("downstream_unsatisfied_dep_ids")))
        if item_id:
            sibling_ids.add(item_id)
        by_downstream[downstream_id].update(sibling_ids)
    return by_downstream


def _share_downstream_coprerequisite_edge(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    left_id = str(left.get("id") or "").strip()
    right_id = str(right.get("id") or "").strip()
    if not left_id or not right_id:
        return False

    left_downstream = _downstream_coprerequisite_ids(left)
    right_downstream = _downstream_coprerequisite_ids(right)
    for downstream_id in set(left_downstream) & set(right_downstream):
        sibling_ids = left_downstream[downstream_id] | right_downstream[downstream_id]
        if left_id in sibling_ids and right_id in sibling_ids:
            return True
    return False


def _downstream_coprerequisite_pairs(items: Sequence[Mapping[str, Any]]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    known_ids = {
        str(item.get("id") or "").strip()
        for item in items
        if str(item.get("id") or "").strip()
    }
    for item in items:
        dependency_ids = sorted(dep_id for dep_id in _hard_dependency_ids(item) if dep_id in known_ids)
        if len(dependency_ids) < 2:
            continue
        for left_index, left_id in enumerate(dependency_ids):
            for right_id in dependency_ids[left_index + 1:]:
                pairs.add((left_id, right_id))
    return pairs


def _semantic_duplicate_groups(items: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    exact_keys: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    buckets: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for item in items:
        exact_key = "|".join(
            [
                _norm_text(item.get("title")),
                _norm_text(item.get("statement")),
                _norm_text(item.get("candidate_work_item_type")),
            ]
        )
        if exact_key.strip("|"):
            exact_keys[exact_key].append(item)
        buckets[_norm_text(item.get("candidate_work_item_type"))].append(item)

    exact_duplicate_ids = {
        str(item.get("id") or "")
        for group in exact_keys.values()
        if len(group) > 1
        for item in group
    }
    groups: List[Dict[str, Any]] = []
    seen_group_keys: set[tuple[str, ...]] = set()
    coprerequisite_pairs = _downstream_coprerequisite_pairs(items)
    for candidate_type, bucket in buckets.items():
        token_rows = []
        for item in sorted(bucket, key=lambda row: str(row.get("id") or "")):
            if str(item.get("id") or "") in exact_duplicate_ids:
                continue
            tokens = _semantic_duplicate_tokens(item)
            if len(tokens) >= SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS:
                token_rows.append((item, tokens))
        edges: Dict[str, set[str]] = defaultdict(set)
        evidence_by_pair: Dict[tuple[str, str], Dict[str, Any]] = {}
        indexed_pair_scan = len(token_rows) > SEMANTIC_DUPLICATE_PAIRWISE_BUCKET_LIMIT
        token_to_indices: Dict[str, List[int]] = defaultdict(list)
        skipped_high_frequency_tokens: set[str] = set()
        pair_shared_counts: Counter[tuple[int, int]] = Counter()
        if indexed_pair_scan:
            for index, (_, tokens) in enumerate(token_rows):
                for token in tokens:
                    token_to_indices[token].append(index)
            for token, indices in token_to_indices.items():
                if len(indices) > SEMANTIC_DUPLICATE_MAX_TOKEN_POSTINGS:
                    skipped_high_frequency_tokens.add(token)
                    continue
                if len(indices) < 2:
                    continue
                for position, left_index in enumerate(indices):
                    for right_index in indices[position + 1:]:
                        pair_shared_counts[(left_index, right_index)] += 1
            candidate_pairs = [
                pair
                for pair, shared_count in pair_shared_counts.items()
                if shared_count >= SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS
            ]
        else:
            candidate_pairs = [
                (left_index, right_index)
                for left_index in range(len(token_rows))
                for right_index in range(left_index + 1, len(token_rows))
            ]

        for left_index, right_index in candidate_pairs:
            left, left_tokens = token_rows[left_index]
            right, right_tokens = token_rows[right_index]
            left_id = str(left.get("id") or "")
            right_id = str(right.get("id") or "")
            shared = left_tokens & right_tokens
            if len(shared) < SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS:
                continue
            union = left_tokens | right_tokens
            overlap = len(shared) / max(1, min(len(left_tokens), len(right_tokens)))
            jaccard = len(shared) / max(1, len(union))
            if overlap < SEMANTIC_DUPLICATE_MIN_OVERLAP or jaccard < SEMANTIC_DUPLICATE_MIN_JACCARD:
                continue
            pair_key = tuple(sorted([left_id, right_id]))
            if (
                _has_hard_dependency_edge(left, right)
                or pair_key in coprerequisite_pairs
                or _share_downstream_coprerequisite_edge(left, right)
            ):
                continue
            edges[left_id].add(right_id)
            edges[right_id].add(left_id)
            evidence_by_pair[pair_key] = {
                "item_ids": [left_id, right_id],
                "shared_tokens": sorted(shared)[:12],
                "overlap_coefficient": round(overlap, 3),
                "jaccard": round(jaccard, 3),
            }

        visited: set[str] = set()
        item_by_id = {str(item.get("id") or ""): item for item, _ in token_rows}
        for item_id in sorted(edges):
            if item_id in visited:
                continue
            stack = [item_id]
            component: set[str] = set()
            while stack:
                current = stack.pop()
                if current in component:
                    continue
                component.add(current)
                stack.extend(sorted(edges.get(current, set()) - component))
            visited.update(component)
            if len(component) < 2:
                continue
            group_key = tuple(sorted(component))
            if group_key in seen_group_keys:
                continue
            seen_group_keys.add(group_key)
            pair_evidence = [
                evidence
                for pair, evidence in sorted(evidence_by_pair.items())
                if set(pair).issubset(component)
            ][:8]
            representative = item_by_id.get(group_key[0], {})
            groups.append(
                {
                    "kind": "semantic_duplicate_capture_group",
                    "item_ids": list(group_key),
                    "title": representative.get("title"),
                    "candidate_work_item_type": candidate_type or None,
                    "detection": {
                        "mode": "conservative_token_overlap",
                        "min_shared_tokens": SEMANTIC_DUPLICATE_MIN_SHARED_TOKENS,
                        "min_overlap_coefficient": SEMANTIC_DUPLICATE_MIN_OVERLAP,
                        "min_jaccard": SEMANTIC_DUPLICATE_MIN_JACCARD,
                        "candidate_scan": (
                            "inverted_token_index"
                            if indexed_pair_scan
                            else "pairwise_small_bucket"
                        ),
                        "high_frequency_token_skip_count": len(skipped_high_frequency_tokens),
                        "pair_evidence": pair_evidence,
                    },
                    "owner_surface": str(VIEWS_REL / "merge_or_retire_candidates.json"),
                    "recommended_action": "review for merge/supersede/retire disposition through supported retire/note/propagate events; preserve all source histories",
                }
            )
    return groups


def _item_state(item: Mapping[str, Any]) -> str:
    return str(item.get("state") or item.get("status") or "").strip()


TERMINAL_EXECUTION_RECEIPT_STATES = {
    "accepted",
    "closed",
    "committed",
    "complete",
    "completed",
    "done",
    "landed",
    "propagated",
    "refined",
    "released",
    "signed_off",
    "signed-off",
}

TERMINAL_EXECUTION_RECEIPT_SUFFIXES = (
    "_landed",
)


def _latest_execution_receipt_state(item: Mapping[str, Any]) -> str:
    receipt = item.get("latest_execution_receipt")
    if not isinstance(receipt, Mapping):
        receipts = item.get("execution_receipts")
        if isinstance(receipts, list):
            receipt = next(
                (row for row in reversed(receipts) if isinstance(row, Mapping)),
                {},
            )
        else:
            receipt = {}
    return str(receipt.get("closeout_state") or receipt.get("status") or "").strip().lower()


def _is_terminal_execution_receipt_state(state: str) -> bool:
    normalized = str(state or "").strip().lower()
    if normalized in TERMINAL_EXECUTION_RECEIPT_STATES:
        return True
    return any(normalized.endswith(suffix) for suffix in TERMINAL_EXECUTION_RECEIPT_SUFFIXES)


def _has_terminal_execution_receipt(item: Mapping[str, Any]) -> bool:
    return _is_terminal_execution_receipt_state(_latest_execution_receipt_state(item))


def _is_closed_or_signed_off(item: Mapping[str, Any]) -> bool:
    return (
        _item_state(item) in CLOSED_WORK_ITEM_STATES
        or bool(item.get("sign_off_id"))
        or _has_terminal_execution_receipt(item)
    )


def _item_event_count(item: Mapping[str, Any]) -> int:
    history = item.get("event_history")
    if isinstance(history, list):
        return len(history)
    return len(item.get("source_event_ids") or [])


def _item_event_types(item: Mapping[str, Any]) -> set[str]:
    event_types = {
        str(row.get("event_type") or "")
        for row in (item.get("event_history") or [])
        if isinstance(row, Mapping)
    }
    event_types.update(str(value or "") for value in (item.get("source_event_types") or []))
    return {event_type for event_type in event_types if event_type}


def _missing_contract_fields(item: Mapping[str, Any]) -> List[str]:
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    missing: List[str] = []
    if not completeness.get("has_satisfaction_contract"):
        missing.append("satisfaction_contract")
    if not completeness.get("has_integration_contract"):
        missing.append("integration_contract")
    if completeness.get("has_integration_contract") and not completeness.get("exact_surfaces_grounded"):
        missing.append("integration_contract.exact_surfaces_discovered")
    return missing


def _capture_triage_status(item: Mapping[str, Any]) -> tuple[str, str, List[str]]:
    state = _item_state(item)
    missing = _missing_contract_fields(item)
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    if _is_closed_or_signed_off(item):
        return ("closed_or_signed_off", "no_action_closed", [])
    if state == "blocked":
        return ("blocked", "inspect_blocker", [])
    if completeness.get("needs_signoff"):
        return ("needs_signoff", "record_signoff_or_residual", [])
    if missing:
        return ("needs_contract_shaping", "append_shape_or_link_contracts", missing)
    if not completeness.get("has_completion_contract"):
        return ("shaped_needs_completion_contract", "shape_completion_or_promote", ["completion_contract"])
    return ("shaped_ready", "promote_rank_or_execute", [])


def _capture_triage_categories(item: Mapping[str, Any], status: str, missing: Sequence[str]) -> List[str]:
    state = _item_state(item)
    event_count = _item_event_count(item)
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    candidate_type = str(item.get("candidate_work_item_type") or item.get("work_item_type") or "").strip()
    searchable = _norm_text(
        " ".join(
            str(value or "")
            for value in (
                item.get("title"),
                item.get("statement"),
                item.get("candidate_work_item_type"),
                item.get("work_item_type"),
            )
        )
    )
    categories: set[str] = set()
    if event_count <= 1 and state == "captured" and status not in {"closed_or_signed_off", "blocked"}:
        categories.add("raw_capture_inbox")
    if status in {"shaped_ready", "shaped_needs_completion_contract"}:
        categories.add("shaped_ready")
    if "satisfaction_contract" in missing:
        categories.add("missing_satisfaction_contract")
    if "integration_contract" in missing or "integration_contract.exact_surfaces_discovered" in missing:
        categories.add("missing_integration_contract")
    if "integration_contract.exact_surfaces_discovered" in missing:
        categories.add("missing_exact_surfaces")
    if "completion_contract" in missing:
        categories.add("missing_completion_contract")
    if status == "blocked":
        categories.add("blocked")
    if status == "needs_signoff":
        categories.add("needs_signoff")
    if status == "closed_or_signed_off":
        categories.add("already_solved_candidate")
    if any(token in searchable for token in ("residual", "follow-up", "followup", "closeout")):
        categories.add("residual_followup")
    if candidate_type in {"meta_mission", "metabolic_reflex", "provider_job", "bridge_action"}:
        categories.add(
            {
                "meta_mission": "meta_mission",
                "metabolic_reflex": "metabolic",
                "provider_job": "provider_assignable",
                "bridge_action": "bridge_assignable",
            }[candidate_type]
        )
    if completeness.get("has_prompt_trace_ref"):
        categories.add("prompt_trace_linked")
    if completeness.get("has_work_ledger_claim_ref"):
        categories.add("work_ledger_linked")
    return sorted(categories)


def _capture_triage_row(item: Mapping[str, Any]) -> Dict[str, Any]:
    status, action, missing = _capture_triage_status(item)
    state = _item_state(item)
    event_count = _item_event_count(item)
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    reasons: List[str] = []
    if event_count <= 1 and state == "captured" and status not in {"closed_or_signed_off", "blocked"}:
        reasons.append("single_capture_event_no_triage")
    if item.get("sign_off_id"):
        reasons.append("signoff_recorded")
    if state in CLOSED_WORK_ITEM_STATES:
        reasons.append(f"state:{state}")
    receipt_state = _latest_execution_receipt_state(item)
    if _is_terminal_execution_receipt_state(receipt_state):
        reasons.append(f"execution_receipt:{receipt_state}")
    if missing:
        reasons.extend(f"missing:{field}" for field in missing)
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "state": state,
        "work_item_type": item.get("work_item_type"),
        "candidate_work_item_type": item.get("candidate_work_item_type"),
        "triage_status": status,
        "recommended_action": action,
        "missing_fields": missing,
        "categories": _capture_triage_categories(item, status, missing),
        "linkage": {
            "prompt_trace_linked": bool(completeness.get("has_prompt_trace_ref")),
            "work_ledger_linked": bool(completeness.get("has_work_ledger_claim_ref")),
        },
        "reasons": reasons,
        "event_count": event_count,
        "rank": item.get("rank"),
        "sign_off_id": item.get("sign_off_id"),
        "updated_at": item.get("updated_at"),
        "source_event_ids": list(item.get("source_event_ids") or []),
    }


def _execution_priority(row: Mapping[str, Any]) -> tuple[Any, Any, Any, str]:
    title = _norm_text(row.get("title"))
    candidate_type = _norm_text(row.get("candidate_work_item_type"))
    status = str(row.get("triage_status") or "")
    status_weight = {
        "shaped_ready": 0,
        "shaped_needs_completion_contract": 1,
        "needs_contract_shaping": 8,
        "needs_signoff": 9,
        "blocked": 10,
        "closed_or_signed_off": 99,
    }.get(status, 20)
    type_weight = {
        "standard_gap": 0,
        "event_substrate": 1,
        "uppropagation_intake": 2,
        "provider_job": 3,
        "subphase": 4,
        "meta_mission": 5,
        "metabolic_reflex": 6,
        "bridge_action": 7,
        "synth_seed_propagation": 8,
        "task": 9,
    }.get(candidate_type, 10)
    token_weight = 50
    priority_tokens = [
        ("capture triage", 0),
        ("strict json", 1),
        ("paper-module projection", 2),
        ("paper module projection", 2),
        ("autonomous seed", 3),
        ("provider receipt", 4),
        ("option-surface", 5),
        ("option surface", 5),
        ("capture assimilation", 6),
        ("station", 7),
        ("hud", 7),
        ("subphase", 8),
    ]
    for token, weight in priority_tokens:
        if token in title:
            token_weight = weight
            break
    return (token_weight, status_weight, type_weight, str(row.get("id") or ""))


def _build_capture_triage_view(captures: List[Mapping[str, Any]], generated_at: str) -> Dict[str, Any]:
    rows = [_capture_triage_row(item) for item in sorted(captures, key=lambda item: str(item.get("id") or ""))]
    counts = _count_capture_triage_statuses(rows)
    stale_count = sum(1 for row in rows if "single_capture_event_no_triage" in (row.get("reasons") or []))
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_capture_triage_v1",
        "view_id": "capture_triage",
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "append Task Ledger events; this view is projection-only",
        },
        "policy": {
            "captures_are_inbox": True,
            "execution_menu_limit": EXECUTION_MENU_LIMIT,
            "wip_rule": "keep active implementation small; promote or shape captures before execution",
        },
        "why_many_captures": "captures are deliberately low-friction inbox records; this projection separates inbox volume from executable WIP",
        "items": rows,
        "count": len(rows),
        "counts_by_status": counts,
        "stale_capture_count": stale_count,
    }


CAPTURE_INBOX_CARD_FIELDS = (
    "id",
    "title",
    "state",
    "status",
    "work_item_type",
    "candidate_work_item_type",
    "created_at",
    "created_by",
    "updated_at",
    "rank",
    "confidence",
    "tags",
    "source_event_ids",
    "source_event_types",
)

CAPTURE_INBOX_CARD_OMITTED_FIELDS = (
    "acceptance",
    "authority",
    "closeout_assurance",
    "completion",
    "event_history",
    "execution_receipts",
    "impact",
    "integration_contract",
    "latest_execution_receipt",
    "notes",
    "problem",
    "projection_completeness",
    "provenance",
    "satisfaction_contract",
    "statement",
)


def _capture_inbox_raw_capture_ids(capture_triage: Mapping[str, Any]) -> set[str]:
    raw_ids: set[str] = set()
    for row in capture_triage.get("items") or []:
        if not isinstance(row, Mapping):
            continue
        if "raw_capture_inbox" not in (row.get("categories") or []):
            continue
        item_id = str(row.get("id") or "").strip()
        if item_id:
            raw_ids.add(item_id)
    return raw_ids


def _capture_inbox_card(item: Mapping[str, Any]) -> Dict[str, Any]:
    card = {
        field: item.get(field)
        for field in CAPTURE_INBOX_CARD_FIELDS
        if item.get(field) not in (None, "", [], {})
    }
    card["item_shape"] = "capture_inbox_card_v0"
    return card


def _build_capture_inbox_view(
    captures: List[Mapping[str, Any]],
    capture_triage: Mapping[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    rows = list(capture_triage.get("items") or [])
    status_counts = capture_triage.get("counts_by_status") or {}
    category_counts = capture_triage.get("category_counts") or _capture_triage_category_counts(rows)
    raw_capture_count = int(category_counts.get("raw_capture_inbox", 0) or 0)
    closed_count = int(status_counts.get("closed_or_signed_off", 0) or 0)
    raw_capture_ids = _capture_inbox_raw_capture_ids(capture_triage)
    items = [
        dict(item) if str(item.get("id") or "").strip() in raw_capture_ids else _capture_inbox_card(item)
        for item in captures
    ]
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_view_v1",
        "view_id": "capture_inbox",
        "generated_at": generated_at,
        "items": items,
        "count": len(captures),
        "count_semantics": "total_capture_log_including_closed_shaped_and_raw_rows",
        "projection_semantics": {
            "role": "low_friction_capture_log",
            "not_live_backlog_count": True,
            "active_pressure_source": "capture_triage.category_counts.raw_capture_inbox",
            "triage_source": "state/task_ledger/views/capture_triage.json",
        },
        "total_capture_count": len(captures),
        "raw_capture_inbox_count": raw_capture_count,
        "active_raw_capture_count": raw_capture_count,
        "closed_or_signed_off_count": closed_count,
        "items_compaction": {
            "profile": "raw_capture_full_else_card_v0",
            "full_item_count": sum(
                1 for item in captures if str(item.get("id") or "").strip() in raw_capture_ids
            ),
            "card_item_count": sum(
                1 for item in captures if str(item.get("id") or "").strip() not in raw_capture_ids
            ),
            "full_item_rule": "rows categorized as raw_capture_inbox stay full for active triage",
            "card_item_shape": "capture_inbox_card_v0",
            "card_fields": list(CAPTURE_INBOX_CARD_FIELDS),
            "card_omitted_fields": list(CAPTURE_INBOX_CARD_OMITTED_FIELDS),
            "authority_for_full_rows": str(LEDGER_REL),
            "triage_source": "state/task_ledger/views/capture_triage.json",
        },
    }


def _count_capture_triage_statuses(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get("triage_status") or "unknown")] += 1
    return dict(sorted(counts.items()))


def _capture_triage_category_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        for category in row.get("categories") or []:
            counts[str(category)] += 1
    return dict(sorted(counts.items()))


def _capture_triage_linkage_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    counts = {"prompt_trace_linked": 0, "work_ledger_linked": 0}
    for row in rows:
        linkage = row.get("linkage") if isinstance(row.get("linkage"), Mapping) else {}
        if linkage.get("prompt_trace_linked"):
            counts["prompt_trace_linked"] += 1
        if linkage.get("work_ledger_linked"):
            counts["work_ledger_linked"] += 1
    return counts


def _annotate_capture_triage_menu_membership(
    capture_triage: Mapping[str, Any],
    execution_menu: Mapping[str, Any],
    promotion_candidates: Mapping[str, Any],
) -> Dict[str, Any]:
    menu_ids = {
        str(row.get("id") or "")
        for row in execution_menu.get("items", [])
        if isinstance(row, Mapping)
    }
    candidate_ids = {
        str(row.get("id") or "")
        for row in promotion_candidates.get("items", [])
        if isinstance(row, Mapping)
    }
    rows: List[Dict[str, Any]] = []
    for raw in capture_triage.get("items", []):
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        categories = set(str(item) for item in row.get("categories") or [])
        in_menu = str(row.get("id") or "") in menu_ids
        in_candidates = str(row.get("id") or "") in candidate_ids
        row["in_execution_menu"] = in_menu
        row["in_promotion_candidates"] = in_candidates
        if in_menu:
            categories.add("execution_menu_candidate")
        elif in_candidates:
            categories.add("promotion_candidate")
        elif str(row.get("triage_status") or "") not in {"closed_or_signed_off", "blocked"}:
            categories.add("parked_not_next")
        row["categories"] = sorted(categories)
        rows.append(row)
    return {
        **dict(capture_triage),
        "items": rows,
        "counts_by_status": _count_capture_triage_statuses(rows),
        "category_counts": _capture_triage_category_counts(rows),
        "linkage_counts": _capture_triage_linkage_counts(rows),
        "execution_menu_count": len(menu_ids),
        "promotion_candidate_count": len(candidate_ids),
        "why_execution_menu_is_small": EXECUTION_MENU_RATIONALE,
    }


def _build_promotion_candidates_view(
    capture_triage: Mapping[str, Any],
    generated_at: str,
    *,
    execution_menu: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    execution_menu_ids = {
        str(row.get("id") or "").strip()
        for row in (execution_menu or {}).get("items", [])
        if isinstance(row, Mapping)
    }
    rows = [
        dict(row)
        for row in capture_triage.get("items", [])
        if isinstance(row, Mapping)
        and str(row.get("triage_status") or "") in {"shaped_ready", "shaped_needs_completion_contract"}
        and str(row.get("id") or "").strip() not in execution_menu_ids
    ]
    rows.sort(key=_execution_priority)
    candidates: List[Dict[str, Any]] = []
    for index, row in enumerate(rows[:EXECUTION_MENU_LIMIT], start=1):
        required_event = (
            "work_item.promoted"
            if row.get("triage_status") == "shaped_ready"
            else "work_item.shaped then work_item.promoted"
        )
        candidates.append(
            {
                **row,
                "candidate_rank": index,
                "required_next_event": required_event,
                "commitment_boundary": "candidate only; not an execution commitment until promoted, ranked, or claimed",
                "why_recommended": "open capture has enough shape for organizer review; promote explicitly before it becomes commitment",
                "why_this_next": [
                    f"triage_status:{row.get('triage_status')}",
                    f"candidate_work_item_type:{row.get('candidate_work_item_type') or 'unspecified'}",
                    "candidate only; not an execution commitment until promoted, ranked, or claimed",
                ],
                "selection_factors": {
                    "categories": list(row.get("categories") or []),
                    "missing_fields": list(row.get("missing_fields") or []),
                    "event_count": row.get("event_count"),
                },
                "mutation_rule": "append Task Ledger events; do not edit projection rows",
            }
        )
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_promotion_candidates_v1",
        "view_id": "promotion_candidates",
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "append Task Ledger events; this view is projection-only",
        },
        "items": candidates,
        "count": len(candidates),
        "why_these_next": [
            "captures are attention, not commitment",
            "promotion candidates are shaped enough to consider but still need explicit promote/rank/claim authority",
            f"the candidate list is capped at {EXECUTION_MENU_LIMIT} to keep organizer review bounded",
        ],
        "wip_policy": "do not implement directly from this view unless operator/controller override names the bypass",
        "selection_rule": {
            "limit": EXECUTION_MENU_LIMIT,
            "rank_order": [
                "priority title tokens",
                "triage_status",
                "candidate_work_item_type",
                "id",
            ],
            "predicate": "capture_triage rows with triage_status shaped_ready or shaped_needs_completion_contract",
        },
    }


def _execution_commitment_source(item: Mapping[str, Any]) -> str:
    event_types = _item_event_types(item)
    state = str(item.get("state") or item.get("status") or "").strip()
    if "work_item.promoted" in event_types:
        return "promoted"
    if "work_item.claimed" in event_types:
        return "claimed"
    if "work_item.state_transitioned" in event_types:
        if state in {"claimed", "active", "review"}:
            return "active_state"
        if state in {"ready", "accepted"}:
            return "ready_state"
        return "state_transitioned"
    if "work_item.rerank_committed" in event_types:
        return "explicit_rerank_commit"
    if "work_item.legacy_bootstrapped" in event_types and item.get("rank_history"):
        return "legacy_rank_only"
    if item.get("rank_history"):
        return "rank_history_without_commitment_event"
    return "unknown"


def _has_execution_commitment_event(item: Mapping[str, Any]) -> bool:
    source = _execution_commitment_source(item)
    return source in {
        "promoted",
        "claimed",
        "ready_state",
        "active_state",
        "state_transitioned",
        "explicit_rerank_commit",
    }


def _committed_menu_row(item: Mapping[str, Any], *, menu_rank: int) -> Dict[str, Any]:
    state = str(item.get("state") or item.get("status") or "").strip()
    commitment_source = _execution_commitment_source(item)
    if state in {"claimed", "active", "review"}:
        required_event = "work_item.state_transitioned or work_item.signoff_recorded"
    elif state == "captured":
        required_event = "work_item.promoted or work_item.claimed"
    else:
        required_event = "work_item.claimed or work_item.state_transitioned"
    return {
        "id": item.get("id"),
        "title": item.get("title"),
        "state": state,
        "work_item_type": item.get("work_item_type"),
        "candidate_work_item_type": item.get("candidate_work_item_type"),
        "rank": item.get("rank"),
        "rank_history": list(item.get("rank_history") or []),
        "owner": item.get("owner"),
        "menu_rank": menu_rank,
        "required_next_event": required_event,
        "commitment_status": "committed_or_promoted",
        "commitment_source": commitment_source,
        "why_recommended": "row has explicit promotion, rerank-commit, claim, or state-transition authority",
        "why_this_next": [
            f"state:{state}",
            f"rank:{item.get('rank') if item.get('rank') is not None else 'none'}",
            f"commitment_source:{commitment_source}",
            "explicit commitment event; not merely a shaped or legacy-ranked capture",
        ],
        "selection_factors": {
            "rank": item.get("rank"),
            "rank_history_count": len(item.get("rank_history") or []),
            "source_event_ids": list(item.get("source_event_ids") or []),
            "source_event_types": sorted(_item_event_types(item)),
        },
        "mutation_rule": "append Task Ledger events; do not edit projection rows",
        "source_event_ids": list(item.get("source_event_ids") or []),
        "source_event_types": sorted(_item_event_types(item)),
    }


def _build_execution_menu_view(work_items: Sequence[Mapping[str, Any]], generated_at: str) -> Dict[str, Any]:
    rows = [
        item
        for item in work_items
        if _has_execution_commitment_event(item)
        and not _is_closed_or_signed_off(item)
        and _item_state(item) not in {"blocked", "signoff"}
    ]
    rows.sort(key=_rank_key)
    menu = [_committed_menu_row(item, menu_rank=index) for index, item in enumerate(rows[:EXECUTION_MENU_LIMIT], start=1)]
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_execution_menu_v2",
        "view_id": "execution_menu",
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "append Task Ledger events; this view is projection-only",
        },
        "items": menu,
        "count": len(menu),
        "why_these_next": EXECUTION_MENU_RATIONALE,
        "wip_policy": "active implementation should come from this explicit-commitment queue; promotion candidates and legacy rank history are not commitment",
        "selection_rule": {
            "limit": EXECUTION_MENU_LIMIT,
            "rank_order": ["rank", "id"],
            "predicate": "WorkItems with work_item.promoted, work_item.claimed, work_item.state_transitioned, or work_item.rerank_committed evidence; legacy rank_history alone is excluded",
        },
    }


def _dependency_resolution_status(item: Mapping[str, Any], dep_id: str) -> str | None:
    resolutions = item.get("dependency_resolutions")
    if isinstance(resolutions, Mapping):
        value = resolutions.get(dep_id)
        if isinstance(value, Mapping):
            status = str(value.get("status") or "").strip()
            return status or None
        status = str(value or "").strip()
        return status or None
    if isinstance(resolutions, list):
        for value in resolutions:
            if not isinstance(value, Mapping):
                continue
            if str(value.get("id") or value.get("work_item_id") or value.get("dep_id") or "").strip() == dep_id:
                status = str(value.get("status") or "").strip()
                return status or None
    return None


def _dependency_is_satisfied(
    dependent: Mapping[str, Any],
    dependency: Mapping[str, Any],
    dep_id: str,
) -> tuple[bool, str]:
    resolution = _dependency_resolution_status(dependent, dep_id)
    if resolution in DEPENDENCY_RESOLUTION_SATISFIED_STATUSES:
        return True, f"dependency_resolution:{resolution}"
    state = _item_state(dependency)
    if state in DEPENDENCY_SATISFIED_STATES:
        return True, f"state:{state}"
    if dependency.get("sign_off_id"):
        return True, "signoff_recorded"
    if state == "retired":
        return False, "retired_requires_dependency_resolution"
    receipt_state = _latest_execution_receipt_state(dependency)
    if _is_terminal_execution_receipt_state(receipt_state):
        return True, f"execution_receipt:{receipt_state}"
    return False, f"state:{state or 'unknown'}"


def _dependency_anomaly(
    anomaly_type: str,
    item_id: str,
    *,
    dep_id: str | None = None,
    details: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    raw = "|".join([anomaly_type, item_id, dep_id or "", json.dumps(details or {}, sort_keys=True)])
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]
    return {
        "id": f"dep_anom_{digest}",
        "anomaly_type": anomaly_type,
        "work_item_id": item_id,
        "dependency_id": dep_id,
        "details": dict(details or {}),
    }


def _dependency_cycle_anomalies(graph: Mapping[str, Sequence[str]]) -> List[Dict[str, Any]]:
    visiting: list[str] = []
    visited: set[str] = set()
    anomalies: List[Dict[str, Any]] = []
    emitted: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            cycle = visiting[visiting.index(node):] + [node]
            key = "->".join(cycle)
            if key not in emitted:
                emitted.add(key)
                anomalies.append(
                    _dependency_anomaly(
                        "dependency_cycle",
                        node,
                        details={"cycle": cycle},
                    )
                )
            return
        if node in visited:
            return
        visiting.append(node)
        for dep in graph.get(node, []):
            if dep in graph:
                visit(dep)
        visiting.pop()
        visited.add(node)

    for node_id in sorted(graph):
        visit(node_id)
    return anomalies


def _build_dependency_views(
    work_items: Sequence[Mapping[str, Any]],
    execution_menu: Mapping[str, Any],
    generated_at: str,
) -> Dict[str, Dict[str, Any]]:
    by_id = {str(item.get("id") or ""): item for item in work_items if item.get("id")}
    id_counts: Dict[str, int] = defaultdict(int)
    for item in work_items:
        item_id = str(item.get("id") or "")
        if item_id:
            id_counts[item_id] += 1
    graph = {item_id: _coerce_id_list(item.get("depends_on")) for item_id, item in by_id.items()}
    downstream: Dict[str, List[str]] = defaultdict(list)
    for item_id, deps in graph.items():
        for dep_id in deps:
            downstream[dep_id].append(item_id)

    def edge_card(edge_id: str, *, relationship: str) -> Dict[str, Any]:
        target = by_id.get(edge_id) or {}
        return {
            "id": edge_id,
            "title": target.get("title"),
            "state": _item_state(target) if target else "missing",
            "rank": target.get("rank"),
            "relationship": relationship,
        }

    anomalies: List[Dict[str, Any]] = []
    statuses: Dict[str, Dict[str, Any]] = {}
    for item_id, item in by_id.items():
        hard_deps = graph.get(item_id, [])
        satisfied: List[str] = []
        unsatisfied: List[str] = []
        dangling: List[str] = []
        dep_states: List[Dict[str, Any]] = []
        anomaly_refs: List[str] = []
        if id_counts[item_id] > 1:
            anomaly = _dependency_anomaly(
                "duplicate_work_item_id",
                item_id,
                details={"count": id_counts[item_id]},
            )
            anomalies.append(anomaly)
            anomaly_refs.append(anomaly["id"])
        for dep_id in hard_deps:
            if dep_id == item_id:
                anomaly = _dependency_anomaly("dependency_self_loop", item_id, dep_id=dep_id)
                anomalies.append(anomaly)
                anomaly_refs.append(anomaly["id"])
                unsatisfied.append(dep_id)
                dep_states.append({"id": dep_id, "status": "self_loop", "satisfied": False})
                continue
            dependency = by_id.get(dep_id)
            if dependency is None:
                anomaly = _dependency_anomaly("dangling_dep_id", item_id, dep_id=dep_id)
                anomalies.append(anomaly)
                anomaly_refs.append(anomaly["id"])
                dangling.append(dep_id)
                unsatisfied.append(dep_id)
                dep_states.append(
                    {
                        **edge_card(dep_id, relationship="upstream_hard_dependency"),
                        "status": "dangling",
                        "satisfied": False,
                    }
                )
                continue
            is_satisfied, reason = _dependency_is_satisfied(item, dependency, dep_id)
            target = satisfied if is_satisfied else unsatisfied
            target.append(dep_id)
            dep_states.append(
                {
                    **edge_card(dep_id, relationship="upstream_hard_dependency"),
                    "sign_off_id": dependency.get("sign_off_id"),
                    "satisfied": is_satisfied,
                    "reason": reason,
                }
            )
        state = _item_state(item)
        schedulable = not unsatisfied and not dangling
        if state in {"ready", "accepted", "claimed", "active"} and unsatisfied:
            anomaly = _dependency_anomaly(
                f"{state}_with_incomplete_hard_deps",
                item_id,
                details={"unsatisfied_dep_ids": unsatisfied},
            )
            anomalies.append(anomaly)
            anomaly_refs.append(anomaly["id"])
        if state == "blocked" and hard_deps and not unsatisfied and not dangling:
            anomaly = _dependency_anomaly(
                "blocked_with_all_hard_deps_satisfied",
                item_id,
                details={"hard_dep_ids": hard_deps},
            )
            anomalies.append(anomaly)
            anomaly_refs.append(anomaly["id"])
        statuses[item_id] = {
            "schedulable": schedulable,
            "hard_dep_count": len(hard_deps),
            "satisfied_dep_ids": satisfied,
            "unsatisfied_dep_ids": unsatisfied,
            "dangling_dep_ids": dangling,
            "downstream_unlock_ids": sorted(downstream.get(item_id, []), key=lambda dep: _rank_key(by_id.get(dep, {}))),
            "anomaly_refs": list(dict.fromkeys(anomaly_refs)),
            "dependency_states": dep_states,
            "upstream_dependency_edges": dep_states,
            "downstream_unlock_edges": [],
        }
    cycle_anomalies = _dependency_cycle_anomalies(graph)
    anomalies.extend(cycle_anomalies)
    for anomaly in cycle_anomalies:
        cycle = anomaly.get("details", {}).get("cycle") if isinstance(anomaly.get("details"), Mapping) else []
        for item_id in cycle or []:
            if item_id in statuses:
                statuses[item_id].setdefault("anomaly_refs", []).append(anomaly["id"])
                statuses[item_id]["schedulable"] = False

    for item_id, status in statuses.items():
        unlock_edges: List[Dict[str, Any]] = []
        for downstream_id in status.get("downstream_unlock_ids") or []:
            downstream_status = statuses.get(downstream_id) or {}
            waiting_on_this = item_id in set(downstream_status.get("unsatisfied_dep_ids") or [])
            unlock_edges.append(
                {
                    **edge_card(downstream_id, relationship="downstream_unlock"),
                    "waiting_on_this": waiting_on_this,
                    "downstream_schedulable": downstream_status.get("schedulable"),
                    "downstream_unsatisfied_dep_ids": list(downstream_status.get("unsatisfied_dep_ids") or []),
                    "unlock_status": "waiting_on_this" if waiting_on_this else "not_blocked_by_this",
                }
            )
        status["downstream_unlock_edges"] = unlock_edges

    dependency_graph_rows = [
        {
            "id": item_id,
            "title": by_id[item_id].get("title"),
            "state": _item_state(by_id[item_id]),
            "rank": by_id[item_id].get("rank"),
            "depends_on": graph.get(item_id, []),
            "dependencies": _coerce_id_list(by_id[item_id].get("dependencies")),
            "dependency_status": statuses[item_id],
        }
        for item_id in sorted(by_id, key=lambda wid: _rank_key(by_id[wid]))
    ]
    ready_schedulable = [
        {**dict(item), "dependency_status": statuses.get(str(item.get("id") or ""), {})}
        for item in work_items
        if _item_state(item) in {"ready", "accepted"}
        and statuses.get(str(item.get("id") or ""), {}).get("schedulable") is True
    ]
    ready_schedulable.sort(key=_rank_key)
    execution_ids = [
        str(row.get("id") or "")
        for row in execution_menu.get("items", [])
        if isinstance(row, Mapping) and row.get("id")
    ]
    execution_schedulable = [
        {**dict(row), "dependency_status": statuses.get(str(row.get("id") or ""), {})}
        for row in execution_menu.get("items", [])
        if isinstance(row, Mapping)
        and statuses.get(str(row.get("id") or ""), {}).get("schedulable") is True
    ]
    blocked_pool_ids = {
        str(item.get("id") or "")
        for item in work_items
        if _item_state(item) in {"ready", "accepted", "claimed", "active", "review"}
    } | set(execution_ids)
    dependency_blocked = [
        {
            "id": item_id,
            "title": by_id[item_id].get("title"),
            "state": _item_state(by_id[item_id]),
            "rank": by_id[item_id].get("rank"),
            "dependency_status": statuses[item_id],
            "recommended_action": "complete, rewire, waive, or explicitly block dependency before scheduling",
        }
        for item_id in blocked_pool_ids
        if item_id in statuses
        and (
            statuses[item_id].get("unsatisfied_dep_ids")
            or statuses[item_id].get("dangling_dep_ids")
            or statuses[item_id].get("schedulable") is False
        )
    ]
    dependency_blocked.sort(key=lambda row: _rank_key(by_id.get(str(row.get("id") or ""), {})))
    unlocks_rows = [
        {
            "id": item_id,
            "title": by_id[item_id].get("title"),
            "state": _item_state(by_id[item_id]),
            "rank": by_id[item_id].get("rank"),
            "downstream_unlock_ids": statuses[item_id]["downstream_unlock_ids"],
            "downstream_unlock_edges": statuses[item_id]["downstream_unlock_edges"],
            "downstream_count": len(statuses[item_id]["downstream_unlock_ids"]),
        }
        for item_id in sorted(by_id, key=lambda wid: _rank_key(by_id[wid]))
        if statuses[item_id]["downstream_unlock_ids"]
    ]

    def view(view_id: str, schema_version: str, items: List[Mapping[str, Any]], *, extra: Mapping[str, Any] | None = None) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "kind": "task_ledger_view",
            "schema_version": schema_version,
            "view_id": view_id,
            "generated_at": generated_at,
            "authority": {
                "source": str(EVENTS_REL),
                "mutation_rule": "read-only dependency projection; append Task Ledger events to change edges",
            },
            "items": list(items),
            "count": len(items),
        }
        if extra:
            payload.update(dict(extra))
        return payload

    return {
        "dependency_graph": view(
            "dependency_graph",
            "task_ledger_dependency_graph_v1",
            dependency_graph_rows,
            extra={
                "edge_semantics": {
                    "depends_on": "hard internal WorkItem prerequisite edge",
                    "dependencies": "broad dependency/context field; not scheduler authority unless typed",
                    "retired_dependency_policy": "retired is not dependency-satisfied without explicit dependency_resolutions status",
                },
            },
        ),
        "schedulable_by_rank": view(
            "schedulable_by_rank",
            "task_ledger_schedulable_by_rank_v1",
            ready_schedulable,
            extra={"selection_rule": "ready/accepted WorkItems with satisfied hard depends_on, sorted by _rank_key"},
        ),
        "execution_menu_schedulable": view(
            "execution_menu_schedulable",
            "task_ledger_execution_menu_schedulable_v1",
            execution_schedulable,
            extra={"selection_rule": "execution_menu rows with satisfied hard depends_on, preserving commitment semantics"},
        ),
        "dependency_blocked": view(
            "dependency_blocked",
            "task_ledger_dependency_blocked_v1",
            dependency_blocked,
            extra={"selection_rule": "ready/accepted/execution-relevant rows blocked by unsatisfied or dangling hard deps"},
        ),
        "dependency_anomalies": view(
            "dependency_anomalies",
            "task_ledger_dependency_anomalies_v1",
            sorted(anomalies, key=lambda row: (str(row.get("anomaly_type") or ""), str(row.get("work_item_id") or ""), str(row.get("dependency_id") or ""))),
        ),
        "unlocks_by_rank": view(
            "unlocks_by_rank",
            "task_ledger_unlocks_by_rank_v1",
            unlocks_rows,
            extra={"selection_rule": "upstream WorkItems ordered by rank whose completion or resolution unlocks downstream WorkItems"},
        ),
    }


def _build_merge_or_retire_candidates_view(captures: List[Mapping[str, Any]], generated_at: str) -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = []
    closed_audit_rows: List[Dict[str, Any]] = []
    open_groups: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    open_items: List[Mapping[str, Any]] = []
    for item in captures:
        state = _item_state(item)
        if _is_closed_or_signed_off(item):
            closed_audit_rows.append(
                {
                    "kind": "already_closed_capture",
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "state": state,
                    "sign_off_id": item.get("sign_off_id"),
                    "disposition": "audit_only_terminal_row",
                    "evidence": {
                        "source_event_ids": list(item.get("source_event_ids") or []),
                    },
                }
            )
            continue
        key = "|".join(
            [
                _norm_text(item.get("title")),
                _norm_text(item.get("statement")),
                _norm_text(item.get("candidate_work_item_type")),
            ]
        )
        if key.strip("|"):
            open_groups[key].append(item)
            open_items.append(item)
    for group in open_groups.values():
        if len(group) < 2:
            continue
        candidates.append(
                {
                    "kind": "possible_duplicate_capture_group",
                    "item_ids": [item.get("id") for item in sorted(group, key=lambda item: str(item.get("id") or ""))],
                    "title": group[0].get("title"),
                    "candidate_work_item_type": group[0].get("candidate_work_item_type"),
                    "recommended_action": "append supported retire/note/propagate disposition; preserve all source histories",
                }
            )
    candidates.extend(_semantic_duplicate_groups(open_items))
    candidates.sort(key=lambda row: (str(row.get("kind") or ""), str(row.get("id") or row.get("item_ids") or "")))
    compaction_governance = _compaction_governance_packet()
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_merge_or_retire_candidates_v1",
        "view_id": "merge_or_retire_candidates",
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "append supported retire/note/propagate disposition events; do not delete history",
        },
        "compaction_governance": compaction_governance,
        "audit_only": {
            "already_closed_capture_count": len(closed_audit_rows),
            "sample_items": sorted(
                closed_audit_rows,
                key=lambda row: str(row.get("id") or ""),
            )[:8],
            "policy": "terminal captures are retained as audit facts and excluded from merge_or_retire candidate actions",
        },
        "items": candidates,
        "count": len(candidates),
    }


def _build_missing_contracts_ranked_view(work_items: List[Mapping[str, Any]], generated_at: str) -> Dict[str, Any]:
    rows: List[Dict[str, Any]] = []
    for item in work_items:
        if _is_closed_or_signed_off(item):
            continue
        missing = _missing_contract_fields(item)
        completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
        if not completeness.get("has_completion_contract") and str(item.get("work_item_type") or "") != "capture":
            missing.append("completion_contract")
        if not missing:
            continue
        rows.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "state": _item_state(item),
                "work_item_type": item.get("work_item_type"),
                "candidate_work_item_type": item.get("candidate_work_item_type"),
                "missing_fields": sorted(set(missing)),
                "recommended_action": "shape WorkItem contracts before implementation",
                "rank": item.get("rank"),
                "updated_at": item.get("updated_at"),
            }
        )
    rows.sort(key=lambda row: (len(row.get("missing_fields") or []), row.get("rank") is None, row.get("rank") or 999999, str(row.get("id") or "")))
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_missing_contracts_ranked_v1",
        "view_id": "missing_contracts_ranked",
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "append satisfaction/integration/shape events; do not edit projection rows",
        },
        "items": rows,
        "count": len(rows),
    }


MISSION_OPERATING_PICTURE_VIEW_ID = "mission_operating_picture"
MISSION_OPERATING_PICTURE_SCHEMA = "mission_operating_picture_v0"
MISSION_TRACE_ROLLUP_SCHEMA = "mission_trace_rollup_for_operating_picture_v0"
MISSION_TRACE_ROLLUP_ROW_SCHEMA = "mission_trace_rollup_for_operating_picture_row_v0"
MISSION_TRACE_ROLLUP_LIMIT = 12
MISSION_OPERATING_CANDIDATE_SOURCES = [
    "satisfaction_refs",
    "principle_refs",
    "axiom_refs",
    "raw_seed_refs",
    "operator_voice_refs",
    "meta_mission_active",
    "mission_blackboard",
]
MISSION_OPERATING_SOURCE_REFS = [
    str(LEDGER_REL),
    str(VIEWS_REL / "dependency_graph.json"),
    str(VIEWS_REL / "unlocks_by_rank.json"),
    str(VIEWS_REL / "meta_mission_active.json"),
    str(VIEWS_REL / "execution_menu_schedulable.json"),
    str(VIEWS_REL / "active_wip.json"),
    str(MISSION_BLACKBOARD_REL),
    str(PROMPT_LEDGER_MISSION_TRACE_CURRENT_STATE_REL),
]
CAP_CENSUS_VIEW_ID = "cap_census"
CAP_CENSUS_SCHEMA = "cap_census_v0"
CAP_CENSUS_SOURCE_REFS = [
    str(LEDGER_REL),
    str(SIGNOFFS_REL),
    str(VIEWS_REL / "active_wip.json"),
    str(VIEWS_REL / "bridge_assignable.json"),
    str(VIEWS_REL / "capture_inbox.json"),
    str(VIEWS_REL / "dependency_graph.json"),
    str(VIEWS_REL / "dependency_blocked.json"),
    str(VIEWS_REL / "execution_menu.json"),
    str(VIEWS_REL / "execution_menu_schedulable.json"),
    str(VIEWS_REL / "mission_operating_picture.json"),
    str(VIEWS_REL / "provider_assignable.json"),
    str(VIEWS_REL / "ready_by_rank.json"),
    str(VIEWS_REL / "signoffs.json"),
    str(VIEWS_REL / "unlocks_by_rank.json"),
]
CAP_CENSUS_STALE_WARNING_DAYS = 7
CAP_CENSUS_ACTIONABLE_LIFECYCLE_STATES = {
    "assigned",
    "claimable",
    "dependency_gated",
    "visible",
}
CAP_CARTOGRAPHY_VIEW_ID = "cap_cartography"
CAP_CARTOGRAPHY_SCHEMA = "cap_cartography_v0"
CAP_CARTOGRAPHY_SOURCE_REFS = list(
    dict.fromkeys(
        [
            str(VIEWS_REL / "cap_census.json"),
            str(VIEWS_REL / "mission_operating_picture.json"),
            *CAP_CENSUS_SOURCE_REFS,
        ]
    )
)
CAP_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT = 5
CAP_CARTOGRAPHY_VISIBLE_CAP_NODE_LIMIT = 96
CAP_CARTOGRAPHY_SUPPORT_NODE_LIMIT = 256
CAP_CARTOGRAPHY_EDGE_LIMIT = 512
CAP_CARTOGRAPHY_OMITTED_EDGE_SAMPLE_LIMIT = 12
CAP_CARTOGRAPHY_UNCLASSIFIED_SAMPLE_LIMIT = 10
CAP_EXECUTION_MARKET_VIEW_ID = "cap_execution_market"
CAP_EXECUTION_MARKET_SCHEMA = "cap_execution_market_v1"
CAP_EXECUTION_MARKET_QUEUES = (
    "must_reenter_now",
    "claimable_next",
    "dependency_gated",
    "historical_or_superseded",
)
CAP_EXECUTION_MARKET_SOURCE_REFS = list(
    dict.fromkeys(
        [
            str(VIEWS_REL / "cap_census.json"),
            str(VIEWS_REL / "cap_cartography.json"),
            *CAP_CENSUS_SOURCE_REFS,
        ]
    )
)

WORKITEM_CARTOGRAPHY_VIEW_ID = "workitem_cartography"
WORKITEM_CARTOGRAPHY_SCHEMA = "workitem_cartography_v1"
WORKITEM_CARTOGRAPHY_SOURCE_REFS = list(
    dict.fromkeys(
        [
            str(LEDGER_REL),
            str(VIEWS_REL / "dependency_graph.json"),
            str(VIEWS_REL / "unlocks_by_rank.json"),
            str(VIEWS_REL / "blocked.json"),
            str(VIEWS_REL / "needs_signoff.json"),
            str(VIEWS_REL / "stale_review.json"),
            str(VIEWS_REL / "capture_inbox.json"),
            str(VIEWS_REL / "missing_satisfaction_contract.json"),
            str(VIEWS_REL / "missing_integration_contract.json"),
            str(VIEWS_REL / "legacy_snapshot_unmodeled.json"),
            str(VIEWS_REL / "work_ledger_unlinked.json"),
            str(VIEWS_REL / "execution_menu.json"),
        ]
    )
)
WORKITEM_CARTOGRAPHY_VISIBLE_NODE_LIMIT = 200
WORKITEM_CARTOGRAPHY_EDGE_LIMIT = 1024
WORKITEM_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT = 8
WORKITEM_CARTOGRAPHY_OMITTED_EDGE_SAMPLE_LIMIT = 24
WORKITEM_CARTOGRAPHY_HIGH_UNLOCK_THRESHOLD = 5

# Wave 2A — route provenance taxonomy.
#
# Each unrouted WorkItem gets a typed `route_reason` derived from existing
# Task Ledger diagnostic views and `projection_completeness` flags. The
# vocabulary is anchored in `std_task_ledger.json` + `operational_work_item_spine.md`
# concepts (legacy_bootstrapped, terminal lifecycle, quick_capture, shaping
# pressure, integration/satisfaction contracts) — no new authority field on
# disk, only projection over existing substrate. Carryover semantics remain
# unsupported (origin/current scope fields do not exist on the ledger);
# every explanation carries `carryover_status="not_evaluated"`.
#
# Priority order is most-specific-first → least-specific → fallback. An
# item that overlaps multiple diagnostic-view memberships gets stamped with
# the first matching reason as primary; remaining matches are recorded in
# `secondary_reasons[]` so the consumer can offer them without rebuilding.
WORKITEM_ROUTE_REASON_PRIORITY: tuple[str, ...] = (
    "legacy_bootstrapped_no_execution_fields",
    "terminal_no_longer_routable",
    "needs_signoff_unrouted",
    "signoff_recorded_awaiting_propagation",
    "work_ledger_unlinked",
    "blocked_without_execution_profile",
    "quick_capture_unshaped",
    "missing_integration_contract",
    "missing_satisfaction_contract",
    "shaped_no_execution_commitment",
    "state_transitioned_no_execution_route",
)
WORKITEM_ROUTE_REASON_UNKNOWN = "unknown_reason"
WORKITEM_ROUTE_REASON_KINDS: Mapping[str, str] = {
    # Benign means "route absence is expected; no remediation owed by the operator."
    "terminal_no_longer_routable": "benign",
    # Anomaly means "the substrate shape is legitimately old / pre-modeled; absorb on schema migration."
    "legacy_bootstrapped_no_execution_fields": "anomaly",
    # Backlog means "expected inbox noise; remediation happens at triage cadence."
    "quick_capture_unshaped": "backlog",
    # Actionable means "operator/agent can usefully act on the missing route."
    "needs_signoff_unrouted": "actionable",
    "signoff_recorded_awaiting_propagation": "actionable",
    "work_ledger_unlinked": "actionable",
    "blocked_without_execution_profile": "actionable",
    "missing_integration_contract": "actionable",
    "missing_satisfaction_contract": "actionable",
    "shaped_no_execution_commitment": "actionable",
    "state_transitioned_no_execution_route": "actionable",
    WORKITEM_ROUTE_REASON_UNKNOWN: "actionable",
}
WORKITEM_ROUTE_REASON_LABELS: Mapping[str, str] = {
    "legacy_bootstrapped_no_execution_fields": "legacy bootstrapped · no execution fields",
    "terminal_no_longer_routable": "terminal · no longer routable",
    "needs_signoff_unrouted": "needs signoff · no execution route",
    "signoff_recorded_awaiting_propagation": "signoff recorded · awaiting propagation",
    "work_ledger_unlinked": "work ledger unlinked",
    "blocked_without_execution_profile": "blocked · no execution profile",
    "quick_capture_unshaped": "quick capture · unshaped",
    "missing_integration_contract": "missing integration contract",
    "missing_satisfaction_contract": "missing satisfaction contract",
    "shaped_no_execution_commitment": "shaped · no execution commitment event",
    "state_transitioned_no_execution_route": "state transitioned · no execution route",
    WORKITEM_ROUTE_REASON_UNKNOWN: "unrouted · reason unknown",
}
# Wave 2A.1 — predicate_kind clarifies whether a reason is backed by a
# diagnostic view, a ledger field, or a derived helper. The audit lane
# uses this to reconcile evidence_refs against the actual predicate.
WORKITEM_ROUTE_REASON_PREDICATE_KIND: Mapping[str, str] = {
    "legacy_bootstrapped_no_execution_fields": "projection_completeness_flag",
    "terminal_no_longer_routable": "ledger_state_field",
    "needs_signoff_unrouted": "projection_completeness_flag",
    "signoff_recorded_awaiting_propagation": "ledger_state_and_signoff_record_field",
    "work_ledger_unlinked": "ledger_state_and_completeness_flag",
    "blocked_without_execution_profile": "ledger_state_and_blocked_flag",
    "quick_capture_unshaped": "ledger_type_and_state_field",
    "missing_integration_contract": "projection_completeness_flag",
    "missing_satisfaction_contract": "projection_completeness_flag",
    "shaped_no_execution_commitment": "execution_commitment_helper",
    "state_transitioned_no_execution_route": "execution_commitment_helper_and_completeness",
    WORKITEM_ROUTE_REASON_UNKNOWN: "fallback_no_predicate_fired",
}
# Wave 2A.1 — typed evidence per reason. evidence_views are diagnostic-view
# memberships (membership claim must reconcile in the audit lane);
# evidence_fields are the substrate field paths that the predicate actually
# reads. Reasons that are purely ledger-derived list NO evidence_view; they
# list evidence_fields only. This closes the 2A defect where a ledger-state
# predicate claimed a diagnostic-view evidence ref.
WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS: Mapping[str, tuple[str, ...]] = {
    "legacy_bootstrapped_no_execution_fields": ("legacy_snapshot_unmodeled.json",),
    "needs_signoff_unrouted": ("needs_signoff.json",),
    "signoff_recorded_awaiting_propagation": ("signoffs.json",),
    "work_ledger_unlinked": ("work_ledger_unlinked.json",),
    # blocked_without_execution_profile is ledger-state derived; NO diagnostic
    # view evidence ref. The audit lane will refuse a diagnostic-view claim here.
    "quick_capture_unshaped": ("capture_inbox.json",),
    "missing_integration_contract": ("missing_integration_contract.json",),
    "missing_satisfaction_contract": ("missing_satisfaction_contract.json",),
    "shaped_no_execution_commitment": ("execution_menu.json",),
    # state_transitioned_no_execution_route relies on the execution_commitment
    # helper plus completeness flags; no single view captures it cleanly.
    # terminal_no_longer_routable is derived from state directly; no view.
    # unknown_reason has no evidence view.
}
WORKITEM_ROUTE_REASON_EVIDENCE_FIELDS: Mapping[str, tuple[str, ...]] = {
    "legacy_bootstrapped_no_execution_fields": (
        "ledger.work_items[].projection_completeness.legacy_snapshot_present",
    ),
    "terminal_no_longer_routable": (
        "ledger.work_items[].state",
        "ledger.work_items[].status",
    ),
    "needs_signoff_unrouted": (
        "ledger.work_items[].projection_completeness.needs_signoff",
    ),
    "signoff_recorded_awaiting_propagation": (
        "ledger.work_items[].state",
        "ledger.work_items[].sign_off_id",
        "ledger.work_items[].completion.signoff_recorded",
    ),
    "work_ledger_unlinked": (
        "ledger.work_items[].state",
        "ledger.work_items[].projection_completeness.has_work_ledger_claim_ref",
    ),
    "blocked_without_execution_profile": (
        "ledger.work_items[].state",
        "ledger.work_items[].blocked",
        "ledger.work_items[].execution",
    ),
    "quick_capture_unshaped": (
        "ledger.work_items[].work_item_type",
        "ledger.work_items[].state",
    ),
    "missing_integration_contract": (
        "ledger.work_items[].projection_completeness.has_integration_contract",
        "ledger.work_items[].projection_completeness.exact_surfaces_grounded",
    ),
    "missing_satisfaction_contract": (
        "ledger.work_items[].projection_completeness.has_satisfaction_contract",
    ),
    "shaped_no_execution_commitment": (
        "ledger.work_items[].projection_completeness.has_integration_contract",
        "ledger.work_items[].projection_completeness.has_satisfaction_contract",
        "ledger.work_items[].event_types (via _has_execution_commitment_event)",
    ),
    "state_transitioned_no_execution_route": (
        "ledger.work_items[].projection_completeness.has_integration_contract",
        "ledger.work_items[].projection_completeness.has_satisfaction_contract",
        "ledger.work_items[].event_types (via _has_execution_commitment_event)",
        "ledger.work_items[].execution",
    ),
}
# Wave 2C — bind the route_reason to its newly-built diagnostic view.
WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS = {
    **WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS,
    "state_transitioned_no_execution_route": (
        "state_transitioned_no_execution_route.json",
    ),
}
WORKITEM_ROUTE_REASON_TERMINAL_STATES: frozenset[str] = frozenset(
    {"done", "retired", "propagated", "completed"}
)
WORKITEM_ROUTE_REASON_ACTIVE_STATES: frozenset[str] = frozenset(
    {"claimed", "active", "review", "signoff"}
)
WORKITEM_ROUTE_REASON_CAPTURE_INBOX_STATES: frozenset[str] = frozenset(
    {"captured"}
)

# Wave 2B — route reason → remedy lane mapping. Maps every typed
# route_reason to the existing Task Ledger owner surface that already
# governs its next move. The vocabulary mirrors the SRE alert→runbook
# pattern and the ITIL known-error → workaround/resolution pattern: a
# labelled condition without a named next surface is incomplete.
#
# This is read-only. The UI exposes the affordance as a chip/link; the
# actual mutation lane is owned by `tools/meta/factory/task_ledger_apply.py`
# (or the equivalent governed apply tool per disposition). Frontend never
# becomes a mutation console — the chip routes to a Task Ledger card /
# diagnostic view, not to a "fix" button.
#
# resolution_disposition values are an enum to keep the consumer simple:
#   triage_or_shape         — capture sitting in the inbox
#   no_remediation          — benign terminal lifecycle
#   signoff                 — operator needs to sign off
#   schedule                — shaped row needs an execution commitment event
#   repair_route_metadata   — substrate gap: events fired but route fields never set
#   shape_contract          — integration/satisfaction contract missing
#   migrate                 — pre-Task-Ledger snapshot to absorb
#   inspect                 — blocked / unknown, operator review only
#
# resolution_status values:
#   available — owner_view exists, examples can be drilled, governed
#               apply lane is named
#   partial   — owner_view exists but does not yet model this reason as
#               its own row class
#   absent    — no owner_view exists yet (substrate gap)
#   benign    — no remediation needed by construction
# Wave 2D — lane_relationship taxonomy.
#
# Wave 2B/2C mapped every reason to an owner_view but used a single word
# ("lane") in the UI. That flattened four distinct relationships:
#   * exact_reason_view              — owner_view items == reason items (1:1)
#   * broad_owner_view_contains_reason_rows  — owner_view is a superset
#   * partial_owner_view_contains_some_reason_rows — some reason rows in owner_view, some not
#   * target_lane_not_current_member — owner_view is where the row goes
#                                       AFTER repair; no current members
#   * benign_no_remediation          — no owner_view; no action needed
#   * fallback_no_owner_view         — no owner_view registered yet
#
# The relationship is computed at projection-build time from the actual
# membership overlap between the reason-id set and the owner_view item
# id set. The UI consumes this typed value and chooses chip language
# accordingly ("view:" / "contains:" / "partial:" / "target:" / "benign:" /
# "no lane:") rather than implying current membership where the contract
# only names a target lane.
WORKITEM_ROUTE_LANE_RELATIONSHIP_EXACT = "exact_reason_view"
WORKITEM_ROUTE_LANE_RELATIONSHIP_BROAD = "broad_owner_view_contains_reason_rows"
WORKITEM_ROUTE_LANE_RELATIONSHIP_PARTIAL = (
    "partial_owner_view_contains_some_reason_rows"
)
WORKITEM_ROUTE_LANE_RELATIONSHIP_TARGET = "target_lane_not_current_member"
WORKITEM_ROUTE_LANE_RELATIONSHIP_BENIGN = "benign_no_remediation"
WORKITEM_ROUTE_LANE_RELATIONSHIP_FALLBACK = "fallback_no_owner_view"

WORKITEM_ROUTE_LANE_RELATIONSHIP_LABEL: Mapping[str, str] = {
    WORKITEM_ROUTE_LANE_RELATIONSHIP_EXACT: "view",
    WORKITEM_ROUTE_LANE_RELATIONSHIP_BROAD: "contains",
    WORKITEM_ROUTE_LANE_RELATIONSHIP_PARTIAL: "partial",
    WORKITEM_ROUTE_LANE_RELATIONSHIP_TARGET: "target",
    WORKITEM_ROUTE_LANE_RELATIONSHIP_BENIGN: "benign",
    WORKITEM_ROUTE_LANE_RELATIONSHIP_FALLBACK: "no lane",
}


def _classify_lane_relationship(
    *,
    reason: str,
    affordance: Mapping[str, Any],
    reason_ids: Set[str],
    owner_view_ids: Optional[Set[str]],
) -> str:
    """
    Wave 2D classifier. Compute the semantic relationship between the set
    of WorkItem ids whose primary route_reason is `reason` and the set of
    ids in the affordance's owner_view (if any). Never assume — always
    compute from actual membership.
    """
    if affordance.get("resolution_status") == "benign":
        return WORKITEM_ROUTE_LANE_RELATIONSHIP_BENIGN
    if not affordance.get("owner_view") or owner_view_ids is None:
        return WORKITEM_ROUTE_LANE_RELATIONSHIP_FALLBACK
    if not reason_ids:
        # Reason present in taxonomy but 0 rows in current substrate.
        return WORKITEM_ROUTE_LANE_RELATIONSHIP_FALLBACK
    overlap = reason_ids & owner_view_ids
    if overlap == reason_ids:
        # Every reason row appears in the owner view.
        if len(reason_ids) == len(owner_view_ids):
            return WORKITEM_ROUTE_LANE_RELATIONSHIP_EXACT  # 1:1
        return WORKITEM_ROUTE_LANE_RELATIONSHIP_BROAD  # owner is superset
    if overlap:
        return WORKITEM_ROUTE_LANE_RELATIONSHIP_PARTIAL
    return WORKITEM_ROUTE_LANE_RELATIONSHIP_TARGET


WORKITEM_ROUTE_RESOLUTION_AFFORDANCES: Mapping[str, Mapping[str, Any]] = {
    "legacy_bootstrapped_no_execution_fields": {
        "resolution_disposition": "migrate",
        "resolution_status": "available",
        "owner_view": "legacy_snapshot_unmodeled",
        "owner_view_path": "state/task_ledger/views/legacy_snapshot_unmodeled.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids legacy_snapshot_unmodeled"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "tools/meta/factory/task_ledger_apply.py — promote/absorb legacy "
            "snapshot into modeled WorkItem"
        ),
        "next_action_label": "absorb legacy snapshot into modeled WorkItem",
    },
    "terminal_no_longer_routable": {
        "resolution_disposition": "no_remediation",
        "resolution_status": "benign",
        "owner_view": None,
        "owner_view_path": None,
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "no_mutation_needed",
        "mutation_lane_hint": None,
        "next_action_label": "no action needed · terminal lifecycle",
    },
    "needs_signoff_unrouted": {
        "resolution_disposition": "signoff",
        "resolution_status": "available",
        "owner_view": "needs_signoff",
        "owner_view_path": "state/task_ledger/views/needs_signoff.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids needs_signoff"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_signoff_lane",
        "mutation_lane_hint": (
            "tools/meta/factory/task_ledger_apply.py signoff — record "
            "work_item.signoff_recorded event"
        ),
        "next_action_label": "record signoff to close work item",
    },
    "signoff_recorded_awaiting_propagation": {
        # Wave 2E — signoff has been RECORDED (sign_off_id populated) but
        # the row is still in state=signoff. The natural next move is a
        # work_item.state_transitioned event to propagated/done. Owner
        # view is the canonical `signoffs.json` catalog (work_item_id
        # field; overlap with this reason is 100% by construction →
        # lane_relationship will be exact_reason_view).
        "resolution_disposition": "propagate",
        "resolution_status": "available",
        "owner_view": "signoffs",
        "owner_view_path": "state/task_ledger/views/signoffs.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids signoffs"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Fire work_item.state_transitioned (signoff → propagated/done) "
            "via tools/meta/factory/task_ledger_apply.py — the signoff "
            "record is already on disk under sign_off_id."
        ),
        "next_action_label": "transition signoff → propagated",
    },
    "work_ledger_unlinked": {
        "resolution_disposition": "link",
        "resolution_status": "available",
        "owner_view": "work_ledger_unlinked",
        "owner_view_path": "state/task_ledger/views/work_ledger_unlinked.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids work_ledger_unlinked"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Work Ledger linkage — bind the WorkItem to its claim ref / "
            "work_ledger row"
        ),
        "next_action_label": "link to Work Ledger claim or close",
    },
    "blocked_without_execution_profile": {
        "resolution_disposition": "inspect",
        "resolution_status": "available",
        "owner_view": "blocked",
        "owner_view_path": "state/task_ledger/views/blocked.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids blocked"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Review unblock condition + add execution profile when unblocked. "
            "NOTE: predicate is ledger-state, not dependency_blocked.json "
            "membership; do not route here as dependency-blocked unless the "
            "row is actually in that view."
        ),
        "next_action_label": "inspect blocker · add execution profile when ready",
    },
    "quick_capture_unshaped": {
        "resolution_disposition": "triage_or_shape",
        "resolution_status": "available",
        "owner_view": "capture_triage",
        "owner_view_path": "state/task_ledger/views/capture_triage.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids capture_triage"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_triage_lane",
        "mutation_lane_hint": (
            "tools/meta/factory/task_ledger_apply.py — promote / shape / "
            "retire from capture inbox via triage events"
        ),
        "next_action_label": "triage capture · promote / shape / retire",
    },
    "missing_integration_contract": {
        "resolution_disposition": "shape_contract",
        "resolution_status": "available",
        "owner_view": "missing_integration_contract",
        "owner_view_path": "state/task_ledger/views/missing_integration_contract.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids missing_integration_contract"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Author integration_contract.candidate_surfaces + "
            "exact_surfaces_discovered before scheduling"
        ),
        "next_action_label": "shape integration contract · exact surfaces",
    },
    "missing_satisfaction_contract": {
        "resolution_disposition": "shape_contract",
        "resolution_status": "available",
        "owner_view": "missing_satisfaction_contract",
        "owner_view_path": "state/task_ledger/views/missing_satisfaction_contract.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids missing_satisfaction_contract"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Author satisfaction_contract.named_invariants before promotion"
        ),
        "next_action_label": "shape satisfaction contract",
    },
    "shaped_no_execution_commitment": {
        "resolution_disposition": "schedule",
        "resolution_status": "available",
        "owner_view": "execution_menu",
        "owner_view_path": "state/task_ledger/views/execution_menu.json",
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids execution_menu"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Fire work_item.promoted / work_item.claimed / "
            "work_item.rerank_committed to enter execution menu"
        ),
        "next_action_label": "promote into execution menu",
    },
    "state_transitioned_no_execution_route": {
        # Wave 2C — the substrate gap surfaced by Wave 2B now has its own
        # diagnostic view (`state_transitioned_no_execution_route.json`).
        # Rows include commitment_source + missing_execution_fields +
        # recommended_action so an operator can act without re-deriving
        # the predicate.
        "resolution_disposition": "repair_route_metadata",
        "resolution_status": "available",
        "owner_view": "state_transitioned_no_execution_route",
        "owner_view_path": (
            "state/task_ledger/views/state_transitioned_no_execution_route.json"
        ),
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band cluster_flag --ids state_transitioned_no_execution_route"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "governed_apply_lane",
        "mutation_lane_hint": (
            "Repair lane: stamp execution.phase_id / source_queue / "
            "queue_sequence / queue_bucket / route via a rerank-commit or "
            "promotion event. Each row in the diagnostic view carries the "
            "commitment_source + the specific missing execution fields."
        ),
        "next_action_label": "stamp execution route metadata",
    },
    WORKITEM_ROUTE_REASON_UNKNOWN: {
        "resolution_disposition": "inspect",
        "resolution_status": "absent",
        "owner_view": None,
        "owner_view_path": None,
        "option_surface_ref": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "card_route_template": (
            "./repo-python kernel.py --option-surface task_ledger "
            "--band card --ids {id}"
        ),
        "mutation_policy": "observe_only_in_ui",
        "mutation_lane_hint": (
            "No predicate fired — inspect manually and consider opening a "
            "WorkItem to extend the taxonomy"
        ),
        "next_action_label": "inspect · taxonomy gap",
    },
}


def _mission_operating_item_id(item: Mapping[str, Any]) -> str:
    return str(item.get("id") or item.get("subject_id") or "").strip()


def _mission_operating_label(item: Mapping[str, Any]) -> str:
    return str(item.get("title") or item.get("label") or item.get("id") or "Untitled").strip()


def _mission_operating_source_refs(item: Mapping[str, Any], source_view: str | None = None) -> List[str]:
    refs = [str(ref) for ref in item.get("source_refs") or [] if ref]
    refs.extend(str(ref) for ref in item.get("source_event_ids") or [] if ref)
    if source_view:
        refs.append(str(VIEWS_REL / f"{source_view}.json"))
    return list(dict.fromkeys(refs))


def _mission_operating_satisfaction_contract(item: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = item.get("satisfaction_contract")
    if isinstance(contract, Mapping):
        return contract
    contracts = item.get("contracts")
    if isinstance(contracts, Mapping):
        return contracts
    return {}


def _mission_operating_imagined_state_refs(item: Mapping[str, Any]) -> List[str]:
    contract = _mission_operating_satisfaction_contract(item)
    return _coerce_id_list(contract.get("imagined_state_refs"))


def _mission_operating_exact_surfaces(item: Mapping[str, Any]) -> List[Dict[str, Any]]:
    contract = item.get("integration_contract")
    if not isinstance(contract, Mapping):
        contracts = item.get("contracts")
        contract = contracts if isinstance(contracts, Mapping) else {}
    surfaces = contract.get("exact_surfaces_discovered") if isinstance(contract, Mapping) else []
    if not isinstance(surfaces, Sequence) or isinstance(surfaces, (str, bytes)):
        return []
    rows: List[Dict[str, Any]] = []
    for surface in surfaces:
        if isinstance(surface, Mapping):
            path = str(surface.get("path") or "").strip()
            if path:
                rows.append({"path": path, "status": surface.get("status"), "role": surface.get("role")})
        else:
            path = str(surface or "").strip()
            if path:
                rows.append({"path": path})
    return rows


def _mission_trace_rollup_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    identity_kind = str(row.get("identity_kind") or "").strip()
    identity_value = str(row.get("identity_value") or "").strip()
    compact: Dict[str, Any] = {
        "schema": MISSION_TRACE_ROLLUP_ROW_SCHEMA,
        "authority_boundary": "derived_overlay_not_safety_authority",
        "matched_by": identity_kind or "trace_id",
        "mission_context_status": row.get("mission_context_status"),
        "identity_kind": identity_kind or None,
        "identity_value": identity_value or None,
        "mission_id": row.get("mission_id"),
        "subject_id": row.get("subject_id"),
        "fallback_subject": row.get("fallback_subject"),
        "trace_id": row.get("trace_id"),
        "event_id": row.get("event_id"),
        "last_event_at": row.get("last_event_at"),
        "last_surface": row.get("last_surface"),
        "last_actor_class": row.get("last_actor_class"),
        "last_step_id": row.get("last_step_id"),
        "parent_step_id": row.get("parent_step_id"),
        "last_prompt_refs": row.get("last_prompt_refs"),
        "last_lane": row.get("last_lane"),
        "last_cluster_id": row.get("last_cluster_id"),
        "last_decision_state": row.get("last_decision_state"),
        "last_reason": row.get("last_reason"),
        "current_blocker": row.get("current_blocker"),
        "current_receipt_ref": row.get("current_receipt_ref"),
        "receipt_refs": row.get("receipt_refs"),
        "commit_refs": row.get("commit_refs"),
        "affected_paths": row.get("affected_paths"),
        "next_safe_action": row.get("next_safe_action"),
        "plan_id": row.get("plan_id"),
        "action_id": row.get("action_id"),
    }
    return {key: value for key, value in compact.items() if value not in (None, [], {})}


def _mission_trace_rollup_for_operating_picture(repo_root: Optional[Path]) -> Dict[str, Any]:
    source_projection = str(PROMPT_LEDGER_MISSION_TRACE_CURRENT_STATE_REL)
    base: Dict[str, Any] = {
        "schema": MISSION_TRACE_ROLLUP_SCHEMA,
        "authority_boundary": "derived_overlay_not_safety_authority",
        "source_projection": source_projection,
        "source_authority": "state/prompt_ledger/events.jsonl",
        "projection_only": True,
        "safety_authority": False,
        "matched_by": "identity_kind",
        "status": "missing",
        "row_count": 0,
        "visible_row_limit": MISSION_TRACE_ROLLUP_LIMIT,
        "rows": [],
    }
    if repo_root is None:
        return {
            **base,
            "reason": "repo_root_unavailable",
            "next_step": "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        }

    payload = _safe_read_json(repo_root / PROMPT_LEDGER_MISSION_TRACE_CURRENT_STATE_REL)
    if not payload:
        return {
            **base,
            "reason": "source_projection_missing_or_unreadable",
            "next_step": "./repo-python tools/meta/observability/prompt_ledger.py rebuild",
        }
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, Sequence) or isinstance(raw_rows, (str, bytes)):
        return {
            **base,
            "reason": "source_projection_rows_missing",
            "next_step": "./repo-python tools/meta/observability/prompt_ledger.py rebuild --check",
        }

    rows = [_mission_trace_rollup_row(row) for row in raw_rows if isinstance(row, Mapping)]
    rows = sorted(
        rows,
        key=lambda row: (str(row.get("last_event_at") or ""), str(row.get("event_id") or "")),
        reverse=True,
    )
    visible_rows = rows[:MISSION_TRACE_ROLLUP_LIMIT]
    status = "available" if rows else "unmatched"
    rollup = {
        **base,
        "status": status,
        "source_projection_schema": payload.get("schema_version"),
        "source_projection_count": payload.get("count"),
        "source_summary": payload.get("summary") if isinstance(payload.get("summary"), Mapping) else {},
        "row_count": len(rows),
        "omitted_row_count": max(0, len(rows) - len(visible_rows)),
        "rows": visible_rows,
    }
    if visible_rows:
        rollup["latest_row"] = visible_rows[0]
        rollup["current_receipt_ref"] = visible_rows[0].get("current_receipt_ref")
        rollup["next_safe_action"] = visible_rows[0].get("next_safe_action")
    return rollup


def _mission_operating_meta_bucket(item: Mapping[str, Any]) -> tuple[str, str]:
    item_id = _mission_operating_item_id(item)
    title = _mission_operating_label(item).lower()
    work_item_type = str(item.get("work_item_type") or "").strip()
    candidate_type = str(item.get("candidate_work_item_type") or "").strip()
    if item_id == "cap_019" or "meta-missions as workitem lane" in title:
        return (
            "anchor_or_registry_row",
            "meta_mission_active row defines the mission WorkItem lane rather than a foreground campaign.",
        )
    if work_item_type == "meta_mission":
        return (
            "foreground_mission",
            "typed meta_mission row in meta_mission_active.",
        )
    if candidate_type == "meta_mission":
        return (
            "candidate_meta_mission_capture",
            "capture is tagged as a candidate meta_mission but is not yet a typed foreground mission.",
        )
    return (
        "foreground_mission",
        "row appears in meta_mission_active.",
    )


def _mission_operating_node_kind(item: Mapping[str, Any]) -> str:
    return "meta_mission" if str(item.get("work_item_type") or "") == "meta_mission" else "work_item"


def _cap_census_item_id(item: Mapping[str, Any]) -> str:
    return str(item.get("id") or item.get("work_item_id") or item.get("subject_id") or "").strip()


def _cap_census_text(item: Mapping[str, Any]) -> str:
    parts = [
        item.get("id"),
        item.get("title"),
        item.get("statement"),
        item.get("work_item_type"),
        item.get("candidate_work_item_type"),
        " ".join(str(tag) for tag in (item.get("tags") or [])),
    ]
    return " ".join(str(part or "") for part in parts).lower()


def _cap_census_namespace_kind(item: Mapping[str, Any]) -> str | None:
    item_id = _cap_census_item_id(item)
    work_item_type = str(item.get("work_item_type") or "").lower()
    candidate_type = str(item.get("candidate_work_item_type") or "").lower()
    tag_text = " ".join(str(tag or "").lower() for tag in (item.get("tags") or []))
    if work_item_type == "cap":
        return "typed_cap"
    if item_id.startswith("cap_"):
        return "cap_prefixed"
    if "cap" in candidate_type or "capability" in candidate_type or "cap" in tag_text or "capability" in tag_text:
        return "cap_like_nonprefixed"
    return None


def _cap_census_nested_nonempty(value: Any, names: set[str]) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in names and bool(nested):
                return True
            if _cap_census_nested_nonempty(nested, names):
                return True
    elif isinstance(value, list):
        return any(_cap_census_nested_nonempty(nested, names) for nested in value)
    return False


def _cap_census_has_umbrella_refs(item: Mapping[str, Any]) -> bool:
    satisfaction = item.get("satisfaction_contract") if isinstance(item.get("satisfaction_contract"), Mapping) else {}
    return _cap_census_nested_nonempty(
        satisfaction,
        {"imagined_state_refs", "umbrella_refs", "north_star_refs", "teleology_refs"},
    )


def _cap_census_has_proof_refs(item: Mapping[str, Any], signoff_work_item_ids: set[str]) -> bool:
    item_id = _cap_census_item_id(item)
    return bool(
        item.get("sign_off_id")
        or item_id in signoff_work_item_ids
        or item.get("receipt_refs")
        or item.get("commit_refs")
        or item.get("execution_receipts")
        or _cap_census_nested_nonempty(item.get("completion") or {}, {"proof_refs", "evidence_refs", "receipt_refs"})
    )


def _cap_census_has_integration_contract(item: Mapping[str, Any]) -> bool:
    integration = item.get("integration_contract")
    return isinstance(integration, Mapping) and any(bool(value) for value in integration.values())


def _cap_census_has_grounded_integration(item: Mapping[str, Any]) -> bool:
    completeness = item.get("projection_completeness") if isinstance(item.get("projection_completeness"), Mapping) else {}
    return bool(completeness.get("exact_surfaces_grounded"))


def _cap_census_done_or_signoff(item: Mapping[str, Any], signoff_work_item_ids: set[str]) -> bool:
    return (
        _item_state(item) in {"done", "signoff", "completed", "propagated"}
        or bool(item.get("sign_off_id"))
        or _has_terminal_execution_receipt(item)
        or _cap_census_item_id(item) in signoff_work_item_ids
    )


def _cap_census_collect_work_item_ids(value: Any, known_ids: set[str]) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in {"id", "work_item_id", "subject_id", "source", "target"} and isinstance(nested, str) and nested in known_ids:
                found.add(nested)
            else:
                found.update(_cap_census_collect_work_item_ids(nested, known_ids))
    elif isinstance(value, list):
        for nested in value:
            found.update(_cap_census_collect_work_item_ids(nested, known_ids))
    return found


def _cap_census_view_memberships(
    views: Mapping[str, Mapping[str, Any]],
    *,
    known_ids: set[str],
) -> Dict[str, set[str]]:
    memberships: Dict[str, set[str]] = {}
    for view_id, payload in views.items():
        source_rows = payload.get("items")
        if not isinstance(source_rows, list):
            source_rows = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        memberships[view_id] = _cap_census_collect_work_item_ids(source_rows, known_ids)
    return memberships


def _cap_census_semantic_role(item: Mapping[str, Any]) -> tuple[str, List[str]]:
    text = _cap_census_text(item)
    if str(item.get("work_item_type") or "") == "meta_mission" or "meta_mission" in text:
        return "mission", ["work_item_type_or_token:meta_mission"]
    if str(item.get("work_item_type") or "") == "closeout_residual" or "residual" in text:
        return "residual", ["work_item_type_or_token:residual"]
    if re.search(r"proof|evidence|receipt|signoff|montage|demo|portfolio|microcosm", text):
        return "evidence", ["proof_or_evidence_token"]
    if re.search(
        r"frontend|station|ui|dashboard|cockpit|route|graph|view|component|runtime|"
        r"kernel|adapter|tool|test|api|server|builder|projection|navigation|atlas|"
        r"hologram|ledger|workflow|bridge|provider|control",
        text,
    ):
        return "infrastructure", ["infrastructure_or_tooling_token"]
    if re.search(r"dissemination|launch|mission|wave|rollout", text):
        return "mission", ["mission_or_wave_token"]
    if "capability" in text or "capabilities" in text:
        return "capability", ["capability_token"]
    if re.search(r"north.?star|umbrella|teleolog|imagined_state", text):
        return "north_star", ["north_star_or_umbrella_token"]
    if _item_state(item) == "captured":
        return "unknown", ["captured_without_stronger_deterministic_role_token"]
    return "pipeline_item", ["fallback_operational_item"]


def _cap_census_temporal_role(
    item: Mapping[str, Any],
    *,
    signoff_work_item_ids: set[str],
    view_memberships: Mapping[str, set[str]],
) -> str:
    item_id = _cap_census_item_id(item)
    state = _item_state(item)
    if state == "blocked":
        return "blocked_future"
    if state == "retired":
        return "past_retired"
    if _cap_census_done_or_signoff(item, signoff_work_item_ids):
        return "past_proven"
    active_views = {
        "mission_operating_picture",
        "execution_menu",
        "execution_menu_schedulable",
        "active_wip",
        "meta_mission_active",
        "metabolic_running",
    }
    if state in {"execution", "shaping", "shaped", "claimed", "active"} or any(
        item_id in view_memberships.get(view_id, set()) for view_id in active_views
    ):
        return "active_conversion"
    return "future_open"


def _cap_census_parse_datetime(value: Any) -> datetime | None:
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


def _cap_census_dependency_refs(item: Mapping[str, Any]) -> List[str]:
    refs = set(_coerce_id_list(item.get("depends_on")))
    dependency_status = item.get("dependency_status")
    if isinstance(dependency_status, Mapping):
        refs.update(_coerce_id_list(dependency_status.get("blocked_dependency_ids")))
        refs.update(_coerce_id_list(dependency_status.get("unsatisfied_dependency_ids")))
        for edge in dependency_status.get("upstream_dependency_edges") or []:
            if isinstance(edge, Mapping):
                dep_id = str(edge.get("dependency_id") or edge.get("id") or "").strip()
                if dep_id:
                    refs.add(dep_id)
    return sorted(refs)


def _cap_census_owner_lane(item: Mapping[str, Any]) -> str:
    for key in ("owner_lane", "owner", "assignee", "actor", "created_by", "last_actor"):
        value = str(item.get(key) or "").strip()
        if value:
            return value
    execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    for key in ("owner_lane", "owner", "provider"):
        value = str(execution.get(key) or "").strip()
        if value:
            return value
    return "task_ledger"


def _cap_census_blocker_class(item: Mapping[str, Any]) -> str:
    text = _cap_census_text(item)
    if re.search(r"projection|generated|sidecar|refresh|drift|stale", text):
        return "projection_refresh"
    if re.search(r"closeout|commit|landing|landable|publication|push|finalizer", text):
        return "closeout_or_landing"
    if re.search(r"claim|owner|session|thread|concurrent|sibling|work ledger", text):
        return "claim_or_owner_coordination"
    if re.search(r"validation|test|ci|failure|red|gate", text):
        return "validation"
    if re.search(r"route|cli|discoverability|hud|trace", text):
        return "route_or_visibility"
    return "general_cap"


def _cap_census_actionable_lifecycle(
    item: Mapping[str, Any],
    *,
    temporal_role: str,
    done_or_signoff: bool,
    view_memberships: Mapping[str, set[str]],
) -> tuple[str, List[str]]:
    item_id = _cap_census_item_id(item)
    state = _item_state(item)
    if state == "retired":
        return "retired", ["state:retired"]
    if state == "superseded" or item.get("superseded_by"):
        return "superseded", ["state_or_field:superseded"]
    if done_or_signoff:
        return "retired", ["terminal_evidence:done_or_signoff"]

    if state == "blocked" or item_id in view_memberships.get("dependency_blocked", set()):
        return "dependency_gated", ["state_or_view:blocked_or_dependency_blocked"]
    if temporal_role == "active_conversion":
        return "assigned", ["temporal_role:active_conversion"]

    claimable_views = {
        "ready_by_rank",
        "execution_menu",
        "execution_menu_schedulable",
        "bridge_assignable",
        "provider_assignable",
        "unlocks_by_rank",
    }
    if any(item_id in view_memberships.get(view_id, set()) for view_id in claimable_views):
        return "claimable", ["view_membership:claimable_execution_queue"]
    if state in {"ready", "accepted", "shaped"}:
        return "claimable", [f"state:{state}"]
    if state == "captured" or item_id in view_memberships.get("capture_inbox", set()):
        return "visible", ["state_or_view:captured_or_capture_inbox"]
    return "visible", ["default_visible_cap"]


def _cap_census_age_days(item: Mapping[str, Any], generated_at: str) -> int | None:
    observed = _cap_census_parse_datetime(generated_at)
    started = _cap_census_parse_datetime(item.get("updated_at") or item.get("last_event_at") or item.get("created_at"))
    if observed is None or started is None:
        return None
    return max(0, int((observed - started).total_seconds() // 86400))


def _build_cap_census_view(
    *,
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
    views: Mapping[str, Mapping[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    by_id = {_cap_census_item_id(item): item for item in work_items if _cap_census_item_id(item)}
    known_ids = set(by_id)
    signoff_work_item_ids = {
        str(signoff.get("work_item_id") or "").strip()
        for signoff in signoffs
        if str(signoff.get("work_item_id") or "").strip()
    }
    view_memberships = _cap_census_view_memberships(views, known_ids=known_ids)
    mission_operating_picture = views.get(MISSION_OPERATING_PICTURE_VIEW_ID, {})
    mission_graph_ids = _cap_census_collect_work_item_ids(mission_operating_picture.get("nodes") or [], known_ids)

    rows: List[Dict[str, Any]] = []
    type_counts: Counter[str] = Counter()
    candidate_type_counts: Counter[str] = Counter()
    state_counts: Counter[str] = Counter()
    namespace_kind_counts: Counter[str] = Counter()
    temporal_counts: Counter[str] = Counter()
    semantic_counts: Counter[str] = Counter()
    view_membership_counts: Counter[str] = Counter()
    lifecycle_counts: Counter[str] = Counter()
    blocker_class_counts: Counter[str] = Counter()

    cap_prefixed_count = 0
    typed_cap_count = 0
    cap_like_nonprefixed_count = 0
    done_or_signoff_count = 0
    captured_count = 0
    active_or_execution_count = 0
    blocked_count = 0
    retired_count = 0
    umbrella_linked_count = 0
    proof_backed_count = 0
    integration_contract_count = 0
    integration_grounded_count = 0
    unclassified_count = 0
    actionable_lifecycle_count = 0
    stale_actionable_count = 0
    missing_reentry_count = 0

    for item in sorted(work_items, key=lambda row: str(row.get("id") or "")):
        item_id = _cap_census_item_id(item)
        namespace_kind = _cap_census_namespace_kind(item)
        if not item_id or namespace_kind is None:
            continue

        is_prefixed = item_id.startswith("cap_")
        is_typed_cap = str(item.get("work_item_type") or "") == "cap"
        cap_prefixed_count += int(is_prefixed)
        typed_cap_count += int(is_typed_cap)
        cap_like_nonprefixed_count += int(namespace_kind == "cap_like_nonprefixed")

        state = _item_state(item)
        work_item_type = str(item.get("work_item_type") or "<missing>")
        candidate_type = str(item.get("candidate_work_item_type") or "<missing>")
        type_counts[work_item_type] += 1
        candidate_type_counts[candidate_type] += 1
        state_counts[state or "<missing>"] += 1
        namespace_kind_counts[namespace_kind] += 1

        item_views = sorted(view_id for view_id, member_ids in view_memberships.items() if item_id in member_ids)
        for view_id in item_views:
            view_membership_counts[view_id] += 1

        temporal_role = _cap_census_temporal_role(
            item,
            signoff_work_item_ids=signoff_work_item_ids,
            view_memberships=view_memberships,
        )
        semantic_role, basis = _cap_census_semantic_role(item)
        temporal_counts[temporal_role] += 1
        semantic_counts[semantic_role] += 1
        unclassified_count += int(semantic_role == "unknown")

        has_umbrella_refs = _cap_census_has_umbrella_refs(item)
        has_proof_refs = _cap_census_has_proof_refs(item, signoff_work_item_ids)
        has_integration_contract = _cap_census_has_integration_contract(item)
        has_grounded_integration = _cap_census_has_grounded_integration(item)
        done_or_signoff = _cap_census_done_or_signoff(item, signoff_work_item_ids)
        actionable_lifecycle_state, lifecycle_basis = _cap_census_actionable_lifecycle(
            item,
            temporal_role=temporal_role,
            done_or_signoff=done_or_signoff,
            view_memberships=view_memberships,
        )
        dependency_refs = _cap_census_dependency_refs(item)
        blocker_class = _cap_census_blocker_class(item)
        owner_lane = _cap_census_owner_lane(item)
        reentry_route = (
            "./repo-python kernel.py --option-surface task_ledger --band card --ids "
            f"{item_id}"
        )
        retirement_evidence_required = actionable_lifecycle_state in CAP_CENSUS_ACTIONABLE_LIFECYCLE_STATES
        stale_age_days = _cap_census_age_days(item, generated_at)
        stale_age_warning = bool(
            retirement_evidence_required
            and stale_age_days is not None
            and stale_age_days >= CAP_CENSUS_STALE_WARNING_DAYS
        )

        done_or_signoff_count += int(done_or_signoff)
        captured_count += int(state == "captured")
        active_or_execution_count += int(temporal_role == "active_conversion")
        blocked_count += int(state == "blocked")
        retired_count += int(state == "retired")
        umbrella_linked_count += int(has_umbrella_refs)
        proof_backed_count += int(has_proof_refs)
        integration_contract_count += int(has_integration_contract)
        integration_grounded_count += int(has_grounded_integration)
        lifecycle_counts[actionable_lifecycle_state] += 1
        blocker_class_counts[blocker_class] += 1
        actionable_lifecycle_count += int(actionable_lifecycle_state in CAP_CENSUS_ACTIONABLE_LIFECYCLE_STATES)
        stale_actionable_count += int(stale_age_warning)
        missing_reentry_count += int(not reentry_route)

        confidence = "missing_source" if semantic_role == "unknown" else "projection_inferred"
        if semantic_role != "unknown" and temporal_role in {"past_proven", "past_retired", "blocked_future"}:
            confidence = "source_evidenced"

        rows.append(
            {
                "id": item_id,
                "title": item.get("title"),
                "state": state,
                "work_item_type": item.get("work_item_type"),
                "candidate_work_item_type": item.get("candidate_work_item_type"),
                "cap_namespace_kind": namespace_kind,
                "temporal_role": temporal_role,
                "semantic_role": semantic_role,
                "views": item_views,
                "view_count": len(item_views),
                "in_mission_operating_picture": item_id in view_memberships.get(MISSION_OPERATING_PICTURE_VIEW_ID, set()),
                "in_mission_operating_picture_graph": item_id in mission_graph_ids,
                "has_umbrella_refs": has_umbrella_refs,
                "has_proof_refs": has_proof_refs,
                "has_integration_contract": has_integration_contract,
                "has_grounded_integration_surfaces": has_grounded_integration,
                "actionable_lifecycle_state": actionable_lifecycle_state,
                "lifecycle_basis": lifecycle_basis,
                "owner_lane": owner_lane,
                "dependency_refs": dependency_refs,
                "dependency_ref_count": len(dependency_refs),
                "reentry_route": reentry_route,
                "blocker_class": blocker_class,
                "retirement_evidence_required": retirement_evidence_required,
                "stale_age_days": stale_age_days,
                "stale_age_warning": stale_age_warning,
                "trace_hud_visible": actionable_lifecycle_state in CAP_CENSUS_ACTIONABLE_LIFECYCLE_STATES,
                "classification_basis": basis,
                "confidence": confidence,
            }
        )

    cap_prefixed_ids = {item_id for item_id in by_id if item_id.startswith("cap_")}
    mission_current_ids = view_memberships.get(MISSION_OPERATING_PICTURE_VIEW_ID, set())
    mission_current_row_count = len(mission_operating_picture.get("items") or [])

    return {
        "kind": "task_ledger_view",
        "schema_version": CAP_CENSUS_SCHEMA,
        "view_id": CAP_CENSUS_VIEW_ID,
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "projection_inputs": list(CAP_CENSUS_SOURCE_REFS),
            "mutation_rule": "read-only cap-universe projection; append Task Ledger events to change source facts",
            "classification_policy": (
                "cap namespace counts are source-evidenced; temporal and semantic roles are projection-labeled "
                "unless backed by state, signoff, or view membership fields"
            ),
        },
        "source_refs": list(CAP_CENSUS_SOURCE_REFS),
        "summary": {
            "work_item_count": len(work_items),
            "cap_universe_count": len(rows),
            "cap_prefixed_count": cap_prefixed_count,
            "typed_cap_count": typed_cap_count,
            "typed_cap_prefixed_count": len(
                [row for row in rows if row["id"].startswith("cap_") and row["work_item_type"] == "cap"]
            ),
            "cap_like_nonprefixed_count": cap_like_nonprefixed_count,
            "mission_operating_picture_current_row_count": mission_current_row_count,
            "mission_operating_picture_current_work_item_count": len(mission_current_ids),
            "cap_prefixed_in_mission_operating_picture_count": len(cap_prefixed_ids & mission_current_ids),
            "mission_operating_picture_graph_work_item_count": len(mission_graph_ids),
            "cap_prefixed_in_mission_operating_picture_graph_count": len(cap_prefixed_ids & mission_graph_ids),
            "done_or_signoff_count": done_or_signoff_count,
            "captured_count": captured_count,
            "active_or_execution_count": active_or_execution_count,
            "blocked_count": blocked_count,
            "retired_count": retired_count,
            "umbrella_linked_count": umbrella_linked_count,
            "proof_backed_count": proof_backed_count,
            "integration_contract_count": integration_contract_count,
            "integration_grounded_count": integration_grounded_count,
            "unclassified_count": unclassified_count,
            "actionable_lifecycle_count": actionable_lifecycle_count,
            "stale_actionable_count": stale_actionable_count,
            "missing_reentry_count": missing_reentry_count,
        },
        "namespace_kind_counts": dict(namespace_kind_counts.most_common()),
        "type_counts": dict(type_counts.most_common()),
        "candidate_type_counts": dict(candidate_type_counts.most_common()),
        "state_counts": dict(state_counts.most_common()),
        "view_membership_counts": dict(view_membership_counts.most_common()),
        "temporal_role_counts": dict(temporal_counts.most_common()),
        "semantic_role_counts": dict(semantic_counts.most_common()),
        "actionable_lifecycle_counts": dict(lifecycle_counts.most_common()),
        "blocker_class_counts": dict(blocker_class_counts.most_common()),
        "classification_basis": {
            "cap_universe_primary": "id starts with cap_ plus strictly cap-like non-prefixed rows from work_item_type, candidate_work_item_type, or tags",
            "typed_cap": "work_item_type == cap",
            "proof_backed": "sign_off_id/sign_offs membership/receipt_refs/commit_refs/execution_receipts/completion proof refs",
            "umbrella_linked": "satisfaction_contract imagined-state/umbrella/north-star/teleology refs",
            "integration_grounded": "projection_completeness.exact_surfaces_grounded",
            "semantic_roles": "deterministic field-token projection; not source authority unless confidence is source_evidenced",
            "actionable_lifecycle_state": (
                "deterministic scheduling projection over state, dependency views, active/ready views, "
                "and terminal evidence; Task Ledger events remain authority"
            ),
        },
        "rows": rows,
        "items": rows,
        "count": len(rows),
    }


def _cap_cartography_slug(value: Any) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", str(value or "unknown").lower()).strip("_")
    return slug or "unknown"


def _cap_cartography_label(value: Any) -> str:
    return str(value or "unknown").replace("_", " ").strip().title() or "Unknown"


def _cap_cartography_cluster_specs(row: Mapping[str, Any]) -> List[Dict[str, Any]]:
    proof_value = "proof_backed" if row.get("has_proof_refs") else "proof_missing"
    if row.get("has_grounded_integration_surfaces"):
        integration_value = "integration_grounded"
    elif row.get("has_integration_contract"):
        integration_value = "integration_contract_only"
    else:
        integration_value = "integration_missing"
    umbrella_value = "umbrella_linked" if row.get("has_umbrella_refs") else "umbrella_missing"
    operating_value = (
        "current_operating_picture"
        if row.get("in_mission_operating_picture")
        else "outside_current_operating_picture"
    )
    return [
        {
            "cluster_kind": "namespace_kind",
            "value": row.get("cap_namespace_kind") or "unknown",
            "source_evidence": "cap_census.rows[].cap_namespace_kind",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "temporal_role",
            "value": row.get("temporal_role") or "unknown",
            "source_evidence": "cap_census.rows[].temporal_role",
            "confidence": "projection_inferred",
        },
        {
            "cluster_kind": "semantic_role",
            "value": row.get("semantic_role") or "unknown",
            "source_evidence": "cap_census.rows[].semantic_role",
            "confidence": "projection_inferred",
        },
        {
            "cluster_kind": "state",
            "value": row.get("state") or "unknown",
            "source_evidence": "cap_census.rows[].state",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "actionable_lifecycle_state",
            "value": row.get("actionable_lifecycle_state") or "unknown",
            "source_evidence": "cap_census.rows[].actionable_lifecycle_state",
            "confidence": "projection_inferred",
        },
        {
            "cluster_kind": "proof_readiness",
            "value": proof_value,
            "source_evidence": "cap_census.rows[].has_proof_refs",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "integration_readiness",
            "value": integration_value,
            "source_evidence": "cap_census.rows[].has_integration_contract / has_grounded_integration_surfaces",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "umbrella_linkage",
            "value": umbrella_value,
            "source_evidence": "cap_census.rows[].has_umbrella_refs",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "operating_picture",
            "value": operating_value,
            "source_evidence": "cap_census.rows[].in_mission_operating_picture",
            "confidence": "source_evidenced",
        },
    ]


def _cap_cartography_row_rank_key(row: Mapping[str, Any], item: Mapping[str, Any] | None = None) -> tuple[Any, ...]:
    item = item or {}
    temporal_order = {
        "active_conversion": 0,
        "blocked_future": 1,
        "future_open": 2,
        "past_proven": 3,
        "past_retired": 4,
    }
    state_order = {
        "execution": 0,
        "active": 1,
        "claimed": 2,
        "shaping": 3,
        "ready": 4,
        "captured": 5,
        "blocked": 6,
        "done": 7,
        "signoff": 8,
        "propagated": 9,
        "retired": 10,
    }
    rank = item.get("rank")
    return (
        0 if row.get("in_mission_operating_picture") else 1,
        temporal_order.get(str(row.get("temporal_role") or ""), 9),
        state_order.get(str(row.get("state") or ""), 99),
        0 if row.get("has_grounded_integration_surfaces") else 1,
        0 if row.get("has_proof_refs") else 1,
        0 if row.get("confidence") == "source_evidenced" else 1,
        rank is None,
        rank or 999999,
        str(row.get("id") or ""),
    )


def _cap_cartography_missing_counts(rows: Sequence[Mapping[str, Any]]) -> Dict[str, int]:
    return {
        "umbrella_refs": sum(1 for row in rows if not row.get("has_umbrella_refs")),
        "proof_refs": sum(1 for row in rows if not row.get("has_proof_refs")),
        "integration": sum(1 for row in rows if not row.get("has_grounded_integration_surfaces")),
        "classification": sum(1 for row in rows if row.get("semantic_role") == "unknown"),
    }


def _cap_cartography_source_refs(item: Mapping[str, Any]) -> List[str]:
    refs: List[str] = []
    for key in (
        "source_refs",
        "source_event_ids",
        "evidence_refs",
        "raw_seed_refs",
        "operator_voice_refs",
        "principle_refs",
        "axiom_refs",
    ):
        refs.extend(_coerce_id_list(item.get(key)))
    return refs


def _cap_cartography_proof_refs(
    item: Mapping[str, Any],
    *,
    signoffs_by_work_item: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[str]:
    refs: List[str] = []
    item_id = _cap_census_item_id(item)
    refs.extend(_coerce_id_list(item.get("sign_off_id")))
    for signoff in signoffs_by_work_item.get(item_id, []):
        refs.extend(_coerce_id_list(signoff.get("id")))
        refs.extend(_coerce_id_list(signoff.get("receipt_refs")))
        refs.extend(_coerce_id_list(signoff.get("commit_refs")))
        refs.extend(_coerce_id_list(signoff.get("evidence_refs")))
    refs.extend(_coerce_id_list(item.get("receipt_refs")))
    refs.extend(_coerce_id_list(item.get("commit_refs")))
    refs.extend(_coerce_id_list(item.get("execution_receipts")))
    completion = item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
    refs.extend(_coerce_id_list(completion.get("proof_refs")))
    refs.extend(_coerce_id_list(completion.get("evidence_refs")))
    refs.extend(_coerce_id_list(completion.get("receipt_refs")))
    return list(dict.fromkeys(refs))


def _cap_cartography_missing_refs(row: Mapping[str, Any]) -> List[str]:
    missing: List[str] = []
    if not row.get("has_umbrella_refs"):
        missing.append("umbrella_refs")
    if not row.get("has_proof_refs"):
        missing.append("proof_refs")
    if not row.get("has_grounded_integration_surfaces"):
        missing.append("grounded_integration")
    if row.get("semantic_role") == "unknown":
        missing.append("classification")
    return missing


def _cap_cartography_drilldown_route_metadata(
    *,
    cluster_kind: str | None = None,
    value: str | None = None,
) -> Dict[str, Any]:
    route: Dict[str, Any] = {
        "option_surface": "./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids cap_cartography",
        "projection_path": str(VIEWS_REL / "cap_cartography.json"),
        "source_view": str(VIEWS_REL / "cap_census.json"),
    }
    if cluster_kind is not None:
        route["member_filter"] = {
            "source_field": f"cap_census.rows[].{cluster_kind}",
            "cluster_kind": cluster_kind,
            "value": value,
        }
    return route


def _cap_cartography_node(
    row: Mapping[str, Any],
    item: Mapping[str, Any],
    *,
    cluster_ids: Sequence[str],
    signoffs_by_work_item: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Dict[str, Any]:
    item_id = str(row.get("id") or "")
    proof_refs = _cap_cartography_proof_refs(item, signoffs_by_work_item=signoffs_by_work_item)
    source_refs = _cap_cartography_source_refs(item)
    return {
        "id": item_id,
        "label": item.get("title") or row.get("title") or item_id,
        "node_kind": "cap",
        "display_role": "representative_cap",
        "cluster_ids": list(cluster_ids),
        "lod": {
            "overview": {
                "cluster_ids": list(cluster_ids),
                "glyph": "work_item",
                "color_basis": "temporal_role",
                "size_basis": "view_count",
            },
            "detail": {
                "state": row.get("state"),
                "cap_namespace_kind": row.get("cap_namespace_kind"),
                "semantic_role": row.get("semantic_role"),
                "temporal_role": row.get("temporal_role"),
                "actionable_lifecycle_state": row.get("actionable_lifecycle_state"),
                "blocker_class": row.get("blocker_class"),
                "owner_lane": row.get("owner_lane"),
                "dependency_ref_count": row.get("dependency_ref_count"),
                "retirement_evidence_required": bool(row.get("retirement_evidence_required")),
                "stale_age_warning": bool(row.get("stale_age_warning")),
                "proof_backed": bool(row.get("has_proof_refs")),
                "integration_grounded": bool(row.get("has_grounded_integration_surfaces")),
                "umbrella_linked": bool(row.get("has_umbrella_refs")),
                "in_current_operating_picture": bool(row.get("in_mission_operating_picture")),
                "confidence": row.get("confidence"),
                "classification_basis": list(row.get("classification_basis") or []),
            },
        },
        "source_refs": source_refs,
        "proof_refs": proof_refs,
        "missing_refs": _cap_cartography_missing_refs(row),
        "source_route_metadata": {
            "task_ledger_card": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{item_id}"
            ),
            "views": list(row.get("views") or []),
            "frontend_actionable": bool(row.get("trace_hud_visible")),
            "reentry_route": row.get("reentry_route"),
        },
    }


def _workitem_cartography_actor(item: Mapping[str, Any]) -> str:
    actor = item.get("actor") or item.get("owner") or item.get("created_by") or item.get("last_actor")
    if isinstance(actor, str) and actor.strip():
        return actor.strip()
    actors = item.get("actors")
    if isinstance(actors, Sequence) and not isinstance(actors, (str, bytes)):
        for entry in reversed(list(actors)):
            if isinstance(entry, str) and entry.strip():
                return entry.strip()
    return "unassigned"


def _workitem_cartography_family(item: Mapping[str, Any]) -> str:
    family = item.get("family_id") or item.get("family") or item.get("phase_id")
    if isinstance(family, str) and family.strip():
        return family.strip()
    return "unknown"


def _workitem_cartography_route(item: Mapping[str, Any]) -> Dict[str, Any]:
    execution = item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    route = {
        "phase_id": execution.get("phase_id"),
        "source_queue": execution.get("source_queue"),
        "queue_sequence": execution.get("queue_sequence"),
        "queue_bucket": execution.get("queue_bucket"),
        "route": execution.get("route"),
    }
    known = any(value not in (None, "", []) for value in route.values())
    route["status"] = "known" if known else "unknown"
    return route


def _workitem_needs_signoff_active(item: Mapping[str, Any]) -> bool:
    """
    Wave 2E predicate identity. Returns True iff the WorkItem ACTIVELY
    needs signoff — i.e. matches the predicate that the
    `needs_signoff.json` view builder uses (just
    `projection_completeness.needs_signoff`). Centralised so the
    cartography route_reason and the diagnostic view consume identical
    semantics, which guarantees the `needs_signoff_unrouted` reason can
    only be exact/broad relative to its owner view, never partial.

    Wave 2D measurement showed the prior cartography helper used a
    broader predicate (state == "signoff" OR completion.signoff_required
    OR projection.needs_signoff) that swept in 71 rows already
    signoff-recorded (state=signoff + sign_off_id populated). Those rows
    no longer need signoff; they need propagation. Wave 2E reroutes them
    via the new `signoff_recorded_awaiting_propagation` reason instead.
    """
    completeness = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), Mapping)
        else {}
    )
    return bool(completeness.get("needs_signoff"))


def _workitem_signoff_recorded_awaiting_propagation(item: Mapping[str, Any]) -> bool:
    """
    Wave 2E predicate for the new `signoff_recorded_awaiting_propagation`
    route_reason. Returns True iff the WorkItem is in `state == "signoff"`
    and a signoff has been RECORDED (sign_off_id populated) — i.e. the
    signoff workflow has produced its record and the row is waiting for a
    `work_item.state_transitioned` to propagated/done.

    Matches the 71 gap rows surfaced by Wave 2D. By construction the
    overlap with the `signoffs` catalog (work_item_id field) is 100%, so
    the lane_relationship will be `exact_reason_view`.
    """
    state = str(item.get("state") or item.get("status") or "").lower()
    if state != "signoff":
        return False
    return bool(item.get("sign_off_id"))


def _state_transitioned_no_execution_route_predicate(
    item: Mapping[str, Any],
) -> bool:
    """
    Wave 2C diagnostic predicate. True iff this WorkItem's primary
    route_reason would be `state_transitioned_no_execution_route` — i.e.
    every earlier-priority predicate misses, both contracts are present,
    `_has_execution_commitment_event(item)` is True, and the execution
    route fields are all empty.

    Mirrors the priority ordering used in
    `_workitem_cartography_route_reason_candidates`; if that priority
    changes, this predicate must move with it. Single source of truth
    for the new `state_transitioned_no_execution_route.json` view.
    """
    completeness = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), Mapping)
        else {}
    )
    state = str(item.get("state") or item.get("status") or "").lower()
    work_item_type = str(
        item.get("work_item_type")
        or item.get("candidate_work_item_type")
        or ""
    ).lower()
    completion = (
        item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
    )
    needs_signoff = (
        bool(completion.get("signoff_required"))
        or bool(completeness.get("needs_signoff"))
        or state == "signoff"
    )
    is_blocked = state == "blocked" or bool(item.get("blocked"))
    execution = (
        item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    )
    route_known = any(
        execution.get(field) not in (None, "", [])
        for field in ("phase_id", "source_queue", "queue_sequence", "queue_bucket", "route")
    )
    # Earlier-priority predicates must NOT fire.
    if completeness.get("legacy_snapshot_present"):
        return False
    if state in WORKITEM_ROUTE_REASON_TERMINAL_STATES:
        return False
    if needs_signoff:
        return False
    if (
        state in WORKITEM_ROUTE_REASON_ACTIVE_STATES
        and not completeness.get("has_work_ledger_claim_ref")
    ):
        return False
    if is_blocked:
        return False
    if (
        work_item_type == "capture"
        and state in WORKITEM_ROUTE_REASON_CAPTURE_INBOX_STATES
    ):
        return False
    if not completeness.get("has_integration_contract") or not completeness.get(
        "exact_surfaces_grounded"
    ):
        return False
    if not completeness.get("has_satisfaction_contract"):
        return False
    # state_transitioned-specific tests.
    if route_known:
        return False
    if not _has_execution_commitment_event(item):
        return False
    return True


def _state_transitioned_no_execution_route_row(
    item: Mapping[str, Any],
) -> Dict[str, Any]:
    """
    Wave 2C diagnostic row. Mirrors the shape of
    `_build_capture_triage_view` / `_build_missing_contracts_ranked_view`
    rows: id + title + state + work_item_type plus a typed
    `commitment_source`, the specific `missing_execution_fields`, and a
    repair `recommended_action`. Source-evidence carried via
    `source_event_types` (subset of state_transitioned/promoted/claimed/etc.).
    """
    item_id = str(item.get("id") or "")
    execution = (
        item.get("execution") if isinstance(item.get("execution"), Mapping) else {}
    )
    missing_execution_fields = [
        field
        for field in ("phase_id", "source_queue", "queue_sequence", "queue_bucket", "route")
        if execution.get(field) in (None, "", [])
    ]
    commitment_source = _execution_commitment_source(item)
    event_types = sorted(_item_event_types(item))
    return {
        "id": item_id,
        "title": str(item.get("title") or item.get("statement") or item_id),
        "state": str(item.get("state") or item.get("status") or "unknown"),
        "work_item_type": str(
            item.get("work_item_type")
            or item.get("candidate_work_item_type")
            or "unknown"
        ),
        "rank": item.get("rank"),
        "updated_at": item.get("updated_at") or item.get("last_event_at"),
        "commitment_source": commitment_source,
        "commitment_evidence": (
            "row had work_item.state_transitioned / promoted / claimed / "
            "rerank_committed event(s) (counted as execution commitment by "
            "execution_menu predicate) yet execution route metadata never "
            "landed"
        ),
        "missing_execution_fields": missing_execution_fields,
        "source_event_types": [
            event_type
            for event_type in event_types
            if event_type
            in {
                "work_item.state_transitioned",
                "work_item.promoted",
                "work_item.claimed",
                "work_item.rerank_committed",
            }
        ],
        "recommended_action": (
            "stamp execution.phase_id / source_queue / queue_sequence / "
            "queue_bucket / route via a rerank-commit or promotion event so "
            "the row enters the execution_menu cleanly"
        ),
        "why_recommended": (
            "commitment-class events fired but no execution route metadata "
            "exists; route_provenance flags this as a repair lane, not a "
            "generic unrouted row"
        ),
    }


def _workitem_cartography_route_reason_candidates(
    item: Mapping[str, Any],
    *,
    state: str,
    work_item_type: str,
    is_blocked: bool,
    needs_signoff: bool,
) -> List[str]:
    """
    Pure projection over existing item fields → ordered list of candidate route
    reasons (most specific first). Caller picks the head as the primary reason
    and stamps the rest as secondaries. No diagnostic-view JSON is read here;
    every test rides on `projection_completeness.*`, state, or a dedicated
    helper that already lives in this module.

    Wave 2A.1 fidelity: every predicate listed here MUST match the
    `WORKITEM_ROUTE_REASON_PREDICATE_KIND` + `WORKITEM_ROUTE_REASON_EVIDENCE_*`
    declarations. The audit lane (`_workitem_route_provenance_audit`) checks
    sample rows against each predicate; a mismatch raises a contract
    violation in the consumption layer instead of silently labelling.
    """
    completeness = (
        item.get("projection_completeness")
        if isinstance(item.get("projection_completeness"), Mapping)
        else {}
    )
    candidates: List[str] = []
    # Priority 1: legacy bootstrapped — pre-Task-Ledger snapshot rows.
    if completeness.get("legacy_snapshot_present"):
        candidates.append("legacy_bootstrapped_no_execution_fields")
    # Priority 2: terminal lifecycle — done/retired/propagated/completed are
    # benign unrouted; the operator should not be asked to remediate.
    if state in WORKITEM_ROUTE_REASON_TERMINAL_STATES:
        candidates.append("terminal_no_longer_routable")
    # Priority 3: active signoff need — predicate identity with the
    # `needs_signoff.json` view (projection_completeness.needs_signoff).
    # Wave 2E narrowed this from the broader `_needs_signoff` helper
    # (which also fired on state=="signoff") so the lane_relationship
    # can be exact/broad rather than partial. Rows that ARE in signoff
    # state with a recorded signoff route to the new priority-4 reason.
    if _workitem_needs_signoff_active(item):
        candidates.append("needs_signoff_unrouted")
    # Priority 4: signoff has been RECORDED and the row is awaiting
    # propagation. By construction overlap with `signoffs.json`
    # (work_item_id field) is 100%, so the lane_relationship is
    # exact_reason_view.
    if _workitem_signoff_recorded_awaiting_propagation(item):
        candidates.append("signoff_recorded_awaiting_propagation")
    # Priority 5: claimed/active/review/signoff state without a Work Ledger
    # claim binding the row to an execution surface.
    if state in WORKITEM_ROUTE_REASON_ACTIVE_STATES and not completeness.get(
        "has_work_ledger_claim_ref"
    ):
        candidates.append("work_ledger_unlinked")
    # Priority 5: blocked rows are not currently routable. This is a
    # LEDGER-STATE predicate (state=="blocked" OR item.blocked truthy), NOT
    # `dependency_blocked.json` membership — the diagnostic view is far
    # narrower than the ledger flag. Named accordingly so evidence claims
    # stay honest.
    if is_blocked:
        candidates.append("blocked_without_execution_profile")
    # Priority 6: capture-shaped row sitting in the inbox.
    if (
        work_item_type == "capture"
        and state in WORKITEM_ROUTE_REASON_CAPTURE_INBOX_STATES
    ):
        candidates.append("quick_capture_unshaped")
    # Priority 7/8: contract pressure — integration before satisfaction so
    # the most specific landing-surface debt is named first.
    if not completeness.get("has_integration_contract") or not completeness.get(
        "exact_surfaces_grounded"
    ):
        candidates.append("missing_integration_contract")
    if not completeness.get("has_satisfaction_contract"):
        candidates.append("missing_satisfaction_contract")
    # Priority 9: contracts are shaped but no explicit execution commitment
    # event has fired. Uses the same predicate `execution_menu` builds on.
    if (
        completeness.get("has_integration_contract")
        and completeness.get("has_satisfaction_contract")
        and not _has_execution_commitment_event(item)
    ):
        candidates.append("shaped_no_execution_commitment")
    # Priority 10: state_transitioned rows that ARE counted as "commitment"
    # by execution_menu's predicate yet still carry no execution route
    # metadata. Captures the small residual that `shaped_no_execution_
    # commitment` cannot reach (because the helper returns True for any
    # state_transitioned event, even one that just moved the row into
    # shaping). Predicate: both contracts present AND
    # _has_execution_commitment_event(item)==True — combined with
    # route.status="unknown" enforced by the caller, this is "shaped row
    # had commitment-class event activity but no routing metadata landed".
    if (
        completeness.get("has_integration_contract")
        and completeness.get("has_satisfaction_contract")
        and _has_execution_commitment_event(item)
    ):
        candidates.append("state_transitioned_no_execution_route")
    return candidates


def _workitem_cartography_route_explanation(
    item: Mapping[str, Any],
    *,
    route: Mapping[str, Any],
    state: str,
    work_item_type: str,
    is_blocked: bool,
    needs_signoff: bool,
) -> Dict[str, Any]:
    """
    Stamp a typed `route_explanation` onto an unrouted atlas_mark. Returns a
    bare presence record for routed items (so the consumer sees a uniform
    shape but doesn't have to filter on truthiness).

    Wave 2A.1 schema additions: every explanation carries evidence_fields[]
    (substrate paths the predicate actually reads) and predicate_kind
    (ledger_state_field | projection_completeness_flag | projection_helper |
    ledger_state_and_completeness_flag | etc.). Together these let the audit
    lane (`_workitem_route_provenance_audit`) reconcile each row's claimed
    evidence against the predicate that actually fired.

    Schema:
      {
        route_status: "known" | "unknown",
        route_reason: str | null,
        route_reason_label: str | null,
        reason_kind: "benign" | "anomaly" | "backlog" | "actionable" | null,
        predicate_kind: str | null,
        secondary_reasons: [str, ...],
        evidence_refs: [str, ...],            # diagnostic-view paths (may be empty)
        evidence_fields: [str, ...],          # ledger field paths the predicate reads
        carryover_status: "not_evaluated",
        carryover_status_reason: str,
        confidence: "projection_evidenced" | "source_evidenced",
      }
    """
    route_status = str(route.get("status") or "unknown")
    if route_status == "known":
        return {
            "route_status": "known",
            "route_reason": None,
            "route_reason_label": None,
            "reason_kind": None,
            "predicate_kind": None,
            "secondary_reasons": [],
            "evidence_refs": [],
            "evidence_fields": [],
            "carryover_status": "not_evaluated",
            "carryover_status_reason": (
                "origin/current-scope fields do not exist on ledger.work_items[]"
            ),
            "confidence": "source_evidenced",
        }

    candidates = _workitem_cartography_route_reason_candidates(
        item,
        state=state,
        work_item_type=work_item_type,
        is_blocked=is_blocked,
        needs_signoff=needs_signoff,
    )
    if candidates:
        primary = candidates[0]
        secondary = list(candidates[1:])
    else:
        primary = WORKITEM_ROUTE_REASON_UNKNOWN
        secondary = []
    evidence_refs: List[str] = []
    for view in WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS.get(primary, ()):
        evidence_refs.append(str(VIEWS_REL / view))
    for reason in secondary:
        for view in WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS.get(reason, ()):
            ref = str(VIEWS_REL / view)
            if ref not in evidence_refs:
                evidence_refs.append(ref)
    evidence_fields: List[str] = list(
        WORKITEM_ROUTE_REASON_EVIDENCE_FIELDS.get(primary, ())
    )
    reason_kind = WORKITEM_ROUTE_REASON_KINDS.get(primary, "actionable")
    predicate_kind = WORKITEM_ROUTE_REASON_PREDICATE_KIND.get(
        primary, "fallback_no_predicate_fired"
    )
    return {
        "route_status": "unknown",
        "route_reason": primary,
        "route_reason_label": WORKITEM_ROUTE_REASON_LABELS.get(primary, primary),
        "reason_kind": reason_kind,
        "predicate_kind": predicate_kind,
        "secondary_reasons": secondary,
        "evidence_refs": evidence_refs,
        "evidence_fields": evidence_fields,
        "carryover_status": "not_evaluated",
        "carryover_status_reason": (
            "origin/current-scope fields do not exist on ledger.work_items[]"
        ),
        "confidence": "projection_evidenced",
    }


def _workitem_cartography_source_refs(item: Mapping[str, Any]) -> List[str]:
    refs: List[str] = []
    for key in ("source_refs", "source_event_ids", "evidence_refs"):
        for ref in item.get(key) or []:
            if isinstance(ref, str) and ref.strip():
                refs.append(ref.strip())
    return list(dict.fromkeys(refs))


def _workitem_cartography_missing_refs(item: Mapping[str, Any]) -> List[str]:
    missing: List[str] = []
    if not _workitem_cartography_source_refs(item):
        missing.append("source_refs")
    if not item.get("state") and not item.get("status"):
        missing.append("state")
    if not item.get("work_item_type") and not item.get("candidate_work_item_type"):
        missing.append("work_item_type")
    return missing


def _workitem_cartography_cluster_specs(
    item: Mapping[str, Any],
    *,
    actor: str,
    family: str,
    route: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    state_value = str(item.get("state") or item.get("status") or "unknown")
    type_value = str(item.get("work_item_type") or item.get("candidate_work_item_type") or "unknown")
    return [
        {
            "cluster_kind": "state",
            "value": state_value,
            "source_evidence": "ledger.work_items[].state",
            "confidence": "source_evidenced",
        },
        {
            "cluster_kind": "work_item_type",
            "value": type_value,
            "source_evidence": "ledger.work_items[].work_item_type",
            "confidence": "source_evidenced" if item.get("work_item_type") else "projection_inferred",
        },
        {
            "cluster_kind": "actor",
            "value": actor,
            "source_evidence": "ledger.work_items[].actor/owner/created_by/last_actor",
            "confidence": "projection_inferred",
        },
        {
            "cluster_kind": "family",
            "value": family,
            "source_evidence": "ledger.work_items[].family_id/family/phase_id",
            "confidence": "source_evidenced" if item.get("family_id") else "projection_inferred",
        },
        {
            "cluster_kind": "route_status",
            "value": str(route.get("status") or "unknown"),
            "source_evidence": "ledger.work_items[].execution route metadata presence",
            "confidence": "projection_inferred",
        },
    ]


def _workitem_cartography_row_rank_key(
    item: Mapping[str, Any],
    *,
    downstream_unlock_count: int,
    is_blocked: bool,
    is_stale: bool,
    needs_signoff: bool,
) -> tuple[Any, ...]:
    state_order = {
        "execution": 0,
        "active": 1,
        "claimed": 2,
        "shaping": 3,
        "ready": 4,
        "captured": 5,
        "blocked": 6,
        "signoff": 7,
        "done": 8,
        "propagated": 9,
        "retired": 10,
    }
    state = str(item.get("state") or item.get("status") or "unknown")
    rank = item.get("rank")
    return (
        0 if needs_signoff else 1,
        0 if is_blocked else 1,
        0 if is_stale else 1,
        -int(downstream_unlock_count or 0),
        state_order.get(state, 99),
        rank if isinstance(rank, (int, float)) else 999_999,
        str(item.get("id") or ""),
    )


def _workitem_cartography_drilldown_route_metadata(
    *,
    cluster_kind: str | None = None,
    value: str | None = None,
) -> Dict[str, Any]:
    metadata: Dict[str, Any] = {
        "option_surface": (
            "./repo-python kernel.py --option-surface task_ledger --band cluster_flag --ids workitem_cartography"
        ),
        "projection_path": str(VIEWS_REL / "workitem_cartography.json"),
        "source_view": str(LEDGER_REL),
    }
    if cluster_kind is not None:
        metadata["member_filter"] = {
            "source_field": f"ledger.work_items[].{cluster_kind}",
            "cluster_kind": cluster_kind,
            "value": value,
        }
    return metadata


def _workitem_cartography_mark(
    item: Mapping[str, Any],
    *,
    actor: str,
    family: str,
    route: Mapping[str, Any],
    cluster_ids: Sequence[str],
    depends_on_count: int,
    downstream_unlock_count: int,
    is_blocked: bool,
    is_stale: bool,
    needs_signoff: bool,
    queue_visible: bool = False,
) -> Dict[str, Any]:
    item_id = str(item.get("id") or "")
    state = str(item.get("state") or item.get("status") or "unknown")
    type_value = str(item.get("work_item_type") or item.get("candidate_work_item_type") or "unknown")
    route_explanation = _workitem_cartography_route_explanation(
        item,
        route=route,
        state=state,
        work_item_type=type_value,
        is_blocked=is_blocked,
        needs_signoff=needs_signoff,
    )
    return {
        "id": item_id,
        "title": str(item.get("title") or item.get("statement") or item_id),
        "state": state,
        "work_item_type": type_value,
        "actor": actor,
        "family": family,
        "route": {
            "status": str(route.get("status") or "unknown"),
            "phase_id": route.get("phase_id"),
            "source_queue": route.get("source_queue"),
            "queue_bucket": route.get("queue_bucket"),
        },
        "route_explanation": route_explanation,
        "updated_at": item.get("updated_at") or item.get("last_event_at") or item.get("created_at"),
        "last_event_at": item.get("last_event_at") or item.get("updated_at"),
        "cluster_ids": list(cluster_ids),
        "overlays": {
            "unrouted": route.get("status") == "unknown",
            "blocked": is_blocked,
            "stale": is_stale,
            "signoff_required": needs_signoff,
            "high_unlock": downstream_unlock_count >= WORKITEM_CARTOGRAPHY_HIGH_UNLOCK_THRESHOLD,
            "queue_visible": queue_visible,
        },
        "edge_summary": {
            "depends_on_count": int(depends_on_count or 0),
            "downstream_unlock_count": int(downstream_unlock_count or 0),
        },
    }


def _workitem_cartography_node(
    item: Mapping[str, Any],
    *,
    actor: str,
    family: str,
    route: Mapping[str, Any],
    cluster_ids: Sequence[str],
    downstream_unlock_count: int,
    is_blocked: bool,
    is_stale: bool,
    needs_signoff: bool,
) -> Dict[str, Any]:
    item_id = str(item.get("id") or "")
    state = str(item.get("state") or item.get("status") or "unknown")
    type_value = str(item.get("work_item_type") or item.get("candidate_work_item_type") or "unknown")
    source_refs = _workitem_cartography_source_refs(item)
    return {
        "id": item_id,
        "label": str(item.get("title") or item_id),
        "node_kind": type_value,
        "display_role": "representative_work_item",
        "cluster_ids": list(cluster_ids),
        "lod": {
            "overview": {
                "cluster_ids": list(cluster_ids),
                "glyph": "work_item",
                "color_basis": "state",
                "size_basis": "downstream_unlock_count",
            },
            "detail": {
                "state": state,
                "work_item_type": type_value,
                "actor": actor,
                "family": family,
                "route_status": str(route.get("status") or "unknown"),
                "downstream_unlock_count": int(downstream_unlock_count or 0),
                "blocked": is_blocked,
                "stale": is_stale,
                "signoff_required": needs_signoff,
            },
        },
        "source_refs": source_refs,
        "missing_refs": _workitem_cartography_missing_refs(item),
        "source_route_metadata": {
            "task_ledger_card": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{item_id}"
            ),
            "frontend_actionable": False,
        },
    }


def _build_cap_cartography_view(
    *,
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
    cap_census: Mapping[str, Any],
    mission_operating_picture: Mapping[str, Any],
    dependency_views: Mapping[str, Mapping[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    cap_rows = [row for row in cap_census.get("rows") or [] if isinstance(row, Mapping)]
    cap_rows_by_id = {str(row.get("id") or ""): row for row in cap_rows if row.get("id")}
    work_items_by_id = {_cap_census_item_id(item): item for item in work_items if _cap_census_item_id(item)}
    signoffs_by_work_item: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for signoff in signoffs:
        work_item_id = str(signoff.get("work_item_id") or "").strip()
        if work_item_id:
            signoffs_by_work_item[work_item_id].append(signoff)

    cluster_rows: Dict[str, Dict[str, Any]] = {}
    cluster_member_rows: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    row_cluster_ids: Dict[str, List[str]] = defaultdict(list)
    for row in cap_rows:
        item_id = str(row.get("id") or "")
        if not item_id:
            continue
        for spec in _cap_cartography_cluster_specs(row):
            cluster_kind = str(spec["cluster_kind"])
            value = str(spec["value"])
            cluster_id = f"cluster:{cluster_kind}:{_cap_cartography_slug(value)}"
            cluster_rows.setdefault(
                cluster_id,
                {
                    "id": cluster_id,
                    "label": _cap_cartography_label(value),
                    "cluster_kind": cluster_kind,
                    "value": value,
                    "source_evidence": spec["source_evidence"],
                    "confidence": spec["confidence"],
                },
            )
            cluster_member_rows[cluster_id].append(row)
            row_cluster_ids[item_id].append(cluster_id)

    representative_ids: List[str] = []
    clusters: List[Dict[str, Any]] = []
    for cluster_id, cluster in sorted(cluster_rows.items(), key=lambda item: (item[1]["cluster_kind"], item[1]["value"])):
        members = sorted(
            cluster_member_rows[cluster_id],
            key=lambda row: _cap_cartography_row_rank_key(row, work_items_by_id.get(str(row.get("id") or ""))),
        )
        reps = [str(row.get("id") or "") for row in members[:CAP_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT] if row.get("id")]
        representative_ids.extend(reps)
        states = Counter(str(row.get("state") or "unknown") for row in members)
        temporal_roles = Counter(str(row.get("temporal_role") or "unknown") for row in members)
        semantic_roles = Counter(str(row.get("semantic_role") or "unknown") for row in members)
        overflow_member_count = max(0, len(members) - len(reps))
        route_metadata = _cap_cartography_drilldown_route_metadata(
            cluster_kind=str(cluster["cluster_kind"]),
            value=str(cluster["value"]),
        )
        clusters.append(
            {
                **cluster,
                "member_count": len(members),
                "representative_ids": reps,
                "member_sample_ids": [str(row.get("id") or "") for row in members[:8] if row.get("id")],
                "overflow_member_count": overflow_member_count,
                "dominant_states": dict(states.most_common(5)),
                "dominant_temporal_roles": dict(temporal_roles.most_common(5)),
                "dominant_semantic_roles": dict(semantic_roles.most_common(5)),
                "missing_counts": _cap_cartography_missing_counts(members),
                "default_visible": cluster["cluster_kind"] in {"temporal_role", "semantic_role", "operating_picture"},
                "classification_basis": (
                    "source field cluster"
                    if cluster["confidence"] == "source_evidenced"
                    else "deterministic projection over cap_census row fields"
                ),
                "drilldown_available": True,
                "source_route_metadata": route_metadata,
                "member_drilldown_policy": (
                    "Use source_route_metadata.member_filter against cap_census rows; "
                    "representative_ids/member_sample_ids are bounded overview hints."
                ),
            }
        )

    visible_cap_ids = list(dict.fromkeys(representative_ids))
    relation_seed_ids = set(visible_cap_ids)
    cap_id_set = set(cap_rows_by_id)
    dependency_items = [
        row
        for row in dependency_views.get("dependency_graph", {}).get("items", [])
        if isinstance(row, Mapping)
    ]
    for dep_row in dependency_items:
        source_id = _mission_operating_item_id(dep_row)
        if source_id not in cap_id_set:
            continue
        dependency_status = dep_row.get("dependency_status") if isinstance(dep_row.get("dependency_status"), Mapping) else {}
        related_ids = _coerce_id_list(dep_row.get("depends_on"))
        related_ids.extend(_coerce_id_list(dependency_status.get("downstream_unlock_ids")))
        for related_id in related_ids:
            if related_id not in cap_id_set:
                continue
            if source_id in relation_seed_ids or related_id in relation_seed_ids:
                if source_id not in visible_cap_ids and len(visible_cap_ids) < CAP_CARTOGRAPHY_VISIBLE_CAP_NODE_LIMIT:
                    visible_cap_ids.append(source_id)
                if related_id not in visible_cap_ids and len(visible_cap_ids) < CAP_CARTOGRAPHY_VISIBLE_CAP_NODE_LIMIT:
                    visible_cap_ids.append(related_id)
                relation_seed_ids.update({source_id, related_id})
    visible_cap_ids = visible_cap_ids[:CAP_CARTOGRAPHY_VISIBLE_CAP_NODE_LIMIT]
    visible_cap_set = set(visible_cap_ids)

    nodes: List[Dict[str, Any]] = []
    support_node_ids: set[str] = set()
    for item_id in sorted(
        visible_cap_set,
        key=lambda row_id: _cap_cartography_row_rank_key(
            cap_rows_by_id.get(row_id, {}),
            work_items_by_id.get(row_id),
        ),
    ):
        row = cap_rows_by_id.get(item_id)
        if not row:
            continue
        nodes.append(
            _cap_cartography_node(
                row,
                work_items_by_id.get(item_id, {"id": item_id, "title": row.get("title")}),
                cluster_ids=row_cluster_ids.get(item_id, []),
                signoffs_by_work_item=signoffs_by_work_item,
            )
        )

    edges: List[Dict[str, Any]] = []
    edge_ids: set[str] = set()
    edge_limit_hit = False
    support_node_limit_hit = False
    omitted_edge_counts: Counter[str] = Counter()
    omitted_by_source_ref: Counter[str] = Counter()
    omitted_by_cluster_id: Counter[str] = Counter()
    omitted_edge_samples: List[Dict[str, Any]] = []

    def record_omitted_edge(
        *,
        source: str,
        target: str,
        edge_kind: str,
        source_ref: str,
        reason: str,
    ) -> None:
        if not source or not target:
            return
        omitted_edge_counts[edge_kind] += 1
        omitted_by_source_ref[source_ref] += 1
        source_clusters = list(row_cluster_ids.get(source, []))
        target_clusters = list(row_cluster_ids.get(target, []))
        if target.startswith("cluster:"):
            omitted_by_cluster_id[target] += 1
        elif source_clusters:
            omitted_by_cluster_id[source_clusters[0]] += 1
        elif target_clusters:
            omitted_by_cluster_id[target_clusters[0]] += 1
        if len(omitted_edge_samples) < CAP_CARTOGRAPHY_OMITTED_EDGE_SAMPLE_LIMIT:
            omitted_edge_samples.append(
                {
                    "source": source,
                    "target": target,
                    "edge_kind": edge_kind,
                    "source_ref": source_ref,
                    "reason": reason,
                    "source_cluster_ids": source_clusters[:3],
                    "target_cluster_ids": target_clusters[:3],
                }
            )

    def add_support_node(node: Dict[str, Any]) -> bool:
        nonlocal support_node_limit_hit
        node_id = str(node.get("id") or "")
        if not node_id or node_id in support_node_ids:
            return bool(node_id)
        if len(support_node_ids) >= CAP_CARTOGRAPHY_SUPPORT_NODE_LIMIT:
            support_node_limit_hit = True
            return False
        support_node_ids.add(node_id)
        nodes.append(node)
        return True

    def add_edge(
        *,
        source: str,
        target: str,
        edge_kind: str,
        confidence: str,
        source_ref: str,
    ) -> None:
        nonlocal edge_limit_hit
        if not source or not target:
            return
        edge_id = f"edge:{edge_kind}:{source}->{target}"
        if edge_id in edge_ids:
            return
        if len(edges) >= CAP_CARTOGRAPHY_EDGE_LIMIT:
            edge_limit_hit = True
            record_omitted_edge(
                source=source,
                target=target,
                edge_kind=edge_kind,
                source_ref=source_ref,
                reason="edge_limit",
            )
            return
        edge_ids.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "edge_kind": edge_kind,
                "confidence": confidence,
                "source_ref": source_ref,
            }
        )

    for dep_row in dependency_items:
        source_id = _mission_operating_item_id(dep_row)
        if source_id not in cap_id_set:
            continue
        for dependency_id in _coerce_id_list(dep_row.get("depends_on")):
            if dependency_id not in cap_id_set:
                continue
            source_ref = str(VIEWS_REL / "dependency_graph.json")
            if source_id in visible_cap_set and dependency_id in visible_cap_set:
                add_edge(
                    source=source_id,
                    target=dependency_id,
                    edge_kind="depends_on",
                    confidence="source_evidenced",
                    source_ref=source_ref,
                )
            else:
                record_omitted_edge(
                    source=source_id,
                    target=dependency_id,
                    edge_kind="depends_on",
                    source_ref=source_ref,
                    reason="endpoint_outside_visible_overview",
                )
        dependency_status = dep_row.get("dependency_status") if isinstance(dep_row.get("dependency_status"), Mapping) else {}
        unlock_edges = dependency_status.get("downstream_unlock_edges")
        if isinstance(unlock_edges, Sequence) and not isinstance(unlock_edges, (str, bytes)):
            for unlock in unlock_edges:
                if not isinstance(unlock, Mapping):
                    continue
                target_id = str(unlock.get("id") or "").strip()
                if target_id not in cap_id_set:
                    continue
                source_ref = str(VIEWS_REL / "unlocks_by_rank.json")
                if source_id in visible_cap_set and target_id in visible_cap_set:
                    add_edge(
                        source=source_id,
                        target=target_id,
                        edge_kind="unlocks",
                        confidence="source_evidenced",
                        source_ref=source_ref,
                    )
                else:
                    record_omitted_edge(
                        source=source_id,
                        target=target_id,
                        edge_kind="unlocks",
                        source_ref=source_ref,
                        reason="endpoint_outside_visible_overview",
                    )

    for item_id in visible_cap_ids:
        item = work_items_by_id.get(item_id, {})
        for proof_ref in _cap_cartography_proof_refs(item, signoffs_by_work_item=signoffs_by_work_item)[:2]:
            proof_node_id = f"proof:{proof_ref}"
            if not add_support_node(
                {
                    "id": proof_node_id,
                    "label": proof_ref,
                    "node_kind": "proof_ref",
                    "display_role": "supporting_evidence",
                    "source_refs": [proof_ref],
                }
            ):
                continue
            add_edge(
                source=item_id,
                target=proof_node_id,
                edge_kind="has_proof",
                confidence="source_evidenced",
                source_ref=str(SIGNOFFS_REL),
            )
        for surface in _mission_operating_exact_surfaces(item)[:2]:
            path = str(surface.get("path") or "").strip()
            if not path:
                continue
            surface_node_id = f"integration_surface:{path}"
            if not add_support_node(
                {
                    "id": surface_node_id,
                    "label": path,
                    "node_kind": "integration_surface",
                    "display_role": "supporting_surface",
                    "state": surface.get("status") or "referenced",
                    "source_refs": [str(LEDGER_REL)],
                }
            ):
                continue
            add_edge(
                source=item_id,
                target=surface_node_id,
                edge_kind="lands_on",
                confidence="source_evidenced",
                source_ref=str(LEDGER_REL),
            )

    for item_id, row in cap_rows_by_id.items():
        if item_id in visible_cap_set:
            continue
        item = work_items_by_id.get(item_id, {})
        for cluster_id in row_cluster_ids.get(item_id, []):
            record_omitted_edge(
                source=item_id,
                target=cluster_id,
                edge_kind="member_of_cluster",
                source_ref=str(VIEWS_REL / "cap_census.json"),
                reason="cap_node_outside_visible_overview",
            )
        for proof_ref in _cap_cartography_proof_refs(item, signoffs_by_work_item=signoffs_by_work_item)[:2]:
            record_omitted_edge(
                source=item_id,
                target=f"proof:{proof_ref}",
                edge_kind="has_proof",
                source_ref=str(SIGNOFFS_REL),
                reason="cap_node_outside_visible_overview",
            )
        for surface in _mission_operating_exact_surfaces(item)[:2]:
            path = str(surface.get("path") or "").strip()
            if path:
                record_omitted_edge(
                    source=item_id,
                    target=f"integration_surface:{path}",
                    edge_kind="lands_on",
                    source_ref=str(LEDGER_REL),
                    reason="cap_node_outside_visible_overview",
                )

    for item_id in visible_cap_ids:
        row = cap_rows_by_id.get(item_id) or {}
        if row.get("in_mission_operating_picture"):
            add_edge(
                source=item_id,
                target="cluster:operating_picture:current_operating_picture",
                edge_kind="in_current_operating_picture",
                confidence="source_evidenced",
                source_ref=str(VIEWS_REL / "mission_operating_picture.json"),
            )

    cluster_confidence = {cluster["id"]: cluster["confidence"] for cluster in clusters}
    for item_id in visible_cap_ids:
        for cluster_id in row_cluster_ids.get(item_id, []):
            add_edge(
                source=item_id,
                target=cluster_id,
                edge_kind="member_of_cluster",
                confidence=cluster_confidence.get(cluster_id, "projection_inferred"),
                source_ref=str(VIEWS_REL / "cap_census.json"),
            )

    lineage_index = [
        {
            "display_id": item_id,
            "drilldown": {
                "task_ledger_card": (
                    "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                    f"{item_id}"
                ),
                "source_refs": _cap_cartography_source_refs(work_items_by_id.get(item_id, {})),
                "views": list(cap_rows_by_id.get(item_id, {}).get("views") or []),
                "proof_refs": _cap_cartography_proof_refs(
                    work_items_by_id.get(item_id, {}),
                    signoffs_by_work_item=signoffs_by_work_item,
                ),
                "missing_refs": _cap_cartography_missing_refs(cap_rows_by_id.get(item_id, {})),
            },
        }
        for item_id in visible_cap_ids
        if item_id in cap_rows_by_id
    ]

    warnings: List[Dict[str, Any]] = []
    cap_summary = cap_census.get("summary") if isinstance(cap_census.get("summary"), Mapping) else {}
    unclassified_count = int(cap_summary.get("unclassified_count") or 0)
    if unclassified_count:
        warnings.append(
            {
                "warning": "unclassified_caps_present",
                "count": unclassified_count,
                "reason": "semantic_role remains unknown for some cap rows; display as missing classification, not as source truth.",
            }
        )
    if edge_limit_hit:
        warnings.append(
            {
                "warning": "edge_limit_hit",
                "limit": CAP_CARTOGRAPHY_EDGE_LIMIT,
                "reason": "cartography view is bounded to keep overview first and drilldown explicit.",
            }
        )
    if support_node_limit_hit:
        warnings.append(
            {
                "warning": "support_node_limit_hit",
                "limit": CAP_CARTOGRAPHY_SUPPORT_NODE_LIMIT,
                "reason": "supporting proof/surface nodes are bounded; omitted support-node edges stay available in source views.",
            }
        )

    cluster_count = len(clusters)
    representative_node_count = sum(1 for node in nodes if node.get("node_kind") == "cap")
    default_cluster_count = sum(1 for cluster in clusters if cluster.get("default_visible"))
    edge_kind_counts = Counter(str(edge.get("edge_kind") or "unknown") for edge in edges)
    confidence_counts = Counter(str(edge.get("confidence") or "unknown") for edge in edges)
    resolvable_ids = {str(cluster.get("id") or "") for cluster in clusters}
    resolvable_ids.update(str(node.get("id") or "") for node in nodes)
    orphan_edge_count = sum(
        1
        for edge in edges
        if str(edge.get("source") or "") not in resolvable_ids
        or str(edge.get("target") or "") not in resolvable_ids
    )
    lineage_ids = {str(row.get("display_id") or "") for row in lineage_index}
    missing_lineage_count = sum(1 for item_id in visible_cap_ids if item_id not in lineage_ids)
    visible_cap_limit_hit = len(cap_rows_by_id) > len(visible_cap_set)
    cluster_representative_limit_hit = any(
        int(cluster.get("overflow_member_count") or 0) > 0 for cluster in clusters
    )
    omitted_edge_count = sum(omitted_edge_counts.values())
    overview_complete = not (
        edge_limit_hit
        or support_node_limit_hit
        or visible_cap_limit_hit
        or cluster_representative_limit_hit
        or omitted_edge_count
    )
    drilldown_index = [
        {
            "id": cluster["id"],
            "kind": "cluster",
            "cluster_kind": cluster["cluster_kind"],
            "value": cluster["value"],
            "member_count": cluster["member_count"],
            "representative_ids": list(cluster.get("representative_ids") or []),
            "member_sample_ids": list(cluster.get("member_sample_ids") or []),
            "overflow_member_count": cluster.get("overflow_member_count", 0),
            "missing_counts": dict(cluster.get("missing_counts") or {}),
            "source_evidence": cluster.get("source_evidence"),
            "confidence": cluster.get("confidence"),
            "source_route_metadata": dict(cluster.get("source_route_metadata") or {}),
            "unavailable_reason": None,
        }
        for cluster in clusters
    ]
    unclassified_rows = sorted(
        (row for row in cap_rows if row.get("semantic_role") == "unknown"),
        key=lambda row: _cap_cartography_row_rank_key(
            row,
            work_items_by_id.get(str(row.get("id") or "")),
        ),
    )
    unclassified_index = {
        "count": len(unclassified_rows),
        "sample_ids": [str(row.get("id") or "") for row in unclassified_rows[:CAP_CARTOGRAPHY_UNCLASSIFIED_SAMPLE_LIMIT]],
        "sample_rows": [
            {
                "id": str(row.get("id") or ""),
                "title": row.get("title"),
                "state": row.get("state"),
                "work_item_type": row.get("work_item_type"),
                "candidate_work_item_type": row.get("candidate_work_item_type"),
                "classification_basis": list(row.get("classification_basis") or []),
                "source_refs": _cap_cartography_source_refs(work_items_by_id.get(str(row.get("id") or ""), {})),
                "source_route_metadata": {
                    "task_ledger_card": (
                        "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                        f"{row.get('id')}"
                    ),
                    "source_view": str(VIEWS_REL / "cap_census.json"),
                },
            }
            for row in unclassified_rows[:CAP_CARTOGRAPHY_UNCLASSIFIED_SAMPLE_LIMIT]
        ],
        "reason": "semantic_role remains unknown under deterministic cap_census classification policy.",
        "missing_classification_basis": (
            "No stronger source field or deterministic role token matched; do not infer role from title alone."
        ),
        "candidate_fields_to_check": [
            "work_item_type",
            "candidate_work_item_type",
            "satisfaction_contract",
            "integration_contract",
            "tags",
            "proof_refs",
            "imagined_state_refs",
        ],
        "source_ref": str(VIEWS_REL / "cap_census.json"),
    }
    overflow_index = {
        "edge_limit_hit": edge_limit_hit,
        "support_node_limit_hit": support_node_limit_hit,
        "visible_cap_limit_hit": visible_cap_limit_hit,
        "cluster_representative_limit_hit": cluster_representative_limit_hit,
        "overview_complete": overview_complete,
        "included_edge_counts": dict(edge_kind_counts.most_common()),
        "omitted_edge_counts": dict(omitted_edge_counts.most_common()),
        "omitted_edge_count": omitted_edge_count,
        "omitted_by_source_ref": dict(omitted_by_source_ref.most_common()),
        "omitted_by_cluster_id": dict(omitted_by_cluster_id.most_common()),
        "omitted_sample": omitted_edge_samples,
        "expansion_routes": {
            "cluster_drilldown_index": "drilldown_index",
            "cap_census_source": str(VIEWS_REL / "cap_census.json"),
            "task_ledger_option_surface": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids <cap_id>"
            ),
            "projection_path": str(VIEWS_REL / "cap_cartography.json"),
        },
    }

    return {
        "kind": "task_ledger_view",
        "schema_version": CAP_CARTOGRAPHY_SCHEMA,
        "view_id": CAP_CARTOGRAPHY_VIEW_ID,
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "projection_inputs": list(CAP_CARTOGRAPHY_SOURCE_REFS),
            "mutation_rule": "read-only cap cartography projection; append Task Ledger events to change source facts",
            "classification_policy": (
                "visual semantics are source-evidenced when backed by state, signoff, view, dependency, or ref fields; "
                "semantic and temporal display roles inherited from cap_census remain projection-labeled"
            ),
        },
        "source_refs": list(CAP_CARTOGRAPHY_SOURCE_REFS),
        "summary": {
            **dict(cap_summary),
            "cluster_count": cluster_count,
            "visible_default_cluster_count": default_cluster_count,
            "representative_node_count": representative_node_count,
            "support_node_count": len(support_node_ids),
            "node_count": len(nodes),
            "edge_count": len(edges),
            "omitted_edge_count": omitted_edge_count,
            "lineage_index_count": len(lineage_index),
            "orphan_edge_count": orphan_edge_count,
            "missing_lineage_count": missing_lineage_count,
            "visible_cap_limit_hit": visible_cap_limit_hit,
            "cluster_representative_limit_hit": cluster_representative_limit_hit,
            "overview_complete": overview_complete,
            "warning_count": len(warnings),
            "mission_operating_picture_current_row_count": mission_operating_picture.get("summary", {}).get(
                "current_mission_count",
                cap_summary.get("mission_operating_picture_current_row_count"),
            )
            if isinstance(mission_operating_picture.get("summary"), Mapping)
            else cap_summary.get("mission_operating_picture_current_row_count"),
        },
        "levels": [
            {
                "id": "level:0:universe_summary",
                "label": "Universe summary",
                "source_ref": str(VIEWS_REL / "cap_census.json"),
                "display_contract": "overview first; aggregate counts before individual WorkItem expansion",
            },
            {
                "id": "level:1:cluster_map",
                "label": "Cluster map",
                "source_ref": str(VIEWS_REL / "cap_census.json"),
                "display_contract": "cluster by source-backed fields and projection-labeled roles",
            },
            {
                "id": "level:2:representative_nodes",
                "label": "Representative nodes",
                "source_ref": str(VIEWS_REL / "cap_cartography.json"),
                "display_contract": "bounded representative caps, not a raw dump of every cap row",
            },
            {
                "id": "level:3:typed_edges",
                "label": "Typed edges",
                "source_ref": str(VIEWS_REL / "dependency_graph.json"),
                "display_contract": "only source-evidenced graph/ref edges plus explicitly projection-labeled cluster membership",
            },
            {
                "id": "level:4:lineage_drilldown",
                "label": "Lineage drilldown",
                "source_ref": str(EVENTS_REL),
                "display_contract": "visible objects expose Task Ledger card route, source refs, proof refs, and missing refs",
            },
        ],
        "overflow_policy": {
            "overview_edge_limit": CAP_CARTOGRAPHY_EDGE_LIMIT,
            "support_node_limit": CAP_CARTOGRAPHY_SUPPORT_NODE_LIMIT,
            "representative_cap_node_limit": CAP_CARTOGRAPHY_VISIBLE_CAP_NODE_LIMIT,
            "cluster_representative_limit": CAP_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT,
            "bounded_overview": True,
            "reason": "overview-first cap cartography; drilldown_index/overflow_index are required for complete expansion",
        },
        "overflow_index": overflow_index,
        "drilldown_index": drilldown_index,
        "unclassified_index": unclassified_index,
        "clusters": clusters,
        "nodes": nodes,
        "edges": edges,
        "lineage_index": lineage_index,
        "legend": {
            "color_basis_options": ["temporal_role", "state", "semantic_role", "proof_readiness"],
            "size_basis_options": ["view_count", "member_count", "downstream_unlock_count"],
            "confidence_values": ["source_evidenced", "projection_inferred", "missing_source"],
            "frontend_posture": "observe_only; no cap creation controls or mutation commands are exposed as frontend actions",
            "edge_kind_counts": dict(edge_kind_counts.most_common()),
            "edge_confidence_counts": dict(confidence_counts.most_common()),
        },
        "warnings": warnings,
        "items": clusters,
        "count": cluster_count,
    }


def _cap_market_text(row: Mapping[str, Any], item: Mapping[str, Any]) -> str:
    parts = [
        row.get("id"),
        row.get("title"),
        row.get("state"),
        row.get("owner_lane"),
        row.get("blocker_class"),
        item.get("title"),
        item.get("statement"),
        item.get("body"),
        item.get("description"),
        item.get("status"),
        item.get("superseded_by"),
        item.get("resolution_note"),
    ]
    for field in ("tags", "labels", "evidence_refs", "receipt_refs", "depends_on"):
        value = item.get(field)
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            parts.extend(str(part) for part in value)
        elif value:
            parts.append(value)
    return " ".join(str(part or "") for part in parts).lower()


def _cap_market_failure_family(text: str) -> str:
    families = [
        (
            "bankruptcy_related",
            ("bankruptcy", "rescue-ref", "rescue ref", "dirty tree", "checkpoint", "publication", "ahead", "behind"),
        ),
        (
            "resource_plane_related",
            ("dev server", "vite", "playwright", "browser", "daemon", "resource lease", "host pressure", "cache", "watcher"),
        ),
        (
            "projection_settlement_related",
            ("projection settlement", "generated view", "generated_state_drainer", "projection queue", "settlement group"),
        ),
        (
            "claim_semantics_related",
            ("claim", "collision", "scope", "ownership", "path lease", "hard mutation", "same-path"),
        ),
        (
            "session_message_related",
            ("session message", "yield", "handoff", "signal", "workflow message", "heartbeat"),
        ),
        (
            "host_pressure_related",
            ("host pressure", "swap", "cpu", "memory pressure", "load shed", "throttle"),
        ),
    ]
    for family, needles in families:
        if any(needle in text for needle in needles):
            return family
    return "other_cap_family"


def _cap_market_current_compatibility(
    row: Mapping[str, Any],
    item: Mapping[str, Any],
    text: str,
) -> str:
    lifecycle = str(row.get("actionable_lifecycle_state") or "")
    state = str(row.get("state") or "")
    if lifecycle in {"retired", "superseded"} or state in {"done", "closed", "retired", "superseded"}:
        return "old_system_historical_signal"
    if item.get("superseded_by") or "0fefa7d1b" in text or "18b135e33" in text:
        return "superseded_by_landed_kernel"
    if not row.get("reentry_route"):
        return "dead_capture_no_reentry"
    if not bool(row.get("has_integration_contract")) and not bool(row.get("has_grounded_integration_surfaces")):
        return "needs_migration_to_current_schema"
    return "still_live_current_system"


def _cap_market_queue(
    *,
    lifecycle: str,
    failure_family: str,
    compatibility: str,
) -> str:
    if lifecycle in {"retired", "superseded"} or compatibility in {
        "old_system_historical_signal",
        "superseded_by_landed_kernel",
    }:
        return "historical_or_superseded"
    if lifecycle == "dependency_gated":
        return "dependency_gated"
    if failure_family in {
        "bankruptcy_related",
        "resource_plane_related",
        "projection_settlement_related",
        "claim_semantics_related",
        "session_message_related",
        "host_pressure_related",
    }:
        return "must_reenter_now"
    return "claimable_next"


def _build_cap_execution_market_view(
    *,
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
    cap_census: Mapping[str, Any],
    cap_cartography: Mapping[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    cap_rows = [row for row in cap_census.get("rows") or [] if isinstance(row, Mapping)]
    work_items_by_id = {_cap_census_item_id(item): item for item in work_items if _cap_census_item_id(item)}
    signed_off_ids = {
        str(signoff.get("work_item_id") or "").strip()
        for signoff in signoffs
        if str(signoff.get("work_item_id") or "").strip()
    }
    queue_rows: Dict[str, List[Dict[str, Any]]] = {queue: [] for queue in CAP_EXECUTION_MARKET_QUEUES}
    failure_counts: Counter[str] = Counter()
    compatibility_counts: Counter[str] = Counter()
    queue_counts: Counter[str] = Counter()
    heatmap_counts: Counter[tuple[str, str, str]] = Counter()
    items: List[Dict[str, Any]] = []

    for row in sorted(cap_rows, key=lambda candidate: str(candidate.get("id") or "")):
        cap_id = str(row.get("id") or "").strip()
        if not cap_id:
            continue
        item = work_items_by_id.get(cap_id, {})
        text = _cap_market_text(row, item)
        lifecycle = str(row.get("actionable_lifecycle_state") or "visible")
        failure_family = _cap_market_failure_family(text)
        compatibility = _cap_market_current_compatibility(row, item, text)
        if cap_id in signed_off_ids and compatibility == "still_live_current_system":
            compatibility = "old_system_historical_signal"
        queue_id = _cap_market_queue(
            lifecycle=lifecycle,
            failure_family=failure_family,
            compatibility=compatibility,
        )
        stale_age_days = row.get("stale_age_days") if isinstance(row.get("stale_age_days"), int) else None
        dependency_state = "gated" if lifecycle == "dependency_gated" or int(row.get("dependency_ref_count") or 0) else "clear"
        market_row = {
            "cap_id": cap_id,
            "id": cap_id,
            "title": row.get("title"),
            "queue_id": queue_id,
            "lifecycle_state": lifecycle,
            "state": row.get("state"),
            "owner_lane": row.get("owner_lane"),
            "dependency_state": dependency_state,
            "dependency_refs": list(row.get("dependency_refs") or []),
            "stale_age_days": stale_age_days,
            "blocker_class": row.get("blocker_class"),
            "failure_family": failure_family,
            "current_system_compatibility": compatibility,
            "current_value": "high" if queue_id == "must_reenter_now" else "medium" if queue_id == "claimable_next" else "reference",
            "risk_if_ignored": (
                "live_concurrency_or_settlement_pressure_stays_unrouted"
                if queue_id == "must_reenter_now"
                else "older_capture_continues_to_occupy_attention_without_execution"
            ),
            "estimated_effort": "small_to_medium_projection_or_control_patch",
            "reentry_command": row.get("reentry_route"),
            "retirement_condition": "land evidence refs, set lifecycle retired/superseded, or attach proof-backed signoff",
            "next_claimable_surface": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                f"{cap_id}"
            ),
            "superseded_by": item.get("superseded_by"),
            "trace_hud_visible": queue_id in {"must_reenter_now", "claimable_next", "dependency_gated"},
            "source_refs": _cap_cartography_source_refs(item),
            "projection_basis": {
                "cap_census_fields": [
                    "actionable_lifecycle_state",
                    "owner_lane",
                    "dependency_refs",
                    "blocker_class",
                    "stale_age_days",
                ],
                "cap_cartography_summary_seen": bool(cap_cartography.get("summary")),
            },
        }
        items.append(market_row)
        queue_rows.setdefault(queue_id, []).append(market_row)
        failure_counts[failure_family] += 1
        compatibility_counts[compatibility] += 1
        queue_counts[queue_id] += 1
        heatmap_counts[(failure_family, compatibility, queue_id)] += 1

    heatmap = [
        {
            "failure_family": family,
            "current_system_compatibility": compatibility,
            "queue_id": queue_id,
            "count": count,
        }
        for (family, compatibility, queue_id), count in sorted(
            heatmap_counts.items(),
            key=lambda item: (-item[1], item[0][0], item[0][1], item[0][2]),
        )
    ]
    queues = {
        queue_id: {
            "queue_id": queue_id,
            "count": len(rows),
            "cap_ids": [str(row.get("cap_id") or "") for row in rows],
            "items": rows,
        }
        for queue_id, rows in queue_rows.items()
    }
    return {
        "kind": "task_ledger_view",
        "schema_version": CAP_EXECUTION_MARKET_SCHEMA,
        "view_id": CAP_EXECUTION_MARKET_VIEW_ID,
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "projection_inputs": list(CAP_EXECUTION_MARKET_SOURCE_REFS),
            "mutation_rule": "read-only CAP execution market; append Task Ledger events to change source facts",
            "classification_policy": "queues and failure families are deterministic projections over cap_census/cap_cartography fields",
        },
        "source_refs": list(CAP_EXECUTION_MARKET_SOURCE_REFS),
        "summary": {
            "cap_count": len(items),
            "must_reenter_now_count": queue_counts.get("must_reenter_now", 0),
            "claimable_next_count": queue_counts.get("claimable_next", 0),
            "dependency_gated_count": queue_counts.get("dependency_gated", 0),
            "historical_or_superseded_count": queue_counts.get("historical_or_superseded", 0),
            "failure_family_count": len(failure_counts),
            "compatibility_class_count": len(compatibility_counts),
        },
        "queue_counts": dict(queue_counts.most_common()),
        "failure_family_counts": dict(failure_counts.most_common()),
        "current_system_compatibility_counts": dict(compatibility_counts.most_common()),
        "heatmap": heatmap,
        "queues": queues,
        "items": items,
        "count": len(items),
    }


def _compute_queue_membership_crosswalk(
    repo_root: Optional[Path],
) -> "tuple[frozenset[str], Dict[str, Any]]":
    """
    Resolve Task Ledger ↔ Work Ledger queue membership via canonical
    structured metadata. NO fuzzy matching, NO title heuristics — only
    explicit-field Tier-1 mappings.

    Read order per Work Ledger thread (first match wins):
      1. metadata.task_ledger_work_item_id         (preferred canonical
         convention, propagated at creation time after Wave 1D.5)
      2. metadata.task_ledger_work_item_bridge.task_ledger_work_item_id
         (existing work_landing_status.py convention — many pre-1D.5
         threads already carry it nested inside the bridge sub-dict)
      3. metadata.subject_id                       (legacy fallback)

    Returns (queue_visible_set, stats). stats now distinguishes:
      - queue_row_count         : total Work Ledger rows scanned
      - mapped_queue_row_count  : rows where any Tier-1 field resolved
      - unique_work_item_id_count: cardinality of the harvested set
      - unjoined_queue_row_count: rows with no Tier-1 field
      - join_methods            : breakdown by field source

    These are NOT interchangeable units; the frontend must label each
    explicitly. Conflating "stamped Atlas marks" with "queue rows" is
    the accounting bug Wave 1D.5 closes.
    """
    stats: Dict[str, Any] = {
        "schema_version": "work_identity_crosswalk_v0",
        "available": False,
        "queue_row_count": 0,
        "mapped_queue_row_count": 0,
        "unique_work_item_id_count": 0,
        "unjoined_queue_row_count": 0,
        "join_methods": {
            "explicit_field_task_ledger_work_item_id": 0,
            "explicit_field_task_ledger_work_item_bridge": 0,
            "explicit_field_subject_id": 0,
        },
        "reason": None,
    }
    if repo_root is None:
        stats["reason"] = "repo_root not threaded into build_views"
        return frozenset(), stats
    try:
        from system.lib import work_ledger as _wl  # local import: avoid module-load cycles

        projection = _wl.load_projection(repo_root)
    except Exception as exc:  # noqa: BLE001 — diagnostic must not crash projection rebuild
        stats["reason"] = f"work_ledger.load_projection failed: {type(exc).__name__}: {exc}"
        return frozenset(), stats

    queue_visible: Set[str] = set()
    seen_td_ids: Set[str] = set()
    stale_td_ids: Set[str] = set()
    queue_row_count = 0
    mapped_queue_rows = 0
    via_canonical = 0
    via_bridge = 0
    via_subject = 0
    via_deep_field: Dict[str, int] = {}
    unjoined = 0

    # Wave 1D.6: deep-field recovery for legacy threads. After the Wave 1D.5
    # recon proved that 7 of 71 unjoined open threads carry the canonical
    # work_item_id in lesser-known structured metadata fields (work_item_id,
    # task_ledger_capture_id, receipt_target_id, signoff_id, blocker_capture,
    # side_capture_id), the harvester reads these as Tier-1 explicit fields
    # so long as the value looks like a cap_*/work_item id (NOT a td_*).
    # This is still explicit-field extraction — no fuzzy matching, no prose
    # title/body scanning.
    _DEEP_FIELDS_REQUIRING_CAP_PREFIX = (
        "receipt_target_id",
        "signoff_id",
    )
    _DEEP_FIELDS_UNRESTRICTED = (
        "work_item_id",
        "task_ledger_capture_id",
        "blocker_capture",
        "side_capture_id",
    )

    def _looks_like_work_item_id(value: str) -> bool:
        s = value.strip()
        if not s:
            return False
        # Reject Work Ledger thread ids; accept cap_* and bare descriptive
        # WorkItem ids (the Task Ledger atlas_marks namespace).
        if s.startswith("td_"):
            return False
        return True

    def _extract_work_item_id(md: Mapping[str, Any]) -> "tuple[Optional[str], Optional[str]]":
        canonical = md.get("task_ledger_work_item_id")
        if canonical:
            return str(canonical), "task_ledger_work_item_id"
        bridge = md.get("task_ledger_work_item_bridge")
        if isinstance(bridge, Mapping):
            bid = bridge.get("task_ledger_work_item_id")
            if bid:
                return str(bid), "task_ledger_work_item_bridge"
        sid = md.get("subject_id")
        if sid:
            return str(sid), "subject_id"
        # Wave 1D.6 deep-field recovery (legacy thread coverage):
        for field in _DEEP_FIELDS_UNRESTRICTED:
            value = md.get(field)
            if value and _looks_like_work_item_id(str(value)):
                return str(value), f"deep_field_{field}"
        for field in _DEEP_FIELDS_REQUIRING_CAP_PREFIX:
            value = md.get(field)
            if value:
                s = str(value).strip()
                if s.startswith("cap_") and _looks_like_work_item_id(s):
                    return s, f"deep_field_{field}"
        return None, None

    def _harvest_rows(rows: Iterable[Mapping[str, Any]], *, stale: bool = False) -> None:
        """Count each Work Ledger thread exactly once. ``stale_open`` is a
        projection over the same open threads as ``open_by_actor`` — counting
        both as independent queue rows would double-count the stale subset
        and silently inflate every downstream coverage ratio."""
        nonlocal queue_row_count, mapped_queue_rows, via_canonical, via_bridge, via_subject, unjoined
        for row in rows or []:
            td_id = str(row.get("td_id") or row.get("root_td_id") or "").strip()
            if stale and td_id:
                stale_td_ids.add(td_id)
            if td_id and td_id in seen_td_ids:
                continue
            if td_id:
                seen_td_ids.add(td_id)
            queue_row_count += 1
            md = row.get("metadata") or {}
            wid, method = _extract_work_item_id(md)
            if wid is None:
                unjoined += 1
                continue
            mapped_queue_rows += 1
            queue_visible.add(wid)
            if method == "task_ledger_work_item_id":
                via_canonical += 1
            elif method == "task_ledger_work_item_bridge":
                via_bridge += 1
            elif method == "subject_id":
                via_subject += 1
            elif method and method.startswith("deep_field_"):
                via_deep_field[method] = via_deep_field.get(method, 0) + 1

    open_by_actor = projection.get("open_by_actor") or {}
    if isinstance(open_by_actor, Mapping):
        for actor_rows in open_by_actor.values():
            if isinstance(actor_rows, list):
                _harvest_rows(actor_rows, stale=False)
    stale_open = projection.get("stale_open")
    if isinstance(stale_open, list):
        _harvest_rows(stale_open, stale=True)

    stats["available"] = True
    stats["queue_row_count"] = queue_row_count
    stats["mapped_queue_row_count"] = mapped_queue_rows
    stats["unique_work_item_id_count"] = len(queue_visible)
    stats["unjoined_queue_row_count"] = unjoined
    stats["stale_queue_row_count"] = len(stale_td_ids)
    stats["dedupe_key"] = "td_id"
    stats["join_methods"]["explicit_field_task_ledger_work_item_id"] = via_canonical
    stats["join_methods"]["explicit_field_task_ledger_work_item_bridge"] = via_bridge
    stats["join_methods"]["explicit_field_subject_id"] = via_subject
    for method, count in via_deep_field.items():
        stats["join_methods"][method] = count
    return frozenset(queue_visible), stats


def _build_workitem_cartography_view(
    *,
    work_items: Sequence[Mapping[str, Any]],
    dependency_views: Mapping[str, Mapping[str, Any]],
    generated_at: str,
    queue_visible_ids: Optional[Set[str]] = None,
    queue_membership_stats: Optional[Mapping[str, Any]] = None,
    owner_view_id_sets: Optional[Mapping[str, Set[str]]] = None,
) -> Dict[str, Any]:
    """
    [ACTION]
    - Teleology: Generate a sibling cartography view that ranges over the full
      WorkItem ledger (not just CAPs), exposing an `atlas_marks` row-grain
      universe plus a bounded representative graph layer that mirrors the
      `cap_cartography` consumption contract grammar.
    - Mechanism: Build clusters across universal axes (state, work_item_type,
      actor, family, route_status); emit one mark per WorkItem; pick a bounded
      slice of visible nodes ranked by signoff/blocked/stale/downstream-unlock
      pressure; emit dependency/unlock/member-of-cluster edges over the visible
      slice; record explicit omission receipts for CAP-specific structures
      (proof refs, support nodes, semantic-role lineage) skipped for v0.
    - Guarantee: Read-only. `route.status="unknown"` is labeled `unrouted` in
      the legend and overlay layer; it is never relabeled as carryover, since
      origin/current-scope semantics do not exist in the substrate yet.
    """
    items_by_id: Dict[str, Mapping[str, Any]] = {}
    for item in work_items:
        item_id = str(item.get("id") or item.get("subject_id") or "").strip()
        if item_id:
            items_by_id[item_id] = item

    dependency_items_by_id: Dict[str, Mapping[str, Any]] = {}
    for row in dependency_views.get("dependency_graph", {}).get("items", []) or []:
        if isinstance(row, Mapping):
            dep_id = str(row.get("id") or row.get("subject_id") or "").strip()
            if dep_id:
                dependency_items_by_id[dep_id] = row

    def _depends_on_count(item_id: str, item: Mapping[str, Any]) -> int:
        dep_row = dependency_items_by_id.get(item_id, {})
        depends_on = dep_row.get("depends_on") if isinstance(dep_row, Mapping) else None
        if not isinstance(depends_on, Sequence) or isinstance(depends_on, (str, bytes)):
            depends_on = item.get("depends_on")
        if not isinstance(depends_on, Sequence) or isinstance(depends_on, (str, bytes)):
            return 0
        return len([dep for dep in depends_on if isinstance(dep, str) and dep.strip()])

    def _downstream_unlock_count(item_id: str) -> int:
        dep_row = dependency_items_by_id.get(item_id, {})
        if not isinstance(dep_row, Mapping):
            return 0
        status = dep_row.get("dependency_status")
        if not isinstance(status, Mapping):
            return 0
        edges = status.get("downstream_unlock_edges")
        if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes)):
            return len([edge for edge in edges if isinstance(edge, Mapping)])
        ids = status.get("downstream_unlock_ids")
        if isinstance(ids, Sequence) and not isinstance(ids, (str, bytes)):
            return len([entry for entry in ids if entry])
        return int(status.get("downstream_count") or 0)

    def _is_blocked(item: Mapping[str, Any]) -> bool:
        state = str(item.get("state") or item.get("status") or "").lower()
        if state == "blocked":
            return True
        return bool(item.get("blocked"))

    def _is_stale(item: Mapping[str, Any]) -> bool:
        state = str(item.get("state") or "").lower()
        return state == "stale" or bool(item.get("stale"))

    def _needs_signoff(item: Mapping[str, Any]) -> bool:
        completion = item.get("completion") if isinstance(item.get("completion"), Mapping) else {}
        projection = (
            item.get("projection_completeness")
            if isinstance(item.get("projection_completeness"), Mapping)
            else {}
        )
        if completion.get("signoff_required") or projection.get("needs_signoff"):
            return True
        state = str(item.get("state") or "").lower()
        return state == "signoff"

    cluster_rows: Dict[str, Dict[str, Any]] = {}
    cluster_member_ids: Dict[str, List[str]] = defaultdict(list)
    item_cluster_ids: Dict[str, List[str]] = defaultdict(list)

    item_actor: Dict[str, str] = {}
    item_family: Dict[str, str] = {}
    item_route: Dict[str, Dict[str, Any]] = {}
    item_depends_on: Dict[str, int] = {}
    item_downstream: Dict[str, int] = {}
    item_blocked: Dict[str, bool] = {}
    item_stale: Dict[str, bool] = {}
    item_needs_signoff: Dict[str, bool] = {}

    for item_id, item in items_by_id.items():
        actor = _workitem_cartography_actor(item)
        family = _workitem_cartography_family(item)
        route = _workitem_cartography_route(item)
        item_actor[item_id] = actor
        item_family[item_id] = family
        item_route[item_id] = route
        item_depends_on[item_id] = _depends_on_count(item_id, item)
        item_downstream[item_id] = _downstream_unlock_count(item_id)
        item_blocked[item_id] = _is_blocked(item)
        item_stale[item_id] = _is_stale(item)
        item_needs_signoff[item_id] = _needs_signoff(item)

        for spec in _workitem_cartography_cluster_specs(
            item, actor=actor, family=family, route=route
        ):
            cluster_kind = str(spec["cluster_kind"])
            value = str(spec["value"])
            cluster_id = f"cluster:{cluster_kind}:{_cap_cartography_slug(value)}"
            cluster_rows.setdefault(
                cluster_id,
                {
                    "id": cluster_id,
                    "label": _cap_cartography_label(value),
                    "cluster_kind": cluster_kind,
                    "value": value,
                    "source_evidence": spec["source_evidence"],
                    "confidence": spec["confidence"],
                },
            )
            cluster_member_ids[cluster_id].append(item_id)
            item_cluster_ids[item_id].append(cluster_id)

    clusters: List[Dict[str, Any]] = []
    for cluster_id, cluster in sorted(
        cluster_rows.items(), key=lambda entry: (entry[1]["cluster_kind"], entry[1]["value"])
    ):
        member_ids = cluster_member_ids[cluster_id]
        ranked_members = sorted(
            member_ids,
            key=lambda mid: _workitem_cartography_row_rank_key(
                items_by_id.get(mid, {}),
                downstream_unlock_count=item_downstream.get(mid, 0),
                is_blocked=item_blocked.get(mid, False),
                is_stale=item_stale.get(mid, False),
                needs_signoff=item_needs_signoff.get(mid, False),
            ),
        )
        reps = ranked_members[:WORKITEM_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT]
        states_counter = Counter(
            str(items_by_id.get(mid, {}).get("state") or "unknown") for mid in member_ids
        )
        types_counter = Counter(
            str(
                items_by_id.get(mid, {}).get("work_item_type")
                or items_by_id.get(mid, {}).get("candidate_work_item_type")
                or "unknown"
            )
            for mid in member_ids
        )
        actors_counter = Counter(item_actor.get(mid, "unassigned") for mid in member_ids)
        unrouted = sum(
            1 for mid in member_ids if item_route.get(mid, {}).get("status") == "unknown"
        )
        blocked_count = sum(1 for mid in member_ids if item_blocked.get(mid))
        stale_count = sum(1 for mid in member_ids if item_stale.get(mid))
        signoff_count = sum(1 for mid in member_ids if item_needs_signoff.get(mid))
        route_metadata = _workitem_cartography_drilldown_route_metadata(
            cluster_kind=str(cluster["cluster_kind"]),
            value=str(cluster["value"]),
        )
        clusters.append(
            {
                **cluster,
                "member_count": len(member_ids),
                "representative_ids": list(reps),
                "member_sample_ids": list(ranked_members[:8]),
                "overflow_member_count": max(0, len(member_ids) - len(reps)),
                "dominant_states": dict(states_counter.most_common(5)),
                "dominant_work_item_types": dict(types_counter.most_common(5)),
                "dominant_actors": dict(actors_counter.most_common(5)),
                "anomaly_counts": {
                    "unrouted": unrouted,
                    "blocked": blocked_count,
                    "stale": stale_count,
                    "signoff_required": signoff_count,
                },
                "default_visible": cluster["cluster_kind"] in {"state", "work_item_type", "route_status"},
                "classification_basis": (
                    "source field cluster"
                    if cluster["confidence"] == "source_evidenced"
                    else "deterministic projection over WorkItem row fields"
                ),
                "drilldown_available": True,
                "source_route_metadata": route_metadata,
                "member_drilldown_policy": (
                    "Use source_route_metadata.member_filter against ledger.work_items rows; "
                    "representative_ids/member_sample_ids are bounded overview hints."
                ),
            }
        )

    queue_visible_set: Set[str] = set(queue_visible_ids or ())
    stamped_atlas_mark_count = 0
    atlas_marks: List[Dict[str, Any]] = []
    for item_id, item in items_by_id.items():
        is_queue_visible = item_id in queue_visible_set
        if is_queue_visible:
            stamped_atlas_mark_count += 1
        atlas_marks.append(
            _workitem_cartography_mark(
                item,
                actor=item_actor[item_id],
                family=item_family[item_id],
                route=item_route[item_id],
                cluster_ids=item_cluster_ids.get(item_id, []),
                depends_on_count=item_depends_on.get(item_id, 0),
                downstream_unlock_count=item_downstream.get(item_id, 0),
                is_blocked=item_blocked.get(item_id, False),
                is_stale=item_stale.get(item_id, False),
                needs_signoff=item_needs_signoff.get(item_id, False),
                queue_visible=is_queue_visible,
            )
        )
    # Coverage breakdown — the frontend must label these distinct units so
    # the operator never sees "mark count of N" reported as "queue row count".
    queue_membership_full: Dict[str, Any] = dict(queue_membership_stats or {"available": False})
    if queue_membership_full.get("available"):
        queue_membership_full["stamped_atlas_mark_count"] = stamped_atlas_mark_count
        unique_count = int(queue_membership_full.get("unique_work_item_id_count") or 0)
        queue_membership_full["unmapped_work_item_id_count"] = max(
            unique_count - stamped_atlas_mark_count, 0
        )
        coverage_state = (
            "mapped_full"
            if (
                stamped_atlas_mark_count > 0
                and int(queue_membership_full.get("unjoined_queue_row_count") or 0) == 0
            )
            else (
                "mapped_partial"
                if stamped_atlas_mark_count > 0
                else "unavailable"
            )
        )
        if int(queue_membership_full.get("queue_row_count") or 0) == 0:
            coverage_state = "empty"
        queue_membership_full["coverage_state"] = coverage_state

    ranked_items = sorted(
        items_by_id.keys(),
        key=lambda mid: _workitem_cartography_row_rank_key(
            items_by_id.get(mid, {}),
            downstream_unlock_count=item_downstream.get(mid, 0),
            is_blocked=item_blocked.get(mid, False),
            is_stale=item_stale.get(mid, False),
            needs_signoff=item_needs_signoff.get(mid, False),
        ),
    )
    visible_node_ids = ranked_items[:WORKITEM_CARTOGRAPHY_VISIBLE_NODE_LIMIT]
    visible_node_set = set(visible_node_ids)
    visible_node_limit_hit = len(items_by_id) > len(visible_node_set)

    nodes: List[Dict[str, Any]] = []
    for item_id in visible_node_ids:
        item = items_by_id[item_id]
        nodes.append(
            _workitem_cartography_node(
                item,
                actor=item_actor[item_id],
                family=item_family[item_id],
                route=item_route[item_id],
                cluster_ids=item_cluster_ids.get(item_id, []),
                downstream_unlock_count=item_downstream.get(item_id, 0),
                is_blocked=item_blocked.get(item_id, False),
                is_stale=item_stale.get(item_id, False),
                needs_signoff=item_needs_signoff.get(item_id, False),
            )
        )

    edges: List[Dict[str, Any]] = []
    edge_ids: set[str] = set()
    edge_limit_hit = False
    omitted_edge_counts: Counter[str] = Counter()
    omitted_edge_samples: List[Dict[str, Any]] = []

    def _record_omitted_edge(*, source: str, target: str, edge_kind: str, source_ref: str, reason: str) -> None:
        if not source or not target:
            return
        omitted_edge_counts[edge_kind] += 1
        if len(omitted_edge_samples) < WORKITEM_CARTOGRAPHY_OMITTED_EDGE_SAMPLE_LIMIT:
            omitted_edge_samples.append(
                {
                    "source": source,
                    "target": target,
                    "edge_kind": edge_kind,
                    "source_ref": source_ref,
                    "reason": reason,
                }
            )

    def _add_edge(*, source: str, target: str, edge_kind: str, confidence: str, source_ref: str) -> None:
        nonlocal edge_limit_hit
        if not source or not target:
            return
        edge_id = f"edge:{edge_kind}:{source}->{target}"
        if edge_id in edge_ids:
            return
        if len(edges) >= WORKITEM_CARTOGRAPHY_EDGE_LIMIT:
            edge_limit_hit = True
            _record_omitted_edge(
                source=source, target=target, edge_kind=edge_kind, source_ref=source_ref, reason="edge_limit"
            )
            return
        edge_ids.add(edge_id)
        edges.append(
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "edge_kind": edge_kind,
                "confidence": confidence,
                "source_ref": source_ref,
            }
        )

    dependency_source_ref = str(VIEWS_REL / "dependency_graph.json")
    unlocks_source_ref = str(VIEWS_REL / "unlocks_by_rank.json")
    for item_id in visible_node_ids:
        dep_row = dependency_items_by_id.get(item_id, {})
        depends_on = dep_row.get("depends_on") if isinstance(dep_row, Mapping) else []
        if isinstance(depends_on, Sequence) and not isinstance(depends_on, (str, bytes)):
            for dep_id in depends_on:
                if not isinstance(dep_id, str):
                    continue
                dep_id = dep_id.strip()
                if not dep_id or dep_id not in items_by_id:
                    continue
                if dep_id in visible_node_set:
                    _add_edge(
                        source=item_id,
                        target=dep_id,
                        edge_kind="depends_on",
                        confidence="source_evidenced",
                        source_ref=dependency_source_ref,
                    )
                else:
                    _record_omitted_edge(
                        source=item_id,
                        target=dep_id,
                        edge_kind="depends_on",
                        source_ref=dependency_source_ref,
                        reason="endpoint_outside_visible_overview",
                    )
        status = dep_row.get("dependency_status") if isinstance(dep_row, Mapping) else None
        if isinstance(status, Mapping):
            unlock_edges = status.get("downstream_unlock_edges")
            if isinstance(unlock_edges, Sequence) and not isinstance(unlock_edges, (str, bytes)):
                for unlock in unlock_edges:
                    if not isinstance(unlock, Mapping):
                        continue
                    target_id = str(unlock.get("id") or "").strip()
                    if not target_id or target_id not in items_by_id:
                        continue
                    if target_id in visible_node_set:
                        _add_edge(
                            source=item_id,
                            target=target_id,
                            edge_kind="unlocks",
                            confidence="source_evidenced",
                            source_ref=unlocks_source_ref,
                        )
                    else:
                        _record_omitted_edge(
                            source=item_id,
                            target=target_id,
                            edge_kind="unlocks",
                            source_ref=unlocks_source_ref,
                            reason="endpoint_outside_visible_overview",
                        )

    cluster_confidence = {cluster["id"]: cluster["confidence"] for cluster in clusters}
    cluster_source_ref = str(LEDGER_REL)
    for item_id in visible_node_ids:
        for cluster_id in item_cluster_ids.get(item_id, []):
            _add_edge(
                source=item_id,
                target=cluster_id,
                edge_kind="member_of_cluster",
                confidence=cluster_confidence.get(cluster_id, "projection_inferred"),
                source_ref=cluster_source_ref,
            )

    lineage_index = [
        {
            "display_id": item_id,
            "drilldown": {
                "task_ledger_card": (
                    "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                    f"{item_id}"
                ),
                "source_refs": _workitem_cartography_source_refs(items_by_id.get(item_id, {})),
                "route": dict(item_route.get(item_id, {})),
                "missing_refs": _workitem_cartography_missing_refs(items_by_id.get(item_id, {})),
                "omitted_fields": [
                    "proof_refs (CAP-specific signoff lookup; omitted for workitem_cartography_v0)",
                ],
            },
        }
        for item_id in visible_node_ids
    ]

    resolvable_ids = {cluster["id"] for cluster in clusters}
    resolvable_ids.update(node["id"] for node in nodes)
    orphan_edge_count = sum(
        1
        for edge in edges
        if edge["source"] not in resolvable_ids or edge["target"] not in resolvable_ids
    )
    lineage_ids = {row["display_id"] for row in lineage_index}
    missing_lineage_count = sum(1 for nid in visible_node_ids if nid not in lineage_ids)
    cluster_representative_limit_hit = any(
        int(cluster.get("overflow_member_count") or 0) > 0 for cluster in clusters
    )
    omitted_edge_count = sum(omitted_edge_counts.values())
    overview_complete = not (
        edge_limit_hit
        or visible_node_limit_hit
        or cluster_representative_limit_hit
        or omitted_edge_count
    )

    nodes_missing_basis = sum(
        1
        for node in nodes
        if not node.get("source_refs") and not node.get("cluster_ids")
    )
    unrouted_count = sum(1 for mark in atlas_marks if mark["overlays"]["unrouted"])
    blocked_total = sum(1 for mark in atlas_marks if mark["overlays"]["blocked"])
    stale_total = sum(1 for mark in atlas_marks if mark["overlays"]["stale"])
    signoff_total = sum(1 for mark in atlas_marks if mark["overlays"]["signoff_required"])
    state_counts = Counter(mark["state"] for mark in atlas_marks)
    type_counts = Counter(mark["work_item_type"] for mark in atlas_marks)
    # Wave 2A — route provenance aggregates. Counts ride the same per-mark
    # universe used by the unrouted overlay; the explained/unknown split
    # surfaces how much of the unrouted bucket the taxonomy actually
    # explains so the consumer contract can fail loud if coverage falls.
    route_reason_counts: Counter[str] = Counter()
    route_reason_kind_counts: Counter[str] = Counter()
    route_reason_secondary_counts: Counter[str] = Counter()
    route_reason_predicate_kind_counts: Counter[str] = Counter()
    route_reason_sample_ids: Dict[str, List[str]] = defaultdict(list)
    route_provenance_explained_count = 0
    route_provenance_unknown_count = 0
    # Wave 2A.1 — per-mark evidence-shape audit. A mark is counted as
    # "evidence-clean" when its route_explanation carries either at least
    # one evidence_ref OR at least one evidence_field (terminal /
    # state_transitioned reasons are field-only). Missing both is a
    # contract violation — the audit summary names the offending reasons.
    route_provenance_evidence_ok_count = 0
    route_provenance_evidence_missing_count = 0
    route_provenance_evidence_missing_reasons: Counter[str] = Counter()
    for mark in atlas_marks:
        if not mark["overlays"]["unrouted"]:
            continue
        explanation = mark.get("route_explanation") or {}
        primary = str(explanation.get("route_reason") or WORKITEM_ROUTE_REASON_UNKNOWN)
        route_reason_counts[primary] += 1
        kind = str(explanation.get("reason_kind") or "actionable")
        route_reason_kind_counts[kind] += 1
        predicate_kind = str(explanation.get("predicate_kind") or "fallback_no_predicate_fired")
        route_reason_predicate_kind_counts[predicate_kind] += 1
        for secondary in explanation.get("secondary_reasons") or ():
            route_reason_secondary_counts[str(secondary)] += 1
        if primary == WORKITEM_ROUTE_REASON_UNKNOWN:
            route_provenance_unknown_count += 1
        else:
            route_provenance_explained_count += 1
        sample = route_reason_sample_ids[primary]
        if len(sample) < 5:
            sample.append(str(mark.get("id") or ""))
        evidence_refs = explanation.get("evidence_refs") or []
        evidence_fields = explanation.get("evidence_fields") or []
        if evidence_refs or evidence_fields:
            route_provenance_evidence_ok_count += 1
        else:
            route_provenance_evidence_missing_count += 1
            route_provenance_evidence_missing_reasons[primary] += 1

    # Wave 2D — build resolution_affordances rows with measured
    # lane_relationship overlap counts. Precomputes per-reason id sets so
    # the dict comprehension stays O(reasons + marks), not O(reasons × marks).
    reason_id_sets: Dict[str, Set[str]] = defaultdict(set)
    for mark in atlas_marks:
        if not mark.get("overlays", {}).get("unrouted"):
            continue
        primary_reason = (
            (mark.get("route_explanation") or {}).get("route_reason")
            or WORKITEM_ROUTE_REASON_UNKNOWN
        )
        mark_id = mark.get("id")
        if mark_id:
            reason_id_sets[str(primary_reason)].add(str(mark_id))
    owner_view_lookup: Mapping[str, Set[str]] = owner_view_id_sets or {}
    # Wave 2F — materialize Task Ledger card routes per sample row so the
    # UI can render addressable drillthrough without string substitution
    # on the client. Title lookup uses the existing atlas_marks set
    # (same id namespace as reason_id_sets).
    atlas_mark_by_id: Dict[str, Mapping[str, Any]] = {
        str(mark.get("id")): mark
        for mark in atlas_marks
        if mark.get("id")
    }
    DRILLTHROUGH_SAMPLE_LIMIT = 3

    def _materialize_card_route(card_template: Optional[str], item_id: str) -> Optional[str]:
        if not card_template or not item_id:
            return None
        return str(card_template).replace("{id}", str(item_id))

    def _drillthrough_sample_row(
        item_id: str,
        *,
        card_template: Optional[str],
        sample_kind: str,
    ) -> Dict[str, Any]:
        mark = atlas_mark_by_id.get(item_id) or {}
        title = str(mark.get("title") or item_id)
        return {
            "id": item_id,
            "title": title,
            "sample_kind": sample_kind,
            "card_route": _materialize_card_route(card_template, item_id),
            "route_materialized": bool(card_template),
        }

    resolution_affordances_built: Dict[str, Dict[str, Any]] = {}
    resolution_lane_relationship_counts: Counter[str] = Counter()
    resolution_drillthrough_materialized_count = 0
    for reason in list(WORKITEM_ROUTE_REASON_PRIORITY) + [WORKITEM_ROUTE_REASON_UNKNOWN]:
        if route_reason_counts.get(reason, 0) == 0:
            continue
        static = WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.get(reason, {})
        owner_view = static.get("owner_view")
        owner_ids: Optional[Set[str]] = (
            owner_view_lookup.get(owner_view) if owner_view else None
        )
        reason_ids = reason_id_sets.get(reason, set())
        relationship = _classify_lane_relationship(
            reason=reason,
            affordance=static,
            reason_ids=reason_ids,
            owner_view_ids=owner_ids,
        )
        resolution_lane_relationship_counts[relationship] += 1
        if owner_ids is None:
            owner_item_count = None
            overlap_count = None
            overlap_sample: List[str] = []
        else:
            overlap_ids = reason_ids & owner_ids
            owner_item_count = len(owner_ids)
            overlap_count = len(overlap_ids)
            overlap_sample = sorted(overlap_ids)[:DRILLTHROUGH_SAMPLE_LIMIT]
        # Wave 2F — build a materialized drillthrough block per affordance.
        # Each sample row carries an executable Task Ledger card route
        # (id substituted into static.card_route_template). owner_surface
        # is populated from static.option_surface_ref (cluster_flag form).
        reason_sample_seed = list(route_reason_sample_ids.get(reason, [])[:DRILLTHROUGH_SAMPLE_LIMIT])
        card_template = static.get("card_route_template")
        reason_sample_rows = [
            _drillthrough_sample_row(
                item_id,
                card_template=card_template,
                sample_kind="reason_sample",
            )
            for item_id in reason_sample_seed
        ]
        owner_overlap_rows = [
            _drillthrough_sample_row(
                item_id,
                card_template=card_template,
                sample_kind="owner_overlap_sample",
            )
            for item_id in overlap_sample
        ]
        owner_surface_route = (
            str(static.get("option_surface_ref")) if static.get("option_surface_ref") else None
        )
        drillthrough_available = (
            bool(reason_sample_rows) or bool(owner_overlap_rows) or bool(owner_surface_route)
        )
        all_routes_materialized = all(
            row["route_materialized"]
            for row in (reason_sample_rows + owner_overlap_rows)
        )
        drillthrough_block: Dict[str, Any] = {
            "schema_version": "workitem_route_resolution_drillthrough_v0",
            "available": drillthrough_available,
            "owner_surface_route": owner_surface_route,
            "owner_surface_present": bool(owner_surface_route),
            "relationship": relationship,
            "relationship_label": WORKITEM_ROUTE_LANE_RELATIONSHIP_LABEL.get(
                relationship, "no lane"
            ),
            "reason_sample_rows": reason_sample_rows,
            "owner_overlap_rows": owner_overlap_rows,
            "sample_count": len(reason_sample_rows) + len(owner_overlap_rows),
            "omission_receipt": {
                "sample_limit": DRILLTHROUGH_SAMPLE_LIMIT,
                "template_materialized": all_routes_materialized,
                "mutation_controls_included": False,
                "card_route_template": card_template,
            },
        }
        if drillthrough_available and all_routes_materialized:
            resolution_drillthrough_materialized_count += 1
        resolution_affordances_built[reason] = {
            **dict(static),
            "primary_count": route_reason_counts.get(reason, 0),
            "sample_ids": list(route_reason_sample_ids.get(reason, [])[:DRILLTHROUGH_SAMPLE_LIMIT]),
            "lane_relationship": relationship,
            "lane_relationship_label": WORKITEM_ROUTE_LANE_RELATIONSHIP_LABEL.get(
                relationship, "no lane"
            ),
            "owner_view_item_count": owner_item_count,
            "owner_view_overlap_count": overlap_count,
            "owner_view_overlap_sample_ids": overlap_sample,
            "drillthrough": drillthrough_block,
        }

    edge_kind_counts = Counter(str(edge.get("edge_kind") or "unknown") for edge in edges)
    confidence_counts = Counter(str(edge.get("confidence") or "unknown") for edge in edges)

    drilldown_index = [
        {
            "id": cluster["id"],
            "kind": "cluster",
            "cluster_kind": cluster["cluster_kind"],
            "value": cluster["value"],
            "member_count": cluster["member_count"],
            "representative_ids": list(cluster.get("representative_ids") or []),
            "member_sample_ids": list(cluster.get("member_sample_ids") or []),
            "overflow_member_count": cluster.get("overflow_member_count", 0),
            "anomaly_counts": dict(cluster.get("anomaly_counts") or {}),
            "source_evidence": cluster.get("source_evidence"),
            "confidence": cluster.get("confidence"),
            "source_route_metadata": dict(cluster.get("source_route_metadata") or {}),
            "unavailable_reason": None,
        }
        for cluster in clusters
    ]

    unclassified_marks = [
        mark for mark in atlas_marks
        if mark["work_item_type"] == "unknown" or mark["state"] == "unknown"
    ]
    unclassified_index = {
        "count": len(unclassified_marks),
        "sample_ids": [mark["id"] for mark in unclassified_marks[:CAP_CARTOGRAPHY_UNCLASSIFIED_SAMPLE_LIMIT]],
        "reason": "work_item_type or state is missing/unknown on the ledger row.",
        "candidate_fields_to_check": ["work_item_type", "candidate_work_item_type", "state", "status"],
        "source_ref": str(LEDGER_REL),
    }

    overflow_index = {
        "edge_limit_hit": edge_limit_hit,
        "visible_node_limit_hit": visible_node_limit_hit,
        "cluster_representative_limit_hit": cluster_representative_limit_hit,
        "overview_complete": overview_complete,
        "included_edge_counts": dict(edge_kind_counts.most_common()),
        "omitted_edge_counts": dict(omitted_edge_counts.most_common()),
        "omitted_edge_count": omitted_edge_count,
        "omitted_sample": omitted_edge_samples,
        "expansion_routes": {
            "cluster_drilldown_index": "drilldown_index",
            "ledger_source": str(LEDGER_REL),
            "task_ledger_option_surface": (
                "./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>"
            ),
            "projection_path": str(VIEWS_REL / "workitem_cartography.json"),
            "atlas_marks_path": "atlas_marks (full row-grain mark universe in this packet)",
        },
    }

    warnings: List[Dict[str, Any]] = []
    if visible_node_limit_hit:
        warnings.append(
            {
                "warning": "visible_node_limit_hit",
                "limit": WORKITEM_CARTOGRAPHY_VISIBLE_NODE_LIMIT,
                "reason": (
                    "graph layer is bounded; full WorkItem universe remains available in atlas_marks."
                ),
            }
        )
    if edge_limit_hit:
        warnings.append(
            {
                "warning": "edge_limit_hit",
                "limit": WORKITEM_CARTOGRAPHY_EDGE_LIMIT,
                "reason": "graph layer is bounded; expansion via overflow_index/drilldown_index.",
            }
        )
    if unclassified_index["count"]:
        warnings.append(
            {
                "warning": "unclassified_workitems_present",
                "count": unclassified_index["count"],
                "reason": "some WorkItem rows are missing work_item_type or state; surface as unknown, not as truth.",
            }
        )

    omission_receipt = {
        "schema_version": "workitem_cartography_omission_receipt_v0",
        "v0_omissions": [
            "proof_refs (CAP-specific signoff/proof lookup; not derived for workitem_cartography_v0)",
            "support_nodes (proof/integration_surface support nodes; gated on proof_refs)",
            "CAP-specific cluster kinds (proof_readiness, integration_readiness, umbrella_linkage, operating_picture)",
            "lineage_index entries inherit only generic drilldown; CAP semantic-role lineage is not duplicated here",
            "true carryover semantics (origin_phase / current_visible_scope fields do not exist in substrate yet)",
        ],
        "carryover_label_policy": (
            "route.status='unknown' is labeled 'unrouted' / 'no_execution_route' in legend and overlays. "
            "It is NOT carryover; carryover requires real origin/current-scope fields that do not exist yet."
        ),
        "atlas_marks_completeness": {
            "row_limit_applied": False,
            "source_work_item_count_reconciles": True,
            "route_provenance_present": True,
            "route_provenance_explained_count": route_provenance_explained_count,
            "route_provenance_unknown_count": route_provenance_unknown_count,
        },
        "route_provenance_policy": (
            "Every unrouted atlas_mark carries a typed route_explanation derived from existing "
            "projection_completeness flags + state + work_item_type + dependency status. The "
            "taxonomy is anchored in std_task_ledger.json + operational_work_item_spine.md "
            "concepts (legacy_bootstrapped, terminal lifecycle, quick_capture, contract pressure, "
            "execution commitment events). carryover_status is locked to 'not_evaluated' on every "
            "row until origin/current-scope fields exist on ledger.work_items[]."
        ),
    }

    summary = {
        "source_work_item_count": len(items_by_id),
        "atlas_mark_count": len(atlas_marks),
        "cluster_count": len(clusters),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "omitted_edge_count": omitted_edge_count,
        "lineage_index_count": len(lineage_index),
        "orphan_edge_count": orphan_edge_count,
        "missing_lineage_count": missing_lineage_count,
        "visible_node_limit_hit": visible_node_limit_hit,
        "cluster_representative_limit_hit": cluster_representative_limit_hit,
        "overview_complete": overview_complete,
        "warning_count": len(warnings),
        "state_counts": dict(state_counts),
        "work_item_type_counts": dict(type_counts),
        "anomaly_counts": {
            "unrouted": unrouted_count,
            "blocked": blocked_total,
            "stale": stale_total,
            "signoff_required": signoff_total,
        },
        "route_provenance": {
            "schema_version": "workitem_route_provenance_v0_2",
            "explained_count": route_provenance_explained_count,
            "unknown_count": route_provenance_unknown_count,
            "reason_counts": dict(route_reason_counts.most_common()),
            "reason_kind_counts": dict(route_reason_kind_counts.most_common()),
            "secondary_reason_counts": dict(
                route_reason_secondary_counts.most_common()
            ),
            "predicate_kind_counts": dict(
                route_reason_predicate_kind_counts.most_common()
            ),
            "reason_sample_ids": {
                reason: list(ids)
                for reason, ids in route_reason_sample_ids.items()
            },
            "reason_priority": list(WORKITEM_ROUTE_REASON_PRIORITY)
            + [WORKITEM_ROUTE_REASON_UNKNOWN],
            # Wave 2A.1 — evidence-shape audit. evidence_ok = at least one
            # ref or field present; evidence_missing = neither, which is a
            # contract violation surfaced by the consumption layer.
            "evidence_ok_count": route_provenance_evidence_ok_count,
            "evidence_missing_count": route_provenance_evidence_missing_count,
            "evidence_missing_by_reason": dict(
                route_provenance_evidence_missing_reasons.most_common()
            ),
            "predicate_evidence_contract": {
                reason: {
                    "predicate_kind": WORKITEM_ROUTE_REASON_PREDICATE_KIND.get(reason),
                    "evidence_views": list(
                        WORKITEM_ROUTE_REASON_EVIDENCE_VIEWS.get(reason, ())
                    ),
                    "evidence_fields": list(
                        WORKITEM_ROUTE_REASON_EVIDENCE_FIELDS.get(reason, ())
                    ),
                    "kind": WORKITEM_ROUTE_REASON_KINDS.get(reason),
                }
                for reason in (
                    list(WORKITEM_ROUTE_REASON_PRIORITY)
                    + [WORKITEM_ROUTE_REASON_UNKNOWN]
                )
            },
            # Wave 2B — Reason → Remedy Map. Per-reason resolution
            # affordance: owner view, option-surface route, mutation
            # policy, next-action label. Read-only; the UI exposes the
            # mapping as a chip/link, not a mutation control.
            #
            # Wave 2D — each affordance row now carries a typed
            # lane_relationship computed from measured membership
            # overlap between the reason-id set and the owner_view item
            # id set. owner_view_overlap_sample_ids gives the consumer
            # bounded evidence to render drillthrough rows without
            # re-deriving membership.
            #
            # affordances are stamped only for reasons that actually
            # appeared in this projection (count > 0). The full contract
            # table lives in WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.
            "resolution_affordances": resolution_affordances_built,
            "resolution_summary": {
                "reason_with_remedy_count": sum(
                    1
                    for reason in (
                        list(WORKITEM_ROUTE_REASON_PRIORITY)
                        + [WORKITEM_ROUTE_REASON_UNKNOWN]
                    )
                    if route_reason_counts.get(reason, 0) > 0
                    and WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.get(reason, {}).get(
                        "resolution_status"
                    )
                    in {"available", "partial", "benign"}
                ),
                "reason_without_remedy_count": sum(
                    1
                    for reason in (
                        list(WORKITEM_ROUTE_REASON_PRIORITY)
                        + [WORKITEM_ROUTE_REASON_UNKNOWN]
                    )
                    if route_reason_counts.get(reason, 0) > 0
                    and WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.get(reason, {}).get(
                        "resolution_status"
                    )
                    == "absent"
                ),
                "resolution_status_counts": dict(
                    Counter(
                        WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.get(reason, {}).get(
                            "resolution_status",
                            "absent",
                        )
                        for reason in (
                            list(WORKITEM_ROUTE_REASON_PRIORITY)
                            + [WORKITEM_ROUTE_REASON_UNKNOWN]
                        )
                        if route_reason_counts.get(reason, 0) > 0
                    ).most_common()
                ),
                "resolution_disposition_counts": dict(
                    Counter(
                        WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.get(reason, {}).get(
                            "resolution_disposition",
                            "inspect",
                        )
                        for reason in (
                            list(WORKITEM_ROUTE_REASON_PRIORITY)
                            + [WORKITEM_ROUTE_REASON_UNKNOWN]
                        )
                        if route_reason_counts.get(reason, 0) > 0
                    ).most_common()
                ),
            },
            "resolution_drillthrough_audit": {
                "schema_version": "workitem_route_resolution_drillthrough_audit_v0",
                "reason_count": len(resolution_affordances_built),
                "materialized_count": resolution_drillthrough_materialized_count,
                "all_materialized": (
                    resolution_drillthrough_materialized_count
                    == len(resolution_affordances_built)
                    if resolution_affordances_built
                    else True
                ),
                "sample_limit": 3,
                "mutation_controls_included": False,
            },
            "resolution_lane_audit": {
                "schema_version": "workitem_route_resolution_lane_audit_v0",
                "relationship_counts": dict(
                    resolution_lane_relationship_counts.most_common()
                ),
                "reason_count": len(resolution_affordances_built),
                "exact_view_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_EXACT, 0
                ),
                "broad_view_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_BROAD, 0
                ),
                "partial_view_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_PARTIAL, 0
                ),
                "target_lane_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_TARGET, 0
                ),
                "benign_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_BENIGN, 0
                ),
                "fallback_count": resolution_lane_relationship_counts.get(
                    WORKITEM_ROUTE_LANE_RELATIONSHIP_FALLBACK, 0
                ),
            },
            "carryover_status": "not_evaluated",
            "carryover_status_reason": (
                "origin/current-scope fields do not exist on ledger.work_items[]"
            ),
        },
        "nodes_missing_basis": nodes_missing_basis,
    }

    return {
        "kind": "task_ledger_view",
        "schema_version": WORKITEM_CARTOGRAPHY_SCHEMA,
        "view_id": WORKITEM_CARTOGRAPHY_VIEW_ID,
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "projection_inputs": list(WORKITEM_CARTOGRAPHY_SOURCE_REFS),
            "mutation_rule": (
                "read-only workitem cartography projection; append Task Ledger events to change source facts"
            ),
            "classification_policy": (
                "visual semantics are source-evidenced when backed by ledger fields; "
                "actor and family clusters are projection-labeled when item lacks explicit field."
            ),
        },
        "source_refs": list(WORKITEM_CARTOGRAPHY_SOURCE_REFS),
        "summary": summary,
        "levels": [
            {
                "id": "level:0:atlas_marks_universe",
                "label": "Atlas marks universe",
                "source_ref": str(LEDGER_REL),
                "display_contract": "full row-grain mark per WorkItem; lattice rendering layer.",
            },
            {
                "id": "level:1:cluster_map",
                "label": "Cluster map",
                "source_ref": str(LEDGER_REL),
                "display_contract": "cluster by universal axes (state, work_item_type, actor, family, route_status).",
            },
            {
                "id": "level:2:representative_nodes",
                "label": "Representative nodes",
                "source_ref": str(VIEWS_REL / "workitem_cartography.json"),
                "display_contract": "bounded representative graph nodes; not a raw dump of every WorkItem.",
            },
            {
                "id": "level:3:typed_edges",
                "label": "Typed edges",
                "source_ref": str(VIEWS_REL / "dependency_graph.json"),
                "display_contract": "only source-evidenced depends_on/unlocks edges plus projection-labeled cluster membership.",
            },
            {
                "id": "level:4:lineage_drilldown",
                "label": "Lineage drilldown",
                "source_ref": str(EVENTS_REL),
                "display_contract": "visible nodes expose Task Ledger card route, source refs, route metadata, and missing refs.",
            },
        ],
        "overflow_policy": {
            "overview_node_limit": WORKITEM_CARTOGRAPHY_VISIBLE_NODE_LIMIT,
            "overview_edge_limit": WORKITEM_CARTOGRAPHY_EDGE_LIMIT,
            "cluster_representative_limit": WORKITEM_CARTOGRAPHY_CLUSTER_REPRESENTATIVE_LIMIT,
            "bounded_overview": True,
            "atlas_marks_bounded": False,
            "reason": (
                "graph layer is bounded for overview-first rendering; atlas_marks layer is full universe."
            ),
        },
        "overflow_index": overflow_index,
        "drilldown_index": drilldown_index,
        "unclassified_index": unclassified_index,
        "clusters": clusters,
        "nodes": nodes,
        "edges": edges,
        "lineage_index": lineage_index,
        "atlas_marks": atlas_marks,
        "queue_membership": queue_membership_full,
        "legend": {
            "color_basis_options": ["state", "work_item_type", "route_status", "actor"],
            "size_basis_options": ["downstream_unlock_count", "depends_on_count", "member_count"],
            "overlay_options": [
                "unrouted",
                "blocked",
                "stale",
                "signoff_required",
                "high_unlock",
                "queue_visible",
            ],
            "confidence_values": ["source_evidenced", "projection_inferred", "missing_source"],
            "frontend_posture": (
                "observe_only; no WorkItem creation controls or mutation commands are exposed as frontend actions"
            ),
            "edge_kind_counts": dict(edge_kind_counts.most_common()),
            "edge_confidence_counts": dict(confidence_counts.most_common()),
            "carryover_label_policy": (
                "carryover label is forbidden until origin_phase / current_visible_scope semantics exist; "
                "use 'unrouted' / 'no_execution_route' instead."
            ),
        },
        "warnings": warnings,
        "omission_receipt": omission_receipt,
        "items": clusters,
        "count": len(clusters),
    }


def _build_mission_operating_picture_view(
    *,
    work_items: Sequence[Mapping[str, Any]],
    dependency_views: Mapping[str, Mapping[str, Any]],
    execution_schedulable: Mapping[str, Any],
    active_wip: Mapping[str, Any],
    meta_mission_active: Mapping[str, Any],
    mission_blackboard: Mapping[str, Any] | None,
    mission_trace_current_state: Mapping[str, Any],
    generated_at: str,
) -> Dict[str, Any]:
    by_id = {
        _mission_operating_item_id(item): item
        for item in work_items
        if _mission_operating_item_id(item)
    }
    dependency_rows = {
        _mission_operating_item_id(row): row
        for row in dependency_views.get("dependency_graph", {}).get("items", [])
        if isinstance(row, Mapping) and _mission_operating_item_id(row)
    }

    current_by_id: Dict[str, Dict[str, Any]] = {}
    bucket_priority = {
        "runtime_active": 0,
        "foreground_mission": 1,
        "execution_candidate": 2,
        "candidate_meta_mission_capture": 3,
        "anchor_or_registry_row": 4,
    }

    def add_current(
        item: Mapping[str, Any],
        *,
        bucket: str,
        source_view: str,
        why_in_set: str,
    ) -> None:
        item_id = _mission_operating_item_id(item)
        if not item_id:
            return
        full_item = by_id.get(item_id, item)
        dep_status = dependency_rows.get(item_id, {}).get("dependency_status")
        if not isinstance(dep_status, Mapping):
            dep_status = item.get("dependency_status") if isinstance(item.get("dependency_status"), Mapping) else {}
        downstream_edges = dep_status.get("downstream_unlock_edges") if isinstance(dep_status, Mapping) else []
        if not isinstance(downstream_edges, Sequence) or isinstance(downstream_edges, (str, bytes)):
            downstream_edges = []
        row = {
            "id": item_id,
            "title": _mission_operating_label(full_item),
            "mission_bucket": bucket,
            "state": _item_state(full_item),
            "work_item_type": full_item.get("work_item_type"),
            "candidate_work_item_type": full_item.get("candidate_work_item_type"),
            "rank": full_item.get("rank"),
            "schedulable": dep_status.get("schedulable") if isinstance(dep_status, Mapping) else None,
            "downstream_unlock_count": len(downstream_edges),
            "why_in_set": why_in_set,
            "source_view": source_view,
            "source_views": [source_view],
        }
        existing = current_by_id.get(item_id)
        if existing:
            source_views = list(existing.get("source_views") or [])
            if source_view not in source_views:
                source_views.append(source_view)
            existing["source_views"] = source_views
            if bucket_priority.get(bucket, 99) < bucket_priority.get(str(existing.get("mission_bucket") or ""), 99):
                existing.update({key: row[key] for key in row if key != "source_views"})
                existing["source_views"] = source_views
            return
        current_by_id[item_id] = row

    for row in meta_mission_active.get("items", []):
        if isinstance(row, Mapping):
            bucket, why = _mission_operating_meta_bucket(row)
            add_current(row, bucket=bucket, source_view="meta_mission_active", why_in_set=why)

    for row in execution_schedulable.get("items", []):
        if isinstance(row, Mapping):
            add_current(
                row,
                bucket="execution_candidate",
                source_view="execution_menu_schedulable",
                why_in_set="execution-menu row whose hard dependencies are satisfied.",
            )

    for row in active_wip.get("items", []):
        if isinstance(row, Mapping):
            add_current(
                row,
                bucket="runtime_active",
                source_view="active_wip",
                why_in_set="currently active WorkItem.",
            )

    nodes: Dict[str, Dict[str, Any]] = {}
    edges: Dict[str, Dict[str, Any]] = {}
    missing_umbrella_refs: List[Dict[str, Any]] = []
    warnings: List[Dict[str, Any]] = []

    def add_node(node: Mapping[str, Any]) -> None:
        node_id = str(node.get("id") or "").strip()
        if not node_id:
            return
        existing = nodes.get(node_id)
        if existing:
            existing_refs = list(existing.get("source_refs") or [])
            for ref in node.get("source_refs") or []:
                if ref not in existing_refs:
                    existing_refs.append(ref)
            existing["source_refs"] = existing_refs
            return
        nodes[node_id] = dict(node)

    def add_edge(source: str, target: str, edge_kind: str, source_ref: str) -> None:
        if not source or not target:
            return
        edge_id = f"{edge_kind}:{source}->{target}"
        edges.setdefault(
            edge_id,
            {
                "id": edge_id,
                "source": source,
                "target": target,
                "edge_kind": edge_kind,
                "source_ref": source_ref,
            },
        )

    def add_work_item_node(item_id: str, source_views: Sequence[str]) -> None:
        item = by_id.get(item_id) or dependency_rows.get(item_id) or {"id": item_id, "title": item_id}
        add_node(
            {
                "id": item_id,
                "label": _mission_operating_label(item),
                "node_kind": _mission_operating_node_kind(item),
                "state": _item_state(item),
                "work_item_type": item.get("work_item_type"),
                "candidate_work_item_type": item.get("candidate_work_item_type"),
                "rank": item.get("rank"),
                "views": list(dict.fromkeys(source_views)),
                "source_refs": _mission_operating_source_refs(item, source_views[0] if source_views else None),
            }
        )

    current_mission_set = sorted(
        current_by_id.values(),
        key=lambda row: (
            bucket_priority.get(str(row.get("mission_bucket") or ""), 99),
            row.get("rank") is None,
            row.get("rank") or 999999,
            str(row.get("id") or ""),
        ),
    )

    for row in current_mission_set:
        item_id = str(row.get("id") or "")
        source_views = [str(view) for view in row.get("source_views") or [row.get("source_view")]]
        add_work_item_node(item_id, source_views)
        item = by_id.get(item_id) or {}
        imagined_state_refs = _mission_operating_imagined_state_refs(item)
        if not imagined_state_refs:
            gap_id = f"umbrella_gap:{item_id}"
            add_node(
                {
                    "id": gap_id,
                    "label": f"Missing umbrella refs for {item_id}",
                    "node_kind": "imagination_gap",
                    "state": "missing",
                    "work_item_type": None,
                    "candidate_work_item_type": None,
                    "rank": None,
                    "views": ["mission_operating_picture"],
                    "source_refs": _mission_operating_source_refs(item, row.get("source_view")),
                }
            )
            add_edge(item_id, gap_id, "missing_umbrella", str(VIEWS_REL / f"{MISSION_OPERATING_PICTURE_VIEW_ID}.json"))
            missing_umbrella_refs.append(
                {
                    "work_item_id": item_id,
                    "title": row.get("title"),
                    "reason": "no satisfaction_contract.imagined_state_refs populated",
                    "candidate_sources_to_check": list(MISSION_OPERATING_CANDIDATE_SOURCES),
                }
            )
        else:
            for ref in imagined_state_refs:
                target_id = f"imagination:{ref}"
                add_node(
                    {
                        "id": target_id,
                        "label": ref,
                        "node_kind": "imagination",
                        "state": "referenced",
                        "work_item_type": None,
                        "candidate_work_item_type": None,
                        "rank": None,
                        "views": ["mission_operating_picture"],
                        "source_refs": _mission_operating_source_refs(item, row.get("source_view")),
                    }
                )
                add_edge(item_id, target_id, "serves", str(LEDGER_REL))

        for surface in _mission_operating_exact_surfaces(item):
            path = str(surface.get("path") or "").strip()
            if not path:
                continue
            target_id = f"integration_surface:{path}"
            add_node(
                {
                    "id": target_id,
                    "label": path,
                    "node_kind": "integration_surface",
                    "state": surface.get("status") or "referenced",
                    "work_item_type": None,
                    "candidate_work_item_type": None,
                    "rank": None,
                    "views": ["mission_operating_picture"],
                    "source_refs": _mission_operating_source_refs(item, row.get("source_view")),
                }
            )
            add_edge(item_id, target_id, "lands_on", str(LEDGER_REL))

        dep_row = dependency_rows.get(item_id) or {}
        dep_status = dep_row.get("dependency_status") if isinstance(dep_row.get("dependency_status"), Mapping) else {}
        for dep_id in _coerce_id_list(dep_row.get("depends_on") or item.get("depends_on")):
            add_work_item_node(dep_id, ["dependency_graph"])
            add_edge(item_id, dep_id, "depends_on", str(VIEWS_REL / "dependency_graph.json"))
        unlock_edges = dep_status.get("downstream_unlock_edges") if isinstance(dep_status, Mapping) else []
        if isinstance(unlock_edges, Sequence) and not isinstance(unlock_edges, (str, bytes)):
            for unlock in unlock_edges:
                if not isinstance(unlock, Mapping):
                    continue
                target_id = str(unlock.get("id") or "").strip()
                if not target_id:
                    continue
                add_work_item_node(target_id, ["unlocks_by_rank", "dependency_graph"])
                add_edge(item_id, target_id, "unlocks", str(VIEWS_REL / "unlocks_by_rank.json"))

    if isinstance(mission_blackboard, Mapping) and mission_blackboard:
        board_rows = mission_blackboard.get("rows")
        if isinstance(board_rows, Sequence) and not isinstance(board_rows, (str, bytes)):
            for raw_row in board_rows:
                if not isinstance(raw_row, Mapping):
                    continue
                row_id = str(raw_row.get("row_id") or raw_row.get("id") or "").strip()
                if not row_id:
                    continue
                node_id = f"mission_blackboard:{row_id}"
                add_node(
                    {
                        "id": node_id,
                        "label": raw_row.get("focus_summary") or raw_row.get("phase_title") or row_id,
                        "node_kind": "runtime_claim",
                        "state": raw_row.get("status") or "unknown",
                        "work_item_type": None,
                        "candidate_work_item_type": None,
                        "rank": None,
                        "views": ["mission_blackboard"],
                        "source_refs": [str(MISSION_BLACKBOARD_REL)],
                    }
                )
                current_mission_set.append(
                    {
                        "id": node_id,
                        "title": raw_row.get("focus_summary") or raw_row.get("phase_title") or row_id,
                        "mission_bucket": "runtime_active",
                        "state": raw_row.get("status") or "unknown",
                        "schedulable": None,
                        "downstream_unlock_count": 0,
                        "why_in_set": "active mission blackboard row.",
                        "source_view": "mission_blackboard",
                        "active_runtime_ref": row_id,
                    }
                )
        else:
            warnings.append(
                {
                    "warning": "mission_blackboard_rows_missing",
                    "source_ref": str(MISSION_BLACKBOARD_REL),
                }
            )
    else:
        warnings.append(
            {
                "warning": "mission_blackboard_unavailable",
                "source_ref": str(MISSION_BLACKBOARD_REL),
            }
        )

    node_rows = sorted(nodes.values(), key=lambda row: str(row.get("id") or ""))
    edge_rows = sorted(edges.values(), key=lambda row: str(row.get("id") or ""))
    missing_umbrella_refs.sort(key=lambda row: str(row.get("work_item_id") or ""))
    current_mission_set.sort(
        key=lambda row: (
            bucket_priority.get(str(row.get("mission_bucket") or ""), 99),
            str(row.get("id") or ""),
        )
    )
    return {
        "kind": "task_ledger_view",
        "schema_version": MISSION_OPERATING_PICTURE_SCHEMA,
        "view_id": MISSION_OPERATING_PICTURE_VIEW_ID,
        "generated_at": generated_at,
        "authority": {
            "source": str(EVENTS_REL),
            "projection_inputs": list(MISSION_OPERATING_SOURCE_REFS),
            "derived_overlay_inputs": [str(PROMPT_LEDGER_MISSION_TRACE_CURRENT_STATE_REL)],
            "authority_boundary": "Task Ledger events remain WorkItem authority; Prompt Ledger mission trace rows are orientation overlay only.",
            "mutation_rule": "read-only operating-picture projection; append Task Ledger events or refresh mission blackboard to change source facts",
        },
        "source_refs": list(MISSION_OPERATING_SOURCE_REFS),
        "summary": {
            "node_count": len(node_rows),
            "edge_count": len(edge_rows),
            "current_mission_count": len(current_mission_set),
            "missing_umbrella_ref_count": len(missing_umbrella_refs),
            "warning_count": len(warnings),
            "mission_trace_current_state_status": mission_trace_current_state.get("status"),
            "mission_trace_current_state_count": mission_trace_current_state.get("row_count", 0),
        },
        "current_mission_set": current_mission_set,
        "mission_trace_current_state": dict(mission_trace_current_state),
        "nodes": node_rows,
        "edges": edge_rows,
        "missing_umbrella_refs": missing_umbrella_refs,
        "warnings": warnings,
        "items": current_mission_set,
        "count": len(current_mission_set),
    }


def build_views(
    work_items: List[Mapping[str, Any]],
    signoffs: List[Mapping[str, Any]],
    events: List[Mapping[str, Any]],
    generated_at: str,
    *,
    mission_blackboard: Mapping[str, Any] | None = None,
    repo_root: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    by_state: Dict[str, List[Mapping[str, Any]]] = defaultdict(list)
    for item in work_items:
        by_state[str(item.get("state") or item.get("status") or "")].append(item)

    def view(name: str, items: List[Mapping[str, Any]]) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "kind": "task_ledger_view",
            "schema_version": "task_ledger_view_v1",
            "view_id": name,
            "generated_at": generated_at,
            "items": list(items),
            "count": len(items),
        }
        if name == "operator_needed":
            payload["operator_authorization_policy"] = _standing_operator_authorization_policy(
                requires_operator_review=True
            )
            payload["operator_needed_semantics"] = (
                "operator-needed rows are attention, signoff, or priority-review boundaries; "
                "standing private/internal authorization means safe scoped local work is not blocked "
                "solely for permission, while public release and safety boundaries remain fail-closed."
            )
        return payload

    action_relevant_items = [item for item in work_items if not _is_closed_or_signed_off(item)]
    captures = [item for item in work_items if str(item.get("work_item_type") or "") == "capture"]
    ready = [
        item
        for item in action_relevant_items
        if str(item.get("state") or item.get("status")) in {"ready", "accepted"}
    ]
    active = [
        item
        for item in action_relevant_items
        if str(item.get("state") or item.get("status")) in {"claimed", "active"}
    ]
    blocked = [
        item
        for item in action_relevant_items
        if str(item.get("state") or item.get("status")) == "blocked"
    ]
    operator_needed = [
        item
        for item in action_relevant_items
        if "operator" in json.dumps(item.get("authority") or {}, ensure_ascii=False).lower()
        or str(item.get("state") or "") == "signoff"
    ]
    bridge_assignable = [
        item
        for item in action_relevant_items
        if str(item.get("work_item_type") or "") == "bridge_action"
        or str(item.get("candidate_work_item_type") or "") == "bridge_action"
        or "bridge" in json.dumps(item.get("execution") or {}, ensure_ascii=False).lower()
    ]
    provider_assignable = [
        item
        for item in action_relevant_items
        if str(item.get("work_item_type") or "") == "provider_job"
        or str(item.get("candidate_work_item_type") or "") == "provider_job"
        or "provider" in json.dumps(item.get("execution") or {}, ensure_ascii=False).lower()
    ]
    contract_debt_items = action_relevant_items
    metabolic = [
        item
        for item in action_relevant_items
        if str(item.get("work_item_type") or "") == "metabolic_reflex"
        or str(item.get("candidate_work_item_type") or "") == "metabolic_reflex"
    ]
    meta_mission = [
        item
        for item in action_relevant_items
        if str(item.get("work_item_type") or "") == "meta_mission"
        or str(item.get("candidate_work_item_type") or "") == "meta_mission"
    ]
    needs_signoff = [
        item
        for item in contract_debt_items
        if (item.get("projection_completeness") or {}).get("needs_signoff")
    ]
    missing_satisfaction = [
        item
        for item in contract_debt_items
        if not (item.get("projection_completeness") or {}).get("has_satisfaction_contract")
    ]
    missing_integration = [
        item
        for item in contract_debt_items
        if not (item.get("projection_completeness") or {}).get("has_integration_contract")
        or not (item.get("projection_completeness") or {}).get("exact_surfaces_grounded")
    ]
    legacy_unmodeled = [
        item
        for item in work_items
        if (item.get("projection_completeness") or {}).get("legacy_snapshot_present")
    ]
    work_ledger_unlinked = [
        item
        for item in action_relevant_items
        if str(item.get("state") or item.get("status")) in {"claimed", "active", "review", "signoff"}
        and not (item.get("projection_completeness") or {}).get("has_work_ledger_claim_ref")
    ]
    # Wave 2C — state_transitioned_no_execution_route diagnostic. Mirrors
    # the route_provenance taxonomy's predicate so atlas_marks and the
    # sibling view reconcile 1:1.
    state_transitioned_no_execution_route_items = [
        _state_transitioned_no_execution_route_row(item)
        for item in work_items
        if _state_transitioned_no_execution_route_predicate(item)
    ]
    incomplete = [
        item
        for item in contract_debt_items
        if item in missing_satisfaction
        or item in missing_integration
        or not (item.get("projection_completeness") or {}).get("has_completion_contract")
        or (item.get("projection_completeness") or {}).get("needs_signoff")
    ]
    recent_events = sorted(events, key=lambda row: (str(row.get("created_at") or ""), str(row.get("event_id") or "")), reverse=True)[:50]
    propagation_needed = _build_propagation_needed_view(work_items, signoffs, generated_at)
    execution_menu = _build_execution_menu_view(work_items, generated_at)
    capture_triage = _build_capture_triage_view(captures, generated_at)
    promotion_candidates = _build_promotion_candidates_view(
        capture_triage,
        generated_at,
        execution_menu=execution_menu,
    )
    dependency_views = _build_dependency_views(work_items, execution_menu, generated_at)
    capture_triage = _annotate_capture_triage_menu_membership(capture_triage, execution_menu, promotion_candidates)
    active_wip = view("active_wip", sorted(active, key=_rank_key))
    meta_mission_active = view("meta_mission_active", sorted(meta_mission, key=_rank_key))
    execution_schedulable = dependency_views["execution_menu_schedulable"]
    mission_trace_current_state = _mission_trace_rollup_for_operating_picture(repo_root)
    mission_operating_picture = _build_mission_operating_picture_view(
        work_items=work_items,
        dependency_views=dependency_views,
        execution_schedulable=execution_schedulable,
        active_wip=active_wip,
        meta_mission_active=meta_mission_active,
        mission_blackboard=mission_blackboard,
        mission_trace_current_state=mission_trace_current_state,
        generated_at=generated_at,
    )

    views = {
        "capture_inbox": _build_capture_inbox_view(
            sorted(captures, key=lambda item: str(item.get("id") or "")),
            capture_triage,
            generated_at,
        ),
        "capture_triage": capture_triage,
        "promotion_candidates": promotion_candidates,
        "execution_menu": execution_menu,
        "execution_menu_schedulable": execution_schedulable,
        "schedulable_by_rank": dependency_views["schedulable_by_rank"],
        "dependency_blocked": dependency_views["dependency_blocked"],
        "dependency_anomalies": dependency_views["dependency_anomalies"],
        "dependency_graph": dependency_views["dependency_graph"],
        "unlocks_by_rank": dependency_views["unlocks_by_rank"],
        "mission_operating_picture": mission_operating_picture,
        "merge_or_retire_candidates": _build_merge_or_retire_candidates_view(captures, generated_at),
        "missing_contracts_ranked": _build_missing_contracts_ranked_view(contract_debt_items, generated_at),
        "ready_by_rank": view("ready_by_rank", sorted(ready, key=_rank_key)),
        "active_wip": active_wip,
        "blocked": view("blocked", sorted(blocked, key=_rank_key)),
        "operator_needed": view("operator_needed", sorted(operator_needed, key=_rank_key)),
        "bridge_assignable": view("bridge_assignable", sorted(bridge_assignable, key=_rank_key)),
        "provider_assignable": view("provider_assignable", sorted(provider_assignable, key=_rank_key)),
        "metabolic_running": view("metabolic_running", sorted(metabolic, key=_rank_key)),
        "meta_mission_active": meta_mission_active,
        "needs_signoff": view("needs_signoff", sorted(needs_signoff, key=_rank_key)),
        "propagation_needed": propagation_needed,
        "incomplete_work_items": view("incomplete_work_items", sorted(incomplete, key=_rank_key)),
        "missing_satisfaction_contract": view("missing_satisfaction_contract", sorted(missing_satisfaction, key=_rank_key)),
        "missing_integration_contract": view("missing_integration_contract", sorted(missing_integration, key=_rank_key)),
        "legacy_snapshot_unmodeled": view("legacy_snapshot_unmodeled", sorted(legacy_unmodeled, key=_rank_key)),
        "work_ledger_unlinked": view("work_ledger_unlinked", sorted(work_ledger_unlinked, key=_rank_key)),
        # Wave 2C — Reason → Remedy owner view for
        # `state_transitioned_no_execution_route`. Read-only diagnostic;
        # rows are sorted by rank to mirror other route-pressure views.
        "state_transitioned_no_execution_route": view(
            "state_transitioned_no_execution_route",
            sorted(
                state_transitioned_no_execution_route_items,
                key=lambda row: (
                    row.get("rank") if isinstance(row.get("rank"), (int, float)) else 999_999,
                    str(row.get("id") or ""),
                ),
            ),
        ),
        "prompt_trace_unlinked": view("prompt_trace_unlinked", []),
        "stale_review": view("stale_review", []),
        "recent_events": view("recent_events", recent_events),
        "signoffs": view("signoffs", signoffs),
    }
    views["cap_census"] = _build_cap_census_view(
        work_items=work_items,
        signoffs=signoffs,
        views=views,
        generated_at=generated_at,
    )
    views["cap_cartography"] = _build_cap_cartography_view(
        work_items=work_items,
        signoffs=signoffs,
        cap_census=views["cap_census"],
        mission_operating_picture=mission_operating_picture,
        dependency_views=dependency_views,
        generated_at=generated_at,
    )
    views["cap_execution_market"] = _build_cap_execution_market_view(
        work_items=work_items,
        signoffs=signoffs,
        cap_census=views["cap_census"],
        cap_cartography=views["cap_cartography"],
        generated_at=generated_at,
    )
    queue_visible_ids, queue_membership_stats = _compute_queue_membership_crosswalk(repo_root)
    # Wave 2D — owner-view membership sets for lane_relationship overlap
    # computation. Pulled from the views dict already built above so the
    # cartography builder reads measured membership instead of assuming it.
    #
    # Wave 2E fix: not every owner view stores the WorkItem id under
    # `id` — `signoffs.json` rows are signoff records whose
    # corresponding WorkItem id lives under `work_item_id`. This map
    # captures per-view id-field overrides so the overlap math compares
    # the right id namespaces.
    owner_view_item_id_field: Mapping[str, str] = {
        "signoffs": "work_item_id",
    }
    def _view_item_ids(view_id: str) -> Set[str]:
        view_payload = views.get(view_id) or {}
        items = view_payload.get("items") or []
        id_field = owner_view_item_id_field.get(view_id, "id")
        return {
            str(row.get(id_field))
            for row in items
            if isinstance(row, Mapping) and row.get(id_field)
        }
    owner_view_id_sets: Dict[str, Set[str]] = {
        owner_view: _view_item_ids(owner_view)
        for affordance in WORKITEM_ROUTE_RESOLUTION_AFFORDANCES.values()
        if (owner_view := affordance.get("owner_view"))
    }
    views["workitem_cartography"] = _build_workitem_cartography_view(
        work_items=work_items,
        dependency_views=dependency_views,
        generated_at=generated_at,
        queue_visible_ids=queue_visible_ids,
        queue_membership_stats=queue_membership_stats,
        owner_view_id_sets=owner_view_id_sets,
    )
    return views


ADAPTER_LEAK_SIGNALS = [
    "TodoWrite",
    "spawn_task",
    "/schedule",
    "future work",
    "by the way",
    "follow-up",
    "followup",
    "deferred",
    "needs verification",
]
CAPTURE_PROVENANCE_RE = re.compile(r"\b(?:cap|cap_quick|cap_upprop)_[A-Za-z0-9_:-]+\b")
ADAPTER_SIGNAL_FAMILIES = {
    "TodoWrite": "native_todo_signal",
    "spawn_task": "native_todo_signal",
    "TaskCreate": "native_todo_signal",
    "TaskUpdate": "native_todo_signal",
    "TaskList": "native_todo_signal",
    "/schedule": "scheduling_signal",
    "future work": "residual_language_signal",
    "follow-up": "residual_language_signal",
    "followup": "residual_language_signal",
    "deferred": "residual_language_signal",
    "needs verification": "residual_language_signal",
    "by the way": "weak_language_signal",
}
NATIVE_TODO_TOOL_NAMES = {"TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "spawn_task"}
ORGANIZER_REPORT_COMPACT_SAMPLE_LIMIT = 3
ORGANIZER_REPORT_FULL_SAMPLE_LIMIT = 8
ORGANIZER_REPORT_COMPACT_ADAPTER_EXAMPLES = 6
ORGANIZER_REPORT_FULL_ADAPTER_EXAMPLES = 20
ORGANIZER_REPORT_COMPACT_CALIBRATION_SAMPLES = 8
ORGANIZER_REPORT_FULL_CALIBRATION_SAMPLES = 30
WORK_GRAPH_PRIORITY_RUBRIC = {
    "rubric_id": "work_graph_priority_metabolism_v0",
    "supersedes": ["workitem_priority_rubric_v0"],
    "purpose": (
        "Choose the next owner action across WorkItems, cap families, self-error clusters, "
        "seeds, standards, skills, paper modules, routes, generated-state blockers, and "
        "operator-intent clusters without letting salience, recency, or capture volume "
        "masquerade as priority."
    ),
    "object_classes": [
        "execution_menu_commitment",
        "dependency_blocker",
        "cap_family",
        "self_error_cluster",
        "autonomous_seed_drift",
        "mechanism_or_route_pressure",
        "missing_contract",
        "duplicate_or_supersession_chain",
        "propagation_debt",
        "generated_state_or_work_ledger_gap",
        "operator_review_or_signoff_gap",
        "raw_capture_memory",
    ],
    "hard_gates_before_score": [
        "authority_health_clean_or_recover_first",
        "git_metadata_and_work_ledger_claims_available_before_source_mutation",
        "execution_menu_commitment_before_promotion_candidate",
        "hard_dependencies_satisfied_or_explicitly_blocked",
        "public_or_secret_boundary_clear_before_publication_or_external_action",
        "active_path_or_workitem_collision_resolved_before_mutation",
        "missing_contracts_route_to_shaping_before_execution",
        "raw_capture_volume_is_not_priority_by_itself",
    ],
    "score_axes_in_order": [
        {
            "axis": "operator_or_phase_alignment",
            "question": "Does this cluster serve the active operator intent, phase objective, or explicit override?",
        },
        {
            "axis": "downstream_unlock_value",
            "question": "Will this action unblock downstream work, remove a blocker, or reduce recurring execution friction?",
        },
        {
            "axis": "repeated_failure_signal",
            "question": "Does the cluster represent repeated caps, self-errors, false greens, route misses, or duplicated work?",
        },
        {
            "axis": "proof_readiness",
            "question": "Are exact surfaces, owner tools, acceptance checks, and validation commands grounded?",
        },
        {
            "axis": "owner_surface_confidence",
            "question": "Is the correct owner a Task Ledger event, source patch, standard, skill, seed, route, paper module, or generated owner?",
        },
        {
            "axis": "substrate_reuse_gain",
            "question": "Will the action improve an existing owner surface instead of creating a parallel board or taxonomy?",
        },
        {
            "axis": "future_agent_time_saved",
            "question": "Will future agents spend less time rediscovering, sorting, or correcting the same pressure?",
        },
        {
            "axis": "propagation_value",
            "question": "Does the local case teach a reusable skill, standard, route, seed, or paper-module lesson?",
        },
        {
            "axis": "blast_radius_validation_and_review_cost",
            "question": "Is the smallest useful action safe, reversible, locally validatable, and below operator-review risk?",
        },
    ],
    "cluster_order": [
        "execution_menu_committed",
        "execution_menu_schedulable",
        "dependency_blocked",
        "cap_family_pressure",
        "self_error_pressure",
        "autonomous_seed_pressure",
        "mechanism_pressure_lens",
        "work_ledger_unlinked",
        "metabolic_running",
        "meta_mission_active",
        "mission_operating_picture",
        "promotion_candidates",
        "missing_contracts",
        "merge_or_retire",
        "propagation_needed",
        "needs_signoff",
        "operator_needed",
        "raw_capture_inbox",
        "possible_adapter_leaks",
    ],
    "anti_rules": [
        "Do not use capture_inbox size as priority.",
        "Do not promote a row just because it is recent.",
        "Do not rank a row whose owner, proof surface, or dependency blocker is unknown.",
        "Do not assume WorkItem priority is the right abstraction when the pressure is a cap family, standard gap, route gap, seed drift, or paper-module gap.",
        "Do not let the low-pass seed mutate rows automatically; it selects a bounded owner action and proposes event commands only where the event lane is the owner.",
    ],
}
WORKITEM_PRIORITY_RUBRIC = WORK_GRAPH_PRIORITY_RUBRIC

SELF_ERROR_FAILURE_FAMILY_SPECS: List[Dict[str, Any]] = [
    {
        "family_id": "work_ledger_command_boundary",
        "label": "Work Ledger command boundary and closeout order",
        "needles": [
            "work ledger",
            "work_ledger",
            "session-finalize",
            "session finalize",
            "read receipt",
            "td_id",
            "missing_or_stale_td_id_claim",
            "append after finalize",
            "append-before-finalize",
        ],
        "exclude_needles": [
            "operator hud",
            "operator attention",
            "response_ready_unseen",
            "hud",
            "gold",
        ],
        "owner_surface_hint": "tools/meta/factory/work_ledger.py | system/lib/work_ledger_runtime.py",
        "suggested_action": "verify live Work Ledger guardrails, then patch command output or retire stale symptoms with proof",
        "why": "Repeated close/finalize mistakes waste sessions and can leave stale append obligations.",
    },
    {
        "family_id": "task_ledger_mutation_serialization",
        "label": "Task Ledger mutation serialization",
        "needles": [
            "parallel task ledger",
            "parallel quick-capture",
            "parallel quick-captures",
            "quick-capture writes",
            "quick-capture commands",
            "quick capture commands",
            "task ledger mutation",
            "task_ledger_apply",
            "events.jsonl",
            "events/projection",
            "quick-capture --rebuild",
            "quick-capture --depends-on",
            "--depends-on",
            "event id",
            "event hash",
        ],
        "exclude_needles": [
            "actual path is",
            "claude.md",
            "doctrine_drift",
            "false alarm",
            "no stale path reference",
            "reclassified out of task ledger mutation serialization",
            "route_or_stale_surface",
            "selector_family_projection_fix",
            "stale path",
            "stale-path",
            "verified_no_defect",
            "tools/meta/control/task_ledger_apply.py",
            "verified no defect",
        ],
        "owner_surface_hint": "tools/meta/factory/task_ledger_apply.py | system/lib/task_ledger_events.py",
        "suggested_action": "use serial or batch mutation lanes; patch command guidance or locking diagnostics if agents keep racing",
        "why": "Task Ledger events are authority, so repeated parallel mutation mistakes are priority pressure.",
    },
    {
        "family_id": "host_shell_environment",
        "label": "Host shell environment and PATH setup",
        "needles": [
            "zsh -f",
            "lacked path",
            "path entries",
            "macos settings",
            "settings reset",
        ],
        "owner_surface_hint": "host command setup, macOS repair scripts, or shell environment preflight",
        "suggested_action": "patch the host-command bootstrap or script example if the PATH failure recurs",
        "why": "Host shell environment mistakes are different from quoting mistakes; they need script/bootstrap evidence, not quote examples.",
    },
    {
        "family_id": "shell_or_cli_quoting",
        "label": "Shell quoting and command substitution",
        "needles": [
            "shell-substitution",
            "command substitution",
            "backticks",
            "backticked",
            "double-quoted rg",
            "single-quoted regex",
            "literal command names",
            "shell quoting",
        ],
        "owner_surface_hint": "command-surface docs, action quotes, and task/cap command examples",
        "suggested_action": "patch the point-of-use command example or action quote instead of only preserving the correction",
        "why": "Quoting mistakes corrupt persisted statements and create correction chains.",
    },
    {
        "family_id": "capture_reflex_protocol",
        "label": "Capture reflex and prose-before-capture protocol",
        "needles": [
            "capture before",
            "flagged without capture",
            "mistake without capture",
            "capture protocol",
            "noticed test failure",
        ],
        "owner_surface_hint": "codex/doctrine/skills/task_ledger/task_ledger.md | AGENTS.override.md",
        "suggested_action": "patch the nearest capture reflex surface or record already-propagated proof",
        "why": "The same residual should not keep escaping into chat instead of Task Ledger authority.",
    },
    {
        "family_id": "route_or_stale_surface",
        "label": "Route miss, stale path, or broad search",
        "needles": [
            "actual path is",
            "claude.md",
            "false alarm",
            "no stale path reference",
            "path row",
            "reclassified out of task ledger mutation serialization",
            "route_or_stale_surface",
            "selector_family_projection_fix",
            "stale path",
            "stale-path",
            "stale cli",
            "route miss",
            "wrong route",
            "broad rg",
            "grep",
            "raw search",
            "tools/meta/control/task_ledger_apply.py",
            "verified_no_defect",
            "verified no defect",
        ],
        "owner_surface_hint": "kernel route, context-pack, docs-route, option surface, or command card",
        "suggested_action": "patch the route or point-of-use surface that made raw search look necessary",
        "why": "Route failures make future agents rediscover owner surfaces manually.",
    },
    {
        "family_id": "false_completion_or_proof",
        "label": "False completion or weak proof",
        "needles": [
            "false green",
            "false completion",
            "semantic proof",
            "proof substituted",
            "visible substrate",
            "overclaimed",
            "operator hud",
            "operator attention",
            "response_ready_unseen",
            "unread gold",
            "stale cached tab memory",
        ],
        "owner_surface_hint": "acceptance gate, checker, proof route, or visible substrate contract",
        "suggested_action": "tighten the proof gate or card route that allowed semantic proof to replace visible evidence",
        "why": "False-green pressure harms trust more than ordinary backlog volume.",
    },
    {
        "family_id": "generated_projection_freshness",
        "label": "Generated projection or freshness confusion",
        "needles": [
            "generated projection",
            "stale generated",
            "projection stale",
            "hologram stale",
            "source coupling",
            "generated state",
        ],
        "owner_surface_hint": "generated owner checker, generated_state_drainer, or projection registry",
        "suggested_action": "patch owner diagnostics or settle through the generated owner; do not hand-edit projections",
        "why": "Freshness confusion creates false-red or false-green work pressure.",
    },
]

CAP_FAMILY_PRESSURE_SPECS: List[Dict[str, Any]] = [
    {
        "family_id": "dissemination_public_release",
        "label": "Dissemination and public release",
        "needles": [
            "dissemination",
            "public release",
            "public-safe",
            "public safe",
            "outreach",
            "recipient",
            "demo",
            "website",
        ],
        "owner_surface_hint": "docs/dissemination/ | dissemination skills/standards | public projection gates",
        "suggested_action": "verify launch owner surface and shape/execute the smallest public-safe release blocker",
        "why": "Dissemination caps often express active phase pressure and can outrank ordinary capture volume.",
    },
    {
        "family_id": "microcosm_release_substrate",
        "label": "Microcosm release substrate",
        "needles": [
            "microcosm",
            "release root",
            "release candidate",
            "synthetic fixture",
            "sandbox",
            "scaffold_idea_microcosm",
            "build_idea_microcosm",
        ],
        "owner_surface_hint": "microcosm release builders, public projection scaffolds, and release candidate registry",
        "suggested_action": "patch or refresh the microcosm owner builder when source coupling is clean; otherwise shape the blocker",
        "why": "Microcosm caps are release-enabling substrate, not a single backlog row.",
    },
    {
        "family_id": "frontend_view_or_contract",
        "label": "Frontend view, graph, and contract substrate",
        "needles": [
            "frontend",
            "root navigator",
            "rootnavigator",
            "station",
            "view contract",
            "semantic layer",
            "screenshot",
            "tsx",
        ],
        "owner_surface_hint": "system/server/ui | frontend route graph | view/receipt standards",
        "suggested_action": "verify the frontend owner route and patch the contract, checker, or visible UI surface",
        "why": "Frontend caps often hide whether the cure is UI code, view metadata, standards, or proof gates.",
    },
    {
        "family_id": "task_ledger_priority_substrate",
        "label": "Task Ledger, Work Ledger, and priority substrate",
        "needles": [
            "task ledger",
            "task_ledger",
            "work ledger",
            "work_ledger",
            "priority",
            "organizer",
            "workitem",
            "work item",
            "missing contract",
        ],
        "owner_surface_hint": "system/lib/task_ledger_events.py | tools/meta/factory/task_ledger_apply.py | Work Ledger tools",
        "suggested_action": "patch organizer/report/command guidance or shape exact ledger events after owner verification",
        "why": "Ledger caps affect how future agents select, mutate, and close work.",
    },
    {
        "family_id": "autonomous_seed_or_metabolism",
        "label": "Autonomous seed or metabolism loop drift",
        "needles": [
            "autonomous seed",
            "autonomous_seed",
            "seed drift",
            "metabolism",
            "metabolic",
            "overnight",
            "rotautonomous",
        ],
        "owner_surface_hint": "state/meta_missions/type_a_autonomous_seed_loop/seeds/ | autonomous seed standards/skills",
        "suggested_action": "rewrite the seed or governing standard when it produces no-op classification loops",
        "why": "Weak seeds create repeated low-value passes unless the action contract is repaired.",
    },
    {
        "family_id": "navigation_route_or_context",
        "label": "Navigation, route, and context-pack repair",
        "needles": [
            "navigation",
            "context-pack",
            "context pack",
            "route",
            "docs-route",
            "option surface",
            "kind-atlas",
            "hologram",
        ],
        "owner_surface_hint": "kernel entry/context routes, navigation metabolism, and option surfaces",
        "suggested_action": "patch the point-of-use route or route diagnostic that made the work hard to find",
        "why": "Route caps convert repeated rediscovery into a reusable entry surface.",
    },
    {
        "family_id": "generated_projection_freshness",
        "label": "Generated projection and freshness debt",
        "needles": [
            "generated projection",
            "generated state",
            "projection stale",
            "stale generated",
            "hologram stale",
            "source coupling",
            "freshness",
        ],
        "owner_surface_hint": "generated owner builder/checker, generated_state_drainer, or projection registry",
        "suggested_action": "run or patch the generated owner only after source ownership/currentness is clear",
        "why": "Freshness caps frequently need owner-route repair, not hand-edited generated outputs.",
    },
    {
        "family_id": "standard_skill_or_paper_module",
        "label": "Standard, skill, or paper-module substrate",
        "needles": [
            "standard",
            "std_",
            "skill",
            "paper module",
            "paper_module",
            "doctrine",
            "principle",
            "axiom",
        ],
        "owner_surface_hint": "codex/standards | codex/doctrine/skills | codex/doctrine/paper_modules",
        "suggested_action": "patch the narrowest governing standard, skill, or paper module and validate its projection",
        "why": "These caps usually point at reusable doctrine substrate rather than one execution row.",
    },
    {
        "family_id": "annex_or_prior_art",
        "label": "Annex and prior-art assimilation",
        "needles": [
            "annex",
            "prior art",
            "pattern transfer",
            "distillation",
            "external pack",
        ],
        "owner_surface_hint": "annex_import.py, annex registry, and annex pattern-transfer doctrine",
        "suggested_action": "route through annex validation/pattern transfer before importing or copying substrate",
        "why": "Annex caps often need transfer disposition, not direct adoption.",
    },
    {
        "family_id": "provider_or_benchmark",
        "label": "Provider, bridge, benchmark, or calibration substrate",
        "needles": [
            "provider",
            "benchmark",
            "verisoftbench",
            "openrouter",
            "bridge",
            "calibration",
        ],
        "owner_surface_hint": "provider runtime, benchmark calibration spine, and bridge/proof tools",
        "suggested_action": "verify runtime artifacts and patch the provider/benchmark owner path when local and safe",
        "why": "Provider caps can hide whether failure is harness, model output, benchmark fixture, or bridge routing.",
    },
    {
        "family_id": "correction_or_supersession_chain",
        "label": "Correction, supersession, duplicate, or stale chain",
        "needles": [
            "correction",
            "supersedes",
            "supercedes",
            "duplicate",
            "stale",
            "retire",
            "demote",
        ],
        "owner_surface_hint": "Task Ledger merge/retire/provenance events plus live owner-surface proof",
        "suggested_action": "collapse the chain only after verifying the current owner truth and preserving provenance",
        "why": "Correction chains are noise until the surviving truth is discoverable at the owner surface.",
    },
    {
        "family_id": "public_private_boundary",
        "label": "Public/private disclosure boundary",
        "needles": [
            "private",
            "public/private",
            "disclosure",
            "redaction",
            "secret",
            "forbidden",
            "safe public",
            "controlled review",
        ],
        "owner_surface_hint": "disclosure map, dissemination gate, and public-safe projection checks",
        "suggested_action": "patch or shape disclosure gate behavior before exposing or claiming public-safe material",
        "why": "Disclosure uncertainty is a hard gate for public-facing work.",
    },
]


def _sample_rows(rows: Sequence[Mapping[str, Any]], *, limit: int = 5) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    for row in rows[:limit]:
        samples.append(
            {
                "id": row.get("id"),
                "title": row.get("title"),
                "state": row.get("state"),
                "triage_status": row.get("triage_status"),
                "recommended_action": row.get("recommended_action"),
                "missing_fields": list(row.get("missing_fields") or row.get("missing_contracts") or []),
                "categories": list(row.get("categories") or []),
                "reasons": list(row.get("reasons") or []),
                "updated_at": row.get("updated_at"),
            }
        )
    return samples


def _count_by_key(rows: Sequence[Mapping[str, Any]], key: str) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key) or "unknown")] += 1
    return dict(sorted(counts.items()))


def _top_ids(rows: Sequence[Mapping[str, Any]], *, limit: int) -> List[str]:
    ids: List[str] = []
    for row in rows[:limit]:
        row_id = str(row.get("id") or "").strip()
        if row_id:
            ids.append(row_id)
    return ids


def _compact_recursive_text(value: Any) -> str:
    parts: List[str] = []

    def visit(node: Any) -> None:
        if node is None:
            return
        if isinstance(node, Mapping):
            for key, nested in node.items():
                parts.append(str(key))
                visit(nested)
            return
        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for nested in node:
                visit(nested)
            return
        parts.append(str(node))

    visit(value)
    return " ".join(part for part in parts if part).lower()


def _load_family_action_receipts(repo_root: Path) -> Dict[str, List[Dict[str, Any]]]:
    receipts_root = repo_root / DISCOVERY_RECEIPTS_REL
    receipts: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    if not receipts_root.exists():
        return {}
    for path in sorted(receipts_root.glob("*family_action*.json")):
        payload = _safe_read_json(path)
        if payload.get("kind") != "task_ledger_family_action_receipt":
            continue
        family_id = str(payload.get("family_id") or "").strip()
        receipt_id = str(payload.get("receipt_id") or path.stem).strip()
        if not family_id:
            continue
        receipts[family_id].append(
            {
                "receipt_id": receipt_id,
                "path": str(path.relative_to(repo_root)) if path.is_absolute() else str(path),
                "created_at": payload.get("created_at"),
                "owner_action": payload.get("owner_action") if isinstance(payload.get("owner_action"), Mapping) else {},
                "source_family_snapshot": (
                    payload.get("source_family_snapshot")
                    if isinstance(payload.get("source_family_snapshot"), Mapping)
                    else {}
                ),
                "applied_dispositions": _family_action_receipt_applied_dispositions(payload),
            }
        )
    return {family_id: rows for family_id, rows in receipts.items()}


def _family_action_receipt_applied_dispositions(payload: Mapping[str, Any]) -> List[Dict[str, Any]]:
    manifest = payload.get("row_disposition_manifest")
    if not isinstance(manifest, Mapping):
        return []
    rows = manifest.get("applied_dispositions")
    if not isinstance(rows, list):
        return []
    return [dict(row) for row in rows if isinstance(row, Mapping)]


def _latest_family_action_receipt(
    family_id: str,
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
) -> Dict[str, Any] | None:
    rows = [
        row for row in family_action_receipts.get(family_id, [])
        if isinstance(row, Mapping)
    ]
    if not rows:
        return None
    return dict(
        sorted(
            rows,
            key=lambda row: (
                str(row.get("created_at") or ""),
                str(row.get("receipt_id") or ""),
                str(row.get("path") or ""),
            ),
        )[-1]
    )


def _family_action_visibility(
    family_id: str,
    rows: Sequence[Mapping[str, Any]],
    *,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
    sample_limit: int,
) -> Dict[str, Any]:
    family_token = f"family_action_{family_id}".lower()
    latest_receipt = _latest_family_action_receipt(family_id, family_action_receipts)
    receipt_ids = [
        str(row.get("receipt_id") or "").strip().lower()
        for row in family_action_receipts.get(family_id, [])
        if isinstance(row, Mapping) and str(row.get("receipt_id") or "").strip()
    ]

    covered_ids: List[str] = []
    referenced_ids: List[str] = []
    noted_ids: List[str] = []
    propagated_ids: List[str] = []
    retired_ids: List[str] = []
    blocked_ids: List[str] = []
    closed_ids: List[str] = []
    explicitly_left_open_ids: List[str] = []
    receipt_dispositions_by_id: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for receipt in family_action_receipts.get(family_id, []):
        if not isinstance(receipt, Mapping):
            continue
        for disposition in receipt.get("applied_dispositions") or []:
            if not isinstance(disposition, Mapping):
                continue
            subject_id = str(disposition.get("subject_id") or disposition.get("work_item_id") or "").strip()
            if subject_id:
                receipt_dispositions_by_id[subject_id].append(dict(disposition))

    def append_unique(values: List[str], value: str) -> None:
        if value and value not in values:
            values.append(value)

    def has_family_ref(text: str) -> bool:
        text = text.lower()
        return family_token in text or any(receipt_id in text for receipt_id in receipt_ids)

    def has_coverage_marker(text: str) -> bool:
        text = text.lower()
        coverage_tokens = [family_token, *receipt_ids]
        return any(
            f"covered by {token}" in text
            or f"covered_by_family_action_receipt:{token}" in text
            for token in coverage_tokens
        )

    def receipt_disposition_is_covered(dispositions: Sequence[Mapping[str, Any]]) -> bool:
        return any(
            has_coverage_marker(_compact_recursive_text(disposition))
            or "covered_by_family_action_receipt" in _compact_recursive_text(disposition)
            for disposition in dispositions
        )

    def receipt_disposition_is_left_open(dispositions: Sequence[Mapping[str, Any]]) -> bool:
        if receipt_disposition_is_covered(dispositions):
            return False
        disposition_text = " ".join(_compact_recursive_text(disposition) for disposition in dispositions)
        return any(
            marker in disposition_text
            for marker in (
                "not fully closed",
                "left open intentionally",
                "still belongs",
                "not fully covered",
                "referenced by",
            )
        )

    for row in rows:
        row_id = str(row.get("id") or "").strip()
        if not row_id:
            continue
        item = work_items_by_id.get(row_id, {})
        state = str(item.get("state") or row.get("state") or "").strip().lower()
        triage_status = str(row.get("triage_status") or "").strip().lower()
        item_text = _compact_recursive_text(item)
        notes = [
            note for note in item.get("notes", [])
            if isinstance(note, Mapping)
        ]
        note_text = " ".join(
            _compact_recursive_text(note.get("note"))
            for note in notes
        )
        receipt_dispositions = receipt_dispositions_by_id.get(row_id, [])
        receipt_referenced = bool(receipt_dispositions)
        receipt_covered = receipt_disposition_is_covered(receipt_dispositions)
        propagation_text = _compact_recursive_text(item.get("propagation"))
        family_referenced = has_family_ref(item_text) or receipt_referenced
        family_noted = has_family_ref(note_text)
        family_propagated = has_family_ref(propagation_text)
        left_open = receipt_disposition_is_left_open(receipt_dispositions) or any(
            marker in note_text
            for marker in (
                "not fully closed",
                "left open intentionally",
                "still belongs",
                "not fully covered",
                "referenced by",
            )
        ) and not any(
            marker in note_text
            for marker in (
                "historical or already-disposed",
                "covered by",
                "covered_by_family_action_receipt",
            )
        )
        covered = receipt_covered or (
            family_referenced and not left_open and (
                family_propagated
                or has_coverage_marker(note_text)
                or state in {"done", "propagated", "retired"}
            )
        )

        if family_referenced:
            append_unique(referenced_ids, row_id)
        if family_noted:
            append_unique(noted_ids, row_id)
        if family_propagated:
            append_unique(propagated_ids, row_id)
        if state == "retired":
            append_unique(retired_ids, row_id)
        if state == "blocked":
            append_unique(blocked_ids, row_id)
        if state in {"done", "propagated", "retired"} or triage_status == "closed_or_signed_off":
            append_unique(closed_ids, row_id)
        if left_open:
            append_unique(explicitly_left_open_ids, row_id)
        if covered:
            append_unique(covered_ids, row_id)

    covered_set = set(covered_ids)
    closed_set = set(closed_ids)
    blocked_set = set(blocked_ids)
    referenced_but_uncovered_ids = [
        row_id for row_id in referenced_ids
        if row_id not in covered_set
    ]
    actionable_open_ids = [
        str(row.get("id") or "").strip()
        for row in rows
        if str(row.get("id") or "").strip()
        and str(row.get("id") or "").strip() not in covered_set
        and str(row.get("id") or "").strip() not in closed_set
        and str(row.get("id") or "").strip() not in blocked_set
    ]
    actionable_open_count = len(actionable_open_ids)

    latest_receipt_coverage_status = "none"
    if latest_receipt:
        if referenced_ids and covered_ids and actionable_open_count == 0:
            latest_receipt_coverage_status = "covering"
        elif referenced_ids and covered_ids:
            latest_receipt_coverage_status = "partial"
        elif referenced_ids:
            latest_receipt_coverage_status = "adjacent_noncovering"
        else:
            latest_receipt_coverage_status = "receipt_without_row_dispositions"

    recommended = "inspect_owner_surface"
    if latest_receipt_coverage_status == "covering":
        recommended = "already_dissolved"
    elif latest_receipt_coverage_status == "partial":
        recommended = "inspect_top_actionable_open_ids_or_misfamily_overlap"
    elif latest_receipt_coverage_status == "adjacent_noncovering":
        recommended = "inspect_top_actionable_open_ids_or_split_family"
    elif latest_receipt:
        recommended = "apply_row_dispositions_or_sample_uncovered_rows"

    why_still_open = None
    if actionable_open_ids:
        why_still_open = "Rows not covered by the latest family-action receipt still require owner inspection or reclassification."
        if latest_receipt_coverage_status == "adjacent_noncovering":
            why_still_open = (
                "The latest family-action receipt references rows but covers none; "
                "treat it as adjacent/non-covering evidence or split the family."
            )
        elif explicitly_left_open_ids:
            why_still_open = (
                "Some rows were explicitly left open because the prior receipt only covered "
                "part of their failure mode."
            )

    return {
        "schema_version": "task_ledger_family_action_visibility_v0",
        "raw_family_count": len(rows),
        "covered_by_family_action_receipt_count": len(covered_ids),
        "row_disposition_reference_count": len(referenced_ids),
        "referenced_but_uncovered_count": len(referenced_but_uncovered_ids),
        "receipt_disposition_count": sum(len(rows) for rows in receipt_dispositions_by_id.values()),
        "receipt_disposition_covered_count": len(
            [row_id for row_id in receipt_dispositions_by_id if row_id in covered_set]
        ),
        "noted_count": len(noted_ids),
        "propagated_count": len(propagated_ids),
        "retired_count": len(retired_ids),
        "blocked_count": len(blocked_ids),
        "closed_or_inactive_count": len(closed_ids),
        "actionable_open_count": actionable_open_count,
        "top_covered_ids": covered_ids[:sample_limit],
        "top_referenced_ids": referenced_ids[:sample_limit],
        "top_referenced_but_uncovered_ids": referenced_but_uncovered_ids[:sample_limit],
        "top_actionable_open_ids": actionable_open_ids[:sample_limit],
        "explicitly_left_open_ids": explicitly_left_open_ids[:sample_limit],
        "last_family_action_receipt": latest_receipt.get("receipt_id") if latest_receipt else None,
        "last_family_action_receipt_path": latest_receipt.get("path") if latest_receipt else None,
        "latest_receipt_coverage_status": latest_receipt_coverage_status,
        "recommended_next_family_action": recommended,
        "why_still_open": why_still_open,
        "actionable_count_basis": (
            "raw_family_count minus rows covered by a family-action receipt, terminal/"
            "inactive rows, and blocked rows; raw count remains historical evidence."
        ),
    }


def _family_target_dependency_status(
    target_ids: Sequence[str],
    *,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    sample_limit: int,
) -> Dict[str, Any]:
    schedulable_ids: List[str] = []
    blocked_ids: List[str] = []
    closed_ids: List[str] = []
    unknown_ids: List[str] = []
    unsatisfied_edges: List[Dict[str, Any]] = []
    blocker_target_ids: Dict[str, set[str]] = {}

    for target_id in target_ids:
        item = work_items_by_id.get(target_id)
        if not isinstance(item, Mapping):
            unknown_ids.append(target_id)
            continue

        state = _item_state(item)
        if _is_closed_or_signed_off(item):
            closed_ids.append(target_id)
            continue

        unsatisfied_dep_ids: List[str] = []
        dangling_dep_ids: List[str] = []
        for dep_id in sorted(_hard_dependency_ids(item)):
            dependency = work_items_by_id.get(dep_id)
            if not isinstance(dependency, Mapping):
                dangling_dep_ids.append(dep_id)
                continue
            satisfied, _reason = _dependency_is_satisfied(item, dependency, dep_id)
            if not satisfied:
                unsatisfied_dep_ids.append(dep_id)

        if unsatisfied_dep_ids or dangling_dep_ids:
            blocked_ids.append(target_id)
            for dep_id in unsatisfied_dep_ids + dangling_dep_ids:
                blocker_target_ids.setdefault(dep_id, set()).add(target_id)
            unsatisfied_edges.append(
                {
                    "id": target_id,
                    "unsatisfied_dep_ids": unsatisfied_dep_ids,
                    "dangling_dep_ids": dangling_dep_ids,
                }
            )
            continue

        schedulable_ids.append(target_id)

    resolution_candidates: List[Dict[str, Any]] = []
    for dep_id, blocked_targets in blocker_target_ids.items():
        dependency = work_items_by_id.get(dep_id)
        if not isinstance(dependency, Mapping):
            resolution_candidates.append(
                {
                    "id": dep_id,
                    "title": None,
                    "state": "unknown",
                    "target_count": len(blocked_targets),
                    "blocked_target_ids": sorted(blocked_targets),
                    "schedulable": False,
                    "unsatisfied_dep_ids": [],
                    "dangling_dep_ids": [dep_id],
                }
            )
            continue

        dependency_unsatisfied_ids: List[str] = []
        dependency_dangling_ids: List[str] = []
        for upstream_id in sorted(_hard_dependency_ids(dependency)):
            upstream = work_items_by_id.get(upstream_id)
            if not isinstance(upstream, Mapping):
                dependency_dangling_ids.append(upstream_id)
                continue
            satisfied, _reason = _dependency_is_satisfied(dependency, upstream, upstream_id)
            if not satisfied:
                dependency_unsatisfied_ids.append(upstream_id)

        resolution_candidates.append(
            {
                "id": dep_id,
                "title": dependency.get("title"),
                "state": _item_state(dependency) or "unknown",
                "target_count": len(blocked_targets),
                "blocked_target_ids": sorted(blocked_targets),
                "schedulable": not dependency_unsatisfied_ids and not dependency_dangling_ids,
                "unsatisfied_dep_ids": dependency_unsatisfied_ids,
                "dangling_dep_ids": dependency_dangling_ids,
            }
        )

    resolution_candidates.sort(
        key=lambda row: (
            0 if row.get("schedulable") else 1,
            -int(row.get("target_count") or 0),
            str(row.get("id") or ""),
        )
    )
    resolution_candidate_ids = [str(row["id"]) for row in resolution_candidates if row.get("id")]
    schedulable_resolution_candidate_ids = [
        str(row["id"])
        for row in resolution_candidates
        if row.get("id") and row.get("schedulable")
    ]
    dependency_blocked_resolution_candidate_ids = [
        str(row["id"])
        for row in resolution_candidates
        if row.get("id") and not row.get("schedulable")
    ]
    resolution_command_ids = schedulable_resolution_candidate_ids or resolution_candidate_ids
    resolution_primary_command = None
    if resolution_command_ids:
        resolution_primary_command = (
            "./repo-python kernel.py --option-surface task_ledger "
            f"--band card --ids {','.join(resolution_command_ids[:sample_limit])}"
        )

    return {
        "schema_version": "task_ledger_family_next_action_dependency_status_v0",
        "target_count": len(target_ids),
        "schedulable_target_ids": schedulable_ids[:sample_limit],
        "dependency_blocked_target_ids": blocked_ids[:sample_limit],
        "closed_or_satisfied_target_ids": closed_ids[:sample_limit],
        "unknown_target_ids": unknown_ids[:sample_limit],
        "unsatisfied_dependency_edges": unsatisfied_edges[:sample_limit],
        "resolution_candidate_ids": resolution_candidate_ids[:sample_limit],
        "schedulable_resolution_candidate_ids": schedulable_resolution_candidate_ids[:sample_limit],
        "dependency_blocked_resolution_candidate_ids": dependency_blocked_resolution_candidate_ids[:sample_limit],
        "resolution_candidate_edges": resolution_candidates[:sample_limit],
        "resolution_primary_command": resolution_primary_command,
        "dependency_decision_rule": (
            "Prefer schedulable_target_ids for execution, source_patch, or family-action receipt; "
            "dependency_blocked_target_ids must resolve dependency_status before row mutation."
        ),
        "resolution_decision_rule": (
            "When family targets are dependency-blocked, open schedulable_resolution_candidate_ids "
            "before mutating the blocked target rows; use dependency_blocked_resolution_candidate_ids "
            "only to continue tracing upstream blockers."
        ),
    }


def _family_next_action(
    *,
    family_id: str,
    visibility: Mapping[str, Any],
    fallback_ids: Sequence[str],
    owner_surface_hint: Any,
    suggested_action: Any,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    sample_limit: int,
) -> Dict[str, Any]:
    recommended = str(visibility.get("recommended_next_family_action") or "inspect_owner_surface")
    top_actionable_ids = [
        str(row_id).strip()
        for row_id in visibility.get("top_actionable_open_ids", [])
        if str(row_id).strip()
    ]
    fallback_id_list = [
        str(row_id).strip()
        for row_id in fallback_ids
        if str(row_id).strip()
    ]
    target_ids = top_actionable_ids or fallback_id_list
    primary_command = None
    if target_ids:
        primary_command = (
            "./repo-python kernel.py --option-surface task_ledger "
            f"--band card --ids {','.join(target_ids)}"
        )
    target_dependency_status = _family_target_dependency_status(
        target_ids,
        work_items_by_id=work_items_by_id,
        sample_limit=sample_limit,
    )

    if recommended == "already_dissolved":
        action_type = "verify_receipt_or_retire_family_pressure"
    elif recommended == "apply_row_dispositions_or_sample_uncovered_rows":
        action_type = "apply_row_dispositions_or_write_family_action_receipt"
    elif recommended == "inspect_top_actionable_open_ids_or_split_family":
        action_type = "inspect_top_actionable_open_ids_or_split_family"
    elif recommended == "inspect_top_actionable_open_ids_or_misfamily_overlap":
        action_type = "inspect_top_actionable_open_ids_or_misfamily_overlap"
    else:
        action_type = "inspect_owner_surface"

    recommended_first_command = primary_command
    recommended_first_command_reason = "inspect_target_ids_first"
    if (
        target_dependency_status.get("dependency_blocked_target_ids")
        and not target_dependency_status.get("schedulable_target_ids")
        and target_dependency_status.get("resolution_primary_command")
    ):
        action_type = "resolve_upstream_dependency_first"
        recommended_first_command = target_dependency_status.get("resolution_primary_command")
        recommended_first_command_reason = "all_target_ids_are_dependency_blocked"
    elif target_dependency_status.get("schedulable_target_ids"):
        recommended_first_command_reason = "target_ids_include_schedulable_work_items"

    return {
        "schema_version": "task_ledger_family_next_action_v0",
        "family_id": family_id,
        "action_type": action_type,
        "recommended_next_family_action": recommended,
        "target_ids": target_ids,
        "primary_command": primary_command,
        "recommended_first_command": recommended_first_command,
        "recommended_first_command_reason": recommended_first_command_reason,
        "target_dependency_status": target_dependency_status,
        "owner_surface_hint": owner_surface_hint,
        "suggested_action": suggested_action,
        "review_boundary": (
            "inspection_only_no_auto_promote_no_auto_rerank_no_auto_retire; "
            "event-bearing state transitions require the Task Ledger event lane and review posture named by the selected card"
        ),
        "post_card_decision_rule": {
            "schema_version": "task_ledger_post_card_decision_rule_v0",
            "first_step": (
                "Run primary_command, then choose exactly one safe_mutation_lane from the opened card evidence."
            ),
            "source_patch_when": (
                "the opened cards expose one source/projection blind spot owned by owner_surface_hint"
            ),
            "work_item_shaped_when": (
                "a target card is otherwise live but lacks a satisfaction, integration, completion, or dependency contract"
            ),
            "family_action_receipt_when": (
                "the targets are foundational, mixed, blocked, or too broad for a truthful row disposition"
            ),
            "operational_handoff_when": (
                "the owner action belongs to a different live work surface after card inspection"
            ),
            "blocked_row_rule": (
                "blocked cards follow dependency_status first; do not mutate or promote a blocked row from family pressure alone"
            ),
        },
        "safe_mutation_lanes": [
            "source_patch",
            "work_item.note_added",
            "work_item.shaped",
            "family_action_receipt",
            "operational_handoff",
        ],
        "basis": (
            "Use top_actionable_open_ids from family_action_visibility when present; "
            "otherwise fall back to the family top_ids sample so future agents have an exact first drilldown."
        ),
    }


def _family_visibility_rollup(families: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    raw_total = 0
    covered_total = 0
    actionable_total = 0
    referenced_total = 0
    family_count = 0
    with_receipts = 0
    for family in families:
        visibility = family.get("family_action_visibility")
        if not isinstance(visibility, Mapping):
            continue
        family_count += 1
        raw_total += int(visibility.get("raw_family_count") or 0)
        covered_total += int(visibility.get("covered_by_family_action_receipt_count") or 0)
        actionable_total += int(visibility.get("actionable_open_count") or 0)
        referenced_total += int(visibility.get("row_disposition_reference_count") or 0)
        if visibility.get("last_family_action_receipt"):
            with_receipts += 1
    return {
        "schema_version": "task_ledger_family_pressure_visibility_rollup_v0",
        "family_count": family_count,
        "families_with_family_action_receipt": with_receipts,
        "raw_family_count_total": raw_total,
        "covered_by_family_action_receipt_count_total": covered_total,
        "row_disposition_reference_count_total": referenced_total,
        "actionable_open_count_total": actionable_total,
        "selector_count_basis": "Use actionable_open_count for family-action selector pressure; keep raw counts as historical evidence.",
    }


def _build_unconverted_substrate_debt_report(
    *,
    priority_cluster_summary: Mapping[str, Any],
    propagation_report: Mapping[str, Any],
    sample_limit: int,
) -> Dict[str, Any]:
    propagation_items = [
        row for row in propagation_report.get("items", [])
        if isinstance(row, Mapping)
    ]
    clusters = [
        row for row in priority_cluster_summary.get("clusters", [])
        if isinstance(row, Mapping)
    ]
    cap_family = next(
        (
            row for row in clusters
            if str(row.get("cluster_id") or "") == "cap_family_pressure"
        ),
        {},
    )
    family_summary = (
        cap_family.get("family_summary")
        if isinstance(cap_family.get("family_summary"), Mapping)
        else {}
    )
    pressure_visibility = (
        family_summary.get("pressure_visibility")
        if isinstance(family_summary.get("pressure_visibility"), Mapping)
        else {}
    )
    family_rows = [
        row for row in family_summary.get("families", [])
        if isinstance(row, Mapping)
    ]
    unconverted_families: List[Dict[str, Any]] = []
    family_count = 0
    families_without_receipts = 0
    for family in family_rows:
        visibility = (
            family.get("family_action_visibility")
            if isinstance(family.get("family_action_visibility"), Mapping)
            else {}
        )
        actionable_count = int(visibility.get("actionable_open_count") or 0)
        if actionable_count <= 0:
            continue
        family_count += 1
        if not visibility.get("last_family_action_receipt"):
            families_without_receipts += 1
        unconverted_families.append(
            {
                "family_id": family.get("family_id"),
                "label": family.get("label"),
                "raw_family_count": int(visibility.get("raw_family_count") or family.get("raw_family_count") or 0),
                "actionable_open_count": actionable_count,
                "covered_by_family_action_receipt_count": int(
                    visibility.get("covered_by_family_action_receipt_count") or 0
                ),
                "row_disposition_reference_count": int(
                    visibility.get("row_disposition_reference_count") or 0
                ),
                "last_family_action_receipt": visibility.get("last_family_action_receipt"),
                "latest_receipt_coverage_status": visibility.get("latest_receipt_coverage_status"),
                "recommended_next_family_action": visibility.get("recommended_next_family_action"),
                "owner_surface_hint": family.get("owner_surface_hint"),
                "suggested_action": family.get("suggested_action"),
                "next_family_action": family.get("next_family_action"),
                "top_actionable_open_ids": list(
                    visibility.get("top_actionable_open_ids") or family.get("top_ids") or []
                )[:sample_limit],
            }
        )
    unconverted_families.sort(
        key=lambda row: (
            str(row.get("family_id") or "") == "other_cap_family",
            -int(row.get("actionable_open_count") or 0),
            str(row.get("family_id") or ""),
        )
    )
    report_state_counts = propagation_report.get("state_counts")
    propagation_state_counts = (
        dict(report_state_counts)
        if isinstance(report_state_counts, Mapping)
        else _count_by_key(propagation_items, "state")
    )
    propagation_candidate_count = int(propagation_report.get("candidate_count") or len(propagation_items))
    family_actionable_total = int(pressure_visibility.get("actionable_open_count_total") or 0)
    status = "clear"
    if propagation_candidate_count or family_actionable_total:
        status = "debt_present"
    return {
        "schema_version": "task_ledger_unconverted_substrate_debt_v0",
        "status": status,
        "purpose": (
            "Expose cap clusters that have not yet been converted into substrate "
            "improvements, family-action receipts, or explicit nothing_to_refine dispositions."
        ),
        "source_views": [
            "state/task_ledger/views/propagation_needed.json",
            "state/task_ledger/views/capture_triage.json",
        ],
        "source_report_paths": [
            "priority_cluster_summary.clusters[cap_family_pressure]",
            "propagation_needed",
        ],
        "summary": {
            "propagation_needed_count": propagation_candidate_count,
            "propagation_state_counts": propagation_state_counts,
            "family_actionable_open_count_total": family_actionable_total,
            "family_raw_count_total": int(pressure_visibility.get("raw_family_count_total") or 0),
            "family_count": family_count,
            "families_without_family_action_receipt_count": families_without_receipts,
            "covered_by_family_action_receipt_count_total": int(
                pressure_visibility.get("covered_by_family_action_receipt_count_total") or 0
            ),
            "row_disposition_reference_count_total": int(
                pressure_visibility.get("row_disposition_reference_count_total") or 0
            ),
        },
        "clusters": [
            {
                "cluster_id": "closed_work_missing_propagation",
                "source_view": "propagation_needed",
                "count": propagation_candidate_count,
                "state_counts": propagation_state_counts,
                "top_ids": _top_ids(propagation_items, limit=sample_limit),
                "disposition": "inspect_owner_surface_then_propagate_or_nothing_to_refine",
                "safe_mutation": "owner_surface_patch_or_verification + work_item.propagation_recorded",
                "why": (
                    "Closed or signed-off work with a generalization signal needs owner-surface "
                    "actuation or verification before its reusable-lesson disposition is recorded."
                ),
            },
            {
                "cluster_id": "cap_family_missing_family_action_receipts",
                "source_view": "capture_triage",
                "count": family_actionable_total,
                "family_count": family_count,
                "families_without_family_action_receipt_count": families_without_receipts,
                "top_families": unconverted_families[:sample_limit],
                "disposition": "inspect_owner_surface_or_write_family_action_receipt",
                "safe_mutation": "source_patch | work_item.note_added | work_item.shaped | family_action_receipt",
                "why": "Repeated cap families remain raw pressure until an owner patch, receipt, or row-level disposition consumes them.",
            },
        ],
        "recommended_order": [
            (
                "Start with closed_work_missing_propagation when the owner surface is named or "
                "readable; patch or verify that owner before appending the propagation receipt."
            ),
            "Use cap_family_missing_family_action_receipts when a repeated family points at one owner-surface patch rather than many row events.",
            "Do not execute from unbucketed cap volume until representative cards identify a coherent owner surface.",
        ],
    }


def _family_summaries(
    rows: Sequence[Mapping[str, Any]],
    *,
    specs: Sequence[Mapping[str, Any]],
    row_text: Any,
    sample_limit: int,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
    other_family_id: str,
    other_label: str,
    other_owner_surface_hint: str,
    other_suggested_action: str,
    other_why: str,
) -> List[Dict[str, Any]]:
    buckets: Dict[str, List[Mapping[str, Any]]] = {
        str(spec["family_id"]): [] for spec in specs
    }
    other_rows: List[Mapping[str, Any]] = []
    for row in rows:
        text = row_text(row)
        matched_spec: Mapping[str, Any] | None = None
        for spec in specs:
            if not any(str(needle).lower() in text for needle in spec.get("needles", [])):
                continue
            if any(str(needle).lower() in text for needle in spec.get("exclude_needles", [])):
                continue
            matched_spec = spec
            break
        if matched_spec:
            buckets[str(matched_spec["family_id"])].append(row)
        else:
            other_rows.append(row)

    summaries: List[Dict[str, Any]] = []
    for index, spec in enumerate(specs):
        family_id = str(spec["family_id"])
        family_rows = buckets.get(family_id, [])
        if not family_rows:
            continue
        top_ids = _top_ids(family_rows, limit=sample_limit)
        visibility = _family_action_visibility(
            family_id,
            family_rows,
            work_items_by_id=work_items_by_id,
            family_action_receipts=family_action_receipts,
            sample_limit=sample_limit,
        )
        summaries.append(
            {
                "_priority_order": index,
                "family_id": family_id,
                "label": spec.get("label"),
                "count": len(family_rows),
                "raw_family_count": len(family_rows),
                "top_ids": top_ids,
                "owner_surface_hint": spec.get("owner_surface_hint"),
                "suggested_action": spec.get("suggested_action"),
                "why": spec.get("why"),
                "family_action_visibility": visibility,
                "next_family_action": _family_next_action(
                    family_id=family_id,
                    visibility=visibility,
                    fallback_ids=top_ids,
                    owner_surface_hint=spec.get("owner_surface_hint"),
                    suggested_action=spec.get("suggested_action"),
                    work_items_by_id=work_items_by_id,
                    sample_limit=sample_limit,
                ),
            }
        )
    if other_rows:
        top_ids = _top_ids(other_rows, limit=sample_limit)
        visibility = _family_action_visibility(
            other_family_id,
            other_rows,
            work_items_by_id=work_items_by_id,
            family_action_receipts=family_action_receipts,
            sample_limit=sample_limit,
        )
        summaries.append(
            {
                "_priority_order": len(specs),
                "family_id": other_family_id,
                "label": other_label,
                "count": len(other_rows),
                "raw_family_count": len(other_rows),
                "top_ids": top_ids,
                "owner_surface_hint": other_owner_surface_hint,
                "suggested_action": other_suggested_action,
                "why": other_why,
                "family_action_visibility": visibility,
                "next_family_action": _family_next_action(
                    family_id=other_family_id,
                    visibility=visibility,
                    fallback_ids=top_ids,
                    owner_surface_hint=other_owner_surface_hint,
                    suggested_action=other_suggested_action,
                    work_items_by_id=work_items_by_id,
                    sample_limit=sample_limit,
                ),
            }
        )
    summaries.sort(
        key=lambda row: (
            str(row.get("family_id") or "") == other_family_id,
            -int(row.get("count") or 0),
            int(row.get("_priority_order") or 0),
        )
    )
    for summary in summaries:
        summary.pop("_priority_order", None)
    return summaries


def _self_error_family_summaries(
    rows: Sequence[Mapping[str, Any]],
    *,
    row_text: Any,
    sample_limit: int,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    return _family_summaries(
        rows,
        specs=SELF_ERROR_FAILURE_FAMILY_SPECS,
        row_text=row_text,
        sample_limit=sample_limit,
        work_items_by_id=work_items_by_id,
        family_action_receipts=family_action_receipts,
        other_family_id="other_self_error",
        other_label="Other self-error pressure",
        other_owner_surface_hint="select representative cards and verify the named owner surface",
        other_suggested_action="aggregate siblings before minting global doctrine",
        other_why="Unbucketed self-errors still need owner verification before action.",
    )


def _cap_family_summaries(
    rows: Sequence[Mapping[str, Any]],
    *,
    row_text: Any,
    sample_limit: int,
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
) -> List[Dict[str, Any]]:
    return _family_summaries(
        rows,
        specs=CAP_FAMILY_PRESSURE_SPECS,
        row_text=row_text,
        sample_limit=sample_limit,
        work_items_by_id=work_items_by_id,
        family_action_receipts=family_action_receipts,
        other_family_id="other_cap_family",
        other_label="Other cap-family pressure",
        other_owner_surface_hint="open representative Task Ledger cards and verify current owner state",
        other_suggested_action="shape, link, retire, or patch only after a coherent owner surface is known",
        other_why="Unbucketed cap rows still need clustering before they become priority instructions.",
    )


def _build_priority_cluster_summary(
    *,
    views: Mapping[str, Any],
    work_items_by_id: Mapping[str, Mapping[str, Any]],
    family_action_receipts: Mapping[str, Sequence[Mapping[str, Any]]],
    propagation_report: Mapping[str, Any],
    adapter_audit: Mapping[str, Any],
    sample_limit: int,
) -> Dict[str, Any]:
    def view_rows(view_id: str) -> List[Mapping[str, Any]]:
        view = views.get(view_id) if isinstance(views.get(view_id), Mapping) else {}
        return [
            row for row in view.get("items", [])
            if isinstance(row, Mapping)
        ]

    raw_rows = [
        row for row in view_rows("capture_triage")
        if "raw_capture_inbox" in (row.get("categories") or [])
    ]
    triage_rows = view_rows("capture_triage")

    def row_text(row: Mapping[str, Any]) -> str:
        parts: List[str] = []
        for key in ("id", "title", "statement", "work_item_type", "triage_status", "recommended_action"):
            value = row.get(key)
            if value:
                parts.append(str(value))
        for key in ("categories", "tags", "source_refs", "reasons"):
            value = row.get(key)
            if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
                parts.extend(str(item) for item in value)
        return " ".join(parts).lower()

    def matching_rows(*needles: str) -> List[Mapping[str, Any]]:
        lowered = [needle.lower() for needle in needles]
        return [
            row for row in triage_rows
            if any(needle in row_text(row) for needle in lowered)
        ]

    cap_rows = [
        row for row in triage_rows
        if str(row.get("id") or "").startswith(("cap_", "cap:", "cap-"))
        or str(row.get("work_item_type") or "").lower() in {"cap", "capability", "cap_family"}
    ]
    self_error_rows = matching_rows("self_error", "self error", "false green", "mistake")
    seed_rows = matching_rows("autonomous_seed", "autonomous seed", "seed drift", "seed")
    mechanism_rows = matching_rows("mechanism", "route gap", "owner route", "standard gap")
    adapter_rows = [
        row for row in adapter_audit.get("examples", [])
        if isinstance(row, Mapping) and row.get("disposition") == "possible_leak"
    ]
    cap_family_rows = _cap_family_summaries(
        cap_rows,
        row_text=row_text,
        sample_limit=sample_limit,
        work_items_by_id=work_items_by_id,
        family_action_receipts=family_action_receipts,
    )
    self_error_family_rows = _self_error_family_summaries(
        self_error_rows,
        row_text=row_text,
        sample_limit=sample_limit,
        work_items_by_id=work_items_by_id,
        family_action_receipts=family_action_receipts,
    )
    clusters = [
        {
            "cluster_id": "execution_menu_committed",
            "source_view": "execution_menu",
            "object_type": "execution_menu_commitment",
            "priority_band": "act_first_when_schedulable",
            "count": len(view_rows("execution_menu")),
            "top_ids": _top_ids(view_rows("execution_menu"), limit=sample_limit),
            "next_event": "claim | execute | block | closeout",
            "why": "Explicit commitment beats shaped-candidate salience.",
        },
        {
            "cluster_id": "execution_menu_schedulable",
            "source_view": "execution_menu_schedulable",
            "object_type": "execution_menu_commitment",
            "priority_band": "highest_actionable_subset",
            "count": len(view_rows("execution_menu_schedulable")),
            "top_ids": _top_ids(view_rows("execution_menu_schedulable"), limit=sample_limit),
            "next_event": "claim_or_execute_committed_work",
            "why": "Committed rows whose hard dependencies are satisfied are the cleanest execution candidates.",
        },
        {
            "cluster_id": "dependency_blocked",
            "source_view": "dependency_blocked",
            "object_type": "dependency_blocker",
            "priority_band": "unblock_or_reclassify_before_execution",
            "count": len(view_rows("dependency_blocked")),
            "top_ids": _top_ids(view_rows("dependency_blocked"), limit=sample_limit),
            "next_event": "complete_dependency | block | note dependency_resolution",
            "why": "Blocked committed work can outrank fresh work when resolving one prerequisite unlocks downstream rows.",
        },
        {
            "cluster_id": "cap_family_pressure",
            "source_view": "capture_triage",
            "object_type": "cap_family",
            "priority_band": "aggregate_or_patch_owner_before_queue_draining",
            "count": len(cap_rows),
            "top_ids": _top_ids(cap_rows, limit=sample_limit),
            "family_summary": {
                "schema_version": "task_ledger_cap_family_summary_v0",
                "bucket_rule": "first matching cap-family spec over id/title/statement/type/status/recommended_action/categories/tags/source_refs/reasons; unbucketed rows stay visible as other_cap_family",
                "pressure_visibility": _family_visibility_rollup(cap_family_rows),
                "families": cap_family_rows,
            },
            "next_event": "source_patch | shape | aggregate_failure_family | operational_handoff",
            "why": "Repeated caps are memory signals; the right action may be an owner-surface repair rather than a single-row priority decision.",
        },
        {
            "cluster_id": "self_error_pressure",
            "source_view": "capture_triage",
            "object_type": "self_error_cluster",
            "priority_band": "repair_failure_class_before_repeating_work",
            "count": len(self_error_rows),
            "top_ids": _top_ids(self_error_rows, limit=sample_limit),
            "family_summary": {
                "schema_version": "task_ledger_self_error_family_summary_v0",
                "bucket_rule": "first matching failure-family spec over id/title/statement/type/status/recommended_action/categories/tags/source_refs/reasons; unbucketed rows stay visible as other_self_error",
                "pressure_visibility": _family_visibility_rollup(self_error_family_rows),
                "families": self_error_family_rows,
            },
            "next_event": "patch owner route | propagate lesson | shape failure family",
            "why": "Self-error clusters should reduce future false completion, wrong-route, or command-boundary failures.",
        },
        {
            "cluster_id": "autonomous_seed_pressure",
            "source_view": "capture_triage",
            "object_type": "autonomous_seed_drift",
            "priority_band": "seed_rewrite_or_owner_contract_patch",
            "count": len(seed_rows),
            "top_ids": _top_ids(seed_rows, limit=sample_limit),
            "next_event": "seed_rewrite | standard_patch | operational_handoff",
            "why": "A seed that repeatedly reports instead of changing substrate should be rewritten or bounded by a stronger action contract.",
        },
        {
            "cluster_id": "mechanism_pressure_lens",
            "source_view": "capture_triage + option_surface:task_ledger mechanism clusters",
            "object_type": "mechanism_or_route_pressure",
            "priority_band": "route_or_owner_surface_repair",
            "count": len(mechanism_rows),
            "top_ids": _top_ids(mechanism_rows, limit=sample_limit),
            "next_event": "patch route | patch standard/skill | write_or_refine paper module",
            "why": "Mechanism, route, and standard-pressure clusters may point at the owner surface future agents need, not at an individual WorkItem.",
        },
        {
            "cluster_id": "work_ledger_unlinked",
            "source_view": "work_ledger_unlinked",
            "object_type": "generated_state_or_work_ledger_gap",
            "priority_band": "coordination_gap_before_more_work",
            "count": len(view_rows("work_ledger_unlinked")),
            "top_ids": _top_ids(view_rows("work_ledger_unlinked"), limit=sample_limit),
            "next_event": "link | closeout | append_exempt | shape owner handoff",
            "why": "Unlinked execution receipts waste future coordination and can hide work that already happened.",
        },
        {
            "cluster_id": "metabolic_running",
            "source_view": "metabolic_running",
            "object_type": "runtime_loop_pressure",
            "priority_band": "runtime_owner_check",
            "count": len(view_rows("metabolic_running")),
            "top_ids": _top_ids(view_rows("metabolic_running"), limit=sample_limit),
            "next_event": "owner_check | block | closeout | handoff",
            "why": "Running metabolic work can outrank raw captures when it is already consuming runtime attention.",
        },
        {
            "cluster_id": "meta_mission_active",
            "source_view": "meta_mission_active",
            "object_type": "active_mission_pressure",
            "priority_band": "mission_continuity_before_new_backlog",
            "count": len(view_rows("meta_mission_active")),
            "top_ids": _top_ids(view_rows("meta_mission_active"), limit=sample_limit),
            "next_event": "continue | block | closeout | refine mission owner",
            "why": "Active meta-missions are already selected work pressure; they should not be buried under fresh capture volume.",
        },
        {
            "cluster_id": "mission_operating_picture",
            "source_view": "mission_operating_picture",
            "object_type": "operating_picture_projection",
            "priority_band": "mission_visibility_before_parallel_execution",
            "count": len(view_rows("mission_operating_picture")),
            "top_ids": _top_ids(view_rows("mission_operating_picture"), limit=sample_limit),
            "next_event": "inspect_projection | populate_umbrella_refs | continue_selected_mission",
            "why": "The operating-picture projection composes active mission, execution, dependency, and umbrella-gap pressure before choosing the next mission slice.",
        },
        {
            "cluster_id": "promotion_candidates",
            "source_view": "promotion_candidates",
            "object_type": "promotion_candidate",
            "priority_band": "operator_review_before_commitment",
            "count": len(view_rows("promotion_candidates")),
            "top_ids": _top_ids(view_rows("promotion_candidates"), limit=sample_limit),
            "next_event": "promote_or_finish_shape",
            "why": "Shaped captures are candidates; promotion is a deliberate priority decision.",
        },
        {
            "cluster_id": "missing_contracts",
            "source_view": "missing_contracts_ranked",
            "object_type": "missing_contract",
            "priority_band": "shape_before_score",
            "count": len(view_rows("missing_contracts_ranked")),
            "top_ids": _top_ids(view_rows("missing_contracts_ranked"), limit=sample_limit),
            "next_event": "shape satisfaction/integration/completion contracts",
            "why": "Rows without contracts need better definition before they become execution priority.",
        },
        {
            "cluster_id": "merge_or_retire",
            "source_view": "merge_or_retire_candidates",
            "object_type": "duplicate_or_supersession_chain",
            "priority_band": "reduce_duplicate_pressure",
            "count": len(view_rows("merge_or_retire_candidates")),
            "top_ids": _top_ids(view_rows("merge_or_retire_candidates"), limit=sample_limit),
            "next_event": "operator_review_then_retire_or_note",
            "why": "Duplicate pressure should compact the ledger instead of creating more captures.",
        },
        {
            "cluster_id": "propagation_needed",
            "source_view": "propagation_needed",
            "object_type": "propagation_debt",
            "priority_band": "learn_from_closed_work",
            "count": len([
                row for row in propagation_report.get("items", [])
                if isinstance(row, Mapping)
            ]),
            "top_ids": _top_ids(
                [
                    row for row in propagation_report.get("items", [])
                    if isinstance(row, Mapping)
                ],
                limit=sample_limit,
            ),
            "next_event": "propagate already_propagated_verified | nothing_to_refine | propagation_debt",
            "why": "Closed work that has not taught the general artifact is not cleanly closed.",
        },
        {
            "cluster_id": "needs_signoff",
            "source_view": "needs_signoff",
            "object_type": "operator_review_or_signoff_gap",
            "priority_band": "prove_or_residualize_before_new_work",
            "count": len(view_rows("needs_signoff")),
            "top_ids": _top_ids(view_rows("needs_signoff"), limit=sample_limit),
            "next_event": "signoff | residual_capture | closeout_assurance",
            "why": "Unsigned work can leave false-completion pressure that future agents must rediscover.",
        },
        {
            "cluster_id": "operator_needed",
            "source_view": "operator_needed",
            "object_type": "operator_review_or_signoff_gap",
            "priority_band": "ask_or_shape_review_boundary",
            "count": len(view_rows("operator_needed")),
            "top_ids": _top_ids(view_rows("operator_needed"), limit=sample_limit),
            "next_event": "ask | shape review boundary | block",
            "why": "Operator-needed rows should be explicit review boundaries, not hidden blockers inside the queue.",
        },
        {
            "cluster_id": "raw_capture_inbox",
            "source_view": "capture_triage",
            "object_type": "raw_capture_memory",
            "priority_band": "batch_shape_not_execute",
            "count": len(raw_rows),
            "top_ids": _top_ids(raw_rows, limit=sample_limit),
            "next_event": "shape | link | retire | no-op",
            "why": "Raw captures are memory; the organizer seed should cluster and shape them, not execute from them.",
        },
        {
            "cluster_id": "possible_adapter_leaks",
            "source_view": "adapter_leak_audit",
            "object_type": "adapter_residual_signal",
            "priority_band": "capture_if_true_durable_work",
            "count": len(adapter_rows),
            "top_ids": [
                str(row.get("source") or row.get("row_id") or "") for row in adapter_rows[:sample_limit]
            ],
            "next_event": "quick-capture only after judgment",
            "why": "Adapter leak examples are possible residuals, not automatic backlog rows.",
        },
    ]
    return {
        "schema_version": "task_ledger_work_graph_priority_cluster_summary_v0",
        "rubric_id": WORK_GRAPH_PRIORITY_RUBRIC["rubric_id"],
        "ordering_rule": "Evaluate hard gates first, then choose the highest-leverage owner action; the correct unit may be a row, cluster, standard, skill, seed, route, paper module, or source patch.",
        "clusters": clusters,
        "cluster_order": list(WORK_GRAPH_PRIORITY_RUBRIC["cluster_order"]),
        "low_loop_contract": {
            "allowed_actions": [
                "read organizer-report",
                "cluster rows by existing Task Ledger views",
                "select one work-pressure object class",
                "patch the owning source, standard, skill, route, seed, or paper module when safe",
                "propose rank/shape/retire/block event commands",
                "write a receipt or seed update",
            ],
            "forbidden_actions": [
                "auto-promote",
                "auto-rerank",
                "auto-retire semantic duplicate groups",
                "execute implementation work from capture_inbox",
                "create a parallel todo board",
                "treat classification, sorting, or validation as success when a patchable owner action exists",
            ],
        },
    }


def _compact_terminal_capture_audit(
    audit_only: Mapping[str, Any],
    *,
    sample_limit: int,
) -> Dict[str, Any]:
    compact = dict(audit_only)
    sample_items = [
        row for row in compact.get("sample_items", [])
        if isinstance(row, Mapping)
    ]
    compact_samples: List[Dict[str, Any]] = []
    for row in sample_items[:sample_limit]:
        compact_samples.append(
            {
                "kind": row.get("kind"),
                "id": row.get("id"),
                "title": row.get("title"),
                "state": row.get("state"),
                "sign_off_id": row.get("sign_off_id"),
                "disposition": row.get("disposition"),
            }
        )
    if sample_items:
        compact["sample_items"] = compact_samples
        compact["sample_items_omitted_count"] = max(0, len(sample_items) - len(compact_samples))
        compact["sample_item_evidence_omitted"] = (
            "source_event_ids are omitted from compact organizer-report; use --detail full "
            "or state/task_ledger/views/merge_or_retire_candidates.json for event evidence."
        )
    return compact


def _command_template(command: str, subject_id: str, payload: Mapping[str, Any] | None = None) -> str:
    payload_text = "<json>"
    if payload:
        payload_text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if command == "quick-capture":
        return (
            "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture "
            "--title '<title>' --statement '<statement>' --source-ref '<transcript_ref>' "
            "--tag adapter_leak --rebuild"
        )
    return (
        f"./repo-python tools/meta/factory/task_ledger_apply.py {command} "
        f"--subject-id {subject_id} --payload-json '{payload_text}' --rebuild"
    )


def _actuation_recommendation(
    *,
    row_id: str,
    current_status: str,
    recommended_action: str,
    why: str,
    mutation_verb: str,
    required_fields: Sequence[str],
    blast_radius: str,
    requires_operator_review: bool,
    payload: Mapping[str, Any] | None = None,
    safe_command_template: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    subject_id = row_id
    if row_id.startswith("task_ledger:"):
        subject_id = row_id.split(":", 2)[1]
    boundary_text = " ".join(
        str(part or "")
        for part in (
            recommended_action,
            why,
            mutation_verb,
            blast_radius,
            safe_command_template or "",
            json.dumps(payload or {}, ensure_ascii=False, sort_keys=True),
            json.dumps(extra or {}, ensure_ascii=False, sort_keys=True),
        )
    )
    boundary_kind = _operator_authorization_boundary_kind(boundary_text)
    authorization_policy = _standing_operator_authorization_policy(
        boundary_kind=boundary_kind,
        requires_operator_review=requires_operator_review,
    )
    recommendation = {
        "row_id": row_id,
        "current_status": current_status,
        "recommended_action": recommended_action,
        "why": why,
        "safe_command_template": safe_command_template or _command_template(mutation_verb, subject_id, payload),
        "required_fields": list(required_fields),
        "mutation_verb": mutation_verb,
        "requires_operator_review": requires_operator_review,
        "blast_radius": blast_radius,
        "authorization_policy": authorization_policy,
        "operator_authorization_status": authorization_policy["operator_authorization_status"],
        "authorization_blocks_execution": authorization_policy["authorization_blocks_execution"],
        "public_release_authorization": authorization_policy["public_release_authorization"],
    }
    if extra:
        recommendation.update(dict(extra))
    return recommendation


def _propagation_action(row: Mapping[str, Any]) -> Dict[str, Any]:
    subject_id = str(row.get("id") or "<work_item_id>")
    return _actuation_recommendation(
        row_id=subject_id,
        current_status=str(row.get("state") or "unknown"),
        recommended_action="inspect_owner_surface_then_propagate_or_nothing_to_refine",
        why=str(
            row.get("why_candidate")
            or "closed row has a generalization signal without owner-surface actuation receipt"
        ),
        mutation_verb="propagate",
        required_fields=[
            "propagation.status",
            "propagation.targets",
            "propagation.lesson or propagation.nothing_to_refine",
            "propagation.owner_surface",
            "propagation.owner_actuation_receipt",
        ],
        requires_operator_review=False,
        blast_radius="owner_surface_patch_or_verification_plus_single_work_item_receipt",
        payload={
            "propagation": {
                "status": "recorded",
                "classification": "already_propagated_verified | nothing_to_refine | propagation_debt",
                "targets": [],
                "lesson": "<lesson or rationale>",
                "nothing_to_refine": False,
            }
        },
        extra={
            "command_role": "receipt_after_owner_surface_actuation",
            "preconditions": [
                "open the Task Ledger card and source event evidence",
                "inspect the named source, standard, skill, route, checker, projector, or code owner",
                "patch or verify that owner surface before recording propagation",
            ],
        },
    )


def _work_item_action(row: Mapping[str, Any], *, source: str) -> Dict[str, Any]:
    subject_id = str(row.get("id") or "<work_item_id>")
    state = str(row.get("state") or "unknown")
    missing = [str(item) for item in (row.get("missing_fields") or row.get("missing_contracts") or [])]
    recommended = str(row.get("recommended_action") or "")
    categories = {str(item) for item in (row.get("categories") or [])}
    if source == "merge_or_retire":
        item_ids = [
            str(item_id)
            for item_id in (row.get("item_ids") or [])
            if str(item_id or "").strip()
        ]
        if item_ids:
            group_kind = str(row.get("kind") or "duplicate_capture_group")
            item_ids_text = ",".join(item_ids)
            return _actuation_recommendation(
                row_id=f"{group_kind}:{item_ids_text}",
                current_status="group_review",
                recommended_action="review_duplicate_group_disposition",
                why="merge/retire row is a duplicate group; choose the kept row and disposition before mutating any single WorkItem",
                mutation_verb="operator_review",
                required_fields=["canonical_work_item_id", "disposition", "reason"],
                requires_operator_review=True,
                blast_radius="multi_work_item_group_review",
                safe_command_template=(
                    "./repo-python kernel.py --option-surface task_ledger --band card --ids "
                    f"{item_ids_text}"
                ),
                extra={
                    "group_kind": group_kind,
                    "item_ids": item_ids,
                    "candidate_commands": [
                        (
                            "./repo-python tools/meta/factory/task_ledger_apply.py retire "
                            "--subject-id <selected_duplicate_id> "
                            "--payload-json '{\"reason\":\"duplicate_or_superseded_by_<canonical_id>\"}' "
                            "--rebuild"
                        ),
                        (
                            "./repo-python tools/meta/factory/task_ledger_apply.py note "
                            "--subject-id <canonical_id> "
                            "--payload-json '{\"note\":\"duplicates reviewed; see merge_or_retire_candidates group item_ids\"}' "
                            "--rebuild"
                        ),
                    ],
                },
            )
        return _actuation_recommendation(
            row_id=subject_id,
            current_status=state,
            recommended_action="retire_or_leave_closed",
            why="merge/retire view is deterministic-only; closed/signoff captures should not be treated as active work",
            mutation_verb="retire",
            required_fields=["reason"],
            requires_operator_review=True,
            blast_radius="single_work_item_state_and_capture_inbox_membership",
            payload={"reason": "closed_or_superseded_capture_after_operator_review"},
        )
    if source == "execution_menu":
        return _actuation_recommendation(
            row_id=subject_id,
            current_status=state,
            recommended_action="claim_or_execute_committed_work",
            why="row is already promoted, ranked, claimed, or active; next mutation should claim, execute, block, or close it",
            mutation_verb="claim",
            required_fields=["owner or execution.work_ledger_session_id"],
            requires_operator_review=False,
            blast_radius="single_work_item_execution_claim",
            payload={"owner": "<owner>", "execution": {"work_ledger_session_id": "<session_id>"}},
        )
    if "missing_satisfaction_contract" in categories or "missing_integration_contract" in categories:
        return _actuation_recommendation(
            row_id=subject_id,
            current_status=state,
            recommended_action="shape_contracts",
            why="row lacks satisfaction or integration evidence required before promotion",
            mutation_verb="shape",
            required_fields=["satisfaction_contract", "integration_contract"],
            requires_operator_review=False,
            blast_radius="single_work_item_contract_fields",
            payload={"satisfaction_contract": {}, "integration_contract": {}},
        )
    if "missing_completion_contract" in categories or "completion_contract" in missing:
        return _actuation_recommendation(
            row_id=subject_id,
            current_status=state,
            recommended_action="shape_completion_contract",
            why="row is otherwise shaped but lacks a completion/closeout contract",
            mutation_verb="shape",
            required_fields=["completion"],
            requires_operator_review=False,
            blast_radius="single_work_item_completion_contract",
            payload={"completion": {"closure_condition": "<definition of done>", "signoff_required": True}},
        )
    if recommended == "promote_rank_or_execute" or "shaped_ready" in categories:
        return _actuation_recommendation(
            row_id=subject_id,
            current_status=state,
            recommended_action="promote_to_execution_menu",
            why="row has shaped-ready signal and no missing contract fields in this report sample",
            mutation_verb="promote",
            required_fields=["rank or rank_history justification"],
            requires_operator_review=True,
            blast_radius="execution_menu_priority_and_commitment_queue",
            payload={"rank": "<rank>", "rank_history": [{"justification": "<why now>"}]},
        )
    return _actuation_recommendation(
        row_id=subject_id,
        current_status=state,
        recommended_action="triage_or_note",
        why="row needs explicit assimilation disposition before promotion or retirement",
        mutation_verb="triage",
        required_fields=["triage_status", "recommended_action"],
        requires_operator_review=True,
        blast_radius="single_work_item_triage_metadata",
        payload={"triage_status": "<status>", "recommended_action": "<action>"},
    )


def _adapter_leak_action(row: Mapping[str, Any]) -> Dict[str, Any]:
    source = str(row.get("source") or "<transcript>")
    line = str(row.get("line") or "<line>")
    return _actuation_recommendation(
        row_id=f"{source}:{line}",
        current_status=str(row.get("disposition") or "unknown"),
        recommended_action="quick_capture_if_true_durable_work",
        why="adapter audit examples are possible leaks only; capture requires human/agent judgment that the excerpt is durable work",
        mutation_verb="quick-capture",
        required_fields=["title", "statement", "source_ref"],
        requires_operator_review=True,
        blast_radius="new_capture_inbox_row_only",
    )


def _propagation_signal(value: Any) -> bool:
    text = json.dumps(value or {}, ensure_ascii=False).lower()
    return any(
        token in text
        for token in (
            "lesson",
            "doctrine",
            "standard",
            "skill",
            "paper",
            "module",
            "prompt",
            "adapter",
            "projection",
            "route",
            "navigation",
            "local-to-general",
            "uppropagation",
        )
    )


def _propagation_needed_rows(
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    signoffs_by_work_item = {
        str(signoff.get("work_item_id") or ""): signoff
        for signoff in signoffs
        if isinstance(signoff, Mapping)
    }
    rows: List[Dict[str, Any]] = []
    for item in work_items:
        work_item_id = str(item.get("id") or "")
        state = _item_state(item)
        signoff = signoffs_by_work_item.get(work_item_id, {})
        propagation = item.get("propagation") if isinstance(item.get("propagation"), Mapping) else {}
        if propagation:
            continue
        if not _is_closed_or_signed_off(item):
            continue
        if signoff:
            if signoff.get("lessons_propagated") or signoff.get("propagation_targets"):
                continue
            signal_source: Any = signoff
        else:
            signal_source = item
        if not _propagation_signal(signal_source):
            continue
        rows.append(
            {
                "id": work_item_id,
                "title": item.get("title"),
                "state": state,
                "sign_off_id": item.get("sign_off_id"),
                "why_candidate": (
                    "closed_or_signed_off_with_generalization_signal_but_no_owner_actuation_receipt"
                ),
                "recommended_action": PROPAGATION_NEEDED_RECOMMENDED_ACTION,
                "source_event_ids": list(item.get("source_event_ids") or []),
            }
        )
    rows.sort(key=lambda row: str(row.get("id") or ""))
    return rows


def _build_propagation_needed_view(
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
    generated_at: str,
) -> Dict[str, Any]:
    rows = _propagation_needed_rows(work_items, signoffs)
    return {
        "kind": "task_ledger_view",
        "schema_version": "task_ledger_propagation_needed_v1",
        "view_id": "propagation_needed",
        "generated_at": generated_at,
        "candidate_count": len(rows),
        "count": len(rows),
        "recommended_action": PROPAGATION_NEEDED_RECOMMENDED_ACTION,
        "items": rows,
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": (
                "read-only projection; patch or verify the owner surface first, then append "
                "work_item.propagation_recorded as the receipt"
            ),
        },
    }


def _build_propagation_needed_report(
    work_items: Sequence[Mapping[str, Any]],
    signoffs: Sequence[Mapping[str, Any]],
    *,
    existing_projection_view: bool = False,
) -> Dict[str, Any]:
    rows = _propagation_needed_rows(work_items, signoffs)
    decision = (
        "durable_projection_view_available; use view for queue shape and organizer-report for command templates"
        if existing_projection_view
        else "add_projection_if_operator_wants_a_durable_queue; organizer-report can surface candidates read-only for now"
    )
    payload: Dict[str, Any] = {
        "existing_projection_view": existing_projection_view,
        "decision": decision,
        "candidate_count": len(rows),
        "state_counts": _count_by_key(rows, "state"),
        "items": rows[:10],
    }
    if existing_projection_view:
        payload["projection_view"] = str(VIEWS_REL / "propagation_needed.json")
    return {
        **payload,
    }


def _project_claude_transcript_dir(repo_root: Path) -> Path:
    token = "-" + re.sub(r"[^A-Za-z0-9]+", "-", str(repo_root).strip("/")).strip("-")
    return Path.home() / ".claude" / "projects" / token


def _latest_transcript_paths(repo_root: Path, *, limit: int = 8) -> List[Path]:
    roots: List[Path] = []
    project_root = _project_claude_transcript_dir(repo_root)
    if project_root.exists():
        roots.append(project_root)
    transport = _safe_read_json(repo_root / "tools/meta/bridge/claude_session_transport.json")
    active = transport.get("extras") if isinstance(transport.get("extras"), Mapping) else {}
    active_session = active.get("active_session") if isinstance(active.get("active_session"), Mapping) else {}
    transcript_path = str(active_session.get("transcript_path") or "").strip()
    paths: Dict[str, Path] = {}
    if transcript_path:
        path = Path(transcript_path).expanduser()
        if path.exists() and path.is_file():
            paths[str(path)] = path
    for root in roots:
        try:
            for path in root.rglob("*.jsonl"):
                if path.is_file():
                    paths[str(path)] = path
        except Exception:
            continue
    return sorted(paths.values(), key=lambda path: path.stat().st_mtime, reverse=True)[:limit]


def _compact_excerpt(value: str, *, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _strip_quoted_or_generated_sections(value: str) -> str:
    kept: List[str] = []
    in_fence = False
    for raw_line in value.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        if stripped.startswith(">"):
            continue
        if re.match(r"^\s*(?:\d+\s+)?(?:[A-Za-z0-9_.-]+/)?[A-Za-z0-9_.-]+\.(?:py|md|json|jsonl|tsx?|jsx?|sh):\d+:", line):
            continue
        kept.append(line)
    return "\n".join(kept).strip()


def _transcript_signal_entries(line: str) -> List[Dict[str, Any]]:
    try:
        payload = json.loads(line)
    except Exception:
        return [{"text": line, "origin": "raw_line", "classification_basis": "unparsed_raw_line"}]
    if not isinstance(payload, Mapping):
        return [{"text": line, "origin": "raw_line", "classification_basis": "non_mapping_json_line"}]
    if payload.get("type") == "queue-operation":
        return [
            {
                "text": str(payload.get("content") or ""),
                "origin": "queue_operation",
                "noise_reason": "prompt_template_noise",
                "classification_basis": "queue_operation_prompt_payload_not_assistant_authored",
            }
        ]
    attachment = payload.get("attachment")
    if isinstance(attachment, Mapping):
        # Tool/skill availability deltas are not agent-authored durable-work claims.
        if str(attachment.get("type") or "") in {
            "deferred_tools_delta",
            "mcp_instructions_delta",
            "skill_listing",
        }:
            return [
                {
                    "text": "",
                    "origin": "attachment",
                    "noise_reason": "provider_tool_event_without_payload",
                    "classification_basis": "tool_or_skill_availability_delta",
                }
            ]
    message = payload.get("message")
    if not isinstance(message, Mapping):
        return []
    role = str(message.get("role") or payload.get("type") or "")
    if role == "user":
        return [
            {
                "text": json.dumps(message.get("content") or "", ensure_ascii=False),
                "origin": "user_message",
                "noise_reason": "quoted_context",
                "classification_basis": "user_pasted_context_ignored",
            }
        ]
    entries: List[Dict[str, Any]] = []
    content = message.get("content")
    if isinstance(content, str):
        entries.append(
            {
                "text": _strip_quoted_or_generated_sections(content),
                "origin": f"{role}_text",
                "classification_basis": "assistant_authored_text" if role == "assistant" else f"{role}_text",
            }
        )
    elif isinstance(content, list):
        for block in content:
            if isinstance(block, str):
                entries.append(
                    {
                        "text": _strip_quoted_or_generated_sections(block),
                        "origin": f"{role}_text",
                        "classification_basis": "assistant_authored_text",
                    }
                )
            elif isinstance(block, Mapping):
                block_type = str(block.get("type") or "")
                if block_type == "text":
                    entries.append(
                        {
                            "text": _strip_quoted_or_generated_sections(str(block.get("text") or "")),
                            "origin": f"{role}_text",
                            "classification_basis": "assistant_authored_text",
                        }
                    )
                elif block_type == "tool_use":
                    name = str(block.get("name") or "")
                    tool_input = block.get("input") if isinstance(block.get("input"), Mapping) else {}
                    if name in NATIVE_TODO_TOOL_NAMES:
                        entries.append(
                            {
                                "text": f"{name} {json.dumps(tool_input, ensure_ascii=False)}",
                                "origin": "assistant_tool_use",
                                "tool_name": name,
                                "classification_basis": "native_todo_tool_use_with_payload"
                                if tool_input
                                else "native_todo_tool_use_without_payload",
                                "noise_reason": None if tool_input else "provider_native_tool_event_without_payload",
                            }
                        )
                    elif name:
                        entries.append(
                            {
                                "text": name,
                                "origin": "assistant_tool_use",
                                "tool_name": name,
                                "classification_basis": "non_native_tool_use_name_only",
                                "noise_reason": "tool_output_noise",
                            }
                        )
                elif block_type == "tool_result":
                    result = str(block.get("content") or "")
                    entries.append(
                        {
                            "text": result[:2000],
                            "origin": "tool_result",
                            "noise_reason": "tool_output_noise",
                            "classification_basis": "tool_result_ignored_unless_native_todo_artifact",
                        }
                    )
    return entries


def _transcript_signal_text(line: str) -> str:
    return "\n".join(str(entry.get("text") or "") for entry in _transcript_signal_entries(line)).strip()


def _adapter_signal_noise_reason(value: str) -> str | None:
    text = re.sub(r"\s+", " ", value).strip()
    lowered = text.lower()
    if not text:
        return "empty"
    if text.startswith("<persisted-output>") or "full output saved to:" in lowered:
        return "tool_output_noise"
    if text.startswith("{") and '"kind": "navigation_context_pack"' in text[:500]:
        return "tool_output_noise"
    if re.fullmatch(r"mcp__[A-Za-z0-9_]+__spawn_task", text):
        return "provider_native_tool_event_without_payload"
    if re.search(r"\b(?:AGENTS|CLAUDE|CODEX)\.md:\d+:", text):
        return "tool_output_noise"
    if re.search(r"\b(?:state|codex|tools|system|obsidian|\.claude)/[^:\s]+:\d+:", text):
        return "tool_output_noise"
    if text.startswith("commit ") and " author:" in lowered:
        return "tool_output_noise"
    if "deliverable_type" in lowered[:600] and "authority_boundary" in lowered[:1000]:
        return "prompt_template_noise"
    if lowered.startswith("next move:") and "```text" in lowered:
        return "prompt_template_noise"
    if re.search(r"\b(?:top-level keys|schema_version|view_id)\b", lowered) and "followup" in lowered:
        return "tool_output_noise"
    return None


def _signal_families(signals: Sequence[str]) -> List[str]:
    return sorted({ADAPTER_SIGNAL_FAMILIES.get(signal, "unknown_signal") for signal in signals})


def _native_todo_payload_is_routine(value: str) -> bool:
    lowered = value.lower()
    if "todowrite" not in lowered:
        return False
    if any(token in lowered for token in ("future work", "follow-up", "followup", "deferred", "later", "cross-session")):
        return False
    return any(status in lowered for status in ('"status": "in_progress"', '"status": "completed"', '"status": "pending"'))


def _adapter_classification_basis(
    *,
    haystack: str,
    signals: Sequence[str],
    entry_basis: str,
    origin: str,
) -> str:
    families = set(_signal_families(signals))
    if origin == "assistant_tool_use" and "native_todo_signal" in families:
        return "native_todo_signal_survived_payload_filter"
    if "scheduling_signal" in families:
        return "assistant_authored_schedule_offer_survived_filters"
    if "residual_language_signal" in families:
        return "assistant_authored_residual_language_survived_filters"
    if "weak_language_signal" in families:
        return "assistant_authored_weak_language_survived_filters"
    return entry_basis or "signal_survived_filters"


def _adapter_captured_source_refs(repo_root: Path) -> set[str]:
    refs: set[str] = set()
    try:
        events = read_authority_events(repo_root)
    except Exception:
        return refs
    for event in events:
        if not isinstance(event, Mapping):
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        source = event.get("source") if isinstance(event.get("source"), Mapping) else {}
        event_refs = event.get("refs") if isinstance(event.get("refs"), Mapping) else {}
        provenance = payload.get("provenance") if isinstance(payload.get("provenance"), Mapping) else {}
        for container in (source, event_refs, provenance):
            for key in ("refs", "source_refs"):
                values = container.get(key) if isinstance(container, Mapping) else None
                if isinstance(values, list):
                    refs.update(str(value) for value in values if value)
        if str(event.get("event_type") or "") == "work_item.captured" and "adapter_leak" in {
            str(tag) for tag in (payload.get("tags") or [])
        }:
            refs.update(str(value) for value in (event_refs.get("source_refs") or []) if value)
    return refs


def _scan_adapter_leaks(
    repo_root: Path,
    *,
    file_limit: int = 8,
    example_limit: int = ORGANIZER_REPORT_FULL_ADAPTER_EXAMPLES,
    calibration_sample_limit: int = ORGANIZER_REPORT_FULL_CALIBRATION_SAMPLES,
) -> Dict[str, Any]:
    paths = _latest_transcript_paths(repo_root, limit=file_limit)
    captured_source_refs = _adapter_captured_source_refs(repo_root)
    examples: List[Dict[str, Any]] = []
    signal_count = 0
    captured_count = 0
    possible_leak_count = 0
    unknown_count = 0
    skipped_noise_count = 0
    by_signal: Dict[str, int] = defaultdict(int)
    by_signal_family: Dict[str, int] = defaultdict(int)
    by_noise_reason: Dict[str, int] = defaultdict(int)
    by_classification_basis: Dict[str, int] = defaultdict(int)
    calibration_sample: List[Dict[str, Any]] = []
    scanned_line_count = 0
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            unknown_count += 1
            continue
        for line_number, line in enumerate(lines[-2500:], start=max(1, len(lines) - 2499)):
            scanned_line_count += 1
            for entry in _transcript_signal_entries(line):
                haystack = str(entry.get("text") or "")
                entry_basis = str(entry.get("classification_basis") or "")
                origin = str(entry.get("origin") or "")
                lowered = haystack.lower()
                signals = [
                    signal
                    for signal in ADAPTER_LEAK_SIGNALS
                    if (signal.lower() in lowered if signal != "TodoWrite" else signal in haystack)
                ]
                if signals == ["deferred"] and "deferred tool" in lowered:
                    signals = []
                if not signals:
                    explicit_noise = entry.get("noise_reason")
                    if explicit_noise and haystack:
                        skipped_noise_count += 1
                        by_noise_reason[str(explicit_noise)] += 1
                    continue
                noise_reason = str(entry.get("noise_reason") or "") or _adapter_signal_noise_reason(haystack)
                if _native_todo_payload_is_routine(haystack):
                    noise_reason = "not_durable_work"
                if noise_reason:
                    skipped_noise_count += 1
                    by_noise_reason[noise_reason] += 1
                    if len(calibration_sample) < calibration_sample_limit:
                        calibration_sample.append(
                            {
                                "source": str(path),
                                "line": line_number,
                                "signals": signals,
                                "signal_families": _signal_families(signals),
                                "classification": noise_reason,
                                "classification_basis": entry_basis or noise_reason,
                                "excerpt": _compact_excerpt(haystack),
                            }
                        )
                    continue
                signal_count += 1
                families = _signal_families(signals)
                for signal in signals:
                    by_signal[signal] += 1
                for family in families:
                    by_signal_family[family] += 1
                classification_basis = _adapter_classification_basis(
                    haystack=haystack,
                    signals=signals,
                    entry_basis=entry_basis,
                    origin=origin,
                )
                by_classification_basis[classification_basis] += 1
                has_capture_ref = bool(CAPTURE_PROVENANCE_RE.search(haystack))
                transcript_ref = f"{path}:{line_number}"
                has_captured_source_ref = transcript_ref in captured_source_refs
                has_disposition_ref = any(
                    token in lowered
                    for token in (
                        "nothing_to_refine",
                        "blocked workitem",
                        "blocked work item",
                        "captured below",
                        "captured as workitems",
                        "captured as workitem",
                        "now capturing",
                        "retired",
                        "work_item.retired",
                        "work_item.propagation_recorded",
                    )
                )
                if has_capture_ref or has_disposition_ref or has_captured_source_ref:
                    captured_count += 1
                    disposition = "captured_or_dispositioned"
                    sample_classification = (
                        "already_captured_or_dispositioned"
                        if not has_captured_source_ref
                        else "already_captured_or_dispositioned_by_source_ref"
                    )
                else:
                    possible_leak_count += 1
                    disposition = "possible_leak"
                    sample_classification = "uncertain"
                row = {
                    "source": str(path),
                    "line": line_number,
                    "signals": signals,
                    "signal_families": families,
                    "disposition": disposition,
                    "classification_basis": classification_basis,
                    "excerpt": _compact_excerpt(haystack),
                    "recommended_capture_command": "./repo-python tools/meta/factory/task_ledger_apply.py quick-capture --title '<title>' --statement '<statement>' --source-ref '<transcript_ref>' --tag adapter_leak --created-by <agent_id>"
                    if disposition == "possible_leak"
                    else None,
                }
                if len(examples) < example_limit:
                    examples.append(row)
                if len(calibration_sample) < calibration_sample_limit:
                    calibration_sample.append(
                        {
                            **{key: row[key] for key in ("source", "line", "signals", "signal_families", "classification_basis", "excerpt")},
                            "classification": sample_classification,
                        }
                    )
    denominator = captured_count + possible_leak_count
    possible_leak_rate = (possible_leak_count / denominator) if denominator else 0.0
    settings = _safe_read_json(repo_root / ".claude/settings.local.json")
    hooks = settings.get("hooks") if isinstance(settings.get("hooks"), Mapping) else {}
    pre_tool_hooks = hooks.get("PreToolUse") if isinstance(hooks.get("PreToolUse"), list) else []
    post_tool_hooks = hooks.get("PostToolUse") if isinstance(hooks.get("PostToolUse"), list) else []
    runtime_hook_text = ""
    runtime_hook_path = repo_root / ".claude/hooks/runtime_hook.py"
    try:
        runtime_hook_text = runtime_hook_path.read_text(encoding="utf-8")
    except Exception:
        runtime_hook_text = ""
    return {
        "scan_scope": {
            "transcript_files_considered": [str(path) for path in paths],
            "transcript_file_count": len(paths),
            "scanned_recent_line_count": scanned_line_count,
            "per_file_recent_line_limit": 2500,
        },
        "counts": {
            "signal_count": signal_count,
            "captured_count": captured_count,
            "possible_leak_count": possible_leak_count,
            "unknown_count": unknown_count,
            "skipped_noise_count": skipped_noise_count,
            "possible_leak_rate": round(possible_leak_rate, 4),
            "by_signal": dict(sorted(by_signal.items())),
            "by_signal_family": dict(sorted(by_signal_family.items())),
            "by_noise_reason": dict(sorted(by_noise_reason.items())),
            "by_classification_basis": dict(sorted(by_classification_basis.items())),
        },
        "interpretation": {
            "metric_status": "calibrated_possible_leak_detector_not_true_leak_rate",
            "true_leak_language_allowed": False,
            "noise_policy": "user-pasted context, queue prompts, tool results, source excerpts, commits, routine in-turn TodoWrite payloads, and handoff prompt templates are excluded before counting possible leaks",
            "estimated_precision": {
                "status": "sample_review_required",
                "basis": "precision is estimated from the calibration sample categories, not treated as a true leak rate",
                "possible_leak_count": possible_leak_count,
                "skipped_noise_count": skipped_noise_count,
            },
            "recommended_next_enforcement": "not_ready_for_hooks_until_uncertain_samples_are_reviewed"
            if possible_leak_count
            else "no_hook_enforcement_needed_from_current_bounded_sample",
        },
        "local_hook_feasibility": {
            "settings_path": ".claude/settings.local.json",
            "pre_tool_hook_groups": len(pre_tool_hooks),
            "post_tool_hook_groups": len(post_tool_hooks),
            "project_hook_omits_matcher_so_tool_events_match_all": any(
                isinstance(group, Mapping) and not group.get("matcher") for group in pre_tool_hooks + post_tool_hooks
            ),
            "runtime_hook_path": ".claude/hooks/runtime_hook.py",
            "runtime_hook_mentions_todowrite": "TodoWrite" in runtime_hook_text,
            "current_enforcement_state": "hook_auditable_but_not_todowrite_specific"
            if pre_tool_hooks or post_tool_hooks
            else "prose_only",
        },
        "calibration_sample": calibration_sample,
        "examples": examples,
    }


def build_organizer_report(
    repo_root: Path,
    *,
    transcript_file_limit: int = 8,
    detail: str = "compact",
) -> Dict[str, Any]:
    detail_profile = str(detail or "compact").strip().lower()
    if detail_profile not in {"compact", "full"}:
        raise ValueError("organizer report detail must be 'compact' or 'full'")
    sample_limit = (
        ORGANIZER_REPORT_FULL_SAMPLE_LIMIT
        if detail_profile == "full"
        else ORGANIZER_REPORT_COMPACT_SAMPLE_LIMIT
    )
    adapter_example_limit = (
        ORGANIZER_REPORT_FULL_ADAPTER_EXAMPLES
        if detail_profile == "full"
        else ORGANIZER_REPORT_COMPACT_ADAPTER_EXAMPLES
    )
    adapter_calibration_limit = (
        ORGANIZER_REPORT_FULL_CALIBRATION_SAMPLES
        if detail_profile == "full"
        else ORGANIZER_REPORT_COMPACT_CALIBRATION_SAMPLES
    )
    projection_read_model = (
        _load_current_projection_read_model(repo_root)
        if detail_profile == "compact"
        else None
    )
    if projection_read_model:
        projection = projection_read_model["projection"]
        authority = {
            "schema": "task_ledger_projection_read_model_health_v0",
            "status": "clean",
            "mode": "projection_read_model",
            "ok": True,
            "full_authority_scan": False,
            "projection_stale_possible": projection_read_model["read_model"].get(
                "projection_stale_possible"
            ),
            "full_authority_check_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py authority-health"
            ),
        }
        events: List[Dict[str, Any]] = []
    else:
        authority = authority_health(repo_root)
        events, projection = _load_validate_events_and_projection(repo_root)
    views = projection["views"]
    ledger = projection["ledger"]
    work_items = list(ledger.get("work_items") or [])
    work_items_by_id = {
        str(item.get("id") or ""): item
        for item in work_items
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }
    signoffs = list(projection.get("sign_offs", {}).get("sign_offs") or [])
    capture_triage = views.get("capture_triage", {})
    triage_rows = [
        row for row in capture_triage.get("items", [])
        if isinstance(row, Mapping)
    ]
    execution_menu = views.get("execution_menu", {})
    promotion_candidates = views.get("promotion_candidates", {})
    merge_or_retire = views.get("merge_or_retire_candidates", {})
    missing_contracts = views.get("missing_contracts_ranked", {})
    execution_rows = [row for row in execution_menu.get("items", []) if isinstance(row, Mapping)]
    promotion_rows = [row for row in promotion_candidates.get("items", []) if isinstance(row, Mapping)]
    merge_rows = [row for row in merge_or_retire.get("items", []) if isinstance(row, Mapping)]
    missing_rows = [row for row in missing_contracts.get("items", []) if isinstance(row, Mapping)]
    merge_audit = (
        merge_or_retire.get("audit_only")
        if isinstance(merge_or_retire.get("audit_only"), Mapping)
        else {}
    )
    propagation_report = _build_propagation_needed_report(
        work_items,
        signoffs,
        existing_projection_view="propagation_needed" in views,
    )
    family_action_receipts = _load_family_action_receipts(repo_root)
    adapter_audit = _scan_adapter_leaks(
        repo_root,
        file_limit=transcript_file_limit,
        example_limit=adapter_example_limit,
        calibration_sample_limit=adapter_calibration_limit,
    )
    samples_by_status: Dict[str, Dict[str, Any]] = {}
    for row in triage_rows:
        status = str(row.get("triage_status") or "unknown")
        if status not in samples_by_status:
            samples_by_status[status] = _sample_rows([row], limit=1)[0]
    merge_counts_by_kind = _count_by_key(merge_rows, "kind")
    semantic_duplicate_count = merge_counts_by_kind.get("semantic_duplicate_capture_group", 0)
    compaction_governance = _compaction_governance_packet()
    capture_total_count = views.get("capture_inbox", {}).get("count", 0)
    capture_status_counts = capture_triage.get("counts_by_status") or {}
    capture_category_counts = capture_triage.get("category_counts") or {}
    closed_capture_count = int(capture_status_counts.get("closed_or_signed_off", 0) or 0)
    raw_capture_inbox_count = int(capture_category_counts.get("raw_capture_inbox", 0) or 0)
    open_capture_count = max(0, int(capture_total_count or 0) - closed_capture_count)
    priority_cluster_summary = _build_priority_cluster_summary(
        views=views,
        work_items_by_id=work_items_by_id,
        family_action_receipts=family_action_receipts,
        propagation_report=propagation_report,
        adapter_audit=adapter_audit,
        sample_limit=sample_limit,
    )
    report = {
        "ok": authority.get("status") == "clean",
        "kind": "task_ledger_organizer_report",
        "schema_version": "task_ledger_organizer_report_v1",
        "output_profile": {
            "profile": detail_profile,
            "default_profile": "compact",
            "sample_limit": sample_limit,
            "adapter_example_limit": adapter_example_limit,
            "adapter_calibration_sample_limit": adapter_calibration_limit,
            "full_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py "
                "organizer-report --detail full"
            ),
            "compaction_reason": (
                "organizer-report is a first-read control surface; compact mode keeps counts, "
                "rules, and command templates while bounding sample fanout."
            ),
        },
        "generated_at": utc_now(),
        "authority_health": authority,
        "projection_read_model": (
            projection_read_model["read_model"]
            if projection_read_model
            else {
                "schema": "task_ledger_projection_read_model_v0",
                "mode": "full_authority_rebuild",
                "full_authority_scan": True,
                "projection_stale_possible": False,
            }
        ),
        "authority": {
            "source": str(EVENTS_REL),
            "mutation_rule": "read-only report; append Task Ledger events for changes",
            "projection_paths": {
                name: str(VIEWS_REL / f"{name}.json")
                for name in sorted(views)
            },
        },
        "operator_authorization_policy": _standing_operator_authorization_policy(),
        "priority_rubric": WORKITEM_PRIORITY_RUBRIC,
        "priority_cluster_summary": priority_cluster_summary,
        "unconverted_substrate_debt": _build_unconverted_substrate_debt_report(
            priority_cluster_summary=priority_cluster_summary,
            propagation_report=propagation_report,
            sample_limit=sample_limit,
        ),
        "health": {
            "work_item_count": len(work_items),
            "capture_count": capture_total_count,
            "total_capture_count": capture_total_count,
            "open_capture_count": open_capture_count,
            "closed_capture_count": closed_capture_count,
            "raw_capture_inbox_count": raw_capture_inbox_count,
            "active_capture_inbox_count": raw_capture_inbox_count,
            "capture_pressure_counts": {
                "total": capture_total_count,
                "open": open_capture_count,
                "closed_or_signed_off": closed_capture_count,
                "raw_capture_inbox": raw_capture_inbox_count,
                "needs_contract_shaping": int(capture_status_counts.get("needs_contract_shaping", 0) or 0),
                "needs_signoff": int(capture_status_counts.get("needs_signoff", 0) or 0),
                "shaped_ready": int(capture_status_counts.get("shaped_ready", 0) or 0),
                "shaped_needs_completion_contract": int(
                    capture_status_counts.get("shaped_needs_completion_contract", 0) or 0
                ),
            },
            "view_counts": {
                name: view.get("count")
                for name, view in sorted(views.items())
            },
            "capture_triage_status_counts": capture_status_counts,
            "capture_triage_category_counts": capture_category_counts,
            "capture_triage_linkage_counts": capture_triage.get("linkage_counts") or {},
            "active_wip_count": views.get("active_wip", {}).get("count", 0),
            "execution_menu_count": execution_menu.get("count", 0),
            "promotion_candidates_count": promotion_candidates.get("count", 0),
            "ready_by_rank_count": views.get("ready_by_rank", {}).get("count", 0),
            "stale_capture_count": capture_triage.get("stale_capture_count", 0),
            "merge_or_retire_count": merge_or_retire.get("count", 0),
            "merge_or_retire_audit_only_count": int(
                merge_audit.get("already_closed_capture_count", 0) or 0
            ),
            "needs_signoff_count": views.get("needs_signoff", {}).get("count", 0),
            "missing_contract_count": missing_contracts.get("count", 0),
        },
        "organizer_classifier": {
            "capture_triage_rules": [
                "closed state or sign_off_id -> closed_or_signed_off / no_action_closed",
                "state blocked -> blocked / inspect_blocker",
                "projection_completeness.needs_signoff -> needs_signoff / record_signoff_or_residual",
                "missing satisfaction/integration/exact-surface fields -> needs_contract_shaping / append_shape_or_link_contracts",
                "has satisfaction/integration but lacks completion contract -> shaped_needs_completion_contract / shape_completion_or_promote",
                "otherwise -> shaped_ready / promote_rank_or_execute",
            ],
            "category_rules": [
                "single captured event that is not closed or blocked -> raw_capture_inbox",
                "shaped_ready or shaped_needs_completion_contract -> shaped_ready",
                "missing contract fields map to missing_* categories",
                "closed_or_signed_off -> already_solved_candidate",
                "title/statement/type contains residual/follow-up -> residual_followup",
                "candidate/work item types map provider_job and bridge_action to assignable categories",
                "prompt/work ledger refs add prompt_trace_linked and work_ledger_linked",
                "promotion-candidate membership adds promotion_candidate; execution-menu membership is reserved for explicit commitment rows",
            ],
            "sample_explanations_by_status": samples_by_status,
        },
        "merge_or_retire_diagnostic": {
            "rules": [
                "closed captures and signoff captures are audit-only terminal rows, not merge/retire candidates",
                "open duplicate groups use exact normalized title + statement + candidate_work_item_type",
                "semantic duplicate groups use conservative token-overlap evidence and require operator review before merge/retire disposition",
                "semantic duplicate groups suppress explicit hard depends_on pairs because dependency-linked rows can share release language without being duplicates",
                "merge and supersede are dispositions represented through supported retire, note, shape, capture, or propagation events unless a future apply-lane event is added",
            ],
            "compaction_governance": compaction_governance,
            "audit_only": (
                dict(merge_audit)
                if detail_profile == "full"
                else _compact_terminal_capture_audit(merge_audit, sample_limit=sample_limit)
            ),
            "counts_by_kind": merge_counts_by_kind,
            "semantic_conflict_detector": {
                "class": "duplicate_generalization_candidate",
                "owner_surface": str(VIEWS_REL / "merge_or_retire_candidates.json"),
                "repair_lane": "append supported retire/note/propagate disposition event; preserve all source histories",
                "count": semantic_duplicate_count,
                "status": "detected" if semantic_duplicate_count else "clear",
            },
            "top_items": _sample_rows(
                merge_rows,
                limit=sample_limit,
            ),
        },
        "top_execution_candidates": _sample_rows(
            execution_rows,
            limit=sample_limit,
        ),
        "top_promotion_candidates": _sample_rows(
            promotion_rows,
            limit=sample_limit,
        ),
        "oldest_raw_captures": _sample_rows(
            [
                row for row in triage_rows
                if "raw_capture_inbox" in (row.get("categories") or [])
            ],
            limit=sample_limit,
        ),
        "top_missing_contract_rows": _sample_rows(
            missing_rows,
            limit=sample_limit,
        ),
        "propagation_needed": propagation_report,
        "adapter_leak_audit": adapter_audit,
        "actuation_recommendations": {
            "contract": {
                "mode": "read_only_command_templates",
                "auto_mutation_allowed": False,
                "review_rule": (
                    "operator review marks attention or priority judgment; standing private/internal "
                    "authorization means safe scoped local action is not blocked solely for permission, "
                    "while public release, external disclosure, destructive, irreversible, or secret "
                    "boundaries still require task-specific authority"
                ),
                "operator_authorization_policy": _standing_operator_authorization_policy(
                    requires_operator_review=True
                ),
            },
            "propagation_needed": [
                _propagation_action(row)
                for row in propagation_report.get("items", [])
                if isinstance(row, Mapping)
            ][:sample_limit],
            "execution_menu": [
                _work_item_action(row, source="execution_menu")
                for row in execution_rows
            ][:sample_limit],
            "promotion_candidates": [
                _work_item_action(row, source="promotion_candidates")
                for row in promotion_rows
            ][:sample_limit],
            "missing_contracts": [
                _work_item_action(row, source="missing_contracts")
                for row in missing_rows
            ][:sample_limit],
            "merge_or_retire": [
                _work_item_action(row, source="merge_or_retire")
                for row in merge_rows
            ][:sample_limit],
            "possible_adapter_leaks": [
                _adapter_leak_action(row)
                for row in adapter_audit.get("examples", [])
                if isinstance(row, Mapping) and row.get("disposition") == "possible_leak"
            ][:sample_limit],
        },
        "next_actions": [
            "Use unconverted_substrate_debt to choose between propagation disposition and family-action owner-surface repair.",
            "If adapter leak examples are valid, quick-capture the durable follow-up or add a TodoWrite-specific audit branch to .claude/hooks/runtime_hook.py.",
            "Keep capture cheap; mutate only by appending Task Ledger events.",
        ],
    }
    return report


def _rebuild_projections_unlocked(
    repo_root: Path,
    *,
    check: bool = False,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    _emit_progress(progress_callback, "load_validate_start", check=bool(check))
    events = load_and_validate_events(repo_root)
    _emit_progress(
        progress_callback,
        "load_validate_done",
        check=bool(check),
        event_count=len(events),
    )
    generated_at: str | None = None
    if check:
        current_ledger = _safe_read_json(repo_root / LEDGER_REL)
        generated_at = str(current_ledger.get("generated_at") or "").strip() or None
        current_projection_event_count = _optional_int(current_ledger.get("event_count"))
    else:
        current_projection_event_count = None
    _emit_progress(
        progress_callback,
        "build_projection_start",
        check=bool(check),
        event_count=len(events),
    )
    projection = build_projection(
        events,
        generated_at=generated_at,
        mission_blackboard=_safe_read_json(repo_root / MISSION_BLACKBOARD_REL),
        repo_root=repo_root,
    )
    _validate_projection_state(projection)
    targets = {
        LEDGER_REL: projection["ledger"],
        SIGNOFFS_REL: projection["sign_offs"],
    }
    for name, payload in projection["views"].items():
        targets[VIEWS_REL / f"{name}.json"] = payload
    _emit_progress(
        progress_callback,
        "build_projection_done",
        check=bool(check),
        event_count=len(events),
        projection_path_count=len(targets),
        work_item_count=len(projection["ledger"].get("work_items") or []),
        signoff_count=len(projection["sign_offs"].get("sign_offs") or []),
    )
    if check:
        _emit_progress(
            progress_callback,
            "projection_check_start",
            projection_path_count=len(targets),
        )
        mismatches = []
        for rel_path, payload in targets.items():
            projection_path = repo_root / rel_path
            current = _safe_read_json(projection_path)
            if not projection_path.exists() or current != payload:
                mismatches.append(str(rel_path))
        _emit_progress(
            progress_callback,
            "projection_check_done",
            ok=not mismatches,
            mismatch_count=len(mismatches),
        )
        return _projection_check_payload(
            mismatches,
            projection_event_count=current_projection_event_count,
            authority_event_count=len(events),
        )
    headroom = task_ledger_disk_write_headroom(
        repo_root,
        operation="task_ledger_projection_rebuild",
        rel_paths=[*list(targets), PROJECTION_MANIFEST_REL],
    )
    if not bool(headroom.get("ok")):
        _emit_disk_headroom_blocked(progress_callback, headroom)
        return _disk_headroom_block_result(headroom)
    _emit_progress(
        progress_callback,
        "projection_write_start",
        projection_path_count=len(targets),
    )
    for rel_path, payload in targets.items():
        atomic_write_json(repo_root / rel_path, payload, compact=True)
    manifest = _write_projection_manifest(
        repo_root,
        targets,
        authority_event_count=len(events),
        authority_tail_hash=_tail_hash(events),
    )
    _emit_progress(
        progress_callback,
        "projection_write_done",
        projection_path_count=len(targets),
    )
    return {
        "ok": True,
        "checked": False,
        "event_count": len(events),
        "projection_paths": [str(path) for path in targets],
        "counts": {
            "work_items": len(projection["ledger"].get("work_items") or []),
            "tasks": len(projection["ledger"].get("tasks") or []),
            "captures": projection["views"]["capture_inbox"]["count"],
            "sign_offs": len(projection["sign_offs"].get("sign_offs") or []),
        },
        "projection_manifest": {
            "path": str(PROJECTION_MANIFEST_REL),
            "target_count": manifest.get("target_count"),
        },
    }


def rebuild_projections(
    repo_root: Path,
    *,
    check: bool = False,
    progress_callback: TaskLedgerProgressCallback | None = None,
) -> Dict[str, Any]:
    _emit_progress(
        progress_callback,
        "lock_wait_start",
        operation="rebuild_projections",
        check=bool(check),
    )
    with file_lock(repo_root / LOCK_REL):
        _emit_progress(
            progress_callback,
            "lock_acquired",
            operation="rebuild_projections",
            check=bool(check),
        )
        _emit_progress(
            progress_callback,
            "rebuild_start",
            operation="rebuild_projections",
            check=bool(check),
        )
        result = _rebuild_projections_with_health_unlocked(
            repo_root,
            check=check,
            progress_callback=progress_callback,
        )
        _emit_progress(
            progress_callback,
            "rebuild_done",
            operation="rebuild_projections",
            check=bool(check),
            ok=result.get("ok"),
            status=result.get("status"),
            event_count=result.get("event_count"),
            projection_path_count=len(result.get("projection_paths") or []),
        )
        _emit_progress(
            progress_callback,
            "done",
            operation="rebuild_projections",
            check=bool(check),
            ok=result.get("ok"),
            status=result.get("status"),
        )
        return result


def _load_validate_event_rows(repo_root: Path) -> List[Dict[str, Any]]:
    events = read_authority_events(repo_root)
    seen: set[str] = set()
    previous: str | None = None
    normalized_rows: List[Dict[str, Any]] = []
    for row in events:
        normalized = validate_event(
            repo_root,
            row,
            allow_historical_local_absence=True,
        )
        event_id = str(normalized.get("event_id") or "")
        if event_id in seen:
            raise TaskLedgerError(f"duplicate event_id {event_id}")
        seen.add(event_id)
        if normalized.get("previous_event_hash") != previous:
            raise TaskLedgerError(
                f"event {event_id} previous_event_hash {normalized.get('previous_event_hash')!r} "
                f"does not match {previous!r}"
            )
        expected_hash = compute_event_hash(normalized)
        if normalized.get("event_hash") != expected_hash:
            raise TaskLedgerError(f"event {event_id} has invalid event_hash")
        previous = str(normalized.get("event_hash") or "")
        normalized_rows.append(normalized)
    return normalized_rows


def _load_validate_events_and_projection(
    repo_root: Path,
) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
    normalized_rows = _load_validate_event_rows(repo_root)
    projection = build_projection(normalized_rows)
    _validate_projection_state(projection)
    return normalized_rows, projection


def _load_current_projection_read_model(repo_root: Path) -> Dict[str, Any] | None:
    ledger_path = repo_root / LEDGER_REL
    signoffs_path = repo_root / SIGNOFFS_REL
    views_root = repo_root / VIEWS_REL
    if not ledger_path.exists() or not signoffs_path.exists() or not views_root.exists():
        return None
    try:
        ledger = _safe_read_json(ledger_path)
        sign_offs = _safe_read_json(signoffs_path)
        views = {
            path.stem: _safe_read_json(path)
            for path in sorted(views_root.glob("*.json"))
            if path.is_file()
        }
    except Exception:
        return None
    try:
        event_mtime_ns = _authority_mtime_ns(repo_root)
        projection_mtime_ns = max(
            [ledger_path.stat().st_mtime_ns, signoffs_path.stat().st_mtime_ns]
            + [path.stat().st_mtime_ns for path in views_root.glob("*.json") if path.is_file()]
        )
    except OSError:
        event_mtime_ns = 0
        projection_mtime_ns = 0
    stale_possible = bool(event_mtime_ns and projection_mtime_ns and event_mtime_ns > projection_mtime_ns)
    return {
        "projection": {
            "ledger": ledger,
            "sign_offs": sign_offs,
            "views": views,
        },
        "read_model": {
            "schema": "task_ledger_projection_read_model_v0",
            "mode": "disk_projection_read_model",
            "full_authority_scan": False,
            "projection_stale_possible": stale_possible,
            "event_log_mtime_ns": int(event_mtime_ns),
            "projection_max_mtime_ns": int(projection_mtime_ns),
            "ledger_path": str(LEDGER_REL),
            "signoffs_path": str(SIGNOFFS_REL),
            "view_count": len(views),
            "fallback_full_authority_condition": "missing_or_unreadable_projection_files",
        },
    }


def load_and_validate_events(repo_root: Path) -> List[Dict[str, Any]]:
    return _load_validate_event_rows(repo_root)


def _surface_exists_now(repo_root: Path, entry: Mapping[str, Any]) -> bool:
    path_value = str(entry.get("path") or "").strip()
    if not path_value:
        return False
    return (repo_root / path_value).exists()


def _event_log_evidence_durability(
    repo_root: Path,
    events: Sequence[Mapping[str, Any]],
) -> Dict[str, Any]:
    counts: Dict[str, int] = defaultdict(int)
    issues: List[Dict[str, Any]] = []
    for event in events:
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        for contract in _integration_contracts_from_payload(payload):
            exact = contract.get("exact_surfaces_discovered")
            if not isinstance(exact, list):
                continue
            for entry in exact:
                if not isinstance(entry, Mapping):
                    continue
                classification = classify_surface_entry(entry)
                artifact_class = str(classification.get("artifact_class") or "unknown_surface")
                counts[artifact_class] += 1
                if classification.get("durable_proof") is True:
                    counts["durable_proof"] += 1
                if str(entry.get("status") or "exists").strip() != "exists":
                    continue
                if _surface_exists_now(repo_root, entry):
                    continue
                if classification.get("ephemeral_local") is True:
                    issue_type = "ephemeral_local_absent_replay_allowed"
                elif artifact_class == "local_absolute_path":
                    issue_type = "local_absolute_absent_replay_allowed"
                elif artifact_class == "repo_path_durable":
                    issue_type = "repo_path_durable_absent_replay_allowed"
                else:
                    continue
                issues.append(
                    {
                        "issue_type": issue_type,
                        "severity": "warning",
                        "event_id": event.get("event_id"),
                        "subject_id": event.get("subject_id"),
                        "path": entry.get("path"),
                        "artifact_class": artifact_class,
                        "validation_policy": classification.get("validation_policy"),
                    }
                )
    severity_counts: Dict[str, int] = defaultdict(int)
    for issue in issues:
        severity_counts[str(issue.get("severity") or "unknown")] += 1
    warning_count = int(severity_counts.get("warning") or 0)
    error_count = sum(
        count
        for severity, count in severity_counts.items()
        if severity not in {"warning", "info"}
    )
    return {
        "schema": "task_ledger_evidence_durability_v0",
        "status": "error" if error_count else ("warning" if warning_count else "clean"),
        "counts": dict(sorted(counts.items())),
        "issue_count": len(issues),
        "warning_count": warning_count,
        "error_count": error_count,
        "severity_counts": dict(sorted(severity_counts.items())),
        "issues": issues[:50],
    }


def _validate_projection_state(projection: Mapping[str, Any]) -> None:
    work_item_rows = [
        item
        for item in projection.get("ledger", {}).get("work_items", [])
        if isinstance(item, Mapping)
    ]
    seen_ids: set[str] = set()
    duplicate_ids: set[str] = set()
    for item in work_item_rows:
        item_id = str(item.get("id") or "").strip()
        if not item_id:
            raise TaskLedgerError("WorkItem projection row is missing id")
        if item_id in seen_ids:
            duplicate_ids.add(item_id)
        seen_ids.add(item_id)
    if duplicate_ids:
        raise TaskLedgerError(f"duplicate WorkItem ids in projection: {sorted(duplicate_ids)}")
    work_items = {
        str(item.get("id") or ""): item
        for item in work_item_rows
    }
    for signoff in projection.get("sign_offs", {}).get("sign_offs", []):
        if not isinstance(signoff, Mapping):
            continue
        work_item_id = str(signoff.get("work_item_id") or signoff.get("task_id") or "").strip()
        if work_item_id and work_item_id not in work_items:
            raise TaskLedgerError(f"signoff {signoff.get('id')} points to unknown WorkItem {work_item_id}")
    for item in work_items.values():
        state = str(item.get("state") or item.get("status") or "")
        if state in {"claimed", "active"}:
            has_owner = bool(item.get("owner"))
            has_execution = bool((item.get("execution") or {}).get("agent_run_id"))
            has_work_ledger_ref = bool(item.get("work_ledger_refs"))
            if not (has_owner or has_execution or has_work_ledger_ref):
                raise TaskLedgerError(f"active WorkItem {item.get('id')} lacks owner or claim evidence")
    _validate_dependency_cycles(work_items)


def _validate_dependency_cycles(work_items: Mapping[str, Mapping[str, Any]]) -> None:
    graph = {
        item_id: _coerce_id_list(item.get("depends_on"))
        for item_id, item in work_items.items()
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            raise TaskLedgerError(f"dependency cycle includes {node}")
        if node in visited:
            return
        visiting.add(node)
        for dep in graph.get(node, []):
            if dep == node:
                raise TaskLedgerError(f"WorkItem {node} depends on itself")
            if dep not in graph:
                raise TaskLedgerError(f"WorkItem {node} depends on unknown WorkItem {dep}")
            visit(dep)
        visiting.remove(node)
        visited.add(node)

    for node_id in graph:
        visit(node_id)


def validate_event_log(repo_root: Path) -> Dict[str, Any]:
    health = authority_health(repo_root)
    strict_json = validate_strict_json_surfaces(repo_root)
    events, projection = _load_validate_events_and_projection(repo_root)
    strict_json["jsonl_paths"] = [str(path) for path in _authority_jsonl_rel_paths(repo_root)]
    strict_json["jsonl_event_count"] = len(events)
    evidence_durability = _event_log_evidence_durability(repo_root, events)
    evidence_status = str(evidence_durability.get("status") or "clean")
    validation_status = "valid_with_warnings" if evidence_status == "warning" else (
        "valid" if evidence_status == "clean" else "invalid"
    )
    if health.get("status") != "clean":
        validation_status = "authority_recovery_required"
    return {
        "ok": health.get("status") == "clean" and evidence_status == "clean",
        "validation_status": validation_status,
        "warning_count": int(evidence_durability.get("warning_count") or 0),
        "error_count": int(evidence_durability.get("error_count") or 0)
        + (0 if health.get("status") == "clean" else 1),
        "event_count": len(events),
        "work_item_count": len(projection["ledger"].get("work_items") or []),
        "task_count": len(projection["ledger"].get("tasks") or []),
        "capture_count": projection["views"]["capture_inbox"]["count"],
        "sign_off_count": len(projection["sign_offs"].get("sign_offs") or []),
        "strict_json": strict_json,
        "evidence_durability": evidence_durability,
        "authority_health": health,
    }


def bootstrap_legacy_events(repo_root: Path, *, created_by: str = "codex") -> Dict[str, Any]:
    existing = read_authority_events(repo_root)
    bootstrapped_subjects = {
        str(event.get("subject_id") or "")
        for event in existing
        if event.get("event_type") == "work_item.legacy_bootstrapped"
    }
    ledger = _safe_read_json(repo_root / LEDGER_REL)
    tasks = ledger.get("tasks") if isinstance(ledger.get("tasks"), list) else []
    appended: List[str] = []
    appended_subjects: List[str] = []
    for task in tasks:
        if not isinstance(task, Mapping):
            continue
        task_id = str(task.get("id") or "").strip()
        if not task_id or task_id in bootstrapped_subjects:
            continue
        work_item = _legacy_task_to_work_item(task)
        result = append_event(
            repo_root,
            {
                "event_type": "work_item.legacy_bootstrapped",
                "created_by": created_by,
                "subject_id": task_id,
                "source": {
                    "kind": "legacy_task_ledger_v0",
                    "refs": [str(LEDGER_REL)],
                },
                "refs": {
                    "legacy_projection_path": str(LEDGER_REL),
                },
                "payload": {
                    "work_item": work_item,
                    "legacy_snapshot": dict(task),
                },
            },
        )
        appended.append(str(result["event"]["event_id"]))
        appended_subjects.append(task_id)
    rebuild = rebuild_projections(repo_root)
    return {
        "ok": True,
        "bootstrapped_count": len(appended),
        "event_ids": appended,
        "projection": rebuild,
        "visibility_receipt": visibility_receipt(
            repo_root,
            subject_ids=appended_subjects,
            event_ids=appended,
            projection_rebuilt=True,
            projection_result=rebuild,
        ) if appended_subjects or appended else None,
    }
