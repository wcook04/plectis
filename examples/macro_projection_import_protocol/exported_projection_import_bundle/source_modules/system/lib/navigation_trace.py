"""Bounded live trace for semantic kernel navigation decisions."""
from __future__ import annotations

import hashlib
import json
import os
import re
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA_VERSION = "navigation_trace_event_v1"
REPLAY_SCHEMA_VERSION = "navigation_trace_replay_v1"
ATTENTION_EVENT_SCHEMA_VERSION = "navigation_attention_event_v0"
ATTENTION_FRAME_SCHEMA_VERSION = "navigation_attention_frame_v0"
STATE_DIR = Path("state/navigation_trace")
EVENTS_FILENAME = "events.jsonl"
ATTENTION_EVENTS_FILENAME = "attention_events.jsonl"
LATEST_REPLAY_FILENAME = "latest_replay.json"
LATEST_ATTENTION_FRAME_FILENAME = "latest_attention_frame.json"
ATTENTION_FRAMES_DIRNAME = "attention_frames"
MAX_EVENT_TARGETS = 6
MAX_REPLAY_EVENTS = 80
MAX_ATTENTION_HANDLES = 20
TRACE_DISABLE_ENV = "AI_WORKFLOW_NAV_TRACE"


class AmbiguousAttentionFrameBinding(RuntimeError):
    """Raised when an alias would append to an ambiguous AttentionFrame."""


class MissingAttentionFrameBinding(RuntimeError):
    """Raised when an alias cannot resolve to an existing AttentionFrame."""

SEMANTIC_EVENT_KINDS = {
    "docs_route",
    "paper_module",
    "navigate",
    "route_query",
    "navigation_efficiency",
    "raw_seed_query",
    "raw_seed_browse",
    "shards",
    "locate",
    "compile",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_ts(value: Any) -> float:
    text = str(value or "").strip()
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return 0.0


def _state_dir(repo_root: Path) -> Path:
    return repo_root / STATE_DIR


def events_path(repo_root: Path) -> Path:
    return _state_dir(repo_root) / EVENTS_FILENAME


def latest_replay_path(repo_root: Path) -> Path:
    return _state_dir(repo_root) / LATEST_REPLAY_FILENAME


def attention_events_path(repo_root: Path) -> Path:
    return _state_dir(repo_root) / ATTENTION_EVENTS_FILENAME


def latest_attention_frame_path(repo_root: Path) -> Path:
    return _state_dir(repo_root) / LATEST_ATTENTION_FRAME_FILENAME


def attention_frame_path(repo_root: Path, frame_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", str(frame_id or "latest"))[:120] or "latest"
    return _state_dir(repo_root) / ATTENTION_FRAMES_DIRNAME / f"{safe_id}.json"


def trace_enabled() -> bool:
    value = str(os.environ.get(TRACE_DISABLE_ENV, "")).strip().casefold()
    return value not in {"0", "false", "no", "off", "disabled"}


def normalize_query(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().casefold())


def lexical_terms(value: Any, *, limit: int = 12) -> list[str]:
    stop = {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "our",
        "the",
        "this",
        "to",
        "with",
    }
    terms = [
        token
        for token in re.findall(r"[a-z0-9_./-]+", normalize_query(value))
        if len(token) > 2 and token not in stop
    ]
    seen: set[str] = set()
    unique: list[str] = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        unique.append(term)
        if len(unique) >= limit:
            break
    return unique


def _short_hash(parts: Iterable[Any], *, length: int = 16) -> str:
    h = hashlib.sha256()
    for part in parts:
        h.update(str(part or "").encode("utf-8", errors="replace"))
        h.update(b"\0")
    return h.hexdigest()[:length]


def _safe_rel(repo_root: Path, value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    path = Path(text)
    if not path.is_absolute():
        return text
    try:
        return str(path.resolve().relative_to(repo_root.resolve()))
    except ValueError:
        return text


def _compact_target(repo_root: Path, raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        text = str(raw or "").strip()
        return {"id": text} if text else None
    target_id = (
        raw.get("target_row_key")
        or raw.get("target_artifact")
        or raw.get("artifact_id")
        or raw.get("route_id")
        or raw.get("slug")
        or raw.get("id")
        or raw.get("path")
        or raw.get("file")
    )
    path = (
        raw.get("source_path")
        or raw.get("target_source_path")
        or raw.get("path")
        or raw.get("file")
    )
    compact = {
        "kind": raw.get("source_kind") or raw.get("target_kind") or raw.get("kind"),
        "id": str(target_id or "").strip() or None,
        "path": _safe_rel(repo_root, path),
        "title": raw.get("title") or raw.get("display_title"),
        "score": raw.get("score") or raw.get("combined_score") or raw.get("semantic_score"),
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [])} or None


def compact_targets(repo_root: Path, targets: Iterable[Any] | None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for raw in list(targets or [])[:MAX_EVENT_TARGETS]:
        compact = _compact_target(repo_root, raw)
        if compact:
            rows.append(compact)
    return rows


def _payload_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {}
    summary: dict[str, Any] = {
        "kind": payload.get("kind"),
        "error": payload.get("error"),
    }
    if isinstance(payload.get("summary"), Mapping):
        summary["summary"] = dict(list(payload["summary"].items())[:6])
    if isinstance(payload.get("resolution"), Mapping):
        summary["route_id"] = payload["resolution"].get("route_id")
        summary["confidence"] = payload["resolution"].get("confidence")
    if isinstance(payload.get("module"), Mapping):
        summary["module_slug"] = payload["module"].get("slug")
    if isinstance(payload.get("route_status_summary"), Mapping):
        stats = payload["route_status_summary"].get("statistics")
        summary["route_statistics"] = stats if isinstance(stats, Mapping) else {}
    for key in ("seed_hits", "routed_hits", "fallback_hits", "hits", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            summary[f"{key}_count"] = len(value)
    return {key: value for key, value in summary.items() if value not in (None, "", {}, [])}


def extract_top_targets(repo_root: Path, event_kind: str, payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw_targets: list[Any] = []
    if event_kind == "docs_route":
        resolution = payload.get("resolution") if isinstance(payload.get("resolution"), Mapping) else {}
        raw_targets.append({"kind": "docs_route", "route_id": resolution.get("route_id")})
        mrs = payload.get("minimum_read_set") if isinstance(payload.get("minimum_read_set"), Mapping) else {}
        raw_targets.extend({"kind": "minimum_read_path", "path": path} for path in list(mrs.get("paths") or [])[:4])
    elif event_kind == "paper_module":
        module = payload.get("module") if isinstance(payload.get("module"), Mapping) else {}
        raw_targets.append({"kind": "paper_module", "slug": module.get("slug"), "file": module.get("file")})
        raw_targets.extend(payload.get("alternatives") or [])
    elif event_kind in {"navigate", "route_query"}:
        raw_targets.extend(payload.get("routed_hits") or payload.get("route_hits") or [])
        raw_targets.extend(payload.get("seed_hits") or [])
        raw_targets.extend(payload.get("fallback_hits") or [])
    elif event_kind == "navigation_efficiency":
        docs_route = payload.get("docs_route") if isinstance(payload.get("docs_route"), Mapping) else {}
        raw_targets.append({"kind": "docs_route", "route_id": docs_route.get("route_id")})
        probe = payload.get("semantic_probe") if isinstance(payload.get("semantic_probe"), Mapping) else {}
        raw_targets.extend(probe.get("top_hits") or [])
    elif event_kind == "locate":
        body = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else payload
        raw_targets.extend(body.get("results") or [])
    elif event_kind == "compile":
        body = payload.get("payload") if isinstance(payload.get("payload"), Mapping) else payload
        raw_targets.extend(body.get("files") or [])
    elif event_kind in {"raw_seed_query", "raw_seed_browse"}:
        if isinstance(payload.get("hits"), list):
            raw_targets.extend(payload.get("hits") or [])
        matches = payload.get("matches") if isinstance(payload.get("matches"), Mapping) else {}
        for key in ("paragraphs", "sections", "shards", "themes", "routes"):
            raw_targets.extend(matches.get(key) or [])
        navigation = payload.get("navigation") if isinstance(payload.get("navigation"), Mapping) else {}
        raw_targets.extend(navigation.get("groups_top") or [])
    return compact_targets(repo_root, raw_targets)


def _phase_context(repo_root: Path) -> dict[str, Any]:
    try:
        from system.lib.phase_activation import load_explicit_active_phase

        active = load_explicit_active_phase(repo_root) or {}
    except Exception:
        active = {}
    phase_id = str(active.get("phase_id") or active.get("active_phase_id") or "").strip() or None
    phase_dir = str(active.get("phase_dir") or active.get("active_phase_dir") or "").strip() or None
    wave_id = None
    if phase_dir:
        synth_path = repo_root / phase_dir / "synth_seed.json"
        try:
            synth = json.loads(synth_path.read_text(encoding="utf-8"))
            current_wave = synth.get("current_wave") if isinstance(synth, Mapping) else {}
            if isinstance(current_wave, Mapping):
                wave_id = current_wave.get("wave_id")
        except Exception:
            wave_id = None
    return {
        "phase_id": phase_id,
        "phase_number": active.get("phase_number") or active.get("active_phase_number"),
        "phase_dir": phase_dir,
        "wave_id": str(wave_id or "").strip() or None,
    }


def current_session_id() -> str:
    for name in (
        "AI_WORKFLOW_NAV_TRACE_SESSION",
        "CODEX_SESSION_ID",
        "CLAUDE_SESSION_ID",
        "CODEX_THREAD_ID",
    ):
        value = str(os.environ.get(name, "")).strip()
        if value:
            return value
    return f"ppid-{os.getppid()}"


def decision_hash(
    *,
    event_kind: str,
    normalized_query: str,
    phase_id: str | None,
    wave_id: str | None,
    top_targets: Iterable[Mapping[str, Any]],
) -> str:
    target_tokens = [
        str(target.get("path") or target.get("id") or target.get("title") or "")
        for target in list(top_targets)[:MAX_EVENT_TARGETS]
    ]
    return _short_hash([event_kind, normalized_query, phase_id or "", wave_id or "", *target_tokens], length=24)


def record_navigation_event(
    repo_root: Path,
    *,
    event_kind: str,
    query: Any = None,
    command: str | None = None,
    top_targets: Iterable[Any] | None = None,
    payload: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Append one semantic navigation event; never raise into command handlers."""
    if not trace_enabled() or event_kind not in SEMANTIC_EVENT_KINDS:
        return None
    try:
        root = repo_root.resolve()
        targets = compact_targets(root, top_targets)
        if not targets:
            targets = extract_top_targets(root, event_kind, payload)
        phase = _phase_context(root)
        normalized = normalize_query(query)
        d_hash = decision_hash(
            event_kind=event_kind,
            normalized_query=normalized,
            phase_id=phase.get("phase_id"),
            wave_id=phase.get("wave_id"),
            top_targets=targets,
        )
        generated_at = _now_iso()
        event = {
            "schema_version": SCHEMA_VERSION,
            "event_id": f"navtrace_{int(time.time() * 1000)}_{d_hash[:10]}",
            "generated_at": generated_at,
            "session_id": current_session_id(),
            "event_kind": event_kind,
            "command": command,
            "query": str(query or "").strip() or None,
            "query_normalized": normalized,
            "lexical_terms": lexical_terms(query),
            "phase": phase,
            "top_targets": targets,
            "decision_hash": d_hash,
            "payload_summary": _payload_summary(payload),
            "metadata": dict(metadata or {}),
        }
        out_path = events_path(root)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        replay = build_replay(root, session="latest", limit=50)
        _write_json(latest_replay_path(root), replay)
        return event
    except Exception:
        return None


def record_navigation_result(
    repo_root: Path,
    *,
    event_kind: str,
    query: Any = None,
    command: str | None = None,
    payload: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    return record_navigation_event(
        repo_root,
        event_kind=event_kind,
        query=query,
        command=command,
        payload=payload,
        metadata=metadata,
    )


def read_events(repo_root: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    path = events_path(repo_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, Mapping):
                rows.append(dict(raw))
    except Exception:
        return []
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


def _latest_session(events: list[Mapping[str, Any]]) -> str | None:
    for event in reversed(events):
        session_id = str(event.get("session_id") or "").strip()
        if session_id:
            return session_id
    return None


def _select_events(events: list[dict[str, Any]], *, session: str = "latest", limit: int = MAX_REPLAY_EVENTS) -> list[dict[str, Any]]:
    selected = events
    if session and session != "all":
        session_id = _latest_session(events) if session == "latest" else session
        if session_id:
            selected = [event for event in events if event.get("session_id") == session_id]
    return selected[-max(1, int(limit or MAX_REPLAY_EVENTS)) :]


def _event_weight(event: Mapping[str, Any], *, now_ts: float) -> float:
    age_hours = max(0.0, (now_ts - _parse_ts(event.get("generated_at"))) / 3600.0)
    return 1.0 / (1.0 + age_hours / 6.0)


def _counter_top(counter: Counter[str], *, limit: int = 8) -> list[dict[str, Any]]:
    return [
        {"value": key, "score": round(score, 4)}
        for key, score in counter.most_common(limit)
    ]


def _repeated_hashes(events: list[Mapping[str, Any]], *, limit: int = 8) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for event in events:
        d_hash = str(event.get("decision_hash") or "")
        if d_hash:
            grouped[d_hash].append(event)
    rows: list[dict[str, Any]] = []
    for d_hash, items in grouped.items():
        if len(items) <= 1:
            continue
        rows.append(
            {
                "decision_hash": d_hash,
                "count": len(items),
                "event_kinds": sorted({str(item.get("event_kind") or "") for item in items}),
                "first_seen": items[0].get("generated_at"),
                "last_seen": items[-1].get("generated_at"),
                "last_query": items[-1].get("query"),
            }
        )
    rows.sort(key=lambda row: (-int(row["count"]), str(row.get("last_seen") or "")))
    return rows[:limit]


def _target_label(target: Mapping[str, Any]) -> str | None:
    return str(target.get("path") or target.get("id") or target.get("title") or "").strip() or None


def _next_cheapest_command(events: list[Mapping[str, Any]], repeated: list[Mapping[str, Any]]) -> dict[str, str]:
    if repeated:
        return {
            "command": "./repo-python kernel.py --navigation-trace-replay latest",
            "reason": "A decision hash repeated; replay the bounded packet before rerunning the same route.",
        }
    if not events:
        return {
            "command": "./repo-python kernel.py --navigation-efficiency \"<query>\"",
            "reason": "No trace events exist yet; start with the command-budgeted route.",
        }
    last = events[-1]
    targets = [target for target in (last.get("top_targets") or []) if isinstance(target, Mapping)]
    for target in targets:
        path = str(target.get("path") or "").strip()
        if path.endswith(".py"):
            return {
                "command": f"./repo-python kernel.py --compile {json.dumps(path)}",
                "reason": "The latest route named a Python source path; compile before raw reading.",
            }
        if path:
            return {
                "command": f"./repo-python kernel.py --docs-route {json.dumps(path)}",
                "reason": "The latest route named a path; route the path before widening.",
            }
    query = str(last.get("query") or "").strip()
    return {
        "command": f"./repo-python kernel.py --navigation-efficiency {json.dumps(query or '<query>')}",
        "reason": "Use the command-budget lane to choose the next semantic surface.",
    }


def _skipped_rung_hints(events: list[Mapping[str, Any]], repeated: list[Mapping[str, Any]]) -> list[str]:
    hints: list[str] = []
    if repeated:
        hints.append("Repeated decision hashes detected; use replay before rerunning the same navigation command.")
    if len(events) >= 4:
        first_ts = _parse_ts(events[-4].get("generated_at"))
        last_ts = _parse_ts(events[-1].get("generated_at"))
        if first_ts and last_ts and last_ts - first_ts < 600:
            hints.append("Four or more semantic navigation events occurred within ten minutes; check command budget.")
    first_kind = str(events[0].get("event_kind") or "") if events else ""
    if first_kind in {"locate", "compile"}:
        hints.append("Trace starts on a structural surface; confirm a semantic route was not skipped.")
    return hints[:6]


def build_replay(repo_root: Path, *, session: str = "latest", limit: int = MAX_REPLAY_EVENTS) -> dict[str, Any]:
    all_events = read_events(repo_root)
    events = _select_events(all_events, session=session, limit=limit)
    now_ts = time.time()
    term_scores: Counter[str] = Counter()
    target_scores: Counter[str] = Counter()
    kind_scores: Counter[str] = Counter()
    for event in events:
        weight = _event_weight(event, now_ts=now_ts)
        kind_scores[str(event.get("event_kind") or "unknown")] += weight
        for term in event.get("lexical_terms") or []:
            term_scores[str(term)] += weight
        for target in event.get("top_targets") or []:
            if isinstance(target, Mapping):
                label = _target_label(target)
                if label:
                    target_scores[label] += weight
    repeated = _repeated_hashes(events)
    latest = events[-1] if events else None
    return {
        "kind": "kernel.navigation_trace.replay",
        "schema_version": REPLAY_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "state": {
            "events_path": str(events_path(repo_root).relative_to(repo_root)),
            "latest_replay_path": str(latest_replay_path(repo_root).relative_to(repo_root)),
            "trace_enabled": trace_enabled(),
        },
        "query": {"session": session, "limit": limit},
        "summary": {
            "event_count": len(events),
            "total_event_count": len(all_events),
            "session_id": latest.get("session_id") if isinstance(latest, Mapping) else None,
            "latest_event_kind": latest.get("event_kind") if isinstance(latest, Mapping) else None,
            "latest_decision_hash": latest.get("decision_hash") if isinstance(latest, Mapping) else None,
            "repeated_decision_hash_count": len(repeated),
        },
        "payload": {
            "active_phase": latest.get("phase") if isinstance(latest, Mapping) else {},
            "decision_chain": [
                {
                    "generated_at": event.get("generated_at"),
                    "event_kind": event.get("event_kind"),
                    "command": event.get("command"),
                    "query": event.get("query"),
                    "decision_hash": event.get("decision_hash"),
                    "top_targets": list(event.get("top_targets") or [])[:3],
                }
                for event in events[-12:]
            ],
            "top_lexical_terms": _counter_top(term_scores),
            "top_target_paths": _counter_top(target_scores),
            "semantic_surface_counts": _counter_top(kind_scores),
            "repeated_decision_hashes": repeated,
            "skipped_rung_hints": _skipped_rung_hints(events, repeated),
            "next_cheapest_command": _next_cheapest_command(events, repeated),
        },
    }


def build_status(repo_root: Path) -> dict[str, Any]:
    events = read_events(repo_root)
    sessions = Counter(str(event.get("session_id") or "unknown") for event in events)
    kinds = Counter(str(event.get("event_kind") or "unknown") for event in events)
    latest = events[-1] if events else {}
    return {
        "kind": "kernel.navigation_trace.status",
        "schema_version": "navigation_trace_status_v1",
        "generated_at": _now_iso(),
        "trace_enabled": trace_enabled(),
        "events_path": str(events_path(repo_root).relative_to(repo_root)),
        "latest_replay_path": str(latest_replay_path(repo_root).relative_to(repo_root)),
        "event_count": len(events),
        "session_count": len(sessions),
        "latest_event": {
            "generated_at": latest.get("generated_at"),
            "session_id": latest.get("session_id"),
            "event_kind": latest.get("event_kind"),
            "query": latest.get("query"),
            "decision_hash": latest.get("decision_hash"),
        },
        "event_kind_counts": dict(kinds.most_common()),
        "recent_sessions": [
            {"session_id": session_id, "event_count": count}
            for session_id, count in sessions.most_common(8)
        ],
    }


def build_convergence(repo_root: Path, *, last: int = 50) -> dict[str, Any]:
    events = read_events(repo_root, limit=max(1, int(last or 50)))
    repeated = _repeated_hashes(events, limit=20)
    return {
        "kind": "kernel.navigation_trace.convergence",
        "schema_version": "navigation_trace_convergence_v1",
        "generated_at": _now_iso(),
        "query": {"last": last},
        "summary": {
            "event_count": len(events),
            "repeated_decision_hash_count": len(repeated),
            "loop_signal": bool(repeated),
        },
        "repeated_decision_hashes": repeated,
        "next": [
            _next_cheapest_command(events, repeated),
        ],
    }


def build_efficiency(repo_root: Path, *, last: int = 50) -> dict[str, Any]:
    events = read_events(repo_root, limit=max(1, int(last or 50)))
    repeated = _repeated_hashes(events, limit=20)
    sessions = defaultdict(list)
    for event in events:
        sessions[str(event.get("session_id") or "unknown")].append(event)
    budget_violations = []
    for session_id, rows in sessions.items():
        if len(rows) > 3:
            budget_violations.append(
                {
                    "session_id": session_id,
                    "event_count": len(rows),
                    "latest_event_kind": rows[-1].get("event_kind"),
                    "latest_query": rows[-1].get("query"),
                }
            )
    kind_counts = Counter(str(event.get("event_kind") or "unknown") for event in events)
    return {
        "kind": "kernel.navigation_trace.efficiency",
        "schema_version": "navigation_trace_efficiency_v1",
        "generated_at": _now_iso(),
        "query": {"last": last},
        "summary": {
            "event_count": len(events),
            "session_count": len(sessions),
            "repeated_decision_hash_count": len(repeated),
            "command_budget_violation_count": len(budget_violations),
        },
        "semantic_surface_counts": dict(kind_counts.most_common()),
        "command_budget_violations": budget_violations[:12],
        "repeated_decision_hashes": repeated,
        "next": [
            _next_cheapest_command(events, repeated),
        ],
    }


def write_replay_summary(repo_root: Path, *, session: str = "latest", limit: int = MAX_REPLAY_EVENTS) -> Path:
    replay = build_replay(repo_root, session=session, limit=limit)
    path = latest_replay_path(repo_root)
    _write_json(path, replay)
    return path


def _handle_prefix(artifact_kind: str) -> str:
    return {
        "skills": "skill",
        "standards": "standard",
        "paper_modules": "paper_module",
        "task_ledger": "work_item",
        "derived_facts": "fact",
        "system_atlas": "system_atlas",
        "python_files": "python_file",
        "python_scopes": "python_scope",
        "raw_seed_shards": "raw_seed_shard",
        "annex_patterns": "annex_pattern",
        "annex_distillation_patterns": "annex_distillation_pattern",
    }.get(str(artifact_kind or "").strip(), str(artifact_kind or "artifact").strip() or "artifact")


def _row_identity(row: Mapping[str, Any], *, artifact_kind: str) -> dict[str, Any] | None:
    raw_handle = row.get("canonical_handle") or row.get("handle")
    raw_id = (
        row.get("id")
        or row.get("skill_id")
        or row.get("standard_id")
        or row.get("slug")
        or row.get("work_item_id")
        or row.get("fact_id")
        or row.get("scope_id")
        or row.get("symbol_id")
        or row.get("path")
        or row.get("row_id")
    )
    text_id = str(raw_id or "").strip()
    handle_text = str(raw_handle or "").strip()
    if not text_id and not handle_text:
        return None
    if str(row.get("canonical_handle") or "").strip():
        handle_source = "canonical_handle"
    elif str(row.get("handle") or "").strip():
        handle_source = "handle"
    else:
        handle_source = "fallback_inference"
    handle = handle_text or (text_id if ":" in text_id else f"{_handle_prefix(artifact_kind)}:{text_id}")
    row_id = str(row.get("row_id") or "").strip() or None
    compact = {
        "handle": handle,
        "handle_source": handle_source,
        "id": text_id,
        "row_id": row_id,
        "title": row.get("title") or row.get("name") or row.get("claim"),
        "drilldown_command": row.get("drilldown_command"),
        "evidence_command": row.get("evidence_command"),
    }
    return {key: value for key, value in compact.items() if value not in (None, "", [])}


def _unique_by_key(rows: Iterable[Mapping[str, Any]], key: str, *, limit: int) -> list[dict[str, Any]]:
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for row in rows:
        value = str(row.get(key) or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        out.append(dict(row))
        if len(out) >= limit:
            break
    return out


def _attention_handle_output(
    rows: Iterable[Mapping[str, Any]],
    *,
    limit: int,
    compact: bool,
) -> list[dict[str, Any]]:
    unique = _unique_by_key(rows, "handle", limit=limit)
    if not compact:
        return unique
    allowed = ("handle", "handle_source", "id", "title")
    return [
        {key: value for key in allowed if (value := row.get(key)) not in (None, "", [])}
        for row in unique
    ]


def _unique_strings(values: Iterable[Any], *, limit: int) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
        if len(out) >= limit:
            break
    return out


def _dominant_handle_source(handles: Iterable[Mapping[str, Any]]) -> str | None:
    sources = [str(row.get("handle_source") or "").strip() for row in handles if isinstance(row, Mapping)]
    if not sources:
        return None
    if "fallback_inference" in sources:
        return "fallback_inference"
    if "handle" in sources:
        return "handle"
    if "canonical_handle" in sources:
        return "canonical_handle"
    return sources[0]


def _compact_mapping(value: Mapping[str, Any], *, limit: int = 8) -> dict[str, Any]:
    compact: dict[str, Any] = {}
    for key, item in value.items():
        if len(compact) >= limit:
            break
        if item in (None, "", [], {}):
            continue
        if isinstance(item, Mapping):
            compact[str(key)] = _compact_mapping(item, limit=5)
        elif isinstance(item, list):
            compact[str(key)] = item[:5]
        else:
            compact[str(key)] = item
    return compact


def _option_surface_focus_semantics(
    payload: Mapping[str, Any],
    *,
    band: str,
    row_count: int,
    command: str | None,
) -> str:
    """Classify option-surface rows as candidates or focused handles.

    Broad browse surfaces show candidate handles. Explicit id/card/detail surfaces focus
    handles, but never select them for the task.
    """
    selection = payload.get("selection") if isinstance(payload.get("selection"), Mapping) else {}
    selection_mode = str(selection.get("mode") or "").strip().lower()
    command_text = str(command or "")
    band_text = str(band or "").strip().lower()
    broad_modes = {"", "all", "query", "browse", "cluster", "artifact_kind_cluster_overview"}
    explicit_modes = {"id", "ids", "row", "single", "explicit"}
    if selection_mode in explicit_modes or "--ids" in command_text or "--row" in command_text:
        return "focused"
    if band_text in {"cluster_flag", "cluster", "flag", "list", "index"}:
        return "candidate"
    if selection_mode in broad_modes and row_count != 1:
        return "candidate"
    if band_text in {"card", "detail", "context", "deep"} and row_count == 1:
        return "focused"
    return "candidate"


def _attention_delta_from_payload(payload: Mapping[str, Any], *, command: str | None = None) -> dict[str, Any]:
    lens = payload.get("lens_packet") if isinstance(payload.get("lens_packet"), Mapping) else {}
    artifact_kind = str(payload.get("artifact_kind") or "").strip()
    if not artifact_kind:
        surface_id = str(lens.get("surface_id") or "")
        if surface_id.startswith("option_surface:"):
            artifact_kind = surface_id.split(":", 1)[1]
    band = str(payload.get("band") or lens.get("attention_delta_shape", {}).get("selected_band") or "").strip()
    rows = [row for row in list(payload.get("rows") or []) if isinstance(row, Mapping)]
    handles = [
        handle
        for row in rows[:MAX_ATTENTION_HANDLES]
        if (handle := _row_identity(row, artifact_kind=artifact_kind))
    ]
    handle_bucket = _option_surface_focus_semantics(
        payload,
        band=band,
        row_count=len(rows),
        command=command,
    )
    candidate_handles = handles if handle_bucket == "candidate" else []
    focused_handles = handles if handle_bucket == "focused" else []
    source_owner = lens.get("source_payload_owner") if isinstance(lens.get("source_payload_owner"), Mapping) else {}
    source_refs = _unique_strings(
        list(source_owner.get("source_refs") or []) + list(payload.get("source_refs") or []),
        limit=20,
    )
    omissions: list[Any] = []
    if isinstance(payload.get("omission_receipt"), Mapping):
        omissions.append(payload["omission_receipt"])
    if isinstance(payload.get("omissions"), list):
        omissions.extend(payload["omissions"][:8])
    for row in rows[:8]:
        if isinstance(row.get("omission_receipt"), Mapping):
            omissions.append(row["omission_receipt"])
    freshness_constraints: list[dict[str, Any]] = []
    for key in ("source_coupling", "currentness", "projection_freshness", "freshness"):
        value = payload.get(key)
        if isinstance(value, Mapping):
            freshness_constraints.append({"kind": key, "value": _compact_mapping(value)})
    navigation_boundary = payload.get("navigation_boundary") if isinstance(payload.get("navigation_boundary"), Mapping) else {}
    mutation_boundary = {
        "mutation_allowed_by_this_profile": bool(lens.get("mutation_allowed_by_this_profile")),
        "source_mutation_allowed_by_this_profile": bool(source_owner.get("source_mutation_allowed_by_this_profile")),
    }
    if navigation_boundary.get("mutation_rule"):
        mutation_boundary["mutation_rule"] = navigation_boundary.get("mutation_rule")
    next_moves: list[dict[str, Any]] = []
    next_handle_rows = focused_handles or candidate_handles
    for row in next_handle_rows[:10]:
        command = row.get("drilldown_command") or row.get("evidence_command")
        if command:
            next_moves.append({"command": command, "reason": f"Open {row.get('handle')} from the attention surface."})
    return {
        "seen_surface": lens.get("surface_id") or f"option_surface:{artifact_kind}",
        "selected_kind": artifact_kind or None,
        "selected_band": band or None,
        "candidate_handles_seen_added": candidate_handles,
        "focused_handles_added": focused_handles,
        "selected_handles_added": [],
        "trusted_authorities_added": [],
        "acted_on_handles_added": [],
        "rejected_handles_added": [],
        "stale_handles_added": [],
        "blocked_handles_added": [],
        "handle_source": _dominant_handle_source(handles),
        "source_refs_added": source_refs,
        "omissions_added": omissions[:10],
        "freshness_constraints_added": freshness_constraints[:8],
        "mutation_boundary": mutation_boundary,
        "next_legal_moves_added": next_moves[:8],
    }


def _status_handle(handle: str, *, status: Any = None, title: Any = None, reason: Any = None) -> dict[str, Any]:
    row = {
        "handle": handle,
        "status": status,
        "title": title,
        "reason": reason,
    }
    return {key: value for key, value in row.items() if value not in (None, "", [])}


def _status_token(value: Any, fallback: str = "unknown") -> str:
    text = str(value or "").strip()
    return text or fallback


def _is_blocking_status(value: Any) -> bool:
    token = _status_token(value, "").lower()
    return (
        token in {"blocked", "hard_stop", "required_missing_session", "required_missing_claim"}
        or token.startswith("blocked_")
    )


def _mission_transaction_receipt_status(
    *,
    finalizers: Mapping[str, Any],
    convergence: Mapping[str, Any],
) -> str:
    receipt = (
        finalizers.get("task_ledger_execution_receipt")
        if isinstance(finalizers.get("task_ledger_execution_receipt"), Mapping)
        else {}
    )
    if receipt.get("status"):
        return str(receipt.get("status"))
    receipt_state = (
        convergence.get("task_ledger_receipt_state")
        if isinstance(convergence.get("task_ledger_receipt_state"), Mapping)
        else {}
    )
    if receipt_state.get("latest_execution_receipt") or receipt_state.get("receipt_refs"):
        return "recorded"
    return "unknown"


def _mutation_boundary_attention_delta(payload: Mapping[str, Any], *, command: str | None = None) -> dict[str, Any]:
    """Summarize transaction legality as attention memory, not task selection."""
    git = payload.get("git") if isinstance(payload.get("git"), Mapping) else {}
    inputs = payload.get("inputs") if isinstance(payload.get("inputs"), Mapping) else {}
    landing = payload.get("landing_decision") if isinstance(payload.get("landing_decision"), Mapping) else {}
    shared_index = (
        payload.get("shared_index_quarantine")
        if isinstance(payload.get("shared_index_quarantine"), Mapping)
        else {}
    )
    work_ledger = payload.get("work_ledger") if isinstance(payload.get("work_ledger"), Mapping) else {}
    candidate = (
        payload.get("transaction_candidate")
        if isinstance(payload.get("transaction_candidate"), Mapping)
        else {}
    )
    claim_requirements = (
        candidate.get("claim_requirements")
        if isinstance(candidate.get("claim_requirements"), Mapping)
        else {}
    )
    finalizers = candidate.get("finalizers") if isinstance(candidate.get("finalizers"), Mapping) else {}
    convergence = (
        payload.get("transaction_convergence")
        if isinstance(payload.get("transaction_convergence"), Mapping)
        else {}
    )
    reconcile = (
        payload.get("transaction_convergence_reconcile")
        if isinstance(payload.get("transaction_convergence_reconcile"), Mapping)
        else {}
    )
    governor = (
        payload.get("derived_state_bloat_governor")
        if isinstance(payload.get("derived_state_bloat_governor"), Mapping)
        else {}
    )
    workspace_pressure = (
        governor.get("workspace_bloat_pressure")
        if isinstance(governor.get("workspace_bloat_pressure"), Mapping)
        else {}
    )
    push_gate = (
        governor.get("github_push_bloat_gate")
        if isinstance(governor.get("github_push_bloat_gate"), Mapping)
        else {}
    )
    dirty_tree = (
        payload.get("dirty_tree_classification")
        if isinstance(payload.get("dirty_tree_classification"), Mapping)
        else {}
    )
    registry = (
        payload.get("generated_projection_registry")
        if isinstance(payload.get("generated_projection_registry"), Mapping)
        else {}
    )
    staged_count = int(git.get("staged_path_count") or shared_index.get("staged_path_count") or 0)
    staged_index = "clear" if staged_count == 0 else "nonempty"
    receipt_status = _mission_transaction_receipt_status(finalizers=finalizers, convergence=convergence)
    work_finalizer = (
        finalizers.get("work_ledger_append_or_exempt")
        if isinstance(finalizers.get("work_ledger_append_or_exempt"), Mapping)
        else {}
    )
    workspace_status = _status_token(workspace_pressure.get("status"), "unknown")
    mutation_boundary = {
        "staged_index": staged_index,
        "staged_path_count": staged_count,
        "private_index_scoped_commit_allowed": shared_index.get("private_index_scoped_commit_allowed"),
        "landing_decision": landing.get("status"),
        "landing_reason": landing.get("reason"),
        "recommended_lane": landing.get("recommended_lane") or payload.get("recommended_landing_lane"),
        "claim_status": claim_requirements.get("status"),
        "claim_required": claim_requirements.get("claim_required"),
        "execution_receipt_status": receipt_status,
        "work_ledger_status": work_finalizer.get("status") or work_ledger.get("status"),
        "workspace_bloat_status": (
            f"{workspace_status}_but_not_local_landing_gate"
            if workspace_status == "blocked" and landing.get("status") not in {"blocked", "hard_stop"}
            else workspace_status
        ),
        "push_gate_status": push_gate.get("status"),
        "transaction_convergence_status": convergence.get("status"),
        "transaction_convergence_next_action": convergence.get("next_action"),
        "reconcile_status": reconcile.get("status"),
        "reconcile_next_action": reconcile.get("next_action"),
    }
    trusted_authorities = [
        _status_handle("authority:git_index", status=staged_index, title="Git index"),
        _status_handle("authority:task_ledger", status=receipt_status, title="Task Ledger"),
        _status_handle(
            "authority:work_ledger",
            status=work_finalizer.get("status") or work_ledger.get("status"),
            title="Work Ledger",
        ),
        _status_handle(
            "authority:shared_worktree_guard",
            status=shared_index.get("status"),
            title="Shared worktree guard",
        ),
    ]
    if registry:
        trusted_authorities.append(
            _status_handle(
                "authority:generated_projection_registry",
                status=registry.get("kind") or registry.get("schema_version"),
                title="Generated projection registry",
            )
        )
    blocked_handles: list[dict[str, Any]] = []
    stale_handles: list[dict[str, Any]] = []
    next_moves: list[dict[str, Any]] = []
    if _is_blocking_status(landing.get("status")):
        blocked_handles.append(
            _status_handle(
                "mutation_boundary:landing_decision",
                status=landing.get("status"),
                reason=landing.get("reason"),
                title="Landing decision",
            )
        )
    if _is_blocking_status(claim_requirements.get("status")):
        blocked_handles.append(
            _status_handle(
                "mutation_boundary:claim_requirements",
                status=claim_requirements.get("status"),
                reason=claim_requirements.get("reason"),
                title="Claim requirements",
            )
        )
    if _is_blocking_status(shared_index.get("status")):
        blocked_handles.append(
            _status_handle(
                "mutation_boundary:shared_index_quarantine",
                status=shared_index.get("status"),
                reason=shared_index.get("next_action"),
                title="Shared index quarantine",
            )
        )
    if _is_blocking_status(dirty_tree.get("status")):
        blocked_handles.append(
            _status_handle(
                "mutation_boundary:dirty_tree_classification",
                status=dirty_tree.get("status"),
                reason=dirty_tree.get("next_action"),
                title="Dirty tree classification",
            )
        )
    for key, value in finalizers.items():
        if not isinstance(value, Mapping):
            continue
        status = value.get("status")
        if _is_blocking_status(status):
            blocked_handles.append(
                _status_handle(
                    f"mutation_boundary:finalizer:{key}",
                    status=status,
                    reason=value.get("command") or value.get("policy"),
                    title=key,
                )
            )
        elif _status_token(status, "") in {"pending", "pending_finalizer"}:
            next_moves.append(
                {
                    "command": value.get("command") or f"complete transaction finalizer: {key}",
                    "reason": f"{key} is {status}",
                }
            )
    summary = convergence.get("summary") if isinstance(convergence.get("summary"), Mapping) else {}
    stale_session_count = int(summary.get("stale_work_ledger_sessions") or 0)
    if stale_session_count:
        stale_handles.append(
            _status_handle(
                "mutation_boundary:stale_work_ledger_sessions",
                status="stale",
                reason=f"{stale_session_count} stale transaction session(s)",
                title="Stale Work Ledger sessions",
            )
        )
    acted_on_handles: list[dict[str, Any]] = []
    for transaction in convergence.get("recent_transactions") or []:
        if not isinstance(transaction, Mapping):
            continue
        receipt = (
            transaction.get("task_ledger_execution_receipt")
            if isinstance(transaction.get("task_ledger_execution_receipt"), Mapping)
            else {}
        )
        commit_ref = next((str(item) for item in transaction.get("commit_refs") or [] if str(item).strip()), "")
        transaction_id = str(transaction.get("transaction_id") or "").strip()
        if receipt.get("status") == "recorded" and commit_ref and transaction_id:
            acted_on_handles.append(
                _status_handle(
                    f"transaction:{transaction_id}",
                    status="recorded",
                    reason=f"commit:{commit_ref}",
                    title="Task Ledger execution receipt",
                )
            )
    for command_value, reason in (
        (landing.get("recommended_lane"), "recommended landing lane"),
        (convergence.get("next_action"), "transaction convergence next action"),
        (reconcile.get("next_action"), "transaction reconcile next action"),
        (shared_index.get("next_action"), "shared index next action"),
    ):
        text = str(command_value or "").strip()
        if text and text != "none":
            next_moves.append({"command": text, "reason": reason})
    source_refs = [
        "system/lib/mission_transaction_landing_preflight.py",
        "tools/meta/control/mission_transaction_preflight.py",
    ]
    authority = convergence.get("authority") if isinstance(convergence.get("authority"), Mapping) else {}
    for key in ("task_ledger_authority", "work_ledger_authority", "runtime_authority"):
        if authority.get(key):
            source_refs.append(str(authority[key]))
    freshness_constraints: list[dict[str, Any]] = []
    for key, value in (
        ("shared_index_quarantine", shared_index),
        ("dirty_tree_classification", dirty_tree),
        ("workspace_bloat_pressure", workspace_pressure),
        ("github_push_bloat_gate", push_gate),
    ):
        if isinstance(value, Mapping) and value:
            freshness_constraints.append({"kind": key, "value": _compact_mapping(value, limit=5)})
    subject_ids = inputs.get("target_ids") if isinstance(inputs.get("target_ids"), list) else []
    return {
        "seen_surface": "mission_transaction_preflight",
        "selected_kind": "transaction_boundary",
        "selected_band": "flag",
        "candidate_handles_seen_added": [],
        "focused_handles_added": [],
        "selected_handles_added": [],
        "trusted_authorities_added": trusted_authorities[:8],
        "acted_on_handles_added": acted_on_handles[:8],
        "rejected_handles_added": [],
        "stale_handles_added": stale_handles[:8],
        "blocked_handles_added": blocked_handles[:8],
        "handle_source": None,
        "source_refs_added": _unique_strings(source_refs, limit=12),
        "omissions_added": [
            {
                "omitted": "full mission transaction preflight body",
                "drilldown": command or "./repo-python tools/meta/control/mission_transaction_preflight.py --full",
            }
        ],
        "freshness_constraints_added": freshness_constraints[:6],
        "mutation_boundary": {key: value for key, value in mutation_boundary.items() if value not in (None, "", [])},
        "next_legal_moves_added": next_moves[:8],
        "subject_ids": [str(item) for item in subject_ids if str(item).strip()][:8],
    }


def _binding_from_event(event: Mapping[str, Any]) -> dict[str, Any]:
    binding = event.get("binding") if isinstance(event.get("binding"), Mapping) else {}
    if binding:
        return {str(key): value for key, value in binding.items() if value not in (None, "", [], {})}
    metadata = event.get("metadata") if isinstance(event.get("metadata"), Mapping) else {}
    binding = metadata.get("binding") if isinstance(metadata.get("binding"), Mapping) else {}
    return {str(key): value for key, value in binding.items() if value not in (None, "", [], {})}


def _binding_alias(value: str) -> tuple[str, str] | None:
    raw = str(value or "").strip()
    if ":" not in raw:
        return None
    prefix, suffix = raw.split(":", 1)
    suffix = suffix.strip()
    if not suffix:
        return None
    key = {
        "task_frame": "task_frame_id",
        "taskframe": "task_frame_id",
        "phase": "phase_id",
        "session": "actor_session_id",
        "actor_session": "actor_session_id",
        "work_item": "work_item_id",
        "workitem": "work_item_id",
        "entry_event": "entry_event_id",
    }.get(prefix.strip().lower())
    if not key:
        return None
    return key, suffix


def _binding_alias_label(key: str) -> str:
    return {
        "task_frame_id": "task_frame",
        "phase_id": "phase",
        "actor_session_id": "session",
        "work_item_id": "work_item",
        "entry_event_id": "entry_event",
    }.get(key, key)


def _binding_alias_candidates(
    events: list[Mapping[str, Any]],
    *,
    key: str,
    value: str,
) -> list[dict[str, Any]]:
    target = str(value or "").strip()
    if not target:
        return []
    by_frame: dict[str, dict[str, Any]] = {}
    for event in events:
        binding = _binding_from_event(event)
        if str(binding.get(key) or "").strip() == target:
            frame_id = str(event.get("frame_id") or "").strip()
            if frame_id:
                generated_at = str(event.get("generated_at") or "")
                previous = by_frame.get(frame_id)
                if previous and _parse_ts(previous.get("latest_event_at")) > _parse_ts(generated_at):
                    continue
                by_frame[frame_id] = {
                    "frame_id": frame_id,
                    "latest_event_at": generated_at,
                    "latest_event_id": event.get("event_id"),
                    "binding": {
                        str(item_key): item_value
                        for item_key, item_value in binding.items()
                        if item_value not in (None, "", [], {})
                    },
                }
    return sorted(by_frame.values(), key=lambda row: _parse_ts(row.get("latest_event_at")), reverse=True)


def _latest_attention_frame_id_for_binding(events: list[Mapping[str, Any]], *, key: str, value: str) -> str | None:
    candidates = _binding_alias_candidates(events, key=key, value=value)
    return str(candidates[0].get("frame_id") or "").strip() if candidates else None


def _binding_disambiguation_hints(candidates: list[Mapping[str, Any]], *, limit: int = 4) -> list[str]:
    hints: list[str] = []
    for candidate in candidates:
        binding = candidate.get("binding") if isinstance(candidate.get("binding"), Mapping) else {}
        task_frame_id = str(binding.get("task_frame_id") or "").strip()
        work_item_id = str(binding.get("work_item_id") or "").strip()
        frame_id = str(candidate.get("frame_id") or "").strip()
        if task_frame_id:
            hints.append(f"./repo-python kernel.py --attention-state task_frame:{task_frame_id} --band flag")
        elif work_item_id:
            hints.append(f"./repo-python kernel.py --attention-state work_item:{work_item_id} --band flag")
        elif frame_id:
            hints.append(f"./repo-python kernel.py --attention-state {frame_id} --band flag")
        if len(hints) >= limit:
            break
    return _unique_strings(hints, limit=limit)


def resolve_attention_frame_binding_receipt(
    repo_root: Path,
    frame_id: str | None,
    *,
    mode: str = "read",
    payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    raw = str(frame_id or "latest").strip()
    requested = raw or "latest"
    events = read_attention_events(repo_root)
    receipt: dict[str, Any] = {
        "requested_frame": requested,
        "resolved_frame_id": None,
        "resolution_kind": None,
        "requested_alias": None,
        "resolved_by": None,
        "binding_key": None,
        "binding_value": None,
        "candidate_count": 0,
        "selected_policy": None,
        "append_safe": False,
        "status": None,
        "disambiguation_hints": [],
    }
    if requested == "new":
        if mode == "append":
            receipt.update(
                {
                    "resolved_frame_id": _new_attention_frame_id(payload),
                    "resolution_kind": "new_frame",
                    "candidate_count": 0,
                    "append_safe": True,
                    "status": "new",
                }
            )
        else:
            receipt.update({"resolution_kind": "new_frame", "status": "no_attention_frame"})
        return receipt
    if requested in {"", "latest"}:
        resolved = _latest_attention_frame_snapshot_id(repo_root) or _latest_attention_frame_id(events)
        receipt.update(
            {
                "resolved_frame_id": resolved,
                "resolution_kind": "latest",
                "candidate_count": 1 if resolved else 0,
                "selected_policy": "latest_snapshot_then_event",
                "append_safe": mode == "append",
                "status": "latest" if resolved else "no_attention_frame",
            }
        )
        return receipt
    if alias := _binding_alias(requested):
        key, value = alias
        candidates = _binding_alias_candidates(events, key=key, value=value)
        candidate_count = len(candidates)
        resolved = str(candidates[0].get("frame_id") or "").strip() if candidates else None
        label = _binding_alias_label(key)
        status = "missing_alias"
        selected_policy = None
        append_safe = False
        if candidate_count == 1:
            status = "exact" if key in {"task_frame_id", "entry_event_id"} else "unambiguous"
            append_safe = True
        elif candidate_count > 1:
            status = "ambiguous_latest"
            selected_policy = "latest_event_at"
        receipt.update(
            {
                "resolved_frame_id": resolved,
                "resolution_kind": "binding_alias",
                "requested_alias": requested,
                "resolved_by": key,
                "binding_key": key,
                "binding_value": value,
                "candidate_count": candidate_count,
                "selected_policy": selected_policy,
                "append_safe": append_safe,
                "status": status,
                "disambiguation_hints": _binding_disambiguation_hints(candidates),
            }
        )
        if candidate_count > 1:
            receipt["disambiguation_hints"].append(
                f"Use task_frame:<id> instead of broad {label}:{value} before appending."
            )
        return receipt
    exists = any(str(event.get("frame_id") or "").strip() == requested for event in events)
    receipt.update(
        {
            "resolved_frame_id": requested,
            "resolution_kind": "frame_id",
            "candidate_count": 1 if exists else 0,
            "append_safe": mode == "append",
            "status": "direct_frame_id" if exists else "direct_frame_id_unseen",
        }
    )
    return receipt


def _attention_binding_delta(payload: Mapping[str, Any], *, command: str | None = None) -> dict[str, Any]:
    """Bind a frame to task/session identity without selecting task artifacts."""
    binding = payload.get("binding") if isinstance(payload.get("binding"), Mapping) else {}
    entry_packet = payload.get("entry_packet") if isinstance(payload.get("entry_packet"), Mapping) else {}
    selected_lane = entry_packet.get("selected_lane") if isinstance(entry_packet.get("selected_lane"), Mapping) else {}
    next_action = entry_packet.get("next_action") if isinstance(entry_packet.get("next_action"), Mapping) else {}
    source_refs = _unique_strings(
        list(payload.get("source_refs") or [])
        + [
            "system/lib/kernel/commands/comprehension_snapshot.py",
            "codex/standards/std_agent_entry_surface.json",
        ],
        limit=8,
    )
    next_moves: list[dict[str, Any]] = []
    next_command = str(next_action.get("command") or "").strip()
    if next_command:
        next_moves.append(
            {
                "command": next_command,
                "reason": "Entry packet next action bound to this AttentionFrame.",
            }
        )
    selected_lane_id = str(selected_lane.get("lane_id") or "").strip()
    freshness_constraints = []
    if entry_packet.get("entry_surface_diagnostics"):
        freshness_constraints.append(
            {
                "kind": "entry_surface_diagnostics",
                "value": _compact_mapping(entry_packet["entry_surface_diagnostics"])
                if isinstance(entry_packet["entry_surface_diagnostics"], Mapping)
                else entry_packet["entry_surface_diagnostics"],
            }
        )
    return {
        "seen_surface": "entry",
        "selected_kind": "task_frame",
        "selected_band": "binding",
        "candidate_handles_seen_added": [],
        "focused_handles_added": [],
        "selected_handles_added": [],
        "trusted_authorities_added": [],
        "acted_on_handles_added": [],
        "rejected_handles_added": [],
        "stale_handles_added": [],
        "blocked_handles_added": [],
        "handle_source": None,
        "source_refs_added": source_refs,
        "omissions_added": [
            {
                "omitted": [
                    "full entry packet body",
                    "operator utterance text",
                    "entry diagnostics row bodies",
                ],
                "reason": "Binding records frame identity and next legal move; entry packet remains the evidence surface.",
                "drilldown": command,
            }
        ],
        "freshness_constraints_added": freshness_constraints[:3],
        "mutation_boundary": {},
        "next_legal_moves_added": next_moves[:3],
        "binding": {str(key): value for key, value in binding.items() if value not in (None, "", [], {})},
        "selected_lane_id": selected_lane_id or None,
    }


def _latest_attention_frame_id(events: list[Mapping[str, Any]]) -> str | None:
    for event in reversed(events):
        frame_id = str(event.get("frame_id") or "").strip()
        if frame_id:
            return frame_id
    return None


def _new_attention_frame_id(payload: Mapping[str, Any] | None = None) -> str:
    lens = payload.get("lens_packet") if isinstance(payload, Mapping) and isinstance(payload.get("lens_packet"), Mapping) else {}
    surface = str(lens.get("surface_id") or (payload or {}).get("artifact_kind") or "nav")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"attn_{stamp}_{_short_hash([surface, time.time_ns()], length=10)}"


def read_attention_events(repo_root: Path, *, limit: int | None = None) -> list[dict[str, Any]]:
    path = attention_events_path(repo_root)
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(raw, Mapping):
                rows.append(dict(raw))
    except Exception:
        return []
    if limit is not None and limit > 0:
        return rows[-limit:]
    return rows


def _latest_attention_frame_snapshot_id(repo_root: Path) -> str | None:
    latest_payload = latest_attention_frame_path(repo_root)
    if latest_payload.exists():
        try:
            latest = json.loads(latest_payload.read_text(encoding="utf-8"))
            value = str(latest.get("frame_id") or "").strip() if isinstance(latest, Mapping) else ""
            if value:
                return value
        except Exception:
            return None
    return None


def resolve_attention_frame_id_for_append(
    repo_root: Path,
    frame_id: str | None,
    *,
    payload: Mapping[str, Any] | None = None,
) -> str:
    receipt = resolve_attention_frame_binding_receipt(repo_root, frame_id, mode="append", payload=payload)
    requested = str(receipt.get("requested_frame") or frame_id or "latest")
    if receipt.get("resolution_kind") == "latest" and not receipt.get("resolved_frame_id"):
        return _new_attention_frame_id(payload)
    if receipt.get("resolution_kind") == "binding_alias":
        if receipt.get("status") == "missing_alias":
            raise MissingAttentionFrameBinding(
                f"{requested} did not resolve to an existing AttentionFrame binding."
            )
        if not receipt.get("append_safe"):
            raise AmbiguousAttentionFrameBinding(
                f"{requested} matched {receipt.get('candidate_count')} AttentionFrames; append requires exact frame id or task_frame alias."
            )
    resolved = str(receipt.get("resolved_frame_id") or "").strip()
    return resolved or requested


def resolve_attention_frame_id_for_read(repo_root: Path, frame_id: str | None) -> str | None:
    receipt = resolve_attention_frame_binding_receipt(repo_root, frame_id, mode="read")
    return str(receipt.get("resolved_frame_id") or "").strip() or None


def resolve_attention_frame_id(repo_root: Path, frame_id: str | None, *, payload: Mapping[str, Any] | None = None) -> str:
    return resolve_attention_frame_id_for_append(repo_root, frame_id, payload=payload)


def _attention_event_failure(
    *,
    frame_id: str | None,
    command: str | None,
    error_class: str,
    error: str,
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": ATTENTION_EVENT_SCHEMA_VERSION,
        "status": "failed",
        "generated_at": _now_iso(),
        "session_id": current_session_id(),
        "frame_id": None,
        "frame_id_requested": str(frame_id or "").strip() or None,
        "event_type": "attention_event_failed",
        "command": command,
        "error_class": error_class,
        "error": error,
        "metadata": dict(metadata or {}),
    }


def record_attention_event(
    repo_root: Path,
    *,
    frame_id: str | None = None,
    event_type: str = "surface_seen",
    command: str | None = None,
    payload: Mapping[str, Any] | None = None,
    attention_delta: Mapping[str, Any] | None = None,
    metadata: Mapping[str, Any] | None = None,
    return_error: bool = False,
) -> dict[str, Any] | None:
    """Append one navigation attention event and refresh the derived frame."""
    if not trace_enabled():
        if return_error:
            return _attention_event_failure(
                frame_id=frame_id,
                command=command,
                error_class="AttentionTraceDisabled",
                error=f"{TRACE_DISABLE_ENV} disables navigation attention events.",
                metadata=metadata,
            )
        return None
    try:
        root = repo_root.resolve()
        resolved_frame_id = resolve_attention_frame_id_for_append(root, frame_id, payload=payload)
        if attention_delta:
            delta = dict(attention_delta)
        elif event_type == "mutation_boundary_observed":
            delta = _mutation_boundary_attention_delta(payload or {}, command=command)
        elif event_type == "attention_frame_bound":
            delta = _attention_binding_delta(payload or {}, command=command)
        else:
            delta = _attention_delta_from_payload(payload or {}, command=command)
        generated_at = _now_iso()
        event_hash = _short_hash(
            [
                resolved_frame_id,
                event_type,
                command or "",
                delta.get("seen_surface"),
                delta.get("selected_kind"),
                generated_at,
            ],
            length=18,
        )
        event = {
            "schema_version": ATTENTION_EVENT_SCHEMA_VERSION,
            "status": "appended",
            "event_id": f"attnevt_{int(time.time() * 1000)}_{event_hash[:10]}",
            "generated_at": generated_at,
            "session_id": current_session_id(),
            "frame_id": resolved_frame_id,
            "event_type": event_type,
            "surface_id": delta.get("seen_surface"),
            "view_profile": (payload or {}).get("lens_packet", {}).get("view_profile")
            if isinstance((payload or {}).get("lens_packet"), Mapping)
            else None,
            "binding": delta.get("binding") if isinstance(delta.get("binding"), Mapping) else None,
            "command": command,
            "attention_delta": delta,
            "metadata": dict(metadata or {}),
        }
        out_path = attention_events_path(root)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")
        frame = build_attention_frame(root, frame_id=resolved_frame_id, band="card")
        _write_json(attention_frame_path(root, resolved_frame_id), frame)
        _write_json(latest_attention_frame_path(root), frame)
        return event
    except Exception as exc:
        if return_error:
            return _attention_event_failure(
                frame_id=frame_id,
                command=command,
                error_class=type(exc).__name__,
                error=str(exc),
                metadata=metadata,
            )
        return None


def _no_attention_frame_packet(
    repo_root: Path,
    *,
    requested_frame: str,
    band: str,
    total_event_count: int,
    binding_resolution: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": "kernel.navigation_attention.frame",
        "schema_version": ATTENTION_FRAME_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "status": "no_attention_frame",
        "frame_id": None,
        "requested_frame": requested_frame,
        "band": band,
        "binding_resolution": dict(binding_resolution or {}),
        "authority_posture": "derived_attention_projection; attention_events_are_authority_for_navigation_memory_not_source_truth",
        "source_payload_owner": {
            "authority_plane": "attention_events",
            "events_path": str(attention_events_path(repo_root).relative_to(repo_root)),
            "source_mutation_allowed_by_this_profile": False,
        },
        "summary": {
            "event_count": 0,
            "total_attention_event_count": total_event_count,
        },
        "binding": {},
        "seen_surfaces": [],
        "selected_kinds": [],
        "candidate_handles_seen": [],
        "focused_handles": [],
        "selected_handles": [],
        "trusted_authorities": [],
        "acted_on_handles": [],
        "rejected_handles": [],
        "stale_handles": [],
        "blocked_handles": [],
        "source_refs": [],
        "freshness_constraints": [],
        "mutation_boundary": {},
        "next_legal_moves": [
            {
                "command": "./repo-python kernel.py --option-surface <kind> --band <band> --attention-frame new",
                "reason": "No attention frame exists yet; append a lens packet before trying to resume one.",
            }
        ],
        "omission_receipt": {
            "omitted_count": 0,
            "shown": [],
            "drilldown": None,
        },
        "resumability": {
            "resume_command": None,
            "event_append_hint": "./repo-python kernel.py --option-surface <kind> --band <band> --attention-frame new",
        },
    }


def build_attention_frame(repo_root: Path, *, frame_id: str = "latest", band: str = "flag", limit: int = 80) -> dict[str, Any]:
    root = repo_root.resolve()
    events_all = read_attention_events(root)
    requested_frame = str(frame_id or "latest").strip() or "latest"
    binding_resolution = resolve_attention_frame_binding_receipt(root, requested_frame, mode="read")
    resolved = str(binding_resolution.get("resolved_frame_id") or "").strip() or None
    if not resolved:
        return _no_attention_frame_packet(
            root,
            requested_frame=requested_frame,
            band=band,
            total_event_count=len(events_all),
            binding_resolution=binding_resolution,
        )
    events = [event for event in events_all if str(event.get("frame_id") or "") == resolved]
    events = events[-max(1, int(limit or 80)) :]
    if not events:
        return _no_attention_frame_packet(
            root,
            requested_frame=requested_frame,
            band=band,
            total_event_count=len(events_all),
            binding_resolution=binding_resolution,
        )
    candidate_handles_seen: list[Mapping[str, Any]] = []
    focused_handles: list[Mapping[str, Any]] = []
    selected_handles: list[Mapping[str, Any]] = []
    trusted_authorities: list[Mapping[str, Any]] = []
    acted_on_handles: list[Mapping[str, Any]] = []
    rejected_handles: list[Mapping[str, Any]] = []
    stale_handles: list[Mapping[str, Any]] = []
    blocked_handles: list[Mapping[str, Any]] = []
    source_refs: list[Any] = []
    omissions: list[Any] = []
    freshness_constraints: list[Mapping[str, Any]] = []
    next_moves: list[Mapping[str, Any]] = []
    seen_surfaces: list[str] = []
    selected_kinds: list[str] = []
    mutation_boundary: dict[str, Any] = {}
    binding: dict[str, Any] = {}
    for event in events:
        delta = event.get("attention_delta") if isinstance(event.get("attention_delta"), Mapping) else {}
        event_binding = _binding_from_event(event)
        if event_binding:
            binding.update(event_binding)
        if isinstance(delta.get("binding"), Mapping):
            binding.update({str(key): value for key, value in delta["binding"].items() if value not in (None, "", [], {})})
        seen_surfaces.extend([delta.get("seen_surface")])
        selected_kinds.extend([delta.get("selected_kind")])
        event_type = str(event.get("event_type") or "").strip()
        legacy_selected = [row for row in list(delta.get("selected_handles_added") or []) if isinstance(row, Mapping)]
        explicit_selection_event = event_type in {
            "handle_selected",
            "handles_selected",
            "task_frame_binding",
            "entry_lane_selected",
            "selection_recorded",
        }
        if explicit_selection_event:
            selected_handles.extend(legacy_selected)
        elif legacy_selected:
            if str(delta.get("selected_band") or "").strip().lower() in {"cluster_flag", "cluster", "flag", "list", "index"}:
                candidate_handles_seen.extend(legacy_selected)
            else:
                focused_handles.extend(legacy_selected)
        candidate_handles_seen.extend(
            row for row in list(delta.get("candidate_handles_seen_added") or []) if isinstance(row, Mapping)
        )
        focused_handles.extend(
            row for row in list(delta.get("focused_handles_added") or []) if isinstance(row, Mapping)
        )
        trusted_authorities.extend(
            row for row in list(delta.get("trusted_authorities_added") or []) if isinstance(row, Mapping)
        )
        acted_on_handles.extend(
            row for row in list(delta.get("acted_on_handles_added") or []) if isinstance(row, Mapping)
        )
        rejected_handles.extend(
            row for row in list(delta.get("rejected_handles_added") or []) if isinstance(row, Mapping)
        )
        stale_handles.extend(
            row for row in list(delta.get("stale_handles_added") or []) if isinstance(row, Mapping)
        )
        blocked_handles.extend(
            row for row in list(delta.get("blocked_handles_added") or []) if isinstance(row, Mapping)
        )
        source_refs.extend(delta.get("source_refs_added") or [])
        omissions.extend(delta.get("omissions_added") or [])
        freshness_constraints.extend(
            row for row in list(delta.get("freshness_constraints_added") or []) if isinstance(row, Mapping)
        )
        next_moves.extend(row for row in list(delta.get("next_legal_moves_added") or []) if isinstance(row, Mapping))
        if isinstance(delta.get("mutation_boundary"), Mapping):
            mutation_boundary.update(delta["mutation_boundary"])
    latest = events[-1] if events else {}
    is_flag = band == "flag"
    handle_limit = 3 if is_flag else MAX_ATTENTION_HANDLES
    candidate_handles_out = _attention_handle_output(candidate_handles_seen, limit=handle_limit, compact=is_flag)
    focused_handles_out = _attention_handle_output(focused_handles, limit=handle_limit, compact=is_flag)
    selected_handles_out = _attention_handle_output(selected_handles, limit=handle_limit, compact=is_flag)
    trusted_authorities_out = _attention_handle_output(trusted_authorities, limit=handle_limit, compact=is_flag)
    acted_on_handles_out = _attention_handle_output(acted_on_handles, limit=handle_limit, compact=is_flag)
    rejected_handles_out = _attention_handle_output(rejected_handles, limit=handle_limit, compact=is_flag)
    stale_handles_out = _attention_handle_output(stale_handles, limit=handle_limit, compact=is_flag)
    blocked_handles_out = _attention_handle_output(blocked_handles, limit=handle_limit, compact=is_flag)
    next_moves_out = _unique_by_key(next_moves, "command", limit=3 if is_flag else 16)
    payload: dict[str, Any] = {
        "kind": "kernel.navigation_attention.frame",
        "schema_version": ATTENTION_FRAME_SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "status": "ok",
        "frame_id": resolved,
        "requested_frame": requested_frame,
        "band": band,
        "binding_resolution": binding_resolution,
        "authority_posture": "derived_attention_projection; attention_events_are_authority_for_navigation_memory_not_source_truth",
        "source_payload_owner": {
            "authority_plane": "attention_events",
            "events_path": str(attention_events_path(root).relative_to(root)),
            "source_mutation_allowed_by_this_profile": False,
        },
        "summary": {
            "event_count": len(events),
            "total_attention_event_count": len(events_all),
            "latest_event_id": latest.get("event_id") if isinstance(latest, Mapping) else None,
            "latest_event_at": latest.get("generated_at") if isinstance(latest, Mapping) else None,
            "candidate_handle_count": len(_unique_by_key(candidate_handles_seen, "handle", limit=10_000)),
            "focused_handle_count": len(_unique_by_key(focused_handles, "handle", limit=10_000)),
            "selected_handle_count": len(_unique_by_key(selected_handles, "handle", limit=10_000)),
            "binding_count": len(binding),
        },
        "binding": binding,
        "seen_surfaces": _unique_strings(seen_surfaces, limit=8 if band == "flag" else 20),
        "selected_kinds": _unique_strings(selected_kinds, limit=8 if band == "flag" else 20),
        "candidate_handles_seen": candidate_handles_out,
        "focused_handles": focused_handles_out,
        "selected_handles": selected_handles_out,
        "trusted_authorities": trusted_authorities_out,
        "acted_on_handles": acted_on_handles_out,
        "rejected_handles": rejected_handles_out,
        "stale_handles": stale_handles_out,
        "blocked_handles": blocked_handles_out,
        "source_refs": _unique_strings(source_refs, limit=4 if band == "flag" else 20),
        "freshness_constraints": list(freshness_constraints)[:3 if band == "flag" else 12],
        "mutation_boundary": mutation_boundary,
        "next_legal_moves": next_moves_out,
        "omission_receipt": {
            "omitted_count": len(omissions) if is_flag else max(0, len(omissions) - 12),
            "shown": [] if is_flag else omissions[:12],
            "drilldown": f"./repo-python kernel.py --attention-state {resolved} --band card",
        },
        "resumability": {
            "resume_command": f"./repo-python kernel.py --attention-state {resolved} --band flag",
            "event_append_hint": f"./repo-python kernel.py --option-surface <kind> --band <band> --attention-frame {resolved}",
            "binding_resume_commands": [
                {
                    "command": f"./repo-python kernel.py --attention-state task_frame:{binding['task_frame_id']} --band flag",
                    "reason": "Resume by TaskFrame identity.",
                }
                if binding.get("task_frame_id")
                else None,
                {
                    "command": f"./repo-python kernel.py --attention-state work_item:{binding['work_item_id']} --band flag",
                    "reason": "Resume by WorkItem identity.",
                }
                if binding.get("work_item_id")
                else None,
                {
                    "command": f"./repo-python kernel.py --attention-state phase:{binding['phase_id']} --band flag",
                    "reason": "Resume by active phase identity.",
                }
                if binding.get("phase_id")
                else None,
                {
                    "command": f"./repo-python kernel.py --attention-state session:{binding['actor_session_id']} --band flag",
                    "reason": "Resume by actor session identity.",
                }
                if binding.get("actor_session_id")
                else None,
            ],
        },
    }
    payload["resumability"]["binding_resume_commands"] = [
        row for row in payload["resumability"]["binding_resume_commands"] if row
    ][:4]
    if band != "flag":
        payload["events"] = [
            {
                "event_id": event.get("event_id"),
                "generated_at": event.get("generated_at"),
                "surface_id": event.get("surface_id"),
                "command": event.get("command"),
                "attention_delta": event.get("attention_delta"),
            }
            for event in events[-20:]
        ]
    return payload


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)
