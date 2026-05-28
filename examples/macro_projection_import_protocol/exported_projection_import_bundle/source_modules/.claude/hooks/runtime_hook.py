#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Local Claude Code lifecycle hook. It performs two cheap controller-owned jobs:
  bounded rehydration from disk for resume surfaces, and compact lifecycle hints for
  Claude sessions.
- Mechanism: Reads the one-shot session transport artifact at
  tools/meta/bridge/claude_session_transport.json, optional resume/signal artifacts, and
  only on true resume surfaces emits a bounded additionalContext payload (capped at
  MAX_CONTEXT_CHARS). The active-session heartbeat is stamped separately on every hook fire.
  Optional Work Ledger / metabolism expansion is env-gated while those paths are migrated to
  async or precomputed hook-safe cards.
- Non-goal: Does not run the bridge, does not validate plans, does not summarize chat into
  ledger rows, and does not act as a universal bootstrap HUD for every new session.

[INTERFACE]
- main(argv) — argv[1] is the canonical hook action name (session-start, subagent-start, etc.).
- Reads JSON payload from stdin if provided; emits JSON additionalContext to stdout.

[FLOW]
1. Read action + stdin payload.
2. Stamp active-session identity into the dedicated heartbeat file.
3. If the action is a true rehydration surface and a one-shot transport is pending,
   build a bounded resume brief from the transport + artifact previews.
4. Emit { hookSpecificOutput: { hookEventName, additionalContext } } JSON to stdout.

[DEPENDENCIES]
- json, sys, pathlib, datetime — stdlib only on module import.
- tools.meta.bridge.session_transport — imported lazily for read_transport / mark_consumed
  (optional; falls back to capped direct file read if the import fails).

[CONSTRAINTS]
- Must be cheap. No subprocess dashboard calls.
- Never blocks on bridge operations.
- Never raises out of main(); errors are swallowed so the hook is non-blocking.
- Output cap: MAX_CONTEXT_CHARS keeps the injected context bounded.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import select
import shlex
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

TRANSPORT_PATH = REPO_ROOT / "tools/meta/bridge/claude_session_transport.json"
AGENT_BOOTSTRAP_CONFIG_PATH = REPO_ROOT / "codex/doctrine/agent_bootstrap.json"
AGENT_BOOTSTRAP_LIVE_PATH = REPO_ROOT / "codex/doctrine/agent_bootstrap_live.json"
NAVIGATION_HINT_CARD_PATH = REPO_ROOT / "tools/meta/control/runtime_hook_navigation_hints.json"
# Reactions engine input event journal — orchestration_events.jsonl is the
# canonical durable surface that reactions_engine polls for incoming lifecycle
# signals (see tools/meta/control/reactions_engine.py:62 and §runtime_hook_ladder
# paper module). Writing a `session_lifecycle_boundary` row here on Stop turns
# the host harness's Stop event into a reactions_engine-visible boundary signal
# without going through the metabolism queue (which is a separate, peer surface).
ORCHESTRATION_EVENTS_REL = "tools/meta/control/orchestration_events.jsonl"
HOOK_SIGNAL_FALLBACK_REL = "tools/meta/control/runtime_hook_signals.jsonl"
AGENT_OBSERVABILITY_FALLBACK_REL = "tools/meta/control/runtime_hook_agent_observability.jsonl"
CLOSEOUT_BASELINE_EVENT_KIND = "closeout_session_baseline"
MAX_CLOSEOUT_BASELINE_SCAN_BYTES = 512_000
MAX_CONTEXT_CHARS = 4500
HOST_CONTEXT_INJECTION_CAP_CHARS = 10000
ARTIFACT_PREVIEW_CHARS = 1200
MAX_STDIN_BYTES = 1024 * 1024
MAX_HOOK_SAFE_READ_BYTES = 64_000
STDIN_FIRST_BYTE_TIMEOUT_SECONDS = 0.2
STDIN_DRAIN_TIMEOUT_SECONDS = 0.01
MAX_OBSERVABILITY_VALUE_CHARS = 2000
MAX_OBSERVABILITY_ITEMS = 24
MAX_OBSERVABILITY_RESPONSE_BYTES = 1024
LARGE_INSTRUCTION_PROMPT_CHARS = 2800
LARGE_INSTRUCTION_PROMPT_LINES = 35
TODO_RESIDUAL_CUE_RE = re.compile(
    r"\b("
    r"follow-?up|defer(?:red)?|later|after this session|next session|"
    r"future work|cross-session|remaining|remainder|residual|backlog"
    r")\b",
    re.IGNORECASE,
)
ENABLE_WORK_LEDGER_HOOK_RUNTIME_ENV = "AIW_RUNTIME_HOOK_ENABLE_WORK_LEDGER"
ENABLE_METABOLISM_HOOK_RUNTIME_ENV = "AIW_RUNTIME_HOOK_ENABLE_METABOLISM"

CLOSEOUT_TERMINAL_CLAIM_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "committed_and_pushed",
        re.compile(r"\b(?:committed|commit(?:ted)?)\b.{0,48}\b(?:pushed|published)\b", re.IGNORECASE),
    ),
    (
        "clean_and_pushed",
        re.compile(r"\bclean[- ]and[- ]pushed\b", re.IGNORECASE),
    ),
    (
        "pushed_to_remote",
        re.compile(r"\b(?:pushed|published)\b.{0,48}\b(?:origin|remote|origin/main|main)\b", re.IGNORECASE),
    ),
    (
        "remote_ref_verified",
        re.compile(r"\b(?:origin/main|remote ref)\b.{0,48}\b(?:verified|updated|settled)\b", re.IGNORECASE),
    ),
    (
        "working_tree_clean",
        re.compile(r"\b(?:working tree|repo|repository)\b.{0,16}\bclean\b", re.IGNORECASE),
    ),
    (
        "closeout_complete",
        re.compile(r"\bcloseout\b.{0,24}\b(?:complete|ready|settled)\b", re.IGNORECASE),
    ),
)
CLOSEOUT_TERMINAL_NEGATION_RE = re.compile(
    r"\b(?:not|not yet|did not|didn't|was not|wasn't|cannot|can't|blocked|held|unsettled|unpublished)\b",
    re.IGNORECASE,
)
CLOSEOUT_EXECUTOR_COMMIT_RE = re.compile(r"\b[0-9a-f]{7,40}\b")
CLOSEOUT_EXECUTOR_ACTION_ID_RE = re.compile(r"\bcea_[0-9a-f]{8,32}\b", re.IGNORECASE)
CLOSEOUT_EXECUTOR_ACTION_EVIDENCE_RE = re.compile(
    r"\b("
    r"executor action executed|primary_action|scoped commit|committed|commit|"
    r"pushed|published|remote verified|origin/main|ls-remote|"
    r"worktree removed|worktree registered|generated[- ]state settlement|"
    r"settled generated"
    r")\b",
    re.IGNORECASE,
)
CLOSEOUT_EXECUTOR_BLOCKER_EVIDENCE_RE = re.compile(
    r"\b("
    r"blocked|blocker|failing test|test failure|failed validation|"
    r"conflict|patch conflict|same[- ]file|same path|permission|secret|"
    r"unsafe|held by policy|not safe|cannot|can't"
    r")\b",
    re.IGNORECASE,
)
REPO_SUBSTRATE_PATH_HINT_RE = re.compile(
    r"(?<![\w./])("
    r"AGENTS\.md|CLAUDE\.md|CODEX\.md|kernel\.py|repo-python|repo-pytest|repo-git|"
    r"\.claude/(?:hooks|settings|follow_on|agents)|"
    r"codex/|docs/|system/|tools/|state/|obsidian/|sites/|self-indexing-cognitive-substrate/"
    r")",
    re.IGNORECASE,
)
REPO_SUBSTRATE_ACTION_RE = re.compile(
    r"\b("
    r"changed|updated|modified|edited|patched|implemented|wired|wrote|created|"
    r"deleted|removed|staged|committed|pushed|published|validated|tested|"
    r"ran tests?|pytest|vitest|build|lint|compiled"
    r")\b",
    re.IGNORECASE,
)
REQUIRED_READS_HEADING_RE = re.compile(r"^##\s+Required reads\b", re.IGNORECASE)

CANONICAL_HOOK_NAMES = {
    "precompact": "PreCompact",
    "postcompact": "PostCompact",
    "pre-tool": "PreToolUse",
    "session-start": "SessionStart",
    "subagent-start": "SubagentStart",
    "user-prompt": "UserPromptSubmit",
    "post-tool": "PostToolUse",
    "session-end": "SessionEnd",
    "stop": "Stop",
}

REHYDRATION_ACTIONS = {"session-start", "subagent-start", "postcompact"}
BASH_NATIVE_FALLTHROUGH_VERBS = {
    "ls",
    "find",
    "grep",
    "rg",
    "cat",
    "head",
    "tail",
    "wc",
    "sed",
    "awk",
    "echo",
}
TYPED_DISCOVERY_TOOL_NAMES = {"Grep", "Glob"}
# Per-verb typed-tool fallback. Route intervention is owned by
# anti_pattern_id / repair_class in navigation_route_intervention.py; this map
# only names the local tool replacement after a shell verb has classified the
# bad command shape.
#
# Capability-aware wording: `Grep` and `Glob` are NOT universally present in
# every Claude Code session (they may be built-in / deferred / absent depending
# on the session's tool manifest, which the hook does not have access to). The
# strings below therefore say "prefer X when available; otherwise Bash <verb>
# is an acceptable fallback" rather than asserting Grep/Glob are present. This
# closes the failure mode where the hook steered an agent toward Grep/Glob in
# a session that did not have those tools, and the agent then misdiagnosed
# their absence (e.g. by treating an empty `ToolSearch select:Grep` result —
# which only searches the deferred-tool list — as proof of global Grep
# unavailability). `Read` / `Edit` / `Write` are core Claude Code tools and
# are recommended without a conditional. See the "Tool availability — built-in
# vs deferred" section in CLAUDE.md for the full probe order.
BASH_VERB_TOOL_SUGGESTIONS = {
    "ls": "Prefer `Glob` for file discovery when it is in your active tool set (returns paths sorted by mtime, no shell needed); otherwise narrow `ls` is an acceptable Bash fallback.",
    "find": "Prefer `Glob` (e.g. `**/*.py` or `path/**/file*`) for path discovery, or `Grep` for content discovery, when those tools are in your active tool set; otherwise narrow `find` / Bash `grep` are acceptable fallbacks.",
    "grep": "Prefer `Grep` (Claude tool — ripgrep-backed, repo-permission-aware) when it is in your active tool set; otherwise Bash `grep` is an acceptable fallback for a known target.",
    "rg": "Prefer `Grep` (Claude tool — ripgrep-backed, repo-permission-aware) when it is in your active tool set; otherwise Bash `rg` / `grep` is an acceptable fallback for a known target.",
    "cat": "Use `Read` (Claude tool) with `offset` / `limit` for files; `./repo-python kernel.py --compile <path>` for a structured file card without a full read.",
    "head": "Use `Read` (Claude tool) with `limit` for the first N lines.",
    "tail": "Use `Read` (Claude tool) with `offset` to read the tail of a file.",
    "wc": "Trust structured counts in kernel output; for files, use `Read` and count inline.",
    "sed": "Use `Edit` (Claude tool) for in-place edits; for inspection prefer `Grep` + `Read` when `Grep` is in your active tool set, otherwise Bash `grep` + `Read`.",
    "awk": "Use `Read` + parse the structured payload in your tool call; for kernel output use the JSON shape directly.",
    "echo": "Output text directly in your message; use `Write` (Claude tool) for file content.",
}
# Tokens whose presence in a shell segment marks that segment as a kernel/repo
# command invocation. Used to detect post-pipe filter use of fallthrough verbs
# (e.g. `kernel.py --pulse | head -100`) so the hint can specifically point at
# the kernel command's own compact / full / structured-payload modes instead of
# emitting the generic verb suggestion.
KERNEL_COMMAND_TOKEN_HINTS = ("kernel.py", "repo-python")
SHELL_COMMAND_BOUNDARIES = {";", "&", "&&", "||", "|", "|&"}
SHELL_TRANSPARENT_PREFIXES = {"command", "builtin", "time", "noglob"}
SHELL_SEGMENT_PREFIXES = {"cd", "pushd", "popd", "set", "export", "ulimit"}
REPO_PYTHON_COMMAND_WORDS = {"repo-python", "python", "python3", "python3.11", "kernel.py"}
HIGH_CARDINALITY_OPTION_SURFACES = {
    "paper_modules",
    "standards",
    "task_ledger",
    "skills",
    "annex_patterns",
    "annex_distillation_patterns",
    "python_files",
    "python_scopes",
    "frontend_components",
    "standard_skill_map",
}
CLUSTER_FIRST_OPTION_SURFACES = {
    "paper_modules",
    "standards",
    "task_ledger",
    "skills",
    "annex_patterns",
    "annex_distillation_patterns",
    "python_files",
    "python_scopes",
    "frontend_components",
    "principles",
}
HIGH_VOLUME_READ_PREFIXES = {
    "state/task_ledger/views/": (
        "Task Ledger views are projection rows, not the first read path. Use "
        "`./repo-python kernel.py --option-surface task_ledger --band cluster_flag` "
        "or `./repo-python tools/meta/factory/task_ledger_apply.py organizer-report --transcript-file-limit 2` "
        "before opening individual view JSON."
    ),
}
HIGH_VOLUME_READ_FILES = {
    "state/task_ledger/ledger.json": (
        "The full Task Ledger ledger is high-cardinality private state. Use "
        "`./repo-python kernel.py --option-surface task_ledger --band cluster_flag`, then "
        "`--option-surface task_ledger --band card --ids <work_item_id>` for a selected row."
    ),
    "codex/doctrine/paper_modules/_index.json": (
        "The paper-module index is a generated projection. Use "
        "`./repo-python kernel.py --option-surface paper_modules --band cluster_flag`, then a card row."
    ),
    "codex/doctrine/paper_modules/_validation_report.json": (
        "The paper-module validation report is evidence after a selected repair. Use "
        "`./repo-python kernel.py --navigation-metabolism \"<task>\" --metabolism-profile quick --context-budget 12000` "
        "or the paper_modules cluster surface first."
    ),
    "codex/doctrine/paper_modules/paper_module_candidates.json": (
        "Paper-module candidates should be reached through the coverage/ledger lane, not raw fan-out. "
        "Start with `--context-pack \"<task>\"` or `--option-surface paper_modules --band cluster_flag`."
    ),
}
PAPER_LATTICE_SLUG_RE = re.compile(r"^[a-z0-9_]+$")
GUESSY_KERNEL_FLAGS = {
    "--task-context",
    "--task_context",
    "--navpack",
    "--relevance-pack",
    "--relevance_pack",
    "--activate-knapsack",
    "--activate_knapsack",
    "--unknown",
    "--unknown-flag",
}

# Cockpit source root — edits under this prefix must route to the owned
# view-quality packet + station_render evidence lanes for visual verification,
# NOT the harness-default preview_* MCP. The doctrine at
# codex/doctrine/skills/frontend/frontend_visual_verification.md §governing
# principles explicitly overrides the generic <preview_tools> block for
# system/server/ui/; the hook enforces that override at runtime by
# counter-injecting an additionalContext block on every PostToolUse:Edit whose
# target sits under this prefix. This closes the drift where the harness
# preamble tells Claude to run `preview_start` but the project has its own
# purpose-built capture surfaces (view_quality_census.py + station_render.py).
COCKPIT_SOURCE_PREFIX = "system/server/ui/"
COCKPIT_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
SEED_SUBSTRATE_EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
RAW_SEED_SUFFIX = "raw_seed.md"
AGENT_SEED_SUFFIX = "agent_seed.md"

# Every hook that Claude Code fires carries session_id + transcript_path + cwd
# in its stdin payload. We cheaply stamp these into the transport artifact
# under extras.active_session, turning every hook tick into a first-class
# "this is the live session" heartbeat. bridge_resume.discover_current_session_id
# prefers the stamped identity over the fragile mtime-based guess.
IDENTITY_CAPTURE_ACTIONS = {
    "session-start",
    "subagent-start",
    "user-prompt",
    "pre-tool",
    "post-tool",
    "precompact",
    "postcompact",
    "session-end",
    "stop",
}


def _read_stdin_bounded() -> str:
    """Read hook stdin without waiting for EOF or buffering unbounded input."""
    try:
        if sys.stdin.isatty():
            return ""
    except Exception:
        pass
    try:
        fd = sys.stdin.fileno()
    except Exception:
        # Non-fd-backed stdin (e.g. io.StringIO under test monkeypatching).
        # Fall back to a bounded direct read so the hook stays exercisable
        # from in-process tests without losing the production fd path below.
        try:
            text = sys.stdin.read(MAX_STDIN_BYTES)
        except Exception:
            return ""
        if isinstance(text, bytes):
            text = text.decode("utf-8", errors="replace")
        return (text or "").strip()

    chunks: List[bytes] = []
    total = 0
    first_read = True
    while total < MAX_STDIN_BYTES:
        timeout = (
            STDIN_FIRST_BYTE_TIMEOUT_SECONDS
            if first_read
            else STDIN_DRAIN_TIMEOUT_SECONDS
        )
        try:
            readable, _, _ = select.select([fd], [], [], timeout)
        except Exception:
            break
        if not readable:
            break
        first_read = False
        try:
            chunk = os.read(fd, min(65536, MAX_STDIN_BYTES - total))
        except BlockingIOError:
            break
        except OSError:
            break
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks).decode("utf-8", errors="replace").strip()


def _read_payload() -> Dict[str, Any]:
    raw = _read_stdin_bounded()
    if not raw:
        return {}
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _compact_hook_value(value: Any, depth: int = 0) -> Any:
    """Return a bounded JSON-compatible preview for hook telemetry handlers."""
    if isinstance(value, str):
        if len(value) <= MAX_OBSERVABILITY_VALUE_CHARS:
            return value
        return value[: MAX_OBSERVABILITY_VALUE_CHARS - 1].rstrip() + "…"
    if isinstance(value, (int, float, bool)) or value is None:
        return value
    if isinstance(value, list):
        if depth >= 2:
            return {"_type": "list", "len": len(value)}
        return [_compact_hook_value(item, depth + 1) for item in value[:MAX_OBSERVABILITY_ITEMS]]
    if isinstance(value, dict):
        if depth >= 2:
            return {"_type": "dict", "keys": sorted(str(key) for key in value.keys())[:MAX_OBSERVABILITY_ITEMS]}
        compact: Dict[str, Any] = {}
        for idx, (key, item) in enumerate(value.items()):
            if idx >= MAX_OBSERVABILITY_ITEMS:
                compact["_omitted_key_count"] = len(value) - MAX_OBSERVABILITY_ITEMS
                break
            compact[str(key)] = _compact_hook_value(item, depth + 1)
        return compact
    return _compact_hook_value(str(value), depth)


def _compact_hook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        str(key): _compact_hook_value(value)
        for key, value in (payload or {}).items()
    }


def _read_text_capped(
    path: Path,
    *,
    max_bytes: int = MAX_HOOK_SAFE_READ_BYTES,
    errors: str = "strict",
) -> Optional[str]:
    """Read only hook-safe files whose size is proven under the local byte cap."""
    try:
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size > max_bytes:
            return None
        with path.open("r", encoding="utf-8", errors=errors) as handle:
            return handle.read(max_bytes + 1)
    except OSError:
        return None


def _navigation_hint_message(anti_pattern_id: str) -> str:
    """Lookup a precomputed route hint from the hook-safe navigation card."""
    card = _read_json_file_safe(NAVIGATION_HINT_CARD_PATH)
    if card.get("schema_version") != "runtime_hook_navigation_hints_v0":
        return ""
    hints = card.get("hints")
    if not isinstance(hints, dict):
        return ""
    row = hints.get(anti_pattern_id)
    if not isinstance(row, dict):
        aliases = card.get("aliases")
        alias_key = aliases.get(anti_pattern_id) if isinstance(aliases, dict) else None
        row = hints.get(alias_key) if isinstance(alias_key, str) else None
    message = row.get("message") if isinstance(row, dict) else ""
    return str(message).strip() if message else ""


def _read_transport_safe() -> Optional[Dict[str, Any]]:
    """Read the one-shot session transport artifact, honoring the consumed marker.

    Returns None for records that already have `consumed_at` set. Otherwise
    reads, marks-consumed, and returns the record. This is the guard that
    prevents stale launch summaries from being re-injected into every new
    SessionStart / PostCompact after the original session already ingested
    the transport. Without this guard, the same "Review required." block
    kept replaying because `mark_consumed` only stamped a timestamp without
    hiding the record from subsequent reads.
    """
    def _load_raw() -> Optional[Dict[str, Any]]:
        raw = _read_text_capped(TRANSPORT_PATH, max_bytes=MAX_HOOK_SAFE_READ_BYTES)
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except Exception:
            return None

    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.meta.bridge.session_transport import read_transport, mark_consumed
        record = read_transport()
    except Exception:
        record = _load_raw()
        mark_consumed = None  # type: ignore[assignment]

    if not record:
        return None
    if record.get("consumed_at"):
        # Already-consumed one-shot record. Do NOT rehydrate.
        return None

    if mark_consumed is not None:
        try:
            mark_consumed()
        except Exception:
            pass
    return record


def _read_json_file_safe(path: Path) -> Dict[str, Any]:
    raw = _read_text_capped(path, max_bytes=MAX_HOOK_SAFE_READ_BYTES)
    if raw is None:
        return {}
    try:
        payload = json.loads(raw)
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _string(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _stamp_active_session_safe(action: str, payload: Dict[str, Any]) -> None:
    """Heartbeat the live Claude Code session identity into the transport.

    Pulls `session_id`, `transcript_path`, and `cwd` from the hook payload
    and merges them under `extras.active_session`. Swallows any import or
    write error — this MUST stay non-blocking so a broken transport never
    breaks the hook path. The payload shape is documented at
    https://docs.claude.com/en/docs/claude-code/hooks (every hook event
    includes session_id + transcript_path + cwd in its JSON stdin).
    """
    try:
        sys.path.insert(0, str(REPO_ROOT))
        from tools.meta.bridge.session_transport import stamp_active_session
        stamp_active_session(
            session_id=payload.get("session_id"),
            transcript_path=payload.get("transcript_path"),
            cwd=payload.get("cwd"),
            event=action,
        )
    except Exception:
        # Never let stamping failure break the hook.
        return


def _forward_agent_observability_safe(action: str, payload: Dict[str, Any]) -> None:
    """Materialize Claude hook evidence into the AgentTrace plane.

    Prefer the live FastAPI receiver when the server is running so WebSocket
    clients see the event immediately; fall back to direct JSONL append for
    hook invocations that happen while the backend is offline.
    """
    event_name = CANONICAL_HOOK_NAMES.get(action, action)
    trace_payload = _compact_hook_payload(payload or {})
    trace_payload.setdefault("hook_event_name", event_name)
    trace_payload.setdefault("action", action)
    encoded = json.dumps(trace_payload, ensure_ascii=False).encode("utf-8")
    try:
        req = urllib.request.Request(
            "http://127.0.0.1:8000/api/agent-observability/hook",
            data=encoded,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=0.2) as response:
            response.read(MAX_OBSERVABILITY_RESPONSE_BYTES)
        return
    except Exception:
        pass
    try:
        fallback_path = REPO_ROOT / AGENT_OBSERVABILITY_FALLBACK_REL
        fallback_path.parent.mkdir(parents=True, exist_ok=True)
        with fallback_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(trace_payload, ensure_ascii=False) + "\n")
    except Exception:
        return


def _read_resume_artifact(rel_path: Optional[str]) -> Optional[str]:
    """Load a resume/signal artifact and return a bounded preview."""
    if not rel_path:
        return None
    candidate = Path(rel_path)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    if not candidate.exists():
        return None
    text = _read_text_capped(
        candidate,
        max_bytes=max(MAX_HOOK_SAFE_READ_BYTES, ARTIFACT_PREVIEW_CHARS),
        errors="replace",
    )
    if text is None:
        return None
    text = text.strip()
    if len(text) > ARTIFACT_PREVIEW_CHARS:
        text = text[: ARTIFACT_PREVIEW_CHARS - 1].rstrip() + "…"
    return text


def _format_resume_brief(record: Dict[str, Any]) -> str:
    """Render a compact resume brief from the one-shot transport record."""
    parts: List[str] = []
    parts.append("## Resume brief")
    parts.append("- source: `tools/meta/bridge/claude_session_transport.json`")
    parts.append(f"- launch_mode: `{record.get('launch_mode')}`")
    parts.append(f"- launched_by: `{record.get('launched_by')}`")
    parts.append(f"- generated_at: `{record.get('generated_at')}`")
    if record.get("signal_kind"):
        parts.append(f"- signal_kind: `{record.get('signal_kind')}`")
    if record.get("summary"):
        parts.append(f"- summary: {record.get('summary')}")
    if record.get("session_id"):
        parts.append(f"- session_id: `{record.get('session_id')}`")
    if record.get("session_url"):
        parts.append(f"- session_url: `{record.get('session_url')}`")
    if record.get("notes"):
        first_note = next(
            (str(note).strip() for note in record.get("notes") or [] if str(note).strip()),
            None,
        )
        if first_note:
            parts.append(f"- note: {first_note}")

    next_steps: List[str] = []
    if record.get("resume_artifact_path"):
        next_steps.append(
            f"Open `{record.get('resume_artifact_path')}` for the persisted continuation state."
        )
    if record.get("signal_artifact_path"):
        next_steps.append(
            f"Inspect `{record.get('signal_artifact_path')}` for the originating signal context."
        )
    if not next_steps:
        next_steps.append("Continue from the persisted repo state; no extra artifacts were attached.")

    parts.append("## Next")
    parts.extend(f"- {step}" for step in next_steps)
    return "\n".join(parts)


def _subagent_payload_maps(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    maps: List[Dict[str, Any]] = []
    for candidate in (
        payload,
        payload.get("tool_input"),
        payload.get("input"),
        payload.get("toolInput"),
    ):
        if isinstance(candidate, dict):
            maps.append(candidate)
    return maps


def _extract_subagent_type(payload: Dict[str, Any]) -> str:
    for mapping in _subagent_payload_maps(payload):
        for key in ("subagent_type", "agent_name", "subagent_name", "agent"):
            token = _string(mapping.get(key))
            if token:
                return token
    return ""


def _load_subagent_actor_spec(subagent_type: str) -> Dict[str, Any]:
    if not subagent_type:
        return {}
    bootstrap = _read_json_file_safe(AGENT_BOOTSTRAP_CONFIG_PATH)
    raw_map = bootstrap.get("subagent_actor_map")
    if not isinstance(raw_map, dict):
        return {}
    entry = raw_map.get(subagent_type)
    return dict(entry) if isinstance(entry, dict) else {}


def _load_actor_context(actor_id: str) -> Dict[str, Any]:
    if not actor_id:
        return {}
    live_payload = _read_json_file_safe(AGENT_BOOTSTRAP_LIVE_PATH)
    rows = live_payload.get("actor_context_surfaces")
    if not isinstance(rows, list):
        return {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        if _string(row.get("actor_id")) == actor_id:
            return dict(row)
    return {}


def _resolve_repo_relative_path(token: str) -> str:
    candidate = Path(token)
    if candidate.is_absolute():
        try:
            return candidate.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
        except ValueError:
            return candidate.resolve().as_posix()
    return candidate.as_posix()


def _resolve_persona_path(spec: Dict[str, Any], subagent_type: str) -> Optional[Path]:
    token = _string(spec.get("persona_path")) or f".claude/agents/{subagent_type}.md"
    candidate = Path(token)
    if not candidate.is_absolute():
        candidate = REPO_ROOT / candidate
    return candidate if candidate.exists() else None


def _persona_required_reads(persona_path: Optional[Path]) -> List[str]:
    if persona_path is None:
        return []
    raw = _read_text_capped(persona_path, max_bytes=MAX_HOOK_SAFE_READ_BYTES, errors="replace")
    if raw is None:
        return []
    lines = raw.splitlines()

    in_required_reads = False
    reads: List[str] = []
    seen: set[str] = set()
    for raw_line in lines:
        line = raw_line.strip()
        if not in_required_reads:
            if REQUIRED_READS_HEADING_RE.match(line):
                in_required_reads = True
            continue
        if line.startswith("## "):
            break
        for match in re.findall(r"`([^`]+)`", raw_line):
            token = _resolve_repo_relative_path(match)
            if not token or token in seen:
                continue
            seen.add(token)
            reads.append(token)
    return reads


def _build_subagent_actor_context(payload: Dict[str, Any]) -> str:
    subagent_type = _extract_subagent_type(payload)
    if not subagent_type:
        return ""

    spec = _load_subagent_actor_spec(subagent_type)
    if not spec:
        return ""

    actor_id = _string(spec.get("actor_id")) or _string(spec.get("base_actor_id"))
    actor_context = _load_actor_context(actor_id)
    persona_path = _resolve_persona_path(spec, subagent_type)
    required_reads = _persona_required_reads(persona_path)

    blocks: List[str] = ["## Subagent actor context"]
    blocks.append(f"- subagent_type: `{subagent_type}`")
    label = _string(spec.get("label"))
    if label:
        blocks.append(f"- label: {label}")
    if persona_path is not None:
        blocks.append(
            f"- persona_path: `{_resolve_repo_relative_path(persona_path.as_posix())}`"
        )
    if actor_id:
        blocks.append(f"- actor_id: `{actor_id}`")
    if actor_context:
        actor_label = _string(actor_context.get("label"))
        if actor_label:
            blocks.append(f"- actor_label: {actor_label}")
        minimum_read_set_id = _string(actor_context.get("minimum_read_set_id"))
        if minimum_read_set_id:
            blocks.append(f"- minimum_read_set_id: `{minimum_read_set_id}`")
        runtime_surface_id = _string(actor_context.get("runtime_surface_id"))
        if runtime_surface_id:
            blocks.append(f"- runtime_surface_id: `{runtime_surface_id}`")
    session_id = _string(payload.get("session_id"))
    if session_id:
        blocks.append(f"- parent_session_id: `{session_id}`")
    cwd = _string(payload.get("cwd"))
    if cwd:
        blocks.append(f"- cwd: `{cwd}`")

    if required_reads:
        blocks.append("## Persona required reads")
        blocks.extend(f"- `{path}`" for path in required_reads)

    primary_commands = actor_context.get("primary_commands")
    if isinstance(primary_commands, list):
        commands = [_string(item) for item in primary_commands if _string(item)]
        if commands:
            blocks.append("## Shared actor commands")
            blocks.extend(f"- `{command}`" for command in commands)

    blocks.append("## Guardrail")
    blocks.append(
        "- This strip is actor-scoped context for a bounded subagent. It intentionally does not replay the parent's resume brief."
    )
    return "\n".join(blocks)


def _build_rehydration_context(action: str, payload: Dict[str, Any]) -> str:
    """Build action-scoped additionalContext for hook rehydration.

    Policy:
      - session-start: if a one-shot transport is pending, inject a compact resume
        brief plus any attached artifact previews.
      - postcompact: if a one-shot transport is pending, inject the same compact
        resume brief plus any attached artifact previews. No operator HUD — compaction
        already preserved the live thread.
      - subagent-start: no generic bootstrap block; inject only a bounded
        actor-specific strip when the payload resolves to a repo-authored persona.

    This keeps the hook transport-first instead of replaying the same operator HUD on
    every lifecycle event.
    """
    if action == "subagent-start":
        return _build_subagent_actor_context(payload)

    blocks: List[str] = []

    transport = _read_transport_safe()
    if transport:
        blocks.append(_format_resume_brief(transport))

        resume_preview = _read_resume_artifact(transport.get("resume_artifact_path"))
        if resume_preview:
            blocks.append(
                f"## Resume artifact ({transport.get('resume_artifact_path')})\n```\n{resume_preview}\n```"
            )

        signal_preview = _read_resume_artifact(transport.get("signal_artifact_path"))
        if signal_preview:
            blocks.append(
                f"## Signal artifact ({transport.get('signal_artifact_path')})\n```\n{signal_preview}\n```"
            )

    if not blocks:
        return ""

    combined = "\n\n".join(blocks)
    if len(combined) > MAX_CONTEXT_CHARS:
        combined = combined[: MAX_CONTEXT_CHARS - 1].rstrip() + "…"
    return combined


def _extract_user_prompt_text(payload: Dict[str, Any]) -> str:
    """Best-effort Claude hook payload prompt extraction without depending on one schema."""
    for key in ("prompt", "user_prompt", "message", "text", "input"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value
    messages = payload.get("messages")
    if isinstance(messages, list):
        parts: List[str] = []
        for item in messages[-3:]:
            if isinstance(item, dict):
                content = item.get("content")
                role = str(item.get("role") or "").lower()
                if role in {"user", "human"} and isinstance(content, str):
                    parts.append(content)
        if parts:
            return "\n\n".join(parts)
    return ""


def _large_instruction_residual_capture_hint(payload: Dict[str, Any]) -> str:
    """Nudge broad prompts toward Task Ledger residual binding without blocking."""
    prompt = _extract_user_prompt_text(payload)
    if not prompt:
        return ""
    line_count = prompt.count("\n") + 1
    marker_hits = sum(
        1
        for marker in (
            "deliverable",
            "workitem",
            "work item",
            "cap_",
            "todo",
            "follow-up",
            "rest of",
            "everything else",
            "next execution",
            "packet",
        )
        if marker in prompt.lower()
    )
    if (
        len(prompt) < LARGE_INSTRUCTION_PROMPT_CHARS
        and line_count < LARGE_INSTRUCTION_PROMPT_LINES
        and marker_hits < 3
    ):
        return ""
    return (
        "## Large instruction residual capture\n"
        "This prompt is broad enough that the current turn may execute only a slice. "
        "Before final response, bind the executed slice to the selected mission/WorkItem, "
        "then route every named durable remainder through an existing matching cap/WorkItem "
        "or a Task Ledger `quick-capture`. Native TODOs or final prose are scratch only; "
        "cite the cap_id/receipt, or state an explicit no-residual/no-op verdict."
    )


def _todo_residual_capture_hint(payload: Dict[str, Any]) -> str:
    """Nudge cross-session native TODO payloads toward durable Task Ledger binding."""
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name not in {"TodoWrite", "TaskCreate", "TaskUpdate", "TaskList", "spawn_task"}:
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    todo_values: List[str] = []
    todos = tool_input.get("todos")
    if isinstance(todos, list):
        for item in todos:
            if isinstance(item, dict):
                todo_values.extend(
                    str(item.get(key) or "")
                    for key in ("content", "title", "description", "activeForm")
                    if item.get(key)
                )
            elif isinstance(item, str):
                todo_values.append(item)
    else:
        todo_values.extend(
            str(tool_input.get(key) or "")
            for key in ("content", "title", "description", "task")
            if tool_input.get(key)
        )
    haystack = "\n".join(todo_values)
    if not haystack or not TODO_RESIDUAL_CUE_RE.search(haystack):
        return ""
    return (
        "## Native TODO residual capture\n"
        f"The pending `{tool_name}` payload uses cross-session residual language. "
        "Native TODOs are scratch only in this repo. Before final response, bind "
        "each durable remainder to an existing cap_*/WorkItem, create a Task Ledger "
        "`quick-capture`, or record an explicit no-residual/no-op disposition. "
        "Cite the cap_id or receipt when you mention it."
    )


def _cockpit_edit_counterinject(payload: Dict[str, Any]) -> str:
    """Counter-inject station_render override for edits under system/server/ui/.

    The harness `<preview_tools>` block tells Claude to reach for generic
    `preview_start` / `preview_snapshot` tools. For this repo, those are the
    wrong surface — `tools/meta/observability/station_render.py` is the owned
    artifact-first capture engine, wired to `station_views.json` and the
    cockpit's `captureMode.ts` readiness protocol, with chromium + webkit dual
    engines and pixel-diff compare. The skill
    `frontend_visual_verification.md` already marks the override in doctrine;
    this hook enforces the override at runtime so Claude does not need to
    re-derive the routing on every UI edit.
    """
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name not in COCKPIT_EDIT_TOOLS:
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    path_raw = (
        tool_input.get("file_path")
        or tool_input.get("filePath")
        or tool_input.get("notebook_path")
        or ""
    )
    path_str = str(path_raw)
    if not path_str:
        return ""
    # Normalise absolute paths relative to repo root.
    try:
        candidate = Path(path_str)
        if candidate.is_absolute():
            rel = candidate.relative_to(REPO_ROOT)
            rel_str = str(rel)
        else:
            rel_str = path_str.lstrip("./")
    except Exception:
        rel_str = path_str
    if not rel_str.startswith(COCKPIT_SOURCE_PREFIX):
        return ""
    return (
        "## Cockpit edit — visual verification override\n"
        f"You just edited `{rel_str}`. For files under `{COCKPIT_SOURCE_PREFIX}`, "
        "this repo **overrides** the harness `<preview_tools>` block. Do NOT call "
        "`preview_start` / `preview_snapshot` / `preview_screenshot` for this "
        "change; the owned verification engine is "
        "`tools/meta/observability/station_render.py` (chromium + webkit dual "
        "engines, pixel-diff compare, wired to `station_views.json` and "
        "`captureMode.ts`).\n\n"
        "If the change is observable in the browser, refresh the per-view "
        "observation packet first, then use its screenshot ledger to select the "
        "render target:\n"
        "```bash\n"
        "./repo-python tools/meta/observability/view_quality_census.py --all \\\n"
        "  --changed-path <repo-relative-path> \\\n"
        "  --out state/observability/view_quality/frontend_view_quality_census_v0.json \\\n"
        "  --write-view-packets \\\n"
        "  --write-visual-settlement\n"
        "# inspect state/observability/view_quality/views/<view_id>.{json,md}\n"
        "# affected packets expose screenshot_ledger.refresh_due + refresh_command\n"
        "# settlement receipt: state/observability/view_quality/frontend_visual_settlement_v0.json\n"
        "./repo-python -m tools.meta.observability.station_render preflight\n"
        "./repo-python -m tools.meta.observability.station_render render --view <slug> --viewport fhd_landscape\n"
        "# then, after the follow-up edit, re-render and diff:\n"
        "./repo-python -m tools.meta.observability.station_render diff --run-a <baseline> --run-b <after> --engine chromium\n"
        "```\n"
        "If the change is type-only, style-token-only, or otherwise not "
        "observable in the browser (per `<when_to_verify>`), skip verification "
        "and say so. Governing doctrine: "
        "`codex/doctrine/skills/frontend/frontend_visual_verification.md` + "
        "`codex/doctrine/paper_modules/station_render_engine.md` + "
        "`codex/standards/std_station_aesthetic.json::frontend_wide_census_v0.per_view_observation_packet_v0`."
    )


def _hook_edit_target_relpath(payload: Dict[str, Any]) -> str:
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    path_raw = (
        tool_input.get("file_path")
        or tool_input.get("filePath")
        or tool_input.get("notebook_path")
        or ""
    )
    path_str = str(path_raw)
    if not path_str:
        return ""
    try:
        candidate = Path(path_str)
        if candidate.is_absolute():
            rel = candidate.relative_to(REPO_ROOT)
            return str(rel)
    except Exception:
        pass
    return path_str.lstrip("./")


def _seed_substrate_edit_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name not in SEED_SUBSTRATE_EDIT_TOOLS:
        return ""
    rel_path = _hook_edit_target_relpath(payload)
    if not rel_path or not rel_path.startswith("obsidian/"):
        return ""
    if rel_path.endswith(RAW_SEED_SUFFIX):
        return (
            "## Seed substrate edit guardrail\n"
            f"You just edited `{rel_path}`. `raw_seed.md` is operator voice only. "
            "Do NOT put agent-authored prose here and do NOT keep editing this file "
            "with Edit/Write tools from an agent session.\n\n"
            "Use one of these instead:\n"
            "- operator voice capture: `python3 kernel.py --append-raw-seed <family> \"<verbatim operator paragraph>\" [--raw-seed-heading <slug>] --live`\n"
            "- agent voice capture: `python3 kernel.py --append-agent-seed <family> --author <agent_id> [--gesture \"<slug>\"] \"<agent-authored paragraph>\" --live`\n"
            "- historical cleanup: `python3 kernel.py --migrate-agent-section <par_id> --live`\n\n"
            "If this edit introduced agent-authored prose into `raw_seed.md`, treat that as a contract violation and repair it before continuing."
        )
    if rel_path.endswith(AGENT_SEED_SUFFIX):
        return (
            "## Agent-seed edit guardrail\n"
            f"You just edited `{rel_path}`. `agent_seed.md` is the correct substrate for agent voice, "
            "but the sanctioned write path is still `python3 kernel.py --append-agent-seed --author <agent_id> ... --live`.\n\n"
            "Direct file edits are for explicit migration or sync-owned repair only. If you were trying to record a new agent-authored paragraph, use the kernel append command instead."
        )
    return ""


def _shell_tokens(command: str) -> List[str]:
    try:
        lexer = shlex.shlex(command, posix=True, punctuation_chars=";&|")
        lexer.whitespace_split = True
        lexer.commenters = ""
        return list(lexer)
    except Exception:
        return command.split()


def _normalise_shell_command_word(token: str) -> str:
    word = token.strip()
    if word.startswith("./"):
        word = word.rsplit("/", 1)[-1]
    if "/" in word:
        word = word.rsplit("/", 1)[-1]
    return word


def _looks_like_env_assignment(token: str) -> bool:
    return bool(re.match(r"^[A-Za-z_][A-Za-z0-9_]*=.*", token))


def _bash_native_fallthrough_verb(command: str) -> str:
    """Return the first ambient navigation verb invoked as a shell command."""
    tokens = _shell_tokens(command)
    at_command_start = True
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in SHELL_COMMAND_BOUNDARIES:
            at_command_start = True
            i += 1
            continue
        if not at_command_start:
            i += 1
            continue

        word = _normalise_shell_command_word(token)
        if _looks_like_env_assignment(token):
            i += 1
            continue
        if word in BASH_NATIVE_FALLTHROUGH_VERBS:
            return word
        if word in SHELL_TRANSPARENT_PREFIXES:
            i += 1
            continue
        if word == "env":
            i += 1
            while i < len(tokens) and (
                tokens[i].startswith("-") or _looks_like_env_assignment(tokens[i])
            ):
                i += 1
            continue
        if word == "timeout":
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
            if i < len(tokens):
                i += 1
            continue
        if word in SHELL_SEGMENT_PREFIXES:
            i += 1
            while i < len(tokens) and tokens[i] not in SHELL_COMMAND_BOUNDARIES:
                i += 1
            continue

        at_command_start = False
        i += 1
    return ""


def _bash_command_uses_kernel_pipeline(command: str, verb: str) -> bool:
    """Return True if `verb` appears as a post-pipe filter after a kernel.py / repo-python segment.

    The detector is intentionally conservative: it only fires when (a) a `|` boundary occurs
    AFTER a segment containing a kernel command token AND (b) the matched fallthrough `verb`
    is invoked at a later command-start position. False positives just produce a slightly
    more specific hint message; false negatives fall back to the per-verb suggestion path.
    """
    if not verb:
        return False
    tokens = _shell_tokens(command)
    pipe_seen_after_kernel = False
    seen_kernel_token_in_segment = False
    at_command_start = True
    for token in tokens:
        if token in SHELL_COMMAND_BOUNDARIES:
            if token == "|" and seen_kernel_token_in_segment:
                pipe_seen_after_kernel = True
            seen_kernel_token_in_segment = False
            at_command_start = True
            continue
        if any(hint in token for hint in KERNEL_COMMAND_TOKEN_HINTS):
            seen_kernel_token_in_segment = True
        if at_command_start:
            normalized = _normalise_shell_command_word(token)
            if normalized == verb and pipe_seen_after_kernel:
                return True
            at_command_start = False
    return False


def _repo_python_invocation_count(command: str) -> int:
    """Count repo Python/kernel command starts inside one Bash tool call."""
    tokens = _shell_tokens(command)
    count = 0
    at_command_start = True
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token in SHELL_COMMAND_BOUNDARIES:
            at_command_start = True
            i += 1
            continue
        if not at_command_start:
            i += 1
            continue

        word = _normalise_shell_command_word(token)
        if _looks_like_env_assignment(token):
            i += 1
            continue
        if word in SHELL_TRANSPARENT_PREFIXES:
            i += 1
            continue
        if word == "env":
            i += 1
            while i < len(tokens) and (
                tokens[i].startswith("-") or _looks_like_env_assignment(tokens[i])
            ):
                i += 1
            continue
        if word == "timeout":
            i += 1
            while i < len(tokens) and tokens[i].startswith("-"):
                i += 1
            if i < len(tokens):
                i += 1
            continue
        if word in SHELL_SEGMENT_PREFIXES:
            i += 1
            while i < len(tokens) and tokens[i] not in SHELL_COMMAND_BOUNDARIES:
                i += 1
            continue
        if word in REPO_PYTHON_COMMAND_WORDS:
            count += 1

        at_command_start = False
        i += 1
    return count


def _mentioned_task_ledger_view_count(command: str) -> int:
    matches = re.findall(r"state/task_ledger/views/[A-Za-z0-9_.-]+\.json", command)
    return len(set(matches))


def _bash_command_efficiency_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name != "Bash":
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    command = str(tool_input.get("command") or "").strip()
    if not command:
        return ""

    repo_invocations = _repo_python_invocation_count(command)
    view_fanout = _mentioned_task_ledger_view_count(command)
    blocks: List[str] = []
    if repo_invocations >= 2:
        route_message = _navigation_hint_message("multi_repo_python_batch")
        blocks.append(
            f"This Bash command starts {repo_invocations} repo Python/kernel commands in one "
            "tool call. In concurrent agent runs, that shape multiplies cold starts and buffers "
            "all output behind one shell turn. Run one control command first, then follow its "
            "selected drilldown: `./repo-python kernel.py --entry \"<task>\" --context-budget 12000`, "
            "`./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000`, or "
            "`./repo-python kernel.py --navigation-metabolism \"<task>\" --metabolism-profile quick --context-budget 12000`."
            + (f" {route_message}" if route_message else "")
        )
    if view_fanout >= 3:
        blocks.append(
            f"This command names {view_fanout} Task Ledger view JSON files. Use the existing "
            "cluster surface instead of raw view fan-out: "
            "`./repo-python kernel.py --option-surface task_ledger --band cluster_flag`, then "
            "`./repo-python kernel.py --option-surface task_ledger --band card --ids <work_item_id>`."
        )
    if not blocks:
        return ""
    return (
        "## Command efficiency guard\n"
        + "\n\n".join(f"- {block}" for block in blocks)
        + "\n\nDo not batch the whole ladder in one Bash command. Persist truly long diagnostics to a temp file, "
        "then inspect a bounded JSON summary or a selected row."
    )


def _high_volume_read_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name != "Read":
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    raw_path = str(tool_input.get("file_path") or tool_input.get("path") or "").strip()
    if not raw_path:
        return ""
    path = Path(raw_path)
    try:
        rel_path = str(path.resolve().relative_to(REPO_ROOT)) if path.is_absolute() else raw_path
    except Exception:
        rel_path = raw_path
    rel_path = rel_path.lstrip("./")
    message = HIGH_VOLUME_READ_FILES.get(rel_path)
    if message is None:
        for prefix, hint in HIGH_VOLUME_READ_PREFIXES.items():
            if rel_path.startswith(prefix):
                message = hint
                break
    if not message:
        return ""
    return (
        "## High-volume projection read hint\n"
        f"`{rel_path}` is a high-volume projection surface. {message}\n\n"
        "Continue only if a control packet already selected this exact file as evidence."
    )


def _command_mentions_existing_path(command: str) -> bool:
    """Return True when the shell command names a concrete existing repo path."""
    for token in _shell_tokens(command):
        stripped = token.strip("'\"")
        if not stripped or stripped.startswith("-"):
            continue
        if "/" not in stripped and "." not in stripped:
            continue
        candidate = (REPO_ROOT / stripped).resolve() if not stripped.startswith("/") else Path(stripped)
        try:
            candidate.relative_to(REPO_ROOT)
        except ValueError:
            continue
        if candidate.exists():
            return True
    return False


def _tool_input_mentions_existing_path(tool_input: Dict[str, Any]) -> bool:
    """Return True when a typed tool input names a concrete existing repo path."""
    for key in ("path", "file_path"):
        raw_path = str(tool_input.get(key) or "").strip()
        if not raw_path or raw_path in {".", "./"}:
            continue
        path = Path(raw_path)
        candidate = (REPO_ROOT / path).resolve() if not path.is_absolute() else path.resolve()
        try:
            candidate.relative_to(REPO_ROOT.resolve())
        except ValueError:
            continue
        if candidate.exists():
            return True
    return False


def _typed_discovery_first_contact_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name not in TYPED_DISCOVERY_TOOL_NAMES:
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    if _tool_input_mentions_existing_path(tool_input):
        return ""

    route_message = _navigation_hint_message("anti_pattern_grep_before_kernel")
    route_repair_note = f"\n\n**Route intervention:** {route_message}" if route_message else ""
    return (
        "## Navigation first-contact hint\n"
        f"The pending `{tool_name}` tool call looks like repo discovery without a selected concrete "
        "path. Session diagnostics classify that shape as `anti_pattern_grep_before_kernel` "
        "when it happens before the kernel ladder.\n\n"
        "Run the canonical entry/control route first when this is first-contact exploration: "
        "`./repo-python kernel.py --entry \"<task>\" --context-budget 12000`, then use "
        "`--context-pack` or a selected option-surface drilldown if the entry packet asks for it."
        f"{route_repair_note}\n\n"
        "Continue if a control packet already selected this exact search as evidence."
    )


# Banned git subcommands when invoked raw against the shared `.git/index`.
# Includes both staging and commit forms — any raw `git add` is unsafe under
# concurrent agents, not only `-A`/`--all`/`.`, because selective `git add`
# also writes through the shared index and can be racey. Per-segment env
# assignments and the scoped_commit.py / ./checkpoint actuators are the
# allowed paths; the explicit operator override is `AIW_ALLOW_RAW_GIT_COMMIT=1`.
BANNED_RAW_GIT_SUBCOMMANDS = ("add", "commit")
# Sanctioned-actuator command-start tokens. A segment whose first non-env,
# non-wrapper token starts with one of these is allowed regardless of
# subsequent git-shaped tokens (the actuator itself is responsible for
# never invoking dangerous git shapes against the shared index).
RAW_GIT_GUARD_SANCTIONED_ACTUATOR_PREFIXES = (
    "scoped_commit.py",
    "checkpoint",  # ./checkpoint — matched after _normalise_shell_command_word
)
# Git "global options" that may appear between `git` and the subcommand.
# Some take a value; some don't. Detection is conservative: any flag
# starting with `-` is consumed as a global option until we hit the
# subcommand token. This is safe because the subcommand is always a
# bare word (no leading dash).
GIT_GLOBAL_OPTS_TAKING_VALUE = (
    "-C", "-c", "--git-dir", "--work-tree", "--namespace", "--super-prefix",
    "--exec-path",  # also `--exec-path=<value>` form, handled below
)


def _split_command_segments(tokens: List[str]) -> List[List[str]]:
    """Split tokenised command into shell-command segments at boundaries."""
    segments: List[List[str]] = []
    current: List[str] = []
    for token in tokens:
        if token in SHELL_COMMAND_BOUNDARIES:
            if current:
                segments.append(current)
                current = []
            continue
        current.append(token)
    if current:
        segments.append(current)
    return segments


def _strip_segment_wrappers(segment: List[str]) -> tuple[List[str], List[str]]:
    """Walk past env assignments and transparent wrappers at a segment's start.

    Returns ``(env_assignments, remaining_tokens)`` where ``env_assignments``
    is the list of literal ``VAR=value`` tokens that appeared before the
    actual command word, and ``remaining_tokens`` begins at the actual
    command token (or is empty if the segment is wrappers-only).

    Recognised wrappers consumed transparently:
      - leading env assignments (``FOO=bar git ...``)
      - ``env`` / ``env -i`` / ``env FOO=bar git ...``
      - ``command`` / ``builtin`` / ``time`` / ``noglob``
      - ``timeout <seconds> git ...`` / ``timeout 10s git ...``
      - subshell-init prefixes ``cd <dir> && ...`` are NOT consumed here
        because they are split off by ``_split_command_segments`` (the
        boundary token ``&&`` ends the ``cd`` segment).
    """
    env_assignments: List[str] = []
    i = 0
    while i < len(segment):
        token = segment[i]
        if _looks_like_env_assignment(token):
            env_assignments.append(token)
            i += 1
            continue
        normalized = _normalise_shell_command_word(token)
        if normalized in SHELL_TRANSPARENT_PREFIXES:
            i += 1
            continue
        if normalized == "env":
            i += 1
            # Consume env-tool flags and additional env assignments.
            while i < len(segment) and (
                segment[i].startswith("-") or _looks_like_env_assignment(segment[i])
            ):
                if _looks_like_env_assignment(segment[i]):
                    env_assignments.append(segment[i])
                i += 1
            continue
        if normalized == "timeout":
            i += 1
            # `timeout` may take optional flags then a duration.
            while i < len(segment) and segment[i].startswith("-"):
                i += 1
            if i < len(segment):
                i += 1  # duration
            continue
        break
    return env_assignments, segment[i:]


def _git_subcommand(tokens_after_git: List[str]) -> Optional[str]:
    """Return the subcommand of a `git ...` invocation, skipping global opts.

    ``tokens_after_git`` is the token list AFTER the `git` command word.
    Walks past any `-C <p>`, `-c <kv>`, `--git-dir <p>`, `--work-tree <p>`,
    `--no-pager`, `--exec-path[=<p>]`, etc., and returns the next bare
    word (the subcommand). Returns None if no subcommand is present.
    """
    i = 0
    while i < len(tokens_after_git):
        tok = tokens_after_git[i]
        if not tok.startswith("-"):
            return tok
        # Flags taking a value (next token).
        if tok in GIT_GLOBAL_OPTS_TAKING_VALUE:
            i += 2
            continue
        # `--flag=value` or bare `--flag`.
        i += 1
    return None


def _segment_is_sanctioned_actuator(words: List[str]) -> bool:
    """Return True if the segment's actual command is a sanctioned actuator.

    Recognises:
      - `./checkpoint ...` / `checkpoint ...`
      - `./repo-python tools/meta/control/scoped_commit.py ...`
        (or any path ending with `scoped_commit.py`)
      - direct `python <...>/scoped_commit.py ...`
    """
    if not words:
        return False
    first = _normalise_shell_command_word(words[0])
    if first.startswith("scoped_commit.py") or first == "scoped_commit.py":
        return True
    if first == "checkpoint":
        return True
    if first in REPO_PYTHON_COMMAND_WORDS or first == "repo-python":
        # Look for scoped_commit.py anywhere in the script-name argument.
        for tok in words[1:]:
            if tok.startswith("-"):
                continue  # flag
            if tok.endswith("scoped_commit.py") or tok == "scoped_commit.py":
                return True
            # First non-flag positional that is not scoped_commit.py:
            # not a sanctioned actuator.
            return False
    return False


def _segment_has_explicit_override(env_assignments: List[str]) -> bool:
    """Return True if the segment's env assignments include
    `AIW_ALLOW_RAW_GIT_COMMIT=1` (or any non-empty value).

    The override must be a real env-assignment for the same command segment,
    not merely a substring elsewhere in the command line. Quoted prose,
    echoed text, or assignments in other segments do not count.
    """
    for assignment in env_assignments:
        name, _, value = assignment.partition("=")
        if name == "AIW_ALLOW_RAW_GIT_COMMIT" and value.strip().strip("\"'"):
            return True
    return False


def _raw_shared_index_git_guard(payload: Dict[str, Any]) -> str:
    """Hard-block raw shared-index git invocations from agent sessions.

    Parses the Bash command into shell-command segments and inspects each
    segment's actual command (after stripping env assignments and
    transparent wrappers). Returns a non-empty block reason if ANY segment
    invokes a banned raw git subcommand (`git add`, `git commit`) against
    the shared index without an explicit per-segment
    `AIW_ALLOW_RAW_GIT_COMMIT=<nonempty>` override or a sanctioned-actuator
    command word.

    This replaces an earlier lexical regex over the whole command string
    that produced two failure modes: (a) false positives on quoted/echoed
    strings containing the banned phrases, and (b) substring bypass via
    cosmetic mentions of test-harness paths anywhere in the line.

    Closes the largest residual trigger of the multi-agent commit-boundary
    contamination class tracked at
    cap_quick_concurrent_broad_sweep_commit_absorbed_i_6cc3039a3fde:
    `git add` writes through the shared `.git/index` and absorbs concurrent
    agents' tracked-but-uncommitted edits; `git commit` (with or without
    `-a`/`--all`/`-am`/`--no-verify`) then commits the absorbed edits — and
    as live commit 486014a07 demonstrated, can also revert another agent's
    recent commit by including older staged content (backward-revert). The
    sanctioned actuators (`scoped_commit.py`, `./checkpoint` as of
    094efe3b4) use private GIT_INDEX_FILE + commit-tree + update-ref CAS
    and bypass these failure modes structurally.
    """
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name != "Bash":
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    command = str(tool_input.get("command") or "").strip()
    if not command:
        return ""

    try:
        tokens = _shell_tokens(command)
    except Exception:
        return ""

    for segment in _split_command_segments(tokens):
        env_assignments, words = _strip_segment_wrappers(segment)
        if not words:
            continue
        if _segment_is_sanctioned_actuator(words):
            continue
        if _segment_has_explicit_override(env_assignments):
            continue
        # Identify a raw `git <subcommand>` invocation.
        first = _normalise_shell_command_word(words[0])
        if first != "git":
            continue
        subcommand = _git_subcommand(words[1:])
        if subcommand is None:
            continue
        if subcommand not in BANNED_RAW_GIT_SUBCOMMANDS:
            continue
        return (
            f"Refusing raw `git {subcommand}` against the shared "
            f"`.git/index` from an agent session. Raw `git {subcommand}` "
            f"writes through the shared index and absorbs concurrent "
            f"agents' tracked-but-uncommitted edits into your staged set "
            f"(forward-absorption) — and on commit can revert another "
            f"agent's recent work by including older staged content "
            f"(backward-revert). See live history: commits b0a857167 and "
            f"486014a07. Tracked at "
            f"cap_quick_concurrent_broad_sweep_commit_absorbed_i_6cc3039a3fde.\n\n"
            f"Use a sanctioned actuator instead:\n"
            f"- `./repo-python tools/meta/control/scoped_commit.py "
            f"full-paths --path <p1> [--path <p2> ...] --message \"...\"` "
            f"(clean owned paths; refuses multi-hunk tracked files unless "
            f"explicitly acknowledged; private GIT_INDEX_FILE + HEAD CAS)\n"
            f"- `./repo-python tools/meta/control/scoped_commit.py "
            f"patch --patch-file <hunk.patch> --path <p> --message \"...\"` "
            f"(entangled files; isolate one hunk)\n"
            f"- `./checkpoint \"<message>\"` (bankruptcy lane only; "
            f"private-index since 094efe3b4)\n\n"
            f"Genuine manual override: prefix this command segment with "
            f"`AIW_ALLOW_RAW_GIT_COMMIT=1` (must be an actual env "
            f"assignment for this segment, not a quoted string elsewhere "
            f"in the line)."
        )
    return ""


def _bash_native_fallthrough_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name != "Bash":
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    command = str(tool_input.get("command") or "").strip()
    if not command:
        return ""
    verb = _bash_native_fallthrough_verb(command)
    if not verb:
        return ""

    suggestion = BASH_VERB_TOOL_SUGGESTIONS.get(
        verb,
        "Prefer the repo's typed navigation tools when they are in your active tool set: "
        "`Read` / `Edit` plus `Grep` / `Glob` (when present) plus `kernel.py --info`, "
        "`--pulse`, `--paper-module`, `--docs-route`, `--navigate`, `--locate`, "
        "`--compile`. If `Grep` / `Glob` are not in the active tool set, Bash `grep` / "
        "`find` remain acceptable narrow fallbacks.",
    )
    route_repair_note = ""
    if verb in {"grep", "rg", "find"} and not _command_mentions_existing_path(command):
        route_message = _navigation_hint_message("anti_pattern_grep_before_kernel")
        if route_message:
            route_repair_note = "\n\n**Route intervention:** " + route_message

    context_note = ""
    try:
        if _bash_command_uses_kernel_pipeline(command, verb):
            context_note = (
                f"\n\n**Detected as post-pipe filter after a kernel command.** Kernel output is "
                f"already structured JSON in compact mode and supports `--full` for the unbounded "
                f"payload. Filtering with `{verb}` after `kernel.py` / `repo-python` discards the "
                f"structured payload and trains the wrong reflex. Read the JSON directly, pass "
                f"`--full`, or use the kernel command's own filter flags instead."
            )
    except Exception:
        # Detector must never raise out of the hook; fall back to the per-verb suggestion alone.
        context_note = ""

    return (
        "## Navigation training-loop hint\n"
        f"The pending Bash command invokes `{verb}` as a shell command. Session diagnostics show "
        f"this verb is a dominant navigation fallthrough in this repo.\n\n"
        f"**Better move for `{verb}`:** {suggestion}{route_repair_note}{context_note}\n\n"
        "Other typed kernel surfaces if you need broader navigation: `--info`, `--pulse`, "
        "`--paper-module`, `--docs-route`, `--navigate`, `--locate`, `--compile`. If this is an "
        "exact literal check after the target is already known, continue; this hint is steering, "
        "not a block."
    )


def _token_after(tokens: List[str], flag: str) -> str:
    try:
        idx = tokens.index(flag)
    except ValueError:
        return ""
    if idx + 1 >= len(tokens):
        return ""
    return tokens[idx + 1]


def _paper_lattice_slug_exists(slug: str) -> bool:
    if not slug or not PAPER_LATTICE_SLUG_RE.fullmatch(slug):
        return False
    return (REPO_ROOT / "codex/doctrine/paper_modules" / f"{slug}.md").exists()


def _kernel_navigation_fallthrough_counterinject(payload: Dict[str, Any]) -> str:
    tool_name = str(payload.get("tool_name") or payload.get("tool") or "")
    if tool_name != "Bash":
        return ""
    tool_input = payload.get("tool_input") or payload.get("input") or {}
    if not isinstance(tool_input, dict):
        return ""
    command = str(tool_input.get("command") or "").strip()
    if not command or not any(hint in command for hint in KERNEL_COMMAND_TOKEN_HINTS):
        return ""

    tokens = _shell_tokens(command)
    normalized_tokens = [_normalise_shell_command_word(token) for token in tokens]
    blocks: List[str] = []

    if "--help" in tokens and any(token == "kernel.py" or "repo-python" in token for token in normalized_tokens + tokens):
        route_message = _navigation_hint_message("raw_kernel_help_first_contact")
        blocks.append(
            "raw `kernel.py --help` is a keyword-guessing surface in this repo. "
            "Use `./repo-python kernel.py --entry \"<task>\" --context-budget 12000` "
            "for the control packet, or `./repo-python kernel.py --context-pack \"<task>\" --context-budget 12000` "
            "for a task-conditioned packet; `--kind-atlas` is an atlas drilldown after that."
            + (f" {route_message}" if route_message else "")
        )

    if any(token in GUESSY_KERNEL_FLAGS for token in tokens):
        guessed = next((token for token in tokens if token in GUESSY_KERNEL_FLAGS), "")
        blocks.append(
            f"`{guessed}` looks like a guessed navigation flag. The shipped composer is "
            "`--context-pack` / `--navigation-context-pack`; start there, then drill by stable ids."
        )

    if "--skill-find" in tokens:
        route_message = _navigation_hint_message("skill_find_first_contact")
        blocks.append(
            "Coverage-first navigation beats lexical-luck search. `--skill-find` is a legacy "
            "evidence drilldown after a skill id or family is already selected, not the "
            "first-contact surface for capability discovery. Start with `--entry \"<task>\"`, "
            "`--context-pack \"<task>\"`, or `--option-surface skills --band cluster_flag`; "
            "`--kind-atlas` is an explicit browse drilldown, not a command to batch with other rungs. "
            "continue only if this query is already an exact lookup, coverage-surface drilldown, "
            "or fallback after coverage-first routing failed."
            + (f" {route_message}" if route_message else "")
        )

    lattice_flag = "--paper-lattice" if "--paper-lattice" in tokens else "--dynamic-paper" if "--dynamic-paper" in tokens else ""
    if lattice_flag:
        slug = _token_after(tokens, lattice_flag)
        if not _paper_lattice_slug_exists(slug):
            requested = slug or "<missing>"
            route_message = _navigation_hint_message("paper_lattice_before_slug_selection")
            blocks.append(
                f"`{lattice_flag} {requested}` is not a first-contact paper/doctrine search route. "
                "The lattice is a stable-slug drilldown, not free-text search. Start with `--context-pack \"<task>\"` or "
                "`--option-surface paper_modules --band cluster_flag`, then open the lattice only "
                "for an existing selected paper-module slug."
                + (f" {route_message}" if route_message else "")
            )

    surface = _token_after(tokens, "--option-surface")
    band = _token_after(tokens, "--band")
    if surface in HIGH_CARDINALITY_OPTION_SURFACES and band == "flag" and "--ids" not in tokens:
        safe_band = "cluster_flag" if surface in CLUSTER_FIRST_OPTION_SURFACES else "card --ids <id>"
        blocks.append(
            f"`--option-surface {surface} --band flag` without `--ids` expands a high-cardinality "
            f"row set. Use `--context-pack \"<task>\"` first, or `--option-surface {surface} "
            f"--band {safe_band}` for bounded drilldown."
        )

    output_band = _token_after(tokens, "--output-band")
    if "--paper-module" in tokens and output_band == "flag":
        route_message = _navigation_hint_message("anti_pattern_paper_module_skip")
        blocks.append(
            "`--paper-module ... --output-band flag` has already proven it can spill a "
            "supposed low band into persisted output. Use `--context-pack \"<task>\"`, "
            "`--option-surface paper_modules --band cluster_flag`, or a single "
            "`--row paper_modules:<slug> --band card` drilldown."
            + (f" {route_message}" if route_message else "")
        )

    if not blocks:
        return ""
    return (
        "## Kernel navigation control-plane hint\n"
        + "\n\n".join(f"- {block}" for block in blocks)
        + "\n\nThis is steering, not a block; continue only if the target and bounded output shape are already explicit."
    )


def build_stop_lifecycle_signal_row(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Build the reactions_engine-shaped JSONL row for a Stop hook event.

    Schema is intentionally a strict subset of `orchestration_events.jsonl`:
    `ts` / `source` / `kind` / `payload` / `stable_digest`. The stable_digest
    is deterministic over (session_id, action, hook_event) so reactions_engine
    can dedupe re-fires of the same Stop boundary without seeing duplicate
    rows. Exposed at module top level so the synthetic payload test can call
    it without invoking the full hook dispatcher.

    Per `codex/doctrine/paper_modules/runtime_hook_ladder.md` (Stop event row
    in the ladder map): "Stop -> reactions_engine boundary signal,
    consolidation". This helper is the runtime-side projection of that
    contract.
    """
    session_id = _string(payload.get("session_id"))
    transcript_path = _string(payload.get("transcript_path")) or None
    cwd = _string(payload.get("cwd")) or None
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    digest_input = json.dumps(
        {
            "session_id": session_id,
            "action": "stop",
            "hook_event": "Stop",
            "agent_surface": "claude",
        },
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    stable_digest = hashlib.sha256(digest_input).hexdigest()[:32]
    return {
        "ts": ts,
        "source": "claude_hook",
        "kind": "session_lifecycle_boundary",
        "payload": {
            "hook_event": "Stop",
            "agent_surface": "claude",
            "boundary": "stop",
            "session_id": session_id,
            "transcript_path": transcript_path,
            "cwd": cwd,
        },
        "stable_digest": stable_digest,
    }


def _emit_stop_lifecycle_signal(payload: Dict[str, Any]) -> int:
    """Write the Stop lifecycle row to the reactions journal.

    Returns 0 on success or skip (no session_id), 1 on write failure
    (operator-visible warning per the 0/1/2 hook exit-code contract canonised
    in `codex/doctrine/paper_modules/runtime_hook_ladder.md`).

    The primary target is `tools/meta/control/orchestration_events.jsonl` —
    the existing reactions_engine input journal. If that path's parent
    directory cannot be created or the append fails, we fall back to a
    clearly-named hook-signal sidecar at `runtime_hook_signals.jsonl` and
    return 1 so the operator sees the soft drift signal on stderr without
    blocking the agent.
    """
    session_id = _string(payload.get("session_id"))
    if not session_id:
        # Without a session_id the row is not deduplicable and not useful;
        # silently skip rather than emit a zombie boundary.
        return 0

    row = build_stop_lifecycle_signal_row(payload)
    encoded_line = json.dumps(row, ensure_ascii=False) + "\n"

    primary_path = REPO_ROOT / ORCHESTRATION_EVENTS_REL
    try:
        primary_path.parent.mkdir(parents=True, exist_ok=True)
        with primary_path.open("a", encoding="utf-8") as f:
            f.write(encoded_line)
        return 0
    except Exception as exc:
        # Fallback: append to a hook-signal sidecar. This keeps the row
        # durable so a later sweep can drain it into the primary journal.
        try:
            fallback_path = REPO_ROOT / HOOK_SIGNAL_FALLBACK_REL
            fallback_path.parent.mkdir(parents=True, exist_ok=True)
            with fallback_path.open("a", encoding="utf-8") as f:
                f.write(encoded_line)
        except Exception:
            pass
        # Operator-visible non-blocking warning. Per the 0/1/2 contract,
        # exit 1 routes stderr to the operator only; the agent does not see
        # this and the session ends normally.
        try:
            sys.stderr.write(
                f"runtime_hook: Stop lifecycle-signal write to "
                f"{ORCHESTRATION_EVENTS_REL} failed ({exc!r}); "
                f"row appended to {HOOK_SIGNAL_FALLBACK_REL} instead.\n"
            )
        except Exception:
            pass
        return 1


def _closeout_git_state_packet() -> dict[str, Any]:
    try:
        from system.lib.git_state_snapshot import (
            build_closeout_git_state_conditions,
            compact_closeout_git_state_conditions,
        )

        return compact_closeout_git_state_conditions(
            build_closeout_git_state_conditions(REPO_ROOT, path_limit=5, recent_limit=1)
        )
    except Exception:
        return {}


def _message_claims_repo_substrate_work(message: str) -> bool:
    """Return True when a final answer claims repo-substrate mutation or closeout work.

    Stop-hook closeout enforcement should catch false clean/commit/push claims
    and unfinished repo work, but it must not hijack pure advice, evaluation, or
    host-memory updates just because the shared repo has ambient closeout debt.
    """
    if not message.strip():
        return False
    if _matched_closeout_terminal_claims(message):
        return True
    if CLOSEOUT_EXECUTOR_ACTION_EVIDENCE_RE.search(message):
        return True
    absolute_repo_path_mentioned = str(REPO_ROOT) in message
    return bool(
        (absolute_repo_path_mentioned or REPO_SUBSTRATE_PATH_HINT_RE.search(message))
        and REPO_SUBSTRATE_ACTION_RE.search(message)
    )


def _closeout_git_state_stop_context(payload: Optional[Dict[str, Any]] = None) -> str:
    packet = _closeout_git_state_packet()
    if not packet:
        return ""
    last_msg = _string((payload or {}).get("last_assistant_message"))
    should_surface_closeout = _message_claims_repo_substrate_work(last_msg)
    if not packet.get("closeout_ready") and not should_surface_closeout:
        return ""
    publication = packet.get("publication") if isinstance(packet.get("publication"), dict) else {}
    recommended = packet.get("recommended_lane") if isinstance(packet.get("recommended_lane"), dict) else {}
    dirty = packet.get("dirty_total")
    staged = packet.get("staged_total")
    ahead = packet.get("ahead")
    behind = packet.get("behind")
    ready = bool(packet.get("closeout_ready"))
    lane = _string(recommended.get("lane"))
    actuator = _string(recommended.get("actuator"))
    lines = [
        "## Closeout / Git State",
        (
            f"- dirty={dirty} staged={staged} ahead={ahead} behind={behind} "
            f"publication={publication.get('status') or 'unknown'} closeout_ready={str(ready).lower()}"
        ),
    ]
    if lane and lane != "closeout_ready":
        lines.append(f"- recommended_lane: `{lane}`")
    if actuator and actuator != "none":
        lines.append(f"- actuator: `{actuator}`")
    if should_surface_closeout:
        lines.append(
            "- closeout executor: preferred `./repo-python tools/meta/control/closeout_executor.py run-burst --max-actions 3 --json`; "
            "minimum `./repo-python tools/meta/control/closeout_executor.py run-one --json`"
        )
    if ready:
        lines.append("- closeout condition: ready")
    else:
        lines.append(
            "- closeout condition: not ready; do not claim clean-and-pushed until the lane above is settled or explicitly blocked."
        )
    return "\n".join(lines)


def _matched_closeout_terminal_claims(message: str) -> list[str]:
    claims: list[str] = []
    for claim_id, pattern in CLOSEOUT_TERMINAL_CLAIM_PATTERNS:
        match = pattern.search(message)
        if not match:
            continue
        prefix = message[max(0, match.start() - 28):match.start()]
        if CLOSEOUT_TERMINAL_NEGATION_RE.search(prefix):
            continue
        claims.append(claim_id)
    return claims


_OPERATOR_CLOSEOUT_HOLD_PATH = REPO_ROOT / ".claude" / "state" / "operator_closeout_hold.json"


def _operator_closeout_hold_active() -> bool:
    """Operator-set sticky hold that short-circuits the Stop-event closeout guards.

    Stored at `.claude/state/operator_closeout_hold.json`. Set/cleared via
    `tools/meta/control/closeout_hold.py set|clear|status`. The hold is the
    explicit "operator no-commit / no-publish for this thread" register-flip
    from CLAUDE.md commit-autonomy lane 3, made sticky so the operator does
    not have to re-state the held-policy reason on every Stop event in the
    same session. Returns True iff the marker file exists, parses, and the
    optional TTL has not yet expired (`null` ttl = never expires until
    cleared).
    """
    try:
        if not _OPERATOR_CLOSEOUT_HOLD_PATH.exists():
            return False
        import json as _json
        import time as _time

        with _OPERATOR_CLOSEOUT_HOLD_PATH.open("r", encoding="utf-8") as fh:
            payload = _json.load(fh)
        if not isinstance(payload, dict):
            return False
        set_at = payload.get("set_at_epoch")
        ttl = payload.get("ttl_seconds")
        if set_at is None:
            return True  # explicit hold without timing constraint
        try:
            set_at_f = float(set_at)
        except (TypeError, ValueError):
            return True
        if ttl is None:
            return True
        try:
            ttl_f = float(ttl)
        except (TypeError, ValueError):
            return True
        return _time.time() <= set_at_f + ttl_f
    except Exception:
        return False


def _closeout_git_state_stop_block_reason(payload: Dict[str, Any]) -> str:
    if _operator_closeout_hold_active():
        return ""
    last_msg = _string(payload.get("last_assistant_message"))
    if not last_msg.strip():
        return ""
    claims = _matched_closeout_terminal_claims(last_msg)
    if not claims:
        return ""
    packet = _closeout_git_state_packet()
    if not packet or packet.get("closeout_ready") is True:
        return ""
    publication = packet.get("publication") if isinstance(packet.get("publication"), dict) else {}
    recommended = packet.get("recommended_lane") if isinstance(packet.get("recommended_lane"), dict) else {}
    publication_settled = int(packet.get("ahead") or 0) == 0 and str(publication.get("status") or "") == "published"
    global_claims = {"clean_and_pushed", "working_tree_clean", "closeout_complete"}
    contradicting_claims: list[str] = []
    for claim in claims:
        if claim in {"committed_and_pushed", "pushed_to_remote", "remote_ref_verified"} and publication_settled:
            if not any(item in claims for item in global_claims):
                continue
        contradicting_claims.append(claim)
    if not contradicting_claims:
        return ""
    condition = str(packet.get("reason") or "CloseoutConditionsNotReady")
    return (
        "Closeout/git-state contradiction: final response claims terminal state "
        f"{contradicting_claims[:3]}, but closeout_git_state says dirty={packet.get('dirty_total')} "
        f"staged={packet.get('staged_total')} ahead={packet.get('ahead')} "
        f"behind={packet.get('behind')} publication={publication.get('status') or 'unknown'} "
        f"closeout_ready=false reason={condition}. Continue only long enough to settle the "
        "publication/dirty-state lane or state an explicit blocked/held closeout with evidence. "
        "Run closeout executor actuator: preferred ./repo-python tools/meta/control/closeout_executor.py run-burst --max-actions 3 --json; "
        "minimum ./repo-python tools/meta/control/closeout_executor.py run-one --json. "
        f"Recommended lane: {recommended.get('lane') or 'refresh_closeout_git_state'}; "
        f"actuator: {recommended.get('actuator') or './repo-python tools/meta/control/git_state_snapshot.py --closeout-conditions'}."
    )


def _closeout_executor_plan(packet: Dict[str, Any]) -> Dict[str, Any]:
    try:
        from system.lib.closeout_executor import build_closeout_executor_plan

        plan = build_closeout_executor_plan(
            REPO_ROOT,
            closeout_summary=packet,
            run_push_audit=False,
        )
        return plan if isinstance(plan, dict) else {}
    except Exception:
        return {}


def _executor_action_lane(plan: Dict[str, Any]) -> tuple[str, str]:
    action = plan.get("primary_action") if isinstance(plan.get("primary_action"), dict) else {}
    lane = _string(action.get("lane"))
    cluster = action.get("cluster") if isinstance(action.get("cluster"), dict) else {}
    cluster_id = _string(cluster.get("cluster_id"))
    return lane, cluster_id


def _message_reports_concrete_closeout_blocker(message: str) -> bool:
    if not message.strip():
        return False
    if CLOSEOUT_EXECUTOR_BLOCKER_EVIDENCE_RE.search(message):
        return bool(
            re.search(
                r"\b(path|file|test|failure|failed|conflict|patch|"
                r"permission|secret|unsafe|held by policy|publication held|"
                r"validation|same[- ]file|same path|branch|head)\b",
                message,
                re.IGNORECASE,
            )
        )
    return False


def _message_action_ids(message: str) -> list[str]:
    return [match.group(0) for match in CLOSEOUT_EXECUTOR_ACTION_ID_RE.finditer(message)]


def _stale_action_id_in_message(message: str, current_action_id: str) -> str:
    current = _string(current_action_id).lower()
    if not current:
        return ""
    for action_id in _message_action_ids(message):
        if action_id.lower() != current:
            return action_id
    return ""


def _action_requires_effect_receipt(action: Dict[str, Any]) -> bool:
    cluster = action.get("cluster") if isinstance(action.get("cluster"), dict) else {}
    receipt = cluster.get("effect_receipt") if isinstance(cluster.get("effect_receipt"), dict) else {}
    return bool(receipt.get("required"))


def _message_reports_ui_effect_receipt(message: str) -> bool:
    if not message.strip():
        return False
    return bool(
        re.search(
            r"\b("
            r"npm run build passed|build passed|vite build passed|lint passed|test passed|"
            r"served (?:route|component|surface|page).*?(?:saw|observed|selector|text|action)|"
            r"(?:bundle|asset) hash (?:changed|updated)|browser smoke|ui smoke|screenshot"
            r")\b",
            message,
            re.IGNORECASE,
        )
    )


def _message_reports_lane_action_or_blocker(message: str, lane: str, cluster_id: str = "") -> bool:
    if not message.strip():
        return False
    if _message_reports_concrete_closeout_blocker(message):
        return True

    lowered = message.lower()
    has_commit_hash = bool(CLOSEOUT_EXECUTOR_COMMIT_RE.search(message))
    has_push_receipt = bool(
        re.search(r"\b(pushed|published|remote verified|origin/main|ls-remote|remote ref verified)\b", message, re.IGNORECASE)
    )
    has_executor_receipt = "executor action executed" in lowered or "primary_action" in lowered
    mentions_cluster = bool(cluster_id and cluster_id.lower() in lowered)
    already_integrated = bool(
        re.search(r"\b(already integrated|already landed|no longer dirty|already clean)\b", message, re.IGNORECASE)
    )

    if lane == "publish_if_clear":
        return has_push_receipt and bool(re.search(r"\b(remote verified|origin/main|ls-remote|remote ref verified)\b", message, re.IGNORECASE))
    if lane == "drain_source_cluster":
        if has_commit_hash and has_push_receipt:
            return True
        if already_integrated and (mentions_cluster or "cluster" in lowered):
            return True
        return False
    if lane == "drain_worktrees":
        return bool(
            re.search(
                r"\b(worktree removed|worktree registered|worktree count decreased|git worktree remove|pruned)\b",
                message,
                re.IGNORECASE,
            )
        )
    if lane == "settle_generated_state":
        return bool(
            re.search(
                r"\b(generated[- ]state settlement|settled generated|generated_state_drainer|owner[- ]lane settlement)\b",
                message,
                re.IGNORECASE,
            )
        )
    if lane == "no_action":
        return True
    if has_executor_receipt and has_commit_hash and has_push_receipt:
        return True
    return False


def _message_reports_closeout_action_or_blocker(message: str) -> bool:
    return _message_reports_lane_action_or_blocker(message, "")


def _recent_orchestration_rows() -> list[Dict[str, Any]]:
    path = REPO_ROOT / ORCHESTRATION_EVENTS_REL
    try:
        with path.open("rb") as f:
            try:
                f.seek(0, os.SEEK_END)
                size = f.tell()
                f.seek(max(0, size - MAX_CLOSEOUT_BASELINE_SCAN_BYTES))
            except OSError:
                pass
            text = f.read().decode("utf-8", errors="replace")
    except Exception:
        return []
    rows: list[Dict[str, Any]] = []
    for raw in text.splitlines():
        try:
            row = json.loads(raw)
        except Exception:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _closeout_baseline_for_session(session_id: str) -> Dict[str, Any]:
    if not session_id:
        return {}
    for row in reversed(_recent_orchestration_rows()):
        if row.get("kind") != CLOSEOUT_BASELINE_EVENT_KIND:
            continue
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        if payload.get("session_id") == session_id:
            return payload
    return {}


def _write_closeout_baseline_event(payload: Dict[str, Any], packet: Dict[str, Any], plan: Dict[str, Any]) -> None:
    session_id = _string(payload.get("session_id"))
    if not session_id:
        return
    lane, cluster_id = _executor_action_lane(plan)
    event_payload = {
        "session_id": session_id,
        "transcript_path": _string(payload.get("transcript_path")) or None,
        "cwd": _string(payload.get("cwd")) or None,
        "closeout": {
            "head": (plan.get("observed") or {}).get("head"),
            "status_hash": (plan.get("observed") or {}).get("status_hash"),
            "dirty_total": packet.get("dirty_total"),
            "ahead": packet.get("ahead"),
            "behind": packet.get("behind"),
            "worktree_count": (plan.get("observed") or {}).get("worktree_count"),
            "closeout_ready": packet.get("closeout_ready"),
        },
        "executor": {
            "plan_id": plan.get("plan_id"),
            "action_id": (plan.get("primary_action") or {}).get("action_id") if isinstance(plan.get("primary_action"), dict) else None,
            "lane": lane,
            "cluster_id": cluster_id or None,
            "status": plan.get("status"),
        },
    }
    ts = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    digest_input = json.dumps(
        {"kind": CLOSEOUT_BASELINE_EVENT_KIND, "session_id": session_id},
        sort_keys=True,
        ensure_ascii=False,
    ).encode("utf-8")
    row = {
        "ts": ts,
        "source": "claude_hook",
        "kind": CLOSEOUT_BASELINE_EVENT_KIND,
        "payload": event_payload,
        "stable_digest": hashlib.sha256(digest_input).hexdigest()[:32],
    }
    try:
        path = REPO_ROOT / ORCHESTRATION_EVENTS_REL
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _record_closeout_baseline_if_needed(action: str, payload: Dict[str, Any]) -> None:
    if action not in {"session-start", "user-prompt"}:
        return
    session_id = _string(payload.get("session_id"))
    if not session_id or _closeout_baseline_for_session(session_id):
        return
    packet = _closeout_git_state_packet()
    if not packet:
        return
    plan = _closeout_executor_plan(packet)
    _write_closeout_baseline_event(payload, packet, plan)


def _closeout_state_delta(payload: Dict[str, Any], packet: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    session_id = _string(payload.get("session_id"))
    baseline = _closeout_baseline_for_session(session_id)
    if not baseline:
        return {"status": "baseline_missing"}
    base_closeout = baseline.get("closeout") if isinstance(baseline.get("closeout"), dict) else {}
    base_executor = baseline.get("executor") if isinstance(baseline.get("executor"), dict) else {}
    observed = plan.get("observed") if isinstance(plan.get("observed"), dict) else {}
    improvements: list[str] = []

    try:
        if int(packet.get("ahead") or 0) < int(base_closeout.get("ahead") or 0):
            improvements.append("ahead_decreased")
    except Exception:
        pass
    try:
        if int(packet.get("dirty_total") or 0) < int(base_closeout.get("dirty_total") or 0):
            improvements.append("dirty_total_decreased")
    except Exception:
        pass
    try:
        if int(observed.get("worktree_count") or 0) < int(base_closeout.get("worktree_count") or 0):
            improvements.append("worktree_count_decreased")
    except Exception:
        pass
    if observed.get("head") and observed.get("head") != base_closeout.get("head"):
        if int(packet.get("ahead") or 0) == 0:
            improvements.append("head_advanced_and_published")
        else:
            improvements.append("head_advanced")
    action = plan.get("primary_action") if isinstance(plan.get("primary_action"), dict) else {}
    if action.get("action_id") and action.get("action_id") != base_executor.get("action_id"):
        improvements.append("executor_action_changed")

    return {
        "status": "improved" if improvements else "unchanged",
        "improvements": improvements,
        "baseline_plan_id": base_executor.get("plan_id"),
        "current_plan_id": plan.get("plan_id"),
    }


def _closeout_state_delta_allows_red_stop(delta: Dict[str, Any]) -> bool:
    improvements = delta.get("improvements") if isinstance(delta.get("improvements"), list) else []
    return any(
        item in {
            "ahead_decreased",
            "dirty_total_decreased",
            "worktree_count_decreased",
            "head_advanced_and_published",
        }
        for item in improvements
    )


def _session_made_no_substrate_change(
    payload: Dict[str, Any], packet: Dict[str, Any], plan: Dict[str, Any]
) -> bool:
    """True iff this session has not mutated the substrate since session-start.

    Compares head, ahead, behind, dirty_total, and worktree_count at Stop
    time against the values recorded by the session-start baseline event.
    When True, the closeout backlog the executor is reporting was already
    present when the session opened and is not residue produced by the
    current turn. Advisory / exploratory yields cleanly under this branch;
    terminal-state contradictions remain caught by the separate
    `_closeout_git_state_stop_block_reason` guard, which fires on claim
    language regardless of this exemption.
    """
    session_id = _string(payload.get("session_id"))
    if not session_id:
        return False
    baseline = _closeout_baseline_for_session(session_id)
    if not baseline:
        return False
    base = baseline.get("closeout") if isinstance(baseline.get("closeout"), dict) else {}
    if not base:
        return False
    observed = plan.get("observed") if isinstance(plan.get("observed"), dict) else {}
    try:
        base_head = base.get("head")
        cur_head = observed.get("head")
        if base_head and cur_head and base_head != cur_head:
            return False
        if int(packet.get("ahead") or 0) != int(base.get("ahead") or 0):
            return False
        if int(packet.get("behind") or 0) != int(base.get("behind") or 0):
            return False
        if int(packet.get("dirty_total") or 0) != int(base.get("dirty_total") or 0):
            return False
        if int(observed.get("worktree_count") or 0) != int(base.get("worktree_count") or 0):
            return False
    except Exception:
        return False
    return True


def _closeout_executor_null_stop_block_reason(payload: Dict[str, Any]) -> str:
    if _operator_closeout_hold_active():
        return ""
    last_msg = _string(payload.get("last_assistant_message"))
    if not last_msg.strip():
        return ""
    packet = _closeout_git_state_packet()
    if not packet or packet.get("closeout_ready") is True:
        return ""
    plan = _closeout_executor_plan(packet)
    if plan.get("status") != "action_required":
        return ""
    if _session_made_no_substrate_change(payload, packet, plan):
        return ""
    if not _message_claims_repo_substrate_work(last_msg):
        return ""
    action = plan.get("primary_action") if isinstance(plan.get("primary_action"), dict) else {}
    lane = _string(action.get("lane"))
    if not lane or lane == "no_action":
        return ""
    cluster = action.get("cluster") if isinstance(action.get("cluster"), dict) else {}
    cluster_id = _string(cluster.get("cluster_id"))
    action_id = _string(action.get("action_id"))
    stale_action_id = _stale_action_id_in_message(last_msg, action_id)
    if stale_action_id:
        return (
            "Closeout executor stale receipt: final response cites "
            f"action_id={stale_action_id}, but current executor action_id={action_id} "
            f"for lane={lane}. Run preferred `./repo-python tools/meta/control/closeout_executor.py run-burst --max-actions 3 --json` "
            "or minimum `./repo-python tools/meta/control/closeout_executor.py run-one --json` "
            "and report the current action receipt, or state a concrete blocker."
        )
    if _action_requires_effect_receipt(action):
        if _message_reports_concrete_closeout_blocker(last_msg):
            return ""
        if _message_reports_lane_action_or_blocker(last_msg, lane, cluster_id) and _message_reports_ui_effect_receipt(last_msg):
            return ""
        cluster_suffix = f" cluster={cluster_id}" if cluster_id else ""
        return (
            "Closeout executor UI-effect guard: executor primary action "
            f"lane={lane}{cluster_suffix} requires effect_receipt evidence. Commit/push receipt alone is not enough; "
            "report build/lint/test effect output, served route/component smoke, bundle/asset hash change, "
            "or a concrete blocker naming why the served effect cannot be verified."
        )
    if _closeout_state_delta_allows_red_stop(_closeout_state_delta(payload, packet, plan)):
        return ""
    if _message_reports_lane_action_or_blocker(last_msg, lane, cluster_id):
        return ""
    cluster_suffix = f" cluster={cluster_id}" if cluster_id else ""
    plan_suffix = f" plan_id={plan.get('plan_id')}" if plan.get("plan_id") else ""
    action_suffix = f" action_id={action.get('action_id')}" if action.get("action_id") else ""
    return (
        "Closeout executor null-yield guard: closeout_ready=false and executor "
        f"has action_required lane={lane}{cluster_suffix}{plan_suffix}{action_suffix}. Before yielding, run "
        "preferred `./repo-python tools/meta/control/closeout_executor.py run-burst --max-actions 3 --json` "
        "or minimum `./repo-python tools/meta/control/closeout_executor.py run-one --json` "
        "and report its typed receipt, or state a concrete blocker "
        "(failing test, patch conflict, same-file ownership conflict, unsafe "
        "publication, or explicit held policy)."
    )


def _additional_context(action: str, payload: Dict[str, Any]) -> str:
    blocks: List[str] = []
    if action in REHYDRATION_ACTIONS:
        rehydration = _build_rehydration_context(action, payload)
        if rehydration:
            blocks.append(rehydration)
    if action == "stop":
        closeout_git_state = _closeout_git_state_stop_context(payload)
        if closeout_git_state:
            blocks.append(closeout_git_state)
    if action == "user-prompt":
        try:
            residual_hint = _large_instruction_residual_capture_hint(payload)
        except Exception:
            residual_hint = ""
        if residual_hint:
            blocks.append(residual_hint)
    if action == "pre-tool":
        try:
            todo_residual_block = _todo_residual_capture_hint(payload)
        except Exception:
            todo_residual_block = ""
        if todo_residual_block:
            blocks.append(todo_residual_block)
        try:
            efficiency_block = _bash_command_efficiency_counterinject(payload)
        except Exception:
            efficiency_block = ""
        if efficiency_block:
            blocks.append(efficiency_block)
        try:
            high_volume_read_block = _high_volume_read_counterinject(payload)
        except Exception:
            high_volume_read_block = ""
        if high_volume_read_block:
            blocks.append(high_volume_read_block)
        try:
            typed_discovery_block = _typed_discovery_first_contact_counterinject(payload)
        except Exception:
            typed_discovery_block = ""
        if typed_discovery_block:
            blocks.append(typed_discovery_block)
        try:
            bash_block = _bash_native_fallthrough_counterinject(payload)
        except Exception:
            bash_block = ""
        if bash_block:
            blocks.append(bash_block)
        try:
            kernel_nav_block = _kernel_navigation_fallthrough_counterinject(payload)
        except Exception:
            kernel_nav_block = ""
        if kernel_nav_block:
            blocks.append(kernel_nav_block)
    if action == "post-tool":
        try:
            cockpit_block = _cockpit_edit_counterinject(payload)
        except Exception:
            cockpit_block = ""
        if cockpit_block:
            blocks.append(cockpit_block)
        try:
            seed_block = _seed_substrate_edit_counterinject(payload)
        except Exception:
            seed_block = ""
        if seed_block:
            blocks.append(seed_block)
    runtime_payload = _compact_hook_payload(payload)
    if os.environ.get(ENABLE_WORK_LEDGER_HOOK_RUNTIME_ENV) == "1":
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from system.lib import work_ledger_runtime

            ledger_context = work_ledger_runtime.handle_hook_event(REPO_ROOT, action, runtime_payload)
            if ledger_context:
                blocks.append(ledger_context)
        except Exception:
            pass
    if os.environ.get(ENABLE_METABOLISM_HOOK_RUNTIME_ENV) == "1":
        try:
            sys.path.insert(0, str(REPO_ROOT))
            from system.lib import metabolism_hooks

            metabolism_context = metabolism_hooks.handle_claude_hook_event(
                REPO_ROOT, action, runtime_payload
            )
            if metabolism_context:
                blocks.append(metabolism_context)
        except Exception:
            pass
    if not blocks:
        return ""
    combined = "\n\n".join(blocks)
    if len(combined) > MAX_CONTEXT_CHARS:
        combined = combined[: MAX_CONTEXT_CHARS - 1].rstrip() + "…"
    return combined


def main(argv: List[str]) -> int:
    action = argv[1] if len(argv) > 1 else ""
    try:
        payload = _read_payload()
    except Exception:
        payload = {}

    # Identity heartbeat runs BEFORE rehydration so a failing stamp never
    # prevents context injection, and a failing rehydration never blocks
    # identity capture. Both paths swallow their own errors.
    if action in IDENTITY_CAPTURE_ACTIONS:
        _stamp_active_session_safe(action, payload)
        _forward_agent_observability_safe(action, payload)
        _record_closeout_baseline_if_needed(action, payload)

    # Stop lifecycle boundary — emit a reactions_engine-visible signal row.
    # Per the 0/1/2 exit-code contract canonised in
    # codex/doctrine/paper_modules/runtime_hook_ladder.md:
    #   exit 0 = success / skip (no session_id available)
    #   exit 1 = non-blocking error -> stderr to operator only
    #   exit 2 = blocking error fed back to agent (NOT applicable for Stop;
    #            the session is already ending, no next agent turn to block)
    # We capture the helper's return code separately so additionalContext
    # emission still runs even when the signal write soft-failed.
    stop_signal_exit = 0
    if action == "stop":
        try:
            stop_signal_exit = _emit_stop_lifecycle_signal(payload)
        except Exception:
            # The helper has its own exception trap; this catch is the
            # last-line guarantee that a broken Stop path never raises out
            # of the hook (the existing module-level contract).
            stop_signal_exit = 0

    # Stop egress action-autonomy check — block the Stop event when the
    # final response contains routine permission-gate language without
    # naming a real blast-radius blocker. Loop protection: respect
    # `stop_hook_active` so the agent's repair attempt is not infinitely
    # re-blocked (Claude Code Stop hook docs explicitly require authors
    # check this flag or otherwise prevent infinite continuation loops).
    # The detector at `system/lib/egress_compliance.py` is the single
    # source of truth for gate/blocker phrase semantics; this block is
    # only the runtime wiring that turns the detector into an enforcement
    # gate. Active rule:
    # `std_agent_entry_surface.json::common_sense_helpfulness_floor::action_over_pointless_inaction`.
    if action == "stop" and not bool(payload.get("stop_hook_active")):
        try:
            closeout_block_reason = _closeout_git_state_stop_block_reason(payload)
            if closeout_block_reason:
                try:
                    print(
                        json.dumps(
                            {"decision": "block", "reason": closeout_block_reason},
                            ensure_ascii=False,
                        )
                    )
                except Exception:
                    pass
                return stop_signal_exit

            closeout_null_reason = _closeout_executor_null_stop_block_reason(payload)
            if closeout_null_reason:
                try:
                    print(
                        json.dumps(
                            {"decision": "block", "reason": closeout_null_reason},
                            ensure_ascii=False,
                        )
                    )
                except Exception:
                    pass
                return stop_signal_exit

            from system.lib.egress_compliance import (
                detect_capture_reflex_tripwire_without_capture,
                detect_no_op_closeout_without_next_action,
                detect_permission_gate_without_blocker,
                detect_residual_deliverable_without_workitem,
                detect_stale_dirty_snapshot_commit_blocker,
            )

            last_msg = _string(payload.get("last_assistant_message"))
            if last_msg.strip():
                stale_dirty_rows = detect_stale_dirty_snapshot_commit_blocker(
                    last_msg
                )
                stale_dirty_violation = next(
                    (row for row in stale_dirty_rows if row.get("violation")),
                    None,
                )
                if stale_dirty_violation:
                    stale_phrases = list(
                        stale_dirty_violation.get("matched_stale_phrases", [])
                    )[:3]
                    reason = (
                        "Stale dirty-tree blocker egress check (per "
                        "std_agent_entry_surface.json::common_sense_helpfulness_floor::"
                        "commit_autonomy_policy.same_path_conflict_freshness_rule): "
                        "final response turns session-start/pre-existing dirt into a "
                        f"commit blocker via {stale_phrases} without fresh pathspec "
                        "status plus Work Ledger claim/mutation proof. Continue only "
                        "long enough to run `git status --short -- <paths>` and "
                        "`./repo-python tools/meta/factory/work_ledger.py "
                        "session-claims --refresh` or `mutation-check --path`; "
                        "if clean/already landed, retire the blocker and proceed "
                        "with scoped landing. If still real, cite the fresh proof."
                    )
                    try:
                        print(
                            json.dumps(
                                {"decision": "block", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    return stop_signal_exit
                no_op_rows = detect_no_op_closeout_without_next_action(last_msg)
                no_op_violation = next(
                    (row for row in no_op_rows if row.get("violation")),
                    None,
                )
                if no_op_violation:
                    tripwire_phrases = list(
                        no_op_violation.get("matched_tripwire_phrases", [])
                    )[:3]
                    reason = (
                        "No-op closeout egress check (per "
                        "std_agent_entry_surface.json::common_sense_helpfulness_floor::"
                        "non_null_pass_yield and std_uppropagation_intake.json::"
                        "pass_closeout_contract): final response uses null/verify/"
                        f"settlement language {tripwire_phrases} without durable "
                        "action, rejected-lane proof, exact claim/policy blocker, "
                        "capture, or residual-free proof. Continue to patch, capture, "
                        "sign off, or run the next bounded substrate-care lane; field "
                        "names like stewardship_checked or next_best_lane_checked do "
                        "not clear the gate by themselves."
                    )
                    try:
                        print(
                            json.dumps(
                                {"decision": "block", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    return stop_signal_exit
                egress_rows = detect_permission_gate_without_blocker(last_msg)
                violation_row = next(
                    (row for row in egress_rows if row.get("violation")),
                    None,
                )
                if violation_row:
                    gate_phrases = list(violation_row.get("matched_gate_phrases", []))[:3]
                    reason = (
                        "Action-autonomy egress check (per "
                        "std_agent_entry_surface.json::common_sense_helpfulness_floor::"
                        "action_over_pointless_inaction): final response contains "
                        f"permission-gate language {gate_phrases} without naming a "
                        "real blast-radius blocker. Continue the safe coherent wave, "
                        "or stop only after naming a legitimate blocker (destructive / "
                        "irreversible / secret-handling / publication boundary / "
                        "non-isolatable concurrent-owner conflict / unsafe generated-"
                        "projection ownership / safety-changing validation failure / "
                        "cross-actor surface ownership)."
                    )
                    try:
                        print(
                            json.dumps(
                                {"decision": "block", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    return stop_signal_exit
                capture_reflex_rows = detect_capture_reflex_tripwire_without_capture(
                    last_msg
                )
                capture_reflex_violation = next(
                    (row for row in capture_reflex_rows if row.get("violation")),
                    None,
                )
                if capture_reflex_violation:
                    tripwire_phrases = list(
                        capture_reflex_violation.get(
                            "matched_tripwire_phrases", []
                        )
                    )[:3]
                    reason = (
                        "Capture-reflex egress check (per "
                        "std_task_ledger.json::metacontrol_contract::"
                        "observed_failure_capture_invariant): final response uses "
                        f"tripwire language {tripwire_phrases} without a durable "
                        "cap_*/WorkItem/capture/no-op binding. Continue only long "
                        "enough to quick-capture, link to an existing cap, block, "
                        "retire, or explicitly no-op the finding, then cite the "
                        "cap_id/receipt."
                    )
                    try:
                        print(
                            json.dumps(
                                {"decision": "block", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    return stop_signal_exit
                residual_rows = detect_residual_deliverable_without_workitem(last_msg)
                residual_violation = next(
                    (row for row in residual_rows if row.get("violation")),
                    None,
                )
                if residual_violation:
                    residual_phrases = list(
                        residual_violation.get("matched_residual_phrases", [])
                    )[:3]
                    reason = (
                        "Residual-deliverable egress check (per "
                        "std_task_ledger.json::metacontrol_contract::"
                        "provider_native_task_affordance_boundary."
                        "partial_instruction_residual_rule): final response names "
                        f"residual language {residual_phrases} without a durable "
                        "cap_*/WorkItem/capture/no-op binding. Continue only long "
                        "enough to quick-capture, link to an existing cap, block, "
                        "retire, or explicitly no-op the residual, then cite the "
                        "cap_id/receipt."
                    )
                    try:
                        print(
                            json.dumps(
                                {"decision": "block", "reason": reason},
                                ensure_ascii=False,
                            )
                        )
                    except Exception:
                        pass
                    return stop_signal_exit
        except Exception:
            # Egress check is non-load-bearing; never raise out of the
            # hook (the existing module-level contract).
            pass

    # PreToolUse hard-block for dangerous shared-index git shapes. This runs
    # BEFORE additionalContext composition so a denied command produces a
    # single, unambiguous deny payload to Claude Code rather than a denial
    # mixed with steering text. Other actions skip this entirely.
    if action == "pre-tool":
        try:
            block_reason = _raw_shared_index_git_guard(payload)
        except Exception:
            block_reason = ""
        if block_reason:
            hook_event_name = CANONICAL_HOOK_NAMES.get(action, action)
            try:
                print(
                    json.dumps(
                        {
                            "hookSpecificOutput": {
                                "hookEventName": hook_event_name,
                                "permissionDecision": "deny",
                                "permissionDecisionReason": block_reason,
                            }
                        },
                        ensure_ascii=False,
                    )
                )
            except Exception:
                pass
            return stop_signal_exit

    try:
        additional_context = _additional_context(action, payload)
    except Exception:
        additional_context = ""

    if additional_context:
        hook_event_name = CANONICAL_HOOK_NAMES.get(action, action)
        try:
            print(
                json.dumps(
                    {
                        "hookSpecificOutput": {
                            "hookEventName": hook_event_name,
                            "additionalContext": additional_context,
                        }
                    },
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass
    return stop_signal_exit


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
