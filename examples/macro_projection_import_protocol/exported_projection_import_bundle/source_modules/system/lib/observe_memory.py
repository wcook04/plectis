"""
[PURPOSE]
- Teleology: Provide shared observe-cycle memory helpers for digests, pending decisions, and friction logging.
- Mechanism: Filesystem-only extraction over observe history entries, session manifests, markdown artifacts, and simple JSONL logs.
- Non-goal: Bridge dispatch, UI transport, or repository mutation outside digest/friction artifact writes.
- When-needed: Open when observe history, session continuity, or friction summaries need the canonical digest-building and pending-item extraction rules instead of reading runner and kernel command call sites separately.
- Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/observe_session.py; tools/meta/apply/run_observe_plan.py
- Navigation-group: kernel_lib

[INTERFACE]
- Exports: extract_pending_items_from_text, compute_cycle_status, observe_digest_path, session_digest_path, load_friction_entries, append_friction_entry, summarize_friction_entries, build_grouped_observe_digest, write_grouped_observe_digest, build_session_manifest_digest, write_session_manifest_digest, load_digest, shlex_quote.
- Reads: Observe history payloads, ObserveSession manifests, markdown or JSON artifacts referenced by those payloads, and state/friction.jsonl.
- Writes: append_friction_entry() appends JSONL to state/friction.jsonl; write_grouped_observe_digest() and write_session_manifest_digest() persist digest JSON files under the observe-history digest surface.
- Schema: Digest builders emit kind=session_digest payloads with source_kind, preferred_entrypoints, recommended_next, pending-decision buckets, and bounded artifact lists.

[FLOW]
- Pending-item extraction parses headings and list-like sections out of observe markdown.
- Cycle-status helpers compress pass counters and assimilation posture into one status object.
- Digest builders resolve bounded artifact sets, load source docs, aggregate pending items, attach friction context, and emit session_digest payloads.
- Digest writers persist those payloads for later kernel resume and review surfaces.

[DEPENDENCIES]
- system.lib.codex_paths.canonicalize_write_path: Normalizes repo-relative artifact paths before digest reads or writes.
- json, re, pathlib.Path, datetime: Support safe artifact parsing, digest path derivation, and timestamping.
- collections.Counter: Summarizes friction categories and repeated descriptions.

[CONSTRAINTS]
- Couples: Digest path and entrypoint shapes stay aligned with system/lib/kernel/commands/observe.py and tools/meta/apply/observe_session.py.
- Orders: Source-doc loading dedupes and bounds artifact reads before aggregation so digests stay deterministic and cheap to reopen.
- Fails: Safe readers return empty text or None on unreadable artifacts; explicit write helpers propagate filesystem failures.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

from system.lib.codex_paths import canonicalize_write_path

OBSERVE_HISTORY_DIGESTS_DIR = "tools/meta/apply/observe_history/digests"
FRICTION_LOG_PATH = "state/friction.jsonl"

_HEADING_RE = re.compile(r"(?m)^(#{1,6})\s+([^\n#][^\n]*)\s*$")
_LIST_RE = re.compile(r"(?m)^\s*(?:[-*]|\d+\.)\s+(.+?)\s*$")
_TAGGED_LINE_RE = re.compile(r"(?m)^\s*(\[[A-Z_]+\].+?)\s*$")
_NEXT_ACTION_RE = re.compile(r"(?im)^NEXT_ACTION:\s*(.+)$")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _normalize_rel(root: Path, value: Any) -> str | None:
    raw = str(value or "").strip()
    if raw and not Path(raw).is_absolute():
        token = canonicalize_write_path(raw)
    else:
        token = ""
    if token:
        return token
    if not raw:
        return None
    candidate = Path(raw)
    try:
        resolved_root = root.resolve()
        resolved = candidate.resolve() if candidate.is_absolute() else (resolved_root / candidate).resolve()
        return resolved.relative_to(resolved_root).as_posix()
    except Exception:
        return None


def _extract_group_response_body(markdown_text: str) -> str:
    text = str(markdown_text or "")
    marker = "\n## Response"
    if marker not in text:
        return text.strip()
    return text.split(marker, 1)[1].strip()


def _extract_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, text
    raw = text[4:end]
    body = text[end + 5 :]
    card: dict[str, Any] = {}
    lines = raw.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx]
        if not line.strip() or ":" not in line:
            idx += 1
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        value = raw_value.strip()
        if value == "":
            items: list[str] = []
            idx += 1
            while idx < len(lines) and lines[idx].startswith("  - "):
                items.append(lines[idx][4:].strip().strip('"'))
                idx += 1
            card[key] = items
            continue
        card[key] = value.strip('"')
        idx += 1
    return card, body


def _extract_heading_sections(text: str) -> dict[str, str]:
    body = str(text or "")
    _frontmatter, body = _extract_frontmatter(body)
    sections: dict[str, str] = {}
    matches = list(_HEADING_RE.finditer(body))
    for idx, match in enumerate(matches):
        title = re.sub(r"\s+", " ", str(match.group(2) or "").strip()).upper()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(body)
        sections[title] = body[start:end].strip()
    return sections


def _section_items(text: str) -> list[str]:
    source = str(text or "").strip()
    if not source:
        return []
    items = [re.sub(r"\s+", " ", match.group(1)).strip() for match in _LIST_RE.finditer(source)]
    if items:
        return [item for item in items if item]
    tagged = [re.sub(r"\s+", " ", match.group(1)).strip() for match in _TAGGED_LINE_RE.finditer(source)]
    if tagged:
        return [item for item in tagged if item]
    lines = []
    for raw_line in source.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("NEXT_ACTION:"):
            continue
        lines.append(re.sub(r"\s+", " ", line).strip())
    return lines


def _dedupe_strings(values: Sequence[Any]) -> list[str]:
    output: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        output.append(token)
    return output


def extract_pending_items_from_text(text: str) -> dict[str, list[str]]:
    """
    [ACTION]
    - Teleology: Recover the pending decisions, followups, and open-question surface from one observe-style markdown or note body.
    - Mechanism: Parse heading sections, normalize list-like lines under the known decision/question headings, and dedupe the resulting item buckets.
    - Guarantee: Returns a dict with operator_decisions_pending, agent_followups_pending, open_questions, decisions_made, and answered lists.
    - Fails: None.
    - When-needed: Open when a digest or continuation surface needs the exact markdown-to-pending-items extraction contract for one observe artifact.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/run_observe_plan.py
    """
    sections = _extract_heading_sections(text)
    operator = _section_items(sections.get("USER DECISIONS", ""))
    agent = _section_items(sections.get("AGENT FOLLOWUPS", ""))
    open_questions = _dedupe_strings(
        [
            *_section_items(sections.get("OPEN QUESTIONS", "")),
            *_section_items(sections.get("UNKNOWNS", "")),
            *_section_items(sections.get("NEXT-PROBE QUESTIONS", "")),
            *_section_items(sections.get("BEST NEXT QUESTIONS", "")),
        ]
    )
    decisions = _dedupe_strings(
        [
            *_section_items(sections.get("DECISION LIST", "")),
            *_section_items(sections.get("LOCKED FACTS", ""))[:3],
        ]
    )
    answered = _dedupe_strings(
        [
            *_section_items(sections.get("LOCKED FACTS", "")),
            *_section_items(sections.get("HIGH-CONFIDENCE FINDINGS", "")),
            *_section_items(sections.get("CONFIRMED FACTS", "")),
        ]
    )
    return {
        "operator_decisions_pending": operator,
        "agent_followups_pending": agent,
        "open_questions": open_questions,
        "decisions_made": decisions,
        "answered": answered,
    }


def compute_cycle_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Summarize one observe payload's cycle posture and assimilation requirements into a compact status object.
    - Mechanism: Inspect pass counters, cadence posture hints, assimilation gates, and reorientation markers on the payload.
    - Guarantee: Returns a dict describing cycle_id, pass/max counts, assimilation flags, completion state, and recommended_next_posture.
    - Fails: None.
    - When-needed: Open when a digest or continuation flow needs the exact rules that decide whether an observe cycle is complete, assimilating, or due for reorientation.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/observe_session.py
    """
    pass_index = payload.get("pass_index")
    max_passes = payload.get("max_passes")
    assimilation_gate = payload.get("assimilation_gate")
    cadence_map = payload.get("cadence_posture_map", {})
    if not isinstance(cadence_map, Mapping):
        cadence_map = {}

    recommended_posture = None
    if isinstance(pass_index, int):
        next_index = pass_index + 1
        for key in (str(next_index), "4+"):
            posture = str(cadence_map.get(key, "")).strip()
            if posture:
                recommended_posture = posture
                break
        if not recommended_posture:
            if next_index <= 1:
                recommended_posture = "wide_epistemic_read"
            elif next_index == 2:
                recommended_posture = "targeted_probe"
            elif next_index == 3:
                recommended_posture = "meta_synthesis"
            else:
                recommended_posture = "narrow_closure_or_scaffold"

    assimilation_required = bool(
        isinstance(pass_index, int)
        and isinstance(assimilation_gate, int)
        and pass_index >= assimilation_gate
    )
    reorientation_required = bool(
        assimilation_required and not str(payload.get("reorientation_note_path", "")).strip()
    )
    cycle_complete = bool(
        isinstance(pass_index, int)
        and isinstance(max_passes, int)
        and pass_index >= max_passes
    )
    return {
        "cycle_id": str(payload.get("cycle_id", "")).strip() or None,
        "pass_index": pass_index if isinstance(pass_index, int) else None,
        "max_passes": max_passes if isinstance(max_passes, int) else None,
        "assimilation_gate": assimilation_gate if isinstance(assimilation_gate, int) else None,
        "assimilation_required": assimilation_required,
        "reorientation_required": reorientation_required,
        "cycle_complete": cycle_complete,
        "recommended_next_posture": recommended_posture,
        "prior_synthesis_path": str(payload.get("prior_synthesis_path", "")).strip() or None,
        "reorientation_note_path": str(payload.get("reorientation_note_path", "")).strip() or None,
    }


def observe_digest_path(root: Path, observe_id: str) -> Path:
    """
    [ACTION]
    - Teleology: Derive the canonical grouped-observe digest file path for one observe_id.
    - Mechanism: Slug the observe_id into a filesystem-safe token and join it under tools/meta/apply/observe_history/digests.
    - Reads: root and observe_id.
    - Writes: None.
    - Guarantee: Returns a Path under OBSERVE_HISTORY_DIGESTS_DIR whose filename ends with `.json`.
    - Fails: None.
    - When-needed: Open when digest writing or resume logic needs the authoritative grouped-observe digest location before touching disk.
    - Escalates-to: system/lib/observe_memory.py::build_grouped_observe_digest; system/lib/kernel/commands/observe.py
    """
    safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(observe_id or "").strip()) or "observe"
    return root / OBSERVE_HISTORY_DIGESTS_DIR / f"{safe}.json"


def session_digest_path(manifest_path: Path) -> Path:
    """
    [ACTION]
    - Teleology: Derive the canonical digest path that lives beside one ObserveSession manifest.
    - Mechanism: Replace the manifest filename with `_session_digest.json` in the same directory.
    - Reads: manifest_path.
    - Writes: None.
    - Guarantee: Returns a sibling Path named `_session_digest.json`.
    - Fails: None.
    - When-needed: Open when ObserveSession harbor or resume code needs the exact colocated digest path for a manifest.
    - Escalates-to: system/lib/observe_memory.py::build_session_manifest_digest; tools/meta/apply/observe_session.py
    """
    return manifest_path.with_name("_session_digest.json")


def load_friction_entries(root: Path, *, limit: int = 25) -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Load the latest friction log entries so observe digests and review surfaces can summarize recurring operator pain points.
    - Mechanism: Read `state/friction.jsonl` in reverse order, parse mapping-shaped lines, and return up to `limit` entries in original chronological order.
    - Guarantee: Returns a list of dict entries, or an empty list when the log is absent or unreadable.
    - Fails: None.
    - When-needed: Open when an observe digest or UI surface needs the canonical recent-friction read path instead of parsing `state/friction.jsonl` ad hoc.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/observe_session.py
    """
    path = (root / FRICTION_LOG_PATH).resolve()
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for raw_line in reversed(path.read_text(encoding="utf-8").splitlines()):
        if not raw_line.strip():
            continue
        try:
            payload = json.loads(raw_line)
        except Exception:
            continue
        if isinstance(payload, dict):
            entries.append(payload)
        if len(entries) >= max(1, limit):
            break
    return list(reversed(entries))


def append_friction_entry(
    root: Path,
    *,
    description: str,
    category: str | None = None,
    workaround: str | None = None,
    suggested_fix: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Append one operator-friction record to the shared JSONL log without involving broader observe runtime mutation.
    - Mechanism: Build a normalized payload with timestamp, category, description, optional workaround/fix text, then append one JSON line to `state/friction.jsonl`.
    - Guarantee: Returns the exact payload written to disk and creates the parent directory when needed.
    - Fails: Propagates filesystem exceptions from parent creation or append writes.
    - When-needed: Open when a kernel or observe runtime surface needs the canonical write contract for friction logging.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/observe_session.py
    """
    payload = {
        "timestamp": _utc_now_iso(),
        "category": str(category or "general").strip() or "general",
        "description": str(description or "").strip(),
        "workaround": str(workaround or "").strip() or None,
        "suggested_fix": str(suggested_fix or "").strip() or None,
        "status": "open",
    }
    path = (root / FRICTION_LOG_PATH).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")
    return payload


def summarize_friction_entries(entries: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Compress recent friction-log entries into category counts, repeated descriptions, and replayable entry rows for digest surfaces.
    - Mechanism: Count normalized category and description fields with Counter, then emit top descriptions and mapping-shaped entries.
    - Reads: entries.
    - Writes: None.
    - Guarantee: Returns total_entries, categories, top_descriptions, and entries keys for the supplied sequence.
    - Fails: None.
    - When-needed: Open when an observe review or digest surface needs the canonical friction-summary shape instead of recomputing counts ad hoc.
    - Escalates-to: system/lib/observe_memory.py::load_friction_entries; system/lib/kernel/commands/observe.py
    """
    category_counts = Counter(
        str(entry.get("category", "general")).strip() or "general"
        for entry in entries
        if isinstance(entry, Mapping)
    )
    description_counts = Counter(
        str(entry.get("description", "")).strip()
        for entry in entries
        if isinstance(entry, Mapping) and str(entry.get("description", "")).strip()
    )
    return {
        "total_entries": len(entries),
        "categories": dict(category_counts),
        "top_descriptions": [
            {"description": description, "count": count}
            for description, count in description_counts.most_common(10)
        ],
        "entries": [dict(entry) for entry in entries if isinstance(entry, Mapping)],
    }


def _observe_artifact_paths(root: Path, payload: Mapping[str, Any]) -> list[str]:
    result_note = payload.get("result_note")
    result_note_path = str(result_note.get("path", "")).strip() if isinstance(result_note, Mapping) else ""
    bridge_synthesis = payload.get("bridge_synthesis")
    bridge_synthesis_path = str(bridge_synthesis.get("path", "")).strip() if isinstance(bridge_synthesis, Mapping) else ""
    heuristic_synthesis = payload.get("synthesis")
    heuristic_synthesis_path = str(heuristic_synthesis.get("path", "")).strip() if isinstance(heuristic_synthesis, Mapping) else ""
    continuation = payload.get("continuation")
    continuation_read_paths = continuation.get("read_paths", []) if isinstance(continuation, Mapping) else []
    response_paths = []
    dump_paths = []
    for group in payload.get("groups", []) if isinstance(payload.get("groups"), list) else []:
        if not isinstance(group, Mapping):
            continue
        response_rel = _normalize_rel(root, group.get("response_file"))
        dump_rel = _normalize_rel(root, group.get("dump_file"))
        if response_rel:
            response_paths.append(response_rel)
        if dump_rel:
            dump_paths.append(dump_rel)
    ordered = _dedupe_strings(
        [
            result_note_path,
            bridge_synthesis_path,
            heuristic_synthesis_path,
            *[str(item).strip() for item in continuation_read_paths if str(item).strip()],
            *response_paths,
            *dump_paths,
        ]
    )
    return ordered


def _session_artifact_paths(root: Path, manifest: Mapping[str, Any]) -> list[str]:
    continuation = manifest.get("continuation")
    read_paths = continuation.get("read_paths", []) if isinstance(continuation, Mapping) else []
    transaction = manifest.get("transaction_receipts")
    transaction_path = (
        str(transaction.get("apply_loop_result_path", "")).strip()
        if isinstance(transaction, Mapping)
        else ""
    )
    records = manifest.get("records", [])
    relpaths = [
        str(record.get("relpath", "")).strip()
        for record in records
        if isinstance(record, Mapping) and str(record.get("relpath", "")).strip()
    ]
    latest_artifact = ""
    if isinstance(continuation, Mapping):
        token = continuation.get("latest_artifact")
        latest_artifact = str(token).strip() if token is not None else ""
    return _dedupe_strings([transaction_path, latest_artifact, *read_paths, *relpaths])


def _load_digest_sources(root: Path, rel_paths: Sequence[str], *, max_files: int = 8) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for rel_path in _dedupe_strings(rel_paths)[:max_files]:
        normalized = _normalize_rel(root, rel_path)
        if not normalized:
            continue
        path = (root / normalized).resolve()
        if not path.exists() or not path.is_file():
            continue
        text = _safe_read_text(path)
        if normalized.endswith("_response.md"):
            text = _extract_group_response_body(text)
        output.append(
            {
                "path": normalized,
                "kind": "markdown" if normalized.endswith(".md") else "json",
                "text": text,
            }
        )
    return output


def _aggregate_digest_items(source_docs: Sequence[Mapping[str, Any]]) -> dict[str, list[str]]:
    operator: list[str] = []
    agent: list[str] = []
    open_questions: list[str] = []
    decisions: list[str] = []
    answered: list[str] = []
    for source in source_docs:
        text = str(source.get("text", "") or "")
        items = extract_pending_items_from_text(text)
        operator.extend(items["operator_decisions_pending"])
        agent.extend(items["agent_followups_pending"])
        open_questions.extend(items["open_questions"])
        decisions.extend(items["decisions_made"])
        answered.extend(items["answered"])
    return {
        "operator_decisions_pending": _dedupe_strings(operator),
        "agent_followups_pending": _dedupe_strings(agent),
        "open_questions": _dedupe_strings(open_questions),
        "decisions_made": _dedupe_strings(decisions),
        "answered": _dedupe_strings(answered),
    }


def _observe_recommended_next(payload: Mapping[str, Any], aggregated: Mapping[str, Sequence[str]]) -> list[dict[str, str]]:
    observe_id = str(payload.get("observe_id", "")).strip()
    next_steps: list[dict[str, str]] = []
    if observe_id:
        next_steps.append(
            {
                "command": f"python3 kernel.py --read-observe {observe_id}",
                "reason": "Reopen the grouped observe continuation surface before widening search.",
            }
        )
        next_steps.append(
            {
                "command": f"python3 kernel.py --digest-observe {observe_id}",
                "reason": "Refresh the session digest after documentation or planning changes.",
            }
        )
    cycle_status = compute_cycle_status(payload)
    if cycle_status.get("assimilation_required"):
        next_steps.append(
            {
                "command": f"python3 kernel.py --metabolize {shlex_quote('latest')} --from-observe {shlex_quote(observe_id or 'latest')}",
                "reason": "Preview writeback into the owning memory surface before more probing.",
            }
        )
    if aggregated.get("operator_decisions_pending"):
        next_steps.append(
            {
                "command": "python3 kernel.py --bootstrap-task <note-or-token>",
                "reason": "Re-enter the owning note family and resolve pending operator decisions explicitly.",
            }
        )
    if observe_id and not cycle_status.get("cycle_complete"):
        next_steps.append(
            {
                "command": f"python3 kernel.py --draft-observe \"<next-pass-question>\" --continue-from {observe_id} --write-plan tools/meta/apply/observe_plan.json",
                "reason": "Draft the next narrower grouped pass from the current artifacts.",
            }
        )
    return next_steps


def build_grouped_observe_digest(root: Path, payload: Mapping[str, Any], history_entry_path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the digest surface for one grouped-observe run so resume and review commands can reopen the run without rescanning every artifact.
    - Mechanism: Resolve the run's artifact paths, load bounded source docs, aggregate pending items, attach friction context, compute cycle status, and assemble preferred entrypoints.
    - Guarantee: Returns a session_digest payload for one grouped observe run without writing it to disk.
    - Fails: None.
    - When-needed: Open when a grouped observe history entry needs the exact digest shape before writing or exposing it through kernel commands.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/run_observe_plan.py
    """
    observe_id = str(payload.get("observe_id", "")).strip() or history_entry_path.stem
    source_paths = _observe_artifact_paths(root, payload)
    source_docs = _load_digest_sources(root, source_paths)
    aggregated = _aggregate_digest_items(source_docs)
    friction = load_friction_entries(root, limit=10)
    cycle_status = compute_cycle_status(payload)
    digest_path = observe_digest_path(root, observe_id)
    recommended_next = _observe_recommended_next(payload, aggregated)
    return {
        "id": f"digest_{observe_id}",
        "kind": "session_digest",
        "source_kind": "grouped_observe",
        "generated_at": _utc_now_iso(),
        "observe_id": observe_id,
        "history_entry": _normalize_rel(root, history_entry_path) or history_entry_path.as_posix(),
        "digest_path": _normalize_rel(root, digest_path) or digest_path.as_posix(),
        "goal_question": str(payload.get("goal_question", "")).strip() or None,
        "success_criteria": str(payload.get("success_criteria", "")).strip() or None,
        "cycle_status": cycle_status,
        "artifacts": source_paths,
        "answered": list(aggregated.get("answered", []))[:8],
        "what_remains_open": list(aggregated.get("open_questions", []))[:10],
        "decisions_made": list(aggregated.get("decisions_made", []))[:10],
        "operator_decisions_pending": list(aggregated.get("operator_decisions_pending", []))[:10],
        "agent_followups_pending": list(aggregated.get("agent_followups_pending", []))[:10],
        "friction_encountered": friction[-5:],
        "preferred_entrypoints": _dedupe_strings(
            [
                f"python3 kernel.py --read-observe {observe_id}",
                source_paths[0] if source_paths else "",
                f"python3 kernel.py --digest-observe {observe_id}",
            ]
        ),
        "recommended_next": recommended_next,
    }


def write_grouped_observe_digest(root: Path, payload: Mapping[str, Any], history_entry_path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Persist the grouped-observe digest so later kernel and runtime surfaces can reopen the run from one bounded JSON file.
    - Mechanism: Build the grouped observe digest, create the destination directory, and write the JSON payload at the computed digest path.
    - Guarantee: Returns the digest payload after writing it to disk.
    - Fails: Propagates filesystem exceptions from mkdir() or write_text().
    - When-needed: Open when grouped observe execution or promotion logic needs the canonical write path for session digests.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/run_observe_plan.py
    """
    digest = build_grouped_observe_digest(root, payload, history_entry_path)
    digest_path = root / str(digest["digest_path"])
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(json.dumps(digest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return digest


def build_session_manifest_digest(root: Path, manifest: Mapping[str, Any], manifest_path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Build the digest surface for one ObserveSession manifest so harbor, readback, and continuation flows can reopen session state cheaply.
    - Mechanism: Resolve artifact paths from the manifest, aggregate pending items from bounded source docs, and project continuity/readback/transaction state into one digest payload.
    - Guarantee: Returns a session_digest payload for one ObserveSession manifest without writing it to disk.
    - Fails: None.
    - When-needed: Open when an ObserveSession manifest needs the exact digest payload that downstream harbor or kernel commands consume.
    - Escalates-to: system/lib/phase_harbor.py; tools/meta/apply/observe_session.py; system/lib/kernel/commands/observe.py
    """
    observe_id = str(manifest.get("observe_id", "")).strip() or manifest_path.parent.name
    source_paths = _session_artifact_paths(root, manifest)
    source_docs = _load_digest_sources(root, source_paths)
    aggregated = _aggregate_digest_items(source_docs)
    digest_path_value = session_digest_path(manifest_path)
    continuation = manifest.get("continuation") if isinstance(manifest.get("continuation"), Mapping) else {}
    session_continuity = manifest.get("session_continuity") if isinstance(manifest.get("session_continuity"), Mapping) else {}
    readback_state = manifest.get("readback_state") if isinstance(manifest.get("readback_state"), Mapping) else {}
    transaction_receipts = manifest.get("transaction_receipts") if isinstance(manifest.get("transaction_receipts"), Mapping) else {}
    friction = load_friction_entries(root, limit=10)
    return {
        "id": f"digest_{observe_id}",
        "kind": "session_digest",
        "source_kind": "observe_session",
        "generated_at": _utc_now_iso(),
        "observe_id": observe_id,
        "session_slug": str(manifest.get("session_slug", "")).strip() or None,
        "session_manifest": _normalize_rel(root, manifest_path) or manifest_path.as_posix(),
        "digest_path": _normalize_rel(root, digest_path_value) or digest_path_value.as_posix(),
        "goal_question": str(manifest.get("goal_question", "") or manifest.get("problem_text", "")).strip() or None,
        "success_criteria": str(manifest.get("success_criteria", "")).strip() or None,
        "session_continuity": dict(session_continuity) if isinstance(session_continuity, Mapping) else {},
        "readback_state": dict(readback_state) if isinstance(readback_state, Mapping) else {},
        "continuation": dict(continuation) if isinstance(continuation, Mapping) else {},
        "transaction_receipts": dict(transaction_receipts) if isinstance(transaction_receipts, Mapping) else {},
        "artifacts": source_paths,
        "answered": list(aggregated.get("answered", []))[:8],
        "what_remains_open": list(aggregated.get("open_questions", []))[:10],
        "decisions_made": list(aggregated.get("decisions_made", []))[:10],
        "operator_decisions_pending": list(aggregated.get("operator_decisions_pending", []))[:10],
        "agent_followups_pending": list(aggregated.get("agent_followups_pending", []))[:10],
        "friction_encountered": friction[-5:],
        "preferred_entrypoints": _dedupe_strings(
            [
                f"python3 kernel.py --read-session {observe_id}",
                str(transaction_receipts.get("apply_loop_result_path", "")).strip()
                if isinstance(transaction_receipts, Mapping)
                else "",
                str(readback_state.get("primary_artifact", "")).strip() if isinstance(readback_state, Mapping) else "",
                source_paths[0] if source_paths else "",
                f"python3 kernel.py --digest-observe {manifest_path.parent.name}",
            ]
        ),
    }


def write_session_manifest_digest(root: Path, manifest: Mapping[str, Any], manifest_path: Path) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Persist the ObserveSession manifest digest so later resume and harbor surfaces can reopen session state from disk.
    - Mechanism: Build the session-manifest digest, create the destination directory, and write the JSON payload at the computed digest path.
    - Guarantee: Returns the digest payload after writing it to disk.
    - Fails: Propagates filesystem exceptions from mkdir() or write_text().
    - When-needed: Open when an ObserveSession runtime or harbor mutation path needs the canonical write contract for manifest digests.
    - Escalates-to: system/lib/phase_harbor.py; tools/meta/apply/observe_session.py
    """
    digest = build_session_manifest_digest(root, manifest, manifest_path)
    digest_path_value = root / str(digest["digest_path"])
    digest_path_value.parent.mkdir(parents=True, exist_ok=True)
    digest_path_value.write_text(json.dumps(digest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return digest


def load_digest(root: Path, rel_path: str | None) -> dict[str, Any] | None:
    """
    [ACTION]
    - Teleology: Load one previously written observe digest by repo-relative path for resume and kernel readback surfaces.
    - Mechanism: Normalize the supplied path against the repo root and reuse the safe JSON loader.
    - Guarantee: Returns a mapping payload for an existing digest file or None when the path is blank, invalid, or unreadable.
    - Fails: None.
    - When-needed: Open when a command already knows a digest path and needs the canonical safe loader rather than reopening the artifact tree manually.
    - Escalates-to: system/lib/kernel/commands/observe.py; tools/meta/apply/observe_session.py
    """
    normalized = _normalize_rel(root, rel_path)
    if not normalized:
        return None
    return _safe_load_json((root / normalized).resolve())


def shlex_quote(value: str) -> str:
    """
    [ACTION]
    - Teleology: Quote one shell token for human-readable kernel command suggestions embedded in digest payloads.
    - Mechanism: Return the token unchanged when it already matches a safe shell subset; otherwise single-quote it with embedded-quote escaping.
    - Reads: value.
    - Writes: None.
    - Guarantee: Returns a non-empty shell-safe token string, using `''` for blank input.
    - Fails: None.
    - When-needed: Open when digest recommendation builders need the exact quoting rule for suggested shell commands.
    - Escalates-to: system/lib/observe_memory.py::_observe_recommended_next; system/lib/kernel/commands/observe.py
    """
    token = str(value or "").strip()
    if not token:
        return "''"
    if re.fullmatch(r"[A-Za-z0-9_./:-]+", token):
        return token
    return "'" + token.replace("'", "'\"'\"'") + "'"
