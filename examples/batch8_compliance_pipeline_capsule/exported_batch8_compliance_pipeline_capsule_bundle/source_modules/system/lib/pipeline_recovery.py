"""
[PURPOSE]
- Teleology: Preserve and rewind phase runtime state so controller-driven pipeline loops can recover from bad writes, archive stale cycles, and keep a bounded history of snapshots.
- Mechanism: Derive a phase-local `.pipeline_recovery` surface, capture manual or pre-save snapshots of `pipeline_state.json`, and archive runtime files or cycle folders into timestamped manifests.

[INTERFACE]
- Exports: recovery_root, snapshots_dir, archives_dir, create_snapshot, maybe_capture_pre_save_snapshot, list_snapshots, load_snapshot, restore_snapshot, phase_runtime_entries, cycle_dirs_after, archive_phase_runtime, archive_cycles_after.
- Reads: Phase runtime files under the active `phase_dir` plus existing recovery snapshots and archives.
- Writes: Recovery snapshots/manifests under `<phase_dir>/.pipeline_recovery/`; restore rewrites phase state, archives move runtime/cycle paths and retention removes old snapshots.

[FLOW]
- Resolve recovery directories from phase state -> capture auto/manual snapshots around state changes -> list/load/restore snapshots for rewind -> archive runtime surfaces or later cycle directories when trimming history.
- When-needed: Open when a controller or operator needs the file-level recovery surface for pipeline state rewind or archival cleanup.
- Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/phase_harbor.py; system/lib/pipeline/stage_process.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- Phase runtime contract: pipeline_state.json, cycle directories, and snapshot/archive manifests bind recovery paths to the supplied phase directory.

[CONSTRAINTS]
- Guarantee: Recovery artifacts stay phase-local under `.pipeline_recovery` and snapshot ids are timestamped plus hashed for stable uniqueness.
- Non-goal: This module does not decide controller routing or mutate synth/shard content beyond writing restored state or moving archived files.
- Atomicity: Snapshot writes, restore writes, archive moves, and retention deletes are sequential filesystem operations, without an all-artifact transaction.
"""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTO_SNAPSHOT_LIMIT = 60
RECOVERY_DIRNAME = ".pipeline_recovery"

RUNTIME_TOP_LEVEL_FILES = {
    "pipeline_state.json",
    "pipeline_resume.json",
    "pipeline_resume.md",
    "pipeline_attention.json",
    "pipeline_attention.md",
    "pipeline_signal.json",
    "pipeline_signal.md",
    "extracted_shards.json",
    "raw_seed_digest.json",
    "system_view.json",
    "task_backlog.json",
    "task_dag.json",
    "apply_plan.json",
    "apply_packet.json",
    "focus_directive.json",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _short_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:10]


def _relative(path: Path, *, repo_root: Path = REPO_ROOT) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dict(payload), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return path


def _phase_dir_token(state: Mapping[str, Any]) -> str:
    return str(state.get("phase_dir") or "").strip()


def _phase_dir_path(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    token = _phase_dir_token(state)
    if not token:
        raise ValueError("state has no phase_dir")
    return repo_root / token


def recovery_root(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    """[ACTION]
    - Teleology: Resolve the top-level recovery directory for the phase referenced by `state`.
    - Guarantee: Returns the absolute Path to `<phase_dir>/.pipeline_recovery`.
    - Fails: Raises ValueError when state has no `phase_dir`.
    """
    return _phase_dir_path(state, repo_root=repo_root) / RECOVERY_DIRNAME


def snapshots_dir(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    """[ACTION]
    - Teleology: Resolve the snapshots subdirectory under the recovery root for the given phase state.
    - Guarantee: Returns the absolute Path to `<phase_dir>/.pipeline_recovery/snapshots`.
    - Fails: Raises ValueError when state has no `phase_dir`.
    """
    return recovery_root(state, repo_root=repo_root) / "snapshots"


def archives_dir(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    """[ACTION]
    - Teleology: Resolve the archives subdirectory under the recovery root for the given phase state.
    - Guarantee: Returns the absolute Path to `<phase_dir>/.pipeline_recovery/archives`.
    - Fails: Raises ValueError when state has no `phase_dir`.
    """
    return recovery_root(state, repo_root=repo_root) / "archives"


def _snapshot_signature(state: Mapping[str, Any]) -> str:
    payload = {
        "stage": str(state.get("stage") or "").strip(),
        "cycle": int(state.get("cycle") or 0),
        "gate_reason": str(state.get("gate_reason") or "").strip(),
        "controller_phase": str(state.get("controller_phase") or "").strip(),
        "current_layer_id": str(state.get("current_layer_id") or "").strip(),
        "observe_plan_path": str(state.get("observe_plan_path") or "").strip(),
        "observe_manifest_path": str(state.get("observe_manifest_path") or "").strip(),
        "observe_session_id": str(state.get("observe_session_id") or "").strip(),
        "current_cycle_dir": str(state.get("current_cycle_dir") or "").strip(),
    }
    return sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()[:16]


def _snapshot_reason(previous: Mapping[str, Any], new_state: Mapping[str, Any]) -> str:
    prev_stage = str(previous.get("stage") or "unknown").strip()
    next_stage = str(new_state.get("stage") or "unknown").strip()
    prev_cycle = int(previous.get("cycle") or 0)
    next_cycle = int(new_state.get("cycle") or 0)
    prev_gate = str(previous.get("gate_reason") or "none").strip() or "none"
    next_gate = str(new_state.get("gate_reason") or "none").strip() or "none"
    return (
        f"auto_before_save:"
        f"{prev_stage}@{prev_cycle}:{prev_gate}"
        f"->"
        f"{next_stage}@{next_cycle}:{next_gate}"
    )


def create_snapshot(
    state_path: Path,
    state: Mapping[str, Any],
    *,
    reason: str,
    repo_root: Path = REPO_ROOT,
    source: str = "manual",
    retention: int = AUTO_SNAPSHOT_LIMIT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Persist one recovery snapshot of pipeline state before or between controller transitions.
    - Mechanism: Build a hashed snapshot id from phase, reason, and state signature; write a snapshot payload under `.pipeline_recovery/snapshots`; then prune older snapshots past retention.
    - Reads: state_path only for metadata recording; the supplied in-memory state is the snapshot authority.
    - Writes: One snapshot JSON file and, when needed, deletes obsolete snapshots beyond the retention window.
    - Guarantee: Returns the written snapshot payload with `snapshot_path` attached.
    - Fails: Raises when phase_dir is missing from state or filesystem writes fail.
    - When-needed: Open when tracing exactly what recovery snapshot gets written around a controller state transition.
    - Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/phase_harbor.py
    """
    phase_dir = _phase_dir_token(state)
    if not phase_dir:
        raise ValueError("state has no phase_dir")
    created_at = _utc_now()
    snapshot_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        f"_{_short_hash(f'{phase_dir}|{reason}|{_snapshot_signature(state)}|{created_at}')}"
    )
    payload = {
        "kind": "pipeline_state_snapshot",
        "snapshot_id": snapshot_id,
        "created_at": created_at,
        "reason": str(reason or "manual").strip() or "manual",
        "source": str(source or "manual").strip() or "manual",
        "state_path": _relative(state_path, repo_root=repo_root),
        "phase_dir": phase_dir,
        "cycle": int(state.get("cycle") or 0),
        "stage": str(state.get("stage") or "").strip() or None,
        "gate_reason": str(state.get("gate_reason") or "").strip() or None,
        "controller_phase": str(state.get("controller_phase") or "").strip() or None,
        "signature": _snapshot_signature(state),
        "state": dict(state),
    }
    snapshot_path = snapshots_dir(state, repo_root=repo_root) / f"{snapshot_id}.json"
    _write_json(snapshot_path, payload)
    _prune_snapshots(state, repo_root=repo_root, retention=retention)
    payload["snapshot_path"] = _relative(snapshot_path, repo_root=repo_root)
    return payload


def _prune_snapshots(
    state: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    retention: int = AUTO_SNAPSHOT_LIMIT,
) -> None:
    if retention <= 0:
        return
    directory = snapshots_dir(state, repo_root=repo_root)
    if not directory.exists():
        return
    snapshots = sorted(directory.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    for obsolete in snapshots[retention:]:
        obsolete.unlink(missing_ok=True)


def maybe_capture_pre_save_snapshot(
    state_path: Path,
    new_state: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    retention: int = AUTO_SNAPSHOT_LIMIT,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Capture an automatic rewind point only when an impending state save would materially change the controller snapshot signature.
    - Mechanism: Load the prior state from disk, compare signatures, and delegate to create_snapshot() only when the new state differs.
    - Reads: state_path and the supplied new_state mapping.
    - Writes: A snapshot file only when the signature changes.
    - Guarantee: Returns None for missing prior state or no-op saves; otherwise returns the created snapshot payload.
    - Fails: Propagates create_snapshot() errors when a snapshot is needed.
    - When-needed: Open when auditing why a pipeline save did or did not create an automatic recovery point.
    - Escalates-to: system/lib/pipeline_recovery.py; system/lib/phase_harbor.py
    """
    previous = _load_json(state_path)
    if not previous:
        return None
    if _snapshot_signature(previous) == _snapshot_signature(new_state):
        return None
    return create_snapshot(
        state_path,
        previous,
        reason=_snapshot_reason(previous, new_state),
        repo_root=repo_root,
        source="auto",
        retention=retention,
    )


def list_snapshots(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Enumerate all persisted recovery snapshots for the active phase, newest first.
    - Guarantee: Returns a list of snapshot payload dicts, each augmented with a `snapshot_path` field; returns `[]` when no snapshots exist.
    - Fails: None.
    """
    directory = snapshots_dir(state, repo_root=repo_root)
    if not directory.exists():
        return []
    snapshots: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
        payload = _load_json(path)
        if not payload:
            continue
        payload["snapshot_path"] = _relative(path, repo_root=repo_root)
        snapshots.append(payload)
    return snapshots


def load_snapshot(
    state: Mapping[str, Any],
    snapshot_id: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Load one named recovery snapshot from the phase snapshots directory.
    - Guarantee: Returns the snapshot payload dict augmented with `snapshot_path` when found.
    - Fails: Raises ValueError when `snapshot_id` is blank; raises FileNotFoundError when the snapshot file does not exist or is unreadable.
    """
    token = str(snapshot_id or "").strip()
    if not token:
        raise ValueError("snapshot_id is required")
    path = snapshots_dir(state, repo_root=repo_root) / f"{token}.json"
    payload = _load_json(path)
    if not payload:
        raise FileNotFoundError(f"snapshot not found: {token}")
    payload["snapshot_path"] = _relative(path, repo_root=repo_root)
    return payload


def restore_snapshot(
    state_path: Path,
    current_state: Mapping[str, Any],
    snapshot_id: str,
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Rewind the active pipeline state to a previously captured snapshot while preserving a backup of the state being replaced.
    - Mechanism: Load the requested snapshot, capture a `before_restore:*` backup of the current state, then overwrite `state_path` with the stored snapshot state.
    - Reads: The requested snapshot plus the current state mapping.
    - Writes: A backup snapshot and the restored pipeline state file.
    - Guarantee: Returns the loaded snapshot, backup snapshot, and restored state payload together.
    - Fails: Raises when the snapshot id is missing/unreadable or when filesystem writes fail.
    - When-needed: Open when an operator needs the exact recovery path that replays a prior controller state onto disk.
    - Escalates-to: system/lib/phase_harbor.py; system/lib/seed_pipeline_controller.py
    - Navigation-group: kernel_lib
    """
    snapshot = load_snapshot(current_state, snapshot_id, repo_root=repo_root)
    backup = create_snapshot(
        state_path,
        current_state,
        reason=f"before_restore:{snapshot_id}",
        repo_root=repo_root,
        source="manual",
    )
    restored_state = dict(snapshot.get("state") or {})
    _write_json(state_path, restored_state)
    return {
        "snapshot": snapshot,
        "backup_snapshot": backup,
        "restored_state": restored_state,
    }


def phase_runtime_entries(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> list[Path]:
    """[ACTION]
    - Teleology: Collect the archivable runtime entries (known pipeline files and cycle directories) present in the active phase directory.
    - Guarantee: Returns a sorted list of Paths for entries that match runtime file names or `cycle_*` directories; returns `[]` when the phase directory does not exist.
    - Fails: Raises ValueError when state has no `phase_dir`.
    """
    phase_dir = _phase_dir_path(state, repo_root=repo_root)
    if not phase_dir.exists():
        return []
    entries: list[Path] = []
    for child in sorted(phase_dir.iterdir(), key=lambda path: path.name):
        if child.name == RECOVERY_DIRNAME:
            continue
        if child.is_dir() and child.name.startswith("cycle_"):
            entries.append(child)
            continue
        if child.is_file() and (
            child.name in RUNTIME_TOP_LEVEL_FILES
            or child.name.startswith("pipeline_")
            or child.match("Pass * Observe Result.md")
        ):
            entries.append(child)
    return entries


def cycle_dirs_after(
    state: Mapping[str, Any],
    after_cycle: int,
    *,
    repo_root: Path = REPO_ROOT,
) -> list[Path]:
    """[ACTION]
    - Teleology: Select all `cycle_N` directories whose numeric index exceeds `after_cycle`.
    - Guarantee: Returns a sorted list of matching cycle directory Paths; returns `[]` when the phase directory does not exist or no later cycles are found.
    - Fails: Raises ValueError when state has no `phase_dir`.
    """
    phase_dir = _phase_dir_path(state, repo_root=repo_root)
    if not phase_dir.exists():
        return []
    selected: list[Path] = []
    for child in sorted(phase_dir.iterdir(), key=lambda path: path.name):
        if not child.is_dir() or not child.name.startswith("cycle_"):
            continue
        suffix = child.name[len("cycle_") :]
        try:
            cycle_num = int(suffix)
        except ValueError:
            continue
        if cycle_num > int(after_cycle):
            selected.append(child)
    return selected


def archive_paths(
    state: Mapping[str, Any],
    paths: Iterable[Path],
    *,
    reason: str,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Move a caller-supplied set of phase-local paths into a timestamped archive under the recovery directory.
    - Guarantee: Returns a manifest dict describing the archive id, moved entries, and archive root; entries that do not exist or are outside the phase directory are silently skipped.
    - Fails: Raises ValueError when state has no `phase_dir`; propagates filesystem errors from `shutil.move` or `mkdir`.
    """
    phase_dir = _phase_dir_path(state, repo_root=repo_root)
    archive_id = (
        f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
        f"_{_short_hash(f'{_phase_dir_token(state)}|{reason}|{_utc_now()}')}"
    )
    archive_root = archives_dir(state, repo_root=repo_root) / archive_id
    archived: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            continue
        try:
            rel = path.resolve().relative_to(phase_dir.resolve())
        except ValueError:
            continue
        destination = archive_root / rel
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(path), str(destination))
        archived.append(
            {
                "source": _relative(path, repo_root=repo_root),
                "destination": _relative(destination, repo_root=repo_root),
            }
        )
    manifest = {
        "kind": "phase_runtime_archive",
        "archive_id": archive_id,
        "created_at": _utc_now(),
        "reason": str(reason or "archive").strip() or "archive",
        "phase_dir": _phase_dir_token(state),
        "archive_root": _relative(archive_root, repo_root=repo_root),
        "entry_count": len(archived),
        "entries": archived,
    }
    if archived:
        _write_json(archive_root / "manifest.json", manifest)
    return manifest


def archive_phase_runtime(
    state: Mapping[str, Any],
    *,
    reason: str,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Move the active phase runtime surface into recovery storage as one bounded archive event.
    - Mechanism: Enumerate phase_runtime_entries() and delegate the move plus manifest creation to archive_paths().
    - Reads: The phase runtime directory under `phase_dir`.
    - Writes: Archived runtime entries and a manifest under `.pipeline_recovery/archives/`.
    - Guarantee: Returns the archive manifest, including any moved entries.
    - Fails: Propagates filesystem and path-resolution failures from archive_paths().
    - When-needed: Open when clearing a phase runtime surface but preserving the exact files for later inspection.
    - Escalates-to: system/lib/phase_harbor.py; system/lib/seed_pipeline_controller.py
    """
    return archive_paths(
        state,
        phase_runtime_entries(state, repo_root=repo_root),
        reason=reason,
        repo_root=repo_root,
    )


def archive_cycles_after(
    state: Mapping[str, Any],
    after_cycle: int,
    *,
    reason: str,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Archive all cycle directories newer than a chosen boundary.
    - Mechanism: Select cycle directories with numbers greater than `after_cycle` and move them through archive_paths().
    - Reads: The phase directory under `phase_dir`.
    - Writes: Archived cycle folders and a manifest under `.pipeline_recovery/archives/`.
    - Guarantee: Returns the archive manifest for the selected cycle directories.
    - Fails: Propagates filesystem and path-resolution failures from archive_paths().
    - When-needed: Open when repairing or rewinding a phase requires trimming later cycles without deleting them outright.
    - Escalates-to: system/lib/phase_harbor.py; system/lib/pipeline/stage_process.py
    """
    return archive_paths(
        state,
        cycle_dirs_after(state, after_cycle, repo_root=repo_root),
        reason=reason,
        repo_root=repo_root,
    )
