"""
[PURPOSE]
- Teleology: Emit the canonical `synth_seed.json` that turns the selected shard working set into the active phase's whiteboard authority.
- Mechanism: Merge selected shards with any existing synth payload, normalize the intent/relevant-file envelope, write the synth artifact, and advance controller state into scope authoring.

[INTERFACE]
- Exports: emit_synth_seed.
- Reads: Selected shards, existing `synth_seed.json` when present, and controller/runtime metadata from the active phase directory.
- Writes: The phase's canonical `synth_seed.json` plus controller state updates and follow-on controller artifacts.

[FLOW]
- Load existing synth payload -> derive normalized intent, relevant files, and investigation threads from selected shards -> write `synth_seed.json` -> advance controller state into the post-emit scope stage.

[DEPENDENCIES]
- Couples: `system.lib.pipeline.stage_extract._active_phase` anchors this stage to the active phase/runtime packet.
- Couples: `system.lib.observe_apply_contracts` defines synth normalization and synth-field derivation semantics.
- Couples: `system.lib.seed_pipeline_controller` persists the controller-state changes that make the new synth seed authoritative.

[CONSTRAINTS]
- Guarantee: This stage rewrites the phase's canonical `synth_seed.json` and refreshes controller artifacts so downstream scope/compile stages read the new synth authority.
- Non-goal: This module does not select shards or compile bridge plans; it only emits the synth seed artifact from an already selected shard set.
- When-needed: Open when the bounded loop needs the exact stage that turns selected shards into the canonical `synth_seed.json`.
- Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline/stage_compile.py; system/lib/phase_harbor.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

from pathlib import Path

from system.lib.pipeline.stage_extract import _active_phase


# ---------------------------------------------------------------------------
# Stage 3: Emit synth_seed.json
# ---------------------------------------------------------------------------
def emit_synth_seed(state: dict, selected_shards: list[dict]) -> Path:
    """
    [ACTION]
    - Teleology: Write the active phase's canonical synth seed from the selected shard working set.
    - Mechanism: Normalize the existing synth payload, derive intent/relevant-files/investigation-threads from the selected shards, write the new synth artifact, and advance controller state into scope.
    - Reads: Existing `synth_seed.json`, `selected_shards`, and synth normalization helpers from `system.lib.observe_apply_contracts`.
    - Writes: `synth_seed.json`, controller-state fields such as `synth_seed_path`, and controller artifacts via `write_controller_artifacts()`.
    - Guarantee: Returns the synth-seed path and leaves the pipeline state staged at `synth_seed_emitted` with relevant-file metadata refreshed.
    - Fails: Propagates filesystem and controller-artifact write failures.
    - When-needed: Open when a caller needs the concrete stage-3 synth-seed emission logic rather than the higher-level pipeline wrapper.
    - Escalates-to: system/lib/pipeline/stage_compile.py::compile_observe_plan; system/lib/phase_harbor.py; seed_pipeline.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _utc_now, _load_json, _write_json_atomic, _log, _dedupe_strings
    from system.lib.observe_apply_contracts import (
        normalize_synth_payload,
        synth_goal_text,
        synth_relevant_file_paths,
        synth_success_criteria_list,
        synth_success_criteria_text,
    )
    from system.lib.seed_pipeline_controller import (
        ensure_controller_state,
        write_controller_artifacts,
    )

    ensure_controller_state(state, repo_root=REPO_ROOT)
    phase_dir = REPO_ROOT / state["phase_dir"]
    synth_path = phase_dir / "synth_seed.json"
    existing = _load_json(synth_path) or {}
    selected_shards = [dict(item) for item in selected_shards if isinstance(item, dict)]

    normalized_existing = normalize_synth_payload(existing) or {}
    relevant_files = _dedupe_strings(
        synth_relevant_file_paths(normalized_existing)
        or [path for shard in selected_shards for path in (shard.get("relevant_files") or [])]
    )
    investigation_threads = []
    for shard in selected_shards:
        statement = str(shard.get("clarified_statement") or shard.get("question") or "").strip()
        if not statement:
            continue
        investigation_threads.append(
            {
                "id": str(shard.get("id") or "").strip() or f"THREAD_{len(investigation_threads) + 1:03d}",
                "statement": statement,
                "concept_group": str(shard.get("concept_group") or "general").strip() or "general",
                "relevant_files": _dedupe_strings(shard.get("relevant_files") or []),
            }
        )

    intent = synth_goal_text(normalized_existing)
    if not intent:
        if investigation_threads:
            intent = investigation_threads[0]["statement"]
        else:
            intent = "Advance the raw seed intent into a reviewable apply plan."

    synth = {
        "version": "synth_seed_v3",
        "authoring_status": "authored",
        "generated_at": str(existing.get("generated_at") or _utc_now()),
        "intent": {
            "goal": intent,
            "why_now": str(normalized_existing.get("intent", {}).get("why_now") or "Evolve the currently selected shard frontier into a tighter synth authority.").strip(),
            "raw_seed_anchors": list(normalized_existing.get("intent", {}).get("raw_seed_anchors") or []),
            "success_criteria": synth_success_criteria_list(normalized_existing) or [
                "Produce a validated apply plan or a concrete blocked reason grounded in the codebase."
            ],
            "non_goals": list(normalized_existing.get("intent", {}).get("non_goals") or []),
        },
        "constraints": _dedupe_strings(
            existing.get("constraints")
            or [
                "Bridge reasoning remains JSON-first after synth_seed creation.",
                "kernel.py --apply is the only mutation engine.",
                "Apply remains human or IDE gated before execution.",
            ]
        ),
        "relevant_files": [
            {
                "path": path,
                "role": "active_scope_candidate",
                "why": "Selected shard evidence names this file as part of the active seed frontier.",
            }
            for path in relevant_files
        ],
        "investigation_threads": investigation_threads,
        "apply_boundary": existing.get("apply_boundary")
        if isinstance(existing.get("apply_boundary"), dict)
        else {
            "review_required": True,
            "apply_via": "kernel.py --apply",
            "mutator": "kernel",
        },
        "source_shards": selected_shards,
        "meta": {
            "phase_id": state.get("controller_version"),
            "phase_number": state.get("controller_version"),
            "phase_title": Path(state["phase_dir"]).name,
            "phase_dir": state["phase_dir"],
            "family_dir": state.get("family_dir"),
            "updated_at": _utc_now(),
            "created_at": str(normalized_existing.get("meta", {}).get("created_at") or _utc_now()),
            "controller_version": state.get("controller_version"),
            "controller_phase": state.get("controller_phase"),
            "current_cycle": int(state.get("cycle") or 0),
            "source_authority_kind": "family_raw_seed",
            "source_authority_path": state.get("raw_seed_path"),
        },
    }

    _write_json_atomic(synth_path, synth)

    state["synth_seed_path"] = str(synth_path.relative_to(REPO_ROOT))
    state["phase"] = "scope"
    state["controller_phase"] = "scope"
    state["phase_depth"] = 0
    state["active_scope_files"] = []
    state["known_relevant_files"] = relevant_files
    state["scope_revision"] = 0
    state["stage"] = "synth_seed_emitted"
    write_controller_artifacts(state, repo_root=REPO_ROOT)
    _log(state, "emit_synth_seed", f"Wrote canonical synth_seed with {len(selected_shards)} source shards")
    return synth_path
