#!/usr/bin/env python3
"""Movement sidecar index — extract aiw:movement v=1 blocks from prompt-shelf raw events.

Sibling to prompt_shelf_uppropagation_index.py. Reads every captured raw event under
obsidian/prompt_shelf/usage/raw_events/<slot>/*.json, identifies the contiguous terminal
sidecar cluster of <!-- aiw:movement v=1 --> ... <!-- /aiw:movement --> blocks immediately
before the final <!-- aiw:uppropagation v=3 --> block, and writes a queryable index to
state/prompt_shelf/movement_index.json.

CRITICAL placement rule (per std_aiw_movement_v1.placement_rules):
  Only movement blocks in the contiguous terminal cluster immediately before the FINAL
  aiw:uppropagation block count as emitted telemetry. Movement blocks earlier in prose
  (quoted examples, design templates, captured documentation) are non-terminal and excluded
  from records. Movement blocks AFTER the final v3 footer are non-terminal too. Movement
  blocks without any v3 anchor are flagged as no_final_uppropagation and excluded.

The index is a read-only projection. No promotion happens here. Movement packets are
typed substrate-motion proposals; promotion routes through each owning plane's
curation skill.

This pipeline is INDEPENDENT of the v3 uppropagation pipeline. v3 indexer changes do
not affect this tool, and this tool does not modify the v3 indexer.

Detected warning kinds (per std_aiw_movement_v1):
  Semantic (cause --validate to exit nonzero):
    - nested_movement_inside_uppropagation
        A movement block is wholly contained inside an uppropagation block.
    - nested_uppropagation_inside_movement
        An uppropagation block is wholly contained inside a movement block.
    - missing_required_field
        A movement block is missing one of the 10 required fields (block-level warning;
        --validate fails when ANY recorded block has any missing required field).
    - unknown_version
        A movement block declares v=N for N != 1.
    - duplicate_recurrence_key_in_same_run
        Two or more movement blocks in one raw_event share the same recurrence_key.

  Advisory (do NOT cause --validate to fail; surfaced for visibility):
    - non_terminal_movement_block_ignored
        A movement block exists before the final v3 footer but is separated from it by
        non-whitespace, non-movement content (i.e., it is a quoted example or template).
    - movement_after_final_uppropagation
        A movement block appears AFTER the final v3 footer.
    - movement_without_final_uppropagation
        Movement blocks exist but no aiw:uppropagation v=3 anchor is present in the
        message; in chat-capture mode, no movement blocks are recorded.

CLI:
  --print     emit JSON to stdout
  --write     write canonical projection to state/prompt_shelf/movement_index.json
  --check     exit non-zero on DRIFT vs disk (currentness only)
  --validate  exit non-zero on SEMANTIC violations (nested / missing / unknown / duplicate)

--check and --validate are independent. --check is for projection currentness; --validate
is for movement-contract semantic validity. Run both for full pre-commit confidence.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
RAW_EVENTS_ROOT = REPO_ROOT / "obsidian" / "prompt_shelf" / "usage" / "raw_events"
INDEX_PATH = REPO_ROOT / "state" / "prompt_shelf" / "movement_index.json"

SCHEMA_VERSION = "1.0.0"
ARTIFACT_KIND = "prompt_shelf_movement_index"
BLOCK_SCHEMA_VERSION = "aiw_movement_v1"
SUPPORTED_BLOCK_VERSIONS = frozenset({1})

MOVEMENT_BLOCK_RE = re.compile(
    r"<!--\s*aiw:movement v=(?P<version>\d+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/aiw:movement\s*-->",
    re.DOTALL,
)

# Mirrored from prompt_shelf_uppropagation_index.py — used here ONLY to detect nesting.
UPPROPAGATION_BLOCK_RE = re.compile(
    r"<!--\s*aiw:uppropagation v=(?P<version>\d+)\s*-->"
    r"(?P<body>.*?)"
    r"<!--\s*/aiw:uppropagation\s*-->",
    re.DOTALL,
)

REQUIRED_FIELDS_V1 = (
    "source_signal",
    "signal_kind",
    "recurrence_key",
    "owning_plane",
    "availability_result",
    "movement",
    "promotion_boundary",
    "evidence_anchor",
    "validation_target",
    "do_not_do",
)


def _required_fields_for_version(version: int) -> tuple[str, ...]:
    if version == 1:
        return REQUIRED_FIELDS_V1
    return REQUIRED_FIELDS_V1


def parse_block_body(body: str, version: int = 1) -> tuple[dict[str, str], dict[str, str]]:
    """Parse the lines inside a movement block into {field: value} and {field: status}.

    status is one of: filled, empty, missing. Mirrors v3 parser semantics so authors
    using the same form get consistent behavior across the two block kinds.
    """
    expected = _required_fields_for_version(version)
    fields: dict[str, str] = {}
    status: dict[str, str] = {}
    seen: dict[str, str] = {}
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
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


def _classify_blocks(
    movement_matches: list,
    uppropagation_matches: list,
    text: str,
) -> tuple[dict[int, str], list[dict]]:
    """Classify each movement block by placement and detect nesting violations.

    Returns (classification_by_index, nesting_warnings).

    Classifications:
      - "nested_inside_uppropagation"  — movement block strictly inside an uppropagation
                                         block; excluded from records (semantic violation)
      - "no_final_uppropagation"       — no aiw:uppropagation anchor in message; movement
                                         blocks excluded from records (advisory)
      - "after_final_uppropagation"    — movement starts after the final v3 footer ends;
                                         excluded from records (advisory)
      - "non_terminal"                 — movement appears before final v3 but is separated
                                         from the terminal cluster by non-whitespace prose
                                         (a quoted example or template); excluded (advisory)
      - "terminal"                     — movement is part of the contiguous terminal cluster
                                         immediately before final v3; INCLUDED in records
      - "malformed_overlap"            — movement span overlaps the final v3 boundary in
                                         a malformed way (rare); excluded (advisory)
    """
    classifications: dict[int, str] = {}
    nesting_warnings: list[dict] = []

    # Step 1: detect nesting (movement strictly inside uppropagation, or vice versa).
    for m_idx, m in enumerate(movement_matches):
        for u in uppropagation_matches:
            if u.start() < m.start() and m.end() < u.end():
                classifications[m_idx] = "nested_inside_uppropagation"
                nesting_warnings.append({
                    "kind": "nested_movement_inside_uppropagation",
                    "movement_block_index": m_idx,
                    "movement_span": [m.start(), m.end()],
                    "containing_uppropagation_span": [u.start(), u.end()],
                    "note": "aiw:movement block is wholly inside an aiw:uppropagation block; std_aiw_movement_v1 forbids nesting.",
                })
                break
    # Mirror direction: uppropagation strictly inside movement is also a violation.
    for u_idx, u in enumerate(uppropagation_matches):
        for m in movement_matches:
            if m.start() < u.start() and u.end() < m.end():
                nesting_warnings.append({
                    "kind": "nested_uppropagation_inside_movement",
                    "uppropagation_block_index": u_idx,
                    "uppropagation_span": [u.start(), u.end()],
                    "containing_movement_span": [m.start(), m.end()],
                    "note": "aiw:uppropagation block is wholly inside an aiw:movement block; std_aiw_movement_v1 forbids nesting.",
                })
                break

    # Step 2: if no uppropagation anchor exists, all non-nested movement blocks are
    # "no_final_uppropagation".
    if not uppropagation_matches:
        for m_idx in range(len(movement_matches)):
            if m_idx not in classifications:
                classifications[m_idx] = "no_final_uppropagation"
        return classifications, nesting_warnings

    # Step 3: find the LAST (final) aiw:uppropagation block — that is the canonical footer.
    final_v3 = max(uppropagation_matches, key=lambda u: u.start())
    u_start = final_v3.start()
    u_end = final_v3.end()

    # Step 4: classify each non-nested movement block by position relative to final v3.
    for m_idx, m in enumerate(movement_matches):
        if m_idx in classifications:
            continue  # already nested
        if m.start() >= u_end:
            classifications[m_idx] = "after_final_uppropagation"
        elif m.end() <= u_start:
            classifications[m_idx] = "before_final_uppropagation_unconfirmed"
        else:
            # Overlap with the v3 footer boundary — malformed.
            classifications[m_idx] = "malformed_overlap"

    # Step 5: walk backward from the v3 footer to find the contiguous terminal cluster.
    # A movement block is "terminal" if all text between it and the next-rightward
    # terminal-or-v3-anchor is whitespace-only.
    before_blocks = [
        (i, m) for i, m in enumerate(movement_matches)
        if classifications.get(i) == "before_final_uppropagation_unconfirmed"
    ]
    before_blocks.sort(key=lambda x: x[1].start())

    next_start = u_start  # the position the previous "anchor" started at
    for i, m in reversed(before_blocks):
        gap_text = text[m.end():next_start]
        if gap_text.strip() == "":
            classifications[i] = "terminal"
            next_start = m.start()
        else:
            # Stop walking — this block and everything before it is non-terminal.
            classifications[i] = "non_terminal"

    # Mark any remaining "unconfirmed" entries (blocks before a non_terminal one) as
    # non_terminal. The walk above stops on the first gap with non-whitespace, but blocks
    # before that need explicit classification.
    for i, m in before_blocks:
        if classifications.get(i) == "before_final_uppropagation_unconfirmed":
            classifications[i] = "non_terminal"

    return classifications, nesting_warnings


def extract_run(raw_event_path: Path) -> tuple[list[dict], list[dict]] | None:
    """Return (block_records, run_warnings) for a raw event, or None when no movement blocks.

    block_records: one dict per TERMINAL movement block (per std_aiw_movement_v1
                   placement rules). Non-terminal blocks are NOT recorded; they appear
                   in run_warnings instead.
    run_warnings: run-level warnings (nesting, non-terminal blocks, no-final-v3,
                  unknown_version, duplicate_recurrence_key_in_same_run). Each warning
                  carries raw_event_path, prompt_run_id, and captured_at so downstream
                  filters (e.g. --validate --since) can act without re-reading files.
    """
    try:
        data = json.loads(raw_event_path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    assistant = data.get("assistant_message") or {}
    text = assistant.get("raw_text") or ""

    movement_matches = list(MOVEMENT_BLOCK_RE.finditer(text))
    if not movement_matches:
        return None

    uppropagation_matches = list(UPPROPAGATION_BLOCK_RE.finditer(text))

    classifications, nesting_warnings = _classify_blocks(
        movement_matches, uppropagation_matches, text,
    )

    rel_path = str(raw_event_path.relative_to(REPO_ROOT))
    run_id = data.get("prompt_run_id")
    captured_at = data.get("captured_at")

    def _attach_run_metadata(warning: dict) -> dict:
        out = dict(warning)
        out["raw_event_path"] = rel_path
        out["prompt_run_id"] = run_id
        out["captured_at"] = captured_at
        return out

    run_warnings: list[dict] = [_attach_run_metadata(w) for w in nesting_warnings]
    block_records: list[dict] = []
    recurrence_keys_seen: dict[str, list[int]] = {}
    terminal_block_count = 0

    for block_index, match in enumerate(movement_matches):
        classification = classifications.get(block_index, "unknown")
        block_v = int(match.group("version"))
        body = match.group("body")
        unknown_version = block_v not in SUPPORTED_BLOCK_VERSIONS
        if unknown_version:
            run_warnings.append(_attach_run_metadata({
                "kind": "unknown_version",
                "block_index": block_index,
                "version": block_v,
                "supported": sorted(SUPPORTED_BLOCK_VERSIONS),
                "classification": classification,
            }))

        # Record only TERMINAL blocks. Non-terminal blocks become advisory warnings.
        if classification != "terminal":
            advisory_kind = {
                "nested_inside_uppropagation": None,  # already added as semantic warning
                "no_final_uppropagation": "movement_without_final_uppropagation",
                "after_final_uppropagation": "movement_after_final_uppropagation",
                "non_terminal": "non_terminal_movement_block_ignored",
                "malformed_overlap": "movement_block_malformed_overlap",
            }.get(classification)
            if advisory_kind is not None:
                run_warnings.append(_attach_run_metadata({
                    "kind": advisory_kind,
                    "block_index": block_index,
                    "movement_span": [match.start(), match.end()],
                    "classification": classification,
                    "note": (
                        "Movement block excluded from records per std_aiw_movement_v1 "
                        "placement rules: only terminal sidecar cluster before final v3 footer is emitted telemetry."
                    ),
                }))
            continue

        # Parse fields for terminal block.
        fields, status = parse_block_body(body, block_v if not unknown_version else 1)

        warnings_block: list[dict] = []
        for fname in REQUIRED_FIELDS_V1:
            if status.get(fname) == "missing":
                warnings_block.append({
                    "kind": "missing_required_field",
                    "field": fname,
                })

        rec_key = fields.get("recurrence_key", "") or ""
        if rec_key:
            recurrence_keys_seen.setdefault(rec_key, []).append(block_index)

        block_records.append({
            "prompt_run_id": run_id,
            "prompt_slot": data.get("prompt_slot"),
            "prompt_slug": data.get("prompt_slug"),
            "raw_event_path": rel_path,
            "captured_at": data.get("captured_at"),
            "conversation_id": data.get("conversation_id"),
            "assistant_message_sha256": (assistant.get("sha256") or "")[:16],
            "block_index": block_index,
            "block_v": block_v,
            "block_schema_version": f"aiw_movement_v{block_v}",
            "block_count": len(movement_matches),
            "terminal_block_position": terminal_block_count,
            "char_start": match.start(),
            "char_end": match.end(),
            "fields": fields,
            "field_status": status,
            "warnings": warnings_block,
        })
        terminal_block_count += 1

    for key, indexes in recurrence_keys_seen.items():
        if len(indexes) > 1:
            run_warnings.append(_attach_run_metadata({
                "kind": "duplicate_recurrence_key_in_same_run",
                "recurrence_key": key,
                "block_indexes": indexes,
                "note": "Two or more movement blocks in this raw_event share the same recurrence_key. Either author error, or genuine duplication that should be collapsed into one block.",
            }))

    return block_records, run_warnings


def build_index() -> dict:
    raw_events = sorted(RAW_EVENTS_ROOT.glob("*/*.json"))
    records: list[dict] = []
    run_warnings: list[dict] = []
    no_block = 0
    for path in raw_events:
        if path.name == ".gitkeep":
            continue
        result = extract_run(path)
        if result is None:
            no_block += 1
            continue
        block_records, warnings = result
        records.extend(block_records)
        # Each warning already carries raw_event_path / prompt_run_id / captured_at
        # via _attach_run_metadata in extract_run, so no further enrichment needed.
        run_warnings.extend(warnings)

    # Stable order: by captured_at, then prompt_run_id, then block_index.
    records.sort(key=lambda r: (
        r.get("captured_at") or "",
        r.get("prompt_run_id") or "",
        r.get("block_index") or 0,
    ))

    blocks_by_slot: dict[str, int] = {}
    recurrence_keys: dict[str, int] = {}
    owning_plane_mentions: dict[str, int] = {}
    availability_counts: dict[str, int] = {}
    movement_counts: dict[str, int] = {}
    promotion_counts: dict[str, int] = {}
    for rec in records:
        slot = rec.get("prompt_slot") or "?"
        blocks_by_slot[slot] = blocks_by_slot.get(slot, 0) + 1
        rec_key = rec["fields"].get("recurrence_key") or ""
        if rec_key:
            recurrence_keys[rec_key] = recurrence_keys.get(rec_key, 0) + 1
        plane = rec["fields"].get("owning_plane") or ""
        if plane:
            owning_plane_mentions[plane] = owning_plane_mentions.get(plane, 0) + 1
        avail = rec["fields"].get("availability_result") or ""
        if avail:
            availability_counts[avail] = availability_counts.get(avail, 0) + 1
        mov = rec["fields"].get("movement") or ""
        if mov:
            movement_counts[mov] = movement_counts.get(mov, 0) + 1
        prom = rec["fields"].get("promotion_boundary") or ""
        if prom:
            promotion_counts[prom] = promotion_counts.get(prom, 0) + 1

    events_with_block = len({r.get("prompt_run_id") for r in records if r.get("prompt_run_id")})

    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": ARTIFACT_KIND,
            "block_schema_version": BLOCK_SCHEMA_VERSION,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "raw_events_scanned": len(raw_events),
            "events_with_block": events_with_block,
            "events_without_block": no_block,
            "movement_blocks_total": len(records),
            "run_warnings_total": len(run_warnings),
            "source_root": str(RAW_EVENTS_ROOT.relative_to(REPO_ROOT)),
        },
        "rollups": {
            "blocks_by_slot": blocks_by_slot,
            "recurrence_keys": recurrence_keys,
            "owning_plane_mentions": owning_plane_mentions,
            "availability_result_counts": availability_counts,
            "movement_action_counts": movement_counts,
            "promotion_boundary_counts": promotion_counts,
        },
        "records": records,
        "run_warnings": run_warnings,
    }


def render_canonical(index: dict) -> str:
    return json.dumps(index, indent=2, ensure_ascii=False, sort_keys=False) + "\n"


# Warning kinds that --validate treats as semantic violations (exit non-zero).
SEMANTIC_VIOLATION_KINDS = frozenset({
    "nested_movement_inside_uppropagation",
    "nested_uppropagation_inside_movement",
    "unknown_version",
    "duplicate_recurrence_key_in_same_run",
})


def collect_semantic_violations(
    index: dict,
    since: str | None = None,
) -> list[dict]:
    """Return the list of semantic violations per std_aiw_movement_v1.

    --validate exits non-zero when this list is non-empty. --check is independent.
    Includes:
      - run-level violations of kind in SEMANTIC_VIOLATION_KINDS
      - any record whose block-level warnings include "missing_required_field"
    Excludes:
      - non-terminal / after-final / no-final-v3 advisory warnings (those are placement
        diagnostics, not semantic contract violations)

    If `since` is provided (an ISO 8601 timestamp string), violations whose
    captured_at is < since are EXCLUDED from the returned list. This implements the
    --validate --since cutover policy: historical scars from before the cutoff are
    preserved in the index but do not cause --validate to fail. ISO 8601 strings sort
    lexicographically, so direct string comparison is used.
    """
    violations: list[dict] = []

    def _captured_at_passes(captured_at: str | None) -> bool:
        if since is None:
            return True
        if not captured_at:
            # No timestamp → cannot prove it's after the cutoff; exclude conservatively.
            return False
        return captured_at >= since

    for w in index.get("run_warnings") or []:
        if w.get("kind") not in SEMANTIC_VIOLATION_KINDS:
            continue
        if not _captured_at_passes(w.get("captured_at")):
            continue
        violations.append({
            "level": "run",
            "kind": w.get("kind"),
            "raw_event_path": w.get("raw_event_path"),
            "prompt_run_id": w.get("prompt_run_id"),
            "captured_at": w.get("captured_at"),
            "detail": w,
        })
    for rec in index.get("records") or []:
        if not _captured_at_passes(rec.get("captured_at")):
            continue
        for w in rec.get("warnings") or []:
            if w.get("kind") == "missing_required_field":
                violations.append({
                    "level": "block",
                    "kind": "missing_required_field",
                    "raw_event_path": rec.get("raw_event_path"),
                    "prompt_run_id": rec.get("prompt_run_id"),
                    "captured_at": rec.get("captured_at"),
                    "block_index": rec.get("block_index"),
                    "field": w.get("field"),
                })
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("--print", action="store_true", help="emit JSON to stdout")
    parser.add_argument("--write", action="store_true", help="write canonical projection")
    parser.add_argument("--check", action="store_true", help="exit non-zero on drift vs disk (currentness only)")
    parser.add_argument("--validate", action="store_true",
                        help="exit non-zero on semantic violations (nested / missing required / unknown version / duplicate recurrence_key)")
    parser.add_argument("--since", type=str, default=None, metavar="ISO_TIMESTAMP",
                        help="(with --validate) cutover timestamp; violations whose captured_at is before this are excluded "
                             "from the failure set. Allows historical scars to remain visible in the index while making "
                             "--validate gateable for new captures.")
    args = parser.parse_args()
    if not (args.print or args.write or args.check or args.validate):
        parser.error("pick one of --print / --write / --check / --validate")
    if args.since is not None and not args.validate:
        parser.error("--since only applies to --validate")

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
            f"({meta['movement_blocks_total']} terminal movement blocks across "
            f"{meta['events_with_block']} events; "
            f"{meta['run_warnings_total']} warnings)"
        )
        return 0
    if args.check:
        if not INDEX_PATH.exists():
            print("missing")
            return 1
        on_disk = json.loads(INDEX_PATH.read_text())
        on_disk["__meta"].pop("generated_at", None)
        fresh = json.loads(rendered)
        fresh["__meta"].pop("generated_at", None)
        if json.dumps(on_disk, sort_keys=True) == json.dumps(fresh, sort_keys=True):
            print("clean")
            return 0
        print("drift detected")
        return 1
    if args.validate:
        violations = collect_semantic_violations(index, since=args.since)
        cutover_note = f" (--since {args.since})" if args.since else ""
        if not violations:
            print(f"valid{cutover_note}")
            return 0
        kind_counts: dict[str, int] = {}
        for v in violations:
            k = v.get("kind") or "unknown"
            kind_counts[k] = kind_counts.get(k, 0) + 1
        sys.stderr.write(f"semantic violations{cutover_note}: {len(violations)} total\n")
        for k, c in sorted(kind_counts.items()):
            sys.stderr.write(f"  {k}: {c}\n")
        for v in violations[:5]:
            sys.stderr.write(
                f"  example: kind={v.get('kind')} "
                f"captured_at={v.get('captured_at') or '?'} "
                f"run={(v.get('prompt_run_id') or '?')[-12:]} "
                f"path={v.get('raw_event_path')}\n"
            )
        if len(violations) > 5:
            sys.stderr.write(f"  ... and {len(violations) - 5} more\n")
        print(f"invalid{cutover_note}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
