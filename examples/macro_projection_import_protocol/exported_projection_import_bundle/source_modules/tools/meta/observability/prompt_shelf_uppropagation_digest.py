#!/usr/bin/env python3
"""Up-propagation digest — compact recursive prompt-improvement projection.

Reads state/prompt_shelf/uppropagation_index.json and writes a small digest at:
  state/prompt_shelf/uppropagation_digest.json
  state/prompt_shelf/uppropagation_digest.md

The digest is intentionally light: latest v3 signals by slot, empty-field counts,
confidence distribution, repeated normalized field values, warning summaries, and
candidate rows. It does not promote prompts, standards, docs routes, principles, or
axioms automatically.

CLI:
  --print  emit JSON digest
  --write  write JSON + Markdown projections
  --check  exit non-zero on drift vs disk
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
INDEX_PATH = REPO_ROOT / "state" / "prompt_shelf" / "uppropagation_index.json"
DIGEST_JSON_PATH = REPO_ROOT / "state" / "prompt_shelf" / "uppropagation_digest.json"
DIGEST_MD_PATH = REPO_ROOT / "state" / "prompt_shelf" / "uppropagation_digest.md"
PROMPT_LEDGER_ADOPTION_POSTURE_PATH = REPO_ROOT / "state" / "prompt_ledger" / "views" / "adoption_posture.json"

# Schema-loose distillation bridge inputs (sibling pipeline; the upprop digest
# composes a small typed status section over these so HUD / world_model /
# HomeStation can consume "schema absent + distillation saved" without
# scraping raw diagnostics or per-event records.
SCHEMA_LOOSE_INDEX_PATH = REPO_ROOT / "state" / "prompt_shelf" / "schema_loose_distillation_index.json"
SCHEMA_LOOSE_PER_DIAGNOSTIC_DIR = REPO_ROOT / "state" / "prompt_shelf" / "distillation" / "per_diagnostic"
SCHEMA_LOOSE_RECEIPT_PATH = REPO_ROOT / "receipts" / "prompt_shelf_schema_loose_distillation_latest.json"
CAPTURE_DIAGNOSTICS_DIR = REPO_ROOT / "state" / "prompt_shelf" / "capture_diagnostics"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt_shelf_uppropagation_digest"
CURRENT_BLOCK_VERSION = 3
SLOTS = ("A0", "B1", "B2", "B3")
ADOPTION_STATES = (
    "captured",
    "indexed",
    "digested",
    "selected_for_adoption",
    "bound_to_workitem",
    "mutated_owner_surface",
    "validated",
    "projected_to_entry",
    "observed_in_future_run",
    "explicit_noop",
)
ADOPTION_PROOF_STATES = (
    "selected_for_adoption",
    "bound_to_workitem",
    "mutated_owner_surface",
    "validated",
    "projected_to_entry",
    "observed_in_future_run",
    "explicit_noop",
)
CANDIDATE_FIELD_KIND = {
    "lesson": "doctrine_or_process_candidate",
    "self_prompting_idea": "prompt_instruction",
    "information_demand": "evidence_affordance",
}


def _norm(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[`*_\"'.,;:!?()\[\]{}<>]", "", value)
    return value.strip()


def _stable_id(prefix: str, *parts: str) -> str:
    digest = hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


def _field_value(record: dict, field: str) -> str:
    return ((record.get("fields") or {}).get(field) or "").strip()


def _record_time_key(record: dict) -> tuple[str, str]:
    return (record.get("captured_at") or "", record.get("prompt_run_id") or "")


def _latest(records: list[dict]) -> dict | None:
    return max(records, key=_record_time_key) if records else None


def _compact_record(record: dict | None) -> dict:
    if not record:
        return {}
    return {
        "prompt_run_id": record.get("prompt_run_id"),
        "prompt_slot": record.get("prompt_slot"),
        "prompt_slug": record.get("prompt_slug"),
        "captured_at": record.get("captured_at"),
        "block_v": record.get("block_v"),
        "lesson": _field_value(record, "lesson"),
        "self_prompting_idea": _field_value(record, "self_prompting_idea"),
        "information_demand": _field_value(record, "information_demand"),
        "prompt_friction": _field_value(record, "prompt_friction"),
        "system_friction": _field_value(record, "system_friction"),
        "confidence": _field_value(record, "confidence"),
        "confidence_label": record.get("confidence_label"),
    }


def _empty_field_counts(records: list[dict]) -> dict:
    counts: dict[str, dict[str, int]] = {}
    for record in records:
        for field, status in (record.get("field_status") or {}).items():
            counts.setdefault(field, {"filled": 0, "empty": 0, "missing": 0})
            if status in counts[field]:
                counts[field][status] += 1
    return counts


def _repeated_values(records: list[dict]) -> list[dict]:
    groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in records:
        fields = record.get("fields") or {}
        for field in ("lesson", "self_prompting_idea", "information_demand", "prompt_friction", "system_friction"):
            value = (fields.get(field) or "").strip()
            normalized = _norm(value)
            if normalized:
                groups[(field, normalized)].append(record)

    repeated: list[dict] = []
    for (field, normalized), group in groups.items():
        if len(group) < 2:
            continue
        sample = _field_value(group[-1], field)
        repeated.append({
            "field": field,
            "normalized_value": normalized,
            "sample_value": sample,
            "count": len(group),
            "supporting_runs": [r.get("prompt_run_id") for r in group],
            "slots": sorted({r.get("prompt_slot") or "?" for r in group}),
        })
    repeated.sort(key=lambda row: (-row["count"], row["field"], row["normalized_value"]))
    return repeated


def _warnings(index: dict, records: list[dict], records_by_slot: dict[str, list[dict]]) -> list[dict]:
    warnings: list[dict] = []
    meta = index.get("__meta") or {}
    missing_blocks = int(meta.get("events_without_block") or 0)
    if missing_blocks:
        warnings.append({
            "kind": "events_without_block",
            "count": missing_blocks,
            "note": "Raw events without assistant-side up-propagation blocks remain outside the digest.",
        })

    historical = [r for r in records if int(r.get("block_v") or 0) < CURRENT_BLOCK_VERSION]
    if historical:
        versions = Counter(str(r.get("block_v")) for r in historical)
        warnings.append({
            "kind": "historical_schema_records",
            "count": len(historical),
            "versions": dict(sorted(versions.items())),
            "note": "Backward compatibility is extractor-only; current prompts should emit v3.",
        })

    multi = [r for r in records if int(r.get("block_count") or 0) > 1]
    if multi:
        warnings.append({
            "kind": "multiple_blocks_last_block_used",
            "count": len(multi),
            "supporting_runs": [r.get("prompt_run_id") for r in multi[:10]],
        })

    for slot in SLOTS:
        if not any(int(r.get("block_v") or 0) == CURRENT_BLOCK_VERSION for r in records_by_slot.get(slot, [])):
            warnings.append({
                "kind": "slot_without_v3_record",
                "slot": slot,
                "note": "No captured v3 output for this slot yet.",
            })
    return warnings


def _candidate_rows(records: list[dict]) -> list[dict]:
    candidates: dict[tuple[str, str, str], dict] = {}
    for record in records:
        slot = record.get("prompt_slot") or "?"
        run_id = record.get("prompt_run_id")
        for field, candidate_kind in CANDIDATE_FIELD_KIND.items():
            value = _field_value(record, field)
            if not value:
                continue
            key = (candidate_kind, field, _norm(value))
            row = candidates.setdefault(key, {
                "candidate_id": _stable_id("cand", candidate_kind, field, _norm(value)),
                "candidate_kind": candidate_kind,
                "source_field": field,
                "candidate": value,
                "slots": [],
                "supporting_runs": [],
                "status": "observed",
                "promotion": "none_auto_created",
            })
            if slot not in row["slots"]:
                row["slots"].append(slot)
            if run_id not in row["supporting_runs"]:
                row["supporting_runs"].append(run_id)
    out = list(candidates.values())
    for row in out:
        row["slots"].sort()
        row["support_count"] = len(row["supporting_runs"])
    out.sort(key=lambda row: (-row["support_count"], row["candidate_kind"], row["source_field"], row["candidate"]))
    return out


def _adoption_posture(records: list[dict], candidate_rows: list[dict]) -> dict:
    counts = {f"{state}_count": 0 for state in ADOPTION_STATES}
    counts["captured_count"] = len(records)
    counts["indexed_count"] = len(records)
    counts["digested_count"] = len(candidate_rows)
    prompt_ledger_receipts: list[dict] = []
    prompt_ledger_receipt_count = 0
    prompt_ledger_candidate_count = 0
    prompt_ledger_adopted_count = 0
    prompt_ledger_behavior_projection_count = 0
    candidate_current_state_counts: dict = {}
    candidate_milestone_counts: dict = {}
    receipt_state_counts: dict = {}
    if PROMPT_LEDGER_ADOPTION_POSTURE_PATH.is_file():
        try:
            prompt_ledger_posture = json.loads(PROMPT_LEDGER_ADOPTION_POSTURE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            prompt_ledger_posture = {}
        candidate_milestone_counts = (
            prompt_ledger_posture.get("candidate_milestone_counts")
            if isinstance(prompt_ledger_posture.get("candidate_milestone_counts"), dict)
            else prompt_ledger_posture.get("state_counts")
            if isinstance(prompt_ledger_posture.get("state_counts"), dict)
            else {}
        )
        candidate_current_state_counts = (
            prompt_ledger_posture.get("candidate_current_state_counts")
            if isinstance(prompt_ledger_posture.get("candidate_current_state_counts"), dict)
            else {}
        )
        receipt_state_counts = (
            prompt_ledger_posture.get("receipt_state_counts")
            if isinstance(prompt_ledger_posture.get("receipt_state_counts"), dict)
            else {}
        )
        for state in ADOPTION_PROOF_STATES:
            counts[f"{state}_count"] += int(candidate_milestone_counts.get(f"{state}_count") or 0)
        prompt_ledger_receipts = [
            row for row in prompt_ledger_posture.get("receipts", []) if isinstance(row, dict)
        ] if isinstance(prompt_ledger_posture.get("receipts"), list) else []
        prompt_ledger_receipt_count = int(prompt_ledger_posture.get("receipt_count") or len(prompt_ledger_receipts))
        prompt_ledger_candidate_count = int(prompt_ledger_posture.get("candidate_count") or 0)
        prompt_ledger_adopted_count = int(prompt_ledger_posture.get("adopted_count") or 0)
        prompt_ledger_behavior_projection_count = int(prompt_ledger_posture.get("behavior_projection_count") or 0)

    adopted_count = prompt_ledger_adopted_count or len(prompt_ledger_receipts) if prompt_ledger_receipts else sum(
        counts[f"{state}_count"] for state in ADOPTION_PROOF_STATES
    )
    behavior_projection_count = (
        prompt_ledger_behavior_projection_count
        or counts["projected_to_entry_count"] + counts["observed_in_future_run_count"]
    )
    return {
        "status": "partial" if records or candidate_rows else "empty",
        "owner": "codex/standards/std_prompt_ledger.json::adoption_state_machine",
        "source_boundary": "Prompt Shelf digest reports capture/index/digest posture; adoption beyond digested requires Prompt Ledger or owner-surface evidence.",
        "state_counts": counts,
        "captured_count": counts["captured_count"],
        "indexed_count": counts["indexed_count"],
        "digested_count": counts["digested_count"],
        "adopted_count": adopted_count,
        "behavior_projection_count": behavior_projection_count,
        "prompt_ledger_receipt_count": prompt_ledger_receipt_count,
        "prompt_ledger_candidate_count": prompt_ledger_candidate_count,
        "prompt_ledger_adoption_receipt_count": prompt_ledger_receipt_count,
        "candidate_current_state_counts": candidate_current_state_counts,
        "candidate_milestone_counts": candidate_milestone_counts,
        "receipt_state_counts": receipt_state_counts,
        "prompt_ledger_receipt_ids": [
            str(row.get("receipt_id") or row.get("event_id") or "")
            for row in prompt_ledger_receipts[:20]
            if row.get("receipt_id") or row.get("event_id")
        ],
        "prompt_ledger_adoption_posture_path": str(PROMPT_LEDGER_ADOPTION_POSTURE_PATH.relative_to(REPO_ROOT))
        if PROMPT_LEDGER_ADOPTION_POSTURE_PATH.is_relative_to(REPO_ROOT)
        else str(PROMPT_LEDGER_ADOPTION_POSTURE_PATH),
        "known_distinctions": [
            "captured != adopted",
            "adopted != projected",
            "projected != observed",
            "receipt_count != candidate_count",
        ],
        "next": "Bind selected digest candidates to Prompt Ledger adoption events, WorkItems, owner-surface mutations, or explicit no-op records.",
    }


def _conversation_key(record: dict) -> str:
    return str(record.get("conversation_id") or record.get("conversation_url") or "unknown")


def _mission_evolution(records: list[dict], *, max_threads: int = 12, max_events_per_thread: int = 16) -> list[dict]:
    groups: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        groups[_conversation_key(record)].append(record)

    rows: list[dict] = []
    for conversation_id, group in groups.items():
        group.sort(key=_record_time_key)
        latest = group[-1]
        timeline: list[dict] = []
        for record in group[-max_events_per_thread:]:
            timeline.append({
                "prompt_run_id": record.get("prompt_run_id"),
                "captured_at": record.get("captured_at"),
                "slot": record.get("prompt_slot"),
                "step_word": record.get("step_word"),
                "step_summary": record.get("step_summary"),
                "lesson": _field_value(record, "lesson"),
                "self_prompting_idea": _field_value(record, "self_prompting_idea"),
                "information_demand": _field_value(record, "information_demand"),
                "confidence_label": record.get("confidence_label"),
            })
        rows.append({
            "conversation_id": conversation_id,
            "conversation_url": latest.get("conversation_url"),
            "run_count": len(group),
            "slots": sorted({str(r.get("prompt_slot") or "?") for r in group}),
            "first_captured_at": group[0].get("captured_at"),
            "latest_captured_at": latest.get("captured_at"),
            "latest_prompt_run_id": latest.get("prompt_run_id"),
            "latest_step_word": latest.get("step_word"),
            "latest_step_summary": latest.get("step_summary"),
            "latest_lesson": _field_value(latest, "lesson"),
            "timeline": timeline,
        })
    rows.sort(key=lambda row: (-(row["run_count"]), str(row.get("latest_captured_at") or "")), reverse=False)
    rows = sorted(rows, key=lambda row: (row["run_count"], str(row.get("latest_captured_at") or "")), reverse=True)
    return rows[:max_threads]


def _build_schema_loose_distillation_section() -> dict:
    """Compose a typed status section over the schema-loose distillation bridge.

    Reads three sibling artifacts produced by the bridge:
      - state/prompt_shelf/schema_loose_distillation_index.json (aggregate)
      - state/prompt_shelf/distillation/per_diagnostic/*.json (per-event)
      - state/prompt_shelf/capture_diagnostics/*.json (raw missing-upprop)

    Authority discipline: this section surfaces a PROJECTION over those
    artifacts; consumers must read ``capture_authority``/``distillation_authority``/
    ``body_persisted`` to know what authority the projection carries. The
    section never grants capture or doctrine authority on its own.
    """
    section: dict = {
        "owner": "tools.meta.observability.prompt_shelf_schema_loose_distillation_index",
        "owning_cap_id": "cap_quick_prompt_shelf_bridge_schema_loose_type_b_4b01dbd8d09f",
        "authority_posture": "distillation_projection_not_full_capture",
        "capture_authority": False,
        "distillation_authority": True,
        "body_persisted": False,
        "status": "missing",
        "capture_status": "no_diagnostic_dir",
        "distillation_status": "not_attempted",
        "index_path": "state/prompt_shelf/schema_loose_distillation_index.json",
        "index_present": False,
        "receipt_ref": "receipts/prompt_shelf_schema_loose_distillation_latest.json",
        "receipt_present": False,
        "diagnostic_count": 0,
        "per_diagnostic_record_count": 0,
        "source_role_counts": {
            "assistant_text": 0,
            "user_tail": 0,
            "pair_combined": 0,
        },
        "complete_enough_count": 0,
        "partial_count": 0,
        "slot_counts": {},
        "latest_saved_distillation_path": None,
        "latest_saved_distillation_at": None,
        "last_checked_at": datetime.now(timezone.utc).isoformat(),
    }

    if CAPTURE_DIAGNOSTICS_DIR.is_dir():
        # Bound the listing; we only need a count, not the full file list.
        diag_count = 0
        for _ in CAPTURE_DIAGNOSTICS_DIR.glob("*.json"):
            diag_count += 1
        section["diagnostic_count"] = diag_count
        section["capture_status"] = (
            "schema_absent_for_some_runs" if diag_count else "no_schema_absent_runs"
        )

    if SCHEMA_LOOSE_INDEX_PATH.is_file():
        try:
            index = json.loads(SCHEMA_LOOSE_INDEX_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            index = None
        if isinstance(index, dict) and index.get("kind") == "prompt_shelf_schema_loose_distillation_index":
            section["index_present"] = True
            coverage = index.get("coverage") or {}
            for role in ("assistant_text", "user_tail", "pair_combined"):
                role_block = coverage.get(role) or {}
                section["source_role_counts"][role] = int(role_block.get("record_count") or 0)
            section["complete_enough_count"] = sum(
                int((coverage.get(role) or {}).get("complete_enough_count") or 0)
                for role in ("assistant_text", "user_tail", "pair_combined")
            )
            section["partial_count"] = sum(
                int((coverage.get(role) or {}).get("partial_count") or 0)
                for role in ("assistant_text", "user_tail", "pair_combined")
            )
            section["slot_counts"] = dict(index.get("slot_counts") or {})
            section["index_generated_at"] = index.get("generated_at")
            section["deduped_record_count"] = int(index.get("deduped_record_count") or 0)
            section["duplicate_count"] = int(index.get("duplicate_count") or 0)

    if SCHEMA_LOOSE_PER_DIAGNOSTIC_DIR.is_dir():
        latest: Path | None = None
        latest_mtime = -1.0
        per_event_count = 0
        for p in SCHEMA_LOOSE_PER_DIAGNOSTIC_DIR.glob("*.json"):
            per_event_count += 1
            mtime = p.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest = p
        section["per_diagnostic_record_count"] = per_event_count
        if latest is not None:
            try:
                section["latest_saved_distillation_path"] = str(latest.relative_to(REPO_ROOT))
            except ValueError:
                section["latest_saved_distillation_path"] = str(latest)
            section["latest_saved_distillation_at"] = datetime.fromtimestamp(
                latest_mtime, tz=timezone.utc
            ).isoformat()

    if SCHEMA_LOOSE_RECEIPT_PATH.is_file():
        section["receipt_present"] = True

    # Derive overall status from the live state of the bridge artifacts.
    if section["per_diagnostic_record_count"] > 0:
        section["status"] = "active"
        section["distillation_status"] = "saved"
    elif section["index_present"] and section["complete_enough_count"] + section["partial_count"] > 0:
        section["status"] = "active"
        section["distillation_status"] = "saved"
    elif section["diagnostic_count"] > 0:
        section["status"] = "degraded"
        section["distillation_status"] = "no_signal"
    else:
        # No diagnostics, no per-event records — the bridge has nothing to do.
        section["status"] = "idle"
        section["distillation_status"] = "not_attempted"

    return section


def build_digest(index: dict) -> dict:
    records = list(index.get("records") or [])
    records.sort(key=_record_time_key)
    records_by_slot: dict[str, list[dict]] = defaultdict(list)
    for record in records:
        records_by_slot[record.get("prompt_slot") or "?"].append(record)

    latest_by_slot = {slot: _compact_record(_latest(records_by_slot.get(slot, []))) for slot in SLOTS}
    latest_v3_by_slot = {
        slot: _compact_record(_latest([r for r in records_by_slot.get(slot, []) if int(r.get("block_v") or 0) == CURRENT_BLOCK_VERSION]))
        for slot in SLOTS
    }

    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": ARTIFACT_KIND,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_artifact_kind": (index.get("__meta") or {}).get("artifact_kind"),
            "source_schema_version": (index.get("__meta") or {}).get("schema_version"),
            "record_count": len(records),
            "candidate_count": 0,  # filled below for stable single-pass construction
        },
        "latest_by_slot": latest_by_slot,
        "latest_v3_by_slot": latest_v3_by_slot,
        "repeated_values": _repeated_values(records),
        "empty_field_counts": _empty_field_counts(records),
        "confidence_distribution_by_slot": (index.get("rollups") or {}).get("confidence_distribution_by_slot", {}),
        "mission_evolution": _mission_evolution(records),
        "warnings": _warnings(index, records, records_by_slot),
        "candidate_rows": [],
        "prompt_adoption_posture": {},
        "schema_loose_distillation": _build_schema_loose_distillation_section(),
    }


def finalize_digest(digest: dict, index: dict) -> dict:
    records = list(index.get("records") or [])
    digest["candidate_rows"] = _candidate_rows(records)
    digest["__meta"]["candidate_count"] = len(digest["candidate_rows"])
    digest["prompt_adoption_posture"] = _adoption_posture(records, digest["candidate_rows"])
    return digest


def load_index(path: Path = INDEX_PATH) -> dict:
    return json.loads(path.read_text())


def render_json(digest: dict) -> str:
    return json.dumps(digest, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def render_markdown(digest: dict) -> str:
    lines = [
        "# Prompt Shelf Up-Propagation Digest",
        "",
        "Compact projection over prompt-shelf up-propagation telemetry. No prompt, doctrine, docs-route, standard, principle, or axiom candidate is promoted automatically.",
        "",
        "## Snapshot",
        "",
        f"- Records: {digest['__meta']['record_count']}",
        f"- Candidate rows: {digest['__meta']['candidate_count']}",
        f"- Warnings: {len(digest['warnings'])}",
        "",
        "## Adoption Posture",
        "",
        f"- Status: {digest.get('prompt_adoption_posture', {}).get('status', 'unavailable')}",
        f"- Captured: {digest.get('prompt_adoption_posture', {}).get('captured_count', 0)}",
        f"- Digested: {digest.get('prompt_adoption_posture', {}).get('digested_count', 0)}",
        f"- Adopted: {digest.get('prompt_adoption_posture', {}).get('adopted_count', 0)}",
        f"- Behavior projection: {digest.get('prompt_adoption_posture', {}).get('behavior_projection_count', 0)}",
        "- Rule: captured/indexed/digested prompt traces are not behavior-change proof without Prompt Ledger adoption and owner-surface evidence.",
        "",
        "## Latest v3 By Slot",
        "",
    ]
    for slot in SLOTS:
        row = digest["latest_v3_by_slot"].get(slot) or {}
        if not row:
            lines.append(f"- `{slot}`: no v3 capture yet")
            continue
        fields = []
        for field in ("lesson", "self_prompting_idea", "information_demand"):
            value = row.get(field)
            if value:
                fields.append(f"{field}={value}")
        summary = "; ".join(fields) if fields else "v3 capture has no filled recursive fields"
        lines.append(f"- `{slot}` `{row.get('prompt_run_id')}`: {summary}")

    lines.extend(["", "## Candidate Rows", ""])
    if digest["candidate_rows"]:
        for row in digest["candidate_rows"][:20]:
            lines.append(
                f"- `{row['candidate_kind']}` from `{row['source_field']}` "
                f"({row['support_count']} run): {row['candidate']}"
            )
    else:
        lines.append("- None yet.")

    lines.extend(["", "## Mission Evolution", ""])
    if digest.get("mission_evolution"):
        for row in digest["mission_evolution"][:8]:
            label = row.get("latest_step_word") or "latest"
            summary = row.get("latest_step_summary") or row.get("latest_lesson") or "no latest summary"
            lines.append(
                f"- `{row['conversation_id']}` ({row['run_count']} runs, slots={','.join(row['slots'])}, latest={label}): {summary}"
            )
    else:
        lines.append("- None yet.")

    lines.extend(["", "## Warnings", ""])
    if digest["warnings"]:
        for warning in digest["warnings"]:
            detail = ", ".join(f"{k}={v}" for k, v in warning.items() if k != "note")
            note = f" — {warning['note']}" if warning.get("note") else ""
            lines.append(f"- {detail}{note}")
    else:
        lines.append("- None.")

    sl = digest.get("schema_loose_distillation") or {}
    if sl:
        lines.extend(["", "## Schema-Loose Distillation Bridge", ""])
        lines.append(
            "Sibling status section for runs where the v3 up-propagation schema was absent. "
            "`saved_distillation_path != full capture`: this section reports a projection, "
            "not a capture-success claim."
        )
        lines.append("")
        lines.append(f"- Status: `{sl.get('status', 'unknown')}`")
        lines.append(f"- Capture status: `{sl.get('capture_status', 'unknown')}`")
        lines.append(f"- Distillation status: `{sl.get('distillation_status', 'unknown')}`")
        lines.append(f"- capture_authority: `{sl.get('capture_authority', False)}`")
        lines.append(f"- distillation_authority: `{sl.get('distillation_authority', False)}`")
        lines.append(f"- body_persisted: `{sl.get('body_persisted', False)}`")
        lines.append(f"- Diagnostics: {sl.get('diagnostic_count', 0)}")
        lines.append(f"- Per-event records: {sl.get('per_diagnostic_record_count', 0)}")
        lines.append(f"- Deduped index records: {sl.get('deduped_record_count', 0)}")
        src = sl.get("source_role_counts") or {}
        lines.append(
            f"- Source role counts: assistant_text={src.get('assistant_text', 0)} "
            f"user_tail={src.get('user_tail', 0)} "
            f"pair_combined={src.get('pair_combined', 0)}"
        )
        lines.append(f"- complete_enough: {sl.get('complete_enough_count', 0)}; partial: {sl.get('partial_count', 0)}")
        latest = sl.get("latest_saved_distillation_path")
        if latest:
            lines.append(f"- Latest per-event payload: `{latest}` (at {sl.get('latest_saved_distillation_at')})")
        else:
            lines.append("- Latest per-event payload: (none yet)")
        lines.append(f"- Receipt: `{sl.get('receipt_ref')}` (present={sl.get('receipt_present', False)})")
        lines.append(f"- Owning cap: `{sl.get('owning_cap_id')}`")
        lines.append(
            "- Rule: schema absent + distillation saved is a degraded-but-preserved state. "
            "Banners and frontends must not display this as full-capture success."
        )

    return "\n".join(lines) + "\n"


def _canonical_for_compare(digest: dict) -> dict:
    clone = json.loads(json.dumps(digest))
    clone["__meta"].pop("generated_at", None)
    return clone


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--print", action="store_true", help="emit JSON digest")
    parser.add_argument("--write", action="store_true", help="write JSON and Markdown digest")
    parser.add_argument("--check", action="store_true", help="exit non-zero on drift vs disk")
    args = parser.parse_args()
    if not (args.print or args.write or args.check):
        parser.error("pick one of --print / --write / --check")

    index = load_index()
    digest = finalize_digest(build_digest(index), index)
    rendered_json = render_json(digest)
    rendered_md = render_markdown(digest)

    if args.print:
        sys.stdout.write(rendered_json)
        return 0
    if args.write:
        DIGEST_JSON_PATH.parent.mkdir(parents=True, exist_ok=True)
        DIGEST_JSON_PATH.write_text(rendered_json)
        DIGEST_MD_PATH.write_text(rendered_md)
        print(
            f"wrote {DIGEST_JSON_PATH.relative_to(REPO_ROOT)} and "
            f"{DIGEST_MD_PATH.relative_to(REPO_ROOT)} "
            f"({digest['__meta']['candidate_count']} candidates)"
        )
        return 0
    if args.check:
        if not DIGEST_JSON_PATH.exists() or not DIGEST_MD_PATH.exists():
            print("missing")
            return 1
        on_disk = json.loads(DIGEST_JSON_PATH.read_text())
        if _canonical_for_compare(on_disk) != _canonical_for_compare(digest):
            print("json drift detected")
            return 1
        if DIGEST_MD_PATH.read_text() != rendered_md:
            print("markdown drift detected")
            return 1
        print("clean")
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
