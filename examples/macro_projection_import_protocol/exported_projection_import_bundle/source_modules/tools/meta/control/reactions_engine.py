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
  - `build_reactions_orchestration_projection`
  - `load_reactions_state`
  - `load_reactions_config`
  - `set_engine_armed_state`
  - `set_reaction_override_state`
"""
from __future__ import annotations

import hashlib
import json
import os
import shlex
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

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
    from system.lib.hologram_build_status import load_hologram_build_status as _load

    return _load(*args, **kwargs)


def load_raw_seed_pipeline_snapshot(*args: Any, **kwargs: Any) -> Any:
    from system.lib.raw_seed_atomization import load_raw_seed_pipeline_snapshot as _load

    return _load(*args, **kwargs)


def load_work_ledger_runtime_status(*args: Any, **kwargs: Any) -> Any:
    from system.lib.work_ledger_runtime import load_runtime_status as _load

    return _load(*args, **kwargs)


def prepare_launch_operation(*args: Any, **kwargs: Any) -> Any:
    from system.lib.launchable_operations import prepare_launch_operation as _prepare_launch_operation

    return _prepare_launch_operation(*args, **kwargs)


def start_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
    from system.lib.launchable_operations import start_meta_mission_run as _start_meta_mission_run

    return _start_meta_mission_run(*args, **kwargs)


def launcher_meta_mission_env(*args: Any, **kwargs: Any) -> Any:
    from system.lib.launchable_operations import launcher_meta_mission_env as _launcher_meta_mission_env

    return _launcher_meta_mission_env(*args, **kwargs)


def artifact_refs_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    from system.lib.launchable_operations import artifact_refs_from_operation_output as _artifact_refs_from_operation_output

    return _artifact_refs_from_operation_output(*args, **kwargs)


def operation_event_fields_from_operation_output(*args: Any, **kwargs: Any) -> Any:
    from system.lib.launchable_operations import (
        operation_event_fields_from_operation_output as _operation_event_fields_from_operation_output,
    )

    return _operation_event_fields_from_operation_output(*args, **kwargs)


def finalize_meta_mission_run(*args: Any, **kwargs: Any) -> Any:
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
        lines = path.read_text(encoding="utf-8").splitlines()
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
    return _resolve(repo_root, REACTIONS_STATE_REL)


def reactions_ledger_path(repo_root: Path) -> Path:
    return _resolve(repo_root, REACTIONS_LEDGER_REL)


def reactions_stop_flag_path(repo_root: Path) -> Path:
    return _resolve(repo_root, REACTIONS_STOP_FLAG_REL)


def orchestration_events_path(repo_root: Path) -> Path:
    return _resolve(repo_root, ORCHESTRATION_EVENTS_REL)


def default_reactions_state() -> dict[str, Any]:
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
    state = _load_json(reactions_state_path(repo_root)) or default_reactions_state()
    return _migrate_reactions_state_to_v2(state)


def save_reactions_state(repo_root: Path, state: Mapping[str, Any]) -> dict[str, Any]:
    merged = default_reactions_state()
    merged.update(dict(state))
    _migrate_reactions_state_to_v2(merged)
    _atomic_write_json(reactions_state_path(repo_root), merged)
    return merged


def ensure_reactions_state(repo_root: Path) -> dict[str, Any]:
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
    runtime_entry = _reaction_runtime_entry(state, target_id)
    runtime_entry.update({
        "last_fired_at": started_at,
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
            "operation_id": operation_id,
            "fired_at": started_at,
            "signal_digest": evaluation["signal_digest"],
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


def build_reactions_snapshot(
    repo_root: Path,
    *,
    state: Optional[Mapping[str, Any]] = None,
    config: Optional[Mapping[str, Any]] = None,
    signal_mode: str = "live",
) -> dict[str, Any]:
    """Build a reaction snapshot.

    ``signal_mode="live"`` is exact and re-runs every configured signal
    producer. ``signal_mode="cached"`` evaluates predicates against each
    reaction's persisted ``last_signal`` from ``reactions_state.json``; use it
    for read-only entry surfaces that need cheap visibility, not scheduler
    authority.
    """
    now = _now_dt()
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

    reactions = []
    last_fired_at = state_payload.get("last_fired_at")
    for reaction in sorted(config_payload.get("reactions") or [], key=_reaction_sort_key):
        if not isinstance(reaction, Mapping):
            continue
        reaction_id = str(reaction.get("reaction_id") or "").strip()
        runtime_entry = _reaction_runtime_entry(state_payload, reaction_id)
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
        reactions.append(
            {
                "reaction_id": reaction_id,
                "label": reaction.get("label"),
                "priority": reaction.get("priority"),
                "source_kind": _safe_mapping(reaction.get("source")).get("kind"),
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
                "action": {
                    "operation_id": _safe_mapping(reaction.get("action")).get("operation_id"),
                    "parameters": evaluation["action_parameters"],
                },
            }
        )
    return {
        "schema": "reactions_snapshot_v1",
        "generated_at": now.isoformat(),
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
        "reactions": reactions,
    }


def build_reactions_orchestration_projection(repo_root: Path) -> dict[str, Any]:
    snapshot = build_reactions_snapshot(repo_root)
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
    snapshot = build_reactions_snapshot(repo_root)
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
    """Spawn the detached run loop if no live pid is recorded.

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
    barrier = {
        "reaction_id": reaction_id,
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
            "operation_id": operation_id,
            "fired_at": started_at,
            "signal_digest": evaluation["signal_digest"],
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
    prior_fingerprint = str(entry.get("last_fired_ledger_fingerprint") or "").strip()
    resolved_fingerprint = str(ledger_fingerprint or prior_fingerprint or "").strip()
    entry.update(
        {
            "last_result": outcome,
            "last_operation_id": operation_id,
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
            "operation_id": operation_id,
            "completed_at": now_iso if outcome == "completed" else None,
            "failed_at": now_iso if outcome == "failed" else None,
            "duration_ms": duration_ms,
            "returncode": returncode,
            "signal_digest": signal_digest,
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
    operation_id: str,
    parameters_json: str,
    signal_digest: str,
    signal_json: str,
    started_at: str,
) -> int:
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
            extra={"duration_ms": duration_ms, "command": prepared.command, "reaction_id": reaction_id},
        )
        raise


def run_engine(repo_root: Path) -> int:
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
    subparsers.add_parser("status")
    subparsers.add_parser("arm")
    subparsers.add_parser("disarm")

    run_action_parser = subparsers.add_parser("run-action")
    run_action_parser.add_argument("--reaction-id", required=True)
    run_action_parser.add_argument("--operation-id", required=True)
    run_action_parser.add_argument("--parameters-json", required=True)
    run_action_parser.add_argument("--signal-digest", required=True)
    run_action_parser.add_argument("--signal-json", required=True)
    run_action_parser.add_argument("--started-at", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "run":
        from tools.meta.control import metabolismd

        return metabolismd.main(["run"])
    if args.command == "tick":
        print(json.dumps(tick_engine(REPO_ROOT), indent=2, ensure_ascii=False))
        return 0
    if args.command == "status":
        print(json.dumps(build_reactions_snapshot(REPO_ROOT), indent=2, ensure_ascii=False))
        return 0
    if args.command == "arm":
        armed_state = set_engine_armed_state(REPO_ROOT, True)
        snapshot = build_reactions_snapshot(REPO_ROOT, state=armed_state)
        snapshot["runner"] = {
            "delegated_to": "metabolismd",
            "command": "./repo-python -m tools.meta.control.metabolismd run",
        }
        print(json.dumps(snapshot, indent=2, ensure_ascii=False))
        return 0
    if args.command == "disarm":
        print(json.dumps(build_reactions_snapshot(REPO_ROOT, state=set_engine_armed_state(REPO_ROOT, False)), indent=2, ensure_ascii=False))
        return 0
    if args.command == "run-action":
        return run_action(
            REPO_ROOT,
            reaction_id=args.reaction_id,
            operation_id=args.operation_id,
            parameters_json=args.parameters_json,
            signal_digest=args.signal_digest,
            signal_json=args.signal_json,
            started_at=args.started_at,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
