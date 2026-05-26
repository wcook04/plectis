"""Generated-state drainer status and narrow projection refresh actions.

The drainer is an egress controller: it reports generated read-model pressure
and owns serial refresh lanes. It is deliberately separate from WorkItem
landing, which records attempt events and receipts but should not commit shared
projection bundles opportunistically.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from system.lib import generated_projection_registry, task_ledger_events, work_ledger


STATUS_SCHEMA = "generated_state_drainer_status_v0"
APPLY_SCHEMA = "generated_state_drainer_apply_v0"
LANDING_PLAN_SCHEMA = "generated_projection_landing_plan_v0"
LANDING_MANIFEST_SCHEMA = "generated_projection_landing_manifest_v0"
LANDING_SCHEMA = "generated_projection_landing_v0"
SETTLEMENT_PLAN_SCHEMA = "generated_projection_settlement_plan_v0"
SETTLEMENT_SCHEMA = "generated_projection_settlement_v0"
WORK_LEDGER_OWNER_ID = "work_ledger_index_projection"
TASK_LEDGER_OWNER_ID = "task_ledger_projection"
SYSTEM_ATLAS_OWNER_ID = "system_atlas_projection"
WORK_LEDGER_REFRESH_ACTION = "work_ledger_projection_refresh"
TASK_LEDGER_REFRESH_ACTION = "task_ledger_projection_refresh"
SYSTEM_ATLAS_REFRESH_ACTION = "system_atlas_projection_refresh"
APPEND_EXEMPT_LANDING_MODE = "append-exempt"
SUPPORTED_LANDING_OWNER_IDS = (WORK_LEDGER_OWNER_ID, TASK_LEDGER_OWNER_ID, SYSTEM_ATLAS_OWNER_ID)
SUPPORTED_SETTLEMENT_OWNER_IDS = (TASK_LEDGER_OWNER_ID, WORK_LEDGER_OWNER_ID, SYSTEM_ATLAS_OWNER_ID)
ProgressCallback = Callable[[Mapping[str, Any]], None]


def _emit_progress(
    progress_callback: ProgressCallback | None,
    *,
    surface: str,
    event: str,
    **fields: Any,
) -> None:
    if progress_callback is None:
        return
    payload: dict[str, Any] = {
        "schema": "generated_state_drainer_progress_v0",
        "surface": surface,
        "event": event,
        "privacy": "phase_names_counts_and_status_only_no_stdout_stderr_bodies",
    }
    payload.update({key: value for key, value in fields.items() if value is not None})
    progress_callback(payload)


def _hash_bytes(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _hash_file(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    return _hash_bytes(path.read_bytes())


def _json_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return _hash_bytes(payload)


def _git_status_map(repo_root: Path) -> dict[str, str]:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "status", "--porcelain=v1", "--untracked-files=all"],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        return {}
    rows: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if not line:
            continue
        status = line[:2]
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        path = path.strip('"')
        if path:
            rows[path] = status
    return rows


def _run_git(repo_root: Path, args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *[str(part) for part in args]],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _dirty_status(rel_path: str, status_map: Mapping[str, str]) -> str:
    status = str(status_map.get(rel_path) or "").strip()
    if not status:
        return "clean"
    if "?" in status:
        return "untracked"
    if "D" in status:
        return "deleted"
    if "M" in status:
        return "modified"
    return status.strip() or "dirty"


def _command_text(argv: Sequence[str]) -> str:
    return " ".join(str(part) for part in argv)


def _run_owner_json_command(repo_root: Path, argv: Sequence[str]) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            [str(part) for part in argv],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        return {
            "ok": False,
            "returncode": 127,
            "stderr": str(exc),
            "command": _command_text(argv),
        }
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    payload.setdefault("ok", proc.returncode == 0)
    payload.setdefault("returncode", proc.returncode)
    if proc.stderr.strip():
        payload.setdefault("stderr", proc.stderr.strip())
    return payload


def _landing_manifest_rel(owner_id: str) -> Path:
    return Path("state/generated_projection_landing") / f"{owner_id}_manifest.json"


def _read_json_dict(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _family_event_hash(repo_root: Path, family_id: str | None) -> str | None:
    token = str(family_id or "").strip()
    if not token:
        return None
    try:
        events = work_ledger.load_events(repo_root, family_id=token)
    except Exception:
        return None
    return _json_hash(events)


def _line_count(path: Path) -> int:
    if not path.exists() or not path.is_file():
        return 0
    try:
        return len(path.read_text(encoding="utf-8", errors="replace").splitlines())
    except OSError:
        return 0


def _projection_diff_stat(
    repo_root: Path,
    projection_rows: Sequence[Mapping[str, Any]],
    *,
    status_map: Mapping[str, str] | None = None,
    collect_numstat: bool = True,
) -> dict[str, Any]:
    paths = [str(row.get("generated_path") or "").strip() for row in projection_rows if row.get("generated_path")]
    if not paths:
        return {
            "paths": [],
            "path_count": 0,
            "total_insertions": 0,
            "total_deletions": 0,
            "total_changed_lines": 0,
            "large_generated_diff": False,
            "review_status": "clear",
        }
    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    if not collect_numstat:
        path_rows = [
            {
                "path": rel_path,
                "dirty_status": _dirty_status(rel_path, status_map),
            }
            for rel_path in paths
        ]
        dirty_count = sum(1 for row in path_rows if row.get("dirty_status") != "clean")
        return {
            "paths": path_rows,
            "path_count": len(paths),
            "dirty_path_count": dirty_count,
            "total_insertions": None,
            "total_deletions": None,
            "total_changed_lines": None,
            "large_generated_diff": None,
            "review_status": "watch" if dirty_count else "clear",
            "stat_mode": "status_only",
        }
    proc = _run_git(repo_root, ["diff", "--numstat", "--", *paths])
    by_path: dict[str, dict[str, Any]] = {}
    total_insertions = 0
    total_deletions = 0
    if proc.returncode == 0:
        for line in proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            insertions_text, deletions_text, rel_path = parts[0], parts[1], parts[2]
            insertions = 0 if insertions_text == "-" else int(insertions_text or 0)
            deletions = 0 if deletions_text == "-" else int(deletions_text or 0)
            by_path[rel_path] = {
                "path": rel_path,
                "insertions": insertions,
                "deletions": deletions,
                "dirty_status": _dirty_status(rel_path, status_map),
            }
            total_insertions += insertions
            total_deletions += deletions
    for rel_path in paths:
        if rel_path in by_path:
            continue
        dirty = _dirty_status(rel_path, status_map)
        insertions = _line_count(repo_root / rel_path) if dirty == "untracked" else 0
        by_path[rel_path] = {
            "path": rel_path,
            "insertions": insertions,
            "deletions": 0,
            "dirty_status": dirty,
        }
        total_insertions += insertions
    total_changed = total_insertions + total_deletions
    large_generated_diff = total_changed >= 10000
    return {
        "paths": [by_path[path] for path in paths],
        "path_count": len(paths),
        "total_insertions": total_insertions,
        "total_deletions": total_deletions,
        "total_changed_lines": total_changed,
        "large_generated_diff": large_generated_diff,
        "review_status": "watch" if total_changed else "clear",
        "stat_mode": "numstat",
    }


def _work_ledger_source_paths(projection_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    paths: set[str] = set()
    for row in projection_rows:
        phase_id = str(row.get("phase_id") or "").strip()
        if phase_id:
            paths.add(str(Path("codex/ledger") / phase_id / "work_ledger.jsonl"))
    return sorted(paths)


def _existing_rel_paths(repo_root: Path, rel_paths: Sequence[Path | str]) -> list[str]:
    paths: list[str] = []
    for rel_path in rel_paths:
        rel = str(rel_path)
        if rel and (repo_root / rel).exists():
            paths.append(rel)
    return sorted(dict.fromkeys(paths))


def _task_ledger_source_artifact_paths(repo_root: Path) -> list[str]:
    return _existing_rel_paths(
        repo_root,
        [
            task_ledger_events.EVENTS_REL,
            task_ledger_events.EVENTS_AUDIT_REL,
        ],
    )


def _task_ledger_projection_artifact_paths(repo_root: Path) -> list[str]:
    rels: list[Path | str] = [task_ledger_events.LEDGER_REL, task_ledger_events.SIGNOFFS_REL]
    views_dir = repo_root / task_ledger_events.VIEWS_REL
    if views_dir.is_dir():
        rels.extend(child.relative_to(repo_root) for child in sorted(views_dir.glob("*.json")))
    return _existing_rel_paths(repo_root, rels)


def _work_ledger_projection_artifact_paths(repo_root: Path) -> list[str]:
    ledger_dir = repo_root / "codex" / "ledger"
    if not ledger_dir.is_dir():
        return []
    return [
        str(path.relative_to(repo_root))
        for path in sorted(ledger_dir.glob("*/work_ledger_index.json"))
        if path.is_file()
    ]


def _work_ledger_source_artifact_paths(repo_root: Path) -> list[str]:
    ledger_dir = repo_root / "codex" / "ledger"
    if not ledger_dir.is_dir():
        return []
    return [
        str(path.relative_to(repo_root))
        for path in sorted(ledger_dir.glob("*/work_ledger.jsonl"))
        if path.is_file()
    ]


def _registry_existing_paths(repo_root: Path, pathspecs: Sequence[str]) -> list[str]:
    paths: list[str] = []
    for pathspec in pathspecs:
        spec = str(pathspec or "").strip()
        if not spec:
            continue
        if any(char in spec for char in "*?[]"):
            for path in sorted(repo_root.glob(spec)):
                if path.is_file():
                    paths.append(str(path.relative_to(repo_root)))
            continue
        path = repo_root / spec
        if path.is_file():
            paths.append(spec)
    return sorted(dict.fromkeys(paths))


def _registry_artifact_paths(repo_root: Path, owner_id: str) -> list[str]:
    owner = generated_projection_registry.get_projection_owner(owner_id)
    return _registry_existing_paths(repo_root, owner.artifacts)


def _registry_source_authority_paths(repo_root: Path, owner_id: str) -> list[str]:
    owner = generated_projection_registry.get_projection_owner(owner_id)
    return _registry_existing_paths(repo_root, owner.source_authorities)


def _dirty_existing_paths(
    repo_root: Path,
    paths: Sequence[str],
    *,
    status_map: Mapping[str, str] | None = None,
) -> list[str]:
    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    dirty: list[str] = []
    for rel_path in paths:
        if _dirty_status(rel_path, status_map) != "clean" and (repo_root / rel_path).exists():
            dirty.append(rel_path)
    return dirty


def _head_changed_existing_paths(
    repo_root: Path,
    paths: Sequence[str],
    *,
    status_map: Mapping[str, str] | None = None,
) -> list[str]:
    candidates = sorted({str(path) for path in paths if str(path).strip()})
    if not candidates:
        return []
    proc = _run_git(repo_root, ["diff", "--name-only", "HEAD", "--", *candidates])
    changed = set(proc.stdout.splitlines()) if proc.returncode == 0 else set()
    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    return [
        rel_path
        for rel_path in candidates
        if (repo_root / rel_path).exists()
        and (rel_path in changed or _dirty_status(rel_path, status_map) == "untracked")
    ]


def _cached_changed_existing_paths(repo_root: Path, paths: Sequence[str]) -> list[str]:
    candidates = sorted({str(path) for path in paths if str(path).strip()})
    if not candidates:
        return []
    proc = _run_git(repo_root, ["diff", "--cached", "--name-only", "--", *candidates])
    if proc.returncode != 0:
        return []
    return [
        rel_path
        for rel_path in proc.stdout.splitlines()
        if rel_path in candidates and (repo_root / rel_path).exists()
    ]


def _refresh_index_only_projection_residue(
    repo_root: Path,
    paths: Sequence[str],
    *,
    status_map: Mapping[str, str] | None = None,
) -> list[str]:
    """Clear owner-scoped index residue when the worktree already matches HEAD.

    Append-exempt landing commits worktree contents through a private index. If a
    previous landing left the shared index staged to an older generated
    projection while the worktree was already equal to HEAD, there is no commit
    to make, but `git status` stays dirty. Refresh only exact owner paths that
    are cached-dirty and not worktree-dirty relative to HEAD.
    """
    candidates = _cached_changed_existing_paths(repo_root, paths)
    if not candidates:
        return []
    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    head_changed = set(_head_changed_existing_paths(repo_root, candidates, status_map=status_map))
    index_only = [rel_path for rel_path in candidates if rel_path not in head_changed]
    if not index_only:
        return []
    _run_git(repo_root, ["reset", "HEAD", "--", *index_only])
    return index_only


def _path_hashes(repo_root: Path, paths: Sequence[str]) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for rel_path in paths:
        digest = _hash_file(repo_root / rel_path)
        if digest:
            hashes[rel_path] = digest
    return hashes


def _task_ledger_expected_targets(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    with task_ledger_events.file_lock(repo_root / task_ledger_events.LOCK_REL):
        events = task_ledger_events.load_and_validate_events(repo_root)
        current_ledger = _read_json_dict(repo_root / task_ledger_events.LEDGER_REL)
        generated_at = str(current_ledger.get("generated_at") or "").strip() or None
        projection = task_ledger_events.build_projection(
            events,
            generated_at=generated_at,
            mission_blackboard=_read_json_dict(repo_root / task_ledger_events.MISSION_BLACKBOARD_REL),
            repo_root=repo_root,
        )
    source_hash = _json_hash(events)
    targets: dict[Path, Mapping[str, Any]] = {
        task_ledger_events.LEDGER_REL: projection["ledger"],
        task_ledger_events.SIGNOFFS_REL: projection["sign_offs"],
    }
    for name, payload in projection["views"].items():
        targets[task_ledger_events.VIEWS_REL / f"{name}.json"] = payload
    return (
        projection,
        [
            {
                "rel_path": str(rel_path),
                "payload": payload,
            }
            for rel_path, payload in targets.items()
        ],
        source_hash,
    )


def _work_ledger_projection_rows(repo_root: Path, status_map: Mapping[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    owner = generated_projection_registry.get_projection_owner(WORK_LEDGER_OWNER_ID)
    check = work_ledger.check_project_all(repo_root)
    rows: list[dict[str, Any]] = []
    for family in check.get("families") or []:
        family_id = str(family.get("family_id") or "").strip()
        source_hash = _family_event_hash(repo_root, family_id)
        for projection in family.get("projection_results") or []:
            rel_path = str(projection.get("index_path") or "").strip()
            path = repo_root / rel_path
            freshness = "fresh" if projection.get("fresh") else str(projection.get("reason") or "projection_stale")
            rows.append(
                {
                    "generated_path": rel_path,
                    "owner_id": owner.owner_id,
                    "owner_tool": _command_text(owner.repair_command),
                    "check_command": _command_text(owner.check_command),
                    "source_authority": "codex/ledger/*/work_ledger.jsonl",
                    "source_event_hash": source_hash,
                    "projection_hash": _hash_file(path),
                    "freshness_status": freshness,
                    "dirty_status": _dirty_status(rel_path, status_map),
                    "durable_projection": True,
                    "commit_policy": "serial_drainer_only",
                    "bloat_class": "work_ledger_event_or_projection",
                    "recommended_owner_action": "none" if projection.get("fresh") else _command_text(owner.repair_command),
                    "safe_to_commit_by_agent": False,
                    "apply_supported": True,
                    "phase_id": projection.get("phase_id"),
                    "family_id": family_id,
                    "counts": projection.get("counts"),
                }
            )
    return rows, check


def _task_ledger_projection_rows(repo_root: Path, status_map: Mapping[str, str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    owner = generated_projection_registry.get_projection_owner(TASK_LEDGER_OWNER_ID)
    if not (repo_root / task_ledger_events.EVENTS_REL).exists():
        existing_artifacts: list[str] = []
        for rel in (task_ledger_events.LEDGER_REL, task_ledger_events.SIGNOFFS_REL):
            if (repo_root / rel).exists():
                existing_artifacts.append(str(rel))
        views_dir = repo_root / task_ledger_events.VIEWS_REL
        if views_dir.is_dir():
            for child in sorted(views_dir.glob("*.json")):
                existing_artifacts.append(str(child.relative_to(repo_root)))
        if not existing_artifacts:
            # Case A: pure uninitialized — no events log AND no projections to be orphaned.
            return [], {
                "ok": True,
                "mode": "check",
                "reason": "task_ledger_events_log_absent",
                "families": [],
            }
        # Case B: source authority is missing but projection artifacts exist on disk.
        # These projections cannot be regenerated without their event log; surface
        # them as source_authority_missing rather than letting summary report fresh_clean.
        rows: list[dict[str, Any]] = []
        for rel_path in existing_artifacts:
            path = repo_root / rel_path
            rows.append(
                {
                    "generated_path": rel_path,
                    "owner_id": owner.owner_id,
                    "owner_tool": _command_text(owner.repair_command),
                    "check_command": _command_text(owner.check_command),
                    "source_authority": "state/task_ledger/events.jsonl",
                    "source_event_hash": None,
                    "projection_hash": _hash_file(path),
                    "freshness_status": "source_authority_missing",
                    "dirty_status": _dirty_status(rel_path, status_map),
                    "durable_projection": True,
                    "commit_policy": "serial_drainer_only",
                    "bloat_class": "task_ledger_event_or_projection",
                    "recommended_owner_action": _command_text(owner.repair_command),
                    "safe_to_commit_by_agent": False,
                    "apply_supported": True,
                    "counts": None,
                }
            )
        return rows, {
            "ok": False,
            "mode": "check",
            "reason": "source_authority_missing_with_existing_projections",
            "families": [],
            "existing_artifact_count": len(existing_artifacts),
        }
    try:
        projection, targets, source_hash = _task_ledger_expected_targets(repo_root)
    except Exception as exc:
        return [], {
            "ok": False,
            "mode": "check",
            "error": str(exc),
            "families": [],
        }
    rows: list[dict[str, Any]] = []
    mismatches: list[str] = []
    for target in targets:
        rel_path = str(target["rel_path"])
        path = repo_root / rel_path
        expected_payload = target["payload"]
        current_payload = _read_json_dict(path)
        fresh = bool(current_payload) and current_payload == expected_payload
        if not fresh:
            mismatches.append(rel_path)
        rows.append(
            {
                "generated_path": rel_path,
                "owner_id": owner.owner_id,
                "owner_tool": _command_text(owner.repair_command),
                "check_command": _command_text(owner.check_command),
                "source_authority": "state/task_ledger/events.jsonl",
                "source_event_hash": source_hash,
                "projection_hash": _hash_file(path),
                "freshness_status": "fresh" if fresh else "projection_stale",
                "dirty_status": _dirty_status(rel_path, status_map),
                "durable_projection": True,
                "commit_policy": "serial_drainer_only",
                "bloat_class": "task_ledger_event_or_projection",
                "recommended_owner_action": "none" if fresh else _command_text(owner.repair_command),
                "safe_to_commit_by_agent": False,
                "apply_supported": True,
                "counts": {
                    "work_items": len(projection["ledger"].get("work_items") or []),
                    "tasks": len(projection["ledger"].get("tasks") or []),
                    "captures": projection["views"]["capture_inbox"]["count"],
                    "sign_offs": len(projection["sign_offs"].get("sign_offs") or []),
                },
            }
        )
    return rows, {
        "ok": not mismatches,
        "mode": "check",
        "mismatches": mismatches,
        "projection_paths": [str(target["rel_path"]) for target in targets],
    }


def _registered_projection_rows(
    repo_root: Path,
    status_map: Mapping[str, str],
    owner_id: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    owner = generated_projection_registry.get_projection_owner(owner_id)
    check = _run_owner_json_command(repo_root, owner.check_command)
    source_coupling = check.get("source_coupling") if isinstance(check.get("source_coupling"), Mapping) else {}
    source_coupling_status = str(source_coupling.get("status") or "").strip()
    if check.get("ok"):
        freshness = "fresh"
        recommended_owner_action = "none"
    elif source_coupling_status:
        freshness = source_coupling_status
        recommended_owner_action = "settle_source_coupling_before_projection_refresh"
    else:
        freshness = "projection_stale"
        recommended_owner_action = _command_text(owner.repair_command)
    rows: list[dict[str, Any]] = []
    for rel_path in owner.artifacts:
        rel = str(rel_path)
        path = repo_root / rel
        rows.append(
            {
                "generated_path": rel,
                "owner_id": owner.owner_id,
                "owner_tool": _command_text(owner.repair_command),
                "check_command": _command_text(owner.check_command),
                "source_authority": "generated_projection_registry.source_authorities",
                "source_event_hash": None,
                "projection_hash": _hash_file(path),
                "freshness_status": freshness if path.exists() else "projection_missing",
                "dirty_status": _dirty_status(rel, status_map) if path.exists() else "missing",
                "durable_projection": True,
                "commit_policy": "serial_drainer_only",
                "bloat_class": f"{owner.owner_id}_event_or_projection",
                "recommended_owner_action": recommended_owner_action,
                "safe_to_commit_by_agent": False,
                "apply_supported": True,
                "counts": None,
            }
        )
    return rows, check


def _owner_catalog_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for owner in generated_projection_registry.iter_projection_owners():
        rows.append(
            {
                "owner_id": owner.owner_id,
                "description": owner.description,
                "artifacts": list(owner.artifacts),
                "source_authorities": list(owner.source_authorities),
                "check_command": _command_text(owner.check_command),
                "repair_command": _command_text(owner.repair_command),
                "apply_supported": owner.owner_id in SUPPORTED_LANDING_OWNER_IDS,
                "commit_policy": "serial_drainer_only",
            }
        )
    return rows


def _projection_summary(projection_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    stale_count = sum(1 for row in projection_rows if row.get("freshness_status") != "fresh")
    dirty_count = sum(1 for row in projection_rows if row.get("dirty_status") != "clean")
    if stale_count:
        summary_status = "stale"
    elif dirty_count:
        summary_status = "fresh_dirty"
    else:
        summary_status = "fresh_clean"
    return {
        "projection_target_count": len(projection_rows),
        "stale_count": stale_count,
        "dirty_count": dirty_count,
        "apply_supported_owner_ids": list(SUPPORTED_LANDING_OWNER_IDS),
        "status": summary_status,
    }


def _dirty_projection_paths(projection_rows: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(row.get("generated_path") or "")
        for row in projection_rows
        if row.get("generated_path") and row.get("dirty_status") != "clean"
    ]


def _owner_source_authority_label(owner_id: str) -> str:
    if owner_id == WORK_LEDGER_OWNER_ID:
        return "codex/ledger/*/work_ledger.jsonl"
    if owner_id == TASK_LEDGER_OWNER_ID:
        return "state/task_ledger/events.jsonl"
    return "generated_projection_registry.source_authorities"


def _owner_bloat_class(owner_id: str) -> str:
    if owner_id == WORK_LEDGER_OWNER_ID:
        return "work_ledger_event_or_projection"
    if owner_id == TASK_LEDGER_OWNER_ID:
        return "task_ledger_event_or_projection"
    return f"{owner_id}_event_or_projection"


def _owner_source_paths(
    repo_root: Path,
    owner_id: str,
    projection_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    if owner_id == WORK_LEDGER_OWNER_ID:
        return _work_ledger_source_paths(projection_rows)
    if owner_id == TASK_LEDGER_OWNER_ID:
        return _task_ledger_source_artifact_paths(repo_root)
    return _registry_source_authority_paths(repo_root, owner_id)


def _owner_repair_action(owner_id: str) -> str:
    if owner_id == WORK_LEDGER_OWNER_ID:
        return WORK_LEDGER_REFRESH_ACTION
    if owner_id == TASK_LEDGER_OWNER_ID:
        return TASK_LEDGER_REFRESH_ACTION
    if owner_id == SYSTEM_ATLAS_OWNER_ID:
        return SYSTEM_ATLAS_REFRESH_ACTION
    return f"{owner_id}_refresh"


def _owner_tool_label(owner_id: str) -> str:
    return "System Atlas" if owner_id == SYSTEM_ATLAS_OWNER_ID else (
        "Work Ledger" if owner_id == WORK_LEDGER_OWNER_ID else "Task Ledger"
    )


def _source_coupling_route_hints(source_coupling: Mapping[str, Any]) -> list[str]:
    hints: list[str] = []
    for key in ("dirty_changed_sources", "blocking_changed_sources", "changed_sources"):
        for row in source_coupling.get(key) or []:
            if not isinstance(row, Mapping):
                continue
            hint = str(row.get("owner_route_hint") or "").strip()
            if hint and hint not in hints:
                hints.append(hint)
    return hints


def _compact_source_coupling(source_coupling: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: source_coupling.get(key)
        for key in (
            "status",
            "reason",
            "changed_source_count",
            "blocking_changed_source_count",
            "dirty_changed_source_count",
            "claimed_dirty_source_count",
            "unknown_git_status_source_count",
            "refresh_policy",
            "safe_to_commit_generated_outputs_without_sources",
        )
        if source_coupling.get(key) not in (None, "")
    }
    rows: list[dict[str, Any]] = []
    for row in source_coupling.get("blocking_changed_sources") or []:
        if not isinstance(row, Mapping):
            continue
        claims = row.get("work_ledger_claims") if isinstance(row.get("work_ledger_claims"), Mapping) else {}
        rows.append(
            {
                key: value
                for key, value in {
                    "source_id": row.get("source_id"),
                    "path": row.get("path"),
                    "git_pathspec": row.get("git_pathspec"),
                    "git_status": row.get("git_status"),
                    "git_status_entries": list(row.get("git_status_entries") or [])[:5],
                    "owner_route_hint": row.get("owner_route_hint"),
                    "work_ledger_claim_status": claims.get("claim_status"),
                    "work_ledger_owner_action_hint": claims.get("owner_action_hint"),
                }.items()
                if value not in (None, "", [])
            }
        )
        if len(rows) >= 8:
            break
    if rows:
        compact["blocking_changed_sources_sample"] = rows
    hints = _source_coupling_route_hints(source_coupling)
    if hints:
        compact["owner_route_hints"] = hints[:8]
    return compact


def build_generated_state_drainer_status(
    repo_root: Path,
    *,
    owner_ids: Sequence[str] | None = None,
    status_map: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    requested = {str(owner_id).strip() for owner_id in (owner_ids or []) if str(owner_id).strip()}
    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    projection_rows: list[dict[str, Any]] = []
    checks: dict[str, Any] = {}
    if not requested or WORK_LEDGER_OWNER_ID in requested:
        work_rows, work_check = _work_ledger_projection_rows(repo_root, status_map)
        projection_rows.extend(work_rows)
        checks[WORK_LEDGER_OWNER_ID] = work_check
    if not requested or TASK_LEDGER_OWNER_ID in requested:
        task_rows, task_check = _task_ledger_projection_rows(repo_root, status_map)
        projection_rows.extend(task_rows)
        checks[TASK_LEDGER_OWNER_ID] = task_check
    if SYSTEM_ATLAS_OWNER_ID in requested:
        atlas_rows, atlas_check = _registered_projection_rows(repo_root, status_map, SYSTEM_ATLAS_OWNER_ID)
        projection_rows.extend(atlas_rows)
        checks[SYSTEM_ATLAS_OWNER_ID] = atlas_check
    if requested:
        known = {row.owner_id for row in generated_projection_registry.iter_projection_owners()}
        missing = sorted(requested - known)
    else:
        missing = []
    summary = _projection_summary(projection_rows)
    return {
        "schema": STATUS_SCHEMA,
        "mode": "read_only",
        "repo_root": str(repo_root),
        "owners": _owner_catalog_rows(),
        "missing_owner_ids": missing,
        "selected_owner_ids": sorted(requested) if requested else sorted([WORK_LEDGER_OWNER_ID, TASK_LEDGER_OWNER_ID]),
        "summary": summary,
        "projection_targets": projection_rows,
        "dirty_generated_paths": [row for row in projection_rows if row.get("dirty_status") != "clean"],
        "owner_checks": checks,
        "non_goals": [
            "does_not_commit_generated_state",
            "does_not_rebuild_task_ledger_in_work_ledger_lane",
            "does_not_sweep_annex_or_ambient_workspace_pressure",
            "does_not_patch_kernel_or_phase_state",
        ],
    }


def build_generated_projection_landing_plan(
    repo_root: Path,
    *,
    owner_id: str = WORK_LEDGER_OWNER_ID,
    status_map: Mapping[str, str] | None = None,
    status: Mapping[str, Any] | None = None,
    collect_diff_stat: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    owner = str(owner_id or WORK_LEDGER_OWNER_ID).strip()
    if owner not in SUPPORTED_LANDING_OWNER_IDS:
        return {
            "schema": LANDING_PLAN_SCHEMA,
            "ok": False,
            "owner_id": owner,
            "status": "refused",
            "reason": "unsupported_owner_for_landing_plan",
            "supported_owner_ids": list(SUPPORTED_LANDING_OWNER_IDS),
            "can_apply": False,
            "blocked_by": ["owner_landing_policy_not_implemented"],
        }

    status_map = status_map if status_map is not None else _git_status_map(repo_root)
    status = status or build_generated_state_drainer_status(repo_root, owner_ids=[owner], status_map=status_map)
    projection_rows = [
        row for row in list(status.get("projection_targets") or []) if row.get("owner_id") == owner
    ]
    summary = _projection_summary(projection_rows)
    projection_paths = [str(row.get("generated_path") or "") for row in projection_rows]
    source_paths = _owner_source_paths(repo_root, owner, projection_rows)
    source_paths_to_stage = _dirty_existing_paths(repo_root, source_paths, status_map=status_map)
    source_hashes = {
        str(row.get("family_id") or owner): row.get("source_event_hash")
        for row in projection_rows
        if row.get("source_event_hash")
    }
    projection_hashes = {
        str(row.get("generated_path") or ""): row.get("projection_hash")
        for row in projection_rows
        if row.get("generated_path")
    }
    unique_source_hashes = sorted({str(value) for value in source_hashes.values() if value})
    stale_count = int(summary.get("stale_count") or 0)
    dirty_count = int(summary.get("dirty_count") or 0)
    source_dirty_count = len(source_paths_to_stage)
    projection_paths_to_stage = _dirty_projection_paths(projection_rows)
    source_authority_missing_count = sum(
        1 for row in projection_rows if row.get("freshness_status") == "source_authority_missing"
    )
    owner_checks = status.get("owner_checks") if isinstance(status.get("owner_checks"), Mapping) else {}
    owner_check = owner_checks.get(owner) if isinstance(owner_checks, Mapping) else {}
    source_coupling = (
        owner_check.get("source_coupling")
        if isinstance(owner_check, Mapping) and isinstance(owner_check.get("source_coupling"), Mapping)
        else {}
    )
    source_coupling_status = str(source_coupling.get("status") or "").strip()
    source_coupling_unsettled = (
        owner == SYSTEM_ATLAS_OWNER_ID
        and source_coupling_status == "source_inputs_changed_since_artifact_generation"
    )
    manifest_rel = _landing_manifest_rel(owner)
    manifest_dirty = _dirty_status(str(manifest_rel), status_map) != "clean" or not (repo_root / manifest_rel).exists()
    diff_stat = _projection_diff_stat(
        repo_root,
        projection_rows,
        status_map=status_map,
        collect_numstat=collect_diff_stat,
    )
    if source_authority_missing_count:
        # Orphaned projections: source authority (events.jsonl) is absent on disk
        # while projection artifacts (ledger.json / sign_offs.json / views/*.json) exist.
        # A refresh would fail because there is nothing to project from. The next move
        # is operator-driven: restore events.jsonl (e.g. via audit-recover or git
        # restore) before any landing/settlement attempt. Surface this distinctly so
        # _settlement_action_for_plan returns "blocked" rather than recommending a
        # refresh that cannot succeed.
        required_next = (
            f"./repo-python tools/meta/factory/task_ledger_apply.py audit-recover  "
            f"# restore {task_ledger_events.EVENTS_REL} before retrying"
        )
        blocked_by = ["source_authority_missing"]
        status_text = "source_authority_missing"
    elif source_coupling_unsettled:
        required_next = _command_text(generated_projection_registry.get_projection_owner(owner).check_command)
        blocked_by = ["source_coupling_not_settled"]
        status_text = "source_coupling_unsettled"
    elif stale_count:
        refresh_action = _owner_repair_action(owner)
        required_next = f"./repo-python tools/meta/control/generated_state_drainer.py apply --only {refresh_action}"
        blocked_by = ["projection_not_fresh"]
        status_text = "refresh_required"
    elif dirty_count or source_dirty_count or manifest_dirty:
        required_next = (
            "./repo-python tools/meta/control/generated_state_drainer.py land "
            f"--owner-id {owner} --mode append-exempt --dry-run"
        )
        blocked_by = []
        status_text = "append_exempt_manifest_available"
    else:
        required_next = "none"
        blocked_by = []
        status_text = "already_landed"

    result = {
        "schema": LANDING_PLAN_SCHEMA,
        "ok": True,
        "owner_id": owner,
        "status": status_text,
        "source_authority": _owner_source_authority_label(owner),
        "source_authority_paths": source_paths,
        "source_authority_paths_to_stage": source_paths_to_stage,
        "projection_paths_to_stage": projection_paths_to_stage,
        "dirty_path_summary": {
            "source_authority_dirty_count": len(source_paths_to_stage),
            "source_authority_clean_count": max(len(source_paths) - len(source_paths_to_stage), 0),
            "projection_dirty_count": len(projection_paths_to_stage),
            "projection_clean_count": max(len(projection_paths) - len(projection_paths_to_stage), 0),
            "landing_manifest_dirty": manifest_dirty,
        },
        "owner_bundle_rationale": (
            "source_authority_paths and projection_paths name the owner authority bundle; "
            "source_authority_paths_to_stage and projection_paths_to_stage are the exact "
            "dirty subset for this owner. Clean bundle paths are context, not staging work."
        ),
        "source_event_hash": unique_source_hashes[0] if len(unique_source_hashes) == 1 else None,
        "source_event_hashes": source_hashes,
        "source_path_hashes": _path_hashes(repo_root, source_paths),
        "projection_paths": projection_paths,
        "projection_hashes": projection_hashes,
        "freshness_status": summary.get("status"),
        "dirty_status": "dirty" if dirty_count or source_dirty_count or manifest_dirty else "clean",
        "source_dirty_status": "dirty" if source_dirty_count else "clean",
        "diff_stat": diff_stat,
        "bloat_class": _owner_bloat_class(owner),
        "push_gate_status": "watch" if diff_stat.get("review_status") == "watch" else "clear",
        "landing_policy": "serial_drainer_only",
        "normal_agent_commit_allowed": False,
        "safe_to_commit_by_agent": False,
        "self_invalidating_if_eventful": True,
        "self_invalidation_reason": (
            "Work Ledger indexes are derived from codex/ledger/*/work_ledger.jsonl; "
            "a normal Work Ledger event for projection landing changes the source event "
            "hash after projection refresh."
            if owner == WORK_LEDGER_OWNER_ID
            else (
                "Task Ledger projections are derived from state/task_ledger/events.jsonl; "
                "a normal Task Ledger event for projection landing changes the source event "
                "hash after projection refresh."
                if owner == TASK_LEDGER_OWNER_ID
                else "System Atlas projections are derived from registry-declared source authorities; "
                "the owner builder must settle source-coupling drift before projection landing."
            )
        ),
        "scoped_commit_directly_appends_work_ledger_event": False,
        "scoped_commit_directly_appends_task_ledger_event": False,
        "normal_work_ledger_event_after_refresh_allowed": False if owner == WORK_LEDGER_OWNER_ID else None,
        "normal_task_ledger_event_after_refresh_allowed": False if owner == TASK_LEDGER_OWNER_ID else None,
        "normal_system_atlas_event_after_refresh_allowed": False if owner == SYSTEM_ATLAS_OWNER_ID else None,
        "append_exempt_policy_verified": True,
        "marker_epoch_policy_verified": False,
        "recommended_mode": "append_exempt_projection_landing",
        "landing_manifest_path": str(manifest_rel),
        "can_apply": not stale_count and not source_coupling_unsettled,
        "blocked_by": blocked_by,
        "required_next_command": required_next,
        "status_ref": {
            "schema": status.get("schema"),
            "summary": summary,
        },
    }
    if source_coupling_unsettled:
        result["source_coupling"] = _compact_source_coupling(source_coupling)
        result["source_coupling_owner_route_hints"] = _source_coupling_route_hints(source_coupling)
        result["owner_handoff_class"] = "source_coupling_source_owner_handoff"
        result["required_owner_resolution"] = (
            "Settle or claim the changed System Atlas source inputs before refreshing generated Atlas outputs."
        )
    return result


def build_generated_projection_landing_manifest(
    repo_root: Path,
    *,
    plan: Mapping[str, Any] | None = None,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    landing_plan = dict(plan or build_generated_projection_landing_plan(repo_root))
    owner = str(landing_plan.get("owner_id") or WORK_LEDGER_OWNER_ID)
    source_paths = [str(path) for path in landing_plan.get("source_authority_paths") or []]
    source_paths_to_stage = [str(path) for path in landing_plan.get("source_authority_paths_to_stage") or []]
    projection_paths = [str(path) for path in landing_plan.get("projection_paths") or []]
    event_name = _owner_tool_label(owner)
    manifest: dict[str, Any] = {
        "schema": LANDING_MANIFEST_SCHEMA,
        "owner_id": owner,
        "source_authority": landing_plan.get("source_authority"),
        "source_authority_paths": source_paths,
        "source_authority_paths_included": source_paths_to_stage,
        "source_inclusion_reason": (
            f"Dirty {event_name} source event logs are included because the refreshed projections "
            f"summarize them; no {event_name} event is appended after projection refresh."
        ),
        "source_event_hashes": landing_plan.get("source_event_hashes") or {},
        "source_path_hashes": landing_plan.get("source_path_hashes") or {},
        "projection_paths": projection_paths,
        "projection_hashes": landing_plan.get("projection_hashes") or {},
        "diff_stat": landing_plan.get("diff_stat") or {},
        "landing_mode": "append_exempt_projection_landing",
        "append_exempt_reason": landing_plan.get("self_invalidation_reason"),
        "normal_source_event_after_refresh_allowed": False,
        "created_by_tool": "generated_state_drainer",
        "manifest_path": str(_landing_manifest_rel(owner)),
        "commit_hash": commit_hash,
    }
    if owner == WORK_LEDGER_OWNER_ID:
        manifest["normal_work_ledger_event_after_refresh_allowed"] = False
    if owner == TASK_LEDGER_OWNER_ID:
        manifest["normal_task_ledger_event_after_refresh_allowed"] = False
    if owner == SYSTEM_ATLAS_OWNER_ID:
        manifest["normal_system_atlas_event_after_refresh_allowed"] = False
    return manifest


def _unsupported_landing_payload(owner_id: str, *, dry_run: bool) -> dict[str, Any]:
    return {
        "schema": LANDING_SCHEMA,
        "ok": False,
        "dry_run": bool(dry_run),
        "owner_id": owner_id,
        "status": "refused",
        "reason": "unsupported_owner_for_landing",
        "supported_owner_ids": list(SUPPORTED_LANDING_OWNER_IDS),
    }


def land_generated_projection_bundle(
    repo_root: Path,
    *,
    owner_id: str = WORK_LEDGER_OWNER_ID,
    mode: str = APPEND_EXEMPT_LANDING_MODE,
    dry_run: bool = False,
    landing_plan: Mapping[str, Any] | None = None,
    commit_func: Callable[..., Mapping[str, Any]] | None = None,
    work_ledger_session_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    owner = str(owner_id or WORK_LEDGER_OWNER_ID).strip()
    landing_mode = str(mode or "").strip()
    if owner not in SUPPORTED_LANDING_OWNER_IDS:
        return _unsupported_landing_payload(owner, dry_run=dry_run)
    if landing_mode != APPEND_EXEMPT_LANDING_MODE:
        return {
            "schema": LANDING_SCHEMA,
            "ok": False,
            "dry_run": bool(dry_run),
            "owner_id": owner,
            "status": "refused",
            "reason": "unsupported_landing_mode",
            "supported_modes": [APPEND_EXEMPT_LANDING_MODE],
        }

    _emit_progress(
        progress_callback,
        surface="landing",
        event="start",
        owner_id=owner,
        dry_run=bool(dry_run),
        mode=landing_mode,
    )
    plan_started = time.perf_counter()
    plan = (
        dict(landing_plan)
        if landing_plan is not None and str(landing_plan.get("owner_id") or "").strip() == owner
        else build_generated_projection_landing_plan(repo_root, owner_id=owner)
    )
    _emit_progress(
        progress_callback,
        surface="landing",
        event="landing_plan_ready",
        owner_id=owner,
        status=plan.get("status"),
        dirty_status=plan.get("dirty_status"),
        source_dirty_status=plan.get("source_dirty_status"),
        wall_ms=round((time.perf_counter() - plan_started) * 1000.0, 3),
        reused_plan=bool(landing_plan is not None),
    )
    if plan.get("status") == "refresh_required" and not dry_run:
        refresh_started = time.perf_counter()
        _emit_progress(
            progress_callback,
            surface="landing",
            event="refresh_start",
            owner_id=owner,
            status=plan.get("status"),
        )
        if owner == WORK_LEDGER_OWNER_ID:
            work_ledger.project_all(repo_root)
        elif owner == TASK_LEDGER_OWNER_ID:
            task_ledger_events.rebuild_projections(repo_root)
        else:
            owner_row = generated_projection_registry.get_projection_owner(owner)
            proc = subprocess.run(
                [str(part) for part in owner_row.repair_command],
                cwd=repo_root,
                check=False,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            if proc.returncode != 0:
                return {
                    "schema": LANDING_SCHEMA,
                    "ok": False,
                    "dry_run": False,
                    "owner_id": owner,
                    "status": "failed",
                    "reason": "owner_repair_command_failed",
                    "returncode": proc.returncode,
                    "stdout": proc.stdout,
                    "stderr": proc.stderr,
                    "plan": plan,
                }
        plan = build_generated_projection_landing_plan(repo_root, owner_id=owner)
        _emit_progress(
            progress_callback,
            surface="landing",
            event="refresh_done",
            owner_id=owner,
            status=plan.get("status"),
            dirty_status=plan.get("dirty_status"),
            wall_ms=round((time.perf_counter() - refresh_started) * 1000.0, 3),
        )
    if plan.get("status") == "refresh_required":
        return {
            "schema": LANDING_SCHEMA,
            "ok": False,
            "dry_run": bool(dry_run),
            "owner_id": owner,
            "status": "refresh_required",
            "blocked_by": plan.get("blocked_by") or ["projection_not_fresh"],
            "required_next_command": plan.get("required_next_command"),
            "plan": plan,
        }
    if not plan.get("can_apply"):
        return {
            "schema": LANDING_SCHEMA,
            "ok": False,
            "dry_run": bool(dry_run),
            "owner_id": owner,
            "status": "refused",
            "reason": "landing_plan_not_apply_safe",
            "blocked_by": plan.get("blocked_by") or [],
            "plan": plan,
        }

    manifest_started = time.perf_counter()
    manifest = build_generated_projection_landing_manifest(repo_root, plan=plan)
    _emit_progress(
        progress_callback,
        surface="landing",
        event="manifest_ready",
        owner_id=owner,
        projection_path_count=len(plan.get("projection_paths") or []),
        wall_ms=round((time.perf_counter() - manifest_started) * 1000.0, 3),
    )
    status_started = time.perf_counter()
    status_map = _git_status_map(repo_root)
    projection_paths_to_stage = _dirty_existing_paths(
        repo_root,
        [str(path) for path in plan.get("projection_paths") or []],
        status_map=status_map,
    )
    paths_to_stage = sorted(
        {
            *[str(path) for path in plan.get("source_authority_paths_to_stage") or []],
            *projection_paths_to_stage,
            str(_landing_manifest_rel(owner)),
        }
    )
    _emit_progress(
        progress_callback,
        surface="landing",
        event="paths_selected",
        owner_id=owner,
        source_stage_path_count=len(plan.get("source_authority_paths_to_stage") or []),
        projection_stage_path_count=len(projection_paths_to_stage),
        total_path_count=len(paths_to_stage),
        wall_ms=round((time.perf_counter() - status_started) * 1000.0, 3),
    )
    dry_payload = {
        "schema": LANDING_SCHEMA,
        "ok": True,
        "dry_run": True,
        "owner_id": owner,
        "status": "would_land" if plan.get("dirty_status") == "dirty" else "already_landed",
        "mode": landing_mode,
        "landing_manifest_path": str(_landing_manifest_rel(owner)),
        "paths_to_stage": paths_to_stage,
        "manifest": manifest,
        "plan": plan,
        "normal_source_event_after_refresh_allowed": False,
    }
    if owner == WORK_LEDGER_OWNER_ID:
        dry_payload["normal_work_ledger_event_after_refresh_allowed"] = False
    if owner == TASK_LEDGER_OWNER_ID:
        dry_payload["normal_task_ledger_event_after_refresh_allowed"] = False
    if owner == SYSTEM_ATLAS_OWNER_ID:
        dry_payload["normal_system_atlas_event_after_refresh_allowed"] = False
    if dry_run:
        _emit_progress(
            progress_callback,
            surface="landing",
            event="done",
            owner_id=owner,
            status=dry_payload["status"],
            commit_hash=None,
        )
        return dry_payload
    if plan.get("dirty_status") != "dirty":
        _emit_progress(
            progress_callback,
            surface="landing",
            event="done",
            owner_id=owner,
            status="already_landed",
            commit_hash=None,
        )
        return {
            **dry_payload,
            "dry_run": False,
            "status": "already_landed",
        }

    manifest_path = repo_root / _landing_manifest_rel(owner)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    commit_plan_started = time.perf_counter()
    status_map = _git_status_map(repo_root)
    paths_to_commit = _head_changed_existing_paths(repo_root, paths_to_stage, status_map=status_map)
    _emit_progress(
        progress_callback,
        surface="landing",
        event="commit_paths_selected",
        owner_id=owner,
        declared_path_count=len(paths_to_stage),
        commit_path_count=len(paths_to_commit),
        wall_ms=round((time.perf_counter() - commit_plan_started) * 1000.0, 3),
    )
    if not paths_to_commit:
        refreshed_index_paths = _refresh_index_only_projection_residue(
            repo_root,
            paths_to_stage,
            status_map=status_map,
        )
        _emit_progress(
            progress_callback,
            surface="landing",
            event="done",
            owner_id=owner,
            status="already_landed",
            commit_hash=None,
        )
        return {
            **dry_payload,
            "dry_run": False,
            "status": "already_landed",
            "paths_to_stage": [],
            "paths_index_refreshed": refreshed_index_paths,
            **(
                {"reason": "index_only_projection_residue_refreshed"}
                if refreshed_index_paths
                else {}
            ),
        }
    try:
        if commit_func is None:
            from tools.meta.control.scoped_commit import perform_scoped_commit

            commit_callable: Callable[..., Mapping[str, Any]] = perform_scoped_commit
        else:
            commit_callable = commit_func

        commit_started = time.perf_counter()
        _emit_progress(
            progress_callback,
            surface="landing",
            event="commit_start",
            owner_id=owner,
            path_count=len(paths_to_commit),
        )
        commit_result = commit_callable(
            repo_root=repo_root,
            paths=paths_to_commit,
            message=f"Land {_owner_tool_label(owner)} projections append-exempt",
            allow_untracked=True,
            allow_multi_hunk_full_paths=True,
            collect_full_path_hunk_counts=False,
            work_ledger_session_id=work_ledger_session_id,
        )
        _emit_progress(
            progress_callback,
            surface="landing",
            event="commit_done",
            owner_id=owner,
            commit_hash=commit_result.get("new_commit"),
            path_count=len(commit_result.get("changed_paths") or []),
            wall_ms=round((time.perf_counter() - commit_started) * 1000.0, 3),
        )
    except Exception as exc:
        return {
            "schema": LANDING_SCHEMA,
            "ok": False,
            "dry_run": False,
            "owner_id": owner,
            "status": "failed",
            "reason": "private_index_commit_failed",
            "error": str(exc),
            "paths_to_stage": paths_to_commit,
            "declared_paths_to_stage": paths_to_stage,
        }
    refreshed_index_paths = _refresh_index_only_projection_residue(repo_root, paths_to_stage)
    _emit_progress(
        progress_callback,
        surface="landing",
        event="done",
        owner_id=owner,
        status="landed",
        commit_hash=commit_result.get("new_commit"),
        index_refreshed_path_count=len(refreshed_index_paths),
    )
    result = {
        "schema": LANDING_SCHEMA,
        "ok": True,
        "dry_run": False,
        "owner_id": owner,
        "status": "landed",
        "mode": landing_mode,
        "commit_hash": commit_result.get("new_commit"),
        "paths_staged": commit_result.get("changed_paths"),
        "landing_manifest_path": str(_landing_manifest_rel(owner)),
        "normal_source_event_after_refresh_allowed": False,
    }
    if refreshed_index_paths:
        result["paths_index_refreshed"] = refreshed_index_paths
    if owner == WORK_LEDGER_OWNER_ID:
        result["normal_work_ledger_event_after_refresh_allowed"] = False
    if owner == TASK_LEDGER_OWNER_ID:
        result["normal_task_ledger_event_after_refresh_allowed"] = False
    if owner == SYSTEM_ATLAS_OWNER_ID:
        result["normal_system_atlas_event_after_refresh_allowed"] = False
    return result


def _settlement_action_for_plan(plan: Mapping[str, Any]) -> str:
    if not plan.get("ok", True):
        return "blocked"
    status = str(plan.get("status") or "").strip()
    if status == "already_landed":
        return "none"
    if status == "append_exempt_manifest_available" and plan.get("can_apply"):
        return "land_append_exempt"
    if status == "refresh_required":
        return "refresh_then_land_append_exempt"
    return "blocked"


def _settlement_owner_row(plan: Mapping[str, Any]) -> dict[str, Any]:
    owner_id = str(plan.get("owner_id") or "").strip()
    required_action = _settlement_action_for_plan(plan)
    row = {
        "_landing_plan": dict(plan),
        "owner_id": owner_id,
        "status": plan.get("status"),
        "freshness_status": plan.get("freshness_status"),
        "dirty_status": plan.get("dirty_status"),
        "source_dirty_status": plan.get("source_dirty_status"),
        "can_apply": bool(plan.get("can_apply")) or required_action == "refresh_then_land_append_exempt",
        "blocked_by": list(plan.get("blocked_by") or []),
        "required_action": required_action,
        "owner_required_next_command": plan.get("required_next_command"),
        "required_next_command": (
            "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
            if required_action in {"land_append_exempt", "refresh_then_land_append_exempt"}
            else plan.get("required_next_command")
        ),
        "landing_manifest_path": plan.get("landing_manifest_path"),
        "normal_source_event_after_refresh_allowed": False,
        "path_count": len(plan.get("projection_paths") or []),
        "diff_stat": plan.get("diff_stat") or {},
        "path_bundle": {
            "source_authority_paths": list(plan.get("source_authority_paths") or []),
            "source_authority_paths_to_stage": list(plan.get("source_authority_paths_to_stage") or []),
            "projection_paths": list(plan.get("projection_paths") or []),
            "projection_paths_to_stage": list(plan.get("projection_paths_to_stage") or []),
            "landing_manifest_path": plan.get("landing_manifest_path"),
            "dirty_path_summary": dict(plan.get("dirty_path_summary") or {}),
            "owner_bundle_rationale": plan.get("owner_bundle_rationale"),
        },
    }
    if owner_id == WORK_LEDGER_OWNER_ID:
        row["normal_work_ledger_event_after_refresh_allowed"] = False
    if owner_id == TASK_LEDGER_OWNER_ID:
        row["normal_task_ledger_event_after_refresh_allowed"] = False
    if owner_id == SYSTEM_ATLAS_OWNER_ID:
        row["normal_system_atlas_event_after_refresh_allowed"] = False
    source_coupling = plan.get("source_coupling")
    if isinstance(source_coupling, Mapping):
        row["source_coupling"] = dict(source_coupling)
        row["source_coupling_owner_route_hints"] = list(plan.get("source_coupling_owner_route_hints") or [])
        row["owner_handoff_class"] = plan.get("owner_handoff_class")
        row["required_owner_resolution"] = plan.get("required_owner_resolution")
    return row


def _public_settlement_plan(plan: Mapping[str, Any]) -> dict[str, Any]:
    public_plan = dict(plan)
    public_owners: list[Any] = []
    for owner in plan.get("owners") or []:
        if isinstance(owner, Mapping):
            public_owners.append({key: value for key, value in owner.items() if key != "_landing_plan"})
        else:
            public_owners.append(owner)
    public_plan["owners"] = public_owners
    return public_plan


def _settlement_owner_ids(owner_ids: Sequence[str] | None = None) -> list[str]:
    requested = [str(owner_id).strip() for owner_id in (owner_ids or []) if str(owner_id).strip()]
    if not requested:
        return list(SUPPORTED_SETTLEMENT_OWNER_IDS)
    seen: set[str] = set()
    ordered: list[str] = []
    for owner_id in requested:
        if owner_id in seen:
            continue
        seen.add(owner_id)
        ordered.append(owner_id)
    return ordered


def _fast_settlement_owner_row(
    repo_root: Path,
    *,
    owner_id: str,
    status_map: Mapping[str, str],
) -> dict[str, Any]:
    if owner_id == TASK_LEDGER_OWNER_ID:
        source_paths = _task_ledger_source_artifact_paths(repo_root)
        source_authority = "state/task_ledger/events.jsonl"
        projection_paths = _task_ledger_projection_artifact_paths(repo_root)
        bloat_class = "task_ledger_event_or_projection"
    elif owner_id == WORK_LEDGER_OWNER_ID:
        source_paths = _work_ledger_source_artifact_paths(repo_root)
        source_authority = "codex/ledger/*/work_ledger.jsonl"
        projection_paths = _work_ledger_projection_artifact_paths(repo_root)
        bloat_class = "work_ledger_event_or_projection"
    else:
        source_paths = _registry_source_authority_paths(repo_root, owner_id)
        source_authority = "generated_projection_registry.source_authorities"
        projection_paths = _registry_artifact_paths(repo_root, owner_id)
        bloat_class = f"{owner_id}_event_or_projection"

    manifest_rel = str(_landing_manifest_rel(owner_id))
    source_dirty = _dirty_existing_paths(repo_root, source_paths, status_map=status_map)
    projection_dirty = _dirty_existing_paths(repo_root, projection_paths, status_map=status_map)
    manifest_dirty = _dirty_status(manifest_rel, status_map) != "clean" or (
        owner_id != SYSTEM_ATLAS_OWNER_ID and not (repo_root / manifest_rel).exists()
    )
    required_task_source_missing = (
        owner_id == TASK_LEDGER_OWNER_ID and not (repo_root / task_ledger_events.EVENTS_REL).exists()
    )
    source_missing_with_projections = bool(projection_paths) and (
        required_task_source_missing
        or (owner_id in {WORK_LEDGER_OWNER_ID, TASK_LEDGER_OWNER_ID} and not source_paths)
    )
    if source_missing_with_projections:
        status_text = "source_authority_missing"
        dirty_status = "dirty" if projection_dirty or manifest_dirty else "clean"
        source_dirty_status = "missing"
        required_action = "blocked"
        can_apply = False
        blocked_by = ["source_authority_missing"]
        required_next = (
            "./repo-python tools/meta/control/generated_state_drainer.py "
            f"settlement-plan --owner-id {owner_id} --full-diff-stat"
        )
    elif source_dirty and not projection_dirty:
        status_text = "refresh_required"
        dirty_status = "dirty"
        source_dirty_status = "dirty"
        required_action = "refresh_then_land_append_exempt"
        can_apply = True
        blocked_by = []
        required_next = "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
    elif source_dirty or projection_dirty or manifest_dirty:
        status_text = "append_exempt_manifest_available"
        dirty_status = "dirty"
        source_dirty_status = "dirty" if source_dirty else "clean"
        required_action = "land_append_exempt"
        can_apply = True
        blocked_by = []
        required_next = "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
    else:
        status_text = "already_landed"
        dirty_status = "clean"
        source_dirty_status = "clean"
        required_action = "none"
        can_apply = True
        blocked_by = []
        required_next = "none"

    diff_stat = _projection_diff_stat(
        repo_root,
        [
            {
                "generated_path": path,
            }
            for path in projection_paths
        ],
        status_map=status_map,
        collect_numstat=False,
    )
    row = {
        "owner_id": owner_id,
        "status": status_text,
        "freshness_status": "not_checked_cached_status_only",
        "dirty_status": dirty_status,
        "source_dirty_status": source_dirty_status,
        "can_apply": can_apply,
        "blocked_by": blocked_by,
        "required_action": required_action,
        "owner_required_next_command": required_next,
        "required_next_command": required_next,
        "landing_manifest_path": manifest_rel,
        "normal_source_event_after_refresh_allowed": False,
        "path_count": len(projection_paths),
        "diff_stat": diff_stat,
        "path_bundle": {
            "source_authority_paths": source_paths,
            "source_authority_paths_to_stage": source_dirty,
            "projection_paths": projection_paths,
            "projection_paths_to_stage": projection_dirty,
            "landing_manifest_path": manifest_rel,
            "dirty_path_summary": {
                "source_authority_dirty_count": len(source_dirty),
                "source_authority_clean_count": max(len(source_paths) - len(source_dirty), 0),
                "projection_dirty_count": len(projection_dirty),
                "projection_clean_count": max(len(projection_paths) - len(projection_dirty), 0),
                "landing_manifest_dirty": manifest_dirty,
            },
            "owner_bundle_rationale": (
                "source_authority_paths and projection_paths name the owner authority bundle; "
                "source_authority_paths_to_stage and projection_paths_to_stage are the exact "
                "dirty subset for this owner. Clean bundle paths are context, not staging work."
            ),
        },
        "source_authority": source_authority,
        "source_authority_paths": source_paths,
        "source_authority_paths_to_stage": source_dirty,
        "projection_paths_to_stage": projection_dirty,
        "projection_paths": projection_paths,
        "projection_hashes": {},
        "bloat_class": bloat_class,
        "planning_mode": "cached_git_status",
    }
    if owner_id == WORK_LEDGER_OWNER_ID:
        row["normal_work_ledger_event_after_refresh_allowed"] = False
    if owner_id == TASK_LEDGER_OWNER_ID:
        row["normal_task_ledger_event_after_refresh_allowed"] = False
    if owner_id == SYSTEM_ATLAS_OWNER_ID:
        row["normal_system_atlas_event_after_refresh_allowed"] = False
    return row


def build_generated_projection_settlement_fast_plan(
    repo_root: Path,
    *,
    owner_ids: Sequence[str] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    requested_owner_ids = _settlement_owner_ids(owner_ids)
    status_map = _git_status_map(repo_root)
    owners: list[dict[str, Any]] = []
    unsupported_owner_ids: list[str] = []
    for owner_id in requested_owner_ids:
        if owner_id not in SUPPORTED_LANDING_OWNER_IDS:
            unsupported_owner_ids.append(owner_id)
            owners.append(
                {
                    "owner_id": owner_id,
                    "status": "refused",
                    "freshness_status": None,
                    "dirty_status": None,
                    "source_dirty_status": None,
                    "can_apply": False,
                    "blocked_by": ["owner_landing_policy_not_implemented"],
                    "required_action": "blocked",
                    "required_next_command": "none",
                    "landing_manifest_path": None,
                    "normal_source_event_after_refresh_allowed": False,
                    "path_count": 0,
                    "diff_stat": {},
                    "planning_mode": "cached_git_status",
                }
            )
            continue
        owners.append(_fast_settlement_owner_row(repo_root, owner_id=owner_id, status_map=status_map))

    refresh_required = [row["owner_id"] for row in owners if row.get("required_action") == "refresh_then_land_append_exempt"]
    blocked = [row["owner_id"] for row in owners if row.get("required_action") == "blocked"]
    dirty = [
        row["owner_id"]
        for row in owners
        if row.get("required_action") in {"land_append_exempt", "refresh_then_land_append_exempt"}
    ]
    if blocked:
        status = "blocked"
    elif dirty:
        status = "settlement_required"
    else:
        status = "clean"
    blocked_by: list[str] = []
    if unsupported_owner_ids:
        blocked_by.append("unsupported_owner_id")
    if blocked:
        blocked_by.append("owner_settlement_blocked")
    can_settle = status in {"clean", "settlement_required"}
    return {
        "schema": SETTLEMENT_PLAN_SCHEMA,
        "ok": not blocked,
        "status": status,
        "planning_mode": "cached_git_status",
        "authority_level": "cached_status_only",
        "full_authority_command": "./repo-python tools/meta/control/generated_state_drainer.py settlement-plan --full-diff-stat",
        "supported_owner_ids": list(SUPPORTED_LANDING_OWNER_IDS),
        "settlement_order": requested_owner_ids,
        "owners": owners,
        "dirty_owner_count": len(dirty),
        "refresh_required_owner_count": len(refresh_required),
        "blocked_owner_count": len(blocked),
        "can_settle": can_settle,
        "blocked_by": blocked_by,
        "required_next_command": (
            "none"
            if status == "clean"
            else "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run --fast-plan"
            if status == "settlement_required"
            else "repair blocked projection owner before settlement"
        ),
        "eventful_closeout_allowed_after_settlement": False,
        "normal_source_event_after_refresh_allowed": False,
    }


def build_generated_projection_settlement_plan(
    repo_root: Path,
    *,
    owner_ids: Sequence[str] | None = None,
    collect_diff_stat: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    requested_owner_ids = _settlement_owner_ids(owner_ids)
    owners: list[dict[str, Any]] = []
    unsupported_owner_ids: list[str] = []
    supported_requested_owner_ids = [
        owner_id for owner_id in requested_owner_ids if owner_id in SUPPORTED_LANDING_OWNER_IDS
    ]
    status_map = _git_status_map(repo_root)
    shared_status_owner_ids = [
        owner_id for owner_id in supported_requested_owner_ids if owner_id != SYSTEM_ATLAS_OWNER_ID
    ]
    shared_status = (
        build_generated_state_drainer_status(
            repo_root,
            owner_ids=shared_status_owner_ids,
            status_map=status_map,
        )
        if shared_status_owner_ids
        else None
    )
    for owner_id in requested_owner_ids:
        if owner_id not in SUPPORTED_LANDING_OWNER_IDS:
            unsupported_owner_ids.append(owner_id)
            owners.append(
                {
                    "owner_id": owner_id,
                    "status": "refused",
                    "freshness_status": None,
                    "dirty_status": None,
                    "source_dirty_status": None,
                    "can_apply": False,
                    "blocked_by": ["owner_landing_policy_not_implemented"],
                    "required_action": "blocked",
                    "required_next_command": "none",
                    "landing_manifest_path": None,
                    "normal_source_event_after_refresh_allowed": False,
                    "path_count": 0,
                    "diff_stat": {},
                }
            )
            continue
        owners.append(
            _settlement_owner_row(
                build_generated_projection_landing_plan(
                    repo_root,
                    owner_id=owner_id,
                    status_map=status_map,
                    status=None if owner_id == SYSTEM_ATLAS_OWNER_ID else shared_status,
                    collect_diff_stat=collect_diff_stat,
                )
            )
        )

    refresh_required = [row["owner_id"] for row in owners if row.get("required_action") == "refresh_then_land_append_exempt"]
    blocked = [row["owner_id"] for row in owners if row.get("required_action") == "blocked"]
    dirty = [
        row["owner_id"]
        for row in owners
        if row.get("required_action") in {"land_append_exempt", "refresh_then_land_append_exempt"}
    ]
    if blocked:
        status = "blocked"
    elif dirty:
        status = "settlement_required"
    else:
        status = "clean"
    blocked_by: list[str] = []
    if unsupported_owner_ids:
        blocked_by.append("unsupported_owner_id")
    if blocked:
        blocked_by.append("owner_settlement_blocked")
    can_settle = status in {"clean", "settlement_required"}
    return {
        "schema": SETTLEMENT_PLAN_SCHEMA,
        "ok": not blocked,
        "status": status,
        "supported_owner_ids": list(SUPPORTED_LANDING_OWNER_IDS),
        "settlement_order": requested_owner_ids,
        "owners": owners,
        "dirty_owner_count": len(dirty),
        "refresh_required_owner_count": len(refresh_required),
        "blocked_owner_count": len(blocked),
        "can_settle": can_settle,
        "blocked_by": blocked_by,
        "required_next_command": (
            "none"
            if status == "clean"
            else "./repo-python tools/meta/control/generated_state_drainer.py settle --dry-run"
            if status == "settlement_required"
            else "repair blocked projection owner before settlement"
        ),
        "eventful_closeout_allowed_after_settlement": False,
        "normal_source_event_after_refresh_allowed": False,
    }


def _settlement_residual_owner_rows(plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for owner in plan.get("owners") or []:
        if owner.get("required_action") not in {"land_append_exempt", "refresh_then_land_append_exempt"}:
            continue
        diff_stat = owner.get("diff_stat") if isinstance(owner.get("diff_stat"), Mapping) else {}
        rows.append(
            {
                "owner_id": owner.get("owner_id"),
                "status": owner.get("status"),
                "required_action": owner.get("required_action"),
                "dirty_status": owner.get("dirty_status"),
                "source_dirty_status": owner.get("source_dirty_status"),
                "landing_manifest_path": owner.get("landing_manifest_path"),
                "path_count": owner.get("path_count"),
                "diff_path_count": diff_stat.get("path_count"),
                "total_changed_lines": diff_stat.get("total_changed_lines"),
            }
        )
    return rows


def _settlement_residual_signature(plan: Mapping[str, Any]) -> str | None:
    rows: list[dict[str, Any]] = []
    for owner in plan.get("owners") or []:
        if owner.get("required_action") not in {"land_append_exempt", "refresh_then_land_append_exempt"}:
            continue
        path_bundle = owner.get("path_bundle") if isinstance(owner.get("path_bundle"), Mapping) else {}
        diff_stat = owner.get("diff_stat") if isinstance(owner.get("diff_stat"), Mapping) else {}
        rows.append(
            {
                "owner_id": owner.get("owner_id"),
                "status": owner.get("status"),
                "freshness_status": owner.get("freshness_status"),
                "dirty_status": owner.get("dirty_status"),
                "source_dirty_status": owner.get("source_dirty_status"),
                "required_action": owner.get("required_action"),
                "blocked_by": list(owner.get("blocked_by") or []),
                "source_authority_paths_to_stage": list(path_bundle.get("source_authority_paths_to_stage") or []),
                "projection_paths": list(path_bundle.get("projection_paths") or []),
                "landing_manifest_path": path_bundle.get("landing_manifest_path") or owner.get("landing_manifest_path"),
                "diff_path_count": diff_stat.get("path_count"),
                "total_changed_lines": diff_stat.get("total_changed_lines"),
            }
        )
    if not rows:
        return None
    return _json_hash(rows)


def _settlement_progress_summary(owner_results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    commits = [str(row.get("commit_hash")) for row in owner_results if row.get("commit_hash")]
    return {
        "commit_count": len(commits),
        "commit_hashes": commits,
        "landed_count": sum(1 for row in owner_results if row.get("result_status") == "landed"),
        "already_landed_count": sum(1 for row in owner_results if row.get("result_status") == "already_landed"),
    }


def _settlement_owner_path_receipt(
    owner: Mapping[str, Any],
    result: Mapping[str, Any],
) -> dict[str, Any]:
    path_bundle = owner.get("path_bundle") if isinstance(owner.get("path_bundle"), Mapping) else {}
    source_authority_paths = sorted(
        dict.fromkeys(
            str(path)
            for path in (
                owner.get("source_authority_paths")
                or path_bundle.get("source_authority_paths")
                or []
            )
        )
    )
    source_authority_paths_to_stage = sorted(
        dict.fromkeys(
            str(path)
            for path in (
                owner.get("source_authority_paths_to_stage")
                or path_bundle.get("source_authority_paths_to_stage")
                or []
            )
        )
    )
    projection_paths = sorted(
        dict.fromkeys(
            str(path)
            for path in (
                owner.get("projection_paths")
                or path_bundle.get("projection_paths")
                or []
            )
        )
    )
    raw_projection_paths_to_stage = (
        owner.get("projection_paths_to_stage")
        if owner.get("projection_paths_to_stage") is not None
        else path_bundle.get("projection_paths_to_stage")
    )
    projection_paths_to_stage = sorted(
        dict.fromkeys(str(path) for path in (raw_projection_paths_to_stage or []))
    )
    if owner.get("required_action") == "refresh_then_land_append_exempt" and not projection_paths_to_stage:
        projection_paths_to_stage = list(projection_paths)
    if raw_projection_paths_to_stage is None:
        staged_path_set = {
            str(path)
            for path in (result.get("paths_to_stage") or result.get("paths_staged") or [])
            if str(path)
        }
        if owner.get("required_action") == "refresh_then_land_append_exempt":
            projection_paths_to_stage = list(projection_paths)
        else:
            projection_paths_to_stage = [
                path for path in projection_paths if path in staged_path_set
            ]
    landing_manifest_path = str(
        result.get("landing_manifest_path")
        or path_bundle.get("landing_manifest_path")
        or owner.get("landing_manifest_path")
        or ""
    )
    paths_to_stage = [
        str(path)
        for path in (result.get("paths_to_stage") or result.get("paths_staged") or [])
        if str(path)
    ]
    expected_stage_paths = set(source_authority_paths_to_stage) | set(projection_paths_to_stage)
    if landing_manifest_path:
        expected_stage_paths.add(landing_manifest_path)
    missing_expected_stage_paths = sorted(expected_stage_paths - set(paths_to_stage))
    task_ledger_audit_declared = None
    if str(owner.get("owner_id") or "") == TASK_LEDGER_OWNER_ID:
        task_ledger_audit_declared = str(task_ledger_events.EVENTS_AUDIT_REL) in source_authority_paths
    return {
        "paths_to_stage": paths_to_stage,
        "source_authority_paths": source_authority_paths,
        "source_authority_paths_to_stage": source_authority_paths_to_stage,
        "projection_paths": projection_paths,
        "path_bundle": {
            "source_authority_paths": source_authority_paths,
            "source_authority_paths_to_stage": source_authority_paths_to_stage,
            "projection_paths": projection_paths,
            "projection_paths_to_stage": projection_paths_to_stage,
            "landing_manifest_path": landing_manifest_path,
        },
        "owner_bundle_completeness": {
            "source_authority_path_count": len(source_authority_paths),
            "source_authority_stage_path_count": len(source_authority_paths_to_stage),
            "projection_path_count": len(projection_paths),
            "projection_stage_path_count": len(projection_paths_to_stage),
            "landing_manifest_included": bool(landing_manifest_path),
            "all_expected_stage_paths_reported": not missing_expected_stage_paths,
            "missing_expected_stage_paths": missing_expected_stage_paths,
            "task_ledger_audit_journal_declared": task_ledger_audit_declared,
        },
    }


def _resource_lease_surface_status(repo_root: Path) -> dict[str, Any]:
    candidates = [
        repo_root / "tools/meta/control/resource_lease.py",
        repo_root / "state/resource_leases/leases.jsonl",
        repo_root / "state/resource_leases/leases.json",
    ]
    existing = [path for path in candidates if path.exists()]
    if not existing:
        return {
            "status": "unavailable",
            "checked_surfaces": [
                "tools/meta/control/resource_lease.py",
                "state/resource_leases/leases.jsonl",
                "state/resource_leases/leases.json",
            ],
        }
    return {
        "status": "available",
        "surface": str(existing[0].relative_to(repo_root)),
    }


def _settlement_base_controls(repo_root: Path) -> dict[str, Any]:
    return {
        "resource_lease_status": _resource_lease_surface_status(repo_root),
        "duplicate_settlement_guard": {
            "status": "available_via_command_run_singleflight",
            "resource_class": "generated_state",
            "entrypoint": "./repo-python tools/meta/control/generated_state_drainer.py settle",
            "note": "The settle CLI is singleflight-wrapped for duplicate suppression; full resource leases are deferred until a concrete lease substrate exists.",
        },
    }


SETTLEMENT_STEWARDSHIP_SURFACES = [
    "source_bundle_coverage",
    "audit_sidecar_coverage",
    "projection_hygiene",
    "owner_tool_contract",
    "operator_friction_signal",
]


def _settlement_source_bundle_by_owner(plan: Mapping[str, Any]) -> dict[str, Any]:
    bundles: dict[str, Any] = {}
    for owner in plan.get("owners") or []:
        owner_id = str(owner.get("owner_id") or "").strip()
        if not owner_id:
            continue
        path_bundle = owner.get("path_bundle") if isinstance(owner.get("path_bundle"), Mapping) else {}
        source_authority_paths = list(
            owner.get("source_authority_paths")
            or path_bundle.get("source_authority_paths")
            or []
        )
        source_authority_paths_to_stage = list(
            owner.get("source_authority_paths_to_stage")
            or path_bundle.get("source_authority_paths_to_stage")
            or []
        )
        projection_paths = list(owner.get("projection_paths") or path_bundle.get("projection_paths") or [])
        bundles[owner_id] = {
            "source_authority_paths": sorted(dict.fromkeys(str(path) for path in source_authority_paths)),
            "source_authority_paths_to_stage": sorted(
                dict.fromkeys(str(path) for path in source_authority_paths_to_stage)
            ),
            "projection_paths": sorted(dict.fromkeys(str(path) for path in projection_paths)),
            "landing_manifest_path": path_bundle.get("landing_manifest_path")
            or owner.get("landing_manifest_path"),
        }
    return bundles


def _settlement_omitted_audit_or_source_sidecars(
    repo_root: Path,
    plan: Mapping[str, Any],
) -> list[dict[str, Any]]:
    bundles = _settlement_source_bundle_by_owner(plan)
    omissions: list[dict[str, Any]] = []
    if TASK_LEDGER_OWNER_ID not in bundles:
        return omissions
    task_bundle = bundles.get(TASK_LEDGER_OWNER_ID) or {}
    expected_audit = str(task_ledger_events.EVENTS_AUDIT_REL)
    expected_events = str(task_ledger_events.EVENTS_REL)
    task_sources = set(task_bundle.get("source_authority_paths") or [])
    if (repo_root / task_ledger_events.EVENTS_REL).exists() and expected_events not in task_sources:
        omissions.append(
            {
                "owner_id": TASK_LEDGER_OWNER_ID,
                "missing_path": expected_events,
                "source_class": "source_authority",
                "reason": "existing Task Ledger event source was not declared in the settlement source bundle",
            }
        )
    if (repo_root / task_ledger_events.EVENTS_AUDIT_REL).exists() and expected_audit not in task_sources:
        omissions.append(
            {
                "owner_id": TASK_LEDGER_OWNER_ID,
                "missing_path": expected_audit,
                "source_class": "audit_sidecar",
                "reason": "existing Task Ledger audit sidecar was not declared in the settlement source bundle",
            }
        )
    return omissions


def _settlement_blocker_summary(plan: Mapping[str, Any]) -> list[str]:
    blockers = [str(item) for item in (plan.get("blocked_by") or []) if str(item)]
    for owner in plan.get("owners") or []:
        owner_id = str(owner.get("owner_id") or "").strip()
        for blocker in owner.get("blocked_by") or []:
            blocker_text = str(blocker).strip()
            if blocker_text:
                blockers.append(f"{owner_id}:{blocker_text}" if owner_id else blocker_text)
    return sorted(dict.fromkeys(blockers))


def _settlement_stewardship_check(repo_root: Path, plan: Mapping[str, Any]) -> dict[str, Any]:
    source_bundle_by_owner = _settlement_source_bundle_by_owner(plan)
    omitted_sidecars = _settlement_omitted_audit_or_source_sidecars(repo_root, plan)
    residual_owners = _settlement_residual_owner_rows(plan)
    blockers = _settlement_blocker_summary(plan)
    plan_status = str(plan.get("status") or "").strip()
    contract_gap = bool(omitted_sidecars or residual_owners or blockers or plan_status == "blocked")
    lane_results: list[dict[str, Any]] = []
    if omitted_sidecars:
        lane_results.append(
            {
                "lane": "source_bundle_coverage",
                "status": "needs_repair",
                "reason": "one or more existing source or audit sidecars are omitted",
            }
        )
    else:
        lane_results.append(
            {
                "lane": "source_bundle_coverage",
                "status": "checked_no_patch",
                "reason": "declared source bundles include existing source and audit sidecars",
            }
        )
    if residual_owners:
        lane_results.append(
            {
                "lane": "projection_hygiene",
                "status": "needs_reentry",
                "reason": "settlement left projection owners requiring additional action",
            }
        )
    else:
        lane_results.append(
            {
                "lane": "projection_hygiene",
                "status": "checked_no_patch",
                "reason": "settlement plan has no residual owner actions",
            }
        )
    if blockers:
        lane_results.append(
            {
                "lane": "owner_tool_contract",
                "status": "blocked_by_claim_or_policy",
                "reason": "settlement plan reports owner blockers",
                "blocked_by": blockers,
            }
        )
    else:
        lane_results.append(
            {
                "lane": "owner_tool_contract",
                "status": "checked_no_patch",
                "reason": "owner tools declared no settlement blockers",
            }
        )
    lane_results.append(
        {
            "lane": "operator_friction_signal",
            "status": "not_observed_by_tool",
            "reason": "manual operator challenge is external to this settlement tool; closeout must capture it when observed",
        }
    )
    reentry_conditions: list[str] = []
    if omitted_sidecars:
        reentry_conditions.append("patch the settlement source-bundle owner before reporting refinement")
    if residual_owners:
        reentry_conditions.append("rerun or repair projection hygiene before reporting settlement completion")
    if blockers:
        reentry_conditions.append("resolve the named owner blocker or capture a precise WorkItem/CAP")
    if not reentry_conditions:
        reentry_conditions.append(
            "re-enter if a source or audit sidecar is omitted, a residual owner appears, an owner tool lands an unexpected projection tail, or manual operator challenge reveals friction"
        )
    return {
        "rule": "settlement_is_not_refinement",
        "checked_surfaces": list(SETTLEMENT_STEWARDSHIP_SURFACES),
        "source_bundle_by_owner": source_bundle_by_owner,
        "omitted_audit_or_source_sidecars": omitted_sidecars,
        "residual_owners": residual_owners,
        "owner_tool_blockers": blockers,
        "settlement_revealed_contract_gap": contract_gap,
        "operator_challenge_signal": "not_observed_by_tool",
        "lane_results": lane_results,
        "reentry_conditions": reentry_conditions,
    }


def _settlement_closeout_fields(
    repo_root: Path,
    *,
    status: str,
    dry_run: bool,
    final_plan: Mapping[str, Any],
) -> dict[str, Any]:
    stewardship = _settlement_stewardship_check(repo_root, final_plan)
    blockers = _settlement_blocker_summary(final_plan)
    settlement_done = status == "already_settled" or (not dry_run and status == "settled")
    validation_done = settlement_done and final_plan.get("status") == "clean"
    return {
        "settlement_done": bool(settlement_done),
        "validation_done": bool(validation_done),
        "refinement_done": False,
        "settlement_is_not_refinement": True,
        "stewardship_checked": True,
        "stewardship_check": stewardship,
        "next_best_lane_checked": True,
        "next_best_lane_check": {
            "lanes_checked": list(SETTLEMENT_STEWARDSHIP_SURFACES),
            "lane_results": stewardship["lane_results"],
            "reentry_conditions": stewardship["reentry_conditions"],
        },
        "blocked_by_claim_or_policy": (
            {
                "owner": "generated_state_projection_settlement",
                "blocked_by": blockers,
            }
            if blockers
            else None
        ),
    }


def settle_generated_projection_owners(
    repo_root: Path,
    *,
    owner_ids: Sequence[str] | None = None,
    dry_run: bool = False,
    max_passes: int = 3,
    fast_plan: bool = False,
    work_ledger_session_id: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    settle_started = time.perf_counter()
    phase_timings: list[dict[str, Any]] = []
    _emit_progress(
        progress_callback,
        surface="settlement",
        event="start",
        owner_ids=list(owner_ids or []),
        dry_run=bool(dry_run),
        max_passes=max_passes,
        fast_plan=bool(fast_plan),
    )

    def _record_phase(phase: str, started: float, **fields: Any) -> None:
        row: dict[str, Any] = {
            "phase": phase,
            "wall_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }
        row.update({key: value for key, value in fields.items() if value is not None})
        phase_timings.append(row)

    def _with_timing(payload: dict[str, Any]) -> dict[str, Any]:
        total_wall_ms = round((time.perf_counter() - settle_started) * 1000.0, 3)
        payload["timing"] = {
            "schema": "generated_projection_settlement_timing_v0",
            "total_wall_ms": total_wall_ms,
            "phase_count": len(phase_timings),
            "phases": phase_timings,
            "privacy": "phase_names_wall_time_and_counts_only_no_stdout_stderr_bodies",
        }
        _emit_progress(
            progress_callback,
            surface="settlement",
            event="done",
            status=payload.get("status"),
            ok=payload.get("ok"),
            total_wall_ms=total_wall_ms,
            phase_count=len(phase_timings),
        )
        return payload

    collect_plan_diff_stat = not dry_run
    plan_builder = (
        build_generated_projection_settlement_fast_plan
        if dry_run and fast_plan
        else build_generated_projection_settlement_plan
    )
    initial_plan_started = time.perf_counter()
    _emit_progress(
        progress_callback,
        surface="settlement",
        event="initial_plan_start",
        dry_run=bool(dry_run),
        fast_plan=bool(dry_run and fast_plan),
    )
    before = (
        plan_builder(repo_root, owner_ids=owner_ids)
        if dry_run and fast_plan
        else plan_builder(repo_root, owner_ids=owner_ids, collect_diff_stat=collect_plan_diff_stat)
    )
    initial_plan_wall_ms = round((time.perf_counter() - initial_plan_started) * 1000.0, 3)
    _record_phase(
        "initial_plan",
        initial_plan_started,
        status=before.get("status"),
        dirty_owner_count=before.get("dirty_owner_count"),
        blocked_owner_count=before.get("blocked_owner_count"),
        fast_plan=bool(dry_run and fast_plan),
    )
    _emit_progress(
        progress_callback,
        surface="settlement",
        event="initial_plan_done",
        status=before.get("status"),
        dirty_owner_count=before.get("dirty_owner_count"),
        blocked_owner_count=before.get("blocked_owner_count"),
        wall_ms=initial_plan_wall_ms,
    )
    controls = _settlement_base_controls(repo_root)
    progress_events: list[dict[str, Any]] = [
        {
            "event": "settlement_plan_built",
            "pass_index": 0,
            "status": before.get("status"),
            "dirty_owner_count": before.get("dirty_owner_count"),
            "blocked_owner_count": before.get("blocked_owner_count"),
        }
    ]
    if before.get("status") == "clean":
        return _with_timing({
            "schema": SETTLEMENT_SCHEMA,
            "ok": True,
            "dry_run": bool(dry_run),
            "status": "already_settled",
            "owners": [],
            "progress_events": progress_events,
            "before_plan": _public_settlement_plan(before),
            "final_plan": _public_settlement_plan(before),
            **controls,
            **_settlement_closeout_fields(
                repo_root,
                status="already_settled",
                dry_run=bool(dry_run),
                final_plan=before,
            ),
            "normal_source_event_after_refresh_allowed": False,
            "eventful_closeout_allowed_after_settlement": False,
        })
    if before.get("status") != "settlement_required" or not before.get("can_settle"):
        status = str(before.get("status") or "blocked")
        return _with_timing({
            "schema": SETTLEMENT_SCHEMA,
            "ok": False,
            "dry_run": bool(dry_run),
            "status": status,
            "reason": "settlement_plan_not_apply_safe",
            "blocked_by": before.get("blocked_by") or [],
            "owners": [],
            "progress_events": progress_events,
            "before_plan": _public_settlement_plan(before),
            "final_plan": _public_settlement_plan(before),
            **controls,
            **_settlement_closeout_fields(
                repo_root,
                status=status,
                dry_run=bool(dry_run),
                final_plan=before,
            ),
            "normal_source_event_after_refresh_allowed": False,
            "eventful_closeout_allowed_after_settlement": False,
        })

    owner_results: list[dict[str, Any]] = []
    final_plan = before
    pass_limit = max(1, int(max_passes or 1))
    seen_residual_signatures: dict[str, int] = {}
    for pass_index in range(1, pass_limit + 1):
        if pass_index == 1:
            active_plan = before
        else:
            replan_started = time.perf_counter()
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="replan_start",
                pass_index=pass_index,
            )
            active_plan = (
                plan_builder(repo_root, owner_ids=owner_ids)
                if dry_run and fast_plan
                else plan_builder(repo_root, owner_ids=owner_ids, collect_diff_stat=collect_plan_diff_stat)
            )
            replan_wall_ms = round((time.perf_counter() - replan_started) * 1000.0, 3)
            _record_phase(
                "replan",
                replan_started,
                pass_index=pass_index,
                status=active_plan.get("status"),
                dirty_owner_count=active_plan.get("dirty_owner_count"),
                blocked_owner_count=active_plan.get("blocked_owner_count"),
            )
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="replan_done",
                pass_index=pass_index,
                status=active_plan.get("status"),
                dirty_owner_count=active_plan.get("dirty_owner_count"),
                blocked_owner_count=active_plan.get("blocked_owner_count"),
                wall_ms=replan_wall_ms,
            )
        final_plan = active_plan
        _emit_progress(
            progress_callback,
            surface="settlement",
            event="pass_start",
            pass_index=pass_index,
            status=active_plan.get("status"),
            dirty_owner_count=active_plan.get("dirty_owner_count"),
        )
        progress_events.append(
            {
                "event": "pass_start",
                "pass_index": pass_index,
                "status": active_plan.get("status"),
                "dirty_owner_count": active_plan.get("dirty_owner_count"),
                "reason": "initial_settlement_pass"
                if pass_index == 1
                else "prior_pass_may_have_changed_dependent_projection_state",
            }
        )
        if active_plan.get("status") == "clean":
            break
        if active_plan.get("status") != "settlement_required" or not active_plan.get("can_settle"):
            status = str(active_plan.get("status") or "blocked")
            return _with_timing({
                "schema": SETTLEMENT_SCHEMA,
                "ok": False,
                "dry_run": bool(dry_run),
                "status": status,
                "reason": "settlement_plan_not_apply_safe",
                "blocked_by": active_plan.get("blocked_by") or [],
                "owners": owner_results,
                "progress_events": progress_events,
                "before_plan": _public_settlement_plan(before),
                "final_plan": _public_settlement_plan(active_plan),
                **controls,
                **_settlement_closeout_fields(
                    repo_root,
                    status=status,
                    dry_run=bool(dry_run),
                    final_plan=active_plan,
                ),
                "normal_source_event_after_refresh_allowed": False,
                "eventful_closeout_allowed_after_settlement": False,
            })
        if not dry_run:
            residual_signature = _settlement_residual_signature(active_plan)
            previous_pass_index = seen_residual_signatures.get(residual_signature or "")
            if residual_signature and previous_pass_index is not None:
                return _with_timing({
                    "schema": SETTLEMENT_SCHEMA,
                    "ok": False,
                    "dry_run": False,
                    "status": "settlement_residual_repeated_signature",
                    "reason": "residual_plan_repeated_after_progress",
                    "pass_count": pass_index - 1,
                    "max_passes": pass_limit,
                    "previous_pass_index": previous_pass_index,
                    "current_pass_index": pass_index,
                    "residual_signature": residual_signature,
                    "progress": _settlement_progress_summary(owner_results),
                    "residual_owners": _settlement_residual_owner_rows(active_plan),
                    "owners": owner_results,
                    "progress_events": progress_events,
                    "before_plan": _public_settlement_plan(before),
                    "final_plan": _public_settlement_plan(active_plan),
                    **controls,
                    **_settlement_closeout_fields(
                        repo_root,
                        status="settlement_residual_repeated_signature",
                        dry_run=False,
                        final_plan=active_plan,
                    ),
                    "normal_source_event_after_refresh_allowed": False,
                    "eventful_closeout_allowed_after_settlement": False,
                })
            if residual_signature:
                seen_residual_signatures[residual_signature] = pass_index
        for owner in active_plan.get("owners") or []:
            if owner.get("required_action") not in {"land_append_exempt", "refresh_then_land_append_exempt"}:
                continue
            owner_id = str(owner.get("owner_id") or "")
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="owner_start",
                pass_index=pass_index,
                owner_id=owner_id,
                required_action=owner.get("required_action"),
                expected_path_count=owner.get("path_count"),
            )
            progress_events.append(
                {
                    "event": "owner_start",
                    "pass_index": pass_index,
                    "owner_id": owner_id,
                    "required_action": owner.get("required_action"),
                    "expected_path_count": owner.get("path_count"),
                }
            )
            if dry_run:
                owner_started = time.perf_counter()
                path_bundle = owner.get("path_bundle") if isinstance(owner.get("path_bundle"), dict) else {}
                if owner.get("required_action") == "refresh_then_land_append_exempt":
                    projection_paths_to_stage = path_bundle.get("projection_paths")
                else:
                    projection_paths_to_stage = (
                        path_bundle.get("projection_paths_to_stage")
                        if path_bundle.get("projection_paths_to_stage") is not None
                        else path_bundle.get("projection_paths")
                    )
                result = {
                    "ok": True,
                    "status": (
                        "would_refresh_then_land"
                        if owner.get("required_action") == "refresh_then_land_append_exempt"
                        else "would_land"
                    ),
                    "paths_to_stage": sorted(
                        {
                            *[str(path) for path in path_bundle.get("source_authority_paths_to_stage") or []],
                            *[str(path) for path in projection_paths_to_stage or []],
                            str(path_bundle.get("landing_manifest_path") or ""),
                        }
                        - {""}
                    ),
                    "landing_manifest_path": owner.get("landing_manifest_path"),
                }
            else:
                landing_plan = owner.get("_landing_plan")
                landing_kwargs: dict[str, Any] = {
                    "owner_id": owner_id,
                    "mode": APPEND_EXEMPT_LANDING_MODE,
                    "dry_run": bool(dry_run),
                    "work_ledger_session_id": work_ledger_session_id,
                }
                if isinstance(landing_plan, Mapping):
                    landing_kwargs["landing_plan"] = landing_plan
                owner_started = time.perf_counter()
                result = land_generated_projection_bundle(
                    repo_root,
                    progress_callback=progress_callback,
                    **landing_kwargs,
                )
            path_receipt = _settlement_owner_path_receipt(owner, result)
            _record_phase(
                "owner_dry_run" if dry_run else "owner_land",
                owner_started,
                pass_index=pass_index,
                owner_id=owner_id,
                required_action=owner.get("required_action"),
                result_status=result.get("status"),
                path_count=len(path_receipt["paths_to_stage"]),
            )
            owner_result = {
                "pass_index": pass_index,
                "owner_id": owner_id,
                "before_status": owner.get("status"),
                "required_action": owner.get("required_action"),
                "result_status": result.get("status"),
                "ok": bool(result.get("ok")),
                "commit_hash": result.get("commit_hash"),
                "paths_to_stage": path_receipt["paths_to_stage"],
                "source_authority_paths": path_receipt["source_authority_paths"],
                "source_authority_paths_to_stage": path_receipt["source_authority_paths_to_stage"],
                "projection_paths": path_receipt["projection_paths"],
                "path_bundle": path_receipt["path_bundle"],
                "owner_bundle_completeness": path_receipt["owner_bundle_completeness"],
                "landing_manifest_path": path_receipt["path_bundle"]["landing_manifest_path"],
                "expected_path_count": owner.get("path_count"),
                "pass_reason": "initial_settlement_pass"
                if pass_index == 1
                else "prior_pass_may_have_changed_dependent_projection_state",
            }
            progress_events.append(
                {
                    "event": "owner_result",
                    "pass_index": pass_index,
                    "owner_id": owner_id,
                    "result_status": result.get("status"),
                    "commit_hash": result.get("commit_hash"),
                    "path_count": len(owner_result["paths_to_stage"]),
                }
            )
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="owner_done",
                pass_index=pass_index,
                owner_id=owner_id,
                result_status=result.get("status"),
                commit_hash=result.get("commit_hash"),
                path_count=len(owner_result["paths_to_stage"]),
            )
            if not result.get("ok"):
                owner_result["error"] = result.get("error")
                owner_result["reason"] = result.get("reason")
                owner_results.append(owner_result)
                if dry_run:
                    final_plan = before
                else:
                    final_plan_started = time.perf_counter()
                    _emit_progress(
                        progress_callback,
                        surface="settlement",
                        event="final_replan_start",
                        reason="owner_failed",
                    )
                    final_plan = build_generated_projection_settlement_plan(
                        repo_root,
                        owner_ids=owner_ids,
                        collect_diff_stat=True,
                    )
                    final_replan_wall_ms = round((time.perf_counter() - final_plan_started) * 1000.0, 3)
                    _record_phase(
                        "final_replan",
                        final_plan_started,
                        status=final_plan.get("status"),
                        dirty_owner_count=final_plan.get("dirty_owner_count"),
                        blocked_owner_count=final_plan.get("blocked_owner_count"),
                    )
                    _emit_progress(
                        progress_callback,
                        surface="settlement",
                        event="final_replan_done",
                        status=final_plan.get("status"),
                        dirty_owner_count=final_plan.get("dirty_owner_count"),
                        blocked_owner_count=final_plan.get("blocked_owner_count"),
                        wall_ms=final_replan_wall_ms,
                    )
                return _with_timing({
                    "schema": SETTLEMENT_SCHEMA,
                    "ok": False,
                    "dry_run": bool(dry_run),
                    "status": "failed",
                    "owners": owner_results,
                    "progress_events": progress_events,
                    "before_plan": _public_settlement_plan(before),
                    "final_plan": _public_settlement_plan(final_plan),
                    **controls,
                    **_settlement_closeout_fields(
                        repo_root,
                        status="failed",
                        dry_run=bool(dry_run),
                        final_plan=final_plan,
                    ),
                    "normal_source_event_after_refresh_allowed": False,
                    "eventful_closeout_allowed_after_settlement": False,
                })
            owner_results.append(owner_result)
        if dry_run:
            break
        pass_results = [row for row in owner_results if int(row.get("pass_index") or 0) == pass_index]
        if pass_results and not any(row.get("commit_hash") for row in pass_results):
            final_plan_started = time.perf_counter()
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="final_replan_start",
                reason="no_commit_progress",
            )
            final_plan = build_generated_projection_settlement_plan(
                repo_root,
                owner_ids=owner_ids,
                collect_diff_stat=True,
            )
            final_replan_wall_ms = round((time.perf_counter() - final_plan_started) * 1000.0, 3)
            _record_phase(
                "final_replan",
                final_plan_started,
                status=final_plan.get("status"),
                dirty_owner_count=final_plan.get("dirty_owner_count"),
                blocked_owner_count=final_plan.get("blocked_owner_count"),
            )
            _emit_progress(
                progress_callback,
                surface="settlement",
                event="final_replan_done",
                status=final_plan.get("status"),
                dirty_owner_count=final_plan.get("dirty_owner_count"),
                blocked_owner_count=final_plan.get("blocked_owner_count"),
                wall_ms=final_replan_wall_ms,
            )
            if final_plan.get("status") != "clean":
                return _with_timing({
                    "schema": SETTLEMENT_SCHEMA,
                    "ok": False,
                    "dry_run": bool(dry_run),
                    "status": "settlement_residual_no_progress",
                    "reason": "dirty_settlement_owner_made_no_commit",
                    "pass_count": pass_index,
                    "max_passes": pass_limit,
                    "progress": _settlement_progress_summary(owner_results),
                    "residual_owners": _settlement_residual_owner_rows(final_plan),
                    "owners": owner_results,
                    "progress_events": progress_events,
                    "before_plan": _public_settlement_plan(before),
                    "final_plan": _public_settlement_plan(final_plan),
                    **controls,
                    **_settlement_closeout_fields(
                        repo_root,
                        status="settlement_residual_no_progress",
                        dry_run=bool(dry_run),
                        final_plan=final_plan,
                    ),
                    "normal_source_event_after_refresh_allowed": False,
                    "eventful_closeout_allowed_after_settlement": False,
                })
    if not dry_run:
        final_plan_started = time.perf_counter()
        _emit_progress(
            progress_callback,
            surface="settlement",
            event="final_plan_start",
        )
        final_plan = build_generated_projection_settlement_plan(
            repo_root,
            owner_ids=owner_ids,
            collect_diff_stat=True,
        )
        final_plan_wall_ms = round((time.perf_counter() - final_plan_started) * 1000.0, 3)
        _record_phase(
            "final_plan",
            final_plan_started,
            status=final_plan.get("status"),
            dirty_owner_count=final_plan.get("dirty_owner_count"),
            blocked_owner_count=final_plan.get("blocked_owner_count"),
        )
        _emit_progress(
            progress_callback,
            surface="settlement",
            event="final_plan_done",
            status=final_plan.get("status"),
            dirty_owner_count=final_plan.get("dirty_owner_count"),
            blocked_owner_count=final_plan.get("blocked_owner_count"),
            wall_ms=final_plan_wall_ms,
        )
    if dry_run:
        status = "would_settle"
        reason = None
    elif final_plan.get("status") == "clean":
        status = "settled"
        reason = None
    else:
        status = "settlement_residual_capped"
        reason = "max_passes_exhausted"
    progress = _settlement_progress_summary(owner_results)
    return _with_timing({
        "schema": SETTLEMENT_SCHEMA,
        "ok": bool(dry_run or final_plan.get("status") == "clean"),
        "dry_run": bool(dry_run),
        "status": status,
        **({"reason": reason} if reason else {}),
        "pass_count": max([int(row.get("pass_index") or 0) for row in owner_results] or [0]),
        "max_passes": pass_limit,
        "progress": progress,
        "residual_owners": [] if dry_run or final_plan.get("status") == "clean" else _settlement_residual_owner_rows(final_plan),
        "owners": owner_results,
        "progress_events": progress_events,
        "before_plan": _public_settlement_plan(before),
        "final_plan": _public_settlement_plan(final_plan),
        **controls,
        **_settlement_closeout_fields(
            repo_root,
            status=status,
            dry_run=bool(dry_run),
            final_plan=final_plan,
        ),
        "normal_source_event_after_refresh_allowed": False,
        "eventful_closeout_allowed_after_settlement": False,
    })


def apply_generated_state_drainer(
    repo_root: Path,
    *,
    only: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    supported_actions = [WORK_LEDGER_REFRESH_ACTION, TASK_LEDGER_REFRESH_ACTION, SYSTEM_ATLAS_REFRESH_ACTION]
    if only not in set(supported_actions):
        return {
            "schema": APPLY_SCHEMA,
            "ok": False,
            "dry_run": bool(dry_run),
            "action_id": only,
            "status": "refused",
            "reason": "unsupported_action",
            "supported_actions": supported_actions,
        }
    owner_id = (
        WORK_LEDGER_OWNER_ID
        if only == WORK_LEDGER_REFRESH_ACTION
        else TASK_LEDGER_OWNER_ID
        if only == TASK_LEDGER_REFRESH_ACTION
        else SYSTEM_ATLAS_OWNER_ID
    )
    before = build_generated_state_drainer_status(repo_root, owner_ids=[owner_id])
    stale_count = int(before.get("summary", {}).get("stale_count") or 0)
    action = {
        "action_id": only,
        "owner_id": owner_id,
        "owner_tool": _command_text(generated_projection_registry.get_projection_owner(owner_id).repair_command),
        "would_mutate": stale_count > 0,
        "commit_policy": "serial_drainer_only",
        "scope": (
            "codex/ledger/*/work_ledger_index.json"
            if owner_id == WORK_LEDGER_OWNER_ID
            else "state/task_ledger/{ledger.json,sign_offs.json,views/*.json}"
            if owner_id == TASK_LEDGER_OWNER_ID
            else "state/system_atlas/*,docs/system_atlas/generated*.md"
        ),
    }
    if dry_run:
        return {
            "schema": APPLY_SCHEMA,
            "ok": True,
            "dry_run": True,
            "status": "would_apply" if stale_count else "already_fresh",
            "action": action,
            "before": before,
        }
    if owner_id == WORK_LEDGER_OWNER_ID:
        projection_result = work_ledger.project_all(repo_root)
    elif owner_id == TASK_LEDGER_OWNER_ID:
        projection_result = task_ledger_events.rebuild_projections(repo_root)
    else:
        owner_row = generated_projection_registry.get_projection_owner(owner_id)
        proc = subprocess.run(
            [str(part) for part in owner_row.repair_command],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        projection_result = {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "command": _command_text(owner_row.repair_command),
            "stdout": proc.stdout,
            "stderr": proc.stderr,
        }
    after = build_generated_state_drainer_status(repo_root, owner_ids=[owner_id])
    return {
        "schema": APPLY_SCHEMA,
        "ok": bool(projection_result.get("ok", True)),
        "dry_run": False,
        "status": "applied" if stale_count else "already_fresh",
        "action": action,
        "projection_result": projection_result,
        "before": before,
        "after": after,
    }
