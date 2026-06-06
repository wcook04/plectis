#!/usr/bin/env python3
"""
pipeline_advance.py — Lightweight pipeline status checker, advancer, and
resume-surface writer.

Designed for long-running seed loops that need to hand off cleanly between
Codex threads, cron, and other external runners.

Usage:
    python3 pipeline_advance.py                                  # Status check
    python3 pipeline_advance.py --advance                        # Advance one step
    python3 pipeline_advance.py --force --advance                # Bypass approval gate
    python3 pipeline_advance.py --advance --bridge --provider chatgpt
    python3 pipeline_advance.py --check-responses               # Check bridge readiness
    python3 pipeline_advance.py --write-resume                  # Refresh resume artifacts
    python3 pipeline_advance.py --resume-prompt                 # Print Codex resume prompt
    python3 pipeline_advance.py --automation-directive          # Print Codex app automation payload
    python3 pipeline_advance.py --attention-gate                # Check if Codex review is requested
"""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from system.lib.continuation_packet import (
    build_continuation_packet,
    render_codex_resume_prompt as render_continuation_resume_prompt,
    render_codex_wake_prompt as render_continuation_wake_prompt,
    write_continuation_packet,
)
from system.lib.phase_lifecycle import resolve_latest_runtime_state
from system.lib.repo_env import build_env_contract, maybe_reexec_into_repo_python

REPO_ROOT = Path(__file__).resolve().parent
if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)

from pipeline_control import normalize_launch_profile, pipeline_runtime_config
from system.lib.observe_apply_contracts import synth_relevant_file_paths
from system.lib.observe_runtime import summarize_degraded_group_diagnostics
from system.lib.pipeline_recovery import (
    archive_cycles_after,
    archive_phase_runtime,
    create_snapshot,
    list_snapshots,
    restore_snapshot,
)
from system.lib.seed_pipeline_controller import controller_config, ensure_controller_state, write_controller_artifacts

TERMINAL_SESSION_STATES = {"success", "error", "cancelled", "aborted", "blocked", "completed", "done"}
TERMINAL_GROUP_STATES = {"success", "quality_error", "error", "aborted", "blocked", "skipped_no_dump", "skipped_missing_dump"}
ATTENTION_SESSION_STATES = {"error", "cancelled", "aborted", "blocked"}
ATTENTION_GROUP_STATES = {"quality_error", "error", "aborted", "blocked", "skipped_no_dump", "skipped_missing_dump"}
REVIEW_INTERVAL_CYCLES = 2
BRIDGE_WAIT_POLL_AFTER_SECONDS = 60
BRIDGE_LOCKS_REL = "tools/meta/apply/observe_history/bridge_locks"
CONTROLLER_GATE_SUMMARIES = {
    "apply_review_pending": "Apply packet compiled and validated. Review before any mutation.",
    "uncertainty_block": "Controller confidence stayed too low after bounded passes. Review and redirect.",
    "contradiction_block": "A refinement pass contradicted the locked plan. Reconcile before continuing.",
    "backlog_bloat_block": "Task backlog exceeded the configured bound without enough closure. Curate before continuing.",
    "error_spike_block": "Probe degradation crossed the configured threshold. Stabilize the bridge before continuing.",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _without_generated_at(value):
    if isinstance(value, dict):
        return {key: _without_generated_at(item) for key, item in value.items() if key != "generated_at"}
    if isinstance(value, list):
        return [_without_generated_at(item) for item in value]
    return value


def _load_json_payload(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _preserve_generated_at_for_noop(path: Path, payload: dict) -> dict:
    existing = _load_json_payload(path)
    if not existing:
        return payload
    if _without_generated_at(existing) != _without_generated_at(payload):
        return payload
    previous_generated_at = str(existing.get("generated_at") or "").strip()
    if not previous_generated_at:
        return payload
    preserved = dict(payload)
    preserved["generated_at"] = previous_generated_at
    return preserved


def _write_text_if_changed(path: Path, text: str) -> None:
    try:
        if path.is_file() and path.read_text(encoding="utf-8") == text:
            return
    except OSError:
        pass
    path.write_text(text, encoding="utf-8")


def _write_json_if_changed(path: Path, payload: dict) -> None:
    _write_text_if_changed(path, json.dumps(payload, indent=2) + "\n")


def _timestamp_to_epoch(value: str | None) -> float | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        return datetime.fromisoformat(token).timestamp()
    except ValueError:
        return None


def _history_lookup_min_started_at(state: dict) -> str | None:
    token = str(
        state.get("observe_dispatch_started_at")
        or state.get("created_at")
        or ""
    ).strip()
    return token or None


def _should_backfill_manifest_from_dump_dir(state: dict) -> bool:
    stage = str(state.get("stage") or "").strip()
    return stage in {"observe_dispatched", "results_processed", "cycle_complete"} or bool(
        str(state.get("observe_session_id") or "").strip()
    )


def _runtime_policy() -> dict[str, str]:
    return pipeline_runtime_config(REPO_ROOT)


def _controller_policy() -> dict[str, object]:
    return controller_config(repo_root=REPO_ROOT)


def _dispatch_command(*, provider: str = "chatgpt", launch_profile: str | None = None) -> str:
    effective_profile = normalize_launch_profile(
        launch_profile,
        default=str(_runtime_policy()["default_launch_profile"]),
    )
    return (
        "python3 pipeline_advance.py --advance --bridge "
        f"--provider {provider} --launch-profile {effective_profile}"
    )


def _resolve_state_path(path_value: str | Path) -> Path:
    raw = Path(str(path_value).strip())
    if raw.is_absolute():
        return raw
    return (REPO_ROOT / raw).resolve()


def _default_state_rel(state: dict) -> str:
    phase_dir = str(state.get("phase_dir") or "").strip()
    if phase_dir:
        return f"{phase_dir}/pipeline_state.json"
    return "pipeline_state.json"


def _state_rel(state_path: Path) -> str:
    return _relative(state_path)


def _state_artifact_dir(state_path: Path) -> Path:
    return state_path.parent


def _uses_explicit_state_scope(state_path: Path, state: dict) -> bool:
    return _state_rel(state_path) != _default_state_rel(state)


def _scope_command_to_state(command: str, state_path: Path, state: dict) -> str:
    scoped = str(command or "").strip()
    if not scoped or not _uses_explicit_state_scope(state_path, state):
        return scoped
    try:
        tokens = shlex.split(scoped)
    except ValueError:
        return scoped
    if not any(
        token.endswith(("pipeline_advance.py", "pipeline_signal_watcher.py", "seed_pipeline.py"))
        or token in {"pipeline_advance.py", "pipeline_signal_watcher.py", "seed_pipeline.py"}
        for token in tokens
    ):
        return scoped
    state_rel = _state_rel(state_path)
    if "--state" in tokens:
        idx = tokens.index("--state")
        if idx == len(tokens) - 1:
            tokens.append(state_rel)
        else:
            tokens[idx + 1] = state_rel
    else:
        tokens.extend(["--state", state_rel])
    return shlex.join(tokens)


def _scope_command_fields(payload: dict, state_path: Path, state: dict, *, keys: tuple[str, ...]) -> dict:
    scoped = dict(payload)
    for key in keys:
        value = str(scoped.get(key) or "").strip()
        if value:
            scoped[key] = _scope_command_to_state(value, state_path, state)
    return scoped


def find_state(explicit_state: str | Path | None = None) -> tuple[Path | None, dict | None]:
    """Find and load the active pipeline state."""
    if explicit_state is not None and str(explicit_state).strip():
        explicit_state_path = _resolve_state_path(explicit_state)
        if not explicit_state_path.exists():
            return explicit_state_path, None
        return explicit_state_path, json.loads(explicit_state_path.read_text())
    state_path = resolve_latest_runtime_state(REPO_ROOT)
    if state_path is None:
        return None, None
    return state_path, json.loads(state_path.read_text())


def _relative(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _path_card(rel_path: str | None) -> dict | None:
    rel = str(rel_path or "").strip()
    if not rel:
        return None
    abs_path = REPO_ROOT / rel
    card = {
        "path": rel,
        "exists": abs_path.exists(),
    }
    if abs_path.exists():
        stat = abs_path.stat()
        card["modified_at"] = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
        card["bytes"] = int(stat.st_size)
    return card


def _pid_running(pid: object) -> bool:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return False
    if pid_int <= 0:
        return False
    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def _live_bridge_locks() -> list[dict]:
    locks_dir = REPO_ROOT / BRIDGE_LOCKS_REL
    if not locks_dir.exists():
        return []
    live: list[dict] = []
    for lock_path in sorted(locks_dir.glob("*.lock")):
        try:
            raw = lock_path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            continue
        process_id = payload.get("process_id") if isinstance(payload, dict) else None
        if _pid_running(process_id):
            live.append(
                {
                    "provider": lock_path.stem,
                    "lock_path": _relative(lock_path),
                    "process_id": process_id,
                }
            )
    return live


def _load_plan(state: dict) -> dict | None:
    plan_path = str(state.get("observe_plan_path") or "").strip()
    if not plan_path:
        return None
    plan_abs = REPO_ROOT / plan_path
    if not plan_abs.exists():
        return None
    try:
        return json.loads(plan_abs.read_text())
    except json.JSONDecodeError:
        return None


def _load_synth_seed(state: dict) -> dict | None:
    synth_path = str(state.get("synth_seed_path") or "").strip()
    if not synth_path:
        return None
    synth_abs = REPO_ROOT / synth_path
    if not synth_abs.exists():
        return None
    try:
        return json.loads(synth_abs.read_text())
    except json.JSONDecodeError:
        return None


def _load_task_dag(state: dict) -> dict | None:
    dag_path = str(state.get("task_dag_path") or "").strip()
    if not dag_path:
        return None
    dag_abs = REPO_ROOT / dag_path
    if not dag_abs.exists():
        return None
    try:
        return json.loads(dag_abs.read_text())
    except json.JSONDecodeError:
        return None


def _dump_dir(state: dict) -> str | None:
    plan = _load_plan(state)
    if not plan:
        return None
    dump_dir = str(plan.get("dump_dir") or "").strip()
    return dump_dir or None


def _find_history_entry_by_dump_dir(
    dump_dir: str | None,
    *,
    min_started_at: str | None = None,
) -> str | None:
    rel_dump_dir = str(dump_dir or "").strip()
    if not rel_dump_dir:
        return None
    min_epoch = _timestamp_to_epoch(min_started_at)
    entries_dir = REPO_ROOT / "tools/meta/apply/observe_history/entries"
    if not entries_dir.exists():
        return None

    matches: list[Path] = []
    for candidate in entries_dir.glob("OBS_*.json"):
        try:
            payload = json.loads(candidate.read_text())
        except json.JSONDecodeError:
            continue
        candidate_dump = str(
            payload.get("dump_dir")
            or payload.get("config", {}).get("dump_dir")
            or ""
        ).strip()
        if candidate_dump != rel_dump_dir:
            continue
        if min_epoch is not None and candidate.stat().st_mtime < min_epoch:
            continue
        if candidate_dump == rel_dump_dir:
            matches.append(candidate)

    if not matches:
        return None
    return _relative(max(matches, key=lambda p: p.stat().st_mtime))


def _load_observe_manifest(state: dict) -> tuple[str | None, dict | None]:
    dump_dir = _dump_dir(state)
    candidates: list[str] = []
    seen: set[str] = set()
    min_started_at = _history_lookup_min_started_at(state)

    def add(rel_path: str | None) -> None:
        rel = str(rel_path or "").strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        candidates.append(rel)

    if _should_backfill_manifest_from_dump_dir(state):
        add(_find_history_entry_by_dump_dir(dump_dir, min_started_at=min_started_at))
    add(state.get("observe_manifest_path"))

    observe_id = str(state.get("observe_session_id") or "").strip()
    if observe_id:
        add(f"tools/meta/apply/observe_history/entries/{observe_id}.json")

    for rel_path in candidates:
        manifest_abs = REPO_ROOT / rel_path
        if not manifest_abs.exists():
            continue
        try:
            return rel_path, json.loads(manifest_abs.read_text())
        except json.JSONDecodeError:
            continue
    return None, None


def _load_cycle_summary(state: dict, manifest: dict | None = None) -> tuple[str | None, dict | None]:
    dump_dir = ""
    if manifest:
        dump_dir = str(
            manifest.get("dump_dir")
            or manifest.get("config", {}).get("dump_dir")
            or ""
        ).strip()
    if not dump_dir:
        dump_dir = str(_dump_dir(state) or "").strip()
    if not dump_dir:
        return None, None

    summary_rel = f"{dump_dir}/_cycle_summary.json"
    summary_abs = REPO_ROOT / summary_rel
    if not summary_abs.exists():
        return None, None
    try:
        return summary_rel, json.loads(summary_abs.read_text())
    except json.JSONDecodeError:
        return None, None


def _load_cycle_timeline_path(
    state: dict,
    *,
    manifest: dict | None = None,
    cycle_summary_path: str | None = None,
) -> str | None:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(rel_path: str | None) -> None:
        rel = str(rel_path or "").strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        candidates.append(rel)

    add(state.get("current_cycle_timeline_path"))

    plan = _load_plan(state) or {}
    add(plan.get("cycle_timeline_path") if isinstance(plan, dict) else None)

    if cycle_summary_path:
        add(str(Path(cycle_summary_path).with_name("cycle_timeline.jsonl")))

    dump_dir = str(
        (manifest or {}).get("dump_dir")
        or (manifest or {}).get("config", {}).get("dump_dir")
        or _dump_dir(state)
        or ""
    ).strip()
    if dump_dir:
        add(f"{dump_dir}/cycle_timeline.jsonl")

    current_cycle_dir = str(state.get("current_cycle_dir") or "").strip()
    if current_cycle_dir:
        add(f"{current_cycle_dir}/cycle_timeline.jsonl")

    completed_cycle = max(0, int(state.get("cycle") or 0) - 1)
    phase_dir = str(state.get("phase_dir") or "").strip()
    if phase_dir:
        add(f"{phase_dir}/cycle_{completed_cycle}/cycle_timeline.jsonl")

    for rel_path in candidates:
        if (REPO_ROOT / rel_path).exists():
            return rel_path
    return candidates[0] if candidates else None


def _load_cycle_assimilation_path(
    state: dict,
    *,
    manifest: dict | None = None,
    cycle_summary_path: str | None = None,
) -> str | None:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(rel_path: str | None) -> None:
        rel = str(rel_path or "").strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        candidates.append(rel)

    add(state.get("current_cycle_assimilation_path"))

    if cycle_summary_path:
        add(str(Path(cycle_summary_path).with_name("cycle_assimilation.json")))

    dump_dir = str(
        (manifest or {}).get("dump_dir")
        or (manifest or {}).get("config", {}).get("dump_dir")
        or _dump_dir(state)
        or ""
    ).strip()
    if dump_dir:
        add(f"{dump_dir}/cycle_assimilation.json")

    current_cycle_dir = str(state.get("current_cycle_dir") or "").strip()
    if current_cycle_dir:
        add(f"{current_cycle_dir}/cycle_assimilation.json")

    completed_cycle = max(0, int(state.get("cycle") or 0) - 1)
    phase_dir = str(state.get("phase_dir") or "").strip()
    if phase_dir:
        add(f"{phase_dir}/cycle_{completed_cycle}/cycle_assimilation.json")

    for rel_path in candidates:
        if (REPO_ROOT / rel_path).exists():
            return rel_path
    return candidates[0] if candidates else None


def _load_cycle_carry_forward_path(
    state: dict,
    *,
    manifest: dict | None = None,
    cycle_summary_path: str | None = None,
) -> str | None:
    candidates: list[str] = []
    seen: set[str] = set()

    def add(rel_path: str | None) -> None:
        rel = str(rel_path or "").strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        candidates.append(rel)

    add(state.get("current_cycle_carry_forward_path"))

    if cycle_summary_path:
        add(str(Path(cycle_summary_path).with_name("carry_forward_context.json")))

    dump_dir = str(
        (manifest or {}).get("dump_dir")
        or (manifest or {}).get("config", {}).get("dump_dir")
        or _dump_dir(state)
        or ""
    ).strip()
    if dump_dir:
        add(f"{dump_dir}/carry_forward_context.json")

    current_cycle_dir = str(state.get("current_cycle_dir") or "").strip()
    if current_cycle_dir:
        add(f"{current_cycle_dir}/carry_forward_context.json")

    completed_cycle = max(0, int(state.get("cycle") or 0) - 1)
    phase_dir = str(state.get("phase_dir") or "").strip()
    if phase_dir:
        add(f"{phase_dir}/cycle_{completed_cycle}/carry_forward_context.json")

    for rel_path in candidates:
        if (REPO_ROOT / rel_path).exists():
            return rel_path
    return candidates[0] if candidates else None


def _cycle_summary_sort_key(path: Path) -> tuple[int, str]:
    parent = path.parent.name
    if parent.startswith("cycle_"):
        suffix = parent.split("_", 1)[1]
        try:
            return int(suffix), parent
        except ValueError:
            pass
    return -1, parent


def _load_recent_cycle_summaries(state: dict, *, limit: int = 8) -> list[dict]:
    phase_dir_rel = str(state.get("phase_dir") or "").strip()
    if not phase_dir_rel:
        return []
    phase_dir = REPO_ROOT / phase_dir_rel
    if not phase_dir.exists():
        return []

    summaries: list[dict] = []
    for path in sorted(
        phase_dir.glob("cycle_*/_cycle_summary.json"),
        key=_cycle_summary_sort_key,
        reverse=True,
    ):
        try:
            payload = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            summaries.append(payload)
        if len(summaries) >= limit:
            break
    return summaries


def _routing_decision_label(summary: dict) -> str:
    routing = summary.get("routing_decision")
    if isinstance(routing, dict):
        decision = str(routing.get("decision") or "").strip()
        if decision:
            return decision
    controller_phase = str(summary.get("controller_phase") or "").strip().lower()
    if controller_phase == "probe":
        return "continue_probe"
    if controller_phase == "scope":
        return "scope_pass"
    if controller_phase == "plan":
        return "plan_pass"
    return controller_phase or "unknown"


def _cycle_degradation_summary(summary: dict | None, manifest: dict | None = None) -> dict:
    if isinstance(summary, dict) and isinstance(summary.get("degradation_summary"), dict):
        return dict(summary.get("degradation_summary") or {})
    if not isinstance(manifest, dict):
        return {}
    groups = manifest.get("groups")
    if not isinstance(groups, list):
        return {}
    probe_count = sum(
        1
        for group in groups
        if isinstance(group, dict) and str(group.get("role") or "probe").strip().lower() == "probe"
    )
    return summarize_degraded_group_diagnostics(
        groups,
        degraded_groups=(summary or {}).get("degraded_groups") if isinstance(summary, dict) else None,
        probe_count=probe_count,
    )


def _smart_pause_attention(state: dict) -> dict | None:
    policy = _controller_policy().get("smart_pause", {})
    if not isinstance(policy, dict):
        policy = {}
    if not bool(policy.get("enabled", True)):
        return None

    limit = max(2, int(policy.get("non_advance_cycle_limit") or 4))
    recent = _load_recent_cycle_summaries(state, limit=max(limit + 2, 8))
    if not recent:
        return None

    streak: list[dict] = []
    for summary in recent:
        gate_reason = str(summary.get("gate_reason") or "").strip().lower()
        if gate_reason not in {"", "none"}:
            break
        if summary.get("degraded_groups"):
            break
        controller_phase = str(summary.get("controller_phase") or "").strip().lower()
        if controller_phase in {"plan", "apply_review_pending", "blocked"}:
            break
        streak.append(summary)

    if len(streak) < limit:
        return None

    latest = streak[0]
    recent_labels = [_routing_decision_label(item) for item in reversed(streak[:limit])]
    latest_phase = str(latest.get("controller_phase") or "").strip() or "unknown"
    latest_confidence = latest.get("confidence_score")

    details = [
        f"Clean non-advance streak: {len(streak)} cycles (limit: {limit}).",
        f"Latest controller phase: {latest_phase}.",
        f"Recent decisions: {', '.join(recent_labels)}.",
    ]
    if latest_confidence is not None:
        details.append(f"Latest confidence: {latest_confidence}.")
    if latest.get("current_task_id"):
        details.append(f"Current task: {latest.get('current_task_id')}.")

    return {
        "needs_attention": True,
        "pause_pipeline": True,
        "wake_requested": False,
        "reason_key": "smart_pause_non_advance",
        "summary": (
            "The unattended loop stayed clean but did not advance beyond scope/probe. "
            "Pause before spending another bridge cycle."
        ),
        "details": details,
        "completed_cycle": max(0, int(state.get("cycle") or 0) - 1),
        "review_interval_cycles": REVIEW_INTERVAL_CYCLES,
        "observe_manifest_path": None,
        "cycle_summary_path": None,
        "continue_command": "python3 pipeline_advance.py --force --advance",
        "gate_command": "python3 pipeline_advance.py --attention-gate",
        "resume_command": "python3 emergency_stop_observe.py --resume",
    }


def _active_scope(state: dict) -> dict:
    synth = _load_synth_seed(state) or {}
    task_dag = _load_task_dag(state) or {}
    source_shards = synth.get("source_shards") or synth.get("seed_shards") or []
    synth_scope_files = synth_relevant_file_paths(synth)
    scope_files = [
        str(path).strip()
        for path in (state.get("active_scope_files") or synth_scope_files or [])
        if str(path).strip()
    ]
    known_scope_files = [
        str(path).strip()
        for path in (state.get("known_relevant_files") or synth_scope_files or scope_files)
        if str(path).strip()
    ]
    concept_groups = sorted(
        {
            str(shard.get("concept_group") or "general")
            for shard in source_shards
            if isinstance(shard, dict)
        }
    )
    shard_ids = [str(shard.get("id")) for shard in source_shards if isinstance(shard, dict) and shard.get("id")]
    return {
        "selected_shard_ids": shard_ids,
        "selected_shard_count": len(shard_ids),
        "active_scope_files": scope_files,
        "active_scope_count": len(scope_files),
        "known_relevant_files": known_scope_files,
        "known_relevant_count": len(known_scope_files),
        "concept_groups": concept_groups,
        "controller_phase": state.get("phase") or state.get("controller_phase"),
        "current_layer_id": state.get("current_layer_id"),
        "current_layer_kind": state.get("current_layer_kind"),
        "current_task_id": state.get("current_task_id"),
        "gate_reason": state.get("gate_reason"),
        "routing_decision": state.get("routing_decision"),
        "task_dag_migrated": bool((task_dag.get("migration") or {}).get("migrated_from_legacy")),
    }


def compute_codex_attention(state: dict) -> dict:
    """Return whether this state should stop and request a fresh Codex review."""
    stage = str(state.get("stage") or "")
    manifest_path, manifest = _load_observe_manifest(state)
    summary_path, cycle_summary = _load_cycle_summary(state, manifest)
    assimilation_path = _load_cycle_assimilation_path(
        state,
        manifest=manifest,
        cycle_summary_path=summary_path,
    )
    cycle_assimilation = None
    if assimilation_path and (REPO_ROOT / assimilation_path).exists():
        try:
            cycle_assimilation = json.loads((REPO_ROOT / assimilation_path).read_text())
        except json.JSONDecodeError:
            cycle_assimilation = None
    carry_forward_path = _load_cycle_carry_forward_path(
        state,
        manifest=manifest,
        cycle_summary_path=summary_path,
    )
    completed_cycle = max(0, int(state.get("cycle") or 0) - 1)

    attention = {
        "needs_attention": False,
        "pause_pipeline": False,
        "wake_requested": False,
        "reason_key": "none",
        "summary": "No Codex review requested. Continue the bounded loop from disk.",
        "details": [],
        "completed_cycle": completed_cycle,
        "review_interval_cycles": REVIEW_INTERVAL_CYCLES,
        "observe_manifest_path": manifest_path,
        "cycle_summary_path": summary_path,
        "cycle_assimilation_path": assimilation_path,
        "carry_forward_context_path": carry_forward_path,
        "continue_command": "python3 pipeline_advance.py --force --advance",
        "gate_command": "python3 pipeline_advance.py --attention-gate",
        "resume_command": "python3 emergency_stop_observe.py --resume",
    }

    controller_reason = str(state.get("gate_reason") or "").strip()
    controller_phase = str(state.get("controller_phase") or "").strip()
    current_layer_kind = str(state.get("current_layer_kind") or "").strip()
    current_layer_id = str(state.get("current_layer_id") or "").strip()
    wake_conditions = {
        str(item).strip()
        for item in _controller_policy().get("wake_conditions", [])
        if str(item).strip()
    }
    if controller_reason in wake_conditions:
        attention.update({
            "needs_attention": True,
            "wake_requested": True,
            "reason_key": controller_reason,
            "summary": CONTROLLER_GATE_SUMMARIES.get(
                controller_reason,
                "Controller requested a deliberate orchestration review.",
            ),
            "details": [],
        })
        if controller_phase:
            attention["details"].append(f"Controller phase: {controller_phase}")
        if current_layer_kind:
            attention["details"].append(f"Current layer: {current_layer_kind}{f' ({current_layer_id})' if current_layer_id else ''}")
        if state.get("current_task_id"):
            attention["details"].append(f"Current task: {state.get('current_task_id')}")
        if state.get("apply_plan_path"):
            attention["details"].append(f"Apply plan: {state.get('apply_plan_path')}")
        return attention

    if stage == "apply_ready":
        attention.update({
            "needs_attention": True,
            "wake_requested": True,
            "reason_key": controller_reason or "apply_review_pending",
            "summary": CONTROLLER_GATE_SUMMARIES.get(
                controller_reason or "apply_review_pending",
                "Apply is ready and requires a deliberate review before proceeding.",
            ),
            "details": ["Apply remains approval-gated by design."],
        })
        if state.get("apply_plan_path"):
            attention["details"].append(f"Apply plan: {state.get('apply_plan_path')}")
        return attention

    if stage not in {"results_processed", "cycle_complete"}:
        return attention

    runtime_state = ""
    degraded_groups: list[str] = []
    if manifest:
        runtime_state = str(
            manifest.get("runtime", {}).get("state")
            or manifest.get("state")
            or manifest.get("status")
            or ""
        ).strip()
        for group in manifest.get("groups", []):
            group_status = str(group.get("response_status") or group.get("runtime_state") or "").strip()
            if group_status in ATTENTION_GROUP_STATES:
                degraded_groups.append(f"{group.get('label', 'unknown')}:{group_status}")
    degradation_summary = _cycle_degradation_summary(cycle_summary, manifest)
    retryable_degradation = bool(degradation_summary.get("all_degraded_auto_retry_safe"))

    if runtime_state in ATTENTION_SESSION_STATES or degraded_groups:
        if not retryable_degradation:
            attention.update({
                "needs_attention": True,
                "reason_key": "degraded_cycle",
                "summary": "The finished cycle ended degraded or errorful. Pause and review before continuing.",
            })
            if runtime_state:
                attention["details"].append(f"Session state: {runtime_state}")
            if degraded_groups:
                attention["details"].append(
                    f"Degraded/error groups: {', '.join(degraded_groups[:6])}"
                )
            return attention

    loop_decision = (
        cycle_assimilation.get("loop_decision")
        if isinstance(cycle_assimilation, dict) and isinstance(cycle_assimilation.get("loop_decision"), dict)
        else {}
    )
    loop_action = str(loop_decision.get("action") or "").strip()
    if str(loop_decision.get("action") or "").strip() == "widen_scope_candidate":
        widened_files = list(loop_decision.get("widened_files_outside_scope") or [])
        attention.update({
            "needs_attention": True,
            "reason_key": "resource_universe_widening",
            "summary": str(loop_decision.get("summary") or "The bounded pass surfaced evidence outside the current scope.").strip(),
            "details": [],
        })
        if widened_files:
            attention["details"].append(
                "Files outside current scope: " + ", ".join(str(item) for item in widened_files[:6])
            )
        missing_count = int(loop_decision.get("missing_evidence_count") or 0)
        if missing_count:
            attention["details"].append(f"Missing-evidence signals: {missing_count}")
        return attention

    controller_phase = str(state.get("controller_phase") or state.get("phase") or "").strip()
    is_controller_state = controller_phase in {"scope", "probe", "plan", "apply_review_pending", "blocked"}

    if not is_controller_state and cycle_summary and int(cycle_summary.get("new_shards_ingested") or 0) > 0:
        attention.update({
            "needs_attention": True,
            "reason_key": "new_frontier",
            "summary": "The finished cycle created new shards. Re-anchor before allowing the loop to widen further.",
            "details": [
                f"New shards ingested: {int(cycle_summary.get('new_shards_ingested') or 0)}"
            ],
        })
        return attention

    zero_evolution_streak = int((cycle_summary or {}).get("zero_evolution_streak") or 0)
    frontier_repeat_streak = int((cycle_summary or {}).get("frontier_repeat_streak") or 0)
    if zero_evolution_streak >= 3 or frontier_repeat_streak >= 3:
        if is_controller_state:
            return attention
        attention.update({
            "needs_attention": True,
            "reason_key": "stagnation",
            "summary": "The loop is mechanically advancing without enough frontier movement. Review before continuing.",
            "details": [],
        })
        if zero_evolution_streak >= 3:
            attention["details"].append(
                f"Zero-evolution streak: {zero_evolution_streak} consecutive cycles."
            )
        if frontier_repeat_streak >= 3:
            attention["details"].append(
                f"Repeated selected frontier: {frontier_repeat_streak} consecutive cycles."
            )
        return attention

    return attention


def check_responses_ready(state: dict) -> dict:
    """Check if bridge dispatch responses are ready."""
    stage = str(state.get("stage") or "").strip()
    gate_reason = str(state.get("gate_reason") or "").strip()
    if gate_reason and gate_reason != "none":
        return _with_readiness_next_action({
            "status": "controller_gate_active",
            "stage": stage or "unknown",
            "gate_reason": gate_reason,
            "ready": False,
            "not_applicable": True,
            "controller_gate_active": True,
            "retryable_gate": gate_reason in {"uncertainty_block", "error_spike_block"},
            "reason": "controller_gate_precedes_response_processing",
            "suggested_command": _gate_command_for_state(state, gate_reason),
        })
    manifest_rel = str(state.get("observe_manifest_path") or "").strip()
    observe_id = str(state.get("observe_session_id") or "").strip()
    plan_dump_dir = _dump_dir(state)
    min_started_at = _history_lookup_min_started_at(state)

    candidates: list[str] = []
    matched_entry = _find_history_entry_by_dump_dir(plan_dump_dir, min_started_at=min_started_at)
    if matched_entry:
        candidates.append(matched_entry)
    if manifest_rel:
        candidates.append(manifest_rel)
    if observe_id:
        candidates.append(f"tools/meta/apply/observe_history/entries/{observe_id}.json")

    for rel_path in candidates:
        manifest_abs = REPO_ROOT / rel_path
        if not manifest_abs.exists():
            continue
        manifest = json.loads(manifest_abs.read_text())
        runtime_state = str(
            manifest.get("state")
            or manifest.get("runtime", {}).get("state")
            or manifest.get("status")
            or ""
        ).strip()
        groups = manifest.get("groups", [])
        if groups:
            terminal = sum(
                1
                for group in groups
                if str(group.get("response_status") or group.get("runtime_state") or "").strip() in TERMINAL_GROUP_STATES
            )
            total = len(groups)
            return _with_readiness_next_action({
                "status": runtime_state or "grouped_observe",
                "responses_found": terminal,
                "groups_expected": total,
                "ready": runtime_state in TERMINAL_SESSION_STATES or terminal >= total,
                "record_path": rel_path,
            })

        node_states = manifest.get("node_states", {})
        if node_states:
            done_count = sum(1 for value in node_states.values() if value == "done")
            total = len(node_states)
            return _with_readiness_next_action({
                "status": manifest.get("status", "unknown"),
                "nodes_done": done_count,
                "nodes_total": total,
                "ready": manifest.get("status") == "done",
                "record_path": rel_path,
            })

    if stage != "observe_dispatched":
        return _with_readiness_next_action({
            "status": "not_applicable_no_observe_dispatch",
            "stage": stage or "unknown",
            "ready": False,
            "not_applicable": True,
            "reason": "check_responses_only_applies_after_observe_dispatch",
            "suggested_command": "python3 pipeline_advance.py --advance",
        })

    # No manifest — check if dump_dir has response files
    plan_path = state.get("observe_plan_path")
    if plan_path:
        plan = json.loads((REPO_ROOT / plan_path).read_text())
        dump_dir = REPO_ROOT / plan.get("dump_dir", "")
        if dump_dir.exists():
            responses = list(dump_dir.glob("*_response.md"))
            groups = plan.get("groups", [])
            live_locks = _live_bridge_locks()
            if (
                not responses
                and not matched_entry
                and not manifest_rel
                and not observe_id
                and str(state.get("stage") or "").strip() == "observe_dispatched"
            ):
                if live_locks:
                    return _with_readiness_next_action({
                        "status": "dispatch_in_progress",
                        "responses_found": 0,
                        "groups_expected": len(groups),
                        "ready": False,
                        "dump_dir": str(dump_dir.relative_to(REPO_ROOT)),
                        "live_bridge_locks": live_locks,
                    })
                return _with_readiness_next_action({
                    "status": "dispatch_unmaterialized",
                    "responses_found": 0,
                    "groups_expected": len(groups),
                    "ready": False,
                    "dump_dir": str(dump_dir.relative_to(REPO_ROOT)),
                    "retryable_dispatch": True,
                    "suggested_command": _dispatch_command(),
                    "reason": "observe_dispatched_without_manifest_or_live_bridge_lock",
                })
            return _with_readiness_next_action({
                "status": "checking",
                "responses_found": len(responses),
                "groups_expected": len(groups),
                "ready": len(responses) >= max(1, len(groups) - 1),
                "dump_dir": str(dump_dir.relative_to(REPO_ROOT)),
            })
    return _with_readiness_next_action({"status": "no_manifest", "ready": False})


def _with_readiness_next_action(readiness: dict) -> dict:
    if readiness.get("controller_gate_active"):
        if readiness.get("retryable_gate"):
            next_action_payload = {
                "key": "retry_gate",
                "summary": "A retryable controller gate is active. Clear or review that gate before processing bridge responses.",
                "command": readiness.get("suggested_command") or "python3 seed_pipeline.py --retry-gate",
            }
        else:
            next_action_payload = {
                "key": "controller_gate",
                "summary": "A controller gate is active. Review that gate before processing bridge responses.",
                "command": readiness.get("suggested_command") or "python3 seed_pipeline.py --status",
            }
    elif readiness.get("ready"):
        next_action_payload = {
            "key": "process_results",
            "summary": "Bridge responses are ready; process results now.",
            "command": "python3 pipeline_advance.py --advance",
        }
    elif readiness.get("retryable_dispatch"):
        next_action_payload = {
            "key": "retry_bridge_dispatch",
            "summary": "Bridge dispatch did not materialize an observe session or live provider lock. Retry the bridge dispatch instead of polling responses forever.",
            "command": readiness.get("suggested_command") or _dispatch_command(),
        }
    elif readiness.get("not_applicable"):
        next_action_payload = {
            "key": "advance_one_step",
            "summary": "No bridge dispatch is active for this stage; advance the pipeline instead of checking responses.",
            "command": readiness.get("suggested_command") or "python3 pipeline_advance.py --advance",
        }
    else:
        next_action_payload = _wait_for_bridge_action()
    enriched = dict(readiness)
    enriched["next_action"] = next_action_payload
    return enriched


def _wait_for_bridge_action() -> dict:
    return {
        "key": "wait_for_bridge",
        "summary": "Bridge work is still in progress. Do not keep a chat thread open just to wait.",
        "command": "python3 pipeline_advance.py --check-responses",
        "poll_after_seconds": BRIDGE_WAIT_POLL_AFTER_SECONDS,
    }


def check_responses_exit_code(readiness: dict) -> int:
    """Return the CLI exit code for a bridge readiness packet."""
    if readiness.get("ready") or readiness.get("not_applicable"):
        return 0
    status = str(readiness.get("status") or "").strip()
    next_key = str((readiness.get("next_action") or {}).get("key") or "").strip()
    healthy_wait_statuses = {"checking", "dispatching", "dispatch_in_progress"}
    if next_key == "wait_for_bridge" and status in healthy_wait_statuses:
        return 0
    return 1


def _state_file_for_state(state: dict) -> str:
    return f"{state['phase_dir']}/pipeline_state.json" if state.get("phase_dir") else "pipeline_state.json"


def _gate_command_for_state(state: dict, gate_reason: str) -> str:
    if gate_reason in {"uncertainty_block", "error_spike_block"}:
        return f"python3 seed_pipeline.py --retry-gate --state '{_state_file_for_state(state)}'"
    if gate_reason == "apply_review_pending":
        return "python3 seed_pipeline.py --status"
    return "python3 pipeline_advance.py --attention-gate"


def next_action(state: dict) -> dict:
    """Return the next bounded move for the current pipeline stage."""
    stage = state["stage"]
    gate_reason = str(state.get("gate_reason") or "").strip()
    state_file = _state_file_for_state(state)

    if stage == "observe_dispatched":
        resp = check_responses_ready(state)
        if resp.get("controller_gate_active"):
            return dict(resp["next_action"])
        if resp.get("ready"):
            return {
                "key": "process_results",
                "summary": "Bridge responses are ready; process results now.",
                "command": "python3 pipeline_advance.py --advance",
            }
        if resp.get("retryable_dispatch"):
            return {
                "key": "retry_bridge_dispatch",
                "summary": "Bridge dispatch did not materialize an observe session or live provider lock. Retry the bridge dispatch instead of polling responses forever.",
                "command": resp.get("suggested_command") or _dispatch_command(),
            }
        return _wait_for_bridge_action()

    if stage == "observe_plan_compiled":
        dispatch_status = str(state.get("observe_dispatch_status") or "").strip()
        dispatch_error = str(state.get("observe_dispatch_error") or "").strip()
        if dispatch_status == "failed":
            summary = "Previous bridge dispatch failed before a session materialized. Retry the compiled observe plan."
            if dispatch_error:
                summary = f"{summary} Last error: {dispatch_error}"
            return {
                "key": "retry_bridge_dispatch",
                "summary": summary,
                "command": _dispatch_command(),
            }
        return {
            "key": "dispatch_bridge",
            "summary": "Observe plan is compiled and ready for bridge dispatch.",
            "command": _dispatch_command(),
        }

    if stage in {"results_processed", "cycle_complete"}:
        if gate_reason in {"uncertainty_block", "error_spike_block"}:
            diagnostic_path = str(state.get("apply_plan_diagnostic_path") or "").strip()
            validation_error = str(state.get("plan_validation_error") or "").strip()
            summary = "A retryable controller gate is active. Review the latest cycle artifacts before clearing it."
            if diagnostic_path:
                summary = (
                    "A retryable controller gate is active because the latest plan receipt was not executable. "
                    f"Review `{diagnostic_path}` first, then clear the gate."
                )
            elif validation_error:
                summary = (
                    "A retryable controller gate is active because the latest plan receipt was not executable. "
                    f"Review the validation error (`{validation_error}`), then clear the gate."
                )
            return {
                "key": "retry_gate",
                "summary": summary,
                "command": f"python3 seed_pipeline.py --retry-gate --state '{state_file}'",
            }
        attention = compute_codex_attention(state)
        if attention.get("needs_attention"):
            return {
                "key": "codex_review_gate",
                "summary": attention["summary"],
                "command": attention["gate_command"],
            }
        return {
            "key": "advance_one_step",
            "summary": "Advance one bounded step and re-evaluate from disk.",
            "command": "python3 pipeline_advance.py --advance",
        }

    if stage in {"shards_extracted", "shards_selected", "synth_seed_emitted", "init"}:
        return {
            "key": "advance_one_step",
            "summary": "Advance one bounded step and re-evaluate from disk.",
            "command": "python3 pipeline_advance.py --advance",
        }

    if stage == "apply_ready":
        return {
            "key": "approval_gate",
            "summary": "Apply is gated. Review the compiled plan before any live mutation.",
            "command": "python3 seed_pipeline.py --status",
        }

    return {
        "key": "inspect",
        "summary": f"Inspect the pipeline state for stage '{stage}'.",
        "command": "python3 seed_pipeline.py --status",
    }


def prepare_state_for_action(state: dict, action: dict) -> bool:
    """Align mutable pipeline state with the selected action before execution."""
    if action.get("key") != "retry_bridge_dispatch":
        return False
    if str(state.get("stage") or "").strip() != "observe_dispatched":
        return False

    state["stage"] = "observe_plan_compiled"
    state["observe_dispatch_status"] = "retrying"
    state["observe_dispatch_retry_reason"] = str(action.get("summary") or "").strip() or None
    state["observe_session_id"] = None
    state["observe_manifest_path"] = None
    return True


def _directive_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ")


def build_codex_automation(packet: dict) -> dict:
    """Return a Codex app automation suggestion for durable resume."""
    commands = packet.get("recommended_commands") or {}
    attention_gate = str(commands.get("attention_gate") or "python3 pipeline_advance.py --attention-gate").strip()
    force_next = str(commands.get("force_next_step") or "python3 pipeline_advance.py --force --advance").strip()
    write_resume = str(commands.get("write_resume") or "python3 pipeline_advance.py --write-resume").strip()
    phase_name = Path(str(packet.get("phase_dir") or packet.get("state_path") or "pipeline")).name
    prompt = (
        "Resume the ai_workflow seed pipeline from disk. "
        f"Treat {packet.get('continuation_packet_path') or 'continuation_packet.json'} as the primary wake contract, with {packet['state_path']}, pipeline_resume.json, and pipeline_attention.json as supporting runtime artifacts. "
        f"Run {attention_gate} first. If no attention is required, stop. "
        "If attention is required, read the current attention and resume packets, then decide whether to continue with "
        f"{force_next} or stop after refreshing the resume artifacts with {write_resume}. "
        "Never keep a thread open just to wait for bridge completion."
    )
    return {
        "mode": "suggested create",
        "name": f"{phase_name} Resume",
        "prompt": prompt,
        "rrule": "FREQ=HOURLY;INTERVAL=1",
        "cwds": str(REPO_ROOT),
        "status": "ACTIVE",
        "notes": (
            "Codex app automations are best used for durable re-entry. "
            "Use pipeline_trigger.sh or cron for sub-hour polling."
        ),
    }


def build_codex_automation_directive(packet: dict) -> str:
    """Return a chat directive that the Codex app can turn into an automation."""
    automation = build_codex_automation(packet)
    return (
        "::automation-update{"
        f"mode=\"{_directive_escape(automation['mode'])}\" "
        f"name=\"{_directive_escape(automation['name'])}\" "
        f"prompt=\"{_directive_escape(automation['prompt'])}\" "
        f"rrule=\"{_directive_escape(automation['rrule'])}\" "
        f"cwds=\"{_directive_escape(automation['cwds'])}\" "
        f"status=\"{_directive_escape(automation['status'])}\""
        "}"
    )


def _build_context_recovery(state: dict, *, state_path: Path | None = None) -> dict:
    """Build context recovery pointers for post-overrun / cold-start re-orientation.

    When an agent's context window exhausts mid-session, the next session needs
    to re-orient quickly from disk. This provides the minimum set of pointers.
    """
    phase_dir = state.get("phase_dir", "")
    family_dir = state.get("family_dir", "") or ""
    synth_seed_path = state.get("synth_seed_path") or ""
    raw_seed_path = state.get("raw_seed_path") or ""

    # Infer raw_seed from phase hierarchy if not explicit
    if not raw_seed_path and (family_dir or phase_dir):
        anchor_dir = str(family_dir or Path(phase_dir).parent)
        candidate = f"{anchor_dir}/raw_seed.md"
        if (REPO_ROOT / candidate).exists():
            raw_seed_path = candidate

    # Infer synth_seed from phase dir if not explicit
    if not synth_seed_path and phase_dir:
        candidate = f"{phase_dir}/synth_seed.json"
        if (REPO_ROOT / candidate).exists():
            synth_seed_path = candidate

    attention_gate = "python3 pipeline_advance.py --attention-gate"
    if state_path is not None:
        attention_gate = _scope_command_to_state(attention_gate, state_path, state)

    return {
        "raw_seed_path": raw_seed_path or None,
        "synth_seed_path": synth_seed_path or None,
        "claude_md_path": "CLAUDE.md",
        "codex_md_path": "CODEX.md",
        "phase_dir": phase_dir,
        "family_dir": family_dir or None,
        "recovery_instructions": [
            "If this is a fresh session after context exhaustion:",
            "1. Read this resume packet and pipeline_attention.json first",
            f"2. Run: {attention_gate}",
            "3. If review needed: read synth_seed.json for intent + shard status",
            "4. If review needed: skim raw_seed.md (first 50 lines) for original voice",
            "5. Then proceed with the next_action command",
        ],
    }


def _phase_ref_for_commands(state: dict, synth: dict | None = None) -> str:
    synth_meta = synth.get("meta") if isinstance(synth, dict) else {}
    if not isinstance(synth_meta, dict):
        synth_meta = {}
    for candidate in (
        synth_meta.get("phase_id"),
        synth_meta.get("phase_number"),
        state.get("phase_id"),
        state.get("phase_number"),
        Path(str(state.get("phase_dir") or "")).name if state.get("phase_dir") else "",
    ):
        token = str(candidate or "").strip()
        if token:
            return token
    return ""


def _build_authority_surfaces(state: dict, *, state_path: Path | None = None) -> dict:
    recovery = _build_context_recovery(state, state_path=state_path)
    synth = _load_synth_seed(state) or {}
    phase_ref = _phase_ref_for_commands(state, synth)
    raw_seed_path = str(recovery.get("raw_seed_path") or "").strip()
    synth_seed_path = str(recovery.get("synth_seed_path") or "").strip()
    meta_ledger_path = str(state.get("meta_ledger_path") or "").strip()
    family_dir = str(recovery.get("family_dir") or "").strip()
    reference_ledger_path = f"{family_dir}/reference_ledger.json" if family_dir else ""
    apply_plan_path = f"{state['phase_dir']}/apply_plan.json"
    apply_packet_path = f"{state['phase_dir']}/apply_packet.json"
    raw_card = _path_card(raw_seed_path)
    synth_card = _path_card(synth_seed_path)
    synth_status = str((synth or {}).get("authoring_status") or "").strip()

    refresh_needed = False
    refresh_reason = "up_to_date"
    raw_abs = (REPO_ROOT / raw_seed_path) if raw_seed_path else None
    synth_abs = (REPO_ROOT / synth_seed_path) if synth_seed_path else None
    if not synth_card or not synth_card.get("exists"):
        refresh_needed = True
        refresh_reason = "synth_missing"
    elif synth_status == "pending_initial_synth_authoring":
        refresh_needed = True
        refresh_reason = "synth_pending_initial_authoring"
    elif raw_abs and synth_abs and raw_abs.exists() and synth_abs.exists() and raw_abs.stat().st_mtime > synth_abs.stat().st_mtime:
        refresh_needed = True
        refresh_reason = "raw_seed_newer_than_synth"

    extract_command = (
        f"python3 kernel.py --phase-dock {phase_ref} --dock-operation extract_subphase_seed --live"
        if phase_ref
        else None
    )
    sync_command = (
        f"python3 kernel.py --sync-synth {phase_ref} --live"
        if phase_ref
        else None
    )
    overnight_command = (
        f"python3 pipeline_overnight.py --phase {phase_ref} --wake-agent both --sleep-policy keep_awake"
        if phase_ref
        else None
    )

    return {
        "phase_ref": phase_ref or None,
        "raw_seed": raw_card,
        "synth_seed": synth_card,
        "reference_ledger": _path_card(reference_ledger_path),
        "meta_ledger": _path_card(meta_ledger_path),
        "apply_plan": _path_card(apply_plan_path),
        "apply_packet": _path_card(apply_packet_path),
        "synth_refresh": {
            "needed": refresh_needed,
            "reason": refresh_reason,
            "authoring_status": synth_status or None,
        },
        "commands": {
            "extract_synth_from_raw_seed": extract_command,
            "sync_synth_markdown": sync_command,
            "overnight_rearm": overnight_command,
        },
        "write_rules": [
            "raw_seed.md is append-only blackboard input; do not rewrite or compress it during routine review.",
            "synth_seed.json is the canonical machine authority and the only synth write target.",
            "synth_seed.md is generated from synth_seed.json; regenerate it with the sync command instead of editing markdown directly.",
        ],
    }


def _build_agent_operating_contract(state: dict, *, state_path: Path | None = None) -> dict:
    authority = _build_authority_surfaces(state, state_path=state_path)
    synth_target = (authority.get("synth_seed") or {}).get("path") or "synth_seed.json"
    sync_command = (authority.get("commands") or {}).get("sync_synth_markdown") or "python3 kernel.py --sync-synth <phase> --live"
    return {
        "bridge_owns": [
            "Cheap synthesis of raw_seed.md, prior passes, and observe dumps.",
            "Initial extract/evolve synth_seed authority from raw seed or observe history.",
            "Routine in-scope probing and plan drafting when the controller is not at a durable proof/approval gate.",
        ],
        "ide_owns": [
            "Local review is reserved for durable controller gates such as contradiction_block and apply_review_pending, or for explicit out-of-universe redirects.",
            "Finding and evaluating files outside the current synth_seed / selected-shard universe when the controller seems blind.",
            f"Deliberate synth authority edits only at {synth_target}, followed by `{sync_command}`.",
        ],
        "ide_should_not": [
            "Re-summarize raw seed or previous passes if bridge-driven synthesis can do it.",
            "Wait in chat for bridge completion.",
            "Open a fresh Codex or Claude thread just because the loop paused; most pauses are pause-only and should resume from the same state file unless a durable gate explicitly requested a wake.",
            "Write synth authority into ad-hoc notes or markdown projections instead of synth_seed.json.",
        ],
    }


def build_resume_packet(state_path: Path, state: dict) -> dict:
    """Build a machine-readable agent handoff packet."""
    readiness = check_responses_ready(state) if state["stage"] == "observe_dispatched" else None
    action = _scope_command_fields(next_action(state), state_path, state, keys=("command",))
    attention = _scope_command_fields(
        compute_codex_attention(state),
        state_path,
        state,
        keys=("gate_command", "continue_command", "resume_command"),
    )
    dump_dir = _dump_dir(state)
    effective_manifest_path = str(state.get("observe_manifest_path") or "").strip()
    effective_observe_id = state.get("observe_session_id")
    matched_entry = None
    if _should_backfill_manifest_from_dump_dir(state):
        matched_entry = _find_history_entry_by_dump_dir(
            dump_dir,
            min_started_at=_history_lookup_min_started_at(state),
        )
    if matched_entry:
        effective_manifest_path = matched_entry
        try:
            matched_payload = json.loads((REPO_ROOT / matched_entry).read_text())
        except json.JSONDecodeError:
            matched_payload = {}
        effective_observe_id = matched_payload.get("observe_id") or effective_observe_id
    artifact_dir = _state_artifact_dir(state_path)
    resume_json_path = _relative(artifact_dir / "pipeline_resume.json")
    resume_md_path = _relative(artifact_dir / "pipeline_resume.md")
    cycle_summary_path = str(attention.get("cycle_summary_path") or "").strip()
    if not cycle_summary_path:
        current_cycle_dir = str(state.get("current_cycle_dir") or "").strip()
        candidate = f"{current_cycle_dir}/_cycle_summary.json" if current_cycle_dir else ""
        if candidate and (REPO_ROOT / candidate).exists():
            cycle_summary_path = candidate
    cycle_timeline_path = _load_cycle_timeline_path(
        state,
        manifest=matched_payload if matched_entry else None,
        cycle_summary_path=cycle_summary_path or None,
    )
    cycle_assimilation_path = _load_cycle_assimilation_path(
        state,
        manifest=matched_payload if matched_entry else None,
        cycle_summary_path=cycle_summary_path or None,
    )
    carry_forward_context_path = _load_cycle_carry_forward_path(
        state,
        manifest=matched_payload if matched_entry else None,
        cycle_summary_path=cycle_summary_path or None,
    )
    snapshots = list_snapshots(state, repo_root=REPO_ROOT)

    source_context = {
        "generated_at": _utc_now(),
        "repo_root": str(REPO_ROOT),
        "pipeline_id": state["pipeline_id"],
        "state_path": _relative(state_path),
        "phase_dir": state["phase_dir"],
        "family_dir": state.get("family_dir"),
        "artifact_dir": _relative(artifact_dir),
        "stage": state["stage"],
        "cycle": state["cycle"],
        "controller_phase": state.get("controller_phase"),
        "current_layer_id": state.get("current_layer_id"),
        "current_layer_kind": state.get("current_layer_kind"),
        "current_task_id": state.get("current_task_id"),
        "gate_reason": state.get("gate_reason"),
        "routing_decision": state.get("routing_decision"),
        "observe_session_id": effective_observe_id,
        "observe_manifest_path": effective_manifest_path or None,
        "cycle_summary_path": cycle_summary_path or None,
        "cycle_timeline_path": cycle_timeline_path or None,
        "cycle_assimilation_path": cycle_assimilation_path or None,
        "carry_forward_context_path": carry_forward_context_path or None,
        "apply_plan_diagnostic_path": state.get("apply_plan_diagnostic_path"),
        "observe_plan_path": state.get("observe_plan_path"),
        "task_dag_path": state.get("task_dag_path"),
        "dump_dir": dump_dir,
        "current_cycle_synth_snapshot_path": state.get("current_cycle_synth_snapshot_path"),
        "active_scope": _active_scope(state),
        "response_readiness": readiness,
        "codex_attention": attention,
        "next_action": action,
        "latest_history": state.get("history", [])[-5:],
        "recovery": {
            "latest_snapshots": [
                {
                    "snapshot_id": item.get("snapshot_id"),
                    "cycle": item.get("cycle"),
                    "stage": item.get("stage"),
                    "reason": item.get("reason"),
                    "snapshot_path": item.get("snapshot_path"),
                }
                for item in snapshots[:5]
            ],
            "commands": {
                "snapshot": _scope_command_to_state(
                    "python3 pipeline_advance.py --snapshot --snapshot-reason manual_checkpoint",
                    state_path,
                    state,
                ),
                "list_snapshots": _scope_command_to_state(
                    "python3 pipeline_advance.py --list-snapshots",
                    state_path,
                    state,
                ),
                "reinit_from_synth": _scope_command_to_state(
                    "python3 pipeline_advance.py --reinit-from-synth",
                    state_path,
                    state,
                ),
            },
        },
        "recommended_commands": {
            "status": _scope_command_to_state("python3 pipeline_advance.py", state_path, state),
            "write_resume": _scope_command_to_state("python3 pipeline_advance.py --write-resume", state_path, state),
            "attention_gate": _scope_command_to_state("python3 pipeline_advance.py --attention-gate", state_path, state),
            "next_step": action["command"],
            "force_next_step": _scope_command_to_state("python3 pipeline_advance.py --force --advance", state_path, state),
            "automation_directive": _scope_command_to_state("python3 pipeline_advance.py --automation-directive", state_path, state),
            "signal_watch_once": _scope_command_to_state("python3 pipeline_signal_watcher.py --once --dry-run", state_path, state),
        },
        "artifacts": {
            "resume_json_path": resume_json_path,
            "resume_md_path": resume_md_path,
            "attention_json_path": _relative(artifact_dir / "pipeline_attention.json"),
            "attention_md_path": _relative(artifact_dir / "pipeline_attention.md"),
        },
    }

    # Context recovery pointers for post-overrun cold starts
    source_context["context_recovery"] = _build_context_recovery(state, state_path=state_path)
    source_context["environment_contract"] = build_env_contract(REPO_ROOT)
    source_context["authority_surfaces"] = _build_authority_surfaces(state, state_path=state_path)
    source_context["agent_operating_contract"] = _build_agent_operating_contract(state, state_path=state_path)

    source_context["codex_automation"] = build_codex_automation(source_context)
    source_context["codex_automation_directive"] = build_codex_automation_directive(source_context)
    wait_kind = "mission_controller" if state_path.name == "_mission_controller_state.json" else "pipeline_signal"
    return build_continuation_packet(
        REPO_ROOT,
        wait_kind=wait_kind,
        artifact_dir=_relative(artifact_dir),
        source_context=source_context,
    )


def _packet_context_file_list(packet: dict, *, limit: int = 6) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    active_scope = packet.get("active_scope") or {}
    routing = packet.get("routing_decision") or {}
    for source in (
        active_scope.get("active_scope_files") or [],
        active_scope.get("known_relevant_files") or [],
        routing.get("relevant_files") or [],
        routing.get("newly_relevant_files") or [],
    ):
        if not isinstance(source, list):
            continue
        for item in source:
            path = str(item or "").strip()
            if not path or path in seen:
                continue
            seen.add(path)
            ordered.append(path)
            if len(ordered) >= limit:
                return ordered
    return ordered


def _packet_context_lines(packet: dict, *, file_limit: int = 6) -> list[str]:
    lines: list[str] = []
    phase_dir = str(packet.get("phase_dir") or "").strip()
    family_dir = str(packet.get("family_dir") or "").strip()
    controller_phase = str(packet.get("controller_phase") or "").strip()
    current_layer_kind = str(packet.get("current_layer_kind") or "").strip()
    current_layer_id = str(packet.get("current_layer_id") or "").strip()
    current_task_id = str(packet.get("current_task_id") or "").strip()
    synth_snapshot = str(packet.get("current_cycle_synth_snapshot_path") or "").strip()
    active_scope = packet.get("active_scope") or {}
    selected_shard_count = int(active_scope.get("selected_shard_count") or 0)

    if phase_dir:
        lines.append(f"- Phase dir: {phase_dir}")
    if family_dir:
        lines.append(f"- Family dir: {family_dir}")
    if controller_phase or current_layer_kind or current_layer_id:
        layer_summary = current_layer_kind or controller_phase or "unknown"
        if current_layer_id:
            layer_summary = f"{layer_summary} ({current_layer_id})"
        lines.append(f"- Controller phase/layer: {controller_phase or current_layer_kind or 'unknown'} / {layer_summary}")
    if current_task_id:
        lines.append(f"- Current task: {current_task_id}")
    if selected_shard_count:
        lines.append(f"- Selected shards in scope: {selected_shard_count}")
    if synth_snapshot:
        lines.append(f"- Cycle synth snapshot: {synth_snapshot}")
    apply_plan_diagnostic = str(packet.get("apply_plan_diagnostic_path") or "").strip()
    if apply_plan_diagnostic:
        lines.append(f"- Apply plan diagnostic: {apply_plan_diagnostic}")
    known_scope_count = int(active_scope.get("known_relevant_count") or 0)
    if known_scope_count:
        lines.append(f"- Known relevant files: {known_scope_count}")

    relevant_files = _packet_context_file_list(packet, limit=file_limit)
    if relevant_files:
        lines.append(f"- Relevant files: {', '.join(relevant_files)}")
    return lines


def build_codex_resume_prompt(packet: dict) -> str:
    """Return a self-contained prompt for a later agent thread (Codex or Claude Code)."""
    return render_continuation_resume_prompt(packet)


def build_codex_wake_prompt(packet: dict) -> str:
    """Return a compact prompt for app deep links and terminal wake-ups."""
    return render_continuation_wake_prompt(packet)


def write_resume_artifacts(state_path: Path, state: dict) -> tuple[Path, Path]:
    """Write machine-readable and human-readable resume artifacts beside the controller state file."""
    packet = build_resume_packet(state_path, state)
    artifact_dir = _state_artifact_dir(state_path)
    resume_json = artifact_dir / "pipeline_resume.json"
    resume_md = artifact_dir / "pipeline_resume.md"
    attention_json = artifact_dir / "pipeline_attention.json"
    attention_md = artifact_dir / "pipeline_attention.md"

    packet = _preserve_generated_at_for_noop(resume_json, packet)
    _write_json_if_changed(resume_json, packet)
    write_continuation_packet(
        REPO_ROOT,
        artifact_dir=_relative(artifact_dir),
        packet=packet,
    )
    attention_payload = {
        "generated_at": packet["generated_at"],
        "pipeline_id": packet["pipeline_id"],
        "state_path": packet["state_path"],
        "continuation_packet_path": packet.get("continuation_packet_path"),
        "continuation_packet_fingerprint": packet.get("continuation_packet_fingerprint"),
        "stage": packet["stage"],
        "cycle": packet["cycle"],
        "controller_phase": packet.get("controller_phase"),
        "current_layer_id": packet.get("current_layer_id"),
        "current_layer_kind": packet.get("current_layer_kind"),
        "current_task_id": packet.get("current_task_id"),
        "gate_reason": packet.get("gate_reason"),
        "routing_decision": packet.get("routing_decision"),
        "active_scope": packet["active_scope"],
        "codex_attention": packet["codex_attention"],
        "carry_forward_context_path": packet.get("carry_forward_context_path"),
        "apply_plan_diagnostic_path": packet.get("apply_plan_diagnostic_path"),
        "cycle_assimilation_path": packet.get("cycle_assimilation_path"),
        "cycle_timeline_path": packet.get("cycle_timeline_path"),
        "cycle_summary_path": packet.get("cycle_summary_path"),
        "observe_manifest_path": packet.get("observe_manifest_path"),
        "next_action": packet["next_action"],
        "latest_history": packet["latest_history"],
    }
    attention_payload = _preserve_generated_at_for_noop(attention_json, attention_payload)
    _write_json_if_changed(attention_json, attention_payload)

    md_lines = [
        "# Pipeline Resume Packet",
        "",
        f"- Generated: `{packet['generated_at']}`",
        f"- Pipeline: `{packet['pipeline_id']}`",
        f"- Stage: `{packet['stage']}`",
        f"- Cycle: `{packet['cycle']}`",
        f"- Controller phase: `{packet.get('controller_phase')}`",
        f"- Current layer: `{packet.get('current_layer_kind')}` / `{packet.get('current_layer_id')}`",
        f"- Current task: `{packet.get('current_task_id')}`",
        f"- State file: `{packet['state_path']}`",
        f"- Continuation packet: `{packet.get('continuation_packet_path')}`",
    ]
    if packet.get("family_dir"):
        md_lines.append(f"- Family dir: `{packet['family_dir']}`")
    if packet.get("routing_decision"):
        md_lines.append(f"- Latest routing decision: `{(packet.get('routing_decision') or {}).get('decision')}`")
    if packet.get("apply_plan_diagnostic_path"):
        md_lines.append(f"- Apply plan diagnostic: `{packet['apply_plan_diagnostic_path']}`")
    if packet.get("observe_session_id"):
        md_lines.append(f"- Observe session: `{packet['observe_session_id']}`")
    if packet.get("observe_manifest_path"):
        md_lines.append(f"- Observe manifest: `{packet['observe_manifest_path']}`")
    if packet.get("cycle_assimilation_path"):
        md_lines.append(f"- Cycle assimilation: `{packet['cycle_assimilation_path']}`")
    if packet.get("cycle_timeline_path"):
        md_lines.append(f"- Cycle timeline: `{packet['cycle_timeline_path']}`")
    if packet.get("dump_dir"):
        md_lines.append(f"- Dump dir: `{packet['dump_dir']}`")

    readiness = packet.get("response_readiness") or {}
    if readiness:
        md_lines.extend(
            [
                "",
                "## Bridge Readiness",
                "",
                f"- Ready: `{readiness.get('ready')}`",
                f"- Status: `{readiness.get('status')}`",
            ]
        )
        if "responses_found" in readiness and "groups_expected" in readiness:
            md_lines.append(
                f"- Progress: `{readiness.get('responses_found')}` / `{readiness.get('groups_expected')}`"
            )

    md_lines.extend(
        [
            "",
            "## Next Action",
            "",
            f"- Summary: {packet['next_action']['summary']}",
            f"- Command: `{packet['next_action']['command']}`",
            "",
            "## Environment Contract",
            "",
        ]
    )
    env_contract = packet.get("environment_contract") or {}
    env_commands = env_contract.get("commands") if isinstance(env_contract.get("commands"), dict) else {}
    if env_contract.get("resolved_env_root"):
        md_lines.append(f"- Resolved env root: `{env_contract['resolved_env_root']}`")
    if env_contract.get("resolved_from"):
        md_lines.append(f"- Resolved from: `{env_contract['resolved_from']}`")
    if env_contract.get("resolved_python"):
        md_lines.append(f"- Resolved python: `{env_contract['resolved_python']}`")
    for label, key in [
        ("Repo python", "repo_python"),
        ("Repo pytest", "repo_pytest"),
        ("Repo env", "repo_env"),
    ]:
        if env_commands.get(key):
            md_lines.append(f"- {label}: `{env_commands[key]}`")
    for rule in env_contract.get("rules", []):
        md_lines.append(f"- Rule: {rule}")

    md_lines.extend(
        [
            "",
            "## Authority Surfaces",
            "",
        ]
    )
    authority = packet.get("authority_surfaces") or {}
    for label, key in [
        ("Raw seed", "raw_seed"),
        ("Synth seed", "synth_seed"),
        ("Reference ledger", "reference_ledger"),
        ("Meta ledger", "meta_ledger"),
        ("Apply plan", "apply_plan"),
        ("Apply packet", "apply_packet"),
    ]:
        card = authority.get(key) if isinstance(authority.get(key), dict) else None
        if card and card.get("path"):
            md_lines.append(f"- {label}: `{card['path']}`")
    commands = authority.get("commands") if isinstance(authority.get("commands"), dict) else {}
    if commands.get("extract_synth_from_raw_seed"):
        md_lines.append(f"- Bridge synth refresh: `{commands['extract_synth_from_raw_seed']}`")
    if commands.get("sync_synth_markdown"):
        md_lines.append(f"- Sync synth markdown: `{commands['sync_synth_markdown']}`")
    synth_refresh = authority.get("synth_refresh") if isinstance(authority.get("synth_refresh"), dict) else {}
    if synth_refresh:
        md_lines.append(f"- Synth refresh needed: `{synth_refresh.get('needed')}`")
        md_lines.append(f"- Synth refresh reason: `{synth_refresh.get('reason')}`")
    for rule in authority.get("write_rules", []):
        md_lines.append(f"- Rule: {rule}")

    md_lines.extend(
        [
            "",
            "## Agent Operating Contract",
            "",
        ]
    )
    contract = packet.get("agent_operating_contract") or {}
    for item in contract.get("bridge_owns", []):
        md_lines.append(f"- Bridge owns: {item}")
    for item in contract.get("ide_owns", []):
        md_lines.append(f"- IDE owns: {item}")
    for item in contract.get("ide_should_not", []):
        md_lines.append(f"- IDE should not: {item}")

    md_lines.extend(
        [
            "",
            "## Active Scope",
            "",
            f"- Selected shards: `{packet['active_scope']['selected_shard_count']}`",
            f"- Concepts: `{', '.join(packet['active_scope']['concept_groups'])}`",
            f"- Shard IDs: `{', '.join(packet['active_scope']['selected_shard_ids'][:10])}`",
            "",
            "## Codex Attention Gate",
            "",
            f"- Needs attention: `{packet['codex_attention']['needs_attention']}`",
            f"- Reason: `{packet['codex_attention']['reason_key']}`",
            f"- Summary: {packet['codex_attention']['summary']}",
            f"- Auto pause: `{packet['codex_attention'].get('pause_pipeline', False)}`",
        ]
    )
    if packet["codex_attention"].get("pause_pipeline"):
        md_lines.append(f"- Resume automation: `{packet['codex_attention'].get('resume_command')}`")
    if packet.get("cycle_assimilation_path"):
        md_lines.append(f"- Cycle assimilation: `{packet['cycle_assimilation_path']}`")
    if packet.get("cycle_timeline_path"):
        md_lines.append(f"- Cycle timeline: `{packet['cycle_timeline_path']}`")
    for detail in packet["codex_attention"]["details"]:
        md_lines.append(f"- Detail: {detail}")
    md_lines.extend(
        [
            "",
            "## Codex App Automation",
            "",
            f"- Name: `{packet['codex_automation']['name']}`",
            f"- Suggested cadence: `{packet['codex_automation']['rrule']}`",
            f"- Workspace: `{packet['codex_automation']['cwds']}`",
            f"- Note: {packet['codex_automation']['notes']}",
            "",
            "```text",
            packet["codex_automation_directive"],
            "```",
            "",
            "## Agent Resume Prompt",
            "",
            "```text",
            packet["codex_resume_prompt"],
            "```",
        ]
    )

    # Context recovery section
    recovery = packet.get("context_recovery") or {}
    if recovery:
        md_lines.extend([
            "",
            "## Context Recovery (post-overrun / cold start)",
            "",
        ])
        if recovery.get("synth_seed_path"):
            md_lines.append(f"- Synth seed (intent + shards): `{recovery['synth_seed_path']}`")
        if recovery.get("raw_seed_path"):
            md_lines.append(f"- Raw seed (original voice): `{recovery['raw_seed_path']}`")
        md_lines.append(f"- CLAUDE.md: `{recovery.get('claude_md_path', 'CLAUDE.md')}`")
        md_lines.append(f"- CODEX.md: `{recovery.get('codex_md_path', 'CODEX.md')}`")
        for instruction in recovery.get("recovery_instructions", []):
            md_lines.append(f"- {instruction}")

    _write_text_if_changed(resume_md, "\n".join(md_lines) + "\n")
    attention_lines = [
        "# Pipeline Attention Gate",
        "",
        f"- Generated: `{packet['generated_at']}`",
        f"- Pipeline: `{packet['pipeline_id']}`",
        f"- Stage: `{packet['stage']}`",
        f"- Cycle: `{packet['cycle']}`",
        f"- Controller phase: `{packet.get('controller_phase')}`",
        f"- Current layer: `{packet.get('current_layer_kind')}` / `{packet.get('current_layer_id')}`",
        f"- Current task: `{packet.get('current_task_id')}`",
        f"- Needs attention: `{packet['codex_attention']['needs_attention']}`",
        f"- Reason: `{packet['codex_attention']['reason_key']}`",
        f"- Summary: {packet['codex_attention']['summary']}",
        f"- Auto pause: `{packet['codex_attention'].get('pause_pipeline', False)}`",
        f"- Gate command: `{packet['codex_attention']['gate_command']}`",
        f"- Continue command: `{packet['codex_attention']['continue_command']}`",
        f"- Cycle assimilation: `{packet.get('cycle_assimilation_path')}`",
        f"- Cycle timeline: `{packet.get('cycle_timeline_path')}`",
        "",
        "## Active Scope",
        "",
        f"- Selected shards: `{packet['active_scope']['selected_shard_count']}`",
        f"- Concepts: `{', '.join(packet['active_scope']['concept_groups'])}`",
    ]
    if packet["codex_attention"].get("pause_pipeline"):
        attention_lines.append(f"- Resume automation: `{packet['codex_attention'].get('resume_command')}`")
    for detail in packet["codex_attention"]["details"]:
        attention_lines.append(f"- Detail: {detail}")
    attention_lines.extend(
        [
            "",
            "## Recent History",
            "",
        ]
    )
    for event in packet["latest_history"]:
        attention_lines.append(
            f"- {event.get('timestamp', '?')} | {event.get('stage', '?')} | {event.get('action', '?')} | {event.get('detail', '')}"
        )
    _write_text_if_changed(attention_md, "\n".join(attention_lines) + "\n")
    return resume_json, resume_md


def create_phase_snapshot(state_path: Path, state: dict, *, reason: str) -> dict:
    snapshot = create_snapshot(state_path, state, reason=reason, repo_root=REPO_ROOT, source="manual")
    write_resume_artifacts(state_path, state)
    return snapshot


def restore_phase_snapshot(state_path: Path, state: dict, *, snapshot_id: str) -> dict:
    result = restore_snapshot(state_path, state, snapshot_id, repo_root=REPO_ROOT)
    restored_state = dict(result["restored_state"])
    ensure_controller_state(restored_state, repo_root=REPO_ROOT)
    write_controller_artifacts(restored_state, repo_root=REPO_ROOT)
    state_path.write_text(json.dumps(restored_state, indent=2) + "\n")
    write_resume_artifacts(state_path, restored_state)
    return {
        "restored_snapshot": {
            "snapshot_id": result["snapshot"].get("snapshot_id"),
            "snapshot_path": result["snapshot"].get("snapshot_path"),
            "reason": result["snapshot"].get("reason"),
        },
        "backup_snapshot": {
            "snapshot_id": result["backup_snapshot"].get("snapshot_id"),
            "snapshot_path": result["backup_snapshot"].get("snapshot_path"),
            "reason": result["backup_snapshot"].get("reason"),
        },
        "state": restored_state,
    }


def reinitialize_phase_from_synth(state_path: Path, state: dict, *, archive_runtime: bool = True) -> dict:
    from seed_pipeline import init_state, save_state

    pre_reinit_snapshot = create_snapshot(
        state_path,
        state,
        reason="before_reinit_from_synth",
        repo_root=REPO_ROOT,
        source="manual",
    )
    archive_manifest = None
    if archive_runtime:
        archive_manifest = archive_phase_runtime(
            state,
            reason="reinit_from_synth",
            repo_root=REPO_ROOT,
        )

    fresh_state = init_state(
        str(state.get("raw_seed_path") or "").strip(),
        str(state.get("phase_dir") or "").strip(),
        str(state.get("family_dir") or "").strip() or None,
    )
    write_controller_artifacts(fresh_state, repo_root=REPO_ROOT)
    save_state(fresh_state, state_path)
    baseline_snapshot = create_snapshot(
        state_path,
        fresh_state,
        reason="post_reinit_clean_baseline",
        repo_root=REPO_ROOT,
        source="manual",
    )
    write_resume_artifacts(state_path, fresh_state)
    return {
        "status": "reinitialized",
        "pre_reinit_snapshot": {
            "snapshot_id": pre_reinit_snapshot.get("snapshot_id"),
            "snapshot_path": pre_reinit_snapshot.get("snapshot_path"),
        },
        "archive": archive_manifest,
        "baseline_snapshot": {
            "snapshot_id": baseline_snapshot.get("snapshot_id"),
            "snapshot_path": baseline_snapshot.get("snapshot_path"),
        },
        "state": fresh_state,
    }


def archive_future_cycles(state_path: Path, state: dict, *, after_cycle: int) -> dict:
    archive_manifest = archive_cycles_after(
        state,
        after_cycle=after_cycle,
        reason=f"archive_cycles_after_{after_cycle}",
        repo_root=REPO_ROOT,
    )
    write_resume_artifacts(state_path, state)
    return archive_manifest


def status_report(state: dict, *, state_path: Path | None = None) -> str:
    """Generate a concise status report."""
    lines = [
        f"Pipeline: {state['pipeline_id']}",
        f"Stage: {state['stage']}",
        f"Cycle: {state['cycle']}",
        f"Controller: {state.get('controller_phase')}",
        f"Layer: {state.get('current_layer_kind')} / {state.get('current_layer_id')}",
        f"Task: {state.get('current_task_id')}",
    ]
    if state.get("routing_decision"):
        lines.append(f"Routing: {(state.get('routing_decision') or {}).get('decision')}")

    if state["stage"] == "observe_dispatched":
        resp = check_responses_ready(state)
        lines.append(f"Bridge: {resp['status']}")
        if "nodes_done" in resp:
            lines.append(f"Progress: {resp['nodes_done']}/{resp['nodes_total']} nodes done")
        lines.append(f"Ready: {resp['ready']}")
    attention = compute_codex_attention(state)
    if attention.get("needs_attention"):
        lines.append(f"ATTENTION: {attention['summary']}")
    action = next_action(state)
    if state_path is not None:
        action = _scope_command_fields(action, state_path, state, keys=("command",))
    lines.append(f"ACTION: {action['summary']}")
    lines.append(f"COMMAND: {action['command']}")

    return "\n".join(lines)


def attention_gate_exit_code(attention: dict, *, exit_mode: str = "clear-ok") -> int:
    needs_attention = bool(attention.get("needs_attention"))
    if exit_mode == "predicate":
        return 0 if needs_attention else 1
    return 1 if needs_attention else 0


def main():
    import argparse
    runtime_policy = _runtime_policy()
    parser = argparse.ArgumentParser()
    parser.add_argument("--advance", action="store_true")
    parser.add_argument("--check-responses", action="store_true")
    parser.add_argument("--write-resume", action="store_true")
    parser.add_argument("--resume-prompt", action="store_true")
    parser.add_argument("--automation-directive", action="store_true")
    parser.add_argument("--attention-gate", action="store_true")
    parser.add_argument(
        "--attention-exit-mode",
        choices=("clear-ok", "predicate"),
        default="clear-ok",
        help=(
            "Exit-code contract for --attention-gate: clear-ok treats no-attention as success; "
            "predicate preserves the old shell-test behavior where attention-needed exits 0."
        ),
    )
    parser.add_argument("--repair-results", action="store_true")
    parser.add_argument("--snapshot", action="store_true")
    parser.add_argument("--snapshot-reason", default="manual_snapshot")
    parser.add_argument("--list-snapshots", action="store_true")
    parser.add_argument("--restore-snapshot", type=str)
    parser.add_argument("--reinit-from-synth", action="store_true")
    parser.add_argument("--archive-cycles-after", type=int)
    parser.add_argument("--from-cycle", type=int)
    parser.add_argument("--to-cycle", type=int)
    parser.add_argument("--state", type=str, help="Explicit pipeline/controller state path. Defaults to active phase discovery.")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--bridge", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--provider", default="chatgpt")
    parser.add_argument(
        "--launch-profile",
        default=str(runtime_policy["default_launch_profile"]),
        help="Observe launch profile for bridge dispatch (safe or experimental).",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    state_path, state = find_state(args.state)
    if not state:
        if args.state:
            print(f"No pipeline state found at: {args.state}")
        else:
            print("No pipeline state found.")
        sys.exit(1)

    if args.check_responses:
        result = check_responses_ready(state)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for k, v in result.items():
                print(f"  {k}: {v}")
        sys.exit(check_responses_exit_code(result))

    if args.write_resume:
        resume_json, resume_md = write_resume_artifacts(state_path, state)
        if args.json:
            print(json.dumps({
                "resume_json": _relative(resume_json),
                "resume_md": _relative(resume_md),
            }, indent=2))
        else:
            print(f"resume_json: {_relative(resume_json)}")
            print(f"resume_md: {_relative(resume_md)}")
        return

    if args.resume_prompt:
        packet = build_resume_packet(state_path, state)
        if args.json:
            print(json.dumps({"codex_resume_prompt": packet["codex_resume_prompt"]}, indent=2))
        else:
            print(packet["codex_resume_prompt"])
        return

    if args.automation_directive:
        packet = build_resume_packet(state_path, state)
        if args.json:
            print(json.dumps({
                "codex_automation": packet["codex_automation"],
                "codex_automation_directive": packet["codex_automation_directive"],
            }, indent=2))
        else:
            print(packet["codex_automation_directive"])
        return

    if args.attention_gate:
        attention = compute_codex_attention(state)
        if args.json:
            print(json.dumps(attention, indent=2))
        else:
            for k, v in attention.items():
                print(f"{k}: {v}")
        sys.exit(attention_gate_exit_code(attention, exit_mode=args.attention_exit_mode))

    if args.snapshot:
        snapshot = create_phase_snapshot(
            state_path,
            state,
            reason=str(args.snapshot_reason or "manual_snapshot").strip() or "manual_snapshot",
        )
        if args.json:
            print(json.dumps(snapshot, indent=2))
        else:
            print(f"snapshot_id: {snapshot['snapshot_id']}")
            print(f"snapshot_path: {snapshot['snapshot_path']}")
            print(f"reason: {snapshot['reason']}")
        return

    if args.list_snapshots:
        snapshots = list_snapshots(state, repo_root=REPO_ROOT)
        if args.json:
            print(json.dumps({"snapshots": snapshots}, indent=2))
        else:
            if not snapshots:
                print("No recovery snapshots found.")
            for snapshot in snapshots:
                print(
                    f"{snapshot.get('snapshot_id')} | cycle={snapshot.get('cycle')} | "
                    f"stage={snapshot.get('stage')} | reason={snapshot.get('reason')}"
                )
        return

    if args.restore_snapshot:
        result = restore_phase_snapshot(
            state_path,
            state,
            snapshot_id=str(args.restore_snapshot).strip(),
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"restored_snapshot: {result['restored_snapshot']['snapshot_id']}")
            print(f"backup_snapshot: {result['backup_snapshot']['snapshot_id']}")
            print(f"stage: {result['state']['stage']}")
            print(f"cycle: {result['state']['cycle']}")
        return

    if args.reinit_from_synth:
        result = reinitialize_phase_from_synth(state_path, state, archive_runtime=True)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"status: {result['status']}")
            print(f"pre_reinit_snapshot: {result['pre_reinit_snapshot']['snapshot_id']}")
            archive = result.get("archive") or {}
            if archive.get("archive_id"):
                print(f"archive_id: {archive['archive_id']}")
                print(f"archived_entries: {archive.get('entry_count', 0)}")
            print(f"baseline_snapshot: {result['baseline_snapshot']['snapshot_id']}")
            print(f"stage: {result['state']['stage']}")
            print(f"cycle: {result['state']['cycle']}")
        return

    if args.archive_cycles_after is not None:
        result = archive_future_cycles(state_path, state, after_cycle=int(args.archive_cycles_after))
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"archive_id: {result.get('archive_id')}")
            print(f"archived_entries: {result.get('entry_count', 0)}")
            print(f"archive_root: {result.get('archive_root')}")
        return

    if args.repair_results:
        if args.from_cycle is None or args.to_cycle is None:
            raise SystemExit("--repair-results requires --from-cycle and --to-cycle")
        from seed_pipeline import repair_results_range
        result = repair_results_range(
            state,
            from_cycle=int(args.from_cycle),
            to_cycle=int(args.to_cycle),
            apply=bool(args.apply),
        )
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
        return

    if args.advance:
        try:
            from system.control.orchestration import load_orchestration_state, selected_action

            orchestration = load_orchestration_state(repo_root=REPO_ROOT, refresh=True)
            selected = selected_action(orchestration)
            selected_command = str(selected.get("command") or "").strip()
            if not selected_command:
                payload = {
                    "status": "blocked",
                    "active_driver": orchestration.get("active_driver"),
                    "summary": selected.get("summary"),
                    "gate": orchestration.get("gate"),
                }
                if args.json:
                    print(json.dumps(payload, indent=2))
                else:
                    print(f"[GATE] {payload['summary'] or 'No executable action is currently recommended.'}")
                raise SystemExit(1)
            if "pipeline_advance.py" not in selected_command:
                result = subprocess.run(
                    shlex.split(selected_command),
                    cwd=str(REPO_ROOT),
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if args.json:
                    print(
                        json.dumps(
                            {
                                "status": "ok" if result.returncode == 0 else "failed",
                                "active_driver": orchestration.get("active_driver"),
                                "command": selected_command,
                                "stdout": result.stdout,
                                "stderr": result.stderr,
                                "returncode": result.returncode,
                            },
                            indent=2,
                        )
                    )
                else:
                    if result.stdout.strip():
                        print(result.stdout.rstrip())
                    if result.stderr.strip():
                        print(result.stderr.rstrip(), file=sys.stderr)
                raise SystemExit(result.returncode)

            selected_tokens = shlex.split(selected_command)
            if "--bridge" in selected_tokens:
                args.bridge = True
            if "--provider" in selected_tokens:
                idx = selected_tokens.index("--provider")
                if idx + 1 < len(selected_tokens):
                    args.provider = selected_tokens[idx + 1]
            if "--launch-profile" in selected_tokens:
                idx = selected_tokens.index("--launch-profile")
                if idx + 1 < len(selected_tokens):
                    args.launch_profile = selected_tokens[idx + 1]
        except Exception:
            orchestration = None

        selected_pipeline_action = next_action(state)
        prepare_state_for_action(state, selected_pipeline_action)

        attention = compute_codex_attention(state)
        if attention.get("needs_attention") and not args.force:
            write_resume_artifacts(state_path, state)
            print(f"[GATE] {attention['summary']}")
            if attention.get("details"):
                for detail in attention["details"]:
                    print(f"  - {detail}")
            print(f"[GATE] Review with: {attention['gate_command']}")
            print(f"[GATE] Continue mechanically only if intended: {attention['continue_command']}")
            if args.json:
                print(json.dumps({"stage": state["stage"], "cycle": state["cycle"], "attention": attention}, indent=2))
            return
        # Import and run one step
        from seed_pipeline import run_step, save_state_if_not_stale
        new_stage = run_step(
            state,
            bridge_enabled=args.bridge,
            provider=args.provider,
            launch_profile=args.launch_profile,
            auto=True,
            state_path=state_path,
        )
        save_state_if_not_stale(state, state_path)
        write_resume_artifacts(state_path, state)
        print(f"Advanced: {new_stage}")
        if args.json:
            print(json.dumps({"stage": new_stage, "cycle": state["cycle"]}, indent=2))
        return

    # Default: status report
    report = status_report(state, state_path=state_path)
    try:
        from system.control.orchestration import load_orchestration_state

        orchestration = load_orchestration_state(repo_root=REPO_ROOT, refresh=True)
        decision = orchestration.get("decision") if isinstance(orchestration.get("decision"), dict) else {}
        gate = orchestration.get("gate") if isinstance(orchestration.get("gate"), dict) else {}
        print(
            "ORCHESTRATION\n"
            f"  active driver: {orchestration.get('active_driver')}\n"
            f"  immediate mode: {decision.get('immediate_mode')}\n"
            f"  gate: {gate.get('gate_reason') or 'none'}\n"
            f"  next: {decision.get('command') or decision.get('summary')}\n"
        )
    except Exception:
        pass
    print(report)
    if args.json:
        print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
