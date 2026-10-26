"""
[PURPOSE]
- Teleology: Centralize observe-apply artifact contracts so synth-first phase scaffolds, synth seeds, standards bundles, and close-promotion payloads share one normalization, rendering, and validation authority.
- Mechanism: Resolve applicable standards from the authority index, normalize synth/seed payload shapes, generate scaffold and synth artifacts, render markdown projections, and validate authored payloads against the contract.
- Non-goal: Execute observe cycles or mutate files directly; this module only defines and shapes the contract payloads.

[INTERFACE]
- Exports: `load_observe_apply_authority_index`, `resolve_observe_apply_standards_bundle`, `render_observe_apply_standards_prompt`, `normalize_synth_payload`, `build_phase_scaffold_payload`, `build_subphase_meta_ledger_payload`, `build_synth_seed_payload`, `render_synth_seed_markdown`, `validate_synth_seed_payload`, `build_subphase_close_promotion_entry`, `canonical_json_text`, plus supporting normalization helpers.
- Reads: Observe-apply standards JSON, authority-index mappings, scaffold/synth payloads, and optional caller-supplied artifact paths.
- Writes: None directly; callers persist the returned payloads or rendered markdown.
- Schema: Shapes include standards bundles, `phase_scaffold`, `synth_seed_v5`, `subphase_meta_ledger`, and subphase-close promotion entries.

[FLOW]
- Load authority index -> resolve standards bundle for artifact paths -> normalize synth payloads and traceability fields -> build scaffold, synth, and ledger payloads -> render markdown projections -> validate authored synth payloads -> build close-promotion entries.
- When-needed: Open when synth-first phase artifacts, standards bundles, or subphase-close promotion payloads need their contract authority instead of scattered caller logic.
- Escalates-to: system/lib/observe_plan_enrichment.py; tools/meta/apply/run_observe_plan.py; system/lib/kernel/commands/navigate.py
- Couples: `system/lib/observe_plan_enrichment.py`, `system/lib/seed_pipeline_controller.py`, `system/lib/phase_scaffold.py`, and kernel navigation commands depend on these shapes staying aligned with the observe-apply standards directory.
- Navigation-group: kernel_lib

[DEPENDENCIES]
- system.lib.codex_paths: Canonicalize repo-relative artifact paths embedded in payloads.
- system.lib.markdown_routing: Render markdown projections for synth-seed notes.
- pathlib.Path + json: Load authority and standards JSON surfaces from disk.
- fnmatch + re: Match artifact paths to authority-index path globs and validate concept-id patterns.

[CONSTRAINTS]
- Guarantee: Public builders return deterministic payloads for stable inputs, and validation accumulates contract errors instead of mutating caller data.
- Orders: Standards selection preserves first-seen artifact-path order after canonicalization, and synth normalization preserves the synth-first contract while migrating legacy payloads forward.
- Fails: Public loaders degrade to `{}` on unreadable JSON authority files; validation returns error lists instead of raising for contract violations.
- Non-goal: This module does not own lifecycle CLI entrypoints or write artifacts to disk.
"""
from __future__ import annotations

import fnmatch
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from system.lib import strict_json
from system.lib.controller_heartbeat import (
    build_controller_heartbeat,
    controller_heartbeat_ref,
    default_mission_blackboard_path,
)
from system.lib.codex_paths import canonicalize_write_path
from system.lib.markdown_routing import render_markdown_document

OBSERVE_APPLY_STANDARDS_DIR = "codex/standards/observe_apply"
OBSERVE_APPLY_AUTHORITY_INDEX_PATH = f"{OBSERVE_APPLY_STANDARDS_DIR}/observe_apply_authority_index.json"
OBSERVE_APPLY_STANDARD_PATHS = {
    "raw_seed": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_raw_seed.json",
    "agent_seed": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_agent_seed.json",
    "raw_seed_index": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_raw_seed_index.json",
    "raw_seed_navigation_graph": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_raw_seed_navigation_graph.json",
    "family_charter": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_family_charter.json",
    "synth_seed": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_synth_seed.json",
    "phase_scaffold": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_phase_scaffold.json",
    "phase_closeout": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_phase_closeout.json",
    "phase_family": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_phase_family.json",
    "phase_memory": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_phase_memory.json",
    "autonomous_seed": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_autonomous_seed.json",
    "meta_ledger": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_meta_ledger.json",
    "reference_ledger": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_reference_ledger.json",
    "observe_plan": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_observe_plan.json",
    "routing_decision": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_routing_decision.json",
    "cycle_summary": f"{OBSERVE_APPLY_STANDARDS_DIR}/std_cycle_summary.json",
    "apply_plan": "codex/standards/std_apply.json",
}
SYNTH_SEED_VERSION = "synth_seed_v5"
PHASE_SCAFFOLD_VERSION = "phase_scaffold_v4"
PHASE_CLOSEOUT_VERSION = "phase_closeout_v1"
SUBPHASE_META_LEDGER_VERSION = "subphase_meta_ledger_v2"
FAMILY_CHARTER_VERSION = "family_charter_v1"
WAVE_PROTOCOL_VERSION = "wave_protocol_v1"
PENDING_SYNTH_AUTHORING = "pending_initial_synth_authoring"
SYNCED_SYNTH_AUTHORING = "synth_seed_synced"
SUBPHASE_META_LEDGER_KIND = "subphase_meta_ledger"
FAMILY_META_LEDGER_KIND = "meta_ledger"
FAMILY_CHARTER_KIND = "family_charter"
EXECUTION_MODES = frozenset(
    {
        "direct_local",
        "hybrid",
        "bridge_graph",
        "continuous_conductor",
        "subagent_cohort",
        "mission_launch",
    }
)
BRIDGE_COMPILABLE_EXECUTION_MODES = frozenset({"bridge_graph", "continuous_conductor"})
CONTINUITY_MODES = frozenset({"gate_bounded", "open_conductor"})
PHASE_STEP_STAGE_KINDS = frozenset({"problem_space", "solution_space", "plan_space"})
DEFAULT_SYNTH_CONSTRAINTS = [
    "Bridge reasoning remains JSON-first after synth_seed creation.",
    "kernel.py --apply is the only mutation engine.",
    "Apply remains human or IDE gated before execution.",
]
DEFAULT_APPLY_BOUNDARY = {
    "review_required": True,
    "apply_via": "kernel.py --apply",
    "mutator": "kernel",
}
DEFAULT_SYNTH_ORIENTATION = {
    "architectural_posture": "Treat the synth seed as the bounded architect's view for this subphase, not as a static note dump.",
    "evidence_posture": "Ground every wave in the synth, targeted raw-seed refs, and the smallest file set that can answer the bounded question.",
    "pivot_rule": "If new evidence changes the file map, execution mode, or work-item ordering, update the synth through assimilation instead of drifting in chat.",
}
_CONCEPT_ID_PATTERN = re.compile(r"^con_[a-z0-9_]+$", re.IGNORECASE)
_CONCEPT_REF_ROLES = frozenset({"primary", "supporting", "inspired_by"})


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _utc_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _string(value: Any) -> str:
    return str(value or "").strip()


def _dedupe_strings(values: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for value in values:
        token = _string(value)
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _read_json_mapping(path: Path) -> dict[str, Any]:
    try:
        payload = strict_json.read_json_strict(path)
    except Exception:
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def load_observe_apply_authority_index(*, repo_root: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Load the observe-apply authority index so callers can resolve which standards govern a given artifact set.
    - Mechanism: Resolve `OBSERVE_APPLY_AUTHORITY_INDEX_PATH` under `repo_root` and return the parsed mapping or `{}` when missing or unreadable.
    - Reads: `repo_root / OBSERVE_APPLY_AUTHORITY_INDEX_PATH`.
    - Writes: None.
    - Guarantee: Returns a mapping-shaped authority index payload or `{}`.
    - Fails: None.
    - When-needed: Open when a planning or scaffold surface needs the governing standards index before matching artifact paths.
    - Escalates-to: system/lib/observe_apply_contracts.py::resolve_observe_apply_standards_bundle; system/lib/observe_plan_enrichment.py
    """
    path = (repo_root / OBSERVE_APPLY_AUTHORITY_INDEX_PATH).resolve()
    if not path.exists():
        return {}
    return _read_json_mapping(path)


def _observe_apply_standard_card(
    rel_path: str,
    *,
    repo_root: Path,
    artifact_kind: str,
    standard_kind: str,
    matched_paths: list[str] | None = None,
) -> dict[str, Any]:
    payload = _read_json_mapping((repo_root / rel_path).resolve())
    card: dict[str, Any] = {
        "kind": standard_kind,
        "artifact_kind": artifact_kind,
        "id": Path(rel_path).stem,
        "path": rel_path,
        "exists": (repo_root / rel_path).exists(),
    }
    if matched_paths:
        card["matched_paths"] = list(matched_paths)
    standard_id = _string(payload.get("id"))
    if standard_id:
        card["id"] = standard_id
    description = _string(payload.get("description") or payload.get("summary"))
    if description:
        card["description"] = description
    schema = payload.get("schema")
    if isinstance(schema, Mapping):
        card["top_level_fields"] = [str(key) for key in schema.keys()]
    return card


def resolve_observe_apply_standards_bundle(
    *,
    artifact_paths: list[str] | tuple[str, ...],
    repo_root: Path,
    extra_artifact_kinds: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Resolve the applicable observe-apply standards bundle for a set of artifact paths so callers inject the right contracts instead of relying on naming folklore.
    - Mechanism: Load the authority index, canonicalize source artifact paths, match them against artifact-kind globs, build JSON/markdown standard cards, and return the governing context-file bundle.
    - Reads: `artifact_paths`, optional `extra_artifact_kinds`, `repo_root`, and the authority-index plus matched standards files under `codex/standards/observe_apply`.
    - Writes: None.
    - Guarantee: Returns a bundle with matched artifact kinds, applicable standard cards, and a deduped `context_files` list suitable for prompt/context injection.
    - Fails: None for missing authority/standard files; missing surfaces simply yield a narrower or empty bundle.
    - Orders: Canonicalized source paths and context files preserve first-seen order after deduplication.
    - When-needed: Open when a plan, pipeline stage, or synth scaffold needs the exact standards bundle that governs a set of observe-apply artifacts.
    - Escalates-to: system/lib/observe_plan_enrichment.py; system/lib/seed_pipeline_controller.py; tools/meta/apply/run_observe_plan.py
    - Navigation-group: kernel_lib
    """
    authority_index = load_observe_apply_authority_index(repo_root=repo_root)
    artifacts = authority_index.get("artifacts") if isinstance(authority_index.get("artifacts"), Mapping) else {}
    normalized_paths = _dedupe_strings(
        [
            canonicalize_write_path(_string(path)) or _string(path)
            for path in artifact_paths
            if _string(path)
        ]
    )
    requested_kinds = {
        _string(kind)
        for kind in (extra_artifact_kinds or [])
        if _string(kind)
    }
    applicable: list[dict[str, Any]] = []
    context_files: list[str] = []
    matched_artifact_kinds: list[str] = []
    matched_paths_by_kind: dict[str, list[str]] = {}

    for artifact_kind, spec in artifacts.items():
        if not isinstance(spec, Mapping):
            continue
        path_globs = [
            _string(item)
            for item in (spec.get("path_globs") or [])
            if _string(item)
        ]
        matched_paths = [
            path for path in normalized_paths
            if any(fnmatch.fnmatch(path, pattern) for pattern in path_globs)
        ]
        if artifact_kind not in requested_kinds and not matched_paths:
            continue
        matched_artifact_kinds.append(str(artifact_kind))
        matched_paths_by_kind[str(artifact_kind)] = matched_paths

        json_standard = _string(spec.get("json_standard"))
        markdown_standard = _string(spec.get("markdown_standard"))
        for rel_path, standard_kind in (
            (json_standard, "json_standard"),
            (markdown_standard, "markdown_standard"),
        ):
            if not rel_path:
                continue
            applicable.append(
                _observe_apply_standard_card(
                    rel_path,
                    repo_root=repo_root,
                    artifact_kind=str(artifact_kind),
                    standard_kind=standard_kind,
                    matched_paths=matched_paths,
                )
            )
            if (repo_root / rel_path).exists():
                context_files.append(rel_path)

    context_files = _dedupe_strings(
        ([OBSERVE_APPLY_AUTHORITY_INDEX_PATH] if (repo_root / OBSERVE_APPLY_AUTHORITY_INDEX_PATH).exists() and applicable else [])
        + context_files
    )
    return {
        "standards_root": OBSERVE_APPLY_STANDARDS_DIR,
        "authority_index": OBSERVE_APPLY_AUTHORITY_INDEX_PATH,
        "source_artifacts": normalized_paths,
        "matched_artifact_kinds": matched_artifact_kinds,
        "matched_paths_by_artifact_kind": matched_paths_by_kind,
        "applicable_standards": applicable,
        "context_files": context_files,
    }


def render_observe_apply_standards_prompt(bundle: Mapping[str, Any] | None) -> str:
    """[ACTION]
    - Teleology: Render a human-readable prompt fragment that describes the applicable observe-apply standards bundle for context injection.
    - Guarantee: Returns a newline-joined string listing the authority index and matched standard cards, or an empty string when no applicable standards exist.
    - Fails: None.
    """
    if not isinstance(bundle, Mapping):
        return ""
    applicable = [
        dict(item)
        for item in (bundle.get("applicable_standards") or [])
        if isinstance(item, Mapping)
    ]
    if not applicable:
        return ""
    lines = [
        "Observe-apply standards are auto-selected for this cycle from the authority index. Treat them as the governing artifact contracts instead of relying on legacy naming or prompt folklore.",
    ]
    authority_index = _string(bundle.get("authority_index"))
    if authority_index:
        lines.append(f"Authority index: `{authority_index}`")
    lines.append("Applicable standards:")
    for card in applicable:
        artifact_kind = _string(card.get("artifact_kind")) or _string(card.get("id")) or "standard"
        standard_kind = _string(card.get("kind")) or "standard"
        rel_path = _string(card.get("path"))
        matched_paths = [
            _string(item)
            for item in (card.get("matched_paths") or [])
            if _string(item)
        ]
        if matched_paths:
            lines.append(f"- {artifact_kind} {standard_kind}: `{rel_path}` (matched `{matched_paths[0]}`)")
        else:
            lines.append(f"- {artifact_kind} {standard_kind}: `{rel_path}`")
    return "\n".join(lines)


def source_authority_kind_for_phase(*, parent_phase_id: str | None = None) -> str:
    """[ACTION]
    - Teleology: Derive the source-authority kind token for a phase based on whether a parent phase exists.
    - Guarantee: Returns `"parent_synth_seed"` when `parent_phase_id` is non-empty, else `"family_raw_seed"`.
    - Fails: None.
    """
    return "parent_synth_seed" if _string(parent_phase_id) else "family_raw_seed"


def source_authority_path_for_phase(
    *,
    family_dir: str,
    parent_phase_dir: str | None = None,
    parent_phase_id: str | None = None,
) -> str:
    """[ACTION]
    - Teleology: Derive the canonical source-authority path for a phase, pointing at the parent synth seed when a parent phase exists or the family raw seed otherwise.
    - Guarantee: Returns a canonicalized path string for the appropriate authority artifact, or an empty string when canonicalization yields nothing.
    - Fails: None.
    """
    if _string(parent_phase_id) and _string(parent_phase_dir):
        return canonicalize_write_path(f"{_string(parent_phase_dir)}/synth_seed.json") or ""
    return canonicalize_write_path(f"{_string(family_dir)}/raw_seed.md") or ""


def synth_goal_placeholder(*, authority_kind: str, authority_path: str) -> str:
    """[ACTION]
    - Teleology: Generate the pending-authoring placeholder text for a synth seed's goal field before long-form content is authored.
    - Guarantee: Returns a non-empty instructional string naming the source authority and describing what the goal section must eventually contain.
    - Fails: None.
    """
    authority_label = (
        f"parent synth authority `{authority_path}`"
        if authority_kind == "parent_synth_seed"
        else f"family raw seed `{authority_path}`"
    )
    return (
        "PENDING: author a long-form goal extracted from the active source authority before the first cycle runs. "
        f"This synth seed is still a scaffold stub and must be grounded in {authority_label}. "
        "Describe the real subphase objective, the intended architectural unlock, the bounded seam being addressed, "
        "and the specific system drift or leverage point that makes this subphase worth running now."
    )


def synth_why_now_placeholder(*, authority_kind: str, authority_path: str) -> str:
    """[ACTION]
    - Teleology: Generate the pending-authoring placeholder text for a synth seed's why_now field before long-form rationale is authored.
    - Guarantee: Returns a non-empty instructional string naming the source authority and describing what the why_now section must eventually contain.
    - Fails: None.
    """
    authority_label = "parent synth" if authority_kind == "parent_synth_seed" else "family raw seed"
    return (
        "PENDING: explain why this subphase is the right next move right now, what it unlocks downstream, "
        "and what would continue to drift if it were skipped. "
        f"Ground this in the current repo state and the selected {authority_label} authority at `{authority_path}`."
    )


def _normalize_path_card_extras(item: Mapping[str, Any]) -> dict[str, Any]:
    extras: dict[str, Any] = {}
    priority = _string(item.get("priority"))
    if priority:
        extras["priority"] = priority
    confidence = _string(item.get("confidence"))
    if confidence:
        extras["confidence"] = confidence
    notes = _string(item.get("notes") or item.get("note"))
    if notes:
        extras["notes"] = notes
    entry_points = _dedupe_strings([_string(entry) for entry in (item.get("entry_points") or [])]) if isinstance(item.get("entry_points"), list) else []
    if entry_points:
        extras["entry_points"] = entry_points
    symbol_focus = _dedupe_strings([_string(entry) for entry in (item.get("symbol_focus") or [])]) if isinstance(item.get("symbol_focus"), list) else []
    if symbol_focus:
        extras["symbol_focus"] = symbol_focus
    related_paths = _dedupe_strings(
        [
            canonicalize_write_path(_string(entry)) or _string(entry)
            for entry in (item.get("related_paths") or [])
            if _string(entry)
        ]
    ) if isinstance(item.get("related_paths"), list) else []
    if related_paths:
        extras["related_paths"] = related_paths
    return extras


def normalize_relevant_files(value: Any) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize a heterogeneous relevant-files list into the canonical structured form expected by synth-seed payloads.
    - Guarantee: Returns a deduped list of dicts with `path`, `role`, and `why` fields, with paths canonicalized and empty or duplicate paths dropped.
    - Fails: None.
    """
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(value, list):
        value = [value] if value is not None else []
    for item in value:
        if isinstance(item, Mapping):
            path = canonicalize_write_path(_string(item.get("path"))) or ""
            if not path or path in seen:
                continue
            seen.add(path)
            row: dict[str, Any] = {
                "path": path,
                "role": _string(item.get("role")) or "candidate_context",
                "why": _string(item.get("why")) or "Imported into the active seed surface context.",
            }
            row.update(_normalize_path_card_extras(item))
            output.append(row)
            continue
        path = canonicalize_write_path(_string(item)) or ""
        if not path or path in seen:
            continue
        seen.add(path)
        output.append(
            {
                "path": path,
                "role": "candidate_context",
                "why": "Imported into the active seed surface context.",
            }
        )
    return output


def is_valid_synth_concept_id(concept_id: str) -> bool:
    """[ACTION]
    - Teleology: Validate that a concept identifier matches the `con_*` doctrine pattern required by intent.concept_refs.
    - Guarantee: Returns True if the id is non-empty and matches `^con_[a-z0-9_]+$` (case-insensitive), else False.
    - Fails: None.
    """
    token = _string(concept_id)
    return bool(token) and bool(_CONCEPT_ID_PATTERN.match(token))


def normalize_intent_concept_refs(value: Any) -> list[dict[str, str]]:
    """[ACTION]
    - Teleology: Normalize intent.concept_refs entries so each item carries a valid concept_id, role, and optional gloss without duplicates.
    - Guarantee: Returns a deduped list of dicts with `concept_id` and `role` fields; roles outside the allowed set are coerced to `"supporting"`.
    - Fails: None.
    """
    output: list[dict[str, str]] = []
    if not isinstance(value, list):
        return output
    seen: set[str] = set()
    for index, item in enumerate(value, start=1):
        if not isinstance(item, Mapping):
            continue
        cid = _string(item.get("concept_id"))
        if not cid:
            continue
        role = _string(item.get("role")).lower() or "supporting"
        if role not in _CONCEPT_REF_ROLES:
            role = "supporting"
        gloss = _string(item.get("gloss"))
        if cid in seen:
            continue
        seen.add(cid)
        row: dict[str, str] = {"concept_id": cid, "role": role}
        if gloss:
            row["gloss"] = gloss
        output.append(row)
    return output


def normalize_intent_extracted_shard_ids(value: Any) -> list[str]:
    """[ACTION]
    - Teleology: Normalize the intent.extracted_shard_ids list into a deduped list of non-empty strings.
    - Guarantee: Returns a deduped list of stripped shard-id strings; non-list input yields an empty list.
    - Fails: None.
    """
    if not isinstance(value, list):
        return []
    return _dedupe_strings([_string(item) for item in value])


def normalize_raw_seed_refs(value: Any) -> list[dict[str, str]]:
    """[ACTION]
    - Teleology: Normalize a raw-seed-refs list into the canonical structured form with id, authority_path, target_kind, target_id, and label fields.
    - Guarantee: Returns a deduped list of dicts; duplicate (authority_path, target_kind, target_id, label) tuples are dropped; paths are canonicalized.
    - Fails: None.
    """
    output: list[dict[str, str]] = []
    seen: set[tuple[str, str, str, str]] = set()
    if not isinstance(value, list):
        value = [value] if value is not None else []
    for index, item in enumerate(value, start=1):
        if isinstance(item, Mapping):
            ref_id = _string(item.get("id")) or f"RAW_REF_{index:03d}"
            authority_path = canonicalize_write_path(_string(item.get("authority_path"))) or ""
            target_kind = _string(item.get("target_kind")) or "manual"
            target_id = _string(item.get("target_id"))
            label = _string(item.get("label") or item.get("anchor") or item.get("target"))
        else:
            ref_id = f"RAW_REF_{index:03d}"
            authority_path = ""
            target_kind = "manual"
            target_id = ""
            label = _string(item)
        identity = (authority_path, target_kind, target_id, label)
        if identity in seen:
            continue
        seen.add(identity)
        output.append(
            {
                "id": ref_id,
                "authority_path": authority_path,
                "target_kind": target_kind,
                "target_id": target_id,
                "label": label,
            }
        )
    return output


def normalize_source_shards(value: Any) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize a source-shards list so each shard carries canonical id, anchor, clarified statement, ref ids, and relevant-file paths.
    - Guarantee: Returns a list of normalized shard dicts; non-Mapping entries are skipped; extracted_shard_id is derived from id when not explicit.
    - Fails: None.
    """
    output: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return output
    for item in value:
        if not isinstance(item, Mapping):
            continue
        shard = dict(item)
        shard["id"] = _string(shard.get("id"))
        shard["raw_seed_anchor"] = _string(shard.get("raw_seed_anchor"))
        shard["clarified_statement"] = _string(shard.get("clarified_statement") or shard.get("question"))
        shard["raw_seed_ref_ids"] = _dedupe_strings([_string(ref_id) for ref_id in shard.get("raw_seed_ref_ids", [])])
        esid = _string(shard.get("extracted_shard_id"))
        sid = _string(shard.get("id"))
        if esid:
            shard["extracted_shard_id"] = esid
        elif sid:
            shard["extracted_shard_id"] = sid
        elif "extracted_shard_id" in shard:
            shard.pop("extracted_shard_id", None)
        shard["relevant_files"] = [
            file_path
            for file_path in synth_relevant_file_paths({"relevant_files": shard.get("relevant_files", [])})
            if file_path
        ]
        output.append(shard)
    return output


def normalize_working_set(value: Any) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize the current-wave working set into the same structured path/role/why shape as relevant files.
    - Guarantee: Returns a deduped list of working-set entries with canonical paths and non-empty role/why text.
    - Fails: None.
    """
    output: list[dict[str, Any]] = []
    seen: set[str] = set()
    if not isinstance(value, list):
        value = [value] if value is not None else []
    for item in value:
        if isinstance(item, Mapping):
            path = canonicalize_write_path(_string(item.get("path"))) or ""
            if not path or path in seen:
                continue
            seen.add(path)
            row: dict[str, Any] = {
                "path": path,
                "role": _string(item.get("role")) or "active_context",
                "why": _string(item.get("why") or item.get("note")) or "Active wave working context.",
            }
            row.update(_normalize_path_card_extras(item))
            output.append(row)
            continue
        path = canonicalize_write_path(_string(item)) or ""
        if not path or path in seen:
            continue
        seen.add(path)
        output.append(
            {
                "path": path,
                "role": "active_context",
                "why": "Active wave working context.",
            }
        )
    return output


def normalize_orientation(
    value: Any,
    *,
    intent: Mapping[str, Any] | None = None,
    current_wave: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """[ACTION]
    - Teleology: Normalize the synth's architect-view envelope so a resumed agent can orient from one concise operating stance instead of inferring it from prose alone.
    - Guarantee: Returns a dict with house_view, architectural_posture, evidence_posture, and pivot_rule.
    - Fails: None.
    """
    payload = dict(value) if isinstance(value, Mapping) else {}
    intent_payload = dict(intent or {})
    wave_payload = dict(current_wave or {})
    house_view = (
        _string(payload.get("house_view"))
        or _string(wave_payload.get("objective"))
        or _string(intent_payload.get("goal"))
        or "State the current architect's view of the subphase here."
    )
    architectural_posture = (
        _string(payload.get("architectural_posture"))
        or DEFAULT_SYNTH_ORIENTATION["architectural_posture"]
    )
    evidence_posture = (
        _string(payload.get("evidence_posture"))
        or DEFAULT_SYNTH_ORIENTATION["evidence_posture"]
    )
    pivot_rule = (
        _string(payload.get("pivot_rule"))
        or DEFAULT_SYNTH_ORIENTATION["pivot_rule"]
    )
    normalized = {
        "house_view": house_view,
        "architectural_posture": architectural_posture,
        "evidence_posture": evidence_posture,
        "pivot_rule": pivot_rule,
    }
    primary_unknown = _string(payload.get("primary_unknown") or wave_payload.get("bounded_question") or intent_payload.get("why_now"))
    if primary_unknown:
        normalized["primary_unknown"] = primary_unknown
    return normalized


def normalize_work_items(
    value: Any,
    *,
    current_wave: Mapping[str, Any] | None = None,
    working_set: list[dict[str, Any]] | None = None,
    execution_mode: str | None = None,
) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize the broad todo graph for a synth seed so multi-wave work can be tracked above the single active wave.
    - Guarantee: Returns a deduped list of work-item cards with stable ids, status, paths, and success signals.
    - Fails: None.
    """
    payload = value if isinstance(value, list) else []
    wave_payload = dict(current_wave or {})
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, item in enumerate(payload, start=1):
        if not isinstance(item, Mapping):
            continue
        work_item_id = _string(item.get("work_item_id") or item.get("id")) or f"work_item_{index:03d}"
        if work_item_id in seen:
            continue
        seen.add(work_item_id)
        row: dict[str, Any] = {
            "work_item_id": work_item_id,
            "title": _string(item.get("title")) or work_item_id.replace("_", " "),
            "status": _string(item.get("status")) or "planned",
            "intent": _string(item.get("intent") or item.get("objective")) or "State the bounded objective for this work item.",
            "paths": _dedupe_strings(
                [
                    canonicalize_write_path(_string(path)) or _string(path)
                    for path in (item.get("paths") or [])
                    if _string(path)
                ]
            ),
            "depends_on": _dedupe_strings([_string(dep) for dep in (item.get("depends_on") or [])]),
            "success_signals": _dedupe_strings([_string(sig) for sig in (item.get("success_signals") or [])]),
            "spawned_wave_ids": _dedupe_strings([_string(wave_id) for wave_id in (item.get("spawned_wave_ids") or [])]),
        }
        mode_hint = _string(item.get("mode_hint"))
        if mode_hint in EXECUTION_MODES:
            row["mode_hint"] = mode_hint
        notes = _string(item.get("notes") or item.get("note"))
        if notes:
            row["notes"] = notes
        normalized.append(row)
    if normalized:
        return normalized

    default_paths = [
        _string(item.get("path"))
        for item in (working_set or [])
        if isinstance(item, Mapping) and _string(item.get("path"))
    ]
    default_wave_id = _string(wave_payload.get("wave_id")) or "wave_001"
    default_item: dict[str, Any] = {
        "work_item_id": f"{default_wave_id}__primary",
        "title": _string(wave_payload.get("objective")) or "Primary wave objective",
        "status": "active" if _string(wave_payload.get("status")) in {"in_progress", "active"} else "planned",
        "intent": _string(wave_payload.get("objective")) or "State the bounded objective for this work item.",
        "paths": _dedupe_strings(default_paths),
        "depends_on": _dedupe_strings([_string(dep) for dep in (wave_payload.get("depends_on") or [])]),
        "success_signals": _dedupe_strings([_string(sig) for sig in (wave_payload.get("success_signals") or [])]),
        "spawned_wave_ids": [default_wave_id] if default_wave_id else [],
    }
    mode_hint = _string(execution_mode or wave_payload.get("mode"))
    if mode_hint in EXECUTION_MODES:
        default_item["mode_hint"] = mode_hint
    return [default_item]


def normalize_synthesis_memory(value: Any) -> dict[str, list[dict[str, Any]]]:
    """[ACTION]
    - Teleology: Normalize the structured synthesis memory so bridge outputs and local learnings can land as facts, decisions, and risks rather than dissolving into prose.
    - Guarantee: Returns an object with confirmed_facts, locked_decisions, and active_risks lists.
    - Fails: None.
    """
    payload = dict(value) if isinstance(value, Mapping) else {}

    def _normalize_fact_rows(rows: Any) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return output
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                continue
            fact_id = _string(row.get("fact_id") or row.get("id")) or f"fact_{index:03d}"
            if fact_id in seen:
                continue
            seen.add(fact_id)
            item: dict[str, Any] = {
                "fact_id": fact_id,
                "fact": _string(row.get("fact") or row.get("statement")),
            }
            evidence_refs = _dedupe_strings([_string(ref) for ref in (row.get("evidence_refs") or [])])
            related_paths = _dedupe_strings(
                [
                    canonicalize_write_path(_string(path)) or _string(path)
                    for path in (row.get("related_paths") or [])
                    if _string(path)
                ]
            )
            confidence = _string(row.get("confidence"))
            if evidence_refs:
                item["evidence_refs"] = evidence_refs
            if related_paths:
                item["related_paths"] = related_paths
            if confidence:
                item["confidence"] = confidence
            if item["fact"]:
                output.append(item)
        return output

    def _normalize_decision_rows(rows: Any) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return output
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                continue
            decision_id = _string(row.get("decision_id") or row.get("id")) or f"decision_{index:03d}"
            if decision_id in seen:
                continue
            seen.add(decision_id)
            item: dict[str, Any] = {
                "decision_id": decision_id,
                "decision": _string(row.get("decision")),
            }
            rationale = _string(row.get("rationale"))
            related_paths = _dedupe_strings(
                [
                    canonicalize_write_path(_string(path)) or _string(path)
                    for path in (row.get("related_paths") or [])
                    if _string(path)
                ]
            )
            scope = _string(row.get("scope"))
            if rationale:
                item["rationale"] = rationale
            if related_paths:
                item["related_paths"] = related_paths
            if scope:
                item["scope"] = scope
            if item["decision"]:
                output.append(item)
        return output

    def _normalize_risk_rows(rows: Any) -> list[dict[str, Any]]:
        output: list[dict[str, Any]] = []
        if not isinstance(rows, list):
            return output
        seen: set[str] = set()
        for index, row in enumerate(rows, start=1):
            if not isinstance(row, Mapping):
                continue
            risk_id = _string(row.get("risk_id") or row.get("id")) or f"risk_{index:03d}"
            if risk_id in seen:
                continue
            seen.add(risk_id)
            item: dict[str, Any] = {
                "risk_id": risk_id,
                "risk": _string(row.get("risk")),
                "status": _string(row.get("status")) or "open",
            }
            mitigation = _string(row.get("mitigation"))
            related_paths = _dedupe_strings(
                [
                    canonicalize_write_path(_string(path)) or _string(path)
                    for path in (row.get("related_paths") or [])
                    if _string(path)
                ]
            )
            if mitigation:
                item["mitigation"] = mitigation
            if related_paths:
                item["related_paths"] = related_paths
            if item["risk"]:
                output.append(item)
        return output

    result: dict[str, Any] = {
        "confirmed_facts": _normalize_fact_rows(payload.get("confirmed_facts")),
        "locked_decisions": _normalize_decision_rows(payload.get("locked_decisions")),
        "active_risks": _normalize_risk_rows(payload.get("active_risks")),
    }
    # Continue-mode / subphase-loop extension fields: preserve verbatim so the
    # dispatch-loop template contract survives normalization.
    open_questions = payload.get("open_questions")
    if isinstance(open_questions, list) and open_questions:
        result["open_questions"] = [_string(item) for item in open_questions if _string(item)]
    per_wave_log = payload.get("per_wave_log")
    if isinstance(per_wave_log, list) and per_wave_log:
        result["per_wave_log"] = [dict(item) for item in per_wave_log if isinstance(item, Mapping)]
    per_wave_contract = payload.get("per_wave_log_entry_contract")
    if isinstance(per_wave_contract, Mapping):
        result["per_wave_log_entry_contract"] = dict(per_wave_contract)
    lifecycle_state = _string(payload.get("current_lifecycle_state"))
    if lifecycle_state:
        result["current_lifecycle_state"] = lifecycle_state
    lifecycle_enum = payload.get("current_lifecycle_state_enum")
    if isinstance(lifecycle_enum, list) and lifecycle_enum:
        result["current_lifecycle_state_enum"] = [
            _string(item) for item in lifecycle_enum if _string(item)
        ]
    learnings = payload.get("learnings_for_template_evolution")
    if isinstance(learnings, list) and learnings:
        result["learnings_for_template_evolution"] = [
            _string(item) for item in learnings if _string(item)
        ]
    return result


def _normalize_wave_groups(value: Any) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return output
    for item in value:
        if not isinstance(item, Mapping):
            continue
        title = _string(item.get("title") or item.get("label") or item.get("group_id"))
        label = _string(item.get("label"))
        group_id = _string(item.get("group_id"))
        if not group_id:
            seed = label or title
            group_id = re.sub(r"[^a-zA-Z0-9]+", "_", seed).strip("_").lower() if seed else ""
        answer = _string(item.get("answer") or item.get("question") or item.get("objective"))
        reads = [
            canonicalize_write_path(_string(entry)) or _string(entry)
            for entry in (item.get("reads") or [])
            if _string(entry)
        ] if isinstance(item.get("reads"), list) else []
        group: dict[str, Any] = {}
        if title:
            group["title"] = title
        if label:
            group["label"] = label
        if group_id:
            group["group_id"] = group_id
        if answer:
            group["answer"] = answer
        if reads:
            group["reads"] = _dedupe_strings(reads)
        role = _string(item.get("role"))
        if role:
            group["role"] = role
        response_path = canonicalize_write_path(_string(item.get("response_path"))) or _string(item.get("response_path"))
        if response_path:
            group["response_path"] = response_path
        target_path = canonicalize_write_path(_string(item.get("target_path"))) or _string(item.get("target_path"))
        if target_path:
            group["target_path"] = target_path
        response_surface = item.get("response_surface")
        if isinstance(response_surface, Mapping):
            group["response_surface"] = dict(response_surface)
        elif _string(response_surface):
            group["response_surface"] = _string(response_surface)
        depends_on = _dedupe_strings([_string(dep) for dep in (item.get("depends_on") or [])])
        if depends_on:
            group["depends_on"] = depends_on
        shard_ids = _dedupe_strings([_string(dep) for dep in (item.get("extracted_shard_ids") or [])])
        if shard_ids:
            group["extracted_shard_ids"] = shard_ids
        incoming_queries: list[dict[str, Any]] = []
        for query in (item.get("incoming_queries") or []):
            if not isinstance(query, Mapping):
                continue
            target_label = _string(query.get("target_label"))
            question = _string(query.get("question"))
            if not target_label and not question:
                continue
            normalized_query: dict[str, Any] = {}
            if target_label:
                normalized_query["target_label"] = target_label
            if question:
                normalized_query["question"] = question
            source_label = _string(query.get("source_label"))
            rationale = _string(query.get("rationale"))
            if source_label:
                normalized_query["source_label"] = source_label
            if rationale:
                normalized_query["rationale"] = rationale
            if normalized_query:
                incoming_queries.append(normalized_query)
        if incoming_queries:
            group["incoming_queries"] = incoming_queries
        if group:
            output.append(group)
    return output


def normalize_checkpoint_policy(value: Any, *, stage_kind: str) -> dict[str, Any]:
    payload = dict(value) if isinstance(value, Mapping) else {}
    normalized_stage = _string(stage_kind)
    if normalized_stage not in PHASE_STEP_STAGE_KINDS:
        normalized_stage = "problem_space"
    max_clarify_depth = max(1, _int(payload.get("max_clarify_depth"), 2))
    clarify_depth = max(0, _int(payload.get("clarify_depth"), 0))
    return {
        "rubric_id": _string(payload.get("rubric_id")) or f"builtin:{normalized_stage}",
        "max_clarify_depth": max_clarify_depth,
        "clarify_depth": clarify_depth,
    }


def normalize_assimilation_targets(
    value: Any,
    *,
    phase_scaffold: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Normalize the phase-assimilation target bundle so kernel lifecycle commands have stable archive, delta, and continuation paths.
    - Guarantee: Returns a dict with canonical repo-relative paths where possible; missing fields fall back to phase-local defaults.
    - Fails: None.
    """
    scaffold = dict(phase_scaffold or {})
    phase_dir = _string(scaffold.get("phase_dir"))
    if not phase_dir and isinstance(value, Mapping):
        for key in ("ledger_path", "delta_path", "continuation_summary_path", "archive_root"):
            candidate = canonicalize_write_path(_string(value.get(key)))
            if not candidate or "/" not in candidate:
                continue
            phase_dir = candidate.rsplit("/", 1)[0]
            if phase_dir.endswith("/archive"):
                phase_dir = phase_dir[: -len("/archive")]
            break
    whiteboard = dict(scaffold.get("whiteboard_contract") or {})
    archive_root_default = canonicalize_write_path(_string(scaffold.get("archive_root")) or f"{phase_dir}/archive") or ""
    ledger_default = canonicalize_write_path(_string(whiteboard.get("meta_ledger_path")) or f"{phase_dir}/meta_ledger.json") or ""
    defaults = {
        "archive_root": archive_root_default,
        "ledger_path": ledger_default,
        "delta_path": canonicalize_write_path(f"{phase_dir}/synth_seed_delta.json") or "",
        "continuation_summary_path": canonicalize_write_path(f"{phase_dir}/continuation_summary.json") or "",
        "artifact_paths": [],
    }
    payload = dict(value) if isinstance(value, Mapping) else {}
    normalized = {
        "archive_root": canonicalize_write_path(_string(payload.get("archive_root"))) or defaults["archive_root"],
        "ledger_path": canonicalize_write_path(_string(payload.get("ledger_path"))) or defaults["ledger_path"],
        "delta_path": canonicalize_write_path(_string(payload.get("delta_path"))) or defaults["delta_path"],
        "continuation_summary_path": canonicalize_write_path(_string(payload.get("continuation_summary_path"))) or defaults["continuation_summary_path"],
        "artifact_paths": _dedupe_strings(
            [
                canonicalize_write_path(_string(item)) or _string(item)
                for item in (payload.get("artifact_paths") or [])
                if _string(item)
            ]
        ),
    }
    for key in ("resume_contract_path", "observe_plan_path"):
        rel = canonicalize_write_path(_string(payload.get(key)))
        if rel:
            normalized[key] = rel
    return normalized


def normalize_track_catalog(value: Any) -> list[dict[str, Any]]:
    """[ACTION]
    - Teleology: Normalize optional parallel-track metadata into a stable list of track cards without making tracks mandatory in v1.
    - Guarantee: Returns a list of track dicts with stable ids and optional descriptive fields.
    - Fails: None.
    """
    output: list[dict[str, Any]] = []
    if not isinstance(value, list):
        return output
    seen: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            continue
        track_id = _string(item.get("track_id") or item.get("id"))
        if not track_id or track_id in seen:
            continue
        seen.add(track_id)
        row = {"track_id": track_id}
        for key in ("label", "status", "focus", "notes"):
            token = _string(item.get(key))
            if token:
                row[key] = token
        output.append(row)
    return output


def normalize_current_wave(
    value: Any,
    *,
    phase_scaffold: Mapping[str, Any] | None = None,
    intent: Mapping[str, Any] | None = None,
    working_set: list[dict[str, str]] | None = None,
    execution_mode: str | None = None,
    fallback_groups: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Normalize the active-wave envelope so execution mode, target paths, and optional bridge groups all flow through one stable contract.
    - Guarantee: Returns a dict with required wave fields populated from explicit input or scaffold/intent fallbacks.
    - Fails: None.
    """
    scaffold = dict(phase_scaffold or {})
    intent_payload = dict(intent or {})
    payload = dict(value) if isinstance(value, Mapping) else {}
    phase_id = _string(scaffold.get("phase_id"))
    if not phase_id:
        meta = dict(scaffold.get("meta") or {})
        phase_id = _string(meta.get("phase_id"))
    phase_title = _string(scaffold.get("phase_title"))
    if not phase_title:
        meta = dict(scaffold.get("meta") or {})
        phase_title = _string(meta.get("phase_title"))
    normalized_mode = _string(payload.get("mode") or execution_mode)
    if normalized_mode not in EXECUTION_MODES:
        normalized_mode = "direct_local"
    success_signals = _dedupe_strings(
        [_string(item) for item in (payload.get("success_signals") or intent_payload.get("success_criteria") or [])]
    )
    target_paths = _dedupe_strings(
        [
            canonicalize_write_path(_string(item)) or _string(item)
            for item in (
                payload.get("target_paths")
                or [item.get("path") for item in (working_set or []) if isinstance(item, Mapping)]
            )
            if _string(item)
        ]
    )
    groups = _normalize_wave_groups(payload.get("groups") or fallback_groups or [])
    stage_kind = _string(payload.get("stage_kind")).lower()
    if stage_kind not in PHASE_STEP_STAGE_KINDS:
        stage_kind = "problem_space"
    checkpoint_policy = normalize_checkpoint_policy(payload.get("checkpoint_policy"), stage_kind=stage_kind)
    wave = {
        "wave_id": _string(payload.get("wave_id")) or f"{phase_id or 'phase'}_wave_001",
        "objective": _string(payload.get("objective")) or _string(intent_payload.get("goal")) or phase_title or "Advance the active phase by one bounded wave.",
        "mode": normalized_mode,
        "stage_kind": stage_kind,
        "bounded_question": _string(payload.get("bounded_question")) or _string(intent_payload.get("why_now")) or "What is the next bounded move?",
        "success_signals": success_signals,
        "target_paths": target_paths,
        "depends_on": _dedupe_strings([_string(item) for item in (payload.get("depends_on") or [])]),
        "status": _string(payload.get("status")) or "planned",
        "checkpoint_policy": checkpoint_policy,
        "spawned_wave_ids": _dedupe_strings([_string(item) for item in (payload.get("spawned_wave_ids") or [])]),
    }
    track_id = _string(payload.get("track_id"))
    if track_id:
        wave["track_id"] = track_id
    operator_notes = _string(payload.get("operator_notes"))
    if operator_notes:
        wave["operator_notes"] = operator_notes
    handoff_requirements = _dedupe_strings([_string(item) for item in (payload.get("handoff_requirements") or [])])
    if handoff_requirements:
        wave["handoff_requirements"] = handoff_requirements
    carry_forward_posture = _string(payload.get("carry_forward_posture"))
    if carry_forward_posture:
        wave["carry_forward_posture"] = carry_forward_posture
    if groups:
        wave["groups"] = groups
    # Preserve deployment-time continue-mode extensions. The dispatch-loop
    # subphase template carries these fields through the runtime contract;
    # dropping them silently breaks continue-mode execution.
    continue_mode_strategy = payload.get("continue_mode_strategy")
    if isinstance(continue_mode_strategy, Mapping):
        wave["continue_mode_strategy"] = dict(continue_mode_strategy)
    return wave


def build_family_charter_payload(
    *,
    family_id: str,
    family_number: str,
    family_title: str,
    family_dir: str,
    parent: str,
    raw_seed_path: str,
    doctrine_refs: list[str] | None = None,
    broad_goal: str = "",
    why_now: str = "",
    success_horizon: list[str] | None = None,
    non_goals: list[str] | None = None,
    invariants: list[str] | None = None,
    raw_seed_refs: list[dict[str, str]] | None = None,
    allowed_execution_modes: list[str] | None = None,
    default_continuity_mode: str = "gate_bounded",
    operating_posture: str = "",
) -> dict[str, Any]:
    """[ACTION]
    - Teleology: Build the durable family-root charter that explains why a family exists without overloading the thin phase_family marker.
    - Guarantee: Returns a deterministic `family_charter_v1` payload with machine-readable family intent, invariants, and operating posture.
    - Fails: None.
    """
    now = _utc_now()
    normalized_continuity = default_continuity_mode if default_continuity_mode in CONTINUITY_MODES else "gate_bounded"
    allowed_modes = [
        mode
        for mode in _dedupe_strings(list(allowed_execution_modes or list(EXECUTION_MODES)))
        if mode in EXECUTION_MODES
    ] or sorted(EXECUTION_MODES)
    charter_raw_seed_refs = raw_seed_refs or [
        {
            "id": "family_raw_seed",
            "authority_path": raw_seed_path,
            "target_kind": "document",
            "target_id": "raw_seed.md",
            "label": f"Phase {family_number} raw seed",
        }
    ]
    return {
        "kind": FAMILY_CHARTER_KIND,
        "schema_version": FAMILY_CHARTER_VERSION,
        "family_id": family_id,
        "family_number": family_number,
        "family_title": family_title,
        "family_dir": family_dir,
        "parent": parent,
        "created_at": now,
        "updated_at": now,
        "broad_goal": _string(broad_goal)
        or (
            f"Carry Phase {family_number} intent through a durable family anchor that keeps the raw seed broad and the subphase packets bounded."
        ),
        "why_now": _string(why_now)
        or (
            "The family charter exists so active packets can change shape without making agents reconstruct the broader intent from stale subphase sediment."
        ),
        "success_horizon": _dedupe_strings(
            list(success_horizon or [
                "New subphases can orient from the family anchor without reopening the whole family raw seed.",
                "Execution mode, continuity posture, and broad non-goals remain stable even as active waves change.",
            ])
        ),
        "non_goals": _dedupe_strings(
            list(non_goals or [
                "Do not turn the family charter into the active implementation whiteboard.",
                "Do not duplicate the raw seed or active synth in slightly different prose.",
            ])
        ),
        "invariants": _dedupe_strings(
            list(invariants or [
                "The family raw seed remains the broad blackboard.",
                "Subphases are bounded whiteboards with one active synth seed and a wave history.",
                "Observe plans are execution strategies, not mandatory entry ceremony.",
            ])
        ),
        "raw_seed_refs": normalize_raw_seed_refs(charter_raw_seed_refs),
        "doctrine_refs": _dedupe_strings(
            list(
                doctrine_refs
                or [
                    OBSERVE_APPLY_STANDARD_PATHS["phase_family"],
                    OBSERVE_APPLY_STANDARD_PATHS["phase_scaffold"],
                    OBSERVE_APPLY_STANDARD_PATHS["synth_seed"],
                ]
            )
        ),
        "allowed_execution_modes": allowed_modes,
        "default_continuity_mode": normalized_continuity,
        "operating_posture": _string(operating_posture)
        or "Start from the family charter, orient through the active phase card, then choose the lightest execution mode that can finish the current wave cleanly.",
    }


def synth_relevant_file_paths(payload: Mapping[str, Any] | None) -> list[str]:
    """[ACTION]
    - Teleology: Extract the flat list of canonicalized relevant-file paths from a synth payload without retaining role or why metadata.
    - Guarantee: Returns a list of non-empty path strings from `payload["relevant_files"]`; non-mapping or empty input yields an empty list.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return []
    files = normalize_relevant_files(payload.get("relevant_files"))
    return [item["path"] for item in files]


def synth_goal_text(payload: Mapping[str, Any] | None) -> str:
    """[ACTION]
    - Teleology: Extract the goal text from a synth-seed payload's intent block, supporting both structured and legacy string intent shapes.
    - Guarantee: Returns a stripped goal string, or an empty string when no goal is present.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return ""
    intent = payload.get("intent")
    if isinstance(intent, Mapping):
        return _string(intent.get("goal"))
    return _string(intent)


def synth_why_now_text(payload: Mapping[str, Any] | None) -> str:
    """[ACTION]
    - Teleology: Extract the why_now text from a synth-seed payload's structured intent block.
    - Guarantee: Returns a stripped why_now string, or an empty string when the field is absent or the intent is not a mapping.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return ""
    intent = payload.get("intent")
    if isinstance(intent, Mapping):
        return _string(intent.get("why_now"))
    return ""


def synth_intent_concept_ids(payload: Mapping[str, Any] | None) -> list[str]:
    """[ACTION]
    - Teleology: Extract the deduped list of concept ids from a synth-seed payload's intent.concept_refs for enrichment and injection use.
    - Guarantee: Returns a deduped list of non-empty concept-id strings, or an empty list when no concept refs exist.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return []
    intent = payload.get("intent")
    if not isinstance(intent, Mapping):
        return []
    refs = normalize_intent_concept_refs(intent.get("concept_refs", []))
    return _dedupe_strings([_string(r.get("concept_id")) for r in refs if _string(r.get("concept_id"))])


def synth_intent_extracted_shard_ids(payload: Mapping[str, Any] | None) -> list[str]:
    """[ACTION]
    - Teleology: Extract the deduped list of extracted shard ids from a synth-seed payload's intent block.
    - Guarantee: Returns a deduped list of non-empty shard-id strings, or an empty list when absent.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return []
    intent = payload.get("intent")
    if not isinstance(intent, Mapping):
        return []
    return normalize_intent_extracted_shard_ids(intent.get("extracted_shard_ids", []))


def synth_success_criteria_list(payload: Mapping[str, Any] | None) -> list[str]:
    """[ACTION]
    - Teleology: Extract the deduped success-criteria list from a synth-seed payload, supporting both structured intent and legacy top-level shapes.
    - Guarantee: Returns a deduped list of non-empty criteria strings, or an empty list when none are present.
    - Fails: None.
    """
    if not isinstance(payload, Mapping):
        return []
    intent = payload.get("intent")
    if isinstance(intent, Mapping) and isinstance(intent.get("success_criteria"), list):
        return _dedupe_strings([_string(item) for item in intent.get("success_criteria", [])])
    legacy = _string(payload.get("success_criteria"))
    return [legacy] if legacy else []


def synth_success_criteria_text(payload: Mapping[str, Any] | None) -> str:
    """[ACTION]
    - Teleology: Render the success-criteria list from a synth-seed payload as a single semicolon-joined string for prompt injection or display.
    - Guarantee: Returns a non-empty semicolon-joined string of criteria, or an empty string when no criteria exist.
    - Fails: None.
    """
    criteria = synth_success_criteria_list(payload)
    return "; ".join(criteria)


def normalize_synth_payload(
    payload: Mapping[str, Any] | None,
    *,
    phase_scaffold: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Normalize authored or legacy synth payloads into the current `synth_seed_v5` contract so downstream validators, renderers, and lifecycle commands work against one stable shape.
    - Mechanism: Merge scaffold defaults, normalize intent traceability fields, preserve living-charter extensions, add wave/working-set state, migrate legacy payloads into the synth-first shape, and return the normalized mapping.
    - Reads: `payload`, optional `phase_scaffold`, and the helper normalizers/constants in this module.
    - Writes: None.
    - Guarantee: Returns `None` for non-mapping payloads; otherwise returns a `synth_seed_v5`-shaped dict with normalized intent, orientation, work-item graph, execution state, relevant files, source shards, synthesis memory, and meta fields.
    - Fails: None.
    - Orders: Current-version payloads stay in the modern authority shape first; legacy payloads are migrated deterministically into the same contract.
    - When-needed: Open when synth JSON must be normalized before validation, markdown rendering, lifecycle sync, or prompt injection.
    - Escalates-to: system/lib/kernel/commands/navigate.py; system/lib/observe_plan_enrichment.py
    - Navigation-group: kernel_lib
    """
    if not isinstance(payload, Mapping):
        return None

    scaffold = dict(phase_scaffold or {})
    scaffold_phase_id = _string(scaffold.get("phase_id"))
    scaffold_phase_number = _string(scaffold.get("phase_number"))
    scaffold_phase_title = _string(scaffold.get("phase_title"))
    scaffold_family_dir = _string(scaffold.get("family_dir"))
    scaffold_phase_dir = _string(scaffold.get("phase_dir"))
    scaffold_parent_phase_id = _string(scaffold.get("parent_phase_id")) or None
    scaffold_source_authority_kind = _string(scaffold.get("source_authority_kind")) or source_authority_kind_for_phase(
        parent_phase_id=scaffold_parent_phase_id
    )
    scaffold_source_authority_path = _string(scaffold.get("source_authority_path"))

    version = _string(payload.get("version"))
    now = _utc_now()
    meta = dict(payload.get("meta") or {})

    if version != SYNTH_SEED_VERSION or not isinstance(payload.get("intent"), Mapping):
        original_payload = dict(payload)
        legacy_intent = dict(payload.get("intent") or {}) if isinstance(payload.get("intent"), Mapping) else {}
        legacy_source_shards = [
            dict(item)
            for item in normalize_source_shards(payload.get("source_shards") or payload.get("seed_shards") or [])
        ]
        investigation_threads = payload.get("investigation_threads")
        if not isinstance(investigation_threads, list):
            investigation_threads = []
        if not investigation_threads:
            for shard in legacy_source_shards:
                statement = _string(shard.get("clarified_statement") or shard.get("question") or shard.get("statement"))
                if not statement:
                    continue
                investigation_threads.append(
                    {
                        "id": _string(shard.get("id") or shard.get("shard_id")) or f"THREAD_{len(investigation_threads) + 1:03d}",
                        "statement": statement,
                        "status": "open",
                        "relevant_files": synth_relevant_file_paths({"relevant_files": shard.get("relevant_files", [])}),
                    }
                )
        payload = {
            "version": SYNTH_SEED_VERSION,
            "authoring_status": _string(payload.get("authoring_status")) or "authored",
            "generated_at": _string(payload.get("generated_at")) or now,
            "intent": {
                "goal": _string(legacy_intent.get("goal")) or _string(payload.get("intent")),
                "why_now": _string(legacy_intent.get("why_now")) or _string(payload.get("why_now")),
                "raw_seed_anchors": _dedupe_strings(
                    [
                        _string(item)
                        for item in (
                            legacy_intent.get("raw_seed_anchors")
                            or payload.get("raw_seed_anchors")
                            or []
                        )
                    ]
                ),
                "raw_seed_refs": normalize_raw_seed_refs(
                    legacy_intent.get("raw_seed_refs") or payload.get("raw_seed_refs", [])
                ),
                "success_criteria": _dedupe_strings(
                    [
                        _string(item)
                        for item in (
                            legacy_intent.get("success_criteria")
                            or (
                                [_string(payload.get("success_criteria"))]
                                if _string(payload.get("success_criteria"))
                                else []
                            )
                        )
                    ]
                ),
                "non_goals": _dedupe_strings(
                    [_string(item) for item in (legacy_intent.get("non_goals") or payload.get("non_goals", []))]
                ),
            },
            "constraints": _dedupe_strings([_string(item) for item in payload.get("constraints", [])]) or list(DEFAULT_SYNTH_CONSTRAINTS),
            "relevant_files": normalize_relevant_files(payload.get("relevant_files")),
            "investigation_threads": [dict(item) for item in investigation_threads if isinstance(item, Mapping)],
            "apply_boundary": dict(payload.get("apply_boundary") or DEFAULT_APPLY_BOUNDARY),
            "source_shards": legacy_source_shards,
            "meta": {
                "phase_id": _string(meta.get("phase_id")) or scaffold_phase_id or None,
                "phase_number": _string(meta.get("phase_number")) or scaffold_phase_number or None,
                "phase_title": _string(meta.get("phase_title")) or scaffold_phase_title or None,
                "phase_dir": _string(meta.get("phase_dir")) or scaffold_phase_dir or None,
                "parent_phase_id": _string(meta.get("parent_phase_id")) or scaffold_parent_phase_id,
                "family_dir": _string(meta.get("family_dir")) or scaffold_family_dir or None,
                "controller_version": _string(meta.get("controller_version")) or scaffold_phase_number or scaffold_phase_id or None,
                "controller_phase": _string(meta.get("controller_phase")) or "scope",
                "current_cycle": int(meta.get("current_cycle") or 0),
                "source_authority_kind": _string(meta.get("source_authority_kind")) or scaffold_source_authority_kind,
                "source_authority_path": _string(meta.get("source_authority_path")) or scaffold_source_authority_path or None,
                "created_at": _string(meta.get("created_at")) or now,
                "updated_at": _string(meta.get("updated_at")) or now,
            },
        }
        if legacy_intent.get("concept_refs"):
            payload["intent"]["concept_refs"] = normalize_intent_concept_refs(legacy_intent.get("concept_refs", []))
        if legacy_intent.get("extracted_shard_ids"):
            payload["intent"]["extracted_shard_ids"] = normalize_intent_extracted_shard_ids(
                legacy_intent.get("extracted_shard_ids", [])
            )
        for key in (
            "continuity_mode",
            "outstanding_questions",
            "active_hypotheses",
            "progress_state",
            "next_step_posture",
            "execution_mode",
            "current_wave",
            "working_set",
            "assimilation_targets",
            "orientation",
            "work_items",
            "synthesis_memory",
            "track_catalog",
            "active_track_id",
        ):
            if key in original_payload:
                payload[key] = original_payload.get(key)
        meta = dict(payload.get("meta") or {})

    effective_scaffold = dict(scaffold)
    if not _string(effective_scaffold.get("phase_id")) and _string(meta.get("phase_id")):
        effective_scaffold["phase_id"] = _string(meta.get("phase_id"))
    if not _string(effective_scaffold.get("phase_title")) and _string(meta.get("phase_title")):
        effective_scaffold["phase_title"] = _string(meta.get("phase_title"))
    if not _string(effective_scaffold.get("phase_dir")) and _string(meta.get("phase_dir")):
        effective_scaffold["phase_dir"] = _string(meta.get("phase_dir"))
    if not _string(effective_scaffold.get("family_dir")) and _string(meta.get("family_dir")):
        effective_scaffold["family_dir"] = _string(meta.get("family_dir"))
    if not _string(effective_scaffold.get("parent_phase_id")) and _string(meta.get("parent_phase_id")):
        effective_scaffold["parent_phase_id"] = _string(meta.get("parent_phase_id"))
    if not _string(effective_scaffold.get("source_authority_kind")) and _string(meta.get("source_authority_kind")):
        effective_scaffold["source_authority_kind"] = _string(meta.get("source_authority_kind"))
    if not _string(effective_scaffold.get("source_authority_path")) and _string(meta.get("source_authority_path")):
        effective_scaffold["source_authority_path"] = _string(meta.get("source_authority_path"))

    intent = dict(payload.get("intent") or {})
    raw_seed_refs = normalize_raw_seed_refs(intent.get("raw_seed_refs", []))
    concept_refs = normalize_intent_concept_refs(intent.get("concept_refs", []))
    extracted_shard_ids = normalize_intent_extracted_shard_ids(intent.get("extracted_shard_ids", []))
    raw_seed_anchors = _dedupe_strings([_string(item) for item in intent.get("raw_seed_anchors", [])])
    if not raw_seed_anchors and raw_seed_refs:
        raw_seed_anchors = _dedupe_strings(
            [_string(item.get("label") or item.get("target_id")) for item in raw_seed_refs]
        )
    intent_out: dict[str, Any] = {
        "goal": _string(intent.get("goal")),
        "why_now": _string(intent.get("why_now")),
        "raw_seed_anchors": raw_seed_anchors,
        "raw_seed_refs": raw_seed_refs,
        "success_criteria": _dedupe_strings([_string(item) for item in intent.get("success_criteria", [])]),
        "non_goals": _dedupe_strings([_string(item) for item in intent.get("non_goals", [])]),
    }
    if concept_refs:
        intent_out["concept_refs"] = concept_refs
    if extracted_shard_ids:
        intent_out["extracted_shard_ids"] = extracted_shard_ids

    relevant_files = normalize_relevant_files(payload.get("relevant_files"))
    working_set = normalize_working_set(payload.get("working_set") or relevant_files)
    current_wave = normalize_current_wave(
        payload.get("current_wave"),
        phase_scaffold=effective_scaffold,
        intent=intent_out,
        working_set=working_set,
        execution_mode=_string(payload.get("execution_mode")),
        fallback_groups=effective_scaffold.get("observe_groups") if isinstance(effective_scaffold.get("observe_groups"), list) else [],
    )
    orientation = normalize_orientation(
        payload.get("orientation"),
        intent=intent_out,
        current_wave=current_wave,
    )
    work_items = normalize_work_items(
        payload.get("work_items"),
        current_wave=current_wave,
        working_set=working_set,
        execution_mode=_string(payload.get("execution_mode")) or _string(current_wave.get("mode")),
    )
    synthesis_memory = normalize_synthesis_memory(payload.get("synthesis_memory"))
    normalized: dict[str, Any] = {
        "version": SYNTH_SEED_VERSION,
        "authoring_status": _string(payload.get("authoring_status")) or PENDING_SYNTH_AUTHORING,
        "generated_at": _string(payload.get("generated_at")) or now,
        "intent": intent_out,
        "orientation": orientation,
        "execution_mode": _string(current_wave.get("mode")) or "direct_local",
        "current_wave": current_wave,
        "work_items": work_items,
        "working_set": working_set,
        "assimilation_targets": normalize_assimilation_targets(payload.get("assimilation_targets"), phase_scaffold=effective_scaffold),
        "constraints": _dedupe_strings([_string(item) for item in payload.get("constraints", [])]) or list(DEFAULT_SYNTH_CONSTRAINTS),
        "relevant_files": relevant_files,
        "investigation_threads": [
            dict(item)
            for item in payload.get("investigation_threads", [])
            if isinstance(item, Mapping)
        ],
        "apply_boundary": dict(payload.get("apply_boundary") or DEFAULT_APPLY_BOUNDARY),
        "source_shards": [
            dict(item)
            for item in normalize_source_shards(payload.get("source_shards"))
        ],
        "synthesis_memory": synthesis_memory,
        "meta": {
            "phase_id": _string(meta.get("phase_id")) or scaffold_phase_id or None,
            "phase_number": _string(meta.get("phase_number")) or scaffold_phase_number or None,
            "phase_title": _string(meta.get("phase_title")) or scaffold_phase_title or None,
            "phase_dir": _string(meta.get("phase_dir")) or scaffold_phase_dir or None,
            "parent_phase_id": _string(meta.get("parent_phase_id")) or scaffold_parent_phase_id,
            "family_dir": _string(meta.get("family_dir")) or scaffold_family_dir or None,
            "controller_version": _string(meta.get("controller_version")) or scaffold_phase_number or scaffold_phase_id or None,
            "controller_phase": _string(meta.get("controller_phase")) or "scope",
            "current_cycle": int(meta.get("current_cycle") or 0),
            "source_authority_kind": _string(meta.get("source_authority_kind")) or scaffold_source_authority_kind,
            "source_authority_path": _string(meta.get("source_authority_path")) or scaffold_source_authority_path or None,
            "created_at": _string(meta.get("created_at")) or now,
            "updated_at": _string(meta.get("updated_at")) or now,
        },
    }
    # Preserve deployment-time meta extensions used by the subphase dispatch
    # loop template. These fields are declarative contract, not authored prose;
    # stripping them breaks the continue-mode runtime.
    meta_extensions = {
        "template_source": _string,
        "dispatch_loop_integration": dict,
        "closeout_protocol": dict,
    }
    for key, caster in meta_extensions.items():
        value = meta.get(key)
        if caster is _string:
            token = _string(value)
            if token:
                normalized["meta"][key] = token
        elif isinstance(value, Mapping):
            normalized["meta"][key] = dict(value)
    continuity_mode = _string(payload.get("continuity_mode"))
    if continuity_mode in CONTINUITY_MODES:
        normalized["continuity_mode"] = continuity_mode
    oq = payload.get("outstanding_questions")
    if isinstance(oq, list) and oq:
        normalized["outstanding_questions"] = [dict(q) for q in oq if isinstance(q, Mapping)]
    ah = payload.get("active_hypotheses")
    if isinstance(ah, list) and ah:
        normalized["active_hypotheses"] = [dict(h) for h in ah if isinstance(h, Mapping)]
    ps = payload.get("progress_state")
    if isinstance(ps, Mapping):
        normalized["progress_state"] = dict(ps)
    nsp = _string(payload.get("next_step_posture"))
    if nsp:
        normalized["next_step_posture"] = nsp
    track_catalog = normalize_track_catalog(payload.get("track_catalog"))
    if track_catalog:
        normalized["track_catalog"] = track_catalog
    active_track_id = _string(payload.get("active_track_id"))
    if active_track_id:
        normalized["active_track_id"] = active_track_id
    family_dir = _string(normalized["meta"].get("family_dir"))
    phase_dir = _string(normalized["meta"].get("phase_dir"))
    synth_seed_path = canonicalize_write_path(f"{phase_dir.rstrip('/')}/synth_seed.json") if phase_dir else ""
    controller_heartbeat = build_controller_heartbeat(
        family_id=_string(effective_scaffold.get("family_id")) or _string(normalized["meta"].get("phase_id")).split("_", 1)[0],
        family_dir=family_dir,
        phase_id=_string(normalized["meta"].get("phase_id")),
        phase_title=_string(normalized["meta"].get("phase_title")),
        phase_dir=phase_dir,
        wave_id=_string(current_wave.get("wave_id")),
        execution_mode=_string(normalized.get("execution_mode")),
        objective=_string(current_wave.get("objective")),
        bounded_question=_string(current_wave.get("bounded_question")),
        next_step_posture=_string(normalized.get("next_step_posture")),
        updated_at=_string(normalized["meta"].get("updated_at")) or _string(normalized.get("generated_at")) or now,
        family_charter_path=_string(effective_scaffold.get("family_charter_path")),
        autonomous_seed_path=(canonicalize_write_path(f"{family_dir.rstrip('/')}/autonomous_seed.json") or "") if family_dir else "",
        synth_seed_path=synth_seed_path or "",
        source_refs=[
            {
                "kind": "phase_scaffold",
                "path": canonicalize_write_path(f"{phase_dir.rstrip('/')}/phase_scaffold.json") if phase_dir else "",
                "summary": "Phase scaffold authority for synth alignment and write targets.",
            },
            {
                "kind": "mission_blackboard",
                "path": default_mission_blackboard_path(),
                "summary": "Live mission-board projection for the active controller row.",
            },
        ],
        existing=payload.get("controller_heartbeat") if isinstance(payload.get("controller_heartbeat"), Mapping) else None,
    )
    normalized["controller_heartbeat"] = controller_heartbeat
    normalized["controller_heartbeat_ref"] = controller_heartbeat_ref(
        controller_heartbeat,
        source_path=synth_seed_path or None,
    )
    return normalized


def build_phase_scaffold_payload(
    *,
    phase_id: str,
    phase_number: str,
    phase_title: str,
    phase_dir: str,
    family_dir: str,
    parent: str,
    parent_phase_id: str | None = None,
    parent_phase_dir: str | None = None,
    family_charter_path: str = "",
    baseline_snapshot: Mapping[str, Any] | None = None,
    requested_goal: str = "",
    requested_problem_statement: str = "",
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the phase-scaffold authority packet that declares a subphase's location, source authority, and whiteboard contract before authored synth work begins.
    - Mechanism: Derive the source-authority kind/path, compute the default synth, ledger, and closeout artifact paths, attach the family charter and baseline snapshot, and return one `phase_scaffold_v4` mapping.
    - Reads: Phase identity/title/dir inputs plus the phase-authority helpers in this module.
    - Writes: None.
    - Guarantee: Returns a `kind=phase_scaffold` payload with synth-path contracts, source-authority metadata, baseline snapshot, and pending authoring status.
    - Fails: None.
    - When-needed: Open when scaffolding a new phase or subphase and the caller needs the canonical scaffold payload before writing files.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/observe_apply_contracts.py::build_synth_seed_payload
    """
    source_authority_kind = source_authority_kind_for_phase(parent_phase_id=parent_phase_id)
    source_authority_path = source_authority_path_for_phase(
        family_dir=family_dir,
        parent_phase_dir=parent_phase_dir,
        parent_phase_id=parent_phase_id,
    )
    synth_seed_path = canonicalize_write_path(f"{phase_dir}/synth_seed.json") or ""
    synth_seed_markdown_path = canonicalize_write_path(f"{phase_dir}/synth_seed.md") or ""
    meta_ledger_path = canonicalize_write_path(f"{phase_dir}/meta_ledger.json") or ""
    phase_closeout_path = canonicalize_write_path(f"{phase_dir}/phase_closeout.json") or ""
    archive_root = canonicalize_write_path(f"{phase_dir}/archive") or ""
    return {
        "kind": "phase_scaffold",
        "schema_version": PHASE_SCAFFOLD_VERSION,
        "phase_id": phase_id,
        "phase_number": phase_number,
        "phase_title": phase_title,
        "phase_dir": phase_dir,
        "family_dir": family_dir,
        "parent": parent,
        "parent_phase_id": parent_phase_id,
        "parent_phase_dir": _string(parent_phase_dir) or None,
        "family_charter_path": canonicalize_write_path(family_charter_path) or None,
        "authoring_status": PENDING_SYNTH_AUTHORING,
        "source_authority_kind": source_authority_kind,
        "source_authority_path": source_authority_path,
        "requested_intent": {
            "goal": _string(requested_goal) or None,
            "problem_statement": _string(requested_problem_statement) or None,
        },
        "baseline_snapshot": dict(baseline_snapshot or {}),
        "archive_root": archive_root,
        "wave_protocol_version": WAVE_PROTOCOL_VERSION,
        "whiteboard_contract": {
            "synth_seed_path": synth_seed_path,
            "synth_seed_markdown_path": synth_seed_markdown_path,
            "meta_ledger_path": meta_ledger_path,
            "phase_closeout_path": phase_closeout_path,
            "cycle_root_pattern": "cycle_N/",
            "cycle_group_responses_pattern": "cycle_N/group_responses/",
        },
        "current_cycle": 0,
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
    }


def build_subphase_meta_ledger_payload(phase_scaffold: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Create the empty subphase-local meta ledger that will accumulate compressed cycle memory beneath one phase scaffold.
    - Mechanism: Copy the identifying phase fields from `phase_scaffold` and wrap them in the wave-history ledger contract with an empty entries list.
    - Reads: `phase_scaffold`.
    - Writes: None.
    - Guarantee: Returns a `kind=subphase_meta_ledger` payload with stable phase metadata, archive root, and an empty `entries` list.
    - Fails: None.
    - When-needed: Open when scaffolding a new subphase and the local compressed-memory ledger must be initialized alongside the scaffold.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/observe_apply_contracts.py::build_subphase_close_promotion_entry
    """
    return {
        "phase_id": _string(phase_scaffold.get("phase_id")),
        "phase_number": _string(phase_scaffold.get("phase_number")),
        "phase_title": _string(phase_scaffold.get("phase_title")),
        "phase_dir": _string(phase_scaffold.get("phase_dir")),
        "family_dir": _string(phase_scaffold.get("family_dir")),
        "parent_phase_id": _string(phase_scaffold.get("parent_phase_id")) or None,
        "kind": SUBPHASE_META_LEDGER_KIND,
        "schema_version": SUBPHASE_META_LEDGER_VERSION,
        "wave_protocol_version": _string(phase_scaffold.get("wave_protocol_version")) or WAVE_PROTOCOL_VERSION,
        "archive_root": _string(phase_scaffold.get("archive_root")) or None,
        "purpose": "Compressed wave history for this subphase. One entry per closed wave, plus close-out events when the subphase promotes upward.",
        "entries": [],
    }


def build_synth_seed_payload(
    phase_scaffold: Mapping[str, Any],
    *,
    requested_goal: str = "",
    requested_problem_statement: str = "",
    relevant_files: list[str] | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Create the initial synth-seed JSON authority packet for a new phase scaffold before an authored long-form synth replaces the placeholders.
    - Mechanism: Derive the source-authority metadata from the scaffold, fill in goal/why-now placeholders when explicit text is absent, normalize relevant files, and return the `synth_seed_v5` payload with an initial active wave, one default work item, and empty synthesis memory.
    - Reads: `phase_scaffold`, optional requested goal/problem statement, and optional relevant file paths.
    - Writes: None.
    - Guarantee: Returns a pending-authoring `synth_seed_v5` payload aligned with the scaffold's phase metadata, source authority, and wave protocol.
    - Fails: None.
    - When-needed: Open when a new synth-first phase needs its initial synth JSON scaffold before the authored seed exists.
    - Escalates-to: system/lib/phase_scaffold.py; system/lib/observe_apply_contracts.py::render_synth_seed_markdown
    """
    source_authority_kind = _string(phase_scaffold.get("source_authority_kind")) or source_authority_kind_for_phase(
        parent_phase_id=_string(phase_scaffold.get("parent_phase_id")) or None
    )
    source_authority_path = _string(phase_scaffold.get("source_authority_path"))
    normalized_relevant_files = normalize_relevant_files(relevant_files or [])
    working_set = normalize_working_set(normalized_relevant_files)
    intent = {
        "goal": _string(requested_goal) or synth_goal_placeholder(
            authority_kind=source_authority_kind,
            authority_path=source_authority_path,
        ),
        "why_now": _string(requested_problem_statement) or synth_why_now_placeholder(
            authority_kind=source_authority_kind,
            authority_path=source_authority_path,
        ),
        "raw_seed_anchors": [],
        "raw_seed_refs": [],
        "success_criteria": [],
        "non_goals": [],
    }
    current_wave = normalize_current_wave(
        {
            "status": "planned",
            "groups": phase_scaffold.get("observe_groups") if isinstance(phase_scaffold.get("observe_groups"), list) else [],
        },
        phase_scaffold=phase_scaffold,
        intent=intent,
        working_set=working_set,
        execution_mode="bridge_graph",
        fallback_groups=phase_scaffold.get("observe_groups") if isinstance(phase_scaffold.get("observe_groups"), list) else [],
    )
    orientation = normalize_orientation(
        {},
        intent=intent,
        current_wave=current_wave,
    )
    work_items = normalize_work_items(
        [],
        current_wave=current_wave,
        working_set=working_set,
        execution_mode=current_wave.get("mode") or "bridge_graph",
    )
    controller_heartbeat = build_controller_heartbeat(
        family_id=_string(phase_scaffold.get("family_dir")).split("/")[-1].split(" - ", 1)[0],
        family_dir=_string(phase_scaffold.get("family_dir")),
        phase_id=_string(phase_scaffold.get("phase_id")),
        phase_title=_string(phase_scaffold.get("phase_title")),
        phase_dir=_string(phase_scaffold.get("phase_dir")),
        wave_id=_string(current_wave.get("wave_id")),
        execution_mode=_string(current_wave.get("mode") or "bridge_graph"),
        objective=_string(current_wave.get("objective")),
        bounded_question=_string(current_wave.get("bounded_question")),
        updated_at=_utc_now(),
        family_charter_path=_string(phase_scaffold.get("family_charter_path")),
        autonomous_seed_path=canonicalize_write_path(f"{_string(phase_scaffold.get('family_dir')).rstrip('/')}/autonomous_seed.json") or "",
        synth_seed_path=canonicalize_write_path(f"{_string(phase_scaffold.get('phase_dir')).rstrip('/')}/synth_seed.json") or "",
    )
    return {
        "version": SYNTH_SEED_VERSION,
        "authoring_status": PENDING_SYNTH_AUTHORING,
        "generated_at": _utc_now(),
        "intent": intent,
        "orientation": orientation,
        "continuity_mode": "gate_bounded",
        "execution_mode": current_wave.get("mode") or "bridge_graph",
        "current_wave": current_wave,
        "work_items": work_items,
        "working_set": working_set,
        "assimilation_targets": normalize_assimilation_targets({}, phase_scaffold=phase_scaffold),
        "constraints": list(DEFAULT_SYNTH_CONSTRAINTS),
        "relevant_files": normalized_relevant_files,
        "investigation_threads": [],
        "apply_boundary": dict(DEFAULT_APPLY_BOUNDARY),
        "source_shards": [],
        "synthesis_memory": {
            "confirmed_facts": [],
            "locked_decisions": [],
            "active_risks": [],
        },
        "meta": {
            "phase_id": _string(phase_scaffold.get("phase_id")) or None,
            "phase_number": _string(phase_scaffold.get("phase_number")) or None,
            "phase_title": _string(phase_scaffold.get("phase_title")) or None,
            "phase_dir": _string(phase_scaffold.get("phase_dir")) or None,
            "parent_phase_id": _string(phase_scaffold.get("parent_phase_id")) or None,
            "family_dir": _string(phase_scaffold.get("family_dir")) or None,
            "controller_version": _string(phase_scaffold.get("phase_number") or phase_scaffold.get("phase_id")) or None,
            "controller_phase": "scope",
            "current_cycle": int(phase_scaffold.get("current_cycle") or 0),
            "source_authority_kind": source_authority_kind,
            "source_authority_path": source_authority_path or None,
            "created_at": _utc_now(),
            "updated_at": _utc_now(),
        },
        "controller_heartbeat": controller_heartbeat,
        "controller_heartbeat_ref": controller_heartbeat_ref(
            controller_heartbeat,
            source_path=canonicalize_write_path(f"{_string(phase_scaffold.get('phase_dir')).rstrip('/')}/synth_seed.json") or None,
        ),
    }


def render_synth_seed_markdown(
    payload: Mapping[str, Any],
    *,
    phase_scaffold_path: str | None = None,
    synth_seed_json_path: str | None = None,
) -> str:
    """
    [ACTION]
    - Teleology: Render the markdown projection of a synth-seed JSON payload so humans and navigation surfaces can read the current synth authority without editing the markdown directly.
    - Mechanism: Normalize the synth payload, project frontmatter and sectioned markdown from the normalized fields, and render the final note through `render_markdown_document()`.
    - Reads: `payload`, optional scaffold/json path hints, and the normalization helpers in this module.
    - Writes: None.
    - Guarantee: Returns one markdown string whose body and frontmatter reflect the normalized synth payload.
    - Fails: None.
    - When-needed: Open when synth JSON needs its generated markdown companion for navigation, review, or lifecycle sync.
    - Escalates-to: system/lib/kernel/commands/navigate.py; system/lib/phase_scaffold.py
    """
    normalized = normalize_synth_payload(payload) or {}
    meta = dict(normalized.get("meta") or {})
    intent = dict(normalized.get("intent") or {})
    orientation = normalize_orientation(
        normalized.get("orientation"),
        intent=intent,
        current_wave=normalized.get("current_wave") if isinstance(normalized.get("current_wave"), Mapping) else {},
    )
    relevant_files = normalize_relevant_files(normalized.get("relevant_files"))
    working_set = normalize_working_set(normalized.get("working_set"))
    current_wave = normalize_current_wave(
        normalized.get("current_wave"),
        phase_scaffold=None,
        intent=intent,
        working_set=working_set,
        execution_mode=_string(normalized.get("execution_mode")),
    )
    assimilation_targets = normalize_assimilation_targets(
        normalized.get("assimilation_targets"),
        phase_scaffold=None,
    )
    authoring_status = _string(normalized.get("authoring_status")) or PENDING_SYNTH_AUTHORING
    is_closed = authoring_status.lower() == "closed"
    source_artifact_paths = _dedupe_strings(
        [
            _string(phase_scaffold_path),
            _string(meta.get("source_authority_path")),
            _string(synth_seed_json_path),
        ]
    )
    frontmatter = {
        "phase_id": _string(meta.get("phase_id")) or None,
        "phase_number": _string(meta.get("phase_number")) or None,
        "phase_title": _string(meta.get("phase_title")) or None,
        "phase_dir": _string(meta.get("phase_dir")) or None,
        "family_dir": _string(meta.get("family_dir")) or None,
        "parent_phase_id": _string(meta.get("parent_phase_id")) or None,
        "phase_family_role": "synth_seed",
        "kind": "synth_seed_note",
        "status": authoring_status,
        "source_artifact_paths": source_artifact_paths,
        "generated_from": _string(synth_seed_json_path) or None,
        "source_authority_kind": _string(meta.get("source_authority_kind")) or None,
        "source_authority_path": _string(meta.get("source_authority_path")) or None,
        "focus_status": "closed" if is_closed else "active",
        "focus_label": "CLOSED PHASE" if is_closed else "DEFAULT PHASE",
        "focus_handoff": (
            "Closed synth authority. Resume through phase_closeout.json or open a successor phase instead of editing this packet."
            if is_closed
            else "Generated synth authority. Edit synth_seed.json, then re-sync this markdown mechanically."
        ),
    }
    body_lines = [
        f"# {_string(meta.get('phase_title')) or 'Synth Seed'}",
        "",
        "This file is generated from `synth_seed.json`. Edit JSON first, then run the synth sync command to regenerate this markdown.",
        "",
        "## Authoring status",
        "",
        f"- status: `{authoring_status}`",
        f"- source authority kind: `{_string(meta.get('source_authority_kind')) or 'unknown'}`",
        f"- source authority path: `{_string(meta.get('source_authority_path')) or 'unknown'}`",
        f"- continuity mode: `{_string(normalized.get('continuity_mode')) or 'unspecified'}`",
        f"- execution mode: `{_string(normalized.get('execution_mode')) or 'unspecified'}`",
        "",
        "## Intent",
        "",
        "### Goal",
        "",
        _string(intent.get("goal")) or "PENDING",
        "",
        "### Why now",
        "",
        _string(intent.get("why_now")) or "PENDING",
        "",
        "### Raw-seed anchors",
        "",
    ]
    anchors = [_string(item) for item in intent.get("raw_seed_anchors", []) if _string(item)]
    body_lines.extend([f"- {item}" for item in anchors] or ["- None yet."])
    body_lines.extend(["", "### Raw-seed refs", ""])
    raw_seed_refs = [dict(item) for item in normalize_raw_seed_refs(intent.get("raw_seed_refs", []))]
    if raw_seed_refs:
        for item in raw_seed_refs:
            label = _string(item.get("label") or item.get("target_id")) or "raw_seed_ref"
            target = _string(item.get("target_id"))
            target_kind = _string(item.get("target_kind")) or "manual"
            authority_path = _string(item.get("authority_path"))
            summary = f"- `{_string(item.get('id')) or 'RAW_REF'}` [{target_kind}] - {label}"
            if target:
                summary += f" -> `{target}`"
            body_lines.append(summary)
            if authority_path:
                body_lines.append(f"  - authority: `{authority_path}`")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "### Success criteria", ""])
    criteria = [_string(item) for item in intent.get("success_criteria", []) if _string(item)]
    body_lines.extend([f"- {item}" for item in criteria] or ["- None yet."])
    body_lines.extend(["", "### Non-goals", ""])
    non_goals = [_string(item) for item in intent.get("non_goals", []) if _string(item)]
    body_lines.extend([f"- {item}" for item in non_goals] or ["- None yet."])
    body_lines.extend(["", "## Orientation", ""])
    body_lines.append(f"- house_view: {_string(orientation.get('house_view')) or 'None yet.'}")
    body_lines.append(f"- architectural_posture: {_string(orientation.get('architectural_posture')) or 'None yet.'}")
    body_lines.append(f"- evidence_posture: {_string(orientation.get('evidence_posture')) or 'None yet.'}")
    body_lines.append(f"- pivot_rule: {_string(orientation.get('pivot_rule')) or 'None yet.'}")
    if _string(orientation.get("primary_unknown")):
        body_lines.append(f"- primary_unknown: {_string(orientation.get('primary_unknown'))}")
    controller_heartbeat = (
        normalized.get("controller_heartbeat")
        if isinstance(normalized.get("controller_heartbeat"), Mapping)
        else {}
    )
    body_lines.extend(["", "## Controller heartbeat", ""])
    if controller_heartbeat:
        body_lines.append(
            f"- ref: family=`{_string(controller_heartbeat.get('family_id'))}` / phase=`{_string(controller_heartbeat.get('phase_id'))}` / wave=`{_string(controller_heartbeat.get('wave_id'))}` / mode=`{_string(controller_heartbeat.get('execution_mode'))}`"
        )
        for field in ("system", "problem", "mission", "action", "continuity"):
            body_lines.append(f"- {field}: {_string(controller_heartbeat.get(field)) or 'None yet.'}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Relevant files", ""])
    if relevant_files:
        for item in relevant_files:
            body_lines.append(f"- `{item['path']}` [{item['role']}] - {item['why']}")
            for key in ("priority", "confidence", "notes"):
                if _string(item.get(key)):
                    body_lines.append(f"  - {key}: {_string(item.get(key))}")
            if isinstance(item.get("entry_points"), list) and item.get("entry_points"):
                body_lines.append(f"  - entry_points: {', '.join(f'`{_string(entry)}`' for entry in item.get('entry_points', []))}")
            if isinstance(item.get("symbol_focus"), list) and item.get("symbol_focus"):
                body_lines.append(f"  - symbol_focus: {', '.join(f'`{_string(entry)}`' for entry in item.get('symbol_focus', []))}")
            if isinstance(item.get("related_paths"), list) and item.get("related_paths"):
                body_lines.append(f"  - related_paths: {', '.join(f'`{_string(entry)}`' for entry in item.get('related_paths', []))}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Investigation threads", ""])
    threads = [
        dict(item)
        for item in normalized.get("investigation_threads", [])
        if isinstance(item, Mapping)
    ]
    if threads:
        for item in threads:
            statement = _string(item.get("statement") or item.get("question"))
            status = _string(item.get("status")) or "open"
            body_lines.append(f"- `{_string(item.get('id')) or 'thread'}` [{status}] - {statement or 'No statement.'}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Source shards", ""])
    shards = [
        dict(item)
        for item in normalized.get("source_shards", [])
        if isinstance(item, Mapping)
    ]
    if shards:
        for shard in shards:
            shard_id = _string(shard.get("id")) or "shard"
            statement = _string(shard.get("clarified_statement") or shard.get("question"))
            anchor = _string(shard.get("raw_seed_anchor"))
            ref_ids = _dedupe_strings([_string(item) for item in shard.get("raw_seed_ref_ids", [])])
            body_lines.append(f"- `{shard_id}` - {statement or 'No clarified statement.'}")
            if anchor:
                body_lines.append(f"  - anchor: {anchor}")
            if ref_ids:
                body_lines.append(f"  - raw_seed_ref_ids: {', '.join(f'`{item}`' for item in ref_ids)}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Wave protocol", ""])
    body_lines.append(f"- wave_id: `{_string(current_wave.get('wave_id')) or 'wave_001'}`")
    body_lines.append(f"- mode: `{_string(current_wave.get('mode')) or _string(normalized.get('execution_mode')) or 'direct_local'}`")
    body_lines.append(f"- stage_kind: `{_string(current_wave.get('stage_kind')) or 'problem_space'}`")
    body_lines.append(f"- status: `{_string(current_wave.get('status')) or 'planned'}`")
    if _string(current_wave.get("track_id")):
        body_lines.append(f"- track_id: `{_string(current_wave.get('track_id'))}`")
    checkpoint_policy = dict(current_wave.get("checkpoint_policy") or {})
    body_lines.append(
        f"- checkpoint_policy: rubric=`{_string(checkpoint_policy.get('rubric_id')) or 'builtin:problem_space'}` / "
        f"clarify_depth=`{_int(checkpoint_policy.get('clarify_depth'), 0)}` / "
        f"max_clarify_depth=`{_int(checkpoint_policy.get('max_clarify_depth'), 2)}`"
    )
    if isinstance(current_wave.get("spawned_wave_ids"), list) and current_wave.get("spawned_wave_ids"):
        body_lines.append(
            f"- spawned_wave_ids: {', '.join(f'`{_string(item)}`' for item in current_wave.get('spawned_wave_ids', []) if _string(item))}"
        )
    if _string(current_wave.get("carry_forward_posture")):
        body_lines.append(f"- carry_forward_posture: {_string(current_wave.get('carry_forward_posture'))}")
    body_lines.extend(["", "### Objective", "", _string(current_wave.get("objective")) or "PENDING", "", "### Bounded question", "", _string(current_wave.get("bounded_question")) or "PENDING", "", "### Success signals", ""])
    success_signals = [_string(item) for item in current_wave.get("success_signals", []) if _string(item)]
    body_lines.extend([f"- {item}" for item in success_signals] or ["- None yet."])
    body_lines.extend(["", "### Target paths", ""])
    target_paths = [_string(item) for item in current_wave.get("target_paths", []) if _string(item)]
    body_lines.extend([f"- `{item}`" for item in target_paths] or ["- None yet."])
    depends_on = [_string(item) for item in current_wave.get("depends_on", []) if _string(item)]
    if depends_on:
        body_lines.extend(["", "### Depends on", ""])
        body_lines.extend([f"- `{item}`" for item in depends_on])
    groups = _normalize_wave_groups(current_wave.get("groups"))
    if groups:
        body_lines.extend(["", "### Bridge/subagent groups", ""])
        for group in groups:
            body_lines.append(f"- {group.get('title') or group.get('label') or 'group'}")
            if _string(group.get("answer")):
                body_lines.append(f"  - question: {_string(group.get('answer'))}")
    work_items = normalize_work_items(
        normalized.get("work_items"),
        current_wave=current_wave,
        working_set=working_set,
        execution_mode=_string(normalized.get("execution_mode")),
    )
    body_lines.extend(["", "## Work items", ""])
    if work_items:
        for item in work_items:
            title = _string(item.get("title")) or _string(item.get("work_item_id")) or "work_item"
            body_lines.append(f"- `{_string(item.get('work_item_id')) or 'work_item'}` [{_string(item.get('status')) or 'planned'}] - {title}")
            if _string(item.get("intent")):
                body_lines.append(f"  - intent: {_string(item.get('intent'))}")
            if _string(item.get("mode_hint")):
                body_lines.append(f"  - mode_hint: `{_string(item.get('mode_hint'))}`")
            if isinstance(item.get("paths"), list) and item.get("paths"):
                body_lines.append(f"  - paths: {', '.join(f'`{_string(path)}`' for path in item.get('paths', []))}")
            if isinstance(item.get("depends_on"), list) and item.get("depends_on"):
                body_lines.append(f"  - depends_on: {', '.join(f'`{_string(dep)}`' for dep in item.get('depends_on', []))}")
            if isinstance(item.get("success_signals"), list) and item.get("success_signals"):
                body_lines.append(f"  - success_signals: {', '.join(item.get('success_signals', []))}")
            if isinstance(item.get("spawned_wave_ids"), list) and item.get("spawned_wave_ids"):
                body_lines.append(f"  - spawned_wave_ids: {', '.join(f'`{_string(wave_id)}`' for wave_id in item.get('spawned_wave_ids', []))}")
            if _string(item.get("notes")):
                body_lines.append(f"  - notes: {_string(item.get('notes'))}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Constraints", ""])
    constraints = [_string(item) for item in normalized.get("constraints", []) if _string(item)]
    body_lines.extend([f"- {item}" for item in constraints] or ["- None yet."])
    body_lines.extend(["", "## Working set", ""])
    if working_set:
        for item in working_set:
            body_lines.append(f"- `{item['path']}` [{item['role']}] - {item['why']}")
            for key in ("priority", "confidence", "notes"):
                if _string(item.get(key)):
                    body_lines.append(f"  - {key}: {_string(item.get(key))}")
            if isinstance(item.get("entry_points"), list) and item.get("entry_points"):
                body_lines.append(f"  - entry_points: {', '.join(f'`{_string(entry)}`' for entry in item.get('entry_points', []))}")
            if isinstance(item.get("symbol_focus"), list) and item.get("symbol_focus"):
                body_lines.append(f"  - symbol_focus: {', '.join(f'`{_string(entry)}`' for entry in item.get('symbol_focus', []))}")
    else:
        body_lines.append("- None yet.")
    body_lines.extend(["", "## Assimilation targets", ""])
    for key in ("archive_root", "ledger_path", "delta_path", "continuation_summary_path", "observe_plan_path", "resume_contract_path"):
        value = _string(assimilation_targets.get(key))
        if value:
            body_lines.append(f"- {key}: `{value}`")
    artifact_paths = [_string(item) for item in assimilation_targets.get("artifact_paths", []) if _string(item)]
    if artifact_paths:
        body_lines.append("- artifact_paths:")
        body_lines.extend([f"  - `{item}`" for item in artifact_paths])
    progress_state = normalized.get("progress_state")
    if isinstance(progress_state, Mapping):
        body_lines.extend(["", "## Progress", ""])
        for key in ("total_objectives", "completed_objectives", "current_focus", "last_wave_outcome"):
            value = progress_state.get(key)
            token = _string(value) if not isinstance(value, int) else str(value)
            if token:
                body_lines.append(f"- {key}: {token}")
    outstanding_questions = [
        dict(item)
        for item in normalized.get("outstanding_questions", [])
        if isinstance(item, Mapping)
    ]
    if outstanding_questions:
        body_lines.extend(["", "## Outstanding questions", ""])
        for item in outstanding_questions:
            body_lines.append(f"- `{_string(item.get('id')) or 'question'}` [{_string(item.get('status')) or 'open'}] - {_string(item.get('question'))}")
    synthesis_memory = normalize_synthesis_memory(normalized.get("synthesis_memory"))
    body_lines.extend(["", "## Synthesis memory", ""])
    confirmed_facts = [dict(item) for item in synthesis_memory.get("confirmed_facts", []) if isinstance(item, Mapping)]
    if confirmed_facts:
        body_lines.append("")
        body_lines.append("### Confirmed facts")
        body_lines.append("")
        for item in confirmed_facts:
            body_lines.append(f"- `{_string(item.get('fact_id')) or 'fact'}` - {_string(item.get('fact'))}")
    locked_decisions = [dict(item) for item in synthesis_memory.get("locked_decisions", []) if isinstance(item, Mapping)]
    if locked_decisions:
        body_lines.append("")
        body_lines.append("### Locked decisions")
        body_lines.append("")
        for item in locked_decisions:
            body_lines.append(f"- `{_string(item.get('decision_id')) or 'decision'}` - {_string(item.get('decision'))}")
    active_risks = [dict(item) for item in synthesis_memory.get("active_risks", []) if isinstance(item, Mapping)]
    if active_risks:
        body_lines.append("")
        body_lines.append("### Active risks")
        body_lines.append("")
        for item in active_risks:
            body_lines.append(f"- `{_string(item.get('risk_id')) or 'risk'}` [{_string(item.get('status')) or 'open'}] - {_string(item.get('risk'))}")
    if not confirmed_facts and not locked_decisions and not active_risks:
        body_lines.append("- None yet.")
    track_catalog = normalize_track_catalog(normalized.get("track_catalog"))
    if track_catalog:
        body_lines.extend(["", "## Track catalog", ""])
        for item in track_catalog:
            line = f"- `{_string(item.get('track_id'))}`"
            if _string(item.get("label")):
                line += f" - {_string(item.get('label'))}"
            body_lines.append(line)
    apply_boundary = dict(normalized.get("apply_boundary") or {})
    body_lines.extend(
        [
            "",
            "## Apply boundary",
            "",
            f"- review_required: `{bool(apply_boundary.get('review_required', True))}`",
            f"- apply_via: `{_string(apply_boundary.get('apply_via')) or 'kernel.py --apply'}`",
            f"- mutator: `{_string(apply_boundary.get('mutator')) or 'kernel'}`",
            "",
            "## Authority",
            "",
            f"- synth json: `{_string(synth_seed_json_path) or 'synth_seed.json'}`",
            f"- phase scaffold: `{_string(phase_scaffold_path) or 'phase_scaffold.json'}`",
            f"- synth standard: `{OBSERVE_APPLY_STANDARD_PATHS['synth_seed']}`",
            f"- authority index: `{OBSERVE_APPLY_AUTHORITY_INDEX_PATH}`",
            "",
        ]
    )
    return render_markdown_document(frontmatter, "\n".join(body_lines))


def validate_synth_seed_payload(
    payload: Mapping[str, Any],
    *,
    phase_scaffold: Mapping[str, Any] | None = None,
    allow_pending: bool = False,
) -> list[str]:
    """
    [ACTION]
    - Teleology: Validate a synth-seed payload against the current synth-first contract before sync, navigation, or lifecycle closure proceeds.
    - Mechanism: Normalize the payload, check version/intent/traceability/relevant-file/meta invariants, optionally enforce authored richness when `allow_pending` is false, and accumulate contract errors.
    - Reads: `payload`, optional `phase_scaffold`, `allow_pending`, and the normalization helpers/constants in this module.
    - Writes: None.
    - Guarantee: Returns a list of human-readable validation errors; an empty list means the payload satisfies the checked contract.
    - Fails: None by raising for contract issues; violations are returned as list entries.
    - When-needed: Open when a synth JSON must be accepted or rejected before markdown sync, observe enrichment, or phase closure.
    - Escalates-to: system/lib/kernel/commands/navigate.py; system/lib/synth_seed_delta_merge.py
    - Navigation-group: kernel_lib
    """
    normalized = normalize_synth_payload(payload, phase_scaffold=phase_scaffold)
    if normalized is None:
        return ["synth seed must be a JSON object."]
    errors: list[str] = []
    if _string(normalized.get("version")) != SYNTH_SEED_VERSION:
        errors.append(f"version must be `{SYNTH_SEED_VERSION}`.")
    authoring_status = _string(normalized.get("authoring_status"))
    if not authoring_status:
        errors.append("authoring_status is required.")
    intent = normalized.get("intent")
    if not isinstance(intent, Mapping):
        errors.append("intent must be an object.")
        return errors
    goal = _string(intent.get("goal"))
    why_now = _string(intent.get("why_now"))
    if not goal:
        errors.append("intent.goal is required.")
    if not why_now:
        errors.append("intent.why_now is required.")
    if not isinstance(intent.get("raw_seed_anchors"), list):
        errors.append("intent.raw_seed_anchors must be a list.")
    if not isinstance(intent.get("raw_seed_refs", []), list):
        errors.append("intent.raw_seed_refs must be a list.")
    concept_refs_raw = intent.get("concept_refs", [])
    if concept_refs_raw is not None and not isinstance(concept_refs_raw, list):
        errors.append("intent.concept_refs must be a list when present.")
    elif isinstance(concept_refs_raw, list):
        for idx, item in enumerate(concept_refs_raw, start=1):
            if item is not None and not isinstance(item, Mapping):
                errors.append(f"intent.concept_refs[{idx}] must be an object.")
    extracted_ids_raw = intent.get("extracted_shard_ids", [])
    if extracted_ids_raw is not None and not isinstance(extracted_ids_raw, list):
        errors.append("intent.extracted_shard_ids must be a list when present.")
    concept_refs = normalize_intent_concept_refs(concept_refs_raw if isinstance(concept_refs_raw, list) else [])
    for idx, cref in enumerate(concept_refs, start=1):
        cid = _string(cref.get("concept_id"))
        if not is_valid_synth_concept_id(cid):
            errors.append(f"intent.concept_refs[{idx}].concept_id must match con_* doctrine id pattern (got {cid!r}).")
    extracted_shard_ids = normalize_intent_extracted_shard_ids(
        extracted_ids_raw if isinstance(extracted_ids_raw, list) else []
    )
    for idx, sid in enumerate(extracted_shard_ids, start=1):
        if not _string(sid):
            errors.append(f"intent.extracted_shard_ids[{idx}] must be a non-empty string.")
    if not isinstance(intent.get("success_criteria"), list):
        errors.append("intent.success_criteria must be a list.")
    if not isinstance(intent.get("non_goals"), list):
        errors.append("intent.non_goals must be a list.")
    orientation = normalized.get("orientation")
    if not isinstance(orientation, Mapping):
        errors.append("orientation must be an object.")
    else:
        for key in ("house_view", "architectural_posture", "evidence_posture", "pivot_rule"):
            if not _string(orientation.get(key)):
                errors.append(f"orientation.{key} is required.")
    execution_mode = _string(normalized.get("execution_mode"))
    if execution_mode not in EXECUTION_MODES:
        errors.append(f"execution_mode must be one of {sorted(EXECUTION_MODES)}.")
    current_wave = normalized.get("current_wave")
    if not isinstance(current_wave, Mapping):
        errors.append("current_wave must be an object.")
    else:
        for key in ("wave_id", "objective", "mode", "bounded_question", "status"):
            if not _string(current_wave.get(key)):
                errors.append(f"current_wave.{key} is required.")
        if _string(current_wave.get("mode")) not in EXECUTION_MODES:
            errors.append(f"current_wave.mode must be one of {sorted(EXECUTION_MODES)}.")
        if _string(current_wave.get("stage_kind")) not in PHASE_STEP_STAGE_KINDS:
            errors.append(f"current_wave.stage_kind must be one of {sorted(PHASE_STEP_STAGE_KINDS)}.")
        for key in ("success_signals", "target_paths", "depends_on"):
            if not isinstance(current_wave.get(key), list):
                errors.append(f"current_wave.{key} must be a list.")
        if not isinstance(current_wave.get("spawned_wave_ids"), list):
            errors.append("current_wave.spawned_wave_ids must be a list.")
        checkpoint_policy = current_wave.get("checkpoint_policy")
        if not isinstance(checkpoint_policy, Mapping):
            errors.append("current_wave.checkpoint_policy must be an object.")
        else:
            if not _string(checkpoint_policy.get("rubric_id")):
                errors.append("current_wave.checkpoint_policy.rubric_id is required.")
            if _int(checkpoint_policy.get("max_clarify_depth"), 0) < 1:
                errors.append("current_wave.checkpoint_policy.max_clarify_depth must be >= 1.")
            if _int(checkpoint_policy.get("clarify_depth"), -1) < 0:
                errors.append("current_wave.checkpoint_policy.clarify_depth must be >= 0.")
        if isinstance(current_wave.get("groups"), list):
            for idx, group in enumerate(current_wave.get("groups", []), start=1):
                if not isinstance(group, Mapping):
                    errors.append(f"current_wave.groups[{idx}] must be an object.")
                    continue
                if not _string(group.get("title") or group.get("label") or group.get("group_id")):
                    errors.append(f"current_wave.groups[{idx}] must declare title, label, or group_id.")
    working_set = normalized.get("working_set")
    if not isinstance(working_set, list):
        errors.append("working_set must be a list.")
    else:
        for index, item in enumerate(working_set, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"working_set[{index}] must be an object.")
                continue
            if not canonicalize_write_path(_string(item.get("path"))):
                errors.append(f"working_set[{index}].path is required.")
            if not _string(item.get("role")):
                errors.append(f"working_set[{index}].role is required.")
            if not _string(item.get("why")):
                errors.append(f"working_set[{index}].why is required.")
    assimilation_targets = normalized.get("assimilation_targets")
    if not isinstance(assimilation_targets, Mapping):
        errors.append("assimilation_targets must be an object.")
    else:
        for key in ("archive_root", "ledger_path", "delta_path", "continuation_summary_path"):
            if not canonicalize_write_path(_string(assimilation_targets.get(key))):
                errors.append(f"assimilation_targets.{key} is required.")
        artifact_paths = assimilation_targets.get("artifact_paths", [])
        if artifact_paths is not None and not isinstance(artifact_paths, list):
            errors.append("assimilation_targets.artifact_paths must be a list.")
    work_items = normalized.get("work_items")
    if not isinstance(work_items, list):
        errors.append("work_items must be a list.")
    else:
        for index, item in enumerate(work_items, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"work_items[{index}] must be an object.")
                continue
            for key in ("work_item_id", "title", "status", "intent"):
                if not _string(item.get(key)):
                    errors.append(f"work_items[{index}].{key} is required.")
            mode_hint = _string(item.get("mode_hint"))
            if mode_hint and mode_hint not in EXECUTION_MODES:
                errors.append(f"work_items[{index}].mode_hint must be one of {sorted(EXECUTION_MODES)} when present.")
            for key in ("paths", "depends_on", "success_signals", "spawned_wave_ids"):
                if not isinstance(item.get(key), list):
                    errors.append(f"work_items[{index}].{key} must be a list.")
    synthesis_memory = normalized.get("synthesis_memory")
    if not isinstance(synthesis_memory, Mapping):
        errors.append("synthesis_memory must be an object.")
    else:
        for key in ("confirmed_facts", "locked_decisions", "active_risks"):
            if not isinstance(synthesis_memory.get(key), list):
                errors.append(f"synthesis_memory.{key} must be a list.")
    track_catalog = normalized.get("track_catalog")
    if track_catalog is not None and not isinstance(track_catalog, list):
        errors.append("track_catalog must be a list when present.")
    if not allow_pending:
        if authoring_status == PENDING_SYNTH_AUTHORING:
            errors.append("authoring_status must not remain pending_initial_synth_authoring once synced.")
        if len(goal) < 160:
            errors.append("intent.goal must be long-form and materially richer than a one-line placeholder.")
        if len(why_now) < 100:
            errors.append("intent.why_now must explain why this subphase is the right next move.")
        anchors = [_string(item) for item in intent.get("raw_seed_anchors", []) if _string(item)]
        raw_seed_refs = normalize_raw_seed_refs(intent.get("raw_seed_refs", []))
        has_trace = bool(anchors or raw_seed_refs or concept_refs or extracted_shard_ids)
        if not has_trace:
            errors.append(
                "intent must include at least one of: raw_seed_anchors, raw_seed_refs, concept_refs, or extracted_shard_ids."
            )
        criteria = [_string(item) for item in intent.get("success_criteria", []) if _string(item)]
        if not criteria:
            errors.append("intent.success_criteria must contain at least one concrete criterion.")
        relevant_files = normalize_relevant_files(normalized.get("relevant_files"))
        if not relevant_files:
            errors.append("relevant_files must contain at least one structured file entry once the synth is synced.")
        if isinstance(working_set, list) and not working_set:
            errors.append("working_set must contain at least one structured entry once the synth is synced.")
        if isinstance(work_items, list) and not work_items:
            errors.append("work_items must contain at least one structured work item once the synth is synced.")
    relevant_files = normalized.get("relevant_files")
    if not isinstance(relevant_files, list):
        errors.append("relevant_files must be a list.")
    else:
        for index, item in enumerate(relevant_files, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"relevant_files[{index}] must be an object.")
                continue
            if not canonicalize_write_path(_string(item.get("path"))):
                errors.append(f"relevant_files[{index}].path is required.")
            if not _string(item.get("role")):
                errors.append(f"relevant_files[{index}].role is required.")
            if not _string(item.get("why")):
                errors.append(f"relevant_files[{index}].why is required.")
    source_shards = normalized.get("source_shards")
    if not isinstance(source_shards, list):
        errors.append("source_shards must be a list.")
    else:
        for index, item in enumerate(source_shards, start=1):
            if not isinstance(item, Mapping):
                errors.append(f"source_shards[{index}] must be an object.")
                continue
            ref_ids = item.get("raw_seed_ref_ids", [])
            if ref_ids is not None and not isinstance(ref_ids, list):
                errors.append(f"source_shards[{index}].raw_seed_ref_ids must be a list when present.")
    meta = normalized.get("meta")
    if not isinstance(meta, Mapping):
        errors.append("meta must be an object.")
    else:
        for key in ("phase_id", "phase_number", "phase_title", "phase_dir", "family_dir", "controller_version", "controller_phase"):
            if not _string(meta.get(key)):
                errors.append(f"meta.{key} is required.")
        if phase_scaffold:
            for key in ("phase_id", "phase_number", "phase_title", "phase_dir", "family_dir"):
                expected = _string(phase_scaffold.get(key))
                observed = _string(meta.get(key))
                if expected and observed and expected != observed:
                    errors.append(f"meta.{key} must match phase_scaffold.json ({expected}).")
        if not _string(meta.get("source_authority_kind")):
            errors.append("meta.source_authority_kind is required.")
        if not _string(meta.get("source_authority_path")):
            errors.append("meta.source_authority_path is required.")
    return errors


def _closeout_done_fallbacks(synth_seed: Mapping[str, Any]) -> list[str]:
    current_wave = dict(synth_seed.get("current_wave") or {})
    work_items = normalize_work_items(
        synth_seed.get("work_items"),
        current_wave=current_wave,
        working_set=normalize_working_set(synth_seed.get("working_set")),
        execution_mode=_string(synth_seed.get("execution_mode")),
    )
    items = [
        _string(item.get("title") or item.get("intent"))
        for item in work_items
        if _string(item.get("status")).strip().lower() in {"completed", "done", "closed", "assimilated"}
    ]
    if _string(current_wave.get("status")).strip().lower() in {"completed", "done", "closed", "assimilated"}:
        items.append(_string(current_wave.get("objective")))
    return _dedupe_strings([item for item in items if item])


def _closeout_learning_fallbacks(synth_seed: Mapping[str, Any]) -> list[str]:
    synthesis_memory = normalize_synthesis_memory(synth_seed.get("synthesis_memory"))
    locked_decisions = [
        _string(item.get("decision"))
        for item in synthesis_memory.get("locked_decisions", [])
        if isinstance(item, Mapping) and _string(item.get("decision"))
    ]
    confirmed_facts = [
        _string(item.get("fact"))
        for item in synthesis_memory.get("confirmed_facts", [])
        if isinstance(item, Mapping) and _string(item.get("fact"))
    ]
    return _dedupe_strings([*locked_decisions, *confirmed_facts])


def _closeout_remaining_work_fallbacks(synth_seed: Mapping[str, Any]) -> list[str]:
    outstanding_questions = [
        _string(item.get("question"))
        for item in (synth_seed.get("outstanding_questions") or [])
        if isinstance(item, Mapping) and _string(item.get("status")).strip().lower() not in {"resolved", "closed", "done"}
    ]
    next_step_posture = _string(synth_seed.get("next_step_posture"))
    items = outstanding_questions[:]
    if next_step_posture:
        items.append(next_step_posture)
    return _dedupe_strings(items)


def _closeout_shard_fallbacks(synth_seed: Mapping[str, Any]) -> list[str]:
    shards = normalize_source_shards(synth_seed.get("source_shards"))
    return _dedupe_strings(
        [
            _string(
                shard.get("extracted_shard_id")
                or shard.get("id")
                or shard.get("raw_seed_anchor")
                or shard.get("clarified_statement")
            )
            for shard in shards
            if isinstance(shard, Mapping)
        ]
    )


def build_subphase_close_promotion_entry(
    phase_scaffold: Mapping[str, Any],
    synth_seed: Mapping[str, Any],
    subphase_meta_ledger: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the family- or parent-ledger promotion entry that records a subphase closure in compressed, post-hoc form.
    - Mechanism: Summarize what was done, learned, and addressed from the subphase ledger entries, fold in relevant files from the synth seed, and emit one `subphase_closed` ledger entry.
    - Reads: `phase_scaffold`, `synth_seed`, and `subphase_meta_ledger`.
    - Writes: None.
    - Guarantee: Returns a dict with `action=subphase_closed`, summary text, compact done/learned/shard lists, and pointers back to the source subphase artifacts.
    - Fails: None.
    - When-needed: Open when a subphase is ready to be promoted into a parent or family meta ledger instead of remaining only in local phase artifacts.
    - Escalates-to: system/lib/kernel/commands/navigate.py; system/lib/observe_apply_contracts.py::build_subphase_meta_ledger_payload
    """
    phase_id = _string(phase_scaffold.get("phase_id"))
    phase_number = _string(phase_scaffold.get("phase_number"))
    phase_title = _string(phase_scaffold.get("phase_title"))
    relevant_files = normalize_relevant_files(synth_seed.get("relevant_files"))
    entries = [
        dict(item)
        for item in subphase_meta_ledger.get("entries", [])
        if isinstance(item, Mapping)
    ]
    what_was_done = _dedupe_strings(
        [
            _string(item)
            for entry in entries
            for item in entry.get("what_was_done", [])
            if _string(item)
        ]
    )
    what_was_learned = _dedupe_strings(
        [
            _string(item)
            for entry in entries
            for item in entry.get("what_was_learned", [])
            if _string(item)
        ]
    )
    shards_addressed = _dedupe_strings(
        [
            _string(item)
            for entry in entries
            for item in entry.get("shards_addressed", [])
            if _string(item)
        ]
    )
    what_was_done = _dedupe_strings([*what_was_done, *_closeout_done_fallbacks(synth_seed)])[:8]
    what_was_learned = _dedupe_strings([*what_was_learned, *_closeout_learning_fallbacks(synth_seed)])[:8]
    shards_addressed = _dedupe_strings([*shards_addressed, *_closeout_shard_fallbacks(synth_seed)])
    summary = (
        f"Closed subphase {phase_number or phase_id}: "
        f"{phase_title or 'Untitled subphase'}."
    )
    if entries:
        summary += f" Captured {len(entries)} cycle ledger entr{'y' if len(entries) == 1 else 'ies'}."
    return {
        "sub_phase": phase_number or phase_id,
        "entry_id": f"{phase_id}_closed_{_utc_date()}_{_string(_utc_now()).replace(':', '').replace('-', '')[:15]}",
        "timestamp": _utc_now(),
        "action": "subphase_closed",
        "summary": summary,
        "what_was_done": what_was_done,
        "what_was_learned": what_was_learned,
        "shards_addressed": shards_addressed,
        "files_relevant_post_hoc": relevant_files,
        "source_subphase_dir": _string(phase_scaffold.get("phase_dir")),
        "source_subphase_meta_ledger": canonicalize_write_path(f"{_string(phase_scaffold.get('phase_dir'))}/meta_ledger.json") or "",
    }


def build_phase_closeout_payload(
    phase_scaffold: Mapping[str, Any],
    synth_seed: Mapping[str, Any],
    subphase_meta_ledger: Mapping[str, Any],
    *,
    promotion_target_path: str,
    promotion_entry: Mapping[str, Any],
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the standalone subphase close-out artifact that records why the packet is complete.
    - Mechanism: Fold the synth success criteria, local ledger history, and promotion event into one `phase_closeout_v1` payload.
    - Reads: `phase_scaffold`, `synth_seed`, `subphase_meta_ledger`, and the already-built promotion entry.
    - Writes: None.
    - Guarantee: Returns a dict suitable for `phase_closeout.json`.
    - Fails: None.
    - When-needed: Open when `cmd_close_phase` needs an explicit file-presence completion record instead of relying only on scaffold status.
    - Escalates-to: system/lib/kernel/commands/navigate.py::cmd_close_phase; docs/synth_first_scaffold_contract.md
    """
    normalized_synth = normalize_synth_payload(synth_seed, phase_scaffold=phase_scaffold) or dict(synth_seed)
    relevant_files = normalize_relevant_files(normalized_synth.get("relevant_files"))
    ledger_entries = [
        dict(item)
        for item in subphase_meta_ledger.get("entries", [])
        if isinstance(item, Mapping)
    ]
    closeout_criteria = [
        {
            "criterion": "Promotion entry recorded in the next governing meta ledger.",
            "status": "satisfied",
        },
        {
            "criterion": "Local subphase ledger reflects the finished work and its lessons.",
            "status": "satisfied",
        },
    ]
    for criterion in [
        _string(item)
        for item in ((normalized_synth.get("intent") or {}).get("success_criteria") or [])
        if _string(item)
    ]:
        closeout_criteria.append({"criterion": criterion, "status": "satisfied"})
    completed_work = _dedupe_strings(
        [
            _string(item)
            for entry in ledger_entries
            for item in entry.get("what_was_done", [])
            if _string(item)
        ]
    )
    completed_work = _dedupe_strings([*completed_work, *_closeout_done_fallbacks(normalized_synth)])
    key_learnings = _dedupe_strings(
        [
            _string(item)
            for entry in ledger_entries
            for item in entry.get("what_was_learned", [])
            if _string(item)
        ]
    )
    key_learnings = _dedupe_strings([*key_learnings, *_closeout_learning_fallbacks(normalized_synth)])
    remaining_follow_on_work = _dedupe_strings(
        [
            _string(item)
            for entry in ledger_entries
            for item in entry.get("open_questions_remaining", [])
            if _string(item)
        ]
    )
    remaining_follow_on_work = _dedupe_strings(
        [*remaining_follow_on_work, *_closeout_remaining_work_fallbacks(normalized_synth)]
    )
    phase_dir = _string(phase_scaffold.get("phase_dir"))
    whiteboard_contract = (
        dict(phase_scaffold.get("whiteboard_contract"))
        if isinstance(phase_scaffold.get("whiteboard_contract"), Mapping)
        else {}
    )
    return {
        "kind": "phase_closeout",
        "schema_version": PHASE_CLOSEOUT_VERSION,
        "status": "closed",
        "phase_id": _string(phase_scaffold.get("phase_id")),
        "phase_number": _string(phase_scaffold.get("phase_number")),
        "phase_title": _string(phase_scaffold.get("phase_title")),
        "phase_dir": phase_dir,
        "family_dir": _string(phase_scaffold.get("family_dir")),
        "parent_phase_id": _string(phase_scaffold.get("parent_phase_id")) or None,
        "closed_at": _string(promotion_entry.get("timestamp")) or _utc_now(),
        "summary": _string(promotion_entry.get("summary"))
        or f"Closed subphase {_string(phase_scaffold.get('phase_number')) or _string(phase_scaffold.get('phase_id'))}.",
        "closeout_criteria": closeout_criteria,
        "completed_work": completed_work,
        "key_learnings": key_learnings,
        "remaining_follow_on_work": remaining_follow_on_work,
        "relevant_files": relevant_files,
        "evidence_artifacts": {
            "phase_scaffold_path": canonicalize_write_path(f"{phase_dir}/phase_scaffold.json") or "",
            "synth_seed_path": _string(whiteboard_contract.get("synth_seed_path"))
            or canonicalize_write_path(f"{phase_dir}/synth_seed.json")
            or "",
            "meta_ledger_path": _string(whiteboard_contract.get("meta_ledger_path"))
            or canonicalize_write_path(f"{phase_dir}/meta_ledger.json")
            or "",
            "promotion_target_path": canonicalize_write_path(promotion_target_path) or promotion_target_path,
            "promotion_entry_id": _string(promotion_entry.get("entry_id")),
            "companion_paths": _dedupe_strings(
                [
                    _string(whiteboard_contract.get("synth_seed_markdown_path")),
                    _string(whiteboard_contract.get("phase_closeout_path")),
                ]
            ),
        },
    }


def canonical_json_text(payload: Mapping[str, Any]) -> str:
    """[ACTION]
    - Teleology: Serialize a mapping to the canonical two-space-indented JSON string used across all observe-apply artifacts.
    - Guarantee: Returns a UTF-8-safe, newline-terminated JSON string for the given payload.
    - Fails: None for well-formed mappings; raises if `json.dumps` cannot serialize the value.
    """
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
