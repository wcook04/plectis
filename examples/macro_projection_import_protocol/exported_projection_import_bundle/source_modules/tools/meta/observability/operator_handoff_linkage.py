#!/usr/bin/env python3
"""Operator Handoff Linkage v0 — join Type B captures to Type A user inputs.

Reads:
  state/prompt_shelf/prompt_shelf_runs_index.json    # Type B captures (assistant turns)
  obsidian/prompt_shelf/usage/raw_events/<slot>/*.json # full assistant raw_text per run
  codex/hologram/process/ledger.json                 # Type A session list (claude + codex)
  ~/.claude/projects/<slug>/*.jsonl                  # Claude rollouts (raw user inputs)
  ~/.codex/sessions/<Y>/<M>/<D>/rollout-*.jsonl      # Codex rollouts (raw user inputs)

Emits scored candidate Type B → Type A handoff edges using existing primitives
from prompt_shelf_fingerprints (_normalize, _index_preserving_normalize,
_anchor_position, _tokenize). No new fuzzy dependency. Semantic embedding is
deferred to v1+.

Confidence bands: strong | tentative | ambiguous | none.
Direction: typeb_to_typea (operator pasted ChatGPT response into Claude/Codex).

CLI:
  operator_handoff_linkage.py --print [--limit N] [--session-limit M]
  operator_handoff_linkage.py --write-projection [--limit N] [--session-limit M]

Output (when --write-projection):
  state/operator_bridge/handoff_linkage_projection.json
  state/operator_bridge/handoff_linkage_diagnostics.json
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

REPO_ROOT = Path(__file__).resolve().parents[3]

# Reuse existing matching primitives — do not import RapidFuzz / SimHash / MinHash for v0.
sys.path.insert(0, str(REPO_ROOT / "tools" / "meta" / "observability"))
from prompt_shelf_fingerprints import (  # noqa: E402
    _anchor_position,
    _index_preserving_normalize,
    _normalize,
    _tokenize,
)

PROMPT_SHELF_RUNS_INDEX = REPO_ROOT / "state" / "prompt_shelf" / "prompt_shelf_runs_index.json"
CAPTURE_DIAGNOSTICS_DIR = REPO_ROOT / "state" / "prompt_shelf" / "capture_diagnostics"
EXECUTION_TRACE_LEDGER = REPO_ROOT / "codex" / "hologram" / "process" / "ledger.json"
PROJECTION_PATH = REPO_ROOT / "state" / "operator_bridge" / "handoff_linkage_projection.json"
DIAGNOSTICS_PATH = REPO_ROOT / "state" / "operator_bridge" / "handoff_linkage_diagnostics.json"

SCHEMA_VERSION = "operator_handoff_linkage_projection_v0"
STATUS_SCHEMA_VERSION = "operator_handoff_linkage_status_v0"

ASSISTANT_ANCHOR_PREFIX_CHARS = 200
DEFAULT_TYPEB_LIMIT = 50
DEFAULT_TYPEA_SESSION_LIMIT = 20
TIME_WINDOW_HOURS_DEFAULT = 48
SOFT_FEED_MIN_ASSISTANT_CHARS = 200  # ignore streaming/empty diagnostic snapshots
# Tight temporal coupling = paste landed within the forward window (capture → paste)
# or within the observer lag tolerance (paste appeared just before observer wrote the
# diagnostic; observer is a polling client, not synchronous).
TIGHT_TIME_FORWARD_SECONDS = 120
TIGHT_TIME_BACKWARD_TOLERANCE_SECONDS = 30
# Composite-evidence thresholds for confidence bumping. Independent strong signals
# (anchor match + high token overlap + tight temporal coupling) jointly justify lifting
# above ambiguous even when containment is False, because the soft observation may be
# only a prefix of the actual response.
COMPOSITE_TENTATIVE_JACCARD = 0.90
COMPOSITE_AMBIGUOUS_JACCARD = 0.80
SOFT_SELECTION_POLICY = "prefer_not_generating_then_longest_then_latest"

# Score weights and thresholds — single place for v0 tuning.
SCORE_WEIGHT_CONTAINMENT = 0.50
SCORE_WEIGHT_ANCHOR = 0.20
SCORE_WEIGHT_JACCARD = 0.20
SCORE_WEIGHT_TIME_PROXIMITY = 0.10

CONFIDENCE_STRONG = 0.80
CONFIDENCE_TENTATIVE = 0.55
CONFIDENCE_AMBIGUOUS = 0.30


# ---------- data shapes ----------


@dataclass
class TypeBCapture:
    prompt_run_id: str
    prompt_slot: str
    prompt_slug: str
    captured_at: str
    conversation_id: str
    conversation_url: str
    assistant_sha256: str
    assistant_raw_text: str
    # Source feed: "prompt_shelf_run" = curated capture (passed up-propagation gate);
    # "capture_diagnostic" = soft observation feed (assistant turn observed by chatgpt
    # observer regardless of capture eligibility — primary feed for handoff linkage).
    source: str = "prompt_shelf_run"
    capture_status: str = "captured"
    skipped_reason: str | None = None
    tab_title: str | None = None
    user_turn_index: int | None = None
    assistant_turn_index: int | None = None
    # Source completeness: "complete" (curated, full assistant text by construction);
    # "best_observed_in_group" (soft, observer re-emitted multiple snapshots for this
    # turn and we picked the best one); "partial_or_unknown" (soft, only one snapshot
    # so we cannot tell if it is the final assistant text or a partial stream).
    source_completeness: str = "complete"
    soft_observation_count: int = 1

    @property
    def captured_at_dt(self) -> _dt.datetime | None:
        return _parse_iso(self.captured_at)


@dataclass
class TypeAUserInput:
    surface: str  # "claude_code" | "codex"
    session_id: str
    session_started_at: str | None
    session_ended_at: str | None
    source_path: str
    cwd: str | None
    timestamp: str | None
    raw_text: str
    turn_uuid: str | None = None

    @property
    def timestamp_dt(self) -> _dt.datetime | None:
        return _parse_iso(self.timestamp)


@dataclass
class EdgeEvidence:
    exact_hash_match: bool
    containment: bool
    anchor_match: bool
    anchor_position: int | None
    token_overlap: float
    time_delta_seconds: int | None
    operator_delta_detected: bool
    competing_candidate_count: int = 0
    top_candidate_gap: float = 0.0
    # Tight temporal coupling fields (independent positive evidence, not just decay).
    # tight_time_coupling: -30 <= delta <= 120 (forward window plus observer lag tolerance)
    # forward_time_coupling: 0 <= delta <= 120 (paste happened after capture)
    # observer_lag_tolerated: -30 <= delta < 0 (paste appeared before capture write — observer poll lag)
    tight_time_coupling: bool = False
    forward_time_coupling: bool = False
    observer_lag_tolerated: bool = False


@dataclass
class OperatorDeltaSummary:
    position: str  # "prefix" | "suffix" | "interleaved" | "none" | "unknown"
    chars: int
    # reliability:
    #   "likely_operator_delta" — source feed is complete (curated raw event, or soft
    #   capture with containment); the observed extra is operator-authored.
    #   "uncertain_source_may_be_partial" — soft capture without containment;
    #   suffix may be operator delta OR unobserved Type B tail.
    #   "unknown" — anchor/containment not established.
    reliability: str = "unknown"
    # source_relation: when the soft observation is detected as a prefix of the Type A
    # paste, this names that relationship explicitly so downstream readers know
    # operator_delta.chars overlaps with possibly-unobserved source tail.
    source_relation: str | None = None


@dataclass
class CandidateEdge:
    edge_id: str
    confidence_band: str
    score: float
    direction: str
    type_b: dict[str, Any]
    type_a: dict[str, Any]
    evidence: EdgeEvidence
    operator_delta_summary: OperatorDeltaSummary

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "confidence_band": self.confidence_band,
            "score": round(self.score, 4),
            "direction": self.direction,
            "type_b": self.type_b,
            "type_a": self.type_a,
            "evidence": {
                "exact_hash_match": self.evidence.exact_hash_match,
                "containment": self.evidence.containment,
                "anchor_match": self.evidence.anchor_match,
                "anchor_position": self.evidence.anchor_position,
                "token_overlap": round(self.evidence.token_overlap, 4),
                "time_delta_seconds": self.evidence.time_delta_seconds,
                "tight_time_coupling": self.evidence.tight_time_coupling,
                "forward_time_coupling": self.evidence.forward_time_coupling,
                "observer_lag_tolerated": self.evidence.observer_lag_tolerated,
                "operator_delta_detected": self.evidence.operator_delta_detected,
                "competing_candidate_count": self.evidence.competing_candidate_count,
                "top_candidate_gap": round(self.evidence.top_candidate_gap, 4),
            },
            "operator_delta_summary": {
                "position": self.operator_delta_summary.position,
                "chars": self.operator_delta_summary.chars,
                "reliability": self.operator_delta_summary.reliability,
                "source_relation": self.operator_delta_summary.source_relation,
            },
        }


# ---------- helpers ----------


def _parse_iso(value: str | None) -> _dt.datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return _dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _now_iso() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text())


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


# ---------- Type B side ----------


def load_typeb_captures(
    *,
    runs_index_path: Path = PROMPT_SHELF_RUNS_INDEX,
    repo_root: Path = REPO_ROOT,
    limit: int = DEFAULT_TYPEB_LIMIT,
) -> list[TypeBCapture]:
    """Load most-recent curated Type B captures from prompt_shelf_runs_index.

    Curated source: only runs that passed the prompt-shelf capture gate (e.g. complete
    up-propagation block). Use load_typeb_capture_diagnostics for the soft observation
    lane that includes skipped pairs.
    """
    if not runs_index_path.exists():
        return []
    try:
        payload = _load_json(runs_index_path)
    except (OSError, json.JSONDecodeError):
        return []
    runs = payload.get("runs") or []
    runs_sorted = sorted(runs, key=lambda r: r.get("captured_at", ""), reverse=True)
    out: list[TypeBCapture] = []
    for run in runs_sorted:
        if len(out) >= limit:
            break
        raw_event_rel = run.get("raw_event_path")
        if not raw_event_rel:
            continue
        raw_event_path = repo_root / raw_event_rel
        if not raw_event_path.exists():
            continue
        try:
            rep = _load_json(raw_event_path)
        except (OSError, json.JSONDecodeError):
            continue
        assistant = rep.get("assistant_message") or {}
        assistant_text = assistant.get("raw_text") or ""
        if not assistant_text:
            continue
        out.append(TypeBCapture(
            prompt_run_id=run.get("prompt_run_id") or "",
            prompt_slot=run.get("prompt_slot") or "",
            prompt_slug=run.get("prompt_slug") or "",
            captured_at=run.get("captured_at") or "",
            conversation_id=run.get("conversation_id") or "",
            conversation_url=run.get("conversation_url") or "",
            assistant_sha256=assistant.get("sha256") or run.get("assistant_message_sha256") or "",
            assistant_raw_text=assistant_text,
            source="prompt_shelf_run",
            capture_status="captured",
            user_turn_index=run.get("user_turn_index"),
            assistant_turn_index=run.get("assistant_turn_index"),
        ))
    return out


def load_typeb_capture_diagnostics(
    *,
    diagnostics_dir: Path = CAPTURE_DIAGNOSTICS_DIR,
    limit: int = DEFAULT_TYPEB_LIMIT,
    min_assistant_chars: int = SOFT_FEED_MIN_ASSISTANT_CHARS,
) -> list[TypeBCapture]:
    """Load most-recent assistant-turn observations from prompt-shelf capture_diagnostics.

    Soft / low-authority feed: every chatgpt-observer sweep that detected a B-lane prompt
    pair but skipped capture (e.g. assistant_missing_complete_uppropagation_block) writes
    a per-pair JSON here with the full assistant_text. This is the right feed for handoff
    linkage because it does not require capture eligibility, only that the observer saw
    an assistant turn.

    The observer re-emits diagnostics for the same (conversation_id, assistant_turn_index,
    slot) as the assistant turn streams to completion — observed group sizes go up to ~9.
    Within each group we pick the most informative snapshot using SOFT_SELECTION_POLICY:
    snapshot_generating == False, then largest assistant_shape.char_count, then latest
    created_at. The selected record's source_completeness is "best_observed_in_group" if
    multiple records exist (we have evidence of completion), else "partial_or_unknown"
    (single observation; we cannot tell whether the assistant turn was complete).

    Filters out streaming/empty snapshots where assistant text is below
    min_assistant_chars — those carry no usable matching signal.
    """
    if not diagnostics_dir.is_dir():
        return []
    raw_records: list[tuple[float, Path, dict[str, Any]]] = []
    for f in diagnostics_dir.glob("*.json"):
        try:
            mtime = f.stat().st_mtime
            rec = _load_json(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rec, dict) or rec.get("kind") != "prompt_shelf_capture_diagnostic":
            continue
        raw_records.append((mtime, f, rec))

    # Group by (conversation_id, assistant_turn_index, slot).
    groups: dict[tuple[str, int | None, str], list[tuple[float, Path, dict[str, Any]]]] = {}
    for entry in raw_records:
        rec = entry[2]
        key = (
            rec.get("conversation_id") or "",
            rec.get("assistant_turn_index"),
            rec.get("slot") or "",
        )
        groups.setdefault(key, []).append(entry)

    selected: list[TypeBCapture] = []
    for key, members in groups.items():
        # Selection: prefer snapshot_generating==False, then largest assistant char count,
        # then latest created_at as final tiebreaker.
        def _rank(item: tuple[float, Path, dict[str, Any]]) -> tuple[int, int, str]:
            mtime, _path, rec = item
            shape = rec.get("assistant_shape") or {}
            generating = bool(rec.get("snapshot_generating"))
            chars = int(shape.get("char_count", 0) or 0)
            created_at = str(rec.get("created_at") or "")
            return (
                0 if not generating else 1,  # non-generating ranks first (smaller key wins after reverse)
                -chars,                        # negate so largest comes first
                # Latest created_at wins; sorted ascending so we'll reverse-key it below.
                # Use mtime as float-encoded fallback.
                _negated_iso(created_at, mtime),
            )
        members_sorted = sorted(members, key=_rank)
        best_mtime, best_path, best_rec = members_sorted[0]

        assistant_text = best_rec.get("assistant_text") or ""
        assistant_shape = best_rec.get("assistant_shape") or {}
        char_count = int(assistant_shape.get("char_count", len(assistant_text)) or 0)
        if char_count < min_assistant_chars:
            continue

        completeness = "best_observed_in_group" if len(members) > 1 else "partial_or_unknown"
        selected.append(TypeBCapture(
            prompt_run_id=f"capdiag::{best_path.stem}",
            prompt_slot=best_rec.get("slot") or "",
            prompt_slug="capture_diagnostic",
            captured_at=best_rec.get("created_at") or "",
            conversation_id=best_rec.get("conversation_id") or "",
            conversation_url=best_rec.get("conversation_url") or "",
            assistant_sha256=assistant_shape.get("sha256") or "",
            assistant_raw_text=assistant_text,
            source="capture_diagnostic",
            capture_status="skipped" if best_rec.get("skipped_reason") else "observed",
            skipped_reason=best_rec.get("skipped_reason"),
            tab_title=best_rec.get("tab_title"),
            user_turn_index=best_rec.get("user_turn_index"),
            assistant_turn_index=best_rec.get("assistant_turn_index"),
            source_completeness=completeness,
            soft_observation_count=len(members),
        ))

    selected.sort(key=lambda c: c.captured_at or "", reverse=True)
    return selected[:limit]


def _negated_iso(iso: str, fallback_mtime: float) -> str:
    """Return a string key whose lexical sort places the latest iso first.

    Used by the soft-feed selection rank where the rest of the tuple uses smallest-wins;
    we want largest-iso to win, so negate via the trivial transform of inverting char codes
    against a fixed sentinel.
    """
    if iso:
        # Lexical inversion: build a string where larger originals sort smaller.
        return "".join(chr(0x10FFFF - ord(c)) if ord(c) < 0x10FFFF else c for c in iso)
    # Fallback: encode mtime so larger mtime sorts smaller via negation.
    return f"~mtime~{1e15 - fallback_mtime:.6f}"


def load_typeb_records(
    *,
    runs_index_path: Path = PROMPT_SHELF_RUNS_INDEX,
    diagnostics_dir: Path = CAPTURE_DIAGNOSTICS_DIR,
    repo_root: Path = REPO_ROOT,
    limit: int = DEFAULT_TYPEB_LIMIT,
    use_soft_feed: bool = True,
) -> list[TypeBCapture]:
    """Merge curated runs + soft capture_diagnostics, dedupe by assistant_sha256, cap to limit.

    Default is soft-feed-first because handoff linkage cares about every observed Type B
    assistant turn, not only ones the prompt-shelf gate accepted. Curated entries supersede
    soft entries when sha256 collides (curated is higher authority).
    """
    soft = load_typeb_capture_diagnostics(diagnostics_dir=diagnostics_dir, limit=limit) if use_soft_feed else []
    curated = load_typeb_captures(runs_index_path=runs_index_path, repo_root=repo_root, limit=limit)
    by_sha: dict[str, TypeBCapture] = {}
    for cap in soft:
        if cap.assistant_sha256:
            by_sha[cap.assistant_sha256] = cap
        else:
            by_sha[cap.prompt_run_id] = cap
    for cap in curated:
        # Curated supersedes soft for the same assistant sha; preserve any soft tab metadata.
        key = cap.assistant_sha256 or cap.prompt_run_id
        prior = by_sha.get(key)
        if prior is not None and prior.source == "capture_diagnostic":
            cap.tab_title = cap.tab_title or prior.tab_title
        by_sha[key] = cap
    merged = list(by_sha.values())
    merged.sort(key=lambda c: c.captured_at or "", reverse=True)
    return merged[:limit]


# ---------- Type A side ----------


def _extract_claude_user_text(message: Any) -> str:
    """Claude rollouts: message.content is str OR list of dicts with 'text'/'type'."""
    if isinstance(message, str):
        return message
    if not isinstance(message, dict):
        return ""
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                kind = item.get("type")
                if kind in ("text", "input_text"):
                    parts.append(item.get("text") or "")
        return "\n\n".join(p for p in parts if p)
    return ""


def _extract_codex_user_text(payload: Any) -> str:
    """Codex rollouts: payload.content is list of {type:'input_text', text:...}."""
    if not isinstance(payload, dict):
        return ""
    content = payload.get("content")
    if not isinstance(content, list):
        return ""
    parts: list[str] = []
    for item in content:
        if isinstance(item, dict):
            kind = item.get("type")
            if kind in ("input_text", "text"):
                parts.append(item.get("text") or "")
    return "\n\n".join(p for p in parts if p)


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue
    except OSError:
        return


def parse_claude_user_inputs(rollout_path: Path, *, session_id: str, started_at: str | None, ended_at: str | None) -> list[TypeAUserInput]:
    out: list[TypeAUserInput] = []
    cwd: str | None = None
    for rec in _iter_jsonl(rollout_path):
        if rec.get("cwd") and not cwd:
            cwd = rec.get("cwd")
        if rec.get("type") != "user":
            continue
        text = _extract_claude_user_text(rec.get("message"))
        if not text or not text.strip():
            continue
        out.append(TypeAUserInput(
            surface="claude_code",
            session_id=session_id,
            session_started_at=started_at,
            session_ended_at=ended_at,
            source_path=str(rollout_path),
            cwd=cwd,
            timestamp=rec.get("timestamp"),
            raw_text=text,
            turn_uuid=rec.get("uuid"),
        ))
    return out


def parse_codex_user_inputs(rollout_path: Path, *, session_id: str, started_at: str | None, ended_at: str | None) -> list[TypeAUserInput]:
    out: list[TypeAUserInput] = []
    cwd: str | None = None
    for rec in _iter_jsonl(rollout_path):
        if rec.get("type") == "session_meta":
            payload = rec.get("payload") or {}
            cwd = cwd or payload.get("cwd")
            continue
        if rec.get("type") != "response_item":
            continue
        payload = rec.get("payload") or {}
        if payload.get("type") != "message":
            continue
        if payload.get("role") != "user":
            continue
        text = _extract_codex_user_text(payload)
        if not text or not text.strip():
            continue
        out.append(TypeAUserInput(
            surface="codex",
            session_id=session_id,
            session_started_at=started_at,
            session_ended_at=ended_at,
            source_path=str(rollout_path),
            cwd=cwd,
            timestamp=rec.get("timestamp"),
            raw_text=text,
            turn_uuid=None,
        ))
    return out


def _claude_project_slug_for_cwd(cwd: Path) -> str:
    """Mirror ~/.claude/projects/<slug>/ slug encoding.

    Encoding parity with system/lib/agent_execution_trace.py::_claude_project_slug:
    slashes and underscores both become hyphens, with a single leading hyphen.
    Example: /Users/example/src/ai_workflow → -Users-willcook-src-ai-workflow.
    """
    return "-" + str(cwd).replace("/", "-").lstrip("-").replace("_", "-")


def _peek_codex_cwd(rollout: Path) -> str | None:
    """Read just the session_meta line of a Codex rollout to extract cwd; cheap O(1)."""
    try:
        with rollout.open("r", encoding="utf-8", errors="replace") as fh:
            for _ in range(20):
                line = fh.readline()
                if not line:
                    return None
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if rec.get("type") == "session_meta":
                    return (rec.get("payload") or {}).get("cwd")
    except OSError:
        return None
    return None


def _discover_recent_rollouts(
    *,
    session_limit: int,
    repo_root: Path = REPO_ROOT,
    include_all_rollouts: bool = False,
) -> list[tuple[str, Path, str]]:
    """Fallback: discover recent rollouts directly from ~/.claude and ~/.codex.

    Filters to rollouts owned by the active repo cwd unless include_all_rollouts is True:
    - Claude: project directory slug == _claude_project_slug_for_cwd(repo_root).
    - Codex: session_meta.payload.cwd == str(repo_root).

    Without this filter, sibling Claude projects (e.g. memory-observer or other repos) and
    cross-repo Codex sessions swamp scoring with shared-substrate vocabulary near-misses.
    """
    home = Path.home()
    rollouts: list[tuple[float, str, Path, str]] = []
    expected_claude_slug = _claude_project_slug_for_cwd(repo_root)
    expected_codex_cwd = str(repo_root)

    claude_root = home / ".claude" / "projects"
    if claude_root.is_dir():
        for proj_dir in claude_root.iterdir():
            if not proj_dir.is_dir():
                continue
            if not include_all_rollouts and proj_dir.name != expected_claude_slug:
                continue
            for f in proj_dir.glob("*.jsonl"):
                try:
                    rollouts.append((f.stat().st_mtime, "claude_code", f, f.stem))
                except OSError:
                    continue

    codex_root = home / ".codex" / "sessions"
    if codex_root.is_dir():
        codex_files: list[tuple[float, Path]] = []
        for f in codex_root.glob("**/rollout-*.jsonl"):
            try:
                codex_files.append((f.stat().st_mtime, f))
            except OSError:
                continue
        # Sort by mtime first, then peek cwd to filter — bounds the cwd-peek cost to the most
        # recent files we'd consider anyway.
        codex_files.sort(reverse=True)
        peek_budget = max(session_limit * 3, 60) if not include_all_rollouts else 10000
        for _mtime, f in codex_files[:peek_budget]:
            if not include_all_rollouts:
                cwd = _peek_codex_cwd(f)
                if cwd != expected_codex_cwd:
                    continue
            try:
                stem = f.stem
                rollouts.append((f.stat().st_mtime, "codex", f, stem.replace("rollout-", "", 1)))
            except OSError:
                continue
    rollouts.sort(reverse=True)
    return [(agent, path, sid) for _mtime, agent, path, sid in rollouts[:session_limit]]


def load_typea_user_inputs(
    *,
    ledger_path: Path = EXECUTION_TRACE_LEDGER,
    session_limit: int = DEFAULT_TYPEA_SESSION_LIMIT,
    repo_root: Path = REPO_ROOT,
    include_all_rollouts: bool = False,
) -> list[TypeAUserInput]:
    """Load recent Type A user inputs.

    Primary path: read execution trace ledger for the session list (agent + source_path +
    started_at + ended_at), then parse rollouts. Fallback: when the ledger is missing or
    empty (it is a generated sidecar that other builders can clear or rebuild), discover
    rollouts directly from ~/.claude/projects/* and ~/.codex/sessions/*, filtered to the
    repo cwd unless include_all_rollouts is True.
    """
    sessions: list[tuple[str, Path, str, str | None, str | None]] = []
    if ledger_path.exists():
        try:
            ledger = _load_json(ledger_path)
        except (OSError, json.JSONDecodeError):
            ledger = {}
        ledger_sessions = ledger.get("sessions") or []
        ledger_sessions = sorted(
            ledger_sessions,
            key=lambda s: s.get("ended_at") or s.get("started_at") or "",
            reverse=True,
        )[:session_limit]
        for s in ledger_sessions:
            sp = s.get("source_path") or ""
            if not sp:
                continue
            rollout = Path(sp)
            if not rollout.exists():
                continue
            sessions.append((
                s.get("agent") or "",
                rollout,
                s.get("session_id") or "",
                s.get("started_at"),
                s.get("ended_at"),
            ))
    if not sessions:
        for agent, rollout, sid in _discover_recent_rollouts(
            session_limit=session_limit,
            repo_root=repo_root,
            include_all_rollouts=include_all_rollouts,
        ):
            sessions.append((agent, rollout, sid, None, None))

    out: list[TypeAUserInput] = []
    for agent, rollout, session_id, started_at, ended_at in sessions:
        # Execution trace ledger uses agent labels "claude_code" and "codex"; tolerate "claude" for safety.
        if agent in ("claude_code", "claude"):
            out.extend(parse_claude_user_inputs(
                rollout,
                session_id=session_id,
                started_at=started_at,
                ended_at=ended_at,
            ))
        elif agent == "codex":
            out.extend(parse_codex_user_inputs(
                rollout,
                session_id=session_id,
                started_at=started_at,
                ended_at=ended_at,
            ))
    return out


# ---------- scoring ----------


def _classify_operator_delta(
    typea_raw: str,
    assistant_raw: str,
    anchor_position: int | None,
    *,
    typeb_source: str = "prompt_shelf_run",
    typeb_completeness: str = "complete",
    containment: bool = False,
) -> OperatorDeltaSummary:
    """Classify operator delta in `_index_preserving_normalize` coordinates.

    `anchor_position` is the start of the assistant text inside the lowercased
    typea text; both `typea_raw` and `assistant_raw` are length-preserved by the
    1:1 normalization, so we can use raw-text lengths here.

    Reliability tagging:
      - curated source OR (soft + containment) → "likely_operator_delta": the source
        feed is known complete (or contains the full assistant text), so suffix/prefix
        text is operator-authored.
      - soft + no containment + suffix → "uncertain_source_may_be_partial": the
        observation may be only a prefix of the actual assistant turn; the suffix
        text could be operator-added OR unobserved Type B tail. Caller must not
        treat operator_delta_summary as proof of operator authorship.
    """
    if anchor_position is None:
        return OperatorDeltaSummary(position="unknown", chars=0, reliability="unknown")
    typea_len = len(typea_raw)
    assistant_len = len(assistant_raw)
    extra_before = anchor_position
    after_anchor = max(0, typea_len - anchor_position - assistant_len)

    soft_partial = (
        typeb_source == "capture_diagnostic"
        and not containment
        and typeb_completeness != "complete"
    )

    if extra_before <= 4 and after_anchor <= 4:
        position, chars = "none", extra_before + after_anchor
    elif extra_before <= 4 and after_anchor > 4:
        position, chars = "suffix", after_anchor
    elif extra_before > 4 and after_anchor <= 4:
        position, chars = "prefix", extra_before
    else:
        position, chars = "interleaved", extra_before + after_anchor

    if position == "none":
        reliability = "likely_operator_delta" if not soft_partial else "uncertain_source_may_be_partial"
        source_relation = None
    elif position == "suffix" and soft_partial:
        reliability = "uncertain_source_may_be_partial"
        source_relation = "observed_source_prefix_of_typea_input"
    elif position == "prefix" and soft_partial:
        # Prefix-on-soft is also uncertain; could be operator preamble OR previous turn material.
        reliability = "uncertain_source_may_be_partial"
        source_relation = None
    elif position == "interleaved" and soft_partial:
        reliability = "uncertain_source_may_be_partial"
        source_relation = None
    else:
        reliability = "likely_operator_delta"
        source_relation = None

    return OperatorDeltaSummary(
        position=position,
        chars=chars,
        reliability=reliability,
        source_relation=source_relation,
    )


def _time_proximity_score(
    captured_at: _dt.datetime | None,
    typea_ts: _dt.datetime | None,
    *,
    window_hours: float = TIME_WINDOW_HOURS_DEFAULT,
) -> tuple[float, int | None]:
    if not captured_at or not typea_ts:
        return 0.0, None
    delta = (typea_ts - captured_at).total_seconds()
    delta_int = int(delta)
    if delta < 0:
        # Type A input came before Type B capture — probably not a paste of this response.
        return 0.0, delta_int
    window_s = window_hours * 3600.0
    if delta > window_s:
        return 0.0, delta_int
    # Linear decay 1.0 → 0.0 across the window.
    return max(0.0, 1.0 - delta / window_s), delta_int


_NORM_CACHE: dict[tuple[int, int], tuple[str, set[str], str]] = {}


def _clear_norm_cache() -> None:
    """Public test hook: clear the per-process normalization cache."""
    _NORM_CACHE.clear()


def _cached_norms(text: str) -> tuple[str, set[str], str]:
    """Return (collapsed-whitespace lowercased, token set, index-preserving lowercased) for a text.

    Cached by (id(text), len(text)) — every TypeBCapture and TypeAUserInput holds a stable
    raw text string, so this avoids recomputing normalizations across the score_pair
    O(captures * inputs) loop. The length component guards against id() reuse after GC,
    which can otherwise return stale cached entries from a previous test or pass.
    """
    key = (id(text), len(text))
    cached = _NORM_CACHE.get(key)
    if cached is not None:
        return cached
    norm = _normalize(text)
    tokens = _tokenize(norm)
    idx_norm = _index_preserving_normalize(text)
    cached = (norm, tokens, idx_norm)
    _NORM_CACHE[key] = cached
    return cached


def score_pair(typeb: TypeBCapture, typea: TypeAUserInput) -> tuple[float, EdgeEvidence, OperatorDeltaSummary]:
    assistant_norm, typeb_tokens, anchor_normalized_full = _cached_norms(typeb.assistant_raw_text)
    typea_norm, typea_tokens, _ = _cached_norms(typea.raw_text)

    if not assistant_norm or not typea_norm:
        ev = EdgeEvidence(
            exact_hash_match=False,
            containment=False,
            anchor_match=False,
            anchor_position=None,
            token_overlap=0.0,
            time_delta_seconds=None,
            operator_delta_detected=False,
        )
        return 0.0, ev, OperatorDeltaSummary(position="unknown", chars=0)

    exact_hash_match = typeb.assistant_raw_text.strip() == typea.raw_text.strip()
    containment = assistant_norm in typea_norm
    # Anchor is taken from the index-preserving (case-folded, length-preserved) form of the
    # assistant text so the search inside _anchor_position lands case-correctly while keeping
    # anchor_pos interpretable as raw-text coordinates for operator-delta classification.
    anchor_prefix = anchor_normalized_full[:ASSISTANT_ANCHOR_PREFIX_CHARS]
    anchor_pos = _anchor_position(typea.raw_text, anchor_prefix)
    anchor_match = anchor_pos is not None

    overlap = 0.0
    if typeb_tokens and typea_tokens:
        intersect = len(typeb_tokens & typea_tokens)
        overlap = intersect / float(len(typeb_tokens))

    time_score, time_delta = _time_proximity_score(typeb.captured_at_dt, typea.timestamp_dt)

    score = 0.0
    if containment or exact_hash_match:
        score += SCORE_WEIGHT_CONTAINMENT
    if anchor_match:
        score += SCORE_WEIGHT_ANCHOR
    score += SCORE_WEIGHT_JACCARD * min(1.0, overlap)
    score += SCORE_WEIGHT_TIME_PROXIMITY * time_score
    if exact_hash_match:
        score = max(score, 0.99)

    # Tight temporal coupling: paste landed within seconds of the capture, or just
    # before the capture due to observer-poll lag. This is independent positive
    # evidence, not a continuous decay weight.
    forward_time = (
        time_delta is not None
        and 0 <= time_delta <= TIGHT_TIME_FORWARD_SECONDS
    )
    observer_lag = (
        time_delta is not None
        and -TIGHT_TIME_BACKWARD_TOLERANCE_SECONDS <= time_delta < 0
    )
    tight_time = forward_time or observer_lag

    # Composite-evidence calibration: when the source feed may be partial (soft capture
    # without containment) but anchor + high token overlap + tight time triangulate
    # independently, the weighted-sum score under-states confidence. Bump to band floors
    # without overriding a higher containment-based score.
    if anchor_match and tight_time and not containment:
        if overlap >= COMPOSITE_TENTATIVE_JACCARD:
            score = max(score, CONFIDENCE_TENTATIVE)
        elif overlap >= COMPOSITE_AMBIGUOUS_JACCARD:
            score = max(score, CONFIDENCE_AMBIGUOUS)

    operator_delta = _classify_operator_delta(
        typea.raw_text,
        typeb.assistant_raw_text,
        anchor_pos if (containment or anchor_match) else None,
        typeb_source=typeb.source,
        typeb_completeness=typeb.source_completeness,
        containment=containment,
    )
    operator_delta_detected = operator_delta.position in ("prefix", "suffix", "interleaved")

    ev = EdgeEvidence(
        exact_hash_match=exact_hash_match,
        containment=containment,
        anchor_match=anchor_match,
        anchor_position=anchor_pos,
        token_overlap=overlap,
        time_delta_seconds=time_delta,
        operator_delta_detected=operator_delta_detected,
        tight_time_coupling=tight_time,
        forward_time_coupling=forward_time,
        observer_lag_tolerated=observer_lag,
    )
    return score, ev, operator_delta


def _band(score: float) -> str:
    if score >= CONFIDENCE_STRONG:
        return "strong"
    if score >= CONFIDENCE_TENTATIVE:
        return "tentative"
    if score >= CONFIDENCE_AMBIGUOUS:
        return "ambiguous"
    return "none"


def compute_edges(
    captures: list[TypeBCapture],
    user_inputs: list[TypeAUserInput],
    *,
    min_score: float = CONFIDENCE_AMBIGUOUS,
) -> list[CandidateEdge]:
    edges: list[CandidateEdge] = []
    for cap_idx, cap in enumerate(captures):
        scored: list[tuple[float, TypeAUserInput, EdgeEvidence, OperatorDeltaSummary]] = []
        for ua in user_inputs:
            score, ev, delta = score_pair(cap, ua)
            if score >= min_score:
                scored.append((score, ua, ev, delta))
        if not scored:
            continue
        scored.sort(key=lambda x: x[0], reverse=True)
        top_score = scored[0][0]
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        gap = top_score - runner_up
        # Emit top edge plus any near-tie within 0.05 as ambiguous companions.
        for rank, (score, ua, ev, delta) in enumerate(scored):
            if rank > 0 and (top_score - score) > 0.05:
                break
            ev.competing_candidate_count = max(0, len(scored) - 1)
            ev.top_candidate_gap = gap if rank == 0 else 0.0
            band = _band(score)
            if rank > 0 and gap < 0.05:
                # Force ambiguous when top two are within 0.05.
                band = "ambiguous"
            edge_id = f"hl_{cap_idx:04d}_{rank}_{cap.prompt_run_id}_{ua.session_id[:16]}"
            edges.append(CandidateEdge(
                edge_id=edge_id,
                confidence_band=band,
                score=score,
                direction="typeb_to_typea",
                type_b={
                    "prompt_run_id": cap.prompt_run_id,
                    "prompt_slot": cap.prompt_slot,
                    "prompt_slug": cap.prompt_slug,
                    "conversation_id": cap.conversation_id,
                    "conversation_url": cap.conversation_url,
                    "assistant_sha256": cap.assistant_sha256,
                    "captured_at": cap.captured_at,
                    "source": cap.source,
                    "capture_status": cap.capture_status,
                    "skipped_reason": cap.skipped_reason,
                    "tab_title": cap.tab_title,
                    "source_completeness": cap.source_completeness,
                    "soft_observation_count": cap.soft_observation_count,
                },
                type_a={
                    "surface": ua.surface,
                    "session_id": ua.session_id,
                    "source_path": ua.source_path,
                    "cwd": ua.cwd,
                    "timestamp": ua.timestamp,
                    "turn_uuid": ua.turn_uuid,
                },
                evidence=ev,
                operator_delta_summary=delta,
            ))
    return edges


# ---------- projection ----------


def build_projection(
    captures: list[TypeBCapture],
    user_inputs: list[TypeAUserInput],
    edges: list[CandidateEdge],
    *,
    drop_none_band: bool = True,
) -> dict[str, Any]:
    """Compose the projection.

    drop_none_band controls whether confidence_band == "none" edges (score below
    CONFIDENCE_AMBIGUOUS, only present when --min-score lowered the candidate floor)
    are excluded from the production projection. They are diagnostic-only signals and
    must not appear in current_bindings.
    """
    eligible = [e for e in edges if not drop_none_band or e.confidence_band != "none"]
    by_session: dict[str, list[str]] = {}
    by_conversation: dict[str, list[str]] = {}
    for e in eligible:
        if e.confidence_band in ("strong", "tentative"):
            sid = e.type_a.get("session_id") or ""
            cid = e.type_b.get("conversation_id") or ""
            by_session.setdefault(sid, []).append(e.edge_id)
            by_conversation.setdefault(cid, []).append(e.edge_id)
    current_bindings = []
    for sid, edge_ids in by_session.items():
        current_bindings.append({
            "session_id": sid,
            "linked_edge_ids": edge_ids,
            "linked_conversation_ids": sorted({
                e.type_b.get("conversation_id")
                for e in eligible
                if e.edge_id in edge_ids and e.type_b.get("conversation_id")
            }),
        })
    typeb_source_counts = {"prompt_shelf_run": 0, "capture_diagnostic": 0, "other": 0}
    for cap in captures:
        bucket = cap.source if cap.source in ("prompt_shelf_run", "capture_diagnostic") else "other"
        typeb_source_counts[bucket] += 1
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": _now_iso(),
        "inputs": {
            "chatgpt_observer_state": "state/prompt_shelf/chatgpt_observer_state.json",
            "prompt_shelf_runs_index": str(PROMPT_SHELF_RUNS_INDEX.relative_to(REPO_ROOT)),
            "capture_diagnostics_dir": str(CAPTURE_DIAGNOSTICS_DIR.relative_to(REPO_ROOT)),
            "agent_execution_trace_ledger": str(EXECUTION_TRACE_LEDGER.relative_to(REPO_ROOT)),
        },
        "counts": {
            "typeb_captures_considered": len(captures),
            "typeb_by_source": typeb_source_counts,
            "typea_user_inputs_considered": len(user_inputs),
            "candidate_edges": len(eligible),
            "strong": sum(1 for e in eligible if e.confidence_band == "strong"),
            "tentative": sum(1 for e in eligible if e.confidence_band == "tentative"),
            "ambiguous": sum(1 for e in eligible if e.confidence_band == "ambiguous"),
            "none_dropped": sum(1 for e in edges if e.confidence_band == "none") if drop_none_band else 0,
        },
        "candidate_edges": [e.to_dict() for e in eligible],
        "current_bindings": current_bindings,
    }


def build_diagnostics(captures: list[TypeBCapture], user_inputs: list[TypeAUserInput], edges: list[CandidateEdge]) -> dict[str, Any]:
    captures_no_match = [c.prompt_run_id for c in captures if not any(e.type_b.get("prompt_run_id") == c.prompt_run_id for e in edges)]
    inputs_no_match = sum(1 for ua in user_inputs if not any(e.type_a.get("session_id") == ua.session_id for e in edges))
    return {
        "schema_version": "operator_handoff_linkage_diagnostics_v0",
        "generated_at": _now_iso(),
        "captures_with_no_candidate_edge": captures_no_match[:50],
        "captures_with_no_candidate_count": len(captures_no_match),
        "user_input_records_with_no_match": inputs_no_match,
        "ambiguous_edges": [e.edge_id for e in edges if e.confidence_band == "ambiguous"][:50],
        "tuning_constants": {
            "ASSISTANT_ANCHOR_PREFIX_CHARS": ASSISTANT_ANCHOR_PREFIX_CHARS,
            "TIME_WINDOW_HOURS_DEFAULT": TIME_WINDOW_HOURS_DEFAULT,
            "TIGHT_TIME_FORWARD_SECONDS": TIGHT_TIME_FORWARD_SECONDS,
            "TIGHT_TIME_BACKWARD_TOLERANCE_SECONDS": TIGHT_TIME_BACKWARD_TOLERANCE_SECONDS,
            "COMPOSITE_TENTATIVE_JACCARD": COMPOSITE_TENTATIVE_JACCARD,
            "COMPOSITE_AMBIGUOUS_JACCARD": COMPOSITE_AMBIGUOUS_JACCARD,
            "SCORE_WEIGHT_CONTAINMENT": SCORE_WEIGHT_CONTAINMENT,
            "SCORE_WEIGHT_ANCHOR": SCORE_WEIGHT_ANCHOR,
            "SCORE_WEIGHT_JACCARD": SCORE_WEIGHT_JACCARD,
            "SCORE_WEIGHT_TIME_PROXIMITY": SCORE_WEIGHT_TIME_PROXIMITY,
            "CONFIDENCE_STRONG": CONFIDENCE_STRONG,
            "CONFIDENCE_TENTATIVE": CONFIDENCE_TENTATIVE,
            "CONFIDENCE_AMBIGUOUS": CONFIDENCE_AMBIGUOUS,
            "SOFT_SELECTION_POLICY": SOFT_SELECTION_POLICY,
        },
    }


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    tmp.replace(path)


# ---------- HUD / cockpit consumer surface ----------
#
# These pure helpers exist for downstream consumers (operator-bridge HUD overlay,
# Cockpit SessionInspectorPanel, server API) to read the projection without parsing
# candidate edges by hand. Output is gated on confidence_band so consumers cannot
# accidentally render an "ambiguous-only" link as confirmed.

PROJECTION_STALE_AGE_SECONDS_DEFAULT = 300.0  # 5 minutes
PRIMARY_BANDS = ("strong", "tentative")
SURFACE_LABELS = {
    "claude_code": "Claude",
    "claude": "Claude",
    "codex": "Codex",
}
# Linked-surface tints. Designed to compose with — not replace — the existing accent /
# favicon_color authority chain in prompt_shelf_chatgpt_observer.py:
#   * tone palette (OPERATOR_VISUAL_TONES) drives response-state colors.
#   * page_chrome.favicon_color drives non-ChatGPT tabs.
#   * tab_order / tab_chrome_title are Chrome-strip authority and never change.
# The HUD reads handoff_linkage_visual.accent_overlay_hex and renders it as a thin
# surface-identity stripe over the existing accent — operator can see Codex vs Claude
# vs unlinked at a glance without losing the response-state color.
LINKED_SURFACE_TINTS = {
    "codex": "#5da8c2",        # slate-blue, distinct from `saved` (#83c5be) and `pending_response` (#6ea8ff)
    "claude_code": "#c98c5f",  # warm tan, distinct from `response_ready_unseen` (#f28c38) and `live`/`needs_save` (#d9b45f)
    "claude": "#c98c5f",
}
LINKED_BAND_INTENSITY = {
    "strong": "primary",
    "tentative": "muted",
}


def load_handoff_projection(path: Path = PROJECTION_PATH) -> dict[str, Any]:
    """Load the projection. Returns an empty payload with status fields when missing."""
    if not path.exists():
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "projection_missing",
            "candidate_edges": [],
            "current_bindings": [],
        }
    try:
        payload = _load_json(path)
    except (OSError, json.JSONDecodeError):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "projection_invalid",
            "candidate_edges": [],
            "current_bindings": [],
        }
    if not isinstance(payload, dict):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "projection_invalid",
            "candidate_edges": [],
            "current_bindings": [],
        }
    payload.setdefault("status", "projection_present")
    return payload


def projection_age_seconds(projection: dict[str, Any], *, now: _dt.datetime | None = None) -> float | None:
    generated_at = _parse_iso(projection.get("generated_at"))
    if generated_at is None:
        return None
    now = now or _dt.datetime.now(_dt.timezone.utc)
    return max(0.0, (now - generated_at).total_seconds())


def projection_freshness_label(projection: dict[str, Any], *, stale_seconds: float = PROJECTION_STALE_AGE_SECONDS_DEFAULT, now: _dt.datetime | None = None) -> str:
    """Return one of: projection_present, projection_stale, projection_missing, projection_invalid."""
    status = projection.get("status") or "projection_present"
    if status in ("projection_missing", "projection_invalid"):
        return status
    age = projection_age_seconds(projection, now=now)
    if age is None:
        return "projection_present"
    return "projection_stale" if age > stale_seconds else "projection_present"


def handoff_linkage_status(
    *,
    projection_path: Path = PROJECTION_PATH,
    diagnostics_path: Path = DIAGNOSTICS_PATH,
    stale_seconds: float = PROJECTION_STALE_AGE_SECONDS_DEFAULT,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Read projection metadata only, without joining raw Type B/Type A text."""
    projection = load_handoff_projection(projection_path)
    freshness = projection_freshness_label(projection, stale_seconds=stale_seconds, now=now)
    age = projection_age_seconds(projection, now=now)
    counts = projection.get("counts") if isinstance(projection.get("counts"), dict) else {}
    candidate_edges = projection.get("candidate_edges") if isinstance(projection.get("candidate_edges"), list) else []
    current_bindings = projection.get("current_bindings") if isinstance(projection.get("current_bindings"), list) else []

    diagnostics_status = "missing"
    diagnostics_counts: dict[str, Any] = {}
    if diagnostics_path.exists():
        try:
            diagnostics = _load_json(diagnostics_path)
        except (OSError, json.JSONDecodeError):
            diagnostics_status = "invalid"
        else:
            if isinstance(diagnostics, dict):
                diagnostics_status = "present"
                ambiguous_edges = diagnostics.get("ambiguous_edges")
                diagnostics_counts = {
                    "captures_with_no_candidate_count": diagnostics.get("captures_with_no_candidate_count"),
                    "user_input_records_with_no_match": diagnostics.get("user_input_records_with_no_match"),
                    "ambiguous_edges": len(ambiguous_edges) if isinstance(ambiguous_edges, list) else None,
                }
            else:
                diagnostics_status = "invalid"

    if freshness == "projection_present":
        next_action = "use_projection"
        decision_authority = "fresh_projection_metadata"
    elif freshness == "projection_stale":
        next_action = "refresh_if_needed"
        decision_authority = "advisory_stale_projection_metadata"
    else:
        next_action = "write_projection"
        decision_authority = "advisory_missing_or_invalid_projection"

    return {
        "schema_version": STATUS_SCHEMA_VERSION,
        "status": freshness,
        "decision_authority": decision_authority,
        "mutates_state": False,
        "projection": {
            "path": _display_path(projection_path),
            "status": projection.get("status"),
            "generated_at": projection.get("generated_at"),
            "age_seconds": int(age) if age is not None else None,
            "stale_after_seconds": stale_seconds,
        },
        "counts": {
            "typeb_captures_considered": counts.get("typeb_captures_considered"),
            "typeb_by_source": counts.get("typeb_by_source"),
            "typea_user_inputs_considered": counts.get("typea_user_inputs_considered"),
            "candidate_edges": counts.get("candidate_edges", len(candidate_edges)),
            "strong": counts.get("strong"),
            "tentative": counts.get("tentative"),
            "ambiguous": counts.get("ambiguous"),
            "none_dropped": counts.get("none_dropped"),
            "current_bindings": len(current_bindings),
        },
        "diagnostics": {
            "path": _display_path(diagnostics_path),
            "status": diagnostics_status,
            "counts": diagnostics_counts,
        },
        "next_action": next_action,
        "commands": {
            "status": "./repo-python tools/meta/observability/operator_handoff_linkage.py --status",
            "refresh_if_stale": "./repo-python tools/meta/observability/operator_handoff_linkage.py --refresh-if-stale",
            "full_join_print": "./repo-python tools/meta/observability/operator_handoff_linkage.py --print --top 20",
            "write_projection": "./repo-python tools/meta/observability/operator_handoff_linkage.py --write-projection",
        },
        "privacy_boundary": (
            "status reads projection and diagnostics metadata only; it does not read raw "
            "assistant/user text, rollout bodies, or prompt-shelf raw event bodies"
        ),
    }


def _summarize_link_for_display(edge: dict[str, Any]) -> dict[str, Any]:
    type_a = edge.get("type_a") or {}
    type_b = edge.get("type_b") or {}
    evidence = edge.get("evidence") or {}
    delta = edge.get("operator_delta_summary") or {}
    surface = type_a.get("surface") or "unknown"
    session_id = str(type_a.get("session_id") or "")
    # Short label: first segment for dotted/dashed ids, else first 8 chars.
    if "T" in session_id and "-" in session_id:
        # Codex session ids look like 2026-05-09T20-56-21-019e0e4f-…
        parts = session_id.split("-")
        short = "-".join(parts[1:3]) if len(parts) >= 3 else session_id[:8]
    else:
        short = session_id[:8] if session_id else "?"
    return {
        "surface": surface,
        "surface_label": SURFACE_LABELS.get(surface, surface or "?"),
        "session_id": session_id,
        "session_short": short,
        "confidence_band": edge.get("confidence_band"),
        "score": edge.get("score"),
        "edge_id": edge.get("edge_id"),
        "conversation_id": type_b.get("conversation_id"),
        "time_delta_seconds": evidence.get("time_delta_seconds"),
        "tight_time_coupling": evidence.get("tight_time_coupling"),
        "source": type_b.get("source"),
        "source_completeness": type_b.get("source_completeness"),
        "operator_delta_reliability": delta.get("reliability"),
    }


def conversation_links(
    projection: dict[str, Any],
    conversation_id: str,
    *,
    bands: tuple[str, ...] = PRIMARY_BANDS,
) -> list[dict[str, Any]]:
    """Return display-shaped links for one conversation, filtered to primary bands.

    Sorted by confidence_band priority (strong > tentative), then by score descending.
    Ambiguous and none bands are excluded — they belong to diagnostic surfaces, not
    primary linkage badges.
    """
    if not conversation_id:
        return []
    edges = projection.get("candidate_edges") or []
    band_priority = {"strong": 0, "tentative": 1}
    matched: list[tuple[int, float, dict[str, Any]]] = []
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        if (edge.get("type_b") or {}).get("conversation_id") != conversation_id:
            continue
        band = edge.get("confidence_band")
        if band not in bands:
            continue
        score = float(edge.get("score") or 0.0)
        matched.append((band_priority.get(band, 99), -score, edge))
    matched.sort(key=lambda triple: (triple[0], triple[1]))
    return [_summarize_link_for_display(triple[2]) for triple in matched]


def conversation_link_index(
    projection: dict[str, Any], *, bands: tuple[str, ...] = PRIMARY_BANDS
) -> dict[str, list[dict[str, Any]]]:
    """Build conversation_id -> [link summary, ...] index in a single pass."""
    index: dict[str, list[dict[str, Any]]] = {}
    edges = projection.get("candidate_edges") or []
    band_priority = {"strong": 0, "tentative": 1}
    grouped: dict[str, list[tuple[int, float, dict[str, Any]]]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        cid = (edge.get("type_b") or {}).get("conversation_id")
        if not cid:
            continue
        band = edge.get("confidence_band")
        if band not in bands:
            continue
        score = float(edge.get("score") or 0.0)
        grouped.setdefault(cid, []).append((band_priority.get(band, 99), -score, edge))
    for cid, triples in grouped.items():
        triples.sort(key=lambda triple: (triple[0], triple[1]))
        index[cid] = [_summarize_link_for_display(t[2]) for t in triples]
    return index


def _compute_handoff_visual(links: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive the additive visual block from ranked links.

    All fields are nullable when there is no primary link, so a HUD consumer can render
    a default tab unchanged. This function never replaces the tab's existing accent or
    favicon_color — those remain Chrome / response-state authority. The overlay hex is
    consumed as a surface-identity stripe alongside the existing accent.
    """
    if not links:
        return {
            "accent_overlay_hex": None,
            "badge_text": None,
            "badge_band": None,
            "badge_intensity": None,
            "chrome_title_prefix_extension": None,
            "linked_surface": None,
            "link_count": 0,
        }
    top = links[0]
    surface = (top.get("surface") or "").lower()
    label = top.get("surface_label") or surface or "?"
    short = top.get("session_short") or ""
    band = top.get("confidence_band") or "tentative"
    overlay = LINKED_SURFACE_TINTS.get(surface)
    badge_text = f"→ {label} {short}".strip()
    if len(links) > 1:
        badge_text = f"{badge_text} +{len(links) - 1}"
    return {
        "accent_overlay_hex": overlay,
        "badge_text": badge_text,
        "badge_band": band,
        "badge_intensity": LINKED_BAND_INTENSITY.get(band, "muted"),
        # Optional Chrome-title shorthand. The Chrome tab number prefix (cap_operator_chrome_tab_order_static_ordinals)
        # owns the leading "<n> · " portion of tab_chrome_title; this extension is a SEPARATE
        # field consumers may append after it without overwriting the existing title.
        "chrome_title_prefix_extension": f"{label} {short}".strip() if short else label,
        "linked_surface": surface or None,
        "link_count": len(links),
    }


def enrich_tab_summary_with_linkage(
    summary: dict[str, Any],
    *,
    link_index: dict[str, list[dict[str, Any]]],
    projection: dict[str, Any],
    stale_seconds: float = PROJECTION_STALE_AGE_SECONDS_DEFAULT,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Add a `handoff_linkage` block to a single tab summary in place; return it.

    Uses `key`/`conversation_prefix` to locate the conversation_id when possible —
    operator-bridge tab summaries already key chatgpt tabs as `chatgpt:<conversation_id>`.
    """
    key = str(summary.get("key") or "")
    conversation_id = ""
    if key.startswith("chatgpt:"):
        conversation_id = key.split(":", 1)[1]
    if not conversation_id:
        # Fall back to extracting the id from a chatgpt.com URL.
        url = str(summary.get("url") or "")
        if "/c/" in url:
            tail = url.split("/c/", 1)[1]
            conversation_id = tail.split("?")[0].split("#")[0].rstrip("/")

    freshness = projection_freshness_label(projection, stale_seconds=stale_seconds, now=now)
    age = projection_age_seconds(projection, now=now)
    links = link_index.get(conversation_id, []) if conversation_id else []

    # Status describes link presence; freshness is a separate metadata field so a UI
    # consumer can render "linked (stale)" without losing the link information.
    if freshness in ("projection_missing", "projection_invalid"):
        status = freshness
    elif links:
        status = "linked"
    else:
        status = "unlinked"

    summary["handoff_linkage"] = {
        "status": status,
        "projection_status": projection.get("status"),
        "projection_generated_at": projection.get("generated_at"),
        "projection_age_seconds": int(age) if age is not None else None,
        "freshness": freshness,
        "conversation_id": conversation_id or None,
        "links": links,
    }
    # Additive visual unification: composes with — never replaces — the existing accent,
    # favicon_color, tab_order, and tab_chrome_title fields. Consumers (HUD overlay,
    # cockpit) read this block to render a surface-identity stripe + linkage badge while
    # the response-state color authority (cap_operator_hud_response_ready_unseen_color)
    # and Chrome strip ordinal authority (cap_operator_chrome_tab_order_static_ordinals)
    # remain intact.
    summary["handoff_linkage_visual"] = _compute_handoff_visual(links)
    return summary


def enrich_tab_observations_payload(
    tab_observations: dict[str, Any],
    *,
    projection: dict[str, Any] | None = None,
    stale_seconds: float = PROJECTION_STALE_AGE_SECONDS_DEFAULT,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Apply enrich_tab_summary_with_linkage to every ChatGPT tab in a tab_observations payload.

    Mutates and returns the same dict for in-place updates.
    """
    proj = projection if projection is not None else load_handoff_projection()
    index = conversation_link_index(proj)
    current = tab_observations.get("current_tabs") or []
    for summary in current:
        if not isinstance(summary, dict):
            continue
        if summary.get("tab_kind") != "chatgpt":
            # Only ChatGPT tabs participate in handoff linkage; clear any stale field on others.
            summary.pop("handoff_linkage", None)
            continue
        enrich_tab_summary_with_linkage(
            summary, link_index=index, projection=proj, stale_seconds=stale_seconds, now=now
        )
    tab_memory = tab_observations.get("tab_memory")
    if isinstance(tab_memory, dict):
        for key, item in tab_memory.items():
            if not isinstance(item, dict) or not str(key).startswith("chatgpt:"):
                continue
            enrich_tab_summary_with_linkage(
                item, link_index=index, projection=proj, stale_seconds=stale_seconds, now=now
            )
    # Roll up a top-level summary so downstream readers do not have to scan every tab.
    linked_chatgpt = [
        item for item in current
        if isinstance(item, dict)
        and item.get("tab_kind") == "chatgpt"
        and (item.get("handoff_linkage") or {}).get("status") == "linked"
    ]
    tab_observations["handoff_linkage_summary"] = {
        "schema_version": "operator_tab_handoff_linkage_summary_v0",
        "linked_chatgpt_tab_count": len(linked_chatgpt),
        "linked_session_ids": sorted({
            link.get("session_id")
            for item in linked_chatgpt
            for link in (item.get("handoff_linkage") or {}).get("links") or []
            if link.get("session_id")
        }),
        "projection_status": proj.get("status"),
        "projection_generated_at": proj.get("generated_at"),
    }
    return tab_observations


def refresh_projection_if_stale(
    *,
    stale_seconds: float = PROJECTION_STALE_AGE_SECONDS_DEFAULT,
    limit: int = DEFAULT_TYPEB_LIMIT,
    session_limit: int = DEFAULT_TYPEA_SESSION_LIMIT,
    now: _dt.datetime | None = None,
    projection_path: Path = PROJECTION_PATH,
    diagnostics_path: Path = DIAGNOSTICS_PATH,
) -> str:
    """Regenerate the projection if it is missing or older than `stale_seconds`.

    Returns one of: "regenerated", "fresh", "skipped_no_inputs". Safe to call from a
    long-lived observer loop at a bounded cadence (e.g. once per N seconds).
    """
    proj = load_handoff_projection(projection_path)
    freshness = projection_freshness_label(proj, stale_seconds=stale_seconds, now=now)
    if freshness == "projection_present":
        return "fresh"

    captures = load_typeb_records(limit=limit)
    user_inputs = load_typea_user_inputs(session_limit=session_limit)
    if not captures or not user_inputs:
        return "skipped_no_inputs"
    edges = compute_edges(captures, user_inputs)
    edges.sort(key=lambda e: e.score, reverse=True)
    new_proj = build_projection(captures, user_inputs, edges)
    _atomic_write_json(projection_path, new_proj)
    _atomic_write_json(diagnostics_path, build_diagnostics(captures, user_inputs, edges))
    return "regenerated"


# ---------- CLI ----------


def _print_summary(projection: dict[str, Any], top_n: int = 20) -> None:
    counts = projection.get("counts", {})
    by_source = counts.get("typeb_by_source", {}) or {}
    print(f"== Operator Handoff Linkage v0 — {projection.get('generated_at')}")
    print(f"   considered: {counts.get('typeb_captures_considered')} Type B "
          f"({by_source.get('prompt_shelf_run', 0)} curated, {by_source.get('capture_diagnostic', 0)} soft), "
          f"{counts.get('typea_user_inputs_considered')} Type A user-input records")
    print(f"   edges:      {counts.get('candidate_edges')} total "
          f"({counts.get('strong')} strong, {counts.get('tentative')} tentative, "
          f"{counts.get('ambiguous')} ambiguous, {counts.get('none_dropped', 0)} none dropped)")
    print()
    edges = projection.get("candidate_edges", [])[:top_n]
    if not edges:
        print("(no candidate edges; try --limit higher or check input freshness)")
        return
    for e in edges:
        tb = e["type_b"]
        ta = e["type_a"]
        ev = e["evidence"]
        delta = e["operator_delta_summary"]
        src_tag = "soft" if tb.get("source") == "capture_diagnostic" else "curated"
        print(f"[{e['confidence_band']:9s} {e['score']:.3f}]  "
              f"[{src_tag}] {tb.get('prompt_slot') or '--':>3}/{(tb.get('prompt_slug') or '')[:24]:24s}  →  "
              f"{ta['surface']}/{ta['session_id'][:16]}")
        print(f"            conv={tb['conversation_url']}")
        print(f"            cap_at={tb['captured_at']}  ta_at={ta['timestamp']}  Δ={ev['time_delta_seconds']}s  "
              f"contain={ev['containment']} anchor={ev['anchor_match']} "
              f"jaccard={ev['token_overlap']:.2f} delta={delta['position']}({delta['chars']})")


TAB_OBSERVATIONS_PATH = REPO_ROOT / "state" / "operator_bridge" / "tab_observations.json"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--print", dest="do_print", action="store_true", help="print top candidate edges to stdout")
    mode.add_argument("--write-projection", dest="do_write", action="store_true", help="write projection + diagnostics JSON")
    mode.add_argument("--enrich-tab-observations", dest="do_enrich", action="store_true", help="apply handoff_linkage enrichment to state/operator_bridge/tab_observations.json")
    mode.add_argument("--refresh-if-stale", dest="do_refresh", action="store_true", help="regenerate projection only if missing or older than --stale-seconds")
    mode.add_argument("--status", dest="do_status", action="store_true", help="print projection freshness/count metadata without reading raw handoff bodies")
    p.add_argument("--stale-seconds", type=float, default=PROJECTION_STALE_AGE_SECONDS_DEFAULT, help="age threshold for stale/regenerate decisions")
    p.add_argument("--limit", type=int, default=DEFAULT_TYPEB_LIMIT, help="max Type B captures considered")
    p.add_argument("--session-limit", type=int, default=DEFAULT_TYPEA_SESSION_LIMIT, help="max Type A sessions considered")
    p.add_argument("--top", type=int, default=20, help="rows to print in --print mode")
    p.add_argument("--min-score", type=float, default=CONFIDENCE_AMBIGUOUS, help="emit candidate edges with score >= this (default = ambiguous threshold)")
    p.add_argument("--curated-only", action="store_true", help="only use prompt_shelf_runs_index; skip soft capture_diagnostics feed")
    p.add_argument("--include-all-rollouts", action="store_true", help="when ledger missing, do not filter rollouts to repo cwd")
    p.add_argument("--keep-none-band", action="store_true", help="emit confidence_band=none diagnostic rows in projection (default drops them)")
    args = p.parse_args(argv)

    # Short-circuit: status, enrichment, and refresh modes do not need a fresh joiner pass.
    if args.do_status:
        status = handoff_linkage_status(stale_seconds=args.stale_seconds)
        print(json.dumps(status, indent=2, ensure_ascii=False))
        return 0

    if args.do_enrich:
        proj = load_handoff_projection()
        if not TAB_OBSERVATIONS_PATH.exists():
            print(f"tab_observations not found: {TAB_OBSERVATIONS_PATH.relative_to(REPO_ROOT)}", file=sys.stderr)
            return 1
        tab_obs = _load_json(TAB_OBSERVATIONS_PATH)
        if not isinstance(tab_obs, dict):
            print("tab_observations payload is not a dict", file=sys.stderr)
            return 1
        enriched = enrich_tab_observations_payload(tab_obs, projection=proj, stale_seconds=args.stale_seconds)
        _atomic_write_json(TAB_OBSERVATIONS_PATH, enriched)
        summary = enriched.get("handoff_linkage_summary") or {}
        print(f"enriched: {TAB_OBSERVATIONS_PATH.relative_to(REPO_ROOT)}")
        print(f"  linked_chatgpt_tab_count: {summary.get('linked_chatgpt_tab_count')}")
        print(f"  linked_session_ids: {summary.get('linked_session_ids')}")
        print(f"  projection_status: {summary.get('projection_status')}")
        return 0

    if args.do_refresh:
        result = refresh_projection_if_stale(stale_seconds=args.stale_seconds, limit=args.limit, session_limit=args.session_limit)
        print(f"refresh result: {result}")
        return 0

    if args.curated_only:
        captures = load_typeb_captures(limit=args.limit)
    else:
        captures = load_typeb_records(limit=args.limit)
    user_inputs = load_typea_user_inputs(
        session_limit=args.session_limit,
        include_all_rollouts=args.include_all_rollouts,
    )
    edges = compute_edges(captures, user_inputs, min_score=args.min_score)
    edges.sort(key=lambda e: e.score, reverse=True)
    projection = build_projection(captures, user_inputs, edges, drop_none_band=not args.keep_none_band)

    if args.do_write:
        _atomic_write_json(PROJECTION_PATH, projection)
        diagnostics = build_diagnostics(captures, user_inputs, edges)
        _atomic_write_json(DIAGNOSTICS_PATH, diagnostics)
        print(f"wrote: {PROJECTION_PATH.relative_to(REPO_ROOT)}")
        print(f"wrote: {DIAGNOSTICS_PATH.relative_to(REPO_ROOT)}")
        _print_summary(projection, top_n=args.top)
    else:
        _print_summary(projection, top_n=args.top)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
