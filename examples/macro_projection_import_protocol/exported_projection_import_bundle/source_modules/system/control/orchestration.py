"""
[PURPOSE]
- Teleology: Build the canonical runtime-control snapshot, brief projections, event-log records, and focus-directive mutations that the control room and docs-route surfaces treat as the authority for current orchestration ownership.
- Mechanism: Read phase, factory, mission, documentation, bridge-lock, and agent-bootstrap state; derive one decision/gate/coordination model; then optionally persist the state, brief, event log, or directive update.

[INTERFACE]
- Exports: build_orchestration_state, build_orchestration_brief, render_orchestration_brief, write_orchestration_artifacts, load_orchestration_state, selected_action, write_active_directive, clear_active_directive, run_selected_action.
- Reads: phase pipeline status, factory state, mission session, docs-route focus, bridge locks, apply staging artifacts, agent bootstrap, and persisted orchestration artifacts under tools/meta/control/.
- Writes: tools/meta/control/orchestration_state.json, tools/meta/control/orchestration_brief.json, tools/meta/control/orchestration_brief.md, tools/meta/control/orchestration_events.jsonl, and the active phase focus directive via seed_pipeline_controller.
- Schema: The persisted state kind is orchestration_state with orchestration_state_v1; projected briefs emit orchestration_brief and event-log entries emit orchestration_event_v1.

[FLOW]
- Orders: Gather lane snapshots -> derive immediate decision + gate -> build coordination/actor frames -> persist state/brief/event log when requested -> expose the selected action or directive mutation helpers to callers.
- When-needed: Open when control-room routing needs the authoritative runtime-control synthesizer or directive mutation surface instead of reading the JSON projections and upstream lane drivers separately.
- Escalates-to: docs/orchestration_state.md; tools/meta/control/orchestration_state.json; system/lib/seed_pipeline_controller.py::write_focus_directive
- Navigation-group: server_control

[DEPENDENCIES]
- system.control.documentation_route_focus: Loads and summarizes the active documentation-route focus overlay for coordination metadata.
- system.lib.seed_pipeline_controller: Ensures controller state exists and writes active focus directives for the current phase.
- pipeline_overnight + pipeline_advance + seed_pipeline (runtime imports): Provide phase lane status, resume packets, and retryable-gate logic.

[CONSTRAINTS]
- Guarantee: All public state builders derive one bounded orchestration authority surface from on-disk runtime snapshots instead of chat-local memory.
- Orders: Event IDs and fingerprints are content-derived so unchanged runtime cores do not append duplicate log entries.
- Non-goal: This module does not own the TUI or CLI shell surfaces; it only computes and persists the control-plane artifacts those surfaces consume.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
import shlex
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib.codex_paths import canonicalize_write_path
from system.lib.phase_activation import load_explicit_active_phase
from system.lib.python_std_compliance_runtime import load_python_std_compliance_coverage
from tools.meta.control import reactions_engine as reactions_runtime

REPO_ROOT = Path(__file__).resolve().parents[2]

ORCHESTRATION_STATE_REL = "tools/meta/control/orchestration_state.json"
ORCHESTRATION_BRIEF_JSON_REL = "tools/meta/control/orchestration_brief.json"
ORCHESTRATION_BRIEF_MD_REL = "tools/meta/control/orchestration_brief.md"
ORCHESTRATION_EVENT_LOG_REL = "tools/meta/control/orchestration_events.jsonl"
FACTORY_STATE_REL = "tools/meta/factory/factory_state.json"
MISSION_SESSION_REL = "tools/meta/factory/mission_session_v0.json"
APPLY_STAGING_REL = "tools/meta/apply/apply_staging"
PHASE_PACKETS_REL = "tools/meta/apply/phase_packets"
BRIDGE_LOCKS_REL = "tools/meta/apply/observe_history/bridge_locks"
DOCS_REL = "docs"
AGENT_BOOTSTRAP_REL = "codex/doctrine/agent_bootstrap.json"
CONTROL_ROOM_COMMAND = "python3 run_control_room.py"
OBSERVE_ROOM_COMMAND = "python3 run_observe.py"
FACTORY_STAGE_APPLY_COMMAND = "./repo-python tools/meta/factory/factory_runner.py --step stage_apply"

INVALID_APPLY_SESSION_STATUSES = {
    "",
    "dry_run",
    "error",
    "failure",
    "ok_no_json",
    "skipped",
}
REVIEW_GATE_REASONS = {
    "apply_review_pending",
    "invalid_review_packet",
    "missing_review_packet",
    "phase_checkpoint_review_pending",
}
PHASE_CHECKPOINT_CONSUMED_WAVE_STATUSES = {
    "assimilated",
    "closed",
    "archived",
    "complete",
    "completed",
    "done",
}

PHASE_PROGRESS_STAGES = {
    "idle",
    "init",
    "initialized",
    "scope",
    "probe",
    "plan",
    "shards_extracted",
    "shards_selected",
    "synth_seed_emitted",
    "observe_plan_compiled",
    "observe_dispatched",
    "results_processed",
    "apply_ready",
    "apply_approved",
    "cycle_complete",
}
FACTORY_ACTIVE_STAGES = {
    "starting",
    "materialized",
    "observe_running",
    "observe_complete",
    "merged",
    "batch_shards_done",
    "concept_link_running",
    "concept_link_complete",
    "merge_concepts_done",
    "gen_synthesis_plan_done",
    "concept_synthesis_running",
    "concept_synthesis_complete",
    "merge_synthesis_done",
    "stage_apply_failed",
}
FACTORY_RETRYABLE_STAGES = {
    "observe_failed": "observe",
    "merge_failed": "merge",
    "batch_shards_failed": "batch_shards",
    "concept_link_failed": "concept_link",
    "merge_concepts_failed": "merge_concepts",
    "gen_synthesis_plan_failed": "gen_synthesis_plan",
    "concept_synthesis_failed": "concept_synthesis",
    "merge_synthesis_failed": "merge_synthesis",
    "stage_apply_failed": "stage_apply",
}
FACTORY_STAGE_TO_NEXT_STEP = {
    "idle": "materialize",
    "starting": "materialize",
    "materialized": "observe",
    "observe_complete": "merge",
    "merged": "batch_shards",
    "batch_shards_done": "concept_link",
    "concept_link_complete": "merge_concepts",
    "merge_concepts_done": "gen_synthesis_plan",
    "gen_synthesis_plan_done": "concept_synthesis",
    "concept_synthesis_complete": "merge_synthesis",
    "merge_synthesis_done": "stage_apply",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _resolve(repo_root: Path, rel_path: str) -> Path:
    return (repo_root / rel_path).resolve()


def _relative(repo_root: Path, path: Path | None) -> str | None:
    if path is None:
        return None
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


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in (value if isinstance(value, list) else []) if str(item).strip()]


def _mtime_iso(path: Path | None) -> str | None:
    if path is None or not path.exists():
        return None
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _parse_iso(value: Any) -> datetime | None:
    token = _string(value)
    if not token:
        return None
    if token.endswith("Z"):
        token = token[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(token)
    except ValueError:
        return None


def _path_card(repo_root: Path, path: Path | None) -> dict[str, Any]:
    exists = bool(path and path.exists())
    return {
        "path": _relative(repo_root, path),
        "exists": exists,
        "modified_at": _mtime_iso(path) if exists else None,
        "bytes": int(path.stat().st_size) if exists else None,
    }


def _safe_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _pid_running(pid: Any) -> bool:
    try:
        value = int(pid)
    except (TypeError, ValueError):
        return False
    if value <= 0:
        return False
    try:
        os.kill(value, 0)
    except OSError:
        return False
    return True


def _safe_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _phase_identity_aliases(value: Any) -> set[str]:
    token = _string(value).casefold()
    if not token:
        return set()
    return {
        item
        for item in {
            token,
            token.replace("_", "."),
            token.replace(".", "_"),
            token.replace("_", "").replace(".", ""),
        }
        if item
    }


def _canonical_phase_dir(value: Any) -> str | None:
    token = _string(value)
    if not token:
        return None
    return canonicalize_write_path(token) or token


def _cached_phase_driver(payload: Mapping[str, Any]) -> dict[str, Any]:
    source_snapshots = _safe_mapping(payload.get("source_snapshots"))
    phase_driver = _safe_mapping(source_snapshots.get("phase_pipeline"))
    if phase_driver:
        return phase_driver
    for item in _safe_list(payload.get("drivers")):
        if not isinstance(item, Mapping):
            continue
        if _string(item.get("driver_id")) == "phase_pipeline":
            return dict(item)
    return {}


def _phase_driver_matches_activation(
    phase_driver: Mapping[str, Any],
    activation: Mapping[str, Any],
) -> bool:
    active_dir = _canonical_phase_dir(activation.get("phase_dir"))
    driver_dir = _canonical_phase_dir(phase_driver.get("phase_dir"))
    if active_dir and driver_dir:
        return active_dir == driver_dir

    active_aliases: set[str] = set()
    for key in ("phase_id", "phase_number", "phase_title"):
        active_aliases.update(_phase_identity_aliases(activation.get(key)))
    driver_aliases: set[str] = set()
    for key in ("phase_ref", "phase_id", "phase_number", "phase_title"):
        driver_aliases.update(_phase_identity_aliases(phase_driver.get(key)))
    if active_aliases or driver_aliases:
        return bool(active_aliases & driver_aliases)
    return True


def _cached_orchestration_active_phase_mismatch(
    repo_root: Path,
    payload: Mapping[str, Any],
) -> bool:
    activation = load_explicit_active_phase(repo_root)
    if not isinstance(activation, Mapping) or not activation:
        return False
    phase_driver = _cached_phase_driver(payload)
    if not phase_driver:
        return True
    return not _phase_driver_matches_activation(phase_driver, activation)


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_last_jsonl_record(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return None
    if not lines:
        return None
    try:
        payload = json.loads(lines[-1])
    except json.JSONDecodeError:
        return None
    return dict(payload) if isinstance(payload, Mapping) else None


def _append_jsonl_record(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(dict(payload), ensure_ascii=False) + "\n")


def _normalize_driver_event(driver: Mapping[str, Any]) -> dict[str, Any]:
    next_action = _safe_mapping(driver.get("next_action"))
    return {
        "driver_id": _string(driver.get("driver_id")) or None,
        "stage": _string(driver.get("stage")) or None,
        "blocked": bool(driver.get("blocked")),
        "gate_reason": _string(driver.get("gate_reason")) or None,
        "next_summary": _string(next_action.get("summary")) or None,
        "next_command": _string(next_action.get("command")) or None,
        "state_path": _string(driver.get("state_path")) or None,
        "last_updated": _string(driver.get("last_updated")) or None,
    }


def _load_agent_bootstrap(repo_root: Path) -> dict[str, Any]:
    return _load_json(_resolve(repo_root, AGENT_BOOTSTRAP_REL)) or {}


def _minimum_read_set_paths(repo_root: Path, set_id: str | None) -> list[str]:
    token = _string(set_id)
    if not token:
        return []
    bootstrap = _load_agent_bootstrap(repo_root)
    minimum_read_sets = bootstrap.get("minimum_read_sets")
    if not isinstance(minimum_read_sets, Mapping):
        return []
    entry = minimum_read_sets.get(token)
    if not isinstance(entry, Mapping):
        return []
    return _string_list(entry.get("paths"))


def _actor_context_rows(repo_root: Path) -> list[dict[str, Any]]:
    bootstrap = _load_agent_bootstrap(repo_root)
    rows = bootstrap.get("actor_context_surfaces")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        actor_id = _string(row.get("actor_id"))
        label = _string(row.get("label"))
        minimum_read_set_id = _string(row.get("minimum_read_set_id")) or None
        if not actor_id or not label:
            continue
        out.append(
            {
                "actor_id": actor_id,
                "label": label,
                "read_order": _string_list(row.get("read_order")),
                "minimum_read_set_id": minimum_read_set_id,
                "minimum_read_paths": _minimum_read_set_paths(repo_root, minimum_read_set_id),
                "primary_commands": _string_list(row.get("primary_commands")),
                "runtime_surface_id": _string(row.get("runtime_surface_id")) or None,
            }
        )
    return out


def _controller_state_from_phase_driver(phase_driver: Mapping[str, Any]) -> dict[str, Any] | None:
    state = _safe_mapping(phase_driver.get("state_payload"))
    phase_dir = _string(state.get("phase_dir")) or _string(phase_driver.get("phase_dir"))
    if not phase_dir:
        return None
    if not state:
        state = {}
    state.setdefault("phase_dir", phase_dir)
    family_dir = _string(state.get("family_dir")) or _string(phase_driver.get("family_dir"))
    if family_dir:
        state.setdefault("family_dir", family_dir)
    phase_ref = _string(state.get("phase_ref")) or _string(phase_driver.get("phase_ref"))
    if phase_ref:
        state.setdefault("phase_ref", phase_ref)
    phase_title = _string(state.get("phase_title")) or _string(phase_driver.get("phase_title"))
    if phase_title:
        state.setdefault("phase_title", phase_title)
    cycle = state.get("cycle", phase_driver.get("cycle"))
    if cycle is not None:
        state.setdefault("cycle", cycle)
    return state


def _controller_artifact_path(
    repo_root: Path,
    controller_state: Mapping[str, Any] | None,
    *,
    state_key: str,
    default_name: str,
) -> Path | None:
    if not isinstance(controller_state, Mapping):
        return None
    explicit = _string(controller_state.get(state_key))
    if explicit:
        return _resolve(repo_root, explicit)
    phase_dir = _string(controller_state.get("phase_dir"))
    if not phase_dir:
        return None
    return _resolve(repo_root, f"{phase_dir.rstrip('/')}/{default_name}")


def _load_system_view_summary(repo_root: Path, phase_driver: Mapping[str, Any]) -> dict[str, Any]:
    controller_state = _controller_state_from_phase_driver(phase_driver)
    path = _controller_artifact_path(
        repo_root,
        controller_state,
        state_key="system_view_path",
        default_name="system_view.json",
    )
    payload = _load_json(path) if path and path.exists() else None
    files = payload.get("files") if isinstance(payload, Mapping) and isinstance(payload.get("files"), list) else []
    preferred_files = [
        _string(item.get("path"))
        for item in files
        if isinstance(item, Mapping) and item.get("preferred")
    ]
    sample_files = [
        _string(item.get("path"))
        for item in files[:5]
        if isinstance(item, Mapping) and _string(item.get("path"))
    ]
    return {
        "path": _relative(repo_root, path) if path else None,
        "exists": bool(path and path.exists()),
        "generated_at": _string((payload or {}).get("generated_at")) or _mtime_iso(path),
        "file_count": _safe_int((payload or {}).get("file_count"), len(files)),
        "preferred_file_count": len(preferred_files),
        "preferred_files": preferred_files[:8],
        "sample_files": sample_files,
    }


def _load_active_directive(repo_root: Path, phase_driver: Mapping[str, Any]) -> dict[str, Any]:
    controller_state = _controller_state_from_phase_driver(phase_driver)
    path = _controller_artifact_path(
        repo_root,
        controller_state,
        state_key="directive_path",
        default_name="focus_directive.json",
    )
    payload = _load_json(path) if path and path.exists() else None
    active = bool(isinstance(payload, Mapping) and payload.get("active"))
    file_targets = _string_list((payload or {}).get("file_targets"))
    return {
        "active": active,
        "path": _relative(repo_root, path) if path else None,
        "task": _string((payload or {}).get("task")) or None,
        "summary": _string((payload or {}).get("summary")) or None,
        "file_targets": file_targets,
        "updated_at": _string((payload or {}).get("updated_at")) or _mtime_iso(path),
    }


def _load_docs_route_focus_summary(repo_root: Path) -> dict[str, Any]:
    try:
        from system.control.documentation_route_focus import (
            load_documentation_route_focus,
            summarize_active_focus,
        )

        focus_doc = load_documentation_route_focus(repo_root)
        summary = summarize_active_focus(focus_doc)
        summary["updated_at"] = _string(focus_doc.get("updated_at")) or None
        summary["set_by"] = _string(focus_doc.get("set_by")) or None
        return summary
    except Exception:
        return {}


def _load_python_std_compliance_projection(repo_root: Path) -> dict[str, Any]:
    coverage = load_python_std_compliance_coverage(repo_root)
    if coverage is None:
        try:
            from system.lib.python_std_compliance_findings import write_python_std_compliance_coverage

            coverage = write_python_std_compliance_coverage(repo_root=repo_root)
        except Exception:
            coverage = {}
    counts = _safe_mapping(coverage.get("counts"))
    triggers = _safe_mapping(coverage.get("triggers"))
    integrity = _safe_mapping(coverage.get("integrity"))
    active_campaign = _safe_mapping(coverage.get("active_campaign"))
    campaigns = [
        dict(item)
        for item in _safe_list(coverage.get("campaigns"))
        if isinstance(item, Mapping)
    ]
    blocked_campaign = next(
        (
            item
            for item in campaigns
            if _string(item.get("lifecycle_state")) == "blocked"
        ),
        {},
    )
    blocked_reason = None
    if bool(integrity.get("multiple_nonterminal_campaigns")):
        blocked_reason = "multiple_nonterminal_campaigns"
    elif blocked_campaign:
        blocked_reason = (
            "remaining_snapshot_findings"
            if _safe_int(blocked_campaign.get("remaining_snapshot_findings")) > 0
            else "blocked_campaign_present"
        )

    if active_campaign:
        stage = _string(active_campaign.get("lifecycle_state")) or "active"
    elif blocked_reason:
        stage = "blocked"
    elif _safe_int(counts.get("findings_unapplied")) > 0:
        stage = "backlog_present"
    else:
        stage = "idle"

    if bool(triggers.get("approval_required")):
        gate = "approval_required"
    elif blocked_reason:
        gate = "blocked"
    elif bool(triggers.get("drain_ready")):
        gate = "drain_ready"
    elif bool(triggers.get("preview_kickoff_ready")):
        gate = "preview_kickoff_ready"
    elif _safe_int(counts.get("findings_unapplied")) > 0:
        gate = "waiting_for_cycle"
    else:
        gate = "clear"

    approval_needed = {
        "required": bool(triggers.get("approval_required")),
        "campaign_summary_path": _string(active_campaign.get("campaign_summary_path")) or None,
        "command": _string(active_campaign.get("approve_command")) or None,
    }
    return {
        "stage": stage,
        "gate": gate,
        "generated_at": _string(coverage.get("generated_at")) or None,
        "coverage_path": _string(coverage.get("coverage_path"))
        or _string(_safe_mapping(coverage.get("paths")).get("coverage_path"))
        or None,
        "counts": counts,
        "triggers": triggers,
        "active_campaign": active_campaign or None,
        "approval_needed": approval_needed,
        "blocked_reason": blocked_reason,
    }


def _add_routing_emphasis(
    target: dict[str, int],
    reasons: list[str],
    *,
    tag: str,
    delta: int,
    reason: str,
) -> None:
    if not tag or not delta:
        return
    target[tag] = int(target.get(tag, 0)) + int(delta)
    reasons.append(reason)


def _current_owner_actor_id(
    *,
    active_driver: str,
    gate: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
) -> str:
    if int(bridge_snapshot.get("live_count") or 0) > 0:
        return "bridge_worker"
    if bool(gate.get("active")):
        gate_reason = _string(gate.get("gate_reason"))
        if gate_reason in REVIEW_GATE_REASONS:
            return "human_operator"
        return "control_room_manager"
    if active_driver in {"manual_review", "manual_documentation", "no_active_runtime_phase"}:
        return "human_operator"
    if active_driver == "wait_existing_bridge":
        return "bridge_worker"
    return "control_room_manager"


def _handoff_actor_id(mode: str) -> str:
    if mode in {"manual_review", "manual_documentation", "no_active_runtime_phase"}:
        return "human_operator"
    if mode == "wait_existing_bridge":
        return "bridge_worker"
    return "control_room_manager"


def _build_current_owner(
    *,
    active_driver: str,
    decision: Mapping[str, Any],
    gate: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    actor_id = _current_owner_actor_id(
        active_driver=active_driver,
        gate=gate,
        bridge_snapshot=bridge_snapshot,
    )
    owner_driver = _string(gate.get("owner_driver")) if bool(gate.get("active")) else active_driver
    reason = (
        _string(gate.get("gate_reason"))
        if bool(gate.get("active"))
        else _string(decision.get("summary"))
    ) or None
    return {
        "actor_id": actor_id,
        "driver_id": owner_driver or active_driver or None,
        "reason": reason,
    }


def _build_next_handoff(
    *,
    decision: Mapping[str, Any],
    gate: Mapping[str, Any],
    human_surface: Mapping[str, Any],
) -> dict[str, Any]:
    sequence = [
        dict(step)
        for step in _safe_list(decision.get("sequence"))
        if isinstance(step, Mapping)
    ]
    if bool(gate.get("active")) and len(sequence) > 1:
        next_step = sequence[1]
    elif sequence:
        next_step = sequence[0]
    else:
        next_step = dict(decision)
    mode = _string(next_step.get("mode")) or _string(decision.get("immediate_mode")) or "unknown"
    review_surface = (
        _string(next_step.get("path"))
        or _string(next_step.get("primary_surface"))
        or _string(human_surface.get("recommended_review_surface"))
        or None
    )
    return {
        "actor_id": _handoff_actor_id(mode),
        "mode": mode,
        "command": _string(next_step.get("command")) or None,
        "review_surface": review_surface,
        "completion_basis": _string(next_step.get("summary")) or _string(decision.get("summary")) or None,
    }


def _build_routing_emphasis(
    *,
    active_driver: str,
    gate: Mapping[str, Any],
    phase_driver: Mapping[str, Any],
    factory_driver: Mapping[str, Any],
    mission_driver: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
    active_directive: Mapping[str, Any],
    system_view: Mapping[str, Any],
) -> dict[str, Any]:
    deltas: dict[str, int] = {}
    reasons: list[str] = []
    if bool(gate.get("active")):
        gate_reason = _string(gate.get("gate_reason")) or "runtime_gate"
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="runtime_control",
            delta=170,
            reason=f"Gate `{gate_reason}` is active, so runtime-control surfaces should win ties.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="control_room",
            delta=140,
            reason="An active gate makes the control room the primary human coordination surface.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="coordination",
            delta=110,
            reason="Coordination details matter more while the runtime selector is gated.",
        )
        if gate_reason in REVIEW_GATE_REASONS:
            _add_routing_emphasis(
                deltas,
                reasons,
                tag="human_operator",
                delta=190,
                reason="Manual review is required, so human-operator routes should dominate.",
            )
    if int(bridge_snapshot.get("live_count") or 0) > 0:
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="bridge_worker",
            delta=180,
            reason="A live bridge lock exists, so bridge-worker context is immediately relevant.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="runtime_control",
            delta=60,
            reason="A live bridge lock also increases the need for runtime-control visibility.",
        )
    if active_driver == "phase_pipeline":
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="phase_artifacts",
            delta=80,
            reason="The phase pipeline is the selected lane, so phase-local artifacts should rank higher.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="ide_agent",
            delta=40,
            reason="Phase-local execution typically needs an IDE agent with exact file context.",
        )
    if active_driver == "factory_lane":
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="factory_lane",
            delta=90,
            reason="The factory lane currently owns the next step.",
        )
    if active_driver == "mission_queue":
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="mission_queue",
            delta=90,
            reason="Mission-queue work is active, so manager-process routing should rank up.",
        )
    if bool(active_directive.get("active")):
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="directive",
            delta=120,
            reason="An active focus directive exists, so directive-bearing routes should gain weight.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="phase_artifacts",
            delta=70,
            reason="The active directive points back to phase-local artifacts.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="agent_context",
            delta=40,
            reason="An active directive raises the value of explicit actor/context surfaces.",
        )
    if bool(system_view.get("exists")):
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="system_view",
            delta=90,
            reason="A live system_view.json exists, so generated phase coverage views should be discoverable.",
        )
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="phase_artifacts",
            delta=50,
            reason="system_view.json is a phase-local artifact and should bias phase routing.",
        )
    if _string(phase_driver.get("stage")) in PHASE_PROGRESS_STAGES:
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="phase_artifacts",
            delta=35,
            reason="The phase lane is active on disk, so phase-local context still matters.",
        )
    if _string(factory_driver.get("stage")) == "apply_review_pending":
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="human_operator",
            delta=90,
            reason=(
                "phase_checkpoint_review_pending increases the priority of human-facing review surfaces."
                if _string(factory_driver.get("gate_reason")) == "phase_checkpoint_review_pending"
                else "apply_review_pending increases the priority of human-facing review surfaces."
            ),
        )
    if bool(mission_driver.get("active")):
        _add_routing_emphasis(
            deltas,
            reasons,
            tag="manager_process",
            delta=70,
            reason="An active mission queue favors manager-process and handoff-aware routing.",
        )
    ordered = dict(sorted(deltas.items(), key=lambda item: (-int(item[1]), item[0])))
    return {
        "active_tags": list(ordered.keys()),
        "tag_deltas": ordered,
        "reasons": reasons,
    }


def _build_actor_frames(
    *,
    repo_root: Path,
    docs_route_focus: Mapping[str, Any],
    current_owner: Mapping[str, Any],
    next_handoff: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
    active_directive: Mapping[str, Any],
    system_view: Mapping[str, Any],
) -> dict[str, Any]:
    frames: dict[str, Any] = {}
    current_owner_actor = _string(current_owner.get("actor_id"))
    next_handoff_actor = _string(next_handoff.get("actor_id"))
    live_bridge = int(bridge_snapshot.get("live_count") or 0) > 0
    active_preset = _string(docs_route_focus.get("active_preset_id")) or None
    for row in _actor_context_rows(repo_root):
        actor_id = _string(row.get("actor_id"))
        status = "standby"
        reasons: list[str] = []
        if actor_id == current_owner_actor:
            status = "current_owner"
            if _string(current_owner.get("reason")):
                reasons.append(_string(current_owner.get("reason")))
        elif actor_id == next_handoff_actor:
            status = "next_handoff"
            if _string(next_handoff.get("completion_basis")):
                reasons.append(_string(next_handoff.get("completion_basis")))
        elif actor_id == "bridge_worker" and live_bridge:
            status = "active"
            reasons.append("A live bridge lock is present.")
        elif actor_id in {"codex", "claude_code"} and (bool(active_directive.get("active")) or bool(system_view.get("exists"))):
            status = "ready"
            reasons.append("Exact-context IDE work is supported by active directive/system-view state.")
        elif actor_id == "control_room_manager":
            status = "active"
            reasons.append("The control room owns coordination even when no manual gate is active.")
        frame = dict(row)
        frame["status"] = status
        frame["reasons"] = reasons
        frame["docs_route_focus"] = active_preset
        frames[actor_id] = frame
    return frames


def _build_coordination(
    *,
    repo_root: Path,
    active_driver: str,
    decision: Mapping[str, Any],
    gate: Mapping[str, Any],
    human_surface: Mapping[str, Any],
    phase_driver: Mapping[str, Any],
    factory_driver: Mapping[str, Any],
    mission_driver: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    docs_route_focus = _load_docs_route_focus_summary(repo_root)
    active_directive = _load_active_directive(repo_root, phase_driver)
    system_view = _load_system_view_summary(repo_root, phase_driver)
    current_owner = _build_current_owner(
        active_driver=active_driver,
        decision=decision,
        gate=gate,
        bridge_snapshot=bridge_snapshot,
    )
    next_handoff = _build_next_handoff(
        decision=decision,
        gate=gate,
        human_surface=human_surface,
    )
    routing_emphasis = _build_routing_emphasis(
        active_driver=active_driver,
        gate=gate,
        phase_driver=phase_driver,
        factory_driver=factory_driver,
        mission_driver=mission_driver,
        bridge_snapshot=bridge_snapshot,
        active_directive=active_directive,
        system_view=system_view,
    )
    actor_frames = _build_actor_frames(
        repo_root=repo_root,
        docs_route_focus=docs_route_focus,
        current_owner=current_owner,
        next_handoff=next_handoff,
        bridge_snapshot=bridge_snapshot,
        active_directive=active_directive,
        system_view=system_view,
    )
    return {
        "docs_route_focus": docs_route_focus,
        "active_directive": active_directive,
        "system_view": system_view,
        "routing_emphasis": routing_emphasis,
        "current_owner": current_owner,
        "next_handoff": next_handoff,
        "actor_frames": actor_frames,
    }


def _coordination_event_slice(state: Mapping[str, Any]) -> dict[str, Any]:
    coordination = _safe_mapping(state.get("coordination"))
    docs_route_focus = _safe_mapping(coordination.get("docs_route_focus"))
    active_directive = _safe_mapping(coordination.get("active_directive"))
    system_view = _safe_mapping(coordination.get("system_view"))
    routing_emphasis = _safe_mapping(coordination.get("routing_emphasis"))
    current_owner = _safe_mapping(coordination.get("current_owner"))
    next_handoff = _safe_mapping(coordination.get("next_handoff"))
    actor_frames = coordination.get("actor_frames") if isinstance(coordination.get("actor_frames"), Mapping) else {}
    actor_status = {
        actor_id: _string(frame.get("status")) or None
        for actor_id, frame in actor_frames.items()
        if isinstance(frame, Mapping) and _string(actor_id)
    }
    return {
        "docs_route_focus": {
            "active_preset_id": _string(docs_route_focus.get("active_preset_id")) or None,
            "label": _string(docs_route_focus.get("label")) or None,
        },
        "active_directive": {
            "active": bool(active_directive.get("active")),
            "path": _string(active_directive.get("path")) or None,
            "task": _string(active_directive.get("task")) or None,
            "summary": _string(active_directive.get("summary")) or None,
            "file_targets": _string_list(active_directive.get("file_targets")),
            "updated_at": _string(active_directive.get("updated_at")) or None,
        },
        "system_view": {
            "path": _string(system_view.get("path")) or None,
            "exists": bool(system_view.get("exists")),
            "file_count": _safe_int(system_view.get("file_count"), 0),
        },
        "routing_emphasis": {
            "active_tags": _string_list(routing_emphasis.get("active_tags")),
            "tag_deltas": _safe_mapping(routing_emphasis.get("tag_deltas")),
            "reasons": _string_list(routing_emphasis.get("reasons")),
        },
        "current_owner": {
            "actor_id": _string(current_owner.get("actor_id")) or None,
            "driver_id": _string(current_owner.get("driver_id")) or None,
        },
        "next_handoff": {
            "actor_id": _string(next_handoff.get("actor_id")) or None,
            "mode": _string(next_handoff.get("mode")) or None,
            "command": _string(next_handoff.get("command")) or None,
            "review_surface": _string(next_handoff.get("review_surface")) or None,
        },
        "actor_status": actor_status,
    }


def _orchestration_event_core(state: Mapping[str, Any]) -> dict[str, Any]:
    decision = _safe_mapping(state.get("decision"))
    gate = _safe_mapping(state.get("gate"))
    human_surface = _safe_mapping(state.get("human_surface"))
    drivers = [
        _normalize_driver_event(driver)
        for driver in _safe_list(state.get("drivers"))
        if isinstance(driver, Mapping)
    ]
    return {
        "kind": "orchestration_event",
        "schema_version": "orchestration_event_v1",
        "recorded_at": _string(state.get("updated_at")) or _utc_now(),
        "active_driver": _string(state.get("active_driver")) or None,
        "immediate_mode": _string(decision.get("immediate_mode")) or None,
        "summary": _string(decision.get("summary")) or None,
        "command": _string(decision.get("command")) or None,
        "gate_reason": _string(gate.get("gate_reason")) or None,
        "gate_owner": _string(gate.get("owner_driver")) or None,
        "launch_recommended_now": bool(decision.get("launch_recommended_now")),
        "recommended_review_surface": _string(human_surface.get("recommended_review_surface")) or None,
        "drivers": drivers,
        "coordination": _coordination_event_slice(state),
    }


def _orchestration_event_fingerprint(core: Mapping[str, Any]) -> str:
    canonical = json.dumps(dict(core), ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _event_id(recorded_at: str, fingerprint: str) -> str:
    stamp = recorded_at.replace(":", "").replace("-", "").replace("+", "_").replace(".", "_")
    return f"orch_{stamp}_{fingerprint[:10]}"


def _phase_launch_command(phase_ref: str | None) -> str | None:
    token = _string(phase_ref)
    if not token:
        return None
    return f"python3 pipeline_overnight.py --phase {token} --wake-agent auto --sleep-policy keep_awake"


def _factory_advance_command() -> str:
    return "./repo-python tools/meta/factory/factory_runner.py --advance --provider chatgpt"


def _mission_step_command() -> str:
    return "./repo-python tools/meta/factory/mission_runner.py --step --provider chatgpt"


def _retryable_gate(state: Mapping[str, Any]) -> bool:
    try:
        seed_pipeline = importlib.import_module("seed_pipeline")
    except Exception:
        return _string(state.get("gate_reason")) in {"uncertainty_block", "error_spike_block"}
    checker = getattr(seed_pipeline, "gate_is_retryable", None)
    if callable(checker):
        try:
            return bool(checker(dict(state)))
        except Exception:
            return False
    return False


def _load_bridge_snapshot(repo_root: Path) -> dict[str, Any]:
    locks_dir = _resolve(repo_root, BRIDGE_LOCKS_REL)
    live: list[dict[str, Any]] = []
    stale: list[dict[str, Any]] = []
    if not locks_dir.exists():
        return {
            "lock_dir": _relative(repo_root, locks_dir),
            "exists": False,
            "live_locks": [],
            "stale_locks": [],
            "live_count": 0,
            "stale_count": 0,
        }
    for lock_path in sorted(locks_dir.glob("*.lock")):
        payload = _load_json(lock_path) or {}
        process_id = payload.get("process_id")
        entry = {
            "provider": lock_path.stem,
            "lock_path": _relative(repo_root, lock_path),
            "owner": payload or None,
            "process_id": process_id,
            "process_live": _pid_running(process_id),
        }
        if entry["process_live"]:
            live.append(entry)
        elif payload:
            stale.append(entry)
    return {
        "lock_dir": _relative(repo_root, locks_dir),
        "exists": True,
        "live_locks": live,
        "stale_locks": stale,
        "live_count": len(live),
        "stale_count": len(stale),
    }


def _phase_packet_candidates(repo_root: Path, phase_ref: str | None, suffix: str) -> list[Path]:
    token = _string(phase_ref)
    packets_dir = _resolve(repo_root, PHASE_PACKETS_REL)
    if not token or not packets_dir.exists():
        return []
    candidates: list[Path] = []
    for path in packets_dir.glob(f"{token}*{suffix}"):
        try:
            _ = path.stat().st_mtime
        except OSError:
            continue
        candidates.append(path)
    return sorted(candidates, key=lambda path: path.stat().st_mtime, reverse=True)


def _latest_phase_dock_error(dock_payload: Mapping[str, Any]) -> dict[str, Any] | None:
    dispatch = _safe_mapping(dock_payload.get("dispatch"))
    waves = [
        dict(item)
        for item in _safe_list(dispatch.get("waves"))
        if isinstance(item, Mapping)
    ]
    for wave in reversed(waves):
        wave_index = wave.get("wave_index")
        results = [
            dict(item)
            for item in _safe_list(wave.get("results"))
            if isinstance(item, Mapping)
        ]
        for result in reversed(results):
            status = _string(result.get("status")) or None
            error = _string(result.get("error")) or None
            error_category = _string(result.get("error_category")) or None
            error_stage = _string(result.get("error_stage")) or None
            if status in {"error", "aborted"} or error or error_category or error_stage:
                return {
                    "status": status,
                    "error": error,
                    "error_category": error_category,
                    "error_stage": error_stage,
                    "unit_id": _string(result.get("unit_id")) or None,
                    "wave_index": wave_index,
                    "provider": _string(result.get("provider")) or None,
                    "route": _string(result.get("route")) or None,
                    "response_path": _string(result.get("response_path")) or None,
                }
    dispatch_status = _string(dispatch.get("status")) or None
    dock_status = _string(dock_payload.get("status")) or None
    if dispatch_status in {"error", "aborted"} or dock_status in {"error", "aborted"}:
        return {
            "status": dock_status or dispatch_status,
            "error": None,
            "error_category": None,
            "error_stage": None,
            "unit_id": None,
            "wave_index": None,
            "provider": _string(dispatch.get("consumer")) or None,
            "route": None,
            "response_path": None,
        }
    return None


def _load_phase_runtime_snapshot(repo_root: Path, phase_driver: Mapping[str, Any]) -> dict[str, Any]:
    phase_ref = _string(phase_driver.get("phase_ref")) or None
    phase_dir_rel = _string(phase_driver.get("phase_dir")) or None
    phase_state_path_rel = _string(phase_driver.get("state_path")) or None
    phase_dir_path = _resolve(repo_root, phase_dir_rel) if phase_dir_rel else None
    phase_state_path = _resolve(repo_root, phase_state_path_rel) if phase_state_path_rel else None
    dock_candidates = _phase_packet_candidates(repo_root, phase_ref, "_dock_status.json")
    latest_dock_path = dock_candidates[0] if dock_candidates else None
    latest_dock_payload = _load_json(latest_dock_path) if latest_dock_path else None
    latest_dock_error = _latest_phase_dock_error(latest_dock_payload or {})
    dispatch_status = _string(_safe_mapping((latest_dock_payload or {}).get("dispatch")).get("status")) or None
    dock_status = _string((latest_dock_payload or {}).get("status")) or None
    latest_dock_snapshot = {
        "path": _relative(repo_root, latest_dock_path),
        "exists": bool(latest_dock_path and latest_dock_path.exists()),
        "operation": _string((latest_dock_payload or {}).get("operation")) or None,
        "updated_at": _string((latest_dock_payload or {}).get("updated_at")) or _mtime_iso(latest_dock_path),
        "generated_at": _string((latest_dock_payload or {}).get("generated_at")) or None,
        "status": dock_status,
        "dispatch_status": dispatch_status,
        "indicates_success": dock_status in {"applied", "preview_ready"} and dispatch_status == "success",
        "indicates_failure": bool(latest_dock_error),
    }
    if latest_dock_error:
        latest_dock_error = {
            **latest_dock_error,
            "path": latest_dock_snapshot["path"],
            "updated_at": latest_dock_snapshot["updated_at"],
            "operation": latest_dock_snapshot["operation"],
        }
    phase_step = None
    if phase_dir_path and phase_dir_path.exists():
        synth_path = phase_dir_path / "synth_seed.json"
        synth_payload = _load_json(synth_path) if synth_path.exists() else None
        if isinstance(synth_payload, Mapping):
            try:
                from system.lib.observe_apply_contracts import normalize_synth_payload
                from system.lib.seed_pipeline_controller import phase_step_preview

                phase_step = phase_step_preview(
                    {
                        "phase_id": phase_ref,
                        "phase_number": phase_ref,
                        "phase_dir": phase_dir_rel or _relative(repo_root, phase_dir_path),
                    },
                    normalize_synth_payload(synth_payload),
                    repo_root=repo_root,
                )
            except Exception:
                phase_step = None
    return {
        "phase_ref": phase_ref,
        "phase_state": {
            "path": _relative(repo_root, phase_state_path),
            "exists": bool(phase_state_path and phase_state_path.exists()),
            "stage": _string(phase_driver.get("stage")) or None,
            "updated_at": _string(phase_driver.get("last_updated")) or _mtime_iso(phase_state_path),
        },
        "latest_dock_status": latest_dock_snapshot,
        "latest_phase_dock_error": latest_dock_error,
        "phase_step_preview": phase_step,
    }


def _load_documentation_snapshot(repo_root: Path, family_dir_rel: str | None) -> dict[str, Any]:
    raw_seed_path = _resolve(repo_root, f"{family_dir_rel}/raw_seed.md") if family_dir_rel else None
    docs_dir = _resolve(repo_root, DOCS_REL)
    doc_paths = sorted(docs_dir.glob("raw_seed_*.md")) if docs_dir.exists() else []
    latest_doc = max(doc_paths, key=lambda path: path.stat().st_mtime, default=None) if doc_paths else None
    raw_seed_newer_than_docs = False
    if raw_seed_path and latest_doc and raw_seed_path.exists():
        raw_seed_newer_than_docs = raw_seed_path.stat().st_mtime > latest_doc.stat().st_mtime
    return {
        "raw_seed": _path_card(repo_root, raw_seed_path),
        "raw_seed_doc_count": len(doc_paths),
        "latest_raw_seed_doc": _path_card(repo_root, latest_doc),
        "raw_seed_newer_than_docs": raw_seed_newer_than_docs,
    }


def _load_apply_staging_snapshot(
    repo_root: Path,
    phase_dir_rel: str | None,
    *,
    phase_runtime: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    candidates: list[Path] = []
    if phase_dir_rel:
        candidates.append(_resolve(repo_root, phase_dir_rel))
    candidates.append(_resolve(repo_root, APPLY_STAGING_REL))

    selected_dir = candidates[-1]
    pending_apply = selected_dir / "pending_apply.json"
    checklist_json = selected_dir / "pending_apply_checklist.json"
    checklist_md = selected_dir / "pending_apply_checklist.md"
    for directory in candidates:
        candidate_pending = directory / "pending_apply.json"
        candidate_checklist_json = directory / "pending_apply_checklist.json"
        candidate_checklist_md = directory / "pending_apply_checklist.md"
        if candidate_pending.exists() or candidate_checklist_json.exists() or candidate_checklist_md.exists():
            selected_dir = directory
            pending_apply = candidate_pending
            checklist_json = candidate_checklist_json
            checklist_md = candidate_checklist_md
            break

    pending_payload = _load_json(pending_apply) if pending_apply.exists() else None
    checklist_payload = _load_json(checklist_json) if checklist_json.exists() else None
    factory_state = _load_json(_resolve(repo_root, FACTORY_STATE_REL)) or {}
    compiled_apply = _safe_mapping((pending_payload or {}).get("compiled_apply"))
    compiled_apply_ready = bool(compiled_apply.get("ready"))
    apply_session_result = _safe_mapping((checklist_payload or {}).get("apply_session_result"))
    source_kind = (
        _string((pending_payload or {}).get("source_kind"))
        or _string(compiled_apply.get("source_kind"))
        or _string(apply_session_result.get("source_kind"))
        or None
    )
    apply_cmd = _string((pending_payload or {}).get("apply_cmd")) or None
    apply_session_status = _string(apply_session_result.get("status"))
    apply_session_error = _string(apply_session_result.get("error")) or None
    pending_staged_at = _string((pending_payload or {}).get("staged_at")) or None
    checklist_staged_at = _string((checklist_payload or {}).get("staged_at")) or None
    packet_staged_at = pending_staged_at or checklist_staged_at
    packet_staged_dt = _parse_iso(packet_staged_at)
    factory_last_stage_apply = _string(factory_state.get("last_stage_apply")) or None
    factory_last_stage_apply_dt = _parse_iso(factory_last_stage_apply)
    stale_against_factory = False
    checklist_item_statuses: dict[str, str] = {}
    for item in _safe_list((checklist_payload or {}).get("items")):
        item_payload = _safe_mapping(item)
        item_id = _string(item_payload.get("id"))
        item_status = _string(item_payload.get("status"))
        if item_id:
            checklist_item_statuses[item_id] = item_status

    invalid_reasons: list[str] = []
    if not pending_apply.exists():
        invalid_reasons.append("pending_apply_missing")
    elif pending_payload is None:
        invalid_reasons.append("pending_apply_unreadable")
    if not checklist_json.exists():
        invalid_reasons.append("checklist_json_missing")
    elif checklist_payload is None:
        invalid_reasons.append("checklist_json_unreadable")
    if not checklist_md.exists():
        invalid_reasons.append("checklist_markdown_missing")
    if pending_payload is not None and not compiled_apply_ready:
        invalid_reasons.append("compiled_apply_not_ready")
    if pending_staged_at and checklist_staged_at and pending_staged_at != checklist_staged_at:
        invalid_reasons.append("packet_staged_at_mismatch")
    if checklist_payload is not None and "apply_ops" not in checklist_item_statuses:
        invalid_reasons.append("apply_ops_item_missing")
    if checklist_payload is not None and apply_session_status in INVALID_APPLY_SESSION_STATUSES:
        invalid_reasons.append(f"apply_session_{apply_session_status or 'missing'}")
    elif checklist_payload is not None and apply_session_status != "success":
        invalid_reasons.append(f"apply_session_{apply_session_status}")
    if apply_session_error and apply_session_error.startswith(
        "no compiled apply-ready observe session found for active phase "
    ):
        invalid_reasons.append("phase_apply_source_missing")
    if factory_last_stage_apply_dt is not None:
        if packet_staged_dt is None:
            invalid_reasons.append("packet_staged_at_missing")
        elif packet_staged_dt < factory_last_stage_apply_dt:
            invalid_reasons.append("stale_review_packet")
            stale_against_factory = True

    phase_runtime_snapshot = dict(phase_runtime) if isinstance(phase_runtime, Mapping) else {}
    latest_dock_status = _safe_mapping(phase_runtime_snapshot.get("latest_dock_status"))
    latest_dock_error = _safe_mapping(phase_runtime_snapshot.get("latest_phase_dock_error"))
    phase_step_preview = _safe_mapping(phase_runtime_snapshot.get("phase_step_preview"))
    stale_against_phase_runtime = False
    phase_checkpoint_consumed = (
        source_kind == "phase_dock_response"
        and _string(phase_step_preview.get("wave_status")).lower() in PHASE_CHECKPOINT_CONSUMED_WAVE_STATUSES
    )
    latest_dock_dt = _parse_iso(latest_dock_status.get("updated_at"))
    if (
        packet_staged_dt is not None
        and latest_dock_dt is not None
        and latest_dock_dt > packet_staged_dt
        and bool(latest_dock_status.get("indicates_success"))
    ):
        if "stale_review_packet" not in invalid_reasons:
            invalid_reasons.append("stale_review_packet")
        stale_against_phase_runtime = True
    if phase_checkpoint_consumed:
        if "phase_checkpoint_already_assimilated" not in invalid_reasons:
            invalid_reasons.append("phase_checkpoint_already_assimilated")
        stale_against_phase_runtime = True
    latest_dock_error_dt = _parse_iso(
        latest_dock_error.get("updated_at") or latest_dock_status.get("updated_at")
    )
    if (
        latest_dock_error
        and packet_staged_dt is not None
        and latest_dock_error_dt is not None
        and latest_dock_error_dt > packet_staged_dt
        and "phase_dock_failed_after_packet" not in invalid_reasons
    ):
        invalid_reasons.append("phase_dock_failed_after_packet")

    packet_present = pending_apply.exists() or checklist_json.exists() or checklist_md.exists()
    review_ready = packet_present and not invalid_reasons
    packet_status = "review_ready" if review_ready else ("invalid_review_packet" if packet_present else "missing_review_packet")

    return {
        "dir": _relative(repo_root, selected_dir),
        "pending_apply": _path_card(repo_root, pending_apply),
        "checklist_json": _path_card(repo_root, checklist_json),
        "checklist_md": _path_card(repo_root, checklist_md),
        "packet_status": packet_status,
        "review_ready": review_ready,
        "source_kind": source_kind,
        "apply_cmd": apply_cmd,
        "invalid_reasons": invalid_reasons,
        "compiled_apply_ready": compiled_apply_ready,
        "apply_session_status": apply_session_status or None,
        "apply_session_error": apply_session_error,
        "pending_apply_staged_at": pending_staged_at,
        "checklist_staged_at": checklist_staged_at,
        "packet_staged_at": packet_staged_at,
        "factory_last_stage_apply": factory_last_stage_apply,
        "stale_against_factory": stale_against_factory,
        "stale_against_phase_runtime": stale_against_phase_runtime,
        "phase_checkpoint_consumed": phase_checkpoint_consumed,
        "checklist_item_statuses": checklist_item_statuses,
        "phase_runtime": phase_runtime_snapshot,
        "latest_phase_dock_error": latest_dock_error or None,
    }


def _phase_driver(repo_root: Path, phase_token: str | None) -> dict[str, Any]:
    pipeline_overnight = importlib.import_module("pipeline_overnight")
    pipeline_advance = importlib.import_module("pipeline_advance")
    status = _safe_mapping(
        pipeline_overnight.overnight_status(
            phase_token=phase_token,
            refresh_mode="auto",
        )
    )
    phase = _safe_mapping(status.get("phase"))
    synth_refresh = _safe_mapping(status.get("synth_refresh"))
    pipeline = _safe_mapping(status.get("pipeline"))
    state_path_rel = _string(pipeline.get("path")) or None
    state_path = _resolve(repo_root, state_path_rel) if state_path_rel else None
    state_payload = _load_json(state_path) if state_path else None
    packet: dict[str, Any] | None = None
    if state_path and state_payload:
        try:
            packet = _safe_mapping(pipeline_advance.build_resume_packet(state_path, state_payload))
        except Exception:
            packet = None

    stage = _string((packet or {}).get("stage") or pipeline.get("stage")) or "missing"
    gate_reason = _string((packet or {}).get("gate_reason") or (state_payload or {}).get("gate_reason")) or "none"
    next_action = _safe_mapping((packet or {}).get("next_action") or pipeline.get("next_action"))
    phase_ref = _string(phase.get("phase_ref") or phase.get("phase_number")) or None
    resume_command = _phase_launch_command(phase_ref)
    if synth_refresh.get("needs_refresh") or pipeline.get("needs_reinit") or not state_path or not state_path.exists():
        next_action = {
            "summary": "Re-arm the active phase so synth refresh and runtime state converge again.",
            "command": resume_command,
        }
    if not state_path or not state_path.exists():
        stage = "no_active_runtime_phase"
        gate_reason = "no_active_runtime_phase"
    attention = _safe_mapping((packet or {}).get("codex_attention") or pipeline.get("attention"))
    review_artifacts = []
    for key in ("resume_json_path", "resume_md_path", "attention_json_path", "attention_md_path"):
        artifact = _string(((packet or {}).get("artifacts") or {}).get(key))
        if artifact:
            review_artifacts.append(artifact)
    blocked = gate_reason not in {"", "none"} or bool(attention.get("pause_pipeline"))

    return {
        "driver_id": "phase_pipeline",
        "label": "Phase pipeline",
        "available": bool(phase),
        "active": stage in PHASE_PROGRESS_STAGES,
        "stage": stage,
        "blocked": blocked,
        "gate_reason": gate_reason if gate_reason not in {"", "none"} else None,
        "next_action": next_action,
        "review_artifacts": review_artifacts,
        "state_path": _relative(repo_root, state_path),
        "last_updated": _string((state_payload or {}).get("updated_at")) or _mtime_iso(state_path),
        "phase_ref": phase_ref,
        "phase_title": _string(phase.get("phase_title")) or None,
        "phase_dir": _string(phase.get("phase_dir")) or _string((state_payload or {}).get("phase_dir")) or None,
        "family_dir": _string(phase.get("family_dir")) or _string((state_payload or {}).get("family_dir")) or None,
        "cycle": (packet or {}).get("cycle") or pipeline.get("cycle"),
        "resume_command": resume_command,
        "needs_synth_refresh": bool(synth_refresh.get("needs_refresh")),
        "needs_reinit": bool(pipeline.get("needs_reinit")),
        "attention": attention,
        "retryable_gate": _retryable_gate(state_payload or {}),
        "packet": packet or {},
        "state_payload": state_payload or {},
    }


def _latest_factory_error_detail(
    factory_payload: Mapping[str, Any] | None,
    *,
    step: str | None = None,
) -> str | None:
    errors = _safe_list((factory_payload or {}).get("errors"))
    for item in reversed(errors):
        if not isinstance(item, Mapping):
            continue
        if step and _string(item.get("step")) != step:
            continue
        detail = _string(item.get("detail"))
        if detail:
            return detail
    return None


def _factory_next_action(
    stage: str,
    *,
    apply_staging: Mapping[str, Any] | None = None,
    phase_resume_command: str | None = None,
    factory_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if stage == "apply_review_pending":
        packet_status = _string((apply_staging or {}).get("packet_status"))
        source_kind = _string((apply_staging or {}).get("source_kind"))
        apply_cmd = _string((apply_staging or {}).get("apply_cmd")) or None
        stale_packet = bool((apply_staging or {}).get("stale_against_factory")) or bool(
            (apply_staging or {}).get("stale_against_phase_runtime")
        )
        invalid_reasons = {
            _string(item)
            for item in _safe_list((apply_staging or {}).get("invalid_reasons"))
            if _string(item)
        }
        latest_phase_dock_error = _safe_mapping((apply_staging or {}).get("latest_phase_dock_error"))
        if "phase_checkpoint_already_assimilated" in invalid_reasons:
            return {
                "summary": (
                    "The staged phase checkpoint packet was already assimilated into the live wave. "
                    "Re-arm the phase pipeline instead of re-reviewing or re-assimilating the stale packet."
                ),
                "command": _string(phase_resume_command) or FACTORY_STAGE_APPLY_COMMAND,
            }
        if "phase_dock_failed_after_packet" in invalid_reasons:
            error_stage = _string(latest_phase_dock_error.get("error_stage")) or "unknown_stage"
            error_category = _string(latest_phase_dock_error.get("error_category")) or "unknown_error"
            return {
                "summary": (
                    "The staged apply packet is invalid because the latest phase-dock run failed at "
                    f"`{error_stage}` (`{error_category}`). Review that dock failure before retrying the phase pipeline or restaging the factory packet."
                ),
                "command": _string(phase_resume_command) or None,
            }
        if (
            packet_status == "invalid_review_packet"
            and "phase_apply_source_missing" in invalid_reasons
            and not stale_packet
            and _string(phase_resume_command)
        ):
            return {
                "summary": "The staged apply packet is invalid because the active phase has not produced an apply-ready session yet. Re-arm the phase pipeline before restaging the factory packet.",
                "command": _string(phase_resume_command),
            }
        return {
            "summary": (
                (
                    "Review the landed phase checkpoint packet before continuing factory work."
                    if source_kind == "phase_dock_response"
                    else "Review the staged apply packet before continuing factory work."
                )
                if packet_status == "review_ready"
                else (
                    "Regenerate the stale staged apply packet through the canonical factory stage-apply step before continuing factory work."
                    if stale_packet
                    else (
                        "Regenerate the invalid staged apply packet through the canonical factory stage-apply step before continuing factory work."
                        if packet_status == "invalid_review_packet"
                        else "Regenerate the missing staged apply packet through the canonical factory stage-apply step before continuing factory work."
                    )
                )
            ),
            "command": apply_cmd if packet_status == "review_ready" and source_kind == "phase_dock_response" else (
                None if packet_status == "review_ready" else FACTORY_STAGE_APPLY_COMMAND
            ),
        }
    if stage in FACTORY_RETRYABLE_STAGES:
        step = FACTORY_RETRYABLE_STAGES[stage]
        latest_error_detail = _latest_factory_error_detail(factory_payload, step=step)
        if (
            stage == "stage_apply_failed"
            and latest_error_detail
            and latest_error_detail.startswith(
                "no compiled apply-ready observe session found for active phase "
            )
            and _string(phase_resume_command)
        ):
            return {
                "summary": "The last stage-apply attempt failed because the active phase has not produced an apply-ready session yet. Re-arm the phase pipeline before restaging the factory packet.",
                "command": _string(phase_resume_command),
            }
        return {
            "summary": f"Retry the failed factory step `{step}`.",
            "command": f"./repo-python tools/meta/factory/factory_runner.py --step {step} --provider chatgpt",
        }
    step = FACTORY_STAGE_TO_NEXT_STEP.get(stage, "materialize")
    return {
        "summary": f"Advance the factory lane through its next bounded step (`{step}`).",
        "command": _factory_advance_command(),
    }


def _factory_driver(
    repo_root: Path,
    apply_staging: Mapping[str, Any],
    *,
    phase_resume_command: str | None = None,
) -> dict[str, Any]:
    state_path = _resolve(repo_root, FACTORY_STATE_REL)
    payload = _load_json(state_path) or {}
    stage = _string(payload.get("stage")) or "missing"
    invalid_reasons = {
        _string(item)
        for item in _safe_list(apply_staging.get("invalid_reasons"))
        if _string(item)
    }
    phase_checkpoint_consumed = "phase_checkpoint_already_assimilated" in invalid_reasons
    review_artifacts: list[str] = []
    for key in ("pending_apply", "checklist_json", "checklist_md"):
        artifact = _safe_mapping(apply_staging.get(key))
        path = _string(artifact.get("path"))
        if path and bool(artifact.get("exists")):
            review_artifacts.append(path)
    blocked = (stage == "apply_review_pending" and not phase_checkpoint_consumed) or stage.endswith("_failed")
    gate_reason = None
    if stage == "apply_review_pending":
        if phase_checkpoint_consumed:
            gate_reason = "phase_runtime_rearm_required"
        else:
            gate_reason = (
                "phase_checkpoint_review_pending"
                if bool(apply_staging.get("review_ready")) and _string(apply_staging.get("source_kind")) == "phase_dock_response"
                else "apply_review_pending"
            )
    elif stage.endswith("_failed"):
        gate_reason = "factory_step_failed"
    return {
        "driver_id": "factory_lane",
        "label": "Factory lane",
        "available": state_path.exists(),
        "active": stage in FACTORY_ACTIVE_STAGES,
        "stage": stage,
        "blocked": blocked,
        "gate_reason": gate_reason,
        "next_action": _factory_next_action(
            stage,
            apply_staging=apply_staging,
            phase_resume_command=phase_resume_command,
            factory_payload=payload,
        ),
        "review_artifacts": review_artifacts if stage == "apply_review_pending" and not phase_checkpoint_consumed else [],
        "state_path": _relative(repo_root, state_path),
        "last_updated": _string(payload.get("last_stage_apply") or payload.get("last_run")) or _mtime_iso(state_path),
        "jobs_completed": list(payload.get("jobs_completed") or []),
        "errors": list(payload.get("errors") or []),
        "state_payload": payload,
    }


def _mission_driver(repo_root: Path) -> dict[str, Any]:
    state_path = _resolve(repo_root, MISSION_SESSION_REL)
    payload = _load_json(state_path) or {}
    queue = payload.get("queue") if isinstance(payload.get("queue"), list) else []
    cursor = max(0, int(payload.get("cursor") or 0))
    active_item = queue[cursor] if cursor < len(queue) and isinstance(queue[cursor], dict) else None
    runs_remaining = 0
    if active_item:
        try:
            runs_remaining = max(0, int(active_item.get("runs_remaining", active_item.get("repeat_remaining", 0)) or 0))
        except (TypeError, ValueError):
            runs_remaining = 0
    active = bool(active_item) and runs_remaining > 0
    stage = "active" if active else ("complete" if queue and cursor >= len(queue) else "idle")
    return {
        "driver_id": "mission_queue",
        "label": "Mission queue",
        "available": state_path.exists(),
        "active": active,
        "stage": stage,
        "blocked": False,
        "gate_reason": None,
        "next_action": {
            "summary": "Advance one mission task from the curated queue.",
            "command": _mission_step_command() if active else None,
        },
        "review_artifacts": [],
        "state_path": _relative(repo_root, state_path),
        "last_updated": _string(payload.get("updated_at")) or _mtime_iso(state_path),
        "mission_id": payload.get("mission_id"),
        "queue_len": len(queue),
        "cursor": cursor,
        "runs_remaining": runs_remaining,
        "active_item": active_item,
        "state_payload": payload,
    }


def _phase_driver_has_runnable_next_action(
    phase_driver: Mapping[str, Any],
    phase_next: Mapping[str, Any],
) -> bool:
    next_command = _string(phase_next.get("command"))
    if not next_command:
        return False
    if next_command == _string(phase_driver.get("resume_command")):
        return False
    if bool(phase_driver.get("needs_synth_refresh")) or bool(phase_driver.get("needs_reinit")):
        return False
    if _string(phase_driver.get("stage")) not in PHASE_PROGRESS_STAGES:
        return False
    if bool(phase_driver.get("retryable_gate")):
        return False
    attention = _safe_mapping(phase_driver.get("attention"))
    if bool(attention.get("needs_attention")) and bool(attention.get("pause_pipeline")):
        return False
    return True


def _doc_follow_up(factory_driver: Mapping[str, Any], docs_snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if _string(factory_driver.get("stage")) == "apply_review_pending" and _string(factory_driver.get("gate_reason")) != "phase_runtime_rearm_required":
        return {
            "mode": "manual_documentation",
            "launch_recommended_now": False,
            "summary": (
                "Lock the checkpoint-review decision in docs/orchestration_state.md after the active gate is cleared."
                if _string(factory_driver.get("gate_reason")) == "phase_checkpoint_review_pending"
                else "Lock the decision in docs/orchestration_state.md after the active approval gate is cleared."
            ),
            "primary_surface": "docs/orchestration_state.md",
            "command": None,
            "archetype": "C",
        }
    if bool(docs_snapshot.get("raw_seed_newer_than_docs")):
        return {
            "mode": "manual_documentation",
            "launch_recommended_now": False,
            "summary": "Fold the latest raw-seed pressure into one bounded documentation pass instead of another ad hoc runtime branch.",
            "primary_surface": "docs/raw_seed_overnight_intent_and_operator_queue.md",
            "command": None,
            "archetype": "B",
        }
    return {
        "mode": "manual_documentation",
        "launch_recommended_now": False,
        "summary": "Strengthen one canonical runtime/control doc instead of creating another thin note.",
        "primary_surface": "docs/raw_seed_doctrine_derivation.md",
        "command": None,
        "archetype": "D",
    }


def _build_decision(
    *,
    phase_driver: Mapping[str, Any],
    factory_driver: Mapping[str, Any],
    mission_driver: Mapping[str, Any],
    apply_staging: Mapping[str, Any],
    docs_snapshot: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    sequence: list[dict[str, Any]] = []
    live_locks = list(bridge_snapshot.get("live_locks") or [])
    phase_next = _safe_mapping(phase_driver.get("next_action"))
    phase_resume_command = _string(phase_driver.get("resume_command")) or _string(phase_next.get("command")) or None
    factory_next = _safe_mapping(factory_driver.get("next_action"))
    mission_next = _safe_mapping(mission_driver.get("next_action"))

    if live_locks:
        providers = ", ".join(
            sorted(_string(lock.get("provider")) for lock in live_locks if _string(lock.get("provider")))
        )
        sequence.append(
            {
                "mode": "wait_existing_bridge",
                "launch_recommended_now": False,
                "summary": f"A bridge run already owns provider lock(s): {providers or 'unknown'}.",
                "command": None,
            }
        )
        return "wait_existing_bridge", sequence[0], sequence

    if _string(phase_driver.get("gate_reason")) == "no_active_runtime_phase":
        bootstrap = {
            "mode": "no_active_runtime_phase",
            "launch_recommended_now": False,
            "summary": "No non-deprecated phase runtime is armed. Bootstrap the active 09.x line explicitly instead of reviving legacy pipeline residue.",
            "command": _string(phase_next.get("command")) or None,
        }
        sequence.append(bootstrap)
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "no_active_runtime_phase", bootstrap, sequence

    if _string(factory_driver.get("stage")) == "apply_review_pending":
        review_ready = bool(apply_staging.get("review_ready"))
        packet_status = _string(apply_staging.get("packet_status"))
        source_kind = _string(apply_staging.get("source_kind"))
        apply_cmd = _string(apply_staging.get("apply_cmd")) or None
        stale_packet = bool(apply_staging.get("stale_against_factory")) or bool(
            apply_staging.get("stale_against_phase_runtime")
        )
        invalid_reasons = {
            _string(item)
            for item in _safe_list(apply_staging.get("invalid_reasons"))
            if _string(item)
        }
        phase_checkpoint_consumed = "phase_checkpoint_already_assimilated" in invalid_reasons
        checklist_md = _safe_mapping(apply_staging.get("checklist_md"))
        latest_phase_dock_error = _safe_mapping(apply_staging.get("latest_phase_dock_error"))
        latest_dock_status = _safe_mapping(_safe_mapping(apply_staging.get("phase_runtime")).get("latest_dock_status"))
        phase_dock_failed = "phase_dock_failed_after_packet" in invalid_reasons
        review_path = (
            _string(latest_dock_status.get("path"))
            if phase_dock_failed and _string(latest_dock_status.get("path"))
            else (checklist_md.get("path") if checklist_md.get("exists") else None)
        )
        if phase_checkpoint_consumed:
            if _phase_driver_has_runnable_next_action(phase_driver, phase_next):
                live_phase_summary = _string(phase_next.get("summary")) or "Continue the current phase-pipeline action."
                follow_live_phase = {
                    "mode": "phase_pipeline",
                    "launch_recommended_now": True,
                    "summary": (
                        "The staged phase checkpoint packet was already assimilated into the live wave. "
                        f"Use the live phase-pipeline action instead of re-reviewing or re-arming stale checkpoint artifacts: {live_phase_summary}"
                    ),
                    "command": _string(phase_next.get("command")),
                }
                sequence.append(follow_live_phase)
                sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
                return "phase_pipeline", follow_live_phase, sequence
            rearm = {
                "mode": "phase_pipeline",
                "launch_recommended_now": True,
                "summary": (
                    "The staged phase checkpoint packet was already assimilated into the live wave. "
                    "Re-arm the phase pipeline instead of re-reviewing the stale checkpoint packet."
                ),
                "command": phase_resume_command or _string((phase_next or {}).get("command")) or FACTORY_STAGE_APPLY_COMMAND,
            }
            sequence.append(rearm)
            sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
            return "phase_pipeline", rearm, sequence
        manual_review = {
            "mode": "manual_review",
            "launch_recommended_now": False,
            "summary": (
                (
                    "Factory stopped at phase-checkpoint review. Review the landed phase_dock packet before any new unattended work."
                    if source_kind == "phase_dock_response"
                    else "Factory stopped at apply_review_pending. Review the staged packet before any new unattended work."
                )
                if review_ready
                else (
                    (
                        "Factory claims apply_review_pending, but the latest phase-dock run failed at "
                        f"`{_string(latest_phase_dock_error.get('error_stage')) or 'unknown_stage'}` "
                        f"(`{_string(latest_phase_dock_error.get('error_category')) or 'unknown_error'}`). "
                        "Review that dock failure before retrying the phase pipeline or restaging the factory packet."
                    )
                    if phase_dock_failed
                    else (
                        "Factory claims apply_review_pending, but the staged packet has no phase-local apply source yet. Re-arm the phase pipeline before restaging the factory packet."
                        if (
                            packet_status == "invalid_review_packet"
                            and "phase_apply_source_missing" in invalid_reasons
                            and not stale_packet
                            and phase_resume_command
                        )
                        else (
                            "Factory claims apply_review_pending, but the staged packet is stale. Regenerate it through the canonical factory stage-apply step before arming anything else."
                            if stale_packet
                            else (
                                "Factory claims apply_review_pending, but the staged packet is invalid. Regenerate it through the canonical factory stage-apply step before arming anything else."
                                if packet_status == "invalid_review_packet"
                                else "Factory claims apply_review_pending, but the staged checklist is missing. Regenerate it through the canonical factory stage-apply step before arming anything else."
                            )
                        )
                    )
                )
            ),
            "path": review_path,
            "command": (
                apply_cmd
                if review_ready and source_kind == "phase_dock_response"
                else (
                    None
                    if review_ready
                    else (
                        phase_resume_command
                        if phase_dock_failed and phase_resume_command
                        else (
                            phase_resume_command
                            if (
                                packet_status == "invalid_review_packet"
                                and "phase_apply_source_missing" in invalid_reasons
                                and not stale_packet
                                and phase_resume_command
                            )
                            else FACTORY_STAGE_APPLY_COMMAND
                        )
                    )
                )
            ),
        }
        sequence.append(manual_review)
        if _string(phase_driver.get("stage")) in PHASE_PROGRESS_STAGES or phase_driver.get("needs_synth_refresh") or phase_driver.get("needs_reinit"):
            sequence.append(
                {
                    "mode": "phase_pipeline",
                    "launch_recommended_now": True,
                    "summary": "After the active gate clears, phase-native runtime is the next machine lane because it keeps synth refresh, observe routing, and gate posture in one authority.",
                    "command": phase_resume_command or phase_next.get("command"),
                }
            )
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "manual_review", manual_review, sequence

    if bool(phase_driver.get("retryable_gate")) and _string(phase_next.get("command")):
        retry_gate = {
            "mode": "phase_pipeline",
            "launch_recommended_now": True,
            "summary": "The active phase is blocked only by a retryable controller gate. Clear it through the canonical retry path before starting any alternate lane.",
            "command": phase_next.get("command"),
        }
        sequence.append(retry_gate)
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "phase_pipeline", retry_gate, sequence

    attention = _safe_mapping(phase_driver.get("attention"))
    if bool(attention.get("needs_attention")) and bool(attention.get("pause_pipeline")):
        manual_review = {
            "mode": "manual_review",
            "launch_recommended_now": False,
            "summary": _string(attention.get("summary")) or "The active phase asked for manual review before another expensive cycle.",
            "command": _string(attention.get("gate_command")) or None,
        }
        sequence.append(manual_review)
        if bool(mission_driver.get("active")):
            sequence.append(
                {
                    "mode": "mission_queue",
                    "launch_recommended_now": True,
                    "summary": "If the phase stays deliberately blocked, the curated mission queue is the cleanest alternate unattended lane.",
                    "command": mission_next.get("command"),
                }
            )
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "manual_review", manual_review, sequence

    if bool(mission_driver.get("active")) and _string(mission_next.get("command")):
        mission = {
            "mode": "mission_queue",
            "launch_recommended_now": True,
            "summary": "An explicit mission queue exists, so use that curated lane instead of inventing another overnight branch.",
            "command": mission_next.get("command"),
        }
        sequence.append(mission)
        if _string(phase_driver.get("stage")) in PHASE_PROGRESS_STAGES or phase_driver.get("needs_synth_refresh") or phase_driver.get("needs_reinit"):
            sequence.append(
                {
                    "mode": "phase_pipeline",
                    "launch_recommended_now": False,
                    "summary": "Keep the phase runtime as the next lane after the mission queue completes; do not interleave both in one unattended window.",
                    "command": phase_next.get("command"),
                }
            )
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "mission_queue", mission, sequence

    if (
        (_string(phase_driver.get("stage")) in PHASE_PROGRESS_STAGES)
        or bool(phase_driver.get("needs_synth_refresh"))
        or bool(phase_driver.get("needs_reinit"))
    ) and _string(phase_next.get("command")):
        phase = {
            "mode": "phase_pipeline",
            "launch_recommended_now": True,
            "summary": (
                "The active phase is the primary lane because it keeps synth refresh, observe routing, and gate posture in one authority surface."
            ),
            "command": phase_next.get("command"),
        }
        sequence.append(phase)
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "phase_pipeline", phase, sequence

    if bool(factory_driver.get("active")) and _string(factory_next.get("command")):
        factory = {
            "mode": "factory_lane",
            "launch_recommended_now": True,
            "summary": "Factory state is mid-lane, so advance that DAG instead of starting a different runtime.",
            "command": factory_next.get("command"),
        }
        sequence.append(factory)
        sequence.append(_doc_follow_up(factory_driver, docs_snapshot))
        return "factory_lane", factory, sequence

    fallback = _doc_follow_up(factory_driver, docs_snapshot)
    sequence.append(fallback)
    return "manual_documentation", fallback, sequence


def _build_gate(
    *,
    active_driver: str,
    decision: Mapping[str, Any],
    phase_driver: Mapping[str, Any],
    factory_driver: Mapping[str, Any],
    mission_driver: Mapping[str, Any],
    apply_staging: Mapping[str, Any],
    bridge_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    if int(bridge_snapshot.get("live_count") or 0) > 0:
        return {
            "active": True,
            "gate_reason": "bridge_lock_owned",
            "owner_driver": "external_bridge",
            "review_ready": False,
            "command": None,
        }
    if _string(phase_driver.get("gate_reason")) == "no_active_runtime_phase":
        return {
            "active": True,
            "gate_reason": "no_active_runtime_phase",
            "owner_driver": "no_active_runtime_phase",
            "review_ready": False,
            "command": _string(((phase_driver.get("next_action") or {}) if isinstance(phase_driver.get("next_action"), Mapping) else {}).get("command")) or None,
        }
    if _string(factory_driver.get("stage")) == "apply_review_pending":
        packet_status = _string(apply_staging.get("packet_status"))
        invalid_reasons = {
            _string(item)
            for item in _safe_list(apply_staging.get("invalid_reasons"))
            if _string(item)
        }
        if "phase_checkpoint_already_assimilated" in invalid_reasons:
            phase_next = _safe_mapping(phase_driver.get("next_action"))
            if _phase_driver_has_runnable_next_action(phase_driver, phase_next):
                return {
                    "active": False,
                    "gate_reason": None,
                    "owner_driver": active_driver,
                    "review_ready": False,
                    "command": None,
                }
            return {
                "active": True,
                "gate_reason": "phase_runtime_rearm_required",
                "owner_driver": "phase_pipeline",
                "review_ready": False,
                "command": _string(((phase_driver.get("next_action") or {}) if isinstance(phase_driver.get("next_action"), Mapping) else {}).get("command")) or None,
            }
        return {
            "active": True,
            "gate_reason": (
                (
                    "phase_checkpoint_review_pending"
                    if _string(apply_staging.get("source_kind")) == "phase_dock_response"
                    else "apply_review_pending"
                )
                if packet_status == "review_ready"
                else (packet_status or "missing_review_packet")
            ),
            "owner_driver": "factory_lane",
            "review_ready": bool(apply_staging.get("review_ready")),
            "command": _string(decision.get("command")) or None,
        }
    if bool(phase_driver.get("retryable_gate")):
        return {
            "active": True,
            "gate_reason": _string(phase_driver.get("gate_reason")) or "retryable_phase_gate",
            "owner_driver": "phase_pipeline",
            "review_ready": False,
            "command": _string(((phase_driver.get("next_action") or {}) if isinstance(phase_driver.get("next_action"), Mapping) else {}).get("command")) or None,
        }
    attention = _safe_mapping(phase_driver.get("attention"))
    if bool(attention.get("needs_attention")) and bool(attention.get("pause_pipeline")):
        return {
            "active": True,
            "gate_reason": _string(phase_driver.get("gate_reason")) or _string(attention.get("reason_key")) or "phase_attention_gate",
            "owner_driver": "phase_pipeline",
            "review_ready": False,
            "command": _string(attention.get("gate_command")) or None,
        }
    return {
        "active": False,
        "gate_reason": None,
        "owner_driver": active_driver,
        "review_ready": False,
        "command": _string(decision.get("command")) or None,
    }


def build_orchestration_state(
    *,
    repo_root: Path = REPO_ROOT,
    phase_token: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Synthesize the current control-plane authority snapshot from the live phase, factory, mission, documentation, and bridge surfaces.
    - Mechanism: Load each lane snapshot, choose the active driver and gate, build coordination metadata and human surfaces, then return one orchestration_state payload without persisting it.
    - Reads: _phase_driver(), _load_apply_staging_snapshot(), _factory_driver(), _mission_driver(), _load_documentation_snapshot(), _load_bridge_snapshot(), _build_decision(), _build_gate(), and _build_coordination().
    - Guarantee: Returns an orchestration_state_v1 mapping with decision, gate, drivers, coordination, artifacts, and source_snapshots populated from disk-backed runtime inputs.
    - Fails: Propagates import or runtime errors from the underlying lane loaders when those authority surfaces cannot be materialized.
    - When-needed: Open when a caller needs the authoritative in-memory orchestration snapshot before writing artifacts or deciding which lane owns the next action.
    - Escalates-to: system/control/orchestration.py::write_orchestration_artifacts; docs/orchestration_state.md
    - Navigation-group: server_control
    """
    phase_driver = _phase_driver(repo_root, phase_token)
    phase_runtime = _load_phase_runtime_snapshot(repo_root, phase_driver)
    apply_staging = _load_apply_staging_snapshot(
        repo_root,
        _string(phase_driver.get("phase_dir")) or None,
        phase_runtime=phase_runtime,
    )
    phase_resume_command = (
        _string(phase_driver.get("resume_command"))
        or _string(_safe_mapping(phase_driver.get("next_action")).get("command"))
        or None
    )
    factory_driver = _factory_driver(
        repo_root,
        apply_staging,
        phase_resume_command=phase_resume_command,
    )
    mission_driver = _mission_driver(repo_root)
    docs_snapshot = _load_documentation_snapshot(repo_root, _string(phase_driver.get("family_dir")) or None)
    bridge_snapshot = _load_bridge_snapshot(repo_root)
    active_driver, immediate, sequence = _build_decision(
        phase_driver=phase_driver,
        factory_driver=factory_driver,
        mission_driver=mission_driver,
        apply_staging=apply_staging,
        docs_snapshot=docs_snapshot,
        bridge_snapshot=bridge_snapshot,
    )
    decision_payload = {
        "immediate_mode": _string(immediate.get("mode")) or active_driver,
        "summary": _string(immediate.get("summary")) or "",
        "command": _string(immediate.get("command")) or None,
        "launch_recommended_now": bool(immediate.get("launch_recommended_now")),
        "sequence": sequence,
    }
    gate = _build_gate(
        active_driver=active_driver,
        decision=immediate,
        phase_driver=phase_driver,
        factory_driver=factory_driver,
        mission_driver=mission_driver,
        apply_staging=apply_staging,
        bridge_snapshot=bridge_snapshot,
    )
    state_path = _resolve(repo_root, ORCHESTRATION_STATE_REL)
    brief_json_path = _resolve(repo_root, ORCHESTRATION_BRIEF_JSON_REL)
    brief_md_path = _resolve(repo_root, ORCHESTRATION_BRIEF_MD_REL)
    event_log_path = _resolve(repo_root, ORCHESTRATION_EVENT_LOG_REL)
    human_surface = {
        "primary_surface": "run_control_room.py",
        "primary_command": CONTROL_ROOM_COMMAND,
        "observe_surface": "run_observe.py",
        "observe_command": OBSERVE_ROOM_COMMAND,
        "recommended_review_surface": (
            _string((sequence[0] or {}).get("path")) if sequence else None
        ) or "docs/orchestration_state.md",
    }
    coordination = _build_coordination(
        repo_root=repo_root,
        active_driver=active_driver,
        decision=decision_payload,
        gate=gate,
        human_surface=human_surface,
        phase_driver=phase_driver,
        factory_driver=factory_driver,
        mission_driver=mission_driver,
        bridge_snapshot=bridge_snapshot,
    )
    agent_actions = [
        {
            "mode": _string(step.get("mode")) or "unknown",
            "summary": _string(step.get("summary")) or "",
            "command": _string(step.get("command")) or None,
            "launch_recommended_now": bool(step.get("launch_recommended_now")),
            "path": _string(step.get("path")) or _string(step.get("primary_surface")) or None,
        }
        for step in sequence
    ]
    reactions = reactions_runtime.build_reactions_orchestration_projection(repo_root)
    python_std_compliance = _load_python_std_compliance_projection(repo_root)
    return {
        "kind": "orchestration_state",
        "schema_version": "orchestration_state_v1",
        "active_driver": active_driver,
        "decision": decision_payload,
        "gate": gate,
        "drivers": [
            {k: v for k, v in phase_driver.items() if k not in {"packet", "state_payload"}},
            {k: v for k, v in factory_driver.items() if k not in {"state_payload"}},
            {k: v for k, v in mission_driver.items() if k not in {"state_payload"}},
        ],
        "reactions": reactions,
        "python_std_compliance": python_std_compliance,
        "agent_actions": agent_actions,
        "human_surface": human_surface,
        "coordination": coordination,
        "artifacts": {
            "state_path": _relative(repo_root, state_path),
            "brief_json_path": _relative(repo_root, brief_json_path),
            "brief_markdown_path": _relative(repo_root, brief_md_path),
            "event_log_path": _relative(repo_root, event_log_path),
            "apply_staging": apply_staging,
            "phase_runtime": phase_runtime,
            "documentation": docs_snapshot,
            "bridge": bridge_snapshot,
        },
        "updated_at": _utc_now(),
        "source_snapshots": {
            "phase_pipeline": phase_driver,
            "phase_runtime": phase_runtime,
            "factory_lane": factory_driver,
            "mission_queue": mission_driver,
        },
    }


def build_orchestration_brief(state: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Project the full orchestration authority state into the smaller JSON brief surface consumed by docs and control-room summaries.
    - Mechanism: Copy the provided state, relabel kind, stamp projection metadata, and drop source_snapshots so the brief stays lightweight.
    - Reads: The caller-provided orchestration state mapping and _utc_now().
    - Guarantee: Returns an orchestration_brief mapping that points back to ORCHESTRATION_STATE_REL as its authority surface.
    - Fails: None.
    - When-needed: Open when a caller already has the full orchestration state and needs the compact JSON projection that feeds the markdown brief.
    - Escalates-to: system/control/orchestration.py::render_orchestration_brief; tools/meta/control/orchestration_brief.json
    """
    payload = dict(state)
    payload["kind"] = "orchestration_brief"
    payload["authority_state_path"] = ORCHESTRATION_STATE_REL
    payload["projection_generated_at"] = _utc_now()
    payload.pop("source_snapshots", None)
    return payload


def render_orchestration_brief(brief: Mapping[str, Any]) -> str:
    """
    [ACTION]
    - Teleology: Render the operator-facing markdown brief from the compact orchestration brief payload.
    - Mechanism: Pull decision, gate, coordination, and driver fields from the mapping and format them into the canonical `# Orchestration Brief` markdown layout.
    - Reads: The caller-provided brief mapping plus helper normalizers such as _safe_mapping(), _string(), and _safe_list()-derived fields.
    - Guarantee: Returns markdown ending with a trailing newline and preserving the canonical sections for drivers, actor frames, and sequence when present.
    - Fails: None.
    - When-needed: Open when a caller needs the human-readable projection written to tools/meta/control/orchestration_brief.md.
    - Escalates-to: tools/meta/control/orchestration_brief.md; system/control/orchestration.py::build_orchestration_brief
    """
    decision = _safe_mapping(brief.get("decision"))
    gate = _safe_mapping(brief.get("gate"))
    event_log = _safe_mapping(brief.get("event_log"))
    coordination = _safe_mapping(brief.get("coordination"))
    docs_route_focus = _safe_mapping(coordination.get("docs_route_focus"))
    active_directive = _safe_mapping(coordination.get("active_directive"))
    next_handoff = _safe_mapping(coordination.get("next_handoff"))
    reactions = _safe_mapping(brief.get("reactions"))
    python_std_compliance = _safe_mapping(brief.get("python_std_compliance"))
    drivers = brief.get("drivers") if isinstance(brief.get("drivers"), list) else []
    lines = [
        "# Orchestration Brief",
        "",
        f"- Authority: `{_string(brief.get('authority_state_path')) or ORCHESTRATION_STATE_REL}`",
        f"- Generated: `{_string(brief.get('projection_generated_at') or brief.get('updated_at'))}`",
        f"- Active driver: `{_string(brief.get('active_driver')) or 'unknown'}`",
        f"- Immediate mode: `{_string(decision.get('immediate_mode')) or 'unknown'}`",
        f"- Launch now: `{'yes' if bool(decision.get('launch_recommended_now')) else 'no'}`",
    ]
    if gate.get("active"):
        lines.append(
            f"- Active gate: `{_string(gate.get('gate_reason'))}` owned by `{_string(gate.get('owner_driver')) or 'unknown'}`"
        )
    if event_log.get("latest_event_id"):
        lines.append(f"- Latest event: `{_string(event_log.get('latest_event_id'))}`")
    human_surface = _safe_mapping(brief.get("human_surface"))
    if human_surface.get("primary_command"):
        lines.append(f"- Control room: `{human_surface.get('primary_command')}`")
    if docs_route_focus.get("active_preset_id"):
        lines.append(
            f"- Docs-route focus: `{_string(docs_route_focus.get('active_preset_id'))}`"
        )
    if bool(active_directive.get("active")):
        lines.append(
            "- Active directive: "
            f"`{_string(active_directive.get('task') or active_directive.get('summary')) or 'active'}`"
        )
    if next_handoff.get("actor_id") or next_handoff.get("mode"):
        lines.append(
            "- Next handoff: "
            f"`{_string(next_handoff.get('actor_id')) or 'unknown'}` via `{_string(next_handoff.get('mode')) or 'unknown'}`"
        )
    if reactions:
        lines.append(
            f"- Reactions engine: `{'armed' if bool(reactions.get('engine_armed')) else 'disarmed'}` / "
            f"`{_string(reactions.get('engine_status')) or 'unknown'}`"
        )
        liveness = _safe_mapping(reactions.get("liveness"))
        if liveness.get("last_event_at"):
            lines.append(f"  last_event=`{_string(liveness.get('last_event_at'))}`")
        if reactions.get("recovery_command"):
            lines.append(f"- Reactions recovery: `{_string(reactions.get('recovery_command'))}`")
        barriers = reactions.get("awaiting_barriers") if isinstance(reactions.get("awaiting_barriers"), list) else []
        if barriers:
            lines.append(f"- Wake barriers: `{len(barriers)}` active")
    if python_std_compliance:
        counts = _safe_mapping(python_std_compliance.get("counts"))
        lines.append(
            f"- Python std compliance: stage `{_string(python_std_compliance.get('stage')) or 'unknown'}` / "
            f"gate `{_string(python_std_compliance.get('gate')) or 'unknown'}` / "
            f"unapplied `{_safe_int(counts.get('findings_unapplied'))}` / "
            f"pending bins `{_safe_int(counts.get('bins_pending'))}`"
        )
        approval_needed = _safe_mapping(python_std_compliance.get("approval_needed"))
        if bool(approval_needed.get("required")):
            lines.append(
                f"- Python std approval: `{_string(approval_needed.get('campaign_summary_path')) or 'unknown campaign'}`"
            )
            if approval_needed.get("command"):
                lines.append(f"- Python std approve command: `{approval_needed.get('command')}`")
        elif python_std_compliance.get("blocked_reason"):
            lines.append(
                f"- Python std blocked: `{_string(python_std_compliance.get('blocked_reason'))}`"
            )

    lines.extend(["", "## Drivers", ""])
    for driver in drivers:
        if not isinstance(driver, Mapping):
            continue
        lines.append(
            f"- `{_string(driver.get('driver_id'))}`: stage `{_string(driver.get('stage')) or 'unknown'}`, "
            f"blocked `{bool(driver.get('blocked'))}`, next `{_string((_safe_mapping(driver.get('next_action'))).get('command')) or 'none'}`"
        )

    actor_frames = coordination.get("actor_frames") if isinstance(coordination.get("actor_frames"), Mapping) else {}
    if actor_frames:
        lines.extend(["", "## Actor Frames", ""])
        for actor_id, frame in actor_frames.items():
            if not isinstance(frame, Mapping):
                continue
            lines.append(
                f"- `{_string(actor_id)}`: status `{_string(frame.get('status')) or 'unknown'}`, "
                f"surface `{_string(frame.get('runtime_surface_id')) or 'n/a'}`"
            )

    lines.extend(["", "## Sequence", ""])
    for index, step in enumerate(decision.get("sequence") or [], start=1):
        if not isinstance(step, Mapping):
            continue
        lines.append(f"{index}. `{_string(step.get('mode')) or 'unknown'}` — {_string(step.get('summary')) or 'No summary.'}")
        command = _string(step.get("command"))
        path = _string(step.get("path") or step.get("primary_surface"))
        if command:
            lines.append(f"   Command: `{command}`")
        if path:
            lines.append(f"   Path: `{path}`")
    return "\n".join(lines).rstrip() + "\n"


def write_orchestration_artifacts(
    *,
    repo_root: Path = REPO_ROOT,
    phase_token: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Refresh every persisted orchestration artifact in one bounded write pass so the control room, docs, and event log all share one authority update.
    - Mechanism: Build the current state, compare its event fingerprint with the latest JSONL record, append a new event only when the core changed, then rewrite the state JSON, brief JSON, and brief markdown.
    - Reads: build_orchestration_state(), prior orchestration_state.json, the latest orchestration_events.jsonl record, and build_orchestration_brief()/render_orchestration_brief().
    - Writes: ORCHESTRATION_STATE_REL, ORCHESTRATION_BRIEF_JSON_REL, ORCHESTRATION_BRIEF_MD_REL, and ORCHESTRATION_EVENT_LOG_REL when the event fingerprint changed.
    - Guarantee: Returns the refreshed state, brief, resolved artifact paths, and the event record that now anchors the persisted control-plane snapshot.
    - Fails: Propagates filesystem and serialization errors when the authority artifacts cannot be written.
    - When-needed: Open when the control plane needs one canonical refresh of state, brief, and event-log artifacts before any human or agent reads them.
    - Escalates-to: tools/meta/control/orchestration_state.json; tools/meta/control/orchestration_events.jsonl; docs/orchestration_state.md
    - Navigation-group: server_control
    """
    state = build_orchestration_state(repo_root=repo_root, phase_token=phase_token)
    state_path = _resolve(repo_root, ORCHESTRATION_STATE_REL)
    brief_json_path = _resolve(repo_root, ORCHESTRATION_BRIEF_JSON_REL)
    brief_md_path = _resolve(repo_root, ORCHESTRATION_BRIEF_MD_REL)
    event_log_path = _resolve(repo_root, ORCHESTRATION_EVENT_LOG_REL)
    previous_state = _load_json(state_path) or {}
    last_event = _load_last_jsonl_record(event_log_path) or {}
    event_core = _orchestration_event_core(state)
    event_fingerprint = _orchestration_event_fingerprint(event_core)
    previous_fingerprint = _string(last_event.get("event_fingerprint"))
    if not previous_fingerprint:
        previous_event_log = _safe_mapping(previous_state.get("event_log"))
        previous_fingerprint = _string(previous_event_log.get("latest_event_fingerprint"))
    appended_event = False
    if event_fingerprint != previous_fingerprint:
        event_record = dict(event_core)
        event_record["event_fingerprint"] = event_fingerprint
        event_record["event_id"] = _event_id(_string(event_core.get("recorded_at")) or _utc_now(), event_fingerprint)
        _append_jsonl_record(event_log_path, event_record)
        appended_event = True
    else:
        event_record = dict(last_event) if last_event else dict(event_core)
        if "event_fingerprint" not in event_record:
            event_record["event_fingerprint"] = event_fingerprint
        if "event_id" not in event_record:
            event_record["event_id"] = _event_id(_string(event_core.get("recorded_at")) or _utc_now(), event_fingerprint)

    state["event_log"] = {
        "path": _relative(repo_root, event_log_path),
        "latest_event_id": _string(event_record.get("event_id")) or None,
        "latest_event_fingerprint": _string(event_record.get("event_fingerprint")) or None,
        "last_appended_at": _string(event_record.get("recorded_at")) or None,
        "appended": appended_event,
    }
    brief = build_orchestration_brief(state)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    brief_json_path.write_text(json.dumps(brief, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    brief_md_path.write_text(render_orchestration_brief(brief), encoding="utf-8")
    return {
        "state": state,
        "brief": brief,
        "state_path": _relative(repo_root, state_path),
        "brief_json_path": _relative(repo_root, brief_json_path),
        "brief_markdown_path": _relative(repo_root, brief_md_path),
        "event_log_path": _relative(repo_root, event_log_path),
        "event": event_record,
        "event_appended": appended_event,
    }


def load_orchestration_state(
    *,
    repo_root: Path = REPO_ROOT,
    refresh: bool = False,
    phase_token: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Provide callers with the current orchestration authority state, reusing the persisted snapshot when it is allowed to be stale.
    - Mechanism: Read ORCHESTRATION_STATE_REL when refresh is false and a valid payload exists; otherwise regenerate artifacts through write_orchestration_artifacts() and return the new state.
    - Reads: tools/meta/control/orchestration_state.json via _load_json() and write_orchestration_artifacts() when regeneration is required.
    - Guarantee: Returns an orchestration_state mapping either from disk cache or from a fresh artifact refresh.
    - Fails: Propagates write_orchestration_artifacts() failures when refresh is requested or the cached state is missing/invalid.
    - When-needed: Open when a caller needs the authoritative orchestration state but only sometimes needs to pay the cost of a full refresh.
    - Escalates-to: system/control/orchestration.py::write_orchestration_artifacts; tools/meta/control/orchestration_state.json
    """
    state_path = _resolve(repo_root, ORCHESTRATION_STATE_REL)
    if not refresh:
        payload = _load_json(state_path)
        if payload:
            if phase_token or _cached_orchestration_active_phase_mismatch(repo_root, payload):
                return build_orchestration_state(repo_root=repo_root, phase_token=phase_token)
            return payload
    return write_orchestration_artifacts(repo_root=repo_root, phase_token=phase_token)["state"]


def selected_action(state: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Collapse the orchestration state to the single next agent action that most callers should execute or display.
    - Mechanism: Prefer the first agent_actions row when present; otherwise synthesize a fallback action from decision.immediate_mode, summary, command, and launch flag.
    - Reads: The caller-provided orchestration state mapping.
    - Guarantee: Returns a dict containing mode, summary, command, and launch_recommended_now for the current top-priority step.
    - Fails: None.
    - When-needed: Open when a caller needs one executable next step without walking the full orchestration sequence.
    - Escalates-to: system/control/orchestration.py::run_selected_action; system/control/orchestration.py::build_orchestration_state
    """
    decision = _safe_mapping(state.get("decision"))
    actions = state.get("agent_actions") if isinstance(state.get("agent_actions"), list) else []
    if actions:
        first = actions[0]
        if isinstance(first, Mapping):
            return dict(first)
    return {
        "mode": _string(decision.get("immediate_mode")) or _string(state.get("active_driver")) or "unknown",
        "summary": _string(decision.get("summary")) or "",
        "command": _string(decision.get("command")) or None,
        "launch_recommended_now": bool(decision.get("launch_recommended_now")),
    }


def _active_phase_controller_state(
    *,
    repo_root: Path,
    phase_token: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    phase_driver = _phase_driver(repo_root, phase_token)
    controller_state = _controller_state_from_phase_driver(phase_driver)
    if controller_state is None:
        raise ValueError("No active phase controller state is available for directive updates.")
    return controller_state, phase_driver


def write_active_directive(
    *,
    summary: str,
    task: str | None = None,
    file_targets: list[str] | None = None,
    repo_root: Path = REPO_ROOT,
    phase_token: str | None = None,
    set_by: str = "control_room",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Persist a new active focus directive onto the currently active phase controller and immediately refresh orchestration artifacts so coordination surfaces reflect it.
    - Mechanism: Resolve the active controller state, ensure the controller scaffold exists, normalize the directive payload, write it through seed_pipeline_controller, then regenerate orchestration artifacts.
    - Reads: _active_phase_controller_state(), ensure_controller_state(), write_focus_directive(), and write_orchestration_artifacts().
    - Writes: The active phase focus_directive.json plus the orchestration artifacts refreshed after the directive change.
    - Guarantee: Returns the directive path, the refreshed coordination.active_directive payload, and the updated orchestration state.
    - Fails: Raises ValueError when no active phase controller exists or when summary is empty; propagates controller/artifact write failures.
    - When-needed: Open when the control room needs to set or retarget the active phase directive and keep orchestration state in sync immediately.
    - Escalates-to: system/lib/seed_pipeline_controller.py::write_focus_directive; tools/meta/control/orchestration_state.json
    """
    from system.lib.seed_pipeline_controller import ensure_controller_state, write_focus_directive

    controller_state, _phase_driver_snapshot = _active_phase_controller_state(
        repo_root=repo_root,
        phase_token=phase_token,
    )
    ensure_controller_state(controller_state, repo_root=repo_root)
    payload: dict[str, Any] = {
        "active": True,
        "summary": _string(summary),
        "task": _string(task) or _string(summary),
        "file_targets": _string_list(file_targets),
        "set_by": _string(set_by) or "control_room",
    }
    if not payload["summary"]:
        raise ValueError("Directive summary is required.")
    path = write_focus_directive(controller_state, payload, repo_root=repo_root)
    refreshed = write_orchestration_artifacts(repo_root=repo_root, phase_token=phase_token)
    return {
        "directive_path": _relative(repo_root, path),
        "directive": refreshed["state"].get("coordination", {}).get("active_directive"),
        "state": refreshed["state"],
    }


def clear_active_directive(
    *,
    repo_root: Path = REPO_ROOT,
    phase_token: str | None = None,
    set_by: str = "control_room",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Clear the current phase focus directive through the same authority path used to write it so coordination surfaces stop advertising stale directive state.
    - Mechanism: Resolve the active controller, ensure the scaffold exists, write an inactive directive payload, then regenerate orchestration artifacts.
    - Reads: _active_phase_controller_state(), ensure_controller_state(), write_focus_directive(), and write_orchestration_artifacts().
    - Writes: The active phase focus_directive.json with active false plus refreshed orchestration artifacts.
    - Guarantee: Returns the directive path, refreshed coordination.active_directive payload, and updated orchestration state after the clear.
    - Fails: Raises ValueError when no active phase controller exists; propagates controller/artifact write failures.
    - When-needed: Open when a control-room action needs to remove the active directive cleanly instead of editing the directive JSON by hand.
    - Escalates-to: system/lib/seed_pipeline_controller.py::write_focus_directive; tools/meta/control/orchestration_state.json
    """
    from system.lib.seed_pipeline_controller import ensure_controller_state, write_focus_directive

    controller_state, _phase_driver_snapshot = _active_phase_controller_state(
        repo_root=repo_root,
        phase_token=phase_token,
    )
    ensure_controller_state(controller_state, repo_root=repo_root)
    path = write_focus_directive(
        controller_state,
        {
            "active": False,
            "summary": "",
            "task": "",
            "file_targets": [],
            "set_by": _string(set_by) or "control_room",
        },
        repo_root=repo_root,
    )
    refreshed = write_orchestration_artifacts(repo_root=repo_root, phase_token=phase_token)
    return {
        "directive_path": _relative(repo_root, path),
        "directive": refreshed["state"].get("coordination", {}).get("active_directive"),
        "state": refreshed["state"],
    }


def run_selected_action(
    *,
    repo_root: Path = REPO_ROOT,
    phase_token: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Execute the current top-priority orchestration command through the repo-local shell runner when the selected action is actually runnable.
    - Mechanism: Refresh the orchestration state, collapse it to selected_action(), refuse when no command exists, otherwise subprocess.run() the tokenized command in repo_root and return the captured result.
    - Reads: load_orchestration_state(), selected_action(), and the chosen command string.
    - Writes: No direct artifact writes beyond those triggered by load_orchestration_state(refresh=True); subprocess side effects are delegated to the selected command.
    - Guarantee: Returns a blocked envelope when the selected action is non-executable, otherwise returns status, active_driver, command, returncode, stdout, and stderr from the invoked process.
    - Fails: Propagates subprocess launch errors before a CompletedProcess exists; command-level failures are returned as status failed with captured stderr/stdout.
    - When-needed: Open when a control-room caller wants the module to execute the recommended next command instead of only reporting it.
    - Escalates-to: system/control/orchestration.py::selected_action; docs/orchestration_state.md
    """
    state = load_orchestration_state(repo_root=repo_root, refresh=True, phase_token=phase_token)
    action = selected_action(state)
    command = _string(action.get("command"))
    if not command:
        return {
            "status": "blocked",
            "active_driver": state.get("active_driver"),
            "summary": _string(action.get("summary")) or "No executable action is recommended.",
            "orchestration_state_path": ORCHESTRATION_STATE_REL,
        }
    result = subprocess.run(
        shlex.split(command),
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    return {
        "status": "ok" if result.returncode == 0 else "failed",
        "active_driver": state.get("active_driver"),
        "command": command,
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }
