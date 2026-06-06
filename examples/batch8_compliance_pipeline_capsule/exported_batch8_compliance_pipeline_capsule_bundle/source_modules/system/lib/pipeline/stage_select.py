"""
[PURPOSE]
- Teleology: Choose the next bounded shard working set for the observe loop, either by following the active task-DAG layer or by scoring pending shards for novelty, grounding, and intent richness.
- Mechanism: Normalize shard state, refresh controller artifacts, consult task-DAG overlays when present, then persist selection metadata back onto the shard ledger for the active cycle.

[INTERFACE]
- Exports: select_shards plus synthesis-payload helpers reused by later pipeline stages.
- Reads: The current shard ledger, controller state, meta-ledger hints, and prior cycle summaries.
- Writes: Updated shard status/selection counters and stage progression back through seed_pipeline persistence helpers.

[FLOW]
- Normalize shards and refresh controller/task-DAG projections -> prefer active DAG-scoped shard ids when available -> otherwise score actionable candidates and diversify by concept group -> persist selection metadata for the current cycle.
- When-needed: Open when a pipeline run needs the exact place that turns shard backlog state into the bounded working set for the next probe cycle.
- Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/pipeline/stage_extract.py; system/lib/pipeline/stage_process.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- system.lib.pipeline.stage_extract: Supplies shard normalization, synthesis payload loading, cycle history, and diversity helpers.
- seed_pipeline: Supplies repo-root persistence, logging, and selection scoring constants.
- system.lib.seed_pipeline_controller: Supplies controller/task-DAG overlays and shard candidate constraints.

[CONSTRAINTS]
- Guarantee: This stage is the authority for which shards move into `selected` for the current cycle and for how selection counters/cooldowns advance.
- Non-goal: This module does not dispatch observe work or interpret completed receipts; later stages own those transitions.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from system.lib.pipeline.stage_extract import (
    TERMINAL_SHARD_STATUSES,
    _active_phase,
    _cycle_dir_path,
    _cycle_dir_rel,
    _cycle_path_candidates,
    _cycle_timeline_rel,
    _empty_synthesis_payload,
    _extract_markdown_section,
    _extract_synthesis_json,
    _guess_concept_group,
    _has_synthesis_payload,
    _legacy_dump_dir_rel,
    _load_cycle_summary_by_cycle,
    _load_receipt_payload,
    _normalize_shards_payload,
    _normalize_shard_record,
    _normalize_synthesis_payload,
    _phase_id_from_state,
    _pick_diverse_shards,
    _selected_shard_ids_for_cycle,
    _stringify_reason,
)


# ---------------------------------------------------------------------------
# Stage 2: Select shards for the working set
# ---------------------------------------------------------------------------
def select_shards(state: dict, *, max_shards: int = 8) -> list[dict]:
    """
    [ACTION]
    - Teleology: Materialize the next shard working set for the active cycle.
    - Mechanism: Normalize shard payloads, refresh controller artifacts, honor any active task-DAG layer, otherwise rank actionable shards by status, novelty, grounding, and intent richness before applying diversity caps.
    - Reads: state, the shard ledger at state["shards_path"], controller/task-DAG projections, and prior selection metadata embedded on shards.
    - Writes: Updated shard selection counters, cooldown metadata, selection timestamps, and stage progression back to the shard ledger and in-memory state.
    - Guarantee: Returns the shard dicts chosen for the next working set and advances state["stage"] to `shards_selected`.
    - Fails: Propagates file and JSON failures from the shard ledger or downstream controller helpers.
    - When-needed: Open when debugging why specific shards were selected, cooled down, or overridden by task-DAG scope for the next probe cycle.
    - Escalates-to: system/lib/seed_pipeline_controller.py; system/lib/pipeline/stage_process.py; system/lib/pipeline/stage_extract.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, STATUS_SELECTION_SCORES, _utc_now, _write_json_atomic, _log
    from system.lib.seed_pipeline_controller import (
        active_task_dag_layer,
        active_task_dag_shard_ids,
        constrain_shard_candidates,
        ensure_task_dag,
        resolve_active_task,
        write_controller_artifacts,
    )

    shards_data, changed = _normalize_shards_payload(
        json.loads((REPO_ROOT / state["shards_path"]).read_text())
    )
    all_shards = shards_data["shards"]
    current_cycle = int(state.get("cycle") or 0)
    write_controller_artifacts(state, repo_root=REPO_ROOT)
    ensure_task_dag(state, repo_root=REPO_ROOT)

    meta_ledger_path = _find_meta_ledger(state)
    if meta_ledger_path and meta_ledger_path.exists():
        state["meta_ledger_path"] = str(meta_ledger_path.relative_to(REPO_ROOT))

    for shard in all_shards:
        last_selected_cycle = shard.get("last_selected_cycle")
        last_status_change_cycle = shard.get("last_status_change_cycle")
        if (
            int(shard.get("consecutive_selected_cycles") or 0) >= 2
            and last_selected_cycle is not None
            and int(last_selected_cycle) >= current_cycle - 1
            and (last_status_change_cycle is None or int(last_status_change_cycle) < int(last_selected_cycle))
            and int(shard.get("cooldown_until_cycle") or 0) <= current_cycle
        ):
            shard["cooldown_until_cycle"] = current_cycle + 2
            shard["consecutive_selected_cycles"] = 0
            if shard.get("status") == "selected":
                shard["status"] = "pending"
            changed = True

    dag_layer = active_task_dag_layer(state, repo_root=REPO_ROOT)
    dag_shard_ids = active_task_dag_shard_ids(state, repo_root=REPO_ROOT)
    if dag_layer:
        if not dag_shard_ids:
            active_task = resolve_active_task(state, repo_root=REPO_ROOT) or {}
            dag_shard_ids = [
                str(item).strip()
                for item in (active_task.get("source_shard_ids") or [])
                if str(item).strip()
            ]
        dag_selected: list[dict] = []
        dag_selected_ids = {str(item).strip() for item in dag_shard_ids if str(item).strip()}
        for shard in all_shards:
            shard_id = str(shard.get("id") or "").strip()
            previous_status = str(shard.get("status") or "pending")
            previous_last_selected = shard.get("last_selected_cycle")
            if shard_id in dag_selected_ids:
                dag_selected.append(shard)
                shard["selection_count"] = int(shard.get("selection_count") or 0) + 1
                if previous_last_selected is not None and int(previous_last_selected) == current_cycle - 1:
                    shard["consecutive_selected_cycles"] = int(shard.get("consecutive_selected_cycles") or 0) + 1
                else:
                    shard["consecutive_selected_cycles"] = 1
                shard["last_selected_cycle"] = current_cycle
                shard["status"] = "selected"
            else:
                if previous_status == "selected":
                    shard["status"] = "pending"
                if previous_last_selected is None or int(previous_last_selected) != current_cycle - 1:
                    shard["consecutive_selected_cycles"] = 0
        shards_data["selected_at"] = _utc_now()
        _write_json_atomic(REPO_ROOT / state["shards_path"], shards_data)
        state["stage"] = "shards_selected"
        _log(
            state,
            "select_shards",
            f"Selected {len(dag_selected)} DAG-scoped shards for layer {dag_layer.get('layer_id')} ({dag_layer.get('layer_kind')})",
        )
        return dag_selected[:max_shards] if max_shards > 0 else dag_selected

    def score(shard: dict) -> int:
        status = str(shard.get("status") or "pending")
        score_value = STATUS_SELECTION_SCORES.get(status, 0)
        relevant_files = shard.get("relevant_files") or []
        score_value += min(
            2,
            sum(1 for file_path in relevant_files if (REPO_ROOT / str(file_path)).exists()),
        )
        if shard.get("intent_provenance"):
            score_value += 1
        if "synthesis_emergence" in (shard.get("intent_provenance") or []):
            score_value += 2
        last_selected_cycle = shard.get("last_selected_cycle")
        if last_selected_cycle is None:
            score_value += 4
        else:
            gap = current_cycle - int(last_selected_cycle)
            if gap >= 3:
                score_value += 3
            elif gap == 2:
                score_value += 2
            elif gap == 1:
                score_value -= 2
            else:
                score_value -= 4
        score_value -= min(3, int(shard.get("consecutive_selected_cycles") or 0))
        score_value -= min(2, int(shard.get("selection_count") or 0) // 4)
        return score_value

    candidates = [
        shard for shard in all_shards
        if str(shard.get("status") or "pending") not in TERMINAL_SHARD_STATUSES
        and int(shard.get("cooldown_until_cycle") or 0) <= current_cycle
    ]
    candidates, active_task, override_selection = constrain_shard_candidates(
        state,
        candidates,
        repo_root=REPO_ROOT,
    )
    candidates.sort(key=score, reverse=True)

    rotation_slots = max(1, max_shards // 4)
    rotation_pool = [
        shard for shard in candidates
        if shard.get("last_selected_cycle") is None
        or current_cycle - int(shard.get("last_selected_cycle") or 0) >= 2
    ]

    group_counts: dict[str, int] = {}
    selected_ids: set[str] = set()
    selected: list[dict] = []
    selected.extend(
        _pick_diverse_shards(
            rotation_pool,
            count=min(rotation_slots, max_shards),
            group_counts=group_counts,
            selected_ids=selected_ids,
        )
    )
    selected.extend(
        _pick_diverse_shards(
            candidates,
            count=max_shards - len(selected),
            group_counts=group_counts,
            selected_ids=selected_ids,
        )
    )

    if override_selection:
        selected = selected[:max_shards]
        selected_ids = {
            str(shard.get("id") or "").strip()
            for shard in selected
            if str(shard.get("id") or "").strip()
        }

    for shard in all_shards:
        shard_id = str(shard.get("id") or "").strip()
        previous_status = str(shard.get("status") or "pending")
        previous_last_selected = shard.get("last_selected_cycle")
        if shard_id in selected_ids:
            shard["selection_count"] = int(shard.get("selection_count") or 0) + 1
            if previous_last_selected is not None and int(previous_last_selected) == current_cycle - 1:
                shard["consecutive_selected_cycles"] = int(shard.get("consecutive_selected_cycles") or 0) + 1
            else:
                shard["consecutive_selected_cycles"] = 1
            shard["last_selected_cycle"] = current_cycle
            shard["status"] = "selected"
        else:
            if previous_status == "selected":
                shard["status"] = "pending"
            if previous_last_selected is None or int(previous_last_selected) != current_cycle - 1:
                shard["consecutive_selected_cycles"] = 0

    shards_data["selected_at"] = _utc_now()
    _write_json_atomic(REPO_ROOT / state["shards_path"], shards_data)

    state["stage"] = "shards_selected"
    if active_task and active_task.get("task_id"):
        state["current_task_id"] = active_task["task_id"]
    _log(
        state,
        "select_shards",
        (
            f"Selected {len(selected)} of {len(all_shards)} shards "
            f"(concept groups: {list(group_counts.keys())})"
            + (
                f" for task {state.get('current_task_id')}"
                if state.get("current_task_id")
                else ""
            )
        ),
    )
    return selected


# ---------------------------------------------------------------------------
# Synthesis payload loading helpers (used by select and process stages)
# ---------------------------------------------------------------------------

def _load_surface_payload(path: Path) -> dict[str, Any] | None:
    from seed_pipeline import _load_json
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return None
    surfaced = payload.get("payload")
    if not isinstance(surfaced, dict):
        return None
    normalized = _normalize_synthesis_payload(surfaced)
    return normalized if _has_synthesis_payload(normalized) else None


def _find_synthesis_group(manifest: dict | None) -> dict[str, Any] | None:
    if not isinstance(manifest, dict):
        return None
    groups = manifest.get("groups") if isinstance(manifest.get("groups"), list) else []
    for group in groups:
        if not isinstance(group, dict):
            continue
        label = str(group.get("label") or "").strip().lower()
        role = str(group.get("role") or "").strip().lower()
        if role in {"synthesis", "evaluation"} or label in {"synthesis", "router", "validator"}:
            return group
    return None


def _load_synthesis_payload_from_dump_dir(dump_dir_path: Path) -> tuple[dict[str, Any], str]:
    surface_candidates = [
        *sorted(dump_dir_path.glob("*synthesis*.surface.json")),
        *sorted(dump_dir_path.glob("*router*.surface.json")),
        *sorted(dump_dir_path.glob("*validator*.surface.json")),
        dump_dir_path / "_synthesis.surface.json",
        dump_dir_path / "_router.surface.json",
        dump_dir_path / "_validator.surface.json",
        dump_dir_path / "06_synthesis_response.surface.json",
        dump_dir_path / "synthesis_response.surface.json",
    ]
    seen_surface: set[Path] = set()
    for candidate in surface_candidates:
        if candidate in seen_surface:
            continue
        seen_surface.add(candidate)
        payload = _load_surface_payload(candidate)
        if payload:
            return payload, "response_surface_sidecar"

    response_candidates = [
        *sorted(dump_dir_path.glob("*synthesis*_response.md")),
        *sorted(dump_dir_path.glob("*router*_response.md")),
        *sorted(dump_dir_path.glob("*validator*_response.md")),
        dump_dir_path / "_synthesis.md",
        dump_dir_path / "_router.md",
        dump_dir_path / "_validator.md",
        dump_dir_path / "06_synthesis_response.md",
        dump_dir_path / "synthesis_response.md",
    ]
    seen_response: set[Path] = set()
    for candidate in response_candidates:
        if candidate in seen_response or not candidate.exists():
            continue
        seen_response.add(candidate)
        payload = _extract_synthesis_json(candidate.read_text(encoding="utf-8"))
        if _has_synthesis_payload(payload):
            return payload, "response_markdown"

    return _empty_synthesis_payload(), "none"


def _load_synthesis_payload(state: dict, manifest: dict | None = None) -> tuple[dict[str, Any], str]:
    from seed_pipeline import REPO_ROOT, _load_json

    synthesis_group = _find_synthesis_group(manifest)
    if synthesis_group:
        response_surface_file = str(synthesis_group.get("response_surface_file") or "").strip()
        if response_surface_file:
            payload = _load_surface_payload(REPO_ROOT / response_surface_file)
            if payload:
                return payload, "response_surface_sidecar"

        response_file = str(synthesis_group.get("response_file") or "").strip()
        if response_file:
            response_path = REPO_ROOT / response_file
            if response_path.exists():
                payload = _extract_synthesis_json(response_path.read_text(encoding="utf-8"))
                if _has_synthesis_payload(payload):
                    return payload, "response_markdown"

    dump_dir = ""
    if isinstance(manifest, dict):
        dump_dir = str(
            manifest.get("dump_dir")
            or (manifest.get("config") or {}).get("dump_dir")
            or ""
        ).strip()
    if not dump_dir:
        plan = _load_json(REPO_ROOT / str(state.get("observe_plan_path") or ""))
        if isinstance(plan, dict):
            dump_dir = str(plan.get("dump_dir") or "").strip()
    if dump_dir:
        payload, source = _load_synthesis_payload_from_dump_dir(REPO_ROOT / dump_dir)
        if _has_synthesis_payload(payload):
            return payload, source

    result_note = REPO_ROOT / state["phase_dir"] / f"Pass {state['cycle'] + 1} Observe Result.md"
    if result_note.exists():
        payload = _extract_synthesis_json(result_note.read_text(encoding="utf-8"))
        if _has_synthesis_payload(payload):
            return payload, "response_markdown"

    return _empty_synthesis_payload(), "none"


def _load_synthesis_payload_for_cycle(state: dict, cycle: int) -> tuple[dict[str, Any], str]:
    from seed_pipeline import _load_json

    if cycle < 0:
        return _empty_synthesis_payload(), "none"
    for candidate in _cycle_path_candidates(state, cycle, "routing_decision.json"):
        payload = _load_json(candidate)
        if isinstance(payload, dict) and payload:
            return _normalize_synthesis_payload(payload), "typed_receipt"
    for dump_dir_path in (_cycle_dir_path(state, cycle), _lazy_repo_root() / _legacy_dump_dir_rel(state, cycle)):
        if dump_dir_path.exists():
            payload, source = _load_synthesis_payload_from_dump_dir(dump_dir_path)
            if _has_synthesis_payload(payload):
                return payload, source
    return _empty_synthesis_payload(), "none"


# ---------------------------------------------------------------------------
# Summary and carry-forward helpers
# ---------------------------------------------------------------------------

def _priority_action_summary(priority_action: Any) -> str:
    if isinstance(priority_action, dict):
        for key in ("summary", "action", "step", "title", "description"):
            text = str(priority_action.get(key) or "").strip()
            if text:
                return text
        return json.dumps(priority_action, ensure_ascii=False, sort_keys=True)[:400]
    return str(priority_action or "").strip()


def _ordered_step_summary(item: Any) -> str:
    if isinstance(item, dict):
        for key in ("step", "action", "summary", "title", "description"):
            text = str(item.get(key) or "").strip()
            if text:
                return text
        return json.dumps(item, ensure_ascii=False, sort_keys=True)[:240]
    return str(item or "").strip()


def _build_previous_cycle_findings(summary: dict | None, payload: dict[str, Any], cycle: int) -> str:
    from seed_pipeline import _dedupe_strings

    # Pull from multiple sources
    priority_action = payload.get("priority_action") or (summary or {}).get("priority_action") or {}
    ordered_sequence = payload.get("ordered_sequence") or (summary or {}).get("ordered_sequence") or []
    shard_updates = payload.get("shard_status_updates") or (summary or {}).get("shard_status_updates") or []
    new_shards = payload.get("new_shards") or (summary or {}).get("new_shards") or []

    decision = str(payload.get("decision") or (summary or {}).get("decision") or "").strip()
    reasoning = str(payload.get("reasoning") or (summary or {}).get("reasoning") or "").strip()
    newly_relevant = payload.get("newly_relevant_files") or (summary or {}).get("newly_relevant_files") or []
    degraded_groups = list((summary or {}).get("degraded_groups") or [])

    lines = [f"### Cycle {cycle} Carry-Forward", ""]

    if decision:
        lines.extend([f"Last routing decision: **{decision}**", ""])
    if reasoning:
        truncated = reasoning[:600].rsplit(" ", 1)[0] if len(reasoning) > 600 else reasoning
        lines.extend([f"Router reasoning: {truncated}", ""])

    if degraded_groups:
        lines.append("Degraded/failed groups (bridge transport failures, not missing scope):")
        lines.extend(f"- {item}" for item in degraded_groups[:6])
        lines.append("")

    if newly_relevant and isinstance(newly_relevant, list):
        lines.append("Files the router identified as relevant:")
        lines.extend(f"- {item}" for item in _dedupe_strings(newly_relevant)[:8])
        lines.append("")

    priority_summary = _priority_action_summary(priority_action)
    if priority_summary:
        lines.extend([
            "Priority summary:",
            f"- {priority_summary}",
            "",
        ])

    ordered_lines = [
        _ordered_step_summary(item)
        for item in ordered_sequence[:4]
        if _ordered_step_summary(item)
    ]
    if ordered_lines:
        lines.append("Top ordered steps:")
        lines.extend(f"- {item}" for item in ordered_lines)
        lines.append("")

    shard_lines: list[str] = []
    for item in shard_updates[:5]:
        if not isinstance(item, dict):
            continue
        shard_id = str(item.get("id") or "").strip()
        new_status = str(item.get("new_status") or "").strip()
        reason = str(item.get("reason") or "").strip()
        if not shard_id:
            continue
        detail = f"{shard_id} -> {new_status}" if new_status else shard_id
        if reason:
            detail = f"{detail}: {reason}"
        shard_lines.append(detail)
    if shard_lines:
        lines.append("Shard changes:")
        lines.extend(f"- {item}" for item in shard_lines)
        lines.append("")

    new_question_lines: list[str] = []
    for item in new_shards[:5]:
        if isinstance(item, dict):
            text = str(item.get("question") or item.get("clarified_statement") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            new_question_lines.append(text)
    if new_question_lines:
        lines.append("New questions:")
        lines.extend(f"- {item}" for item in new_question_lines)
        lines.append("")

    text = "\n".join(lines).strip()
    if len(text) > 3000:
        text = text[:3000].rsplit("\n", 1)[0].rstrip() + "\n- [carry-forward truncated]"
    return text


# ---------------------------------------------------------------------------
# Discover helpers
# ---------------------------------------------------------------------------

def _find_latest_state() -> Path | None:
    """Auto-discover the most recent runtime-eligible pipeline_state.json in the repo."""
    from seed_pipeline import REPO_ROOT
    from system.lib.phase_lifecycle import resolve_latest_runtime_state

    return resolve_latest_runtime_state(REPO_ROOT)


def _find_meta_ledger(state: dict) -> Path | None:
    """Find the active subphase meta_ledger.json."""
    from seed_pipeline import REPO_ROOT

    phase_token = str(state.get("phase_dir") or "").strip()
    if not phase_token:
        return None
    candidate = REPO_ROOT / phase_token / "meta_ledger.json"
    if candidate.exists():
        return candidate
    return None


def _observe_record_candidates(state: dict, result: dict | None = None) -> list[str]:
    """Return likely observe history/runtime artifacts for a completed session."""
    candidates: list[str] = []
    seen: set[str] = set()

    def add(rel_path: str | None) -> None:
        rel = str(rel_path or "").strip()
        if not rel or rel in seen:
            return
        seen.add(rel)
        candidates.append(rel)

    dump_dir = ""
    if result:
        add(result.get("entry_file"))
        add(result.get("runtime_manifest"))
        add(result.get("manifest_path"))
        dump_dir = str(result.get("dump_dir") or "").strip()

    observe_id = str((result or {}).get("observe_id") or state.get("observe_session_id") or "").strip()
    if observe_id:
        add(f"tools/meta/apply/observe_history/entries/{observe_id}.json")

    plan_path = str(state.get("observe_plan_path") or "").strip()
    if not dump_dir and plan_path:
        from seed_pipeline import REPO_ROOT
        plan_abs = REPO_ROOT / plan_path
        if plan_abs.exists():
            try:
                plan = json.loads(plan_abs.read_text())
                dump_dir = str(plan.get("dump_dir") or "").strip()
            except json.JSONDecodeError:
                dump_dir = ""
    if dump_dir:
        add(
            _find_history_entry_by_dump_dir(
                dump_dir,
                min_started_at=str(
                    state.get("observe_dispatch_started_at")
                    or state.get("created_at")
                    or ""
                ).strip()
                or None,
            )
        )
        add(f"{dump_dir}/_session_manifest.json")

    return candidates


def _find_history_entry_by_dump_dir(dump_dir: str, *, min_started_at: str | None = None) -> str | None:
    """Return the newest observe-history entry that owns the given dump_dir."""
    from seed_pipeline import REPO_ROOT, _timestamp_to_epoch

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
            or (payload.get("config") or {}).get("dump_dir")
            or ""
        ).strip()
        if candidate_dump != rel_dump_dir:
            continue
        if min_epoch is not None and candidate.stat().st_mtime < min_epoch:
            continue
        matches.append(candidate)

    if not matches:
        return None
    return str(max(matches, key=lambda p: p.stat().st_mtime).relative_to(REPO_ROOT))


def _resolve_observe_record_path(state: dict, result: dict | None = None) -> str | None:
    """Return the first on-disk observe artifact suitable for result ingestion."""
    from seed_pipeline import REPO_ROOT

    for rel_path in _observe_record_candidates(state, result=result):
        if (REPO_ROOT / rel_path).exists():
            return rel_path
    return None


def _lazy_repo_root() -> Path:
    from seed_pipeline import REPO_ROOT
    return REPO_ROOT
