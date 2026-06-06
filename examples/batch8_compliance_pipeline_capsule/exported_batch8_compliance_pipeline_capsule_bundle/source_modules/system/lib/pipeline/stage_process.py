"""
[PURPOSE]
- Teleology: Process observe results into the next controller decision by trusting typed receipts, updating shard/synth state, and writing cycle assimilation artifacts.
- Mechanism: Read the current observe manifest and receipt surfaces, choose the primary typed receipt, merge synthesis updates into shard/controller state, and emit cycle summaries, carry-forward context, and assimilation packets.

[INTERFACE]
- Exports: process_results, repair_results_range.
- Reads: Observe manifests/receipts, current controller state, prior cycle summaries, and synthesis payload helpers from earlier stages.
- Writes: Cycle summaries, assimilation/carry-forward artifacts, shard updates, and controller state transitions for the next loop step.

[FLOW]
- Load the active manifest and selected receipt -> normalize synthesis updates and shard mutations -> write cycle summaries and assimilation artifacts -> advance controller state or repair ranges of prior cycles.

[DEPENDENCIES]
- Couples: `system.lib.pipeline.stage_extract` supplies receipt loading, synthesis normalization, shard normalization, and cycle/event helpers that define result-processing semantics.
- Couples: `system.lib.pipeline.stage_select` supplies observe-record resolution and prior-cycle findings used when choosing carry-forward context.
- Couples: `system.lib.pipeline.stage_compile` supplies synthesis sanitization and follow-up file prioritization used to frame the next bounded loop.

[CONSTRAINTS]
- Guarantee: This stage writes the canonical cycle summary and assimilation outputs that later loops and recovery surfaces treat as the authority for a finished observe pass.
- Non-goal: This module does not dispatch observe work; it only processes completed results or repairs prior result ranges.
- When-needed: Open when a pipeline loop needs the exact stage that turns observe receipts into shard/controller updates and carry-forward artifacts.
- Escalates-to: system/lib/pipeline_recovery.py; system/lib/pipeline/stage_compile.py; system/lib/phase_harbor.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from system.lib.pipeline.stage_extract import (
    DEGRADED_GROUP_STATES,
    _active_phase,
    _cycle_dir_path,
    _cycle_dir_rel,
    _cycle_path_candidates,
    _cycle_timeline_rel,
    _guess_concept_group,
    _legacy_dump_dir_rel,
    _load_cycle_summary_by_cycle,
    _load_group_receipt,
    _normalize_shard_record,
    _normalize_synthesis_payload,
    _phase_id_from_state,
    _record_cycle_event,
    _selected_shard_ids_for_cycle,
    _selected_signature,
    _stringify_reason,
)
from system.lib.pipeline.stage_select import (
    _build_previous_cycle_findings,
    _find_meta_ledger,
    _load_synthesis_payload,
    _priority_action_summary,
    _resolve_observe_record_path,
)
from system.lib.pipeline.stage_compile import (
    _coerce_text_list,
    _flatten_text_entries,
    _priority_followup_files,
    _sanitize_synthesis_payload,
)


# ---------------------------------------------------------------------------
# Stage 6: Process results
# ---------------------------------------------------------------------------

def _apply_synthesis_updates_to_shards(
    state: dict,
    shards_data: dict,
    payload: dict[str, Any],
    *,
    cycle: int,
) -> tuple[dict, dict[str, int]]:
    from system.lib.pipeline.stage_extract import _normalize_shards_payload

    data, _ = _normalize_shards_payload(shards_data)
    shards = data.get("shards", [])
    by_id = {
        str(shard.get("id") or "").strip(): shard
        for shard in shards
        if isinstance(shard, dict) and str(shard.get("id") or "").strip()
    }
    shard_updates_applied = 0
    new_shards_ingested = 0

    for update in payload.get("shard_status_updates", []):
        if not isinstance(update, dict):
            continue
        shard_id = str(update.get("id") or "").strip()
        if not shard_id or shard_id not in by_id:
            continue
        shard = by_id[shard_id]
        previous_status = str(shard.get("status") or "pending")
        previous_variant = str(shard.get("status_variant") or "").strip()
        previous_reason = str(shard.get("status_reason") or "").strip()
        new_status = str(update.get("new_status") or "pending").strip()
        new_variant = str(update.get("status_variant") or "").strip()
        new_reason = str(update.get("reason") or "").strip()

        changed = (
            previous_status != new_status
            or previous_variant != new_variant
            or (new_reason and previous_reason != new_reason)
        )
        shard["status"] = new_status
        if new_variant:
            shard["status_variant"] = new_variant
        else:
            shard.pop("status_variant", None)
        if new_reason:
            shard["status_reason"] = new_reason
        if changed:
            shard["last_status_change_cycle"] = cycle
            shard["cooldown_until_cycle"] = 0
            if new_status != "selected":
                shard["consecutive_selected_cycles"] = 0
            shard_updates_applied += 1

    existing_ids = set(by_id.keys())
    next_num = len(existing_ids) + 1
    for new_shard in payload.get("new_shards", []):
        if not isinstance(new_shard, dict):
            continue
        question = str(new_shard.get("question") or "").strip()
        if not question:
            continue
        new_id = str(new_shard.get("id") or "").strip()
        while not new_id or new_id in existing_ids:
            new_id = f"SHARD_{next_num:03d}"
            next_num += 1
        synthesized = _normalize_shard_record(
            {
                "id": new_id,
                "raw_seed_anchor": f"emerged from cycle {cycle} synthesis",
                "clarified_statement": question,
                "concept_group": str(new_shard.get("concept_group") or "").strip() or _guess_concept_group(question),
                "intent_provenance": ["synthesis_emergence"],
                "relevant_files": new_shard.get("file_targets", []),
                "status": "pending",
                "status_reason": _stringify_reason(new_shard.get("reason")),
            }
        )
        new_shard["id"] = new_id
        shards.append(synthesized)
        by_id[new_id] = synthesized
        existing_ids.add(new_id)
        new_shards_ingested += 1

    data["shards"] = shards
    return data, {
        "shard_updates_applied": shard_updates_applied,
        "new_shards_ingested": new_shards_ingested,
    }


def _cycle_zero_evolution_streak(state: dict, *, cycle: int, shard_updates: int, new_shards: int) -> int:
    if shard_updates > 0 or new_shards > 0:
        return 0
    previous = _load_cycle_summary_by_cycle(state, cycle - 1)
    return int((previous or {}).get("zero_evolution_streak") or 0) + 1


def _cycle_frontier_repeat_streak(state: dict, *, cycle: int, selected_signature: str) -> int:
    if not selected_signature:
        return 0
    streak = 1
    previous_cycle = cycle - 1
    while previous_cycle >= 0:
        summary = _load_cycle_summary_by_cycle(state, previous_cycle) or {}
        if str(summary.get("selected_signature") or "").strip() != selected_signature:
            break
        streak += 1
        previous_cycle -= 1
    return streak


def _receipt_selection_meta(phase: str, group: dict[str, Any] | None, source: str) -> tuple[str, dict[str, Any]]:
    label = str((group or {}).get("label") or "").strip()
    role = str((group or {}).get("role") or "").strip().lower() or ""
    if phase == "scope":
        selection_kind = "scope"
    elif phase == "plan":
        selection_kind = "plan"
    elif label == "router" or role in {"synthesis", "evaluation"}:
        selection_kind = "router"
    else:
        selection_kind = "probe_fallback"
    normalized_source = f"{selection_kind}_{source}" if source not in {"", "none"} else "none"
    meta = {
        "selected_group_label": label or None,
        "selected_group_role": role or None,
        "selection_kind": selection_kind,
        "is_fallback": selection_kind == "probe_fallback",
        "source": normalized_source,
    }
    return normalized_source, meta


def _select_primary_receipt(
    state: dict,
    manifest: dict | None,
    *,
    plan: dict | None = None,
) -> tuple[dict[str, Any] | None, str, str | None, dict[str, Any]]:
    if not isinstance(manifest, dict):
        return None, "none", None, {}
    phase = _active_phase(state)
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), list) else []
    plan_groups = plan.get("groups") if isinstance(plan, dict) and isinstance(plan.get("groups"), list) else []
    plan_groups_by_label = {
        str(group.get("label") or "").strip(): group
        for group in plan_groups
        if isinstance(group, dict) and str(group.get("label") or "").strip()
    }
    receipts: list[tuple[dict[str, Any], dict[str, Any], str, str | None]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        payload, source = _load_group_receipt(
            group,
            plan_group=plan_groups_by_label.get(str(group.get("label") or "").strip()),
        )
        if not payload:
            continue
        receipt_path = str(group.get("response_receipt_file") or group.get("response_surface_file") or "").strip() or None
        if receipt_path is None and source == "response_markdown_fallback":
            receipt_path = str(group.get("response_file") or "").strip() or None
        receipts.append((group, payload, source, receipt_path))
    if not receipts:
        return None, "none", None, {}

    def _choose(predicate) -> tuple[dict[str, Any] | None, str, str | None, dict[str, Any]]:
        for group, payload, source, receipt_path in receipts:
            if predicate(group):
                normalized_source, meta = _receipt_selection_meta(phase, group, source)
                return payload, normalized_source, receipt_path, meta
        return None, "none", None, {}

    if phase == "scope":
        payload, source, receipt_path, meta = _choose(lambda group: str(group.get("label") or "").strip() == "scope")
        if payload:
            return payload, source, receipt_path, meta
        fallback_group, fallback_payload, fallback_source, fallback_path = receipts[0]
        normalized_source, fallback_meta = _receipt_selection_meta(phase, fallback_group, fallback_source)
        return fallback_payload, normalized_source, fallback_path, fallback_meta
    if phase == "plan":
        payload, source, receipt_path, meta = _choose(
            lambda group: str(group.get("label") or "").strip() in {"validator", "plan", "planner"}
            or str(group.get("role") or "").strip().lower() in {"evaluation", "advisory"}
        )
        if payload:
            return payload, source, receipt_path, meta
        fallback_group, fallback_payload, fallback_source, fallback_path = receipts[-1]
        normalized_source, fallback_meta = _receipt_selection_meta(phase, fallback_group, fallback_source)
        return fallback_payload, normalized_source, fallback_path, fallback_meta
    payload, source, receipt_path, meta = _choose(
        lambda group: str(group.get("label") or "").strip() == "router"
        or str(group.get("role") or "").strip().lower() in {"synthesis", "evaluation"}
    )
    if payload:
        return payload, source, receipt_path, meta
    fallback_group, fallback_payload, fallback_source, fallback_path = receipts[-1]
    normalized_source, fallback_meta = _receipt_selection_meta(phase, fallback_group, fallback_source)
    return fallback_payload, normalized_source, fallback_path, fallback_meta


def _normalize_typed_receipt_for_controller(phase: str, receipt: dict[str, Any]) -> dict[str, Any]:
    if phase == "scope":
        return {
            "relevant_files": receipt.get("relevant_files", []),
            "newly_relevant_files": receipt.get("newly_relevant_files", []),
            "dropped_files": receipt.get("dropped_files", []),
            "rationale": receipt.get("rationale", ""),
            "confidence": receipt.get("confidence", 0.0),
        }
    if phase == "plan":
        return {
            "decision": receipt.get("decision", ""),
            "confidence": receipt.get("confidence", 0.0),
            "reasoning": receipt.get("reasoning", ""),
            "apply_plan": receipt.get("apply_plan", {}),
            "verification": receipt.get("verification", []),
        }
    return {
        "decision": receipt.get("decision", ""),
        "next_phase": receipt.get("next_phase", ""),
        "confidence": receipt.get("confidence", 0.0),
        "reasoning": receipt.get("reasoning", ""),
        "newly_relevant_files": receipt.get("newly_relevant_files", []),
        "shard_status_updates": receipt.get("shard_updates", []),
        "routing_decision": {
            "decision": receipt.get("decision", ""),
            "next_phase": receipt.get("next_phase", ""),
            "confidence": receipt.get("confidence", 0.0),
            "reasoning": receipt.get("reasoning", ""),
        },
    }


def _group_assimilation_entry(
    *,
    group: dict[str, Any],
    plan_group: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload, receipt_source = _load_group_receipt(group, plan_group=plan_group)
    label = str(group.get("label") or "").strip() or "unknown"
    role = str(group.get("role") or "probe").strip().lower() or "probe"
    response_status = str(group.get("response_status") or group.get("runtime_state") or "").strip() or None
    receipt_path = str(group.get("response_receipt_file") or group.get("response_surface_file") or "").strip() or None
    if receipt_path is None and receipt_source == "response_markdown_fallback":
        receipt_path = str(group.get("response_file") or "").strip() or None

    facts: list[str] = []
    problems: list[str] = []
    open_questions: list[str] = []
    missing_evidence: list[str] = []
    newly_relevant_files: list[str] = []
    shard_update_ids: list[str] = []
    files_examined: list[str] = []

    prompt_question = str((plan_group or {}).get("question") or "").strip() or None
    if payload:
        files_examined = _coerce_text_list(payload.get("files_examined"))
        findings = payload.get("findings")
        if isinstance(findings, list):
            for item in findings:
                if not isinstance(item, dict):
                    continue
                summary = str(item.get("summary") or "").strip()
                if not summary:
                    continue
                status = str(item.get("status") or "").strip().lower()
                if status in {"contradicted", "blocked"}:
                    problems.append(summary)
                else:
                    facts.append(summary)

        missing_evidence = _coerce_text_list(payload.get("missing_evidence"))
        problems.extend(missing_evidence)

        newly_relevant_files = _coerce_text_list(
            payload.get("newly_relevant_files") or payload.get("relevant_files")
        )

        reasoning = str(payload.get("reasoning") or payload.get("rationale") or "").strip()
        if reasoning:
            facts.append(reasoning)

        decision = str(payload.get("decision") or "").strip()
        next_phase = str(payload.get("next_phase") or "").strip()
        if decision:
            decision_line = f"Decision: {decision}"
            if next_phase:
                decision_line += f" -> {next_phase}"
            facts.append(decision_line)

        verification = payload.get("verification")
        if isinstance(verification, list) and verification:
            facts.extend(_coerce_text_list(verification))

        shard_updates = payload.get("shard_updates")
        if isinstance(shard_updates, list):
            for item in shard_updates:
                if not isinstance(item, dict):
                    continue
                shard_id = str(item.get("shard_id") or item.get("id") or "").strip()
                if shard_id:
                    shard_update_ids.append(shard_id)
                summary = str(item.get("summary") or item.get("reason") or "").strip()
                status = str(item.get("status") or "").strip().lower()
                if summary:
                    if status in {"contradicted", "blocked"}:
                        problems.append(summary)
                    else:
                        facts.append(summary)

        emergent_questions = payload.get("new_shards")
        if isinstance(emergent_questions, list):
            for item in emergent_questions:
                if not isinstance(item, dict):
                    continue
                question = str(item.get("question") or item.get("clarified_statement") or "").strip()
                if question:
                    open_questions.append(question)

    if response_status in DEGRADED_GROUP_STATES:
        problems.append(f"Group finished in degraded state: {response_status}.")

    return {
        "label": label,
        "role": role,
        "question": prompt_question,
        "response_status": response_status,
        "receipt_source": receipt_source,
        "receipt_path": receipt_path,
        "facts": _coerce_text_list(facts),
        "problems": _coerce_text_list(problems),
        "open_questions": _coerce_text_list(open_questions),
        "missing_evidence": _coerce_text_list(missing_evidence),
        "newly_relevant_files": newly_relevant_files,
        "shard_update_ids": _coerce_text_list(shard_update_ids),
        "files_examined": files_examined,
    }


def _build_cycle_assimilation(
    state: dict,
    *,
    plan: dict[str, Any],
    manifest: dict[str, Any],
    cycle_summary: dict[str, Any],
    synthesis_updates: dict[str, Any],
    synthesis_source: str,
    receipt_path: str | None,
    receipt_meta: dict[str, Any],
) -> dict[str, Any]:
    from seed_pipeline import _utc_now, _dedupe_strings

    manifest_groups = manifest.get("groups") if isinstance(manifest.get("groups"), list) else []
    plan_groups = plan.get("groups") if isinstance(plan.get("groups"), list) else []
    plan_groups_by_label = {
        str(group.get("label") or "").strip(): group
        for group in plan_groups
        if isinstance(group, dict) and str(group.get("label") or "").strip()
    }

    group_reports = [
        _group_assimilation_entry(
            group=group,
            plan_group=plan_groups_by_label.get(str(group.get("label") or "").strip()),
        )
        for group in manifest_groups
        if isinstance(group, dict)
    ]

    aggregate_facts: list[dict[str, str]] = []
    aggregate_problems: list[dict[str, str]] = []
    aggregate_questions: list[dict[str, str]] = []
    missing_evidence: list[str] = []
    newly_relevant_files: list[str] = []
    files_examined: list[str] = []

    for report in group_reports:
        label = str(report.get("label") or "unknown").strip() or "unknown"
        for text in _coerce_text_list(report.get("facts")):
            aggregate_facts.append({"group_label": label, "text": text})
        for text in _coerce_text_list(report.get("problems")):
            aggregate_problems.append({"group_label": label, "text": text})
        for text in _coerce_text_list(report.get("open_questions")):
            aggregate_questions.append({"group_label": label, "text": text})
        missing_evidence.extend(_coerce_text_list(report.get("missing_evidence")))
        newly_relevant_files.extend(_coerce_text_list(report.get("newly_relevant_files")))
        files_examined.extend(_coerce_text_list(report.get("files_examined")))

    selected_group_label = str(receipt_meta.get("selected_group_label") or "").strip()
    for shard in synthesis_updates.get("new_shards", []):
        if not isinstance(shard, dict):
            continue
        question = str(shard.get("question") or shard.get("clarified_statement") or "").strip()
        if question:
            aggregate_questions.append(
                {"group_label": selected_group_label or "selected_receipt", "text": question}
            )

    active_scope_files = {
        str(path).strip()
        for path in (state.get("active_scope_files") or [])
        if str(path).strip()
    }
    known_relevant_files = {
        str(path).strip()
        for path in (
            state.get("known_relevant_files")
            or state.get("active_scope_files")
            or []
        )
        if str(path).strip()
    }
    widened_files = sorted(
        {
            path
            for path in _coerce_text_list(newly_relevant_files)
            if path and path not in known_relevant_files
        }
    )
    known_universe_widening = sorted(
        {
            path
            for path in _coerce_text_list(newly_relevant_files)
            if path and path in known_relevant_files and path not in active_scope_files
        }
    )
    priority_followup_files_list = _priority_followup_files(
        known_files=sorted(known_relevant_files),
        active_scope_files=sorted(active_scope_files),
        missing_evidence=missing_evidence,
        known_universe_files=known_universe_widening,
        extra_texts=[
            *_flatten_text_entries(aggregate_facts),
            *_flatten_text_entries(aggregate_problems),
            *_flatten_text_entries(aggregate_questions),
        ],
    )

    gate_reason = str(state.get("gate_reason") or "none").strip() or "none"
    degraded_groups = list(cycle_summary.get("degraded_groups") or [])
    degradation_summary = (
        dict(cycle_summary.get("degradation_summary"))
        if isinstance(cycle_summary.get("degradation_summary"), dict)
        else {}
    )
    retryable_degradation = bool(degradation_summary.get("all_degraded_auto_retry_safe"))
    routing_decision = str(
        (synthesis_updates.get("routing_decision") or {}).get("decision")
        or synthesis_updates.get("decision")
        or ""
    ).strip()
    if gate_reason not in {"", "none"}:
        action = "review_required"
        reason_key = gate_reason
        summary = f"Controller gate `{gate_reason}` stops the bounded loop."
    elif degraded_groups and not retryable_degradation:
        action = "review_required"
        reason_key = "degraded_cycle"
        summary = "The finished pass degraded or errored. Review before continuing."
    elif routing_decision == "continue_probe" and not widened_files:
        action = "continue_bounded_loop"
        reason_key = "continue_probe_within_known_universe"
        summary = (
            "Router kept the next pass inside the current known universe, "
            "so missing evidence should be handled by another bounded probe."
        )
    elif routing_decision == "advance_to_plan" and not widened_files:
        action = "continue_bounded_loop"
        reason_key = "advance_to_plan_within_known_universe"
        summary = (
            "The finished pass grounded enough evidence to move into planning "
            "without widening beyond the current known universe."
        )
    elif (
        routing_decision == "expand_scope"
        and widened_files
        and gate_reason in {"", "none"}
        and str(state.get("controller_phase") or "").strip() == "probe"
    ):
        action = "continue_bounded_loop"
        reason_key = "auto_absorbed_scope_widening"
        summary = (
            "The pass named concrete local files, and the controller absorbed them "
            "directly into the next bounded probe without waking IDE."
        )
    elif widened_files or (missing_evidence and not known_universe_widening):
        action = "widen_scope_candidate"
        reason_key = "resource_universe_widening"
        summary = "The finished pass surfaced evidence outside the current bounded universe."
    elif known_universe_widening:
        action = "continue_bounded_loop"
        reason_key = "known_universe_widening"
        summary = (
            "The finished pass only widened the next probe within files the phase already knows are relevant."
        )
    elif degraded_groups and retryable_degradation:
        action = "continue_bounded_loop"
        reason_key = "retryable_degraded_cycle"
        summary = (
            "The finished pass degraded only via retryable bridge failures, "
            "so the bounded loop can continue from disk."
        )
    else:
        action = "continue_bounded_loop"
        reason_key = "none"
        summary = "The finished pass stayed in-bounds. The machine loop can continue from disk."

    return {
        "kind": "cycle_assimilation",
        "schema_version": "cycle_assimilation_v1",
        "generated_at": _utc_now(),
        "cycle": int(state.get("cycle") or 0),
        "phase": str(cycle_summary.get("phase") or _active_phase(state)).strip(),
        "pipeline_id": state.get("pipeline_id"),
        "observe_session_id": state.get("observe_session_id"),
        "dump_dir": cycle_summary.get("dump_dir"),
        "observe_manifest_path": cycle_summary.get("observe_manifest_path"),
        "cycle_summary_path": f"{cycle_summary.get('dump_dir')}/_cycle_summary.json" if cycle_summary.get("dump_dir") else None,
        "routing_decision_path": f"{cycle_summary.get('dump_dir')}/routing_decision.json" if cycle_summary.get("dump_dir") else None,
        "selected_receipt": {
            "group_label": receipt_meta.get("selected_group_label"),
            "group_role": receipt_meta.get("selected_group_role"),
            "is_fallback": bool(receipt_meta.get("is_fallback")),
            "source": synthesis_source,
            "path": receipt_path,
        },
        "group_reports": group_reports,
        "aggregate": {
            "facts": aggregate_facts,
            "problems": aggregate_problems,
            "open_questions": aggregate_questions,
            "missing_evidence": _coerce_text_list(missing_evidence),
            "files_examined": _coerce_text_list(files_examined),
            "newly_relevant_files": _coerce_text_list(newly_relevant_files),
            "widened_files_outside_scope": widened_files,
            "known_universe_files_outside_active_scope": known_universe_widening,
            "priority_followup_files": priority_followup_files_list,
        },
        "loop_decision": {
            "action": action,
            "reason_key": reason_key,
            "summary": summary,
            "controller_gate_reason": gate_reason if gate_reason not in {"", "none"} else None,
            "degraded_groups": degraded_groups,
            "retryable_degraded_groups": list(degradation_summary.get("retryable_labels") or []),
            "non_retryable_degraded_groups": list(degradation_summary.get("non_retryable_labels") or []),
            "widened_files_outside_scope": widened_files,
            "known_universe_files_outside_active_scope": known_universe_widening,
            "missing_evidence_count": len(_coerce_text_list(missing_evidence)),
        },
    }


def _build_cycle_carry_forward_context(
    state: dict,
    *,
    cycle_summary: Mapping[str, Any],
    cycle_assimilation: Mapping[str, Any],
) -> dict[str, Any]:
    from seed_pipeline import _utc_now, _dedupe_strings
    from system.lib.observe_apply_contracts import synth_relevant_file_paths
    from system.lib.seed_pipeline_controller import load_synth_seed

    REPO_ROOT = _lazy_repo_root()
    synth = load_synth_seed(state, repo_root=REPO_ROOT, write_back=False) or {}
    known_scope = _coerce_text_list(
        state.get("known_relevant_files") or synth_relevant_file_paths(synth)
    )
    active_scope = _coerce_text_list(state.get("active_scope_files") or known_scope)
    aggregate = (
        dict(cycle_assimilation.get("aggregate") or {})
        if isinstance(cycle_assimilation.get("aggregate"), Mapping)
        else {}
    )
    loop_decision = (
        dict(cycle_assimilation.get("loop_decision") or {})
        if isinstance(cycle_assimilation.get("loop_decision"), Mapping)
        else {}
    )
    carry_forward_notes: list[dict[str, str]] = [
        item
        for item in [
            {
                "event": "ADD",
                "text": f"Loop decision: {str(loop_decision.get('summary') or '').strip()}",
            },
            *[
                {
                    "event": "ADD",
                    "text": f"Fact: {str(item.get('text') or '').strip()}",
                }
                for item in list(aggregate.get("facts") or [])[:6]
                if isinstance(item, dict) and str(item.get("text") or "").strip()
            ],
            *[
                {
                    "event": "ADD",
                    "text": f"Problem: {str(item.get('text') or '').strip()}",
                }
                for item in list(aggregate.get("problems") or [])[:6]
                if isinstance(item, dict) and str(item.get("text") or "").strip()
            ],
            *[
                {
                    "event": "ADD",
                    "text": f"Open question: {str(item.get('text') or '').strip()}",
                }
                for item in list(aggregate.get("open_questions") or [])[:6]
                if isinstance(item, dict) and str(item.get("text") or "").strip()
            ],
        ]
        if isinstance(item, dict) and str(item.get("text") or "").strip()
    ]
    degradation_summary = (
        dict(cycle_summary.get("degradation_summary") or {})
        if isinstance(cycle_summary.get("degradation_summary"), Mapping)
        else {}
    )
    if degradation_summary.get("all_degraded_auto_retry_safe"):
        carry_forward_notes.append(
            {
                "event": "RETAIN",
                "text": "Retryable provider failures are transport noise and must not be treated as missing scope.",
            }
        )
    known_universe_files = _coerce_text_list(
        aggregate.get("known_universe_files_outside_active_scope")
    )
    if known_universe_files:
        carry_forward_notes.append(
            {
                "event": "RETAIN",
                "text": "Known-universe widening candidates: " + ", ".join(known_universe_files[:8]),
            }
        )
    priority_followup_files_list = _priority_followup_files(
        known_files=known_scope,
        active_scope_files=active_scope,
        missing_evidence=aggregate.get("missing_evidence"),
        known_universe_files=(
            aggregate.get("priority_followup_files")
            or aggregate.get("known_universe_files_outside_active_scope")
        ),
        extra_texts=_coerce_text_list(carry_forward_notes),
    )
    if priority_followup_files_list:
        carry_forward_notes.append(
            {
                "event": "RETAIN",
                "text": "Priority follow-up files: " + ", ".join(priority_followup_files_list[:8]),
            }
        )
    return {
        "kind": "carry_forward_context",
        "schema_version": "carry_forward_context_v2",
        "generated_at": _utc_now(),
        "cycle": int(state.get("cycle") or 0),
        "phase": str(cycle_summary.get("phase") or _active_phase(state)).strip(),
        "pipeline_id": state.get("pipeline_id"),
        "observe_session_id": state.get("observe_session_id"),
        "known_relevant_files": known_scope,
        "active_scope_files": active_scope,
        "files_examined": _coerce_text_list(aggregate.get("files_examined")),
        "newly_relevant_files": _coerce_text_list(aggregate.get("newly_relevant_files")),
        "widened_files_outside_scope": _coerce_text_list(aggregate.get("widened_files_outside_scope")),
        "known_universe_files_outside_active_scope": known_universe_files,
        "missing_evidence": _coerce_text_list(aggregate.get("missing_evidence")),
        "priority_followup_files": priority_followup_files_list,
        "carry_forward_notes": carry_forward_notes,
        "continuity_artifacts": _dedupe_strings(
            [
                str(cycle_assimilation.get("cycle_summary_path") or "").strip(),
                str(cycle_assimilation.get("routing_decision_path") or "").strip(),
                str(cycle_assimilation.get("observe_manifest_path") or "").strip(),
                str((cycle_assimilation.get("selected_receipt") or {}).get("path") or "").strip(),
            ]
        ),
    }


def _try_apply_synth_seed_delta_receipts(
    plan: Mapping[str, Any],
    dump_dir_path: Path,
    repo_root: Path,
) -> list[str]:
    """When observe_plan.apply_synth_seed_delta_receipts is true, merge typed deltas from dump_dir."""
    from system.lib.synth_seed_delta_merge import apply_synth_seed_delta

    if not bool(plan.get("apply_synth_seed_delta_receipts")):
        return []
    lines: list[str] = []
    for rec_path in sorted(dump_dir_path.glob("*.receipt.json")):
        try:
            data = json.loads(rec_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        delta: dict[str, Any] | None = None
        if isinstance(data, dict):
            if str(data.get("schema_version") or "").strip() == "synth_seed_delta_v0":
                delta = data
            else:
                inner = data.get("payload")
                if isinstance(inner, dict) and str(inner.get("schema_version") or "").strip() == "synth_seed_delta_v0":
                    delta = inner
        if not delta:
            continue
        ok, msgs = apply_synth_seed_delta(repo_root, delta, allow_pending_validation=True)
        prefix = rec_path.name
        lines.extend(f"{prefix}: {m}" for m in msgs)
        if not ok:
            lines.append(f"{prefix}: synth_seed_delta merge failed")
    return lines


def process_results(state: dict) -> dict:
    """
    [ACTION]
    - Teleology: Consume the active observe manifest and receipts, then advance the pipeline's durable state based on the selected typed result.
    - Mechanism: Load the current manifest, select the primary receipt, normalize synthesis updates, mutate shard/controller state, and write cycle summaries plus assimilation/carry-forward artifacts.
    - Reads: The active observe manifest/receipt files, prior cycle summaries, and synthesis helpers imported from extract/select/compile stages.
    - Writes: Cycle summary JSON, cycle assimilation artifacts, carry-forward context, shard/controller state updates, and cycle event records.
    - Guarantee: Returns the cycle-summary payload for the processed cycle and leaves the pipeline state advanced to the next controller-visible checkpoint.
    - Fails: Missing manifests or malformed receipt surfaces degrade into explicit controller-visible summaries rather than silent success.
    - When-needed: Open when a caller needs the authoritative stage-6 result-processing flow for the current active cycle.
    - Escalates-to: system/lib/pipeline_recovery.py; system/lib/pipeline/stage_compile.py::compile_observe_plan; system/lib/phase_harbor.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _utc_now, _load_json, _write_json_atomic, _log, _short_hash
    from system.lib.observe_runtime import summarize_degraded_group_diagnostics
    from system.lib.seed_pipeline_controller import (
        advance_controller_after_results,
        controller_version_for_state,
    )

    manifest_path = str(state.get("observe_manifest_path") or "").strip()
    plan = _load_json(REPO_ROOT / state["observe_plan_path"]) or {}
    plan_dump_dir = str(plan.get("dump_dir") or _cycle_dir_rel(state)).strip()
    state["current_cycle_timeline_path"] = str(plan.get("cycle_timeline_path") or _cycle_timeline_rel(state)).strip()

    if manifest_path and plan_dump_dir:
        current_manifest = _load_json(REPO_ROOT / manifest_path) or {}
        manifest_dump_dir = str(
            current_manifest.get("dump_dir")
            or (current_manifest.get("config") or {}).get("dump_dir")
            or ""
        ).strip()
        if manifest_dump_dir and manifest_dump_dir != plan_dump_dir:
            manifest_path = ""

    manifest_path = manifest_path or _resolve_observe_record_path(state)
    if manifest_path:
        state["observe_manifest_path"] = manifest_path
    if not manifest_path:
        print("[INFO] No manifest path. Skipping result processing.")
        state["stage"] = "results_processed"
        _record_cycle_event(
            state,
            "results_processing_skipped",
            reason="missing_manifest",
            observe_plan_path=state.get("observe_plan_path"),
        )
        _log(state, "process_results", "No manifest to process")
        return {"status": "skipped"}

    manifest = _load_json(REPO_ROOT / manifest_path) or {}
    if manifest.get("observe_id"):
        state["observe_session_id"] = manifest.get("observe_id")

    dump_dir_rel = str(
        manifest.get("dump_dir")
        or (manifest.get("config") or {}).get("dump_dir")
        or plan_dump_dir
        or ""
    ).strip()
    dump_dir_path = (REPO_ROOT / dump_dir_rel) if dump_dir_rel else _cycle_dir_path(state)
    dump_dir_path.mkdir(parents=True, exist_ok=True)

    phase = _active_phase(state)
    receipt_payload, receipt_source, receipt_path, receipt_meta = _select_primary_receipt(state, manifest, plan=plan)
    active_cycle_mode = dump_dir_rel.startswith(f"{state['phase_dir']}/cycle_")
    if receipt_payload:
        synthesis_updates = _normalize_typed_receipt_for_controller(phase, receipt_payload)
        synthesis_source = receipt_source
    elif active_cycle_mode:
        synthesis_updates = _normalize_typed_receipt_for_controller(phase, {})
        synthesis_source = "missing_typed_receipt"
    else:
        synthesis_updates, synthesis_source = _load_synthesis_payload(state, manifest)

    synthesis_updates, payload_metrics = _sanitize_synthesis_payload(state, synthesis_updates)
    routing_ready = bool(
        str((synthesis_updates.get("routing_decision") or {}).get("decision") or "").strip()
        or str(synthesis_updates.get("decision") or "").strip()
    )
    if phase == "scope":
        artifact_semantics = "scope_receipt_projection"
    elif phase == "plan":
        artifact_semantics = "plan_receipt_projection"
    elif synthesis_source == "missing_typed_receipt":
        artifact_semantics = "probe_cycle_state_missing_receipt"
    elif bool(receipt_meta.get("is_fallback")):
        artifact_semantics = "probe_cycle_state_from_upstream_probe_fallback"
    else:
        artifact_semantics = "probe_routing_projection"
    synthesis_updates["artifact_meta"] = {
        "artifact_name": "routing_decision.json",
        "artifact_semantics": artifact_semantics,
        "phase": phase,
        "selected_receipt_group_label": receipt_meta.get("selected_group_label"),
        "selected_receipt_group_role": receipt_meta.get("selected_group_role"),
        "selected_receipt_source": synthesis_source,
        "selected_receipt_path": receipt_path,
        "routing_decision_ready": routing_ready,
    }

    shard_metrics = {"shard_updates_applied": 0, "new_shards_ingested": 0}
    if state.get("shards_path"):
        shards_path = REPO_ROOT / state["shards_path"]
        shards_data = _load_json(shards_path) or {}
        shards_data, shard_metrics = _apply_synthesis_updates_to_shards(
            state,
            shards_data,
            synthesis_updates,
            cycle=int(state["cycle"]),
        )
        if int(shard_metrics.get("shard_updates_applied") or 0) > 0 or int(
            shard_metrics.get("new_shards_ingested") or 0
        ) > 0:
            _write_json_atomic(shards_path, shards_data)

    groups = manifest.get("groups") if isinstance(manifest.get("groups"), list) else []
    probe_count = len(
        [
            group
            for group in groups
            if isinstance(group, dict) and str(group.get("role") or "probe").strip().lower() == "probe"
        ]
    )
    if probe_count == 0 and dump_dir_path.exists():
        probe_count = len(list(dump_dir_path.glob("probe_*_response.md")))

    runtime_state = str(
        manifest.get("runtime", {}).get("state")
        or manifest.get("state")
        or manifest.get("status")
        or "unknown"
    ).strip() or "unknown"
    degraded_groups = []
    group_diagnostics: list[dict[str, Any]] = []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = str(group.get("label") or "unknown").strip()
        group_state = str(group.get("response_status") or group.get("runtime_state") or "").strip()
        diag: dict[str, Any] = {
            "label": label,
            "status": group_state or "unknown",
            "role": str(group.get("role") or "probe").strip(),
        }
        error_val = (
            group.get("response_error")
            or group.get("error")
            or group.get("bridge_error")
            or ""
        )
        if isinstance(error_val, dict):
            error_val = error_val.get("message") or error_val.get("detail") or str(error_val)
        error_str = str(error_val).strip()
        if error_str:
            diag["error"] = error_str[:300]
        error_category = str(group.get("response_error_category") or "").strip()
        if error_category:
            diag["error_category"] = error_category[:120]
        error_stage = str(group.get("response_error_stage") or "").strip()
        if error_stage:
            diag["error_stage"] = error_stage[:120]
        transport = group.get("provider_transport") or group.get("transport")
        if transport:
            diag["transport"] = str(transport).strip()[:100]
        group_diagnostics.append(diag)
        if group_state in DEGRADED_GROUP_STATES:
            degraded_groups.append(f"{label}:{group_state}")
    degradation_summary = summarize_degraded_group_diagnostics(
        group_diagnostics,
        degraded_groups=degraded_groups,
        probe_count=probe_count,
    )

    selected_shard_ids = _selected_shard_ids_for_cycle(state)
    selected_sig = _selected_signature(selected_shard_ids)
    shard_updates_applied = int(shard_metrics["shard_updates_applied"])
    new_shards_ingested = int(shard_metrics["new_shards_ingested"])
    zero_evolution_streak = _cycle_zero_evolution_streak(
        state,
        cycle=int(state["cycle"]),
        shard_updates=shard_updates_applied,
        new_shards=new_shards_ingested,
    )
    frontier_repeat_streak = _cycle_frontier_repeat_streak(
        state,
        cycle=int(state["cycle"]),
        selected_signature=selected_sig,
    )

    cycle_summary = {
        "cycle": state["cycle"],
        "timestamp": _utc_now(),
        "phase": phase,
        "session_id": state.get("observe_session_id", "unknown"),
        "probe_count": probe_count,
        "dump_dir": dump_dir_rel or _cycle_dir_rel(state),
        "observe_manifest_path": manifest_path,
        "selected_shard_ids": selected_shard_ids,
        "selected_signature": selected_sig,
        "runtime_state": runtime_state,
        "degraded_groups": degraded_groups,
        "group_diagnostics": group_diagnostics,
        "degradation_summary": degradation_summary,
        "synthesis_source": synthesis_source,
        "synth_seed_snapshot_path": state.get("current_cycle_synth_snapshot_path"),
        "cycle_timeline_path": state.get("current_cycle_timeline_path"),
        "receipt_path": receipt_path,
        "latest_receipt_path": receipt_path,
        "selected_receipt_group_label": receipt_meta.get("selected_group_label"),
        "selected_receipt_group_role": receipt_meta.get("selected_group_role"),
        "selected_receipt_is_fallback": bool(receipt_meta.get("is_fallback")),
        "routing_decision": synthesis_updates.get("routing_decision", {}),
        "priority_action": synthesis_updates.get("priority_action", {}),
        "ordered_sequence": synthesis_updates.get("ordered_sequence", []),
        "shard_status_updates": synthesis_updates.get("shard_status_updates", []),
        "new_shards": synthesis_updates.get("new_shards", []),
        "new_shards_filtered_out": int(payload_metrics.get("dropped_new_shards") or 0),
        "shard_updates": shard_updates_applied,
        "new_shards_ingested": new_shards_ingested,
        "zero_evolution_streak": zero_evolution_streak,
        "frontier_repeat_streak": frontier_repeat_streak,
        "routing_artifact_meta": synthesis_updates.get("artifact_meta", {}),
    }

    controller_result = advance_controller_after_results(
        state,
        cycle_summary,
        synthesis_updates,
        repo_root=REPO_ROOT,
    )
    cycle_summary.update(
        {
            "controller_version": state.get("controller_version"),
            "controller_phase": state.get("controller_phase"),
            "current_layer_id": state.get("current_layer_id"),
            "current_layer_kind": state.get("current_layer_kind"),
            "current_task_id": state.get("current_task_id"),
            "confidence_score": state.get("confidence_score"),
            "uncertainty_score": state.get("uncertainty_score"),
            "gate_reason": state.get("gate_reason"),
            "locked_plan_path": state.get("locked_plan_path"),
            "apply_plan_path": state.get("apply_plan_path"),
            "apply_packet_path": state.get("apply_packet_path"),
            "task_dag_path": state.get("task_dag_path"),
            "controller_result": controller_result,
        }
    )

    cycle_assimilation = _build_cycle_assimilation(
        state,
        plan=plan,
        manifest=manifest,
        cycle_summary=cycle_summary,
        synthesis_updates=synthesis_updates,
        synthesis_source=synthesis_source,
        receipt_path=receipt_path,
        receipt_meta=receipt_meta,
    )
    cycle_assimilation_path = dump_dir_path / "cycle_assimilation.json"
    cycle_assimilation_rel = str(cycle_assimilation_path.relative_to(REPO_ROOT))
    cycle_summary["cycle_assimilation_path"] = cycle_assimilation_rel
    state["current_cycle_assimilation_path"] = cycle_assimilation_rel
    carry_forward_context = _build_cycle_carry_forward_context(
        state,
        cycle_summary=cycle_summary,
        cycle_assimilation=cycle_assimilation,
    )
    carry_forward_path = dump_dir_path / "carry_forward_context.json"
    carry_forward_rel = str(carry_forward_path.relative_to(REPO_ROOT))
    cycle_summary["carry_forward_context_path"] = carry_forward_rel
    state["current_cycle_carry_forward_path"] = carry_forward_rel

    _write_json_atomic(dump_dir_path / "_cycle_summary.json", cycle_summary)
    _write_json_atomic(dump_dir_path / "routing_decision.json", synthesis_updates)
    _write_json_atomic(cycle_assimilation_path, cycle_assimilation)
    _write_json_atomic(carry_forward_path, carry_forward_context)
    delta_lines = _try_apply_synth_seed_delta_receipts(plan, dump_dir_path, REPO_ROOT)
    if delta_lines:
        cycle_summary["synth_seed_delta_receipts"] = delta_lines
        _write_json_atomic(dump_dir_path / "_cycle_summary.json", cycle_summary)
    _record_cycle_event(
        state,
        "results_processed",
        runtime_state=runtime_state,
        synthesis_source=synthesis_source,
        receipt_path=receipt_path,
        selected_receipt_group_label=receipt_meta.get("selected_group_label"),
        selected_receipt_group_role=receipt_meta.get("selected_group_role"),
        selected_receipt_is_fallback=bool(receipt_meta.get("is_fallback")),
        routing_decision=((synthesis_updates.get("routing_decision") or {}).get("decision") or synthesis_updates.get("decision") or None),
        cycle_summary_path=str((dump_dir_path / "_cycle_summary.json").relative_to(REPO_ROOT)),
        routing_artifact_path=str((dump_dir_path / "routing_decision.json").relative_to(REPO_ROOT)),
        cycle_assimilation_path=cycle_assimilation_rel,
    )

    meta_ledger_path = _find_meta_ledger(state)
    if meta_ledger_path:
        ledger = _load_json(meta_ledger_path) or {
            "phase_id": _phase_id_from_state(state),
            "phase_number": controller_version_for_state(state, repo_root=REPO_ROOT),
            "phase_title": Path(str(state.get("phase_dir") or "")).name,
            "phase_dir": str(state.get("phase_dir") or ""),
            "family_dir": str(state.get("family_dir") or ""),
            "parent_phase_id": None,
            "kind": "subphase_meta_ledger",
            "schema_version": "subphase_meta_ledger_v1",
            "purpose": "Compressed memory of what happened within this subphase, cycle by cycle.",
            "entries": [],
        }
        entries = ledger.get("entries")
        if not isinstance(entries, list):
            entries = []
            ledger["entries"] = entries
        entry_id = f"{_phase_id_from_state(state)}_cycle_{state['cycle']}_{_short_hash(_utc_now())}"
        what_was_learned: list[str] = []
        priority_summary = _priority_action_summary(synthesis_updates.get("priority_action"))
        if priority_summary:
            what_was_learned.append(f"Priority: {priority_summary[:200]}")
        reasoning = str(synthesis_updates.get("reasoning") or synthesis_updates.get("rationale") or "").strip()
        if reasoning:
            what_was_learned.append(reasoning[:200])
        open_questions_remaining: list[str] = []
        shards_addressed: list[str] = []
        for update in synthesis_updates.get("shard_status_updates", []):
            if not isinstance(update, dict):
                continue
            shard_id = str(update.get("shard_id") or update.get("id") or "").strip()
            if shard_id:
                shards_addressed.append(shard_id)
        for shard in synthesis_updates.get("new_shards", []):
            if not isinstance(shard, dict):
                continue
            question = str(shard.get("question") or shard.get("clarified_statement") or "").strip()
            if question:
                what_was_learned.append(f"New question: {question[:150]}")
                open_questions_remaining.append(question[:200])
        entries.append(
            {
                "cycle": int(state["cycle"]),
                "entry_id": entry_id,
                "timestamp": _utc_now(),
                "action": f"pipeline_cycle_{state['cycle']}_results",
                "summary": f"Processed cycle {state['cycle']} in phase {phase}. Session: {state.get('observe_session_id', 'unknown')}.",
                "what_was_done": [
                    f"Processed {probe_count} probe groups.",
                    f"Updated {shard_updates_applied} shard statuses.",
                    f"Ingested {new_shards_ingested} new shards.",
                    f"Ingested receipts from {synthesis_source}.",
                ],
                "what_was_learned": what_was_learned,
                "shards_addressed": sorted({item for item in shards_addressed if item}),
                "files_changed": [],
                "open_questions_remaining": open_questions_remaining[:8],
            }
        )
        _write_json_atomic(meta_ledger_path, ledger)
        state["meta_ledger_path"] = str(meta_ledger_path.relative_to(REPO_ROOT))

    state["stage"] = "results_processed"
    state["cycle"] += 1
    if state.get("gate_reason") == "apply_review_pending":
        state["stage"] = "apply_ready"
    _log(
        state,
        "process_results",
        f"Cycle {state['cycle'] - 1} results processed: phase={phase}, probes={probe_count}, shard_updates={shard_updates_applied}, new_shards={new_shards_ingested}"
        + (
            f", controller gate={state.get('gate_reason')}"
            if str(state.get("gate_reason") or "").strip() not in {"", "none"}
            else ""
        ),
    )
    return {
        "status": "processed",
        "synthesis": synthesis_updates,
        "cycle_summary": cycle_summary,
        "cycle_assimilation": cycle_assimilation,
    }


def repair_results_range(
    state: dict,
    *,
    from_cycle: int,
    to_cycle: int,
    apply: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Re-run or preview result-processing across a bounded cycle range so historical controller artifacts can be repaired deterministically.
    - Mechanism: Iterate the requested cycle window, replay stage-6 processing logic for each cycle, and optionally write the repaired outputs back to disk.
    - Reads: Existing cycle manifests, receipts, summaries, and controller state for the requested cycle range.
    - Writes: When `apply=True`, rewrites repaired cycle artifacts and controller-visible summaries for the requested range.
    - Guarantee: Returns a structured repair summary for the requested range whether running in preview or apply mode.
    - Fails: Propagates invalid cycle-range arguments and repair-time filesystem errors.
    - When-needed: Open when a caller needs the bounded repair path for already-finished cycle results instead of the normal single-cycle processing flow.
    - Escalates-to: system/lib/pipeline_recovery.py; pipeline_advance.py; system/lib/pipeline/stage_process.py::process_results
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _load_json, _write_json_atomic

    start_cycle = int(from_cycle)
    end_cycle = int(to_cycle)
    if end_cycle < start_cycle:
        raise ValueError("to_cycle must be >= from_cycle")

    working_shards = None
    if apply:
        if not state.get("shards_path"):
            raise ValueError("state has no shards_path; cannot apply repair")
        working_shards = _load_json(REPO_ROOT / state["shards_path"]) or {"shards": []}

    cycles: list[dict[str, Any]] = []
    totals = {
        "parsed_shard_updates": 0,
        "parsed_new_shards": 0,
        "applied_shard_updates": 0,
        "applied_new_shards": 0,
    }

    for cycle in range(start_cycle, end_cycle + 1):
        from system.lib.pipeline.stage_select import _load_synthesis_payload_for_cycle

        payload, source = _load_synthesis_payload_for_cycle(state, cycle)
        probe_questions: list[str] = []
        for candidate in _cycle_path_candidates(state, cycle, "observe_plan.json"):
            probe_questions = _probe_questions_for_plan_path(candidate)
            if probe_questions or candidate.exists():
                break
        payload, payload_metrics = _sanitize_synthesis_payload(state, payload, probe_questions=probe_questions)
        parsed_updates = len(payload.get("shard_status_updates", []))
        parsed_new_shards = len(payload.get("new_shards", []))
        totals["parsed_shard_updates"] += parsed_updates
        totals["parsed_new_shards"] += parsed_new_shards

        cycle_summary_candidates = [
            _cycle_dir_path(state, cycle) / "_cycle_summary.json",
            REPO_ROOT / _legacy_dump_dir_rel(state, cycle) / "_cycle_summary.json",
        ]
        current_cycle = int(state.get("cycle") or 0) - 1
        if current_cycle == cycle:
            current_assimilation = str(state.get("current_cycle_assimilation_path") or "").strip()
            if current_assimilation:
                cycle_summary_candidates.append(
                    (REPO_ROOT / current_assimilation).with_name("_cycle_summary.json")
                )
            current_cycle_dir = str(state.get("current_cycle_dir") or "").strip()
            if current_cycle_dir:
                cycle_summary_candidates.append(REPO_ROOT / current_cycle_dir / "_cycle_summary.json")

        cycle_summary_path = cycle_summary_candidates[0]
        existing_summary = None
        for candidate in cycle_summary_candidates:
            loaded_summary = _load_json(candidate)
            if isinstance(loaded_summary, dict):
                cycle_summary_path = candidate
                existing_summary = loaded_summary
                break
        if not isinstance(existing_summary, dict):
            existing_summary = {"cycle": cycle}
        applied_metrics = {
            "shard_updates_applied": 0,
            "new_shards_ingested": 0,
        }

        if apply and working_shards is not None:
            working_shards, applied_metrics = _apply_synthesis_updates_to_shards(
                state,
                working_shards,
                payload,
                cycle=cycle,
            )
            totals["applied_shard_updates"] += int(applied_metrics["shard_updates_applied"])
            totals["applied_new_shards"] += int(applied_metrics["new_shards_ingested"])

            selected_sig = str(existing_summary.get("selected_signature") or "").strip()
            updated_summary = dict(existing_summary)
            updated_summary.update({
                "priority_action": payload.get("priority_action", {}),
                "ordered_sequence": payload.get("ordered_sequence", []),
                "shard_status_updates": payload.get("shard_status_updates", []),
                "new_shards": payload.get("new_shards", []),
                "new_shards_filtered_out": int(payload_metrics.get("dropped_new_shards") or 0),
                "shard_updates": int(applied_metrics["shard_updates_applied"]),
                "new_shards_ingested": int(applied_metrics["new_shards_ingested"]),
                "synthesis_source": source,
                "zero_evolution_streak": _cycle_zero_evolution_streak(
                    state,
                    cycle=cycle,
                    shard_updates=int(applied_metrics["shard_updates_applied"]),
                    new_shards=int(applied_metrics["new_shards_ingested"]),
                ),
                "frontier_repeat_streak": _cycle_frontier_repeat_streak(
                    state,
                    cycle=cycle,
                    selected_signature=selected_sig,
                ),
            })
            plan_payload = None
            for candidate in _cycle_path_candidates(state, cycle, "observe_plan.json"):
                plan_payload = _load_json(candidate)
                if isinstance(plan_payload, dict):
                    break
            if not isinstance(plan_payload, dict):
                plan_payload = {}

            manifest_rel = str(updated_summary.get("observe_manifest_path") or "").strip()
            manifest_payload = _load_json(REPO_ROOT / manifest_rel) if manifest_rel else {}
            if not isinstance(manifest_payload, dict):
                manifest_payload = {}
            manifest_groups = manifest_payload.get("groups")
            if isinstance(manifest_groups, list):
                probe_count = sum(
                    1
                    for group in manifest_groups
                    if isinstance(group, dict)
                    and str(group.get("role") or "probe").strip().lower() == "probe"
                )
                updated_summary["degradation_summary"] = summarize_degraded_group_diagnostics(
                    manifest_groups,
                    degraded_groups=updated_summary.get("degraded_groups"),
                    probe_count=probe_count,
                )

            cycle_summary_path.parent.mkdir(parents=True, exist_ok=True)
            cycle_summary_path.write_text(
                json.dumps(updated_summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            repair_state = dict(state)
            repair_state.update(
                {
                    "cycle": cycle,
                    "phase": str(updated_summary.get("phase") or state.get("phase") or "").strip(),
                    "controller_phase": str(
                        updated_summary.get("controller_phase")
                        or state.get("controller_phase")
                        or updated_summary.get("phase")
                        or state.get("phase")
                        or ""
                    ).strip(),
                    "observe_session_id": updated_summary.get("session_id") or state.get("observe_session_id"),
                    "observe_manifest_path": manifest_rel or state.get("observe_manifest_path"),
                    "gate_reason": updated_summary.get("gate_reason") or state.get("gate_reason"),
                }
            )
            receipt_meta = {
                "selected_group_label": updated_summary.get("selected_receipt_group_label"),
                "selected_group_role": updated_summary.get("selected_receipt_group_role"),
                "is_fallback": bool(updated_summary.get("selected_receipt_is_fallback")),
            }
            cycle_assimilation = _build_cycle_assimilation(
                repair_state,
                plan=plan_payload,
                manifest=manifest_payload,
                cycle_summary=updated_summary,
                synthesis_updates=payload,
                synthesis_source=source,
                receipt_path=updated_summary.get("receipt_path"),
                receipt_meta=receipt_meta,
            )
            carry_forward_context = _build_cycle_carry_forward_context(
                repair_state,
                cycle_summary=updated_summary,
                cycle_assimilation=cycle_assimilation,
            )
            cycle_dir = cycle_summary_path.parent
            _write_json_atomic(cycle_dir / "cycle_assimilation.json", cycle_assimilation)
            _write_json_atomic(cycle_dir / "carry_forward_context.json", carry_forward_context)

        cycles.append({
            "cycle": cycle,
            "synthesis_source": source,
            "parsed_shard_updates": parsed_updates,
            "parsed_new_shards": parsed_new_shards,
            "filtered_new_shards": int(payload_metrics.get("dropped_new_shards") or 0),
            "applied_shard_updates": int(applied_metrics["shard_updates_applied"]),
            "applied_new_shards": int(applied_metrics["new_shards_ingested"]),
            "cycle_summary_path": str(cycle_summary_path.relative_to(REPO_ROOT)) if cycle_summary_path.exists() else None,
        })

    if (
        apply
        and working_shards is not None
        and state.get("shards_path")
        and (totals["applied_shard_updates"] or totals["applied_new_shards"])
    ):
        (REPO_ROOT / state["shards_path"]).write_text(
            json.dumps(working_shards, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    return {
        "status": "applied" if apply else "dry_run",
        "from_cycle": start_cycle,
        "to_cycle": end_cycle,
        "cycles": cycles,
        "totals": totals,
    }


def _probe_questions_for_plan_path(plan_path: Path | None) -> list[str]:
    """Re-export for use by repair_results_range."""
    from system.lib.pipeline.stage_compile import _probe_questions_for_plan_path as _pq
    return _pq(plan_path)


def _lazy_repo_root() -> Path:
    from seed_pipeline import REPO_ROOT
    return REPO_ROOT
