#!/usr/bin/env python3
"""Prompt-shelf runs index — compact metadata projection over captured runs.

Reads three substrates that the capture loop already produces and emits a
single JSON projection that downstream consumers (Obsidian Bases view, future
Kind Atlas row, future outbox classifier, future frontend lens) can browse
without scraping the full run-note markdown or raw-event JSON.

Sources
-------
  obsidian/prompt_shelf/usage/runs/<slot>/*.md       normalized run notes
  obsidian/prompt_shelf/usage/raw_events/<slot>/*.json   raw event sidecars
  obsidian/prompt_shelf/<slot> Ledger.md             receipt anchors

Output
------
  state/prompt_shelf/prompt_shelf_runs_index.json

The projection deliberately does NOT copy raw user/assistant text. Each row
points at the run-note path and raw-event path; consumers read those when
they need the full bytes. Index rows carry only metadata, hashes, sizes, and
segmentation char-counts.

CLI
---
    prompt_shelf_runs_index.py --print     # emit JSON to stdout
    prompt_shelf_runs_index.py --write     # write canonical index
    prompt_shelf_runs_index.py --check     # nonzero on integrity violation
    prompt_shelf_runs_index.py --summary   # fast metadata table by slot
    prompt_shelf_runs_index.py --summary --slot B2  # one slot only
    prompt_shelf_runs_index.py --coverage  # fast metadata coverage; nonzero
                                           # if any --require-slots is empty
    prompt_shelf_runs_index.py --review --slot B2 --limit 12
                                           # bounded private excerpt review:
                                           # prompt sent, operator addendum,
                                           # assistant closeout, failed-capture
                                           # diagnostics, and metadata
    prompt_shelf_runs_index.py --review --run-id <prompt_run_id>
                                           # inspect an older selected run

Integrity checks (--check)
--------------------------
  - no duplicate prompt_run_id across all slots
  - every run note's raw_event_path resolves on disk
  - prompt_slot directory matches frontmatter slot
  - prompt_run_id parseable from filename

Slot coverage (--coverage)
--------------------------
A separate gate from --check. The capture substrate can be integrity-clean
while still missing real captures for some current cockpit slots. Building
classifiers / Kind Atlas rows / frontend lenses against a slot-skewed sample
biases everything downstream. --coverage reports per-slot counts and exits
nonzero when any slot named via --require-slots has zero runs.

Command economy
---------------
--summary, --coverage, --check, and --review intentionally use metadata-only indexing:
they stat raw event sidecars for byte counts and integrity but do not read raw
prompt/provider bodies until a bounded review row is selected. Use --print,
--write, --nesting-audit, or --b3-lint-audit when the full raw-event path is
required.

Private-root boundary
---------------------
Use --summary/--coverage as the first prompt-shelf discovery route. Do not
scan obsidian/prompt_shelf/usage/runs or raw_events wholesale; open one
source run/raw file only after this metadata projection selects the row.
Use --review as the next private-root drilldown when the task needs the
prompt-sent -> agent-closeout trace shape before proposing prompt refinements.
Recent capture diagnostics are included in review output by default so failed
or incomplete captures remain visible in the same evidence surface as landed
runs.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
USAGE_ROOT = REPO_ROOT / "obsidian" / "prompt_shelf" / "usage"
RUNS_ROOT = USAGE_ROOT / "runs"
RAW_EVENTS_ROOT = USAGE_ROOT / "raw_events"
LEDGERS_ROOT = REPO_ROOT / "obsidian" / "prompt_shelf"
PROJECTION_PATH = REPO_ROOT / "state" / "prompt_shelf" / "prompt_shelf_runs_index.json"
CAPTURE_DIAGNOSTICS_ROOT = REPO_ROOT / "state" / "prompt_shelf" / "capture_diagnostics"

# Sibling fingerprint module (stdlib import is enough — same parent package)
_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import prompt_shelf_fingerprints as _fp  # noqa: E402
import b3_packet_lint as _b3_lint  # noqa: E402

SCHEMA_VERSION = "1.2.0"

SLOT_DIR_BY_SLOT = {
    "A0": "A0_explore",
    "B1": "B1_instantiation",
    "B2": "B2_continue",
    "B6": "B6_autonomous_seed",
    "B3": "B3_compact",
}

LEDGER_FILENAME_BY_SLOT = {
    "A0": "A0 Explore Ledger.md",
    "B1": "B1 Instantiation Ledger.md",
    "B2": "B2 Continue Ledger.md",
    "B2.2": "B2 Continue Ledger.md",
    "B3": "B3 Compact Ledger.md",
    "B6": "B6 Autonomous Seed Ledger.md",
}

# B2.2 is a B2-family semantic carryforward variant. B6 is the Type B
# autonomous-seed authoring slot. Both are captured and shown in summaries, but
# coverage gates stay on the four historical primary slots.
DEFAULT_REQUIRED_COVERAGE_SLOTS = ["A0", "B1", "B2", "B3"]
SLOT_ALIASES_BY_DIR_SLOT = {
    "B2": {"B2.2"},
}

DEFAULT_REVIEW_LIMIT = 12
MAX_REVIEW_LIMIT = 100
DEFAULT_REVIEW_SNIPPET_CHARS = 700
MAX_REVIEW_SNIPPET_CHARS = 2400

REVIEW_SIGNAL_NEEDLES = (
    "current_telos",
    "deliverable_type",
    "depth_floor",
    "authority_boundary",
    "integration_target",
    "mutation_contour",
    "mutation amplitude",
    "recipient_binding_status",
    "handoff_delivery_status",
    "external_reviewer_replay_status",
    "public_release_authority",
    "proof_authority_delta",
    "type a should",
    "type b should",
    "what changed",
    "anti-goals",
)

STOP_FRAME_OVERRIDE_SCENARIO_ID = (
    "type_b_no_op_after_deciding_evidence_operator_asks_action"
)
STOP_FRAME_RE = re.compile(
    r"\b("
    r"wait|no[- ]?op|no edits?|make no edits|do not mutate|"
    r"nothing (?:to do|changed)|status[- ]?only|stop at status"
    r")\b",
    re.IGNORECASE,
)
DECIDING_EVIDENCE_RE = re.compile(
    r"\b("
    r"deciding evidence|already supplied|reported(?:ly)? landed|"
    r"committed|validated|receipted|closed|workitem|cap(?:_| )quick|"
    r"execution receipt|trace capsule"
    r")\b",
    re.IGNORECASE,
)
OPERATOR_STATUS_ONLY_RE = re.compile(
    r"\b(status only|only status|just status|recap only|no edits?)\b",
    re.IGNORECASE,
)
OPERATOR_HIGH_AGENCY_RE = re.compile(
    r"\b(always something to do|have agency|go make edits?|make edits?|"
    r"stop wasting|do something|do the work)\b",
    re.IGNORECASE,
)
OPERATOR_CORRECTION_RE = re.compile(
    r"\b(fix(?: this)?|correct(?:ion)?|failure mode|self[- ]?error|"
    r"failed instruction|failed frame|patch)\b",
    re.IGNORECASE,
)
OPERATOR_ACTION_RE = re.compile(
    r"\b(act|action|mutate|edit|ship|bind|close|record|capture|"
    r"update|repair|validate)\b",
    re.IGNORECASE,
)


@dataclass
class RunIndexEntry:
    prompt_run_id: str
    prompt_slot: str
    prompt_slug: str
    captured_at: str
    source: str
    conversation_id: str | None
    conversation_url: str | None
    user_turn_index: int | None
    assistant_turn_index: int | None
    match_method: str
    match_confidence: float
    segmented: bool
    pre_prompt_chars: int | None
    matched_prompt_chars: int | None
    post_prompt_chars: int | None
    inferred_addendum_chars: int | None
    user_message_chars: int | None
    assistant_message_chars: int | None
    user_message_sha256: str | None
    assistant_message_sha256: str | None
    run_note_path: str
    run_note_bytes: int
    raw_event_path: str
    raw_event_bytes: int
    raw_event_present: bool
    ledger_receipt_present: bool
    b3_packet_lint_status: str | None = None
    b3_packet_lint_issue_count: int | None = None
    b3_packet_lint_issue_codes: list[str] = field(default_factory=list)
    # Nested-prompt audit: which other slot anchors appeared in the user message,
    # at what positions. Used to flag captures where multiple cockpit prompts
    # are textually present (the operator pasted a packet that quoted other
    # prompt bodies). Coverage is "ambiguous" — not necessarily wrong, but
    # worth surfacing before any classifier runs.
    other_anchor_positions: dict[str, int] = field(default_factory=dict)
    matched_anchor_position: int | None = None
    other_anchors_count: int = 0
    nested_match_suspected: bool = False
    issues: list[str] = field(default_factory=list)


def _frontmatter(text: str) -> dict[str, str]:
    """Parse a flat top-of-file YAML-style frontmatter block.

    Keeps it minimal: top-level `key: value` pairs only. List/nested values are
    not consumed by this index (we only need scalar metadata here).
    """
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    fm: dict[str, str] = {}
    for line in parts[1].splitlines():
        if not line or line.startswith(" ") or line.startswith("\t"):
            continue
        if line.lstrip().startswith("-"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    return fm


def _read_frontmatter_text(path: Path, *, max_bytes: int = 64 * 1024) -> str:
    """Read only the leading frontmatter block from a run note.

    Run notes can include large pasted prompt/provider transcripts. The index
    only consumes scalar frontmatter from the note, so full-file reads turn
    summary/check routes into corpus scans for no extra integrity signal.
    """
    try:
        with path.open("rb") as fh:
            prefix = fh.read(max_bytes)
    except OSError:
        return ""
    text = prefix.decode("utf-8", errors="replace")
    if not text.startswith("---"):
        return text
    # Keep the closing delimiter when it is inside the bounded prefix.
    match = re.search(r"\n---(?:\r?\n|$)", text[3:])
    if match:
        end = 3 + match.end()
        return text[:end]
    return text


def _maybe_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _maybe_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _maybe_bool(value: str | None) -> bool:
    return str(value).strip().lower() == "true"


def _b3_lint_from_raw_event(raw: dict[str, Any], *, run_id: str) -> dict[str, Any] | None:
    """Compute or normalize B3 packet lint status for a captured raw event."""
    if str(raw.get("prompt_slot") or "").upper() != "B3":
        return None
    assistant = raw.get("assistant_message") or {}
    assistant_text = assistant.get("raw_text") if isinstance(assistant, dict) else ""
    if not isinstance(assistant_text, str) or not assistant_text.lstrip().startswith("PACKET v=3.2"):
        return None

    existing = raw.get("b3_packet_lint")
    if isinstance(existing, dict) and existing.get("status"):
        codes = existing.get("issue_codes")
        return {
            "status": str(existing.get("status") or ""),
            "issue_count": _maybe_int(str(existing.get("issue_count")))
                if existing.get("issue_count") is not None else None,
            "issue_codes": [str(code) for code in codes] if isinstance(codes, list) else [],
        }

    report = _b3_lint.lint_packet_text(assistant_text, name=f"{run_id}:assistant_message")
    issues = report.get("issues") if isinstance(report.get("issues"), list) else []
    issue_codes = sorted({
        str(issue.get("code"))
        for issue in issues
        if isinstance(issue, dict) and issue.get("code")
    })
    issue_count = int(report.get("issue_count") or 0)
    return {
        "status": "clean" if issue_count == 0 else "issues",
        "issue_count": issue_count,
        "issue_codes": issue_codes,
    }


def _load_receipts_by_slot(ledgers_root: Path) -> dict[str, set[str]]:
    """Scan each root ledger for ``aiw:receipt prompt_run_id="..."`` anchors."""
    by_slot: dict[str, set[str]] = {
        slot: set()
        for slot in sorted(set(SLOT_DIR_BY_SLOT) | set(LEDGER_FILENAME_BY_SLOT))
    }
    pattern = re.compile(r'aiw:receipt prompt_run_id="([^"]+)"')
    for slot, filename in LEDGER_FILENAME_BY_SLOT.items():
        path = ledgers_root / filename
        if not path.exists():
            continue
        try:
            text = path.read_text()
        except OSError:
            continue
        for m in pattern.finditer(text):
            by_slot[slot].add(m.group(1))
    return by_slot


def _entry_from_run(run_path: Path, slot: str, slot_dir_name: str,
                    receipts: set[str], raw_events_root: Path, *,
                    include_raw_details: bool = True) -> RunIndexEntry:
    text = _read_frontmatter_text(run_path)
    fm = _frontmatter(text)
    run_id = fm.get("prompt_run_id", "")
    raw_event_rel = fm.get("raw_event_path", "")
    issues: list[str] = []

    if not run_id:
        issues.append("missing_prompt_run_id")

    fm_slot = fm.get("prompt_slot", "")
    allowed_slots = {slot, *SLOT_ALIASES_BY_DIR_SLOT.get(slot, set())}
    entry_slot = slot
    if fm_slot and fm_slot in allowed_slots:
        entry_slot = fm_slot
    elif fm_slot and fm_slot != slot:
        issues.append(f"slot_mismatch: frontmatter={fm_slot} dir={slot}")

    # Parse run id from filename if frontmatter is empty
    if not run_id:
        m = re.match(r"^([^-]+--[A-Z0-9]+--[a-f0-9]+)", run_path.name)
        if m:
            run_id = m.group(1)
        else:
            run_id = run_path.stem

    # Resolve raw event path. The frontmatter stores a repo-relative path; we
    # resolve against REPO_ROOT (or, in tests, the active raw_events_root's
    # grandparent).
    raw_event_present = False
    raw_event_bytes = 0
    raw_event_resolved: Path | None = None
    if raw_event_rel:
        candidate = REPO_ROOT / raw_event_rel
        if candidate.exists():
            raw_event_resolved = candidate
        else:
            # Test/dev fallback: try the active raw_events_root by basename
            fallback = raw_events_root / slot_dir_name / Path(raw_event_rel).name
            if fallback.exists():
                raw_event_resolved = fallback
        if raw_event_resolved is not None and raw_event_resolved.exists():
            raw_event_present = True
            try:
                raw_event_bytes = raw_event_resolved.stat().st_size
            except OSError:
                pass
        else:
            issues.append("raw_event_missing")
    else:
        issues.append("missing_raw_event_path")

    # Pull richer detail from raw event JSON if available
    pre_chars = matched_chars = post_chars = addendum_chars = None
    user_chars = assistant_chars = None
    other_anchor_positions: dict[str, int] = {}
    matched_anchor_pos: int | None = None
    b3_lint_status: str | None = None
    b3_lint_issue_count: int | None = None
    b3_lint_issue_codes: list[str] = []
    if include_raw_details and raw_event_resolved is not None and raw_event_resolved.exists():
        try:
            raw = json.loads(raw_event_resolved.read_text())
        except (OSError, json.JSONDecodeError):
            issues.append("raw_event_unreadable")
            raw = {}
        seg = raw.get("segmentation") or {}
        if isinstance(seg, dict):
            pre_chars = len(seg.get("pre_prompt_material") or "")
            matched_chars = len(seg.get("matched_prompt_invocation") or "")
            post_chars = len(seg.get("post_prompt_material") or "")
            addendum_chars = len(seg.get("inferred_latest_operator_addendum") or "")
            mps = seg.get("matched_prompt_char_start")
            if isinstance(mps, int):
                matched_anchor_pos = mps
        user_msg = raw.get("user_message") or {}
        assistant_msg = raw.get("assistant_message") or {}
        if isinstance(user_msg, dict):
            user_chars = user_msg.get("char_count")
            other_anchor_positions = _scan_other_anchor_positions(
                user_msg.get("raw_text") or "", entry_slot,
            )
        if isinstance(assistant_msg, dict):
            assistant_chars = assistant_msg.get("char_count")
            b3_status = _b3_lint_from_raw_event(raw, run_id=run_id)
            if b3_status is not None:
                b3_lint_status = b3_status["status"]
                b3_lint_issue_count = b3_status["issue_count"]
                b3_lint_issue_codes = b3_status["issue_codes"]
    nested_match_suspected = bool(
        other_anchor_positions
        and matched_anchor_pos is not None
        and any(pos < matched_anchor_pos for pos in other_anchor_positions.values())
    )
    # Note: nested_match_suspected is NOT added to `issues` — it's a review
    # signal, not an integrity violation. Surface via --nesting-audit and the
    # per-row field; --check stays focused on path/frontmatter/duplicate
    # integrity.

    try:
        run_note_bytes = run_path.stat().st_size
    except OSError:
        run_note_bytes = 0

    return RunIndexEntry(
        prompt_run_id=run_id,
        prompt_slot=entry_slot,
        prompt_slug=fm.get("prompt_slug", ""),
        captured_at=fm.get("captured_at", ""),
        source=fm.get("source", ""),
        conversation_id=fm.get("conversation_id") or None,
        conversation_url=fm.get("conversation_url") or None,
        user_turn_index=_maybe_int(fm.get("user_turn_index")),
        assistant_turn_index=_maybe_int(fm.get("assistant_turn_index")),
        match_method=fm.get("prompt_match_method", "unspecified"),
        match_confidence=_maybe_float(fm.get("prompt_match_confidence")),
        segmented=_maybe_bool(fm.get("segmented")),
        pre_prompt_chars=pre_chars,
        matched_prompt_chars=matched_chars,
        post_prompt_chars=post_chars,
        inferred_addendum_chars=addendum_chars,
        user_message_chars=user_chars,
        assistant_message_chars=assistant_chars,
        user_message_sha256=fm.get("user_message_sha256") or None,
        assistant_message_sha256=fm.get("assistant_message_sha256") or None,
        run_note_path=run_path.relative_to(REPO_ROOT).as_posix()
            if REPO_ROOT in run_path.parents else run_path.as_posix(),
        run_note_bytes=run_note_bytes,
        raw_event_path=raw_event_rel,
        raw_event_bytes=raw_event_bytes,
        raw_event_present=raw_event_present,
        ledger_receipt_present=run_id in receipts,
        b3_packet_lint_status=b3_lint_status,
        b3_packet_lint_issue_count=b3_lint_issue_count,
        b3_packet_lint_issue_codes=b3_lint_issue_codes,
        other_anchor_positions=other_anchor_positions,
        matched_anchor_position=matched_anchor_pos,
        other_anchors_count=len(other_anchor_positions),
        nested_match_suspected=nested_match_suspected,
        issues=issues,
    )


def _scan_other_anchor_positions(user_text: str, matched_slot: str) -> dict[str, int]:
    """For each cockpit slot OTHER than the matched one, report the position of
    its anchor in the user message (or omit the slot if the anchor is absent).

    Uses index-preserving normalization (lowercase + smart-quote/dash
    translation, NO whitespace collapse) so the position the scan reports is
    comparable to ``segmentation.matched_prompt_char_start`` from the observer
    — both are now raw-text coordinates. The fingerprint anchor itself was
    built with whitespace collapse, so we match it as a whitespace-tolerant
    regex (each token separated by ``\\s+``).

    This is the diagnostic that surfaces nested-prompt risk: when a user
    message contains anchors for multiple slots, the operator pasted a packet
    that quoted other prompt bodies. The matched slot may still be correct,
    but the capture is no longer unambiguous.
    """
    if not user_text:
        return {}
    fingerprints = _fp.build_fingerprints()
    norm = user_text.lower().translate(str.maketrans({
        "‘": "'", "’": "'",  # smart single quotes
        "“": '"', "”": '"',  # smart double quotes
        "—": "-", "–": "-",  # em / en dash
    }))
    out: dict[str, int] = {}
    for fingerprint in fingerprints:
        if fingerprint.slot == matched_slot:
            continue
        if not fingerprint.anchor:
            continue
        tokens = fingerprint.anchor.split()
        if not tokens:
            continue
        pattern = r"\s+".join(re.escape(t) for t in tokens)
        m = re.search(pattern, norm)
        if m:
            out[fingerprint.slot] = m.start()
    return out


def build_index(*, runs_root: Path | None = None,
                raw_events_root: Path | None = None,
                ledgers_root: Path | None = None,
                include_raw_details: bool = True) -> list[RunIndexEntry]:
    """Build the prompt-shelf runs index.

    ``include_raw_details=False`` is the command-economy path for summary and
    coverage: it still stats raw sidecars and checks receipts, but it does not
    read raw event bodies. Full integrity/audit/write paths keep the default.
    """
    runs = runs_root if runs_root is not None else RUNS_ROOT
    raws = raw_events_root if raw_events_root is not None else RAW_EVENTS_ROOT
    ledgers = ledgers_root if ledgers_root is not None else LEDGERS_ROOT
    receipts_by_slot = _load_receipts_by_slot(ledgers)
    entries: list[RunIndexEntry] = []
    if not runs.is_dir():
        return entries
    for slot, slot_dir_name in SLOT_DIR_BY_SLOT.items():
        slot_runs = runs / slot_dir_name
        if not slot_runs.is_dir():
            continue
        alias_slots = {slot, *SLOT_ALIASES_BY_DIR_SLOT.get(slot, set())}
        receipts: set[str] = set()
        for receipt_slot in alias_slots:
            receipts.update(receipts_by_slot.get(receipt_slot, set()))
        for note in sorted(slot_runs.glob("*.md")):
            entries.append(_entry_from_run(
                note, slot, slot_dir_name, receipts, raws,
                include_raw_details=include_raw_details,
            ))
    return entries


def detect_duplicates(entries: list[RunIndexEntry]) -> list[str]:
    seen: dict[str, int] = {}
    for e in entries:
        if not e.prompt_run_id:
            continue
        seen[e.prompt_run_id] = seen.get(e.prompt_run_id, 0) + 1
    return sorted(rid for rid, count in seen.items() if count > 1)


def projection_payload(entries: list[RunIndexEntry]) -> dict[str, Any]:
    by_slot: dict[str, dict[str, Any]] = {}
    total_run_bytes = 0
    total_raw_bytes = 0
    receipt_present = 0
    issues_total = 0
    nested_suspect_count = 0
    multi_anchor_count = 0
    b3_linted_count = 0
    b3_lint_issue_run_count = 0
    b3_lint_issue_total = 0
    largest = {"prompt_run_id": None, "bytes": 0}
    for e in entries:
        slot = by_slot.setdefault(e.prompt_slot, {
            "run_count": 0,
            "run_note_bytes": 0,
            "raw_event_bytes": 0,
            "receipt_present_count": 0,
            "issues_count": 0,
            "multi_anchor_count": 0,
            "nested_suspect_count": 0,
            "b3_linted_count": 0,
            "b3_lint_issue_run_count": 0,
            "b3_lint_issue_total": 0,
        })
        slot["run_count"] += 1
        slot["run_note_bytes"] += e.run_note_bytes
        slot["raw_event_bytes"] += e.raw_event_bytes
        slot["receipt_present_count"] += int(e.ledger_receipt_present)
        slot["issues_count"] += len(e.issues)
        slot["multi_anchor_count"] += int(e.other_anchors_count > 0)
        slot["nested_suspect_count"] += int(e.nested_match_suspected)
        total_run_bytes += e.run_note_bytes
        total_raw_bytes += e.raw_event_bytes
        receipt_present += int(e.ledger_receipt_present)
        issues_total += len(e.issues)
        if e.other_anchors_count > 0:
            multi_anchor_count += 1
        if e.nested_match_suspected:
            nested_suspect_count += 1
        if e.b3_packet_lint_status is not None:
            b3_linted_count += 1
            slot["b3_linted_count"] += 1
            issue_count = int(e.b3_packet_lint_issue_count or 0)
            b3_lint_issue_total += issue_count
            slot["b3_lint_issue_total"] += issue_count
            if issue_count:
                b3_lint_issue_run_count += 1
                slot["b3_lint_issue_run_count"] += 1
        combined = e.run_note_bytes + e.raw_event_bytes
        if combined > largest["bytes"]:
            largest = {"prompt_run_id": e.prompt_run_id, "bytes": combined}
    duplicates = detect_duplicates(entries)
    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": "prompt_shelf_runs_index",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "run_count": len(entries),
            "run_count_by_slot": {s: by_slot[s]["run_count"] for s in by_slot},
            "receipt_present_count": receipt_present,
            "duplicate_prompt_run_ids": duplicates,
            "issues_total": issues_total,
            "multi_anchor_count": multi_anchor_count,
            "nested_match_suspected_count": nested_suspect_count,
            "b3_linted_count": b3_linted_count,
            "b3_lint_issue_run_count": b3_lint_issue_run_count,
            "b3_lint_issue_total": b3_lint_issue_total,
            "total_run_note_bytes": total_run_bytes,
            "total_raw_event_bytes": total_raw_bytes,
            "largest_run": largest,
            "by_slot": by_slot,
        },
        "runs": [asdict(e) for e in entries],
    }


def render_nesting_audit(entries: list[RunIndexEntry]) -> str:
    """Per-capture audit of multi-anchor presence. Surfaces every run where
    more than one cockpit prompt anchor was textually present in the user
    message (the operator's paste contained a quoted prompt body)."""
    lines = [f"prompt_shelf_runs nesting audit — {len(entries)} runs scanned"]
    multi = [e for e in entries if e.other_anchors_count > 0]
    suspect = [e for e in entries if e.nested_match_suspected]
    lines.append(f"  multi-anchor runs:           {len(multi)}")
    lines.append(f"  nested-match-suspected runs: {len(suspect)}")
    lines.append("")
    if not multi:
        lines.append("  (no multi-anchor captures — all runs had only one prompt anchor in the user message)")
        return "\n".join(lines)
    for e in multi:
        flag = " ✗ NESTED-SUSPECT" if e.nested_match_suspected else ""
        lines.append(
            f"  {e.prompt_run_id}  slot={e.prompt_slot}{flag}"
        )
        lines.append(
            f"    matched at pos {e.matched_anchor_position}, also present: "
            + ", ".join(f"{slot}@{pos}" for slot, pos in
                        sorted(e.other_anchor_positions.items(),
                               key=lambda kv: kv[1]))
        )
    return "\n".join(lines)


def render_b3_lint_audit(entries: list[RunIndexEntry]) -> str:
    rows = [e for e in entries if e.b3_packet_lint_status is not None]
    issue_rows = [e for e in rows if int(e.b3_packet_lint_issue_count or 0) > 0]
    lines = [f"prompt_shelf_runs B3 packet lint audit — {len(rows)} B3 PACKET v=3.2 runs linted"]
    lines.append(f"  runs with issues: {len(issue_rows)}")
    lines.append(f"  total issues:     {sum(int(e.b3_packet_lint_issue_count or 0) for e in rows)}")
    lines.append("")
    if not rows:
        lines.append("  (no captured B3 PACKET v=3.2 outputs found)")
        return "\n".join(lines)
    for e in rows:
        issue_count = int(e.b3_packet_lint_issue_count or 0)
        status = "clean" if issue_count == 0 else "issues"
        codes = ", ".join(e.b3_packet_lint_issue_codes[:12])
        lines.append(
            f"  {e.prompt_run_id}  {status}  issues={issue_count}"
            + (f"  codes={codes}" if codes else "")
        )
    return "\n".join(lines)


def write_projection(payload: dict[str, Any], path: Path = PROJECTION_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _capture_diagnostic_summary(root: Path | None = None,
                                slots: list[str] | None = None) -> dict[str, Any]:
    wanted = {slot.strip().upper() for slot in slots or [] if slot.strip()}
    by_reason: dict[str, int] = {}
    newest: tuple[_dt.datetime, str] | None = None
    total = 0
    for path, diagnostic in _load_capture_diagnostics(root):
        slot = _diagnostic_slot(diagnostic) or "unknown"
        if wanted and slot not in wanted:
            continue
        reason = str(diagnostic.get("skipped_reason") or "unknown")
        total += 1
        by_reason[reason] = by_reason.get(reason, 0) + 1
        created = _parse_captured_at(str(diagnostic.get("created_at") or ""))
        diag_id = _diagnostic_id(path, diagnostic)
        if newest is None or (created, diag_id) > newest:
            newest = (created, diag_id)
    return {
        "total": total,
        "by_reason": by_reason,
        "newest_id": newest[1] if newest else None,
    }


def render_summary(payload: dict[str, Any], *, slots: list[str] | None = None,
                   diagnostics_root: Path | None = None) -> str:
    """Compact human-readable summary. Always includes every current cockpit
    slot, even ones with zero runs, so missing slots are visible."""
    meta = payload["__meta"]
    lines = [
        f"prompt_shelf_runs_index — {meta['run_count']} runs total",
        f"  generated_at: {meta['generated_at']}",
        f"  receipts:     {meta['receipt_present_count']}/{meta['run_count']}",
        f"  issues:       {meta['issues_total']}",
        f"  B3 lint:      {meta['b3_linted_count']} linted · "
        f"{meta['b3_lint_issue_run_count']} runs with issues · "
        f"{meta['b3_lint_issue_total']} total issues",
        f"  duplicates:   {len(meta['duplicate_prompt_run_ids'])}",
        f"  raw bytes:    {meta['total_raw_event_bytes']:,}",
        f"  run bytes:    {meta['total_run_note_bytes']:,}",
        "  boundary:     metadata-only; raw prompt/provider bodies stay in source refs",
        "  safe route:   use --summary/--coverage first; open one selected row if needed",
        "",
        f"  largest run:  {meta['largest_run']['prompt_run_id'] or '(none)'} "
        f"({meta['largest_run']['bytes']:,} bytes)",
    ]
    if diagnostics_root is not None:
        diagnostics = _capture_diagnostic_summary(diagnostics_root, slots=slots)
        lines.append(
            f"  diagnostics:  {diagnostics['total']} capture diagnostics"
            + (f" · newest {diagnostics['newest_id']}" if diagnostics["newest_id"] else "")
        )
        lines.append("                included by default in --review; use --no-diagnostics to hide them")
        if diagnostics["by_reason"]:
            reason_counts = ", ".join(
                f"{reason}={count}"
                for reason, count in sorted(diagnostics["by_reason"].items())
            )
            lines.append(f"                reasons: {reason_counts}")
    lines.extend(["", "  by slot:"])
    by_slot = meta["by_slot"]
    # Always render every current cockpit slot; render variant slots too when
    # the index contains captures for them. Variant slots stay non-required for
    # coverage, but hiding them in the summary makes active Type B evidence
    # easy to miss.
    display_slots = slots if slots is not None else _slot_display_order(by_slot)
    for slot in display_slots:
        stats = by_slot.get(slot)
        if stats is None:
            lines.append(f"    {slot}:   0 runs · (no captures yet)")
            continue
        lines.append(
            f"    {slot}: {stats['run_count']:>3} runs · "
            f"receipts {stats['receipt_present_count']}/{stats['run_count']} · "
            f"issues {stats['issues_count']} · "
            f"B3 lint {stats.get('b3_lint_issue_run_count', 0)}/{stats.get('b3_linted_count', 0)} · "
            f"raw {stats['raw_event_bytes']:,}B · "
            f"runs {stats['run_note_bytes']:,}B"
        )
    return "\n".join(lines)


def _bounded_int(value: int | None, *, default: int, low: int, high: int) -> int:
    try:
        parsed = int(value if value is not None else default)
    except (TypeError, ValueError):
        parsed = default
    return max(low, min(parsed, high))


def _parse_captured_at(value: str) -> _dt.datetime:
    if not value:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    normalized = value.strip().replace("Z", "+00:00")
    try:
        parsed = _dt.datetime.fromisoformat(normalized)
    except ValueError:
        return _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=_dt.timezone.utc)
    return parsed


def _slot_dir_name_for_entry(slot: str) -> str:
    wanted = str(slot or "").strip().upper()
    for base_slot, dirname in SLOT_DIR_BY_SLOT.items():
        aliases = SLOT_ALIASES_BY_DIR_SLOT.get(base_slot, set())
        if wanted == base_slot or wanted in aliases:
            return dirname
    return wanted


def _resolve_raw_event_path(entry: RunIndexEntry, *,
                            raw_events_root: Path | None = None) -> Path | None:
    raw_event_rel = entry.raw_event_path or ""
    if not raw_event_rel:
        return None
    raw_root = raw_events_root if raw_events_root is not None else RAW_EVENTS_ROOT
    candidates = [
        REPO_ROOT / raw_event_rel,
        raw_root / _slot_dir_name_for_entry(entry.prompt_slot) / Path(raw_event_rel).name,
        raw_root / Path(raw_event_rel).name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _load_raw_event_for_entry(entry: RunIndexEntry, *,
                              raw_events_root: Path | None = None) -> tuple[dict[str, Any], Path | None, list[str]]:
    path = _resolve_raw_event_path(entry, raw_events_root=raw_events_root)
    if path is None:
        return {}, None, ["raw_event_missing"]
    try:
        return json.loads(path.read_text()), path, []
    except (OSError, json.JSONDecodeError) as exc:
        return {}, path, [f"raw_event_unreadable:{exc.__class__.__name__}"]


def _clean_excerpt(text: str, *, max_chars: int) -> str:
    compact = re.sub(r"[ \t]+", " ", str(text or "")).strip()
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + "..."


def _nonempty_lines(text: str) -> list[str]:
    return [line.strip() for line in str(text or "").splitlines() if line.strip()]


def _first_lines_excerpt(text: str, *, max_lines: int, max_chars: int) -> str:
    return _clean_excerpt("\n".join(_nonempty_lines(text)[:max_lines]), max_chars=max_chars)


def _tail_lines_excerpt(text: str, *, max_lines: int, max_chars: int) -> str:
    lines = _nonempty_lines(text)
    return _clean_excerpt("\n".join(lines[-max_lines:]), max_chars=max_chars)


def _signal_key(line: str) -> str:
    stripped = line.strip().lstrip("#>- ").strip()
    stripped = stripped.replace("**", "").replace("__", "").replace("`", "")
    return stripped.lower()


def _extract_contract_signals(text: str, *, max_signals: int = 12,
                              max_chars: int = 220) -> list[str]:
    signals: list[str] = []
    for line in _nonempty_lines(text):
        normalized = _signal_key(line)
        if any(needle in normalized for needle in REVIEW_SIGNAL_NEEDLES):
            signals.append(_clean_excerpt(line, max_chars=max_chars))
        if len(signals) >= max_signals:
            break
    return signals


def _raw_event_texts(raw: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
    user_msg = raw.get("user_message") if isinstance(raw.get("user_message"), dict) else {}
    assistant_msg = raw.get("assistant_message") if isinstance(raw.get("assistant_message"), dict) else {}
    seg = raw.get("segmentation") if isinstance(raw.get("segmentation"), dict) else {}
    return (
        str(user_msg.get("raw_text") or ""),
        str(assistant_msg.get("raw_text") or ""),
        seg,
    )


def _entry_matches_review_contains(entry: RunIndexEntry, needle: str, *,
                                   raw_events_root: Path | None = None) -> bool:
    query = needle.strip().lower()
    if not query:
        return True
    metadata_blob = "\n".join(
        str(part or "")
        for part in (
            entry.prompt_run_id,
            entry.prompt_slot,
            entry.prompt_slug,
            entry.captured_at,
            entry.source,
            entry.conversation_id,
            entry.run_note_path,
            entry.raw_event_path,
        )
    ).lower()
    if query in metadata_blob:
        return True
    raw, _path, _issues = _load_raw_event_for_entry(entry, raw_events_root=raw_events_root)
    user_text, assistant_text, seg = _raw_event_texts(raw)
    body_blob = "\n".join(
        [
            user_text,
            assistant_text,
            str(seg.get("matched_prompt_invocation") or ""),
            str(seg.get("inferred_latest_operator_addendum") or ""),
        ]
    ).lower()
    return query in body_blob


def _diagnostic_id(path: Path, diagnostic: dict[str, Any]) -> str:
    value = diagnostic.get("diagnostic_id") or diagnostic.get("prompt_run_id")
    return str(value or path.stem)


def _diagnostic_slot(diagnostic: dict[str, Any]) -> str:
    return str(diagnostic.get("slot") or diagnostic.get("prompt_slot") or "").upper()


def _diagnostic_text_blob(diagnostic: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in (
        "skipped_reason",
        "conversation_id",
        "conversation_url",
        "tab_title",
        "assistant_text",
        "user_text_tail",
    ):
        parts.append(str(diagnostic.get(key) or ""))
    for shape_key in ("user_shape", "assistant_shape"):
        shape = diagnostic.get(shape_key)
        if isinstance(shape, dict):
            parts.extend(str(shape.get(k) or "") for k in ("head", "tail", "sha16"))
    return "\n".join(parts)


def _load_capture_diagnostics(root: Path | None = None) -> list[tuple[Path, dict[str, Any]]]:
    diag_root = root if root is not None else CAPTURE_DIAGNOSTICS_ROOT
    if not diag_root.is_dir():
        return []
    rows: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(diag_root.glob("*.json")):
        try:
            diagnostic = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(diagnostic, dict):
            rows.append((path, diagnostic))
    return rows


def select_diagnostic_review_rows(*,
                                  diagnostics_root: Path | None = None,
                                  slot: str | None = None,
                                  run_ids: list[str] | None = None,
                                  contains: str | None = None,
                                  limit: int = DEFAULT_REVIEW_LIMIT,
                                  max_snippet_chars: int = DEFAULT_REVIEW_SNIPPET_CHARS) -> list[dict[str, Any]]:
    wanted_slot = slot.strip().upper() if slot else None
    wanted_ids = {
        item.strip()
        for item in (run_ids or [])
        for item in item.split(",")
        if item.strip()
    }
    query = contains.strip().lower() if contains else ""
    bounded_limit = _bounded_int(limit, default=DEFAULT_REVIEW_LIMIT, low=1, high=MAX_REVIEW_LIMIT)
    candidates: list[tuple[_dt.datetime, str, dict[str, Any]]] = []
    for path, diagnostic in _load_capture_diagnostics(diagnostics_root):
        diag_id = _diagnostic_id(path, diagnostic)
        diag_slot = _diagnostic_slot(diagnostic)
        if wanted_slot and diag_slot != wanted_slot:
            continue
        if wanted_ids and diag_id not in wanted_ids and path.name not in wanted_ids:
            continue
        if query and query not in _diagnostic_text_blob(diagnostic).lower():
            continue
        row = _diagnostic_review_row(
            path,
            diagnostic,
            max_snippet_chars=max_snippet_chars,
        )
        captured_at = _parse_captured_at(str(diagnostic.get("created_at") or ""))
        candidates.append((captured_at, diag_id, row))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    if wanted_ids:
        return [row for _captured, _diag_id, row in candidates]
    return [row for _captured, _diag_id, row in candidates[:bounded_limit]]


def select_review_entries(entries: list[RunIndexEntry], *,
                          run_ids: list[str] | None = None,
                          contains: str | None = None,
                          limit: int = DEFAULT_REVIEW_LIMIT,
                          raw_events_root: Path | None = None) -> list[RunIndexEntry]:
    """Select runs for bounded review.

    Default selection is recent-first and limited. ``--run-id`` overrides
    recency so an old selected run can be inspected directly. ``--contains`` is
    an explicit private-root body search and still returns a bounded result.
    """
    wanted_ids = {
        item.strip()
        for item in (run_ids or [])
        for item in item.split(",")
        if item.strip()
    }
    bounded_limit = _bounded_int(limit, default=DEFAULT_REVIEW_LIMIT, low=1, high=MAX_REVIEW_LIMIT)
    ordered = sorted(
        entries,
        key=lambda entry: (_parse_captured_at(entry.captured_at), entry.prompt_run_id),
        reverse=True,
    )
    if wanted_ids:
        selected = [entry for entry in ordered if entry.prompt_run_id in wanted_ids]
    else:
        selected = ordered
    if contains:
        selected = [
            entry
            for entry in selected
            if _entry_matches_review_contains(entry, contains, raw_events_root=raw_events_root)
        ]
    if wanted_ids:
        return selected
    return selected[:bounded_limit]


def _review_row(entry: RunIndexEntry, *,
                raw_events_root: Path | None = None,
                max_snippet_chars: int = DEFAULT_REVIEW_SNIPPET_CHARS) -> dict[str, Any]:
    max_chars = _bounded_int(
        max_snippet_chars,
        default=DEFAULT_REVIEW_SNIPPET_CHARS,
        low=120,
        high=MAX_REVIEW_SNIPPET_CHARS,
    )
    raw, raw_path, read_issues = _load_raw_event_for_entry(entry, raw_events_root=raw_events_root)
    user_text, assistant_text, seg = _raw_event_texts(raw)
    matched_prompt = str(seg.get("matched_prompt_invocation") or "")
    operator_addendum = str(seg.get("inferred_latest_operator_addendum") or "")
    post_prompt = str(seg.get("post_prompt_material") or "")
    prompt_sent_excerpt = matched_prompt or user_text
    addendum_excerpt = operator_addendum or post_prompt or _tail_lines_excerpt(user_text, max_lines=8, max_chars=max_chars)
    user_msg = raw.get("user_message") if isinstance(raw.get("user_message"), dict) else {}
    assistant_msg = raw.get("assistant_message") if isinstance(raw.get("assistant_message"), dict) else {}
    return {
        "prompt_run_id": entry.prompt_run_id,
        "prompt_slot": entry.prompt_slot,
        "prompt_slug": entry.prompt_slug,
        "captured_at": entry.captured_at,
        "source": entry.source,
        "conversation_id": entry.conversation_id,
        "user_turn_index": entry.user_turn_index,
        "assistant_turn_index": entry.assistant_turn_index,
        "match": {
            "method": entry.match_method,
            "confidence": entry.match_confidence,
            "segmented": entry.segmented,
        },
        "char_counts": {
            "user_message": user_msg.get("char_count", entry.user_message_chars),
            "assistant_message": assistant_msg.get("char_count", entry.assistant_message_chars),
            "pre_prompt": len(str(seg.get("pre_prompt_material") or "")),
            "matched_prompt": len(matched_prompt),
            "post_prompt": len(post_prompt),
            "inferred_addendum": len(operator_addendum),
        },
        "hashes": {
            "user_sha256_prefix": (entry.user_message_sha256 or "")[:12] or None,
            "assistant_sha256_prefix": (entry.assistant_message_sha256 or "")[:12] or None,
        },
        "refs": {
            "run_note_path": entry.run_note_path,
            "raw_event_path": entry.raw_event_path,
            "diagnostic_path": None,
            "raw_event_resolved": raw_path.relative_to(REPO_ROOT).as_posix()
                if raw_path is not None and REPO_ROOT in raw_path.parents
                else (raw_path.as_posix() if raw_path is not None else None),
        },
        "receipt": {
            "ledger_receipt_present": entry.ledger_receipt_present,
            "raw_event_present": raw_path is not None,
            "read_issues": read_issues,
        },
        "prompt_sent_excerpt": _clean_excerpt(prompt_sent_excerpt, max_chars=max_chars),
        "operator_addendum_excerpt": _clean_excerpt(addendum_excerpt, max_chars=max_chars),
        "assistant_opening_excerpt": _first_lines_excerpt(assistant_text, max_lines=8, max_chars=max_chars),
        "assistant_closeout_excerpt": _tail_lines_excerpt(assistant_text, max_lines=10, max_chars=max_chars),
        "prompt_contract_signals": _extract_contract_signals(user_text, max_signals=10),
        "assistant_contract_signals": _extract_contract_signals(assistant_text, max_signals=10),
    }


def _diagnostic_shape(diagnostic: dict[str, Any], key: str) -> dict[str, Any]:
    shape = diagnostic.get(key)
    return shape if isinstance(shape, dict) else {}


def _diagnostic_review_row(path: Path,
                           diagnostic: dict[str, Any], *,
                           max_snippet_chars: int = DEFAULT_REVIEW_SNIPPET_CHARS) -> dict[str, Any]:
    max_chars = _bounded_int(
        max_snippet_chars,
        default=DEFAULT_REVIEW_SNIPPET_CHARS,
        low=120,
        high=MAX_REVIEW_SNIPPET_CHARS,
    )
    user_shape = _diagnostic_shape(diagnostic, "user_shape")
    assistant_shape = _diagnostic_shape(diagnostic, "assistant_shape")
    assistant_text = str(diagnostic.get("assistant_text") or "")
    user_tail = str(diagnostic.get("user_text_tail") or user_shape.get("tail") or "")
    user_head = str(user_shape.get("head") or "")
    assistant_head = assistant_text or str(assistant_shape.get("head") or "")
    assistant_tail = str(assistant_shape.get("tail") or assistant_text)
    diagnostic_path = (
        path.relative_to(REPO_ROOT).as_posix()
        if REPO_ROOT in path.parents
        else path.as_posix()
    )
    reason = str(diagnostic.get("skipped_reason") or "capture_diagnostic")
    return {
        "prompt_run_id": _diagnostic_id(path, diagnostic),
        "prompt_slot": _diagnostic_slot(diagnostic),
        "prompt_slug": "",
        "captured_at": str(diagnostic.get("created_at") or ""),
        "source": "capture_diagnostic",
        "conversation_id": diagnostic.get("conversation_id"),
        "user_turn_index": diagnostic.get("user_turn_index"),
        "assistant_turn_index": diagnostic.get("assistant_turn_index"),
        "match": {
            "method": diagnostic.get("match_method") or "diagnostic",
            "confidence": float(diagnostic.get("match_confidence") or 0.0),
            "segmented": False,
        },
        "char_counts": {
            "user_message": user_shape.get("char_count"),
            "assistant_message": assistant_shape.get("char_count"),
            "pre_prompt": 0,
            "matched_prompt": 0,
            "post_prompt": 0,
            "inferred_addendum": 0,
        },
        "hashes": {
            "user_sha256_prefix": str(user_shape.get("sha16") or "")[:12] or None,
            "assistant_sha256_prefix": str(assistant_shape.get("sha16") or "")[:12] or None,
        },
        "refs": {
            "run_note_path": None,
            "raw_event_path": None,
            "diagnostic_path": diagnostic_path,
            "raw_event_resolved": None,
        },
        "receipt": {
            "ledger_receipt_present": False,
            "raw_event_present": False,
            "read_issues": [reason],
        },
        "capture_status": {
            "status": "diagnostic",
            "skipped_reason": reason,
            "tab_title": diagnostic.get("tab_title"),
        },
        "prompt_sent_excerpt": _clean_excerpt(user_head or user_tail, max_chars=max_chars),
        "operator_addendum_excerpt": _clean_excerpt(user_tail, max_chars=max_chars),
        "assistant_opening_excerpt": _first_lines_excerpt(assistant_head, max_lines=8, max_chars=max_chars),
        "assistant_closeout_excerpt": _clean_excerpt(assistant_tail, max_chars=max_chars),
        "prompt_contract_signals": _extract_contract_signals(user_head + "\n" + user_tail, max_signals=10),
        "assistant_contract_signals": _extract_contract_signals(assistant_text or assistant_tail, max_signals=10),
    }


def review_payload(entries: list[RunIndexEntry], *,
                   raw_events_root: Path | None = None,
                   diagnostics_root: Path | None = None,
                   include_diagnostics: bool = True,
                   slot: str | None = None,
                   run_ids: list[str] | None = None,
                   contains: str | None = None,
                   limit: int = DEFAULT_REVIEW_LIMIT,
                   max_snippet_chars: int = DEFAULT_REVIEW_SNIPPET_CHARS) -> dict[str, Any]:
    bounded_limit = _bounded_int(limit, default=DEFAULT_REVIEW_LIMIT, low=1, high=MAX_REVIEW_LIMIT)
    bounded_snippet = _bounded_int(
        max_snippet_chars,
        default=DEFAULT_REVIEW_SNIPPET_CHARS,
        low=120,
        high=MAX_REVIEW_SNIPPET_CHARS,
    )
    selected = select_review_entries(
        entries,
        run_ids=run_ids,
        contains=contains,
        limit=bounded_limit,
        raw_events_root=raw_events_root,
    )
    wanted_ids = [
        item.strip()
        for item in (run_ids or [])
        for item in item.split(",")
        if item.strip()
    ]
    run_rows = [
        _review_row(
            entry,
            raw_events_root=raw_events_root,
            max_snippet_chars=bounded_snippet,
        )
        for entry in selected
    ]
    diagnostic_rows = (
        select_diagnostic_review_rows(
            diagnostics_root=diagnostics_root,
            slot=slot,
            run_ids=run_ids,
            contains=contains,
            limit=bounded_limit,
            max_snippet_chars=bounded_snippet,
        )
        if include_diagnostics else []
    )
    combined = sorted(
        run_rows + diagnostic_rows,
        key=lambda row: (_parse_captured_at(str(row.get("captured_at") or "")),
                         str(row.get("prompt_run_id") or "")),
        reverse=True,
    )
    if not wanted_ids:
        combined = combined[:bounded_limit]
    return {
        "__meta": {
            "schema_version": SCHEMA_VERSION,
            "artifact_kind": "prompt_shelf_run_review",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "selection_order": "recent_first_unless_run_id_selected",
            "selected_count": len(combined),
            "input_count": len(entries),
            "limit": bounded_limit,
            "max_snippet_chars": bounded_snippet,
            "slot_filtered_before_review": sorted({entry.prompt_slot for entry in entries}),
            "run_ids": wanted_ids,
            "contains": contains or None,
            "include_diagnostics": include_diagnostics,
            "diagnostic_selected_count": len(diagnostic_rows),
            "privacy_boundary": (
                "private-root bounded excerpts only; raw prompt/provider bodies stay in "
                "run_note_path/raw_event_path/diagnostic_path refs"
            ),
        },
        "runs": combined,
    }


def render_review(payload: dict[str, Any]) -> str:
    meta = payload["__meta"]
    lines = [
        f"prompt_shelf_run_review — {meta['selected_count']} run(s) selected",
        f"  generated_at: {meta['generated_at']}",
        f"  selection:    {meta['selection_order']} · limit {meta['limit']}",
        f"  boundary:     {meta['privacy_boundary']}",
        "",
    ]
    if not payload["runs"]:
        lines.append("  (no matching prompt-shelf runs)")
        return "\n".join(lines)
    for idx, row in enumerate(payload["runs"], start=1):
        match = row["match"]
        counts = row["char_counts"]
        refs = row["refs"]
        receipt = row["receipt"]
        lines.append(f"{idx}. {row['prompt_run_id']} [{row['prompt_slot']}] {row['captured_at']}")
        lines.append(
            "   meta: "
            f"source={row['source'] or 'unknown'} "
            f"conversation_id={row['conversation_id'] or 'none'} "
            f"turns={row['user_turn_index']}->{row['assistant_turn_index']} "
            f"match={match['method']}/{match['confidence']:.2f} "
            f"segmented={match['segmented']}"
        )
        lines.append(
            "   chars: "
            f"user={counts['user_message']} assistant={counts['assistant_message']} "
            f"prompt={counts['matched_prompt']} addendum={counts['inferred_addendum']} "
            f"post={counts['post_prompt']}"
        )
        lines.append(
            "   refs: "
            f"run_note={refs.get('run_note_path') or 'none'} "
            f"raw_event={refs.get('raw_event_path') or 'none'} "
            f"diagnostic={refs.get('diagnostic_path') or 'none'} "
            f"receipt={receipt['ledger_receipt_present']} raw_ok={receipt['raw_event_present']}"
        )
        if receipt["read_issues"]:
            lines.append(f"   read_issues: {receipt['read_issues']}")
        if row.get("capture_status"):
            status = row["capture_status"]
            lines.append(
                "   capture_status: "
                f"{status.get('status')} reason={status.get('skipped_reason')} "
                f"tab={status.get('tab_title') or 'none'}"
            )
        if row["prompt_contract_signals"]:
            lines.append("   prompt signals:")
            for signal in row["prompt_contract_signals"]:
                lines.append(f"     - {signal}")
        if row["assistant_contract_signals"]:
            lines.append("   assistant signals:")
            for signal in row["assistant_contract_signals"]:
                lines.append(f"     - {signal}")
        lines.append("   prompt sent excerpt:")
        lines.append(f"     {row['prompt_sent_excerpt'] or '(empty)'}")
        lines.append("   operator/addendum excerpt:")
        lines.append(f"     {row['operator_addendum_excerpt'] or '(empty)'}")
        lines.append("   assistant closeout excerpt:")
        lines.append(f"     {row['assistant_closeout_excerpt'] or '(empty)'}")
        lines.append("")
    return "\n".join(lines).rstrip()


def operator_intent_pressure(operator_text: str) -> str:
    """Classify whether the latest operator turn asks Type A to act.

    This is deliberately a small regression guard, not a general sentiment
    analyzer. It exists to prevent a Type B advisory stop-frame from becoming
    a substrate stop-command when the operator is explicitly asking for agency.
    """
    text = str(operator_text or "")
    if OPERATOR_STATUS_ONLY_RE.search(text):
        return "STATUS_ONLY"
    if OPERATOR_HIGH_AGENCY_RE.search(text):
        return "HIGH_AGENCY_REQUESTED"
    if OPERATOR_CORRECTION_RE.search(text):
        return "CORRECTION_REQUESTED"
    if OPERATOR_ACTION_RE.search(text):
        return "ACTION_REQUESTED"
    return "STATUS_ONLY"


def classify_stop_frame_override(
    *,
    operator_text: str,
    type_b_text: str,
    deciding_evidence_present: bool | None = None,
) -> dict[str, Any]:
    """Classify the A/B shuttle failure where Type B says to stop too early.

    The classifier is intentionally conservative: override is required only
    when all three signals are present:
      1. Type B emitted a wait/no-op/no-edits stop frame.
      2. The latest operator turn asks for action, correction, or agency.
      3. Deciding evidence is present, either passed explicitly by the caller
         or visible in the texts.
    """
    operator = str(operator_text or "")
    type_b = str(type_b_text or "")
    combined = f"{operator}\n{type_b}"
    stop_frame_detected = bool(STOP_FRAME_RE.search(type_b))
    intent_pressure = operator_intent_pressure(operator)
    action_requested = intent_pressure in {
        "ACTION_REQUESTED",
        "CORRECTION_REQUESTED",
        "HIGH_AGENCY_REQUESTED",
    }
    evidence_present = (
        bool(DECIDING_EVIDENCE_RE.search(combined))
        if deciding_evidence_present is None
        else bool(deciding_evidence_present)
    )
    override_required = stop_frame_detected and action_requested and evidence_present
    if override_required:
        classification = "failed_type_b_stop_frame"
        frame_authority = "FAILED_STOP_FRAME"
        required_response = "EXECUTE_SCOPED_PATCH_OR_RECORD_TYPED_BLOCK"
        override_status = "OVERRIDE_REQUIRED"
        instruction = (
            "Cite failed_type_b_stop_frame, inspect mission trace and "
            "prompt-shelf evidence, then patch the nearest safe owner surface "
            "or record a typed blocked receipt with an exact re-entry condition."
        )
    else:
        classification = "not_applicable"
        frame_authority = "ADVISORY"
        required_response = "STATUS_ONLY_ALLOWED"
        override_status = "NOT_APPLICABLE"
        instruction = (
            "No stop-frame override is required unless operator action intent, "
            "a Type B stop-frame, and deciding evidence are all present."
        )
    return {
        "schema_version": "stop_frame_override_classifier_v0",
        "scenario_id": STOP_FRAME_OVERRIDE_SCENARIO_ID,
        "classification": classification,
        "type_b_frame_authority": frame_authority,
        "operator_intent_pressure": intent_pressure,
        "type_a_required_response": required_response,
        "stop_frame_override_status": override_status,
        "proof_boundary": "prompt_run_regression_guard_not_substrate_authority",
        "signals": {
            "type_b_stop_frame_detected": stop_frame_detected,
            "operator_action_requested": action_requested,
            "deciding_evidence_present": evidence_present,
        },
        "emitted_type_a_instruction": instruction,
    }


def stop_frame_override_regression_payload() -> dict[str, Any]:
    """Executable red-team fixture for the failed Type B stop-frame class."""
    operator_text = (
        "Fix this failure mode. Type B gave a failed instruction that means "
        "you do not make edits, but I am asking for agency: go make edits, "
        "inspect mission trace and prompt shelf, and patch the owner surface."
    )
    type_b_text = (
        "The trace capsule shows the deciding evidence was already supplied "
        "and the WorkItem is closed. No concrete recipient row exists, so "
        "wait, make no edits, and return no-op/status only."
    )
    receipt = classify_stop_frame_override(
        operator_text=operator_text,
        type_b_text=type_b_text,
        deciding_evidence_present=True,
    )
    required_instruction_fragments = [
        "Cite failed_type_b_stop_frame",
        "inspect mission trace",
        "prompt-shelf evidence",
        "patch the nearest safe owner surface",
        "typed blocked receipt",
    ]
    instruction = receipt["emitted_type_a_instruction"]
    contains = {
        fragment: fragment in instruction
        for fragment in required_instruction_fragments
    }
    expected = {
        "classification": "failed_type_b_stop_frame",
        "type_b_frame_authority": "FAILED_STOP_FRAME",
        "stop_frame_override_status": "OVERRIDE_REQUIRED",
        "type_a_required_response": "EXECUTE_SCOPED_PATCH_OR_RECORD_TYPED_BLOCK",
    }
    expected_matched = all(receipt.get(key) == value for key, value in expected.items())
    payload = {
        "__meta": {
            "artifact_kind": "prompt_shelf_stop_frame_override_regression",
            "schema_version": "stop_frame_override_regression_v0",
            "generated_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
            "scenario_id": STOP_FRAME_OVERRIDE_SCENARIO_ID,
            "fixture_status": (
                "pass" if expected_matched and all(contains.values()) else "fail"
            ),
            "authority_boundary": (
                "regression fixture over prompt-run governance; Type A still "
                "verifies live substrate before mutation"
            ),
        },
        "expected": expected,
        "required_instruction_fragments_present": contains,
        "receipt": receipt,
    }
    return payload


@dataclass
class CoverageReport:
    """Per-slot coverage snapshot. Rendered by --coverage; consumed by tests."""
    run_count_by_slot: dict[str, int]
    required_slots: list[str]
    missing_slots: list[str]
    covered_slots: list[str]

    def passed(self) -> bool:
        return not self.missing_slots


def coverage_report(entries: list[RunIndexEntry],
                    required_slots: list[str] | None = None) -> CoverageReport:
    """Per-slot capture coverage.

    ``required_slots=None`` defaults to the four historical primary slots; B2
    family variants can be captured without becoming hard coverage gates.
    """
    counts = {slot: 0 for slot in SLOT_DIR_BY_SLOT}
    for e in entries:
        if e.prompt_slot in counts:
            counts[e.prompt_slot] += 1
        else:
            counts[e.prompt_slot] = counts.get(e.prompt_slot, 0) + 1
    required = required_slots if required_slots is not None else list(DEFAULT_REQUIRED_COVERAGE_SLOTS)
    missing = [s for s in required if counts.get(s, 0) == 0]
    covered = [s for s in required if counts.get(s, 0) > 0]
    return CoverageReport(
        run_count_by_slot=counts,
        required_slots=required,
        missing_slots=missing,
        covered_slots=covered,
    )


def filter_entries_by_slot(entries: list[RunIndexEntry], slot: str | None) -> list[RunIndexEntry]:
    """Return entries for one cockpit slot without reading raw prompt bodies."""
    if not slot:
        return entries
    wanted = slot.strip().upper()
    return [entry for entry in entries if entry.prompt_slot.upper() == wanted]


def _slot_display_order(counts_by_slot: dict[str, Any] | None = None,
                        required_slots: list[str] | None = None) -> list[str]:
    """Display primary slots plus present/required variants in cockpit order."""
    counts_by_slot = counts_by_slot or {}
    required = set(required_slots or [])
    out: list[str] = []
    for slot in SLOT_DIR_BY_SLOT:
        if slot not in out:
            out.append(slot)
        for alias in sorted(SLOT_ALIASES_BY_DIR_SLOT.get(slot, set())):
            if alias in counts_by_slot or alias in required:
                out.append(alias)
    for slot in sorted(set(counts_by_slot) | required):
        if slot not in out:
            out.append(slot)
    return out


def render_coverage(report: CoverageReport) -> str:
    lines = ["prompt_shelf_runs coverage:"]
    for slot in _slot_display_order(report.run_count_by_slot, report.required_slots):
        n = report.run_count_by_slot.get(slot, 0)
        flag = ""
        if slot in report.required_slots:
            flag = " ✓" if n > 0 else " ✗ MISSING"
        lines.append(f"  {slot}: {n:>3} runs{flag}")
    if report.missing_slots:
        lines.append("")
        lines.append(f"  required-but-empty: {report.missing_slots}")
    else:
        lines.append("")
        lines.append("  all required slots covered")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--print", dest="print_mode", action="store_true",
                      help="emit JSON to stdout")
    mode.add_argument("--write", action="store_true",
                      help="write canonical projection")
    mode.add_argument("--check", action="store_true",
                      help="exit nonzero on integrity violation")
    mode.add_argument("--summary", action="store_true",
                      help="human-readable summary")
    mode.add_argument("--coverage", action="store_true",
                      help="report slot coverage; nonzero if any required "
                           "slot has zero runs")
    mode.add_argument("--review", action="store_true",
                      help="bounded private excerpt review of selected runs: "
                           "prompt sent, operator addendum, assistant closeout, "
                           "and metadata")
    mode.add_argument("--review-json", action="store_true",
                      help="emit bounded private excerpt review as JSON")
    mode.add_argument("--nesting-audit", action="store_true",
                      help="per-capture audit of multi-anchor presence; "
                           "flags runs where more than one cockpit prompt "
                           "anchor appeared in the user message")
    mode.add_argument("--b3-lint-audit", action="store_true",
                      help="audit captured B3 PACKET v=3.2 outputs with "
                           "b3_packet_lint.py; exits nonzero when any "
                           "captured packet has lint issues")
    mode.add_argument("--stop-frame-regression", action="store_true",
                      help="run the Type B no-op/wait stop-frame override "
                           "red-team regression fixture")
    parser.add_argument("--require-slots",
                        default="A0,B1,B2,B3",
                        help="comma-separated cockpit slots that must have "
                             "≥1 run for --coverage to pass "
                             "(default: A0,B1,B2,B3)")
    parser.add_argument("--slot",
                        help="limit --print/--summary/--coverage to one cockpit slot, e.g. B2")
    parser.add_argument("--limit", type=int, default=DEFAULT_REVIEW_LIMIT,
                        help=f"maximum rows for --review/--review-json "
                             f"(default: {DEFAULT_REVIEW_LIMIT}; cap: {MAX_REVIEW_LIMIT})")
    parser.add_argument("--run-id", action="append", default=[],
                        help="review one selected prompt_run_id; may be repeated "
                             "or comma-separated; overrides recency selection")
    parser.add_argument("--contains",
                        help="explicit private-root search over selected raw "
                             "prompt/provider bodies before bounded review output")
    parser.add_argument("--no-diagnostics", action="store_true",
                        help="exclude recent capture diagnostics from --review output")
    parser.add_argument("--max-snippet-chars", type=int,
                        default=DEFAULT_REVIEW_SNIPPET_CHARS,
                        help=f"maximum chars per review excerpt "
                             f"(default: {DEFAULT_REVIEW_SNIPPET_CHARS}; "
                             f"cap: {MAX_REVIEW_SNIPPET_CHARS})")
    args = parser.parse_args()

    if args.stop_frame_regression:
        payload = stop_frame_override_regression_payload()
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 0 if payload["__meta"]["fixture_status"] == "pass" else 1

    fast_metadata_mode = bool(args.summary or args.coverage or args.check or args.review or args.review_json)
    entries = build_index(include_raw_details=not fast_metadata_mode)
    entries = filter_entries_by_slot(entries, args.slot)
    payload = projection_payload(entries)

    if args.write:
        write_projection(payload)
        print(f"wrote {PROJECTION_PATH.relative_to(REPO_ROOT)} "
              f"({payload['__meta']['run_count']} runs)")
        return 0

    if args.check:
        meta = payload["__meta"]
        problems: list[str] = []
        if meta["duplicate_prompt_run_ids"]:
            problems.append(f"duplicate prompt_run_ids: "
                            f"{meta['duplicate_prompt_run_ids']}")
        if meta["issues_total"] > 0:
            for e in entries:
                if e.issues:
                    problems.append(f"{e.prompt_run_id}: {e.issues}")
        if problems:
            for p in problems:
                print(p, file=sys.stderr)
            return 1
        print(f"clean — {meta['run_count']} runs, "
              f"receipts {meta['receipt_present_count']}/{meta['run_count']}")
        return 0

    if args.summary:
        summary_slots = [args.slot.strip().upper()] if args.slot else None
        print(render_summary(payload, slots=summary_slots,
                             diagnostics_root=CAPTURE_DIAGNOSTICS_ROOT))
        return 0

    if args.coverage:
        required = (
            [args.slot.strip().upper()]
            if args.slot
            else [s.strip() for s in args.require_slots.split(",") if s.strip()]
        )
        report = coverage_report(entries, required_slots=required)
        print(render_coverage(report))
        return 0 if report.passed() else 1

    if args.review or args.review_json:
        review = review_payload(
            entries,
            raw_events_root=RAW_EVENTS_ROOT,
            diagnostics_root=CAPTURE_DIAGNOSTICS_ROOT,
            include_diagnostics=not args.no_diagnostics,
            slot=args.slot,
            run_ids=args.run_id,
            contains=args.contains,
            limit=args.limit,
            max_snippet_chars=args.max_snippet_chars,
        )
        if args.review_json:
            json.dump(review, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print(render_review(review))
        return 0

    if args.nesting_audit:
        print(render_nesting_audit(entries))
        return 0

    if args.b3_lint_audit:
        print(render_b3_lint_audit(entries))
        return 0 if payload["__meta"]["b3_lint_issue_run_count"] == 0 else 1

    # Default → --print
    json.dump(payload, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
