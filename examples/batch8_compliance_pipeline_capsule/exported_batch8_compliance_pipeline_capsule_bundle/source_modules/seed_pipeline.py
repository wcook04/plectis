#!/usr/bin/env python3
"""
seed_pipeline.py — End-to-end seed pipeline runner.

The active hard-cut loop is synth-first:
authored synth_seed → compile observe_plan → execute via bridge → process results →
update subphase meta ledger → repeat until a review/apply gate or explicit close.

Usage:
    # Initialize pipeline from an authored subphase synth seed
    python3 seed_pipeline.py --init --phase-dir "<private-obsidian-root>/.../08.1 - ..."

    # Run the next step in the pipeline
    python3 seed_pipeline.py --step --state pipeline_state.json

    # Run the full loop until a gate (default: stops before apply)
    python3 seed_pipeline.py --run --state pipeline_state.json

    # Run with bridge dispatch enabled
    python3 seed_pipeline.py --run --state pipeline_state.json --bridge --provider chatgpt

    # Show current state
    python3 seed_pipeline.py --status --state pipeline_state.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import threading
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from system.lib.repo_env import maybe_reexec_into_repo_python

REPO_ROOT = Path(__file__).resolve().parent
if __name__ == "__main__":
    maybe_reexec_into_repo_python(REPO_ROOT)

from pipeline_control import normalize_launch_profile, pipeline_runtime_config
from system.lib.codex_paths import canonicalize_write_path
from system.lib.dispatch_policy import provider_ceiling_for_provider
from system.lib.json_payloads import json_candidate_blocks
from system.lib.observe_apply_contracts import (
    PENDING_SYNTH_AUTHORING,
    normalize_synth_payload,
    render_observe_apply_standards_prompt,
    resolve_observe_apply_standards_bundle,
    synth_goal_text,
    synth_relevant_file_paths,
    synth_success_criteria_text,
)
from system.lib.observe_runtime import (
    append_jsonl,
    observe_cycle_timeline_path,
    observe_runtime_policy,
    resolve_effective_workers,
    summarize_degraded_group_diagnostics,
)
from system.lib.pipeline_recovery import maybe_capture_pre_save_snapshot
from system.lib.raw_seed_atomization import (
    build_atomization_redrive_plan,
    import_atomization_session_results,
)
from system.lib.synth_seed_delta_merge import apply_synth_seed_delta
from system.lib.seed_pipeline_controller import (
    active_task_dag_layer,
    active_task_dag_shard_ids,
    advance_controller_after_results,
    analytics_report,
    constrain_shard_candidates,
    controller_gate_active,
    curate_backlog,
    ensure_controller_state,
    ensure_task_dag,
    known_relevant_file_paths,
    load_task_dag,
    load_synth_seed,
    observe_brief,
    resolve_active_task,
    controller_version_for_state,
    write_controller_artifacts,
    write_focus_directive,
)

CANONICAL_SHARD_STATUSES = {
    "pending",
    "selected",
    "in_progress",
    "partially_addressed",
    "addressed",
    "resolved",
    "superseded",
    "completed",
}
TERMINAL_SHARD_STATUSES = {"completed", "superseded", "addressed", "resolved"}
STATUS_SELECTION_SCORES = {
    "pending": 6,
    "selected": 4,
    "in_progress": 3,
    "partially_addressed": 2,
    "addressed": 0,
    "resolved": 0,
    "superseded": 0,
    "completed": 0,
}
SYNTHESIS_REQUIRED_FIELDS = (
    "priority_action",
    "ordered_sequence",
    "shard_status_updates",
    "new_shards",
)
DEGRADED_GROUP_STATES = {
    "quality_error",
    "error",
    "aborted",
    "blocked",
    "skipped_no_dump",
    "skipped_missing_dump",
}
MISSION_REDRIVE_SESSION_STATES = {"error", "cancelled", "aborted", "blocked"}
MISSION_REDRIVE_MAX_ATTEMPTS = 3
MAX_PROBE_TARGET_FILES = 8
MAX_PROBE_TARGET_BYTES = 500_000
PROBE_GROUP_TARGET_CHAR_BUDGET = 90_000
PLAN_GROUP_CHAR_BUDGET = 120_000  # stay well under chatgpt hard_char_cap=150K
SCOPE_CONTEXT_CHAR_BUDGET = 110_000  # reserve space for question + scaffold overhead
OUTLINE_TARGET_CHAR_CAP = 60_000
SCOPE_PROJECTION_STOPWORDS = {
    "about",
    "active",
    "advance",
    "attached",
    "authority",
    "bridge",
    "bounded",
    "carry",
    "concrete",
    "context",
    "criteria",
    "current",
    "cycle",
    "discovery",
    "files",
    "focus",
    "group",
    "identify",
    "intent",
    "needed",
    "phase",
    "probe",
    "question",
    "relevant",
    "return",
    "scope",
    "seed",
    "signal",
    "smallest",
    "standards",
    "success",
    "synth",
    "system",
    "treat",
    "using",
    "view",
}
NEW_SHARD_EXISTING_SIMILARITY = 0.88
NEW_SHARD_PROMPT_SIMILARITY = 0.82

# ---------------------------------------------------------------------------
# State machine stages
# ---------------------------------------------------------------------------
STAGES = [
    "init",                 # legacy bootstrap stage retained for older states
    "shards_extracted",     # legacy bootstrap stage retained for older states
    "shards_selected",      # legacy bootstrap stage retained for older states
    "synth_seed_emitted",   # authored synth_seed.json is the active subphase authority
    "observe_plan_compiled", # observe_plan.json compiled from synth_seed
    "observe_dispatched",   # observe session launched via bridge
    "results_processed",    # results read, shards updated, subphase meta_ledger appended
    "apply_ready",          # apply plan compiled, awaiting approval gate
    "apply_approved",       # operator approved, apply can execute
    "cycle_complete",       # cycle done, ready to loop back to shard selection
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mark_observe_dispatch_failed(
    state: dict,
    *,
    provider: str,
    launch_profile: str,
    dump_dir: str,
    reason: str,
    state_path: Path | None = None,
) -> None:
    """Return a failed/unmaterialized dispatch to the compiled-plan retry state."""
    state["stage"] = "observe_plan_compiled"
    state["observe_dispatch_status"] = "failed"
    state["observe_dispatch_error"] = reason
    state["observe_session_id"] = None
    state["observe_manifest_path"] = None
    _record_cycle_event(
        state,
        "observe_dispatch_failed",
        provider=provider,
        launch_profile=launch_profile,
        observe_plan_path=state.get("observe_plan_path"),
        dump_dir=dump_dir,
        reason=reason,
    )
    _log(state, "execute_observe", f"Bridge dispatch failed before session materialized: {reason}")
    if state_path is not None:
        save_state_if_not_stale(state, state_path)


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


def _short_hash(text: str) -> str:
    return sha256(text.encode()).hexdigest()[:8]


def _dedupe_strings(values: list[str]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def _discover_family_dir(phase_dir: str) -> str:
    token = str(phase_dir or "").strip()
    if not token:
        return token
    phase_abs = REPO_ROOT / token
    obsidian_root = (REPO_ROOT / "obsidian").resolve()
    if phase_abs.exists():
        scaffold_path = phase_abs / "phase_scaffold.json"
        if scaffold_path.exists():
            payload = _load_json(scaffold_path)
            if isinstance(payload, dict):
                family_dir = str(payload.get("family_dir") or "").strip()
                if family_dir:
                    return family_dir
        for current in [phase_abs, *phase_abs.parents]:
            try:
                current.relative_to(obsidian_root)
            except ValueError:
                break
            marker_path = current / "phase_family.json"
            if marker_path.exists():
                payload = _load_json(marker_path)
                if isinstance(payload, dict):
                    family_dir = str(payload.get("family_dir") or "").strip()
                    if family_dir:
                        return family_dir
                return str(current.relative_to(REPO_ROOT))
            if all((current / name).exists() for name in ("raw_seed.md", "meta_ledger.json", "reference_ledger.json")):
                return str(current.relative_to(REPO_ROOT))
    return str(Path(phase_dir).parent)


def _discover_family_raw_seed_path(phase_dir: str, family_dir: str | None = None) -> str:
    resolved_family_dir = str(family_dir or "").strip() or _discover_family_dir(phase_dir)
    if not resolved_family_dir:
        return ""
    candidate = canonicalize_write_path(f"{resolved_family_dir}/raw_seed.md") or ""
    if candidate and (REPO_ROOT / candidate).exists():
        return candidate
    return ""


# ---------------------------------------------------------------------------
# Pipeline state
# ---------------------------------------------------------------------------
def init_state(raw_seed_path: str, phase_dir: str, family_dir: str | None = None) -> dict:
    """Create initial pipeline state."""
    resolved_family_dir = str(family_dir or "").strip() or _discover_family_dir(phase_dir)
    synth_seed_path = canonicalize_write_path(f"{phase_dir}/synth_seed.json") or ""
    synth_seed_abs = REPO_ROOT / synth_seed_path if synth_seed_path else None
    if not synth_seed_abs or not synth_seed_abs.exists():
        raise ValueError(f"synth_seed.json must exist before pipeline init: {synth_seed_path or phase_dir}")
    synth_payload = normalize_synth_payload(_load_json(synth_seed_abs) or {})
    if not synth_payload:
        raise ValueError(f"synth_seed.json is invalid: {synth_seed_path}")
    if str(synth_payload.get("authoring_status") or "").strip() == PENDING_SYNTH_AUTHORING:
        raise ValueError("synth_seed.json is still pending initial authoring; sync it before pipeline init.")
    resolved_raw_seed_path = str(raw_seed_path or "").strip() or _discover_family_raw_seed_path(phase_dir, resolved_family_dir)
    meta_ledger_path = canonicalize_write_path(f"{phase_dir}/meta_ledger.json") or None

    # Bootstrap shards from synth_seed.source_shards so the shard evolution
    # tracker has something to update across cycles. Without this, all cycle
    # shard_updates stay 0 → zero_evolution_streak climbs → uncertainty_block.
    source_shards = synth_payload.get("source_shards") or []
    bootstrapped_shards = [
        {**s, "status": s.get("status") or "selected"}
        for s in source_shards
        if isinstance(s, dict)
    ]
    shards_path_rel: str | None = None
    if bootstrapped_shards:
        shards_abs = (REPO_ROOT / phase_dir / "extracted_shards.json").resolve()
        shards_abs.parent.mkdir(parents=True, exist_ok=True)
        shards_abs.write_text(
            json.dumps({"shards": bootstrapped_shards, "extracted_at": _utc_now(), "source": "synth_seed_bootstrap"}, indent=2) + "\n"
        )
        shards_path_rel = canonicalize_write_path(str(shards_abs.relative_to(REPO_ROOT.resolve()))) or None

    state = {
        "pipeline_id": f"PIPE_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}_{_short_hash(synth_seed_path or phase_dir)}",
        "stage": "synth_seed_emitted",
        "created_at": _utc_now(),
        "updated_at": _utc_now(),
        "raw_seed_path": resolved_raw_seed_path or None,
        "phase_dir": phase_dir,
        "family_dir": resolved_family_dir,
        "cycle": 0,
        "shards_path": shards_path_rel,
        "synth_seed_path": synth_seed_path,
        "observe_plan_path": None,
        "observe_session_id": None,
        "observe_manifest_path": None,
        "observe_dispatch_started_at": None,
        "meta_ledger_path": meta_ledger_path,
        "known_relevant_files": synth_relevant_file_paths(synth_payload),
        "history": [],
    }
    ensure_controller_state(state, repo_root=REPO_ROOT)
    return state


def load_state(path: Path) -> dict:
    state = json.loads(path.read_text())
    ensure_controller_state(state, repo_root=REPO_ROOT)
    return state


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError:
        return None


def save_state(state: dict, path: Path) -> None:
    ensure_controller_state(state, repo_root=REPO_ROOT)
    maybe_capture_pre_save_snapshot(path, state, repo_root=REPO_ROOT)
    state["updated_at"] = _utc_now()
    _write_json_atomic(path, state)


def save_state_if_not_stale(state: dict, path: Path) -> bool:
    ensure_controller_state(state, repo_root=REPO_ROOT)
    existing = _load_json(path)
    if isinstance(existing, dict):
        ensure_controller_state(existing, repo_root=REPO_ROOT)
        if int(existing.get("cycle") or 0) > int(state.get("cycle") or 0):
            return False
    save_state(state, path)
    return True


def _write_json_atomic(path: Path, payload: Any) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp_path.replace(path)
    return path


def _log(state: dict, action: str, detail: str) -> None:
    state["history"].append({
        "timestamp": _utc_now(),
        "stage": state["stage"],
        "action": action,
        "detail": detail,
    })


# ---------------------------------------------------------------------------
# Stage 1: Extract shards from raw_seed
# ---------------------------------------------------------------------------
def extract_shards(state: dict, *, bridge_fn=None, provider: str = "chatgpt") -> list[dict]:
    """Read raw_seed.md and extract structured shards.

    If bridge_fn is provided, sends raw_seed to bridge for AI extraction.
    Otherwise, does a rule-based extraction (headers, bold statements, key patterns).
    """
    raw_seed_path = REPO_ROOT / state["raw_seed_path"]
    raw_text = raw_seed_path.read_text()

    if bridge_fn:
        shards = _extract_shards_via_bridge(raw_text, bridge_fn, provider)
    else:
        shards = _extract_shards_local(raw_text)

    # Write shards to phase dir
    phase_dir = REPO_ROOT / state["phase_dir"]
    shards_path = phase_dir / "extracted_shards.json"
    shards_path.write_text(json.dumps({"shards": shards, "extracted_at": _utc_now()}, indent=2) + "\n")

    state["shards_path"] = str(shards_path.relative_to(REPO_ROOT))
    state["stage"] = "shards_extracted"
    write_controller_artifacts(state, repo_root=REPO_ROOT)
    _log(state, "extract_shards", f"Extracted {len(shards)} shards from {state['raw_seed_path']}")
    return shards


def digest_raw_seed(raw_text: str, max_chars: int = 30000) -> str:
    """Compress a large raw_seed into a structured digest that fits in bridge context.

    Strategy: Keep headers and bold statements verbatim. Keep directive lines.
    Summarize long narrative blocks by their first sentence. Skip duplicate/noise.
    Output is still readable text but much smaller.
    """
    lines = raw_text.split("\n")
    digest_parts: list[str] = []
    current_section = ""
    narrative_buffer: list[str] = []
    total_chars = 0

    def flush_narrative():
        nonlocal total_chars
        if not narrative_buffer:
            return
        # Keep first line of narrative blocks, skip the rest
        first = narrative_buffer[0].strip()
        if len(first) > 20:
            line = f"  [{len(narrative_buffer)} lines] {first[:200]}"
            digest_parts.append(line)
            total_chars += len(line)
        narrative_buffer.clear()

    for line in lines:
        stripped = line.strip()

        if total_chars >= max_chars:
            digest_parts.append(f"\n[TRUNCATED at {max_chars} chars — {len(lines)} total lines in raw seed]")
            break

        # Always keep headers
        if stripped.startswith("#"):
            flush_narrative()
            digest_parts.append(stripped)
            current_section = stripped
            total_chars += len(stripped)
            continue

        # Always keep bold statements
        if stripped.startswith("**") and "**" in stripped[2:]:
            flush_narrative()
            digest_parts.append(stripped)
            total_chars += len(stripped)
            continue

        # Always keep ALL CAPS directives
        if stripped.isupper() and len(stripped) > 30:
            flush_narrative()
            digest_parts.append(stripped)
            total_chars += len(stripped)
            continue

        # Keep directive lines
        if any(kw in stripped.lower() for kw in ["need to", "should ", "must ", "the entire point", "the critical"]):
            flush_narrative()
            digest_parts.append(stripped[:300])
            total_chars += min(len(stripped), 300)
            continue

        # Keep code blocks and JSON
        if stripped.startswith("```") or stripped.startswith("{") or stripped.startswith("["):
            flush_narrative()
            digest_parts.append(stripped[:500])
            total_chars += min(len(stripped), 500)
            continue

        # Everything else is narrative — buffer it
        if stripped:
            narrative_buffer.append(stripped)

    flush_narrative()
    return "\n".join(digest_parts)


def _extract_shards_via_bridge(raw_text: str, bridge_fn, provider: str) -> list[dict]:
    """Send raw_seed to bridge for AI-powered shard extraction.

    If the raw_seed is too large, it first digests it down to fit bridge context.
    """
    # Digest if too large (bridge context is ~200K chars but we want room for response)
    seed_text = raw_text if len(raw_text) < 80000 else digest_raw_seed(raw_text, max_chars=60000)

    prompt = f"""You are a shard extractor. Read the following raw seed document and extract every discrete idea, insight, or directive as a structured shard.

For each shard, output a JSON object with these fields:
- "id": "SHARD_NNN" (sequential)
- "raw_seed_anchor": short quote + approximate line reference
- "clarified_statement": clean restatement that removes conversational noise without changing intent
- "concept_group": short grouping label (e.g. "shard_extraction", "state_machine", "bridge_dispatch")
- "intent_provenance": what higher-level goal this serves (1-2 short strings)
- "relevant_files": repo-relative file paths this shard would touch (best guess, can be empty)
- "status": "pending"

Output ONLY a JSON array of shard objects. No markdown, no explanation.

---
RAW SEED:
{seed_text}
"""
    config = {"platform": provider, "timeout_s": 120}
    response = bridge_fn(prompt, config=config, cancel=threading.Event())

    # Try to parse JSON from response
    try:
        # Find JSON array in response
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        start = text.index("[")
        end = text.rindex("]") + 1
        return json.loads(text[start:end])
    except (json.JSONDecodeError, ValueError):
        print(f"[WARN] Bridge response not parseable as JSON, falling back to local extraction", file=sys.stderr)
        return _extract_shards_local(response)


def _extract_shards_local(raw_text: str) -> list[dict]:
    """Rule-based shard extraction when bridge is not available.

    Scans for key patterns: bold statements, ALL CAPS lines, lines with 'need',
    'should', 'must', 'idea', concrete file paths, and section headers.
    """
    shards = []
    lines = raw_text.split("\n")
    shard_id = 0

    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        if not stripped or len(stripped) < 20:
            continue

        is_bold = stripped.startswith("**") and "**" in stripped[2:]
        is_caps = stripped.isupper() and len(stripped) > 30
        is_directive = any(kw in stripped.lower() for kw in [
            "need to", "should ", "must ", "the idea is", "the point is",
            "we need", "i think we", "the entire point", "the critical",
        ])
        is_header = stripped.startswith("##") and not stripped.startswith("###")

        if is_bold or is_caps or is_directive:
            shard_id += 1
            # Determine concept group from context
            concept = _guess_concept_group(stripped)
            shards.append({
                "id": f"SHARD_{shard_id:03d}",
                "raw_seed_anchor": f"line {i}: \"{stripped[:80]}\"",
                "clarified_statement": stripped.strip("*# "),
                "concept_group": concept,
                "intent_provenance": [],
                "relevant_files": [],
                "status": "pending",
            })

    return shards


def _guess_concept_group(text: str) -> str:
    """Simple keyword-based concept grouping."""
    t = text.lower()
    if any(w in t for w in ["bridge", "dispatch", "cdp"]):
        return "bridge_infrastructure"
    if any(w in t for w in ["shard", "extract"]):
        return "shard_extraction"
    if any(w in t for w in ["observe", "pass", "group"]):
        return "observe_framework"
    if any(w in t for w in ["apply", "implement"]):
        return "apply_framework"
    if any(w in t for w in ["kernel", "cli", "navigation"]):
        return "kernel_navigation"
    if any(w in t for w in ["state machine", "loop", "autonomous"]):
        return "autonomous_loop"
    if any(w in t for w in ["seed", "synth", "raw"]):
        return "seed_lifecycle"
    if any(w in t for w in ["principle", "intent", "doctrine"]):
        return "principles_and_intent"
    if any(w in t for w in ["reference", "ledger", "memory"]):
        return "memory_and_ledgers"
    if any(w in t for w in ["json", "markdown", "schema"]):
        return "artifact_format"
    return "general"


def _stringify_reason(reason: Any) -> str | None:
    if reason in (None, "", [], {}):
        return None
    if isinstance(reason, str):
        text = reason.strip()
    else:
        text = json.dumps(reason, ensure_ascii=False, sort_keys=True)
    return text[:1500] if text else None


def _normalize_shard_status(raw_status: Any) -> tuple[str, str | None]:
    raw = str(raw_status or "pending").strip()
    token = raw.lower().replace(" ", "_")
    if token in CANONICAL_SHARD_STATUSES:
        return token, None
    if "completed" in token:
        return "completed", raw
    if token == "resolved":
        return "resolved", None
    if token == "addressed":
        return "addressed", None
    if "in_progress" in token:
        return "in_progress", raw if token != "in_progress" else None
    if "partially_addressed" in token:
        return "partially_addressed", raw if token != "partially_addressed" else None
    if "superseded" in token:
        return "partially_addressed" if token != "superseded" else "superseded", raw if token != "superseded" else None
    if token == "selected":
        return "selected", None
    return "pending", raw if token != "pending" else None


def _normalize_shard_record(shard: dict, *, default_status_reason: str | None = None) -> dict:
    normalized = dict(shard)
    status, variant = _normalize_shard_status(normalized.get("status", "pending"))
    normalized["status"] = status
    if variant:
        normalized["status_variant"] = variant
    else:
        normalized.pop("status_variant", None)
    status_reason = _stringify_reason(normalized.get("status_reason")) or default_status_reason
    if status_reason:
        normalized["status_reason"] = status_reason
    else:
        normalized.pop("status_reason", None)
    normalized["intent_provenance"] = [
        str(item).strip()
        for item in normalized.get("intent_provenance", [])
        if str(item).strip()
    ] if isinstance(normalized.get("intent_provenance"), list) else []
    normalized["relevant_files"] = [
        str(item).strip()
        for item in normalized.get("relevant_files", [])
        if str(item).strip()
    ] if isinstance(normalized.get("relevant_files"), list) else []
    normalized["selection_count"] = max(0, int(normalized.get("selection_count") or 0))
    normalized["consecutive_selected_cycles"] = max(0, int(normalized.get("consecutive_selected_cycles") or 0))
    normalized["last_selected_cycle"] = (
        int(normalized["last_selected_cycle"])
        if normalized.get("last_selected_cycle") is not None
        else None
    )
    normalized["last_status_change_cycle"] = (
        int(normalized["last_status_change_cycle"])
        if normalized.get("last_status_change_cycle") is not None
        else None
    )
    normalized["cooldown_until_cycle"] = max(0, int(normalized.get("cooldown_until_cycle") or 0))
    return normalized


def _normalize_shards_payload(payload: dict) -> tuple[dict, bool]:
    data = dict(payload or {})
    changed = False
    shards = data.get("shards")
    if not isinstance(shards, list):
        shards = []
        changed = True
    normalized_shards = []
    for shard in shards:
        original = dict(shard) if isinstance(shard, dict) else {}
        normalized = _normalize_shard_record(original)
        normalized_shards.append(normalized)
        if normalized != original:
            changed = True
    data["shards"] = normalized_shards
    return data, changed


def _selected_signature(shard_ids: list[str]) -> str:
    joined = "|".join(sorted(str(item).strip() for item in shard_ids if str(item).strip()))
    return sha256(joined.encode()).hexdigest()[:16] if joined else ""


def _cycle_dir_rel(state: dict, cycle: int | None = None) -> str:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    return str(Path(state["phase_dir"]) / f"cycle_{resolved_cycle}")


def _cycle_dir_path(state: dict, cycle: int | None = None) -> Path:
    return REPO_ROOT / _cycle_dir_rel(state, cycle)


def _cycle_timeline_rel(state: dict, cycle: int | None = None) -> str:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    cycle_dir = _cycle_dir_rel(state, resolved_cycle)
    return str(Path(cycle_dir) / "cycle_timeline.jsonl")


def _record_cycle_event(
    state: dict,
    event: str,
    *,
    cycle: int | None = None,
    **fields: Any,
) -> str | None:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    dump_dir = _cycle_dir_rel(state, resolved_cycle)
    try:
        timeline_path = observe_cycle_timeline_path(REPO_ROOT, dump_dir)
    except ValueError:
        return None
    payload = {
        "timestamp": _utc_now(),
        "pipeline_id": str(state.get("pipeline_id") or "").strip() or None,
        "phase": _active_phase(state),
        "stage": str(state.get("stage") or "").strip() or None,
        "cycle": resolved_cycle,
        "event": event,
    }
    payload.update(fields)
    append_jsonl(timeline_path, payload)
    return _cycle_timeline_rel(state, resolved_cycle)


def _snapshot_cycle_synth_seed(state: dict, cycle_dir: Path) -> str | None:
    synth_rel = str(state.get("synth_seed_path") or "").strip()
    if not synth_rel:
        return None
    synth_abs = REPO_ROOT / synth_rel
    if not synth_abs.exists():
        return None
    snapshot_path = cycle_dir / "synth_seed.original.json"
    if snapshot_path.exists():
        return str(snapshot_path.relative_to(REPO_ROOT))
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot_path.write_text(synth_abs.read_text(encoding="utf-8"), encoding="utf-8")
    return str(snapshot_path.relative_to(REPO_ROOT))


def _legacy_dump_dir_rel(state: dict, cycle: int | None = None) -> str:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    return f"tools/meta/apply/observe_dumps/{_phase_id_from_state(state)}_cycle_{resolved_cycle}"


def _cycle_path_candidates(state: dict, cycle: int, filename: str) -> list[Path]:
    return [
        _cycle_dir_path(state, cycle) / filename,
        REPO_ROOT / _legacy_dump_dir_rel(state, cycle) / filename,
    ]


def _latest_cycle_assimilation(state: dict) -> dict[str, Any] | None:
    candidates: list[Path] = []
    explicit_rel = str(state.get("current_cycle_assimilation_path") or "").strip()
    if explicit_rel:
        candidates.append(REPO_ROOT / explicit_rel)
    cycle = max(0, int(state.get("cycle") or 0) - 1)
    candidates.extend(_cycle_path_candidates(state, cycle, "cycle_assimilation.json"))
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        payload = _load_json(candidate)
        if isinstance(payload, dict):
            return payload
    return None


def _latest_cycle_summary(state: dict) -> dict[str, Any] | None:
    assimilation = _latest_cycle_assimilation(state)
    summary_rel = str((assimilation or {}).get("cycle_summary_path") or "").strip()
    if summary_rel:
        payload = _load_json(REPO_ROOT / summary_rel)
        if isinstance(payload, dict):
            return payload
    cycle = max(0, int(state.get("cycle") or 0) - 1)
    for candidate in _cycle_path_candidates(state, cycle, "_cycle_summary.json"):
        payload = _load_json(candidate)
        if isinstance(payload, dict):
            return payload
    return None


def _mission_launch_redrive_plan_path(state: dict) -> str | None:
    rel = str(state.get("mission_launch_plan_path") or "").strip()
    if not rel:
        return None
    return rel if (REPO_ROOT / rel).exists() else None


def _should_redrive_mission_launch(state: dict) -> bool:
    if str(state.get("launch_origin") or "").strip() != "mission_launch":
        return False
    if str(state.get("mission_redrive_policy") or "").strip() != "retry_same_plan_on_degraded_cycle":
        return False
    if int(state.get("mission_redrive_count") or 0) >= MISSION_REDRIVE_MAX_ATTEMPTS:
        return False
    if not _mission_launch_redrive_plan_path(state):
        return False
    cycle_summary = _latest_cycle_summary(state) or {}
    runtime_state = str(cycle_summary.get("runtime_state") or "").strip()
    if runtime_state not in MISSION_REDRIVE_SESSION_STATES:
        return False
    if str(state.get("mission_id") or "").strip() == "raw_seed_atomization":
        atomization_import = cycle_summary.get("atomization_import")
        if isinstance(atomization_import, Mapping) and str(atomization_import.get("status") or "").strip().lower() != "error":
            remaining_plan = atomization_import.get("remaining_plan_paragraphs")
            if remaining_plan in (None, ""):
                remaining_plan = len(
                    {
                        str(paragraph_id).strip()
                        for paragraph_id in (
                            list(atomization_import.get("retryable_paragraph_ids") or [])
                            + list(atomization_import.get("failed_paragraph_ids") or [])
                            + list(atomization_import.get("remaining_plan_paragraph_ids") or [])
                        )
                        if str(paragraph_id).strip()
                    }
                )
            return int(remaining_plan or 0) > 0
    receipt_path = str(cycle_summary.get("receipt_path") or "").strip()
    if receipt_path:
        return False
    if int(cycle_summary.get("shard_updates") or 0) > 0:
        return False
    if int(cycle_summary.get("new_shards_ingested") or 0) > 0:
        return False
    return True


def _rearm_mission_launch_plan(state: dict) -> bool:
    plan_rel = _mission_launch_redrive_plan_path(state)
    if not plan_rel:
        return False
    redrive_plan: Mapping[str, Any] = {}
    if str(state.get("mission_id") or "").strip() == "raw_seed_atomization":
        family_dir = str(state.get("family_dir") or "").strip()
        if not family_dir:
            return False
        redrive_plan = build_atomization_redrive_plan(
            family_dir=family_dir,
            plan_path=plan_rel,
            repo_root=REPO_ROOT,
        )
        redrive_status = str(redrive_plan.get("status") or "").strip().lower()
        if redrive_status == "completed":
            plan_rel = str(redrive_plan.get("plan_path") or plan_rel).strip() or plan_rel
        elif redrive_status == "noop":
            return False
        state["mission_launch_plan_path"] = plan_rel
    state["observe_plan_path"] = plan_rel
    state["observe_session_id"] = None
    state["observe_manifest_path"] = None
    state["observe_dispatch_started_at"] = None
    state["stage"] = "observe_plan_compiled"
    state["mission_redrive_count"] = int(state.get("mission_redrive_count") or 0) + 1
    _record_cycle_event(
        state,
        "mission_launch_redrive_rearmed",
        mission_launch_plan_path=plan_rel,
        mission_redrive_count=int(state["mission_redrive_count"]),
        pending_probe_count=(
            int(redrive_plan.get("pending_probe_count") or 0)
            if str(state.get("mission_id") or "").strip() == "raw_seed_atomization"
            else None
        ),
    )
    _log(
        state,
        "mission_launch_redrive",
        f"Re-armed mission launch plan for degraded cycle retry ({state['mission_redrive_count']}/{MISSION_REDRIVE_MAX_ATTEMPTS}).",
    )
    return True


def _load_receipt_payload(path: Path) -> dict[str, Any] | None:
    payload = _load_json(path)
    if not isinstance(payload, dict):
        return None
    surfaced = payload.get("payload")
    if isinstance(surfaced, dict):
        return surfaced
    return payload if isinstance(payload.get("response_schema"), dict) and isinstance(payload.get("payload"), dict) else None


def _extract_response_body(text: str) -> str:
    source = str(text or "")
    marker = "\n## Response\n"
    if marker in source:
        return source[source.index(marker) + len(marker):].strip()
    return source.strip()


def _load_group_receipt(
    group: dict[str, Any] | None,
    *,
    plan_group: dict[str, Any] | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if not isinstance(group, dict):
        return None, "none"
    for key in ("response_receipt_file", "response_surface_file"):
        rel = str(group.get(key) or "").strip()
        if not rel:
            continue
        payload = _load_receipt_payload(REPO_ROOT / rel)
        if payload:
            return payload, "typed_receipt" if key == "response_receipt_file" else "response_surface_sidecar"
    response_rel = str(group.get("response_file") or "").strip()
    response_schema = (
        plan_group.get("response_schema")
        if isinstance(plan_group, dict) and isinstance(plan_group.get("response_schema"), dict)
        else None
    )
    if response_rel and response_schema:
        response_path = REPO_ROOT / response_rel
        if response_path.exists():
            try:
                from tools.meta.apply.run_observe_plan import _validate_group_response

                response_text = _extract_response_body(response_path.read_text(encoding="utf-8"))
                validation = _validate_group_response(
                    str(plan_group.get("question") or ""),
                    response_text,
                    output_contract=plan_group.get("output_contract"),
                    prompt_metadata=plan_group.get("prompt_metadata")
                    if isinstance(plan_group.get("prompt_metadata"), dict)
                    else None,
                    response_schema=response_schema,
                    json_only=bool(plan_group.get("json_only")),
                )
                payload = validation.get("receipt_payload")
                if isinstance(payload, dict):
                    return payload, "response_markdown_fallback"
            except Exception:
                pass
    return None, "none"


def _load_cycle_summary_by_cycle(state: dict, cycle: int) -> dict | None:
    if cycle < 0:
        return None
    for path in _cycle_path_candidates(state, cycle, "_cycle_summary.json"):
        payload = _load_json(path)
        if payload:
            return payload
    return None


def _selected_shard_ids_for_cycle(state: dict) -> list[str]:
    synth = _load_json(REPO_ROOT / str(state.get("synth_seed_path") or ""))
    if not isinstance(synth, dict):
        return []
    shards = synth.get("source_shards") or synth.get("seed_shards") or []
    if not isinstance(shards, list):
        return []
    return [str(shard.get("id")).strip() for shard in shards if isinstance(shard, dict) and str(shard.get("id")).strip()]


def _pick_diverse_shards(
    pool: list[dict],
    *,
    count: int,
    group_counts: dict[str, int],
    selected_ids: set[str],
) -> list[dict]:
    chosen: list[dict] = []
    for shard in pool:
        if len(chosen) >= count:
            break
        shard_id = str(shard.get("id") or "").strip()
        if not shard_id or shard_id in selected_ids:
            continue
        concept_group = str(shard.get("concept_group") or "general")
        if group_counts.get(concept_group, 0) >= 2:
            continue
        chosen.append(shard)
        selected_ids.add(shard_id)
        group_counts[concept_group] = group_counts.get(concept_group, 0) + 1
    return chosen


def _empty_synthesis_payload() -> dict[str, Any]:
    return {
        "decision": "",
        "next_phase": "",
        "confidence": 0.0,
        "reasoning": "",
        "rationale": "",
        "relevant_files": [],
        "newly_relevant_files": [],
        "dropped_files": [],
        "verification": [],
        "routing_decision": {},
        "priority_action": {},
        "ordered_sequence": [],
        "shard_status_updates": [],
        "new_shards": [],
        "problem_map": {},
        "solution_map": {},
        "plan_packet": {},
        "apply_plan": {},
    }


def _strip_markdown_list_marker(text: str) -> str:
    return re.sub(r"^(?:[-*+]\s+|\d+\.\s+)", "", str(text or "").strip(), count=1)


def _markdown_section_blocks(text: Any) -> list[str]:
    source = str(text or "").strip()
    if not source:
        return []

    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if lines and all(re.match(r"^(?:[-*+]\s+|\d+\.\s+)", line) for line in lines):
        return [
            cleaned
            for line in lines
            if (cleaned := _strip_markdown_list_marker(line))
        ]

    blocks: list[str] = []
    for block in re.split(r"\n\s*\n", source):
        token = block.strip()
        if not token:
            continue
        block_lines = [line.rstrip() for line in token.splitlines() if line.strip()]
        if not block_lines:
            continue
        block_lines[0] = _strip_markdown_list_marker(block_lines[0])
        cleaned_block = "\n".join(block_lines).strip()
        if cleaned_block:
            blocks.append(cleaned_block)
    return blocks


def _first_markdown_block(text: Any) -> str:
    blocks = _markdown_section_blocks(text)
    return blocks[0] if blocks else ""


def _normalize_synthesis_payload(payload: Any) -> dict[str, Any]:
    normalized = _empty_synthesis_payload()
    if not isinstance(payload, dict):
        return normalized

    for field in ("decision", "next_phase", "reasoning", "rationale"):
        if payload.get(field) not in (None, ""):
            normalized[field] = str(payload.get(field) or "").strip()
    if payload.get("confidence") not in (None, ""):
        try:
            normalized["confidence"] = max(0.0, min(1.0, float(payload.get("confidence") or 0.0)))
        except (TypeError, ValueError):
            normalized["confidence"] = 0.0
    for field in ("relevant_files", "newly_relevant_files", "dropped_files", "verification"):
        if isinstance(payload.get(field), list):
            items: list[Any] = []
            for item in payload.get(field):
                if isinstance(item, dict):
                    items.append(dict(item))
                    continue
                token = str(item).strip()
                if token:
                    items.append(token)
            normalized[field] = items

    routing_decision = payload.get("routing_decision")
    if isinstance(routing_decision, dict):
        decision = str(routing_decision.get("decision") or "").strip()
        normalized["routing_decision"] = {
            "decision": decision,
            "next_layer_kind": str(routing_decision.get("next_layer_kind") or "").strip(),
            "block_reason": str(routing_decision.get("block_reason") or "").strip(),
            "adopted_shard_ids": [
                str(item).strip()
                for item in (routing_decision.get("adopted_shard_ids") or [])
                if str(item).strip()
            ] if isinstance(routing_decision.get("adopted_shard_ids"), list) else [],
            "next_groups": [
                dict(item)
                for item in (routing_decision.get("next_groups") or [])
                if isinstance(item, dict)
            ] if isinstance(routing_decision.get("next_groups"), list) else [],
            "sidecars": [
                dict(item)
                for item in (routing_decision.get("sidecars") or [])
                if isinstance(item, dict)
            ] if isinstance(routing_decision.get("sidecars"), list) else [],
        }
        if routing_decision.get("confidence") not in (None, ""):
            try:
                normalized["routing_decision"]["confidence"] = max(
                    0.0,
                    min(1.0, float(routing_decision.get("confidence") or 0.0)),
                )
            except (TypeError, ValueError):
                pass

    priority_action = payload.get("priority_action")
    if isinstance(priority_action, dict):
        normalized["priority_action"] = dict(priority_action)
    elif isinstance(priority_action, str) and priority_action.strip():
        normalized["priority_action"] = {"summary": priority_action.strip()}
    elif priority_action not in (None, "", [], {}):
        normalized["priority_action"] = {"summary": str(priority_action).strip()}

    ordered_sequence = payload.get("ordered_sequence")
    if not isinstance(ordered_sequence, list):
        ordered_sequence = [ordered_sequence] if ordered_sequence not in (None, "", [], {}) else []
    for item in ordered_sequence:
        if isinstance(item, dict):
            normalized["ordered_sequence"].append(dict(item))
        elif str(item or "").strip():
            normalized["ordered_sequence"].append({"step": str(item).strip()})

    shard_status_updates = payload.get("shard_status_updates")
    if isinstance(shard_status_updates, list):
        for item in shard_status_updates:
            if not isinstance(item, dict):
                continue
            shard_id = str(item.get("id") or item.get("shard_id") or "").strip()
            if not shard_id:
                continue
            new_status, variant = _normalize_shard_status(
                item.get("new_status") or item.get("status") or "pending"
            )
            explicit_variant = str(item.get("status_variant") or "").strip()
            if explicit_variant:
                variant = explicit_variant
            update = {
                "id": shard_id,
                "new_status": new_status,
            }
            if variant:
                update["status_variant"] = variant
            reason = _stringify_reason(
                item.get("reason")
                or item.get("status_reason")
                or item.get("note")
            )
            if reason:
                update["reason"] = reason
            normalized["shard_status_updates"].append(update)

    new_shards = payload.get("new_shards")
    if isinstance(new_shards, list):
        for item in new_shards:
            if isinstance(item, dict):
                question = str(
                    item.get("question")
                    or item.get("clarified_statement")
                    or item.get("statement")
                    or ""
                ).strip()
                if not question:
                    continue
                new_shard = {
                    "question": question,
                    "file_targets": [
                        str(path).strip()
                        for path in (
                            item.get("file_targets")
                            if isinstance(item.get("file_targets"), list)
                            else item.get("relevant_files")
                            if isinstance(item.get("relevant_files"), list)
                            else []
                        )
                        if str(path).strip()
                    ],
                }
                if item.get("id"):
                    new_shard["id"] = str(item.get("id")).strip()
                concept_group = str(item.get("concept_group") or "").strip()
                if concept_group:
                    new_shard["concept_group"] = concept_group
                reason = _stringify_reason(item.get("reason") or item.get("note"))
                if reason:
                    new_shard["reason"] = reason
                normalized["new_shards"].append(new_shard)
                continue
            question = str(item or "").strip()
            if question:
                normalized["new_shards"].append({
                    "question": question,
                    "file_targets": [],
                })

    for field in ("problem_map", "solution_map", "plan_packet", "apply_plan"):
        value = payload.get(field)
        if isinstance(value, dict):
            normalized[field] = dict(value)
        elif isinstance(value, list):
            normalized[field] = list(value)
        elif isinstance(value, str) and value.strip():
            normalized[field] = value.strip()

    synthesis = str(payload.get("synthesis") or "").strip()
    contradictions = str(payload.get("cross_group_contradictions") or "").strip()
    prioritized_action_blocks = _markdown_section_blocks(payload.get("prioritized_next_actions"))
    open_question_blocks = _markdown_section_blocks(payload.get("open_questions"))
    next_fork = str(payload.get("next_fork") or "").strip()

    if synthesis and not normalized["reasoning"]:
        normalized["reasoning"] = synthesis
    if contradictions and not normalized["rationale"]:
        normalized["rationale"] = contradictions
    if prioritized_action_blocks and not normalized["ordered_sequence"]:
        normalized["ordered_sequence"] = [{"step": block} for block in prioritized_action_blocks]
    if not normalized["priority_action"]:
        summary = (
            _first_markdown_block(payload.get("prioritized_next_actions"))
            or _first_markdown_block(payload.get("next_fork"))
            or _first_markdown_block(payload.get("synthesis"))
        )
        if summary:
            normalized["priority_action"] = {"summary": summary}

    problem_map = dict(normalized["problem_map"]) if isinstance(normalized["problem_map"], dict) else {}
    solution_map = dict(normalized["solution_map"]) if isinstance(normalized["solution_map"], dict) else {}
    if contradictions:
        problem_map.setdefault("cross_group_contradictions", contradictions)
    if open_question_blocks:
        problem_map.setdefault("open_questions", open_question_blocks)
    if synthesis:
        solution_map.setdefault("synthesis", synthesis)
    if prioritized_action_blocks:
        solution_map.setdefault("prioritized_next_actions", prioritized_action_blocks)
    if next_fork:
        solution_map.setdefault("next_fork", next_fork)
    if problem_map:
        normalized["problem_map"] = problem_map
    if solution_map:
        normalized["solution_map"] = solution_map

    return normalized


def _has_synthesis_payload(payload: dict[str, Any]) -> bool:
    return any(
        bool(payload.get(field))
        for field in (
            "routing_decision",
            *SYNTHESIS_REQUIRED_FIELDS,
            "problem_map",
            "solution_map",
            "plan_packet",
            "apply_plan",
        )
    )


def _extract_markdown_section(text: str, heading: str) -> str:
    source = str(text or "")
    if not source.strip():
        return ""
    if heading.lower() == "response" and (
        source.lstrip().startswith("<<FORM_RESPONSE>>")
        or source.lstrip().startswith("{")
        or source.lstrip().startswith("[")
        or source.lstrip().startswith("```")
    ):
        return source.strip()

    pattern = re.compile(rf"(?im)^##\s+{re.escape(heading)}\s*$")
    match = pattern.search(source)
    if not match:
        return ""
    start = match.end()
    remainder = source[start:]
    next_match = re.search(r"(?m)^##\s+.+$", remainder)
    if next_match:
        remainder = remainder[:next_match.start()]
    return remainder.strip()


def _strip_code_fence(text: str) -> str:
    stripped = str(text or "").strip()
    if not stripped.startswith("```"):
        return stripped
    lines = stripped.splitlines()
    if not lines:
        return stripped
    if lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    if lines and lines[0].strip().lower() == "json":
        lines = lines[1:]
    return "\n".join(lines).strip()


def _json_block_candidates(text: str, *, max_candidates: int = 64) -> list[str]:
    return json_candidate_blocks(text, max_candidates=max_candidates)


def _extract_synthesis_json(text: str) -> dict[str, Any]:
    """Extract synthesis JSON candidates from the response section only."""
    response_only = _extract_markdown_section(text, "Response") or str(text or "").strip()
    if not response_only:
        return _empty_synthesis_payload()
    merged: dict[str, Any] = {}

    for candidate in _json_block_candidates(response_only):
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            recognized = {
                key: parsed.get(key)
                for key in ("routing_decision", *SYNTHESIS_REQUIRED_FIELDS, "problem_map", "solution_map", "plan_packet", "apply_plan")
                if key in parsed
            }
            if recognized:
                merged.update(recognized)
                continue
        if isinstance(parsed, list) and parsed:
            if all(isinstance(item, dict) and (item.get("id") or item.get("shard_id")) for item in parsed):
                merged.setdefault("shard_status_updates", parsed)
                continue
            if all(
                isinstance(item, dict)
                and (item.get("question") or item.get("clarified_statement") or item.get("statement"))
                for item in parsed
            ):
                merged.setdefault("new_shards", parsed)
                continue

    section_payload = {
        "synthesis": _extract_markdown_section(response_only, "SYNTHESIS"),
        "cross_group_contradictions": _extract_markdown_section(response_only, "CROSS-GROUP CONTRADICTIONS"),
        "prioritized_next_actions": _extract_markdown_section(response_only, "PRIORITIZED NEXT ACTIONS"),
        "open_questions": _extract_markdown_section(response_only, "OPEN QUESTIONS"),
        "next_fork": _extract_markdown_section(response_only, "NEXT FORK"),
    }
    merged.update({key: value for key, value in section_payload.items() if value})

    return _normalize_synthesis_payload(merged)


def _normalize_compare_text(value: Any) -> str:
    text = str(value or "").strip().casefold()
    if not text:
        return ""
    text = re.sub(r"[`*_>#]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _texts_probably_same(left: str, right: str, *, threshold: float) -> bool:
    if not left or not right:
        return False
    if left == right:
        return True
    shorter, longer = (left, right) if len(left) <= len(right) else (right, left)
    if len(shorter) >= 40 and shorter in longer:
        return True
    return SequenceMatcher(None, left, right).ratio() >= threshold


# ---------------------------------------------------------------------------
# Stage 2: Select shards for the working set
# ---------------------------------------------------------------------------
def select_shards(state: dict, *, max_shards: int = 8) -> list[dict]:
    """Select pending shards for the next synth_seed working set.

    Selection heuristic:
    1. Filter to actionable statuses (pending, selected, partially_addressed, in_progress)
    2. Exclude completed/superseded shards
    3. Score by: novelty (not recently probed), file groundedness, intent richness
    4. Cap at max_shards, ensuring concept group diversity
    """
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


def _load_surface_payload(path: Path) -> dict[str, Any] | None:
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
    if cycle < 0:
        return _empty_synthesis_payload(), "none"
    for candidate in _cycle_path_candidates(state, cycle, "routing_decision.json"):
        payload = _load_json(candidate)
        if isinstance(payload, dict) and payload:
            return _normalize_synthesis_payload(payload), "typed_receipt"
    for dump_dir_path in (_cycle_dir_path(state, cycle), REPO_ROOT / _legacy_dump_dir_rel(state, cycle)):
        if dump_dir_path.exists():
            payload, source = _load_synthesis_payload_from_dump_dir(dump_dir_path)
            if _has_synthesis_payload(payload):
                return payload, source
    return _empty_synthesis_payload(), "none"


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
    # Pull from multiple sources — routing decisions often have reasoning/decision
    # populated while priority_action/ordered_sequence are empty.
    priority_action = payload.get("priority_action") or (summary or {}).get("priority_action") or {}
    ordered_sequence = payload.get("ordered_sequence") or (summary or {}).get("ordered_sequence") or []
    shard_updates = payload.get("shard_status_updates") or (summary or {}).get("shard_status_updates") or []
    new_shards = payload.get("new_shards") or (summary or {}).get("new_shards") or []

    # Routing decision fields (always populated, unlike priority_action)
    decision = str(payload.get("decision") or (summary or {}).get("decision") or "").strip()
    reasoning = str(payload.get("reasoning") or (summary or {}).get("reasoning") or "").strip()
    newly_relevant = payload.get("newly_relevant_files") or (summary or {}).get("newly_relevant_files") or []
    degraded_groups = list((summary or {}).get("degraded_groups") or [])

    lines = [f"### Cycle {cycle} Carry-Forward", ""]

    # Routing decision and reasoning (most useful signal for next cycle)
    if decision:
        lines.extend([f"Last routing decision: **{decision}**", ""])
    if reasoning:
        truncated = reasoning[:600].rsplit(" ", 1)[0] if len(reasoning) > 600 else reasoning
        lines.extend([f"Router reasoning: {truncated}", ""])

    # Degraded groups (critical for next cycle to know what failed)
    if degraded_groups:
        lines.append("Degraded/failed groups (bridge transport failures, not missing scope):")
        lines.extend(f"- {item}" for item in degraded_groups[:6])
        lines.append("")

    # Newly relevant files from router
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


def _find_latest_state() -> Path | None:
    """Auto-discover the most recent runtime-eligible pipeline_state.json in the repo."""
    from system.lib.phase_lifecycle import resolve_latest_runtime_state

    return resolve_latest_runtime_state(REPO_ROOT)


def _find_meta_ledger(state: dict) -> Path | None:
    """Find the active subphase meta_ledger.json."""
    phase_token = str(state.get("phase_dir") or "").strip()
    if not phase_token:
        return None
    candidate = REPO_ROOT / phase_token / "meta_ledger.json"
    if candidate.exists():
        return candidate
    return None


def _observe_record_candidates(state: dict, result: dict | None = None) -> list[str]:
    """Return likely observe history/runtime artifacts for a completed session.

    The grouped observe runtime now writes durable state under observe_history,
    while older flows sometimes surfaced dump-local `_session_manifest.json`
    files. Prefer the history entry because it carries dump_dir, result note,
    continuation, and group summaries in one stable artifact.
    """
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
    for rel_path in _observe_record_candidates(state, result=result):
        if (REPO_ROOT / rel_path).exists():
            return rel_path
    return None


def _mirror_observe_record_into_dump_manifest(
    *,
    record_rel: str | None,
    fallback_dump_dir: str | None = None,
) -> str | None:
    """Mirror the authoritative observe record into dump-local `_session_manifest.json`."""
    record_token = str(record_rel or "").strip()
    if not record_token:
        return None
    payload = _load_json(REPO_ROOT / record_token)
    if not isinstance(payload, dict):
        return None
    dump_dir = str(
        payload.get("dump_dir")
        or (payload.get("config") or {}).get("dump_dir")
        or fallback_dump_dir
        or ""
    ).strip()
    if not dump_dir:
        return None
    dump_manifest_path = REPO_ROOT / dump_dir / "_session_manifest.json"
    _write_json_atomic(dump_manifest_path, payload)
    return str(dump_manifest_path.relative_to(REPO_ROOT))


# ---------------------------------------------------------------------------
# Stage 3: Emit synth_seed.json
# ---------------------------------------------------------------------------
def emit_synth_seed(state: dict, selected_shards: list[dict]) -> Path:
    """Write the canonical synth_seed.json from the selected bootstrap shards."""
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
                "why": "Selected shard evidence names this file as part of the active synth frontier.",
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


# ---------------------------------------------------------------------------
# Stage 4: Compile observe_plan.json
# ---------------------------------------------------------------------------
def _probe_questions_for_plan_path(plan_path: Path | None) -> list[str]:
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
    for candidate in _cycle_path_candidates(state, cycle, filename):
        if candidate.exists():
            payload = _load_json(candidate)
            if isinstance(payload, dict):
                return payload
    return {}


def _flatten_text_entries(values: Any) -> list[str]:
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
    """Return structured probe artifacts from the most recent successful cycle.

    Prefer typed receipt sidecars so the planning phase receives compact evidence.
    Falls back to response markdown when no receipt sidecars are present.
    """
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


def _target_effective_size(size: int, scope: str) -> int:
    if str(scope or "").strip() == "outline":
        return min(size // 20, OUTLINE_TARGET_CHAR_CAP)
    return size


def _bounded_target_specs(file_paths: list[str]) -> list[dict[str, str]]:
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
        # Large files get outline scope — structural signatures instead of
        # full content.  This keeps probe prompts under the bridge token
        # budget and avoids fidelity-check failures on huge pastes.
        scope = "outline" if size > OUTLINE_THRESHOLD_BYTES else "full"
        targets.append({"file": rel, "scope": scope})
        # For budget accounting, outline files contribute ~5% of their
        # actual size (the outline is much smaller than the full file).
        effective_size = _target_effective_size(size, scope)
        total_bytes += effective_size
        if len(targets) >= MAX_PROBE_TARGET_FILES:
            break
    return targets


def _probe_questions_for_current_plan(state: dict) -> list[str]:
    plan_path = str(state.get("observe_plan_path") or "").strip()
    if not plan_path:
        return []
    return _probe_questions_for_plan_path(REPO_ROOT / plan_path)


def _existing_shard_statements(state: dict) -> list[str]:
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


def _curate_plan_context(
    *,
    session_context_files: list[str],
    prior_cycle_context_files: list[str],
    prior_probe_artifacts: list[str],
    standards_bundle: dict[str, Any],
    char_budget: int = PLAN_GROUP_CHAR_BUDGET,
    target_chars_used: int = 0,
) -> list[str]:
    """Budget-aware context curation for plan-phase groups.

    Type A responsibility: choose the minimum sufficient context that fits
    within the bridge char budget.  Orientation artifacts (raw_seed_digest,
    large markdown guides) are excluded from implementation/evaluation groups.
    JSON standards are preferred over markdown companions.
    ``target_chars_used`` is subtracted from the budget to account for space
    already consumed by the group's target files.
    """
    char_budget = max(5_000, char_budget - target_chars_used)
    # Orientation artifacts that should never be in plan-phase bridge prompts
    ORIENTATION_BLOCKLIST_FRAGMENTS = [
        "raw_seed_digest",
        "raw_seed_index",
        "system_view.json",
        "focus_directive.json",
    ]

    # Collect candidate files with priorities
    # Priority 1: essential schemas (apply, synth_seed, routing_decision)
    # Priority 2: prior cycle memory (carry_forward, cycle_assimilation, probe receipts)
    # Priority 3: other standards JSON
    # Priority 4: session context
    # Priority 5: markdown companions (lowest priority, drop first)

    essential_patterns = ["std_apply.json", "std_synth_seed.json", "observe_apply_authority_index.json"]
    cycle_memory_patterns = ["carry_forward", "cycle_assimilation", "routing_decision", "receipt.json"]
    markdown_patterns = [".md"]

    all_candidates = _dedupe_strings([
        *[f for f in (standards_bundle.get("context_files") or []) if str(f).strip() and (REPO_ROOT / str(f).strip()).exists()],
        *prior_cycle_context_files,
        *prior_probe_artifacts,
        *session_context_files,
    ])

    def _is_blocked(path: str) -> bool:
        return any(frag in path for frag in ORIENTATION_BLOCKLIST_FRAGMENTS)

    def _priority(path: str) -> int:
        if any(p in path for p in essential_patterns):
            return 1
        if any(p in path for p in cycle_memory_patterns):
            return 2
        if path.endswith(".json") and "std_" in path:
            return 3
        if path.endswith(".json"):
            return 4
        if any(p in path for p in markdown_patterns):
            return 6
        return 5

    filtered = [(p, _priority(p)) for p in all_candidates if not _is_blocked(p)]
    filtered.sort(key=lambda x: x[1])

    curated: list[str] = []
    total_chars = 0
    for path, _prio in filtered:
        abs_path = REPO_ROOT / path
        if not abs_path.exists():
            continue
        size = abs_path.stat().st_size
        if total_chars + size > char_budget:
            continue  # skip, over budget
        curated.append(path)
        total_chars += size

    return curated


def _file_char_count(rel_path: str) -> int:
    abs_path = REPO_ROOT / rel_path
    if not abs_path.exists() or abs_path.is_dir():
        return 0
    try:
        return len(abs_path.read_text(encoding="utf-8", errors="replace"))
    except OSError:
        return 0


def _scope_projection_terms(*texts: str, file_paths: list[str] | None = None) -> list[str]:
    terms: list[str] = []
    for raw_text in texts:
        text = str(raw_text or "").strip().lower()
        if not text:
            continue
        for token in re.findall(r"[a-z0-9_./-]+", text):
            normalized = token.strip("`'\"").strip()
            if len(normalized) < 4 or normalized in SCOPE_PROJECTION_STOPWORDS:
                continue
            terms.append(normalized)
    for rel_path in file_paths or []:
        for token in re.split(r"[/_.-]+", str(rel_path or "").lower()):
            normalized = token.strip()
            if len(normalized) < 4 or normalized in SCOPE_PROJECTION_STOPWORDS:
                continue
            terms.append(normalized)
    return _dedupe_strings(terms)[:40]


def _project_scope_raw_seed_digest(
    *,
    raw_seed_digest_rel: str,
    cycle_dir: Path,
    query_terms: list[str],
    max_chars: int = 28_000,
    max_chunks: int = 14,
) -> str:
    source_path = REPO_ROOT / raw_seed_digest_rel
    payload = _load_json(source_path)
    chunks = list(payload.get("chunks") or [])

    def _projected_chunk(chunk: Mapping[str, Any], *, matched_terms: list[str]) -> dict[str, Any]:
        return {
            "chunk_id": str(chunk.get("chunk_id") or ""),
            "section": str(chunk.get("section") or ""),
            "line_start": int(chunk.get("line_start") or 0),
            "line_end": int(chunk.get("line_end") or 0),
            "char_count": int(chunk.get("char_count") or 0),
            "excerpt": str(chunk.get("excerpt") or "")[:320],
            "matched_terms": matched_terms[:6],
        }

    ordered: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
    for index, chunk in enumerate(chunks):
        haystack = "\n".join(
            [
                str(chunk.get("section") or ""),
                str(chunk.get("excerpt") or ""),
                str(chunk.get("body") or ""),
            ]
        ).lower()
        matched_terms = [term for term in query_terms if term in haystack]
        score = len(matched_terms) * 10
        if index < 3:
            score += 20 - index
        projected = _projected_chunk(chunk, matched_terms=matched_terms)
        ordered.append((score, index, projected, dict(chunk)))

    ordered.sort(key=lambda item: (-item[0], item[1]))
    selected: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    used_chars = 0

    for score, _index, projected, _raw_chunk in ordered:
        chunk_id = projected.get("chunk_id")
        if not chunk_id or chunk_id in seen_ids:
            continue
        if len(selected) >= max_chunks:
            break
        estimated = len(json.dumps(projected, ensure_ascii=False))
        if selected and used_chars + estimated > max_chars:
            continue
        selected.append(projected)
        seen_ids.add(chunk_id)
        used_chars += estimated
        if used_chars >= max_chars:
            break

    if not selected and chunks:
        selected.append(_projected_chunk(chunks[0], matched_terms=[]))

    projection = {
        "generated_at": _utc_now(),
        "kind": "scope_raw_seed_digest_projection",
        "schema_version": "scope_raw_seed_digest_projection_v1",
        "source_path": raw_seed_digest_rel,
        "source_sha256": payload.get("source_sha256"),
        "source_chunk_count": int(payload.get("chunk_count") or len(chunks)),
        "selection_strategy": "excerpt_only_relevance_projection",
        "query_terms": query_terms[:20],
        "included_chunk_count": len(selected),
        "omitted_chunk_count": max(0, len(chunks) - len(selected)),
        "chunks": selected,
    }
    projection_path = cycle_dir / "_scope_raw_seed_digest_projection.json"
    _write_json_atomic(projection_path, projection)
    return str(projection_path.relative_to(REPO_ROOT))


def _project_scope_system_view(
    *,
    system_view_rel: str,
    cycle_dir: Path,
    focus_files: list[str],
    max_chars: int = 24_000,
    max_entries: int = 80,
) -> str:
    source_path = REPO_ROOT / system_view_rel
    payload = _load_json(source_path)
    files = list(payload.get("files") or [])
    focus_paths = _dedupe_strings([str(item).strip() for item in focus_files if str(item).strip()])
    focus_set = set(focus_paths)
    focus_dirs = {str(Path(path).parent) for path in focus_paths if "/" in path}
    focus_roots = {path.split("/", 1)[0] for path in focus_paths}
    include_annexes = any(path.startswith("annexes/") for path in focus_paths)

    root_counts: dict[str, int] = {}
    for item in files:
        rel = str(item.get("path") or "").strip()
        if not rel:
            continue
        top_root = rel.split("/", 1)[0]
        root_counts[top_root] = int(root_counts.get(top_root, 0)) + 1

    def _score(item: Mapping[str, Any]) -> tuple[int, str]:
        rel = str(item.get("path") or "").strip()
        if not rel:
            return (-1000, "")
        top_root = rel.split("/", 1)[0]
        score = 0
        if rel in focus_set:
            score += 100
        parent = str(Path(rel).parent)
        if parent in focus_dirs:
            score += 35
        if top_root in focus_roots:
            score += 10
        if rel.startswith("<private-obsidian-root>/"):
            score += 5
        if rel.endswith(".py"):
            score += 4
        if rel.endswith(".md"):
            score += 2
        if top_root == "annexes" and not include_annexes:
            score -= 50
        return (score, rel)

    projected_entries: list[dict[str, Any]] = []
    used_chars = 0
    for item in sorted(files, key=_score, reverse=True):
        rel = str(item.get("path") or "").strip()
        if not rel:
            continue
        projected = {
            "path": rel,
            "kind": item.get("kind"),
            "bytes": item.get("bytes"),
            "headings": list(item.get("headings") or [])[:6],
        }
        estimated = len(json.dumps(projected, ensure_ascii=False))
        if projected_entries and (len(projected_entries) >= max_entries or used_chars + estimated > max_chars):
            continue
        projected_entries.append(projected)
        used_chars += estimated
        if len(projected_entries) >= max_entries or used_chars >= max_chars:
            break

    if not projected_entries and files:
        first = files[0]
        projected_entries.append(
            {
                "path": str(first.get("path") or ""),
                "kind": first.get("kind"),
                "bytes": first.get("bytes"),
                "headings": list(first.get("headings") or [])[:6],
            }
        )

    projection = {
        "generated_at": _utc_now(),
        "kind": "scope_system_view_projection",
        "schema_version": "scope_system_view_projection_v1",
        "source_path": system_view_rel,
        "source_file_count": int(payload.get("file_count") or len(files)),
        "focus_paths": focus_paths[:30],
        "selection_strategy": "focus_and_directory_priority_projection",
        "top_roots": [
            {"root": root, "count": count}
            for root, count in sorted(root_counts.items(), key=lambda item: (-item[1], item[0]))[:12]
        ],
        "selected_files": projected_entries,
        "omitted_file_count": max(0, len(files) - len(projected_entries)),
    }
    projection_path = cycle_dir / "_scope_system_view_projection.json"
    _write_json_atomic(projection_path, projection)
    return str(projection_path.relative_to(REPO_ROOT))


def _curate_scope_context(
    *,
    session_context_files: list[str],
    cycle_dir: Path,
    scope_files: list[str],
    known_scope_files: list[str],
    synth: Mapping[str, Any],
    standards_bundle: Mapping[str, Any],
    intent_text: str,
    success_criteria: str,
    char_budget: int = SCOPE_CONTEXT_CHAR_BUDGET,
) -> list[str]:
    curated: list[str] = []
    used_chars = 0
    max_context_chars = max(30_000, char_budget)
    query_terms = _scope_projection_terms(
        intent_text,
        success_criteria,
        synth_goal_text(dict(synth)),
        " ".join(str(item.get("question") or "") for item in (synth.get("outstanding_questions") or []) if isinstance(item, dict)),
        file_paths=[*scope_files, *known_scope_files],
    )

    def _append(rel_path: str) -> None:
        nonlocal used_chars
        normalized = str(rel_path or "").strip()
        if not normalized or normalized in curated:
            return
        size = _file_char_count(normalized)
        if size <= 0:
            return
        if curated and used_chars + size > max_context_chars:
            return
        curated.append(normalized)
        used_chars += size

    standards_paths = [
        str(item).strip()
        for item in (standards_bundle.get("context_files") or [])
        if str(item).strip() and (REPO_ROOT / str(item).strip()).exists()
    ]
    for rel_path in standards_paths:
        _append(rel_path)

    synth_paths = [path for path in session_context_files if str(path).strip().endswith("synth_seed.json")]
    for rel_path in synth_paths:
        _append(rel_path)

    for rel_path in session_context_files:
        normalized = str(rel_path).strip()
        if not normalized or normalized in synth_paths:
            continue
        if normalized.endswith("raw_seed_digest.json"):
            source_chars = _file_char_count(normalized)
            projected_rel = (
                _project_scope_raw_seed_digest(
                    raw_seed_digest_rel=normalized,
                    cycle_dir=cycle_dir,
                    query_terms=query_terms,
                )
                if source_chars > 40_000
                else normalized
            )
            _append(projected_rel)
            continue
        if normalized.endswith("system_view.json"):
            source_chars = _file_char_count(normalized)
            projected_rel = (
                _project_scope_system_view(
                    system_view_rel=normalized,
                    cycle_dir=cycle_dir,
                    focus_files=[*scope_files, *known_scope_files],
                )
                if source_chars > 40_000
                else normalized
            )
            _append(projected_rel)
            continue
        _append(normalized)

    return curated


def _plan_phase_seam_groups(
    *,
    plan_targets: list[dict[str, str]],
    session_context_files: list[str],
    prior_cycle_context_files: list[str],
    prior_probe_artifacts: list[str],
    standards_bundle_fn: Any,  # callable returning bundle
    plan_question_fn: Any,  # callable(targets) returning question text
    receipt_schema: Any,
    carry_forward_block: str,
    char_budget: int = PLAN_GROUP_CHAR_BUDGET,
) -> list[dict[str, Any]]:
    """Decompose plan-phase into per-seam probes + receipt synthesis.

    Type A (IDE) curates the graph: which files go to which bridge group,
    what context each group needs, and how synthesis depends on probes.
    Type B (bridge) does bounded analysis on each slice.

    Returns a list of observe groups ready for the plan.
    """
    groups: list[dict[str, Any]] = []

    # Measure target sizes
    sized_targets: list[tuple[dict[str, str], int]] = []
    for spec in plan_targets:
        fp = str(spec.get("file") or "").strip()
        abs_path = REPO_ROOT / fp
        size = abs_path.stat().st_size if abs_path.exists() else 0
        sized_targets.append((spec, size))

    # Bin-pack targets into groups that fit within char_budget
    # Reserve ~40K chars for context files and prompt text
    target_budget = max(10_000, char_budget - 40_000)
    seam_groups: list[list[dict[str, str]]] = []
    current_group: list[dict[str, str]] = []
    current_bytes = 0

    for spec, size in sized_targets:
        effective_size = _target_effective_size(size, str(spec.get("scope") or "").strip())
        if current_group and current_bytes + effective_size > target_budget:
            seam_groups.append(current_group)
            current_group = []
            current_bytes = 0
        current_group.append(spec)
        current_bytes += effective_size

    if current_group:
        seam_groups.append(current_group)

    if not seam_groups:
        seam_groups = [plan_targets]

    def _target_chars(targets: list[dict[str, str]]) -> int:
        total = 0
        for spec in targets:
            fp = str(spec.get("file") or "").strip()
            p = REPO_ROOT / fp
            if fp and p.exists():
                s = p.stat().st_size
                total += _target_effective_size(s, str(spec.get("scope") or "").strip())
        return total

    # If everything fits in one group, use the old single-validator pattern
    if len(seam_groups) == 1:
        bundle = standards_bundle_fn(target_specs=seam_groups[0])
        curated_context = _curate_plan_context(
            session_context_files=session_context_files,
            prior_cycle_context_files=prior_cycle_context_files,
            prior_probe_artifacts=prior_probe_artifacts,
            standards_bundle=bundle,
            char_budget=char_budget,
            target_chars_used=_target_chars(seam_groups[0]),
        )
        groups.append({
            "label": "validator",
            "role": "evaluation",
            "notes": "Produce the final typed plan receipt with executable operations.",
            "question": plan_question_fn(seam_groups[0]),
            "acceptance": "Receipt returns either an apply-ready plan with operations/unified_diff or a concrete reason to continue probing/block.",
            "depends_on": [],
            "targets": seam_groups[0],
            "context_files": curated_context,
            "standards": bundle,
            "response_schema": receipt_schema,
            "json_only": True,
        })
        return groups

    # Multiple seams: emit per-seam analysis probes + final synthesis
    probe_labels: list[str] = []
    for idx, seam_targets in enumerate(seam_groups):
        label = f"plan_seam_{idx + 1}"
        probe_labels.append(label)
        file_names = ", ".join(t.get("file", "?") for t in seam_targets)
        bundle = standards_bundle_fn(target_specs=seam_targets)
        curated_context = _curate_plan_context(
            session_context_files=session_context_files,
            prior_cycle_context_files=prior_cycle_context_files,
            prior_probe_artifacts=prior_probe_artifacts,
            standards_bundle=bundle,
            char_budget=char_budget,
            target_chars_used=_target_chars(seam_targets),
        )
        seam_question = "\n\n".join([
            f"Analyze these files for the changes described in the synth seed: {file_names}",
            "For each concrete change needed, emit an executable operation (replace_block, insert_function, replace_function, etc.) using the schema in std_apply.json.",
            "If a change requires more context than provided, describe what is missing.",
            carry_forward_block,
        ]).strip()
        groups.append({
            "label": label,
            "role": "probe",
            "notes": f"Plan-phase structural analysis for: {file_names}",
            "question": seam_question,
            "acceptance": "Returns executable operations for the target files, or identifies missing context.",
            "depends_on": [],
            "targets": seam_targets,
            "context_files": curated_context,
            "standards": bundle,
            "json_only": True,
        })

    # Synthesis group: reads seam receipts, not raw source
    synthesis_bundle = standards_bundle_fn(
        target_specs=[],
        extra_artifact_kinds=["apply_plan"],
    )
    synthesis_context = _curate_plan_context(
        session_context_files=session_context_files,
        prior_cycle_context_files=prior_cycle_context_files,
        prior_probe_artifacts=[],  # receipts come via depends_on
        standards_bundle=synthesis_bundle,
        char_budget=char_budget,
    )
    synthesis_question = "\n\n".join([
        "You are synthesizing an executable apply plan from the attached seam analysis receipts.",
        "Merge the operations from each seam into a single apply_plan with a non-empty operations list.",
        "Executable means `apply_plan` must contain either a non-empty `operations` list or a non-empty `unified_diff`/`diff`/`patch` string.",
        "Do not return a descriptive edit inventory. Each operation must use one of the allowed_ops from std_apply.json (replace_block, replace_function, insert_function, etc.).",
        "If any seam reported missing context, return `continue_probe` with that gap as reason.",
    ]).strip()
    groups.append({
        "label": "validator",
        "role": "evaluation",
        "notes": "Synthesize seam receipts into a single executable apply plan.",
        "question": synthesis_question,
        "acceptance": "Receipt returns either an apply-ready plan with operations/unified_diff or a concrete reason to continue probing/block.",
        "depends_on": probe_labels,
        "targets": [],
        "context_files": synthesis_context,
        "standards": synthesis_bundle,
        "response_schema": receipt_schema,
        "json_only": True,
    })

    return groups


def compile_observe_plan(state: dict, selected_shards: list[dict]) -> Path:
    """Compile a phase-native observe plan into the active cycle directory."""
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
        """Bin-pack files into bridge-safe probe groups by size.

        Large files (>200KB) get their own probe.  Remaining files are
        packed into groups using a bridge-oriented target budget rather than
        the broader repo-byte ceiling.  This avoids probe groups that pass
        file-count checks but still exceed provider prompt limits once synth
        context and prior-cycle memory are attached.
        """
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

        # Measure file sizes; sort small-first for better packing
        sized: list[tuple[str, int]] = []
        for path in deduped:
            abs_path = REPO_ROOT / path
            size = int(abs_path.stat().st_size) if abs_path.exists() and abs_path.is_file() else 0
            sized.append((path, size))

        LARGE_THRESHOLD = 200_000  # files above this get their own group
        large = [(p, s) for p, s in sized if s > LARGE_THRESHOLD]
        small = [(p, s) for p, s in sized if s <= LARGE_THRESHOLD]

        groups: list[list[str]] = []

        # Large files each get their own probe (most impactful)
        for path, _size in large:
            if len(groups) >= effective_max_chunks:
                break
            groups.append([path])

        target_budget = min(MAX_PROBE_TARGET_BYTES, PROBE_GROUP_TARGET_CHAR_BUDGET)

        # Bin-pack remaining small files
        for path, size in small:
            if len(groups) >= effective_max_chunks:
                # Append to the last group if we're at max
                groups[-1].append(path)
                continue
            # Try to fit in existing non-large group
            placed = False
            for group in groups:
                group_bytes = sum(
                    (REPO_ROOT / p).stat().st_size
                    for p in group
                    if (REPO_ROOT / p).exists()
                )
                if group_bytes + size <= target_budget and len(group) < MAX_PROBE_TARGET_FILES:
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
        scope_intent_text = str(brief.get("intent") or synth_goal_text(synth) or "Advance the active synth seed.").strip()
        scope_success_criteria = str(brief.get("success_criteria") or synth_success_criteria_text(synth) or "").strip()
        scope_question = "\n\n".join(
            [
                f"Intent: {scope_intent_text}",
                f"Success criteria: {scope_success_criteria}",
                "You are running the scope discovery cycle.",
                "Read the synth seed plus the attached raw-seed and system-view orientation artifacts. Identify the smallest concrete sub-universe of files needed for the next probe cycle.",
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
                "context_files": _curate_scope_context(
                    session_context_files=_dedupe_strings(
                        [
                            *list(brief.get("session_context_files") or []),
                            *prior_cycle_context_files,
                        ]
                    ),
                    cycle_dir=cycle_dir,
                    scope_files=scope_files,
                    known_scope_files=known_scope_files,
                    synth=synth,
                    standards_bundle=scope_bundle,
                    intent_text=scope_intent_text,
                    success_criteria=scope_success_criteria,
                ),
                "standards": scope_bundle,
                "response_schema": brief["scope_receipt_schema"],
                "json_only": True,
            }
        )
    elif phase == "plan":
        plan_targets = _bounded_target_specs(scope_files)
        intent_text = brief.get("intent") or synth_goal_text(synth) or "Advance the active synth seed."
        carry_forward_text = _carry_forward_block()

        # Compute prior-cycle context notes for inclusion in question text
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

        def _plan_question_for_targets(targets: list[dict[str, str]]) -> str:
            return "\n\n".join([
                f"Intent: {intent_text}",
                "You are in the planning phase.",
                "Using the attached in-scope files plus the prior probe-cycle routing evidence and probe receipts, produce a kernel-compatible apply plan if the evidence is sufficient.",
                "Executable means `apply_plan` must contain either a non-empty `operations` list or a non-empty `unified_diff`/`diff`/`patch` string.",
                "Do not return a descriptive edit inventory, implementation sketch, or evidence-only plan inside `apply_plan`.",
                "If the plan is not ready, return either `continue_probe` with a concrete reason or `blocked` with the missing precondition.",
                "Verification must be explicit and mechanical where possible.",
                *([prior_cycle_context_note] if prior_cycle_context_note else []),
                *([prior_probe_artifacts_note] if prior_probe_artifacts_note else []),
                render_observe_apply_standards_prompt(
                    _group_standards_bundle(
                        target_specs=targets,
                        extra_artifact_kinds=["cycle_summary", "routing_decision", "apply_plan"],
                    )
                ),
                carry_forward_text,
            ]).strip()

        def _plan_standards_bundle_fn(
            target_specs: list[dict[str, str]],
            extra_artifact_kinds: list[str] | None = None,
        ) -> dict[str, Any]:
            return _group_standards_bundle(
                target_specs=target_specs,
                extra_artifact_kinds=["cycle_summary", "routing_decision", "apply_plan", *(extra_artifact_kinds or [])],
            )

        plan_groups = _plan_phase_seam_groups(
            plan_targets=plan_targets,
            session_context_files=list(brief.get("session_context_files") or []),
            prior_cycle_context_files=prior_cycle_context_files,
            prior_probe_artifacts=prior_probe_artifacts,
            standards_bundle_fn=_plan_standards_bundle_fn,
            plan_question_fn=_plan_question_for_targets,
            receipt_schema=brief["plan_receipt_schema"],
            carry_forward_block=carry_forward_text,
        )
        observe_groups.extend(plan_groups)
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
            # Keep probe question compact — full intent is in synth_seed.json context file.
            short_intent = (brief.get('intent') or synth_goal_text(synth) or 'Advance the active synth seed.')
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
                    "context_files": _curate_plan_context(
                        session_context_files=list(brief.get("session_context_files") or []),
                        prior_cycle_context_files=prior_cycle_context_files,
                        prior_probe_artifacts=prior_probe_artifacts,
                        standards_bundle=probe_bundle,
                        target_chars_used=sum(
                            (
                                _target_effective_size(
                                    (REPO_ROOT / str(item.get("file") or "")).stat().st_size,
                                    str(item.get("scope") or "").strip(),
                                )
                            )
                            for item in target_specs
                            if str(item.get("file") or "").strip() and (REPO_ROOT / str(item.get("file") or "")).exists()
                        ),
                    ),
                    "standards": probe_bundle,
                    "response_schema": brief["probe_receipt_schema"],
                    "json_only": True,
                }
            )

        router_bundle = _group_standards_bundle(target_specs=[], extra_artifact_kinds=["cycle_summary", "routing_decision"])
        short_intent_router = (brief.get('intent') or synth_goal_text(synth) or 'Advance the active synth seed.')
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
                "context_files": _curate_plan_context(
                    session_context_files=list(brief.get("session_context_files") or []),
                    prior_cycle_context_files=prior_cycle_context_files,
                    prior_probe_artifacts=prior_probe_artifacts,
                    standards_bundle=router_bundle,
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


def _phase_id_from_state(state: dict) -> str:
    phase_dir = state["phase_dir"]
    # Extract something like "07_6" from the path
    parts = Path(phase_dir).name.split(" - ")
    if parts:
        return parts[0].replace(".", "_").replace("Phase ", "")
    return "unknown"


# ---------------------------------------------------------------------------
# Stage 5: Execute observe plan
# ---------------------------------------------------------------------------
def execute_observe(
    state: dict,
    *,
    bridge_enabled: bool = False,
    provider: str = "chatgpt",
    launch_profile: str | None = None,
    state_path: Path | None = None,
) -> dict | None:
    """Execute the compiled observe plan via the existing observe session orchestrator.

    If bridge_enabled=False, just compiles artifacts without dispatching.
    """
    plan_path = REPO_ROOT / state["observe_plan_path"]

    runtime_cfg = pipeline_runtime_config(REPO_ROOT)
    effective_launch_profile = normalize_launch_profile(
        launch_profile,
        default=str(runtime_cfg["default_launch_profile"]),
    )
    provider_capability_cap = (
        provider_ceiling_for_provider(provider, REPO_ROOT / "tools/meta/bridge/provider_capabilities.json")
        or int(observe_runtime_policy(REPO_ROOT).get("max_workers_ceiling") or 1)
    )

    if not bridge_enabled:
        print("[INFO] Bridge not enabled. Observe plan compiled at:", plan_path)
        print(
            "[INFO] To dispatch: python3 run_observe.py --plan",
            state["observe_plan_path"],
            "--bridge --provider",
            provider,
            "--launch-profile",
            effective_launch_profile,
        )
        state["stage"] = "observe_dispatched"
        state["current_cycle_timeline_path"] = _cycle_timeline_rel(state)
        _record_cycle_event(
            state,
            "observe_dispatch_skipped",
            provider=provider,
            launch_profile=effective_launch_profile,
            reason="bridge_disabled",
            observe_plan_path=state.get("observe_plan_path"),
        )
        _log(state, "execute_observe", "Plan compiled but bridge not enabled. Manual dispatch needed.")
        if state_path is not None:
            save_state_if_not_stale(state, state_path)
        return None

    # Import the observe machinery
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from tools.meta.apply.run_observe_plan import run_once
    except ImportError as e:
        print(f"[ERROR] Cannot import observe machinery: {e}", file=sys.stderr)
        state["stage"] = "observe_dispatched"
        _log(state, "execute_observe", f"Import failed: {e}")
        return None

    # Build paths for run_once — it expects repo_root-relative Path objects
    plan = json.loads(plan_path.read_text())
    plan_groups = plan.get("groups") if isinstance(plan.get("groups"), list) else []
    worker_resolution = resolve_effective_workers(
        repo_root=REPO_ROOT,
        requested_workers=provider_capability_cap,
        launch_profile=effective_launch_profile,
        wave_size=max(1, len(plan_groups) or 1),
        provider=provider,
    )
    provider_worker_cap = int(worker_resolution["effective_workers"])
    result_note_path = plan.get("result_note_path", str(Path(state["phase_dir"]) / f"Pass {state['cycle'] + 1} Observe Result.md"))

    # Ensure dump_dir exists before dispatch
    dump_dir = plan.get("dump_dir", f"tools/meta/apply/observe_dumps/{_phase_id_from_state(state)}_cycle_{state['cycle']}")
    (REPO_ROOT / dump_dir).mkdir(parents=True, exist_ok=True)

    print(f"[BRIDGE] Dispatching observe plan via {provider}...")
    print(f"[BRIDGE] Dump dir: {dump_dir}")
    print(f"[BRIDGE] Worker cap: {provider_worker_cap}")
    print(f"[BRIDGE] This may take several minutes per probe group.")

    # Persist the dispatch boundary before the long-running bridge call starts so
    # cron or later agents do not mistake the plan as still undispatched.
    state["stage"] = "observe_dispatched"
    state["observe_session_id"] = None
    state["observe_manifest_path"] = None
    state["observe_dispatch_started_at"] = _utc_now()
    state["observe_dispatch_status"] = "in_progress"
    state["observe_dispatch_error"] = None
    state["current_cycle_timeline_path"] = _cycle_timeline_rel(state)
    _record_cycle_event(
        state,
        "observe_dispatch_started",
        provider=provider,
        launch_profile=effective_launch_profile,
        observe_plan_path=state.get("observe_plan_path"),
        dump_dir=dump_dir,
        bridge_workers=provider_worker_cap,
    )
    _log(state, "execute_observe", f"Bridge dispatch started via {provider}")
    if state_path is not None:
        save_state(state, state_path)

    # Execute with run_once's actual signature.
    # Request adaptive worker selection so grouped observe can fan out across
    # dependency-safe waves instead of pinning every cycle to serial dispatch.
    # bridge_timeout_s=360: give complex probes a bit more headroom.
    try:
        result = run_once(
            repo_root=REPO_ROOT,
            plan_path=plan_path,
            result_path=REPO_ROOT / result_note_path,
            history_dir=REPO_ROOT / "tools/meta/apply/observe_history",
            sentence_count=None,
            sticky_dump_dir=False,
            bridge_enabled=True,
            bridge_provider=provider,
            bridge_max_chars=400000,
            bridge_timeout_s=360.0,
            bridge_workers=provider_worker_cap,
            launch_profile=effective_launch_profile,
            cancel_event=threading.Event(),
        )
    except Exception as exc:
        reason = str(exc).strip() or exc.__class__.__name__
        _mark_observe_dispatch_failed(
            state,
            provider=provider,
            launch_profile=effective_launch_profile,
            dump_dir=dump_dir,
            reason=reason,
            state_path=state_path,
        )
        raise

    if not result or not str(result.get("observe_id") or "").strip():
        _mark_observe_dispatch_failed(
            state,
            provider=provider,
            launch_profile=effective_launch_profile,
            dump_dir=dump_dir,
            reason="run_once_returned_without_observe_id",
            state_path=state_path,
        )
        return None

    state["observe_session_id"] = result.get("observe_id")
    state["observe_manifest_path"] = _resolve_observe_record_path(state, result=result)
    state["observe_dispatch_status"] = "materialized"
    state["observe_dispatch_error"] = None
    _mirror_observe_record_into_dump_manifest(
        record_rel=state.get("observe_manifest_path"),
        fallback_dump_dir=dump_dir,
    )

    state["stage"] = "observe_dispatched"
    _record_cycle_event(
        state,
        "observe_dispatch_checkpointed",
        observe_session_id=result.get("observe_id") if result else None,
        observe_manifest_path=state.get("observe_manifest_path"),
        dump_dir=dump_dir,
    )
    _log(state, "execute_observe", f"Session dispatched: {result.get('observe_id', 'unknown')}")
    if state_path is not None:
        save_state_if_not_stale(state, state_path)
    return result


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


def _active_phase(state: dict) -> str:
    return str(state.get("phase") or state.get("controller_phase") or "scope").strip() or "scope"


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


def _coerce_text_list(values: Any) -> list[str]:
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
    priority_followup_files = _priority_followup_files(
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
            "priority_followup_files": priority_followup_files,
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
    # Typed event items per Mem0 ADD/UPDATE/RETAIN delta pattern.
    # ADD = new-this-cycle evidence; RETAIN = stable structural notes.
    # _coerce_text_list extracts .text so old consumers still get plain strings.
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
    priority_followup_files = _priority_followup_files(
        known_files=known_scope,
        active_scope_files=active_scope,
        missing_evidence=aggregate.get("missing_evidence"),
        known_universe_files=(
            aggregate.get("priority_followup_files")
            or aggregate.get("known_universe_files_outside_active_scope")
        ),
        extra_texts=_coerce_text_list(carry_forward_notes),
    )
    if priority_followup_files:
        carry_forward_notes.append(
            {
                "event": "RETAIN",
                "text": "Priority follow-up files: " + ", ".join(priority_followup_files[:8]),
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
        "priority_followup_files": priority_followup_files,
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
    """Read observe results, trust typed receipts for active runs, and advance phase-native state."""
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

    atomization_import: dict[str, Any] | None = None
    if str(state.get("mission_id") or "").strip() == "raw_seed_atomization":
        family_dir = str(state.get("family_dir") or "").strip()
        if family_dir:
            try:
                atomization_import = import_atomization_session_results(
                    family_dir=family_dir,
                    manifest=manifest,
                    plan=plan,
                    repo_root=REPO_ROOT,
                    observe_id=str(state.get("observe_session_id") or "").strip() or None,
                    source_plan_path=str(state.get("observe_plan_path") or "").strip() or None,
                )
            except Exception as exc:
                atomization_import = {
                    "status": "error",
                    "error": str(exc),
                    "observe_id": str(state.get("observe_session_id") or "").strip() or None,
                }

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
        # Capture error details for every group (not just degraded)
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
        # Capture bridge transport info if available
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
    selected_signature = _selected_signature(selected_shard_ids)
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
        selected_signature=selected_signature,
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
        "selected_signature": selected_signature,
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
        "atomization_import": atomization_import,
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

            selected_signature = str(existing_summary.get("selected_signature") or "").strip()
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
                    selected_signature=selected_signature,
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


# ---------------------------------------------------------------------------
# Full loop runner
# ---------------------------------------------------------------------------
def run_step(
    state: dict,
    *,
    bridge_enabled: bool = False,
    provider: str = "chatgpt",
    launch_profile: str | None = None,
    auto: bool = False,
    state_path: Path | None = None,
) -> str:
    """Execute the next step in the pipeline. Returns the new stage."""
    ensure_controller_state(state, repo_root=REPO_ROOT)
    stage = state["stage"]

    if stage == "init":
        extract_shards(state, bridge_fn=_get_bridge_fn() if bridge_enabled else None, provider=provider)
    elif stage == "shards_extracted":
        select_shards(state)
    elif stage == "shards_selected":
        shards_data = json.loads((REPO_ROOT / state["shards_path"]).read_text())
        selected = [s for s in shards_data["shards"] if s.get("status") == "selected"]
        emit_synth_seed(state, selected)
    elif stage == "synth_seed_emitted":
        if state.get("shards_path"):
            shards_data = json.loads((REPO_ROOT / state["shards_path"]).read_text())
            selected = [s for s in shards_data["shards"] if s.get("status") == "selected"]
        else:
            # synth-seed-first init: pull source_shards directly from the synth seed
            synth_p = state.get("synth_seed_path")
            synth_data = json.loads((REPO_ROOT / synth_p).read_text()) if synth_p else {}
            selected = synth_data.get("source_shards", [])
        compile_observe_plan(state, selected)
    elif stage == "observe_plan_compiled":
        execute_observe(
            state,
            bridge_enabled=bridge_enabled,
            provider=provider,
            launch_profile=launch_profile,
            state_path=state_path,
        )
    elif stage == "observe_dispatched":
        process_results(state)
    elif stage in ("results_processed", "cycle_complete"):
        if controller_gate_active(state):
            print(f"[GATE] Controller requested review: {state.get('gate_reason')}")
            return state["stage"]
        if auto:
            print(f"[AUTO] Cycle {state['cycle']} complete — advancing to next cycle")
            if _should_redrive_mission_launch(state):
                _rearm_mission_launch_plan(state)
            elif state.get("synth_seed_path"):
                state["stage"] = "synth_seed_emitted"
                compile_observe_plan(state, [])
            else:
                state["stage"] = "shards_extracted"
                select_shards(state)
        elif stage == "results_processed":
            print(f"[GATE] Cycle {state['cycle']} complete.")
            print(f"[GATE] Review results, then either:")
            print(f"  --step again to compile the next cycle")
            print(f"  --approve to move to apply planning")
            state["stage"] = "cycle_complete"
        else:
            if state.get("synth_seed_path"):
                state["stage"] = "synth_seed_emitted"
                compile_observe_plan(state, [])
            else:
                state["stage"] = "shards_extracted"
                select_shards(state)
    elif stage == "apply_ready":
        print("[GATE] Apply plan ready. Review apply_plan.json and apply_packet.json before --approve.")
    elif stage == "apply_approved":
        print("[INFO] Apply approved. Executing apply...")
        _execute_approved_apply_plan(state)
    else:
        print(f"[ERROR] Unknown stage: {stage}")

    return state["stage"]


def _execute_approved_apply_plan(state: dict) -> dict[str, Any]:
    """Execute the controller-approved apply plan and record the result."""
    from tools.meta import apply as meta_apply

    plan_rel = str(state.get("apply_plan_path") or "").strip()
    if not plan_rel:
        raise ValueError("apply_approved state is missing apply_plan_path")
    plan_path = REPO_ROOT / plan_rel
    if not plan_path.exists():
        raise FileNotFoundError(f"Apply plan not found: {plan_rel}")

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    result = meta_apply.run(
        {
            "mode": "apply",
            "plan": plan if isinstance(plan, dict) else {},
            "dry_run": False,
            "capture_diffs": True,
            "root_hint": str(REPO_ROOT),
        }
    )
    result_rel = str(state.get("apply_result_path") or "").strip()
    if not result_rel:
        result_rel = str((REPO_ROOT / state["phase_dir"] / "apply_result.json").relative_to(REPO_ROOT))
    result_path = REPO_ROOT / result_rel
    _write_json_atomic(result_path, result)
    state["apply_result_path"] = result_rel

    status = str(result.get("metadata", {}).get("status") or "").strip().lower()
    data = result.get("data") if isinstance(result.get("data"), dict) else {}
    failures = list(data.get("failures") or []) if isinstance(data, dict) else []
    if status == "success" and not failures:
        state["stage"] = "cycle_complete"
        state["gate_reason"] = "none"
        _log(state, "apply_execute", f"Applied {plan_rel}; result written to {result_rel}")
        return result

    state["stage"] = "apply_ready"
    state["gate_reason"] = "apply_review_pending"
    _log(state, "apply_execute_failed", f"Apply failed for {plan_rel}; result written to {result_rel}")
    return result


# ---------------------------------------------------------------------------
# Gate helpers — retry / continuous loop
# ---------------------------------------------------------------------------

#: Gates that are transient (bridge noise, timing) and safe to retry.
RETRYABLE_GATES = {"error_spike_block", "uncertainty_block"}
#: Gates that genuinely require a human decision before the loop can continue.
HUMAN_GATES = {"apply_review_pending", "contradiction_block"}


def gate_is_retryable(state: dict) -> bool:
    """Return True when the current gate is transient and can be auto-cleared."""
    return str(state.get("gate_reason") or "").strip() in RETRYABLE_GATES


def reset_transient_gate(state: dict, *, reason: str = "auto_retry") -> None:
    """Clear a transient gate and restore the pipeline to probe phase.

    Increments ``retry_count`` so the continuous loop can bail after too many
    retries.  Also resets the ``zero_evolution_streak`` counter from the most
    recent cycle summary so a fresh dispatch starts clean.
    """
    state["gate_reason"] = "none"
    state["failed_transitions"] = []
    # Restore the phase that should be retried next (default: probe).
    resume_phase = str(state.get("retry_resume_phase") or "probe").strip() or "probe"
    if resume_phase == "blocked":
        resume_phase = "probe"
    for key in ("phase", "controller_phase", "current_layer_kind"):
        state[key] = resume_phase
    rev = int(state.get("scope_revision") or 0)
    depth = int(state.get("phase_depth") or 0)
    state["current_layer_id"] = f"{resume_phase}_rev{rev}_d{depth}"
    state["stage"] = "cycle_complete"
    state.pop("retry_resume_phase", None)

    # Zero-out the evolution streak in the last cycle summary so the controller
    # doesn't re-block immediately after the first clean dispatch.
    cycle_dir = _cycle_dir_path(state)
    summary_path = cycle_dir / "_cycle_summary.json"
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
            summary["zero_evolution_streak"] = 0
            summary["degraded_groups"] = []
            _write_json_atomic(summary_path, summary)
        except Exception:
            pass

    state.setdefault("retry_count", 0)
    state["retry_count"] = int(state.get("retry_count") or 0) + 1
    state["updated_at"] = _utc_now()
    _log(state, "reset_transient_gate", f"{reason}: gate cleared, retry_count={state['retry_count']}")


def run_continuous(
    state: dict,
    *,
    bridge_enabled: bool = False,
    provider: str = "chatgpt",
    launch_profile: str | None = None,
    max_cycles: int = 20,
    max_retries: int = 3,
    state_path: Path | None = None,
) -> str:
    """Run the pipeline continuously, auto-retrying transient gates.

    Stops only when:
    - A human gate (apply_review_pending / contradiction_block) fires.
    - The controller advances to apply_ready.
    - max_retries transient gate resets have been exhausted.
    - max_cycles total bridge cycles have run.

    Returns the final stage name.
    """
    retries_used = 0
    cycles_this_run = 0

    while cycles_this_run < max_cycles:
        # ---- single pass until any gate or cycle limit ----
        run_loop(
            state,
            bridge_enabled=bridge_enabled,
            provider=provider,
            launch_profile=launch_profile,
            max_cycles=max_cycles - cycles_this_run,
            auto=True,
            state_path=state_path,
        )
        stage = state["stage"]

        # Track how many bridge cycles happened
        cycles_this_run = int(state.get("cycle", 0))

        # ---- apply / human gate → stop and hand off to human ----
        gate = str(state.get("gate_reason") or "").strip()
        if stage == "apply_ready" or gate in HUMAN_GATES:
            print(f"\n[CONTINUOUS] Stopping: human gate '{gate or stage}'. Review and --approve to proceed.")
            break

        # ---- transient gate → maybe retry ----
        if gate_is_retryable(state):
            if retries_used >= max_retries:
                print(f"\n[CONTINUOUS] Max retries ({max_retries}) exhausted on gate '{gate}'. Stopping.")
                break
            retries_used += 1
            print(f"\n[CONTINUOUS] Transient gate '{gate}' — retry {retries_used}/{max_retries}. Resetting…")
            reset_transient_gate(state, reason=f"continuous_retry_{retries_used}")
            if state_path is not None:
                save_state(state, state_path)
            continue

        # ---- clean stop (no gate, loop hit max_cycles) ----
        print(f"\n[CONTINUOUS] Loop complete. Stage: {stage}")
        break

    return state["stage"]


def run_loop(
    state: dict,
    *,
    bridge_enabled: bool = False,
    provider: str = "chatgpt",
    launch_profile: str | None = None,
    max_cycles: int = 3,
    auto: bool = False,
    state_path: Path | None = None,
) -> None:
    """Run the full pipeline loop until a gate or max_cycles.

    If auto=True, skips cycle gates and auto-advances (still stops at apply_ready).
    """
    cycles_done = 0
    last_cycle = state.get("cycle", 0)
    while cycles_done < max_cycles:
        stage = run_step(
            state,
            bridge_enabled=bridge_enabled,
            provider=provider,
            launch_profile=launch_profile,
            auto=auto,
            state_path=state_path,
        )
        print(f"  → Stage: {stage}")

        # Track cycle completion
        if state.get("cycle", 0) > last_cycle:
            last_cycle = state["cycle"]
            cycles_done += 1
            if cycles_done >= max_cycles:
                print(f"\n[STOP] Reached max_cycles={max_cycles}")
                break
            print(f"\n--- Cycle {state['cycle']} ---")

        if stage == "cycle_complete" and not auto:
            print(f"\n[GATE] Cycle complete. Use --auto to auto-advance.")
            break

        if stage in ("apply_ready",) or controller_gate_active(state):
            print(f"\n[GATE] Apply ready. Use --approve to proceed.")
            break

        if stage in ("apply_approved",):
            break


def _load_master_config() -> dict:
    """Load master_config.json for bridge configuration."""
    config_path = REPO_ROOT / "master_config.json"
    if config_path.exists():
        return json.loads(config_path.read_text())
    return {}


def _get_bridge_fn():
    """Load the bridge callable."""
    sys.path.insert(0, str(REPO_ROOT))
    try:
        from system.core.bridge import ask_ai
        return ask_ai
    except ImportError:
        return None


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    runtime_cfg = pipeline_runtime_config(REPO_ROOT)
    parser = argparse.ArgumentParser(description="End-to-end seed pipeline runner")
    parser.add_argument("--init", action="store_true", help="Initialize pipeline from an authored subphase synth seed")
    parser.add_argument("--step", action="store_true", help="Run the next pipeline step")
    parser.add_argument("--run", action="store_true", help="Run the full loop until gate")
    parser.add_argument("--status", action="store_true", help="Show current pipeline state")
    parser.add_argument("--approve", action="store_true", help="Approve apply gate")
    parser.add_argument("--digest", type=str, metavar="RAW_SEED_PATH", help="Preview digest of a raw seed (compression for bridge)")
    parser.add_argument("--analytics", action="store_true", help="Emit controller analytics from cycle history and task backlog")
    parser.add_argument(
        "--curate",
        choices=["show-stale", "merge-similar", "retire-answered", "promote", "set-status"],
        help="Run a controller backlog curation action",
    )
    parser.add_argument("--directive", type=str, help="Inline JSON or a JSON file path for a one-shot orchestrator focus directive")
    parser.add_argument("--task-id", type=str, help="Task id for --curate promote|set-status")
    parser.add_argument("--task-status", type=str, help="Task status for --curate set-status")

    parser.add_argument("--raw-seed", type=str, help="Optional family raw_seed.md path override (for --init)")
    parser.add_argument("--phase-dir", type=str, help="Phase directory (for --init)")
    parser.add_argument("--family-dir", type=str, help="Family directory (for --init, optional)")
    parser.add_argument("--state", type=str, default=None, help="Path to pipeline state JSON")
    parser.add_argument("--bridge", action="store_true", help="Enable bridge dispatch")
    parser.add_argument("--provider", type=str, default="chatgpt", help="Bridge provider")
    parser.add_argument(
        "--launch-profile",
        type=str,
        default=str(runtime_cfg["default_launch_profile"]),
        help="Observe launch profile for bridge dispatch (safe or experimental).",
    )
    parser.add_argument("--max-cycles", type=int, default=3, help="Max cycles before stopping")
    parser.add_argument("--auto", action="store_true", help="Skip cycle gates and auto-advance (still stops at apply)")
    parser.add_argument("--continuous", action="store_true",
                        help="Run autonomously, auto-retrying transient gates (error_spike/uncertainty) up to --max-retries times. Stops only at apply_review_pending or contradiction_block.")
    parser.add_argument("--max-retries", type=int, default=3,
                        help="Max transient gate resets before --continuous stops (default: 3)")
    parser.add_argument("--retry-gate", action="store_true",
                        help="Clear the current transient gate and reset to probe phase, then exit")
    parser.add_argument("--ingest-session", type=str, metavar="MANIFEST_PATH",
                        help="Ingest a manually-dispatched observe session manifest into pipeline state")
    parser.add_argument("--add-shard", type=str, metavar="STATEMENT",
                        help="Inject a new shard with the given clarified_statement")
    parser.add_argument("--shard-group", type=str, default=None,
                        help="Concept group for --add-shard (auto-detected if not given)")
    parser.add_argument("--shard-files", type=str, nargs="*", default=[],
                        help="Relevant files for --add-shard")
    parser.add_argument("--dashboard", action="store_true",
                        help="Show compact pipeline dashboard")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if args.digest:
        raw_path = REPO_ROOT / args.digest
        if not raw_path.exists():
            print(f"[ERROR] File not found: {raw_path}", file=sys.stderr)
            sys.exit(1)
        raw_text = raw_path.read_text()
        digested = digest_raw_seed(raw_text)
        print(f"Original: {len(raw_text)} chars ({len(raw_text.splitlines())} lines)")
        print(f"Digest:   {len(digested)} chars ({len(digested.splitlines())} lines)")
        print(f"Ratio:    {len(digested)/len(raw_text)*100:.1f}%")
        print("---")
        print(digested)
        return

    if args.init:
        if not args.phase_dir:
            parser.error("--init requires --phase-dir")
        state = init_state(args.raw_seed or "", args.phase_dir, args.family_dir)
        write_controller_artifacts(state, repo_root=REPO_ROOT)

        # Determine state file path
        state_path = Path(args.state) if args.state else (REPO_ROOT / args.phase_dir / "pipeline_state.json")
        save_state(state, state_path)
        print(f"Pipeline initialized: {state['pipeline_id']}")
        print(f"State file: {state_path}")
        if args.json:
            print(json.dumps(state, indent=2))
        return

    # All other commands need state — auto-discover if not provided
    if not args.state:
        state_path = _find_latest_state()
        if not state_path:
            parser.error("--state required (or place pipeline_state.json in an active phase dir)")
        print(f"[AUTO] Found state: {state_path.relative_to(REPO_ROOT)}")
    else:
        state_path = Path(args.state)
        if not state_path.is_absolute():
            state_path = REPO_ROOT / state_path

    if not state_path.exists():
        print(f"[ERROR] State file not found: {state_path}", file=sys.stderr)
        sys.exit(1)

    state = load_state(state_path)
    write_controller_artifacts(state, repo_root=REPO_ROOT)

    if args.status:
        print(f"Pipeline: {state['pipeline_id']}")
        print(f"Stage:    {state['stage']}")
        print(f"Cycle:    {state['cycle']}")
        print(f"Controller: {state.get('controller_version')} / {state.get('controller_phase')}")
        print(f"Layer:      {state.get('current_layer_kind')} / {state.get('current_layer_id')}")
        print(f"Task:       {state.get('current_task_id')}")
        print(f"Gate:       {state.get('gate_reason')}")
        if state.get("routing_decision"):
            print(f"Routing:    {(state.get('routing_decision') or {}).get('decision')}")
        print(f"Confidence: {state.get('confidence_score')} | Uncertainty: {state.get('uncertainty_score')}")
        print(f"Updated:  {state['updated_at']}")
        print(f"Raw seed: {state['raw_seed_path']}")
        if state.get("shards_path"):
            shards_data = json.loads((REPO_ROOT / state["shards_path"]).read_text())
            total = len(shards_data["shards"])
            selected = sum(1 for s in shards_data["shards"] if s.get("status") == "selected")
            print(f"Shards:   {selected} selected / {total} total")
        if state.get("observe_plan_path"):
            print(f"Plan:     {state['observe_plan_path']}")
        print(f"\nHistory ({len(state['history'])} entries):")
        for entry in state["history"][-5:]:
            print(f"  [{entry['timestamp'][:19]}] {entry['action']}: {entry['detail']}")
        if args.json:
            print(json.dumps(state, indent=2))
        return

    if args.analytics:
        report = analytics_report(state, repo_root=REPO_ROOT)
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print(json.dumps(report, indent=2))
        save_state(state, state_path)
        return

    if args.directive:
        directive_token = args.directive
        try:
            directive_payload = json.loads(directive_token)
        except json.JSONDecodeError:
            directive_path = REPO_ROOT / directive_token
            if not directive_path.exists():
                print(f"[ERROR] Directive file not found: {directive_path}", file=sys.stderr)
                sys.exit(1)
            directive_payload = json.loads(directive_path.read_text(encoding="utf-8"))
        write_focus_directive(state, directive_payload, repo_root=REPO_ROOT)
        save_state(state, state_path)
        print("Directive written.")
        if args.json:
            print(json.dumps(directive_payload, indent=2))
        return

    if args.curate:
        result = curate_backlog(
            state,
            args.curate,
            repo_root=REPO_ROOT,
            task_id=args.task_id,
            task_status=args.task_status,
        )
        save_state(state, state_path)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(json.dumps(result, indent=2))
        return

    if args.ingest_session:
        manifest_rel = args.ingest_session
        manifest_abs = REPO_ROOT / manifest_rel
        if not manifest_abs.exists():
            print(f"[ERROR] Manifest not found: {manifest_abs}", file=sys.stderr)
            sys.exit(1)
        manifest = json.loads(manifest_abs.read_text())
        state["observe_session_id"] = manifest.get("observe_id")
        state["observe_manifest_path"] = manifest_rel
        if state["stage"] in ("observe_plan_compiled", "observe_dispatched"):
            state["stage"] = "observe_dispatched"
        _log(state, "ingest_session", f"Ingested session {manifest.get('observe_id', '?')} from {manifest_rel}")
        save_state(state, state_path)
        print(f"Ingested session: {manifest.get('observe_id')}")
        print(f"Stage: {state['stage']}")
        return

    if args.dashboard:
        import subprocess
        result = subprocess.run(
            ["python3", "run_control_room.py"] + (["--json"] if args.json else []),
            capture_output=False, cwd=str(REPO_ROOT),
        )
        return

    if args.add_shard:
        if not state.get("shards_path"):
            print("[ERROR] No shards file in pipeline state. Run --init and --step first.", file=sys.stderr)
            sys.exit(1)
        shards_data = json.loads((REPO_ROOT / state["shards_path"]).read_text())
        next_num = len(shards_data["shards"]) + 1
        new_id = f"SHARD_{next_num:03d}"
        concept = args.shard_group or _guess_concept_group(args.add_shard)
        new_shard = {
            "id": new_id,
            "raw_seed_anchor": "injected via --add-shard CLI",
            "clarified_statement": args.add_shard,
            "concept_group": concept,
            "intent_provenance": ["cli_injection"],
            "relevant_files": args.shard_files,
            "status": "pending",
        }
        shards_data["shards"].append(new_shard)
        (REPO_ROOT / state["shards_path"]).write_text(json.dumps(shards_data, indent=2) + "\n")
        _log(state, "add_shard", f"Injected {new_id}: {args.add_shard[:60]}...")
        write_controller_artifacts(state, repo_root=REPO_ROOT)
        save_state(state, state_path)
        print(f"Added {new_id} ({concept}): {args.add_shard[:80]}")
        if args.json:
            print(json.dumps(new_shard, indent=2))
        return

    if args.approve:
        state["stage"] = "apply_approved"
        state["gate_reason"] = "none"
        save_state(state, state_path)
        print("Apply approved.")
        return

    if args.retry_gate:
        gate = str(state.get("gate_reason") or "").strip()
        if not gate or gate == "none":
            print("[INFO] No active gate to clear.")
        elif gate_is_retryable(state):
            reset_transient_gate(state, reason="manual_retry_gate")
            save_state(state, state_path)
            print(f"Gate '{gate}' cleared. Stage: {state['stage']}")
        else:
            print(f"[WARN] Gate '{gate}' is not auto-retryable (requires human review). Use --approve.")
        return

    if args.continuous:
        final = run_continuous(
            state,
            bridge_enabled=args.bridge,
            provider=args.provider,
            launch_profile=args.launch_profile,
            max_cycles=args.max_cycles,
            max_retries=args.max_retries,
            state_path=state_path,
        )
        save_state(state, state_path)
        print(f"\nFinal stage: {final}")
        if args.json:
            print(json.dumps(state, indent=2))
        return

    if args.step:
        new_stage = run_step(
            state,
            bridge_enabled=args.bridge,
            provider=args.provider,
            launch_profile=args.launch_profile,
            auto=args.auto,
            state_path=state_path,
        )
        save_state(state, state_path)
        print(f"Stage: {state['stage']}")
        if args.json:
            print(json.dumps(state, indent=2))
        return

    if args.run:
        run_loop(
            state,
            bridge_enabled=args.bridge,
            provider=args.provider,
            launch_profile=args.launch_profile,
            max_cycles=args.max_cycles,
            auto=args.auto,
            state_path=state_path,
        )
        save_state(state, state_path)
        print(f"\nFinal stage: {state['stage']}")
        if args.json:
            print(json.dumps(state, indent=2))
        return

    parser.print_help()


if __name__ == "__main__":
    main()
