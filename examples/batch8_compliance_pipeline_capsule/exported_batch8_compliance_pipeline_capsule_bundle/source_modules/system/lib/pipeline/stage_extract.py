"""
[PURPOSE]
- Teleology: Extract the shard frontier from `raw_seed.md` and host the shared normalization helpers that later pipeline stages reuse.
- Mechanism: Read the family raw seed, optionally compress it for bridge extraction, fall back to local rule-based extraction, and centralize shard/cycle helper utilities used across select/compile/process stages.

[INTERFACE]
- Exports: extract_shards, digest_raw_seed.
- Reads: The active phase's `raw_seed.md`, controller state, and optional bridge-extraction responses.
- Writes: `extracted_shards.json`, controller artifacts, and shared cycle metadata through helper utilities.

[FLOW]
- Read `raw_seed.md` -> choose bridge or local extraction -> normalize and persist shard artifacts -> expose shared shard, cycle, and synthesis helper utilities for the downstream stages.

[DEPENDENCIES]
- Couples: `system.lib.json_payloads` supplies JSON recovery heuristics used when bridge extraction returns malformed payloads.
- Couples: `system.lib.seed_pipeline_controller` persists controller artifacts that make extracted shards visible to later stage transitions.
- Couples: `tools.meta.apply.run_observe_plan` and bridge-facing helpers shape the optional AI extraction path.

[CONSTRAINTS]
- Guarantee: Stage-1 extraction writes a canonical `extracted_shards.json` artifact and refreshes controller state so later stages work from a durable shard frontier.
- Non-goal: This module does not decide shard selection or compile observe plans; it establishes the shard substrate and the shared helpers those later stages consume.
- When-needed: Open when a pipeline loop needs the raw-seed extraction stage or the shared shard/cycle helpers that later stages import.
- Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline/stage_compile.py; system/lib/phase_harbor.py
- Navigation-group: kernel_lib
"""
from __future__ import annotations

import json
import re
import sys
import threading
from datetime import datetime, timezone
from difflib import SequenceMatcher
from hashlib import sha256
from pathlib import Path
from typing import Any


def _lazy_repo_root() -> Path:
    from seed_pipeline import REPO_ROOT
    return REPO_ROOT


def _lazy_utc_now() -> str:
    from seed_pipeline import _utc_now
    return _utc_now()


def _lazy_write_json_atomic(path: Path, payload: Any) -> Path:
    from seed_pipeline import _write_json_atomic
    return _write_json_atomic(path, payload)


def _lazy_log(state: dict, action: str, detail: str) -> None:
    from seed_pipeline import _log
    _log(state, action, detail)


def _lazy_load_json(path: Path) -> dict | None:
    from seed_pipeline import _load_json
    return _load_json(path)


def _lazy_dedupe_strings(values: list[str]) -> list[str]:
    from seed_pipeline import _dedupe_strings
    return _dedupe_strings(values)


# ---------------------------------------------------------------------------
# Constants (mirrored from seed_pipeline.py)
# ---------------------------------------------------------------------------

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
MAX_PROBE_TARGET_FILES = 8
MAX_PROBE_TARGET_BYTES = 500_000
NEW_SHARD_EXISTING_SIMILARITY = 0.88
NEW_SHARD_PROMPT_SIMILARITY = 0.82


# ---------------------------------------------------------------------------
# Stage 1: Extract shards from raw_seed
# ---------------------------------------------------------------------------
def extract_shards(state: dict, *, bridge_fn=None, provider: str = "chatgpt") -> list[dict]:
    """
    [ACTION]
    - Teleology: Build the phase's first durable shard frontier from the current `raw_seed.md`.
    - Mechanism: Read the raw seed, choose bridge-backed or local extraction, write `extracted_shards.json`, and update controller state to the `shards_extracted` stage.
    - Reads: `state["raw_seed_path"]`, optional `bridge_fn`, and controller helpers from `system.lib.seed_pipeline_controller`.
    - Writes: `extracted_shards.json`, controller artifacts, and stage metadata in `state`.
    - Guarantee: Returns the extracted shard list and leaves the pipeline state pointing at the canonical shards artifact on disk.
    - Fails: Propagates raw-seed read failures; bridge extraction parse failures degrade into local extraction.
    - When-needed: Open when a caller needs the authoritative stage-1 shard extraction path from the current raw seed.
    - Escalates-to: system/lib/pipeline/stage_select.py; system/lib/pipeline/stage_compile.py; system/lib/phase_harbor.py
    - Navigation-group: kernel_lib
    """
    from seed_pipeline import REPO_ROOT, _utc_now, _log
    from system.lib.seed_pipeline_controller import write_controller_artifacts

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
    """
    [ACTION]
    - Teleology: Compress an oversized raw seed into a bridge-friendly digest without losing the headings and directive lines that drive shard extraction.
    - Mechanism: Preserve headers, bold statements, directive lines, and structural markers while collapsing long narrative runs to one representative line.
    - Reads: Caller-provided raw seed text only.
    - Guarantee: Returns a readable digest bounded by `max_chars` unless a truncation marker is appended.
    - Fails: None.
    - When-needed: Open when bridge extraction needs the stage-standard raw-seed compression heuristic instead of sending the full raw seed verbatim.
    - Escalates-to: system/lib/pipeline/stage_extract.py::extract_shards; system/lib/json_payloads.py
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


# ---------------------------------------------------------------------------
# Shared shard normalization helpers (used across stages)
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Shared cycle directory and timeline helpers (used across stages)
# ---------------------------------------------------------------------------

def _selected_signature(shard_ids: list[str]) -> str:
    joined = "|".join(sorted(str(item).strip() for item in shard_ids if str(item).strip()))
    return sha256(joined.encode()).hexdigest()[:16] if joined else ""


def _cycle_dir_rel(state: dict, cycle: int | None = None) -> str:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    return str(Path(state["phase_dir"]) / f"cycle_{resolved_cycle}")


def _cycle_dir_path(state: dict, cycle: int | None = None) -> Path:
    from seed_pipeline import REPO_ROOT
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
    from seed_pipeline import REPO_ROOT, _utc_now
    from system.lib.observe_runtime import append_jsonl, observe_cycle_timeline_path

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
    from seed_pipeline import REPO_ROOT

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


def _phase_id_from_state(state: dict) -> str:
    phase_dir = state["phase_dir"]
    # Extract something like "07_6" from the path
    parts = Path(phase_dir).name.split(" - ")
    if parts:
        return parts[0].replace(".", "_").replace("Phase ", "")
    return "unknown"


def _legacy_dump_dir_rel(state: dict, cycle: int | None = None) -> str:
    resolved_cycle = int(state.get("cycle") or 0) if cycle is None else int(cycle)
    return f"tools/meta/apply/observe_dumps/{_phase_id_from_state(state)}_cycle_{resolved_cycle}"


def _cycle_path_candidates(state: dict, cycle: int, filename: str) -> list[Path]:
    return [
        _cycle_dir_path(state, cycle) / filename,
        _lazy_repo_root() / _legacy_dump_dir_rel(state, cycle) / filename,
    ]


def _active_phase(state: dict) -> str:
    return str(state.get("phase") or state.get("controller_phase") or "scope").strip() or "scope"


# ---------------------------------------------------------------------------
# Shared receipt/response loading helpers
# ---------------------------------------------------------------------------

def _load_receipt_payload(path: Path) -> dict[str, Any] | None:
    payload = _lazy_load_json(path)
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
    from seed_pipeline import REPO_ROOT

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
        payload = _lazy_load_json(path)
        if payload:
            return payload
    return None


def _selected_shard_ids_for_cycle(state: dict) -> list[str]:
    from seed_pipeline import REPO_ROOT

    synth = _lazy_load_json(REPO_ROOT / str(state.get("synth_seed_path") or ""))
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


# ---------------------------------------------------------------------------
# Shared synthesis payload helpers
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Shared text extraction and comparison helpers
# ---------------------------------------------------------------------------

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
    from system.lib.json_payloads import json_candidate_blocks
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
