"""
[PURPOSE]
- Teleology: Own the canonical `continuation_packet.json` contract used for Codex
  overnight re-entry across `pipeline_signal`, `resume_contract`, and
  `mission_controller` waits.
- Mechanism: Merge runtime-specific source context with durable family continuity,
  render the canonical Codex resume/wake prompts from that packet, and persist the
  packet beside the owning runtime artifact directory.
- Non-goal: This module does not decide *when* orchestration wakes Codex; it only
  decides what durable context is injected once a wake seam exists.

[INTERFACE]
- Exports: `build_continuation_packet`, `default_continuation_packet_path`,
  `render_codex_resume_prompt`, `render_codex_wake_prompt`, and
  `write_continuation_packet`.
- Reads: Runtime-specific source-context payloads plus family continuity artifacts
  such as `phase_family.json`, `phase_memory.json`, and `autonomous_seed.json`.
- Writes: `write_continuation_packet()` persists one canonical JSON packet.

[FLOW]
- Normalize the source context -> discover/load family continuity -> attach the
  canonical continuation-packet path and fingerprint -> render prompts from the
  final packet -> optionally persist the packet to disk.
- When-needed: Open when detached controller waits need one disk-first wake
  contract rather than handwritten prompt fragments.
- Escalates-to: pipeline_advance.py; pipeline_codex_handoff.py;
  pipeline_signal_watcher.py; tools/meta/bridge/codex_resume.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from system.lib.autonomous_seed import (
    build_autonomous_seed_payload,
    default_autonomous_seed_markdown_path,
    default_autonomous_seed_path,
    write_autonomous_seed,
)
from system.lib.codex_paths import canonicalize_write_path
from system.lib.mutation_governance import (
    build_compaction_resume_capsule,
    classify_latest_user_intent,
)

CONTINUATION_PACKET_KIND = "continuation_packet"
CONTINUATION_PACKET_VERSION = "continuation_packet_v1"
WAIT_KINDS = frozenset({"pipeline_signal", "resume_contract", "mission_controller"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _string_list(value: Any, *, limit: int | None = None) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit] if limit is not None else items


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _relative(repo_root: Path, path: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return str(path.resolve())


def _resolve_repo_path(repo_root: Path, token: str | Path | None) -> Path | None:
    raw = _string(token)
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute():
        path = repo_root / raw
    try:
        return path.resolve()
    except OSError:
        return path


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _first_context_string(source_context: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        token = _string(source_context.get(key))
        if token:
            return token
    context_bundle = source_context.get("context_bundle") if isinstance(source_context.get("context_bundle"), Mapping) else {}
    for key in keys:
        token = _string(context_bundle.get(key))
        if token:
            return token
    return ""


def _build_compaction_resume_capsule(source_context: Mapping[str, Any]) -> dict[str, Any]:
    existing = source_context.get("compaction_resume_capsule")
    if isinstance(existing, Mapping):
        return dict(existing)

    latest_user_intent = _string(source_context.get("latest_user_intent"))
    if not latest_user_intent:
        latest_user_message = _first_context_string(
            source_context,
            (
                "latest_user_message",
                "operator_message",
                "original_intent",
                "task",
            ),
        )
        latest_user_intent = classify_latest_user_intent(latest_user_message)

    return build_compaction_resume_capsule(
        latest_user_intent=latest_user_intent,
        active_transaction_id=_string(source_context.get("active_transaction_id")) or None,
        appended_rows=_string_list(source_context.get("appended_rows")),
        refreshed_sidecars=_string_list(source_context.get("refreshed_sidecars")),
        blockers_seen=_string_list(source_context.get("blockers_seen")),
        successful_append=bool(source_context.get("successful_append")),
    )


def _compaction_capsule_lines(packet: Mapping[str, Any]) -> list[str]:
    capsule = packet.get("compaction_resume_capsule") if isinstance(packet.get("compaction_resume_capsule"), Mapping) else {}
    if not capsule:
        return []
    prohibited = [str(item) for item in capsule.get("prohibited_next_actions") or [] if str(item).strip()]
    safe_next_action = _string(capsule.get("safe_next_action"))
    lines = [
        "- Latest intent: " + (_string(capsule.get("latest_user_intent")) or "unknown"),
    ]
    if safe_next_action:
        lines.append(f"- Safe next action: {safe_next_action}")
    if prohibited:
        lines.append(f"- Prohibited next actions: {', '.join(prohibited)}")
    already_completed = capsule.get("already_completed") if isinstance(capsule.get("already_completed"), Mapping) else {}
    appended = _string_list(already_completed.get("appended_rows"), limit=4)
    blockers = _string_list(already_completed.get("blockers_seen"), limit=4)
    if appended:
        lines.append(f"- Already appended rows: {', '.join(appended)}")
    if blockers:
        lines.append(f"- Blockers seen: {', '.join(blockers)}")
    return lines


def default_continuation_packet_path(artifact_dir: str) -> str:
    return canonicalize_write_path(f"{artifact_dir.rstrip('/')}/continuation_packet.json") or ""


def _candidate_repo_paths(source_context: Mapping[str, Any]) -> list[str]:
    candidates: list[str] = []
    for key in (
        "state_path",
        "phase_dir",
        "family_dir",
        "synth_seed_path",
        "raw_seed_path",
        "resume_contract_path",
        "plan_path",
        "observe_plan_path",
        "observe_manifest_path",
        "carry_forward_context_path",
        "cycle_assimilation_path",
        "cycle_timeline_path",
        "cycle_summary_path",
        "current_cycle_synth_snapshot_path",
    ):
        token = _string(source_context.get(key))
        if token:
            candidates.append(token)

    for key in ("resume_artifact_paths", "read_first", "artifact_paths", "key_files"):
        candidates.extend(_string_list(source_context.get(key)))

    context_bundle = source_context.get("context_bundle") if isinstance(source_context.get("context_bundle"), Mapping) else {}
    candidates.extend(_string_list(context_bundle.get("artifact_paths")))
    candidates.extend(_string_list(context_bundle.get("key_files")))

    for branch_key in ("on_success", "on_failure"):
        branch = source_context.get(branch_key) if isinstance(source_context.get(branch_key), Mapping) else {}
        candidates.extend(_string_list(branch.get("read_first")))
        candidates.extend(_string_list(branch.get("artifact_paths")))

    artifacts = source_context.get("artifacts") if isinstance(source_context.get("artifacts"), Mapping) else {}
    for value in artifacts.values():
        token = _string(value)
        if token:
            candidates.append(token)
    return _dedupe_strings(candidates)


def _discover_family_dir(repo_root: Path, source_context: Mapping[str, Any]) -> str:
    explicit = canonicalize_write_path(_string(source_context.get("family_dir")))
    if explicit:
        return explicit

    for token in _candidate_repo_paths(source_context):
        path = _resolve_repo_path(repo_root, token)
        if path is None:
            continue
        current = path if path.is_dir() else path.parent
        for candidate in [current, *current.parents]:
            try:
                candidate.relative_to(repo_root)
            except ValueError:
                break
            if (candidate / "phase_family.json").is_file():
                return _relative(repo_root, candidate)
    return ""


def _build_family_continuity(repo_root: Path, source_context: Mapping[str, Any]) -> dict[str, Any]:
    family_dir = _discover_family_dir(repo_root, source_context)
    if not family_dir:
        return {}

    family_marker = dict(_load_json(repo_root / family_dir / "phase_family.json") or {})
    if not family_marker:
        return {
            "family_dir": family_dir,
        }

    family_charter_path = _string(family_marker.get("family_charter_path")) or canonicalize_write_path(
        f"{family_dir}/family_charter.json"
    ) or ""
    raw_seed_path = _string(family_marker.get("raw_seed_path")) or canonicalize_write_path(f"{family_dir}/raw_seed.md") or ""
    raw_seed_principles_path = _string(family_marker.get("raw_seed_principles_path")) or canonicalize_write_path(
        f"{family_dir}/raw_seed/raw_seed_principles.json"
    ) or ""
    reference_ledger_path = _string(family_marker.get("reference_ledger_path")) or canonicalize_write_path(
        f"{family_dir}/reference_ledger.json"
    ) or ""
    meta_ledger_path = _string(family_marker.get("meta_ledger_path")) or canonicalize_write_path(
        f"{family_dir}/meta_ledger.json"
    ) or ""
    phase_memory_path = _string(family_marker.get("phase_memory_path")) or canonicalize_write_path(
        f"{family_dir}/phase_memory.json"
    ) or ""
    autonomous_seed_path = _string(family_marker.get("autonomous_seed_path")) or default_autonomous_seed_path(family_dir)
    autonomous_seed_markdown_path = _string(family_marker.get("autonomous_seed_markdown_path")) or default_autonomous_seed_markdown_path(
        family_dir
    )

    autonomous_seed_payload = dict(_load_json(repo_root / autonomous_seed_path) or {})
    if not autonomous_seed_payload:
        _json_rel, _markdown_rel, built_payload = write_autonomous_seed(
            repo_root,
            family_dir=family_dir,
            payload=build_autonomous_seed_payload(repo_root, family_dir=family_dir, family_marker=family_marker),
        )
        autonomous_seed_payload = dict(built_payload)

    return {
        "family_id": _string(family_marker.get("family_id")),
        "family_number": _string(family_marker.get("family_number")),
        "family_title": _string(family_marker.get("family_title")),
        "family_dir": family_dir,
        "family_charter_path": family_charter_path or None,
        "raw_seed_path": raw_seed_path or None,
        "raw_seed_principles_path": raw_seed_principles_path or None,
        "reference_ledger_path": reference_ledger_path or None,
        "meta_ledger_path": meta_ledger_path or None,
        "phase_memory_path": phase_memory_path or None,
        "autonomous_seed_path": autonomous_seed_path or None,
        "autonomous_seed_markdown_path": autonomous_seed_markdown_path or None,
        "active_phase": dict(autonomous_seed_payload.get("active_phase") or {}),
        "recent_closed_phases": [
            dict(item)
            for item in (autonomous_seed_payload.get("recent_closed_phases") or [])
            if isinstance(item, Mapping)
        ],
        "principle_refs": [
            dict(item)
            for item in (autonomous_seed_payload.get("principle_refs") or [])
            if isinstance(item, Mapping)
        ],
        "narrative_continuity": dict(autonomous_seed_payload.get("narrative_continuity") or {}),
    }


def _packet_context_file_list(packet: Mapping[str, Any], *, limit: int = 6) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    active_scope = packet.get("active_scope") if isinstance(packet.get("active_scope"), Mapping) else {}
    routing = packet.get("routing_decision") if isinstance(packet.get("routing_decision"), Mapping) else {}
    for source in (
        active_scope.get("active_scope_files") or [],
        active_scope.get("known_relevant_files") or [],
        routing.get("relevant_files") or [],
        routing.get("newly_relevant_files") or [],
    ):
        if not isinstance(source, list):
            continue
        for item in source:
            path = _string(item)
            if not path or path in seen:
                continue
            seen.add(path)
            ordered.append(path)
            if len(ordered) >= limit:
                return ordered
    return ordered


def _packet_context_lines(packet: Mapping[str, Any], *, file_limit: int = 6) -> list[str]:
    lines: list[str] = []
    phase_dir = _string(packet.get("phase_dir"))
    family_dir = _string(packet.get("family_dir"))
    controller_phase = _string(packet.get("controller_phase"))
    current_layer_kind = _string(packet.get("current_layer_kind"))
    current_layer_id = _string(packet.get("current_layer_id"))
    current_task_id = _string(packet.get("current_task_id"))
    synth_snapshot = _string(packet.get("current_cycle_synth_snapshot_path"))
    active_scope = packet.get("active_scope") if isinstance(packet.get("active_scope"), Mapping) else {}
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
    apply_plan_diagnostic = _string(packet.get("apply_plan_diagnostic_path"))
    if apply_plan_diagnostic:
        lines.append(f"- Apply plan diagnostic: {apply_plan_diagnostic}")
    known_scope_count = int(active_scope.get("known_relevant_count") or 0)
    if known_scope_count:
        lines.append(f"- Known relevant files: {known_scope_count}")

    relevant_files = _packet_context_file_list(packet, limit=file_limit)
    if relevant_files:
        lines.append(f"- Relevant files: {', '.join(relevant_files)}")
    return lines


def _family_context_lines(packet: Mapping[str, Any]) -> list[str]:
    continuity = packet.get("family_continuity") if isinstance(packet.get("family_continuity"), Mapping) else {}
    if not continuity:
        return []
    lines: list[str] = [
        f"- Raw seed blackboard: {_string(continuity.get('raw_seed_path')) or 'not resolved'}",
        f"- Family autonomous seed: {_string(continuity.get('autonomous_seed_path')) or 'not resolved'}",
        f"- Phase memory rollup: {_string(continuity.get('phase_memory_path')) or 'not resolved'}",
        f"- Raw-seed principles: {_string(continuity.get('raw_seed_principles_path')) or 'not resolved'}",
    ]
    narrative = continuity.get("narrative_continuity") if isinstance(continuity.get("narrative_continuity"), Mapping) else {}
    if _string(narrative.get("active_focus")):
        lines.append(f"- Continuity focus: {_string(narrative.get('active_focus'))}")
    principle_refs = continuity.get("principle_refs") if isinstance(continuity.get("principle_refs"), list) else []
    if principle_refs:
        labels = [
            _string(item.get("title"))
            for item in principle_refs[:3]
            if isinstance(item, Mapping) and _string(item.get("title"))
        ]
        if labels:
            lines.append(f"- Principle refs: {', '.join(labels)}")
    return lines


def _continuation_packet_token(packet: Mapping[str, Any]) -> str:
    direct = _string(packet.get("continuation_packet_path"))
    if direct:
        return direct
    artifacts = packet.get("artifacts") if isinstance(packet.get("artifacts"), Mapping) else {}
    artifact_path = _string(artifacts.get("continuation_packet_path"))
    if artifact_path:
        return artifact_path
    artifact_dir = _string(packet.get("artifact_dir"))
    if artifact_dir:
        return default_continuation_packet_path(artifact_dir)
    return "continuation_packet.json"


def _resume_contract_context_lines(packet: Mapping[str, Any]) -> list[str]:
    lines: list[str] = []
    resume_contract_path = _string(packet.get("resume_contract_path"))
    plan_path = _string(packet.get("plan_path"))
    if resume_contract_path:
        lines.append(f"- Resume contract: {resume_contract_path}")
    if plan_path:
        lines.append(f"- Plan path: {plan_path}")
    context_bundle = packet.get("context_bundle") if isinstance(packet.get("context_bundle"), Mapping) else {}
    original_intent = _string(context_bundle.get("original_intent") or context_bundle.get("macro_goal"))
    if original_intent:
        lines.append(f"- Original intent: {original_intent}")
    key_files = _string_list(context_bundle.get("key_files"), limit=8)
    if key_files:
        lines.append(f"- Key files: {', '.join(key_files)}")
    return lines


def _state_first_commands(packet: Mapping[str, Any]) -> list[str]:
    commands = packet.get("recommended_commands") if isinstance(packet.get("recommended_commands"), Mapping) else {}
    next_action = packet.get("next_action") if isinstance(packet.get("next_action"), Mapping) else {}
    first_commands = [
        f"1. {commands.get('status', 'python3 pipeline_advance.py')}",
        f"2. {commands.get('attention_gate', 'python3 pipeline_advance.py --attention-gate')}",
    ]
    next_command = _string(next_action.get("command"))
    if next_command and next_command != _string(commands.get("attention_gate")):
        first_commands.append(f"3. {next_command}")
    elif (
        isinstance(packet.get("codex_attention"), Mapping)
        and packet["codex_attention"].get("needs_attention")
        and _string(packet["codex_attention"].get("continue_command"))
    ):
        first_commands.append(f"3. {packet['codex_attention']['continue_command']}  # only after review")
    return first_commands


def _render_state_resume_prompt(packet: Mapping[str, Any]) -> str:
    readiness = packet.get("response_readiness") if isinstance(packet.get("response_readiness"), Mapping) else {}
    env_contract = packet.get("environment_contract") if isinstance(packet.get("environment_contract"), Mapping) else {}
    authority = packet.get("authority_surfaces") if isinstance(packet.get("authority_surfaces"), Mapping) else {}
    contract = packet.get("agent_operating_contract") if isinstance(packet.get("agent_operating_contract"), Mapping) else {}
    commands = packet.get("recommended_commands") if isinstance(packet.get("recommended_commands"), Mapping) else {}
    next_action = packet.get("next_action") if isinstance(packet.get("next_action"), Mapping) else {}
    first_commands = _state_first_commands(packet)

    lines = [
        f"You are resuming the ai_workflow seed pipeline in {packet['repo_root']}.",
        f"Treat {_continuation_packet_token(packet)} as the primary Codex wake contract.",
        f"Treat {packet['state_path']} as the authoritative live runtime state, not prior chat memory.",
        f"Current stage: {packet.get('stage')}",
        f"Current cycle: {packet.get('cycle')}",
        f"Controller phase: {packet.get('controller_phase')}",
        f"Current layer: {packet.get('current_layer_kind')} ({packet.get('current_layer_id')})",
        f"Current task: {packet.get('current_task_id')}",
        f"Next action: {_string(next_action.get('summary'))}",
        "",
        "First commands:",
        *first_commands,
        "",
        "Operating rules:",
        "- Read the continuation packet first, then the runtime artifacts it points to.",
        "- Advance only one bounded step unless the current step is an explicit bridge dispatch.",
        "- If the attention gate says no review is needed, do not invent extra thinking work.",
        "- If the attention gate says review is needed, re-anchor from continuation_packet.json, pipeline_attention.json, and pipeline_resume.json before continuing.",
        "- Read the latest cycle outputs from disk before asking the bridge the same question again.",
        "- If the latest cycle already makes a bounded code or synth edit obvious, land that local work before launching another bridge pass.",
        "- After local implementation or synth edits, refresh resume artifacts and set up the next cycle from disk.",
        f"- After any material state change, refresh the resume artifacts with `{commands.get('write_resume', 'python3 pipeline_advance.py --write-resume')}`.",
        "- If bridge work is still running, stop instead of waiting in chat. Resume later from the same state file.",
        "- Read the observe manifest or dump directory only if the continuation packet points you there.",
    ]

    context_lines = _packet_context_lines(packet)
    if context_lines:
        lines.extend(["", "Current context:", *context_lines])

    capsule_lines = _compaction_capsule_lines(packet)
    if capsule_lines:
        lines.extend(
            [
                "",
                "Compaction resume capsule:",
                *capsule_lines,
                "- Reclassify latest intent before any route replay or file write.",
            ]
        )

    env_commands = env_contract.get("commands") if isinstance(env_contract.get("commands"), Mapping) else {}
    env_rules = list(env_contract.get("rules") or [])
    if env_commands or env_rules:
        lines.extend(
            [
                "",
                "Environment:",
                f"- Canonical repo python: {env_commands.get('repo_python', './repo-python')}",
                f"- Canonical repo pytest: {env_commands.get('repo_pytest', './repo-pytest')}",
                f"- Shell/bootstrap wrapper: {env_commands.get('repo_env', './repo-env')}",
            ]
        )
        for rule in env_rules[:2]:
            lines.append(f"- Rule: {rule}")

    synth_target = ((authority.get("synth_seed") or {}) if isinstance(authority.get("synth_seed"), Mapping) else {}).get("path")
    raw_target = ((authority.get("raw_seed") or {}) if isinstance(authority.get("raw_seed"), Mapping) else {}).get("path")
    sync_command = ((authority.get("commands") or {}) if isinstance(authority.get("commands"), Mapping) else {}).get("sync_synth_markdown")
    extract_command = ((authority.get("commands") or {}) if isinstance(authority.get("commands"), Mapping) else {}).get(
        "extract_synth_from_raw_seed"
    )
    if raw_target or synth_target:
        lines.extend(
            [
                "",
                "Authority files:",
                f"- Raw seed blackboard: {raw_target or 'raw_seed.md'}",
                f"- Canonical synth write target: {synth_target or 'synth_seed.json'}",
            ]
        )
        if sync_command:
            lines.append(f"- After synth edits, sync markdown with: {sync_command}")
    lines.extend(["", "Family continuity:"])
    lines.extend(_family_context_lines(packet) or ["- Family continuity artifacts were not resolved for this packet."])

    synth_refresh = authority.get("synth_refresh") if isinstance(authority.get("synth_refresh"), Mapping) else {}
    if synth_refresh.get("needed"):
        lines.append(
            f"- Synth refresh is pending ({synth_refresh.get('reason')}); prefer the bridge refresh path before doing manual synthesis."
        )
        if extract_command:
            lines.append(f"- Bridge synth refresh command: {extract_command}")

    bridge_owns = list(contract.get("bridge_owns") or [])
    ide_owns = list(contract.get("ide_owns") or [])
    ide_should_not = list(contract.get("ide_should_not") or [])
    if bridge_owns or ide_owns or ide_should_not:
        lines.extend(["", "Escalation policy:"])
    for item in bridge_owns:
        lines.append(f"- Bridge owns: {item}")
    for item in ide_owns:
        lines.append(f"- IDE owns: {item}")
    for item in ide_should_not:
        lines.append(f"- IDE should not: {item}")

    for key, label in (
        ("cycle_assimilation_path", "Current cycle assimilation"),
        ("carry_forward_context_path", "Current carry-forward context"),
        ("cycle_summary_path", "Current cycle summary"),
        ("cycle_timeline_path", "Current cycle timeline"),
        ("apply_plan_diagnostic_path", "Apply plan diagnostic"),
        ("observe_manifest_path", "Current observe manifest"),
        ("dump_dir", "Current dump dir"),
    ):
        token = _string(packet.get(key))
        if token:
            lines.append(f"- {label}: {token}")
    if readiness:
        lines.append(
            f"- Bridge readiness: ready={readiness.get('ready')} status={readiness.get('status')}."
        )
    if isinstance(packet.get("codex_attention"), Mapping) and packet["codex_attention"].get("pause_pipeline"):
        lines.append(
            f"- Automation is paused until reviewed. Resume with `{packet['codex_attention'].get('resume_command')}`."
        )

    recovery = packet.get("context_recovery") if isinstance(packet.get("context_recovery"), Mapping) else {}
    if recovery.get("synth_seed_path") or recovery.get("raw_seed_path"):
        lines.extend(
            [
                "",
                "Context recovery (if resuming after context exhaustion):",
                "- Read the continuation packet and pipeline_attention.json first.",
                f"- Synth seed (intent + shards): {recovery.get('synth_seed_path', 'synth_seed.json in phase dir')}",
                f"- Raw seed (original voice): {recovery.get('raw_seed_path', 'raw_seed.md in family dir')}",
                "- Then proceed with the first commands above.",
            ]
        )
    return "\n".join(lines)


def _render_state_wake_prompt(packet: Mapping[str, Any]) -> str:
    env_contract = packet.get("environment_contract") if isinstance(packet.get("environment_contract"), Mapping) else {}
    authority = packet.get("authority_surfaces") if isinstance(packet.get("authority_surfaces"), Mapping) else {}
    contract = packet.get("agent_operating_contract") if isinstance(packet.get("agent_operating_contract"), Mapping) else {}
    next_action = packet.get("next_action") if isinstance(packet.get("next_action"), Mapping) else {}
    first_commands = _state_first_commands(packet)

    synth_target = ((authority.get("synth_seed") or {}) if isinstance(authority.get("synth_seed"), Mapping) else {}).get("path") or "synth_seed.json"
    raw_target = ((authority.get("raw_seed") or {}) if isinstance(authority.get("raw_seed"), Mapping) else {}).get("path") or "raw_seed.md"
    sync_command = ((authority.get("commands") or {}) if isinstance(authority.get("commands"), Mapping) else {}).get("sync_synth_markdown")
    env_commands = env_contract.get("commands") if isinstance(env_contract.get("commands"), Mapping) else {}
    context_lines = _packet_context_lines(packet)
    lines = [
        f"Exceptional wake for ai_workflow in {packet['repo_root']}.",
        f"Continuation packet: {_continuation_packet_token(packet)}",
        f"Authority state: {packet['state_path']}",
        f"Stage/cycle: {packet.get('stage')} / {packet.get('cycle')}",
        f"Summary: {_string(next_action.get('summary'))}",
        "",
        "Do first:",
        *first_commands,
        "- Read continuation_packet.json first, then pipeline_resume.json and pipeline_attention.json from disk before any non-trivial action.",
        f"- Read the carry-forward context first: {_string(packet.get('carry_forward_context_path')) or 'not written yet'}",
        f"- Read the cycle assimilation first: {_string(packet.get('cycle_assimilation_path')) or 'not written yet'}",
        f"- Then read the cycle timeline: {_string(packet.get('cycle_timeline_path')) or 'not written yet'}",
        "- Read the latest cycle outputs before launching another bridge pass.",
        "",
        "Escalation policy:",
        f"- Bridge owns cheap synthesis: {(contract.get('bridge_owns') or ['raw seed digestion, prior-pass synthesis, synth extract/evolve, routine in-scope probing'])[0]}",
        f"- Local review is reserved for: {(contract.get('ide_owns') or ['durable gates, out-of-universe file discovery, deliberate synth edits'])[0]}",
        "- Do not treat a pause-only attention state as permission to spawn another agent thread.",
        "- Do not wait in chat for bridge completion or rewrite synth authority into markdown/ad-hoc notes.",
        "",
        "Authority files:",
        f"- Raw seed blackboard: {raw_target}",
        f"- Canonical synth write target: {synth_target}",
        f"- Environment: use {env_commands.get('repo_python', './repo-python')} and {env_commands.get('repo_pytest', './repo-pytest')}; avoid bare python3 -m pytest.",
    ]
    if context_lines:
        lines[lines.index("Authority files:"):lines.index("Authority files:")] = ["", "Current context:", *context_lines]
    capsule_lines = _compaction_capsule_lines(packet)
    if capsule_lines:
        lines.extend(["", "Compaction resume capsule:", *capsule_lines])
    lines.extend(["", "Family continuity:"])
    lines.extend(_family_context_lines(packet) or ["- Family continuity artifacts were not resolved for this packet."])
    if sync_command:
        lines.append(f"- After synth edits: {sync_command}")
    lines.extend(
        [
            f"- Current carry-forward context: {_string(packet.get('carry_forward_context_path')) or 'not written yet'}",
            f"- Current cycle assimilation: {_string(packet.get('cycle_assimilation_path')) or 'not written yet'}",
            f"- Current cycle timeline: {_string(packet.get('cycle_timeline_path')) or 'not written yet'}",
            f"- Current cycle summary: {_string(packet.get('cycle_summary_path')) or 'not written yet'}",
            f"- Apply plan diagnostic: {_string(packet.get('apply_plan_diagnostic_path')) or 'none'}",
            f"- Current observe manifest: {_string(packet.get('observe_manifest_path')) or 'not written yet'}",
            "- Do not rewrite raw_seed.md during routine review.",
            "- Do not write synth anywhere except synth_seed.json.",
        ]
    )
    return "\n".join(lines)


def _render_resume_contract_resume_prompt(packet: Mapping[str, Any]) -> str:
    lines = [
        f"You are resuming ai_workflow in {packet['repo_root']}.",
        f"Treat {_continuation_packet_token(packet)} as the primary Codex wake contract.",
        "This wake came from a detached bridge/observe resume_contract seam.",
        f"Read this contract first: {_string(packet.get('resume_contract_path'))}",
        "",
        "Rules:",
        "- Treat continuation_packet.json, resume_contract.json, and referenced artifacts as authority, not prior chat memory.",
        "- Inspect the live outputs on disk before deciding whether on_success or on_failure is the relevant branch.",
        "- Continue from the contract's read_first and artifact_paths surfaces; do not recreate context already persisted there.",
        "- Use family continuity artifacts only to re-anchor intent, not to override the explicit contract branch.",
    ]
    context_lines = _resume_contract_context_lines(packet)
    if context_lines:
        lines.extend(["", "Contract context:", *context_lines])
    capsule_lines = _compaction_capsule_lines(packet)
    if capsule_lines:
        lines.extend(["", "Compaction resume capsule:", *capsule_lines])
    lines.extend(["", "Family continuity:"])
    lines.extend(_family_context_lines(packet) or ["- Family continuity artifacts were not resolved for this packet."])
    next_action = _string(((packet.get("next_action") or {}) if isinstance(packet.get("next_action"), Mapping) else {}).get("summary"))
    if next_action:
        lines.extend(["", f"Initial continuation hint: {next_action}"])
    return "\n".join(lines)


def _render_resume_contract_wake_prompt(packet: Mapping[str, Any]) -> str:
    lines = [
        f"Exceptional wake for ai_workflow in {packet['repo_root']}.",
        f"Continuation packet: {_continuation_packet_token(packet)}",
        "This is a detached resume_contract completion seam.",
        f"Read this contract first: {_string(packet.get('resume_contract_path'))}",
    ]
    lines.extend(_resume_contract_context_lines(packet))
    capsule_lines = _compaction_capsule_lines(packet)
    if capsule_lines:
        lines.extend(["", "Compaction resume capsule:", *capsule_lines])
    lines.extend(["", "Family continuity:"])
    lines.extend(_family_context_lines(packet) or ["- Family continuity artifacts were not resolved for this packet."])
    lines.extend(
        [
            "",
            "Rules:",
            "- Decide the relevant branch from disk, not from stale chat context.",
            "- Read the packet's referenced artifacts before re-launching any bridge work.",
        ]
    )
    return "\n".join(lines)


def render_codex_resume_prompt(packet: Mapping[str, Any]) -> str:
    if _string(packet.get("wait_kind")) == "resume_contract":
        return _render_resume_contract_resume_prompt(packet)
    return _render_state_resume_prompt(packet)


def render_codex_wake_prompt(packet: Mapping[str, Any]) -> str:
    if _string(packet.get("wait_kind")) == "resume_contract":
        return _render_resume_contract_wake_prompt(packet)
    return _render_state_wake_prompt(packet)


def _fingerprint_basis(packet: Mapping[str, Any]) -> dict[str, Any]:
    family_continuity = packet.get("family_continuity") if isinstance(packet.get("family_continuity"), Mapping) else {}
    active_phase = family_continuity.get("active_phase") if isinstance(family_continuity.get("active_phase"), Mapping) else {}
    recent_closed = family_continuity.get("recent_closed_phases") if isinstance(family_continuity.get("recent_closed_phases"), list) else []
    return {
        "wait_kind": _string(packet.get("wait_kind")),
        "repo_root": _string(packet.get("repo_root")),
        "artifact_dir": _string(packet.get("artifact_dir")),
        "state_path": _string(packet.get("state_path")),
        "resume_contract_path": _string(packet.get("resume_contract_path")),
        "pipeline_id": _string(packet.get("pipeline_id")),
        "stage": _string(packet.get("stage")),
        "cycle": packet.get("cycle"),
        "next_action": dict(packet.get("next_action") or {}),
        "codex_attention": dict(packet.get("codex_attention") or {}),
        "artifacts": dict(packet.get("artifacts") or {}),
        "family_dir": _string(family_continuity.get("family_dir")),
        "active_phase": {
            "phase_number": _string(active_phase.get("phase_number")),
            "phase_title": _string(active_phase.get("phase_title")),
            "wave_id": _string(((active_phase.get("current_wave") or {}) if isinstance(active_phase.get("current_wave"), Mapping) else {}).get("wave_id")),
        },
        "recent_closed_phases": [
            _string(item.get("phase_number"))
            for item in recent_closed[:3]
            if isinstance(item, Mapping)
        ],
        "compaction_resume_capsule": dict(packet.get("compaction_resume_capsule") or {}),
    }


def build_continuation_packet(
    repo_root: Path,
    *,
    wait_kind: str,
    artifact_dir: str | Path,
    source_context: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the canonical continuation packet for one Codex wake seam.
    - Mechanism: Merge runtime-specific source context with discovered family
      continuity, attach packet path/fingerprint fields, and render the canonical
      Codex prompts from the final packet.
    - Guarantee: Returns a deterministic packet shape for the supplied wait kind.
    - Fails: Raises ValueError when `wait_kind` is unsupported.
    - When-needed: Open when a controller/runtime surface needs one shared packet
      instead of handwritten prompts.
    """
    normalized_wait_kind = _string(wait_kind)
    if normalized_wait_kind not in WAIT_KINDS:
        raise ValueError(f"Unsupported continuation packet wait kind: {wait_kind!r}")

    repo_root = Path(repo_root).resolve()
    artifact_dir_rel = canonicalize_write_path(_string(artifact_dir)) or _relative(
        repo_root,
        _resolve_repo_path(repo_root, artifact_dir) or repo_root,
    )
    packet = {
        "kind": CONTINUATION_PACKET_KIND,
        "schema_version": CONTINUATION_PACKET_VERSION,
        "generated_at": _utc_now(),
        "wait_kind": normalized_wait_kind,
        "repo_root": str(repo_root),
        **dict(source_context or {}),
    }
    packet["artifact_dir"] = artifact_dir_rel
    packet["family_continuity"] = _build_family_continuity(repo_root, packet)
    packet["compaction_resume_capsule"] = _build_compaction_resume_capsule(packet)
    if not _string(packet.get("family_dir")):
        packet["family_dir"] = _string((packet.get("family_continuity") or {}).get("family_dir")) or None

    artifacts = dict(packet.get("artifacts") or {})
    continuation_packet_path = default_continuation_packet_path(artifact_dir_rel)
    artifacts["continuation_packet_path"] = continuation_packet_path
    packet["artifacts"] = artifacts
    packet["continuation_packet_path"] = continuation_packet_path

    prompts = {
        "codex_resume_prompt": render_codex_resume_prompt(packet),
        "codex_wake_prompt": render_codex_wake_prompt(packet),
    }
    packet["prompts"] = prompts
    packet["codex_resume_prompt"] = prompts["codex_resume_prompt"]
    packet["codex_wake_prompt"] = prompts["codex_wake_prompt"]

    fingerprint = sha256(json.dumps(_fingerprint_basis(packet), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]
    packet["continuation_packet_fingerprint"] = fingerprint
    packet["fingerprint"] = fingerprint
    packet["artifacts"]["continuation_packet_fingerprint"] = fingerprint
    return packet


def write_continuation_packet(
    repo_root: Path,
    *,
    artifact_dir: str | Path,
    packet: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Persist `continuation_packet.json` beside the owning runtime
      artifact directory.
    - Mechanism: Resolve the canonical packet path from `artifact_dir`, create the
      parent directory, and write canonical JSON.
    - Guarantee: Returns the repo-relative path written plus the payload that
      landed on disk.
    - Fails: Filesystem errors propagate when the target cannot be written.
    """
    repo_root = Path(repo_root).resolve()
    artifact_dir_rel = canonicalize_write_path(_string(artifact_dir)) or _relative(
        repo_root,
        _resolve_repo_path(repo_root, artifact_dir) or repo_root,
    )
    built = dict(packet or {})
    target_rel = _string(built.get("continuation_packet_path")) or default_continuation_packet_path(artifact_dir_rel)
    target = repo_root / target_rel
    target.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(built, indent=2, ensure_ascii=False) + "\n"
    try:
        if target.is_file() and target.read_text(encoding="utf-8") == text:
            return target_rel, built
    except OSError:
        pass
    target.write_text(text, encoding="utf-8")
    return target_rel, built
