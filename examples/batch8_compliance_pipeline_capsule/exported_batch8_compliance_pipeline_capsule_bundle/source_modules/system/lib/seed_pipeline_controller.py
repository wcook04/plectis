"""
[PURPOSE]
- Teleology: Own the phase-native controller metadata for synth-first observe/apply loops by normalizing controller state, projecting runtime artifacts, framing observe briefs, and routing completed receipts into the next controller phase.
- Mechanism: Read phase/family scaffold artifacts, synth surfaces, and controller config; write digest/system-view/apply/task projections; expose helpers that constrain shard selection and advance state after scope/probe/plan results.

[INTERFACE]
- Exports: Controller config/state helpers, artifact writers, observe brief generation, routing guards, controller advancement, task-DAG projections, and analytics/reporting helpers listed in `__all__`.
- Reads: phase_scaffold.json, synth_seed.json, family markers, pipeline config, current cycle summaries, and runtime controller artifacts.
- Writes: raw_seed_digest.json, system_view.json, task_dag.json, task_backlog.json, apply_plan.json, apply_packet.json, focus_directive.json, and in-memory controller-state normalization.

[FLOW]
- Normalize controller state and phase aliases -> project digest/system/task artifacts -> build observe briefs and file scopes for the current phase -> guard routing decisions and advance after typed receipts -> expose analytics and task-DAG projections to downstream stages.
- When-needed: Open when a pipeline question is really about the controller contract rather than one individual stage file.
- Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline_recovery.py; system/lib/phase_harbor.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- pipeline_control: Supplies repo-level controller configuration.
- system.lib.observe_apply_contracts: Supplies synth normalization, standards-bundle resolution, and synth-derived intent/success criteria.
- system.lib.observe_runtime: Supplies degraded-group summarization used in routing and analytics.
- system.control.orchestration: Receives refreshed orchestration artifacts after controller writes.

[CONSTRAINTS]
- Guarantee: Controller writes remain JSON-first and apply execution remains gated behind `kernel.py --apply`; this module only prepares state and artifacts for that boundary.
- Non-goal: This module does not execute apply plans or dispatch bridge work itself.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable, Mapping

from pipeline_control import load_master_config
from system.lib.codex_paths import canonicalize_write_path
from system.lib.observe_apply_contracts import (
    PENDING_SYNTH_AUTHORING,
    normalize_assimilation_targets,
    normalize_current_wave,
    normalize_orientation,
    normalize_synthesis_memory,
    normalize_synth_payload,
    resolve_observe_apply_standards_bundle,
    synth_goal_text,
    synth_relevant_file_paths,
    synth_success_criteria_list,
    synth_success_criteria_text,
)
from system.lib.observe_runtime import summarize_degraded_group_diagnostics

REPO_ROOT = Path(__file__).resolve().parents[2]

CONTROLLER_VERSION = "phase_native_dynamic"
CONTROLLER_PHASES = (
    "scope",
    "probe",
    "plan",
    "apply_review_pending",
    "blocked",
)
BLOCKING_GATE_REASONS = {
    "apply_review_pending",
    "uncertainty_block",
    "contradiction_block",
    "error_spike_block",
}
DEFAULT_WAKE_CONDITIONS = [
    "apply_review_pending",
    "contradiction_block",
    "backlog_bloat_block",
]
LEGACY_PHASE_MIRRORS = {
    "task_curation": "scope",
    "problem_space_mapping": "scope",
    "solution_space_mapping": "probe",
    "plan_refinement": "plan",
    "apply_review_pending": "apply_review_pending",
    "scope": "scope",
    "deep_probe": "probe",
    "solution_compare": "probe",
    "plan": "plan",
    "blocked": "blocked",
}
SYSTEM_VIEW_IGNORE_PARTS = {
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    "command_cache",
    "command_outputs",
}
SYSTEM_VIEW_IGNORE_PREFIXES = (
    "<private-obsidian-root>/meta/observe_sessions/",
    "state/command_cache/",
    "state/command_outputs/",
    "tools/meta/apply/observe_history/",
    "tools/meta/apply/observe_dumps/",
    "tools/meta/apply/observe_plans/",
    "sandbox/",
)
DEFAULT_CONSTRAINTS = [
    "Bridge reasoning remains JSON-first after synth_seed creation.",
    "kernel.py --apply is the only mutation engine.",
    "Apply remains human or IDE gated before execution.",
]
DEFAULT_APPLY_BOUNDARY = {
    "review_required": True,
    "apply_via": "kernel.py --apply",
    "mutator": "kernel",
}
PHASE_STEP_STAGE_KINDS = ("problem_space", "solution_space", "plan_space")
PHASE_STEP_DECISIONS = ("clarify", "advance", "reframe", "escalate", "abort", "complete")
PHASE_STEP_ACTIVE_WAVE_STATUSES = {"dispatched", "in_flight", "awaiting_barrier", "awaiting_review"}
PHASE_STEP_TERMINAL_WAVE_STATUSES = {
    "aborted",
    "assimilated",
    "cancelled",
    "closed",
    "completed",
    "done",
    "superseded",
}
PHASE_STEP_DEFAULT_MAX_CLARIFY_DEPTH = 2
PHASE_STEP_BUILTIN_RUBRICS = {
    "problem_space": {
        "rubric_id": "builtin:problem_space",
        "title": "Problem-space checkpoint rubric",
        "checks": [
            "Surface grounded facts from the current slice before widening scope.",
            "Name the open questions or insufficiencies that still block a clean frame.",
            "Decide whether the frame is sufficient to advance, needs clarification, or should escalate/abort.",
        ],
    },
    "solution_space": {
        "rubric_id": "builtin:solution_space",
        "title": "Solution-space checkpoint rubric",
        "checks": [
            "Compare bounded candidate approaches against the active scope and evidence.",
            "Name the tradeoffs or insufficiencies that still block a confident plan.",
            "Decide whether to advance, clarify in-stage, reframe the problem, or escalate/abort.",
        ],
    },
    "plan_space": {
        "rubric_id": "builtin:plan_space",
        "title": "Plan-space checkpoint rubric",
        "checks": [
            "Produce a sequenced plan that is ready for apply-gate or higher-level handoff.",
            "Name any insufficiencies that still block operator-gated apply or phase handoff.",
            "Decide whether the plan is complete, needs clarification, should reframe, or must escalate/abort.",
        ],
    },
}
PHASE_STEP_DECISION_MATRIX = {
    "problem_space": {"clarify", "advance", "escalate", "abort"},
    "solution_space": {"clarify", "advance", "reframe", "escalate", "abort"},
    "plan_space": {"clarify", "reframe", "escalate", "abort", "complete"},
}
SCOPE_RECEIPT_SCHEMA = {
    "schema_id": "scope_receipt_v1",
    "type": "object",
    "required": [
        "relevant_files",
        "newly_relevant_files",
        "dropped_files",
        "rationale",
        "confidence",
    ],
    "properties": {
        "relevant_files": {"type": "array", "items": {"type": "string"}},
        "newly_relevant_files": {"type": "array", "items": {"type": "string"}},
        "dropped_files": {"type": "array", "items": {"type": "string"}},
        "rationale": {"type": "string"},
        "confidence": {"type": "number"},
    },
}
PROBE_RECEIPT_SCHEMA = {
    "schema_id": "probe_receipt_v2",
    "type": "object",
    "required": [
        "files_examined",
        "shard_updates",
    ],
    "properties": {
        "files_examined": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of file paths examined (plain path strings only).",
        },
        "findings": {
            "type": "array",
            "description": "Short plain-text summary per finding. Never embed raw code.",
            "items": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "One-sentence plain-text finding."},
                    "file": {"type": "string", "description": "File path where evidence was found."},
                    "status": {"type": "string", "description": "confirmed | contradicted | partial | unknown"},
                },
            },
        },
        "missing_evidence": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Plain-text descriptions of what evidence is still missing.",
        },
        "shard_updates": {
            "type": "array",
            "description": "Status update per shard. Use plain text, never raw code.",
            "items": {
                "type": "object",
                "properties": {
                    "shard_id": {"type": "string"},
                    "status": {"type": "string", "description": "grounded | partial | contradicted | blocked | open"},
                    "summary": {"type": "string", "description": "One-sentence plain-text status update."},
                },
            },
        },
    },
}
ROUTER_RECEIPT_SCHEMA = {
    "schema_id": "router_receipt_v2",
    "type": "object",
    "required": [
        "decision",
        "next_phase",
        "confidence",
        "reasoning",
        "newly_relevant_files",
        "shard_updates",
    ],
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["continue_probe", "expand_scope", "advance_to_plan", "blocked"],
        },
        "next_phase": {"type": "string", "enum": ["probe", "scope", "plan", "blocked"]},
        "confidence": {"type": "number"},
        "reasoning": {"type": "string", "description": "Short plain-text rationale. No code."},
        "newly_relevant_files": {"type": "array", "items": {"type": "string"}},
        "shard_updates": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "shard_id": {"type": "string"},
                    "status": {"type": "string"},
                    "summary": {"type": "string", "description": "Plain text, no code."},
                },
            },
        },
        "plan_outline": {"type": "array", "items": {"type": "string"}},
    },
}
PLAN_RECEIPT_SCHEMA = {
    "schema_id": "plan_receipt_v2",
    "type": "object",
    "required": [
        "decision",
        "confidence",
        "reasoning",
        "apply_plan",
        "verification",
    ],
    "properties": {
        "decision": {
            "type": "string",
            "enum": ["apply_review_ready", "continue_probe", "blocked"],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": "string"},
        "apply_plan": {
            "type": "object",
            "description": (
                "Executable kernel apply payload only. Descriptive edit inventories are invalid. "
                "Return either a non-empty `operations` list or a non-empty unified diff field."
            ),
            "anyOf": [
                {
                    "required": ["operations"],
                    "properties": {
                        "operations": {
                            "type": "array",
                            "minItems": 1,
                            "items": {"type": "object"},
                        }
                    },
                },
                {
                    "required": ["unified_diff"],
                    "properties": {
                        "unified_diff": {"type": "string", "minLength": 1}
                    },
                },
                {
                    "required": ["diff"],
                    "properties": {
                        "diff": {"type": "string", "minLength": 1}
                    },
                },
                {
                    "required": ["patch"],
                    "properties": {
                        "patch": {"type": "string", "minLength": 1}
                    },
                },
            ],
        },
        "verification": {"type": "array", "items": {"type": "string"}},
    },
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _config_value(value: Any, default: Any) -> Any:
    if isinstance(value, Mapping) and "value" in value:
        return value.get("value", default)
    return value if value is not None else default


def _clamp_score(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = 0.0
    return round(max(0.0, min(1.0, parsed)), 3)


def _read_json(path: Path, *, default: Any = None) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _write_json(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return path


def _phase_scaffold_payload(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Mapping[str, Any]:
    phase_dir = _phase_dir(state, repo_root=repo_root)
    payload = _read_json(phase_dir / "phase_scaffold.json", default=None)
    return payload if isinstance(payload, Mapping) else {}


def controller_version_for_state(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> str:
    """
    [ACTION]
    - Teleology: Derive the canonical controller version string for a given state by inspecting phase scaffold and state fields.
    - Guarantee: Returns a non-empty version string from scaffold, state override, phase-dir prefix, or fallback constant.
    - Fails: None.
    """
    scaffold = _phase_scaffold_payload(state, repo_root=repo_root)
    for key in ("phase_number", "phase_id"):
        token = str(scaffold.get(key) or "").strip()
        if token:
            return token
    existing = str(state.get("controller_version") or "").strip()
    if existing and existing != CONTROLLER_VERSION:
        return existing
    phase_dir = _phase_dir(state, repo_root=repo_root)
    match = re.match(r"^(\d+(?:\.\d+)*)\b", phase_dir.name.strip())
    if match:
        return match.group(1)
    phase_id = str(state.get("phase_id") or "").strip()
    if phase_id:
        return phase_id
    return CONTROLLER_VERSION


def family_dir_for_state(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> str:
    """
    [ACTION]
    - Teleology: Resolve the family directory string for a given controller state.
    - Guarantee: Returns a repo-relative family dir string, falling back to the phase dir when no family marker is found.
    - Fails: None.
    """
    scaffold = _phase_scaffold_payload(state, repo_root=repo_root)
    family_dir = str(scaffold.get("family_dir") or state.get("family_dir") or "").strip()
    if family_dir:
        return family_dir
    phase_dir = _phase_dir(state, repo_root=repo_root)
    obsidian_root = (repo_root / "obsidian").resolve()
    for current in [phase_dir, *phase_dir.parents]:
        try:
            current.relative_to(obsidian_root)
        except ValueError:
            break
        marker_payload = _read_json(current / "phase_family.json", default=None)
        if isinstance(marker_payload, Mapping):
            marker_family_dir = str(marker_payload.get("family_dir") or "").strip()
            if marker_family_dir:
                return marker_family_dir
        if all((current / name).exists() for name in ("raw_seed.md", "meta_ledger.json", "reference_ledger.json")):
            try:
                return str(current.relative_to(repo_root))
            except ValueError:
                break
    try:
        return str(phase_dir.relative_to(repo_root))
    except ValueError:
        return str(phase_dir)


def _relative(path: Path | str, *, repo_root: Path = REPO_ROOT) -> str:
    if path in (None, ""):
        return ""
    candidate = Path(path)
    try:
        return str(candidate.relative_to(repo_root))
    except ValueError:
        return str(candidate)


def _phase_dir(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    return repo_root / str(state.get("phase_dir") or "").strip()


def _current_cycle_dir(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT, cycle: int | None = None) -> Path:
    explicit = str(state.get("current_cycle_dir") or "").strip()
    if cycle is None and explicit:
        return repo_root / explicit
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    return _phase_dir(state, repo_root=repo_root) / f"cycle_{resolved_cycle}"


def _artifact_paths(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Path]:
    phase_dir = _phase_dir(state, repo_root=repo_root)
    return {
        "raw_seed_digest": phase_dir / "raw_seed_digest.json",
        "system_view": phase_dir / "system_view.json",
        "apply_plan": phase_dir / "apply_plan.json",
        "apply_packet": phase_dir / "apply_packet.json",
        "focus_directive": phase_dir / "focus_directive.json",
        "legacy_task_backlog": phase_dir / "task_backlog.json",
        "legacy_task_dag": phase_dir / "task_dag.json",
    }


def _phase_step_observe_plan_path(
    synth: Mapping[str, Any],
    *,
    phase_dir: str,
) -> str:
    assimilation_targets = normalize_assimilation_targets(synth.get("assimilation_targets"), phase_scaffold={"phase_dir": phase_dir})
    configured = canonicalize_write_path(str(assimilation_targets.get("observe_plan_path") or "").strip()) or ""
    return configured or (canonicalize_write_path(f"{phase_dir}/observe_plan.json") or "")


def _phase_step_history_entry(
    *,
    repo_root: Path,
    observe_plan_path: str,
) -> str | None:
    plan_rel = canonicalize_write_path(observe_plan_path) or observe_plan_path
    plan_payload = _read_json(repo_root / plan_rel, default=None)
    if not isinstance(plan_payload, Mapping):
        return None
    dump_dir = str(plan_payload.get("dump_dir") or "").strip()
    if not dump_dir:
        return None
    entries_dir = repo_root / "tools" / "meta" / "apply" / "observe_history" / "entries"
    if not entries_dir.exists():
        return None
    matches: list[Path] = []
    for path in entries_dir.glob("OBS_*.json"):
        payload = _read_json(path, default=None)
        if not isinstance(payload, Mapping):
            continue
        candidate_dump_dir = str(payload.get("dump_dir") or "").strip()
        if candidate_dump_dir == dump_dir:
            matches.append(path)
    if not matches:
        return None
    latest = max(matches, key=lambda item: item.stat().st_mtime)
    return _relative(latest, repo_root=repo_root)


def phase_step_probe_schema(stage_kind: str) -> dict[str, Any]:
    return dict(_phase_step_probe_schema(stage_kind))


def phase_step_history_state(
    *,
    repo_root: Path,
    observe_history_entry: str | None,
    stage_kind: str,
) -> dict[str, Any]:
    entry_rel = _relative(observe_history_entry, repo_root=repo_root) if observe_history_entry else None
    if not entry_rel:
        return {
            "history_entry": None,
            "entry_payload": None,
            "checkpoint_payload": None,
            "probe_payloads": [],
            "artifact_paths": [],
            "checkpoint_ready": False,
            "has_terminal_groups": False,
        }
    payload = _read_json(repo_root / entry_rel, default=None)
    if not isinstance(payload, Mapping):
        return {
            "history_entry": entry_rel,
            "entry_payload": None,
            "checkpoint_payload": None,
            "probe_payloads": [],
            "artifact_paths": [],
            "checkpoint_ready": False,
            "has_terminal_groups": False,
        }
    probe_schema_id = str(phase_step_probe_schema(stage_kind).get("schema_id") or "").strip()
    checkpoint_schema_id = str(phase_step_checkpoint_schema(stage_kind).get("schema_id") or "").strip()
    terminal_statuses = {
        "success",
        "degraded",
        "quality_error",
        "error",
        "blocked",
        "aborted",
        "cancelled",
        "skipped",
        "completed",
    }
    probe_payloads: list[dict[str, Any]] = []
    artifact_paths: list[str] = []
    checkpoint_payload: dict[str, Any] | None = None
    has_terminal_groups = False
    for group in payload.get("groups", []) if isinstance(payload.get("groups"), list) else []:
        if not isinstance(group, Mapping):
            continue
        schema = group.get("response_schema") if isinstance(group.get("response_schema"), Mapping) else {}
        schema_id = str(schema.get("schema_id") or "").strip()
        label = str(group.get("label") or "").strip()
        runtime_state = str(
            group.get("runtime_state")
            or group.get("response_status")
            or group.get("status")
            or ""
        ).strip()
        if runtime_state in terminal_statuses:
            has_terminal_groups = True
        receipt = group.get("response_receipt_payload") if isinstance(group.get("response_receipt_payload"), Mapping) else None
        for key in ("response_file", "response_receipt_file", "response_surface_file"):
            rel = _relative(group.get(key), repo_root=repo_root)
            if rel:
                artifact_paths.append(rel)
        if not receipt:
            continue
        if schema_id == checkpoint_schema_id:
            checkpoint_payload = dict(receipt)
        elif schema_id == probe_schema_id:
            probe_payloads.append(
                {
                    "label": label,
                    "receipt": dict(receipt),
                }
            )
    return {
        "history_entry": entry_rel,
        "entry_payload": dict(payload),
        "checkpoint_payload": checkpoint_payload,
        "probe_payloads": probe_payloads,
        "artifact_paths": _dedupe_strings(artifact_paths),
        "checkpoint_ready": checkpoint_payload is not None,
        "has_terminal_groups": has_terminal_groups,
    }


def _phase_step_checkpoint_artifacts_current(
    *,
    repo_root: Path,
    continuation_summary_path: str,
    current_wave_id: str,
    legacy_cycle_index: int,
) -> bool:
    continuation_payload = _read_json(repo_root / continuation_summary_path, default={})
    if not isinstance(continuation_payload, Mapping):
        return True

    artifact_wave_id = str(continuation_payload.get("wave_id") or "").strip()
    if artifact_wave_id and current_wave_id and artifact_wave_id != current_wave_id:
        return False

    artifact_cycle = continuation_payload.get("legacy_cycle_index")
    if artifact_cycle is not None and _int(artifact_cycle, -1) != legacy_cycle_index:
        return False

    return True


def phase_step_preview(
    phase_entry: Mapping[str, Any],
    synth: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    force: bool = False,
) -> dict[str, Any]:
    normalized_synth = normalize_synth_payload(synth) or {}
    current_wave = (
        normalized_synth.get("current_wave")
        if isinstance(normalized_synth.get("current_wave"), Mapping)
        else {}
    )
    phase_dir = str(phase_entry.get("phase_dir") or normalized_synth.get("meta", {}).get("phase_dir") or "").strip()
    stage_kind = str(current_wave.get("stage_kind") or "problem_space").strip().lower() or "problem_space"
    checkpoint_policy = (
        current_wave.get("checkpoint_policy")
        if isinstance(current_wave.get("checkpoint_policy"), Mapping)
        else {}
    )
    legacy_cycle_index = _int((normalized_synth.get("meta") or {}).get("current_cycle"), 0)
    observe_plan_path = _phase_step_observe_plan_path(normalized_synth, phase_dir=phase_dir)
    assimilation_targets = normalize_assimilation_targets(
        normalized_synth.get("assimilation_targets"),
        phase_scaffold={"phase_dir": phase_dir},
    )
    continuation_summary_path = str(assimilation_targets.get("continuation_summary_path") or "").strip()
    synth_delta_path = str(assimilation_targets.get("delta_path") or "").strip()
    observe_history_entry = _phase_step_history_entry(repo_root=repo_root, observe_plan_path=observe_plan_path) if observe_plan_path else None
    history_state = phase_step_history_state(
        repo_root=repo_root,
        observe_history_entry=observe_history_entry,
        stage_kind=stage_kind,
    )

    observe_plan_exists = bool(observe_plan_path and (repo_root / observe_plan_path).exists())
    continuation_exists = bool(continuation_summary_path and (repo_root / continuation_summary_path).exists())
    delta_exists = bool(synth_delta_path and (repo_root / synth_delta_path).exists())
    current_wave_id = str(current_wave.get("wave_id") or "wave_001").strip()
    wave_status = str(current_wave.get("status") or "planned").strip()
    wave_status_key = wave_status.lower()
    terminal_wave = wave_status_key in PHASE_STEP_TERMINAL_WAVE_STATUSES
    checkpoint_artifacts_current = (
        continuation_exists
        and delta_exists
        and continuation_summary_path
        and _phase_step_checkpoint_artifacts_current(
            repo_root=repo_root,
            continuation_summary_path=continuation_summary_path,
            current_wave_id=current_wave_id,
            legacy_cycle_index=legacy_cycle_index,
        )
    )
    active_wave = (
        wave_status_key in PHASE_STEP_ACTIVE_WAVE_STATUSES
        or (observe_plan_exists and not continuation_exists and not terminal_wave)
    )

    action = "dispatch"
    status = "dispatchable"
    no_op_reason: str | None = None
    if terminal_wave and not force:
        action = "reuse_active_wave"
        status = "no_op"
        no_op_reason = f"wave_already_{wave_status_key}"
    elif checkpoint_artifacts_current and not force:
        action = "assimilate_ready"
        status = "checkpoint_ready"
        no_op_reason = "checkpoint_artifacts_already_exist"
    elif history_state.get("checkpoint_ready") and not continuation_exists:
        action = "resume"
        status = "resumable"
    elif observe_history_entry and not continuation_exists and not force:
        action = "reuse_active_wave"
        status = "no_op"
        no_op_reason = (
            "awaiting_checkpoint_receipt"
            if history_state.get("has_terminal_groups")
            else "active_wave_artifacts_already_exist"
        )
    elif active_wave and not force:
        action = "reuse_active_wave"
        status = "no_op"
        no_op_reason = "active_wave_artifacts_already_exist"

    writes: list[dict[str, Any]] = []
    if action == "dispatch":
        writes.append({"path": observe_plan_path, "kind": "observe_plan"})
    elif action == "resume":
        writes.extend(
            [
                {"path": continuation_summary_path, "kind": "continuation_summary"},
                {"path": synth_delta_path, "kind": "synth_seed_delta"},
            ]
        )
    preview = {
        "stage_kind": stage_kind,
        "wave_id": current_wave_id,
        "status": status,
        "action": action,
        "dispatchable": action == "dispatch",
        "resumable": action == "resume",
        "checkpoint_ready": action == "assimilate_ready",
        "no_op_reason": no_op_reason,
        "observe_plan_path": observe_plan_path or None,
        "observe_history_entry": observe_history_entry,
        "observe_history_checkpoint_ready": bool(history_state.get("checkpoint_ready")),
        "continuation_summary_path": continuation_summary_path or None,
        "synth_delta_path": synth_delta_path or None,
        "wave_status": wave_status,
        "legacy_cycle_index": legacy_cycle_index,
        "checkpoint_policy": {
            "rubric_id": str(checkpoint_policy.get("rubric_id") or phase_step_builtin_rubric(stage_kind).get("rubric_id") or "").strip(),
            "clarify_depth": _int(checkpoint_policy.get("clarify_depth"), 0),
            "max_clarify_depth": _int(checkpoint_policy.get("max_clarify_depth"), PHASE_STEP_DEFAULT_MAX_CLARIFY_DEPTH),
        },
        "allowed_decisions": list(phase_step_allowed_decisions(stage_kind)),
        "rubric": phase_step_builtin_rubric(stage_kind),
        "writes": writes,
    }
    return preview


def _investigation_threads_from_synth(synth: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        dict(item)
        for item in (synth.get("investigation_threads") or [])
        if isinstance(item, Mapping)
    ]


def _project_task_dag(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    synth = load_synth_seed(state, repo_root=repo_root, write_back=False)
    if not synth:
        return None
    phase = _phase_from_state(state)
    task = resolve_active_task(dict(state), repo_root=repo_root) or {}
    relevant_files = _dedupe_strings(state.get("active_scope_files") or synth_relevant_file_paths(synth))
    threads = _investigation_threads_from_synth(synth)
    layer = {
        "layer_id": str(state.get("current_layer_id") or f"{phase}_rev{int(state.get('scope_revision') or 0)}").strip(),
        "layer_kind": phase,
        "status": "active",
        "objective": synth_success_criteria_text(synth) or synth_goal_text(synth),
        "groups": [
            {
                "label": "scope" if phase == "scope" else "probe_primary" if phase == "probe" else "plan_primary",
                "objective": synth_goal_text(synth),
                "file_targets": relevant_files,
                "shard_ids": [
                    str(item.get("id") or "").strip()
                    for item in (synth.get("source_shards") or [])
                    if isinstance(item, Mapping) and str(item.get("id") or "").strip()
                ],
            }
        ],
        "sidecars": [],
        "compiled_from_cycle": int(state.get("cycle") or 0),
        "router_result": dict(state.get("routing_decision") or {}),
    }
    return {
        "schema_version": "projection_v1",
        "projection_only": True,
        "task_id": str(task.get("task_id") or "").strip() or "TASK_synth_seed",
        "task_title": str(task.get("title") or synth_goal_text(synth) or "Active synth seed").strip(),
        "current_layer_id": layer["layer_id"],
        "current_layer_kind": phase,
        "layers": [layer],
        "migration": {
            "migrated_from_legacy": bool(state.get("legacy_phase_pass_counts") or state.get("phase_pass_counts")),
            "projection_only": True,
        },
        "investigation_threads": threads,
        "relevant_files": relevant_files,
    }


def _project_task_backlog(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    synth = load_synth_seed(state, repo_root=repo_root, write_back=False)
    if not synth:
        return None
    task = resolve_active_task(dict(state), repo_root=repo_root) or {}
    threads = _investigation_threads_from_synth(synth)
    backlog_items = []
    for item in threads:
        backlog_items.append(
            {
                "task_id": str(item.get("id") or _stable_hash(str(item.get("statement") or ""))).strip(),
                "title": str(item.get("statement") or "").strip(),
                "concept_group": str(item.get("concept_group") or "general").strip() or "general",
                "reference_files": _dedupe_strings(item.get("relevant_files") or []),
                "status": "active" if str(state.get("phase") or "") not in {"apply_review_pending", "blocked"} else "gated",
            }
        )
    return {
        "schema_version": "projection_v1",
        "projection_only": True,
        "generated_at": _utc_now(),
        "root_task_id": str(task.get("task_id") or "TASK_synth_seed"),
        "tasks": backlog_items,
    }


def _stable_slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text or "").strip().lower()).strip("_") or "phase"


def _stable_hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()[:12]


def _dedupe_strings(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return out


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return _dedupe_strings(value)


def phase_step_allowed_decisions(stage_kind: str) -> tuple[str, ...]:
    normalized = str(stage_kind or "").strip().lower() or "problem_space"
    allowed = PHASE_STEP_DECISION_MATRIX.get(normalized)
    return tuple(sorted(allowed)) if allowed else tuple(sorted(PHASE_STEP_DECISION_MATRIX["problem_space"]))


def phase_step_builtin_rubric(stage_kind: str) -> dict[str, Any]:
    normalized = str(stage_kind or "").strip().lower() or "problem_space"
    return dict(PHASE_STEP_BUILTIN_RUBRICS.get(normalized) or PHASE_STEP_BUILTIN_RUBRICS["problem_space"])


def _phase_step_next_stage(stage_kind: str, decision: str) -> str | None:
    normalized_stage = str(stage_kind or "").strip().lower() or "problem_space"
    normalized_decision = str(decision or "").strip().lower()
    if normalized_decision == "clarify":
        return normalized_stage
    if normalized_decision == "advance":
        return {
            "problem_space": "solution_space",
            "solution_space": "plan_space",
        }.get(normalized_stage)
    if normalized_decision == "reframe":
        return {
            "solution_space": "problem_space",
            "plan_space": "solution_space",
        }.get(normalized_stage)
    return None


def _phase_step_routing_outcome(decision: str) -> str:
    normalized = str(decision or "").strip().lower()
    return {
        "clarify": "retry",
        "advance": "advance",
        "reframe": "redirect",
        "escalate": "escalate",
        "abort": "stop",
        "complete": "stop",
    }.get(normalized, "advance")


def _phase_step_probe_schema(stage_kind: str) -> dict[str, Any]:
    normalized_stage = str(stage_kind or "").strip().lower() or "problem_space"
    return {
        "schema_id": f"{normalized_stage}_probe_checkpoint_v1",
        "type": "object",
        "required": ["files_examined", "facts", "open_questions", "insufficiencies"],
        "properties": {
            "files_examined": {"type": "array", "items": {"type": "string"}},
            "facts": {"type": "array", "items": {"type": "string"}},
            "open_questions": {"type": "array", "items": {"type": "string"}},
            "insufficiencies": {"type": "array", "items": {"type": "string"}},
            "cross_group_queries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["target_label", "question"],
                    "properties": {
                        "target_label": {"type": "string"},
                        "question": {"type": "string"},
                        "rationale": {"type": "string"},
                    },
                },
            },
            "summary": {"type": "string"},
        },
    }


def phase_step_checkpoint_schema(stage_kind: str) -> dict[str, Any]:
    normalized_stage = str(stage_kind or "").strip().lower() or "problem_space"
    return {
        "schema_id": f"{normalized_stage}_checkpoint_v1",
        "type": "object",
        "required": ["decision", "checkpoint_summary", "current_focus", "insufficiencies"],
        "properties": {
            "decision": {
                "type": "string",
                "enum": list(phase_step_allowed_decisions(normalized_stage)),
            },
            "checkpoint_summary": {"type": "string"},
            "current_focus": {"type": "string"},
            "insufficiencies": {"type": "array", "items": {"type": "string"}},
            "next_step_posture": {"type": "string"},
            "carry_forward_posture": {"type": "string"},
            "bounded_question": {"type": "string"},
            "target_paths": {"type": "array", "items": {"type": "string"}},
            "success_signals": {"type": "array", "items": {"type": "string"}},
            "confirmed_facts": {"type": "array", "items": {"type": "string"}},
            "locked_decisions": {"type": "array", "items": {"type": "string"}},
            "active_risks": {"type": "array", "items": {"type": "string"}},
            "orientation_patch": {
                "type": "object",
                "properties": {
                    "house_view": {"type": "string"},
                    "architectural_posture": {"type": "string"},
                    "evidence_posture": {"type": "string"},
                    "pivot_rule": {"type": "string"},
                    "primary_unknown": {"type": "string"},
                },
            },
        },
    }


def _phase_step_next_wave_id(current_wave_id: str, decision: str, clarify_depth: int) -> str:
    base = str(current_wave_id or "wave_001").strip() or "wave_001"
    slug = re.sub(r"[^a-z0-9]+", "_", str(decision or "next").strip().lower()).strip("_") or "next"
    if slug == "clarify":
        return f"{base}__clarify_{clarify_depth:02d}"
    return f"{base}__{slug}"


def _phase_step_question_from_insufficiencies(
    insufficiencies: Iterable[Any],
    *,
    fallback: str,
) -> str:
    items = _dedupe_strings(insufficiencies)
    if not items:
        return str(fallback or "").strip() or "What is the next bounded clarification?"
    if len(items) == 1:
        return items[0]
    return f"{items[0]} (plus {len(items) - 1} additional insufficiencies)"


def _phase_step_merged_synthesis_memory(
    synth: Mapping[str, Any],
    checkpoint_payload: Mapping[str, Any],
) -> dict[str, Any]:
    existing = dict(synth.get("synthesis_memory") or {})
    memory = {
        "confirmed_facts": list(existing.get("confirmed_facts") or []),
        "locked_decisions": list(existing.get("locked_decisions") or []),
        "active_risks": list(existing.get("active_risks") or []),
    }
    for raw_fact in _string_list(checkpoint_payload.get("confirmed_facts")):
        memory["confirmed_facts"].append(
            {
                "fact_id": f"fact_{_stable_hash(raw_fact)}",
                "fact": raw_fact,
            }
        )
    for raw_decision in _string_list(checkpoint_payload.get("locked_decisions")):
        memory["locked_decisions"].append(
            {
                "decision_id": f"decision_{_stable_hash(raw_decision)}",
                "decision": raw_decision,
            }
        )
    for raw_risk in _string_list(checkpoint_payload.get("active_risks")):
        memory["active_risks"].append(
            {
                "risk_id": f"risk_{_stable_hash(raw_risk)}",
                "risk": raw_risk,
                "status": "open",
            }
        )
    return normalize_synthesis_memory(memory)


def _phase_step_incoming_queries(
    probe_payloads: Iterable[Mapping[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for payload in probe_payloads:
        source_label = str(payload.get("label") or "").strip() or None
        receipt = payload.get("receipt") if isinstance(payload.get("receipt"), Mapping) else {}
        for raw_query in (receipt.get("cross_group_queries") or []):
            if not isinstance(raw_query, Mapping):
                continue
            target_label = str(raw_query.get("target_label") or "").strip()
            question = str(raw_query.get("question") or "").strip()
            if not target_label or not question:
                continue
            entry = {
                "target_label": target_label,
                "question": question,
            }
            rationale = str(raw_query.get("rationale") or "").strip()
            if source_label:
                entry["source_label"] = source_label
            if rationale:
                entry["rationale"] = rationale
            grouped.setdefault(target_label, []).append(entry)
    return grouped


def phase_step_transition(
    synth: Mapping[str, Any],
    checkpoint_payload: Mapping[str, Any],
    *,
    probe_payloads: Iterable[Mapping[str, Any]] | None = None,
    force: bool = False,
) -> dict[str, Any]:
    normalized_synth = normalize_synth_payload(synth) or {}
    current_wave = (
        normalized_synth.get("current_wave")
        if isinstance(normalized_synth.get("current_wave"), Mapping)
        else {}
    )
    stage_kind = str(current_wave.get("stage_kind") or "problem_space").strip().lower() or "problem_space"
    allowed = set(phase_step_allowed_decisions(stage_kind))
    decision = str(checkpoint_payload.get("decision") or "").strip().lower()
    if decision not in allowed:
        raise ValueError(
            f"decision `{decision or 'missing'}` is invalid for stage_kind `{stage_kind}`; expected one of {sorted(allowed)}"
        )
    checkpoint_policy = (
        current_wave.get("checkpoint_policy")
        if isinstance(current_wave.get("checkpoint_policy"), Mapping)
        else {}
    )
    clarify_depth = max(0, _int(checkpoint_policy.get("clarify_depth"), 0))
    max_clarify_depth = max(1, _int(checkpoint_policy.get("max_clarify_depth"), PHASE_STEP_DEFAULT_MAX_CLARIFY_DEPTH))
    insufficiencies = _string_list(checkpoint_payload.get("insufficiencies"))
    effective_decision = decision
    auto_escalated = False
    if decision == "clarify" and clarify_depth >= max_clarify_depth and not force:
        effective_decision = "escalate"
        auto_escalated = True

    next_stage_kind = _phase_step_next_stage(stage_kind, effective_decision)
    next_wave: dict[str, Any] | None = None
    spawned_wave_ids = _string_list(current_wave.get("spawned_wave_ids"))
    incoming_queries = _phase_step_incoming_queries(probe_payloads or [])
    if next_stage_kind:
        next_clarify_depth = clarify_depth + 1 if effective_decision == "clarify" and next_stage_kind == stage_kind else 0
        next_question = (
            str(checkpoint_payload.get("bounded_question") or "").strip()
            or _phase_step_question_from_insufficiencies(
                insufficiencies,
                fallback=str(current_wave.get("bounded_question") or "").strip(),
            )
        )
        target_paths = _string_list(checkpoint_payload.get("target_paths")) or _string_list(current_wave.get("target_paths"))
        success_signals = _string_list(checkpoint_payload.get("success_signals")) or _string_list(current_wave.get("success_signals"))
        next_wave_id = _phase_step_next_wave_id(
            str(current_wave.get("wave_id") or "wave_001").strip(),
            effective_decision,
            next_clarify_depth,
        )
        next_wave = normalize_current_wave(
            {
                "wave_id": next_wave_id,
                "objective": str(checkpoint_payload.get("checkpoint_summary") or current_wave.get("objective") or "").strip()
                or "Advance the bounded wave.",
                "mode": str(current_wave.get("mode") or normalized_synth.get("execution_mode") or "bridge_graph").strip() or "bridge_graph",
                "stage_kind": next_stage_kind,
                "bounded_question": next_question,
                "success_signals": success_signals,
                "target_paths": target_paths,
                "depends_on": [],
                "status": "planned",
                "checkpoint_policy": {
                    "rubric_id": phase_step_builtin_rubric(next_stage_kind).get("rubric_id"),
                    "max_clarify_depth": max_clarify_depth,
                    "clarify_depth": next_clarify_depth,
                },
                "carry_forward_posture": str(
                    checkpoint_payload.get("carry_forward_posture")
                    or current_wave.get("carry_forward_posture")
                    or checkpoint_payload.get("next_step_posture")
                    or normalized_synth.get("next_step_posture")
                    or ""
                ).strip()
                or None,
                "spawned_wave_ids": [],
                "groups": [
                    {
                        **dict(group),
                        **(
                            {"incoming_queries": incoming_queries.get(str(group.get("title") or group.get("label") or "").strip(), [])}
                            if incoming_queries.get(str(group.get("title") or group.get("label") or "").strip())
                            else {}
                        ),
                    }
                    for group in (current_wave.get("groups") or [])
                    if isinstance(group, Mapping)
                ],
            },
            phase_scaffold={},
            intent=normalized_synth.get("intent") if isinstance(normalized_synth.get("intent"), Mapping) else {},
            working_set=normalized_synth.get("working_set") if isinstance(normalized_synth.get("working_set"), list) else [],
            execution_mode=str(current_wave.get("mode") or normalized_synth.get("execution_mode") or "").strip(),
            fallback_groups=[],
        )
        spawned_wave_ids = _dedupe_strings([*spawned_wave_ids, str(next_wave.get("wave_id") or "").strip()])

    progress_state = dict(normalized_synth.get("progress_state") or {})
    current_focus = str(checkpoint_payload.get("current_focus") or checkpoint_payload.get("checkpoint_summary") or "").strip()
    if current_focus:
        progress_state["current_focus"] = current_focus
    progress_state["last_wave_outcome"] = effective_decision

    patches: list[dict[str, Any]] = [
        {"op": "set_progress_state", "value": progress_state},
        {
            "op": "set_next_step_posture",
            "value": str(
                checkpoint_payload.get("next_step_posture")
                or checkpoint_payload.get("checkpoint_summary")
                or normalized_synth.get("next_step_posture")
                or ""
            ).strip(),
        },
    ]
    synthesis_memory = _phase_step_merged_synthesis_memory(normalized_synth, checkpoint_payload)
    if any(synthesis_memory.get(key) for key in ("confirmed_facts", "locked_decisions", "active_risks")):
        patches.append({"op": "set_synthesis_memory", "value": synthesis_memory})
    orientation_patch = checkpoint_payload.get("orientation_patch")
    if isinstance(orientation_patch, Mapping) and orientation_patch:
        merged_orientation = dict(normalized_synth.get("orientation") or {})
        merged_orientation.update(dict(orientation_patch))
        patches.append({"op": "set_orientation", "value": merged_orientation})
    if next_wave is not None:
        patches.append(
            {
                "op": "patch_current_wave",
                "value": {
                    "spawned_wave_ids": spawned_wave_ids,
                },
            }
        )

    return {
        "stage_kind": stage_kind,
        "decision": decision,
        "effective_decision": effective_decision,
        "auto_escalated": auto_escalated,
        "routing_outcome": _phase_step_routing_outcome(effective_decision),
        "allowed_decisions": sorted(allowed),
        "recommended_next_wave": next_wave,
        "delta_patches": [patch for patch in patches if patch.get("value") not in (None, "", {})],
    }


def build_phase_step_continuation_summary(
    *,
    phase_entry: Mapping[str, Any],
    synth: Mapping[str, Any],
    checkpoint_payload: Mapping[str, Any],
    transition: Mapping[str, Any],
    files_touched: Iterable[Any],
    artifact_paths: Iterable[Any],
    probe_payloads: Iterable[Mapping[str, Any]] | None = None,
    legacy_cycle_index: int | None = None,
) -> dict[str, Any]:
    normalized_synth = normalize_synth_payload(synth) or {}
    current_wave = (
        normalized_synth.get("current_wave")
        if isinstance(normalized_synth.get("current_wave"), Mapping)
        else {}
    )
    probe_rows = [dict(item) for item in (probe_payloads or []) if isinstance(item, Mapping)]
    facts_learned = _dedupe_strings(
        [
            *[
                fact
                for row in probe_rows
                for fact in _string_list((row.get("receipt") or {}).get("facts"))
            ],
            *_string_list(checkpoint_payload.get("confirmed_facts")),
        ]
    )
    questions_raised = _dedupe_strings(
        [
            *[
                question
                for row in probe_rows
                for question in _string_list((row.get("receipt") or {}).get("open_questions"))
            ],
            *_string_list(checkpoint_payload.get("insufficiencies")),
        ]
    )
    checkpoint_summary = str(checkpoint_payload.get("checkpoint_summary") or "").strip()
    current_focus = str(checkpoint_payload.get("current_focus") or checkpoint_summary).strip() or None
    next_step_posture = str(
        checkpoint_payload.get("next_step_posture")
        or checkpoint_summary
        or normalized_synth.get("next_step_posture")
        or ""
    ).strip() or None
    return {
        "kind": "continuation_summary",
        "schema_version": "continuation_summary_v2",
        "phase_id": str(phase_entry.get("phase_id") or "").strip() or None,
        "wave_id": str(current_wave.get("wave_id") or "wave_001").strip(),
        "checkpoint_kind": str(current_wave.get("stage_kind") or "problem_space").strip() or "problem_space",
        "decision": str(transition.get("effective_decision") or transition.get("decision") or "").strip(),
        "routing_outcome": str(transition.get("routing_outcome") or "").strip() or None,
        "status": "checkpoint_ready",
        "current_focus": current_focus,
        "checkpoint_summary": checkpoint_summary or None,
        "summary": checkpoint_summary or next_step_posture,
        "insufficiencies": _string_list(checkpoint_payload.get("insufficiencies")),
        "recommended_next_wave": dict(transition.get("recommended_next_wave") or {}) or None,
        "facts_learned": facts_learned,
        "questions_raised": questions_raised,
        "files_touched": _dedupe_strings(files_touched),
        "artifact_paths": _dedupe_strings(artifact_paths),
        "next_step_posture": next_step_posture,
        "legacy_cycle_index": legacy_cycle_index,
        "learning_summary": checkpoint_summary or next_step_posture,
    }


def _phase_from_state(state: Mapping[str, Any]) -> str:
    raw = str(
        state.get("phase")
        or state.get("controller_phase")
        or state.get("current_layer_kind")
        or "scope"
    ).strip()
    return LEGACY_PHASE_MIRRORS.get(raw, raw if raw in CONTROLLER_PHASES else "scope")


def _apply_phase_aliases(state: dict[str, Any]) -> None:
    phase = _phase_from_state(state)
    state["phase"] = phase
    state["controller_phase"] = phase
    state["current_layer_kind"] = phase
    state["current_layer_id"] = f"{phase}_rev{int(state.get('scope_revision') or 0)}_d{int(state.get('phase_depth') or 0)}"


def controller_config(*, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Materialize the effective controller tuning knobs for the phase-native loop.
    - Mechanism: Read master pipeline config, coerce nested `value` wrappers, and fill in defaults for wake conditions, depth limits, uncertainty thresholds, smart-pause behavior, and orchestrator identities.
    - Reads: pipeline_control.load_master_config() and repo-level pipeline config.
    - Writes: None.
    - Guarantee: Returns a normalized config dict with every controller knob present.
    - Fails: Propagates configuration-loading failures from load_master_config().
    - When-needed: Open when a routing or wake decision depends on the controller's effective thresholds and limits rather than the raw config file.
    - Escalates-to: system/lib/phase_harbor.py; system/lib/seed_pipeline_controller.py
    """
    config = load_master_config(repo_root)
    pipeline_cfg = config.get("pipeline")
    if not isinstance(pipeline_cfg, Mapping):
        pipeline_cfg = {}
    wake_conditions = _config_value(pipeline_cfg.get("wake_conditions"), DEFAULT_WAKE_CONDITIONS)
    if not isinstance(wake_conditions, list) or not wake_conditions:
        wake_conditions = list(DEFAULT_WAKE_CONDITIONS)
    max_phase_depth = max(1, int(_config_value(pipeline_cfg.get("max_layers_per_task"), 3) or 3))
    uncertainty_cfg = _config_value(pipeline_cfg.get("uncertainty_thresholds"), {})
    if not isinstance(uncertainty_cfg, Mapping):
        uncertainty_cfg = {}
    smart_pause_cfg = _config_value(pipeline_cfg.get("smart_pause"), {})
    if not isinstance(smart_pause_cfg, Mapping):
        smart_pause_cfg = {}
    return {
        "controller_version": CONTROLLER_VERSION,
        "wake_conditions": [str(item).strip() for item in wake_conditions if str(item).strip()],
        "max_phase_depth": max_phase_depth,
        "max_probe_groups": max(1, int(_config_value(pipeline_cfg.get("max_groups_per_layer"), 4) or 4)),
        "max_auto_scope_absorb_files": max(
            1,
            int(_config_value(pipeline_cfg.get("max_auto_scope_absorb_files"), 24) or 24),
        ),
        "max_in_universe_probe_redrives": max(
            2,
            int(_config_value(pipeline_cfg.get("max_in_universe_probe_redrives"), 6) or 6),
        ),
        "max_scope_passes_per_task": max(1, int(_config_value(pipeline_cfg.get("max_scope_passes_per_task"), 2) or 2)),
        "max_probe_passes_per_task": max(1, int(_config_value(pipeline_cfg.get("max_probe_passes_per_task"), 2) or 2)),
        "max_plan_passes_per_task": max(1, int(_config_value(pipeline_cfg.get("max_plan_passes_per_task"), 1) or 1)),
        "uncertainty_thresholds": {
            "scope": float(_config_value(uncertainty_cfg.get("scope"), 0.45) or 0.45),
            "probe": float(_config_value(uncertainty_cfg.get("probe"), 0.55) or 0.55),
            "plan": float(_config_value(uncertainty_cfg.get("plan"), 0.65) or 0.65),
        },
        "planner_group_count": 1,
        "error_spike_threshold": float(_config_value(pipeline_cfg.get("error_spike_threshold"), 0.5) or 0.5),
        "smart_pause": {
            "enabled": bool(_config_value(smart_pause_cfg.get("enabled"), True)),
            "non_advance_cycle_limit": max(
                2,
                int(_config_value(smart_pause_cfg.get("non_advance_cycle_limit"), 4) or 4),
            ),
        },
        "orchestrator_primary": str(_config_value(pipeline_cfg.get("orchestrator_primary"), "codex") or "codex"),
        "orchestrator_fallback": str(_config_value(pipeline_cfg.get("orchestrator_fallback"), "claude") or "claude"),
    }


def ensure_controller_state(state: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> bool:
    """
    [ACTION]
    - Teleology: Normalize a mutable controller state dict so downstream stages can rely on a complete, phase-native surface.
    - Mechanism: Fill default artifact paths and controller fields, normalize file lists and scores, derive family/controller versions, and apply phase aliases.
    - Reads: state plus phase/family scaffold artifacts when needed to infer defaults.
    - Writes: Mutates the supplied state dict in place.
    - Guarantee: Returns True when normalization changed the state; otherwise False.
    - Fails: Propagates failures from scaffold and synth helpers when they are needed for normalization.
    - When-needed: Open when a stage or harbor flow needs to know which controller fields are guaranteed after normalization.
    - Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline_recovery.py; system/lib/phase_harbor.py
    """
    changed = False
    paths = _artifact_paths(state, repo_root=repo_root)
    controller_version = controller_version_for_state(state, repo_root=repo_root)
    family_dir = family_dir_for_state(state, repo_root=repo_root)
    defaults: dict[str, Any] = {
        "controller_version": controller_version,
        "family_dir": family_dir,
        "phase": _phase_from_state(state),
        "phase_depth": max(0, int(state.get("phase_depth") or 0)),
        "failed_transitions": [],
        "active_scope_files": [],
        "known_relevant_files": [],
        "scope_revision": max(0, int(state.get("scope_revision") or 0)),
        "current_cycle_dir": _relative(_current_cycle_dir(state, repo_root=repo_root), repo_root=repo_root),
        "latest_router_receipt_path": None,
        "gate_reason": "none",
        "raw_seed_digest_path": _relative(paths["raw_seed_digest"], repo_root=repo_root),
        "system_view_path": _relative(paths["system_view"], repo_root=repo_root),
        "apply_plan_path": _relative(paths["apply_plan"], repo_root=repo_root),
        "apply_packet_path": _relative(paths["apply_packet"], repo_root=repo_root),
        "directive_path": _relative(paths["focus_directive"], repo_root=repo_root),
        "task_dag_path": _relative(paths["legacy_task_dag"], repo_root=repo_root),
        "task_backlog_path": _relative(paths["legacy_task_backlog"], repo_root=repo_root),
        "confidence_score": 0.0,
        "uncertainty_score": 1.0,
    }
    for key, value in defaults.items():
        if key not in state:
            state[key] = value
            changed = True

    normalized_phase = _phase_from_state(state)
    if state.get("phase") != normalized_phase:
        state["phase"] = normalized_phase
        changed = True

    if str(state.get("controller_version") or "").strip() != controller_version:
        state["controller_version"] = controller_version
        changed = True

    if str(state.get("family_dir") or "").strip() != family_dir:
        state["family_dir"] = family_dir
        changed = True

    normalized_failed = _dedupe_strings(state.get("failed_transitions") or [])
    if normalized_failed != list(state.get("failed_transitions") or []):
        state["failed_transitions"] = normalized_failed
        changed = True

    normalized_scope = _dedupe_strings(state.get("active_scope_files") or [])
    if normalized_scope != list(state.get("active_scope_files") or []):
        state["active_scope_files"] = normalized_scope
        changed = True

    normalized_known = _dedupe_strings(state.get("known_relevant_files") or [])
    if not normalized_known:
        synth = load_synth_seed(state, repo_root=repo_root, write_back=False) or {}
        normalized_known = _dedupe_strings(synth_relevant_file_paths(synth))
    if normalized_known != list(state.get("known_relevant_files") or []):
        state["known_relevant_files"] = normalized_known
        changed = True

    current_cycle_rel = _relative(_current_cycle_dir(state, repo_root=repo_root), repo_root=repo_root)
    if str(state.get("current_cycle_dir") or "").strip() != current_cycle_rel:
        state["current_cycle_dir"] = current_cycle_rel
        changed = True

    state["phase_depth"] = max(0, int(state.get("phase_depth") or 0))
    state["scope_revision"] = max(0, int(state.get("scope_revision") or 0))
    state["confidence_score"] = _clamp_score(state.get("confidence_score", 0.0))
    state["uncertainty_score"] = _clamp_score(state.get("uncertainty_score", 1.0))
    _apply_phase_aliases(state)
    return changed


def controller_gate_active(state: Mapping[str, Any]) -> bool:
    """
    [ACTION]
    - Teleology: Test whether the controller is currently held at a blocking gate.
    - Guarantee: Returns True when state's gate_reason is a member of BLOCKING_GATE_REASONS.
    - Fails: None.
    """
    return str(state.get("gate_reason") or "").strip() in BLOCKING_GATE_REASONS


def build_raw_seed_digest(
    state: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    max_chunk_chars: int = 4000,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compress the family raw seed into chunked JSON that later observe briefs can inject without re-reading the whole markdown source.
    - Mechanism: Resolve the family raw_seed.md path, split it into heading-bounded chunks under a char cap, and stamp each chunk with stable ids and excerpts.
    - Reads: raw_seed.md from the family directory or explicit state override.
    - Writes: None — callers persist the returned digest.
    - Guarantee: Returns a digest mapping even when the raw seed is missing.
    - Fails: Propagates unexpected filesystem errors while reading the raw seed.
    - When-needed: Open when a controller artifact write or observe brief needs the exact chunking contract for family raw seed context.
    - Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/phase_harbor.py
    """
    raw_seed_token = str(state.get("raw_seed_path") or "").strip()
    if not raw_seed_token:
        family_dir = family_dir_for_state(state, repo_root=repo_root)
        if family_dir:
            raw_seed_token = canonicalize_write_path(f"{family_dir}/raw_seed.md") or ""
    if not raw_seed_token:
        return {"generated_at": _utc_now(), "source_path": None, "chunk_count": 0, "chunks": []}
    raw_seed_path = repo_root / raw_seed_token
    if not raw_seed_path.exists() or raw_seed_path.is_dir():
        return {"generated_at": _utc_now(), "source_path": _relative(raw_seed_path, repo_root=repo_root), "chunk_count": 0, "chunks": []}

    text = raw_seed_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    chunks: list[dict[str, Any]] = []
    buffer: list[str] = []
    section = "root"
    chunk_start = 1
    chunk_index = 0

    def flush(end_line: int) -> None:
        nonlocal buffer, chunk_index, chunk_start
        if not buffer:
            return
        body = "\n".join(buffer).strip()
        if not body:
            buffer = []
            chunk_start = end_line + 1
            return
        chunk_index += 1
        chunks.append(
            {
                "chunk_id": f"RAW_{chunk_index:03d}_{_stable_hash(f'{section}|{chunk_start}|{end_line}|{body[:120]}')}",
                "section": section,
                "line_start": chunk_start,
                "line_end": end_line,
                "char_count": len(body),
                "excerpt": body[:280],
                "body": body,
            }
        )
        buffer = []
        chunk_start = end_line + 1

    current_chars = 0
    for line_number, line in enumerate(lines, 1):
        stripped = line.strip()
        if stripped.startswith("#"):
            flush(line_number - 1)
            section = stripped.lstrip("#").strip() or section
            buffer = [line]
            current_chars = len(line)
            chunk_start = line_number
            continue
        if buffer and current_chars + len(line) + 1 > max_chunk_chars:
            flush(line_number - 1)
            current_chars = 0
            chunk_start = line_number
        buffer.append(line)
        current_chars += len(line) + 1
    flush(len(lines))

    return {
        "generated_at": _utc_now(),
        "source_path": _relative(raw_seed_path, repo_root=repo_root),
        "source_sha256": sha256(text.encode("utf-8")).hexdigest(),
        "chunk_count": len(chunks),
        "chunks": chunks,
    }


def _python_symbol_summary(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    symbols: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("def "):
            symbols.append(stripped.split("def ", 1)[1].split("(", 1)[0])
        elif stripped.startswith("class "):
            symbols.append(stripped.split("class ", 1)[1].split("(", 1)[0].split(":", 1)[0])
        if len(symbols) >= 12:
            break
    return symbols


def _markdown_heading_summary(path: Path) -> list[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    headings: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            headings.append(stripped.lstrip("#").strip())
        if len(headings) >= 8:
            break
    return headings


def _include_in_system_view(rel_path: str) -> bool:
    if any(part in SYSTEM_VIEW_IGNORE_PARTS for part in Path(rel_path).parts):
        return False
    return not any(rel_path.startswith(prefix) for prefix in SYSTEM_VIEW_IGNORE_PREFIXES)


def _prune_system_view_dir(parent_rel: Path, name: str) -> bool:
    if name in SYSTEM_VIEW_IGNORE_PARTS:
        return True
    parent_parts = parent_rel.parts
    if len(parent_parts) == 2 and parent_parts[0] == "annexes" and name == "repo":
        return True
    candidate = (parent_rel / name).as_posix().strip("/")
    candidate_prefix = f"{candidate}/" if candidate else ""
    return any(candidate_prefix.startswith(prefix) for prefix in SYSTEM_VIEW_IGNORE_PREFIXES)


def _iter_system_view_files(repo_root: Path) -> Iterable[Path]:
    for current_root, dirnames, filenames in os.walk(repo_root):
        relative_base = Path(current_root).relative_to(repo_root)
        dirnames[:] = sorted(
            name
            for name in dirnames
            if not _prune_system_view_dir(relative_base, name)
        )
        base = Path(current_root)
        for filename in sorted(filenames):
            candidate = base / filename
            if candidate.is_file():
                yield candidate


def load_synth_seed(
    state: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    write_back: bool = False,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Load and normalize the active synth seed surface for the current phase.
    - Mechanism: Resolve synth_seed.json from state or phase defaults, read it, normalize it against the phase scaffold, and optionally write back the normalized payload.
    - Reads: synth_seed.json and phase_scaffold.json.
    - Writes: synth_seed.json only when `write_back` is True and normalization changes the payload.
    - Guarantee: Returns a normalized synth mapping or None when the synth surface is absent/invalid.
    - Fails: Propagates filesystem write failures when `write_back` is True.
    - When-needed: Open when a stage needs the canonical synth surface rather than raw JSON from disk.
    - Escalates-to: system/lib/pipeline/stage_select.py; system/lib/phase_harbor.py
    """
    synth_token = str(state.get("synth_seed_path") or "").strip()
    if not synth_token:
        candidate = _phase_dir(state, repo_root=repo_root) / "synth_seed.json"
        if not candidate.exists():
            return None
        synth_path = candidate
        synth_token = _relative(candidate, repo_root=repo_root)
    else:
        synth_path = repo_root / synth_token
    payload = _read_json(synth_path, default=None)
    if not isinstance(payload, Mapping):
        return None
    scaffold = _phase_scaffold_payload(state, repo_root=repo_root)
    normalized = normalize_synth_payload(payload, phase_scaffold=scaffold)
    if normalized is None:
        return None
    if write_back and normalized != payload:
        _write_json(synth_path, normalized)
    return normalized


def build_system_view(
    state: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
    max_files: int = 2000,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build a bounded repository file inventory that keeps the active synth's relevant files visually prominent for controller and observe consumers.
    - Mechanism: Walk the repo, filter ignored regions, annotate files with byte size plus quick symbol/heading summaries, and mark synth-preferred paths.
    - Reads: Repository filesystem plus the normalized synth seed.
    - Writes: None — callers persist the returned system view.
    - Guarantee: Returns a JSON-ready system view with at most `max_files` entries.
    - Fails: Propagates filesystem traversal failures.
    - When-needed: Open when a controller artifact write or observe brief needs the bounded file-universe card for the current phase.
    - Escalates-to: system/lib/phase_harbor.py; system/lib/pipeline_expansion.py
    """
    synth = load_synth_seed(state, repo_root=repo_root, write_back=False) or {}
    preferred = set(_dedupe_strings(synth_relevant_file_paths(synth)))
    files: list[dict[str, Any]] = []
    for path in _iter_system_view_files(repo_root):
        rel = _relative(path, repo_root=repo_root)
        if not _include_in_system_view(rel):
            continue
        entry: dict[str, Any] = {
            "path": rel,
            "kind": path.suffix.lstrip(".") or "file",
            "bytes": max(1, int(path.stat().st_size)),
        }
        if rel in preferred:
            entry["preferred"] = True
        if path.suffix == ".py":
            symbols = _python_symbol_summary(path)
            if symbols:
                entry["symbols"] = symbols
        elif path.suffix in {".md", ".markdown"}:
            headings = _markdown_heading_summary(path)
            if headings:
                entry["headings"] = headings
        files.append(entry)
        if len(files) >= max_files:
            break
    return {
        "generated_at": _utc_now(),
        "repo_root": str(repo_root),
        "file_count": len(files),
        "files": files,
    }


def write_controller_artifacts(state: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, str]:
    """
    [ACTION]
    - Teleology: Refresh the controller's durable artifact pack for the active phase.
    - Mechanism: Normalize state, rebuild raw-seed digest and system view, project legacy task surfaces from synth, ensure apply/focus placeholders exist, then refresh bootstrap/orchestration side effects when available.
    - Reads: Controller state, synth seed, phase/family scaffold artifacts, and repo filesystem.
    - Writes: raw_seed_digest.json, system_view.json, task_dag.json, task_backlog.json, apply_plan.json, apply_packet.json, and focus_directive.json as needed.
    - Guarantee: Returns repo-relative paths for the freshly written digest and system-view artifacts and updates matching keys on the mutable state dict.
    - Fails: Propagates filesystem write failures from underlying helpers.
    - When-needed: Open when a stage needs the canonical place that refreshes controller-side runtime artifacts before selection, routing, or operator review.
    - Escalates-to: system/lib/pipeline/stage_select.py; system/lib/phase_harbor.py; system/lib/pipeline_recovery.py
    - Navigation-group: kernel_lib
    """
    ensure_controller_state(state, repo_root=repo_root)
    paths = _artifact_paths(state, repo_root=repo_root)
    written: dict[str, str] = {}
    raw_seed_digest = build_raw_seed_digest(state, repo_root=repo_root)
    _write_json(paths["raw_seed_digest"], raw_seed_digest)
    written["raw_seed_digest_path"] = _relative(paths["raw_seed_digest"], repo_root=repo_root)
    system_view = build_system_view(state, repo_root=repo_root)
    _write_json(paths["system_view"], system_view)
    written["system_view_path"] = _relative(paths["system_view"], repo_root=repo_root)
    if state.get("synth_seed_path"):
        load_synth_seed(state, repo_root=repo_root, write_back=True)
    projected_dag = _project_task_dag(state, repo_root=repo_root)
    if projected_dag is not None:
        _write_json(paths["legacy_task_dag"], projected_dag)
        state["task_dag_path"] = _relative(paths["legacy_task_dag"], repo_root=repo_root)
    projected_backlog = _project_task_backlog(state, repo_root=repo_root)
    if projected_backlog is not None:
        _write_json(paths["legacy_task_backlog"], projected_backlog)
        state["task_backlog_path"] = _relative(paths["legacy_task_backlog"], repo_root=repo_root)
    if not paths["apply_plan"].exists():
        _write_json(paths["apply_plan"], {})
    if not paths["apply_packet"].exists():
        _write_json(paths["apply_packet"], {})
    if not paths["focus_directive"].exists():
        _write_json(paths["focus_directive"], {"active": False})
    state["raw_seed_digest_path"] = written["raw_seed_digest_path"]
    state["system_view_path"] = written["system_view_path"]
    try:
        from system.lib.agent_bootstrap_projection import try_refresh_after_controller_write

        try_refresh_after_controller_write(repo_root=repo_root)
    except Exception:
        pass
    try:
        from system.control.orchestration import write_orchestration_artifacts

        write_orchestration_artifacts(repo_root=repo_root)
    except Exception:
        pass
    return written


def _load_focus_directive(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    directive_path = str(state.get("directive_path") or "").strip()
    if not directive_path:
        return None
    path = repo_root / directive_path
    payload = _read_json(path, default=None)
    if not isinstance(payload, Mapping) or not payload.get("active"):
        return None
    return dict(payload)


def write_focus_directive(state: dict[str, Any], directive: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> Path:
    """
    [ACTION]
    - Teleology: Persist a focus directive to the controller's focus_directive.json artifact path.
    - Guarantee: Returns the path of the written directive file after normalizing state and stamping the payload.
    - Fails: Propagates filesystem write failures.
    """
    ensure_controller_state(state, repo_root=repo_root)
    payload = dict(directive)
    payload["active"] = bool(payload.get("active", True))
    payload["updated_at"] = _utc_now()
    path = _artifact_paths(state, repo_root=repo_root)["focus_directive"]
    _write_json(path, payload)
    state["directive_path"] = _relative(path, repo_root=repo_root)
    return path


def resolve_active_task(state: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Determine the currently active task from a focus directive or the active synth seed.
    - Guarantee: Returns a task dict with task_id, title, summary, reference_files, and source_shard_ids, or None when no synth surface is present.
    - Fails: None.
    """
    synth = load_synth_seed(state, repo_root=repo_root, write_back=True)
    directive = _load_focus_directive(state, repo_root=repo_root)
    if directive:
        task_id = f"TASK_{_stable_slug(str(directive.get('task') or directive.get('summary') or 'directive'))}"
        state["current_task_id"] = task_id
        return {
            "task_id": task_id,
            "title": str(directive.get("task") or directive.get("summary") or "Directive focus").strip(),
            "summary": str(directive.get("summary") or directive.get("task") or "").strip(),
            "reference_files": _dedupe_strings(directive.get("file_targets") or []),
            "source_shard_ids": [],
        }
    if not synth:
        return None
    task_id = f"TASK_{_stable_slug(synth_goal_text(synth) or 'synth_seed')}"
    state["current_task_id"] = task_id
    return {
        "task_id": task_id,
        "title": str(synth_goal_text(synth) or "Active synth seed").strip(),
        "summary": synth_success_criteria_text(synth),
        "reference_files": _dedupe_strings(synth_relevant_file_paths(synth)),
        "source_shard_ids": [
            str(item.get("id") or "").strip()
            for item in (synth.get("source_shards") or [])
            if isinstance(item, Mapping) and str(item.get("id") or "").strip()
        ],
    }


def constrain_shard_candidates(
    state: dict[str, Any],
    shards: list[dict[str, Any]],
    *,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[dict[str, Any]], dict[str, Any] | None, bool]:
    """
    [ACTION]
    - Teleology: Reorder the shard candidate list so shards that match the active synth's source ids or relevant files appear first.
    - Guarantee: Returns a (reordered_shards, active_task, constrained_flag) tuple; falls back to the original list when no synth is available.
    - Fails: None.
    """
    task = resolve_active_task(state, repo_root=repo_root)
    synth = load_synth_seed(state, repo_root=repo_root, write_back=False)
    if not synth:
        return shards, task, False
    source_ids = {
        str(item.get("id") or "").strip()
        for item in (synth.get("source_shards") or [])
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    }
    relevant_files = set(synth_relevant_file_paths(synth))
    preferred: list[dict[str, Any]] = []
    for shard in shards:
        shard_id = str(shard.get("id") or "").strip()
        shard_files = {
            str(path).strip()
            for path in (shard.get("relevant_files") or [])
            if str(path).strip()
        }
        if shard_id in source_ids or shard_files.intersection(relevant_files):
            preferred.append(shard)
    if preferred:
        return preferred + [item for item in shards if item not in preferred], task, False
    return shards, task, False


def known_relevant_file_paths(
    state: Mapping[str, Any],
    synth: Mapping[str, Any] | None = None,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Return the deduplicated list of file paths currently known to be relevant for the active phase.
    - Guarantee: Returns the state's known_relevant_files list when populated, otherwise falls back to the synth's relevant file paths.
    - Fails: None.
    """
    if synth is None:
        synth = {}
    return _dedupe_strings(
        list(state.get("known_relevant_files") or [])
        or synth_relevant_file_paths(synth)
    )


def observe_brief(
    state: Mapping[str, Any],
    selected_shards: list[dict[str, Any]],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Assemble the controller-authored brief that bounded observe plans consume for the current phase.
    - Mechanism: Normalize controller context, load synth and directive surfaces, resolve the standards bundle, derive relevant/session context files, and package intent, success criteria, and receipt schemas together.
    - Reads: Controller state, synth seed, focus directive, standards-bundle artifacts, and selected shard context.
    - Writes: May normalize/write back synth_seed.json as part of load_synth_seed(..., write_back=True).
    - Guarantee: Returns a brief mapping with intent, relevant files, context files, and typed receipt schemas for scope/probe/router/plan phases.
    - Fails: Raises ValueError when the synth seed still has `pending_initial_authoring` status.
    - When-needed: Open when authoring or debugging the exact context packet handed from the controller to observe-plan generation.
    - Escalates-to: system/lib/pipeline/stage_select.py; system/lib/phase_harbor.py; system/lib/pipeline_expansion.py
    - Navigation-group: kernel_lib
    """
    ensure_controller_state(dict(state), repo_root=repo_root)
    synth = load_synth_seed(state, repo_root=repo_root, write_back=True) or {}
    if str(synth.get("authoring_status") or "").strip() == PENDING_SYNTH_AUTHORING:
        raise ValueError("synth_seed.json is still pending initial authoring; run kernel.py --sync-synth after authoring it.")
    phase = _phase_from_state(state)
    directive = _load_focus_directive(state, repo_root=repo_root)
    relevant_files = _dedupe_strings(
        state.get("active_scope_files") or known_relevant_file_paths(state, synth)
    )
    phase_dir = str(state.get("phase_dir") or "").strip()
    family_dir = str(state.get("family_dir") or "").strip()
    standards_source_artifacts = _dedupe_strings(
        [
            str(state.get("synth_seed_path") or "").strip() or canonicalize_write_path(f"{phase_dir}/synth_seed.json") or "",
            canonicalize_write_path(f"{phase_dir}/phase_scaffold.json") or "",
            canonicalize_write_path(f"{phase_dir}/meta_ledger.json") or "",
            canonicalize_write_path(f"{family_dir}/phase_family.json") or "",
            canonicalize_write_path(f"{family_dir}/meta_ledger.json") or "",
            canonicalize_write_path(f"{family_dir}/reference_ledger.json") or "",
            str(state.get("current_cycle_assimilation_path") or "").strip(),
            str(state.get("current_cycle_carry_forward_path") or "").strip(),
        ]
    )
    standards_bundle = resolve_observe_apply_standards_bundle(
        artifact_paths=standards_source_artifacts,
        repo_root=repo_root,
        extra_artifact_kinds=["observe_plan", *(["apply_plan"] if phase == "plan" else [])],
    )
    standards_context_files = [
        item
        for item in (standards_bundle.get("context_files") or [])
        if item and (repo_root / item).exists()
    ]
    session_context_files = _dedupe_strings(
        [
            str(state.get("synth_seed_path") or "").strip(),
            str(state.get("raw_seed_digest_path") or "").strip(),
            str(state.get("system_view_path") or "").strip() if phase == "scope" else "",
            str(state.get("directive_path") or "").strip() if directive else "",
            *standards_context_files,
        ]
    )
    session_context_files = [
        item for item in session_context_files
        if item and (repo_root / item).exists()
    ]
    task = resolve_active_task(dict(state), repo_root=repo_root)
    intent = str(synth_goal_text(synth) or (task or {}).get("title") or "Advance the active seed surface").strip()
    success_criteria = synth_success_criteria_text(synth)
    wait_notes = (
        f"Phase: {phase}. "
        "Bridge authors typed JSON receipts; kernel apply remains the only mutator and stays gated."
    )
    if relevant_files:
        wait_notes += f" Active scope files: {', '.join(relevant_files[:8])}."
    return {
        "phase": phase,
        "task": task,
        "synth_seed": synth,
        "relevant_files": relevant_files,
        "session_context_files": session_context_files,
        "observe_apply_standards": standards_bundle,
        "observe_apply_standard_context_files": standards_context_files,
        "observe_apply_standard_source_artifacts": standards_source_artifacts,
        "intent": intent,
        "success_criteria": success_criteria,
        "wait_notes": wait_notes,
        "scope_receipt_schema": dict(SCOPE_RECEIPT_SCHEMA),
        "probe_receipt_schema": dict(PROBE_RECEIPT_SCHEMA),
        "router_receipt_schema": dict(ROUTER_RECEIPT_SCHEMA),
        "plan_receipt_schema": dict(PLAN_RECEIPT_SCHEMA),
    }


def _routing_signature(current_phase: str, next_phase: str, payload: Mapping[str, Any]) -> str:
    signature_payload = {
        "current_phase": current_phase,
        "next_phase": next_phase,
        "decision": payload.get("decision"),
        "newly_relevant_files": list(payload.get("newly_relevant_files") or []),
        "reasoning": str(payload.get("reasoning") or "").strip(),
    }
    return sha256(json.dumps(signature_payload, sort_keys=True).encode("utf-8")).hexdigest()[:12]


def guard_routing(
    *,
    current_phase: str,
    next_phase: str,
    phase_depth: int,
    failed_transitions: Iterable[str],
    max_depth: int,
    decision_signature: str,
    degraded_ratio: float,
    error_spike_threshold: float,
    allow_extended_probe_loop: bool = False,
    allow_repeated_probe_signature: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Decide whether a proposed controller phase transition is safe to accept or should be blocked with a gate reason.
    - Mechanism: Inspect degraded ratios, explicit blocked transitions, repeated decision signatures, and phase-depth exhaustion, with narrow probe-loop overrides for safe redrives.
    - Reads: Proposed phase transition metadata and controller depth/error thresholds supplied by callers.
    - Writes: None.
    - Guarantee: Returns a mapping with `allowed`, `gate_reason`, and `detail`.
    - Fails: None.
    - When-needed: Open when a controller advance path needs the precise guardrail that turned a routing decision into `blocked`, `uncertainty_block`, or `error_spike_block`.
    - Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/phase_harbor.py
    """
    if degraded_ratio > error_spike_threshold:
        return {"allowed": False, "gate_reason": "error_spike_block", "detail": "degraded_probe_ratio_exceeded"}
    if next_phase == "blocked":
        return {"allowed": False, "gate_reason": "contradiction_block", "detail": "explicit_blocked_transition"}
    if decision_signature and decision_signature in {str(item).strip() for item in failed_transitions if str(item).strip()}:
        if current_phase == next_phase == "probe" and allow_repeated_probe_signature:
            return {"allowed": True, "gate_reason": "none", "detail": "repeated_probe_signature_redrive_allowed"}
        return {"allowed": False, "gate_reason": "uncertainty_block", "detail": "repeated_non_progress_routing"}
    if current_phase == next_phase and next_phase in {"scope", "probe", "plan"} and phase_depth >= max_depth - 1:
        if next_phase == "probe" and allow_extended_probe_loop:
            return {"allowed": True, "gate_reason": "none", "detail": "extended_probe_loop_allowed"}
        return {"allowed": False, "gate_reason": "uncertainty_block", "detail": "max_phase_depth_exhausted"}
    return {"allowed": True, "gate_reason": "none", "detail": ""}


def _validate_apply_plan(plan: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    from tools.meta import apply as meta_apply

    plan_dict = dict(plan)
    try:
        compiled = meta_apply.compile_apply_plan(plan_dict, root_hint=str(repo_root))
    except Exception as exc:
        keys = sorted(str(key).strip() for key in plan_dict.keys() if str(key).strip())
        keys_summary = ", ".join(keys[:8]) if keys else "<none>"
        raise ValueError(
            "Invalid apply plan: expected executable `operations` or `unified_diff` content; "
            f"received top-level keys [{keys_summary}]. Original error: {exc}"
        ) from exc
    validation = meta_apply.run(
        {
            "mode": "apply",
            "plan": compiled,
            "validate_only": True,
            "root_hint": str(repo_root),
        }
    )
    status = str(validation.get("metadata", {}).get("status") or "").strip().lower()
    if status not in {"success", "info"}:
        raise ValueError(str(validation.get("metadata", {}).get("error") or "apply validation failed"))
    return compiled


def _write_invalid_apply_plan_diagnostic(
    state: Mapping[str, Any],
    *,
    apply_plan: Mapping[str, Any] | None,
    error: str,
    synthesis_payload: Mapping[str, Any],
    repo_root: Path = REPO_ROOT,
) -> str:
    diagnostic_path = _current_cycle_dir(state, repo_root=repo_root) / "apply_plan.invalid.json"
    payload = {
        "generated_at": _utc_now(),
        "controller_version": controller_version_for_state(state, repo_root=repo_root),
        "phase": str(state.get("phase") or "").strip() or "plan",
        "cycle": int(state.get("cycle") or 0),
        "gate_reason": "uncertainty_block",
        "error": str(error or "").strip() or "invalid apply plan",
        "receipt_path": str((synthesis_payload.get("artifact_meta") or {}).get("selected_receipt_path") or "").strip() or None,
        "decision": str(synthesis_payload.get("decision") or "").strip() or None,
        "apply_plan": dict(apply_plan) if isinstance(apply_plan, Mapping) else apply_plan,
        "expected_contract": {
            "accepted_shapes": [
                {"operations": ["<kernel apply operation objects>"]},
                {"unified_diff": "--- a/file\n+++ b/file\n..."},
                {"diff": "--- a/file\n+++ b/file\n..."},
                {"patch": "--- a/file\n+++ b/file\n..."},
            ],
            "note": "Descriptive edit lists are not executable apply plans.",
        },
    }
    _write_json(diagnostic_path, payload)
    return _relative(diagnostic_path, repo_root=repo_root)


def _build_apply_packet(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT, summary: str = "") -> dict[str, Any]:
    config = controller_config(repo_root=repo_root)
    return {
        "generated_at": _utc_now(),
        "controller_version": controller_version_for_state(state, repo_root=repo_root),
        "phase": "apply_review_pending",
        "review_required": True,
        "apply_plan_path": str(state.get("apply_plan_path") or "").strip() or None,
        "orchestrator_primary": config["orchestrator_primary"],
        "orchestrator_fallback": config["orchestrator_fallback"],
        "summary": summary,
    }


def _receipt_confidence(payload: Mapping[str, Any], *, default: float = 0.0) -> float:
    if "confidence" in payload:
        return _clamp_score(payload.get("confidence", default))
    return _clamp_score(default)


def _cycle_degradation_summary(cycle_summary: Mapping[str, Any]) -> dict[str, Any]:
    existing = cycle_summary.get("degradation_summary")
    if isinstance(existing, Mapping):
        return dict(existing)
    return summarize_degraded_group_diagnostics(
        cycle_summary.get("group_diagnostics"),
        degraded_groups=cycle_summary.get("degraded_groups"),
        probe_count=int(cycle_summary.get("probe_count") or 0),
    )


def _retryable_error_spike_override(
    *,
    decision: str,
    next_phase: str,
    degradation_summary: Mapping[str, Any],
) -> dict[str, Any] | None:
    if decision not in {"continue_probe", "expand_scope", "advance_to_plan"}:
        return None
    if next_phase == "blocked":
        return None
    if not bool(degradation_summary.get("all_degraded_auto_retry_safe")):
        return None
    successful_probe_count = degradation_summary.get("successful_probe_count")
    if successful_probe_count is not None and int(successful_probe_count) <= 0:
        return None
    return {
        "kind": "retryable_error_spike",
        "reason": "all_degraded_groups_retryable",
        "retryable_degraded_groups": list(degradation_summary.get("retryable_labels") or []),
        "successful_probe_count": successful_probe_count,
        "error_categories": dict(degradation_summary.get("error_categories") or {}),
        "error_stages": dict(degradation_summary.get("error_stages") or {}),
    }


def _auto_absorb_scope_candidates(
    files: Iterable[str],
    *,
    repo_root: Path,
    max_files: int,
) -> list[str]:
    candidates = _dedupe_strings(files)
    if not candidates or len(candidates) > max_files:
        return []
    absorbed: list[str] = []
    for raw_path in candidates:
        token = str(raw_path or "").strip().replace("\\", "/")
        if not token or token.startswith("/") or ".." in Path(token).parts:
            return []
        resolved = (repo_root / token).resolve()
        try:
            resolved.relative_to(repo_root.resolve())
        except ValueError:
            return []
        if not resolved.exists() or resolved.is_dir():
            return []
        absorbed.append(token)
    return absorbed


def advance_controller_after_results(
    state: dict[str, Any],
    cycle_summary: Mapping[str, Any],
    synthesis_payload: Mapping[str, Any],
    *,
    repo_root: Path = REPO_ROOT,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Turn a finished scope/probe/plan receipt into the next controller phase, gate, and artifact state.
    - Mechanism: Refresh controller artifacts, compute confidence and routing guards, absorb or widen scope when needed, validate plan receipts, and move the controller into probe, plan, apply_review_pending, or blocked.
    - Reads: Mutable controller state, current cycle summary, synthesized routing/apply payload, controller config, synth seed, and existing controller artifacts.
    - Writes: Mutates controller state in place and may write refreshed controller artifacts, apply plans, apply packets, or plan diagnostics.
    - Guarantee: Returns a summary of the resulting gate/controller phase and any routing or validation side effects.
    - Fails: Propagates artifact-write failures; handles routing/apply-plan problems by converting them into blocked-state results where possible.
    - When-needed: Open when a pipeline run needs the exact state machine that consumes typed results and decides the next controller step.
    - Escalates-to: system/lib/pipeline/stage_process.py; system/lib/pipeline_expansion.py; system/lib/phase_harbor.py
    - Navigation-group: kernel_lib
    """
    ensure_controller_state(state, repo_root=repo_root)
    write_controller_artifacts(state, repo_root=repo_root)
    config = controller_config(repo_root=repo_root)
    phase = _phase_from_state(state)
    state["gate_reason"] = "none"
    state["confidence_score"] = _receipt_confidence(synthesis_payload, default=0.0)
    state["uncertainty_score"] = _clamp_score(1.0 - state["confidence_score"])
    state["current_cycle_dir"] = _relative(_current_cycle_dir(state, repo_root=repo_root), repo_root=repo_root)
    receipt_path = str(cycle_summary.get("receipt_path") or cycle_summary.get("latest_receipt_path") or "").strip()
    if receipt_path:
        state["latest_router_receipt_path"] = receipt_path

    # When blocked with gate cleared, re-enter the probe flow so the routing
    # decision can drive a real phase transition.
    if phase == "blocked" and str(state.get("gate_reason") or "").strip() in ("none", ""):
        phase = "probe"
        state["phase"] = "probe"
        _apply_phase_aliases(state)

    if phase == "scope":
        synth = load_synth_seed(state, repo_root=repo_root, write_back=False) or {}
        known_relevant = known_relevant_file_paths(state, synth)
        active_scope = _dedupe_strings(state.get("active_scope_files") or known_relevant)
        scoped_focus = _dedupe_strings(
            synthesis_payload.get("relevant_files")
            or synthesis_payload.get("newly_relevant_files")
            or active_scope
            or known_relevant
        )
        next_known_relevant = _dedupe_strings(
            [
                *known_relevant,
                *synth_relevant_file_paths(synth),
                *list(synthesis_payload.get("relevant_files") or []),
                *list(synthesis_payload.get("newly_relevant_files") or []),
            ]
        )
        if scoped_focus != active_scope:
            state["scope_revision"] = max(0, int(state.get("scope_revision") or 0)) + 1
        state["known_relevant_files"] = next_known_relevant
        state["active_scope_files"] = scoped_focus
        state["phase"] = "probe"
        state["phase_depth"] = 0
        _apply_phase_aliases(state)
        return {"gate_reason": state["gate_reason"], "controller_phase": state["phase"]}

    if phase == "probe":
        decision = str(synthesis_payload.get("decision") or "continue_probe").strip() or "continue_probe"
        next_phase = str(synthesis_payload.get("next_phase") or "").strip() or {
            "continue_probe": "probe",
            "expand_scope": "scope",
            "advance_to_plan": "plan",
            "blocked": "blocked",
        }.get(decision, "probe")
        synth = load_synth_seed(state, repo_root=repo_root, write_back=False) or {}
        known_scope_set = set(known_relevant_file_paths(state, synth))
        newly_relevant = _dedupe_strings(synthesis_payload.get("newly_relevant_files") or [])
        genuinely_new = [path for path in newly_relevant if path not in known_scope_set]
        degradation_summary = _cycle_degradation_summary(cycle_summary)
        retryable_degradation = bool(degradation_summary.get("all_degraded_auto_retry_safe"))
        bounded_probe_progress = (
            int(cycle_summary.get("shard_updates") or 0) > 0
            or int(cycle_summary.get("new_shards_ingested") or 0) > 0
            or bool(
                degradation_summary.get("successful_probe_count")
            )
        )
        frontier_repeat_streak = max(0, int(cycle_summary.get("frontier_repeat_streak") or 0))
        max_redrive_streak = int(config["max_in_universe_probe_redrives"])
        allow_extended_probe_loop = (
            decision == "continue_probe"
            and next_phase == "probe"
            and not genuinely_new
            and frontier_repeat_streak < max_redrive_streak
            and (bounded_probe_progress or retryable_degradation)
        )
        allow_repeated_probe_signature = (
            decision == "continue_probe"
            and next_phase == "probe"
            and not genuinely_new
            and frontier_repeat_streak < max_redrive_streak
            and (
                bounded_probe_progress
                or retryable_degradation
                or int(degradation_summary.get("successful_probe_count") or 0) > 0
            )
        )
        degraded_ratio = len(cycle_summary.get("degraded_groups") or []) / max(1, int(cycle_summary.get("probe_count") or 0))
        signature = _routing_signature(phase, next_phase, synthesis_payload)
        guard = guard_routing(
            current_phase=phase,
            next_phase=next_phase,
            phase_depth=int(state.get("phase_depth") or 0),
            failed_transitions=state.get("failed_transitions") or [],
            max_depth=int(config["max_phase_depth"]),
            decision_signature=signature,
            degraded_ratio=degraded_ratio,
            error_spike_threshold=float(config["error_spike_threshold"]),
            allow_extended_probe_loop=allow_extended_probe_loop,
            allow_repeated_probe_signature=allow_repeated_probe_signature,
        )
        routing_override = None
        if not guard["allowed"] and str(guard.get("gate_reason") or "") == "error_spike_block":
            routing_override = _retryable_error_spike_override(
                decision=decision,
                next_phase=next_phase,
                degradation_summary=degradation_summary,
            )
            if routing_override:
                guard = {
                    "allowed": True,
                    "gate_reason": "none",
                    "detail": "retryable_error_spike_override",
                }
        if not guard["allowed"]:
            state["failed_transitions"] = _dedupe_strings([*(state.get("failed_transitions") or []), signature])
            state["gate_reason"] = str(guard["gate_reason"] or "uncertainty_block")
            state["phase"] = "blocked"
            _apply_phase_aliases(state)
            # Surface degraded group diagnostics when blocking on error spike
            result: dict[str, Any] = {"gate_reason": state["gate_reason"], "controller_phase": state["phase"], "routing_decision": dict(synthesis_payload)}
            if guard.get("gate_reason") == "error_spike_block":
                result["degraded_groups"] = list(cycle_summary.get("degraded_groups") or [])
                result["degraded_ratio"] = degraded_ratio
                result["probe_count"] = int(cycle_summary.get("probe_count") or 0)
                result["degradation_summary"] = degradation_summary
                diags = cycle_summary.get("group_diagnostics")
                if isinstance(diags, list):
                    result["group_diagnostics"] = [d for d in diags if isinstance(d, dict) and d.get("error")]
            return result

        state["routing_decision"] = dict(synthesis_payload)
        if next_phase == "scope":
            known_scope = known_relevant_file_paths(state, synth)
            current_scope = set(state.get("active_scope_files") or known_scope)
            known_scope_set = set(known_scope)
            genuinely_new = [f for f in newly_relevant if f not in known_scope_set]
            newly_active = [f for f in newly_relevant if f not in current_scope]
            merged_scope = _dedupe_strings([*(state.get("active_scope_files") or []), *newly_relevant])
            merged_known_scope = _dedupe_strings([*known_scope, *newly_relevant])
            auto_absorbed = _auto_absorb_scope_candidates(
                genuinely_new,
                repo_root=repo_root,
                max_files=int(config["max_auto_scope_absorb_files"]),
            )
            if merged_known_scope != known_scope:
                state["known_relevant_files"] = merged_known_scope
            if merged_scope != list(state.get("active_scope_files") or []):
                state["scope_revision"] = max(0, int(state.get("scope_revision") or 0)) + 1
            state["active_scope_files"] = merged_scope
            if auto_absorbed and len(auto_absorbed) == len(genuinely_new):
                state["phase"] = "probe"
                state["phase_depth"] = 0
                _apply_phase_aliases(state)
                return {
                    "gate_reason": state["gate_reason"],
                    "controller_phase": state["phase"],
                    "routing_decision": dict(synthesis_payload),
                    "scope_redirect": "auto_absorb_scope_files",
                    "auto_absorbed_files": auto_absorbed,
                }
            # If the router only named files already known to the phase, widen
            # the next probe locally instead of paying for another scope cycle.
            if not genuinely_new:
                state["phase"] = "probe" if newly_active else "plan"
                state["phase_depth"] = 0
                _apply_phase_aliases(state)
                return {
                    "gate_reason": state["gate_reason"],
                    "controller_phase": state["phase"],
                    "routing_decision": dict(synthesis_payload),
                    "scope_redirect": (
                        "expand_scope_within_known_universe"
                        if newly_active
                        else "expand_scope_to_plan_all_files_already_in_scope"
                    ),
                }
            state["phase"] = "scope"
            state["phase_depth"] = 0
        elif next_phase == "plan":
            state["phase"] = "plan"
            state["phase_depth"] = 0
        else:
            state["phase"] = "probe"
            state["phase_depth"] = max(0, int(state.get("phase_depth") or 0)) + 1
        _apply_phase_aliases(state)
        result = {
            "gate_reason": state["gate_reason"],
            "controller_phase": state["phase"],
            "routing_decision": dict(synthesis_payload),
        }
        if routing_override:
            result["routing_override"] = routing_override
            result["degradation_summary"] = degradation_summary
        return result

    if phase == "plan":
        decision = str(synthesis_payload.get("decision") or "").strip() or "blocked"
        if decision == "continue_probe":
            signature = _routing_signature("plan", "probe", synthesis_payload)
            guard = guard_routing(
                current_phase="plan",
                next_phase="probe",
                phase_depth=int(state.get("phase_depth") or 0),
                failed_transitions=state.get("failed_transitions") or [],
                max_depth=int(config["max_phase_depth"]),
                decision_signature=signature,
                degraded_ratio=len(cycle_summary.get("degraded_groups") or []) / max(1, int(cycle_summary.get("probe_count") or 0)),
                error_spike_threshold=float(config["error_spike_threshold"]),
            )
            if not guard["allowed"]:
                state["failed_transitions"] = _dedupe_strings([*(state.get("failed_transitions") or []), signature])
                state["gate_reason"] = str(guard["gate_reason"] or "uncertainty_block")
                state["phase"] = "blocked"
                _apply_phase_aliases(state)
                return {"gate_reason": state["gate_reason"], "controller_phase": state["phase"], "routing_decision": dict(synthesis_payload)}
            state["phase"] = "probe"
            state["phase_depth"] = 0
            _apply_phase_aliases(state)
            return {"gate_reason": state["gate_reason"], "controller_phase": state["phase"], "routing_decision": dict(synthesis_payload)}

        if decision != "apply_review_ready":
            state["gate_reason"] = "contradiction_block" if decision == "blocked" else "uncertainty_block"
            state["phase"] = "blocked"
            _apply_phase_aliases(state)
            return {"gate_reason": state["gate_reason"], "controller_phase": state["phase"], "routing_decision": dict(synthesis_payload)}

        apply_plan = synthesis_payload.get("apply_plan")
        if not isinstance(apply_plan, Mapping) or not apply_plan:
            state["retry_resume_phase"] = "plan"
            diagnostic_path = _write_invalid_apply_plan_diagnostic(
                state,
                apply_plan=apply_plan if isinstance(apply_plan, Mapping) else None,
                error="Plan receipt returned `apply_review_ready` without an executable apply payload.",
                synthesis_payload=synthesis_payload,
                repo_root=repo_root,
            )
            state["apply_plan_diagnostic_path"] = diagnostic_path
            state["plan_validation_error"] = "Plan receipt returned `apply_review_ready` without an executable apply payload."
            state["gate_reason"] = "uncertainty_block"
            state["phase"] = "blocked"
            _apply_phase_aliases(state)
            return {
                "gate_reason": state["gate_reason"],
                "controller_phase": state["phase"],
                "routing_decision": dict(synthesis_payload),
                "apply_plan_error": state["plan_validation_error"],
                "apply_plan_diagnostic_path": diagnostic_path,
            }
        try:
            compiled = _validate_apply_plan(apply_plan, repo_root=repo_root)
        except Exception as exc:
            state["retry_resume_phase"] = "plan"
            state["plan_validation_error"] = str(exc)
            diagnostic_path = _write_invalid_apply_plan_diagnostic(
                state,
                apply_plan=apply_plan,
                error=str(exc),
                synthesis_payload=synthesis_payload,
                repo_root=repo_root,
            )
            state["apply_plan_diagnostic_path"] = diagnostic_path
            state["gate_reason"] = "uncertainty_block"
            state["phase"] = "blocked"
            _apply_phase_aliases(state)
            return {
                "gate_reason": state["gate_reason"],
                "controller_phase": state["phase"],
                "routing_decision": dict(synthesis_payload),
                "apply_plan_error": str(exc),
                "apply_plan_diagnostic_path": diagnostic_path,
            }
        paths = _artifact_paths(state, repo_root=repo_root)
        _write_json(paths["apply_plan"], compiled)
        state["apply_plan_path"] = _relative(paths["apply_plan"], repo_root=repo_root)
        state.pop("apply_plan_diagnostic_path", None)
        state.pop("plan_validation_error", None)
        state.pop("retry_resume_phase", None)
        packet = _build_apply_packet(
            state,
            repo_root=repo_root,
            summary=str(synthesis_payload.get("reasoning") or "").strip(),
        )
        _write_json(paths["apply_packet"], packet)
        state["apply_packet_path"] = _relative(paths["apply_packet"], repo_root=repo_root)
        state["phase"] = "apply_review_pending"
        state["gate_reason"] = "apply_review_pending"
        state["stage"] = "apply_ready"
        _apply_phase_aliases(state)
        return {"gate_reason": state["gate_reason"], "controller_phase": state["phase"], "routing_decision": dict(synthesis_payload)}

    return {"gate_reason": state.get("gate_reason"), "controller_phase": _phase_from_state(state)}


def analytics_report(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compile a summary analytics report of cycle history for the active phase.
    - Guarantee: Returns a dict with controller version, phase, gate reason, cycle count, and the last 10 cycle summaries.
    - Fails: None.
    """
    ensure_controller_state(dict(state), repo_root=repo_root)
    phase_dir = _phase_dir(state, repo_root=repo_root)
    summaries: list[dict[str, Any]] = []
    for path in sorted(phase_dir.glob("cycle_*/_cycle_summary.json")):
        payload = _read_json(path, default=None)
        if isinstance(payload, Mapping):
            summaries.append(dict(payload))
    summaries.sort(key=lambda item: int(item.get("cycle") or 0))
    return {
        "controller_version": controller_version_for_state(state, repo_root=repo_root),
        "phase": _phase_from_state(state),
        "gate_reason": str(state.get("gate_reason") or "").strip(),
        "cycle_count": len(summaries),
        "cycles": summaries[-10:],
    }


def curate_backlog(
    state: dict[str, Any],
    action: str,
    *,
    repo_root: Path = REPO_ROOT,
    task_id: str | None = None,
    task_status: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Stub backlog-curation entry point retained for API compatibility; task backlog curation is deprecated in the bridge-native controller.
    - Guarantee: Returns a deprecation notice dict without mutating any state.
    - Fails: None.
    """
    ensure_controller_state(state, repo_root=repo_root)
    return {
        "action": action,
        "deprecated": True,
        "message": "Task backlog curation is deprecated in the bridge-native controller.",
        "task_id": task_id,
        "task_status": task_status,
    }


def active_task_dag_layer(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Return the currently active layer from the task DAG projection for the given state.
    - Guarantee: Returns the matching layer dict or None when the DAG is absent or has no matching layer.
    - Fails: None.
    """
    task_dag = load_task_dag(state, repo_root=repo_root)
    if not isinstance(task_dag, Mapping):
        return None
    current_layer_id = str(task_dag.get("current_layer_id") or "").strip()
    for layer in task_dag.get("layers", []) if isinstance(task_dag.get("layers"), list) else []:
        if not isinstance(layer, Mapping):
            continue
        if not current_layer_id or str(layer.get("layer_id") or "").strip() == current_layer_id:
            return dict(layer)
    return None


def active_task_dag_shard_ids(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> list[str]:
    """
    [ACTION]
    - Teleology: Return the shard ids sourced by the active synth seed for the current phase.
    - Guarantee: Returns a list of non-empty shard id strings from the synth seed's source_shards field, or an empty list.
    - Fails: None.
    """
    synth = load_synth_seed(state, repo_root=repo_root, write_back=False) or {}
    return [
        str(item.get("id") or "").strip()
        for item in (synth.get("source_shards") or [])
        if isinstance(item, Mapping) and str(item.get("id") or "").strip()
    ]


def ensure_task_dag(state: dict[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Ensure controller state and artifacts are current, then return the task DAG projection.
    - Guarantee: Returns the task DAG dict after refreshing controller artifacts, or None when no DAG is available.
    - Fails: Propagates artifact-write failures from write_controller_artifacts.
    """
    ensure_controller_state(state, repo_root=repo_root)
    write_controller_artifacts(state, repo_root=repo_root)
    return load_task_dag(state, repo_root=repo_root)


def load_task_dag(state: Mapping[str, Any], *, repo_root: Path = REPO_ROOT) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Load the task DAG projection from the path recorded in controller state.
    - Guarantee: Returns the task DAG mapping or None when the file is absent or not a mapping.
    - Fails: None.
    """
    path = repo_root / str(state.get("task_dag_path") or "").strip()
    payload = _read_json(path, default=None)
    return dict(payload) if isinstance(payload, Mapping) else None


__all__ = [
    "BLOCKING_GATE_REASONS",
    "CONTROLLER_PHASES",
    "CONTROLLER_VERSION",
    "PLAN_RECEIPT_SCHEMA",
    "PROBE_RECEIPT_SCHEMA",
    "ROUTER_RECEIPT_SCHEMA",
    "SCOPE_RECEIPT_SCHEMA",
    "active_task_dag_layer",
    "active_task_dag_shard_ids",
    "advance_controller_after_results",
    "analytics_report",
    "build_raw_seed_digest",
    "build_phase_step_continuation_summary",
    "build_system_view",
    "constrain_shard_candidates",
    "controller_config",
    "controller_version_for_state",
    "controller_gate_active",
    "curate_backlog",
    "ensure_controller_state",
    "ensure_task_dag",
    "guard_routing",
    "load_synth_seed",
    "load_task_dag",
    "observe_brief",
    "phase_step_allowed_decisions",
    "phase_step_builtin_rubric",
    "phase_step_checkpoint_schema",
    "phase_step_history_state",
    "phase_step_preview",
    "phase_step_probe_schema",
    "phase_step_transition",
    "resolve_active_task",
    "write_controller_artifacts",
    "write_focus_directive",
]
