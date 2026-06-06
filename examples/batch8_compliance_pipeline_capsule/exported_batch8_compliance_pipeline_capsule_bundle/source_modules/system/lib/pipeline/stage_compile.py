"""
[PURPOSE]
- Teleology: Compile the phase-native `observe_plan.json` that turns the selected shard frontier and prior-cycle evidence into the next bounded observe pass.
- Mechanism: Reuse stage-extract and stage-select helpers to gather carry-forward context, synth payloads, follow-up files, and router/probe group scaffolds before writing a cycle-local observe plan.

[INTERFACE]
- Exports: compile_observe_plan.
- Reads: Selected shards, synth/controller state, prior cycle summaries, and prior observe artifacts under the active phase directory.
- Writes: The current cycle's `observe_plan.json`, cycle-local support artifacts, and controller/event updates through shared pipeline helpers.

[FLOW]
- Gather prior-cycle findings and artifact context -> sanitize synthesis payloads -> bound target specs and follow-up files -> assemble probe/router groups -> write the compiled observe plan into the active cycle directory.

[DEPENDENCIES]
- Couples: `system.lib.pipeline.stage_extract` supplies cycle-path helpers, synthesis-payload normalization, event logging, and active-phase state that shape the compiled plan.
- Couples: `system.lib.pipeline.stage_select` supplies prior-cycle findings and synthesis payload recovery used to seed the next observe pass.
- Couples: `system.lib.observe_runtime` and `system.lib.observe_apply_contracts` define the runtime and standards bundle carried into the compiled plan.

[CONSTRAINTS]
- Guarantee: The stage compiles a cycle-local observe plan that is bounded by target-count and target-byte ceilings before later dispatch stages read it.
- Non-goal: This module does not dispatch bridge work or process observe receipts; it only compiles the next observe plan artifact.
- When-needed: Open when a pipeline loop needs the exact stage that turns selected shards plus prior-cycle evidence into the next `observe_plan.json`.
- Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline/stage_execute.py; system/lib/phase_harbor.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Mapping

from system.lib.pipeline.stage_extract import (
    _active_phase,
    _cycle_dir_path,
    _cycle_dir_rel,
    _cycle_path_candidates,
    _cycle_timeline_rel,
    _has_synthesis_payload,
    _legacy_dump_dir_rel,
    _load_cycle_summary_by_cycle,
    _normalize_compare_text,
    _normalize_synthesis_payload,
    _phase_id_from_state,
    _record_cycle_event,
    _snapshot_cycle_synth_seed,
    _texts_probably_same,
    NEW_SHARD_EXISTING_SIMILARITY,
    NEW_SHARD_PROMPT_SIMILARITY,
    DEGRADED_GROUP_STATES,
    MAX_PROBE_TARGET_FILES,
    MAX_PROBE_TARGET_BYTES,
)
from system.lib.pipeline.stage_select import (
    _build_previous_cycle_findings,
    _load_synthesis_payload_for_cycle,
)


# ---------------------------------------------------------------------------
# Stage 4: Compile observe_plan.json
# ---------------------------------------------------------------------------

def _probe_questions_for_plan_path(plan_path: Path | None) -> list[str]:
    from seed_pipeline import _load_json

    if plan_path is None or not plan_path.exists():
        return []
    plan = _load_json(plan_path)
    if not isinstance(plan, dict):
        return []
    questions: list[str] = []
    for group in plan.get("groups", []):
        if not isinstance(group, dict):
            continue
        role = str(group.get("role") or "probe").strip().lower() or "probe"
        if role not in {"probe", "advisory"}:
            continue
        question = str(group.get("question") or "").strip()
        if question:
            questions.append(question)
    return questions


def _load_previous_cycle_findings(state: dict) -> str:
    """Load a compact previous-cycle summary for carry-forward context."""
    if state["cycle"] < 1:
        return ""

    for lookback in range(1, min(4, state["cycle"] + 1)):
        prev_cycle = state["cycle"] - lookback
        if prev_cycle < 0:
            break
        summary = _load_cycle_summary_by_cycle(state, prev_cycle)
        payload, _ = _load_synthesis_payload_for_cycle(state, prev_cycle)
        probe_questions: list[str] = []
        for candidate in _cycle_path_candidates(state, prev_cycle, "observe_plan.json"):
            probe_questions = _probe_questions_for_plan_path(candidate)
            if probe_questions or candidate.exists():
                break
        payload, _ = _sanitize_synthesis_payload(state, payload, probe_questions=probe_questions)
        findings = _build_previous_cycle_findings(summary, payload, prev_cycle)
        if findings:
            return findings

    return ""


def _prior_cycle_context_bundle(state: dict, *, max_lookback: int = 4) -> dict[str, Any]:
    from seed_pipeline import _dedupe_strings, REPO_ROOT

    if state["cycle"] < 1:
        return {"files": [], "lookback": None, "source_cycle": None}

    for lookback in range(1, min(max_lookback, state["cycle"]) + 1):
        prev_cycle = state["cycle"] - lookback
        if prev_cycle < 0:
            break
        context_files: list[str] = []
        for filename in ("carry_forward_context.json", "cycle_assimilation.json", "_cycle_summary.json", "routing_decision.json"):
            for candidate in _cycle_path_candidates(state, prev_cycle, filename):
                if candidate.exists():
                    context_files.append(str(candidate.relative_to(REPO_ROOT)))
                    break
        if context_files:
            return {
                "files": _dedupe_strings(context_files),
                "lookback": lookback,
                "source_cycle": prev_cycle,
            }

    return {"files": [], "lookback": None, "source_cycle": None}


def _prior_cycle_context_files(state: dict, *, max_lookback: int = 4) -> list[str]:
    bundle = _prior_cycle_context_bundle(state, max_lookback=max_lookback)
    files = bundle.get("files")
    return list(files) if isinstance(files, list) else []


def _load_cycle_payload_by_name(state: dict, cycle: int, filename: str) -> dict[str, Any]:
    from seed_pipeline import _load_json

    for candidate in _cycle_path_candidates(state, cycle, filename):
        if candidate.exists():
            payload = _load_json(candidate)
            if isinstance(payload, dict):
                return payload
    return {}


def _flatten_text_entries(values: Any) -> list[str]:
    from seed_pipeline import _dedupe_strings

    if not isinstance(values, list):
        return []
    output: list[str] = []
    for item in values:
        if isinstance(item, Mapping):
            text = str(item.get("text") or item.get("summary") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            output.append(text)
    return _dedupe_strings(output)


def _extract_known_file_mentions(texts: list[str], known_files: list[str]) -> list[str]:
    from seed_pipeline import _dedupe_strings

    normalized_texts = [str(text or "").strip().lower() for text in texts if str(text or "").strip()]
    normalized_known = _dedupe_strings([str(path or "").strip() for path in known_files if str(path or "").strip()])
    if not normalized_texts or not normalized_known:
        return []

    basename_index: dict[str, list[str]] = {}
    for path in normalized_known:
        basename_index.setdefault(Path(path).name.lower(), []).append(path)

    matches: list[str] = []
    for text in normalized_texts:
        for path in sorted(normalized_known, key=len, reverse=True):
            if path.lower() in text:
                matches.append(path)
        for basename, paths in basename_index.items():
            if len(paths) != 1:
                continue
            if re.search(rf"(?<![A-Za-z0-9_/.-]){re.escape(basename)}(?![A-Za-z0-9_/.-])", text):
                matches.append(paths[0])
    return _dedupe_strings(matches)


def _priority_followup_files(
    *,
    known_files: list[str],
    active_scope_files: list[str],
    missing_evidence: Any = None,
    known_universe_files: Any = None,
    extra_texts: list[str] | None = None,
) -> list[str]:
    from seed_pipeline import _dedupe_strings

    known = _dedupe_strings([str(path).strip() for path in known_files if str(path).strip()])
    active_scope = set(_dedupe_strings([str(path).strip() for path in active_scope_files if str(path).strip()]))
    known_universe = [path for path in _coerce_text_list(known_universe_files) if path in known]
    mentioned = _extract_known_file_mentions(
        [
            *_coerce_text_list(missing_evidence),
            *(extra_texts or []),
        ],
        known,
    )
    prioritized = _dedupe_strings([*known_universe, *mentioned])
    outside_active = [path for path in prioritized if path not in active_scope]
    inside_active = [path for path in prioritized if path in active_scope]
    return _dedupe_strings([*outside_active, *inside_active])


def _prior_cycle_followup_bundle(
    state: dict,
    *,
    scope_files: list[str],
    known_scope_files: list[str],
    max_lookback: int = 3,
) -> dict[str, Any]:
    from seed_pipeline import _dedupe_strings

    if state["cycle"] < 1:
        return {
            "priority_files": [],
            "recently_examined_files": [],
            "source_cycles": [],
        }

    known_universe = _dedupe_strings([*known_scope_files, *scope_files])
    priority_files: list[str] = []
    recently_examined_files: list[str] = []
    source_cycles: list[int] = []

    for lookback in range(1, min(max_lookback, state["cycle"]) + 1):
        prev_cycle = state["cycle"] - lookback
        if prev_cycle < 0:
            break

        carry_forward = _load_cycle_payload_by_name(state, prev_cycle, "carry_forward_context.json")
        if carry_forward:
            source_cycles.append(prev_cycle)
            recently_examined_files.extend(_coerce_text_list(carry_forward.get("files_examined")))
            priority_files.extend(
                _priority_followup_files(
                    known_files=known_universe,
                    active_scope_files=scope_files,
                    missing_evidence=carry_forward.get("missing_evidence"),
                    known_universe_files=(
                        carry_forward.get("priority_followup_files")
                        or carry_forward.get("known_universe_files_outside_active_scope")
                    ),
                    extra_texts=_coerce_text_list(carry_forward.get("carry_forward_notes")),
                )
            )

        cycle_assimilation = _load_cycle_payload_by_name(state, prev_cycle, "cycle_assimilation.json")
        if cycle_assimilation:
            aggregate = (
                dict(cycle_assimilation.get("aggregate") or {})
                if isinstance(cycle_assimilation.get("aggregate"), Mapping)
                else {}
            )
            source_cycles.append(prev_cycle)
            recently_examined_files.extend(_coerce_text_list(aggregate.get("files_examined")))
            priority_files.extend(
                _priority_followup_files(
                    known_files=known_universe,
                    active_scope_files=scope_files,
                    missing_evidence=aggregate.get("missing_evidence"),
                    known_universe_files=(
                        aggregate.get("priority_followup_files")
                        or aggregate.get("known_universe_files_outside_active_scope")
                    ),
                    extra_texts=[
                        *_flatten_text_entries(aggregate.get("facts")),
                        *_flatten_text_entries(aggregate.get("problems")),
                        *_flatten_text_entries(aggregate.get("open_questions")),
                    ],
                )
            )

    return {
        "priority_files": [path for path in _dedupe_strings(priority_files) if path in known_universe],
        "recently_examined_files": [
            path for path in _dedupe_strings(recently_examined_files) if path in known_universe
        ],
        "source_cycles": sorted(set(source_cycles)),
    }


def _load_previous_layer_findings(state: dict) -> str:
    from system.lib.seed_pipeline_controller import load_task_dag
    from seed_pipeline import REPO_ROOT

    task_dag = load_task_dag(state, repo_root=REPO_ROOT)
    if not isinstance(task_dag, dict):
        return ""
    current_layer_id = str(task_dag.get("current_layer_id") or "").strip()
    layers = task_dag.get("layers")
    if not isinstance(layers, list):
        return ""
    prior_layers = [
        dict(layer)
        for layer in layers
        if isinstance(layer, dict)
        and str(layer.get("layer_id") or "").strip() != current_layer_id
        and str(layer.get("status") or "").strip() == "completed"
        and isinstance(layer.get("router_result"), dict)
    ]
    if not prior_layers:
        return ""
    latest = prior_layers[-1]
    payload, _ = _sanitize_synthesis_payload(state, dict(latest.get("router_result") or {}), probe_questions=[])
    summary = {
        "cycle": latest.get("compiled_from_cycle"),
        "priority_action": payload.get("priority_action", {}),
        "ordered_sequence": payload.get("ordered_sequence", []),
        "shard_status_updates": payload.get("shard_status_updates", []),
        "new_shards": payload.get("new_shards", []),
    }
    findings = _build_previous_cycle_findings(summary, payload, int(latest.get("compiled_from_cycle") or 0))
    decision = str((payload.get("routing_decision") or {}).get("decision") or "").strip()
    if decision:
        findings += f"\n\nPrevious routed decision: {decision}."
    return findings.strip()


def _prior_cycle_probe_artifacts_bundle(state: dict) -> dict[str, Any]:
    """Return structured probe artifacts from the most recent successful cycle."""
    from seed_pipeline import REPO_ROOT

    if state["cycle"] < 1:
        return {"files": [], "lookback": None, "source_cycle": None, "source_kind": None}

    for lookback in range(1, min(4, state["cycle"] + 1)):
        prev_cycle = state["cycle"] - lookback
        if prev_cycle < 0:
            break
        for prev_dump in (_cycle_dir_path(state, prev_cycle), REPO_ROOT / _legacy_dump_dir_rel(state, prev_cycle)):
            if not prev_dump.exists():
                continue
            receipt_files = [
                str(path.relative_to(REPO_ROOT))
                for path in sorted(prev_dump.glob("*probe_*_response.receipt.json"))
            ]
            if receipt_files:
                return {
                    "files": receipt_files,
                    "lookback": lookback,
                    "source_cycle": prev_cycle,
                    "source_kind": "typed_probe_receipts",
                }

            markdown_files = []
            for path in sorted(prev_dump.glob("*probe_*_response.md")):
                try:
                    header = path.read_text(encoding="utf-8")[:500]
                except Exception:
                    continue
                if "status: `success`" in header or "status: `degraded_structural`" in header:
                    markdown_files.append(str(path.relative_to(REPO_ROOT)))
            if markdown_files:
                return {
                    "files": markdown_files,
                    "lookback": lookback,
                    "source_cycle": prev_cycle,
                    "source_kind": "probe_response_markdown",
                }

    return {"files": [], "lookback": None, "source_cycle": None, "source_kind": None}


def _prior_cycle_probe_artifacts(state: dict) -> list[str]:
    bundle = _prior_cycle_probe_artifacts_bundle(state)
    files = bundle.get("files")
    return list(files) if isinstance(files, list) else []


OUTLINE_THRESHOLD_BYTES = 150_000  # files above this get outline scope instead of full
OUTLINE_TARGET_CHAR_CAP = 60_000


def _target_effective_size(size: int, scope: str) -> int:
    if str(scope or "").strip() == "outline":
        return min(size // 20, OUTLINE_TARGET_CHAR_CAP)
    return size


def _bounded_target_specs(file_paths: list[str]) -> list[dict[str, str]]:
    from seed_pipeline import REPO_ROOT

    targets: list[dict[str, str]] = []
    total_bytes = 0
    for file_path in file_paths:
        rel = str(file_path or "").strip()
        if not rel:
            continue
        abs_path = REPO_ROOT / rel
        if not abs_path.exists() or not abs_path.is_file():
            continue
        size = max(1, int(abs_path.stat().st_size))
        if targets and (
            len(targets) >= MAX_PROBE_TARGET_FILES
            or total_bytes + size > MAX_PROBE_TARGET_BYTES
        ):
            continue
        scope = "outline" if size > OUTLINE_THRESHOLD_BYTES else "full"
        targets.append({"file": rel, "scope": scope})
        effective_size = _target_effective_size(size, scope)
        total_bytes += effective_size
        if len(targets) >= MAX_PROBE_TARGET_FILES:
            break
    return targets


def _probe_questions_for_current_plan(state: dict) -> list[str]:
    from seed_pipeline import REPO_ROOT

    plan_path = str(state.get("observe_plan_path") or "").strip()
    if not plan_path:
        return []
    return _probe_questions_for_plan_path(REPO_ROOT / plan_path)


def _existing_shard_statements(state: dict) -> list[str]:
    from seed_pipeline import REPO_ROOT, _load_json

    shards_path = str(state.get("shards_path") or "").strip()
    if not shards_path:
        return []
    payload = _load_json(REPO_ROOT / shards_path)
    if not isinstance(payload, dict):
        return []
    statements: list[str] = []
    for shard in payload.get("shards", []):
        if not isinstance(shard, dict):
            continue
        statement = str(shard.get("clarified_statement") or shard.get("question") or "").strip()
        if statement:
            statements.append(statement)
    return statements


def _sanitize_synthesis_payload(
    state: dict,
    payload: dict[str, Any],
    *,
    probe_questions: list[str] | None = None,
) -> tuple[dict[str, Any], dict[str, int]]:
    sanitized = _normalize_synthesis_payload(payload)
    existing_texts = [
        _normalize_compare_text(item)
        for item in _existing_shard_statements(state)
    ]
    existing_texts = [item for item in existing_texts if item]
    probe_question_texts = probe_questions if probe_questions is not None else _probe_questions_for_current_plan(state)
    probe_questions = [
        _normalize_compare_text(item)
        for item in probe_question_texts
    ]
    probe_questions = [item for item in probe_questions if item]

    filtered_new_shards: list[dict[str, Any]] = []
    seen_questions: list[str] = []
    dropped = 0

    for item in sanitized.get("new_shards", []):
        if not isinstance(item, dict):
            continue
        question = str(item.get("question") or item.get("clarified_statement") or "").strip()
        normalized_question = _normalize_compare_text(question)
        if len(normalized_question) < 12:
            dropped += 1
            continue
        if any(
            _texts_probably_same(normalized_question, existing, threshold=NEW_SHARD_EXISTING_SIMILARITY)
            for existing in existing_texts
        ):
            dropped += 1
            continue
        if any(
            _texts_probably_same(normalized_question, prompt, threshold=NEW_SHARD_PROMPT_SIMILARITY)
            for prompt in probe_questions
        ):
            dropped += 1
            continue
        if any(
            _texts_probably_same(normalized_question, prior, threshold=NEW_SHARD_EXISTING_SIMILARITY)
            for prior in seen_questions
        ):
            dropped += 1
            continue
        filtered_new_shards.append(item)
        seen_questions.append(normalized_question)

    sanitized["new_shards"] = filtered_new_shards
    return sanitized, {"dropped_new_shards": dropped}


def _coerce_text_list(values: Any) -> list[str]:
    from seed_pipeline import _dedupe_strings

    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for item in values:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
        else:
            text = str(item or "").strip()
        if text:
            normalized.append(text)
    return _dedupe_strings(normalized)


def compile_observe_plan(state: dict, selected_shards: list[dict]) -> Path:
    """
    [ACTION]
    - Teleology: Materialize the next cycle's observe plan from the currently selected shard frontier and the controller's active phase state.
    - Mechanism: Build an observe brief, recover synth and prior-cycle context, assemble bounded probe and router groups, write the plan under the current cycle directory, and update controller-visible state.
    - Reads: `selected_shards`, controller state, prior-cycle artifacts, `system.lib.observe_runtime.observe_runtime_policy()`, and observe/apply standards helpers.
    - Writes: The current cycle's `observe_plan.json`, group-response directory scaffolding, cycle event records, and controller state fields such as `observe_plan_path`.
    - Guarantee: Returns the path to the compiled cycle-local observe plan and leaves the pipeline state pointed at that plan for later execute/process stages.
    - Fails: Propagates filesystem and helper errors from plan compilation dependencies.
    - When-needed: Open when a caller needs the authoritative stage-4 observe-plan compilation flow instead of the broader `seed_pipeline` wrapper.
    - Escalates-to: system/lib/pipeline/stage_execute.py::execute_observe; system/lib/pipeline/stage_select.py; system/lib/phase_harbor.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _utc_now, _write_json_atomic, _log, _dedupe_strings
    from system.lib.observe_apply_contracts import (
        render_observe_apply_standards_prompt,
        resolve_observe_apply_standards_bundle,
        synth_goal_text,
        synth_success_criteria_text,
    )
    from system.lib.observe_runtime import observe_runtime_policy
    from system.lib.seed_pipeline_controller import (
        ensure_controller_state,
        known_relevant_file_paths,
        observe_brief,
        write_controller_artifacts,
    )

    ensure_controller_state(state, repo_root=REPO_ROOT)
    write_controller_artifacts(state, repo_root=REPO_ROOT)
    brief = observe_brief(state, selected_shards, repo_root=REPO_ROOT)
    synth = brief.get("synth_seed") if isinstance(brief.get("synth_seed"), dict) else {}
    phase = str(brief.get("phase") or state.get("phase") or "scope").strip() or "scope"
    cycle_dir = _cycle_dir_path(state)
    cycle_dir.mkdir(parents=True, exist_ok=True)
    (cycle_dir / "group_responses").mkdir(parents=True, exist_ok=True)
    synth_snapshot_rel = _snapshot_cycle_synth_seed(state, cycle_dir)
    plan_path = cycle_dir / "observe_plan.json"
    dump_dir = _cycle_dir_rel(state)
    prev_findings = _load_previous_cycle_findings(state)
    scope_files = _dedupe_strings(
        state.get("active_scope_files") or known_relevant_file_paths(state, synth)
    )
    known_scope_files = _dedupe_strings(known_relevant_file_paths(state, synth) or scope_files)
    threads = [
        dict(item)
        for item in (synth.get("investigation_threads") or [])
        if isinstance(item, dict)
    ]
    prior_cycle_context = _prior_cycle_context_bundle(state)
    prior_cycle_context_files = list(prior_cycle_context.get("files") or [])
    prior_probe_bundle = _prior_cycle_probe_artifacts_bundle(state)
    prior_probe_artifacts = list(prior_probe_bundle.get("files") or [])
    prior_followup = _prior_cycle_followup_bundle(
        state,
        scope_files=scope_files,
        known_scope_files=known_scope_files,
    )
    base_standard_source_artifacts = _dedupe_strings(
        list(brief.get("observe_apply_standard_source_artifacts") or [])
    )
    base_standards_bundle = (
        dict(brief.get("observe_apply_standards") or {})
        if isinstance(brief.get("observe_apply_standards"), dict)
        else {}
    )

    def _carry_forward_block() -> str:
        if not prev_findings:
            return ""
        return (
            "\n\nPrevious cycle carry-forward is attached via prior-cycle context files. "
            "Use that bounded memory instead of rediscovering already-settled seams."
        )

    def _file_chunks(files: list[str], *, max_chunks: int | None = None) -> list[list[str]]:
        """Bin-pack files into probe groups by size."""
        deduped = _dedupe_strings(files)
        if not deduped:
            return [[]]
        effective_max_chunks = max(
            1,
            int(
                max_chunks
                or observe_runtime_policy(REPO_ROOT).get("max_workers_ceiling")
                or 15
            ),
        )

        sized: list[tuple[str, int]] = []
        for path in deduped:
            abs_path = REPO_ROOT / path
            size = int(abs_path.stat().st_size) if abs_path.exists() and abs_path.is_file() else 0
            sized.append((path, size))

        LARGE_THRESHOLD = 200_000
        large = [(p, s) for p, s in sized if s > LARGE_THRESHOLD]
        small = [(p, s) for p, s in sized if s <= LARGE_THRESHOLD]

        groups: list[list[str]] = []

        for path, _size in large:
            if len(groups) >= effective_max_chunks:
                break
            groups.append([path])

        for path, size in small:
            if len(groups) >= effective_max_chunks:
                groups[-1].append(path)
                continue
            placed = False
            for group in groups:
                group_bytes = sum(
                    (REPO_ROOT / p).stat().st_size
                    for p in group
                    if (REPO_ROOT / p).exists()
                )
                if group_bytes + size <= MAX_PROBE_TARGET_BYTES and len(group) < MAX_PROBE_TARGET_FILES:
                    group.append(path)
                    placed = True
                    break
            if not placed:
                groups.append([path])

        return groups[:effective_max_chunks] if groups else [[]]

    def _group_standards_bundle(
        *,
        target_specs: list[dict[str, Any]],
        extra_artifact_kinds: list[str] | None = None,
    ) -> dict[str, Any]:
        target_files = [
            str(item.get("file") or "").strip()
            for item in target_specs
            if str(item.get("file") or "").strip()
        ]
        return resolve_observe_apply_standards_bundle(
            artifact_paths=[*base_standard_source_artifacts, *target_files],
            repo_root=REPO_ROOT,
            extra_artifact_kinds=["observe_plan", *(extra_artifact_kinds or [])],
        )

    def _merge_group_context_files(existing: list[str], bundle: dict[str, Any]) -> list[str]:
        return _dedupe_strings(
            [
                *existing,
                *[
                    item
                    for item in (bundle.get("context_files") or [])
                    if str(item).strip() and (REPO_ROOT / str(item).strip()).exists()
                ],
            ]
        )

    observe_groups: list[dict[str, Any]] = []

    if phase == "scope":
        relevant_hint = ", ".join(scope_files[:12]) if scope_files else "none yet"
        scope_question = "\n\n".join(
            [
                f"Intent: {brief.get('intent') or synth_goal_text(synth) or 'Advance the active seed surface.'}",
                f"Success criteria: {brief.get('success_criteria') or synth_success_criteria_text(synth) or ''}",
                "You are running the scope discovery cycle.",
                "Read the synth seed, raw-seed digest, and system view. Identify the smallest concrete sub-universe of files needed for the next probe cycle.",
                "Treat `relevant_files` as the next probe working set, not a destructive rewrite of the broader phase universe. Omitted files stay known unless directly contradicted.",
                "Prefer precise repo-relative file paths. Drop speculative files from the next probe slice. If no expansion is needed, keep the list tight.",
                f"Current relevant-file hint: {relevant_hint}",
                render_observe_apply_standards_prompt(base_standards_bundle),
                _carry_forward_block(),
            ]
        ).strip()
        scope_bundle = _group_standards_bundle(target_specs=[], extra_artifact_kinds=["phase_scaffold", "synth_seed"])
        observe_groups.append(
            {
                "label": "scope",
                "role": "probe",
                "notes": "Discover or refine the active file universe.",
                "question": scope_question,
                "acceptance": "Receipt returns a bounded relevant file set and concise rationale.",
                "depends_on": [],
                "targets": [],
                "context_files": _merge_group_context_files(
                    [
                        *list(brief.get("session_context_files") or []),
                        *prior_cycle_context_files,
                    ],
                    scope_bundle,
                ),
                "standards": scope_bundle,
                "response_schema": brief["scope_receipt_schema"],
                "json_only": True,
            }
        )
    elif phase == "plan":
        plan_targets = _bounded_target_specs(scope_files)
        prior_cycle_context_note = ""
        previous_cycle = state["cycle"] - 1
        if isinstance(prior_cycle_context.get("lookback"), int) and prior_cycle_context["lookback"] > 1:
            source_cycle = prior_cycle_context.get("source_cycle")
            prior_cycle_context_note = (
                "Prior-cycle routing context is attached from "
                f"cycle {source_cycle} because cycle {previous_cycle} did not expose "
                "`_cycle_summary.json` or `routing_decision.json`."
            )
        prior_probe_artifacts_note = ""
        if isinstance(prior_probe_bundle.get("lookback"), int) and prior_probe_bundle["lookback"] > 1:
            source_cycle = prior_probe_bundle.get("source_cycle")
            source_kind = str(prior_probe_bundle.get("source_kind") or "probe artifacts").replace("_", " ")
            prior_probe_artifacts_note = (
                "Prior probe evidence is attached from "
                f"cycle {source_cycle} ({source_kind}) because cycle {previous_cycle} did not expose usable probe receipts."
            )
        plan_question = "\n\n".join(
            [
                f"Intent: {brief.get('intent') or synth_goal_text(synth) or 'Advance the active seed surface.'}",
                "You are in the planning phase.",
                "Using the attached in-scope files plus the prior probe-cycle routing evidence and probe receipts, produce a kernel-compatible apply plan if the evidence is sufficient.",
                "Executable means `apply_plan` must contain either a non-empty `operations` list or a non-empty `unified_diff`/`diff`/`patch` string.",
                "Do not return a descriptive edit inventory, implementation sketch, or evidence-only plan inside `apply_plan`.",
                "If the plan is not ready, return either `continue_probe` with a concrete reason or `blocked` with the missing precondition.",
                "Verification must be explicit and mechanical where possible.",
                *( [prior_cycle_context_note] if prior_cycle_context_note else [] ),
                *( [prior_probe_artifacts_note] if prior_probe_artifacts_note else [] ),
                render_observe_apply_standards_prompt(
                    _group_standards_bundle(
                        target_specs=plan_targets,
                        extra_artifact_kinds=["cycle_summary", "routing_decision", "apply_plan"],
                    )
                ),
                _carry_forward_block(),
            ]
        ).strip()
        validator_bundle = _group_standards_bundle(
            target_specs=plan_targets,
            extra_artifact_kinds=["cycle_summary", "routing_decision", "apply_plan"],
        )
        observe_groups.append(
            {
                "label": "validator",
                "role": "evaluation",
                "notes": "Produce the final typed plan receipt.",
                "question": plan_question,
                "acceptance": "Receipt returns either an apply-ready plan or a concrete reason to continue probing/block.",
                "depends_on": [],
                "targets": plan_targets,
                "context_files": _dedupe_strings(
                    [
                        *_merge_group_context_files(list(brief.get("session_context_files") or []), validator_bundle),
                        *prior_cycle_context_files,
                        *prior_probe_artifacts,
                    ]
                ),
                "standards": validator_bundle,
                "response_schema": brief["plan_receipt_schema"],
                "json_only": True,
            }
        )
    else:
        probe_labels: list[str] = []
        base_probe_files = scope_files or _dedupe_strings(
            [path for item in selected_shards for path in (item.get("relevant_files") or [])]
        )
        priority_probe_files = _dedupe_strings(list(prior_followup.get("priority_files") or []))
        recently_examined = set(prior_followup.get("recently_examined_files") or [])
        probe_files = _dedupe_strings(
            [
                *priority_probe_files,
                *[
                    path
                    for path in base_probe_files
                    if path not in priority_probe_files and path not in recently_examined
                ],
                *[
                    path
                    for path in known_scope_files
                    if path not in base_probe_files and path not in priority_probe_files and path not in recently_examined
                ],
                *[
                    path
                    for path in base_probe_files
                    if path not in priority_probe_files and path in recently_examined
                ],
                *[
                    path
                    for path in known_scope_files
                    if path not in base_probe_files and path not in priority_probe_files and path in recently_examined
                ],
            ]
        )
        priority_focus_text = ", ".join(priority_probe_files[:10]) if priority_probe_files else ""
        for index, file_chunk in enumerate(_file_chunks(probe_files), start=1):
            probe_labels.append(f"probe_{index}")
            target_specs = _bounded_target_specs(file_chunk)
            chunk_threads = [
                item for item in threads
                if not item.get("relevant_files")
                or set(_dedupe_strings(item.get("relevant_files") or [])).intersection(file_chunk)
            ] or threads
            investigation_lines = [
                str(item.get("statement") or "").strip()
                for item in chunk_threads[:6]
                if str(item.get("statement") or "").strip()
            ]
            probe_bundle = _group_standards_bundle(
                target_specs=target_specs,
                extra_artifact_kinds=["cycle_summary", "routing_decision"],
            )
            short_intent = (brief.get('intent') or synth_goal_text(synth) or 'Advance the active seed surface.')
            if len(short_intent) > 300:
                short_intent = short_intent[:300].rsplit(" ", 1)[0] + "..."
            thread_ids = [str(item.get("id") or "").strip() for item in chunk_threads[:6] if item.get("id")]
            thread_ref = f"Focus on investigation threads: {', '.join(thread_ids)}." if thread_ids else ""
            probe_question = "\n\n".join(
                [
                    f"Intent (see synth_seed.json for full detail): {short_intent}",
                    "You are running a bounded probe cycle over the attached files.",
                    "Use only live code evidence from the attached files. If required evidence is outside the attached set, name it under missing_evidence.",
                    "IMPORTANT: If a probe group failed due to bridge transport errors in a prior cycle, that is NOT evidence of missing scope — those files may already be in scope but were not delivered to the bridge.",
                    "If a file is already in the attached prior-cycle context or the broader known universe, widen the next probe slice instead of escalating the phase universe.",
                    *(
                        [
                            "Priority follow-up files already inside the known universe: "
                            f"{priority_focus_text}. Cover these before claiming scope expansion."
                        ]
                        if priority_focus_text
                        else []
                    ),
                    thread_ref,
                    ("Investigation threads:\n- " + "\n- ".join(investigation_lines)) if investigation_lines else "Investigate the attached files and map the current state, missing evidence, and useful shard updates.",
                    f"Applicable standards: see authority index in context files.",
                    _carry_forward_block(),
                ]
            ).strip()
            observe_groups.append(
                {
                    "label": f"probe_{index}",
                    "role": "probe",
                    "notes": "Bounded code probe over the current active scope.",
                    "question": probe_question,
                    "acceptance": "Receipt returns findings, files examined, missing evidence, and shard updates.",
                    "depends_on": [],
                    "targets": target_specs,
                    "context_files": _merge_group_context_files(
                        [
                            *[path for path in list(brief.get("session_context_files") or []) if path.endswith("synth_seed.json")],
                            *prior_cycle_context_files,
                            *prior_probe_artifacts,
                        ],
                        probe_bundle,
                    ),
                    "standards": probe_bundle,
                    "response_schema": brief["probe_receipt_schema"],
                    "json_only": True,
                }
            )

        router_bundle = _group_standards_bundle(target_specs=[], extra_artifact_kinds=["cycle_summary", "routing_decision"])
        short_intent_router = (brief.get('intent') or synth_goal_text(synth) or 'Advance the active seed surface.')
        if len(short_intent_router) > 300:
            short_intent_router = short_intent_router[:300].rsplit(" ", 1)[0] + "..."
        scope_file_list = ", ".join(scope_files[:20]) if scope_files else "none"
        known_scope_list = ", ".join(known_scope_files[:20]) if known_scope_files else "none"
        router_question = "\n\n".join(
            [
                f"Intent (see synth_seed.json for full detail): {short_intent_router}",
                "You are the routing join node for this probe cycle.",
                "Read the upstream typed probe receipts and decide the next phase.",
                "Allowed decisions: `continue_probe`, `expand_scope`, `advance_to_plan`, `blocked`.",
                "",
                "CRITICAL ROUTING RULES:",
                "1. `expand_scope` means files genuinely NOT in the current scope need to be added. Do NOT use expand_scope just because a probe group failed to run (bridge transport error) — that is a delivery failure, not a scope gap.",
                "2. If upstream probes are empty/degraded due to bridge errors but the scope file list already covers the investigation threads, prefer `advance_to_plan` or `continue_probe` over `expand_scope`.",
                "3. Before recommending `expand_scope`, check the scope file list below. If the files you would name are already there, the issue is probe delivery, not scope.",
                "4. Files already in the broader known universe but absent from the current probe slice are a working-set widening, not a phase-universe escalation.",
                f"5. Current scope files ({len(scope_files)}): {scope_file_list}",
                f"6. Known relevant files ({len(known_scope_files)}): {known_scope_list}",
                *(
                    [
                        "7. This cycle already queues known-universe follow-up files: "
                        f"{priority_focus_text}."
                    ]
                    if priority_focus_text
                    else []
                ),
                "",
                "Keep reasoning short and decisive.",
                f"Applicable standards: see authority index in context files.",
                _carry_forward_block(),
            ]
        ).strip()
        observe_groups.append(
            {
                "label": "router",
                "role": "synthesis",
                "notes": "Typed routing decision for the next phase transition.",
                "question": router_question,
                "acceptance": "Receipt returns a decisive next-phase routing result.",
                "depends_on": probe_labels,
                "targets": [],
                "context_files": _merge_group_context_files(
                    [
                        *list(brief.get("session_context_files") or []),
                        *prior_cycle_context_files,
                        *prior_probe_artifacts,
                    ],
                    router_bundle,
                ),
                "standards": router_bundle,
                "response_schema": brief["router_receipt_schema"],
                "json_only": True,
            }
        )

    wait_notes = str(brief.get("wait_notes") or "").strip()
    if prev_findings:
        wait_notes += " This cycle builds directly on the previous cycle summary."

    plan = {
        "schema_version": "2.0",
        "drafted_at": _utc_now(),
        "phase": phase,
        "goal_question": str(brief.get("intent") or synth_goal_text(synth) or "").strip(),
        "success_criteria": str(brief.get("success_criteria") or synth_success_criteria_text(synth) or "").strip(),
        "problem_text": "",
        "dump_dir": dump_dir,
        "wait_notes": wait_notes,
        "context_merge_mode": "group_only",
        "context_files": list(brief.get("session_context_files") or []),
        "standards": base_standards_bundle,
        "result_note_path": str(Path(dump_dir) / "observe_result.md"),
        "groups": observe_groups,
        "campaign_id": state["pipeline_id"],
        "round_index": max(1, state["cycle"] + 1),
        "task_dag_path": state.get("task_dag_path"),
        "current_layer_id": state.get("current_layer_id"),
        "current_layer_kind": state.get("current_layer_kind"),
        "synth_seed_snapshot_path": synth_snapshot_rel,
        "cycle_timeline_path": _cycle_timeline_rel(state),
    }

    _write_json_atomic(plan_path, plan)

    state["current_cycle_dir"] = str(cycle_dir.relative_to(REPO_ROOT))
    state["current_cycle_synth_snapshot_path"] = synth_snapshot_rel
    state["current_cycle_timeline_path"] = _cycle_timeline_rel(state)
    state["observe_plan_path"] = str(plan_path.relative_to(REPO_ROOT))
    state["stage"] = "observe_plan_compiled"
    _record_cycle_event(
        state,
        "observe_plan_compiled",
        observe_plan_path=state["observe_plan_path"],
        dump_dir=plan.get("dump_dir"),
        group_count=len(observe_groups),
        synth_seed_snapshot_path=synth_snapshot_rel,
    )
    _log(state, "compile_observe_plan", f"Compiled {phase} observe plan with {len(observe_groups)} groups in {state['current_cycle_dir']}")
    return plan_path
