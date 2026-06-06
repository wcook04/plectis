"""
Agent Experience Grand Rounds diagnostics compiler.

This module builds a read-only, provider-neutral report over existing agent
observability and execution-trace substrates. It emits diagnostic cases and
repair candidates; it does not promote WorkItems, mutate hooks, or treat
assistant closeout prose as authority.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from system.lib.agent_execution_trace import build_agent_execution_trace
from system.lib.agent_observability import DEFAULT_TRACE_RELATIVE_PATH, AgentTraceStore, _read_jsonl_tail_lines


KIND = "kernel.navigate.agent_experience_diagnostics"
SCHEMA_VERSION = "agent_experience_diagnostics_v0"
CASE_SCHEMA_VERSION = "agent_experience_case_v0"
DEFAULT_SESSION_LIMIT = 50
DEFAULT_EVENT_LIMIT = 5000
DEFAULT_CLOSEOUT_LIMIT = 100
MAX_EVENT_LIMIT = 20000
MAX_CLOSEOUT_LIMIT = 1000
MAX_CASES = 80
MAX_REPAIR_CANDIDATES = 16

UNKNOWN_SESSION_IDS = {"", "unknown", "codex_app", "claude_code", "agent_observability"}

CASE_KIND_BY_PATTERN = {
    "grep_before_kernel": "route_drift",
    "paper_module_skip": "route_drift",
    "cold_boot_missing_info": "route_drift",
    "loop_detected": "loop",
    "stall_detected": "stall",
    "read_bomb": "reread",
    "route_non_compliance": "route_drift",
    "deep_without_ladder": "route_drift",
}

SEVERITY_WEIGHT = {
    "info": 1.0,
    "watch": 2.0,
    "warn": 3.0,
    "warning": 3.0,
    "critical": 4.0,
    "blocker": 5.0,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _bounded(value: Any, *, default: int, minimum: int = 1, maximum: int | None = None) -> int:
    resolved = max(minimum, _safe_int(value, default))
    if maximum is not None:
        resolved = min(resolved, maximum)
    return resolved


def _short_hash(parts: Iterable[Any]) -> str:
    h = hashlib.sha1()
    for part in parts:
        h.update(str(part or "").encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()[:16]


def _case_id(case_kind: str, *parts: Any) -> str:
    return f"aexp_case_{case_kind}_{_short_hash((case_kind, *parts))}"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _compact_text(text: Any, *, limit: int = 220) -> str | None:
    raw = " ".join(str(text or "").strip().split())
    if not raw:
        return None
    if len(raw) <= limit:
        return raw
    return raw[: max(0, limit - 3)].rstrip() + "..."


def _event_ref(event: Mapping[str, Any]) -> str:
    seq = event.get("seq")
    event_id = event.get("id")
    if seq is not None:
        return f"agent_event:{seq}"
    if event_id:
        return f"agent_event:{event_id}"
    return "agent_event:unknown"


def _span_ref(session_id: str | None, index: int) -> str:
    return f"span:{session_id or 'unknown'}:{index}"


def _provider_from_agent(agent: Any) -> str:
    raw = str(agent or "").lower()
    if "codex" in raw:
        return "codex_app"
    if "claude" in raw:
        return "claude_code"
    if raw:
        return raw
    return "unknown"


def normalize_process_pattern_id(pattern_id: str | None) -> str:
    """Collapse process-audit anti-pattern ids into stable diagnostic keys."""
    raw = str(pattern_id or "").strip()
    for prefix in ("anti_pattern_", "pattern_"):
        if raw.startswith(prefix):
            return raw[len(prefix) :]
    return raw


def _session_is_bound(session_id: Any) -> bool:
    return str(session_id or "").strip() not in UNKNOWN_SESSION_IDS


def _payload_get(payload: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload and payload.get(key) not in (None, ""):
            return payload.get(key)
    return None


def _nested_payload_get(payload: Mapping[str, Any], *paths: Sequence[str]) -> Any:
    for path in paths:
        cursor: Any = payload
        ok = True
        for key in path:
            if isinstance(cursor, Mapping) and key in cursor:
                cursor = cursor.get(key)
            else:
                ok = False
                break
        if ok and cursor not in (None, ""):
            return cursor
    return None


def _extract_command_shape(span: Mapping[str, Any]) -> str | None:
    command = span.get("normalized_command") or span.get("command")
    if command:
        return str(command)
    tool = span.get("tool_name") or span.get("action_kind")
    return str(tool) if tool else None


def _file_refs_from_span(span: Mapping[str, Any]) -> list[str]:
    refs: list[str] = []
    for key in ("target_paths", "artifact_refs"):
        value = span.get(key)
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and item and item not in refs:
                    refs.append(item)
    return refs[:20]


def _provider_counts_from_events(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    return dict(Counter(str(event.get("source_runtime") or "unknown") for event in events))


def _session_counts_from_execution(payload: Mapping[str, Any]) -> dict[str, int]:
    summary = _as_mapping(_as_mapping(payload.get("ledger")).get("summary"))
    result = {
        "total": int(summary.get("session_count") or 0),
        "claude_code": int(summary.get("claude_count") or 0),
        "codex_app": int(summary.get("codex_count") or 0),
    }
    if not result["total"]:
        sessions = _as_list(_as_mapping(payload.get("ledger")).get("sessions"))
        counts = Counter(_provider_from_agent(_as_mapping(session).get("agent")) for session in sessions)
        result = {"total": len(sessions), **dict(counts)}
    return result


def _compute_identity_coverage(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total = len(events)
    bound = sum(1 for event in events if _session_is_bound(event.get("session_id")))
    unknown = total - bound
    by_provider: dict[str, dict[str, Any]] = {}
    for provider, rows in _group_events_by_provider(events).items():
        provider_total = len(rows)
        provider_bound = sum(1 for event in rows if _session_is_bound(event.get("session_id")))
        by_provider[provider] = {
            "event_count": provider_total,
            "bound_session_event_count": provider_bound,
            "unknown_session_event_count": provider_total - provider_bound,
            "bind_rate": _ratio(provider_bound, provider_total),
        }
    return {
        "event_count": total,
        "bound_session_event_count": bound,
        "unknown_session_event_count": unknown,
        "bind_rate": _ratio(bound, total),
        "by_provider": by_provider,
    }


def _ratio(numerator: int | float, denominator: int | float) -> float:
    if not denominator:
        return 0.0
    return round(float(numerator) / float(denominator), 4)


def _group_events_by_provider(events: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        grouped[str(event.get("source_runtime") or "unknown")].append(event)
    return dict(grouped)


def _compute_codex_coverage(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    codex_events = [event for event in events if str(event.get("source_runtime") or "") == "codex_app"]
    total = len(codex_events)
    thread_bound = 0
    turn_bound = 0
    item_bound = 0
    tool_bound = 0
    source_contracts: Counter[str] = Counter()
    for event in codex_events:
        payload = _as_mapping(event.get("payload"))
        if _session_is_bound(event.get("session_id")) or _payload_get(payload, "thread_id", "threadId"):
            thread_bound += 1
        if event.get("turn_id") or _payload_get(payload, "turn_id", "turnId"):
            turn_bound += 1
        if _payload_get(payload, "item_id", "itemId", "id"):
            item_bound += 1
        if event.get("tool_use_id") or _payload_get(payload, "tool_use_id", "toolUseId", "call_id", "callId"):
            tool_bound += 1
        source_contracts[str(payload.get("source_contract") or payload.get("type") or "unknown")] += 1
    return {
        "event_count": total,
        "thread_id_bind_rate": _ratio(thread_bound, total),
        "turn_id_bind_rate": _ratio(turn_bound, total),
        "item_id_bind_rate": _ratio(item_bound, total),
        "tool_use_id_bind_rate": _ratio(tool_bound, total),
        "source_contract_counts": dict(source_contracts.most_common(12)),
    }


def _compute_claude_coverage(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    claude_events = [event for event in events if str(event.get("source_runtime") or "") == "claude_code"]
    total = len(claude_events)
    session_bound = 0
    prompt_bound = 0
    sequence_bound = 0
    tool_bound = 0
    subagent_bound = 0
    compaction = 0
    for event in claude_events:
        payload = _as_mapping(event.get("payload"))
        if _session_is_bound(event.get("session_id")) or _payload_get(payload, "session_id", "sessionId"):
            session_bound += 1
        if _payload_get(payload, "prompt.id", "prompt_id", "promptId") or _nested_payload_get(payload, ("prompt", "id")):
            prompt_bound += 1
        if _payload_get(payload, "event.sequence", "event_sequence", "sequence"):
            sequence_bound += 1
        if event.get("tool_use_id") or _payload_get(payload, "tool_use_id", "toolUseId"):
            tool_bound += 1
        if event.get("subagent_id") or _payload_get(payload, "agent_id", "agentId", "agent_type", "agentType"):
            subagent_bound += 1
        if str(event.get("canonical_type") or "").startswith("compaction."):
            compaction += 1
    return {
        "event_count": total,
        "session_id_bind_rate": _ratio(session_bound, total),
        "prompt_id_bind_rate": _ratio(prompt_bound, total),
        "event_sequence_bind_rate": _ratio(sequence_bound, total),
        "tool_use_id_bind_rate": _ratio(tool_bound, total),
        "subagent_marker_rate": _ratio(subagent_bound, total),
        "compaction_event_count": compaction,
    }


def _extract_closeout_text(event: Mapping[str, Any]) -> str | None:
    canonical = str(event.get("canonical_type") or "")
    source_name = str(event.get("source_event_name") or "")
    payload = _as_mapping(event.get("payload"))
    candidates: list[Any] = [
        payload.get("last_agent_message"),
        payload.get("final_message"),
        payload.get("assistant_final_message"),
        payload.get("closeout"),
        payload.get("summary"),
        event.get("summary"),
    ]
    if canonical in {"message.assistant", "turn.completed"} or source_name in {"Stop", "SessionEnd", "task_complete"}:
        candidates.extend([payload.get("message"), payload.get("content"), payload.get("text")])
    text_parts: list[str] = []
    for candidate in candidates:
        text = _text_from_payload_value(candidate)
        if text:
            text_parts.append(text)
    if not text_parts:
        return None
    combined = "\n".join(text_parts)
    markers = (
        "navigation_seed_used:",
        "refinement_result:",
        "plane_home:",
        "::git-commit",
        "validation",
        "tests",
        "residual",
        "not done",
        "next wave",
        "committed",
        "commit ",
    )
    lower = combined.lower()
    if canonical == "turn.completed" or any(marker in lower for marker in markers):
        return combined
    return None


def _text_from_payload_value(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip() or None
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, Mapping):
                parts.append(str(item.get("text") or item.get("content") or item.get("message") or ""))
            else:
                parts.append(str(item or ""))
        text = "\n".join(part for part in parts if part.strip()).strip()
        return text or None
    if isinstance(value, Mapping):
        return _text_from_payload_value(value.get("text") or value.get("content") or value.get("message"))
    return str(value).strip() or None


COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
CAP_RE = re.compile(r"\bcap_[A-Za-z0-9_]+\b")
FOOTER_RE = re.compile(
    r"^(navigation_seed_used|general_artifacts_checked|refinement_result|plane_home|discoverability_refresh):\s*(.+)$",
    re.MULTILINE,
)


def extract_declared_closeout(
    text: str | None,
    *,
    source_ref: str,
    repo_root: Path,
    task_ledger_ids: set[str] | None = None,
) -> dict[str, Any]:
    """Extract closeout testimony without granting authority to prose."""
    raw = str(text or "")
    lower = raw.lower()
    commit_refs = sorted(set(match.group(0) for match in COMMIT_RE.finditer(raw)))
    cap_refs = sorted(set(match.group(0) for match in CAP_RE.finditer(raw)))
    footer_claims = {match.group(1): match.group(2).strip() for match in FOOTER_RE.finditer(raw)}
    validation_claims = _line_claims(raw, ("validation", "validated", "test", "pytest", "smoke", "passed", "failed"))
    residual_claims = _line_claims(raw, ("residual", "follow-up", "follow up", "side finding", "captured"))
    not_done_claims = _line_claims(raw, ("not done", "non-goal", "did not", "next wave", "next slice"))
    self_error_claims = _line_claims(raw, ("self-error", "self_error", "mistake", "error captured", "capture"))
    dirty_scope_claims = _line_claims(raw, ("dirty", "excluded", "untracked", "generated sidecar"))
    next_wave_claims = _line_claims(raw, ("next wave", "next slice", "next move", "follow-up"))
    git_claims = [_verify_commit_ref(repo_root, ref) for ref in commit_refs]
    cap_claims = [_verify_cap_ref(ref, task_ledger_ids) for ref in cap_refs]
    verifiable_claims = [*git_claims, *cap_claims]
    contradicted = [row for row in verifiable_claims if row["status"] == "contradicted"]
    verified = [row for row in verifiable_claims if row["status"] == "verified"]
    unverified = [row for row in verifiable_claims if row["status"] == "unverified"]
    verification_status = "unverified"
    if verifiable_claims:
        if contradicted and not verified:
            verification_status = "contradicted"
        elif verified and not contradicted and not unverified:
            verification_status = "verified"
        elif unverified and not contradicted and not verified:
            verification_status = "unverified"
        else:
            verification_status = "partially_verified"
    elif validation_claims or residual_claims or not_done_claims or footer_claims:
        verification_status = "unverified"
    present = bool(raw.strip()) and (
        bool(commit_refs)
        or bool(validation_claims)
        or bool(residual_claims)
        or bool(not_done_claims)
        or bool(self_error_claims)
        or bool(dirty_scope_claims)
        or bool(next_wave_claims)
        or bool(footer_claims)
        or "::git-commit" in raw
        or "committed" in lower
    )
    return {
        "kind": "declared_closeout",
        "schema_version": "declared_closeout_v0",
        "source_ref": source_ref,
        "present": present,
        "commit_refs": commit_refs,
        "cap_refs": cap_refs,
        "validation_claims": validation_claims,
        "residual_claims": residual_claims,
        "self_error_claims": self_error_claims,
        "not_done_claims": not_done_claims,
        "dirty_scope_claims": dirty_scope_claims,
        "next_wave_claims": next_wave_claims,
        "footer_claims": footer_claims,
        "git_claims": git_claims,
        "cap_claims": cap_claims,
        "claim_authority": "testimony_only",
        "verification_status": verification_status,
    }


def _line_claims(text: str, needles: Sequence[str], *, limit: int = 8) -> list[str]:
    rows: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if any(needle in lower for needle in needles):
            compact = _compact_text(line, limit=180)
            if compact and compact not in rows:
                rows.append(compact)
        if len(rows) >= limit:
            break
    return rows


def _verify_commit_ref(repo_root: Path, ref: str) -> dict[str, Any]:
    if len(ref) < 7:
        return {"ref": ref, "status": "unverified", "reason": "too_short"}
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_root), "cat-file", "-e", f"{ref}^{{commit}}"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"ref": ref, "status": "unverified", "reason": "git_unavailable"}
    if result.returncode == 0:
        return {"ref": ref, "status": "verified"}
    return {"ref": ref, "status": "contradicted"}


def _verify_cap_ref(ref: str, task_ledger_ids: set[str] | None) -> dict[str, Any]:
    if not task_ledger_ids:
        return {"ref": ref, "status": "unverified", "reason": "task_ledger_index_unavailable"}
    if ref in task_ledger_ids:
        return {"ref": ref, "status": "verified"}
    return {"ref": ref, "status": "contradicted"}


def _load_task_ledger_ids(repo_root: Path) -> set[str]:
    path = repo_root / "state/task_ledger/ledger.json"
    if not path.exists():
        return set()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    ids: set[str] = set()
    for key in ("work_items", "tasks", "captures"):
        rows = payload.get(key) if isinstance(payload, Mapping) else None
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, Mapping) and row.get("id"):
                    ids.add(str(row.get("id")))
    return ids


def _closeout_records(
    events: Sequence[Mapping[str, Any]],
    *,
    repo_root: Path,
    closeout_limit: int = DEFAULT_CLOSEOUT_LIMIT,
) -> list[dict[str, Any]]:
    if closeout_limit <= 0:
        return []
    records: list[dict[str, Any]] = []
    task_ledger_ids = _load_task_ledger_ids(repo_root)
    for event in events:
        text = _extract_closeout_text(event)
        if not text:
            continue
        closeout = extract_declared_closeout(
            text,
            source_ref=_event_ref(event),
            repo_root=repo_root,
            task_ledger_ids=task_ledger_ids,
        )
        if closeout.get("present"):
            closeout["provider"] = event.get("source_runtime") or "unknown"
            closeout["session_id"] = event.get("session_id") or "unknown"
            closeout["event_ref"] = _event_ref(event)
            closeout["source_contract"] = "agent_event_payload"
            records.append(closeout)
    records.extend(
        _closeout_corpus_records(
            repo_root,
            limit=max(0, closeout_limit - len(records)),
            task_ledger_ids=task_ledger_ids,
        )
    )
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in records:
        key = str(row.get("source_ref") or row.get("event_ref") or "") + "|" + ",".join(row.get("commit_refs") or [])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
        if len(deduped) >= closeout_limit:
            break
    return deduped


def _closeout_corpus_records(
    repo_root: Path,
    *,
    limit: int,
    task_ledger_ids: set[str] | None,
) -> list[dict[str, Any]]:
    if limit <= 0:
        return []
    records: list[dict[str, Any]] = []
    sources = _closeout_corpus_sources(repo_root)
    per_source_tail = max(20, min(300, limit * 4))
    for source_path in sources:
        if len(records) >= limit:
            break
        for index, record in enumerate(_iter_jsonl_tail_records(source_path, limit=per_source_tail)):
            text = _closeout_text_from_record(record)
            if not text:
                continue
            source_ref = f"{source_path.relative_to(repo_root)}:tail:{index}"
            closeout = extract_declared_closeout(
                text,
                source_ref=source_ref,
                repo_root=repo_root,
                task_ledger_ids=task_ledger_ids,
            )
            if not closeout.get("present"):
                continue
            closeout["provider"] = str(record.get("source_runtime") or record.get("actor_id") or record.get("created_by") or "ledger")
            closeout["session_id"] = str(record.get("session_id") or record.get("agent_run_id") or record.get("thread_id") or "ledger")
            closeout["source_contract"] = _closeout_source_contract(source_path)
            records.append(closeout)
            if len(records) >= limit:
                break
    return records


def _closeout_corpus_sources(repo_root: Path) -> list[Path]:
    candidates: list[Path] = []
    exact = [
        repo_root / "state/task_ledger/events.jsonl",
        repo_root / "codex/ledger/09_53/work_ledger.jsonl",
    ]
    candidates.extend(path for path in exact if path.exists())
    ledger_root = repo_root / "codex/ledger"
    if ledger_root.exists():
        work_ledgers = sorted(
            ledger_root.glob("*/work_ledger.jsonl"),
            key=lambda path: path.stat().st_mtime if path.exists() else 0,
            reverse=True,
        )
        for path in work_ledgers[:8]:
            if path not in candidates:
                candidates.append(path)
    return candidates


def _iter_jsonl_tail_records(path: Path, *, limit: int) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in _read_jsonl_tail_lines(path, limit=limit):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict):
            rows.append(record)
    return rows


def _closeout_text_from_record(record: Mapping[str, Any]) -> str | None:
    payload = record.get("payload") if isinstance(record.get("payload"), Mapping) else {}
    refs = record.get("refs") if isinstance(record.get("refs"), Mapping) else {}
    candidates: list[Any] = [
        record.get("body"),
        record.get("note"),
        record.get("summary"),
        record.get("outcome_summary"),
        payload.get("body"),
        payload.get("note"),
        payload.get("summary"),
        payload.get("outcome_summary"),
        payload.get("closeout"),
        payload.get("message"),
    ]
    if isinstance(payload.get("execution_receipt"), Mapping):
        candidates.append(json.dumps(payload.get("execution_receipt"), sort_keys=True))
    if isinstance(refs, Mapping) and refs:
        candidates.append(json.dumps(refs, sort_keys=True))
    text = "\n".join(part for part in (_text_from_payload_value(candidate) for candidate in candidates) if part)
    if not text:
        return None
    markers = (
        "navigation_seed_used:",
        "refinement_result:",
        "plane_home:",
        "::git-commit",
        "validation",
        "pytest",
        "residual",
        "not done",
        "committed",
        "commit",
        "receipt",
        "closeout",
    )
    lower = text.lower()
    return text if any(marker in lower for marker in markers) else None


def _closeout_source_contract(path: Path) -> str:
    text = str(path)
    if "state/task_ledger/events.jsonl" in text:
        return "task_ledger_events_tail"
    if "work_ledger.jsonl" in text:
        return "work_ledger_tail"
    return "bounded_closeout_corpus"


def _canonical_events(
    repo_root: Path,
    *,
    event_limit: int,
    trace_path: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any], list[dict[str, Any]]]:
    gaps: list[dict[str, Any]] = []
    try:
        store = AgentTraceStore(repo_root, trace_path=trace_path, max_history=event_limit)
        status = store.status()
        events = store.replay(limit=event_limit)
        return events, status, gaps
    except Exception as exc:  # pragma: no cover - defensive route guard
        gaps.append(
            {
                "field": "agent_trace",
                "reason": "source_unavailable",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        )
        return [], {"trace_path": str(trace_path or repo_root / DEFAULT_TRACE_RELATIVE_PATH)}, gaps


def _execution_trace(
    repo_root: Path,
    *,
    last: int,
    since_ts: str | None = None,
    home: Path | None = None,
    execution_trace_payload: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], list[dict[str, Any]]]:
    if execution_trace_payload is not None:
        return execution_trace_payload, []
    try:
        payload = build_agent_execution_trace(
            repo_root=repo_root,
            home=home,
            since_ts=since_ts,
            session_limit=last,
        )
        return payload, []
    except Exception as exc:  # pragma: no cover - defensive route guard
        return {}, [
            {
                "field": "execution_trace",
                "reason": "source_unavailable",
                "detail": f"{type(exc).__name__}: {exc}",
            }
        ]


def _build_identity_gap_cases(events: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        provider = str(event.get("source_runtime") or "unknown")
        session_id = str(event.get("session_id") or "unknown")
        if not _session_is_bound(session_id):
            grouped[(provider, session_id)].append(event)
    for (provider, session_id), rows in grouped.items():
        evidence = [_event_ref(row) for row in rows[-8:]]
        cases.append(
            _case(
                case_kind="identity_gap",
                case_source="agent_trace",
                provider=provider,
                session_id=session_id,
                severity="watch" if provider in {"codex_app", "claude_code"} else "info",
                confidence="high",
                message=(
                    f"{len(rows)} recent {provider} canonical events have weak or aggregate session identity "
                    f"({session_id!r})."
                ),
                evidence_refs=evidence,
                hard_trace_summary={"event_count": len(rows), "source": "AgentEvent"},
                diagnostics={
                    "identity_gaps": [
                        {
                            "provider": provider,
                            "session_id": session_id,
                            "event_count": len(rows),
                        }
                    ]
                },
            )
        )
    return cases


def _case(
    *,
    case_kind: str,
    case_source: str,
    provider: str,
    session_id: str | None,
    severity: str,
    confidence: str,
    message: str,
    evidence_refs: Sequence[str] | None = None,
    event_refs: Sequence[str] | None = None,
    span_refs: Sequence[str] | None = None,
    commit_refs: Sequence[str] | None = None,
    ledger_refs: Sequence[str] | None = None,
    hard_trace_summary: Mapping[str, Any] | None = None,
    declared_closeout: Mapping[str, Any] | None = None,
    outcome_verdict: Mapping[str, Any] | None = None,
    diagnostics: Mapping[str, Any] | None = None,
    repair_candidates: Sequence[Mapping[str, Any]] | None = None,
    future_measurements: Sequence[Mapping[str, Any]] | None = None,
    turn_refs: Sequence[str] | None = None,
) -> dict[str, Any]:
    evidence = list(evidence_refs or [])
    event_refs = list(event_refs or [ref for ref in evidence if ref.startswith("agent_event:")])
    span_refs = list(span_refs or [ref for ref in evidence if ref.startswith("span:")])
    commit_refs = list(commit_refs or [])
    ledger_refs = list(ledger_refs or [])
    turn_refs = list(turn_refs or [])
    return {
        "kind": "agent_experience_case",
        "schema_version": CASE_SCHEMA_VERSION,
        "case_id": _case_id(case_kind, provider, session_id, message, ",".join(evidence[:4])),
        "case_kind": case_kind,
        "case_source": case_source,
        "providers": [provider],
        "session_refs": [session_id] if session_id else [],
        "thread_refs": [session_id] if provider == "codex_app" and session_id and _session_is_bound(session_id) else [],
        "turn_refs": turn_refs,
        "event_refs": event_refs,
        "span_refs": span_refs,
        "commit_refs": commit_refs,
        "task_ledger_refs": [ref for ref in ledger_refs if str(ref).startswith("cap_")],
        "work_ledger_refs": [ref for ref in ledger_refs if not str(ref).startswith("cap_")],
        "severity": severity,
        "confidence": confidence,
        "message": message,
        "hard_trace": {
            "summary": dict(hard_trace_summary or {}),
            "confidence": "high" if evidence else "medium",
            "gaps": [],
        },
        "declared_closeout": dict(
            declared_closeout
            or {
                "present": False,
                "claim_authority": "testimony_only",
                "verification_status": "unverified",
            }
        ),
        "outcome_verdict": dict(
            outcome_verdict
            or {
                "status": "unverified",
                "tests": [],
                "git": [],
                "ledger": [],
                "dirty_tree": [],
            }
        ),
        "diagnostics": dict(
            diagnostics
            or {
                "anti_patterns": [],
                "positive_patterns": [],
                "operator_interventions": [],
                "identity_gaps": [],
                "outcome_gaps": [],
                "schema_drift": [],
            }
        ),
        "repair_candidates": list(repair_candidates or []),
        "future_measurements": list(future_measurements or []),
    }


def _build_process_cases(execution_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    audit = _as_mapping(execution_payload.get("audit"))
    findings = _as_list(audit.get("findings"))
    for finding in findings:
        if not isinstance(finding, Mapping):
            continue
        raw_pattern_id = str(finding.get("pattern_id") or finding.get("kind") or finding.get("finding_id") or "")
        normalized_pattern_id = normalize_process_pattern_id(raw_pattern_id)
        case_kind = CASE_KIND_BY_PATTERN.get(normalized_pattern_id)
        finding_kind = str(finding.get("kind") or "")
        if not case_kind and "route" in finding_kind:
            case_kind = "route_drift"
        if not case_kind:
            continue
        session_id = str(finding.get("session_id") or "unknown")
        provider = _provider_from_agent(finding.get("agent") or finding.get("provider"))
        severity = str(finding.get("severity") or ("warn" if case_kind in {"route_drift", "loop"} else "watch"))
        evidence = []
        span_index = finding.get("span_index")
        if span_index is not None:
            evidence.append(_span_ref(session_id, _safe_int(span_index, 0)))
        message = str(
            finding.get("message")
            or finding.get("summary")
            or f"{raw_pattern_id or finding_kind} observed in {session_id}."
        )
        cases.append(
            _case(
                case_kind=case_kind,
                case_source="execution_trace",
                provider=provider,
                session_id=session_id,
                severity=severity,
                confidence="high",
                message=message,
                evidence_refs=evidence,
                hard_trace_summary={
                    "source": "agent_execution_trace",
                    "finding": {k: finding.get(k) for k in ("kind", "pattern_id", "span_index", "severity") if k in finding},
                    "raw_pattern_id": raw_pattern_id,
                    "normalized_pattern_id": normalized_pattern_id,
                },
                diagnostics={
                    "anti_patterns": [normalized_pattern_id or finding_kind],
                    "raw_pattern_id": raw_pattern_id,
                    "normalized_pattern_id": normalized_pattern_id,
                    "positive_patterns": [],
                    "operator_interventions": [],
                    "identity_gaps": [],
                    "outcome_gaps": [],
                    "schema_drift": [],
                },
            )
        )
    cases.extend(_build_positive_process_cases(execution_payload))
    return cases


def _build_positive_process_cases(execution_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    ledger = _as_mapping(execution_payload.get("ledger"))
    sessions = [row for row in _as_list(ledger.get("sessions")) if isinstance(row, Mapping)]
    spans_by_session = _as_mapping(execution_payload.get("spans_by_session"))
    cases: list[dict[str, Any]] = []
    for session in sessions:
        session_id = str(session.get("session_id") or "unknown")
        provider = _provider_from_agent(session.get("agent"))
        route_compliance = _as_mapping(session.get("route_compliance"))
        score = route_compliance.get("score")
        try:
            route_score = float(score)
        except (TypeError, ValueError):
            route_score = 0.0
        if route_score >= 0.95 and int(session.get("span_count") or 0) >= 2:
            cases.append(
                _case(
                    case_kind="positive_pattern",
                    case_source="execution_trace",
                    provider=provider,
                    session_id=session_id,
                    severity="info",
                    confidence="medium",
                    message=f"{provider} session {session_id} climbed the route ladder before work.",
                    evidence_refs=[_span_ref(session_id, 0)],
                    hard_trace_summary={
                        "source": "agent_execution_trace",
                        "route_compliance_score": route_score,
                        "ladder_rungs_hit": route_compliance.get("ladder_rungs_hit") or [],
                    },
                    diagnostics={
                        "anti_patterns": [],
                        "positive_patterns": ["route_before_edit"],
                        "operator_interventions": [],
                        "identity_gaps": [],
                        "outcome_gaps": [],
                        "schema_drift": [],
                    },
                )
            )
        spans = [row for row in _as_list(spans_by_session.get(session_id)) if isinstance(row, Mapping)]
        if _has_validation_after_edit(spans):
            cases.append(
                _case(
                    case_kind="positive_pattern",
                    case_source="execution_trace",
                    provider=provider,
                    session_id=session_id,
                    severity="info",
                    confidence="medium",
                    message=f"{provider} session {session_id} shows edit/write followed by validation.",
                    evidence_refs=[_span_ref(session_id, 0)],
                    hard_trace_summary={"source": "agent_execution_trace", "pattern": "validation_after_edit"},
                    diagnostics={
                        "anti_patterns": [],
                        "positive_patterns": ["validation_after_edit"],
                        "operator_interventions": [],
                        "identity_gaps": [],
                        "outcome_gaps": [],
                        "schema_drift": [],
                    },
                )
            )
    return cases[:12]


def _has_validation_after_edit(spans: Sequence[Mapping[str, Any]]) -> bool:
    edit_seen = False
    for span in spans:
        action = str(span.get("action_kind") or "").lower()
        tool = str(span.get("tool_name") or "").lower()
        command = str(span.get("command") or span.get("normalized_command") or "").lower()
        if action in {"edit", "write"} or tool in {"edit", "write", "multiedit"}:
            edit_seen = True
        if edit_seen and ("pytest" in command or "repo-pytest" in command or " test" in command or action == "test"):
            return True
    return False


def _build_closeout_cases(closeouts: Sequence[Mapping[str, Any]], execution_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for closeout in closeouts:
        session_id = str(closeout.get("session_id") or "unknown")
        provider = str(closeout.get("provider") or "unknown")
        status = str(closeout.get("verification_status") or "unverified")
        commit_refs = [str(ref) for ref in _as_list(closeout.get("commit_refs"))]
        cap_refs = [str(ref) for ref in _as_list(closeout.get("cap_refs"))]
        git_claims = [row for row in _as_list(closeout.get("git_claims")) if isinstance(row, Mapping)]
        outcome_verdict = _outcome_verdict_for_closeout(closeout, execution_payload)
        outcome_status = str(outcome_verdict.get("status") or "unverified")
        if status != "verified" or outcome_status != "verified":
            gap_status = "contradicted" if "contradicted" in {status, outcome_status} else outcome_status
        else:
            gap_status = "verified"
        if gap_status != "verified" and (
            commit_refs or closeout.get("validation_claims") or closeout.get("residual_claims")
        ):
            cases.append(
                _case(
                    case_kind="closeout_gap",
                    case_source="closeout_testimony",
                    provider=provider,
                    session_id=session_id,
                    severity="watch" if gap_status == "unverified" else "warn",
                    confidence="medium",
                    message=f"Closeout testimony for {session_id} is {gap_status}; claims remain non-authoritative.",
                    evidence_refs=[str(closeout.get("event_ref") or closeout.get("source_ref") or "closeout:unknown")],
                    commit_refs=commit_refs,
                    ledger_refs=cap_refs,
                    declared_closeout=closeout,
                    outcome_verdict=outcome_verdict,
                    hard_trace_summary={
                        "source": "declared_closeout",
                        "verification_status": status,
                        "outcome_verdict_status": outcome_status,
                    },
                    diagnostics={
                        "anti_patterns": [],
                        "positive_patterns": [],
                        "operator_interventions": [],
                        "identity_gaps": [],
                        "outcome_gaps": ["closeout_unverified" if gap_status == "unverified" else "closeout_contradicted"],
                        "schema_drift": [],
                    },
                )
            )
        if closeout.get("dirty_scope_claims"):
            cases.append(
                _case(
                    case_kind="dirty_tree_gap",
                    case_source="closeout_testimony",
                    provider=provider,
                    session_id=session_id,
                    severity="info",
                    confidence="medium",
                    message=f"Closeout for {session_id} declared dirty-scope boundaries.",
                    evidence_refs=[str(closeout.get("event_ref") or closeout.get("source_ref") or "closeout:unknown")],
                    declared_closeout=closeout,
                    outcome_verdict=outcome_verdict,
                    hard_trace_summary={"source": "declared_closeout", "dirty_scope_claims": closeout.get("dirty_scope_claims")},
                    diagnostics={
                        "anti_patterns": [],
                        "positive_patterns": ["dirty_scope_exclusion"],
                        "operator_interventions": [],
                        "identity_gaps": [],
                        "outcome_gaps": [],
                        "schema_drift": [],
                    },
                )
            )
    return cases


def _outcome_verdict_for_closeout(
    closeout: Mapping[str, Any],
    execution_payload: Mapping[str, Any],
) -> dict[str, Any]:
    git_claims = [row for row in _as_list(closeout.get("git_claims")) if isinstance(row, Mapping)]
    cap_claims = [row for row in _as_list(closeout.get("cap_claims")) if isinstance(row, Mapping)]
    test_claims = _validation_claim_verdicts(closeout, execution_payload)
    all_claims = [*git_claims, *cap_claims, *test_claims]
    verified_refs = [str(row.get("ref") or row.get("claim")) for row in all_claims if row.get("status") == "verified"]
    contradicted_refs = [str(row.get("ref") or row.get("claim")) for row in all_claims if row.get("status") == "contradicted"]
    unverified_claims = [str(row.get("ref") or row.get("claim")) for row in all_claims if row.get("status") == "unverified"]
    if contradicted_refs and not verified_refs:
        status = "contradicted"
    elif contradicted_refs or (verified_refs and unverified_claims):
        status = "partially_verified"
    elif verified_refs and not unverified_claims:
        status = "verified"
    else:
        status = "unverified"
    return {
        "status": status,
        "verified_refs": verified_refs,
        "contradicted_refs": contradicted_refs,
        "unverified_claims": unverified_claims,
        "tests": test_claims,
        "git": git_claims,
        "ledger": cap_claims,
        "dirty_tree": [{"claim": claim, "status": "testimony_only"} for claim in _as_list(closeout.get("dirty_scope_claims"))],
    }


def _validation_claim_verdicts(closeout: Mapping[str, Any], execution_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    claims = [str(claim) for claim in _as_list(closeout.get("validation_claims")) if str(claim).strip()]
    if not claims:
        return []
    command_text = "\n".join(_validation_command_strings(execution_payload)).lower()
    verdicts: list[dict[str, Any]] = []
    for claim in claims:
        lower = claim.lower()
        status = "unverified"
        if command_text and any(token in lower and token in command_text for token in ("repo-pytest", "pytest", " test ")):
            status = "verified"
        verdicts.append({"claim": claim, "status": status, "authority": "span_match" if status == "verified" else "testimony_only"})
    return verdicts


def _validation_command_strings(execution_payload: Mapping[str, Any]) -> list[str]:
    spans_by_session = _as_mapping(execution_payload.get("spans_by_session"))
    commands: list[str] = []
    for spans in spans_by_session.values():
        for span in _as_list(spans):
            if not isinstance(span, Mapping):
                continue
            command = str(span.get("command") or span.get("normalized_command") or "")
            lower = command.lower()
            if "pytest" in lower or "repo-pytest" in lower or " test" in lower:
                commands.append(command)
    return commands


def _case_metrics(cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    counts = Counter(str(case.get("case_kind") or "unknown") for case in cases)
    source_counts = Counter(str(case.get("case_source") or "unknown") for case in cases)
    severity_counts = Counter(str(case.get("severity") or "unknown") for case in cases)
    return {
        "case_count": len(cases),
        "case_kind_counts": dict(counts),
        "case_source_counts": dict(source_counts),
        "severity_counts": dict(severity_counts),
    }


def _heatmaps(execution_payload: Mapping[str, Any]) -> dict[str, list[dict[str, Any]]]:
    spans_by_session = _as_mapping(execution_payload.get("spans_by_session"))
    command_counts: Counter[str] = Counter()
    tool_counts: Counter[str] = Counter()
    file_counts: Counter[str] = Counter()
    validation_counts: Counter[str] = Counter()
    for spans in spans_by_session.values():
        for span in _as_list(spans):
            if not isinstance(span, Mapping):
                continue
            command = _extract_command_shape(span)
            if command:
                command_counts[command[:160]] += 1
            tool = span.get("tool_name") or span.get("action_kind")
            if tool:
                tool_counts[str(tool)] += 1
            for ref in _file_refs_from_span(span):
                file_counts[ref] += 1
            command_l = str(span.get("command") or span.get("normalized_command") or "").lower()
            if "pytest" in command_l or "repo-pytest" in command_l or " test" in command_l:
                validation_counts[str(span.get("normalized_command") or span.get("command") or "test")] += 1
    return {
        "commands": _counter_rows(command_counts, limit=12),
        "tools": _counter_rows(tool_counts, limit=12),
        "files": _counter_rows(file_counts, limit=12),
        "validation": _counter_rows(validation_counts, limit=8),
    }


def _counter_rows(counter: Counter[str], *, limit: int) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in counter.most_common(limit)]


def _behavior_metrics(execution_payload: Mapping[str, Any], cases: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary = _as_mapping(_as_mapping(execution_payload.get("summary")).get("summary"))
    pattern_counts = _normalized_pattern_counter(summary.get("pattern_counts") or {})
    if not pattern_counts:
        for case in cases:
            diagnostics = _as_mapping(case.get("diagnostics"))
            for pattern in _as_list(diagnostics.get("anti_patterns")):
                pattern_counts[normalize_process_pattern_id(str(pattern))] += 1
    heatmaps = _heatmaps(execution_payload)
    return {
        "route_compliance": {
            "average": summary.get("average_route_compliance"),
            "route_drift_case_count": sum(1 for case in cases if case.get("case_kind") == "route_drift"),
        },
        "grep_before_kernel_count": int(pattern_counts.get("grep_before_kernel", 0)),
        "paper_module_skip_count": int(pattern_counts.get("paper_module_skip", 0)),
        "cold_boot_missing_info_count": int(pattern_counts.get("cold_boot_missing_info", 0)),
        "loop_count": int(pattern_counts.get("loop_detected", 0)),
        "reread_count": int(pattern_counts.get("read_bomb", 0)),
        "stall_count": int(pattern_counts.get("stall_detected", 0)),
        "tool_failure_count": int(summary.get("error_count") or 0),
        "heatmaps": heatmaps,
    }


def _normalized_pattern_counter(raw_counts: Mapping[str, Any]) -> Counter[str]:
    counter: Counter[str] = Counter()
    if not isinstance(raw_counts, Mapping):
        return counter
    for raw_key, raw_count in raw_counts.items():
        counter[normalize_process_pattern_id(str(raw_key))] += _safe_int(raw_count, 0)
    return counter


def _closeout_quality(closeouts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "closeout_count": len(closeouts),
        "commit_declared_count": sum(1 for row in closeouts if row.get("commit_refs")),
        "commit_claim_contradicted_count": sum(
            1
            for row in closeouts
            for claim in _as_list(row.get("git_claims"))
            if isinstance(claim, Mapping) and claim.get("status") == "contradicted"
        ),
        "cap_claim_verified_count": sum(
            1
            for row in closeouts
            for claim in _as_list(row.get("cap_claims"))
            if isinstance(claim, Mapping) and claim.get("status") == "verified"
        ),
        "cap_claim_contradicted_count": sum(
            1
            for row in closeouts
            for claim in _as_list(row.get("cap_claims"))
            if isinstance(claim, Mapping) and claim.get("status") == "contradicted"
        ),
        "validation_claim_unverified_count": sum(
            1
            for row in closeouts
            if row.get("validation_claims") and row.get("verification_status") != "verified"
        ),
        "residual_without_capture_ref_count": sum(
            1 for row in closeouts if row.get("residual_claims") and not row.get("cap_refs")
        ),
        "self_error_captured_count": sum(1 for row in closeouts if row.get("self_error_claims") and row.get("cap_refs")),
        "dirty_scope_exclusion_count": sum(1 for row in closeouts if row.get("dirty_scope_claims")),
        "not_done_honesty_count": sum(1 for row in closeouts if row.get("not_done_claims")),
    }


def _provider_adapter_gaps(coverage: Mapping[str, Any]) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    codex = _as_mapping(coverage.get("codex_thread_turn_item_coverage"))
    if codex.get("event_count") and float(codex.get("turn_id_bind_rate") or 0.0) < 0.5:
        gaps.append(
            {
                "provider": "codex_app",
                "gap": "codex_turn_id_coverage_low",
                "message": "Codex events are present but turn_id coverage is weak; prefer hooks/app-server/exec-json ids before shadow lab work.",
                "first_safe_slice": "add provider_identity envelope preserving thread_id/turn_id/item_id/tool_use_id.",
            }
        )
    if codex.get("event_count") and float(codex.get("item_id_bind_rate") or 0.0) < 0.5:
        gaps.append(
            {
                "provider": "codex_app",
                "gap": "codex_item_id_coverage_low",
                "message": "Codex item identity is not yet reliably represented in canonical AgentEvent rows.",
                "first_safe_slice": "map item.id and item.type from app-server/exec-json/rollout adapters into provider_identity.",
            }
        )
    claude = _as_mapping(coverage.get("claude_prompt_sequence_coverage"))
    if claude.get("event_count") and float(claude.get("prompt_id_bind_rate") or 0.0) == 0.0:
        gaps.append(
            {
                "provider": "claude_code",
                "gap": "claude_prompt_id_unavailable",
                "message": "Claude session/tool events are available, but prompt.id coverage is absent; treat prompt-level turn identity as unavailable.",
                "first_safe_slice": "capture prompt.id/event.sequence only if Claude telemetry is enabled locally.",
            }
        )
    return gaps


def _build_provider_gap_cases(provider_gaps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    for gap in provider_gaps:
        provider = str(gap.get("provider") or "unknown")
        gap_id = str(gap.get("gap") or "provider_gap")
        cases.append(
            _case(
                case_kind="provider_schema_gap",
                case_source="provider_adapter_gap",
                provider=provider,
                session_id=None,
                severity="watch",
                confidence="high",
                message=str(gap.get("message") or gap_id),
                hard_trace_summary={
                    "source": "coverage",
                    "gap": gap_id,
                    "first_safe_slice": gap.get("first_safe_slice"),
                },
                diagnostics={
                    "anti_patterns": [],
                    "positive_patterns": [],
                    "operator_interventions": [],
                    "identity_gaps": [],
                    "outcome_gaps": [],
                    "schema_drift": [gap_id],
                },
            )
        )
    return cases


def _repair_candidates(cases: Sequence[Mapping[str, Any]], provider_gaps: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for case in cases:
        grouped[str(case.get("case_kind") or "unknown")].append(case)
    if "provider_schema_gap" not in grouped:
        for gap in provider_gaps:
            grouped[f"provider_adapter_gap:{gap.get('gap')}"].append(
                {
                    "case_kind": "provider_schema_gap",
                    "severity": "watch",
                    "confidence": "high",
                    "message": gap.get("message"),
                    "providers": [gap.get("provider")],
                }
            )
    candidates: list[dict[str, Any]] = []
    for key, rows in grouped.items():
        if not rows:
            continue
        case_kind = str(rows[0].get("case_kind") or key)
        recurrence = len(rows)
        severity = max((str(row.get("severity") or "info") for row in rows), key=lambda s: SEVERITY_WEIGHT.get(s, 1.0))
        confidence_values = [str(row.get("confidence") or "medium") for row in rows]
        evidence_quality = "hard" if case_kind not in {"closeout_gap", "dirty_tree_gap"} else "mixed"
        owner_candidates, proposed_surface, first_safe_slice = _owner_for_case_kind(case_kind, key)
        ambiguity_penalty = 1.0 if any(str(row.get("confidence") or "") == "low" for row in rows) else 0.0
        rank = round(
            recurrence
            + SEVERITY_WEIGHT.get(severity, 1.0)
            + (3.0 if evidence_quality == "hard" else 2.0)
            + (2.0 if owner_candidates else 0.0)
            + 1.0
            + 1.0
            - ambiguity_penalty,
            3,
        )
        candidates.append(
            {
                "candidate_id": f"aexp_repair_{_short_hash((key, recurrence, severity))}",
                "title": _repair_title(case_kind, key),
                "case_refs": [str(row.get("case_id") or "") for row in rows if row.get("case_id")][:12],
                "pattern": case_kind,
                "recurrence": recurrence,
                "severity": severity,
                "confidence": Counter(confidence_values).most_common(1)[0][0],
                "evidence_quality": evidence_quality,
                "owner_candidates": owner_candidates,
                "proposed_surface": proposed_surface,
                "first_safe_slice": first_safe_slice,
                "rank": rank,
                "future_measurement": _future_measurement(case_kind),
            }
        )
    candidates.sort(key=lambda row: (-float(row.get("rank") or 0.0), str(row.get("title") or "")))
    return candidates[:MAX_REPAIR_CANDIDATES]


def _repair_title(case_kind: str, key: str) -> str:
    if case_kind == "identity_gap":
        return "Preserve provider identity before downstream case science"
    if case_kind == "provider_schema_gap":
        return "Add provider identity envelope for weak adapter fields"
    if case_kind == "route_drift":
        return "Reduce raw-search and paper-module route drift"
    if case_kind == "loop":
        return "Detect and interrupt repeated action loops in diagnostics"
    if case_kind == "reread":
        return "Surface same-file reread clusters as route debt"
    if case_kind == "stall":
        return "Classify long action gaps and stall shapes"
    if case_kind == "closeout_gap":
        return "Separate closeout testimony from verified outcomes"
    if case_kind == "dirty_tree_gap":
        return "Keep dirty-scope boundaries visible in closeout verdicts"
    if case_kind == "positive_pattern":
        return "Promote recurring successful route and validation chains"
    return f"Repair {key}"


def _owner_for_case_kind(case_kind: str, key: str) -> tuple[list[str], str, str]:
    if case_kind in {"identity_gap", "provider_schema_gap"}:
        return (
            ["system/lib/agent_observability.py", "agent_session_attribution", "provider_adapter"],
            "provider_adapter",
            "Add provider_identity envelope fields without changing event authority.",
        )
    if case_kind in {"route_drift", "loop", "reread", "stall"}:
        return (
            ["agent_execution_trace", "navigation_metabolism", "navigation_seed"],
            "route_or_skill",
            "Tune existing trace rules or navigation route discoverability; do not add live nudges.",
        )
    if case_kind in {"closeout_gap", "validation_gap", "dirty_tree_gap"}:
        return (
            ["std_task_ledger", "std_work_ledger", "closeout_audit"],
            "standard_or_ledger",
            "Improve closeout claim capture and verification joins as read-only diagnostics.",
        )
    if case_kind == "positive_pattern":
        return (
            ["navigation_metabolism", "std_skill", "prompt_ledger"],
            "skill_or_standard",
            "Compile recurrence before promoting a success pattern into doctrine.",
        )
    return (["recursive_self_improvement_operating_loop"], "work_item", "Capture as a WorkItem candidate only after recurrence.")


def _future_measurement(case_kind: str) -> dict[str, Any]:
    metrics = {
        "identity_gap": "unknown_session_rate",
        "provider_schema_gap": "provider_identity_field_bind_rate",
        "route_drift": "route_drift_cases_per_session",
        "loop": "loop_detected_cases_per_session",
        "reread": "reread_cluster_cases_per_session",
        "stall": "stall_cases_per_session",
        "closeout_gap": "closeout_verification_rate",
        "dirty_tree_gap": "dirty_scope_claims_with_verdict_rate",
        "positive_pattern": "positive_pattern_recurrence_rate",
    }
    return {
        "metric": metrics.get(case_kind, f"{case_kind}_rate"),
        "baseline_window": "current --agent-experience-diagnostics window",
        "future_window": "next comparable diagnostics window after owner-lane repair",
        "success_condition": "metric improves without increasing high-severity regressions",
        "regression_condition": "metric worsens or ambiguity increases after repair",
    }


def _positive_patterns(cases: Sequence[Mapping[str, Any]], closeouts: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    evidence: dict[str, list[str]] = defaultdict(list)
    for case in cases:
        diagnostics = _as_mapping(case.get("diagnostics"))
        for pattern in _as_list(diagnostics.get("positive_patterns")):
            key = str(pattern)
            counts[key] += 1
            if case.get("case_id"):
                evidence[key].append(str(case.get("case_id")))
    for closeout in closeouts:
        if closeout.get("self_error_claims") and closeout.get("cap_refs"):
            counts["self_error_captured"] += 1
            evidence["self_error_captured"].append(str(closeout.get("event_ref") or closeout.get("source_ref")))
        if closeout.get("dirty_scope_claims"):
            counts["dirty_scope_exclusion"] += 1
            evidence["dirty_scope_exclusion"].append(str(closeout.get("event_ref") or closeout.get("source_ref")))
        if closeout.get("validation_claims") and closeout.get("commit_refs"):
            counts["scoped_commit_with_validation_claim"] += 1
            evidence["scoped_commit_with_validation_claim"].append(str(closeout.get("event_ref") or closeout.get("source_ref")))
    return [
        {
            "pattern": pattern,
            "count": count,
            "evidence_refs": evidence.get(pattern, [])[:8],
            "authority": "diagnostic_pattern_not_promotion",
        }
        for pattern, count in counts.most_common(12)
    ]


def _source_inputs(
    *,
    trace_status: Mapping[str, Any],
    execution_payload: Mapping[str, Any],
    closeout_limit: int,
    closeout_count: int,
    capture_gaps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "agent_trace": {
            "trace_path": trace_status.get("trace_path"),
            "read_mode": "bounded_tail",
            "history_size": trace_status.get("history_size"),
            "max_history": trace_status.get("max_history"),
            "gap_count": trace_status.get("gap_count"),
        },
        "execution_trace": {
            "available": bool(execution_payload),
            "session_count": _as_mapping(_as_mapping(execution_payload.get("ledger")).get("summary")).get("session_count"),
            "parse_failure_count": _as_mapping(_as_mapping(execution_payload.get("summary")).get("summary")).get("parse_failure_count"),
        },
        "session_attribution": {
            "mode": "not_invoked_v0",
            "reason": "v0 lifts identity confidence from canonical events and process sessions only.",
        },
        "session_analyzer": {"mode": "not_invoked_v0"},
        "operational_record_miner": {"mode": "not_invoked_v0"},
        "task_ledger": {"mode": "cheap_ref_only_v0"},
        "work_ledger": {"mode": "cheap_ref_only_v0"},
        "git": {"mode": "commit_ref_cat_file_only"},
        "closeout_sources": {
            "mode": "agent_event_payload_plus_bounded_corpus",
            "closeout_limit": closeout_limit,
            "closeout_count": closeout_count,
        },
        "capture_gaps": list(capture_gaps),
    }


def _coverage(
    events: Sequence[Mapping[str, Any]],
    execution_payload: Mapping[str, Any],
    closeouts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    canonical_event_count = len(events)
    execution_summary = _as_mapping(_as_mapping(execution_payload.get("summary")).get("summary"))
    provider_counts = _provider_counts_from_events(events)
    execution_session_counts = _session_counts_from_execution(execution_payload)
    commit_claims = [
        claim
        for closeout in closeouts
        for claim in _as_list(closeout.get("git_claims"))
        if isinstance(claim, Mapping)
    ]
    cap_claims = [
        claim
        for closeout in closeouts
        for claim in _as_list(closeout.get("cap_claims"))
        if isinstance(claim, Mapping)
    ]
    verified = sum(1 for claim in commit_claims if claim.get("status") == "verified")
    contradicted = sum(1 for claim in commit_claims if claim.get("status") == "contradicted")
    cap_verified = sum(1 for claim in cap_claims if claim.get("status") == "verified")
    cap_contradicted = sum(1 for claim in cap_claims if claim.get("status") == "contradicted")
    return {
        "canonical_event_count": canonical_event_count,
        "provider_counts": provider_counts,
        "execution_trace_session_counts": execution_session_counts,
        "identity_coverage": _compute_identity_coverage(events),
        "codex_thread_turn_item_coverage": _compute_codex_coverage(events),
        "claude_prompt_sequence_coverage": _compute_claude_coverage(events),
        "closeout_coverage": {
            "closeout_count": len(closeouts),
            "session_count_with_closeout": len({row.get("session_id") for row in closeouts if row.get("session_id")}),
            "presence_rate_vs_execution_sessions": _ratio(len({row.get("session_id") for row in closeouts if row.get("session_id")}), int(execution_session_counts.get("total") or 0)),
            "source_contract_counts": dict(Counter(str(row.get("source_contract") or "unknown") for row in closeouts)),
        },
        "outcome_join_coverage": {
            "commit_claim_count": len(commit_claims),
            "commit_claim_verified_count": verified,
            "commit_claim_contradicted_count": contradicted,
            "commit_claim_verified_rate": _ratio(verified, len(commit_claims)),
            "cap_claim_count": len(cap_claims),
            "cap_claim_verified_count": cap_verified,
            "cap_claim_contradicted_count": cap_contradicted,
            "cap_claim_verified_rate": _ratio(cap_verified, len(cap_claims)),
        },
        "schema_drift": [],
        "parse_failure_count": int(execution_summary.get("parse_failure_count") or 0),
    }


def _metrics(
    events: Sequence[Mapping[str, Any]],
    execution_payload: Mapping[str, Any],
    cases: Sequence[Mapping[str, Any]],
    closeouts: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    behavior = _behavior_metrics(execution_payload, cases)
    return {
        "coverage": {
            "canonical_event_count": len(events),
            "case_count": len(cases),
        },
        "behavior": behavior,
        "closeout_quality": _closeout_quality(closeouts),
        "cases": _case_metrics(cases),
    }


def _next_slices(provider_gaps: Sequence[Mapping[str, Any]], cases: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    slices: list[dict[str, Any]] = []
    if provider_gaps:
        slices.append(
            {
                "title": "Provider identity envelope",
                "reason": "Diagnostics found adapter coverage gaps that weaken cross-session case compilation.",
                "first_safe_slice": "Add provider_identity dict to AgentEvent without changing existing top-level contract.",
            }
        )
    if any(case.get("case_kind") == "closeout_gap" for case in cases):
        slices.append(
            {
                "title": "Closeout verifier extraction",
                "reason": "Closeout testimony is now detected but not deeply verified.",
                "first_safe_slice": "Split closeout extraction/verdict helpers into a dedicated module after v0 report proves value.",
            }
        )
    if any(case.get("case_kind") in {"route_drift", "loop", "stall", "reread"} for case in cases):
        slices.append(
            {
                "title": "Decision-point exposure lab",
                "reason": "Recurring process cases are present; decision-point logging can be built after provider identity is strong enough.",
                "first_safe_slice": "Build agent_experience_decision_point_v0 over existing spans before adding shadow policies.",
            }
        )
    if not slices:
        slices.append(
            {
                "title": "Grand rounds calibration",
                "reason": "No high-signal cases found in this window.",
                "first_safe_slice": "Increase --last or event limit, then inspect coverage before adding new logic.",
            }
        )
    return slices


def _grand_rounds_section(
    *,
    cases: Sequence[Mapping[str, Any]],
    repair_candidates: Sequence[Mapping[str, Any]],
    positive_patterns: Sequence[Mapping[str, Any]],
    provider_gaps: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    failures = [
        {
            "case_kind": case.get("case_kind"),
            "severity": case.get("severity"),
            "message": case.get("message"),
        }
        for case in cases
        if case.get("case_kind") not in {"positive_pattern", "dirty_tree_gap"}
    ][:8]
    return {
        "what_agents_did_well": list(positive_patterns)[:8],
        "recurring_failures": failures,
        "provider_adapter_gaps": list(provider_gaps)[:8],
        "top_repair_candidates": list(repair_candidates)[:8],
        "authority_note": "Grand Rounds narrative is a projection over replayable cases, not a promotion lane.",
    }


def build_agent_experience_diagnostics(
    repo_root: Path,
    *,
    last: int | None = None,
    event_limit: int | None = None,
    closeout_limit: int | None = None,
    since_ts: str | None = None,
    grand_rounds: bool = False,
    now: datetime | None = None,
    home: Path | None = None,
    trace_path: Path | None = None,
    execution_trace_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build the read-only Grand Rounds diagnostics packet."""
    repo_root = Path(repo_root)
    session_limit = _bounded(last, default=DEFAULT_SESSION_LIMIT, minimum=1, maximum=500)
    canonical_event_limit = _bounded(event_limit, default=DEFAULT_EVENT_LIMIT, minimum=1, maximum=MAX_EVENT_LIMIT)
    bounded_closeout_limit = _bounded(closeout_limit, default=DEFAULT_CLOSEOUT_LIMIT, minimum=0, maximum=MAX_CLOSEOUT_LIMIT)
    generated_at = (now.astimezone(timezone.utc).isoformat(timespec="milliseconds") if now else _now_iso())

    events, trace_status, trace_gaps = _canonical_events(repo_root, event_limit=canonical_event_limit, trace_path=trace_path)
    execution_payload, execution_gaps = _execution_trace(
        repo_root,
        last=session_limit,
        since_ts=since_ts,
        home=home,
        execution_trace_payload=execution_trace_payload,
    )
    capture_gaps = [*trace_gaps, *execution_gaps]
    closeouts = _closeout_records(events, repo_root=repo_root, closeout_limit=bounded_closeout_limit)

    cases: list[dict[str, Any]] = []
    cases.extend(_build_identity_gap_cases(events))
    cases.extend(_build_process_cases(execution_payload))

    coverage = _coverage(events, execution_payload, closeouts)
    provider_gaps = _provider_adapter_gaps(coverage)
    cases.extend(_build_provider_gap_cases(provider_gaps))
    cases.extend(_build_closeout_cases(closeouts, execution_payload))
    cases = cases[:MAX_CASES]
    positive_patterns = _positive_patterns(cases, closeouts)
    repair_candidates = _repair_candidates(cases, provider_gaps)
    next_slices = _next_slices(provider_gaps, cases)
    packet: dict[str, Any] = {
        "kind": KIND,
        "schema_version": SCHEMA_VERSION,
        "generated_at": generated_at,
        "window": {
            "mode": "last_sessions",
            "last": session_limit,
            "event_limit": canonical_event_limit,
            "closeout_limit": bounded_closeout_limit,
            "since": since_ts,
            "providers": ["claude_code", "codex_app"],
        },
        "source_inputs": _source_inputs(
            trace_status=trace_status,
            execution_payload=execution_payload,
            closeout_limit=bounded_closeout_limit,
            closeout_count=len(closeouts),
            capture_gaps=capture_gaps,
        ),
        "coverage": coverage,
        "metrics": _metrics(events, execution_payload, cases, closeouts),
        "cases": cases,
        "repair_candidates": repair_candidates,
        "positive_patterns": positive_patterns,
        "provider_adapter_gaps": provider_gaps,
        "next_slices": next_slices,
        "authority_boundary": {
            "hard_trace_is_evidence": True,
            "closeout_is_testimony": True,
            "ledger_git_tests_are_verdict": True,
            "repair_candidates_are_not_law": True,
        },
    }
    if grand_rounds:
        packet["grand_rounds"] = _grand_rounds_section(
            cases=cases,
            repair_candidates=repair_candidates,
            positive_patterns=positive_patterns,
            provider_gaps=provider_gaps,
        )
    return packet
