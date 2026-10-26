"""
[PURPOSE]
- Teleology: Apply typed `synth_seed_delta_v0` receipts onto an existing `synth_seed.json` without rerunning full synth regeneration.
- Mechanism: Load the target synth seed, apply a bounded patch vocabulary onto a working copy, normalize and validate the result, then rewrite the file when the merged payload passes validation.
- Non-goal: Full synth reseeding, phase scaffolding, or observe-plan execution.

[INTERFACE]
- Exports: apply_synth_seed_delta.
- Reads: `repo_root/<target_phase_dir>/synth_seed.json` plus the supplied delta payload.
- Writes: apply_synth_seed_delta() rewrites the target `synth_seed.json` after successful normalize/validate checks.

[FLOW]
- Validate the delta schema_version, target_phase_dir, and patch list.
- Load the target synth seed and apply supported patch ops onto a working copy.
- Normalize and validate the merged synth payload.
- Write the normalized synth seed back to disk and return `(ok, messages)`.
- When-needed: Open when typed synth-seed delta receipts need to be merged into a live phase packet instead of regenerating or hand-editing `synth_seed.json`.
- Escalates-to: system/lib/pipeline/stage_process.py::_try_apply_synth_seed_delta_receipts; system/lib/phase_scaffold.py; system/lib/observe_apply_contracts.py
- Navigation-group: kernel_lib

[DEPENDENCIES]
- json: Read and rewrite the synth seed payload.
- pathlib.Path: Resolve the target phase packet location.
- system.lib.codex_paths.canonicalize_write_path: Normalize target phase directories.
- system.lib.observe_apply_contracts: Normalize and validate the merged synth payload.

[CONSTRAINTS]
- Guarantee: Writes only after normalize_synth_payload() succeeds and validate_synth_seed_payload() returns no errors.
- Orders: Patches apply sequentially, so later patch ops see earlier mutations.
- Atomicity: The target synth seed is rewritten in one write_text() call after successful validation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from system.lib.codex_paths import canonicalize_write_path
from system.lib.observe_apply_contracts import (
    normalize_current_wave,
    normalize_orientation,
    normalize_relevant_files,
    normalize_synth_payload,
    normalize_synthesis_memory,
    normalize_work_items,
    validate_synth_seed_payload,
)


def _string(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_str_list(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in items:
        t = _string(x)
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def apply_synth_seed_delta(
    repo_root: Path,
    delta: Mapping[str, Any],
    *,
    allow_pending_validation: bool = True,
) -> tuple[bool, list[str]]:
    """
    [ACTION]
    - Teleology: Merge one typed synth-seed delta receipt into the target phase packet's synth seed.
    - Mechanism: Validate the delta envelope, load the target synth seed, apply supported patch ops onto a working copy, normalize and validate the merged payload, then rewrite the file on success.
    - Guarantee: Returns `(True, messages)` only after the merged synth payload has been normalized, validated, and written back to disk.
    - Fails: None — invalid deltas or unreadable payloads return `(False, messages)` instead of raising.
    - When-needed: Open when pipeline or review logic needs the exact delta-merge contract for `synth_seed_delta_v0` receipts.
    - Escalates-to: system/lib/pipeline/stage_process.py::_try_apply_synth_seed_delta_receipts; system/lib/phase_scaffold.py
    """
    msgs: list[str] = []
    ver = _string(delta.get("schema_version"))
    if ver != "synth_seed_delta_v0":
        return False, [f"unsupported schema_version {ver!r}, expected synth_seed_delta_v0"]
    phase_dir = canonicalize_write_path(_string(delta.get("target_phase_dir")))
    if not phase_dir:
        return False, ["target_phase_dir is required"]
    path = repo_root / phase_dir / "synth_seed.json"
    if not path.is_file():
        return False, [f"missing synth_seed.json at {path.relative_to(repo_root)}"]

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return False, [f"failed to read synth_seed: {exc}"]

    patches = delta.get("patches")
    if not isinstance(patches, list) or not patches:
        return False, ["patches must be a non-empty list"]

    base = dict(raw) if isinstance(raw, Mapping) else {}
    for patch in patches:
        if not isinstance(patch, Mapping):
            msgs.append("skip: non-object patch")
            continue
        ptype = _string(patch.get("op") or patch.get("type"))
        if ptype == "append_investigation_threads":
            items = patch.get("items")
            if not isinstance(items, list):
                continue
            base.setdefault("investigation_threads", [])
            if not isinstance(base["investigation_threads"], list):
                base["investigation_threads"] = []
            for it in items:
                if isinstance(it, Mapping):
                    base["investigation_threads"].append(dict(it))
        elif ptype == "append_constraints":
            items = patch.get("items")
            if isinstance(items, list):
                cur = [_string(x) for x in base.get("constraints", []) if isinstance(base.get("constraints"), list) for x in (base.get("constraints") or [])]
                if not isinstance(base.get("constraints"), list):
                    base["constraints"] = []
                merged = _dedupe_str_list([*cur, *[_string(x) for x in items]])
                base["constraints"] = merged
        elif ptype == "append_relevant_files":
            items = patch.get("items")
            if isinstance(items, list):
                existing = base.get("relevant_files")
                combined = [*existing, *items] if isinstance(existing, list) else list(items)
                base["relevant_files"] = normalize_relevant_files(combined)
        elif ptype == "append_work_items":
            items = patch.get("items")
            if isinstance(items, list):
                existing = base.get("work_items")
                combined = [*existing, *items] if isinstance(existing, list) else list(items)
                base["work_items"] = normalize_work_items(
                    combined,
                    current_wave=base.get("current_wave") if isinstance(base.get("current_wave"), Mapping) else {},
                    working_set=base.get("working_set") if isinstance(base.get("working_set"), list) else [],
                    execution_mode=_string(base.get("execution_mode")),
                )
        elif ptype == "update_work_item_status":
            work_item_id = _string(patch.get("id"))
            new_status = _string(patch.get("status"))
            spawned_wave_id = _string(patch.get("spawned_wave_id"))
            notes = _string(patch.get("notes"))
            if work_item_id:
                base.setdefault("work_items", [])
                if not isinstance(base["work_items"], list):
                    base["work_items"] = []
                for item in base.get("work_items", []):
                    if isinstance(item, dict) and _string(item.get("work_item_id") or item.get("id")) == work_item_id:
                        if new_status:
                            item["status"] = new_status
                        if spawned_wave_id:
                            item.setdefault("spawned_wave_ids", [])
                            if isinstance(item["spawned_wave_ids"], list):
                                item["spawned_wave_ids"] = _dedupe_str_list([*item["spawned_wave_ids"], spawned_wave_id])
                        if notes:
                            item["notes"] = notes
                        break
        elif ptype == "set_meta_controller_phase":
            val = _string(patch.get("value"))
            if val:
                base.setdefault("meta", {})
                if isinstance(base["meta"], Mapping):
                    meta = dict(base["meta"])
                    meta["controller_phase"] = val
                    base["meta"] = meta
        elif ptype == "set_meta_current_cycle":
            try:
                cyc = int(patch.get("value"))
            except (TypeError, ValueError):
                continue
            base.setdefault("meta", {})
            if isinstance(base["meta"], Mapping):
                meta = dict(base["meta"])
                meta["current_cycle"] = cyc
                base["meta"] = meta
        elif ptype == "append_intent_non_goals":
            items = patch.get("items")
            if isinstance(items, list):
                base.setdefault("intent", {})
                if isinstance(base["intent"], Mapping):
                    intent = dict(base["intent"])
                    cur = [_string(x) for x in intent.get("non_goals", []) if isinstance(intent.get("non_goals"), list) for x in intent.get("non_goals", [])]
                    intent["non_goals"] = _dedupe_str_list([*cur, *[_string(x) for x in items]])
                    base["intent"] = intent
        elif ptype == "append_intent_success_criteria":
            items = patch.get("items")
            if isinstance(items, list):
                base.setdefault("intent", {})
                if isinstance(base["intent"], Mapping):
                    intent = dict(base["intent"])
                    cur = [
                        _string(x)
                        for x in intent.get("success_criteria", [])
                        if isinstance(intent.get("success_criteria"), list)
                        for x in intent.get("success_criteria", [])
                    ]
                    intent["success_criteria"] = _dedupe_str_list([*cur, *[_string(x) for x in items]])
                    base["intent"] = intent
        elif ptype == "set_continuity_mode":
            val = _string(patch.get("value"))
            if val in ("gate_bounded", "open_conductor"):
                base["continuity_mode"] = val
        elif ptype == "append_outstanding_questions":
            items = patch.get("items")
            if isinstance(items, list):
                base.setdefault("outstanding_questions", [])
                if not isinstance(base["outstanding_questions"], list):
                    base["outstanding_questions"] = []
                for it in items:
                    if isinstance(it, Mapping):
                        base["outstanding_questions"].append(dict(it))
        elif ptype == "update_outstanding_question_status":
            qid = _string(patch.get("id"))
            new_status = _string(patch.get("status"))
            if qid and new_status:
                for q in base.get("outstanding_questions", []):
                    if isinstance(q, dict) and _string(q.get("id")) == qid:
                        q["status"] = new_status
                        break
        elif ptype == "append_active_hypotheses":
            items = patch.get("items")
            if isinstance(items, list):
                base.setdefault("active_hypotheses", [])
                if not isinstance(base["active_hypotheses"], list):
                    base["active_hypotheses"] = []
                for it in items:
                    if isinstance(it, Mapping):
                        base["active_hypotheses"].append(dict(it))
        elif ptype == "update_hypothesis_status":
            hid = _string(patch.get("id"))
            new_status = _string(patch.get("status"))
            if hid:
                for h in base.get("active_hypotheses", []):
                    if isinstance(h, dict) and _string(h.get("id")) == hid:
                        if new_status:
                            h["status"] = new_status
                        ef = patch.get("evidence_for")
                        if isinstance(ef, list):
                            h.setdefault("evidence_for", [])
                            h["evidence_for"].extend([_string(x) for x in ef if _string(x)])
                        ea = patch.get("evidence_against")
                        if isinstance(ea, list):
                            h.setdefault("evidence_against", [])
                            h["evidence_against"].extend([_string(x) for x in ea if _string(x)])
                        break
        elif ptype == "set_progress_state":
            val = patch.get("value")
            if isinstance(val, Mapping):
                base["progress_state"] = dict(val)
        elif ptype == "set_next_step_posture":
            val = _string(patch.get("value"))
            if val:
                base["next_step_posture"] = val
        elif ptype == "set_orientation":
            val = patch.get("value")
            if isinstance(val, Mapping):
                base["orientation"] = normalize_orientation(
                    dict(val),
                    intent=base.get("intent") if isinstance(base.get("intent"), Mapping) else {},
                    current_wave=base.get("current_wave") if isinstance(base.get("current_wave"), Mapping) else {},
                )
        elif ptype == "set_work_items":
            items = patch.get("value")
            if isinstance(items, list):
                base["work_items"] = normalize_work_items(
                    items,
                    current_wave=base.get("current_wave") if isinstance(base.get("current_wave"), Mapping) else {},
                    working_set=base.get("working_set") if isinstance(base.get("working_set"), list) else [],
                    execution_mode=_string(base.get("execution_mode")),
                )
        elif ptype == "set_synthesis_memory":
            val = patch.get("value")
            if isinstance(val, Mapping):
                base["synthesis_memory"] = normalize_synthesis_memory(val)
        elif ptype == "set_current_wave":
            val = patch.get("value")
            if isinstance(val, Mapping):
                base["current_wave"] = normalize_current_wave(
                    dict(val),
                    phase_scaffold={},
                    intent=base.get("intent") if isinstance(base.get("intent"), Mapping) else {},
                    working_set=base.get("working_set") if isinstance(base.get("working_set"), list) else [],
                    execution_mode=_string(base.get("execution_mode")),
                    fallback_groups=[],
                )
                base["execution_mode"] = _string(base.get("current_wave", {}).get("mode")) or _string(base.get("execution_mode"))
        elif ptype == "patch_current_wave":
            val = patch.get("value")
            if isinstance(val, Mapping):
                merged_wave = dict(base.get("current_wave") or {})
                merged_wave.update(dict(val))
                base["current_wave"] = normalize_current_wave(
                    merged_wave,
                    phase_scaffold={},
                    intent=base.get("intent") if isinstance(base.get("intent"), Mapping) else {},
                    working_set=base.get("working_set") if isinstance(base.get("working_set"), list) else [],
                    execution_mode=_string(base.get("execution_mode")),
                    fallback_groups=[],
                )
                base["execution_mode"] = _string(base.get("current_wave", {}).get("mode")) or _string(base.get("execution_mode"))
        elif ptype == "append_confirmed_facts":
            items = patch.get("items")
            if isinstance(items, list):
                memory = dict(base.get("synthesis_memory") or {})
                existing = memory.get("confirmed_facts")
                combined = [*existing, *items] if isinstance(existing, list) else list(items)
                memory["confirmed_facts"] = normalize_synthesis_memory({"confirmed_facts": combined}).get("confirmed_facts", [])
                base["synthesis_memory"] = memory
        elif ptype == "append_locked_decisions":
            items = patch.get("items")
            if isinstance(items, list):
                memory = dict(base.get("synthesis_memory") or {})
                existing = memory.get("locked_decisions")
                combined = [*existing, *items] if isinstance(existing, list) else list(items)
                memory["locked_decisions"] = normalize_synthesis_memory({"locked_decisions": combined}).get("locked_decisions", [])
                base["synthesis_memory"] = memory
        elif ptype == "append_active_risks":
            items = patch.get("items")
            if isinstance(items, list):
                memory = dict(base.get("synthesis_memory") or {})
                existing = memory.get("active_risks")
                combined = [*existing, *items] if isinstance(existing, list) else list(items)
                memory["active_risks"] = normalize_synthesis_memory({"active_risks": combined}).get("active_risks", [])
                base["synthesis_memory"] = memory
        elif ptype == "update_risk_status":
            risk_id = _string(patch.get("id"))
            new_status = _string(patch.get("status"))
            mitigation = _string(patch.get("mitigation"))
            if risk_id:
                memory = dict(base.get("synthesis_memory") or {})
                risks = memory.get("active_risks")
                if not isinstance(risks, list):
                    risks = []
                for item in risks:
                    if isinstance(item, dict) and _string(item.get("risk_id") or item.get("id")) == risk_id:
                        if new_status:
                            item["status"] = new_status
                        if mitigation:
                            item["mitigation"] = mitigation
                        break
                memory["active_risks"] = risks
                base["synthesis_memory"] = memory
        else:
            msgs.append(f"skip: unknown patch type {ptype!r}")

    normalized = normalize_synth_payload(base)
    if normalized is None:
        return False, ["normalize_synth_payload failed after patch"]
    errs = validate_synth_seed_payload(normalized, allow_pending=allow_pending_validation)
    if errs:
        return False, [f"validation: {e}" for e in errs]

    path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    msgs.append(f"wrote {path.relative_to(repo_root)}")
    return True, msgs
