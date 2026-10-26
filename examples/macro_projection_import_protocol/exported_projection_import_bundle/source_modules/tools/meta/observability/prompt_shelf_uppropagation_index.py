#!/usr/bin/env python3
"""Up-propagation index — extract aiw:uppropagation blocks from prompt-shelf raw events.

Reads every captured raw event under obsidian/prompt_shelf/usage/raw_events/<slot>/*.json,
parses the last <!-- aiw:uppropagation v=N --> ... <!-- /aiw:uppropagation --> block out
of assistant_message.raw_text, and writes a queryable index to
state/prompt_shelf/uppropagation_index.json.

The block is the model's self-reported improvement signal per run. Aggregated
downstream this becomes auto-surfaced outbox candidate signal — but no promotion
happens here. This is a read-only projection over raw events. Stdlib only.

CLI mirrors prompt_shelf_fingerprints.py:
  --print  emit JSON to stdout
  --write  write canonical projection
  --check  exit non-zero on drift vs disk
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_EVENTS_ROOT = REPO_ROOT / "obsidian" / "prompt_shelf" / "usage" / "raw_events"
INDEX_PATH = REPO_ROOT / "state" / "prompt_shelf" / "uppropagation_index.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt_shelf_uppropagation_index"
BLOCK_SCHEMA_VERSION = "v1_v2_v3"

BLOCK_RE = re.compile(
    r"<!--\s*aiw:uppropagation v=(?P<version>\d+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/aiw:uppropagation\s*-->",
    re.DOTALL,
)
TRAILING_NOISE = {"sources", "source", "copy", "share"}
FIELD_NAMES_BY_VERSION = {
    1: ("surprised", "prompt_friction", "system_friction", "deferred", "confidence"),
    2: (
        "prompt_received",
        "prompt_interpretation",
        "lesson",
        "prompt_friction",
        "system_friction",
        "confidence",
    ),
    3: (
        "prompt_received",
        "prompt_interpretation",
        "lesson",
        "self_prompting_idea",
        "information_demand",
        "prompt_friction",
        "system_friction",
        "confidence",
    ),
}
FIELD_NAMES = tuple(dict.fromkeys(name for names in FIELD_NAMES_BY_VERSION.values() for name in names))
DISPLAY_FIELD_NAMES = (
    "step_word",
    "step_summary",
    "state_word",
    "hud_state",
    "operator_summary",
    "next_move",
    "ui_badge",
)
CONFIDENCE_PREFIX_RE = re.compile(r"^\s*(high|medium|low)\b", re.IGNORECASE)


def field_names_for_version(version: int) -> tuple[str, ...]:
    return FIELD_NAMES_BY_VERSION.get(version, FIELD_NAMES_BY_VERSION[max(FIELD_NAMES_BY_VERSION)])


def parse_block_body(body: str, version: int = 1) -> tuple[dict[str, str], dict[str, str]]:
    """Parse the lines inside a block into {field: value} and {field: status}.

    status is one of: filled, empty, missing. A field with no colon at all is missing;
    a field with colon but only whitespace after is empty; otherwise filled.
    """
    expected = field_names_for_version(version)
    fields: dict[str, str] = {}
    status: dict[str, str] = {}
    # Tokenize line-by-line; each field is "name: value" on its own line.
    seen: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        # match "fieldname:" prefix
        if ":" not in stripped:
            continue
        head, _, tail = stripped.partition(":")
        head = head.strip().lower()
        if head in expected:
            seen[head] = tail.strip()
    for name in expected:
        if name not in seen:
            status[name] = "missing"
            fields[name] = ""
        elif not seen[name]:
            status[name] = "empty"
            fields[name] = ""
        else:
            status[name] = "filled"
            fields[name] = seen[name]
    return fields, status


def parse_display_fields(body: str) -> dict[str, str]:
    """Parse optional operator-facing HUD display fields from any block version."""
    fields: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or ":" not in stripped:
            continue
        head, _, tail = stripped.partition(":")
        key = head.strip().lower()
        if key in DISPLAY_FIELD_NAMES:
            fields[key] = tail.strip()
    return fields


def _block_is_quoted_or_code(text: str, start: int) -> bool:
    prefix = text[:start]
    if prefix.count("```") % 2 == 1:
        return True
    line_start = text.rfind("\n", 0, start) + 1
    line_prefix = text[line_start:start].strip()
    return line_prefix.startswith((">", "```", "`", "|"))


def _trailing_after_block_is_noise(text: str, end: int) -> bool:
    trailing = text[end:].strip()
    if not trailing:
        return True
    compact = re.sub(r"\s+", " ", trailing).strip().lower()
    return compact in TRAILING_NOISE


def _canonical_assistant_block_matches(text: str) -> tuple[list[re.Match[str]], re.Match[str] | None]:
    matches = list(BLOCK_RE.finditer(text or ""))
    if not matches:
        return [], None
    # A canonical emitted packet is a top-level final machine block. This avoids
    # indexing examples inside fenced code, quotes, tables, or mid-response prose.
    for match in reversed(matches):
        if _block_is_quoted_or_code(text, match.start()):
            continue
        if not _trailing_after_block_is_noise(text, match.end()):
            continue
        return matches, match
    return matches, None


def extract_record(raw_event_path: Path) -> dict | None:
    """Return one record per raw event that has at least one parseable block.

    If multiple blocks are present in assistant_message.raw_text, take the LAST one
    (it is the model's emitted block; earlier occurrences are typically the model
    quoting the prompt). Records block_count for visibility.
    """
    try:
        data = json.loads(raw_event_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    invalidation = data.get("invalidation") or {}
    if isinstance(invalidation, dict) and invalidation.get("status") == "quarantined":
        return None
    assistant = data.get("assistant_message") or {}
    text = assistant.get("raw_text") or ""
    extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
    if extra.get("uppropagation_capture_eligible") is False:
        return None
    if extra.get("uppropagation_provenance") in {"user_embedded_context", "assistant_quoted_or_code"}:
        return None
    matches, last = _canonical_assistant_block_matches(text)
    if not matches or last is None:
        return None
    block_v = int(last.group("version"))
    body = last.group("body")
    block_text = last.group(0)
    block_sha256 = hashlib.sha256(block_text.encode("utf-8")).hexdigest()
    assistant_sha256 = assistant.get("sha256") or ""
    fields, status = parse_block_body(body, block_v)
    display_fields = parse_display_fields(body)
    confidence_label = None
    conf_value = fields.get("confidence", "")
    if conf_value:
        m = CONFIDENCE_PREFIX_RE.match(conf_value)
        if m:
            confidence_label = m.group(1).lower()
    return {
        "prompt_run_id": data.get("prompt_run_id"),
        "prompt_slot": data.get("prompt_slot"),
        "prompt_slug": data.get("prompt_slug"),
        "raw_event_path": str(raw_event_path.relative_to(REPO_ROOT)),
        "captured_at": data.get("captured_at"),
        "conversation_id": data.get("conversation_id"),
        "conversation_url": data.get("conversation_url"),
        "user_turn_index": data.get("user_turn_index"),
        "assistant_turn_index": data.get("assistant_turn_index"),
        "assistant_message_sha256": assistant_sha256,
        "assistant_message_sha16": assistant_sha256[:16],
        "uppropagation_block_sha256": block_sha256,
        "uppropagation_block_sha16": block_sha256[:16],
        "block_v": block_v,
        "block_schema_version": f"v{block_v}",
        "block_count": len(matches),
        "canonical_block_count": 1,
        "uppropagation_provenance": extra.get("uppropagation_provenance") or "assistant_emitted_active",
        "uppropagation_capture_eligible": True,
        "uppropagation_selection": extra.get("uppropagation_selection") or "top_level_final_assistant_block",
        "fields": fields,
        "display_fields": display_fields,
        "step_word": display_fields.get("step_word"),
        "step_summary": display_fields.get("step_summary"),
        "state_word": display_fields.get("step_word") or display_fields.get("state_word") or display_fields.get("hud_state"),
        "field_status": status,
        "confidence_label": confidence_label,
    }


def build_index() -> dict:
    raw_events = sorted(RAW_EVENTS_ROOT.glob("*/*.json"))
    records: list[dict] = []
    no_block = 0
    for path in raw_events:
        if path.name == ".gitkeep":
            continue
        rec = extract_record(path)
        if rec is None:
            no_block += 1
        else:
            records.append(rec)
    # stable order: by captured_at then prompt_run_id
    records.sort(key=lambda r: (r.get("captured_at") or "", r.get("prompt_run_id") or ""))
    # per-slot rollups for quick visibility (no promotion logic — pure projection)
    slot_counts: dict[str, int] = {}
    field_filled_counts: dict[str, dict[str, int]] = {f: {} for f in FIELD_NAMES}
    confidence_distribution: dict[str, dict[str, int]] = {}
    for rec in records:
        slot = rec.get("prompt_slot") or "?"
        slot_counts[slot] = slot_counts.get(slot, 0) + 1
        for fname, fstatus in rec["field_status"].items():
            if fstatus == "filled":
                field_filled_counts[fname][slot] = field_filled_counts[fname].get(slot, 0) + 1
        cl = rec.get("confidence_label")
        if cl:
            confidence_distribution.setdefault(slot, {})
            confidence_distribution[slot][cl] = confidence_distribution[slot].get(cl, 0) + 1
    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": ARTIFACT_KIND,
            "block_schema_version": BLOCK_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "raw_events_scanned": len(raw_events),
            "events_with_block": len(records),
            "events_without_block": no_block,
            "source_root": str(RAW_EVENTS_ROOT.relative_to(REPO_ROOT)),
        },
        "rollups": {
            "records_by_slot": slot_counts,
            "filled_field_counts_by_slot": field_filled_counts,
            "confidence_distribution_by_slot": confidence_distribution,
        },
        "records": records,
    }


def render_canonical(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--print", action="store_true", help="emit JSON to stdout")
    parser.add_argument("--write", action="store_true", help="write canonical projection")
    parser.add_argument("--check", action="store_true", help="exit non-zero on drift vs disk")
    args = parser.parse_args()
    if not (args.print or args.write or args.check):
        parser.error("pick one of --print / --write / --check")

    index = build_index()
    rendered = render_canonical(index)

    if args.print:
        sys.stdout.write(rendered)
        return 0
    if args.write:
        INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
        INDEX_PATH.write_text(rendered)
        meta = index["__meta"]
        print(
            f"wrote {INDEX_PATH.relative_to(REPO_ROOT)} "
            f"({meta['events_with_block']} blocks parsed from {meta['raw_events_scanned']} events)"
        )
        return 0
    if args.check:
        if not INDEX_PATH.exists():
            print("missing")
            return 1
        # Compare ignoring generated_at, since timestamps drift.
        on_disk = json.loads(INDEX_PATH.read_text())
        on_disk["__meta"].pop("generated_at", None)
        fresh = json.loads(rendered)
        fresh["__meta"].pop("generated_at", None)
        if json.dumps(on_disk, sort_keys=True) == json.dumps(fresh, sort_keys=True):
            print("clean")
            return 0
        print("drift detected")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
