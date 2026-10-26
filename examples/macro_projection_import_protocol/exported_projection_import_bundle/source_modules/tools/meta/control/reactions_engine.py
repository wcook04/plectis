"""
[PURPOSE]
- Teleology: Run the Phase 09.35 journal-gated reactions loop as durable repo
  runtime state rather than chat-memory ceremony.
- Mechanism: Load tracked reaction config from `reactions.yaml`, persist runtime
  state in `tools/meta/control/reactions_state.json`, journal decisions in
  `tools/meta/control/reactions_ledger.jsonl`, and append compact visibility
  rows into `tools/meta/control/orchestration_events.jsonl`.

[INTERFACE]
- CLI:
  - `run`     start the detached single-flight engine loop
  - `tick`    execute one evaluation cycle
  - `status`  print the compiled reactions snapshot
  - `arm`     set `desired_armed=true`
  - `disarm`  set `desired_armed=false` and create the stop flag
- Importable helpers:
  - `build_reactions_snapshot`
  - `build_ready_deferred_reactions_projection`
  - `build_reactions_frontend_contract_fixture_pack`
  - `resolve_reaction_graph_scene_inspector`
  - `build_reactions_orchestration_projection`
  - `load_reactions_state`
  - `load_reactions_config`
  - `set_engine_armed_state`
  - `set_reaction_override_state`
"""
from __future__ import annotations

import hashlib
import copy
import json
import os
import shlex
import sys
import tempfile
import threading
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Sequence

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import graph_scene_core

_YAML_SAFE_LOADER: Any | None = None
_yaml_module: Any | None = None


def _yaml_loader() -> tuple[Any, Any]:
    global _YAML_SAFE_LOADER, _yaml_module
    if _yaml_module is None:
        import yaml as loaded_yaml

        _yaml_module = loaded_yaml
        _YAML_SAFE_LOADER = getattr(loaded_yaml, "CSafeLoader", loaded_yaml.SafeLoader)
    return _yaml_module, _YAML_SAFE_LOADER


def load_hologram_build_status(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate hologram build-status loading through a lazy import."""
    from system.lib.hologram_build_status import load_hologram_build_status as _load

    return _load(*args, **kwargs)


def load_raw_seed_pipeline_snapshot(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate raw-seed pipeline snapshot loading through a lazy import."""
    from system.lib.raw_seed_atomization import load_raw_seed_pipeline_snapshot as _load

    return _load(*args, **kwargs)


def load_work_ledger_runtime_status(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate Work Ledger runtime-status loading through a lazy import."""
    from system.lib.work_ledger_runtime import load_runtime_status as _load

    return _load(*args, **kwargs)


def prepare_launch_operation(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate launch-operation preparation without importing the launcher at module load."""
    from system.lib.launchable_operations import prepare_launch_operation as _prepare_launch_operation

    return _prepare_launch_operation(*args, **kwargs)


def find_launchable_operation(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate launchable-operation lookup through the launch catalog authority."""
    from system.lib.launchable_operations import find_launchable_operation as _find_launchable_operation

    return _find_launchable_operation(*args, **kwargs)


def start_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate meta-mission run creation through the launch-operation authority."""
    from system.lib.launchable_operations import start_meta_mission_run as _start_meta_mission_run

    return _start_meta_mission_run(*args, **kwargs)


def launcher_meta_mission_env(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate launch environment construction through the meta-mission launcher."""
    from system.lib.launchable_operations import launcher_meta_mission_env as _launcher_meta_mission_env

    return _launcher_meta_mission_env(*args, **kwargs)


def artifact_refs_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Extract operation artifact references using the launcher parser."""
    from system.lib.launchable_operations import artifact_refs_from_operation_output as _artifact_refs_from_operation_output

    return _artifact_refs_from_operation_output(*args, **kwargs)


def operation_event_fields_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Extract orchestration event fields using the launcher output parser."""
    from system.lib.launchable_operations import (
        operation_event_fields_from_operation_output as _operation_event_fields_from_operation_output,
    )

    return _operation_event_fields_from_operation_output(*args, **kwargs)


def finalize_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
    """[ACTION] Delegate meta-mission run finalization to the launch-operation authority."""
    from system.lib.launchable_operations import finalize_meta_mission_run as _finalize_meta_mission_run

    return _finalize_meta_mission_run(*args, **kwargs)

REACTIONS_CONFIG_REL = "reactions.yaml"
REACTIONS_STATE_REL = "tools/meta/control/reactions_state.json"
REACTIONS_LEDGER_REL = "tools/meta/control/reactions_ledger.jsonl"
REACTIONS_STOP_FLAG_REL = "tools/meta/control/reactions_stop.flag"
ORCHESTRATION_EVENTS_REL = "tools/meta/control/orchestration_events.jsonl"
DEFAULT_POLL_SECONDS = 15
ENGINE_ACTOR_ID = "reactions_engine"
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
REACTION_TIMELINE_LIMIT = 24
REACTION_LEDGER_SCAN_LIMIT = 240
REACTION_TOPOLOGY_LIMIT = 160
REACTION_EPISODE_LIMIT = 32
REACTION_LINEAGE_REF_LIMIT = 8
REACTION_DIAGRAM_NODE_LIMIT = 220
REACTION_DIAGRAM_EDGE_LIMIT = 360
REACTION_DIAGRAM_FOCUS_LIMIT = 10
REACTION_DIAGRAM_MERMAID_NODE_LIMIT = 36
REACTION_DIAGRAM_MERMAID_EDGE_LIMIT = 48
REACTION_GRAPH_SCENE_CACHE_MAX_ENTRIES = 8
_REACTION_GRAPH_SCENE_CACHE_LOCK = threading.Lock()
_REACTION_GRAPH_SCENE_CACHE: dict[str, dict[str, Any]] = {}

REACTION_DIAGRAM_LANES = [
    ("runtime/control", "Runtime / Control"),
    ("signal/source", "Signal / Source"),
    ("predicate/gate", "Predicate / Gate"),
    ("reaction", "Reaction"),
    ("episode/run", "Episode / Run"),
    ("operation/output", "Operation / Output"),
    ("receiver/effect", "Receiver / Effect"),
    ("artifact/workitem/trace", "Artifact / WorkItem / Trace"),
]
REACTION_DIAGRAM_DOMAIN_ROWS = [
    ("raw_seed", "Raw Seed"),
    ("compliance", "Compliance"),
    ("standards", "Standards"),
    ("provider", "Provider"),
    ("hologram", "Hologram"),
    ("work_ledger", "Work Ledger"),
    ("lifecycle", "Lifecycle"),
    ("orchestration", "Orchestration"),
    ("other", "Other"),
]

# Reactions state schema v2 additive fields.
REACTIONS_STATE_SCHEMA_V2 = "reactions_state_v2"
REACTIONS_STATE_SCHEMA_V1 = "reactions_state_v1"
COMPLETED_DIGESTS_CAP = 500

# Volatile signal keys that must not participate in the ledger fingerprint.
# Coverage-bump paths deliberately tweak these to force a new signal digest;
# ledger_fingerprint deliberately ignores them so "same material, just a
# timestamp bump" can still dedupe a terminal outcome.
LEDGER_FINGERPRINT_VOLATILE_KEYS = frozenset(
    {
        "generated_at",
        "last_updated",
        "computed_at",
        "coverage_digest_bumped_at",
        "bumped_at",
        "as_of",
        "asof",
        "timestamp",
    }
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _now_dt() -> datetime:
    return datetime.now(timezone.utc)


def _string(value: Any) -> str:
    return value if isinstance(value, str) else ""


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _relative(repo_root: Path, path: Path) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except Exception:
        return str(path)


def _resolve(repo_root: Path, rel_path: str) -> Path:
    return repo_root / rel_path


def _write_python_std_compliance_coverage(repo_root: Path) -> dict[str, Any]:
    from system.lib.python_std_compliance_findings import write_python_std_compliance_coverage

    return write_python_std_compliance_coverage(repo_root=repo_root)


def write_python_std_compliance_coverage(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Refresh the Python standard compliance coverage artifact for reactions signals."""
    return _write_python_std_compliance_coverage(repo_root)


def _pid_running(pid: Any) -> bool:
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _event_id(prefix: str, now: datetime) -> str:
    stamp = now.strftime("%Y%m%dT%H%M%S")
    micro = f"{now.microsecond:06d}"
    seed = f"{prefix}:{now.isoformat()}:{os.getpid()}".encode("utf-8")
    fingerprint = hashlib.sha1(seed).hexdigest()[:10]
    return f"{prefix}_{stamp}_{micro}_0000_{fingerprint}"


def _stable_hex(parts: Sequence[Any], *, length: int = 16) -> str:
    payload = json.dumps([str(part or "") for part in parts], sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:length]


def _command_hash(command: Any) -> str | None:
    text = str(command or "").strip()
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _rendered_command_summary(command: Any) -> str | None:
    text = str(command or "").strip()
    if not text:
        return None
    try:
        argv = shlex.split(text)
    except ValueError:
        return _clip_text(text, limit=180)
    if not argv:
        return None
    if len(argv) <= 6:
        return _clip_text(" ".join(argv), limit=180)
    return _clip_text(" ".join(argv[:6]) + f" ... (+{len(argv) - 6} args)", limit=180)


def _new_reaction_run_id(
    *,
    reaction_id: str,
    operation_id: str,
    signal_digest: str,
    started_at: str,
) -> str:
    return "rxrun_" + _stable_hex(
        [reaction_id, operation_id, signal_digest, started_at, os.getpid()],
        length=20,
    )


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=False) + "\n")


def _load_jsonl_tail(path: Path, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        file_size = path.stat().st_size
        tail_bytes = min(file_size, max(64 * 1024, max(limit, 1) * 4096))
        with path.open("rb") as handle:
            if tail_bytes < file_size:
                handle.seek(file_size - tail_bytes)
                handle.readline()
            payload = handle.read().decode("utf-8", errors="replace")
        lines = payload.splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines[-max(limit, 1) :]:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            out.append(payload)
    return out


def _load_latest_orchestration_event(repo_root: Path) -> dict[str, Any] | None:
    events = _load_jsonl_tail(_resolve(repo_root, ORCHESTRATION_EVENTS_REL), limit=1)
    return events[-1] if events else None


def _load_latest_operation_event(
    repo_root: Path,
    *,
    operation_id: str | None = None,
    family: str | None = None,
    limit: int = 200,
) -> dict[str, Any] | None:
    events = _load_jsonl_tail(_resolve(repo_root, ORCHESTRATION_EVENTS_REL), limit=limit)
    op_token = str(operation_id or "").strip()
    family_token = str(family or "").strip()
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if str(event.get("kind") or "").strip() != "operation_launched":
            continue
        if op_token and str(event.get("operation_id") or "").strip() != op_token:
            continue
        resolved_parameters = event.get("resolved_parameters")
        if family_token:
            if not isinstance(resolved_parameters, Mapping):
                continue
            if str(resolved_parameters.get("family") or "").strip() != family_token:
                continue
        return dict(event)
    return None


def _load_latest_lifecycle_boundary_event(
    repo_root: Path,
    *,
    agent_surface: str | None = None,
    boundary: str | None = None,
    limit: int = 200,
) -> dict[str, Any] | None:
    """Find the most recent ``session_lifecycle_boundary`` row matching filters.

    Mirrors ``_load_latest_operation_event``'s shape but filters on
    ``kind == "session_lifecycle_boundary"`` rows produced by
    ``.claude/hooks/runtime_hook.py::_emit_stop_lifecycle_signal`` (and any
    future SessionEnd/SessionStart hooks that share the row schema canonised
    in ``codex/doctrine/paper_modules/runtime_hook_ladder.md``). The
    ``agent_surface`` and ``boundary`` filters read from ``payload`` because
    that is where the runtime hook places them; they are optional and
    treated as match-anything when blank.

    The returned dict is the raw JSONL row including its ``stable_digest``;
    the gather-signal layer surfaces that digest as
    ``stable_signal_digest`` so ``_compute_signal_digest`` reuses it
    directly and ``dedupe_by: signal_digest`` blocks re-fires of the same
    boundary without any new dedupe machinery.
    """
    events = _load_jsonl_tail(_resolve(repo_root, ORCHESTRATION_EVENTS_REL), limit=limit)
    surface_token = str(agent_surface or "").strip()
    boundary_token = str(boundary or "").strip()
    for event in reversed(events):
        if not isinstance(event, dict):
            continue
        if str(event.get("kind") or "").strip() != "session_lifecycle_boundary":
            continue
        payload = event.get("payload")
        if not isinstance(payload, Mapping):
            continue
        if surface_token and str(payload.get("agent_surface") or "").strip() != surface_token:
            continue
        if boundary_token and str(payload.get("boundary") or "").strip() != boundary_token:
            continue
        return dict(event)
    return None


def reactions_state_path(repo_root: Path) -> Path:
    """[ACTION] Resolve the reactions engine runtime-state JSON path under a repo root."""
    return _resolve(repo_root, REACTIONS_STATE_REL)


def reactions_ledger_path(repo_root: Path) -> Path:
    """[ACTION] Resolve the reactions engine append-only ledger path under a repo root."""
    return _resolve(repo_root, REACTIONS_LEDGER_REL)


def reactions_stop_flag_path(repo_root: Path) -> Path:
    """[ACTION] Resolve the stop-flag path that asks the detached engine loop to exit."""
    return _resolve(repo_root, REACTIONS_STOP_FLAG_REL)


def orchestration_events_path(repo_root: Path) -> Path:
    """[ACTION] Resolve the orchestration-events JSONL path used by engine visibility surfaces."""
    return _resolve(repo_root, ORCHESTRATION_EVENTS_REL)


def default_reactions_state() -> dict[str, Any]:
    """[ACTION] Build the schema-versioned default reactions runtime state object."""
    return {
        "kind": "reactions_state",
        "schema_version": REACTIONS_STATE_SCHEMA_V2,
        "compat": {"previous": REACTIONS_STATE_SCHEMA_V1},
        "desired_armed": False,
        "effective_armed": False,
        "pid": None,
        "status": "disarmed",
        "cursor_event_id": None,
        "cursor_recorded_at": None,
        "active_reaction_id": None,
        "awaiting_barriers": [],
        "per_reaction": {},
        "last_tick_at": None,
        "last_error": None,
        "last_fired_at": None,
        # Schema v2: rolling window of terminal outcomes keyed by signal digest.
        # See `_record_completed_digest` for the entry shape.
        "completed_digests": {},
    }


def _migrate_reactions_state_to_v2(state: dict[str, Any]) -> dict[str, Any]:
    """One-shot forward migration: add completed_digests, bump schema_version.

    Missing ledger_fingerprint fields on individual per-reaction runtime entries
    are left blank — treated as "unknown → allow one more fire" — so the first
    post-upgrade tick does not mass-suppress real work.
    """
    if not isinstance(state, dict):
        return state
    state.setdefault("completed_digests", {})
    if not isinstance(state.get("completed_digests"), dict):
        state["completed_digests"] = {}
    previous = str(state.get("schema_version") or "").strip()
    if previous != REACTIONS_STATE_SCHEMA_V2:
        state["schema_version"] = REACTIONS_STATE_SCHEMA_V2
        if previous and previous != REACTIONS_STATE_SCHEMA_V2:
            compat = state.get("compat")
            if not isinstance(compat, dict):
                compat = {}
            compat.setdefault("previous", previous)
            state["compat"] = compat
    return state


def load_reactions_state(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Load reactions runtime state and migrate it to the current schema."""
    state = _load_json(reactions_state_path(repo_root)) or default_reactions_state()
    return _migrate_reactions_state_to_v2(state)


def save_reactions_state(repo_root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    """[ACTION] Persist a merged reactions runtime state object with schema migration applied."""
    merged = default_reactions_state()
    merged.update(dict(state))
    _migrate_reactions_state_to_v2(merged)
    _atomic_write_json(reactions_state_path(repo_root), merged)
    return merged


def ensure_reactions_state(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Load or initialize the reactions runtime state file for a repo root."""
    state = load_reactions_state(repo_root)
    if not reactions_state_path(repo_root).exists():
        save_reactions_state(repo_root, state)
    return state


def _parse_fast_config_scalar(raw: str) -> Any:
    value = raw.strip()
    if value == "{}":
        return {}
    if value == "[]":
        return []
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    lowered = value.lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value


def _split_fast_config_pair(stripped: str) -> tuple[str, Any] | None:
    if ":" not in stripped:
        return None
    key, raw_value = stripped.split(":", 1)
    key = key.strip()
    if not key:
        return None
    return key, _parse_fast_config_scalar(raw_value)


def _load_reactions_config_fast(repo_root: Path) -> dict[str, Any] | None:
    """Parse the small reactions.yaml subset needed by cached pulse snapshots.

    This intentionally covers the authored reactions config shape: a top-level
    reactions list with simple nested source/predicate/action/gate mappings.
    Live engine paths still use the full YAML loader.
    """
    path = _resolve(repo_root, REACTIONS_CONFIG_REL)
    if not path.exists():
        return {
            "kind": "reactions_config",
            "schema_version": "reactions_config_v1",
            "reactions": [],
        }
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None

    payload: dict[str, Any] = {
        "kind": "reactions_config",
        "schema_version": "reactions_config_v1",
        "reactions": [],
    }
    reactions: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    section: str | None = None
    subsection: str | None = None
    in_reactions = False
    current_base_indent = 2

    for raw in lines:
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        stripped = raw.strip()
        if stripped.startswith("- ") and (indent == 2 or (indent == 0 and in_reactions)):
            if current:
                reactions.append(current)
            current = {}
            section = None
            subsection = None
            current_base_indent = indent
            pair = _split_fast_config_pair(stripped[2:].strip())
            if pair:
                current[pair[0]] = pair[1]
            continue
        if indent == 0:
            if stripped == "reactions:":
                in_reactions = True
                continue
            pair = _split_fast_config_pair(stripped)
            if pair and pair[0] in {"kind", "schema_version"}:
                payload[pair[0]] = pair[1]
            continue
        if current is None or ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        value_text = raw_value.strip()
        top_indent = current_base_indent + 2
        nested_indent = current_base_indent + 4
        subnested_indent = current_base_indent + 6
        if indent <= top_indent:
            subsection = None
            if not value_text:
                section = key
                current.setdefault(section, {})
            else:
                current[key] = _parse_fast_config_scalar(value_text)
                section = None
            continue
        if indent == nested_indent and section:
            target = current.setdefault(section, {})
            if not isinstance(target, dict):
                continue
            if not value_text:
                subsection = key
                target.setdefault(subsection, {})
            else:
                target[key] = _parse_fast_config_scalar(value_text)
                subsection = None
            continue
        if indent >= subnested_indent and section and subsection:
            target = current.setdefault(section, {})
            if not isinstance(target, dict):
                continue
            nested = target.setdefault(subsection, {})
            if isinstance(nested, dict):
                nested[key] = _parse_fast_config_scalar(value_text)

    if current:
        reactions.append(current)
    if not reactions and any(line.strip().startswith("- ") for line in lines):
        return None
    payload["reactions"] = reactions
    return payload


def _load_reactions_config_yaml(repo_root: Path) -> dict[str, Any]:
    yaml_module, loader = _yaml_loader()
    path = _resolve(repo_root, REACTIONS_CONFIG_REL)
    try:
        payload = yaml_module.load(path.read_text(encoding="utf-8"), Loader=loader) or {}
    except Exception:
        payload = {}
    return payload if isinstance(payload, dict) else {}


def load_reactions_config(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Load reactions.yaml into the normalized reactions-config envelope."""
    path = _resolve(repo_root, REACTIONS_CONFIG_REL)
    if not path.exists():
        return {
            "kind": "reactions_config",
            "schema_version": "reactions_config_v1",
            "reactions": [],
        }
    payload = _load_reactions_config_yaml(repo_root)
    payload.setdefault("kind", "reactions_config")
    payload.setdefault("schema_version", "reactions_config_v1")
    reactions = payload.get("reactions")
    payload["reactions"] = reactions if isinstance(reactions, list) else []
    return payload


def _reaction_sort_key(reaction: Mapping[str, Any]) -> tuple[int, str]:
    priority = str(reaction.get("priority") or "medium").strip().lower()
    return (PRIORITY_ORDER.get(priority, 99), str(reaction.get("reaction_id") or ""))


def _reaction_runtime_entry(state: Mapping[str, Any], reaction_id: str) -> dict[str, Any]:
    per_reaction = state.get("per_reaction") if isinstance(state.get("per_reaction"), Mapping) else {}
    entry = per_reaction.get(reaction_id)
    return dict(entry) if isinstance(entry, Mapping) else {}


def _set_reaction_runtime_entry(state: dict[str, Any], reaction_id: str, entry: Mapping[str, Any]) -> None:
    per_reaction = state.get("per_reaction")
    if not isinstance(per_reaction, dict):
        per_reaction = {}
        state["per_reaction"] = per_reaction
    per_reaction[reaction_id] = dict(entry)


def _resolve_field(payload: Mapping[str, Any], field_path: str) -> Any:
    current: Any = payload
    for token in str(field_path or "").split("."):
        if not token:
            continue
        if not isinstance(current, Mapping):
            return None
        current = current.get(token)
    return current


def _predicate_matches(signal: Mapping[str, Any], predicate: Mapping[str, Any]) -> bool:
    field = str(predicate.get("field") or "").strip()
    operator = str(predicate.get("operator") or "").strip().lower()
    expected = predicate.get("value")
    actual = _resolve_field(signal, field) if field else signal
    if operator == "nonempty":
        if actual is None:
            return False
        if isinstance(actual, (list, tuple, dict, str)):
            return len(actual) > 0
        return bool(actual)
    if operator in {"ge", "gt", "eq"}:
        if actual is None:
            return False
        try:
            if isinstance(actual, (int, float)) or isinstance(expected, (int, float)):
                actual_num = float(actual)
                expected_num = float(expected)
                if operator == "ge":
                    return actual_num >= expected_num
                if operator == "gt":
                    return actual_num > expected_num
                return actual_num == expected_num
        except (TypeError, ValueError):
            actual_text = str(actual)
            expected_text = str(expected)
            if operator == "ge":
                return actual_text >= expected_text
            if operator == "gt":
                return actual_text > expected_text
            return actual_text == expected_text
    return False


def _compute_signal_digest(reaction: Mapping[str, Any], signal: Mapping[str, Any]) -> str:
    stable_signal_digest = str(signal.get("stable_signal_digest") or "").strip()
    if stable_signal_digest:
        return stable_signal_digest
    payload = {
        "reaction_id": reaction.get("reaction_id"),
        "source_kind": _safe_mapping(reaction.get("source")).get("kind"),
        "signal": signal,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _strip_volatile_for_fingerprint(value: Any) -> Any:
    """Deep-copy ``value`` minus volatile timestamp fields.

    The fingerprint is intended to answer "has the source *material* changed?",
    not "did any timestamp bump?". Coverage-bump paths in the raw-seed pipeline
    deliberately shift generated_at to force a fresh signal digest; we want
    those bumps to trip the digest check but *not* the fingerprint check.
    """
    if isinstance(value, Mapping):
        return {
            key: _strip_volatile_for_fingerprint(item)
            for key, item in value.items()
            if key not in LEDGER_FINGERPRINT_VOLATILE_KEYS
        }
    if isinstance(value, list):
        return [_strip_volatile_for_fingerprint(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_volatile_for_fingerprint(item) for item in value)
    return value


def _compute_ledger_fingerprint(
    reaction: Mapping[str, Any], signal: Mapping[str, Any]
) -> str:
    """Content fingerprint for a reaction signal, excluding volatile timestamps.

    Pairs with ``signal_digest`` so dedupe can distinguish "same digest, same
    content" (suppress repeat-fail loops) from "same digest, different content"
    (rare digest collision or forced re-fire; allow).
    """
    payload = {
        "reaction_id": reaction.get("reaction_id"),
        "source_kind": _safe_mapping(reaction.get("source")).get("kind"),
        "signal": _strip_volatile_for_fingerprint(dict(signal or {})),
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _completed_digest_entry(
    state: Mapping[str, Any], signal_digest: str
) -> dict[str, Any]:
    completed = state.get("completed_digests") if isinstance(state.get("completed_digests"), Mapping) else {}
    entry = completed.get(signal_digest)
    return dict(entry) if isinstance(entry, Mapping) else {}


def _record_completed_digest(
    state: dict[str, Any],
    *,
    signal_digest: str,
    ledger_fingerprint: str,
    outcome: str,
    operation_id: str,
    completed_at: str,
    reaction_id: str,
    cap: int = COMPLETED_DIGESTS_CAP,
) -> None:
    """Append a terminal outcome to the rolling completed_digests window."""
    if not signal_digest:
        return
    completed = state.get("completed_digests")
    if not isinstance(completed, dict):
        completed = {}
        state["completed_digests"] = completed
    completed[signal_digest] = {
        "outcome": outcome,
        "operation_id": operation_id,
        "completed_at": completed_at,
        "ledger_fingerprint": ledger_fingerprint,
        "reaction_id": reaction_id,
    }
    if len(completed) > cap:
        # Evict oldest by completed_at string (ISO-8601 sorts lexicographically).
        ordered = sorted(
            completed.items(),
            key=lambda kv: str(kv[1].get("completed_at") or ""),
        )
        # Keep the most-recent `cap` entries.
        keep = ordered[-cap:]
        completed.clear()
        for digest_key, entry in keep:
            completed[digest_key] = entry


def _render_parameter_template(value: Any, signal: Mapping[str, Any]) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith("{signal.") and value.endswith("}"):
        field_path = value[len("{signal.") : -1]
        resolved = _resolve_field(signal, field_path)
        if isinstance(resolved, list):
            return ",".join(str(item).strip() for item in resolved if str(item).strip())
        return resolved
    return value


def _render_action_parameters(action: Mapping[str, Any], signal: Mapping[str, Any]) -> dict[str, Any]:
    parameters = action.get("parameters") if isinstance(action.get("parameters"), Mapping) else {}
    rendered: dict[str, Any] = {}
    for key, value in parameters.items():
        resolved = _render_parameter_template(value, signal)
        if resolved is not None:
            rendered[str(key)] = resolved
    return rendered


def _clip_text(value: Any, *, limit: int = 160) -> str:
    text = str(value if value is not None else "").strip()
    if len(text) <= limit:
        return text
    return text[: max(limit - 3, 0)].rstrip() + "..."


def _display_value(value: Any, *, list_limit: int = 5, text_limit: int = 120) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}".rstrip("0").rstrip(".")
    if isinstance(value, (int, str)):
        return _clip_text(value, limit=text_limit)
    if isinstance(value, (list, tuple)):
        items = [_display_value(item, text_limit=32) for item in value[:list_limit]]
        if len(value) > list_limit:
            items.append(f"+{len(value) - list_limit}")
        return ", ".join(items) if items else "none"
    if isinstance(value, Mapping):
        scalar_items: list[str] = []
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)) or item is None:
                scalar_items.append(f"{key}={_display_value(item, text_limit=32)}")
            if len(scalar_items) >= list_limit:
                break
        if scalar_items:
            suffix = f", +{len(value) - list_limit}" if len(value) > list_limit else ""
            return _clip_text(", ".join(scalar_items) + suffix, limit=text_limit)
        return f"{len(value)} fields"
    return _clip_text(value, limit=text_limit)


def _human_label(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    return " ".join(part for part in text.replace("-", "_").split("_") if part).title()


def _signal_attribute(label: str, value: Any) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "display_value": _display_value(value),
    }


def _reaction_domain(
    reaction_id: str,
    *,
    source_kind: str | None,
    action_operation_id: str | None,
    source: Mapping[str, Any],
) -> str:
    source_token = str(source_kind or "").strip()
    if source_token == "raw_seed_coverage":
        return str(source.get("substrate") or "raw_seed").strip() or "raw_seed"
    source_domain = {
        "python_std_compliance_coverage": "python_std",
        "operation_event": "operation_event",
        "hologram_build_status": "hologram",
        "work_ledger_status": "work_ledger",
        "orchestration_event": "orchestration",
        "lifecycle_boundary": "agent_lifecycle",
        "provider_model_catalog_signal": "provider",
        "standard_skill_gap_signal": "standards",
        "compliance_coverage_signal": "compliance",
    }.get(source_token)
    if source_domain:
        return source_domain
    for prefix in (
        "raw_seed",
        "semantic_routes",
        "python_std",
        "provider",
        "standard_skill",
        "compliance",
        "hologram",
        "work_ledger",
        "claude_stop",
        "route",
        "rediscovery",
        "subagent",
    ):
        if reaction_id.startswith(prefix):
            return prefix
    operation = str(action_operation_id or "").strip()
    if operation:
        return operation.split("_", 1)[0]
    return reaction_id.split("_", 1)[0] if "_" in reaction_id else "reaction"


def _predicate_view(
    predicate: Mapping[str, Any],
    signal: Mapping[str, Any],
    *,
    matched: bool,
) -> dict[str, Any]:
    field = str(predicate.get("field") or "").strip()
    operator = str(predicate.get("operator") or "").strip().lower()
    expected = predicate.get("value")
    actual = _resolve_field(signal, field) if field else signal
    subject = field or "signal"
    if operator == "nonempty":
        summary = f"{subject} is nonempty"
    elif operator:
        summary = f"{subject} {operator} {_display_value(expected)}"
    else:
        summary = "No predicate declared"
    return {
        "field": field or None,
        "operator": operator or None,
        "expected": expected,
        "expected_display": _display_value(expected),
        "actual": actual,
        "actual_display": _display_value(actual),
        "matched": bool(matched),
        "summary": summary,
    }


def _signal_summary(source_kind: str | None, signal: Mapping[str, Any]) -> dict[str, Any]:
    source_token = str(source_kind or signal.get("kind") or "unknown").strip() or "unknown"
    attrs: list[dict[str, Any]] = []
    summary = _human_label(source_token)

    def add(label: str, value: Any) -> None:
        if value is not None and value != "":
            attrs.append(_signal_attribute(label, value))

    if source_token == "raw_seed_coverage":
        counts = _safe_mapping(signal.get("counts"))
        top_group = _safe_mapping(signal.get("top_pending_routing_group"))
        add("family", signal.get("family"))
        add("substrate", signal.get("substrate"))
        add("pending shards", counts.get("pending_routing_shards"))
        add("pending bins", counts.get("pending_routing_bins"))
        add("fresh bins", counts.get("fresh_pending_bins"))
        add("top group", top_group.get("group_id"))
        summary = (
            f"{_human_label(signal.get('substrate') or 'raw_seed')} coverage: "
            f"{_display_value(counts.get('pending_routing_shards'))} pending shards"
        )
    elif source_token == "python_std_compliance_coverage":
        counts = _safe_mapping(signal.get("counts"))
        triggers = _safe_mapping(signal.get("triggers"))
        active_campaign = _safe_mapping(signal.get("active_campaign"))
        add("unapplied findings", counts.get("findings_unapplied"))
        add("pending bins", counts.get("bins_pending"))
        add("approval required", triggers.get("approval_required"))
        add("drain ready", triggers.get("drain_ready"))
        add("campaign", active_campaign.get("campaign_slug"))
        add("campaign state", active_campaign.get("lifecycle_state"))
        summary = (
            "Python STD compliance: "
            f"{_display_value(counts.get('findings_unapplied'))} unapplied findings"
        )
    elif source_token == "operation_event":
        resolved = _safe_mapping(signal.get("resolved_parameters"))
        add("operation", signal.get("operation_id"))
        add("return code", signal.get("returncode"))
        add("family", resolved.get("family"))
        add("event", signal.get("event_id"))
        summary = (
            f"Operation {signal.get('operation_id') or 'unknown'} "
            f"returned {_display_value(signal.get('returncode'))}"
        )
    elif source_token == "hologram_build_status":
        add("stale count", signal.get("stale_count"))
        add("stale phases", signal.get("stale_phase_ids"))
        add("all current", signal.get("all_current"))
        summary = f"Hologram build: {_display_value(signal.get('stale_count'))} stale phases"
    elif source_token == "work_ledger_status":
        counts = _safe_mapping(signal.get("counts"))
        triggers = _safe_mapping(signal.get("triggers"))
        add("active claims", counts.get("active_claims"))
        add("effective sessions", counts.get("effective_active_sessions"))
        add("orphaned sessions", counts.get("orphaned_active_sessions"))
        add("stale", triggers.get("stale"))
        summary = f"Work ledger: {_display_value(counts.get('active_claims'))} active claims"
    elif source_token == "lifecycle_boundary" or str(signal.get("kind") or "") == "session_lifecycle_boundary":
        add("agent", signal.get("agent_surface"))
        add("boundary", signal.get("boundary"))
        add("session", signal.get("session_id"))
        summary = (
            f"{_human_label(signal.get('agent_surface'))} "
            f"{_human_label(signal.get('boundary'))} boundary"
        )
    elif source_token == "provider_model_catalog_signal":
        add("row count", signal.get("row_count"))
        add("target row", signal.get("next_target_row_id") or signal.get("first_target_row_id"))
        add("provider", signal.get("next_provider_id") or signal.get("first_provider_id"))
        summary = f"Provider catalog: {_display_value(signal.get('row_count'))} rows"
    elif source_token == "standard_skill_gap_signal":
        add("missing skills", signal.get("missing_authoring_skill"))
        add("paired", signal.get("paired_explicit"))
        add("standards", signal.get("standards_total"))
        add("sample missing", signal.get("sample_missing"))
        summary = (
            "Standard-skill gap: "
            f"{_display_value(signal.get('missing_authoring_skill'))} missing authoring skills"
        )
    elif source_token == "compliance_coverage_signal":
        add("ready now", signal.get("ready_now_count"))
        add("below floor", signal.get("below_floor_count"))
        add("average rate", signal.get("average_known_compliance_rate"))
        add("standards", signal.get("standards_total"))
        summary = (
            "Compliance coverage: "
            f"{_display_value(signal.get('ready_now_count'))} ready, "
            f"{_display_value(signal.get('below_floor_count'))} below floor"
        )
    else:
        add("kind", signal.get("kind") or source_token)
        add("digest", signal.get("stable_signal_digest") or signal.get("digest"))
        for key, value in signal.items():
            if key in {"kind", "stable_signal_digest", "digest"}:
                continue
            if isinstance(value, (str, int, float, bool)) or value is None:
                add(str(key), value)
            if len(attrs) >= 6:
                break
        summary = f"{_human_label(source_token)} signal"

    return {
        "source_kind": source_token,
        "summary": _clip_text(summary, limit=180),
        "attributes": attrs[:8],
        "generated_at": signal.get("generated_at") or signal.get("recorded_at") or signal.get("ts"),
        "source_path": signal.get("source_path") or signal.get("path"),
        "raw_key_count": len(signal),
    }


def _reason_code(preview_reason: str) -> str:
    reason = preview_reason.lower()
    if "completed_digest_fingerprint" in reason:
        return "deduped_terminal_fingerprint"
    if "signal_digest" in reason:
        return "deduped_signal_digest"
    if "cooldown" in reason:
        return "cooldown_active"
    if "disarmed" in reason:
        return "reaction_disarmed"
    if "predicate" in reason:
        return "predicate_not_matched"
    if "would fire" in reason:
        return "eligible_now"
    return reason.replace(" ", "_") or "unknown"


def _state_tone(state: str) -> str:
    return {
        "eligible": "amber",
        "firing": "cyan",
        "blocked": "amber",
        "cooldown": "amber",
        "failed": "red",
        "completed": "green",
        "disabled": "muted",
        "waiting": "muted",
    }.get(state, "muted")


def _reaction_state_view(
    *,
    reaction_id: str,
    engine_armed: bool,
    active_reaction_id: Any,
    barriers: list[dict[str, Any]],
    runtime_entry: Mapping[str, Any],
    evaluation: Mapping[str, Any],
) -> dict[str, Any]:
    preview_reason = str(evaluation.get("preview_reason") or "").strip()
    last_result = str(runtime_entry.get("last_result") or "").strip().lower()
    effective_armed = bool(evaluation.get("effective_armed"))
    matched = bool(evaluation.get("matched"))
    can_fire = bool(evaluation.get("can_fire"))
    cooldown_active = bool(evaluation.get("cooldown_active"))

    if str(active_reaction_id or "") == reaction_id:
        state = "firing"
        reason = "Active reaction has an outstanding operation barrier."
        code = "active_reaction"
    elif barriers:
        barrier_kind = str(barriers[0].get("kind") or "")
        if barrier_kind == "cooldown":
            state = "cooldown"
            reason = "Cooldown barrier is still active."
            code = "cooldown_active"
        else:
            state = "blocked"
            reason = barriers[0].get("label") or "Reaction is waiting on a wake barrier."
            code = "awaiting_barrier"
    elif not engine_armed:
        state = "disabled"
        reason = "Engine is disarmed."
        code = "engine_disarmed"
    elif not effective_armed:
        state = "disabled"
        reason = "Reaction is disarmed by runtime override."
        code = "reaction_disarmed"
    elif cooldown_active:
        state = "cooldown"
        reason = "Cooldown is active."
        code = "cooldown_active"
    elif can_fire:
        state = "eligible"
        reason = "Predicate matched and no runtime gate is blocking this reaction."
        code = "eligible_now"
    elif last_result == "failed":
        state = "failed"
        reason = runtime_entry.get("last_error") or preview_reason or "Last run failed."
        code = "last_run_failed"
    elif last_result == "completed":
        state = "completed"
        reason = preview_reason or "Last run completed."
        code = _reason_code(preview_reason)
    else:
        state = "waiting"
        reason = preview_reason or "Waiting for a matching signal."
        code = _reason_code(preview_reason)

    return {
        "state": state,
        "label": _human_label(state),
        "tone": _state_tone(state),
        "matched": matched,
        "eligible": can_fire,
        "reason_code": code,
        "why_not_eligible": None if can_fire else _clip_text(reason, limit=220),
        "preview_reason": preview_reason or None,
        "sort_rank": {
            "firing": 0,
            "failed": 1,
            "blocked": 2,
            "eligible": 3,
            "cooldown": 4,
            "waiting": 5,
            "completed": 6,
            "disabled": 7,
        }.get(state, 9),
    }


def _normalize_reaction_event(row: Mapping[str, Any]) -> dict[str, Any] | None:
    reaction_id = str(row.get("reaction_id") or "").strip()
    kind = str(row.get("kind") or "").strip()
    if not reaction_id or not kind.startswith("reaction_"):
        return None
    at = (
        row.get("recorded_at")
        or row.get("fired_at")
        or row.get("completed_at")
        or row.get("failed_at")
        or row.get("suppressed_at")
    )
    status = {
        "reaction_fired": "fired",
        "reaction_completed": "completed",
        "reaction_failed": "failed",
        "reaction_suppressed": "suppressed",
        "reaction_fired_manual_proof": "manual_proof",
        "reaction_state_changed": "state_changed",
    }.get(kind, kind.replace("reaction_", ""))
    summary = str(row.get("summary") or "").strip()
    if not summary:
        if status == "completed":
            summary = f"{reaction_id} completed {row.get('operation_id') or 'operation'}."
        elif status == "failed":
            summary = f"{reaction_id} failed {row.get('operation_id') or 'operation'}."
        elif status == "suppressed":
            summary = f"{reaction_id} suppressed: {row.get('reason') or 'runtime gate'}."
        elif status == "fired":
            summary = f"{reaction_id} fired {row.get('operation_id') or 'operation'}."
        else:
            summary = f"{reaction_id}: {status}."
    written = row.get("written") if isinstance(row.get("written"), list) else []
    reaction_run_id = str(row.get("reaction_run_id") or row.get("run_id") or "").strip() or None
    return {
        "event_id": row.get("event_id"),
        "kind": kind,
        "status": status,
        "reaction_run_id": reaction_run_id,
        "reaction_id": reaction_id,
        "operation_id": row.get("operation_id"),
        "recorded_at": at,
        "fired_at": row.get("fired_at"),
        "completed_at": row.get("completed_at"),
        "failed_at": row.get("failed_at"),
        "suppressed_at": row.get("suppressed_at"),
        "duration_ms": row.get("duration_ms"),
        "returncode": row.get("returncode"),
        "signal_digest": row.get("signal_digest"),
        "ledger_fingerprint": row.get("ledger_fingerprint"),
        "dedupe_key": row.get("dedupe_key"),
        "reason": row.get("reason"),
        "error": row.get("error"),
        "summary": _clip_text(summary, limit=220),
        "log_path": row.get("log_path"),
        "artifact_paths": [str(item) for item in written[:8]],
        "command": row.get("command"),
        "command_hash": _command_hash(row.get("command")),
        "rendered_command_summary": _rendered_command_summary(row.get("command")),
        "parameters": dict(row.get("parameters")) if isinstance(row.get("parameters"), Mapping) else {},
        "stdout_excerpt_ref": "ledger:stdout" if row.get("stdout") else None,
        "stderr_excerpt_ref": "ledger:stderr" if row.get("stderr") else None,
    }


def _build_reaction_event_views(
    repo_root: Path,
    *,
    timeline_limit: int = REACTION_TIMELINE_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]], dict[str, Any]]:
    rows = _load_jsonl_tail(
        reactions_ledger_path(repo_root),
        limit=max(REACTION_LEDGER_SCAN_LIMIT, timeline_limit),
    )
    normalized: list[dict[str, Any]] = []
    by_reaction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in reversed(rows):
        event = _normalize_reaction_event(row)
        if not event:
            continue
        normalized.append(event)
        bucket = by_reaction[event["reaction_id"]]
        if len(bucket) < 6:
            bucket.append(event)
    return normalized[:timeline_limit], dict(by_reaction), {
        "ledger_rows_scanned": len(rows),
        "ledger_tail_limit": max(REACTION_LEDGER_SCAN_LIMIT, timeline_limit),
        "ledger_truncated": len(rows) >= max(REACTION_LEDGER_SCAN_LIMIT, timeline_limit),
        "normalized_events": normalized,
    }


def _causal_chain_view(
    *,
    reaction_id: str,
    domain: str,
    label: Any,
    source_kind: str | None,
    predicate: Mapping[str, Any],
    state: Mapping[str, Any],
    action_operation_id: str | None,
    recent_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    chain = [
        {
            "kind": "signal",
            "node_id": f"signal:{reaction_id}",
            "label": _human_label(source_kind or "unknown signal"),
            "domain": domain,
        },
        {
            "kind": "predicate",
            "node_id": f"predicate:{reaction_id}",
            "label": predicate.get("summary") or "Predicate",
            "matched": predicate.get("matched"),
            "domain": domain,
        },
        {
            "kind": "reaction",
            "node_id": f"reaction:{reaction_id}",
            "label": label or reaction_id,
            "state": state.get("state"),
            "domain": domain,
        },
    ]
    if action_operation_id:
        chain.append(
            {
                "kind": "operation",
                "node_id": f"operation:{action_operation_id}",
                "label": action_operation_id,
                "domain": domain,
            }
        )
    latest_artifacts = []
    for event in recent_events:
        latest_artifacts.extend(event.get("artifact_paths") or [])
    if latest_artifacts:
        chain.append(
            {
                "kind": "artifact",
                "node_id": f"artifact:{reaction_id}",
                "label": _display_value(latest_artifacts, list_limit=3, text_limit=90),
                "artifact_paths": latest_artifacts[:5],
                "domain": domain,
            }
        )
    return chain


def _build_reactions_topology(reactions: list[dict[str, Any]]) -> dict[str, Any]:
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []

    def add_node(node: Mapping[str, Any]) -> None:
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            return
        if node_id not in nodes_by_id:
            nodes_by_id[node_id] = dict(node)

    for reaction in reactions:
        chain = reaction.get("causal_chain") if isinstance(reaction.get("causal_chain"), list) else []
        previous_id: str | None = None
        for node in chain:
            if not isinstance(node, Mapping):
                continue
            add_node(node)
            node_id = str(node.get("node_id") or "").strip()
            if previous_id and node_id:
                edges.append(
                    {
                        "edge_id": f"{previous_id}->{node_id}",
                        "source": previous_id,
                        "target": node_id,
                        "reaction_id": reaction.get("reaction_id"),
                        "state": _safe_mapping(reaction.get("state")).get("state"),
                        "domain": reaction.get("domain"),
                    }
                )
            previous_id = node_id or previous_id
            if len(nodes_by_id) + len(edges) >= REACTION_TOPOLOGY_LIMIT:
                break
        if len(nodes_by_id) + len(edges) >= REACTION_TOPOLOGY_LIMIT:
            break

    return {
        "schema": "reaction_topology_v1",
        "layout": "stable_lanes",
        "lanes": ["signal", "predicate", "reaction", "operation", "artifact"],
        "nodes": list(nodes_by_id.values()),
        "edges": edges,
        "truncated": len(nodes_by_id) + len(edges) >= REACTION_TOPOLOGY_LIMIT,
    }


def _diagram_domain_id(domain: Any) -> str:
    token = str(domain or "").strip().lower()
    if token.startswith("raw_seed") or token == "raw":
        return "raw_seed"
    if token in {"compliance", "compliance_coverage"}:
        return "compliance"
    if token in {"python_std", "standard_skill", "standard_skill_gap", "standards"}:
        return "standards"
    if token.startswith("provider"):
        return "provider"
    if token.startswith("hologram"):
        return "hologram"
    if token.startswith("work_ledger"):
        return "work_ledger"
    if token in {"agent_lifecycle", "lifecycle", "lifecycle_boundary"}:
        return "lifecycle"
    if token in {"orchestration", "operation_event"}:
        return "orchestration"
    return "other"


def _diagram_node_ports(kind: str) -> list[dict[str, str]]:
    ports = [
        {"id": "in", "role": "target", "side": "left"},
        {"id": "out", "role": "source", "side": "right"},
    ]
    if kind == "predicate":
        ports.extend(
            [
                {"id": "out_pass", "role": "source", "side": "right"},
                {"id": "out_block", "role": "source", "side": "bottom"},
            ]
        )
    elif kind in {"gate", "barrier"}:
        ports.extend(
            [
                {"id": "out_pass", "role": "source", "side": "right"},
                {"id": "out_block", "role": "source", "side": "bottom"},
            ]
        )
    elif kind == "reaction":
        ports.extend(
            [
                {"id": "in_gate", "role": "target", "side": "top"},
                {"id": "out_fire", "role": "source", "side": "right"},
                {"id": "out_control", "role": "source", "side": "bottom"},
                {"id": "out_suppress", "role": "source", "side": "bottom"},
            ]
        )
    elif kind == "episode":
        ports.extend(
            [
                {"id": "out_result", "role": "source", "side": "right"},
                {"id": "out_trace", "role": "source", "side": "bottom"},
            ]
        )
    elif kind == "operation":
        ports.extend(
            [
                {"id": "out_receiver", "role": "source", "side": "right"},
                {"id": "out_artifact", "role": "source", "side": "right"},
            ]
        )
    elif kind == "operation_receiver":
        ports.append({"id": "out_effect", "role": "source", "side": "right"})
    return ports


def _diagram_payload_preview(value: Any, *, limit: int = 8) -> Any:
    if isinstance(value, Mapping):
        preview: dict[str, Any] = {}
        for key, item in value.items():
            if isinstance(item, (str, int, float, bool)) or item is None:
                preview[str(key)] = item
            elif isinstance(item, (list, tuple)):
                preview[str(key)] = [_display_value(row, text_limit=36) for row in item[:3]]
            elif isinstance(item, Mapping):
                preview[str(key)] = _display_value(item, list_limit=4, text_limit=80)
            if len(preview) >= limit:
                break
        return preview
    if isinstance(value, (list, tuple)):
        return [_diagram_payload_preview(item, limit=4) for item in value[:limit]]
    return _display_value(value)


def _diagram_edge_style(relation: str) -> str:
    return {
        "blocks": "blocked",
        "fails": "danger",
        "suppresses": "dashed",
        "dispatches_to": "dashed",
        "declares_effect_on": "dashed",
        "receiver_unresolved": "dotted",
        "observed_effect_on": "solid",
        "guarded_by": "dotted",
        "controlled_by": "dotted",
        "links_trace": "dotted",
        "fires": "active",
        "enqueues": "solid",
        "completes": "success",
        "writes": "solid",
        "passes": "solid",
        "watches": "solid",
        "evaluates": "solid",
    }.get(relation, "solid")


def _diagram_edge_tone(relation: str, state: Any = None) -> str:
    if relation in {"blocks", "fails"}:
        return "red" if relation == "fails" else "amber"
    if relation in {"dispatches_to", "declares_effect_on"}:
        return "amber"
    if relation == "receiver_unresolved":
        return "muted"
    if relation == "observed_effect_on":
        return "green"
    if relation in {"fires", "enqueues"}:
        return "cyan"
    if relation in {"completes", "writes", "passes"}:
        return "green" if relation == "completes" else "muted"
    if relation in {"suppresses", "guarded_by", "controlled_by", "links_trace"}:
        return "muted"
    return _state_tone(str(state or "waiting"))


def _receiver_domain_from_side_effect(side_effect: Any, *, fallback_domain: Any = None) -> str:
    token = str(side_effect or "").strip().lower()
    if not token:
        return _diagram_domain_id(fallback_domain)
    if "raw_seed" in token:
        return "raw_seed"
    if "compliance" in token:
        return "compliance"
    if "standard" in token or "python_std" in token:
        return "standards"
    if "provider" in token:
        return "provider"
    if "hologram" in token:
        return "hologram"
    if "work_ledger" in token or "ledger" in token:
        return "work_ledger"
    if "meta_mission" in token or "mission" in token or "lifecycle" in token:
        return "lifecycle"
    if "repo_or_runtime" in token or "runtime" in token or "operation" in token:
        return "orchestration"
    if "unknown" in token:
        return "other"
    return _diagram_domain_id(fallback_domain)


def _receiver_claim_payload(
    *,
    operation_id: str,
    receiver_class: str,
    evidence_class: str,
    claim_ceiling: str,
    side_effect: Any = None,
    native_ref: Mapping[str, Any] | None = None,
    observed_effect: bool = False,
) -> dict[str, Any]:
    return {
        "schema": "reaction_receiver_proxy_v1",
        "operation_id": operation_id,
        "receiver_class": receiver_class,
        "evidence_class": evidence_class,
        "claim_ceiling": claim_ceiling,
        "side_effect": side_effect,
        "observed_effect": bool(observed_effect),
        "native_ref": dict(native_ref or {"kind": "operation", "id": operation_id}),
    }


def _observed_receiver_effects_by_reaction_operation(
    episodes: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], list[dict[str, Any]]]:
    effects: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for episode in episodes:
        if str(episode.get("status") or "").strip().lower() != "completed":
            continue
        reaction_id = str(episode.get("reaction_id") or "").strip()
        operation_id = str(episode.get("operation_id") or "").strip()
        if not reaction_id or not operation_id:
            continue
        for artifact_path in list(episode.get("artifact_paths") or [])[:4]:
            artifact = str(artifact_path or "").strip()
            if not artifact:
                continue
            effects[(reaction_id, operation_id)].append(
                {
                    "schema": "reaction_observed_receiver_effect_v1",
                    "reaction_id": reaction_id,
                    "operation_id": operation_id,
                    "episode_id": episode.get("episode_id"),
                    "artifact_path": artifact,
                    "evidence_class": "reaction_episode.artifact_paths",
                    "claim_ceiling": "observed_effect_within_reaction_ledger_window",
                    "terminal_event_id": episode.get("terminal_event_id"),
                    "ledger_event_ids": list(episode.get("ledger_event_ids") or [])[:8],
                }
            )
    return effects


def _diagram_mermaid_id(node_id: str) -> str:
    digest = hashlib.sha1(node_id.encode("utf-8")).hexdigest()[:12]
    return f"n_{digest}"


def _diagram_mermaid_label(value: Any) -> str:
    text = _clip_text(value, limit=48)
    return text.replace('"', "'").replace("\n", " ")


def _build_mermaid_debug_export(
    *,
    nodes_by_id: Mapping[str, dict[str, Any]],
    edges: list[dict[str, Any]],
    focus_path: Mapping[str, Any] | None = None,
) -> str:
    if focus_path:
        focus_node_ids = [str(item) for item in focus_path.get("node_ids") or []]
        focus_edge_ids = {str(item) for item in focus_path.get("edge_ids") or []}
        selected_nodes = [nodes_by_id[item] for item in focus_node_ids if item in nodes_by_id]
        selected_edges = [edge for edge in edges if edge.get("id") in focus_edge_ids]
    else:
        selected_nodes = sorted(
            nodes_by_id.values(),
            key=lambda row: int(row.get("rank") or 0),
        )[:REACTION_DIAGRAM_MERMAID_NODE_LIMIT]
        selected_ids = {str(row.get("id")) for row in selected_nodes}
        selected_edges = [
            edge
            for edge in edges
            if edge.get("source") in selected_ids and edge.get("target") in selected_ids
        ][:REACTION_DIAGRAM_MERMAID_EDGE_LIMIT]
    if not selected_nodes:
        return "flowchart LR\n  empty[\"No reaction diagram nodes\"]"
    lines = ["flowchart LR"]
    for node in selected_nodes[:REACTION_DIAGRAM_MERMAID_NODE_LIMIT]:
        lines.append(f"  {_diagram_mermaid_id(str(node.get('id')))}[\"{_diagram_mermaid_label(node.get('short_label') or node.get('label'))}\"]")
    selected_node_ids = {str(row.get("id")) for row in selected_nodes[:REACTION_DIAGRAM_MERMAID_NODE_LIMIT]}
    for edge in selected_edges[:REACTION_DIAGRAM_MERMAID_EDGE_LIMIT]:
        source = str(edge.get("source") or "")
        target = str(edge.get("target") or "")
        if source not in selected_node_ids or target not in selected_node_ids:
            continue
        relation = str(edge.get("relation") or "")
        arrow = "-.->" if edge.get("line_style_hint") == "dotted" else ("-->|" + relation + "|")
        if edge.get("line_style_hint") == "dashed":
            arrow = "-. " + relation + " .->"
        if arrow.startswith("-->|"):
            lines.append(f"  {_diagram_mermaid_id(source)} {arrow} {_diagram_mermaid_id(target)}")
        else:
            lines.append(f"  {_diagram_mermaid_id(source)} {arrow} {_diagram_mermaid_id(target)}")
    return "\n".join(lines)


def _episode_relation(status: Any) -> str:
    token = str(status or "").strip().lower()
    if token == "failed":
        return "fails"
    if token == "completed":
        return "completes"
    if token == "suppressed":
        return "suppresses"
    if token in {"running", "fired"}:
        return "enqueues"
    return "enqueues"


def _build_reaction_diagram(
    *,
    generated_at: str,
    engine_status: str,
    engine_armed: bool,
    active_reaction_id: Any,
    reactions: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    awaiting_barriers: list[dict[str, Any]],
    attention: Mapping[str, Any],
    summary: Mapping[str, Any],
    signal_mode: str,
) -> dict[str, Any]:
    lane_order = {lane_id: index for index, (lane_id, _label) in enumerate(REACTION_DIAGRAM_LANES)}
    domain_order = {domain_id: index for index, (domain_id, _label) in enumerate(REACTION_DIAGRAM_DOMAIN_ROWS)}
    nodes_by_id: dict[str, dict[str, Any]] = {}
    edges: list[dict[str, Any]] = []
    edge_by_id: dict[str, dict[str, Any]] = {}
    inspectors: dict[str, dict[str, Any]] = {}
    reaction_paths: dict[str, dict[str, Any]] = defaultdict(lambda: {"node_ids": [], "edge_ids": []})
    episode_paths: dict[str, dict[str, Any]] = defaultdict(lambda: {"node_ids": [], "edge_ids": []})
    observed_effects_by_reaction_operation = _observed_receiver_effects_by_reaction_operation(episodes)
    truncated = False

    def remember_path(path: dict[str, Any], *, node_ids: Sequence[str] = (), edge_ids: Sequence[str] = ()) -> None:
        for node_id in node_ids:
            if node_id and node_id not in path["node_ids"]:
                path["node_ids"].append(node_id)
        for edge_id in edge_ids:
            if edge_id and edge_id not in path["edge_ids"]:
                path["edge_ids"].append(edge_id)

    def add_inspector(
        ref: str,
        *,
        kind: str,
        title: str,
        summary_text: str,
        state: str | None,
        tone: str,
        metrics: Mapping[str, Any] | None = None,
        refs: list[dict[str, Any]] | None = None,
        payload: Any = None,
    ) -> None:
        if ref in inspectors:
            return
        inspectors[ref] = {
            "schema": "reaction_diagram_inspector_v1",
            "ref": ref,
            "kind": kind,
            "title": _clip_text(title, limit=120),
            "summary": _clip_text(summary_text, limit=220),
            "state": state,
            "tone": tone,
            "metrics": dict(metrics or {}),
            "refs": list(refs or []),
            "payload_preview": _diagram_payload_preview(payload),
        }

    def add_node(
        *,
        node_id: str,
        kind: str,
        label: str,
        lane: str,
        domain: Any,
        subtitle: str = "",
        state: str | None = None,
        tone: str | None = None,
        priority: Any = None,
        badges: list[dict[str, Any]] | None = None,
        metrics: Mapping[str, Any] | None = None,
        refs: list[dict[str, Any]] | None = None,
        collapsed_default: bool = False,
        detail_level: str = "summary",
        payload: Any = None,
    ) -> str:
        nonlocal truncated
        if node_id in nodes_by_id:
            node = nodes_by_id[node_id]
            if metrics:
                node_metrics = _safe_mapping(node.get("metrics"))
                for key, value in metrics.items():
                    if key not in node_metrics:
                        node_metrics[str(key)] = value
                node["metrics"] = node_metrics
            return node_id
        if len(nodes_by_id) >= REACTION_DIAGRAM_NODE_LIMIT:
            truncated = True
            return node_id
        domain_id = _diagram_domain_id(domain)
        stable_order = len(nodes_by_id) + 1
        rank = lane_order.get(lane, 99) * 1000 + domain_order.get(domain_id, 99) * 100 + stable_order
        inspector_ref = f"diagram:{node_id}"
        node = {
            "id": node_id,
            "kind": kind,
            "label": _clip_text(label, limit=120),
            "short_label": _clip_text(_human_label(label), limit=42),
            "subtitle": _clip_text(subtitle, limit=160),
            "domain": domain_id,
            "lane": lane,
            "rank": rank,
            "stable_order": stable_order,
            "state": state,
            "tone": tone or _state_tone(str(state or "waiting")),
            "priority": priority,
            "parent_cluster_id": f"domain:{domain_id}",
            "ports": _diagram_node_ports(kind),
            "badges": list(badges or []),
            "metrics": dict(metrics or {}),
            "refs": list(refs or []),
            "inspector_ref": inspector_ref,
            "collapsed_default": bool(collapsed_default),
            "detail_level": detail_level,
        }
        nodes_by_id[node_id] = node
        add_inspector(
            inspector_ref,
            kind=kind,
            title=label,
            summary_text=subtitle or label,
            state=state,
            tone=str(node["tone"]),
            metrics=metrics,
            refs=refs,
            payload=payload,
        )
        return node_id

    def add_edge(
        *,
        source: str,
        target: str,
        relation: str,
        source_port: str = "out",
        target_port: str = "in",
        reaction_id: str | None = None,
        episode_ids: Sequence[str] = (),
        gate_ids: Sequence[str] = (),
        domain: Any = None,
        priority: Any = None,
        label: str | None = None,
        state: Any = None,
        bundle_id: str | None = None,
        refs: list[dict[str, Any]] | None = None,
    ) -> str:
        nonlocal truncated
        edge_seed = "|".join(
            [
                source,
                source_port,
                relation,
                target,
                target_port,
                str(reaction_id or ""),
                ",".join(str(item) for item in episode_ids),
                ",".join(str(item) for item in gate_ids),
            ]
        )
        edge_id = f"edge:{hashlib.sha1(edge_seed.encode('utf-8')).hexdigest()[:16]}"
        if edge_id in edge_by_id:
            edge = edge_by_id[edge_id]
            edge["recent_count"] = int(edge.get("recent_count") or 1) + 1
            for episode_id in episode_ids:
                if episode_id not in edge["episode_ids"]:
                    edge["episode_ids"].append(str(episode_id))
            for gate_id in gate_ids:
                if gate_id not in edge["gate_ids"]:
                    edge["gate_ids"].append(str(gate_id))
            return edge_id
        if len(edges) >= REACTION_DIAGRAM_EDGE_LIMIT:
            truncated = True
            return edge_id
        edge = {
            "id": edge_id,
            "source": source,
            "target": target,
            "relation": relation,
            "label": label or _human_label(relation),
            "source_port": source_port,
            "target_port": target_port,
            "bundle_id": bundle_id or f"bundle:{relation}:{source}:{target}",
            "line_style_hint": _diagram_edge_style(relation),
            "state": state,
            "tone": _diagram_edge_tone(relation, state),
            "domain": _diagram_domain_id(domain),
            "priority": priority,
            "reaction_id": reaction_id,
            "episode_ids": [str(item) for item in episode_ids if item],
            "gate_ids": [str(item) for item in gate_ids if item],
            "recent_count": 1,
            "refs": list(refs or []),
            "inspector_ref": f"diagram:{edge_id}",
        }
        edge_by_id[edge_id] = edge
        edges.append(edge)
        add_inspector(
            str(edge["inspector_ref"]),
            kind="edge",
            title=f"{source} {relation} {target}",
            summary_text=label or _human_label(relation),
            state=str(state) if state is not None else None,
            tone=str(edge["tone"]),
            metrics={"recent_count": edge["recent_count"]},
            refs=refs,
            payload=edge,
        )
        return edge_id

    engine_node_id = add_node(
        node_id="runtime:engine",
        kind="runtime_control",
        label="Reaction engine",
        lane="runtime/control",
        domain="orchestration",
        subtitle=f"{_human_label(engine_status)} / {'armed' if engine_armed else 'disarmed'}",
        state=engine_status,
        tone="cyan" if engine_armed else "muted",
        metrics={
            "reaction_count": summary.get("reaction_count", len(reactions)),
            "eligible_now": summary.get("eligible_now", 0),
            "blocked_count": summary.get("blocked_count", 0),
            "failed_count": summary.get("failed_count", 0),
        },
        refs=[{"kind": "runtime_state", "path": REACTIONS_STATE_REL}],
        payload={"engine_status": engine_status, "engine_armed": engine_armed},
    )

    for reaction in reactions:
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        if not reaction_id:
            continue
        state_view = _safe_mapping(reaction.get("state"))
        state = str(state_view.get("state") or "unknown")
        domain_id = _diagram_domain_id(reaction.get("domain"))
        priority = reaction.get("priority")
        source_kind = str(reaction.get("source_kind") or "").strip() or "unknown"
        signal_payload = _safe_mapping(reaction.get("current_signal"))
        signal_node_id = f"signal:{domain_id}:{source_kind}"
        predicate_node_id = f"predicate:{reaction_id}"
        reaction_node_id = f"reaction:{reaction_id}"
        operation_id = str(_safe_mapping(reaction.get("action")).get("operation_id") or "").strip()
        signal_summary = _safe_mapping(reaction.get("signal_summary"))
        predicate = _safe_mapping(reaction.get("predicate"))
        eligibility = _safe_mapping(reaction.get("eligibility"))
        source_metrics = {
            "attribute_count": len(signal_summary.get("attributes") or []),
            "last_signal_digest": reaction.get("last_signal_digest"),
        }
        add_node(
            node_id=signal_node_id,
            kind="signal",
            label=_human_label(source_kind),
            lane="signal/source",
            domain=domain_id,
            subtitle=str(signal_summary.get("summary") or source_kind),
            state="matched" if predicate.get("matched") else "watching",
            tone="green" if predicate.get("matched") else "muted",
            priority=priority,
            badges=[{"label": "cached" if signal_mode == "cached" else "live", "tone": "muted"}],
            metrics=source_metrics,
            refs=[{"kind": "source_kind", "id": source_kind}],
            collapsed_default=True,
            payload=signal_payload,
        )
        add_node(
            node_id=predicate_node_id,
            kind="predicate",
            label=str(predicate.get("summary") or "Predicate"),
            lane="predicate/gate",
            domain=domain_id,
            subtitle=f"actual: {predicate.get('actual_display') or 'unknown'}",
            state="passed" if predicate.get("matched") else "blocked",
            tone="green" if predicate.get("matched") else "amber",
            priority=priority,
            metrics={
                "matched": bool(predicate.get("matched")),
                "field": predicate.get("field"),
                "operator": predicate.get("operator"),
            },
            refs=[{"kind": "reaction", "id": reaction_id}],
            payload=predicate,
        )
        add_node(
            node_id=reaction_node_id,
            kind="reaction",
            label=str(reaction.get("label") or reaction_id),
            lane="reaction",
            domain=domain_id,
            subtitle=str(state_view.get("why_not_eligible") or state_view.get("preview_reason") or state_view.get("label") or ""),
            state=state,
            tone=str(state_view.get("tone") or _state_tone(state)),
            priority=priority,
            badges=[
                {"label": str(priority or "priority"), "tone": "muted"},
                {"label": "override" if reaction.get("override_armed") is not None else "default", "tone": "muted"},
            ],
            metrics={
                "would_fire_now": bool(reaction.get("would_fire_now")),
                "effective_armed": bool(reaction.get("effective_armed")),
                "reason_code": state_view.get("reason_code"),
            },
            refs=[{"kind": "reaction", "id": reaction_id}],
            payload=reaction,
        )
        watches_edge = add_edge(
            source=engine_node_id,
            target=signal_node_id,
            relation="watches",
            target_port="in",
            reaction_id=reaction_id,
            domain=domain_id,
            priority=priority,
            bundle_id=f"bundle:watch:{source_kind}",
            refs=[{"kind": "reaction", "id": reaction_id}],
        )
        evaluates_edge = add_edge(
            source=signal_node_id,
            target=predicate_node_id,
            relation="evaluates",
            reaction_id=reaction_id,
            domain=domain_id,
            priority=priority,
            bundle_id=f"bundle:signal:{signal_node_id}",
            refs=[{"kind": "reaction", "id": reaction_id}],
        )
        predicate_relation = "passes" if predicate.get("matched") else "blocks"
        predicate_edge = add_edge(
            source=predicate_node_id,
            target=reaction_node_id,
            relation=predicate_relation,
            source_port="out_pass" if predicate_relation == "passes" else "out_block",
            target_port="in_gate",
            reaction_id=reaction_id,
            domain=domain_id,
            priority=priority,
            state=state,
            gate_ids=[str(eligibility.get("primary_blocking_gate_id") or "predicate")] if predicate_relation == "blocks" else [],
            refs=[{"kind": "reaction", "id": reaction_id}],
        )
        controlled_edge = add_edge(
            source=engine_node_id,
            target=reaction_node_id,
            relation="controlled_by",
            target_port="in_gate",
            reaction_id=reaction_id,
            domain=domain_id,
            priority=priority,
            state=state,
            bundle_id="bundle:engine:controls",
            refs=[{"kind": "reaction", "id": reaction_id}],
        )
        remember_path(
            reaction_paths[reaction_id],
            node_ids=[engine_node_id, signal_node_id, predicate_node_id, reaction_node_id],
            edge_ids=[watches_edge, evaluates_edge, predicate_edge, controlled_edge],
        )
        primary_gate_id = str(eligibility.get("primary_blocking_gate_id") or "").strip()
        if primary_gate_id:
            gate_node_id = f"gate:{reaction_id}:{primary_gate_id}"
            add_node(
                node_id=gate_node_id,
                kind="gate",
                label=_human_label(primary_gate_id),
                lane="predicate/gate",
                domain=domain_id,
                subtitle=str(eligibility.get("operator_actionability") or state_view.get("why_not_eligible") or ""),
                state="blocked",
                tone="amber",
                priority=priority,
                refs=[{"kind": "reaction", "id": reaction_id}, {"kind": "gate", "id": primary_gate_id}],
                collapsed_default=True,
                payload=eligibility,
            )
            gate_edge = add_edge(
                source=gate_node_id,
                target=reaction_node_id,
                relation="blocks",
                source_port="out_block",
                target_port="in_gate",
                reaction_id=reaction_id,
                domain=domain_id,
                priority=priority,
                state=state,
                gate_ids=[primary_gate_id],
                refs=[{"kind": "reaction", "id": reaction_id}, {"kind": "gate", "id": primary_gate_id}],
            )
            remember_path(reaction_paths[reaction_id], node_ids=[gate_node_id], edge_ids=[gate_edge])
        if operation_id:
            operation_node_id = f"operation:{operation_id}"
            operation_safety = _safe_mapping(reaction.get("operation_safety"))
            add_node(
                node_id=operation_node_id,
                kind="operation",
                label=operation_id,
                lane="operation/output",
                domain=domain_id,
                subtitle=str(operation_safety.get("description") or "Launchable operation"),
                state=str(operation_safety.get("safety_state") or "configured"),
                tone="green" if operation_safety.get("known_operation") else "amber",
                priority=priority,
                badges=[{"label": str(operation_safety.get("side_effect_level") or "operation"), "tone": "muted"}],
                metrics={
                    "known_operation": bool(operation_safety.get("known_operation")),
                    "requires_confirmation": bool(operation_safety.get("requires_confirmation")),
                },
                refs=[{"kind": "operation", "id": operation_id}],
                payload=operation_safety,
            )
            relation = "fires" if state in {"eligible", "firing"} else ("fails" if state == "failed" else "enqueues")
            if state in {"waiting", "disabled", "cooldown", "blocked"} and not reaction.get("would_fire_now"):
                relation = "suppresses"
            operation_edge = add_edge(
                source=reaction_node_id,
                target=operation_node_id,
                relation=relation,
                source_port="out_fire" if relation in {"fires", "enqueues", "fails"} else "out_suppress",
                reaction_id=reaction_id,
                domain=domain_id,
                priority=priority,
                state=state,
                bundle_id=f"bundle:operation:{operation_id}",
                refs=[{"kind": "reaction", "id": reaction_id}, {"kind": "operation", "id": operation_id}],
            )
            remember_path(reaction_paths[reaction_id], node_ids=[operation_node_id], edge_ids=[operation_edge])
            if bool(operation_safety.get("known_operation")):
                receiver_node_id = f"receiver:operation:{operation_id}"
                observed_effects = observed_effects_by_reaction_operation.get((reaction_id, operation_id), [])
                observed_effect_count = len(observed_effects)
                receiver_payload = _receiver_claim_payload(
                    operation_id=operation_id,
                    receiver_class="declared_operation_receiver",
                    evidence_class="action_operation_id+reaction_episode.artifact_paths"
                    if observed_effect_count
                    else "action_operation_id",
                    claim_ceiling="declared_dispatch_target_with_observed_artifact_effect"
                    if observed_effect_count
                    else "declared_dispatch_target_not_observed_effect",
                    native_ref={
                        "kind": "operation",
                        "id": operation_id,
                        "observed_effect_count": observed_effect_count,
                    },
                    observed_effect=bool(observed_effect_count),
                )
                add_node(
                    node_id=receiver_node_id,
                    kind="operation_receiver",
                    label=operation_id,
                    lane="receiver/effect",
                    domain=domain_id,
                    subtitle="Declared dispatch target with observed artifact evidence in the reaction ledger."
                    if observed_effect_count
                    else "Declared dispatch target; effect not observed by config alone.",
                    state="declared",
                    tone="green" if observed_effect_count else "amber",
                    priority=priority,
                    badges=[
                        {"label": "declared", "tone": "amber"},
                        {"label": "observed effect", "tone": "green"}
                        if observed_effect_count
                        else {"label": "not observed", "tone": "muted"},
                    ],
                    metrics={
                        "observed_effect": bool(observed_effect_count),
                        "observed_effect_count": observed_effect_count,
                        "receiver_claim_ceiling": "observed_effect"
                        if observed_effect_count
                        else "declared",
                    },
                    refs=[
                        {"kind": "operation", "id": operation_id},
                        {"kind": "evidence", "id": "reaction.action.operation_id"},
                    ],
                    payload=receiver_payload,
                )
                dispatch_edge = add_edge(
                    source=operation_node_id,
                    target=receiver_node_id,
                    relation="dispatches_to",
                    source_port="out_receiver",
                    reaction_id=reaction_id,
                    domain=domain_id,
                    priority=priority,
                    label="declared dispatch",
                    state="declared",
                    bundle_id=f"bundle:receiver:operation:{operation_id}",
                    refs=[
                        {"kind": "reaction", "id": reaction_id},
                        {"kind": "operation", "id": operation_id},
                        {"kind": "evidence", "id": "reaction.action.operation_id"},
                    ],
                )
                receiver_node_ids = [receiver_node_id]
                receiver_edge_ids = [dispatch_edge]
                for side_effect in list(operation_safety.get("side_effects") or [])[:4]:
                    side_effect_text = str(side_effect or "").strip()
                    if not side_effect_text or side_effect_text == "unknown_operation":
                        continue
                    effect_domain = _receiver_domain_from_side_effect(side_effect_text, fallback_domain=domain_id)
                    effect_node_id = f"receiver:effect:{operation_id}:{_stable_hex([operation_id, side_effect_text], length=10)}"
                    effect_payload = _receiver_claim_payload(
                        operation_id=operation_id,
                        receiver_class="side_effect_domain_receiver",
                        evidence_class="operation_safety.side_effects",
                        claim_ceiling="side_effect_domain_declared_not_observed_effect",
                        side_effect=side_effect_text,
                        native_ref={"kind": "operation_safety.side_effect", "id": side_effect_text},
                    )
                    add_node(
                        node_id=effect_node_id,
                        kind="effect_domain",
                        label=_human_label(side_effect_text),
                        lane="receiver/effect",
                        domain=effect_domain,
                        subtitle="Safety-declared effect domain; not an observed write/result.",
                        state="declared",
                        tone="amber",
                        priority=priority,
                        badges=[
                            {"label": "effect domain", "tone": "amber"},
                            {"label": "unobserved", "tone": "muted"},
                        ],
                        metrics={
                            "observed_effect": False,
                            "receiver_claim_ceiling": "side_effect_domain",
                        },
                        refs=[
                            {"kind": "operation", "id": operation_id},
                            {"kind": "side_effect", "id": side_effect_text},
                        ],
                        collapsed_default=True,
                        payload=effect_payload,
                    )
                    effect_edge = add_edge(
                        source=receiver_node_id,
                        target=effect_node_id,
                        relation="declares_effect_on",
                        source_port="out_effect",
                        reaction_id=reaction_id,
                        domain=effect_domain,
                        priority=priority,
                        label="declares effect domain",
                        state="declared",
                        bundle_id=f"bundle:receiver:effect:{side_effect_text}",
                        refs=[
                            {"kind": "operation", "id": operation_id},
                            {"kind": "side_effect", "id": side_effect_text},
                        ],
                    )
                    receiver_node_ids.append(effect_node_id)
                    receiver_edge_ids.append(effect_edge)
                remember_path(
                    reaction_paths[reaction_id],
                    node_ids=receiver_node_ids,
                    edge_ids=receiver_edge_ids,
                )
            else:
                unresolved_node_id = f"receiver:unresolved:{operation_id}"
                unresolved_payload = _receiver_claim_payload(
                    operation_id=operation_id,
                    receiver_class="unresolved_operation_receiver",
                    evidence_class="unknown_operation_id",
                    claim_ceiling="no_receiver_claim_catalog_miss",
                    native_ref={"kind": "operation", "id": operation_id},
                )
                add_node(
                    node_id=unresolved_node_id,
                    kind="unresolved_receiver",
                    label="Unresolved receiver",
                    lane="receiver/effect",
                    domain="other",
                    subtitle=f"{operation_id} is not in launchable_operations.",
                    state="unresolved",
                    tone="muted",
                    priority=priority,
                    badges=[
                        {"label": "unresolved", "tone": "muted"},
                        {"label": "not observed", "tone": "muted"},
                    ],
                    metrics={
                        "observed_effect": False,
                        "receiver_claim_ceiling": "none",
                    },
                    refs=[
                        {"kind": "operation", "id": operation_id},
                        {"kind": "evidence", "id": "unknown_operation_id"},
                    ],
                    payload=unresolved_payload,
                )
                unresolved_edge = add_edge(
                    source=operation_node_id,
                    target=unresolved_node_id,
                    relation="receiver_unresolved",
                    source_port="out_receiver",
                    reaction_id=reaction_id,
                    domain="other",
                    priority=priority,
                    label="receiver unresolved",
                    state="unresolved",
                    bundle_id=f"bundle:receiver:unresolved:{operation_id}",
                    refs=[
                        {"kind": "reaction", "id": reaction_id},
                        {"kind": "operation", "id": operation_id},
                        {"kind": "evidence", "id": "unknown_operation_id"},
                    ],
                )
                remember_path(
                    reaction_paths[reaction_id],
                    node_ids=[unresolved_node_id],
                    edge_ids=[unresolved_edge],
                )

    for barrier in awaiting_barriers:
        reaction_id = str(barrier.get("reaction_id") or "").strip()
        barrier_kind = str(barrier.get("kind") or "barrier")
        barrier_domain = _diagram_domain_id("orchestration")
        if reaction_id:
            reaction_domain = next(
                (
                    _diagram_domain_id(row.get("domain"))
                    for row in reactions
                    if str(row.get("reaction_id") or "") == reaction_id
                ),
                barrier_domain,
            )
            barrier_domain = reaction_domain
        barrier_node_id = f"barrier:{reaction_id or 'global'}:{barrier_kind}"
        add_node(
            node_id=barrier_node_id,
            kind="barrier",
            label=str(barrier.get("label") or _human_label(barrier_kind)),
            lane="predicate/gate",
            domain=barrier_domain,
            subtitle=str(barrier.get("operation_id") or barrier.get("wake_at") or "wake barrier"),
            state=str(barrier.get("status") or "blocked"),
            tone="amber",
            priority="high",
            refs=[{"kind": "barrier", "id": barrier_kind}, {"kind": "reaction", "id": reaction_id}],
            payload=barrier,
        )
        control_edge = add_edge(
            source=engine_node_id,
            target=barrier_node_id,
            relation="controlled_by",
            target_port="in",
            reaction_id=reaction_id or None,
            domain=barrier_domain,
            priority="high",
            bundle_id="bundle:engine:barriers",
            refs=[{"kind": "barrier", "id": barrier_kind}],
        )
        if reaction_id:
            reaction_node_id = f"reaction:{reaction_id}"
            guarded_edge = add_edge(
                source=reaction_node_id,
                target=barrier_node_id,
                relation="guarded_by",
                source_port="out_control",
                target_port="in",
                reaction_id=reaction_id,
                domain=barrier_domain,
                priority="high",
                gate_ids=[barrier_kind],
                refs=[{"kind": "barrier", "id": barrier_kind}, {"kind": "reaction", "id": reaction_id}],
            )
            blocks_edge = add_edge(
                source=barrier_node_id,
                target=reaction_node_id,
                relation="blocks",
                source_port="out_block",
                target_port="in_gate",
                reaction_id=reaction_id,
                domain=barrier_domain,
                priority="high",
                gate_ids=[barrier_kind],
                refs=[{"kind": "barrier", "id": barrier_kind}, {"kind": "reaction", "id": reaction_id}],
            )
            remember_path(
                reaction_paths[reaction_id],
                node_ids=[barrier_node_id],
                edge_ids=[control_edge, guarded_edge, blocks_edge],
            )

    for episode in episodes:
        episode_id = str(episode.get("episode_id") or "").strip()
        reaction_id = str(episode.get("reaction_id") or "").strip()
        if not episode_id or not reaction_id:
            continue
        search = _safe_mapping(episode.get("search_attributes"))
        domain_id = _diagram_domain_id(search.get("domain") or episode.get("domain"))
        status = str(episode.get("status") or "unknown")
        episode_node_id = f"episode:{episode_id}"
        operation_id = str(episode.get("operation_id") or search.get("operation_id") or "").strip()
        add_node(
            node_id=episode_node_id,
            kind="episode",
            label=f"{reaction_id} {status}",
            lane="episode/run",
            domain=domain_id,
            subtitle=str(episode.get("summary") or episode.get("episode_id_source") or ""),
            state=status,
            tone="red" if status == "failed" else ("green" if status == "completed" else "amber"),
            priority=search.get("priority"),
            badges=[{"label": str(episode.get("episode_id_source") or "episode"), "tone": "muted"}],
            metrics={
                "duration_ms": episode.get("duration_ms"),
                "returncode": episode.get("returncode"),
                "event_count": len(episode.get("event_ids") or []),
            },
            refs=[{"kind": "episode", "id": episode_id}, {"kind": "reaction", "id": reaction_id}],
            payload=episode,
        )
        reaction_node_id = f"reaction:{reaction_id}"
        fires_edge = add_edge(
            source=reaction_node_id,
            target=episode_node_id,
            relation="fires" if status != "suppressed" else "suppresses",
            source_port="out_fire" if status != "suppressed" else "out_suppress",
            reaction_id=reaction_id,
            episode_ids=[episode_id],
            domain=domain_id,
            priority=search.get("priority"),
            state=status,
            refs=[{"kind": "episode", "id": episode_id}, {"kind": "reaction", "id": reaction_id}],
        )
        remember_path(reaction_paths[reaction_id], node_ids=[episode_node_id], edge_ids=[fires_edge])
        remember_path(episode_paths[episode_id], node_ids=[reaction_node_id, episode_node_id], edge_ids=[fires_edge])
        if operation_id:
            operation_node_id = f"operation:{operation_id}"
            add_node(
                node_id=operation_node_id,
                kind="operation",
                label=operation_id,
                lane="operation/output",
                domain=domain_id,
                subtitle="Episode operation",
                state=status,
                tone="red" if status == "failed" else ("green" if status == "completed" else "amber"),
                priority=search.get("priority"),
                refs=[{"kind": "operation", "id": operation_id}],
                collapsed_default=True,
                payload=episode,
            )
            result_edge = add_edge(
                source=episode_node_id,
                target=operation_node_id,
                relation=_episode_relation(status),
                source_port="out_result",
                reaction_id=reaction_id,
                episode_ids=[episode_id],
                domain=domain_id,
                priority=search.get("priority"),
                state=status,
                bundle_id=f"bundle:operation:{operation_id}:episodes",
                refs=[{"kind": "episode", "id": episode_id}, {"kind": "operation", "id": operation_id}],
            )
            remember_path(reaction_paths[reaction_id], node_ids=[operation_node_id], edge_ids=[result_edge])
            remember_path(episode_paths[episode_id], node_ids=[operation_node_id], edge_ids=[result_edge])
            for index, artifact_path in enumerate(list(episode.get("artifact_paths") or [])[:2]):
                artifact_node_id = f"artifact:{hashlib.sha1(str(artifact_path).encode('utf-8')).hexdigest()[:12]}"
                add_node(
                    node_id=artifact_node_id,
                    kind="artifact",
                    label=Path(str(artifact_path)).name or str(artifact_path),
                    lane="artifact/workitem/trace",
                    domain=domain_id,
                    subtitle=str(artifact_path),
                    state="written",
                    tone="green",
                    priority=search.get("priority"),
                    refs=[{"kind": "path", "path": str(artifact_path)}],
                    collapsed_default=True,
                    detail_level="detail" if index == 0 else "summary",
                    payload={"path": str(artifact_path), "episode_id": episode_id},
                )
                artifact_edge = add_edge(
                    source=operation_node_id,
                    target=artifact_node_id,
                    relation="writes",
                    source_port="out_artifact",
                    reaction_id=reaction_id,
                    episode_ids=[episode_id],
                    domain=domain_id,
                    priority=search.get("priority"),
                    state=status,
                    refs=[{"kind": "path", "path": str(artifact_path)}],
                )
                remember_path(reaction_paths[reaction_id], node_ids=[artifact_node_id], edge_ids=[artifact_edge])
                remember_path(episode_paths[episode_id], node_ids=[artifact_node_id], edge_ids=[artifact_edge])
                receiver_node_id = f"receiver:operation:{operation_id}"
                observed_effects = observed_effects_by_reaction_operation.get((reaction_id, operation_id), [])
                matching_effect = next(
                    (
                        effect
                        for effect in observed_effects
                        if str(effect.get("artifact_path") or "") == str(artifact_path)
                    ),
                    None,
                )
                if matching_effect and receiver_node_id in nodes_by_id:
                    observed_edge = add_edge(
                        source=receiver_node_id,
                        target=artifact_node_id,
                        relation="observed_effect_on",
                        source_port="out_effect",
                        reaction_id=reaction_id,
                        episode_ids=[episode_id],
                        domain=domain_id,
                        priority=search.get("priority"),
                        label="observed artifact effect",
                        state="observed",
                        bundle_id=f"bundle:receiver:observed:{operation_id}",
                        refs=[
                            {"kind": "episode", "id": episode_id},
                            {"kind": "operation", "id": operation_id},
                            {"kind": "path", "path": str(artifact_path)},
                            {"kind": "evidence", "id": "reaction_episode.artifact_paths"},
                            {
                                "kind": "claim_ceiling",
                                "id": "observed_effect_within_reaction_ledger_window",
                            },
                        ],
                    )
                    remember_path(
                        reaction_paths[reaction_id],
                        node_ids=[receiver_node_id, artifact_node_id],
                        edge_ids=[observed_edge],
                    )
                    remember_path(
                        episode_paths[episode_id],
                        node_ids=[receiver_node_id, artifact_node_id],
                        edge_ids=[observed_edge],
                    )
        trace_binding = _safe_mapping(episode.get("trace_binding"))
        trace_id = str(trace_binding.get("trace_id") or "").strip()
        if trace_id:
            trace_node_id = f"trace:{trace_id}"
            add_node(
                node_id=trace_node_id,
                kind="trace_binding",
                label=f"Trace {trace_id}",
                lane="artifact/workitem/trace",
                domain=domain_id,
                subtitle=str(trace_binding.get("source") or "trace binding"),
                state=status,
                tone="muted",
                priority=search.get("priority"),
                refs=[{"kind": "trace", "id": trace_id}, {"kind": "episode", "id": episode_id}],
                collapsed_default=True,
                payload=trace_binding,
            )
            trace_edge = add_edge(
                source=episode_node_id,
                target=trace_node_id,
                relation="links_trace",
                source_port="out_trace",
                reaction_id=reaction_id,
                episode_ids=[episode_id],
                domain=domain_id,
                priority=search.get("priority"),
                state=status,
                refs=[{"kind": "trace", "id": trace_id}, {"kind": "episode", "id": episode_id}],
            )
            remember_path(reaction_paths[reaction_id], node_ids=[trace_node_id], edge_ids=[trace_edge])
            remember_path(episode_paths[episode_id], node_ids=[trace_node_id], edge_ids=[trace_edge])

    bundle_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for edge in edges:
        bundle_groups[str(edge.get("bundle_id") or "")].append(edge)
    edge_bundles = []
    for bundle_id, bundle_edges in sorted(bundle_groups.items()):
        if not bundle_id or len(bundle_edges) < 2:
            continue
        edge_bundles.append(
            {
                "bundle_id": bundle_id,
                "relation": bundle_edges[0].get("relation"),
                "edge_count": len(bundle_edges),
                "source_ids": sorted({str(edge.get("source")) for edge in bundle_edges})[:8],
                "target_ids": sorted({str(edge.get("target")) for edge in bundle_edges})[:8],
                "reaction_ids": sorted({str(edge.get("reaction_id")) for edge in bundle_edges if edge.get("reaction_id")})[:12],
                "episode_ids": sorted(
                    {
                        str(episode_id)
                        for edge in bundle_edges
                        for episode_id in (edge.get("episode_ids") or [])
                        if episode_id
                    }
                )[:12],
                "line_style_hint": bundle_edges[0].get("line_style_hint"),
            }
        )

    nodes = sorted(nodes_by_id.values(), key=lambda row: int(row.get("rank") or 0))
    cluster_counts: dict[str, dict[str, Any]] = {}
    for domain_id, label in REACTION_DIAGRAM_DOMAIN_ROWS:
        cluster_counts[domain_id] = {
            "id": f"domain:{domain_id}",
            "kind": "domain",
            "label": label,
            "domain": domain_id,
            "collapsed_default": domain_id not in {"raw_seed", "standards", "orchestration"},
            "node_count": 0,
            "edge_count": 0,
            "state_counts": Counter(),
            "priority_counts": Counter(),
            "lanes": set(),
            "tone": "muted",
        }
    for node in nodes:
        domain_id = str(node.get("domain") or "other")
        cluster = cluster_counts.setdefault(domain_id, {
            "id": f"domain:{domain_id}",
            "kind": "domain",
            "label": _human_label(domain_id),
            "domain": domain_id,
            "collapsed_default": True,
            "node_count": 0,
            "edge_count": 0,
            "state_counts": Counter(),
            "priority_counts": Counter(),
            "lanes": set(),
            "tone": "muted",
        })
        cluster["node_count"] += 1
        cluster["state_counts"].update([str(node.get("state") or "unknown")])
        cluster["priority_counts"].update([str(node.get("priority") or "unknown")])
        cluster["lanes"].add(str(node.get("lane") or "unknown"))
        if node.get("tone") == "red":
            cluster["tone"] = "red"
        elif node.get("tone") == "amber" and cluster["tone"] != "red":
            cluster["tone"] = "amber"
        elif node.get("tone") == "green" and cluster["tone"] == "muted":
            cluster["tone"] = "green"
    for edge in edges:
        domain_id = str(edge.get("domain") or "other")
        if domain_id in cluster_counts:
            cluster_counts[domain_id]["edge_count"] += 1
    clusters = []
    for cluster in cluster_counts.values():
        clusters.append(
            {
                **{key: value for key, value in cluster.items() if key not in {"state_counts", "priority_counts", "lanes"}},
                "state_counts": dict(cluster["state_counts"]),
                "priority_counts": dict(cluster["priority_counts"]),
                "lanes": sorted(cluster["lanes"]),
            }
        )

    def path_for_reaction(reaction_id: str) -> tuple[list[str], list[str]]:
        path = reaction_paths.get(reaction_id) or {"node_ids": [], "edge_ids": []}
        return list(path["node_ids"]), list(path["edge_ids"])

    def path_for_episode(episode_id: str) -> tuple[list[str], list[str]]:
        path = episode_paths.get(episode_id) or {"node_ids": [], "edge_ids": []}
        return list(path["node_ids"]), list(path["edge_ids"])

    focus_paths: list[dict[str, Any]] = []

    def add_focus(
        focus_id: str,
        *,
        kind: str,
        label: str,
        reason: str,
        tone: str,
        node_ids: Sequence[str],
        edge_ids: Sequence[str],
        scene_id: str,
        rank: int,
        domain: Any = None,
        refs: list[dict[str, Any]] | None = None,
    ) -> None:
        if len(focus_paths) >= REACTION_DIAGRAM_FOCUS_LIMIT:
            return
        filtered_nodes = [node_id for node_id in node_ids if node_id in nodes_by_id]
        filtered_edges = [edge_id for edge_id in edge_ids if edge_id in edge_by_id]
        focus_paths.append(
            {
                "id": focus_id,
                "kind": kind,
                "scene_id": scene_id,
                "label": _clip_text(label, limit=120),
                "reason": _clip_text(reason, limit=180),
                "tone": tone,
                "rank": rank,
                "domain": _diagram_domain_id(domain),
                "node_ids": filtered_nodes,
                "edge_ids": filtered_edges,
                "refs": list(refs or []),
            }
        )

    add_focus(
        "engine_status",
        kind="engine_status",
        label="Engine status",
        reason=str(attention.get("headline_reason") or engine_status),
        tone="cyan" if engine_armed else "muted",
        node_ids=[engine_node_id],
        edge_ids=[],
        scene_id="engine_status",
        rank=0,
        domain="orchestration",
        refs=[{"kind": "runtime_state", "path": REACTIONS_STATE_REL}],
    )
    active_ids = [
        str(row.get("reaction_id") or "")
        for row in reactions
        if str(_safe_mapping(row.get("state")).get("state") or "") == "firing"
        or str(row.get("reaction_id") or "") == str(active_reaction_id or "")
    ]
    failed_ids = [
        str(row.get("reaction_id") or "")
        for row in reactions
        if str(_safe_mapping(row.get("state")).get("state") or "") == "failed"
    ]
    eligible_ids = [
        str(row.get("reaction_id") or "")
        for row in reactions
        if str(_safe_mapping(row.get("state")).get("state") or "") == "eligible"
    ]
    blocker_id = ""
    for item in attention.get("top_blockers") or []:
        item_map = _safe_mapping(item)
        status = str(item_map.get("status") or "")
        rank_reason = str(item_map.get("rank_reason") or "")
        if status not in {"blocked", "cooldown", "firing"} and rank_reason not in {
            "no_active_singleflight",
            "no_runtime_barrier",
            "singleflight_barrier_active",
            "signal_fresh_enough",
        }:
            continue
        ref = str(item_map.get("ref") or "")
        if ref.startswith("reaction:"):
            blocker_id = ref.split(":", 2)[1]
            break
    if not blocker_id and awaiting_barriers:
        blocker_id = str(_safe_mapping(awaiting_barriers[0]).get("reaction_id") or "")
    if active_ids:
        node_ids, edge_ids = path_for_reaction(active_ids[0])
        add_focus(
            "active_firing",
            kind="active_run",
            label=f"Active: {active_ids[0]}",
            reason="Reaction has an active run or wake barrier.",
            tone="cyan",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="active_run",
            rank=1,
            refs=[{"kind": "reaction", "id": active_ids[0]}],
        )
    if blocker_id:
        node_ids, edge_ids = path_for_reaction(blocker_id)
        add_focus(
            "top_blocker",
            kind="top_blocker",
            label=f"Blocked: {blocker_id}",
            reason="Highest-ranked blocking gate or wake barrier.",
            tone="amber",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="blocked",
            rank=2,
            refs=[{"kind": "reaction", "id": blocker_id}],
        )
    if failed_ids:
        node_ids, edge_ids = path_for_reaction(failed_ids[0])
        add_focus(
            "top_failure",
            kind="top_failure",
            label=f"Failed: {failed_ids[0]}",
            reason="Reaction has the most recent failed runtime state.",
            tone="red",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="failure_triage",
            rank=3,
            refs=[{"kind": "reaction", "id": failed_ids[0]}],
        )
    failed_episode = next((row for row in episodes if row.get("status") == "failed"), None)
    if failed_episode and not failed_ids:
        episode_id = str(failed_episode.get("episode_id") or "")
        node_ids, edge_ids = path_for_episode(episode_id)
        add_focus(
            "top_failure",
            kind="top_failure",
            label=f"Failed episode: {failed_episode.get('reaction_id')}",
            reason="Latest episode ended failed.",
            tone="red",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="failure_triage",
            rank=3,
            refs=[{"kind": "episode", "id": episode_id}],
        )
    if eligible_ids:
        node_ids, edge_ids = path_for_reaction(eligible_ids[0])
        add_focus(
            "eligible_now",
            kind="eligible",
            label=f"Eligible: {eligible_ids[0]}",
            reason="Predicate passed and runtime gates allow a fire.",
            tone="amber",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="eligible_now",
            rank=4,
            refs=[{"kind": "reaction", "id": eligible_ids[0]}],
        )
    recent_completed = next((row for row in episodes if row.get("status") == "completed"), None)
    if recent_completed:
        episode_id = str(recent_completed.get("episode_id") or "")
        node_ids, edge_ids = path_for_episode(episode_id)
        add_focus(
            "recent_completed",
            kind="recent_completed",
            label=f"Completed: {recent_completed.get('reaction_id')}",
            reason="Most recent completed episode path.",
            tone="green",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="recent_activity",
            rank=5,
            refs=[{"kind": "episode", "id": episode_id}],
        )
    stale_id = ""
    for item in attention.get("stale_signals") or []:
        ref = str(_safe_mapping(item).get("ref") or "")
        if ref.startswith("reaction:"):
            stale_id = ref.split(":", 2)[1]
            break
    if stale_id:
        node_ids, edge_ids = path_for_reaction(stale_id)
        add_focus(
            "stale_signal",
            kind="stale_signal",
            label=f"Stale signal: {stale_id}",
            reason="Signal freshness gate is blocking the reaction.",
            tone="amber",
            node_ids=node_ids,
            edge_ids=edge_ids,
            scene_id="blocked",
            rank=6,
            refs=[{"kind": "reaction", "id": stale_id}],
        )
    domain_counts = _safe_mapping(summary.get("domain_counts"))
    if domain_counts:
        selected_domain = _diagram_domain_id(max(domain_counts.items(), key=lambda item: int(item[1] or 0))[0])
    else:
        selected_domain = "other"
    domain_node_ids = [str(node.get("id")) for node in nodes if node.get("domain") == selected_domain][:24]
    domain_node_set = set(domain_node_ids)
    domain_edge_ids = [
        str(edge.get("id"))
        for edge in edges
        if edge.get("source") in domain_node_set and edge.get("target") in domain_node_set
    ][:32]
    add_focus(
        f"domain:{selected_domain}",
        kind="selected_domain",
        label=f"{_human_label(selected_domain)} domain",
        reason="Largest visible reaction domain in the snapshot.",
        tone=next((str(cluster.get("tone")) for cluster in clusters if cluster.get("domain") == selected_domain), "muted"),
        node_ids=domain_node_ids,
        edge_ids=domain_edge_ids,
        scene_id="selected_domain",
        rank=7,
        domain=selected_domain,
        refs=[{"kind": "domain", "id": selected_domain}],
    )

    if active_ids:
        default_scene_id = "active_run"
        default_focus_id = "active_firing"
    elif failed_ids or any(row.get("status") == "failed" for row in episodes):
        default_scene_id = "failure_triage"
        default_focus_id = "top_failure"
    elif awaiting_barriers or blocker_id:
        default_scene_id = "blocked"
        default_focus_id = "top_blocker"
    elif eligible_ids:
        default_scene_id = "eligible_now"
        default_focus_id = "eligible_now"
    elif episodes:
        default_scene_id = "recent_activity"
        default_focus_id = "recent_completed" if recent_completed else "engine_status"
    else:
        default_scene_id = "quiet_system_map"
        default_focus_id = "engine_status"
    focus_by_id = {str(path.get("id")): path for path in focus_paths}
    selected_focus = focus_by_id.get(default_focus_id) or focus_by_id.get("engine_status")

    return {
        "schema": "reaction_diagram_v1",
        "generated_at": generated_at,
        "layout_contract": {
            "orientation": "horizontal_lanes",
            "node_rank_source": "backend_stable_rank",
            "port_aware_edges": True,
            "large_graph_policy": "bounded_inline_snapshot",
        },
        "lanes": [
            {"id": lane_id, "label": label, "order": index, "axis": "x"}
            for index, (lane_id, label) in enumerate(REACTION_DIAGRAM_LANES)
        ],
        "domains": [
            {"id": domain_id, "label": label, "order": index, "axis": "y"}
            for index, (domain_id, label) in enumerate(REACTION_DIAGRAM_DOMAIN_ROWS)
        ],
        "default_scene_id": default_scene_id,
        "default_focus_id": str(selected_focus.get("id") if selected_focus else "engine_status"),
        "nodes": nodes,
        "edges": edges,
        "edge_bundles": edge_bundles,
        "focus_paths": focus_paths,
        "clusters": clusters,
        "inspectors": inspectors,
        "debug_exports": {
            "mermaid_overview": _build_mermaid_debug_export(nodes_by_id=nodes_by_id, edges=edges),
            "mermaid_selected_focus": _build_mermaid_debug_export(
                nodes_by_id=nodes_by_id,
                edges=edges,
                focus_path=selected_focus,
            ),
        },
        "truncated": truncated,
    }


def _build_diagram_manifest(diagram: Mapping[str, Any], *, signal_mode: str) -> dict[str, Any]:
    nodes = diagram.get("nodes") if isinstance(diagram.get("nodes"), list) else []
    edges = diagram.get("edges") if isinstance(diagram.get("edges"), list) else []
    focus_paths = diagram.get("focus_paths") if isinstance(diagram.get("focus_paths"), list) else []
    inspectors = diagram.get("inspectors") if isinstance(diagram.get("inspectors"), Mapping) else {}
    return {
        "schema": "reaction_diagram_manifest_v1",
        "default_scene_id": diagram.get("default_scene_id") or "quiet_system_map",
        "default_focus_id": diagram.get("default_focus_id") or "engine_status",
        "counts": {
            "lanes": len(diagram.get("lanes") or []),
            "domains": len(diagram.get("domains") or []),
            "nodes": len(nodes),
            "edges": len(edges),
            "edge_bundles": len(diagram.get("edge_bundles") or []),
            "focus_paths": len(focus_paths),
            "clusters": len(diagram.get("clusters") or []),
            "inspectors": len(inspectors),
        },
        "top_focus_paths": [str(row.get("id")) for row in focus_paths[:5] if isinstance(row, Mapping)],
        "full_diagram_available": not bool(diagram.get("truncated")),
        "endpoint_or_resolver_ref": "snapshot.diagram",
        "generated_from_cache": signal_mode == "cached",
        "truncated": bool(diagram.get("truncated")),
    }


def _reaction_graph_source_fingerprint(
    *,
    reactions: Sequence[Mapping[str, Any]],
    episodes: Sequence[Mapping[str, Any]],
    awaiting_barriers: Sequence[Mapping[str, Any]],
    summary: Mapping[str, Any],
    topology: Mapping[str, Any],
    diagram: Mapping[str, Any],
    signal_mode: str,
) -> str:
    reaction_rows = []
    for reaction in reactions:
        state = _safe_mapping(reaction.get("state"))
        predicate = _safe_mapping(reaction.get("predicate"))
        reaction_rows.append(
            {
                "reaction_id": reaction.get("reaction_id"),
                "domain": reaction.get("domain"),
                "priority": reaction.get("priority"),
                "source_kind": reaction.get("source_kind"),
                "operation_id": _safe_mapping(reaction.get("action")).get("operation_id"),
                "state": state.get("state"),
                "reason_code": state.get("reason_code"),
                "predicate_matched": predicate.get("matched"),
                "last_signal_digest": reaction.get("last_signal_digest"),
                "last_result": reaction.get("last_result"),
                "last_operation_id": reaction.get("last_operation_id"),
                "would_fire_now": reaction.get("would_fire_now"),
                "effective_armed": reaction.get("effective_armed"),
                "primary_blocking_gate_id": _safe_mapping(reaction.get("eligibility")).get("primary_blocking_gate_id"),
            }
        )
    episode_rows = [
        {
            "episode_id": episode.get("episode_id"),
            "reaction_id": episode.get("reaction_id"),
            "reaction_run_id": episode.get("reaction_run_id"),
            "status": episode.get("status"),
            "terminal_event_id": episode.get("terminal_event_id"),
            "artifact_paths": episode.get("artifact_paths") or [],
        }
        for episode in episodes
    ]
    barrier_rows = [
        {
            "reaction_id": barrier.get("reaction_id"),
            "reaction_run_id": barrier.get("reaction_run_id"),
            "kind": barrier.get("kind"),
            "status": barrier.get("status"),
            "operation_id": barrier.get("operation_id"),
            "wake_at": barrier.get("wake_at"),
        }
        for barrier in awaiting_barriers
    ]
    diagram_shape = {
        "default_scene_id": diagram.get("default_scene_id"),
        "default_focus_id": diagram.get("default_focus_id"),
        "node_ids": [node.get("id") for node in (diagram.get("nodes") or []) if isinstance(node, Mapping)],
        "edge_ids": [edge.get("id") for edge in (diagram.get("edges") or []) if isinstance(edge, Mapping)],
        "bundle_ids": [
            bundle.get("bundle_id") or bundle.get("id")
            for bundle in (diagram.get("edge_bundles") or [])
            if isinstance(bundle, Mapping)
        ],
    }
    return graph_scene_core.source_fingerprint_for_payload(
        {
            "schema": "reaction_graph_scene_source_v1",
            "signal_mode": signal_mode,
            "reactions": reaction_rows,
            "episodes": episode_rows,
            "barriers": barrier_rows,
            "summary": {
                "engine_state": summary.get("engine_state"),
                "engine_armed": summary.get("engine_armed"),
                "state_counts": summary.get("state_counts"),
                "domain_counts": summary.get("domain_counts"),
            },
            "topology": {
                "nodes": len(topology.get("nodes") or []),
                "edges": len(topology.get("edges") or []),
                "truncated": topology.get("truncated"),
            },
            "diagram": diagram_shape,
        }
    )


def _diagram_node_to_graph_scene_node(node: Mapping[str, Any], *, focus_ids: set[str]) -> dict[str, Any]:
    row = dict(node)
    row["native_schema"] = "reaction_diagram_node_v1"
    row["native_ref"] = {"schema": "reaction_diagram_v1", "id": node.get("id")}
    row["lane_id"] = node.get("lane")
    row["row_id"] = node.get("domain")
    row["attention_score"] = graph_scene_core.attention_score(row, focus_ids=focus_ids)
    row["layout_constraints"] = {
        "projection": "reaction_lane_dag",
        "lane_id": node.get("lane"),
        "row_id": node.get("domain"),
        "rank": node.get("rank"),
        "stable_order": node.get("stable_order"),
        "parent_cluster_id": node.get("parent_cluster_id"),
        "port_constraints": node.get("ports") or [],
        "pinning": "backend_ranked_lane",
    }
    return row


def _diagram_edge_to_graph_scene_edge(edge: Mapping[str, Any], *, focus_ids: set[str]) -> dict[str, Any]:
    row = dict(edge)
    row["native_schema"] = "reaction_diagram_edge_v1"
    row["native_ref"] = {"schema": "reaction_diagram_v1", "id": edge.get("id")}
    row["attention_score"] = graph_scene_core.attention_score(row, focus_ids=focus_ids)
    row["layout_constraints"] = {
        "projection": "reaction_lane_dag",
        "source_port": edge.get("source_port"),
        "target_port": edge.get("target_port"),
        "bundle_id": edge.get("bundle_id"),
        "routing": "orthogonal_port_aware",
        "line_style_hint": edge.get("line_style_hint"),
    }
    return row


def _reaction_graph_closure_refs(diagram: Mapping[str, Any]) -> dict[str, Any]:
    focus_paths = [row for row in (diagram.get("focus_paths") or []) if isinstance(row, Mapping)]

    def refs_for(*kinds: str) -> list[dict[str, Any]]:
        selected = []
        kind_set = set(kinds)
        for focus in focus_paths:
            if str(focus.get("kind") or "") in kind_set or str(focus.get("id") or "") in kind_set:
                selected.append(
                    {
                        "focus_id": focus.get("id"),
                        "kind": focus.get("kind"),
                        "scene_id": focus.get("scene_id"),
                        "node_count": len(focus.get("node_ids") or []),
                        "edge_count": len(focus.get("edge_ids") or []),
                        "refs": list(focus.get("refs") or []),
                    }
                )
        return selected

    return {
        "schema": "reaction_graph_scene_closure_refs_v1",
        "causal_path_refs": refs_for(
            "engine_status",
            "active_run",
            "eligible",
            "recent_completed",
            "selected_domain",
        ),
        "blocking_cut_refs": refs_for("top_blocker", "stale_signal", "blocked"),
        "lineage_closure_refs": refs_for("recent_completed", "recent_activity"),
        "failure_cone_refs": refs_for("top_failure", "failure_triage"),
    }


def _compact_reaction_diagram(
    diagram: Mapping[str, Any],
    *,
    diagram_manifest: Mapping[str, Any],
    graph_scene_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "reaction_diagram_v1",
        "generated_at": diagram.get("generated_at"),
        "layout_contract": dict(diagram.get("layout_contract") or {}),
        "lanes": list(diagram.get("lanes") or []),
        "domains": list(diagram.get("domains") or []),
        "default_scene_id": diagram.get("default_scene_id"),
        "default_focus_id": diagram.get("default_focus_id"),
        "counts": dict(diagram_manifest.get("counts") or {}),
        "graph_scene_manifest_ref": "snapshot.graph_scene_manifest",
        "graph_scene_revision": graph_scene_manifest.get("revision"),
        "truncated": bool(diagram.get("truncated")),
        "omitted": {
            "nodes": len(diagram.get("nodes") or []),
            "edges": len(diagram.get("edges") or []),
            "edge_bundles": len(diagram.get("edge_bundles") or []),
            "focus_paths": len(diagram.get("focus_paths") or []),
            "clusters": len(diagram.get("clusters") or []),
            "inspectors": len(diagram.get("inspectors") or {}),
            "reason": "diagram_mode_manifest",
            "full_diagram_resolver_ref": "snapshot.diagram?diagram_mode=full",
            "default_focus_resolver_ref": "snapshot.graph_scene_default_focus",
        },
    }


def _reaction_graph_scene_cache_get(cache_key: str) -> dict[str, Any] | None:
    with _REACTION_GRAPH_SCENE_CACHE_LOCK:
        cached = _REACTION_GRAPH_SCENE_CACHE.get(cache_key)
        if cached is None:
            return None
        return copy.deepcopy(cached)


def _reaction_graph_scene_cache_set(cache_key: str, scene: Mapping[str, Any]) -> None:
    with _REACTION_GRAPH_SCENE_CACHE_LOCK:
        _REACTION_GRAPH_SCENE_CACHE[cache_key] = copy.deepcopy(dict(scene))
        while len(_REACTION_GRAPH_SCENE_CACHE) > REACTION_GRAPH_SCENE_CACHE_MAX_ENTRIES:
            _REACTION_GRAPH_SCENE_CACHE.pop(next(iter(_REACTION_GRAPH_SCENE_CACHE)))


def _build_reaction_graph_scene_pack(
    *,
    diagram: Mapping[str, Any],
    source_fingerprint: str,
    signal_mode: str,
    generated_at: str,
    elapsed_ms: float,
    previous_revision: str | None = None,
) -> dict[str, Any]:
    default_focus_id = str(diagram.get("default_focus_id") or "engine_status")
    cache_key = graph_scene_core.stable_json_hash(
        {
            "source_schema": "reaction_diagram_v1",
            "source_fingerprint": source_fingerprint,
            "default_focus_id": default_focus_id,
            "default_projection": "reaction_lane_dag",
            "core_version": graph_scene_core.GRAPH_SCENE_CORE_VERSION,
        },
        length=32,
    )
    cached = _reaction_graph_scene_cache_get(cache_key)
    cache_status = "hit" if cached is not None else "miss"
    if cached is None:
        focus_ids = {
            str(node_id)
            for path in (diagram.get("focus_paths") or [])
            if isinstance(path, Mapping)
            for node_id in (path.get("node_ids") or [])
            if node_id
        }
        focus_edge_ids = {
            str(edge_id)
            for path in (diagram.get("focus_paths") or [])
            if isinstance(path, Mapping)
            for edge_id in (path.get("edge_ids") or [])
            if edge_id
        }
        nodes = [
            _diagram_node_to_graph_scene_node(node, focus_ids=focus_ids)
            for node in (diagram.get("nodes") or [])
            if isinstance(node, Mapping)
        ]
        edges = [
            _diagram_edge_to_graph_scene_edge(edge, focus_ids=focus_edge_ids)
            for edge in (diagram.get("edges") or [])
            if isinstance(edge, Mapping)
        ]
        scene = graph_scene_core.build_graph_scene(
            scene_id="reactions_runtime_scene",
            source_schema="reaction_diagram_v1",
            source_fingerprint=source_fingerprint,
            generated_at=generated_at,
            nodes=nodes,
            edges=edges,
            lanes=[row for row in (diagram.get("lanes") or []) if isinstance(row, Mapping)],
            rows=[row for row in (diagram.get("domains") or []) if isinstance(row, Mapping)],
            clusters=[row for row in (diagram.get("clusters") or []) if isinstance(row, Mapping)],
            bundles=[row for row in (diagram.get("edge_bundles") or []) if isinstance(row, Mapping)],
            focus_paths=[row for row in (diagram.get("focus_paths") or []) if isinstance(row, Mapping)],
            inspectors=diagram.get("inspectors") if isinstance(diagram.get("inspectors"), Mapping) else {},
            default_projection="reaction_lane_dag",
            default_focus_id=default_focus_id,
            available_projections=[
                {
                    "id": "reaction_lane_dag",
                    "label": "Reaction Lane DAG",
                    "purpose": "Causal automation map across runtime, signal, predicate, reaction, episode, operation, receiver/effect, and artifact lanes.",
                },
                {
                    "id": "reaction_focus_context",
                    "label": "Reaction Focus + Context",
                    "purpose": "Default backend-ranked focus path plus local neighborhood.",
                },
                {
                    "id": "reaction_domain_matrix",
                    "label": "Reaction Domain Matrix",
                    "purpose": "Domain rows crossed with lifecycle lanes for scanning dense automation state.",
                },
                {
                    "id": "reaction_bundle_overview",
                    "label": "Reaction Bundle Overview",
                    "purpose": "Shared signal/operation bundles for reducing repeated edge families.",
                },
            ],
            resolver_refs={
                "manifest": "snapshot.graph_scene_manifest",
                "default_focus": "snapshot.graph_scene_default_focus",
                "full_scene": "snapshot.graph_scene",
                "delta": "snapshot.graph_scene_delta_manifest",
                "inspect": "snapshot.graph_scene.inspectors[ref]",
            },
            generated_from_cache=signal_mode == "cached",
            elapsed_ms=elapsed_ms,
            source_ref="snapshot.diagram",
            debug_exports=diagram.get("debug_exports") if isinstance(diagram.get("debug_exports"), Mapping) else {},
            layout_constraints={
                "rank_direction": "LR",
                "lane_axis": "x",
                "row_axis": "y",
                "rank_source": "backend_stable_rank",
                "edge_routing": "port_aware_orthogonal",
            },
        )
        scene["closure_refs"] = _reaction_graph_closure_refs(diagram)
        scene["manifest"] = graph_scene_core.build_graph_scene_manifest(scene)
        scene["validation"] = graph_scene_core.validate_graph_scene(scene)
        _reaction_graph_scene_cache_set(cache_key, scene)
    else:
        scene = cached
        scene["generated_from_cache"] = True
        scene["elapsed_ms"] = elapsed_ms
        scene["manifest"]["generated_from_cache"] = True
        scene["manifest"]["elapsed_ms"] = elapsed_ms
    manifest = graph_scene_core.build_graph_scene_manifest(scene)
    default_focus = graph_scene_core.build_default_focus_excerpt(scene, focus_id=default_focus_id)
    delta_manifest = graph_scene_core.build_graph_scene_delta_manifest(
        manifest,
        previous_revision=previous_revision,
    )
    return {
        "scene": scene,
        "manifest": manifest,
        "default_focus": default_focus,
        "delta_manifest": delta_manifest,
        "cache_key": cache_key,
        "cache_status": cache_status,
    }


def _build_reactions_summary(
    reactions: list[dict[str, Any]],
    *,
    awaiting_barriers: list[dict[str, Any]],
    engine_status: str,
    engine_armed: bool,
    timeline: list[dict[str, Any]],
) -> dict[str, Any]:
    state_counts = Counter(str(_safe_mapping(row.get("state")).get("state") or "unknown") for row in reactions)
    domain_counts = Counter(str(row.get("domain") or "unknown") for row in reactions)
    priority_counts = Counter(str(row.get("priority") or "unknown") for row in reactions)
    source_counts = Counter(str(row.get("source_kind") or "unknown") for row in reactions)
    recent_counts = Counter(str(row.get("status") or "unknown") for row in timeline)
    return {
        "schema": "reaction_summary_v1",
        "engine_state": engine_status,
        "engine_armed": engine_armed,
        "reaction_count": len(reactions),
        "eligible_now": state_counts.get("eligible", 0),
        "blocked_count": max(state_counts.get("blocked", 0), len(awaiting_barriers)),
        "failed_count": state_counts.get("failed", 0),
        "active_count": state_counts.get("firing", 0),
        "disabled_count": state_counts.get("disabled", 0),
        "completed_count": state_counts.get("completed", 0),
        "waiting_count": state_counts.get("waiting", 0),
        "state_counts": dict(sorted(state_counts.items())),
        "domain_counts": dict(sorted(domain_counts.items())),
        "priority_counts": dict(sorted(priority_counts.items())),
        "source_kind_counts": dict(sorted(source_counts.items())),
        "recent_event_counts": dict(sorted(recent_counts.items())),
    }


def _runtime_status_rail(
    *,
    engine_status: str,
    engine_armed: bool,
    reactions: list[dict[str, Any]],
    awaiting_barriers: list[dict[str, Any]],
    last_fired_at: Any,
    last_tick_at: Any,
) -> list[dict[str, Any]]:
    summary = _build_reactions_summary(
        reactions,
        awaiting_barriers=awaiting_barriers,
        engine_status=engine_status,
        engine_armed=engine_armed,
        timeline=[],
    )
    return [
        {"id": "engine", "label": "Automation", "value": "enabled" if engine_armed else "disabled", "tone": "green" if engine_armed else "muted"},
        {"id": "runner", "label": "Runner", "value": engine_status, "tone": "amber" if engine_status == "armed_waiting_runner" else "green"},
        {"id": "reactions", "label": "Reactions", "value": len(reactions), "tone": "muted"},
        {"id": "eligible", "label": "Eligible now", "value": summary["eligible_now"], "tone": "amber" if summary["eligible_now"] else "muted"},
        {"id": "blockers", "label": "Blockers", "value": len(awaiting_barriers), "tone": "amber" if awaiting_barriers else "muted"},
        {"id": "last_fired", "label": "Last fired", "value": last_fired_at, "tone": "muted"},
        {"id": "last_tick", "label": "Last tick", "value": last_tick_at or "No tick recorded", "tone": "muted"},
    ]


def _reaction_filter_options(reactions: list[dict[str, Any]]) -> dict[str, list[str]]:
    return {
        "states": sorted({str(_safe_mapping(row.get("state")).get("state")) for row in reactions if row.get("state")}),
        "domains": sorted({str(row.get("domain")) for row in reactions if row.get("domain")}),
        "source_kinds": sorted({str(row.get("source_kind")) for row in reactions if row.get("source_kind")}),
        "priorities": sorted({str(row.get("priority")) for row in reactions if row.get("priority")}),
        "operations": sorted(
            {
                str(_safe_mapping(row.get("action")).get("operation_id"))
                for row in reactions
                if _safe_mapping(row.get("action")).get("operation_id")
            }
        ),
    }


def _iso_to_dt(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _lineage_ref(
    *,
    kind: str,
    ref: Any,
    label: Any = None,
    digest: Any = None,
    observed_at: Any = None,
    freshness: Any = None,
    produced_at: Any = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "ref": str(ref or f"{kind}:unknown"),
        "label": _clip_text(label if label is not None else ref, limit=120),
        "digest": digest,
        "observed_at": observed_at,
        "freshness": freshness,
        "produced_at": produced_at,
    }


def _relationship(source_ref: Any, target_ref: Any, relation: str) -> dict[str, Any]:
    return {
        "source_ref": str(source_ref or ""),
        "target_ref": str(target_ref or ""),
        "relation": relation,
    }


def _operation_catalog_entry(operation_id: Any) -> dict[str, Any]:
    op_id = str(operation_id or "").strip()
    if not op_id:
        return {}
    try:
        found = find_launchable_operation(op_id)
    except Exception:
        found = None
    return dict(found) if isinstance(found, Mapping) else {}


def _operation_safety(operation: Mapping[str, Any]) -> dict[str, Any]:
    if not operation:
        return {
            "known_operation": False,
            "safety_class": "unknown",
            "impact_class": "unknown",
            "side_effects": ["unknown_operation"],
            "side_effect_level": "unresolved",
            "safety_state": "unresolved",
            "requires_confirmation": False,
            "description": "Operation id is not present in launchable_operations.",
        }
    command = str(operation.get("command") or "").strip()
    meta_mission_id = str(operation.get("meta_mission_id") or "").strip()
    side_effects: list[str] = []
    if meta_mission_id:
        side_effects.append(f"meta_mission:{meta_mission_id}")
    if any(token in command for token in (" --write", " --commit", " apply", " run ")):
        side_effects.append("repo_or_runtime_write_possible")
    if not side_effects:
        side_effects.append("read_or_status_operation")
    write_possible = "repo_or_runtime_write_possible" in side_effects or bool(meta_mission_id)
    return {
        "known_operation": True,
        "safety_class": str(operation.get("safety_class") or "catalog_allowlisted"),
        "impact_class": str(operation.get("impact_class") or ("runtime" if meta_mission_id else "low")),
        "side_effects": side_effects[:4],
        "side_effect_level": "write_possible" if write_possible else "read_or_status",
        "execution_mode": str(operation.get("execution_mode") or "sync"),
        "requires_confirmation": bool(operation.get("requires_confirmation")),
        "safety_state": "configured",
        "description": operation.get("description_short"),
    }


def _gate(
    gate_id: str,
    label: str,
    state: str,
    *,
    blocking: bool = False,
    reason_code: str | None = None,
    reason_summary: str | None = None,
    evidence_ref: str | None = None,
    observed_at: str | None = None,
) -> dict[str, Any]:
    return {
        "gate_id": gate_id,
        "label": label,
        "state": state,
        "blocking": bool(blocking),
        "reason_code": reason_code or state,
        "reason_summary": _clip_text(reason_summary or _human_label(state), limit=180),
        "evidence_ref": evidence_ref,
        "observed_at": observed_at,
    }


def _operator_actionability(state: str, gate_id: str | None) -> str:
    if state == "eligible":
        return "run_now_possible"
    if state in {"firing", "blocked", "cooldown"}:
        return "wait"
    if state == "failed":
        return "repair_needed"
    if gate_id in {"engine_armed", "reaction_armed"}:
        return "arm_possible"
    if state == "disabled":
        return "arm_possible"
    if state == "waiting":
        return "inspect"
    return "none"


def _build_evaluation_ladder(
    *,
    reaction: Mapping[str, Any],
    runtime_entry: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    state_view: Mapping[str, Any],
    engine_armed: bool,
    barriers_for_reaction: list[dict[str, Any]],
    global_barriers: list[dict[str, Any]],
    operation_catalog: Mapping[str, Any],
    signal_mode: str,
    observed_at: str,
) -> dict[str, Any]:
    signal = _safe_mapping(evaluation.get("signal"))
    source_kind = str(_safe_mapping(reaction.get("source")).get("kind") or signal.get("kind") or "unknown")
    gate_config = _safe_mapping(reaction.get("gate"))
    operation_id = str(_safe_mapping(reaction.get("action")).get("operation_id") or "").strip()
    matched = bool(evaluation.get("matched"))
    effective_armed = bool(evaluation.get("effective_armed"))
    cooldown_active = bool(evaluation.get("cooldown_active"))
    preview_reason = str(evaluation.get("preview_reason") or "").strip()
    dedupe_hit = preview_reason.startswith("deduped")
    cached_signal_present = isinstance(runtime_entry.get("last_signal"), Mapping)
    source_available = bool(source_kind and source_kind != "unknown")
    active_global_barrier = bool(global_barriers)
    active_own_barrier = bool(barriers_for_reaction)
    generated_at = signal.get("generated_at") or signal.get("recorded_at") or signal.get("ts")
    generated_dt = _iso_to_dt(generated_at)
    now_dt = _iso_to_dt(observed_at) or _now_dt()
    stale_signal = bool(generated_dt and (now_dt - generated_dt).total_seconds() > 86400)

    ladder = [
        _gate(
            "source_available",
            "Source available",
            "pass" if source_available else "unknown",
            blocking=not source_available,
            reason_code="source_kind_available" if source_available else "unknown_source_kind",
            reason_summary=f"source.kind={source_kind}",
            evidence_ref=REACTIONS_CONFIG_REL,
            observed_at=observed_at,
        ),
        _gate(
            "signal_loaded_or_cached",
            "Signal loaded or cached",
            "pass" if signal_mode == "live" or cached_signal_present else "unknown",
            blocking=False,
            reason_code="cached_signal_used" if signal_mode == "cached" else "live_signal_loaded",
            reason_summary=(
                "Cached Station read used persisted last_signal."
                if signal_mode == "cached"
                else "Live scheduler read loaded the signal producer."
            ),
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "signal_fresh_enough",
            "Signal fresh enough",
            "blocked" if stale_signal else ("unknown" if not generated_at else "pass"),
            blocking=stale_signal,
            reason_code="signal_stale" if stale_signal else "freshness_not_blocking",
            reason_summary=(
                f"Signal timestamp {generated_at} is older than 24h."
                if stale_signal
                else (f"Signal timestamp {generated_at}." if generated_at else "No freshness timestamp on signal.")
            ),
            evidence_ref=REACTIONS_STATE_REL if signal_mode == "cached" else source_kind,
            observed_at=observed_at,
        ),
        _gate(
            "predicate_matched",
            "Predicate matched",
            "pass" if matched else "fail",
            blocking=not matched,
            reason_code="predicate_matched" if matched else "predicate_not_matched",
            reason_summary=str(preview_reason or "predicate evaluated"),
            evidence_ref="reaction.predicate",
            observed_at=observed_at,
        ),
        _gate(
            "engine_armed",
            "Engine armed",
            "pass" if engine_armed else "fail",
            blocking=not engine_armed,
            reason_code="engine_armed" if engine_armed else "engine_disarmed",
            reason_summary="Engine desired_armed is true." if engine_armed else "Engine desired_armed is false.",
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "reaction_armed",
            "Reaction armed",
            "pass" if effective_armed else "fail",
            blocking=not effective_armed,
            reason_code="reaction_armed" if effective_armed else "reaction_disarmed",
            reason_summary=(
                "Reaction is enabled by config/runtime override."
                if effective_armed
                else "Reaction is disabled by config or runtime override."
            ),
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "no_active_singleflight",
            "No active single-flight",
            "pass" if not active_global_barrier else "blocked",
            blocking=active_global_barrier,
            reason_code="singleflight_clear" if not active_global_barrier else "singleflight_barrier_active",
            reason_summary=(
                "No global wake barrier is active."
                if not active_global_barrier
                else "A wake barrier is active; V1 permits one in-flight reaction."
            ),
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "no_runtime_barrier",
            "No reaction barrier",
            "pass" if not active_own_barrier else "blocked",
            blocking=active_own_barrier,
            reason_code="reaction_barrier_clear" if not active_own_barrier else "reaction_barrier_active",
            reason_summary=barriers_for_reaction[0].get("label") if active_own_barrier else "No reaction-specific barrier.",
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "cooldown_clear",
            "Cooldown clear",
            "pass" if not cooldown_active else "blocked",
            blocking=cooldown_active,
            reason_code="cooldown_clear" if not cooldown_active else "cooldown_active",
            reason_summary=(
                "Cooldown is clear."
                if not cooldown_active
                else f"Cooldown active until {runtime_entry.get('cooldown_until') or 'unknown'}."
            ),
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "dedupe_clear",
            "Dedupe clear",
            "pass" if not dedupe_hit else "blocked",
            blocking=dedupe_hit,
            reason_code="dedupe_clear" if not dedupe_hit else _reason_code(preview_reason),
            reason_summary=preview_reason if dedupe_hit else f"dedupe_by={gate_config.get('dedupe_by') or 'none'} clear.",
            evidence_ref=REACTIONS_STATE_REL,
            observed_at=observed_at,
        ),
        _gate(
            "launch_operation_allowed",
            "Launch operation allowed",
            "pass" if operation_catalog else "fail",
            blocking=not bool(operation_catalog),
            reason_code="operation_catalog_hit" if operation_catalog else "unknown_operation_id",
            reason_summary=(
                f"{operation_id} is present in launchable_operations."
                if operation_catalog
                else f"{operation_id or 'unknown'} is not present in launchable_operations."
            ),
            evidence_ref="system/lib/launchable_operations.py",
            observed_at=observed_at,
        ),
        _gate(
            "parameters_rendered",
            "Parameters rendered",
            "pass" if isinstance(evaluation.get("action_parameters"), Mapping) else "unknown",
            blocking=False,
            reason_code="parameters_rendered",
            reason_summary=f"{len(evaluation.get('action_parameters') or {})} parameter(s) rendered.",
            evidence_ref="reaction.action.parameters",
            observed_at=observed_at,
        ),
        _gate(
            "parameter_shape_valid",
            "Parameter shape valid",
            "pass" if operation_catalog else "unknown",
            blocking=False,
            reason_code="parameter_shape_preview",
            reason_summary="Catalog metadata is available for validation preview." if operation_catalog else "Validation preview unavailable.",
            evidence_ref="system/lib/launchable_operations.py",
            observed_at=observed_at,
        ),
        _gate(
            "impact_preview_available",
            "Impact preview available",
            "pass" if operation_catalog else "unknown",
            blocking=False,
            reason_code="impact_preview_available" if operation_catalog else "impact_preview_missing",
            reason_summary=(
                _clip_text(operation_catalog.get("description_short") or operation_id, limit=160)
                if operation_catalog
                else "No operation metadata available."
            ),
            evidence_ref="system/lib/launchable_operations.py",
            observed_at=observed_at,
        ),
    ]
    primary_blocking = next((row for row in ladder if row.get("blocking")), None)
    passed = [row for row in ladder if row.get("state") == "pass"]
    eligibility_state = str(state_view.get("state") or "unknown")
    sentence = (
        f"{reaction.get('label') or reaction.get('reaction_id')} is {eligibility_state}: "
        f"{(primary_blocking or {}).get('reason_summary') or state_view.get('preview_reason') or state_view.get('why_not_eligible') or 'no blocking gate'}"
    )
    primary_blocking_gate_id = str(primary_blocking.get("gate_id")) if primary_blocking else None
    return {
        "schema": "reaction_evaluation_ladder_v1",
        "evaluation_ladder": ladder,
        "primary_blocking_gate_id": primary_blocking_gate_id,
        "primary_positive_gate_id": str(passed[-1].get("gate_id")) if passed else None,
        "eligibility_state": eligibility_state,
        "eligibility_sentence": _clip_text(sentence, limit=240),
        "operator_actionability": _operator_actionability(eligibility_state, primary_blocking_gate_id),
    }


def _build_reaction_lineage(
    *,
    reaction_id: str,
    source_kind: str,
    domain: str,
    signal: Mapping[str, Any],
    signal_digest: str,
    ledger_fingerprint: str,
    operation_id: str,
    action_parameters: Mapping[str, Any],
    recent_events: list[dict[str, Any]],
) -> dict[str, Any]:
    signal_ref = f"reaction:{reaction_id}:signal:{signal_digest[:12] if signal_digest else 'unknown'}"
    reaction_ref = f"reaction:{reaction_id}"
    operation_ref = f"operation:{operation_id or 'unknown'}"
    inputs = [
        _lineage_ref(
            kind="signal",
            ref=signal_ref,
            label=f"{_human_label(source_kind)} signal",
            digest=signal_digest,
            observed_at=signal.get("generated_at") or signal.get("recorded_at") or signal.get("ts"),
            freshness="cached_or_live",
        ),
        _lineage_ref(
            kind="config",
            ref=f"{REACTIONS_CONFIG_REL}::{reaction_id}",
            label="Tracked reaction config",
            observed_at=None,
        ),
    ]
    if ledger_fingerprint:
        inputs.append(
            _lineage_ref(
                kind="ledger",
                ref=f"{REACTIONS_LEDGER_REL}::fingerprint:{ledger_fingerprint[:12]}",
                label="Reaction material fingerprint",
                digest=ledger_fingerprint,
            )
        )
    outputs = [
        _lineage_ref(
            kind="operation",
            ref=operation_ref,
            label=operation_id or "No operation",
            produced_at=None,
        )
    ]
    artifact_paths: list[str] = []
    for event in recent_events:
        for artifact in event.get("artifact_paths") or []:
            if artifact not in artifact_paths:
                artifact_paths.append(str(artifact))
    for artifact in artifact_paths[:REACTION_LINEAGE_REF_LIMIT]:
        outputs.append(_lineage_ref(kind="artifact", ref=artifact, label=Path(artifact).name, produced_at=None))
    relationships = [
        _relationship(signal_ref, reaction_ref, "watched"),
        _relationship(signal_ref, f"predicate:{reaction_id}", "evaluated"),
        _relationship(reaction_ref, operation_ref, "fires" if operation_id else "would_fire"),
    ]
    for artifact in artifact_paths[:REACTION_LINEAGE_REF_LIMIT]:
        relationships.append(_relationship(operation_ref, artifact, "wrote"))
    return {
        "schema": "reaction_lineage_v1",
        "domain": domain,
        "inputs": inputs[:REACTION_LINEAGE_REF_LIMIT],
        "outputs": outputs[:REACTION_LINEAGE_REF_LIMIT],
        "relationships": relationships[:REACTION_LINEAGE_REF_LIMIT * 2],
        "action_parameters_digest": _stable_hex([action_parameters], length=16) if action_parameters else None,
    }


def _trace_binding(
    *,
    episode_id: str,
    reaction_id: str,
    domain: str,
    state: str,
    operation_id: str,
    signal_digest: str,
    ledger_fingerprint: str | None,
    source: str,
) -> dict[str, Any]:
    trace_id = _stable_hex(["trace", episode_id, reaction_id], length=32)
    span_id = _stable_hex(["span", episode_id, operation_id], length=16)
    return {
        "schema": "reaction_trace_binding_v1",
        "source": source,
        "trace_id": trace_id,
        "span_id": span_id,
        "parent_span_id": None,
        "linked_span_ids": [],
        "span_name": f"reaction/{reaction_id}",
        "span_kind": "reaction",
        "status": state,
        "attributes": {
            "reaction.id": reaction_id,
            "reaction.domain": domain,
            "reaction.state": state,
            "reaction.operation_id": operation_id,
            "reaction.signal_digest": signal_digest,
            "reaction.ledger_fingerprint": ledger_fingerprint,
            "reaction.run_id": episode_id,
        },
    }


def _episode_failure_class(event: Mapping[str, Any] | None) -> str | None:
    if not event:
        return None
    if event.get("returncode") not in (None, 0):
        return "nonzero_returncode"
    if event.get("error"):
        return "runtime_error"
    if event.get("stderr_excerpt_ref"):
        return "stderr_present"
    return None


def _event_time(event: Mapping[str, Any]) -> str:
    for key in ("recorded_at", "fired_at", "completed_at", "failed_at", "suppressed_at"):
        value = str(event.get(key) or "").strip()
        if value:
            return value
    return ""


def _build_episode_views(
    events: list[dict[str, Any]],
    *,
    reaction_meta: Mapping[str, Mapping[str, Any]],
    limit: int = REACTION_EPISODE_LIMIT,
) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    groups: dict[str, dict[str, Any]] = {}
    open_legacy_by_triple: dict[tuple[str, str, str], str] = {}
    for event in reversed(events):
        reaction_id = str(event.get("reaction_id") or "").strip()
        operation_id = str(event.get("operation_id") or "").strip()
        signal_digest = str(event.get("signal_digest") or "").strip()
        run_id = str(event.get("reaction_run_id") or "").strip()
        source = "reaction_run_id"
        if run_id:
            group_key = f"run:{run_id}"
            episode_id = run_id
        else:
            source = "synthetic_legacy"
            triple = (reaction_id, operation_id, signal_digest)
            if event.get("kind") == "reaction_fired":
                episode_id = "rxlegacy_" + _stable_hex([reaction_id, operation_id, signal_digest, event.get("event_id")], length=18)
                group_key = f"legacy:{episode_id}"
                open_legacy_by_triple[triple] = group_key
            else:
                group_key = open_legacy_by_triple.get(triple) or (
                    "legacy:rxlegacy_" + _stable_hex([reaction_id, operation_id, signal_digest, event.get("event_id")], length=18)
                )
                episode_id = group_key.split(":", 1)[1]
        group = groups.setdefault(
            group_key,
            {
                "episode_id": episode_id,
                "reaction_run_id": run_id or None,
                "episode_id_source": source,
                "events": [],
            },
        )
        group["events"].append(event)

    episodes: list[dict[str, Any]] = []
    by_reaction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for group in groups.values():
        group_events = sorted(group["events"], key=_event_time)
        latest = group_events[-1] if group_events else {}
        first = group_events[0] if group_events else {}
        fired = next((event for event in group_events if event.get("kind") in {"reaction_fired", "reaction_fired_manual_proof"}), None)
        terminal = next((event for event in reversed(group_events) if event.get("status") in {"completed", "failed"}), None)
        reaction_id = str((latest or first).get("reaction_id") or "").strip()
        meta = dict(reaction_meta.get(reaction_id) or {})
        domain = str(meta.get("domain") or "reaction")
        operation_id = str((latest or first).get("operation_id") or meta.get("operation_id") or "").strip()
        status = str((terminal or latest or {}).get("status") or "unknown")
        if fired and not terminal and status == "fired":
            status = "running"
        if status == "state_changed":
            status = "unknown"
        artifact_paths: list[str] = []
        ledger_event_ids: list[str] = []
        for event in group_events:
            event_id = str(event.get("event_id") or "").strip()
            if event_id:
                ledger_event_ids.append(event_id)
            for artifact in event.get("artifact_paths") or []:
                if artifact not in artifact_paths:
                    artifact_paths.append(str(artifact))
        signal_digest = str((latest or first).get("signal_digest") or meta.get("signal_digest") or "").strip()
        ledger_fingerprint = str((latest or first).get("ledger_fingerprint") or meta.get("ledger_fingerprint") or "").strip()
        episode_id = str(group["episode_id"])
        lineage = _build_reaction_lineage(
            reaction_id=reaction_id,
            source_kind=str(meta.get("source_kind") or ""),
            domain=domain,
            signal=dict(meta.get("signal") or {}),
            signal_digest=signal_digest,
            ledger_fingerprint=ledger_fingerprint,
            operation_id=operation_id,
            action_parameters=dict(meta.get("action_parameters") or {}),
            recent_events=group_events,
        )
        episode = {
            "schema": "reaction_episode_v1",
            "episode_id": episode_id,
            "reaction_run_id": group.get("reaction_run_id"),
            "episode_id_source": group.get("episode_id_source"),
            "reaction_id": reaction_id,
            "domain": domain,
            "source_kind": meta.get("source_kind"),
            "operation_id": operation_id,
            "status": status,
            "started_at": (fired or first).get("fired_at") or (fired or first).get("recorded_at"),
            "ended_at": (terminal or {}).get("completed_at") or (terminal or {}).get("failed_at") or (terminal or {}).get("recorded_at"),
            "duration_ms": (terminal or latest).get("duration_ms"),
            "returncode": (terminal or latest).get("returncode"),
            "signal_digest": signal_digest,
            "ledger_fingerprint": ledger_fingerprint or None,
            "dedupe_key": (latest or first).get("dedupe_key") or signal_digest,
            "trigger_event_id": (fired or first).get("event_id"),
            "terminal_event_id": (terminal or {}).get("event_id"),
            "ledger_event_ids": ledger_event_ids,
            "command": (fired or latest).get("command"),
            "command_hash": (fired or latest).get("command_hash"),
            "rendered_command_summary": (fired or latest).get("rendered_command_summary"),
            "input_refs": lineage["inputs"],
            "output_refs": lineage["outputs"],
            "artifact_paths": artifact_paths[:REACTION_LINEAGE_REF_LIMIT],
            "workitem_refs": [],
            "cap_refs": [],
            "trace_refs": [f"trace:{episode_id}"],
            "failure_class": _episode_failure_class(terminal),
            "failure_summary": _clip_text((terminal or {}).get("error") or (terminal or {}).get("summary"), limit=180)
            if status == "failed"
            else None,
            "stdout_excerpt_ref": (terminal or latest).get("stdout_excerpt_ref"),
            "stderr_excerpt_ref": (terminal or latest).get("stderr_excerpt_ref"),
            "search_attributes": {
                "state": status,
                "domain": domain,
                "source_kind": meta.get("source_kind"),
                "operation_id": operation_id,
                "reaction_id": reaction_id,
                "failure_class": _episode_failure_class(terminal),
                "episode_id_source": group.get("episode_id_source"),
            },
            "lineage": lineage,
            "trace_binding": _trace_binding(
                episode_id=episode_id,
                reaction_id=reaction_id,
                domain=domain,
                state=status,
                operation_id=operation_id,
                signal_digest=signal_digest,
                ledger_fingerprint=ledger_fingerprint or None,
                source="reaction_episode" if group.get("reaction_run_id") else "synthetic_reaction_episode",
            ),
        }
        episodes.append(episode)
        by_reaction[reaction_id].append(episode)

    episodes.sort(key=lambda item: str(item.get("ended_at") or item.get("started_at") or ""), reverse=True)
    limited = episodes[:limit]
    limited_ids = {item["episode_id"] for item in limited}
    by_reaction_limited: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reaction_id, rows in by_reaction.items():
        for row in rows:
            if row["episode_id"] in limited_ids:
                by_reaction_limited[reaction_id].append(row)
    return limited, dict(by_reaction_limited)


def _attention_item(
    *,
    ref: str,
    label: str,
    rank_reason: str,
    severity: str,
    confidence: float = 0.8,
    status: str | None = None,
) -> dict[str, Any]:
    return {
        "ref": ref,
        "label": _clip_text(label, limit=140),
        "rank_reason": rank_reason,
        "severity": severity,
        "confidence": confidence,
        "status": status,
    }


def _build_attention(
    *,
    reactions: list[dict[str, Any]],
    episodes: list[dict[str, Any]],
    awaiting_barriers: list[dict[str, Any]],
    summary: Mapping[str, Any],
) -> dict[str, Any]:
    top_reactions = sorted(
        reactions,
        key=lambda row: (
            int(_safe_mapping(row.get("state")).get("sort_rank") or 9),
            str(row.get("last_fired_at") or row.get("last_completed_at") or row.get("last_failed_at") or ""),
        ),
    )[:8]
    failures = [
        row for row in reactions if str(_safe_mapping(row.get("state")).get("state") or "") == "failed"
    ]
    blockers = []
    for row in reactions:
        eligibility = _safe_mapping(row.get("eligibility"))
        gate_id = eligibility.get("primary_blocking_gate_id")
        state = str(_safe_mapping(row.get("state")).get("state") or "")
        if gate_id or state in {"blocked", "cooldown"}:
            blockers.append((row, gate_id or state))
    newly_eligible = [
        row for row in reactions if str(_safe_mapping(row.get("state")).get("state") or "") == "eligible"
    ]
    stale_signals = []
    for row in reactions:
        ladder = _safe_mapping(row.get("eligibility")).get("evaluation_ladder")
        if isinstance(ladder, list) and any(
            isinstance(gate, Mapping)
            and gate.get("gate_id") == "signal_fresh_enough"
            and gate.get("state") == "blocked"
            for gate in ladder
        ):
            stale_signals.append(row)
    top_episodes = sorted(
        episodes,
        key=lambda row: (
            {"running": 0, "fired": 0, "failed": 1, "completed": 5, "suppressed": 6}.get(str(row.get("status")), 7),
            str(row.get("ended_at") or row.get("started_at") or ""),
        ),
    )[:8]
    if awaiting_barriers:
        headline_state = "blocked"
        headline_reason = f"{len(awaiting_barriers)} wake barrier(s) active."
    elif summary.get("failed_count"):
        headline_state = "failed"
        headline_reason = f"{summary.get('failed_count')} reaction(s) need repair attention."
    elif summary.get("eligible_now"):
        headline_state = "eligible"
        headline_reason = f"{summary.get('eligible_now')} reaction(s) can fire when the scheduler runs."
    else:
        headline_state = "quiet"
        headline_reason = "No active reaction blockers or eligible fires in the cached snapshot."
    return {
        "schema": "reaction_attention_v1",
        "headline_state": headline_state,
        "headline_reason": headline_reason,
        "top_reactions": [
            _attention_item(
                ref=f"reaction:{row.get('reaction_id')}",
                label=str(row.get("label") or row.get("reaction_id")),
                rank_reason=str(_safe_mapping(row.get("state")).get("reason_code") or "state_rank"),
                severity=str(_safe_mapping(row.get("state")).get("tone") or "muted"),
                status=str(_safe_mapping(row.get("state")).get("state") or ""),
            )
            for row in top_reactions
        ],
        "top_episodes": [
            _attention_item(
                ref=f"episode:{row.get('episode_id')}",
                label=f"{row.get('reaction_id')} {row.get('status')}",
                rank_reason="episode_status_rank",
                severity="red" if row.get("status") == "failed" else ("amber" if row.get("status") in {"running", "fired"} else "muted"),
                status=str(row.get("status") or ""),
            )
            for row in top_episodes
        ],
        "top_blockers": [
            _attention_item(
                ref=f"reaction:{row.get('reaction_id')}:gate:{gate_id}",
                label=str(row.get("label") or row.get("reaction_id")),
                rank_reason=str(gate_id),
                severity="amber",
                status=str(_safe_mapping(row.get("state")).get("state") or ""),
            )
            for row, gate_id in blockers[:8]
        ],
        "top_failures": [
            _attention_item(
                ref=f"reaction:{row.get('reaction_id')}",
                label=str(row.get("label") or row.get("reaction_id")),
                rank_reason=str(row.get("last_error") or "last_run_failed"),
                severity="red",
                status="failed",
            )
            for row in failures[:8]
        ],
        "stale_signals": [
            _attention_item(
                ref=f"reaction:{row.get('reaction_id')}:signal",
                label=str(row.get("label") or row.get("reaction_id")),
                rank_reason="signal_stale",
                severity="amber",
                status=str(_safe_mapping(row.get("state")).get("state") or ""),
            )
            for row in stale_signals[:8]
        ],
        "newly_eligible": [
            _attention_item(
                ref=f"reaction:{row.get('reaction_id')}",
                label=str(row.get("label") or row.get("reaction_id")),
                rank_reason="eligible_now",
                severity="amber",
                status="eligible",
            )
            for row in newly_eligible[:8]
        ],
        "recently_changed": [
            _attention_item(
                ref=f"episode:{row.get('episode_id')}",
                label=f"{row.get('reaction_id')} {row.get('status')}",
                rank_reason="recent_episode",
                severity="muted",
                status=str(row.get("status") or ""),
            )
            for row in episodes[:8]
        ],
    }


def _control_action(
    action_id: str,
    *,
    action_label: str,
    effect_summary: str,
    side_effects: list[str],
    safety_class: str,
    requires_confirmation: bool,
    starts_runner: bool = False,
    writes_stop_flag: bool = False,
    cache_invalidation: bool = True,
    reason_disabled: str | None = None,
) -> dict[str, Any]:
    return {
        "action_id": action_id,
        "action_label": action_label,
        "effect_summary": effect_summary,
        "side_effects": side_effects,
        "safety_class": safety_class,
        "requires_confirmation": bool(requires_confirmation),
        "starts_runner": bool(starts_runner),
        "writes_stop_flag": bool(writes_stop_flag),
        "cache_invalidation": bool(cache_invalidation),
        "reason_disabled": reason_disabled,
    }


def _build_control_contract(
    *,
    engine_status: str,
    engine_armed: bool,
    reactions: list[dict[str, Any]],
) -> dict[str, Any]:
    engine_actions = []
    if engine_armed:
        engine_actions.append(
            _control_action(
                "disarm_engine",
                action_label="Disarm engine",
                effect_summary="Set desired_armed=false and write the stop flag; in-flight barriers may finish.",
                side_effects=[REACTIONS_STATE_REL, REACTIONS_STOP_FLAG_REL, "snapshot_cache_invalidation"],
                safety_class="runtime_override",
                requires_confirmation=False,
                writes_stop_flag=True,
            )
        )
    else:
        engine_actions.append(
            _control_action(
                "arm_engine",
                action_label="Arm engine",
                effect_summary="Set desired_armed=true; the FastAPI route starts the detached metabolism runner when needed.",
                side_effects=[REACTIONS_STATE_REL, "metabolismd_runner_may_start", "snapshot_cache_invalidation"],
                safety_class="runtime_override",
                requires_confirmation=False,
                starts_runner=True,
            )
        )
    per_reaction = []
    for row in reactions:
        reaction_id = str(row.get("reaction_id") or "")
        effective_armed = bool(row.get("effective_armed"))
        action_id = "disarm_reaction" if effective_armed else "arm_reaction"
        per_reaction.append(
            {
                "reaction_id": reaction_id,
                "override_state": row.get("override_armed"),
                "available_actions": [
                    _control_action(
                        action_id,
                        action_label="Disarm reaction" if effective_armed else "Arm reaction",
                        effect_summary=(
                            "Set this reaction's runtime override_armed=false."
                            if effective_armed
                            else "Set this reaction's runtime override_armed=true."
                        ),
                        side_effects=[REACTIONS_STATE_REL, "snapshot_cache_invalidation"],
                        safety_class="runtime_override",
                        requires_confirmation=False,
                    )
                ],
                "reason_disabled": None if engine_armed else "Engine is disarmed.",
            }
        )
    return {
        "schema": "reaction_control_contract_v1",
        "engine": {
            "current_state": engine_status,
            "available_actions": engine_actions,
        },
        "per_reaction": per_reaction,
        "runtime_semantics": {
            "single_flight": True,
            "cache_invalidates_on_state_write": True,
            "tracked_config_mutable_from_ui": False,
            "state_write_surface": "POST /api/world-model/reactions/state",
            "config_authority": REACTIONS_CONFIG_REL,
        },
    }


def _effective_reaction_armed(reaction: Mapping[str, Any], runtime_entry: Mapping[str, Any]) -> bool:
    override = runtime_entry.get("override_armed")
    if isinstance(override, bool):
        return override
    return bool(reaction.get("enabled_by_default", True))


def _load_reaction_signal(repo_root: Path, reaction: Mapping[str, Any]) -> dict[str, Any]:
    source = _safe_mapping(reaction.get("source"))
    kind = str(source.get("kind") or source.get("source_kind") or "").strip()
    if kind == "raw_seed_coverage":
        action = _safe_mapping(reaction.get("action"))
        action_parameters = _safe_mapping(action.get("parameters"))
        substrate = str(
            source.get("substrate")
            or action_parameters.get("substrate")
            or "raw_seed"
        ).strip() or "raw_seed"
        family = str(
            source.get("family")
            or action_parameters.get("family")
            or "09"
        ).strip() or "09"
        snapshot = load_raw_seed_pipeline_snapshot(
            repo_root,
            family_dir=None,
            family_number=family,
            substrate=substrate,
        )
        return {
            "kind": "raw_seed_coverage",
            "family": family,
            "substrate": substrate,
            "path": snapshot.get("raw_seed_coverage_path"),
            "raw_seed_shards_path": snapshot.get("raw_seed_shards_path"),
            "top_pending_routing_group": snapshot.get("top_pending_routing_group"),
            "pending_routing_groups": snapshot.get("pending_routing_groups") or [],
            "counts": {
                "total_bins": snapshot.get("total_bins"),
                "pending_routing_shards": snapshot.get("pending_routing_shards"),
                "pending_routing_bins": snapshot.get("pending_routing_bins"),
                "max_pending_routing_group_shards": snapshot.get("max_pending_routing_group_shards"),
                "paragraphs_without_atoms": snapshot.get("paragraphs_without_atoms"),
                "total_atomized_shards": snapshot.get("atomized_shards"),
                "review_queue_entries": snapshot.get("review_queue_entries"),
                "review_queue_bins": snapshot.get("review_queue_bins"),
                "fresh_pending_bins": snapshot.get("fresh_pending_bins"),
                "raw_seed_total_paragraphs": snapshot.get("raw_seed_total_paragraphs"),
                "raw_seed_atomized_shards": snapshot.get("raw_seed_atomized_shards"),
                "raw_seed_paragraphs_without_atoms": snapshot.get("raw_seed_paragraphs_without_atoms"),
                "agent_seed_total_paragraphs": snapshot.get("agent_seed_total_paragraphs"),
                "agent_seed_atomized_shards": snapshot.get("agent_seed_atomized_shards"),
                "agent_seed_paragraphs_without_atoms": snapshot.get("agent_seed_paragraphs_without_atoms"),
            },
            "generated_at": snapshot.get("last_updated"),
        }
    if kind == "python_std_compliance_coverage":
        return write_python_std_compliance_coverage(repo_root)
    if kind == "operation_event":
        operation_id = str(source.get("operation_id") or "").strip()
        family = str(source.get("family") or "").strip() or None
        latest = _load_latest_operation_event(
            repo_root,
            operation_id=operation_id or None,
            family=family,
        ) or {}
        if latest:
            return latest
        return {
            "kind": "operation_event",
            "operation_id": operation_id or None,
            "returncode": None,
            "resolved_parameters": {"family": family} if family else {},
        }
    if kind == "hologram_build_status":
        status = load_hologram_build_status(repo_root)
        return {
            **status,
            "phase_list": ",".join(status.get("stale_phase_ids") or []),
        }
    if kind == "work_ledger_status":
        return load_work_ledger_runtime_status(repo_root)
    if kind == "orchestration_event":
        latest = _load_latest_orchestration_event(repo_root) or {}
        return latest
    if kind == "lifecycle_boundary":
        agent_surface = str(source.get("agent_surface") or "").strip() or None
        boundary = str(source.get("boundary") or "").strip() or None
        latest = _load_latest_lifecycle_boundary_event(
            repo_root,
            agent_surface=agent_surface,
            boundary=boundary,
        )
        if not latest:
            return {
                "kind": "session_lifecycle_boundary",
                "agent_surface": agent_surface,
                "boundary": boundary,
                "payload": {},
            }
        # Surface the row's stable_digest as stable_signal_digest so
        # _compute_signal_digest uses it directly. dedupe_by: signal_digest
        # then blocks re-fires of the same boundary without any new state.
        signal: dict[str, Any] = dict(latest)
        stable = str(latest.get("stable_digest") or "").strip()
        if stable:
            signal["stable_signal_digest"] = stable
        # Promote a small set of payload fields to the top level so reaction
        # predicates can match on them via the standard `field: payload.X`
        # path. Keep the full row available for action parameter expansion.
        payload = latest.get("payload") if isinstance(latest.get("payload"), Mapping) else {}
        signal.setdefault("agent_surface", payload.get("agent_surface"))
        signal.setdefault("boundary", payload.get("boundary"))
        signal.setdefault("session_id", payload.get("session_id"))
        return signal
    if kind == "provider_model_catalog_signal":
        # The signal producer is pure (no provider calls, no transform_job
        # builds, no writes); see system.lib.provider_metabolism_signal.
        # Predicate evaluators bind {signal.<flat_field>} so we expose
        # row_count / first_target_row_id / first_provider_id at top level.
        from system.lib.provider_metabolism_signal import (
            derive_provider_model_catalog_signal,
        )

        payload = derive_provider_model_catalog_signal(repo_root)
        # Promote the producer's deterministic signal_digest (covers the
        # projected rows + schema_version) to stable_signal_digest so the
        # engine's _compute_signal_digest reuses it directly, keeping
        # dedupe_by:signal_digest tight to actual catalog content rather
        # than to incidental serialization order.
        producer_digest = str(payload.get("signal_digest") or "").strip()
        if producer_digest:
            payload["stable_signal_digest"] = producer_digest
        return payload
    if kind == "standard_skill_gap_signal":
        # Wave_004B: load the standard-skill gap signal from the
        # hologram-projected pairing map. The producer is pure-read
        # (no mutation, no provider calls). The digest covers the sorted
        # missing-standard ids + standards_total, so dedupe_by:signal_digest
        # blocks re-fires while the gap composition is unchanged.
        from system.lib.compliance_reaction_signals import (
            build_standard_skill_gap_signal,
        )

        payload = build_standard_skill_gap_signal(repo_root)
        producer_digest = str(payload.get("digest") or "").strip()
        if producer_digest:
            payload["stable_signal_digest"] = producer_digest
        return payload
    if kind == "compliance_coverage_signal":
        # Wave_004B: load the cross-standard compliance coverage signal from
        # the hologram-projected ledger. coverage_low fires when ready_now
        # has at least one entry OR any per-standard rate is below the floor.
        # Pure-read producer; digest covers ready_now ids + below_floor ids
        # + ledger generated_at.
        from system.lib.compliance_reaction_signals import (
            build_compliance_coverage_signal,
        )

        payload = build_compliance_coverage_signal(repo_root)
        producer_digest = str(payload.get("digest") or "").strip()
        if producer_digest:
            payload["stable_signal_digest"] = producer_digest
        return payload
    return {"kind": kind or "unknown"}


_SUPPORTED_SOURCE_KINDS: tuple[str, ...] = (
    "raw_seed_coverage",
    "raw_seed_pipeline_status",
    "python_std_compliance_coverage",
    "operation_event",
    "hologram_build_status",
    "work_ledger_status",
    "orchestration_event",
    "lifecycle_boundary",
    "provider_model_catalog_signal",
    "standard_skill_gap_signal",
    "compliance_coverage_signal",
)


def supported_source_kinds() -> list[str]:
    """
    [ACTION]
    - Teleology: Wave_004B operator-visible audit. Return the explicit list of
      source.kind values that ``_load_source_signal`` resolves natively. Any
      reaction in reactions.yaml whose source.kind is NOT in this list is
      authored doctrine awaiting engine-loader integration.
    """
    return list(_SUPPORTED_SOURCE_KINDS)


def preview_reaction(repo_root: Path, reaction_id: str) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004B2 proof helper. Public wrapper over the engine's
      private _evaluate_reaction_candidate so reaction_proof.py and tests can
      ask "would this reaction fire right now, with what signal_digest, what
      operation, and what rendered command?" — without firing, without
      mutating engine state, and without re-implementing predicate/digest
      semantics.
    """
    config = load_reactions_config(repo_root)
    reactions = [r for r in (config.get("reactions") or []) if isinstance(r, Mapping)]
    target = next((r for r in reactions if str(r.get("reaction_id") or "") == reaction_id), None)
    if target is None:
        return {
            "kind": "reaction_preview",
            "schema_version": "reaction_preview_v1",
            "reaction_id": reaction_id,
            "status": "unknown_reaction_id",
        }
    state = ensure_reactions_state(repo_root)
    now = _now_dt()
    evaluation = _evaluate_reaction_candidate(repo_root, state, target, now)
    action = _safe_mapping(target.get("action"))
    operation_id = str(action.get("operation_id") or "").strip()
    rendered_command: str | None = None
    render_error: str | None = None
    try:
        prepared = prepare_launch_operation(
            repo_root,
            operation_id=operation_id,
            parameters=evaluation.get("action_parameters") or {},
        )
        rendered_command = prepared.command
        resolved_parameters = dict(prepared.resolved_parameters)
    except Exception as exc:
        render_error = f"{exc.__class__.__name__}: {exc}"
        resolved_parameters = {}
    return {
        "kind": "reaction_preview",
        "schema_version": "reaction_preview_v1",
        "reaction_id": reaction_id,
        "source_kind": str(_safe_mapping(target.get("source")).get("kind") or ""),
        "supported_source_kind": str(_safe_mapping(target.get("source")).get("kind") or "") in _SUPPORTED_SOURCE_KINDS,
        "matched": bool(evaluation.get("matched")),
        "can_fire": bool(evaluation.get("can_fire")),
        "preview_reason": evaluation.get("preview_reason"),
        "signal_digest": evaluation.get("signal_digest"),
        "ledger_fingerprint": evaluation.get("ledger_fingerprint"),
        "cooldown_active": bool(evaluation.get("cooldown_active")),
        "operation_id": operation_id,
        "action_parameters": evaluation.get("action_parameters"),
        "resolved_parameters": resolved_parameters,
        "rendered_command": rendered_command,
        "render_error": render_error,
        "enabled_by_default": bool(target.get("enabled_by_default")),
        "mutation_policy": "candidate_packet_only",
    }


def tick_engine_targeted(
    repo_root: Path,
    *,
    reaction_ids: Sequence[str],
    wait: bool = True,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004B3 daemon-grade proof. Fire one specific reaction id
      through the SAME path the always-on daemon uses on a normal tick:
      _evaluate_reaction_candidate (matched + can_fire), prepare_launch_operation
      (rendered command), runtime entry update (last_fired_signal_digest,
      last_fired_ledger_fingerprint, last_result=fired, last_operation_id),
      ledger row with ``kind: reaction_fired`` (NOT manual_proof), orchestration
      event, subprocess execution, _finalize_action_state (cooldown_until +
      _record_completed_digest). After this returns, a second evaluation must
      dedupe by signal_digest or completed_digest_fingerprint.
    - Mechanism: targeted-allowlist replacement for tick_engine; same path,
      same state writes, but only one reaction id at a time so the proof is
      unambiguous and a higher-priority unrelated reaction cannot win.
    - Non-goal: replace tick_engine for production daemon use, manage barriers
      across multi-reaction queues, or emit reaction_fired_manual_proof rows
      (Wave_004B2 fire_reaction is the manual path; this is the daemon path).
    """
    if not reaction_ids:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "status": "no_reaction_ids",
            "reaction_ids": [],
        }
    target_id = str(reaction_ids[0]).strip()
    config = load_reactions_config(repo_root)
    reactions = [r for r in (config.get("reactions") or []) if isinstance(r, Mapping)]
    target = next((r for r in reactions if str(r.get("reaction_id") or "") == target_id), None)
    if target is None:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "reaction_id": target_id,
            "status": "unknown_reaction_id",
        }
    state = ensure_reactions_state(repo_root)
    state.setdefault("desired_armed", True)
    state["desired_armed"] = True
    save_reactions_state(repo_root, state)
    state = ensure_reactions_state(repo_root)
    now = _now_dt()
    evaluation = _evaluate_reaction_candidate(repo_root, state, target, now)
    matched = bool(evaluation.get("matched"))
    can_fire = bool(evaluation.get("can_fire"))
    if not matched:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "reaction_id": target_id,
            "status": "predicate_not_matched",
            "preview_reason": evaluation.get("preview_reason"),
            "signal_digest": evaluation.get("signal_digest"),
        }
    if not can_fire:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "reaction_id": target_id,
            "status": "cannot_fire_dedupe_or_cooldown",
            "preview_reason": evaluation.get("preview_reason"),
            "signal_digest": evaluation.get("signal_digest"),
            "cooldown_active": evaluation.get("cooldown_active"),
        }
    action = _safe_mapping(target.get("action"))
    operation_id = str(action.get("operation_id") or "").strip()
    parameters = evaluation.get("action_parameters") or {}
    try:
        prepared = prepare_launch_operation(repo_root, operation_id=operation_id, parameters=parameters)
    except Exception as exc:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "reaction_id": target_id,
            "status": "render_failed",
            "render_error": f"{exc.__class__.__name__}: {exc}",
        }
    started_at = now.isoformat()
    reaction_run_id = _new_reaction_run_id(
        reaction_id=target_id,
        operation_id=operation_id,
        signal_digest=str(evaluation["signal_digest"]),
        started_at=started_at,
    )
    runtime_entry = _reaction_runtime_entry(state, target_id)
    runtime_entry.update({
        "last_fired_at": started_at,
        "last_reaction_run_id": reaction_run_id,
        "last_fired_signal_digest": evaluation["signal_digest"],
        "last_fired_ledger_fingerprint": evaluation.get("ledger_fingerprint") or "",
        "last_result": "fired",
        "last_operation_id": operation_id,
        "last_signal": evaluation["signal"],
        "last_error": None,
    })
    _set_reaction_runtime_entry(state, target_id, runtime_entry)
    save_reactions_state(repo_root, state)
    _append_ledger_row(
        repo_root,
        "reaction_fired",
        {
            "reaction_id": target_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "fired_at": started_at,
            "signal_digest": evaluation["signal_digest"],
            "ledger_fingerprint": evaluation.get("ledger_fingerprint") or "",
            "signal": evaluation["signal"],
            "command": prepared.command,
            "parameters": parameters,
            "runner_pid": None,
            "log_path": None,
            "tick_kind": "targeted_tick",
        },
    )
    _append_orchestration_event(
        repo_root,
        "reaction_fired_v1",
        {
            "reaction_id": target_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "summary": f"Reaction {target_id} fired {operation_id} via targeted tick.",
            "signal_digest": evaluation["signal_digest"],
        },
    )
    if not wait:
        return {
            "kind": "reaction_targeted_tick_result",
            "schema_version": "reaction_targeted_tick_result_v1",
            "reaction_id": target_id,
            "status": "fired_no_wait",
            "ledger_kind": "reaction_fired",
            "reaction_run_id": reaction_run_id,
            "signal_digest": evaluation["signal_digest"],
            "operation_id": operation_id,
            "rendered_command": prepared.command,
        }
    import subprocess

    proc_started = _now_dt()
    try:
        proc = subprocess.run(
            shlex.split(prepared.command),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        returncode = proc.returncode
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
    except subprocess.TimeoutExpired:
        returncode = 124
        stdout = ""
        stderr = "subprocess timed out"
    duration_ms = int((_now_dt() - proc_started).total_seconds() * 1000)
    outcome = "completed" if returncode == 0 else "failed"
    _finalize_action_state(
        repo_root,
        reaction_id=target_id,
        reaction_run_id=reaction_run_id,
        operation_id=operation_id,
        started_at=started_at,
        signal_digest=evaluation["signal_digest"],
        outcome=outcome,
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        duration_ms=duration_ms,
        ledger_fingerprint=evaluation.get("ledger_fingerprint") or "",
    )
    written: list[str] = []
    digest = str(evaluation["signal_digest"] or "")
    if operation_id == "standard_skill_pairing_campaign":
        candidate = repo_root / "state/meta_missions/standard_skill_pairing" / f"std_skill_pairing_{digest}" / "campaign_packet.json"
        if candidate.is_file():
            written.append(candidate.relative_to(repo_root).as_posix())
    elif operation_id == "compliance_autocure_campaign":
        candidate = repo_root / "state/meta_missions/compliance_autocure" / f"compliance_autocure_{digest}" / "campaign_packet.json"
        if candidate.is_file():
            written.append(candidate.relative_to(repo_root).as_posix())
    state_after = ensure_reactions_state(repo_root)
    runtime_after = _reaction_runtime_entry(state_after, target_id)
    return {
        "kind": "reaction_targeted_tick_result",
        "schema_version": "reaction_targeted_tick_result_v1",
        "reaction_id": target_id,
        "status": "completed" if returncode == 0 else "operation_failed",
        "ledger_kind": "reaction_fired",
        "reaction_run_id": reaction_run_id,
        "signal_digest": evaluation["signal_digest"],
        "ledger_fingerprint": evaluation.get("ledger_fingerprint"),
        "operation_id": operation_id,
        "returncode": returncode,
        "duration_ms": duration_ms,
        "written": written,
        "rendered_command": prepared.command,
        "dedupe_state_recorded": bool(runtime_after.get("last_fired_signal_digest") == evaluation["signal_digest"]),
        "cooldown_until": runtime_after.get("cooldown_until"),
        "promotion_state": "draft",
        "mutation_policy": "candidate_packet_only",
    }


def fire_reaction(
    repo_root: Path,
    reaction_id: str,
    *,
    force: bool = False,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Wave_004B2 proof helper. Execute one reaction's prepared
      operation through the same shape the engine uses (predicate, digest,
      parameters, prepare_launch_operation, subprocess), then append a
      reactions_ledger row tagged ``reaction_fired_manual_proof`` so the proof
      is durable. Refuses to fire when matched=false unless force=True; never
      writes outside state/meta_missions/<lane>/<slug>/.
    - Mechanism: Calls preview_reaction for the evaluation, prepare_launch
      for the command, then subprocess.run; ledger row carries reaction_id +
      signal_digest + returncode + stdout_excerpt + written_paths.
    - Non-goal: Replace tick_engine, manage barriers, run multiple reactions,
      mutate reactions_state, or interact with the always-on daemon.
    """
    preview = preview_reaction(repo_root, reaction_id)
    if preview.get("status") == "unknown_reaction_id":
        return {
            "kind": "reaction_fire_result",
            "schema_version": "reaction_fire_result_v1",
            "reaction_id": reaction_id,
            "status": "unknown_reaction_id",
        }
    matched = bool(preview.get("matched"))
    can_fire = bool(preview.get("can_fire"))
    if not matched and not force:
        return {
            "kind": "reaction_fire_result",
            "schema_version": "reaction_fire_result_v1",
            "reaction_id": reaction_id,
            "status": "predicate_not_matched",
            "preview": preview,
        }
    if not preview.get("rendered_command"):
        return {
            "kind": "reaction_fire_result",
            "schema_version": "reaction_fire_result_v1",
            "reaction_id": reaction_id,
            "status": "render_failed",
            "preview": preview,
        }
    if not preview.get("supported_source_kind"):
        return {
            "kind": "reaction_fire_result",
            "schema_version": "reaction_fire_result_v1",
            "reaction_id": reaction_id,
            "status": "unsupported_source_kind",
            "preview": preview,
        }
    rendered = str(preview["rendered_command"])
    started_at = _utc_now()
    import subprocess

    try:
        proc = subprocess.run(
            shlex.split(rendered),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        returncode = proc.returncode
        stdout_excerpt = (proc.stdout or "")[:1500]
        stderr_excerpt = (proc.stderr or "")[:500]
    except subprocess.TimeoutExpired:
        returncode = 124
        stdout_excerpt = ""
        stderr_excerpt = "subprocess timed out"
    completed_at = _utc_now()

    operation_id = str(preview.get("operation_id") or "")
    reaction_run_id = _new_reaction_run_id(
        reaction_id=reaction_id,
        operation_id=operation_id,
        signal_digest=str(preview.get("signal_digest") or ""),
        started_at=started_at,
    )
    written: list[str] = []
    if operation_id == "standard_skill_pairing_campaign":
        digest = str(preview.get("signal_digest") or "")
        candidate = (
            repo_root
            / "state/meta_missions/standard_skill_pairing"
            / f"std_skill_pairing_{digest}"
            / "campaign_packet.json"
        )
        if candidate.is_file():
            written.append(candidate.relative_to(repo_root).as_posix())
    elif operation_id == "compliance_autocure_campaign":
        digest = str(preview.get("signal_digest") or "")
        candidate = (
            repo_root
            / "state/meta_missions/compliance_autocure"
            / f"compliance_autocure_{digest}"
            / "campaign_packet.json"
        )
        if candidate.is_file():
            written.append(candidate.relative_to(repo_root).as_posix())

    result = {
        "kind": "reaction_fire_result",
        "schema_version": "reaction_fire_result_v1",
        "reaction_id": reaction_id,
        "status": "ok" if returncode == 0 else "operation_failed",
        "started_at": started_at,
        "completed_at": completed_at,
        "returncode": returncode,
        "rendered_command": rendered,
        "operation_id": operation_id,
        "reaction_run_id": reaction_run_id,
        "source_kind": preview.get("source_kind"),
        "signal_digest": preview.get("signal_digest"),
        "ledger_fingerprint": preview.get("ledger_fingerprint"),
        "matched": matched,
        "can_fire": can_fire,
        "force": force,
        "stdout_excerpt": stdout_excerpt,
        "stderr_excerpt": stderr_excerpt,
        "written": written,
        "mutation_policy": "candidate_packet_only",
        "promotion_state": "draft",
    }
    _append_ledger_row(
        repo_root,
        "reaction_fired_manual_proof",
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "signal_digest": preview.get("signal_digest"),
            "ledger_fingerprint": preview.get("ledger_fingerprint"),
            "operation_id": operation_id,
            "returncode": returncode,
            "written": written,
            "mutation_policy": "candidate_packet_only",
            "promotion_state": "draft",
            "force": force,
            "summary": f"Wave_004B2 manual proof fire of {reaction_id} (returncode={returncode})",
        },
    )
    return result


def _barrier_is_active(barrier: Mapping[str, Any], now: datetime) -> bool:
    status = str(barrier.get("status") or "").strip().lower()
    if status in {"pending", "running"}:
        return True
    if status == "cooldown":
        wake_at = str(barrier.get("wake_at") or "").strip()
        if not wake_at:
            return False
        try:
            wake_dt = datetime.fromisoformat(wake_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if wake_dt.tzinfo is None:
            wake_dt = wake_dt.replace(tzinfo=timezone.utc)
        return wake_dt > now
    return False


def _normalize_barrier(barrier: Mapping[str, Any]) -> dict[str, Any]:
    kind = str(barrier.get("kind") or "").strip() or "operation_completion"
    label = str(barrier.get("label") or "").strip()
    operation_id = str(barrier.get("operation_id") or "").strip() or None
    wake_at = str(barrier.get("wake_at") or "").strip() or None
    if not label:
        if kind == "cooldown":
            label = "cooldown"
        elif operation_id:
            label = f"awaiting operation: {operation_id}"
        else:
            label = "awaiting barrier"
    return {
        "reaction_id": barrier.get("reaction_id"),
        "reaction_run_id": barrier.get("reaction_run_id"),
        "kind": kind,
        "label": label,
        "status": barrier.get("status") or "pending",
        "operation_id": operation_id,
        "wake_at": wake_at,
        "started_at": barrier.get("started_at"),
    }


def _append_ledger_row(repo_root: Path, kind: str, payload: Mapping[str, Any]) -> None:
    now = _now_dt()
    row = {
        "kind": kind,
        "schema_version": f"{kind}_v1",
        "recorded_at": now.isoformat(),
        "event_id": _event_id("rxn", now),
        **dict(payload),
    }
    _append_jsonl(reactions_ledger_path(repo_root), row)


def _append_orchestration_event(repo_root: Path, kind: str, payload: Mapping[str, Any]) -> None:
    now = _now_dt()
    row = {
        "kind": kind,
        "schema_version": kind,
        "recorded_at": now.isoformat(),
        "event_id": _event_id("rxnorch", now),
        **dict(payload),
    }
    _append_jsonl(orchestration_events_path(repo_root), row)


def _maybe_clear_expired_barrier(repo_root: Path, state: dict[str, Any], now: datetime) -> bool:
    barriers = state.get("awaiting_barriers")
    if not isinstance(barriers, list) or not barriers:
        return False
    barrier = barriers[0] if isinstance(barriers[0], Mapping) else None
    if not barrier or not _barrier_is_active(barrier, now):
        reaction_id = str(barrier.get("reaction_id") or "").strip() if barrier else ""
        state["awaiting_barriers"] = []
        state["active_reaction_id"] = None
        state["status"] = "armed"
        if reaction_id:
            entry = _reaction_runtime_entry(state, reaction_id)
            entry["cooldown_until"] = None
            _set_reaction_runtime_entry(state, reaction_id, entry)
        _append_ledger_row(
            repo_root,
            "reaction_state_changed",
            {"summary": "Cleared expired wake barrier.", "reaction_id": reaction_id or None},
        )
        return True
    return False


def _mark_unexpected_runner_exit(repo_root: Path, state: dict[str, Any], barrier: Mapping[str, Any]) -> None:
    reaction_id = str(barrier.get("reaction_id") or "").strip()
    operation_id = str(barrier.get("operation_id") or "").strip()
    reaction_run_id = str(barrier.get("reaction_run_id") or "").strip()
    entry = _reaction_runtime_entry(state, reaction_id)
    failed_at = _utc_now()
    entry.update(
        {
            "last_failed_at": failed_at,
            "last_result": "failed",
            "last_error": "runner exited before writing completion state",
        }
    )
    _set_reaction_runtime_entry(state, reaction_id, entry)
    state["awaiting_barriers"] = []
    state["active_reaction_id"] = None
    state["status"] = "armed"
    state["last_error"] = "runner exited before writing completion state"
    _append_ledger_row(
        repo_root,
        "reaction_failed",
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id or None,
            "operation_id": operation_id or None,
            "failed_at": failed_at,
            "error": "runner exited before writing completion state",
        },
    )
    _append_orchestration_event(
        repo_root,
        "reaction_failed_v1",
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id or None,
            "operation_id": operation_id or None,
            "summary": f"Reaction {reaction_id} failed: runner exited before writing completion state.",
            "error": "runner exited before writing completion state",
        },
    )


def _evaluate_reaction_candidate(
    repo_root: Path,
    state: Mapping[str, Any],
    reaction: Mapping[str, Any],
    now: datetime,
    *,
    signal_mode: str = "live",
) -> dict[str, Any]:
    reaction_id = str(reaction.get("reaction_id") or "").strip()
    runtime_entry = _reaction_runtime_entry(state, reaction_id)
    cached_signal = runtime_entry.get("last_signal")
    if signal_mode == "cached" and isinstance(cached_signal, Mapping):
        signal = dict(cached_signal)
    elif signal_mode == "cached":
        signal = {"kind": _safe_mapping(reaction.get("source")).get("kind") or "unknown"}
    else:
        signal = _load_reaction_signal(repo_root, reaction)
    signal_digest = _compute_signal_digest(reaction, signal)
    ledger_fingerprint = _compute_ledger_fingerprint(reaction, signal)
    matched = _predicate_matches(signal, _safe_mapping(reaction.get("predicate")))
    action = _safe_mapping(reaction.get("action"))
    parameters = _render_action_parameters(action, signal)
    effective_armed = _effective_reaction_armed(reaction, runtime_entry)

    cooldown_until_raw = str(runtime_entry.get("cooldown_until") or "").strip()
    cooldown_active = False
    if cooldown_until_raw:
        try:
            cooldown_until = datetime.fromisoformat(cooldown_until_raw.replace("Z", "+00:00"))
            if cooldown_until.tzinfo is None:
                cooldown_until = cooldown_until.replace(tzinfo=timezone.utc)
            cooldown_active = cooldown_until > now
        except ValueError:
            cooldown_active = False

    gate = _safe_mapping(reaction.get("gate"))
    dedupe_by = str(gate.get("dedupe_by") or "").strip()
    last_fired_signal_digest = str(runtime_entry.get("last_fired_signal_digest") or "").strip()
    signal_digest_dedupe_hit = (
        dedupe_by == "signal_digest"
        and signal_digest == last_fired_signal_digest
        and bool(last_fired_signal_digest)
    )

    # Schema v2: terminal-outcome-plus-fingerprint dedupe. Pairs the signal
    # digest with the ledger fingerprint so:
    #   * Same digest, same fingerprint, prior terminal outcome → suppress
    #     (prevents repeat-fail loops on unchanged source material).
    #   * Same digest, different fingerprint → allow fire (digest collision
    #     or genuine content change under a stable digest).
    #   * Different digest → let the existing last_fired check govern.
    completed_entry = _completed_digest_entry(state, signal_digest)
    completed_fingerprint = str(completed_entry.get("ledger_fingerprint") or "").strip()
    completed_outcome = str(completed_entry.get("outcome") or "").strip()
    terminal_fingerprint_dedupe_hit = (
        dedupe_by == "signal_digest"
        and completed_outcome in {"completed", "failed"}
        and bool(completed_fingerprint)
        and completed_fingerprint == ledger_fingerprint
    )

    dedupe_hit = signal_digest_dedupe_hit or terminal_fingerprint_dedupe_hit

    can_fire = matched and effective_armed and not cooldown_active and not dedupe_hit
    if not matched:
        preview_reason = "signal predicate did not match"
    elif cooldown_active:
        preview_reason = "cooldown active"
    elif terminal_fingerprint_dedupe_hit:
        preview_reason = f"deduped by completed_digest_fingerprint ({completed_outcome})"
    elif signal_digest_dedupe_hit:
        preview_reason = "deduped by signal_digest"
    elif not effective_armed:
        preview_reason = "disarmed by runtime override"
    else:
        preview_reason = "would fire"

    return {
        "reaction_id": reaction_id,
        "signal": signal,
        "signal_digest": signal_digest,
        "ledger_fingerprint": ledger_fingerprint,
        "matched": matched,
        "can_fire": can_fire,
        "effective_armed": effective_armed,
        "action_parameters": parameters,
        "preview_reason": preview_reason,
        "cooldown_active": cooldown_active,
        "would_fire_now": can_fire,
        "completed_digest_entry": completed_entry,
    }


def _maybe_record_suppression(
    repo_root: Path,
    state: dict[str, Any],
    *,
    reaction_id: str,
    signal: Mapping[str, Any],
    signal_digest: str,
    reason: str,
) -> None:
    if not reaction_id or not reason:
        return
    entry = _reaction_runtime_entry(state, reaction_id)
    last_reason = str(entry.get("last_suppressed_reason") or "").strip()
    last_digest = str(entry.get("last_suppressed_signal_digest") or "").strip()
    if last_reason == reason and last_digest == signal_digest:
        return
    recorded_at = _utc_now()
    entry["last_suppressed_at"] = recorded_at
    entry["last_suppressed_reason"] = reason
    entry["last_suppressed_signal_digest"] = signal_digest
    _set_reaction_runtime_entry(state, reaction_id, entry)
    _append_ledger_row(
        repo_root,
        "reaction_suppressed",
        {
            "reaction_id": reaction_id,
            "reason": reason,
            "signal_digest": signal_digest,
            "signal": dict(signal),
            "suppressed_at": recorded_at,
        },
    )


def build_ready_deferred_reactions_projection(
    repo_root: Path,
    *,
    state: Optional[Mapping[str, Any]] = None,
    config: Optional[Mapping[str, Any]] = None,
    signal_mode: str = "cached",
    limit: int = 5,
) -> list[dict[str, Any]]:
    """[ACTION] Build the compact ready-but-deferred projection used by quick pulse.

    This intentionally avoids `build_reactions_snapshot`, whose frontend,
    timeline, diagram, and graph-scene payloads are useful for the reactions
    route but too expensive for the bootstrap pulse hot path.
    """
    now = _now_dt()
    state_payload = dict(state) if isinstance(state, Mapping) else load_reactions_state(repo_root)
    if isinstance(config, Mapping):
        config_payload = dict(config)
    elif signal_mode == "cached":
        config_payload = _load_reactions_config_fast(repo_root) or load_reactions_config(repo_root)
    else:
        config_payload = load_reactions_config(repo_root)

    active = str(state_payload.get("active_reaction_id") or "").strip() or None
    barriers_raw = [
        dict(barrier)
        for barrier in (state_payload.get("awaiting_barriers") or [])
        if isinstance(barrier, Mapping) and _barrier_is_active(barrier, now)
    ]
    awaiting_barriers = [_normalize_barrier(barrier) for barrier in barriers_raw]
    barrier_owner: str | None = None
    barrier_kind: str | None = None
    if awaiting_barriers:
        barrier_owner = str(awaiting_barriers[0].get("reaction_id") or "").strip() or None
        barrier_kind = str(awaiting_barriers[0].get("kind") or "").strip() or None
    blocker = barrier_owner or active

    bound = max(1, int(limit))
    deferred: list[dict[str, Any]] = []
    for reaction in sorted(config_payload.get("reactions") or [], key=_reaction_sort_key):
        if not isinstance(reaction, Mapping):
            continue
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        if not reaction_id:
            continue
        if active and reaction_id == active:
            continue
        if barrier_owner and reaction_id == barrier_owner:
            continue
        evaluation = _evaluate_reaction_candidate(
            repo_root,
            state_payload,
            reaction,
            now,
            signal_mode=signal_mode,
        )
        if not evaluation.get("would_fire_now"):
            continue
        action = _safe_mapping(reaction.get("action"))
        params = evaluation.get("action_parameters")
        if not isinstance(params, Mapping):
            params = {}
        deferred.append(
            {
                "reaction_id": reaction_id,
                "operation_id": action.get("operation_id"),
                "priority": str(reaction.get("priority") or "").strip(),
                "preview_reason": str(evaluation.get("preview_reason") or "").strip(),
                "target_row_id": str(params.get("target_row_id") or "").strip(),
                "blocked_by": blocker,
                "barrier_kind": barrier_kind if barrier_owner else None,
            }
        )
        if len(deferred) >= bound:
            break
    return deferred


def build_reactions_snapshot(
    repo_root: Path,
    *,
    state: Optional[Mapping[str, Any]] = None,
    config: Optional[Mapping[str, Any]] = None,
    signal_mode: str = "live",
    diagram_mode: str = "full",
    graph_scene_mode: str = "manifest",
    previous_graph_scene_revision: str | None = None,
) -> dict[str, Any]:
    """[ACTION] Build the complete reaction snapshot for status, frontend, and routing views.

    ``signal_mode="live"`` is exact and re-runs every configured signal
    producer. ``signal_mode="cached"`` evaluates predicates against each
    reaction's persisted ``last_signal`` from ``reactions_state.json``; use it
    for read-only entry surfaces that need cheap visibility, not scheduler
    authority.
    """
    perf_started = time.perf_counter()
    now = _now_dt()
    observed_at = now.isoformat()
    state_payload = dict(state) if isinstance(state, Mapping) else load_reactions_state(repo_root)
    if isinstance(config, Mapping):
        config_payload = dict(config)
    elif signal_mode == "cached":
        config_payload = _load_reactions_config_fast(repo_root) or load_reactions_config(repo_root)
    else:
        config_payload = load_reactions_config(repo_root)
    desired_armed = bool(state_payload.get("desired_armed"))
    pid = state_payload.get("pid")
    engine_running = _pid_running(pid)
    barriers_raw = [
        dict(barrier)
        for barrier in (state_payload.get("awaiting_barriers") or [])
        if isinstance(barrier, Mapping) and _barrier_is_active(barrier, now)
    ]
    awaiting_barriers = [_normalize_barrier(barrier) for barrier in barriers_raw]

    if not desired_armed:
        engine_status = "disarmed"
    elif awaiting_barriers:
        engine_status = awaiting_barriers[0]["kind"] == "cooldown" and "cooldown" or "awaiting_barrier"
    elif engine_running:
        engine_status = "armed"
    else:
        engine_status = "armed_waiting_runner"

    timeline, timeline_by_reaction, timeline_meta = _build_reaction_event_views(repo_root)
    normalized_events = list(timeline_meta.pop("normalized_events", []) or [])
    barriers_by_reaction: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for barrier in awaiting_barriers:
        owner = str(barrier.get("reaction_id") or "").strip()
        if owner:
            barriers_by_reaction[owner].append(barrier)

    reactions = []
    reaction_meta: dict[str, dict[str, Any]] = {}
    last_fired_at = state_payload.get("last_fired_at")
    for reaction in sorted(config_payload.get("reactions") or [], key=_reaction_sort_key):
        if not isinstance(reaction, Mapping):
            continue
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        runtime_entry = _reaction_runtime_entry(state_payload, reaction_id)
        source = _safe_mapping(reaction.get("source"))
        source_kind = source.get("kind")
        action = _safe_mapping(reaction.get("action"))
        operation_id = action.get("operation_id")
        evaluation = _evaluate_reaction_candidate(
            repo_root,
            state_payload,
            reaction,
            now,
            signal_mode=signal_mode,
        )
        if runtime_entry.get("last_fired_at"):
            if not last_fired_at or str(runtime_entry.get("last_fired_at")) > str(last_fired_at):
                last_fired_at = runtime_entry.get("last_fired_at")
        predicate_view = _predicate_view(
            _safe_mapping(reaction.get("predicate")),
            evaluation["signal"],
            matched=bool(evaluation.get("matched")),
        )
        signal_view = _signal_summary(str(source_kind or ""), evaluation["signal"])
        recent_events = list(timeline_by_reaction.get(reaction_id) or [])[:6]
        domain = _reaction_domain(
            reaction_id,
            source_kind=str(source_kind or ""),
            action_operation_id=str(operation_id or ""),
            source=source,
        )
        state_view = _reaction_state_view(
            reaction_id=reaction_id,
            engine_armed=desired_armed,
            active_reaction_id=state_payload.get("active_reaction_id"),
            barriers=barriers_by_reaction.get(reaction_id, []),
            runtime_entry=runtime_entry,
            evaluation=evaluation,
        )
        operation_catalog = _operation_catalog_entry(operation_id)
        operation_safety = _operation_safety(operation_catalog)
        evaluation_ladder = _build_evaluation_ladder(
            reaction=reaction,
            runtime_entry=runtime_entry,
            evaluation=evaluation,
            state_view=state_view,
            engine_armed=desired_armed,
            barriers_for_reaction=barriers_by_reaction.get(reaction_id, []),
            global_barriers=awaiting_barriers,
            operation_catalog=operation_catalog,
            signal_mode=signal_mode,
            observed_at=observed_at,
        )
        causal_chain = _causal_chain_view(
            reaction_id=reaction_id,
            domain=domain,
            label=reaction.get("label"),
            source_kind=str(source_kind or ""),
            predicate=predicate_view,
            state=state_view,
            action_operation_id=str(operation_id or ""),
            recent_events=recent_events,
        )
        lineage = _build_reaction_lineage(
            reaction_id=reaction_id,
            source_kind=str(source_kind or ""),
            domain=domain,
            signal=evaluation["signal"],
            signal_digest=evaluation["signal_digest"],
            ledger_fingerprint=str(evaluation.get("ledger_fingerprint") or ""),
            operation_id=str(operation_id or ""),
            action_parameters=evaluation["action_parameters"],
            recent_events=recent_events,
        )
        trace_binding = _trace_binding(
            episode_id=f"reaction:{reaction_id}:{str(evaluation['signal_digest'])[:12]}",
            reaction_id=reaction_id,
            domain=domain,
            state=str(state_view.get("state") or "unknown"),
            operation_id=str(operation_id or ""),
            signal_digest=str(evaluation.get("signal_digest") or ""),
            ledger_fingerprint=str(evaluation.get("ledger_fingerprint") or "") or None,
            source="synthetic_reaction_state",
        )
        reaction_meta[reaction_id] = {
            "domain": domain,
            "source_kind": source_kind,
            "operation_id": operation_id,
            "signal": evaluation["signal"],
            "signal_digest": evaluation["signal_digest"],
            "ledger_fingerprint": evaluation.get("ledger_fingerprint"),
            "action_parameters": evaluation["action_parameters"],
        }
        reactions.append(
            {
                "reaction_id": reaction_id,
                "label": reaction.get("label"),
                "domain": domain,
                "priority": reaction.get("priority"),
                "source_kind": source_kind,
                "enabled_by_default": bool(reaction.get("enabled_by_default", True)),
                "override_armed": runtime_entry.get("override_armed"),
                "effective_armed": evaluation["effective_armed"],
                "last_signal_digest": evaluation["signal_digest"],
                "last_signal_at": state_payload.get("last_tick_at"),
                "last_fired_at": runtime_entry.get("last_fired_at"),
                "last_completed_at": runtime_entry.get("last_completed_at"),
                "last_failed_at": runtime_entry.get("last_failed_at"),
                "cooldown_until": runtime_entry.get("cooldown_until"),
                "last_result": runtime_entry.get("last_result"),
                "last_error": runtime_entry.get("last_error"),
                "last_operation_id": runtime_entry.get("last_operation_id"),
                "current_signal": evaluation["signal"],
                "would_fire_now": evaluation["would_fire_now"],
                "preview_reason": evaluation["preview_reason"],
                "predicate": predicate_view,
                "state": state_view,
                "eligibility": {
                    "matched": bool(evaluation.get("matched")),
                    "can_fire": bool(evaluation.get("can_fire")),
                    "effective_armed": bool(evaluation.get("effective_armed")),
                    "cooldown_active": bool(evaluation.get("cooldown_active")),
                    "dedupe": {
                        "signal_digest": evaluation.get("signal_digest"),
                        "ledger_fingerprint": evaluation.get("ledger_fingerprint"),
                        "completed_digest_entry": evaluation.get("completed_digest_entry") or {},
                    },
                    "why_not_eligible": state_view.get("why_not_eligible"),
                    "reason_code": state_view.get("reason_code"),
                    **evaluation_ladder,
                },
                "signal_summary": signal_view,
                "display": {
                    "title": reaction.get("label") or _human_label(reaction_id),
                    "subtitle": f"{_human_label(domain)} / {_human_label(str(source_kind or 'unknown'))}",
                    "primary_state": state_view.get("label"),
                    "primary_metric": signal_view.get("summary"),
                    "chips": [
                        {"label": domain, "tone": "muted"},
                        {"label": reaction.get("priority") or "medium", "tone": "muted"},
                        {"label": state_view.get("state"), "tone": state_view.get("tone")},
                    ],
                },
                "causal_chain": causal_chain,
                "lineage": lineage,
                "trace_binding": trace_binding,
                "search_attributes": {
                    "state": state_view.get("state"),
                    "domain": domain,
                    "source_kind": source_kind,
                    "operation_id": operation_id,
                    "priority": reaction.get("priority"),
                    "primary_blocking_gate_id": evaluation_ladder.get("primary_blocking_gate_id"),
                    "operator_actionability": evaluation_ladder.get("operator_actionability"),
                },
                "operation_safety": operation_safety,
                "recent_events": recent_events,
                "recent_episodes": [],
                "action": {
                    "operation_id": operation_id,
                    "parameters": evaluation["action_parameters"],
                },
            }
        )
    episodes, episodes_by_reaction = _build_episode_views(
        normalized_events,
        reaction_meta=reaction_meta,
        limit=REACTION_EPISODE_LIMIT,
    )
    for reaction in reactions:
        reaction_id = str(reaction.get("reaction_id") or "")
        reaction["recent_episodes"] = list(episodes_by_reaction.get(reaction_id) or [])[:4]
    summary = _build_reactions_summary(
        reactions,
        awaiting_barriers=awaiting_barriers,
        engine_status=engine_status,
        engine_armed=desired_armed,
        timeline=timeline,
    )
    topology = _build_reactions_topology(reactions)
    attention = _build_attention(
        reactions=reactions,
        episodes=episodes,
        awaiting_barriers=awaiting_barriers,
        summary=summary,
    )
    control_contract = _build_control_contract(
        engine_status=engine_status,
        engine_armed=desired_armed,
        reactions=reactions,
    )
    diagram = _build_reaction_diagram(
        generated_at=observed_at,
        engine_status=engine_status,
        engine_armed=desired_armed,
        active_reaction_id=state_payload.get("active_reaction_id"),
        reactions=reactions,
        episodes=episodes,
        awaiting_barriers=awaiting_barriers,
        attention=attention,
        summary=summary,
        signal_mode=signal_mode,
    )
    diagram_manifest = _build_diagram_manifest(diagram, signal_mode=signal_mode)
    graph_source_fingerprint = _reaction_graph_source_fingerprint(
        reactions=reactions,
        episodes=episodes,
        awaiting_barriers=awaiting_barriers,
        summary=summary,
        topology=topology,
        diagram=diagram,
        signal_mode=signal_mode,
    )
    graph_scene_pack = _build_reaction_graph_scene_pack(
        diagram=diagram,
        source_fingerprint=graph_source_fingerprint,
        signal_mode=signal_mode,
        generated_at=observed_at,
        elapsed_ms=round((time.perf_counter() - perf_started) * 1000, 3),
        previous_revision=previous_graph_scene_revision,
    )
    graph_scene_manifest = graph_scene_pack["manifest"]
    graph_scene_default_focus = graph_scene_pack["default_focus"]
    graph_scene_delta_manifest = graph_scene_pack["delta_manifest"]
    diagram_payload = (
        _compact_reaction_diagram(
            diagram,
            diagram_manifest=diagram_manifest,
            graph_scene_manifest=graph_scene_manifest,
        )
        if diagram_mode == "manifest"
        else diagram
    )
    projection_health = {
        "schema": "reaction_projection_health_v1",
        "generated_at": observed_at,
        "signal_mode": signal_mode,
        "cache_mode": "cached_last_signal" if signal_mode == "cached" else "live_signal_load",
        "elapsed_ms": round((time.perf_counter() - perf_started) * 1000, 3),
        "ledger_rows_scanned": timeline_meta.get("ledger_rows_scanned", 0),
        "ledger_tail_limit": timeline_meta.get("ledger_tail_limit", REACTION_LEDGER_SCAN_LIMIT),
        "topology_node_count": len(topology.get("nodes") or []),
        "topology_edge_count": len(topology.get("edges") or []),
        "diagram_node_count": diagram_manifest["counts"]["nodes"],
        "diagram_edge_count": diagram_manifest["counts"]["edges"],
        "diagram_focus_path_count": diagram_manifest["counts"]["focus_paths"],
        "diagram_payload_mode": diagram_mode,
        "graph_scene_payload_mode": graph_scene_mode,
        "graph_scene_core_version": graph_scene_core.GRAPH_SCENE_CORE_VERSION,
        "graph_scene_source_fingerprint": graph_scene_manifest.get("source_fingerprint"),
        "graph_scene_revision": graph_scene_manifest.get("revision"),
        "graph_scene_cache_key": graph_scene_pack.get("cache_key"),
        "graph_scene_cache_status": graph_scene_pack.get("cache_status"),
        "graph_scene_quality": graph_scene_manifest.get("quality"),
        "graph_scene_validation_ok": _safe_mapping(graph_scene_pack["scene"].get("validation")).get("ok"),
        "episode_count": len(episodes),
        "truncated": bool(timeline_meta.get("ledger_truncated") or topology.get("truncated") or diagram.get("truncated")),
        "degraded_fields": [
            row.get("reaction_id")
            for row in reactions
            if signal_mode == "cached"
            and not isinstance(
                _reaction_runtime_entry(state_payload, str(row.get("reaction_id") or "")).get("last_signal"),
                Mapping,
            )
        ],
        "warnings": [],
    }
    snapshot = {
        "schema": "reactions_snapshot_v1",
        "generated_at": observed_at,
        "config_path": REACTIONS_CONFIG_REL,
        "state_path": REACTIONS_STATE_REL,
        "ledger_path": REACTIONS_LEDGER_REL,
        "stop_flag_path": REACTIONS_STOP_FLAG_REL,
        "desired_armed": desired_armed,
        "engine_armed": desired_armed,
        "engine_status": engine_status,
        "pid": pid,
        "cursor_event_id": state_payload.get("cursor_event_id"),
        "last_tick_at": state_payload.get("last_tick_at"),
        "last_error": state_payload.get("last_error"),
        "awaiting_barriers": awaiting_barriers,
        "active_reaction_id": state_payload.get("active_reaction_id"),
        "last_fired_at": last_fired_at,
        "summary": summary,
        "runtime_status_rail": _runtime_status_rail(
            engine_status=engine_status,
            engine_armed=desired_armed,
            reactions=reactions,
            awaiting_barriers=awaiting_barriers,
            last_fired_at=last_fired_at,
            last_tick_at=state_payload.get("last_tick_at"),
        ),
        "event_timeline": timeline,
        "episodes": episodes,
        "topology": topology,
        "attention": attention,
        "control_contract": control_contract,
        "diagram_manifest": diagram_manifest,
        "diagram": diagram_payload,
        "graph_scene_manifest": graph_scene_manifest,
        "graph_scene_default_focus": graph_scene_default_focus,
        "graph_scene_delta_manifest": graph_scene_delta_manifest,
        "projection_health": projection_health,
        "filters": _reaction_filter_options(reactions),
        "display_contract": {
            "schema": "reaction_observatory_display_contract_v1",
            "raw_payload_policy": "raw current_signal remains available, but signal_summary/predicate/state/causal_chain/evaluation_ladder/episodes/lineage/diagram_manifest/graph_scene_manifest/default_focus are the display-ready defaults",
            "snapshot_mode": signal_mode,
            "performance_note": "cached snapshots use persisted per-reaction last_signal and a bounded ledger tail; live signal producers are not run by Station reads",
            "capabilities": [
                "evaluation_ladder",
                "reaction_episodes",
                "reaction_lineage",
                "trace_binding",
                "attention_ranking",
                "control_contract",
                "projection_health",
                "reaction_diagram",
                "receiver_effect_proxies",
                "diagram_manifest",
                "graph_scene_manifest",
                "graph_scene_default_focus",
                "graph_scene_delta_manifest",
                "graph_scene_semantic_zoom",
                "graph_scene_inspector_manifest",
            ],
        },
        "reactions": reactions,
    }
    if graph_scene_mode == "full":
        snapshot["graph_scene"] = graph_scene_pack["scene"]
    return snapshot


def resolve_reaction_graph_scene_inspector(
    snapshot: Mapping[str, Any],
    ref: str,
) -> dict[str, Any]:
    """[ACTION] Resolve one full-scene inspector ref with typed not-found semantics."""
    ref_text = str(ref or "").strip()
    scene = _safe_mapping(snapshot.get("graph_scene"))
    manifest = _safe_mapping(scene.get("manifest")) or _safe_mapping(snapshot.get("graph_scene_manifest"))
    if not ref_text:
        return {
            "schema": "graph_scene_inspector_v1",
            "status": "not_found",
            "ref": ref_text,
            "reason": "empty_ref",
            "source_revision": manifest.get("revision"),
        }
    if not scene:
        return {
            "schema": "graph_scene_inspector_v1",
            "status": "unavailable",
            "ref": ref_text,
            "reason": "full_graph_scene_not_loaded",
            "source_revision": manifest.get("revision"),
            "full_scene_resolver_ref": _safe_mapping(manifest.get("resolver_refs")).get("full_scene"),
        }
    inspectors = scene.get("inspectors") if isinstance(scene.get("inspectors"), Mapping) else {}
    payload = inspectors.get(ref_text) if isinstance(inspectors, Mapping) else None
    if not isinstance(payload, Mapping):
        return {
            "schema": "graph_scene_inspector_v1",
            "status": "not_found",
            "ref": ref_text,
            "reason": "unknown_inspector_ref",
            "source_revision": manifest.get("revision"),
        }
    return {
        "schema": "graph_scene_inspector_v1",
        "status": "ok",
        "ref": ref_text,
        "source_schema": scene.get("schema"),
        "source_revision": manifest.get("revision"),
        "source_fingerprint": manifest.get("source_fingerprint"),
        "raw_payload_policy": "bounded_full_scene_payload_only",
        "payload": copy.deepcopy(dict(payload)),
    }


def _frontend_contract_reaction(
    reaction_id: str,
    *,
    operation_id: str = "python_std_compliance_cycle",
    priority: str = "low",
) -> dict[str, Any]:
    return {
        "reaction_id": reaction_id,
        "label": reaction_id.replace("_", " ").title(),
        "priority": priority,
        "source": {"kind": "python_std_compliance_coverage"},
        "predicate": {"field": "ready", "operator": "eq", "value": True},
        "action": {
            "operation_id": operation_id,
            "parameters": {"target_row_id": "{signal.target_row_id}"},
        },
        "gate": {"dedupe_by": "signal_digest"},
        "enabled_by_default": True,
        "provenance": {"annexes": ["restate", "agent-orchestrator"]},
    }


def _frontend_contract_signal(reaction_id: str, *, ready: bool) -> dict[str, Any]:
    return {
        "kind": "python_std_compliance_coverage",
        "ready": bool(ready),
        "target_row_id": f"std_python:{reaction_id}",
        "stable_signal_digest": f"contract_fixture:{reaction_id}:{'ready' if ready else 'waiting'}",
    }


def _frontend_contract_state(
    reactions: Sequence[Mapping[str, Any]],
    *,
    desired_armed: bool = True,
    ready: bool = True,
    per_reaction: Mapping[str, Mapping[str, Any]] | None = None,
    awaiting_barriers: Sequence[Mapping[str, Any]] | None = None,
    last_tick_at: str | None = "2026-04-17T00:00:00+00:00",
) -> dict[str, Any]:
    state = default_reactions_state()
    state["desired_armed"] = bool(desired_armed)
    state["effective_armed"] = bool(desired_armed)
    state["status"] = "armed" if desired_armed else "disarmed"
    state["last_tick_at"] = last_tick_at
    state["awaiting_barriers"] = [dict(row) for row in (awaiting_barriers or []) if isinstance(row, Mapping)]
    supplied = dict(per_reaction or {})
    state["per_reaction"] = {}
    for reaction in reactions:
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        if not reaction_id:
            continue
        entry = dict(supplied.get(reaction_id) or {})
        if "last_signal" not in entry and entry.get("omit_last_signal") is not True:
            entry["last_signal"] = _frontend_contract_signal(reaction_id, ready=ready)
        entry.pop("omit_last_signal", None)
        state["per_reaction"][reaction_id] = entry
    return state


def _frontend_contract_temp_snapshot(
    *,
    reactions: Sequence[Mapping[str, Any]],
    state: Mapping[str, Any],
    ledger_rows: Sequence[Mapping[str, Any]] = (),
    diagram_mode: str = "manifest",
    graph_scene_mode: str = "manifest",
    previous_graph_scene_revision: str | None = None,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="reactions_contract_fixture_") as tmp_name:
        tmp_root = Path(tmp_name)
        if ledger_rows:
            ledger_path = reactions_ledger_path(tmp_root)
            ledger_path.parent.mkdir(parents=True, exist_ok=True)
            ledger_path.write_text(
                "\n".join(json.dumps(dict(row), sort_keys=True) for row in ledger_rows) + "\n",
                encoding="utf-8",
            )
        return build_reactions_snapshot(
            tmp_root,
            state=state,
            config={
                "kind": "reactions_config",
                "schema_version": "reactions_config_v1",
                "reactions": [dict(row) for row in reactions],
            },
            signal_mode="cached",
            diagram_mode=diagram_mode,
            graph_scene_mode=graph_scene_mode,
            previous_graph_scene_revision=previous_graph_scene_revision,
        )


def _payload_size_bytes(payload: Any) -> int:
    return len(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8"))


def _payload_size_class(size: int) -> str:
    if size <= 64_000:
        return "small"
    if size <= 512_000:
        return "medium"
    return "large"


def _first_inspector_ref(snapshot: Mapping[str, Any]) -> str | None:
    scene = _safe_mapping(snapshot.get("graph_scene"))
    manifest = _safe_mapping(scene.get("inspectors_manifest"))
    for row in manifest.get("refs") or []:
        if isinstance(row, Mapping) and row.get("ref"):
            return str(row.get("ref"))
    default_focus = _safe_mapping(snapshot.get("graph_scene_default_focus"))
    focus_manifest = _safe_mapping(default_focus.get("inspectors_manifest"))
    for row in focus_manifest.get("refs") or []:
        if isinstance(row, Mapping) and row.get("ref"):
            return str(row.get("ref"))
    return None


def _frontend_contract_projection_health_excerpt(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    health = _safe_mapping(snapshot.get("projection_health"))
    return {
        "schema": health.get("schema"),
        "elapsed_ms": health.get("elapsed_ms"),
        "signal_mode": health.get("signal_mode"),
        "diagram_payload_mode": health.get("diagram_payload_mode"),
        "graph_scene_payload_mode": health.get("graph_scene_payload_mode"),
        "graph_scene_cache_status": health.get("graph_scene_cache_status"),
        "graph_scene_validation_ok": health.get("graph_scene_validation_ok"),
        "graph_scene_quality": health.get("graph_scene_quality"),
        "diagram_node_count": health.get("diagram_node_count"),
        "diagram_edge_count": health.get("diagram_edge_count"),
        "episode_count": health.get("episode_count"),
        "degraded_fields": list(health.get("degraded_fields") or []),
        "truncated": bool(health.get("truncated")),
    }


def _frontend_contract_fixture_entry(
    name: str,
    snapshot: Mapping[str, Any],
    *,
    include_full_scene: bool = False,
    include_resolved_inspector: bool = False,
    notes: Sequence[str] = (),
) -> dict[str, Any]:
    manifest = _safe_mapping(snapshot.get("graph_scene_manifest"))
    default_focus = _safe_mapping(snapshot.get("graph_scene_default_focus"))
    delta_manifest = _safe_mapping(snapshot.get("graph_scene_delta_manifest"))
    diagram = _safe_mapping(snapshot.get("diagram"))
    inspector_ref = _first_inspector_ref(snapshot)
    entry: dict[str, Any] = {
        "schema": "reaction_frontend_contract_fixture_v1",
        "name": name,
        "snapshot_schema": snapshot.get("schema"),
        "generated_at": snapshot.get("generated_at"),
        "graph_scene_manifest": copy.deepcopy(manifest),
        "graph_scene_default_focus": copy.deepcopy(default_focus),
        "graph_scene_delta_manifest": copy.deepcopy(delta_manifest),
        "projection_health": _frontend_contract_projection_health_excerpt(snapshot),
        "diagram_omission": copy.deepcopy(diagram.get("omitted")) if isinstance(diagram.get("omitted"), Mapping) else None,
        "resolver_refs": copy.deepcopy(manifest.get("resolver_refs") or {}),
        "inspector_ref": inspector_ref,
        "inspector_manifest": copy.deepcopy(
            _safe_mapping(_safe_mapping(snapshot.get("graph_scene")).get("inspectors_manifest"))
            or _safe_mapping(default_focus.get("inspectors_manifest"))
        ),
        "has_full_scene": "graph_scene" in snapshot,
        "raw_inspector_payload_policy": "full_scene_or_resolver_only",
        "notes": list(notes),
    }
    if include_full_scene and isinstance(snapshot.get("graph_scene"), Mapping):
        entry["graph_scene"] = copy.deepcopy(snapshot["graph_scene"])
    if include_resolved_inspector and inspector_ref:
        entry["resolved_inspector"] = resolve_reaction_graph_scene_inspector(snapshot, inspector_ref)
    return entry


def _build_frontend_contract_payload_receipt(
    *,
    compact_snapshot: Mapping[str, Any],
    full_snapshot: Mapping[str, Any],
    cold_ms: float | None,
    warm_manifest_ms: float | None,
    warm_full_scene_ms: float | None,
    cache_statuses: Sequence[str],
) -> dict[str, Any]:
    compact_payload_bytes = _payload_size_bytes(compact_snapshot)
    full_scene_payload_bytes = _payload_size_bytes(full_snapshot.get("graph_scene") or {})
    default_focus = _safe_mapping(compact_snapshot.get("graph_scene_default_focus"))
    full_scene = _safe_mapping(full_snapshot.get("graph_scene"))
    inspectors_manifest = _safe_mapping(full_scene.get("inspectors_manifest"))
    hit_count = sum(1 for status in cache_statuses if status == "hit")
    return {
        "schema": "reaction_graph_scene_payload_budget_receipt_v1",
        "compact_payload_bytes": compact_payload_bytes,
        "compact_payload_size_class": _payload_size_class(compact_payload_bytes),
        "default_focus_node_count": len(default_focus.get("nodes") or []),
        "default_focus_edge_count": len(default_focus.get("edges") or []),
        "full_scene_payload_bytes": full_scene_payload_bytes,
        "full_scene_payload_size_class": _payload_size_class(full_scene_payload_bytes),
        "full_scene_node_count": len(full_scene.get("nodes") or []),
        "full_scene_edge_count": len(full_scene.get("edges") or []),
        "inspector_manifest_count": int(inspectors_manifest.get("count") or 0),
        "full_inspector_payload_policy": "lazy_drilldown_full_scene_or_resolver_only",
        "cold_build_ms": None if cold_ms is None else round(cold_ms, 3),
        "warm_manifest_ms": None if warm_manifest_ms is None else round(warm_manifest_ms, 3),
        "warm_full_scene_ms": None if warm_full_scene_ms is None else round(warm_full_scene_ms, 3),
        "cache_hit_rate_sample": {
            "sample_size": len(cache_statuses),
            "hit_count": hit_count,
            "hit_ratio": round(hit_count / max(1, len(cache_statuses)), 3),
            "statuses": list(cache_statuses),
        },
        "budget_policy": {
            "compact_default": "safe_for_polling_manifest_default_focus_only",
            "full_scene": "explicit_drilldown_only",
            "inspectors": "manifest_refs_on_poll_payload_payloads_only_in_full_or_resolver_mode",
            "timings": "receipt_fields_are_observability_not_brittle_thresholds",
        },
    }


def build_reactions_frontend_contract_fixture_pack(
    repo_root: Path,
    *,
    generated_at: str | None = None,
    measure_performance: bool = True,
) -> dict[str, Any]:
    """[ACTION] Generate frontend contract fixtures without reading live reaction signals."""
    del repo_root  # The pack is synthetic and must not mutate or depend on the live checkout.
    generated = generated_at or _utc_now()
    ready = _frontend_contract_reaction("contract_ready")
    waiting = _frontend_contract_reaction("contract_waiting")
    blocked = _frontend_contract_reaction("contract_blocked", priority="high")
    failed = _frontend_contract_reaction("contract_failed", priority="high")
    completed = _frontend_contract_reaction("contract_completed")
    stale = _frontend_contract_reaction("contract_stale")

    quiet_snapshot = _frontend_contract_temp_snapshot(
        reactions=[waiting],
        state=_frontend_contract_state([waiting], ready=False),
    )
    eligible_snapshot = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=_frontend_contract_state([ready], ready=True),
    )
    barrier_snapshot = _frontend_contract_temp_snapshot(
        reactions=[blocked],
        state=_frontend_contract_state(
            [blocked],
            ready=True,
            awaiting_barriers=[
                {
                    "reaction_id": "contract_blocked",
                    "reaction_run_id": "rxrun_contract_blocked",
                    "kind": "operation_completion",
                    "status": "pending",
                    "operation_id": "python_std_compliance_cycle",
                    "started_at": "2026-04-17T00:00:00+00:00",
                }
            ],
        ),
    )
    failure_snapshot = _frontend_contract_temp_snapshot(
        reactions=[failed],
        state=_frontend_contract_state(
            [failed],
            ready=False,
            per_reaction={
                "contract_failed": {
                    "last_result": "failed",
                    "last_error": "operation returned non-zero",
                    "last_failed_at": "2026-04-17T00:00:03+00:00",
                    "last_signal": _frontend_contract_signal("contract_failed", ready=False),
                }
            },
        ),
    )
    completed_rows = [
        {
            "kind": "reaction_fired",
            "schema_version": "reaction_fired_v1",
            "event_id": "rxn_contract_completed_1",
            "recorded_at": "2026-04-17T00:00:00+00:00",
            "reaction_id": "contract_completed",
            "reaction_run_id": "rxrun_contract_completed",
            "operation_id": "python_std_compliance_cycle",
            "signal_digest": "contract_completed_digest",
        },
        {
            "kind": "reaction_completed",
            "schema_version": "reaction_completed_v1",
            "event_id": "rxn_contract_completed_2",
            "recorded_at": "2026-04-17T00:00:02+00:00",
            "reaction_id": "contract_completed",
            "reaction_run_id": "rxrun_contract_completed",
            "operation_id": "python_std_compliance_cycle",
            "signal_digest": "contract_completed_digest",
            "duration_ms": 22,
            "returncode": 0,
        },
    ]
    completed_snapshot = _frontend_contract_temp_snapshot(
        reactions=[completed],
        state=_frontend_contract_state(
            [completed],
            ready=False,
            per_reaction={
                "contract_completed": {
                    "last_result": "completed",
                    "last_completed_at": "2026-04-17T00:00:02+00:00",
                    "last_signal": _frontend_contract_signal("contract_completed", ready=False),
                }
            },
        ),
        ledger_rows=completed_rows,
    )
    stale_snapshot = _frontend_contract_temp_snapshot(
        reactions=[stale],
        state=_frontend_contract_state(
            [stale],
            ready=False,
            per_reaction={"contract_stale": {"omit_last_signal": True}},
            last_tick_at="2026-04-01T00:00:00+00:00",
        ),
    )
    compact_snapshot = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=_frontend_contract_state([ready], ready=True),
        diagram_mode="manifest",
        graph_scene_mode="manifest",
    )
    full_snapshot = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=_frontend_contract_state([ready], ready=True),
        diagram_mode="full",
        graph_scene_mode="full",
    )
    first_delta = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=_frontend_contract_state([ready], ready=True),
    )
    changed_state = _frontend_contract_state([ready], ready=True)
    changed_state["per_reaction"]["contract_ready"]["last_signal"]["target_row_id"] = "std_python:contract_ready_changed"
    changed_state["per_reaction"]["contract_ready"]["last_signal"]["stable_signal_digest"] = (
        "contract_fixture:contract_ready:changed"
    )
    delta_changed = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=changed_state,
        previous_graph_scene_revision=first_delta["graph_scene_manifest"]["revision"],
    )
    delta_unchanged = _frontend_contract_temp_snapshot(
        reactions=[ready],
        state=_frontend_contract_state([ready], ready=True),
        previous_graph_scene_revision=first_delta["graph_scene_manifest"]["revision"],
    )
    degraded_snapshot = _frontend_contract_temp_snapshot(
        reactions=[stale],
        state=_frontend_contract_state([stale], per_reaction={"contract_stale": {"omit_last_signal": True}}),
    )
    large_reactions = [
        _frontend_contract_reaction(f"contract_bundle_{index:02d}")
        for index in range(36)
    ]
    large_snapshot = _frontend_contract_temp_snapshot(
        reactions=large_reactions,
        state=_frontend_contract_state(large_reactions, ready=True),
        diagram_mode="manifest",
        graph_scene_mode="manifest",
    )

    cold_ms: float | None = None
    warm_manifest_ms: float | None = None
    warm_full_scene_ms: float | None = None
    cache_statuses: list[str] = []
    if measure_performance:
        with _REACTION_GRAPH_SCENE_CACHE_LOCK:
            _REACTION_GRAPH_SCENE_CACHE.clear()
        started = time.perf_counter()
        cold_snapshot = _frontend_contract_temp_snapshot(
            reactions=[ready],
            state=_frontend_contract_state([ready], ready=True),
            diagram_mode="manifest",
            graph_scene_mode="manifest",
        )
        cold_ms = (time.perf_counter() - started) * 1000
        cache_statuses.append(str(_safe_mapping(cold_snapshot.get("projection_health")).get("graph_scene_cache_status")))
        started = time.perf_counter()
        warm_manifest_snapshot = _frontend_contract_temp_snapshot(
            reactions=[ready],
            state=_frontend_contract_state([ready], ready=True),
            diagram_mode="manifest",
            graph_scene_mode="manifest",
        )
        warm_manifest_ms = (time.perf_counter() - started) * 1000
        cache_statuses.append(str(_safe_mapping(warm_manifest_snapshot.get("projection_health")).get("graph_scene_cache_status")))
        started = time.perf_counter()
        warm_full_snapshot = _frontend_contract_temp_snapshot(
            reactions=[ready],
            state=_frontend_contract_state([ready], ready=True),
            diagram_mode="full",
            graph_scene_mode="full",
        )
        warm_full_scene_ms = (time.perf_counter() - started) * 1000
        cache_statuses.append(str(_safe_mapping(warm_full_snapshot.get("projection_health")).get("graph_scene_cache_status")))

    fixtures = [
        _frontend_contract_fixture_entry("quiet_system_map", quiet_snapshot),
        _frontend_contract_fixture_entry("eligible_now", eligible_snapshot),
        _frontend_contract_fixture_entry("blocked_barrier", barrier_snapshot),
        _frontend_contract_fixture_entry("failure_triage", failure_snapshot),
        _frontend_contract_fixture_entry("recent_completed", completed_snapshot),
        _frontend_contract_fixture_entry("stale_signal", stale_snapshot),
        _frontend_contract_fixture_entry("compact_manifest_only", compact_snapshot, notes=["Default world-model polling shape."]),
        _frontend_contract_fixture_entry("full_scene", full_snapshot, include_full_scene=True),
        _frontend_contract_fixture_entry(
            "inspector_ref_resolution",
            full_snapshot,
            include_full_scene=True,
            include_resolved_inspector=True,
        ),
        _frontend_contract_fixture_entry("delta_changed", delta_changed),
        _frontend_contract_fixture_entry("delta_unchanged", delta_unchanged),
        _frontend_contract_fixture_entry("degraded_fallback", degraded_snapshot),
        _frontend_contract_fixture_entry("large_graph_bundle_pressure", large_snapshot),
    ]
    return {
        "schema": "reactions_frontend_contract_fixture_pack_v1",
        "generated_at": generated,
        "source_snapshot_schema": "reactions_snapshot_v1",
        "consumer_contract_schema": "reaction_graph_scene_consumer_contract_v1",
        "fixture_count": len(fixtures),
        "fixture_names": [fixture["name"] for fixture in fixtures],
        "resolver_boundary": {
            "schema": "reaction_graph_scene_resolver_boundary_v1",
            "default_http_route": "GET /api/world-model/reactions",
            "default_route_contract": "compact manifest/default-focus/delta only",
            "full_scene_contract": "available from build_reactions_snapshot(..., graph_scene_mode=\"full\") and fixture pack; add HTTP route only when a frontend pass proves the need",
            "inspector_contract": "manifest refs on polling payload, bounded payloads via full scene or future inspector resolver",
            "delta_contract": "graph_scene_delta_manifest reports changed_since_previous; full deltas remain a backend helper/core affordance",
        },
        "stable_schema_names": [
            "graph_scene_manifest_v1",
            "graph_scene_focus_excerpt_v1",
            "graph_scene_delta_manifest_v1",
            "graph_scene_v1",
            "graph_scene_inspector_manifest_v1",
            "reaction_diagram_v1",
            "reaction_diagram_manifest_v1",
        ],
        "payload_receipt": _build_frontend_contract_payload_receipt(
            compact_snapshot=compact_snapshot,
            full_snapshot=full_snapshot,
            cold_ms=cold_ms,
            warm_manifest_ms=warm_manifest_ms,
            warm_full_scene_ms=warm_full_scene_ms,
            cache_statuses=cache_statuses,
        ),
        "fixtures": fixtures,
    }


def build_reactions_orchestration_projection(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Project the cached reactions snapshot into orchestration status fields."""
    snapshot = build_reactions_snapshot(repo_root, signal_mode="cached")
    return {
        "engine_armed": snapshot.get("engine_armed"),
        "engine_status": snapshot.get("engine_status"),
        "pid": snapshot.get("pid"),
        "cursor_event_id": snapshot.get("cursor_event_id"),
        "last_tick_at": snapshot.get("last_tick_at"),
        "last_error": snapshot.get("last_error"),
        "awaiting_barriers": snapshot.get("awaiting_barriers") or [],
        "active_reaction_id": snapshot.get("active_reaction_id"),
        "last_fired_at": snapshot.get("last_fired_at"),
    }


def build_wake_barriers_snapshot(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Project cached active wake barriers for runtime handoff surfaces."""
    snapshot = build_reactions_snapshot(repo_root, signal_mode="cached")
    return {
        "schema": "wake_barriers_v1",
        "generated_at": snapshot.get("generated_at"),
        "engine_armed": snapshot.get("engine_armed"),
        "engine_status": snapshot.get("engine_status"),
        "items": snapshot.get("awaiting_barriers") or [],
    }


def _persist_state_change(
    repo_root: Path,
    state: dict[str, Any],
    *,
    summary: str,
    reaction_id: str | None = None,
) -> dict[str, Any]:
    saved = save_reactions_state(repo_root, state)
    _append_ledger_row(
        repo_root,
        "reaction_state_changed",
        {"summary": summary, "reaction_id": reaction_id},
    )
    return saved


def set_engine_armed_state(repo_root: Path, armed: bool) -> dict[str, Any]:
    """[ACTION] Persist the desired engine armed state and manage the stop flag."""
    state = ensure_reactions_state(repo_root)
    state["desired_armed"] = bool(armed)
    state["effective_armed"] = bool(armed and _pid_running(state.get("pid")))
    state["status"] = "armed" if armed else "disarmed"
    state["last_error"] = None if armed else state.get("last_error")
    stop_flag = reactions_stop_flag_path(repo_root)
    if armed:
        if stop_flag.exists():
            stop_flag.unlink()
    else:
        stop_flag.parent.mkdir(parents=True, exist_ok=True)
        stop_flag.write_text(_utc_now() + "\n", encoding="utf-8")
    return _persist_state_change(
        repo_root,
        state,
        summary="Engine armed." if armed else "Engine disarmed.",
    )


def ensure_engine_running(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Spawn the detached run loop if no live pid is recorded.

    Idempotent: returns without side effects when a live pid is already
    present. Used by the CLI `arm` command and the FastAPI arm route so
    "arming" is one button regardless of surface — before this helper
    existed, CLI arm only flipped desired_armed and left the loop stopped,
    so the operator had to remember to run `run` separately or trigger the
    Station route.
    """
    state = load_reactions_state(repo_root)
    pid = state.get("pid") if isinstance(state, Mapping) else None
    if _pid_running(pid):
        return {"spawned": False, "pid": int(pid), "reason": "already_running"}
    log_dir = repo_root / "state" / "launcher_ops"
    log_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ").lower()
    log_path = log_dir / f"{stamp}_reactions_engine.log"
    handle = log_path.open("w", encoding="utf-8")
    import subprocess

    process = subprocess.Popen(
        [
            str(repo_root / "repo-python"),
            "tools/meta/control/reactions_engine.py",
            "run",
        ],
        cwd=str(repo_root),
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    handle.close()
    return {
        "spawned": True,
        "pid": int(process.pid),
        "log_path": _relative(repo_root, log_path),
    }


def set_reaction_override_state(repo_root: Path, reaction_id: str, armed: bool) -> dict[str, Any]:
    """[ACTION] Persist a per-reaction override flag in runtime state."""
    state = ensure_reactions_state(repo_root)
    entry = _reaction_runtime_entry(state, reaction_id)
    entry["override_armed"] = bool(armed)
    entry["updated_at"] = _utc_now()
    _set_reaction_runtime_entry(state, reaction_id, entry)
    return _persist_state_change(
        repo_root,
        state,
        summary=f"Reaction override set to {'armed' if armed else 'disarmed'}.",
        reaction_id=reaction_id,
    )


def _spawn_action_runner(
    repo_root: Path,
    *,
    reaction_id: str,
    reaction_run_id: str,
    operation_id: str,
    parameters: Mapping[str, Any],
    signal_digest: str,
    signal: Mapping[str, Any],
    started_at: str,
) -> tuple[int, str]:
    log_dir = repo_root / "state" / "launcher_ops"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_name = f"{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()}_{reaction_id}.log"
    log_path = log_dir / log_name
    handle = log_path.open("w", encoding="utf-8")
    argv = [
        str(repo_root / "repo-python"),
        "tools/meta/control/reactions_engine.py",
        "run-action",
        "--reaction-id",
        reaction_id,
        "--reaction-run-id",
        reaction_run_id,
        "--operation-id",
        operation_id,
        "--parameters-json",
        json.dumps(dict(parameters), ensure_ascii=False),
        "--signal-digest",
        signal_digest,
        "--signal-json",
        json.dumps(dict(signal), ensure_ascii=False),
        "--started-at",
        started_at,
    ]
    import subprocess

    process = subprocess.Popen(
        argv,
        cwd=str(repo_root),
        stdout=handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    handle.close()
    return int(process.pid), _relative(repo_root, log_path)


def tick_engine(repo_root: Path) -> dict[str, Any]:
    """[ACTION] Evaluate one scheduler cycle, firing at most one eligible reaction."""
    now = _now_dt()
    config = load_reactions_config(repo_root)
    state = ensure_reactions_state(repo_root)
    latest_event = _load_latest_orchestration_event(repo_root) or {}
    state["cursor_event_id"] = latest_event.get("event_id")
    state["cursor_recorded_at"] = latest_event.get("recorded_at")
    state["last_tick_at"] = now.isoformat()
    state["pid"] = os.getpid()
    state["effective_armed"] = bool(state.get("desired_armed"))

    if _maybe_clear_expired_barrier(repo_root, state, now):
        save_reactions_state(repo_root, state)

    barriers = state.get("awaiting_barriers") if isinstance(state.get("awaiting_barriers"), list) else []
    active_barrier = barriers[0] if barriers and isinstance(barriers[0], Mapping) else None
    if active_barrier and _barrier_is_active(active_barrier, now):
        runner_pid = active_barrier.get("runner_pid")
        if str(active_barrier.get("kind") or "").strip() == "operation_completion" and runner_pid and not _pid_running(runner_pid):
            _mark_unexpected_runner_exit(repo_root, state, active_barrier)
            save_reactions_state(repo_root, state)
            return build_reactions_snapshot(repo_root, state=state, config=config)
        # Hard max-age guard: even if the runner process is still alive,
        # force-clear the barrier after 45 minutes. A single distill cohort
        # (wave_width 6, 12 paragraphs) should complete in ~5-10 min.
        # 45 min means the runner is truly stuck (bridge tab hung waiting
        # on a response the UI has already finished, typically). Better to
        # kill the hang and refire than to sit on the barrier indefinitely.
        started_at_raw = str(active_barrier.get("started_at") or "").strip()
        if started_at_raw and str(active_barrier.get("kind") or "").strip() == "operation_completion":
            try:
                started_dt = datetime.fromisoformat(started_at_raw.replace("Z", "+00:00"))
                if started_dt.tzinfo is None:
                    started_dt = started_dt.replace(tzinfo=timezone.utc)
                age_s = (now - started_dt).total_seconds()
            except Exception:
                age_s = 0.0
            if age_s > 2700:
                if runner_pid and _pid_running(runner_pid):
                    try:
                        os.kill(int(runner_pid), 9)
                    except (ProcessLookupError, PermissionError, ValueError):
                        pass
                _mark_unexpected_runner_exit(repo_root, state, active_barrier)
                state["last_error"] = f"barrier force-cleared after {int(age_s)}s (max 2700s)"
                save_reactions_state(repo_root, state)
                _append_ledger_row(
                    repo_root,
                    "reaction_state_changed",
                    {"summary": f"Force-cleared stuck barrier after {int(age_s)}s.", "reaction_id": active_barrier.get("reaction_id")},
                )
                return build_reactions_snapshot(repo_root, state=state, config=config)
        state["status"] = "cooldown" if str(active_barrier.get("kind")) == "cooldown" else "awaiting_barrier"
        save_reactions_state(repo_root, state)
        return build_reactions_snapshot(repo_root, state=state, config=config)

    if not bool(state.get("desired_armed")):
        state["effective_armed"] = False
        state["status"] = "disarmed"
        save_reactions_state(repo_root, state)
        return build_reactions_snapshot(repo_root, state=state, config=config)

    candidate_payloads = []
    for reaction in sorted(config.get("reactions") or [], key=_reaction_sort_key):
        if not isinstance(reaction, Mapping):
            continue
        candidate_payloads.append(
            (reaction, _evaluate_reaction_candidate(repo_root, state, reaction, now))
        )
    winner = next((item for item in candidate_payloads if item[1]["can_fire"]), None)
    if winner is None:
        for reaction, evaluation in candidate_payloads:
            if not evaluation["matched"]:
                continue
            if evaluation["can_fire"]:
                continue
            _maybe_record_suppression(
                repo_root,
                state,
                reaction_id=str(reaction.get("reaction_id") or "").strip(),
                signal=evaluation["signal"],
                signal_digest=evaluation["signal_digest"],
                reason=str(evaluation["preview_reason"] or "").strip(),
            )
        state["status"] = "armed"
        save_reactions_state(repo_root, state)
        return build_reactions_snapshot(repo_root, state=state, config=config)

    reaction, evaluation = winner
    reaction_id = str(reaction.get("reaction_id") or "").strip()
    action = _safe_mapping(reaction.get("action"))
    operation_id = str(action.get("operation_id") or "").strip()
    parameters = evaluation["action_parameters"]
    prepared = prepare_launch_operation(repo_root, operation_id=operation_id, parameters=parameters)
    started_at = now.isoformat()
    reaction_run_id = _new_reaction_run_id(
        reaction_id=reaction_id,
        operation_id=operation_id,
        signal_digest=str(evaluation["signal_digest"]),
        started_at=started_at,
    )
    barrier = {
        "reaction_id": reaction_id,
        "reaction_run_id": reaction_run_id,
        "kind": str(_safe_mapping(reaction.get("gate")).get("barrier_kind") or "operation_completion"),
        "label": f"awaiting operation: {operation_id}",
        "status": "pending",
        "operation_id": operation_id,
        "wake_at": None,
        "started_at": started_at,
        "runner_pid": None,
        "log_path": None,
    }
    state["active_reaction_id"] = reaction_id
    state["awaiting_barriers"] = [barrier]
    state["status"] = "awaiting_barrier"
    state["last_fired_at"] = started_at
    runtime_entry = _reaction_runtime_entry(state, reaction_id)
    runtime_entry.update(
        {
            "last_fired_at": started_at,
            "last_reaction_run_id": reaction_run_id,
            "last_fired_signal_digest": evaluation["signal_digest"],
            "last_fired_ledger_fingerprint": evaluation.get("ledger_fingerprint") or "",
            "last_result": "fired",
            "last_operation_id": operation_id,
            "last_signal": evaluation["signal"],
            "last_error": None,
        }
    )
    _set_reaction_runtime_entry(state, reaction_id, runtime_entry)
    save_reactions_state(repo_root, state)

    runner_pid, log_path = _spawn_action_runner(
        repo_root,
        reaction_id=reaction_id,
        reaction_run_id=reaction_run_id,
        operation_id=operation_id,
        parameters=parameters,
        signal_digest=evaluation["signal_digest"],
        signal=evaluation["signal"],
        started_at=started_at,
    )
    state = load_reactions_state(repo_root)
    barriers = state.get("awaiting_barriers") if isinstance(state.get("awaiting_barriers"), list) else []
    if barriers and isinstance(barriers[0], dict):
        barriers[0]["runner_pid"] = runner_pid
        barriers[0]["log_path"] = log_path
    state["pid"] = os.getpid()
    save_reactions_state(repo_root, state)

    _append_ledger_row(
        repo_root,
        "reaction_fired",
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "fired_at": started_at,
            "signal_digest": evaluation["signal_digest"],
            "ledger_fingerprint": evaluation.get("ledger_fingerprint") or "",
            "signal": evaluation["signal"],
            "command": prepared.command,
            "parameters": parameters,
            "runner_pid": runner_pid,
            "log_path": log_path,
        },
    )
    _append_orchestration_event(
        repo_root,
        "reaction_fired_v1",
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "summary": f"Reaction {reaction_id} fired {operation_id}.",
            "signal_digest": evaluation["signal_digest"],
        },
    )
    return build_reactions_snapshot(repo_root, state=state, config=config)


def _finalize_action_state(
    repo_root: Path,
    *,
    reaction_id: str,
    reaction_run_id: str | None = None,
    operation_id: str,
    started_at: str,
    signal_digest: str,
    outcome: str,
    stdout: str,
    stderr: str,
    returncode: int,
    duration_ms: int,
    ledger_fingerprint: str = "",
) -> None:
    now_iso = _utc_now()
    config = load_reactions_config(repo_root)
    reaction = next(
        (
            item
            for item in config.get("reactions") or []
            if isinstance(item, Mapping) and str(item.get("reaction_id") or "").strip() == reaction_id
        ),
        {},
    )
    gate = _safe_mapping(_safe_mapping(reaction).get("gate"))
    cooldown_minutes = int(gate.get("cooldown_minutes") or 0)
    cooldown_until = None
    if cooldown_minutes > 0:
        cooldown_until = (datetime.now(timezone.utc) + timedelta(minutes=cooldown_minutes)).isoformat()

    state = ensure_reactions_state(repo_root)
    entry = _reaction_runtime_entry(state, reaction_id)
    if not reaction_run_id:
        reaction_run_id = str(entry.get("last_reaction_run_id") or "").strip() or None
    if not reaction_run_id:
        barriers = state.get("awaiting_barriers") if isinstance(state.get("awaiting_barriers"), list) else []
        active = barriers[0] if barriers and isinstance(barriers[0], Mapping) else {}
        reaction_run_id = str(active.get("reaction_run_id") or "").strip() or None
    if not reaction_run_id:
        reaction_run_id = _new_reaction_run_id(
            reaction_id=reaction_id,
            operation_id=operation_id,
            signal_digest=signal_digest,
            started_at=started_at,
        )
    prior_fingerprint = str(entry.get("last_fired_ledger_fingerprint") or "").strip()
    resolved_fingerprint = str(ledger_fingerprint or prior_fingerprint or "").strip()
    entry.update(
        {
            "last_result": outcome,
            "last_operation_id": operation_id,
            "last_reaction_run_id": reaction_run_id,
            "last_fired_signal_digest": signal_digest,
            "last_error": stderr[:512] if outcome == "failed" and stderr else None,
        }
    )
    if resolved_fingerprint:
        entry["last_fired_ledger_fingerprint"] = resolved_fingerprint
    if outcome == "completed":
        entry["last_completed_at"] = now_iso
    else:
        entry["last_failed_at"] = now_iso
    entry["cooldown_until"] = cooldown_until
    _set_reaction_runtime_entry(state, reaction_id, entry)

    # Schema v2: record the (digest, fingerprint) pair with its terminal outcome
    # so the next evaluation of the same reaction on the same material can
    # suppress re-fire without relying solely on last_fired_signal_digest.
    _record_completed_digest(
        state,
        signal_digest=signal_digest,
        ledger_fingerprint=resolved_fingerprint,
        outcome=outcome,
        operation_id=operation_id,
        completed_at=now_iso,
        reaction_id=reaction_id,
    )

    state["awaiting_barriers"] = []
    state["active_reaction_id"] = None
    state["status"] = "armed" if bool(state.get("desired_armed")) else "disarmed"
    state["last_error"] = stderr[:512] if outcome == "failed" and stderr else None
    save_reactions_state(repo_root, state)

    ledger_kind = "reaction_completed" if outcome == "completed" else "reaction_failed"
    orchestration_kind = "reaction_completed_v1" if outcome == "completed" else "reaction_failed_v1"
    _append_ledger_row(
        repo_root,
        ledger_kind,
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "completed_at": now_iso if outcome == "completed" else None,
            "failed_at": now_iso if outcome == "failed" else None,
            "duration_ms": duration_ms,
            "returncode": returncode,
            "signal_digest": signal_digest,
            "ledger_fingerprint": resolved_fingerprint,
            "stdout": stdout[:1024],
            "stderr": stderr[:1024],
        },
    )
    summary = (
        f"Reaction {reaction_id} completed {operation_id}."
        if outcome == "completed"
        else f"Reaction {reaction_id} failed {operation_id}."
    )
    _append_orchestration_event(
        repo_root,
        orchestration_kind,
        {
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "operation_id": operation_id,
            "summary": summary,
            "returncode": returncode,
            "duration_ms": duration_ms,
            "signal_digest": signal_digest,
        },
    )


def run_action(
    repo_root: Path,
    *,
    reaction_id: str,
    reaction_run_id: str,
    operation_id: str,
    parameters_json: str,
    signal_digest: str,
    signal_json: str,
    started_at: str,
) -> int:
    """[ACTION] Execute one launched reaction action and bind its terminal receipt."""
    parameters = json.loads(parameters_json or "{}")
    signal = json.loads(signal_json or "{}")
    if not isinstance(parameters, dict):
        parameters = {}
    if not isinstance(signal, dict):
        signal = {}
    # Compute fingerprint at run time so the completion record has both the
    # signal digest (source address) and the material fingerprint (which is
    # stable across coverage timestamp bumps).
    config = load_reactions_config(repo_root)
    reaction_payload = next(
        (
            item
            for item in config.get("reactions") or []
            if isinstance(item, Mapping) and str(item.get("reaction_id") or "").strip() == reaction_id
        ),
        {},
    )
    ledger_fingerprint = _compute_ledger_fingerprint(reaction_payload, signal)
    prepared = prepare_launch_operation(repo_root, operation_id=operation_id, parameters=parameters)
    mm_run_id = start_meta_mission_run(
        repo_root,
        prepared=prepared,
        operation_id=operation_id,
        parameters=parameters,
        trigger="reaction",
    )
    env = launcher_meta_mission_env(
        meta_mission_id=str(prepared.operation.get("meta_mission_id") or "").strip(),
        meta_mission_run_id=mm_run_id,
        execution_mode="sync",
    )
    started_dt = _now_dt()
    import subprocess

    try:
        proc = subprocess.run(
            shlex.split(prepared.command),
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            env=env,
            check=False,
        )
        duration_ms = int((_now_dt() - started_dt).total_seconds() * 1000)
        artifact_refs = artifact_refs_from_operation_output(proc.stdout or "")
        output_fields = operation_event_fields_from_operation_output(proc.stdout or "")
        route_evidence_results: list[dict[str, Any]] = []
        if int(proc.returncode) == 0 and isinstance(output_fields.get("route_evidence"), list):
            try:
                from system.lib.semantic_routing import append_operation_route_evidence

                route_evidence_results = append_operation_route_evidence(
                    repo_root,
                    evidence_rows=output_fields["route_evidence"],
                    actor_id=ENGINE_ACTOR_ID,
                    operation_id=operation_id,
                )
            except Exception:
                route_evidence_results = []
        operation_event = {
            "kind": "operation_launched",
            "schema_version": "operation_launched_v1",
            "recorded_at": _utc_now(),
            "event_id": _event_id("op", started_dt),
            "operation_id": operation_id,
            "reaction_id": reaction_id,
            "reaction_run_id": reaction_run_id,
            "actor_id": ENGINE_ACTOR_ID,
            "command": prepared.command,
            "returncode": int(proc.returncode),
            "duration_ms": duration_ms,
            "truncated_stdout": (proc.stdout or "")[:4096],
            "resolved_parameters": parameters,
            "meta_mission_id": str(prepared.operation.get("meta_mission_id") or "").strip() or None,
            "meta_mission_run_id": mm_run_id,
            **output_fields,
        }
        if route_evidence_results:
            operation_event["route_evidence_results"] = route_evidence_results
        _append_jsonl(orchestration_events_path(repo_root), operation_event)
        outcome = "completed" if int(proc.returncode) == 0 else "failed"
        _finalize_action_state(
            repo_root,
            reaction_id=reaction_id,
            reaction_run_id=reaction_run_id,
            operation_id=operation_id,
            started_at=started_at,
            signal_digest=signal_digest,
            outcome=outcome,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            returncode=int(proc.returncode),
            duration_ms=duration_ms,
            ledger_fingerprint=ledger_fingerprint,
        )
        finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="succeeded" if outcome == "completed" else "failed",
            error=(proc.stderr or "")[:1024] if outcome == "failed" else None,
            artifact_refs=artifact_refs,
            extra={
                "returncode": int(proc.returncode),
                "duration_ms": duration_ms,
                "command": prepared.command,
                "reaction_id": reaction_id,
                "reaction_run_id": reaction_run_id,
                **output_fields,
                "route_evidence_results": route_evidence_results,
            },
        )
        if proc.stdout:
            sys.stdout.write(proc.stdout)
        if proc.stderr:
            sys.stderr.write(proc.stderr)
        return int(proc.returncode)
    except Exception as exc:  # pragma: no cover - defensive
        duration_ms = int((_now_dt() - started_dt).total_seconds() * 1000)
        _finalize_action_state(
            repo_root,
            reaction_id=reaction_id,
            reaction_run_id=reaction_run_id,
            operation_id=operation_id,
            started_at=started_at,
            signal_digest=signal_digest,
            outcome="failed",
            stdout="",
            stderr=f"{type(exc).__name__}: {exc}",
            returncode=-1,
            duration_ms=duration_ms,
            ledger_fingerprint=ledger_fingerprint,
        )
        finalize_meta_mission_run(
            repo_root,
            prepared=prepared,
            run_id=mm_run_id,
            status="failed",
            error=f"{type(exc).__name__}: {exc}",
            extra={
                "duration_ms": duration_ms,
                "command": prepared.command,
                "reaction_id": reaction_id,
                "reaction_run_id": reaction_run_id,
            },
        )
        raise


def run_engine(repo_root: Path) -> int:
    """[ACTION] Run the polling reactions engine until a stop flag can be honored."""
    state = ensure_reactions_state(repo_root)
    state["pid"] = os.getpid()
    state["effective_armed"] = bool(state.get("desired_armed"))
    state["status"] = "armed" if bool(state.get("desired_armed")) else "disarmed"
    save_reactions_state(repo_root, state)
    _append_ledger_row(repo_root, "reaction_engine_started", {"pid": os.getpid()})
    try:
        while True:
            tick_engine(repo_root)
            state = load_reactions_state(repo_root)
            if reactions_stop_flag_path(repo_root).exists() and not (state.get("awaiting_barriers") or []):
                state["effective_armed"] = False
                state["status"] = "disarmed"
                state["pid"] = None
                save_reactions_state(repo_root, state)
                break
            time.sleep(DEFAULT_POLL_SECONDS)
    finally:
        reactions_stop_flag_path(repo_root).unlink(missing_ok=True)
        _append_ledger_row(repo_root, "reaction_engine_stopped", {"pid": os.getpid()})
    return 0


def _build_parser() -> argparse.ArgumentParser:
    import argparse

    parser = argparse.ArgumentParser(description="Phase 09.35 reactions engine")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("run")
    subparsers.add_parser("tick")
    status_parser = subparsers.add_parser("status")
    status_parser.add_argument("--signal-mode", choices=("cached", "live"), default="cached")
    contract_fixture_parser = subparsers.add_parser("contract-fixtures")
    contract_fixture_parser.add_argument(
        "--no-measure-performance",
        action="store_true",
        help="Skip cold/warm timing sample while still emitting payload-size receipt fields.",
    )
    subparsers.add_parser("arm")
    subparsers.add_parser("disarm")

    run_action_parser = subparsers.add_parser("run-action")
    run_action_parser.add_argument("--reaction-id", required=True)
    run_action_parser.add_argument("--reaction-run-id", required=True)
    run_action_parser.add_argument("--operation-id", required=True)
    run_action_parser.add_argument("--parameters-json", required=True)
    run_action_parser.add_argument("--signal-digest", required=True)
    run_action_parser.add_argument("--signal-json", required=True)
    run_action_parser.add_argument("--started-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """[ACTION] Parse the reactions-engine CLI and dispatch the selected command."""
    args = _build_parser().parse_args(argv)
    if args.command == "run":
        from tools.meta.control import metabolismd

        return metabolismd.main(["run"])
    if args.command == "tick":
        print(json.dumps(tick_engine(REPO_ROOT), indent=2, ensure_ascii=False))
        return 0
    if args.command == "status":
        print(
            json.dumps(
                build_reactions_snapshot(REPO_ROOT, signal_mode=args.signal_mode),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "contract-fixtures":
        print(
            json.dumps(
                build_reactions_frontend_contract_fixture_pack(
                    REPO_ROOT,
                    measure_performance=not args.no_measure_performance,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "arm":
        armed_state = set_engine_armed_state(REPO_ROOT, True)
        snapshot = build_reactions_snapshot(REPO_ROOT, state=armed_state, signal_mode="cached")
        snapshot["runner"] = {
            "delegated_to": "metabolismd",
            "command": "./repo-python -m tools.meta.control.metabolismd run",
        }
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0
    if args.command == "disarm":
        print(
            json.dumps(
                build_reactions_snapshot(
                    REPO_ROOT,
                    state=set_engine_armed_state(REPO_ROOT, False),
                    signal_mode="cached",
                ),
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0
    if args.command == "run-action":
        return run_action(
            REPO_ROOT,
            reaction_id=args.reaction_id,
            reaction_run_id=args.reaction_run_id,
            operation_id=args.operation_id,
            parameters_json=args.parameters_json,
            signal_digest=args.signal_digest,
            signal_json=args.signal_json,
            started_at=args.started_at,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
