"""
[PURPOSE]
- Teleology: Provide the canonical disk-first helpers every meta-mission
  runtime uses to record one run into its own durable career workspace at
  state/meta_missions/<mission_id>/runs/<run_id>/.
- Mechanism: Read the meta_mission_registry, resolve workspace/runtime paths,
  mint iso_timestamp_plus_slug run ids, append events/artifacts, finalize a
  canonical run.json, and aggregate list/detail metrics across registered
  missions — including parent+child linking for chain meta-missions.
- Non-goal: Executing mission steps, launching bridge work, or authoring
  mission.json payloads. The registry owns lifecycle metadata, mission.json
  owns procedure and skill bundles, and the per-mission runtime owns step
  execution. This module is the neutral ledger surface underneath.

[INTERFACE]
- load_registry(repo_root)                                            -> dict
- resolve_mission_entry(repo_root, mission_id)                        -> dict | None
- resolve_workspace_root(repo_root, mission_id)                       -> Path
- resolve_runtime_root(repo_root, mission_id)                         -> Path
- mint_run_id(mission_id, *, when=None, slug=None)                    -> str
- start_run(...)                                                      -> dict
- append_event(repo_root, mission_id, run_id, event)                  -> Path
- append_artifact_ref(repo_root, mission_id, run_id, artifact)        -> Path
- finalize_run(...)                                                   -> dict
- load_run(repo_root, mission_id, run_id)                             -> dict | None
- read_run_events(repo_root, mission_id, run_id)                      -> list[dict]
- read_run_artifacts(repo_root, mission_id, run_id)                   -> list[dict]
- list_runs(repo_root, mission_id, *, limit=None, offset=0)           -> list[dict]
- aggregate_metrics(repo_root, mission_id)                            -> dict
- list_missions(repo_root)                                            -> list[dict]
- workspace_summary_slice(repo_root, *, limit_per_mission=1)          -> dict

[CONSTRAINTS]
- Atomicity: Append-only JSONL ledger (events.jsonl, artifacts.jsonl); run.json
  is the single authoritative summary per run and is rewritten atomically via
  os.replace.
- Forbid: Writing under tools/meta/apply/meta_missions/* (legacy debris) or
  inventing a second registry.
- Failure: Missing run.json / malformed JSONL degrade to empty summaries, never
  raise; registry-missing mission_id raises ValueError because caller is the
  bug.
- When-needed: Open when a mission runtime needs the canonical run manifest
  shape without reimplementing it, or when the server/UI needs list/detail
  metrics over mission careers.
- Escalates-to: codex/standards/observe/mission_templates/std_meta_mission_workspace.json;
  system/server/world_model.py; system/server/main.py
- Navigation-group: meta_missions

[FLOW]
- Resolve a registered mission career, create its run record, append event/artifact trails, finalize status and aggregate run metrics.

[DEPENDENCIES]
- Meta-mission registry JSON and mission-owned workspace/runtime directories; filesystem writes are local.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

REPO_ROOT_MARKER_FILE = "AGENTS.md"
REGISTRY_REL = "codex/standards/observe/mission_templates/meta_mission_registry.json"
STANDARD_REL = "codex/standards/observe/mission_templates/std_meta_mission_workspace.json"
WORKSPACE_ROOT_REL = "state/meta_missions"

RUN_JSON_NAME = "run.json"
EVENTS_JSONL_NAME = "events.jsonl"
ARTIFACTS_JSONL_NAME = "artifacts.jsonl"
INDEX_JSONL_NAME = "index.jsonl"

VALID_RUN_STATUSES = {
    "running",
    "succeeded",
    "failed",
    "graceful_stop",
    "interrupted",
    "skipped",
}
TERMINAL_RUN_STATUSES = {"succeeded", "failed", "graceful_stop", "interrupted", "skipped"}

VALID_TRIGGERS = {"operator", "phase", "chain", "scheduled_task", "test", "unknown"}


# ---------------------------------------------------------------------------
# small helpers


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_stamp(when: datetime | None = None) -> str:
    point = when or datetime.now(timezone.utc)
    return point.strftime("%Y%m%dT%H%M%SZ").lower()


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _safe_slug(token: str, *, fallback: str = "run") -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", _string(token)).strip("_").lower()
    return cleaned or fallback


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _ensure_dir(path.parent)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    _ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            rows.append(payload)
    return rows


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _rel_posix(repo_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


# ---------------------------------------------------------------------------
# registry access


def _resolve_registry_path(repo_root: Path) -> Path:
    return (repo_root / REGISTRY_REL).resolve()


def load_registry(repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Return the canonical meta-mission registry payload.
    - Mechanism: Read the JSON file at REGISTRY_REL.
    - Guarantee: Returns a dict with the schema-declared fields on success; raises
      FileNotFoundError when the registry is missing (it is authoritative; do not
      silently run without it).
    - Fails: ValueError on malformed JSON.
    - When-needed: Open when any consumer needs the mission inventory before
      resolving paths or enumerating missions.
    """
    path = _resolve_registry_path(repo_root)
    if not path.exists():
        raise FileNotFoundError(f"Meta-mission registry missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Meta-mission registry is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Meta-mission registry must be a JSON object: {path}")
    return payload


def _registry_entries(repo_root: Path) -> list[dict[str, Any]]:
    """Return the registry entries, tolerating a missing or malformed registry.

    Callers that want the whole payload should use `load_registry` directly; that
    helper raises to preserve the 'registry is authoritative' contract from the
    standard. This private helper exists for the yes/no lookup paths where a
    missing registry reads as 'no missions registered' — useful for tests and for
    controller paths that want to no-op gracefully when the repo has not been
    bootstrapped yet.
    """
    try:
        payload = load_registry(repo_root)
    except (FileNotFoundError, ValueError):
        return []
    raw_entries = payload.get("entries") if isinstance(payload.get("entries"), list) else []
    return [dict(entry) for entry in raw_entries if isinstance(entry, Mapping)]


def resolve_mission_entry(repo_root: Path, mission_id: str) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Resolve one registry entry by mission_id.
    - Mechanism: Look up the entry in the registry entries list.
    - Guarantee: Returns the entry dict or None when the mission_id is not
      registered or the registry itself is absent. Callers decide whether absence
      is an error.
    """
    token = _string(mission_id)
    if not token:
        return None
    for entry in _registry_entries(repo_root):
        if _string(entry.get("mission_id")) == token:
            return entry
    return None


def _require_entry(repo_root: Path, mission_id: str) -> dict[str, Any]:
    entry = resolve_mission_entry(repo_root, mission_id)
    if entry is None:
        raise ValueError(
            f"mission_id {mission_id!r} is not registered in meta_mission_registry.json"
        )
    return entry


def list_missions(repo_root: Path) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Return the registry entries as a shallow-copy list.
    - Mechanism: Read the registry and surface entries in registry order.
    - Guarantee: Always a list; empty when the registry declares no entries.
    """
    return _registry_entries(repo_root)


# ---------------------------------------------------------------------------
# workspace / runtime path resolution


def resolve_workspace_root(repo_root: Path, mission_id: str) -> Path:
    """
    [ACTION]
    - Teleology: Resolve the absolute on-disk workspace root for one mission.
    - Mechanism: Prefer registry-declared workspace_root; fall back to the
      canonical state/meta_missions/<mission_id>/ convention when the entry does
      not declare one.
    - Guarantee: Returns an absolute Path. Does not create the directory.
    """
    entry = resolve_mission_entry(repo_root, mission_id)
    token = _string((entry or {}).get("workspace_root")) if entry else ""
    if not token:
        token = f"{WORKSPACE_ROOT_REL}/{_string(mission_id)}"
    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = repo_root / candidate
    return candidate.resolve()


def resolve_runtime_root(repo_root: Path, mission_id: str) -> Path:
    """
    [ACTION]
    - Teleology: Resolve the absolute runtime root for mission-owned control
      artifacts (active state, ledger, stop flag). Distinct from the runs/ root
      because runtime files are per-career, not per-run.
    - Mechanism: Prefer registry-declared runtime_root; fall back to
      <workspace_root>/runtime/.
    - Guarantee: Returns an absolute Path. Does not create the directory.
    """
    entry = resolve_mission_entry(repo_root, mission_id)
    token = _string((entry or {}).get("runtime_root")) if entry else ""
    if token:
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = repo_root / candidate
        return candidate.resolve()
    return (resolve_workspace_root(repo_root, mission_id) / "runtime").resolve()


def resolve_runs_root(repo_root: Path, mission_id: str) -> Path:
    """Convenience helper: <workspace_root>/runs/."""
    return (resolve_workspace_root(repo_root, mission_id) / "runs").resolve()


def resolve_run_dir(repo_root: Path, mission_id: str, run_id: str) -> Path:
    """Convenience helper: <workspace_root>/runs/<run_id>/."""
    return (resolve_runs_root(repo_root, mission_id) / _string(run_id)).resolve()


# ---------------------------------------------------------------------------
# run id minting


_RUN_ID_RE = re.compile(r"^[0-9]{8}t[0-9]{6}z(_[a-z0-9_]+)?$")


def mint_run_id(
    mission_id: str,
    *,
    when: datetime | None = None,
    slug: str | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Produce a deterministic iso-timestamp-plus-slug run id per
      canonical_run_manifest_shape.run_id in std_meta_mission_workspace.json.
    - Mechanism: "<utc_stamp>_<slug>" where utc_stamp = YYYYMMDDTHHMMSSZ
      (lowercased) and slug defaults to the mission_id.
    - Guarantee: Returns a run id matching the workspace run_id regex.
    - Fails: None.
    """
    stamp = _utc_stamp(when)
    slug_token = _safe_slug(slug or mission_id, fallback=_safe_slug(mission_id, fallback="run"))
    return f"{stamp}_{slug_token}"


def is_valid_run_id(token: str) -> bool:
    return bool(_RUN_ID_RE.match(_string(token).lower()))


# ---------------------------------------------------------------------------
# run lifecycle


def _canonical_run_shape(
    *,
    mission_id: str,
    run_id: str,
    template_version: str | None,
    trigger: str,
    phase_ref: str | None,
    parent_run_id: str | None,
    chain_ref: Mapping[str, Any] | None,
    provider: str | None,
    dispatch_policy_resolved: Mapping[str, Any] | None,
    selection_summary: Mapping[str, Any] | None,
    started_at: str,
    inputs_digest: str | None,
    log_path: str | None,
    notes: str | None,
) -> dict[str, Any]:
    return {
        "kind": "meta_mission_run",
        "schema_version": "1.0",
        "mission_id": mission_id,
        "run_id": run_id,
        "template_version": template_version,
        "trigger": trigger if trigger in VALID_TRIGGERS else "unknown",
        "phase_ref": phase_ref,
        "parent_run_id": parent_run_id,
        "chain_ref": dict(chain_ref) if isinstance(chain_ref, Mapping) else None,
        "provider": provider,
        "dispatch_policy_resolved": dict(dispatch_policy_resolved or {}),
        "selection_summary": dict(selection_summary or {}),
        "started_at": started_at,
        "finished_at": None,
        "status": "running",
        "inputs_digest": inputs_digest,
        "artifact_refs": [],
        "log_path": log_path,
        "notes": notes,
    }


def compute_inputs_digest(payload: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Hash the controller-resolved inputs into a stable digest for
      idempotency checks across chain steps and re-runs.
    - Mechanism: Canonical JSON encode (sort_keys=True) and return sha256 hex.
    - Guarantee: Deterministic across equal inputs.
    """
    encoded = json.dumps(dict(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def start_run(
    repo_root: Path,
    *,
    mission_id: str,
    run_id: str | None = None,
    trigger: str = "operator",
    phase_ref: str | None = None,
    parent_run_id: str | None = None,
    chain_ref: Mapping[str, Any] | None = None,
    provider: str | None = None,
    dispatch_policy_resolved: Mapping[str, Any] | None = None,
    selection_summary: Mapping[str, Any] | None = None,
    inputs_digest: str | None = None,
    template_version: str | None = None,
    log_path: str | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Create a new run directory and canonical run.json for one
      mission career.
    - Mechanism: Mint a run id if none provided, create <workspace>/runs/<run_id>/,
      write run.json with status=running, and append an index.jsonl row pointing
      at it.
    - Guarantee: Returns the run shape plus `run_dir` and `run_json_path` paths
      (repo-relative) for callers.
    - Fails: ValueError when mission_id not in registry.
    """
    entry = _require_entry(repo_root, mission_id)
    run_identifier = _string(run_id) or mint_run_id(mission_id)
    run_dir = resolve_run_dir(repo_root, mission_id, run_identifier)
    _ensure_dir(run_dir)

    started_at = _utc_now_iso()
    effective_template_version = (
        _string(template_version)
        or _string(entry.get("template_version"))
        or None
    )
    run_shape = _canonical_run_shape(
        mission_id=_string(mission_id),
        run_id=run_identifier,
        template_version=effective_template_version,
        trigger=_string(trigger) or "operator",
        phase_ref=_string(phase_ref) or None,
        parent_run_id=_string(parent_run_id) or None,
        chain_ref=chain_ref if isinstance(chain_ref, Mapping) else None,
        provider=_string(provider) or None,
        dispatch_policy_resolved=dispatch_policy_resolved,
        selection_summary=selection_summary,
        started_at=started_at,
        inputs_digest=_string(inputs_digest) or None,
        log_path=_string(log_path) or None,
        notes=_string(notes) or None,
    )
    run_json_path = run_dir / RUN_JSON_NAME
    _atomic_write_json(run_json_path, run_shape)

    # Always seed events.jsonl with the run-start event so timelines are
    # complete even when a runtime crashes before finalize_run().
    append_event(
        repo_root,
        mission_id=mission_id,
        run_id=run_identifier,
        event={
            "kind": "meta_mission_run_event",
            "event_type": "run_started",
            "status": "running",
            "recorded_at": started_at,
            "trigger": run_shape["trigger"],
            "phase_ref": run_shape["phase_ref"],
            "parent_run_id": run_shape["parent_run_id"],
            "chain_ref": run_shape["chain_ref"],
        },
    )

    index_path = resolve_workspace_root(repo_root, mission_id) / INDEX_JSONL_NAME
    _append_jsonl(
        index_path,
        {
            "kind": "meta_mission_index_entry",
            "event_type": "run_started",
            "mission_id": mission_id,
            "run_id": run_identifier,
            "parent_run_id": run_shape["parent_run_id"],
            "trigger": run_shape["trigger"],
            "phase_ref": run_shape["phase_ref"],
            "status": "running",
            "recorded_at": started_at,
        },
    )

    return {
        **run_shape,
        "run_dir": _rel_posix(repo_root, run_dir),
        "run_json_path": _rel_posix(repo_root, run_json_path),
    }


def append_event(
    repo_root: Path,
    *,
    mission_id: str,
    run_id: str,
    event: Mapping[str, Any],
) -> Path:
    """Append one JSONL event into <run_dir>/events.jsonl and return its path."""
    run_dir = resolve_run_dir(repo_root, mission_id, run_id)
    payload = dict(event)
    payload.setdefault("mission_id", mission_id)
    payload.setdefault("run_id", run_id)
    payload.setdefault("recorded_at", _utc_now_iso())
    path = run_dir / EVENTS_JSONL_NAME
    _append_jsonl(path, payload)
    return path


def append_artifact_ref(
    repo_root: Path,
    *,
    mission_id: str,
    run_id: str,
    artifact: Mapping[str, Any],
) -> Path:
    """Append one JSONL artifact descriptor into <run_dir>/artifacts.jsonl.

    Expected fields: {path, kind?, role?, size_bytes?, notes?}
    """
    run_dir = resolve_run_dir(repo_root, mission_id, run_id)
    payload = dict(artifact)
    payload.setdefault("mission_id", mission_id)
    payload.setdefault("run_id", run_id)
    payload.setdefault("recorded_at", _utc_now_iso())
    path = run_dir / ARTIFACTS_JSONL_NAME
    _append_jsonl(path, payload)
    return path


def finalize_run(
    repo_root: Path,
    *,
    mission_id: str,
    run_id: str,
    status: str,
    error: str | None = None,
    artifact_refs: Sequence[str] | None = None,
    selection_summary: Mapping[str, Any] | None = None,
    notes: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Close out a run by stamping finished_at + terminal status into
      run.json and emitting a matching index row.
    - Mechanism: Re-read run.json, merge the new fields, write atomically, append
      an events.jsonl terminator and an index.jsonl row.
    - Guarantee: Returns the merged run shape with run_dir and run_json_path.
    - Fails: ValueError on unknown status or missing run.json.
    """
    normalized = _string(status).lower()
    if normalized not in VALID_RUN_STATUSES:
        raise ValueError(f"Unknown run status {status!r}; expected one of {sorted(VALID_RUN_STATUSES)}")

    run_dir = resolve_run_dir(repo_root, mission_id, run_id)
    run_json_path = run_dir / RUN_JSON_NAME
    current = _read_json(run_json_path)
    if current is None:
        raise ValueError(f"run.json not found for mission_id={mission_id!r} run_id={run_id!r}")

    finished_at = _utc_now_iso()
    merged = dict(current)
    merged["status"] = normalized
    merged["finished_at"] = finished_at
    if error is not None:
        merged["error"] = _string(error) or None
    if artifact_refs is not None:
        merged["artifact_refs"] = [
            _string(item) for item in artifact_refs if _string(item)
        ]
    if selection_summary is not None:
        merged["selection_summary"] = dict(selection_summary)
    if notes is not None:
        merged["notes"] = _string(notes) or None
    if extra:
        for key, value in dict(extra).items():
            merged[_string(key)] = value
    _atomic_write_json(run_json_path, merged)

    append_event(
        repo_root,
        mission_id=mission_id,
        run_id=run_id,
        event={
            "kind": "meta_mission_run_event",
            "event_type": "run_finalized",
            "status": normalized,
            "recorded_at": finished_at,
            "error": merged.get("error"),
        },
    )

    index_path = resolve_workspace_root(repo_root, mission_id) / INDEX_JSONL_NAME
    _append_jsonl(
        index_path,
        {
            "kind": "meta_mission_index_entry",
            "event_type": "run_finalized",
            "mission_id": mission_id,
            "run_id": run_id,
            "parent_run_id": merged.get("parent_run_id"),
            "trigger": merged.get("trigger"),
            "phase_ref": merged.get("phase_ref"),
            "status": normalized,
            "recorded_at": finished_at,
            "error": merged.get("error"),
        },
    )

    return {
        **merged,
        "run_dir": _rel_posix(repo_root, run_dir),
        "run_json_path": _rel_posix(repo_root, run_json_path),
    }


# ---------------------------------------------------------------------------
# read / aggregate


def load_run(repo_root: Path, mission_id: str, run_id: str) -> dict[str, Any] | None:
    """Return the canonical run.json payload or None when absent."""
    run_dir = resolve_run_dir(repo_root, mission_id, run_id)
    shape = _read_json(run_dir / RUN_JSON_NAME)
    if shape is None:
        return None
    shape["run_dir"] = _rel_posix(repo_root, run_dir)
    shape["run_json_path"] = _rel_posix(repo_root, run_dir / RUN_JSON_NAME)
    events_path = run_dir / EVENTS_JSONL_NAME
    artifacts_path = run_dir / ARTIFACTS_JSONL_NAME
    shape["events_path"] = _rel_posix(repo_root, events_path) if events_path.exists() else None
    shape["artifacts_path"] = (
        _rel_posix(repo_root, artifacts_path) if artifacts_path.exists() else None
    )
    return shape


def read_run_events(repo_root: Path, mission_id: str, run_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Return the append-only events trail for one run.
    - Mechanism: Read <run_dir>/events.jsonl through the shared JSONL decoder.
    - Guarantee: Returns [] when the trail is absent or malformed.
    """
    return _read_jsonl(resolve_run_dir(repo_root, mission_id, run_id) / EVENTS_JSONL_NAME)


def read_run_artifacts(repo_root: Path, mission_id: str, run_id: str) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Return the append-only artifact trail for one run.
    - Mechanism: Read <run_dir>/artifacts.jsonl through the shared JSONL decoder.
    - Guarantee: Returns [] when the trail is absent or malformed.
    """
    return _read_jsonl(resolve_run_dir(repo_root, mission_id, run_id) / ARTIFACTS_JSONL_NAME)


def _iter_run_shapes(repo_root: Path, mission_id: str) -> Iterable[dict[str, Any]]:
    runs_root = resolve_runs_root(repo_root, mission_id)
    if not runs_root.exists():
        return []
    shapes: list[dict[str, Any]] = []
    for entry in runs_root.iterdir():
        if not entry.is_dir():
            continue
        run_id = entry.name
        shape = load_run(repo_root, mission_id, run_id)
        if shape is None:
            continue
        shapes.append(shape)
    return shapes


def list_runs(
    repo_root: Path,
    mission_id: str,
    *,
    limit: int | None = None,
    offset: int = 0,
    include_running: bool = True,
) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Return runs for one mission career, most recent first.
    - Mechanism: Walk runs/<run_id>/run.json, sort by started_at desc, slice.
    - Guarantee: Returns an empty list when the career has no runs yet.
    """
    shapes = list(_iter_run_shapes(repo_root, mission_id))
    if not include_running:
        shapes = [shape for shape in shapes if _string(shape.get("status")) != "running"]
    shapes.sort(key=lambda item: _string(item.get("started_at")), reverse=True)
    if offset:
        shapes = shapes[max(0, int(offset)) :]
    if limit is not None:
        shapes = shapes[: max(0, int(limit))]
    return shapes


def aggregate_metrics(repo_root: Path, mission_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compute the career-level summary used by the Station tile and
      the /meta-missions list view.
    - Mechanism: Walk run.json shapes and tally totals, last-run summary, and a
      naive success rate over terminal statuses.
    - Guarantee: Always returns the full summary shape; zeroes when empty.
    """
    shapes = list(_iter_run_shapes(repo_root, mission_id))
    total = len(shapes)
    by_status: dict[str, int] = {}
    terminal_total = 0
    succeeded_total = 0
    failed_total = 0
    running_total = 0
    for shape in shapes:
        status = _string(shape.get("status")) or "unknown"
        by_status[status] = by_status.get(status, 0) + 1
        if status in TERMINAL_RUN_STATUSES:
            terminal_total += 1
            if status == "succeeded":
                succeeded_total += 1
            elif status == "failed":
                failed_total += 1
        elif status == "running":
            running_total += 1

    shapes.sort(key=lambda item: _string(item.get("started_at")), reverse=True)
    last_run = shapes[0] if shapes else None
    success_rate = (succeeded_total / terminal_total) if terminal_total else None
    return {
        "mission_id": mission_id,
        "total_runs": total,
        "running_total": running_total,
        "failed_total": failed_total,
        "succeeded_total": succeeded_total,
        "terminal_total": terminal_total,
        "success_rate": success_rate,
        "by_status": by_status,
        "last_run": (
            {
                "run_id": last_run.get("run_id"),
                "mission_id": last_run.get("mission_id") or mission_id,
                "status": last_run.get("status"),
                "started_at": last_run.get("started_at"),
                "finished_at": last_run.get("finished_at"),
                "trigger": last_run.get("trigger"),
                "phase_ref": last_run.get("phase_ref"),
                "parent_run_id": last_run.get("parent_run_id"),
                "provider": last_run.get("provider"),
                "error": last_run.get("error"),
            }
            if last_run
            else None
        ),
    }


def workspace_summary_slice(
    repo_root: Path,
    *,
    limit_per_mission: int = 1,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Produce the Station-level `meta_missions` slice: a compact row
      per active mission plus the tiny recent-runs tail used for urgent-state
      signals on /station (failed / graceful_stop / running).
    - Mechanism: Walk only `active` registry entries, aggregate metrics, and
      attach the top-N recent runs.
    - Guarantee: Always returns a dict with `generated_at`, `missions`,
      `totals`, and `urgent` keys. Safe when no runs exist.
    """
    generated_at = _utc_now_iso()
    missions_rows: list[dict[str, Any]] = []
    total_runs = 0
    running_total = 0
    failed_total = 0
    urgent: list[dict[str, Any]] = []
    for entry in _registry_entries(repo_root):
        status = _string(entry.get("status"))
        if status != "active":
            continue
        mission_id = _string(entry.get("mission_id"))
        metrics = aggregate_metrics(repo_root, mission_id)
        recent = list_runs(repo_root, mission_id, limit=max(0, int(limit_per_mission)))
        row = {
            "mission_id": mission_id,
            "title": _string(entry.get("title")) or mission_id,
            "kind": _string(entry.get("kind")),
            "status": status,
            "runtime_surface": _string(entry.get("runtime_surface")) or None,
            "supports_resume": bool(entry.get("supports_resume")),
            "launcher_operation_ids": list(entry.get("launcher_operation_ids") or []),
            "workspace_root": _string(entry.get("workspace_root")) or f"{WORKSPACE_ROOT_REL}/{mission_id}",
            "metrics": metrics,
            "recent_runs": recent,
        }
        missions_rows.append(row)
        total_runs += int(metrics.get("total_runs") or 0)
        running_total += int(metrics.get("running_total") or 0)
        failed_total += int(metrics.get("failed_total") or 0)
        last_run = metrics.get("last_run") or {}
        if _string(last_run.get("status")) in {"failed", "graceful_stop"}:
            urgent.append(
                {
                    "mission_id": mission_id,
                    "title": row["title"],
                    "status": last_run.get("status"),
                    "run_id": last_run.get("run_id"),
                    "finished_at": last_run.get("finished_at"),
                    "error": last_run.get("error"),
                    "supports_resume": row["supports_resume"],
                }
            )

    return {
        "generated_at": generated_at,
        "totals": {
            "active_missions": len(missions_rows),
            "total_runs": total_runs,
            "running_total": running_total,
            "failed_total": failed_total,
        },
        "missions": missions_rows,
        "urgent": urgent,
    }
