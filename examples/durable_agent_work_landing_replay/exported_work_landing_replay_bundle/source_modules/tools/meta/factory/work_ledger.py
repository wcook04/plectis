#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter, deque
import hashlib
import json
import os
import re
import shlex
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
SESSION_HEARTBEAT_STATE_ALIASES = {
    "validate": "validating",
    "validation": "validating",
}
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import agent_seed_handoffs, shared_worktree_guard, work_admission, work_ledger, work_ledger_runtime
from system.lib.work_ledger_commands import (
    WORK_LEDGER_CLAIM_CARDS_REFRESH_COMMAND,
    WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
    WORK_LEDGER_SEED_SPEED_COMMAND,
    WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
)

CODEX_STATE_DB = Path.home() / ".codex" / "state_5.sqlite"
CLAUDE_IDE_DIR = Path.home() / ".claude" / "ide"
CLAUDE_TODOS_DIR = Path.home() / ".claude" / "todos"
BACKGROUND_DOWNSHIFT_STATE = REPO_ROOT / "state" / "performance" / "background_loop_downshift.json"
SESSION_YIELD_REQUESTS = REPO_ROOT / "state" / "performance" / "session_yield_requests.jsonl"
SESSION_YIELD_RESULTS = REPO_ROOT / "state" / "performance" / "session_yield_results.jsonl"
CODEX_ROLLOUT_TAIL_EVENTS = 400
CODEX_ROLLOUT_COMMAND_LIMIT = 12
CODEX_ROLLOUT_PATH_LIMIT = 40
OVERLAP_TITLE_INLINE_BYTE_LIMIT = 1024
OVERLAP_TITLE_PREVIEW_CHARS = 240
SERIAL_MUTATION_HELP = (
    "Mutation ordering: do not launch Work Ledger lifecycle or claim mutations "
    "in parallel for the same session. Use session-preflight to bootstrap and "
    "claim td/path scopes in one serialized command, then finalize only after a "
    "Work Ledger append or append-exempt evidence exists."
)
HEARTBEAT_PARTICIPATION_HELP = (
    "Heartbeat participation: for long-running Type A/Codex passes, publish one "
    "public now/done heartbeat at pass start, plan pivot, before validation, and "
    "closeout. Do not derive heartbeat text from raw transcripts or hidden reasoning."
)
WRITE_PROFILE_PATHS: Dict[str, tuple[str, ...]] = {
    "agent_bootstrap_projection": (
        "AGENTS.md",
        "AGENTS.override.md",
        "CLAUDE.md",
        "CODEX.md",
        "codex/doctrine/agent_bootstrap_live.json",
        "codex/doctrine/agent_bootstrap_injection_strip.json",
    ),
    "paper_module_index": (
        "codex/doctrine/paper_modules/README.md",
        "codex/doctrine/paper_modules/_index.json",
        "codex/doctrine/paper_modules/_validation_report.json",
        "codex/doctrine/paper_modules/_doctrine_to_paper_modules.json",
        "codex/doctrine/paper_modules/_route_coverage.json",
    ),
    "skill_catalog_projection": (
        "AGENTS.md",
        "codex/doctrine/skills/skill_registry.json",
        "codex/doctrine/skills/skill_map.md",
    ),
    "annex_catalog_projection": (
        "annexes/annex_distillation_index.json",
        "docs/annex_registry.md",
    ),
    "annex_assimilation": (
        "annexes",
        "annexes/annex_distillation_index.json",
        "docs/annex_registry.md",
    ),
    "raw_seed_family_projection": (
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.json",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed.snapshot.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/raw_seed",
    ),
    "agent_seed_family_projection": (
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.json",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.md",
        "obsidian/okay lets do this/09 - Raw-Seed Preservation, Semantic Reset, and Fresh Execution Spine/agent_seed.snapshot.md",
    ),
    "doctrine_skill_projection": (
        "codex/doctrine/skills",
        "codex/doctrine/skills/skill_registry.json",
        "codex/doctrine/skills/skill_map.md",
        "AGENTS.md",
    ),
    "orchestration_runtime_projection": (
        "tools/meta/control/orchestration_state.json",
        "tools/meta/control/orchestration_brief.json",
        "tools/meta/control/orchestration_brief.md",
        "tools/meta/control/orchestration_events.jsonl",
    ),
    "navigation_hologram_projection": (
        "codex/navigation_hologram",
    ),
    "architectural_projection": (
        "state/architectural_projection",
        "system/lib/architectural_projection.py",
        "tools/meta/factory/build_architectural_projection.py",
        "codex/standards/std_architectural_projection.json",
        "codex/doctrine/paper_modules/architectural_projection_plane.md",
    ),
    "task_ledger": (
        "state/task_ledger/events.jsonl",
        "state/task_ledger/events_audit.jsonl",
        "state/task_ledger/ledger.json",
        "state/task_ledger/views",
    ),
    "autonomous_seed": (
        "state/meta_missions/type_a_autonomous_seed_loop/README.md",
        "state/meta_missions/type_a_autonomous_seed_loop/seeds",
    ),
}
_CODEX_PATH_TOKEN_RE = re.compile(
    r"(?<![A-Za-z0-9_./~-])(?P<path>(?:\./)?(?:(?:\.agents|\.claude|\.codex|\.cursor|annexes|codex|docs|system|tools|state|obsidian|scripts|tests|src|lib)/[A-Za-z0-9_./%+@=-]+|(?:AGENTS|CODEX|CLAUDE|GEMINI)\.md|kernel\.py|(?:pipeline|run)_[A-Za-z0-9_/-]+\.py))"
)
_CODEX_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Delete|Update) File: (?P<path>.+?)\s*$", re.MULTILINE)

def _print(payload: Dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")


def _read_jsonl_tail(path: Path, *, limit: int = 20) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: deque[str] = deque(maxlen=max(1, int(limit or 1)))
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(line)
    records: list[dict[str, Any]] = []
    for line in rows:
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict):
            records.append(payload)
    return records


def _mint_session_yield_request_id(target_session_id: str | None, requested_action: str | None) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    seed = f"{stamp}:{target_session_id or 'unknown'}:{requested_action or 'yield'}:{os.getpid()}"
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8]
    return f"syr_{stamp}_{digest}"


def _session_yield_request_receipt_from_event(row: Mapping[str, Any]) -> dict[str, Any]:
    nested = row.get("session_yield_request")
    if isinstance(nested, dict):
        return nested
    if row.get("schema") == work_admission.SESSION_YIELD_REQUEST_SCHEMA:
        return dict(row)
    return {}


def _find_session_yield_request(
    *,
    request_id: str | None = None,
    target_session_id: str | None = None,
    limit: int = 400,
) -> dict[str, Any] | None:
    for row in reversed(_read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=limit)):
        receipt = _session_yield_request_receipt_from_event(row)
        if not receipt:
            continue
        if request_id and receipt.get("request_id") == request_id:
            return receipt
        if target_session_id and receipt.get("target_id") == target_session_id:
            return receipt
    return None


def _heartbeat_participation_contract(session_id: str | None = None) -> Dict[str, Any]:
    session_token = shlex.quote(str(session_id)) if str(session_id or "").strip() else "<session_id>"
    return {
        "schema": "work_ledger_heartbeat_participation_contract_v0",
        "status": "recommended_for_participating_sessions",
        "when": [
            "long_pass_start",
            "plan_pivot",
            "before_validation",
            "closeout",
        ],
        "command_template": (
            "./repo-python tools/meta/factory/work_ledger.py session-heartbeat "
            f"--session-id {session_token} --state <state> "
            "--now '<public current pass>' --done '<public previous result>' "
            "--scope-ref <path-or-claim>"
        ),
        "boundary": (
            "Explicit public coordination assertion; runtime-only; not durable "
            "progress; never summarize raw transcripts or hidden reasoning."
        ),
    }


def _resolution_episode_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    metadata = None
    if args.resolution_metadata_json:
        metadata = json.loads(args.resolution_metadata_json)
        if not isinstance(metadata, dict):
            raise ValueError("resolution_metadata_json must decode to an object")
    return work_ledger.build_resolution_episode(
        args.resolution_kind,
        args.resolution_ref,
        label=args.resolution_label,
        metadata=metadata,
    )


def _progress_bridge_resolution_hint(args: argparse.Namespace) -> tuple[str, str, str]:
    evidence_refs = [
        str(ref).strip()
        for ref in getattr(args, "evidence_ref", [])
        if str(ref).strip()
    ]
    if evidence_refs:
        ref = evidence_refs[0]
        if re.fullmatch(r"[0-9a-fA-F]{7,40}", ref):
            return "git_commit", ref, "Work Ledger progress bridge evidence commit"
        return "artifact", ref, "Work Ledger progress bridge evidence"
    return "session", str(args.actor_session_id), "Work Ledger progress bridge closeout"


def _metadata_from_args(args: argparse.Namespace) -> Dict[str, Any]:
    raw = getattr(args, "metadata_json", None)
    metadata: Dict[str, Any] = {}
    if raw:
        decoded = json.loads(raw)
        if not isinstance(decoded, dict):
            raise ValueError("metadata_json must decode to an object")
        metadata = decoded
    body_ingest = getattr(args, "_body_ingest", None)
    if body_ingest:
        if "body_ingest" in metadata:
            raise SystemExit(
                "metadata_json may not contain body_ingest when --body-file or --body-stdin is used; "
                "body_ingest is system-owned attestation metadata."
            )
        metadata["body_ingest"] = body_ingest
    mutation_guard = getattr(args, "_mutation_guard", None)
    if mutation_guard:
        if "mutation_guard" in metadata:
            raise SystemExit(
                "metadata_json may not contain mutation_guard when Work Ledger mutation authority "
                "is checked; mutation_guard is system-owned concurrency metadata."
            )
        metadata["mutation_guard"] = mutation_guard
    return metadata


def _body_ingest_attestation(
    *,
    mode: str,
    raw: bytes,
    source_text: str,
    path: Path | None = None,
) -> Dict[str, Any]:
    stored_text = str(source_text or "").strip()
    stored_bytes = stored_text.encode("utf-8")
    source_sha256 = hashlib.sha256(raw).hexdigest()
    source_byte_count = len(raw)
    source_newline_count = source_text.count("\n")
    stored_sha256 = hashlib.sha256(stored_bytes).hexdigest()
    stored_byte_count = len(stored_bytes)
    stored_newline_count = stored_text.count("\n")
    attestation: Dict[str, Any] = {
        "mode": mode,
        "sha256": source_sha256,
        "byte_count": source_byte_count,
        "newline_count": source_newline_count,
        "source_sha256": source_sha256,
        "source_byte_count": source_byte_count,
        "source_newline_count": source_newline_count,
        "stored_sha256": stored_sha256,
        "stored_byte_count": stored_byte_count,
        "stored_newline_count": stored_newline_count,
        "canonicalization": {
            "storage": "work_ledger_event_shape_str_strip",
            "leading_trailing_whitespace_stripped": stored_text != source_text,
            "trailing_newline_removed": source_text.endswith("\n")
            and stored_text == source_text.rstrip("\n"),
        },
    }
    if path is not None:
        attestation["path"] = str(path)
    return attestation


def _resolve_body_and_ingest(args: argparse.Namespace) -> None:
    """Resolve --body / --body-file / --body-stdin into args.body and args._body_ingest.

    Closeout bodies are governance evidence; shell command-substitution can corrupt
    inline --body text. --body-file PATH reads UTF-8 bytes from disk; --body-stdin
    reads sys.stdin.buffer; both are mutually exclusive with --body and with each
    other. For file/stdin sources, body_ingest metadata records source-byte and
    stored-body digests so the closeout event carries an attestation envelope
    alongside the body text.
    """
    inline = getattr(args, "body", None)
    body_file = getattr(args, "body_file", None)
    body_stdin = bool(getattr(args, "body_stdin", False))
    sources = sum(1 for v in (inline is not None, bool(body_file), body_stdin) if v)
    if sources > 1:
        raise SystemExit(
            "Only one of --body, --body-file, --body-stdin may be supplied (mutually exclusive)."
        )
    args._body_ingest = None  # type: ignore[attr-defined]
    if body_file:
        path = Path(body_file)
        if not path.is_file():
            raise SystemExit(f"--body-file path does not exist: {path}")
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"--body-file must be UTF-8: {exc}") from exc
        args.body = text
        args._body_ingest = _body_ingest_attestation(  # type: ignore[attr-defined]
            mode="file",
            path=path,
            raw=raw,
            source_text=text,
        )
    elif body_stdin:
        raw = sys.stdin.buffer.read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SystemExit(f"--body-stdin must receive UTF-8: {exc}") from exc
        args.body = text
        args._body_ingest = _body_ingest_attestation(  # type: ignore[attr-defined]
            mode="stdin",
            raw=raw,
            source_text=text,
        )


def _looks_like_task_ledger_work_item_id(value: str) -> bool:
    return bool(re.match(r"^(cap|task|wi|work_item|self_error)[A-Za-z0-9_.:-]*", value))


def _thread_claim_conflict_payload(
    *,
    operation: str,
    td_id: str,
    session_id: str,
    error: Exception,
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "schema": "work_ledger_mutation_claim_conflict_v1",
        "status": "blocked",
        "operation": operation,
        "td_id": td_id,
        "actor_session_id": session_id,
        "reason": "missing_or_stale_td_id_claim",
        "message": str(error),
        "repair_route": "Run session-claim --td-id for this actor_session_id, then retry the mutation.",
    }
    if td_id and not work_ledger.TD_ID_RE.fullmatch(td_id):
        requested_kind = "task_ledger_work_item_id" if _looks_like_task_ledger_work_item_id(td_id) else "non_work_ledger_td_id"
        payload["identity_axis_mismatch"] = {
            "schema": "work_ledger_identity_axis_mismatch_v1",
            "requested_id": td_id,
            "requested_id_kind": requested_kind,
            "expected_id_kind": "work_ledger_td_id",
            "expected_pattern": "td_*",
            "why": (
                "Work Ledger close/supersede/reopen mutate Work Ledger threads. "
                "Task Ledger WorkItem ids can be recorded through progress, which opens "
                "a bridge thread and returns a generated td_id plus next_close_command."
            ),
            "progress_bridge_command": (
                "./repo-python tools/meta/factory/work_ledger.py progress "
                "--td-id <task_ledger_work_item_id> --title '<progress-title>' "
                "--body-file '<closeout-body.md>'"
            ),
            "task_ledger_receipt_command": (
                "./repo-python tools/meta/factory/task_ledger_apply.py "
                "record-execution-receipt --subject-id <task_ledger_work_item_id> "
                "--transaction-id <transaction_id> --commit-hash <commit_hash> --rebuild"
            ),
        }
        if operation in {"todo_close", "todo_supersede", "todo_reopen"}:
            payload["repair_route"] = (
                "Do not pass a Task Ledger WorkItem id to close/supersede/reopen. "
                "Use the generated Work Ledger td_id from a prior progress bridge "
                "result (next_close_command), or record closeout through the Task Ledger "
                "execution-receipt/note lane."
            )
    return payload


def _claim_conflict_exit(*, operation: str, td_id: str, session_id: str, error: Exception) -> None:
    raise SystemExit(
        json.dumps(
            _thread_claim_conflict_payload(
                operation=operation,
                td_id=td_id,
                session_id=session_id,
                error=error,
            ),
            sort_keys=True,
        )
    )


def _work_item_claim_conflict_exit(
    *,
    operation: str,
    work_item_id: str,
    session_id: str,
    error: Exception,
) -> None:
    raise SystemExit(
        json.dumps(
            {
                "schema": "work_ledger_mutation_claim_conflict_v1",
                "status": "blocked",
                "operation": operation,
                "work_item_id": work_item_id,
                "actor_session_id": session_id,
                "reason": "missing_or_stale_work_item_id_claim",
                "message": str(error),
                "repair_route": "Run session-preflight --td-id <work_item_id> for this actor_session_id, then retry the mutation.",
            },
            sort_keys=True,
        )
    )


def _read_receipt_error_reason(message: str) -> str:
    normalized = message.lower()
    if "ended session" in normalized:
        return "ended_session"
    if "does not match" in normalized:
        return "session_mismatch"
    if "not valid" in normalized:
        return "invalid_receipt"
    if "required" in normalized:
        return "missing_receipt"
    return "receipt_validation_failed"


def _read_receipt_error_exit(
    *,
    command: str,
    operation: str,
    args: argparse.Namespace,
    error: Exception,
) -> None:
    message = str(error)
    actor = str(getattr(args, "actor", "") or "<actor>").strip() or "<actor>"
    phase_id = str(getattr(args, "phase_id", "") or "<phase_id>").strip() or "<phase_id>"
    family_id = str(getattr(args, "family_id", "") or "<family_id>").strip() or "<family_id>"
    target_id = str(getattr(args, "td_id", "") or "").strip()
    session_slug = f"<new_{command}_session_slug>"
    recovery_command = (
        "./repo-python tools/meta/factory/work_ledger.py session-preflight "
        f"--session-slug {session_slug} --actor {actor} --phase-id {phase_id} --family-id {family_id}"
    )
    if target_id:
        recovery_command += f" --td-id {target_id}"
    payload: Dict[str, Any] = {
        "schema": "work_ledger_read_receipt_error_v1",
        "status": "blocked",
        "command": command,
        "operation": operation,
        "reason": _read_receipt_error_reason(message),
        "message": message,
        "read_receipt_id": str(getattr(args, "read_receipt_id", "") or "").strip(),
        "actor_session_id": str(getattr(args, "actor_session_id", "") or "").strip(),
        "repair_route": (
            "Read receipts are live-session write tokens. Append progress before "
            "session-finalize; after finalization, bootstrap a new session and retry "
            "with the new read_receipt_id."
        ),
        "recovery_command": recovery_command,
    }
    if target_id:
        payload["td_id"] = target_id
    raise SystemExit(json.dumps(payload, sort_keys=True))


def _verify_thread_claim_or_bypass(
    args: argparse.Namespace,
    *,
    operation: str,
    allow_unclaimed_note: bool = False,
) -> None:
    args._mutation_guard = None  # type: ignore[attr-defined]
    td_id = str(getattr(args, "td_id", "") or "").strip()
    session_id = str(getattr(args, "actor_session_id", "") or "").strip()
    try:
        claim = work_ledger_runtime.require_active_thread_claim(
            REPO_ROOT,
            session_id=session_id,
            td_id=td_id,
            operation=operation,
        )
    except ValueError as exc:
        if not (allow_unclaimed_note and bool(getattr(args, "allow_unclaimed_note", False))):
            _claim_conflict_exit(operation=operation, td_id=td_id, session_id=session_id, error=exc)
        args._mutation_guard = {  # type: ignore[attr-defined]
            "schema": "work_ledger_mutation_guard_v1",
            "status": "claim_bypassed",
            "mode": "explicit_unclaimed_note",
            "severity": "warning",
            "operation": operation,
            "td_id": td_id,
            "actor_session_id": session_id,
            "reason": "operator_marked_low_blast_unclaimed_note",
            "repair_route": "Prefer session-claim --td-id before mutating a WorkItem.",
        }
        return
    args._mutation_guard = {  # type: ignore[attr-defined]
        "schema": "work_ledger_mutation_guard_v1",
        "status": "claim_verified",
        "operation": operation,
        "td_id": td_id,
        "actor_session_id": session_id,
        "claim_id": claim.get("claim_id"),
        "claim_scope": claim.get("scope_id") or claim.get("td_id"),
        "leased_until": claim.get("leased_until"),
    }


def _verify_work_item_claim_or_bypass(
    args: argparse.Namespace,
    *,
    operation: str,
    allow_unclaimed_note: bool = False,
) -> None:
    args._mutation_guard = None  # type: ignore[attr-defined]
    work_item_id = str(getattr(args, "td_id", "") or "").strip()
    session_id = str(getattr(args, "actor_session_id", "") or "").strip()
    try:
        claim = work_ledger_runtime.require_active_work_item_claim(
            REPO_ROOT,
            session_id=session_id,
            work_item_id=work_item_id,
            operation=operation,
        )
    except ValueError as exc:
        if not (allow_unclaimed_note and bool(getattr(args, "allow_unclaimed_note", False))):
            _work_item_claim_conflict_exit(
                operation=operation,
                work_item_id=work_item_id,
                session_id=session_id,
                error=exc,
            )
        args._mutation_guard = {  # type: ignore[attr-defined]
            "schema": "work_ledger_mutation_guard_v1",
            "status": "claim_bypassed",
            "mode": "explicit_unclaimed_work_item_note",
            "severity": "warning",
            "operation": operation,
            "work_item_id": work_item_id,
            "actor_session_id": session_id,
            "reason": "operator_marked_low_blast_unclaimed_note",
            "repair_route": "Prefer session-preflight --td-id <work_item_id> before appending WorkItem progress.",
        }
        return
    args._mutation_guard = {  # type: ignore[attr-defined]
        "schema": "work_ledger_mutation_guard_v1",
        "status": "claim_verified",
        "operation": operation,
        "work_item_id": work_item_id,
        "actor_session_id": session_id,
        "claim_id": claim.get("claim_id"),
        "claim_scope": claim.get("scope_id") or claim.get("work_item_id"),
        "leased_until": claim.get("leased_until"),
    }


def _require_receipt(args: argparse.Namespace) -> Dict[str, Any]:
    session = work_ledger_runtime.validate_read_receipt(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
    )
    if not getattr(args, "actor_session_id", None):
        args.actor_session_id = str(session.get("session_id") or "")
    if not getattr(args, "actor", None):
        args.actor = str(session.get("actor") or "unknown")
    if not getattr(args, "phase_id", None):
        args.phase_id = str(session.get("phase_id") or "")
    if not getattr(args, "family_id", None):
        args.family_id = str(session.get("family_id") or "")
    # Resolve --body / --body-file / --body-stdin once per mutation command and
    # stash any body_ingest attestation metadata on args for _metadata_from_args
    # to pick up. Body args are only present on mutation parsers (append-open /
    # progress / note / close / supersede / reopen); reads are no-ops elsewhere.
    if hasattr(args, "body") or hasattr(args, "body_file") or hasattr(args, "body_stdin"):
        _resolve_body_and_ingest(args)
    return session


def cmd_bootstrap(args: argparse.Namespace) -> int:
    payload = work_ledger.bootstrap_phase_bucket(
        REPO_ROOT,
        phase_id=args.phase_id,
        family_id=args.family_id,
    )
    return _print(payload)


def cmd_session_bootstrap(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.bootstrap_session(
        REPO_ROOT,
        session_id=args.session_id,
        actor=args.actor,
        phase_id=args.phase_id,
        family_id=args.family_id,
        limit=args.limit,
    )
    return _print(payload)


def cmd_session_activity(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.mark_session_activity(
        REPO_ROOT,
        session_id=args.session_id,
        action=args.action,
        td_id=args.td_id,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(
        _compact_session_lifecycle_payload(
            payload,
            schema="work_ledger_session_activity_result_v1",
            command="session-activity",
            session_id=args.session_id,
            action=args.action,
            limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
        )
    )


def cmd_session_heartbeat(args: argparse.Namespace) -> int:
    if not args.current_pass_line and not args.last_pass_result_line:
        raise SystemExit(
            "session-heartbeat requires --current-pass-line/--now or "
            "--last-pass-result-line/--done"
        )
    pass_state = SESSION_HEARTBEAT_STATE_ALIASES.get(str(args.state or ""), args.state)
    payload = work_ledger_runtime.mark_session_pass_heartbeat(
        REPO_ROOT,
        session_id=args.session_id,
        pass_state=pass_state,
        current_pass_line=args.current_pass_line,
        last_pass_result_line=args.last_pass_result_line,
        td_id=args.td_id,
        scope_refs=list(args.scope_ref or []),
        pass_id=args.pass_id,
        source=args.source,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(
        _compact_session_lifecycle_payload(
            payload,
            schema="work_ledger_session_heartbeat_result_v1",
            command="session-heartbeat",
            session_id=args.session_id,
            action=pass_state,
            limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
        )
    )


def cmd_session_finalize(args: argparse.Namespace) -> int:
    append_exempt_reason = str(getattr(args, "append_exempt_reason", "") or "").strip()
    if append_exempt_reason:
        read_receipt_id = str(getattr(args, "read_receipt_id", "") or "").strip()
        if not read_receipt_id:
            raise SystemExit("--read-receipt-id is required with --append-exempt-reason")
        work_ledger_runtime.mark_session_append_exempt(
            REPO_ROOT,
            read_receipt_id=read_receipt_id,
            session_id=args.session_id,
            reason=append_exempt_reason,
            evidence_refs=list(getattr(args, "append_exempt_ref", []) or []),
            td_ids=list(getattr(args, "append_exempt_td_id", []) or []),
            work_item_ids=list(getattr(args, "append_exempt_work_item_id", []) or []),
        )
    if not bool(getattr(args, "allow_missing_append", False)):
        pre_status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
        sessions = pre_status.get("sessions") if isinstance(pre_status.get("sessions"), Mapping) else {}
        session = dict(sessions.get(args.session_id) or {}) if isinstance(sessions, Mapping) else {}
        append_satisfied = bool(session.get("session_had_ledger_append")) or bool(
            session.get("append_exempt")
        )
        if session.get("touched_work") and not append_satisfied:
            payload = _compact_session_lifecycle_payload(
                pre_status,
                schema="work_ledger_session_finalize_result_v1",
                command="session-finalize",
                session_id=args.session_id,
                action=args.action,
                limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
            )
            payload["status"] = "blocked"
            payload["mutation_performed"] = False
            payload["blocked_by"] = ["append_missing_before_finalize"]
            payload["safe_next_action"] = (
                "Append progress, close, or append-open evidence with the live "
                "read_receipt_id, then run session-finalize again. For commit-only "
                "or projection-only sessions, rerun session-finalize with "
                "--read-receipt-id <wlr_*> --append-exempt-reason <reason> "
                "--append-exempt-ref <commit-or-receipt-ref>."
            )
            payload["append_exempt_closeout"] = {
                "required_flag": "--append-exempt-reason",
                "requires": ["--read-receipt-id"],
                "optional_refs": ["--append-exempt-ref", "--append-exempt-td-id", "--append-exempt-work-item-id"],
                "use_when": (
                    "The session touched work through path claims and the durable "
                    "evidence is a scoped commit, Task Ledger receipt, or generated "
                    "projection settlement rather than a Work Ledger append."
                ),
            }
            payload["diagnostic_escape_hatch"] = {
                "flag": "--allow-missing-append",
                "use_only_when": (
                    "You intentionally want to finalize as stale after recording why "
                    "no Work Ledger append can be written in this session."
                ),
            }
            _print(payload)
            return 2
    payload = work_ledger_runtime.finalize_session(
        REPO_ROOT,
        session_id=args.session_id,
        action=args.action,
        release_claims=not bool(getattr(args, "no_release_claims", False)),
        release_reason=args.action,
    )
    if getattr(args, "full", False):
        return _print(payload)
    return _print(
        _compact_session_lifecycle_payload(
            payload,
            schema="work_ledger_session_finalize_result_v1",
            command="session-finalize",
            session_id=args.session_id,
            action=args.action,
            limit=getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT),
        )
    )


def cmd_session_status(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    session_id = str(getattr(args, "session_id", "") or "").strip()
    limit = getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT)
    if session_id:
        return _print(
            _compact_single_session_status(
                payload,
                session_id=session_id,
                limit=limit,
                include_full_session=bool(getattr(args, "full", False)),
            )
        )
    if getattr(args, "full", False):
        return _print(payload)
    seed_speed = bool(
        getattr(args, "seed_speed", False) or getattr(args, "speed_only", False)
    )
    overview_limit = max(int(limit or 0), 100) if seed_speed else limit
    overview = work_ledger_runtime.build_session_cohort_overview(
        payload,
        limit=overview_limit,
    )
    if seed_speed:
        dirty_tree_pressure = None
        if bool(getattr(args, "no_heartbeat", False)) or bool(
            getattr(args, "dirty_tree_pressure", False)
        ):
            dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(REPO_ROOT)
            dirty_tree_pressure = work_ledger_runtime.build_dirty_tree_bankruptcy_pressure(
                REPO_ROOT,
                status=payload,
                dirty_paths=dirty_paths,
                dirty_scan_status=dirty_scan_status,
                bankruptcy_authorized=bool(
                    getattr(args, "bankruptcy_authorized", False)
                ),
                limit=limit,
            )
            dirty_tree_pressure["sweep_dry_run"] = True
        return _print(
            _seed_speed_status(
                overview,
                limit=limit,
                prefer_non_heartbeat=bool(getattr(args, "no_heartbeat", False)),
                dirty_tree_pressure=dirty_tree_pressure,
            )
        )
    if getattr(args, "with_session_cards", False):
        return _print(overview)
    return _print(
        _compact_session_status_overview(
            overview,
            limit=limit,
            include_rows=not bool(getattr(args, "cards_only", False)),
        )
    )


def cmd_session_claims(args: argparse.Namespace) -> int:
    limit = getattr(args, "limit", work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT)
    if getattr(args, "refresh", False):
        status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
        work_ledger_runtime.write_active_claims_snapshot(REPO_ROOT, status)
    payload = work_ledger_runtime.load_active_claims_snapshot(
        REPO_ROOT,
        limit=limit,
        allow_stale=bool(getattr(args, "allow_stale", False)),
    )
    if not getattr(args, "full", False):
        payload = _compact_session_claims_cards(payload, limit=limit)
    return _print(payload)


def _compact_claim_card(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "scope_kind": row.get("scope_kind"),
        "scope_id": row.get("scope_id"),
        "td_id": row.get("td_id"),
        "path": row.get("path"),
        "work_item_id": row.get("work_item_id"),
        "session_id": row.get("session_id"),
        "actor": row.get("actor"),
        "phase_id": row.get("phase_id"),
        "leased_until": row.get("leased_until"),
    }


def _compact_session_claims_cards(snapshot: Mapping[str, Any], *, limit: int) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    collisions = [
        row
        for row in list(snapshot.get("claim_collisions") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    return {
        "schema": "work_ledger_active_claims_cards_v1",
        "generated_at": snapshot.get("generated_at"),
        "status": snapshot.get("status"),
        "counts": snapshot.get("counts") or {},
        "active_claim_cards": [
            _compact_claim_card(row)
            for row in list(snapshot.get("active_claims") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ],
        "claim_collision_cards": [
            {
                "scope_kind": row.get("scope_kind"),
                "scope_id": row.get("scope_id"),
                "td_id": row.get("td_id"),
                "path": row.get("path"),
                "work_item_id": row.get("work_item_id"),
                "claim_count": row.get("claim_count"),
                "actors": list(row.get("actors") or []),
                "active_claim_cards": [
                    _compact_claim_card(claim)
                    for claim in list(row.get("active_claims") or [])[:safe_limit]
                    if isinstance(claim, Mapping)
                ],
            }
            for row in collisions
        ],
        "truncation": snapshot.get("truncation") or {},
        "source_freshness": {
            "status": (snapshot.get("source_freshness") or {}).get("status")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
            "policy": (snapshot.get("source_freshness") or {}).get("policy")
            if isinstance(snapshot.get("source_freshness"), Mapping)
            else None,
        },
        "drilldown_commands": {
            "full_claims": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit} --full"
            ),
            "refresh": WORK_LEDGER_REFRESH_CLAIMS_COMMAND,
            "session_overview_cards": WORK_LEDGER_SESSION_OVERVIEW_CARDS_COMMAND,
            "seed_speed_status": WORK_LEDGER_SEED_SPEED_COMMAND,
            "mutation_check": "./repo-python tools/meta/factory/work_ledger.py mutation-check --path <path> --require-exclusive",
        },
        "omission_receipt": {
            "omitted": [
                "claim_id",
                "claimed_at",
                "released_at",
                "expired_at",
                "note",
                "release_reason",
                "source_receipt",
                "source_hash",
            ],
            "reason": "cards-only claims preserve scope, owner session, collision, and lease fields for routine routing; full claim rows remain behind the drilldown.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-claims --limit {safe_limit} --full"
            ),
        },
    }


def _parse_optional_datetime(value: Any) -> datetime | None:
    token = str(value or "").strip()
    if not token:
        return None
    if token.endswith("Z"):
        token = f"{token[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(token)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _pass_freshness_for_session(row: Mapping[str, Any], heartbeat: Mapping[str, Any]) -> str | None:
    explicit = str(heartbeat.get("freshness_state") or "").strip()
    if explicit:
        return explicit
    if row.get("ended_at") or row.get("ended"):
        return "ended"
    if row.get("orphaned_active"):
        return "orphaned"
    if row.get("stale"):
        return "stale"
    expires_at = _parse_optional_datetime(heartbeat.get("expires_at"))
    if expires_at is not None and expires_at < datetime.now(timezone.utc):
        return "expired"
    if heartbeat:
        return "live"
    return None


def _compact_session_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    risk_flags: list[str] = []
    if row.get("orphaned_active"):
        risk_flags.append("orphaned_active")
    if row.get("stale"):
        risk_flags.append("stale")
    if row.get("unclaimed_touched_td_ids") or row.get("unclaimed_touched_work_item_ids"):
        risk_flags.append("unclaimed_touched_work")
    if row.get("active_claims"):
        risk_flags.append("active_claims")
    heartbeat = (
        dict(row.get("pass_heartbeat") or {})
        if isinstance(row.get("pass_heartbeat"), Mapping)
        else {}
    )
    return {
        "session_id": row.get("session_id"),
        "actor": row.get("actor"),
        "phase_id": row.get("phase_id"),
        "last_activity_at": row.get("last_activity_at"),
        "last_signal_at": row.get("last_signal_at"),
        "idle_seconds": row.get("idle_seconds"),
        "pass_state": heartbeat.get("pass_state"),
        "current_pass_line": heartbeat.get("current_pass_line"),
        "last_pass_result_line": heartbeat.get("last_pass_result_line"),
        "freshness_state": _pass_freshness_for_session(row, heartbeat),
        "pass_source": heartbeat.get("source"),
        "risk_flags": risk_flags,
        "drilldown_command": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
    }


def _compact_single_session_status(
    runtime_status: Mapping[str, Any],
    *,
    session_id: str,
    limit: int,
    include_full_session: bool = False,
) -> Dict[str, Any]:
    sessions = runtime_status.get("sessions") if isinstance(runtime_status.get("sessions"), Mapping) else {}
    session = sessions.get(session_id) if isinstance(sessions, Mapping) else None
    safe_limit = max(0, int(limit or 0))
    if not isinstance(session, Mapping):
        return {
            "schema": "work_ledger_session_status_card_v1",
            "status": "missing",
            "session_id": session_id,
            "hint": "Run session-status --overview --with-session-cards to inspect active session ids.",
            "drilldown_commands": {
                "overview": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
                "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
            },
        }

    active_claims = [
        claim
        for claim in list(session.get("claims") or [])[:safe_limit]
        if isinstance(claim, Mapping) and not claim.get("released_at") and not claim.get("expired_at")
    ]
    payload: Dict[str, Any] = {
        "schema": "work_ledger_session_status_detail_v1"
        if include_full_session
        else "work_ledger_session_status_card_v1",
        "status": "found",
        "session_id": session_id,
        "session": dict(session) if include_full_session else _compact_session_row(session),
        "session_state": {
            "ended": bool(session.get("ended_at")),
            "stale": bool(session.get("stale")),
            "append_exempt": bool(session.get("append_exempt")),
            "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
            "touched_work": bool(session.get("touched_work")),
        },
        "active_claim_count": len(active_claims),
        "active_claim_cards": [_compact_claim_card(claim) for claim in active_claims],
        "drilldown_commands": {
            "overview": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
            "single_full": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --session-id {shlex.quote(session_id)} --full"
            ),
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
    }
    if not session.get("ended_at"):
        payload["finalize_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-finalize --session-id {shlex.quote(session_id)}"
        )
    return payload


_AWARENESS_CARD_KEYS: tuple[str, ...] = (
    "session_id",
    "actor",
    "phase_id",
    "freshness_state",
    "idle_seconds",
    "orphaned_active",
    "pass_id",
    "pass_seq",
    "pass_state",
    "current_pass_line",
    "last_pass_result_line",
    "source",
    "updated_at",
    "scope_refs",
    "claim_refs",
    "touched_td_ids",
    "touched_work_item_ids",
)


def _awareness_repair_summary(
    repair_rows: List[Mapping[str, Any]],
    *,
    session_id: str | None,
) -> Dict[str, Any]:
    failure_classes = sorted(
        {
            str(row.get("failure_class"))
            for row in repair_rows
            if row.get("failure_class")
        }
    )
    owning_surfaces = sorted(
        {
            str(row.get("owning_surface"))
            for row in repair_rows
            if row.get("owning_surface")
        }
    )
    drilldown = "./repo-python tools/meta/factory/work_ledger.py session-status --full"
    if session_id:
        drilldown = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-status --session-id {shlex.quote(session_id)} --full"
        )
    return {
        "repair_row_count": len(repair_rows),
        "failure_classes": failure_classes,
        "owning_surfaces": owning_surfaces[:4],
        "drilldown": drilldown,
    }


def _compact_awareness_card(
    row: Mapping[str, Any],
    *,
    include_repair_rows: bool,
) -> Dict[str, Any]:
    card: Dict[str, Any] = {}
    for key in _AWARENESS_CARD_KEYS:
        value = row.get(key)
        if isinstance(value, Mapping):
            card[key] = dict(value)
        elif isinstance(value, list):
            card[key] = list(value)
        else:
            card[key] = value

    repair_rows = [
        dict(item) for item in list(row.get("repair_rows") or []) if isinstance(item, Mapping)
    ]
    if not repair_rows:
        return card
    if include_repair_rows:
        card["repair_rows"] = repair_rows
    else:
        card["repair_summary"] = _awareness_repair_summary(
            repair_rows,
            session_id=str(row.get("session_id") or "") or None,
        )
    return card


def _cohort_speed_summary(
    overview: Mapping[str, Any],
    *,
    awareness_cards: List[Mapping[str, Any]],
) -> Dict[str, Any]:
    counts = overview.get("counts") if isinstance(overview.get("counts"), Mapping) else {}
    heartbeat = (
        overview.get("heartbeat_participation")
        if isinstance(overview.get("heartbeat_participation"), Mapping)
        else {}
    )
    active_claim_session_ids = sorted(
        {
            str(card.get("session_id"))
            for card in awareness_cards
            if card.get("session_id") and card.get("claim_refs")
        }
    )
    return {
        "effective_active_sessions": counts.get(
            "effective_active_sessions", heartbeat.get("effective_active_sessions")
        ),
        "active_claims": counts.get("active_claims"),
        "active_claim_session_count": len(active_claim_session_ids),
        "active_claim_session_ids": active_claim_session_ids[:8],
        "explicit_current_pass_sessions": heartbeat.get("explicit_current_pass_count", 0),
        "projected_unknown_sessions": heartbeat.get("projected_unknown_count", 0),
        "orphaned_active_sessions": counts.get("orphaned_active_sessions"),
        "first_action": (
            "Use session-claims for write-active lanes, then publish session-heartbeat "
            "for participating live seeds that can write."
        ),
        "claims_fast_path": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-claims --refresh --limit 50 --cards-only"
        ),
        "heartbeat_fast_path": (
            "./repo-python tools/meta/factory/work_ledger.py "
            "session-heartbeat --session-id <id> --state <state> "
            "--now '<public current pass>' --done '<public previous result>' "
            "--scope-ref <path-or-claim>"
        ),
    }


def _seed_speed_status(
    overview: Mapping[str, Any],
    *,
    limit: int,
    prefer_non_heartbeat: bool = False,
    dirty_tree_pressure: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return work_ledger_runtime.build_seed_speed_status(
        overview,
        limit=limit,
        prefer_non_heartbeat=prefer_non_heartbeat,
        dirty_tree_pressure=dirty_tree_pressure,
    )


def _seed_speed_heartbeat_gap_row(card: Mapping[str, Any]) -> Dict[str, Any]:
    session_id = str(card.get("session_id") or "").strip()
    scope_ref = _seed_speed_scope_ref(card)
    return {
        "session_id": session_id,
        "actor": card.get("actor"),
        "phase_id": card.get("phase_id"),
        "active_claim_count": card.get("active_claim_count"),
        "heartbeat_source": card.get("heartbeat_source"),
        "freshness_state": card.get("freshness_state"),
        "scope_ref": scope_ref,
        "heartbeat_command": (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-heartbeat --session-id {shlex.quote(session_id)} --state <state> "
            "--now '<public current pass>' --done '<public previous result>' "
            f"--scope-ref {shlex.quote(scope_ref)}"
        ),
    }


def _seed_speed_scope_ref(card: Mapping[str, Any]) -> str:
    for key in ("paths_preview", "work_item_ids_preview", "td_ids_preview"):
        rows = card.get(key)
        if not isinstance(rows, list):
            continue
        for row in rows:
            text = str(row or "").strip()
            if text:
                return text
    return "<path-or-claim>"


def _seed_speed_claim_collision_failure_class(collision: Mapping[str, Any]) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
    if len(sessions) == 1 and len(claims) > 1:
        return "duplicate_same_session_claim"
    if collision.get("path"):
        return "path_claim_collision"
    if collision.get("work_item_id"):
        return "work_item_claim_collision"
    if collision.get("td_id"):
        return "td_claim_collision"
    return "claim_collision"


def _seed_speed_claim_collision_command(
    collision: Mapping[str, Any],
    *,
    failure_class: str,
) -> str:
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    sessions = sorted({str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")})
    claim_ids = [str(claim.get("claim_id") or "") for claim in claims if claim.get("claim_id")]
    path = str(collision.get("path") or "").strip()
    work_item_id = str(collision.get("work_item_id") or "").strip()
    td_id = str(collision.get("td_id") or "").strip()
    scope_kind = str(collision.get("scope_kind") or "").strip()
    if failure_class == "duplicate_same_session_claim" and sessions and claim_ids:
        return (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-release-claim --session-id {shlex.quote(sessions[0])} "
            f"--claim-id {shlex.quote(claim_ids[-1])} "
            "--reason duplicate_same_session_claim"
        )
    if path:
        return (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"mutation-check --path {shlex.quote(path)} --require-exclusive"
        )
    if work_item_id:
        return (
            "./repo-python tools/meta/control/mission_transaction_preflight.py "
            f"--subject-id {shlex.quote(work_item_id)} --control-summary"
        )
    if td_id:
        return (
            "./repo-python tools/meta/control/mission_transaction_preflight.py "
            f"--subject-id {shlex.quote(td_id)} --control-summary"
        )
    return (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-claims --refresh --limit 12 --full # scope_kind={shlex.quote(scope_kind)}"
    )


def _seed_speed_claim_collision_action_row(collision: Mapping[str, Any]) -> Dict[str, Any]:
    failure_class = _seed_speed_claim_collision_failure_class(collision)
    claims = [claim for claim in collision.get("active_claims") or [] if isinstance(claim, Mapping)]
    return {
        "failure_class": failure_class,
        "scope_kind": collision.get("scope_kind"),
        "scope_id": collision.get("scope_id"),
        "td_id": collision.get("td_id"),
        "path": collision.get("path"),
        "work_item_id": collision.get("work_item_id"),
        "claim_count": collision.get("claim_count"),
        "actors": list(collision.get("actors") or []),
        "session_ids": sorted(
            {str(claim.get("session_id") or "") for claim in claims if claim.get("session_id")}
        ),
        "active_claims_preview": [
            {
                "claim_id": claim.get("claim_id"),
                "session_id": claim.get("session_id"),
                "actor": claim.get("actor"),
                "phase_id": claim.get("phase_id"),
                "scope_kind": claim.get("scope_kind"),
                "path": claim.get("path"),
                "work_item_id": claim.get("work_item_id"),
                "td_id": claim.get("td_id"),
                "leased_until": claim.get("leased_until"),
            }
            for claim in claims[:3]
        ],
        "safe_next_command": _seed_speed_claim_collision_command(
            collision,
            failure_class=failure_class,
        ),
    }


def _compact_session_status_overview(
    overview: Mapping[str, Any],
    *,
    limit: int,
    include_rows: bool = True,
) -> Dict[str, Any]:
    safe_limit = max(0, int(limit or 0))
    contention = overview.get("contention") if isinstance(overview.get("contention"), Mapping) else {}
    awareness_cards = [
        _compact_awareness_card(row, include_repair_rows=include_rows)
        for row in list(overview.get("awareness_cards") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    repair_rows = [
        dict(row)
        for row in list(overview.get("repair_rows") or [])[:safe_limit]
        if isinstance(row, Mapping)
    ]
    payload: Dict[str, Any] = {
        "schema": overview.get("schema"),
        "generated_at": overview.get("generated_at"),
        "mode": "compact_overview" if include_rows else "cards_only_overview",
        "orphan_after_seconds": overview.get("orphan_after_seconds"),
        "counts": overview.get("counts") or {},
        "monitor_cards": list(overview.get("monitor_cards") or []),
        "awareness_cards": awareness_cards,
        "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
        "repair_rows": repair_rows,
        "cohort_speed_summary": _cohort_speed_summary(
            overview,
            awareness_cards=awareness_cards,
        ),
        "recommended_landing_lane": overview.get("recommended_landing_lane"),
        "contention": {
            "risk_level": contention.get("risk_level"),
            "signals": list(contention.get("signals") or []),
            "td_id_collision_count": len(contention.get("td_id_collisions") or []),
            "claim_collision_count": len(contention.get("claim_collisions") or []),
            "unknown_scope_active_session_count": len(contention.get("unknown_scope_active_sessions") or []),
            "unclaimed_touched_session_count": len(contention.get("unclaimed_touched_sessions") or []),
            "orphaned_active_session_count": len(contention.get("orphaned_active_sessions") or []),
        },
        "recommended_actions": list(overview.get("recommended_actions") or [])[:safe_limit],
        "drilldown_commands": {
            "with_session_cards": "./repo-python tools/meta/factory/work_ledger.py session-status --overview --with-session-cards --limit 12",
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
    }
    if include_rows:
        payload["active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
        payload["effective_active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("effective_active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
        payload["orphaned_active_session_rows"] = [
            _compact_session_row(row)
            for row in list(overview.get("orphaned_active_sessions") or [])[:safe_limit]
            if isinstance(row, Mapping)
        ]
    else:
        payload["omission_receipt"] = {
            "omitted": [
                "active_session_rows",
                "effective_active_session_rows",
                "orphaned_active_session_rows",
                "per_awareness_card_repair_rows",
            ],
            "reason": "cards-only overview preserves monitor cards, awareness cards, repair summaries, and counts for routine status checks; row evidence remains behind drilldowns.",
            "drilldown": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --overview --limit {safe_limit}"
            ),
        }
    return payload


def _compact_session_lifecycle_payload(
    status: Mapping[str, Any],
    *,
    schema: str,
    command: str,
    session_id: str,
    action: str,
    limit: int,
) -> Dict[str, Any]:
    sessions = status.get("sessions") if isinstance(status.get("sessions"), Mapping) else {}
    session = dict(sessions.get(session_id) or {}) if isinstance(sessions, Mapping) else {}
    overview = work_ledger_runtime.build_session_cohort_overview(status, limit=limit)
    contention = dict(overview.get("contention") or {})
    counts = dict(overview.get("counts") or {})
    session_summary: Dict[str, Any] | None = None
    if session:
        claims = [item for item in (session.get("claims") or []) if isinstance(item, Mapping)]
        active_claim_count = sum(
            1 for claim in claims if not claim.get("released_at") and not claim.get("expired_at")
        )
        session_summary = {
            "session_id": session.get("session_id"),
            "actor": session.get("actor"),
            "phase_id": session.get("phase_id"),
            "family_id": session.get("family_id"),
            "read_receipt_id": session.get("read_receipt_id"),
            "bootstrapped_at": session.get("bootstrapped_at"),
            "last_activity_at": session.get("last_activity_at"),
            "last_query_at": session.get("last_query_at"),
            "last_append_at": session.get("last_append_at"),
            "pass_heartbeat": dict(session.get("pass_heartbeat") or {})
            if isinstance(session.get("pass_heartbeat"), Mapping)
            else None,
            "ended_at": session.get("ended_at"),
            "end_action": session.get("end_action"),
            "has_activity": bool(session.get("has_activity")),
            "touched_work": bool(session.get("touched_work")),
            "touched_td_ids": list(session.get("touched_td_ids") or []),
            "touched_work_item_ids": list(session.get("touched_work_item_ids") or []),
            "queries": int(session.get("queries") or 0),
            "writes": int(session.get("writes") or 0),
            "session_had_ledger_append": bool(session.get("session_had_ledger_append")),
            "append_exempt": bool(session.get("append_exempt")),
            "append_exempt_reason": session.get("append_exempt_reason"),
            "append_exempt_refs": list(session.get("append_exempt_refs") or []),
            "append_exempted_at": session.get("append_exempted_at"),
            "stale": bool(session.get("stale")),
            "stale_reason": session.get("stale_reason"),
            "open_todos_touched_this_session": int(
                session.get("open_todos_touched_this_session") or 0
            ),
            "claim_count": len(claims),
            "active_claim_count": active_claim_count,
        }
    receipt_authority_guard: Dict[str, Any] | None = None
    if (
        command == "session-finalize"
        and session_summary
        and session_summary["touched_work"]
        and not session_summary["session_had_ledger_append"]
        and not session_summary["append_exempt"]
    ):
        receipt_authority_guard = {
            "status": "append_missing_before_finalize",
            "rule": (
                "Read receipts are live-session write tokens. Append or close the Work "
                "Ledger receipt before session-finalize; after finalization, this "
                "session's read_receipt_id cannot write."
            ),
            "point_of_use": "session-finalize compact payload",
            "mutation_stage": (
                "post_finalize_stale_session" if session_summary.get("ended_at") else "pre_finalize_block"
            ),
            "pre_finalize_repair": (
                "Run progress/close/append-open with the live read_receipt_id before "
                "running session-finalize."
            ),
            "post_finalize_recovery": (
                "Bootstrap a fresh Work Ledger session, append the missing receipt "
                "with the new read_receipt_id, then finalize that recovery session."
            ),
            "recovery_command_template": (
                "./repo-python tools/meta/factory/work_ledger.py session-preflight "
                "--session-slug <recovery_session_slug> --actor <actor> --phase-id <phase_id> "
                "--td-id <td_or_work_item_id>"
            ),
        }
    payload = {
        "schema": schema,
        "generated_at": status.get("generated_at") or work_ledger.utc_now(),
        "mode": "compact",
        "command": command,
        "session_id": session_id,
        "action": action,
        "session_found": bool(session),
        "session": session_summary,
        "overview_summary": {
            "schema": overview.get("schema"),
            "counts": {
                "sessions_total": counts.get("sessions_total", 0),
                "active_sessions": counts.get("active_sessions", 0),
                "effective_active_sessions": counts.get("effective_active_sessions", 0),
                "orphaned_active_sessions": counts.get("orphaned_active_sessions", 0),
                "stale_sessions": counts.get("stale_sessions", 0),
                "active_claims": counts.get("active_claims", 0),
                "claim_collisions": counts.get("claim_collisions", 0),
                "unclaimed_touched_sessions": counts.get("unclaimed_touched_sessions", 0),
            },
            "contention": {
                "risk_level": contention.get("risk_level", "clear"),
                "signals": list(contention.get("signals") or []),
            },
            "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
            "recommended_actions": list(overview.get("recommended_actions") or [])[:limit],
        },
        "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
        "drilldown_commands": {
            "compact_overview": (
                "./repo-python tools/meta/factory/work_ledger.py "
                f"session-status --overview --limit {int(limit or 0)}"
            ),
            "full_runtime": "./repo-python tools/meta/factory/work_ledger.py session-status --full",
        },
        "landmine_avoidance": {
            "rule": "Agent-facing lifecycle commands do not print runtime_status.sessions by default, and session-finalize blocks touched/no-append sessions before it releases claims unless an explicit append-exempt closeout is recorded.",
            "why": "The full session map is machine state; use compact overview unless diagnosing the runtime file itself. Finalize is the normal closeout path after a Work Ledger append exists; --append-exempt-reason is for commit-only/projection-only sessions, while --allow-missing-append and --no-release-claims are diagnostic escape hatches.",
        },
    }
    if receipt_authority_guard:
        payload["receipt_authority_guard"] = receipt_authority_guard
    return payload


def _iso_utc_from_epoch(epoch: object) -> str | None:
    try:
        value = int(epoch)
    except (TypeError, ValueError):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _json_loads_maybe(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    text = value.strip()
    if not text or text[0] not in "{[":
        return value
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return value


def _compact_codex_command(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if not text:
        return ""
    text = text.replace(str(Path.home()), "~")
    if len(text) > 240:
        return f"{text[:237]}..."
    return text


def _compact_handle_preview(value: Any, *, limit: int = OVERLAP_TITLE_PREVIEW_CHARS) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    safe_limit = max(16, int(limit or 16))
    if len(text) <= safe_limit:
        return text
    return f"{text[: max(0, safe_limit - 3)]}..."


def _handle_payload_kind(value: Any) -> str:
    text = str(value or "").lstrip()
    if text.startswith("PACKET v="):
        return "packet_title_or_long_prompt"
    if "\n" in text:
        return "long_prompt_or_trace_title"
    return "session_title"


def _session_title_handle_fields(row: Mapping[str, Any]) -> Dict[str, Any]:
    title = str(row.get("title") or row.get("external_title") or "")
    title_bytes = len(title.encode("utf-8"))
    title_hash = f"sha256:{hashlib.sha256(title.encode('utf-8')).hexdigest()}"
    preview = _compact_handle_preview(title)
    fields: Dict[str, Any] = {
        "title": title if title_bytes <= OVERLAP_TITLE_INLINE_BYTE_LIMIT else preview,
        "title_preview": preview,
        "title_bytes": title_bytes,
        "title_hash": title_hash,
        "title_kind": _handle_payload_kind(title),
        "title_full_omitted": title_bytes > OVERLAP_TITLE_INLINE_BYTE_LIMIT,
    }
    if title_bytes > OVERLAP_TITLE_INLINE_BYTE_LIMIT:
        session_id = str(row.get("session_id") or "").strip()
        title_drilldown = (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same session-preflight args>"
        )
        fields["title_ref"] = (
            f"work_ledger_runtime_session:{session_id}:external_title"
            if session_id
            else "work_ledger_runtime_session:external_title"
        )
        fields["title_drilldown"] = title_drilldown
        fields["omission_receipt"] = {
            "omitted": ["full title body"],
            "reason": (
                "Overlap rows identify sessions; full prompt/title bodies remain "
                "recoverable by rerunning the same Work Ledger session-preflight "
                "with --full."
            ),
            "drilldown": title_drilldown,
            "source_ref": fields["title_ref"],
        }
    return fields


def _normalize_codex_repo_path(raw_path: Any, repo_root: Path) -> str | None:
    token = str(raw_path or "").strip().strip("\"'`[]{}(),;")
    token = token.replace("\\/", "/")
    root_prefix = f"{repo_root}/"
    if token.startswith(root_prefix):
        token = token[len(root_prefix) :]
    if token.startswith("./"):
        token = token[2:]
    token = re.sub(r"(?::\d+|#L\d+)$", "", token)
    token = token.strip().strip("\"'`[]{}(),;")
    if not token or token.startswith("/") or token.startswith("~"):
        return None
    if "..." in token:
        return None
    parts = [part for part in token.split("/") if part]
    if not parts or any(part == ".." for part in parts):
        return None
    if token.startswith((".codex/auth", ".codex/config", ".claude/.credentials")):
        return None
    return "/".join(parts)


def _extract_codex_repo_paths(text: Any, repo_root: Path) -> List[str]:
    haystack = str(text or "")
    if not haystack:
        return []
    haystack = haystack.replace(f"{repo_root}/", "")
    paths: List[str] = []
    for match in _CODEX_PATH_TOKEN_RE.finditer(haystack):
        path = _normalize_codex_repo_path(match.group("path"), repo_root)
        if path:
            paths.append(path)
    return paths


def _extract_patch_paths(text: Any, repo_root: Path) -> List[str]:
    paths: List[str] = []
    for match in _CODEX_PATCH_FILE_RE.finditer(str(text or "")):
        path = _normalize_codex_repo_path(match.group("path"), repo_root)
        if path:
            paths.append(path)
    return paths


def _recent_unique(values: List[str], limit: int) -> List[str]:
    seen: set[str] = set()
    recent: List[str] = []
    for value in reversed(values):
        if not value or value in seen:
            continue
        seen.add(value)
        recent.append(value)
        if len(recent) >= limit:
            break
    return list(reversed(recent))


def _safe_codex_tool_texts(value: Any) -> List[tuple[str, str]]:
    decoded = _json_loads_maybe(value)
    collected: List[tuple[str, str]] = []
    if isinstance(decoded, dict):
        for key, nested in decoded.items():
            if key in {"encrypted_content", "output", "aggregated_output", "stdout", "stderr", "content", "message"}:
                continue
            if key in {"cmd", "path", "file", "filename", "workdir", "recipient_name"}:
                collected.append((key, str(nested or "")))
            collected.extend(_safe_codex_tool_texts(nested))
        return collected
    if isinstance(decoded, list):
        for nested in decoded:
            collected.extend(_safe_codex_tool_texts(nested))
        return collected
    if isinstance(decoded, str):
        collected.append(("text", decoded))
    return collected


def _codex_command_from_event_payload(payload: Dict[str, Any]) -> str:
    command = payload.get("command")
    if isinstance(command, list):
        argv = [str(part) for part in command]
        if "-lc" in argv:
            index = argv.index("-lc")
            if index + 1 < len(argv):
                return argv[index + 1]
        return " ".join(argv)
    return ""


def _codex_rollout_activity_summary(
    rollout_path: str | None,
    *,
    repo_root: Path,
    max_events: int = CODEX_ROLLOUT_TAIL_EVENTS,
) -> Dict[str, Any] | None:
    if not rollout_path:
        return None
    path = Path(str(rollout_path)).expanduser()
    if not path.exists() or not path.is_file():
        return {
            "schema": "codex_rollout_activity_summary_v1",
            "rollout_path": str(path),
            "available": False,
            "reason": "rollout_path_missing",
        }
    lines: deque[str] = deque(maxlen=max(1, int(max_events or 1)))
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for line in handle:
            if line.strip():
                lines.append(line)
    tool_counts: Counter[str] = Counter()
    commands: List[str] = []
    referenced_paths: List[str] = []
    mutation_paths: List[str] = []
    parsed_events = 0
    for line in lines:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, dict):
            continue
        parsed_events += 1
        payload = event.get("payload")
        if not isinstance(payload, dict):
            continue
        if event.get("type") == "response_item" and payload.get("type") == "function_call":
            tool_name = str(payload.get("name") or "unknown")
            tool_counts[tool_name] += 1
            raw_arguments = payload.get("arguments")
            for key, text in _safe_codex_tool_texts(raw_arguments):
                if key == "cmd":
                    command = _compact_codex_command(text)
                    if command:
                        commands.append(command)
                referenced_paths.extend(_extract_codex_repo_paths(text, repo_root))
            if tool_name.endswith("apply_patch"):
                mutation_paths.extend(_extract_patch_paths(raw_arguments, repo_root))
        elif event.get("type") == "event_msg" and payload.get("type") == "exec_command_end":
            tool_counts["exec_command"] += 1
            raw_command = _codex_command_from_event_payload(payload)
            command = _compact_codex_command(raw_command)
            if command:
                commands.append(command)
                referenced_paths.extend(_extract_codex_repo_paths(raw_command, repo_root))
            parsed_cmd = payload.get("parsed_cmd")
            if isinstance(parsed_cmd, list):
                for entry in parsed_cmd:
                    if isinstance(entry, dict):
                        for key in ("cmd", "path", "name"):
                            referenced_paths.extend(_extract_codex_repo_paths(entry.get(key), repo_root))
    return {
        "schema": "codex_rollout_activity_summary_v1",
        "rollout_path": str(path),
        "available": True,
        "tail_event_count": len(lines),
        "parsed_event_count": parsed_events,
        "recent_tool_names": sorted(tool_counts.keys()),
        "recent_commands": _recent_unique(commands, CODEX_ROLLOUT_COMMAND_LIMIT),
        "recent_referenced_paths": _recent_unique(referenced_paths, CODEX_ROLLOUT_PATH_LIMIT),
        "recent_mutation_paths": _recent_unique(mutation_paths, CODEX_ROLLOUT_PATH_LIMIT),
    }


def _codex_thread_candidates(
    *,
    db_path: Path,
    repo_root: Path,
    since_minutes: float,
    limit: int,
    include_all_cwds: bool,
) -> List[Dict[str, Any]]:
    if not db_path.exists():
        return []
    cutoff = int((datetime.now(timezone.utc) - timedelta(minutes=since_minutes)).timestamp())
    conditions = ["archived = 0", "updated_at >= ?"]
    params: List[Any] = [cutoff]
    if not include_all_cwds:
        conditions.append("(cwd = ? OR cwd LIKE ?)")
        params.extend((str(repo_root), f"{repo_root}/.claude/worktrees/%"))
    where_clause = " AND ".join(conditions)
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        conn.execute("PRAGMA query_only = 1")
        columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(threads)").fetchall()}
        rollout_select = "rollout_path" if "rollout_path" in columns else "NULL AS rollout_path"
        sql = (
            "SELECT id, created_at, updated_at, title, agent_role, reasoning_effort, "
            f"tokens_used, git_branch, model, cwd, {rollout_select} "
            f"FROM threads WHERE {where_clause} ORDER BY updated_at DESC LIMIT ?"
        )
        params.append(max(1, int(limit or 1)))
        rows = conn.execute(sql, params).fetchall()
    finally:
        conn.close()
    candidates: List[Dict[str, Any]] = []
    for row in rows:
        (
            thread_id,
            created_at,
            updated_at,
            title,
            agent_role,
            reasoning_effort,
            tokens_used,
            git_branch,
            model,
            cwd,
            rollout_path,
        ) = row
        rollout_activity = _codex_rollout_activity_summary(
            str(rollout_path or ""),
            repo_root=repo_root,
        )
        candidates.append(
            {
                "codex_thread_id": str(thread_id),
                "session_id": f"codex:{thread_id}",
                "title": title or "",
                "created_at": _iso_utc_from_epoch(created_at),
                "updated_at": _iso_utc_from_epoch(updated_at),
                "agent_role": agent_role or "",
                "reasoning_effort": reasoning_effort or "",
                "tokens_used": int(tokens_used or 0),
                "git_branch": git_branch or "",
                "model": model or "",
                "cwd": cwd or "",
                "rollout_path": rollout_path or "",
                "rollout_activity": rollout_activity,
            }
        )
    return candidates


def _import_codex_sessions(
    *,
    db_path: Path,
    actor: str,
    phase_id: str | None,
    family_id: str | None,
    since_minutes: float,
    limit: int,
    include_all_cwds: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    candidates = _codex_thread_candidates(
        db_path=db_path,
        repo_root=REPO_ROOT,
        since_minutes=since_minutes,
        limit=limit,
        include_all_cwds=include_all_cwds,
    )
    observations: List[Dict[str, Any]] = []
    if not dry_run:
        observations = work_ledger_runtime.observe_external_sessions(
            REPO_ROOT,
            observations=[
                {
                    "session_id": str(row["session_id"]),
                    "actor": actor,
                    "phase_id": phase_id,
                    "family_id": family_id,
                    "started_at": row.get("created_at"),
                    "last_signal_at": row.get("updated_at"),
                    "title": row.get("title"),
                    "source": "codex_state_5.sqlite",
                    "metadata": {
                        "codex_thread_id": row.get("codex_thread_id"),
                        "agent_role": row.get("agent_role"),
                        "reasoning_effort": row.get("reasoning_effort"),
                        "tokens_used": row.get("tokens_used"),
                        "git_branch": row.get("git_branch"),
                        "model": row.get("model"),
                        "cwd": row.get("cwd"),
                        "rollout_path": row.get("rollout_path"),
                        "rollout_activity": row.get("rollout_activity"),
                    },
                }
                for row in candidates
            ],
        )
    return {
        "schema": "work_ledger_codex_session_import_v1",
        "dry_run": bool(dry_run),
        "db_path": str(db_path),
        "since_minutes": float(since_minutes),
        "candidate_count": len(candidates),
        "imported_count": len(observations),
        "candidates": candidates,
        "observations": observations,
    }


def cmd_session_import_codex(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
    return _print(
        _import_codex_sessions(
            db_path=db_path,
            actor=args.actor,
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=bool(args.dry_run),
        )
    )


def _iso_utc_from_mtime(path: Path) -> str | None:
    try:
        return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()
    except OSError:
        return None


def _safe_load_json_file(path: Path) -> Dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _claude_todo_counts() -> Dict[str, int]:
    total = 0
    nonempty = 0
    if not CLAUDE_TODOS_DIR.exists():
        return {"todo_files_total": 0, "todo_files_nonempty": 0}
    for path in CLAUDE_TODOS_DIR.glob("*.json"):
        total += 1
        try:
            if path.stat().st_size > 5:
                nonempty += 1
        except OSError:
            continue
    return {"todo_files_total": total, "todo_files_nonempty": nonempty}


def _claude_ide_candidates(
    *,
    since_minutes: float,
    limit: int,
    include_all_workspaces: bool,
) -> List[Dict[str, Any]]:
    if not CLAUDE_IDE_DIR.exists():
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=float(since_minutes or 0))
    rows: List[Dict[str, Any]] = []
    for path in sorted(CLAUDE_IDE_DIR.glob("*.lock")):
        mtime_iso = _iso_utc_from_mtime(path)
        mtime = datetime.fromisoformat(mtime_iso) if mtime_iso else None
        if mtime is not None and since_minutes > 0 and mtime < cutoff:
            continue
        payload = _safe_load_json_file(path)
        workspace_folders = [
            str(item)
            for item in payload.get("workspaceFolders") or []
            if str(item or "").strip()
        ]
        repo_resolved = REPO_ROOT.resolve(strict=False)
        in_repo_scope = False
        for folder in workspace_folders:
            try:
                folder_resolved = Path(folder).expanduser().resolve(strict=False)
                in_repo_scope = in_repo_scope or (
                    folder_resolved == repo_resolved
                    or repo_resolved in folder_resolved.parents
                    or folder_resolved in repo_resolved.parents
                )
            except OSError:
                in_repo_scope = in_repo_scope or folder == str(REPO_ROOT) or folder.startswith(f"{REPO_ROOT}/")
        if not include_all_workspaces and workspace_folders and not in_repo_scope:
            continue
        pid = str(payload.get("pid") or path.stem).strip()
        rows.append(
            {
                "session_id": f"claude_ide:{pid}",
                "pid": pid,
                "lock_path": str(path),
                "last_activity_at": mtime_iso,
                "title": f"Claude IDE lock {pid}",
                "workspace_folders": workspace_folders,
                "in_repo_scope": in_repo_scope,
                "ide_name": str(payload.get("ideName") or ""),
                "transport": str(payload.get("transport") or ""),
                "running_in_windows": bool(payload.get("runningInWindows")),
            }
        )
    rows.sort(key=lambda row: str(row.get("last_activity_at") or ""), reverse=True)
    return rows[: max(1, int(limit or 1))]


def _import_claude_ide_sessions(
    *,
    phase_id: str | None,
    family_id: str | None,
    since_minutes: float,
    limit: int,
    include_all_workspaces: bool,
    dry_run: bool,
) -> Dict[str, Any]:
    candidates = _claude_ide_candidates(
        since_minutes=since_minutes,
        limit=limit,
        include_all_workspaces=include_all_workspaces,
    )
    todo_counts = _claude_todo_counts()
    observations: List[Dict[str, Any]] = []
    if not dry_run:
        observations = work_ledger_runtime.observe_external_sessions(
            REPO_ROOT,
            observations=[
                {
                    "session_id": str(row["session_id"]),
                    "actor": "claude_code",
                    "phase_id": phase_id,
                    "family_id": family_id,
                    "started_at": row.get("last_activity_at"),
                    "last_signal_at": row.get("last_activity_at"),
                    "title": row.get("title"),
                    "source": "claude_ide_lock",
                    "metadata": {
                        "pid": row.get("pid"),
                        "lock_path": row.get("lock_path"),
                        "workspace_folders": row.get("workspace_folders"),
                        "in_repo_scope": row.get("in_repo_scope"),
                        "ide_name": row.get("ide_name"),
                        "transport": row.get("transport"),
                        "running_in_windows": row.get("running_in_windows"),
                        **todo_counts,
                    },
                }
                for row in candidates
            ],
        )
    return {
        "schema": "work_ledger_claude_ide_import_v1",
        "dry_run": bool(dry_run),
        "since_minutes": float(since_minutes),
        "candidate_count": len(candidates),
        "imported_count": len(observations),
        "todo_counts": todo_counts,
        "candidates": candidates,
        "observations": observations,
    }


def cmd_session_import_host_surfaces(args: argparse.Namespace) -> int:
    db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
    codex_import = None
    claude_import = None
    if not args.skip_codex:
        codex_import = _import_codex_sessions(
            db_path=db_path,
            actor="codex",
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=bool(args.dry_run),
        )
    if not args.skip_claude:
        claude_import = _import_claude_ide_sessions(
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.limit,
            include_all_workspaces=bool(args.include_all_workspaces),
            dry_run=bool(args.dry_run),
        )
    status_after_imports = work_ledger_runtime.load_runtime_status(REPO_ROOT, rebuild=False)
    cached_overview = (
        status_after_imports.get("cohort_overview")
        if isinstance(status_after_imports.get("cohort_overview"), Mapping)
        else None
    )
    if (
        int(args.overview_limit or 0) == work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        and cached_overview is not None
    ):
        overview = dict(cached_overview)
    else:
        overview = work_ledger_runtime.build_session_cohort_overview(
            status_after_imports,
            limit=args.overview_limit,
        )
    signals = list((overview.get("contention") or {}).get("signals") or [])
    if claude_import and int(claude_import.get("candidate_count") or 0) > 1:
        signals.append("multiple_claude_ide_locks")
    return _print(
        {
            "schema": "work_ledger_host_surface_import_v1",
            "dry_run": bool(args.dry_run),
            "since_minutes": float(args.since_minutes),
            "codex_import": codex_import,
            "claude_ide_import": claude_import,
            "coordination": {
                "risk_level": (overview.get("contention") or {}).get("risk_level"),
                "signals": sorted(set(signals)),
                "counts": overview.get("counts") or {},
                "heartbeat_participation": overview.get("heartbeat_participation") or {},
                "recommended_actions": overview.get("recommended_actions") or [],
            },
        }
    )


def _session_slug(value: str | None) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", str(value or "autonomous").strip()).strip("_")
    return slug.lower() or "autonomous"


def _mint_preflight_session_id(actor: str, slug: str | None) -> str:
    actor_token = _session_slug(actor)
    slug_token = _session_slug(slug)
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{actor_token}_{now}_{slug_token}"


def _claim_scope(row: Mapping[str, Any]) -> tuple[str, str]:
    claim = row.get("claim") if isinstance(row.get("claim"), Mapping) else {}
    scope_kind = str(claim.get("scope_kind") or row.get("scope_kind") or "").strip()
    scope_id = str(
        claim.get("scope_id")
        or claim.get("td_id")
        or claim.get("work_item_id")
        or claim.get("path")
        or row.get("scope_id")
        or row.get("td_id")
        or row.get("work_item_id")
        or row.get("path")
        or ""
    ).strip()
    return scope_kind, scope_id


def _claim_closeout_plan(
    session_id: str,
    claims: List[Dict[str, Any]],
    *,
    read_receipt_id: str = "",
    actor: str = "",
    phase_id: str = "",
    family_id: str = "",
) -> Dict[str, Any]:
    progress_commands: List[str] = []
    close_commands: List[str] = []
    alternative_commands: List[Dict[str, Any]] = []
    session_arg = shlex.quote(session_id)
    receipt_arg = shlex.quote(read_receipt_id or "<live_read_receipt_id>")
    actor_arg = shlex.quote(actor or "<actor>")
    phase_arg = shlex.quote(phase_id or "<phase_id>")
    family_arg = shlex.quote(family_id or "<family_id>")
    td_ids: List[str] = []
    work_item_ids: List[str] = []
    path_claim_seen = False
    for row in claims:
        if not isinstance(row, Mapping):
            continue
        scope_kind, scope_id = _claim_scope(row)
        if not scope_id:
            continue
        if scope_kind == "td_id" and scope_id not in td_ids:
            td_ids.append(scope_id)
        elif scope_kind == "work_item_id" and scope_id not in work_item_ids:
            work_item_ids.append(scope_id)
        elif scope_kind == "path":
            path_claim_seen = True
    for work_item_id in work_item_ids[:3]:
        progress_commands.append(
            "./repo-python tools/meta/factory/work_ledger.py progress "
            f"--actor {actor_arg} --actor-session-id {session_arg} "
            f"--phase-id {phase_arg} --family-id {family_arg} "
            f"--read-receipt-id {receipt_arg} "
            f"--td-id {shlex.quote(work_item_id)} "
            "--title '<progress-title>' --body-file '<closeout-body.md>'"
        )
    for td_id in td_ids[:3]:
        close_commands.append(
            "./repo-python tools/meta/factory/work_ledger.py close "
            f"--actor {actor_arg} --actor-session-id {session_arg} "
            f"--phase-id {phase_arg} --family-id {family_arg} "
            f"--read-receipt-id {receipt_arg} "
            f"--td-id {shlex.quote(td_id)} "
            "--resolution-kind '<artifact|git_commit|orchestration_event|raw_seed_paragraph|session>' "
            "--resolution-ref '<ref>'"
        )
    append_exempt_command = ""
    if path_claim_seen:
        append_exempt_command = (
            "./repo-python tools/meta/factory/work_ledger.py "
            f"session-finalize --session-id {session_arg} --action codex-turn-end "
            f"--read-receipt-id {receipt_arg} "
            "--append-exempt-reason '<commit-or-projection-closeout>' "
            "--append-exempt-ref '<commit-or-receipt-ref>'"
        )
        for td_id in td_ids[:3]:
            append_exempt_command += f" --append-exempt-td-id {shlex.quote(td_id)}"
        for work_item_id in work_item_ids[:3]:
            append_exempt_command += f" --append-exempt-work-item-id {shlex.quote(work_item_id)}"
    bare_finalize_command = (
        "./repo-python tools/meta/factory/work_ledger.py "
        f"session-finalize --session-id {session_arg} --action codex-turn-end"
    )

    recommended_sequence: List[str] = []
    if progress_commands or close_commands:
        recommended_sequence.extend(progress_commands)
        recommended_sequence.extend(close_commands)
        recommended_sequence.append(bare_finalize_command)
        if append_exempt_command:
            alternative_commands.append(
                {
                    "role": "commit_or_projection_closeout",
                    "command": append_exempt_command,
                    "use_when": (
                        "The touched path work is fully evidenced by a scoped commit, "
                        "Task Ledger receipt, or generated projection settlement instead "
                        "of a Work Ledger progress/close append."
                    ),
                    "finalizes_session": True,
                    "do_not_follow_with_bare_finalize": True,
                }
            )
    elif append_exempt_command:
        recommended_sequence.append(append_exempt_command)
    else:
        recommended_sequence.append(bare_finalize_command)

    command_roles: List[Dict[str, Any]] = []
    if progress_commands:
        command_roles.append(
            {
                "role": "work_item_progress_before_finalize",
                "commands": progress_commands,
                "finalizes_session": False,
            }
        )
    if close_commands:
        command_roles.append(
            {
                "role": "work_ledger_close_before_finalize",
                "commands": close_commands,
                "finalizes_session": False,
            }
        )
    if append_exempt_command:
        command_roles.append(
            {
                "role": "append_exempt_finalize_for_path_or_projection_closeout",
                "commands": [append_exempt_command],
                "finalizes_session": True,
                "do_not_follow_with_bare_finalize": True,
            }
        )
    command_roles.append(
        {
            "role": "bare_finalize_after_append_exists",
            "commands": [bare_finalize_command],
            "finalizes_session": True,
            "only_after": "session_had_ledger_append=true or append_exempt=true",
            "will_block_if": "touched_work=true and no Work Ledger append or append-exempt closeout exists",
        }
    )
    return {
        "schema": "work_ledger_closeout_plan_v1",
        "ordering_rule": (
            "Choose one closeout path. If progress/close writes a Work Ledger append, "
            "finish with bare session-finalize. If the durable evidence is commit-only "
            "or projection-only, use the append-exempt session-finalize command as the "
            "finalizer and do not run bare session-finalize afterward."
        ),
        "read_receipt_id": read_receipt_id or "<live_read_receipt_id>",
        "recommended_sequence": recommended_sequence,
        "command_roles": command_roles,
        "alternative_commands": alternative_commands,
        "legacy_flat_commands_policy": (
            "closeout_commands is a compatibility field containing only the recommended "
            "sequence for the detected claims; use closeout_plan for role and ordering details."
        ),
    }


def _claim_closeout_commands(
    session_id: str,
    claims: List[Dict[str, Any]],
    *,
    read_receipt_id: str = "",
    actor: str = "",
    phase_id: str = "",
    family_id: str = "",
) -> List[str]:
    return list(
        _claim_closeout_plan(
            session_id,
            claims,
            read_receipt_id=read_receipt_id,
            actor=actor,
            phase_id=phase_id,
            family_id=family_id,
        )["recommended_sequence"]
    )


def _path_scope_overlaps(left: str, right: str) -> bool:
    left_parts = tuple(part for part in str(left or "").split("/") if part)
    right_parts = tuple(part for part in str(right or "").split("/") if part)
    if not left_parts or not right_parts:
        return False
    if left_parts == right_parts:
        return True
    if len(left_parts) < len(right_parts):
        return right_parts[: len(left_parts)] == left_parts
    return left_parts[: len(right_parts)] == right_parts


def _preflight_requested_paths(paths: List[str]) -> List[str]:
    normalized: List[str] = []
    for path in paths:
        token = _normalize_codex_repo_path(path, REPO_ROOT)
        if token and token not in normalized:
            normalized.append(token)
    return normalized


def _preflight_write_profiles(profile_names: List[str]) -> List[Dict[str, Any]]:
    profiles: List[Dict[str, Any]] = []
    for name in profile_names:
        token = str(name or "").strip()
        if not token:
            continue
        if token not in WRITE_PROFILE_PATHS:
            raise ValueError(f"unknown write profile: {token}")
        paths = list(WRITE_PROFILE_PATHS[token])
        profiles.append(
            {
                "profile": token,
                "paths": paths,
                "path_count": len(paths),
            }
        )
    return profiles


def _preflight_claim_paths(paths: List[str], profiles: List[Dict[str, Any]]) -> List[str]:
    claimed_paths: List[str] = []
    for path in paths:
        token = _normalize_codex_repo_path(path, REPO_ROOT)
        if token and token not in claimed_paths:
            claimed_paths.append(token)
    for profile in profiles:
        for path in profile.get("paths") or []:
            token = _normalize_codex_repo_path(path, REPO_ROOT)
            if token and token not in claimed_paths:
                claimed_paths.append(token)
    return claimed_paths


def _observed_path_overlaps(
    *,
    requested_paths: List[str],
    codex_import: Dict[str, Any] | None,
    limit: int = 12,
) -> List[Dict[str, Any]]:
    if not requested_paths or not isinstance(codex_import, dict):
        return []
    rows: List[Dict[str, Any]] = []
    imported_rows = codex_import.get("candidates") or codex_import.get("observations") or []
    for row in imported_rows:
        if not isinstance(row, dict):
            continue
        metadata = row.get("external_metadata") if isinstance(row.get("external_metadata"), dict) else {}
        activity = row.get("rollout_activity") or metadata.get("rollout_activity")
        if not isinstance(activity, dict):
            continue
        mutation_paths = [
            path
            for path in activity.get("recent_mutation_paths") or []
            if isinstance(path, str)
        ]
        referenced_paths = [
            path
            for path in activity.get("recent_referenced_paths") or []
            if isinstance(path, str)
        ]
        for requested in requested_paths:
            mutation_overlaps = [
                path for path in mutation_paths if _path_scope_overlaps(requested, path)
            ]
            reference_overlaps = [
                path
                for path in referenced_paths
                if _path_scope_overlaps(requested, path) and path not in mutation_overlaps
            ]
            if not mutation_overlaps and not reference_overlaps:
                continue
            overlap_row = {
                "requested_path": requested,
                "session_id": row.get("session_id"),
                "updated_at": row.get("updated_at") or row.get("last_activity_at"),
                "mutation_paths": mutation_overlaps[:8],
                "referenced_paths": reference_overlaps[:8],
                "recent_commands": list(activity.get("recent_commands") or [])[:3],
            }
            overlap_row.update(_session_title_handle_fields(row))
            rows.append(overlap_row)
            if len(rows) >= limit:
                return rows
    return rows


def _observed_shared_worktree_git_risks(
    *,
    codex_import: Dict[str, Any] | None,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    if not isinstance(codex_import, dict):
        return []
    rows: List[Dict[str, Any]] = []
    imported_rows = codex_import.get("candidates") or codex_import.get("observations") or []
    for row in imported_rows:
        if not isinstance(row, dict):
            continue
        metadata = row.get("external_metadata") if isinstance(row.get("external_metadata"), dict) else {}
        activity = row.get("rollout_activity") or metadata.get("rollout_activity")
        if not isinstance(activity, dict):
            continue
        for command in activity.get("recent_commands") or []:
            risks = shared_worktree_guard.detect_git_risks_in_text(str(command or ""))
            if not risks:
                continue
            for risk in risks:
                risk_row = dict(risk)
                risk_row.update(
                    {
                        "session_id": row.get("session_id"),
                        "updated_at": row.get("updated_at") or row.get("last_activity_at"),
                    }
                )
                risk_row.update(_session_title_handle_fields(row))
                rows.append(risk_row)
                if len(rows) >= limit:
                    return rows
            break
    return rows


def _compact_preflight_claim(result: Dict[str, Any]) -> Dict[str, Any]:
    claim = result.get("claim") if isinstance(result.get("claim"), dict) else {}
    collisions = result.get("collisions") if isinstance(result.get("collisions"), list) else []
    return {
        "status": result.get("status"),
        "scope_kind": claim.get("scope_kind") or result.get("scope_kind"),
        "scope_id": claim.get("scope_id") or result.get("scope_id"),
        "claim_id": claim.get("claim_id"),
        "td_id": claim.get("td_id") or result.get("td_id") or "",
        "path": claim.get("path") or result.get("path") or "",
        "work_item_id": claim.get("work_item_id") or result.get("work_item_id") or "",
        "leased_until": claim.get("leased_until"),
        "collision_count": len(collisions),
        "collision_sessions": [
            {
                "session_id": row.get("session_id"),
                "actor": row.get("actor"),
                "scope_kind": (row.get("claim") or {}).get("scope_kind")
                if isinstance(row.get("claim"), dict)
                else None,
                "scope_id": (row.get("claim") or {}).get("scope_id")
                if isinstance(row.get("claim"), dict)
                else None,
            }
            for row in collisions
            if isinstance(row, dict)
        ],
    }


def _compact_preflight_overview(overview: Dict[str, Any]) -> Dict[str, Any]:
    contention = overview.get("contention") if isinstance(overview.get("contention"), dict) else {}
    counts = overview.get("counts") if isinstance(overview.get("counts"), dict) else {}
    count_keys = (
        "sessions_total",
        "effective_active_sessions",
        "orphaned_active_sessions",
        "stale_sessions",
        "active_claims",
        "claim_collisions",
        "unclaimed_touched_sessions",
    )
    return {
        "risk_level": contention.get("risk_level"),
        "signals": list(contention.get("signals") or []),
        "counts": {key: counts.get(key, 0) for key in count_keys},
        "heartbeat_participation": dict(overview.get("heartbeat_participation") or {}),
        "recommended_actions": list(overview.get("recommended_actions") or []),
    }


def _compact_observed_path_overlap(row: Mapping[str, Any]) -> Dict[str, Any]:
    mutation_paths = [path for path in list(row.get("mutation_paths") or []) if isinstance(path, str)]
    referenced_paths = [path for path in list(row.get("referenced_paths") or []) if isinstance(path, str)]
    recent_commands = [
        _compact_handle_preview(_compact_codex_command(command), limit=120)
        for command in list(row.get("recent_commands") or [])
        if str(command or "").strip()
    ]
    compact: Dict[str, Any] = {
        "requested_path": row.get("requested_path"),
        "session_id": row.get("session_id"),
        "updated_at": row.get("updated_at"),
        "mutation_paths": mutation_paths[:4],
        "mutation_path_count": len(mutation_paths),
        "referenced_paths": referenced_paths[:4],
        "referenced_path_count": len(referenced_paths),
        "recent_commands": recent_commands[:1],
        "recent_command_count": len(recent_commands),
        "title_bytes": row.get("title_bytes"),
        "title_hash": row.get("title_hash"),
        "title_kind": row.get("title_kind"),
        "title_full_omitted": row.get("title_full_omitted"),
    }
    if row.get("title_full_omitted"):
        compact["title_preview"] = row.get("title_preview")
        compact["title_ref"] = row.get("title_ref")
        compact["title_drilldown"] = row.get("title_drilldown")
        if isinstance(row.get("omission_receipt"), Mapping):
            receipt = row.get("omission_receipt") or {}
            compact["omission_receipt"] = {
                key: receipt.get(key)
                for key in ("omitted", "drilldown", "source_ref")
                if receipt.get(key) not in (None, "", [], {})
            }
    else:
        compact["title_preview"] = row.get("title_preview")
    return {
        key: value
        for key, value in compact.items()
        if value not in (None, "", [], {})
    }


def _compact_preflight_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    codex_import = payload.get("codex_import")
    import_summary = None
    if isinstance(codex_import, dict):
        import_summary = {
            "candidate_count": codex_import.get("candidate_count", 0),
            "imported_count": codex_import.get("imported_count", 0),
            "since_minutes": codex_import.get("since_minutes"),
            "db_path": codex_import.get("db_path"),
        }
    claude_import = payload.get("claude_ide_import")
    claude_summary = None
    if isinstance(claude_import, dict):
        claude_summary = {
            "candidate_count": claude_import.get("candidate_count", 0),
            "imported_count": claude_import.get("imported_count", 0),
            "since_minutes": claude_import.get("since_minutes"),
            "todo_counts": claude_import.get("todo_counts") or {},
        }
    claims = payload.get("claims") if isinstance(payload.get("claims"), list) else []
    claim_rows = [_compact_preflight_claim(row) for row in claims if isinstance(row, dict)]
    status_counts = Counter(str(row.get("status") or "unknown") for row in claim_rows)
    payload_claim_summary = (
        payload.get("claim_summary") if isinstance(payload.get("claim_summary"), Mapping) else None
    )
    overview = payload.get("overview") if isinstance(payload.get("overview"), dict) else {}
    overlap_rows = [
        row for row in list(payload.get("observed_path_overlaps") or []) if isinstance(row, Mapping)
    ]
    compact_overlap_rows = [_compact_observed_path_overlap(row) for row in overlap_rows[:8]]
    overlap_summary = {
        "returned": len(compact_overlap_rows),
        "total": len(overlap_rows),
        "omitted": max(0, len(overlap_rows) - len(compact_overlap_rows)),
        "full_payload_drilldown": (
            "./repo-python tools/meta/factory/work_ledger.py session-preflight "
            "--full <same args>"
        ),
    }
    return {
        "schema": payload.get("schema"),
        "mode": "compact",
        "status": payload.get("status"),
        "session_id": payload.get("session_id"),
        "actor": payload.get("actor"),
        "phase_id": payload.get("phase_id"),
        "family_id": payload.get("family_id"),
        "read_receipt_id": payload.get("read_receipt_id"),
        "codex_import_summary": import_summary,
        "claude_ide_import_summary": claude_summary,
        "claim_summary": dict(payload_claim_summary)
        if payload_claim_summary
        else {
            "requested": len(claim_rows),
            "claimed": status_counts.get("claimed", 0),
            "claimed_with_collision": status_counts.get("claimed_with_collision", 0),
            "refused": status_counts.get("refused", 0),
        },
        "claims": claim_rows,
        "write_profiles": payload.get("write_profiles") or [],
        "work_creation_classification": payload.get("work_creation_classification") or {},
        "work_admission": payload.get("work_admission") or {},
        "observed_path_overlaps": compact_overlap_rows,
        "observed_path_overlap_summary": overlap_summary,
        "shared_worktree_git_risks": payload.get("shared_worktree_git_risks") or [],
        "overview_summary": _compact_preflight_overview(overview),
        "heartbeat_participation_contract": payload.get("heartbeat_participation_contract") or {},
        "closeout_rule": payload.get("closeout_rule") or {},
        "closeout_plan": payload.get("closeout_plan") or {},
        "closeout_commands": payload.get("closeout_commands") or [],
        "full_payload_hint": "rerun with --full to include bootstrap, imported candidates, and full cohort lists",
    }


def _active_claim_collisions_for_paths(paths: List[str], *, session_id: str | None = None) -> List[Dict[str, Any]]:
    status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    return work_ledger_runtime.active_claim_collisions_for_paths(
        REPO_ROOT,
        paths,
        status=status,
        session_id=session_id,
    )


def cmd_mutation_check(args: argparse.Namespace) -> int:
    write_profiles = _preflight_write_profiles(list(getattr(args, "write_profile", []) or []))
    paths = _preflight_claim_paths(list(args.path or []), write_profiles)
    collisions = _active_claim_collisions_for_paths(paths, session_id=args.session_id)
    status = "blocked" if collisions and args.require_exclusive else ("watch" if collisions else "clear")
    payload = {
        "schema": "work_ledger_mutation_check_v1",
        "status": status,
        "require_exclusive": bool(args.require_exclusive),
        "write_profiles": write_profiles,
        "paths": paths,
        "collision_count": len(collisions),
        "collisions": collisions,
        "recommended_actions": [
            "Run session-preflight with the same --path/--write-profile and claim the work before mutation.",
        ] if status == "clear" and not args.session_id else [],
    }
    _print(payload)
    return 2 if status == "blocked" else 0


def cmd_helper_lease_admission(args: argparse.Namespace) -> int:
    decision = work_admission.build_helper_lease_admission_decision(
        REPO_ROOT,
        lease_kind=args.lease_kind,
        policy=getattr(args, "host_pressure_policy", None) or "auto",
        request_id=getattr(args, "request_id", None),
        requested_by=getattr(args, "requested_by", None),
        owner_status=getattr(args, "owner_status", None),
        current_lease_count=getattr(args, "current_lease_count", None),
    )
    _print(decision)
    return work_admission.ADMISSION_TEMPFAIL if not bool(decision.get("allow", True)) else 0


def _current_host_pressure_packet(*, workload_class: str = "mixed_realistic") -> Dict[str, Any]:
    try:
        from system.lib.agent_observability import AgentTraceStore
        from system.lib.host_pressure import build_progress_pressure_packet_from_store

        store = AgentTraceStore(REPO_ROOT, max_history=500)
        return build_progress_pressure_packet_from_store(
            store,
            REPO_ROOT,
            event_limit=500,
            include_processes=False,
            requested_workload_class=workload_class,
        )
    except Exception as exc:  # pragma: no cover - host adapters must degrade.
        return {
            "summary": {
                "bottleneck_class": "unknown",
                "pressure_index": 0,
                "progress_per_pressure": 0,
            },
            "source_error": {
                "error_class": type(exc).__name__,
                "message": str(exc),
            },
        }


def cmd_resident_pressure_relief(args: argparse.Namespace) -> int:
    before_packet = _current_host_pressure_packet()
    release_request = work_admission.build_helper_owner_release_request(
        process_kind=args.process_kind,
        owner_status=args.owner_status,
        rss_mb_total=args.rss_mb_total,
        target_owner=args.target_owner,
        pressure_mode=args.pressure_mode,
    )
    release_result = work_admission.build_owner_release_result_receipt(
        release_request=release_request,
        result=args.owner_release_result,
        result_note=args.result_note,
    )
    downshift = None
    if args.background_loop_kind:
        downshift_result = "applied" if args.apply_background_downshift else args.background_loop_result
        downshift = work_admission.build_background_loop_downshift_receipt(
            loop_kind=args.background_loop_kind,
            owner_surface=args.owner_surface or "unknown",
            pressure_mode=args.pressure_mode,
            result=downshift_result,
            duration_s=args.duration_s,
            effective_interval_s=args.effective_interval_s,
        )
        if args.apply_background_downshift:
            BACKGROUND_DOWNSHIFT_STATE.parent.mkdir(parents=True, exist_ok=True)
            BACKGROUND_DOWNSHIFT_STATE.write_text(
                json.dumps(downshift, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
    window = work_admission.build_resident_pressure_relief_window(
        before_packet=before_packet,
        owner_release_results=[release_result],
        background_downshifts=[downshift] if downshift else [],
        blocked_work_starts=args.blocked_work_starts,
        blocked_helper_leases=args.blocked_helper_leases,
        workload_mix_changed=bool(args.workload_mix_changed),
    )
    payload = {
        "schema": "resident_pressure_relief_command_v1",
        "status": window.get("verdict"),
        "pressure_mode": args.pressure_mode,
        "helper_owner_release_request": release_request,
        "owner_release_result": release_result,
        "background_loop_downshift": downshift,
        "background_downshift_state_path": str(BACKGROUND_DOWNSHIFT_STATE.relative_to(REPO_ROOT))
        if args.apply_background_downshift and downshift
        else None,
        "resident_pressure_relief_window": window,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }
    _print(payload)
    return 0 if window.get("verdict") != "no_resident_actuator" else work_admission.ADMISSION_TEMPFAIL


def cmd_session_yield_request(args: argparse.Namespace) -> int:
    request_id = getattr(args, "request_id", None) or _mint_session_yield_request_id(
        args.target_session_id,
        args.requested_action,
    )
    receipt = work_admission.build_session_yield_request_receipt(
        target_id=args.target_session_id,
        request_id=request_id,
        target_class=args.target_class,
        requested_action=args.requested_action,
        owner_status=args.owner_status,
        pressure_mode=args.pressure_mode,
        result=args.result,
        helper_rss_mb=args.helper_rss_mb,
        recent_progress_units=args.recent_progress_units,
        result_note=args.result_note,
    )
    rank = work_admission.build_session_pressure_rank(
        [
            {
                "session_id": args.target_session_id,
                "owner_status": args.owner_status,
                "helper_rss_mb": args.helper_rss_mb,
                "recent_progress_units": args.recent_progress_units,
                "idle_age_s": args.idle_age_s,
                "last_heartbeat_age_s": args.last_heartbeat_age_s,
                "active_claim_count": args.active_claim_count,
                "operator_priority_hint": args.operator_priority_hint,
            }
        ],
        limit=1,
    )
    payload = {
        "schema": "session_yield_request_command_v1",
        "status": receipt.get("result"),
        "written": not bool(args.dry_run),
        "request_id": request_id,
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "session_yield_request": receipt,
        "session_pressure_rank": rank,
        "safety": {
            "no_process_signal_sent": True,
            "no_unknown_owner_killed": True,
            "no_active_session_terminated": True,
        },
    }
    if not args.dry_run:
        _append_jsonl(SESSION_YIELD_REQUESTS, payload)
    _print(payload)
    return 0 if receipt.get("result") != "owner_unresolved" else work_admission.ADMISSION_TEMPFAIL


def cmd_session_yield_result(args: argparse.Namespace) -> int:
    yield_request = _find_session_yield_request(
        request_id=getattr(args, "request_id", None),
        target_session_id=getattr(args, "target_session_id", None),
    )
    if not yield_request:
        payload = {
            "schema": "owner_yield_result_command_v1",
            "status": "request_not_found",
            "written": False,
            "request_id": getattr(args, "request_id", None),
            "target_session_id": getattr(args, "target_session_id", None),
            "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
            "result_log_path": str(SESSION_YIELD_RESULTS.relative_to(REPO_ROOT)),
            "safety": {
                "no_process_signal_sent": True,
                "no_unknown_owner_killed": True,
                "no_active_session_terminated": True,
            },
        }
        _print(payload)
        return work_admission.ADMISSION_TEMPFAIL
    result = work_admission.build_owner_yield_result_receipt(
        yield_request=yield_request,
        result=args.result,
        applied_action=args.applied_action,
        delivery=args.delivery,
        result_note=args.result_note,
    )
    payload = {
        "schema": "owner_yield_result_command_v1",
        "status": result.get("status"),
        "written": not bool(args.dry_run),
        "request_id": result.get("request_id"),
        "request_log_path": str(SESSION_YIELD_REQUESTS.relative_to(REPO_ROOT)),
        "result_log_path": str(SESSION_YIELD_RESULTS.relative_to(REPO_ROOT)),
        "matched_request": yield_request,
        "owner_yield_result": result,
        "safety": result.get("safety"),
    }
    if not args.dry_run:
        _append_jsonl(SESSION_YIELD_RESULTS, payload)
    _print(payload)
    return 0 if result.get("result") != "owner_unresolved" else work_admission.ADMISSION_TEMPFAIL


def cmd_session_yield_control(args: argparse.Namespace) -> int:
    background_loop_downshift: dict[str, Any] | None = None
    if BACKGROUND_DOWNSHIFT_STATE.exists():
        try:
            decoded = json.loads(BACKGROUND_DOWNSHIFT_STATE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            decoded = None
        if isinstance(decoded, dict):
            background_loop_downshift = decoded
    payload = work_admission.build_session_yield_control_surface(
        request_events=_read_jsonl_tail(SESSION_YIELD_REQUESTS, limit=args.limit),
        result_events=_read_jsonl_tail(SESSION_YIELD_RESULTS, limit=args.limit),
        background_loop_downshift=background_loop_downshift,
        limit=args.limit,
    )
    _print(payload)
    return 0


def cmd_session_preflight(args: argparse.Namespace) -> int:
    session_id = args.session_id or _mint_preflight_session_id(args.actor, args.session_slug)
    write_profiles = _preflight_write_profiles(list(getattr(args, "write_profile", []) or []))
    claim_paths = _preflight_claim_paths(list(args.path or []), write_profiles)
    work_creation_classification = work_admission.classify_work_creation_request(
        paths=claim_paths,
        write_profiles=write_profiles,
        requested_class=getattr(args, "work_admission_class", None),
    )
    work_admission_decision = work_admission.build_work_admission_decision(
        REPO_ROOT,
        work_class=str(work_creation_classification.get("work_class") or work_admission.CHEAP_READ),
        policy=getattr(args, "host_pressure_policy", None) or "auto",
        request_id=session_id,
    )
    if not bool(work_admission_decision.get("allow", True)):
        blocked_payload = {
            "schema": "work_ledger_session_preflight_v1",
            "mode": "full",
            "status": "blocked_by_work_admission",
            "session_id": session_id,
            "actor": args.actor,
            "phase_id": args.phase_id,
            "family_id": args.family_id,
            "read_receipt_id": None,
            "codex_import": None,
            "claude_ide_import": None,
            "bootstrap": {},
            "write_profiles": write_profiles,
            "work_creation_classification": work_creation_classification,
            "work_admission": work_admission_decision,
            "claim_summary": {
                "requested": len(claim_paths) + len(args.td_id or []),
                "claimed": 0,
                "claimed_with_collision": 0,
                "refused": len(claim_paths) + len(args.td_id or []),
            },
            "claims": [],
            "observed_path_overlaps": [],
            "shared_worktree_git_risks": [],
            "overview": {},
            "closeout_rule": {
                "schema": "work_ledger_preflight_closeout_rule_v1",
                "status": "not_started_blocked_by_work_admission",
                "rule": "No Work Ledger claims were written because pressure admission refused this work start.",
            },
            "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
            "closeout_plan": {
                "schema": "work_ledger_closeout_plan_v1",
                "recommended_sequence": [],
            },
            "closeout_commands": [],
        }
        if getattr(args, "full", False):
            _print(blocked_payload)
        else:
            _print(_compact_preflight_payload(blocked_payload))
        return work_admission.ADMISSION_TEMPFAIL
    codex_import = None
    if not getattr(args, "skip_import_codex", False):
        db_path = Path(args.db_path).expanduser() if args.db_path else CODEX_STATE_DB
        codex_import = _import_codex_sessions(
            db_path=db_path,
            actor=args.actor,
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.import_limit,
            include_all_cwds=bool(args.include_all_cwds),
            dry_run=False,
        )
    claude_import = None
    if not getattr(args, "skip_import_claude", False):
        claude_import = _import_claude_ide_sessions(
            phase_id=args.phase_id,
            family_id=args.family_id,
            since_minutes=args.since_minutes,
            limit=args.import_limit,
            include_all_workspaces=bool(args.include_all_workspaces),
            dry_run=False,
        )
    claim_scopes: List[Dict[str, str]] = [
        {"scope_kind": work_ledger_runtime.CLAIM_SCOPE_THREAD, "scope_id": str(td_id)}
        for td_id in (args.td_id or [])
    ]
    claim_scopes.extend(
        {
            "scope_kind": work_ledger_runtime.CLAIM_SCOPE_PATH,
            "scope_id": str(path),
        }
        for path in claim_paths
    )
    bootstrap = work_ledger_runtime.bootstrap_session(
        REPO_ROOT,
        session_id=session_id,
        actor=args.actor,
        phase_id=args.phase_id,
        family_id=args.family_id,
        limit=args.bootstrap_limit,
        claim_scopes=claim_scopes,
        claim_lease_minutes=args.lease_minutes,
        claim_note=args.note,
        require_exclusive_claims=bool(args.require_exclusive),
    )
    claims = list(bootstrap.get("claims") or [])
    observed_path_overlaps = _observed_path_overlaps(
        requested_paths=_preflight_requested_paths(claim_paths),
        codex_import=codex_import,
    )
    shared_worktree_git_risks = _observed_shared_worktree_git_risks(codex_import=codex_import)
    cached_overview = (
        bootstrap.get("cohort_overview")
        if isinstance(bootstrap.get("cohort_overview"), Mapping)
        else None
    )
    if (
        int(args.overview_limit or 0) == work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT
        and cached_overview is not None
    ):
        overview = dict(cached_overview)
    else:
        status_after_claims = work_ledger_runtime.load_runtime_status(REPO_ROOT, rebuild=False)
        overview = work_ledger_runtime.build_session_cohort_overview(
            status_after_claims,
            limit=args.overview_limit,
        )
    closeout_plan = _claim_closeout_plan(
        session_id,
        claims,
        read_receipt_id=str(bootstrap.get("read_receipt_id") or ""),
        actor=args.actor,
        phase_id=str(bootstrap.get("phase_id") or args.phase_id or ""),
        family_id=str(bootstrap.get("family_id") or args.family_id or ""),
    )
    payload = {
        "schema": "work_ledger_session_preflight_v1",
        "mode": "full",
        "session_id": session_id,
        "actor": args.actor,
        "phase_id": bootstrap.get("phase_id"),
        "family_id": bootstrap.get("family_id"),
        "read_receipt_id": bootstrap.get("read_receipt_id"),
        "codex_import": codex_import,
        "claude_ide_import": claude_import,
        "bootstrap": bootstrap,
        "write_profiles": write_profiles,
        "work_creation_classification": work_creation_classification,
        "work_admission": work_admission_decision,
        "claims": claims,
        "observed_path_overlaps": observed_path_overlaps,
        "shared_worktree_git_risks": shared_worktree_git_risks,
        "overview": overview,
        "closeout_rule": {
            "schema": "work_ledger_preflight_closeout_rule_v1",
            "status": "append_or_append_exempt_before_finalize",
            "read_receipt_id": bootstrap.get("read_receipt_id"),
            "rule": (
                "If this session touched claimed work, write Work Ledger progress/close "
                "evidence or record an append-exempt closeout before bare session-finalize. "
                "The finalizer blocks touched/no-append sessions unless append-exempt is explicit."
            ),
        },
        "heartbeat_participation_contract": _heartbeat_participation_contract(session_id),
        "closeout_plan": closeout_plan,
        "closeout_commands": closeout_plan["recommended_sequence"],
    }
    if getattr(args, "full", False):
        return _print(payload)
    return _print(_compact_preflight_payload(payload))


def cmd_session_claim(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.claim_work_thread(
        REPO_ROOT,
        session_id=args.session_id,
        td_id=args.td_id,
        lease_minutes=args.lease_minutes,
        note=args.note,
        require_exclusive=bool(getattr(args, "require_exclusive", False)),
    )
    return _print(payload)


def cmd_session_claim_path(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.claim_work_path(
        REPO_ROOT,
        session_id=args.session_id,
        path=args.path,
        lease_minutes=args.lease_minutes,
        note=args.note,
        require_exclusive=bool(getattr(args, "require_exclusive", False)),
    )
    return _print(payload)


def cmd_session_release_claim(args: argparse.Namespace) -> int:
    payload = work_ledger_runtime.release_claim(
        REPO_ROOT,
        session_id=args.session_id,
        claim_id=args.claim_id,
        td_id=args.td_id,
        path=args.path,
        reason=args.reason,
    )
    return _print(payload)


def _dirty_paths_from_git_status(repo_root: Path) -> tuple[List[str], str]:
    try:
        completed = subprocess.run(
            [
                "git",
                "-C",
                str(repo_root),
                "status",
                "--porcelain=v1",
                "-z",
                "--untracked-files=all",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
    except OSError as exc:
        return [], f"git_status_unavailable:{type(exc).__name__}"
    if completed.returncode != 0:
        stderr = " ".join((completed.stderr or "").split())
        return [], f"git_status_failed:{stderr or completed.returncode}"
    paths: List[str] = []
    entries = completed.stdout.split("\0")
    index = 0
    while index < len(entries):
        entry = entries[index]
        index += 1
        if not entry:
            continue
        status = entry[:2]
        path = entry[3:] if len(entry) > 3 else ""
        if path:
            paths.append(path)
        if status[:1] in {"R", "C"} or status[1:2] in {"R", "C"}:
            # Porcelain -z rename/copy entries carry the old path in the next field.
            index += 1
    return paths, "git_status_porcelain_v1_z"


def cmd_session_sweep(args: argparse.Namespace) -> int:
    import datetime as _dt

    if bool(getattr(args, "dirty_tree_pressure", False)) and not bool(args.dry_run):
        print(
            json.dumps(
                {
                    "schema": "work_ledger_sweep_report_v1",
                    "status": "blocked",
                    "reason": "DirtyTreePressureRequiresDryRun",
                    "dry_run": False,
                    "next_safe_command": (
                        "./repo-python tools/meta/factory/work_ledger.py "
                        "session-sweep --dry-run --dirty-tree-pressure"
                    ),
                    "mutation_policy": (
                        "dirty-tree pressure is an orientation readback; run session-sweep "
                        "without --dirty-tree-pressure for the explicit live sweep lane"
                    ),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 2

    hours = float(args.orphan_after_hours or 0)
    orphan_after = (
        _dt.timedelta(hours=hours)
        if hours > 0
        else work_ledger_runtime.ACTIVE_SESSION_ORPHAN_SWEEP_AFTER
    )
    expiry = work_ledger_runtime.sweep_expired_claims(
        REPO_ROOT,
        dry_run=bool(args.dry_run),
    )
    orphans = work_ledger_runtime.sweep_orphan_sessions(
        REPO_ROOT,
        orphan_sweep_after=orphan_after,
        dry_run=bool(args.dry_run),
    )
    dirty_tree_pressure = None
    if bool(getattr(args, "dirty_tree_pressure", False)):
        supplied_dirty_paths = list(getattr(args, "dirty_path", None) or [])
        if supplied_dirty_paths:
            dirty_paths = supplied_dirty_paths
            dirty_scan_status = "provided"
        else:
            dirty_paths, dirty_scan_status = _dirty_paths_from_git_status(REPO_ROOT)
        dirty_tree_pressure = work_ledger_runtime.build_dirty_tree_bankruptcy_pressure(
            REPO_ROOT,
            dirty_paths=dirty_paths,
            dirty_scan_status=dirty_scan_status,
            bankruptcy_authorized=bool(getattr(args, "bankruptcy_authorized", False)),
            orphan_sweep_after=orphan_after,
        )
        dirty_tree_pressure["sweep_dry_run"] = bool(args.dry_run)
    duplicate_claim_dedupe = None
    if bool(getattr(args, "dedupe_duplicate_claims", False)):
        duplicate_claim_dedupe = work_ledger_runtime.dedupe_duplicate_same_session_claims(
            REPO_ROOT,
            dry_run=bool(args.dry_run),
        )
    dirty_tree_pressure_alias = (
        work_ledger_runtime.dirty_tree_pressure_alias(dirty_tree_pressure)
        if dirty_tree_pressure is not None
        else None
    )
    return _print(
        {
            "schema": "work_ledger_sweep_report_v1",
            "dry_run": bool(args.dry_run),
            "orphan_sweep_after_hours": orphan_after.total_seconds() / 3600.0,
            "claim_expiry": expiry,
            "orphan_sessions": orphans,
            **(
                {"dirty_tree_bankruptcy_pressure": dirty_tree_pressure}
                if dirty_tree_pressure is not None
                else {}
            ),
            **(
                {"dirty_tree_pressure": dirty_tree_pressure_alias}
                if dirty_tree_pressure_alias is not None
                else {}
            ),
            **(
                {"duplicate_claim_dedupe": duplicate_claim_dedupe}
                if duplicate_claim_dedupe is not None
                else {}
            ),
        }
    )


def cmd_append_open(args: argparse.Namespace) -> int:
    _require_receipt(args)
    result = work_ledger.open_thread(
        REPO_ROOT,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        title=args.title,
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[str(result["event"]["td_id"])],
        event_ids=[str(result["event"]["event_id"])],
    )
    td_id = str(result["event"]["td_id"])
    try:
        result["runtime_claim"] = work_ledger_runtime.claim_work_thread(
            REPO_ROOT,
            session_id=args.actor_session_id,
            td_id=td_id,
            note="append-open auto-claim for same-session follow-up mutation",
        )
    except Exception as exc:
        result["runtime_claim"] = {
            "schema": "work_ledger_append_open_runtime_claim_v1",
            "status": "claim_failed",
            "td_id": td_id,
            "session_id": args.actor_session_id,
            "reason": str(exc),
            "repair_route": "Run session-claim --td-id for this actor_session_id, then retry close/supersede/reopen.",
        }
    return _print(result)


def cmd_progress(args: argparse.Namespace) -> int:
    try:
        _require_receipt(args)
    except ValueError as exc:
        _read_receipt_error_exit(
            command="progress",
            operation="progress_note",
            args=args,
            error=exc,
        )
    target_id = str(args.td_id or "").strip()
    if not work_ledger.TD_ID_RE.fullmatch(target_id):
        _verify_work_item_claim_or_bypass(
            args,
            operation="work_item_progress_note",
            allow_unclaimed_note=True,
        )
        metadata = _metadata_from_args(args)
        bridge = metadata.setdefault("task_ledger_work_item_bridge", {})
        if not isinstance(bridge, dict):
            raise SystemExit("metadata_json.task_ledger_work_item_bridge must be an object when present")
        bridge.update(
            {
                "receipt_mode": "task_ledger_work_item_progress",
                "task_ledger_work_item_id": target_id,
                "requested_work_ledger_td_id": target_id,
            }
        )
        result = work_ledger.open_thread(
            REPO_ROOT,
            actor=args.actor,
            actor_session_id=args.actor_session_id,
            phase_id=args.phase_id,
            family_id=args.family_id,
            title=args.title or f"Task Ledger progress: {target_id}",
            body=args.body,
            evidence_refs=args.evidence_ref,
            read_receipt_id=args.read_receipt_id,
            metadata=metadata,
        )
        work_ledger_runtime.mark_ledger_append(
            REPO_ROOT,
            read_receipt_id=args.read_receipt_id,
            session_id=args.actor_session_id,
            work_item_ids=[target_id],
            event_ids=[str(result["event"]["event_id"])],
        )
        generated_td_id = str(result["event"]["td_id"])
        try:
            result["runtime_claim"] = work_ledger_runtime.claim_work_thread(
                REPO_ROOT,
                session_id=args.actor_session_id,
                td_id=generated_td_id,
                note="work-item progress auto-claim for same-session close",
            )
        except Exception as exc:
            result["runtime_claim"] = {
                "schema": "work_ledger_work_item_progress_runtime_claim_v1",
                "status": "claim_failed",
                "td_id": generated_td_id,
                "work_item_id": target_id,
                "session_id": args.actor_session_id,
                "reason": str(exc),
                "repair_route": (
                    "Run session-claim --td-id for the generated Work Ledger td_id, "
                    "then retry close/supersede/reopen."
                ),
            }
        result["work_item_bridge"] = dict(bridge)
        result["generated_td_id"] = generated_td_id
        resolution_kind, resolution_ref, resolution_label = _progress_bridge_resolution_hint(args)
        result["next_claim_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py session-claim "
            f"--session-id {shlex.quote(str(args.actor_session_id))} "
            f"--td-id {shlex.quote(generated_td_id)} "
            "--lease-minutes 30 "
            "--note 'Claim generated Work Ledger receipt for closeout'"
        )
        result["next_close_command"] = (
            "./repo-python tools/meta/factory/work_ledger.py close "
            f"--actor {shlex.quote(str(args.actor))} "
            f"--actor-session-id {shlex.quote(str(args.actor_session_id))} "
            f"--phase-id {shlex.quote(str(args.phase_id))} "
            f"--family-id {shlex.quote(str(args.family_id))} "
            f"--read-receipt-id {shlex.quote(str(args.read_receipt_id))} "
            f"--td-id {shlex.quote(generated_td_id)} "
            f"--resolution-kind {shlex.quote(resolution_kind)} "
            f"--resolution-ref {shlex.quote(resolution_ref)} "
            f"--resolution-label {shlex.quote(resolution_label)}"
        )
        result["repair_route"] = (
            "Use next_claim_command if the generated td_id claim is missing, then "
            "use next_close_command with the generated Work Ledger td_id; do not "
            "pass the original Task Ledger WorkItem id to close."
        )
        return _print(result)

    _verify_thread_claim_or_bypass(args, operation="progress_note", allow_unclaimed_note=True)
    result = work_ledger.progress_thread(
        REPO_ROOT,
        td_id=target_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        body=args.body,
        title=args.title,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[target_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_close(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_close")
    result = work_ledger.close_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        resolution_episode=_resolution_episode_from_args(args),
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_supersede(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_supersede")
    result = work_ledger.supersede_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        title=args.title,
        resolution_episode=_resolution_episode_from_args(args),
        body=args.body,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id, str(result.get("successor_td_id") or "")],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_reopen(args: argparse.Namespace) -> int:
    _require_receipt(args)
    _verify_thread_claim_or_bypass(args, operation="todo_reopen")
    result = work_ledger.reopen_thread(
        REPO_ROOT,
        td_id=args.td_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        phase_id=args.phase_id,
        family_id=args.family_id,
        body=args.body,
        title=args.title,
        evidence_refs=args.evidence_ref,
        read_receipt_id=args.read_receipt_id,
        metadata=_metadata_from_args(args),
    )
    work_ledger_runtime.mark_ledger_append(
        REPO_ROOT,
        read_receipt_id=args.read_receipt_id,
        session_id=args.actor_session_id,
        td_ids=[args.td_id],
        event_ids=[str(result["event"]["event_id"])],
    )
    return _print(result)


def cmd_project(args: argparse.Namespace) -> int:
    if args.check:
        if args.all:
            return _print(work_ledger.check_project_all(REPO_ROOT))
        return _print(
            work_ledger.check_project_phase(
                REPO_ROOT,
                phase_id=args.phase_id,
                family_id=args.family_id,
            )
        )
    if args.all:
        return _print(work_ledger.project_all(REPO_ROOT))
    return _print(
        work_ledger.project_phase(
            REPO_ROOT,
            phase_id=args.phase_id,
            family_id=args.family_id,
        )
    )


def cmd_query(args: argparse.Namespace) -> int:
    if args.read_receipt_id:
        work_ledger_runtime.mark_ledger_query(
            REPO_ROOT,
            read_receipt_id=args.read_receipt_id,
            session_id=args.actor_session_id,
            td_id=args.td_id,
        )
    payload = work_ledger.query_recipe(
        REPO_ROOT,
        recipe=args.recipe,
        phase_id=args.phase_id,
        family_id=args.family_id,
        actor=args.actor,
        actor_session_id=args.actor_session_id,
        td_id=args.td_id,
        limit=args.limit,
    )
    return _print(payload)


def cmd_agent_seed_handoffs(args: argparse.Namespace) -> int:
    if args.live:
        _require_receipt(args)
    payload = agent_seed_handoffs.extract_agent_seed_handoffs(
        REPO_ROOT,
        family_id=args.family_id,
        since_date=args.since_date,
        limit=args.limit,
        include_imported=bool(args.include_imported),
    )
    opened: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    if args.live:
        for candidate in payload.get("candidates") or []:
            if not isinstance(candidate, Mapping):
                continue
            if candidate.get("imported"):
                skipped.append(
                    {
                        "candidate_id": candidate.get("candidate_id"),
                        "reason": "already_imported",
                        "existing_td_id": candidate.get("existing_td_id"),
                    }
                )
                continue
            result = work_ledger.open_thread(
                REPO_ROOT,
                actor=args.actor,
                actor_session_id=args.actor_session_id,
                phase_id=args.phase_id,
                family_id=args.family_id,
                title=str(candidate.get("title") or "Agent-seed handoff"),
                body=str(candidate.get("body") or ""),
                evidence_refs=list(candidate.get("evidence_refs") or []),
                read_receipt_id=args.read_receipt_id,
                metadata=dict(candidate.get("metadata") or {}),
            )
            opened.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "td_id": result["event"]["td_id"],
                    "event_id": result["event"]["event_id"],
                    "title": result["event"].get("title"),
                }
            )
        if opened:
            work_ledger_runtime.mark_ledger_append(
                REPO_ROOT,
                read_receipt_id=args.read_receipt_id,
                session_id=args.actor_session_id,
                td_ids=[str(row.get("td_id")) for row in opened if row.get("td_id")],
                event_ids=[str(row.get("event_id")) for row in opened if row.get("event_id")],
            )
        payload = {
            **payload,
            "live": True,
            "opened_count": len(opened),
            "opened": opened,
            "skipped": skipped,
        }
    else:
        payload = {**payload, "live": False}
    return _print(payload)


def _add_common_mutation_args(
    parser: argparse.ArgumentParser,
    *,
    require_td_id: bool = False,
    allow_unclaimed_note_arg: bool = False,
) -> None:
    parser.add_argument("--actor", default=None)
    parser.add_argument("--actor-session-id", default=None)
    parser.add_argument("--phase-id", default=None)
    parser.add_argument("--family-id", default=None)
    parser.add_argument("--read-receipt-id", required=True)
    parser.add_argument("--title", default=None)
    parser.add_argument("--body", default=None,
                        help="Inline body text. Mutually exclusive with --body-file and --body-stdin.")
    parser.add_argument("--body-file", default=None,
                        help="Read body from a UTF-8 file. Closeout bodies are governance evidence; "
                             "this avoids shell command-substitution corruption of inline text.")
    parser.add_argument("--body-stdin", action="store_true",
                        help="Read body from stdin (UTF-8). Mutually exclusive with --body and --body-file.")
    parser.add_argument("--evidence-ref", action="append", default=[])
    parser.add_argument("--metadata-json", default=None)
    if require_td_id:
        parser.add_argument(
            "--td-id",
            required=True,
            help=(
                "Work Ledger td_* thread id. For progress/note only, a claimed Task Ledger "
                "WorkItem id such as cap_* is accepted and converted into a linked open receipt."
            ),
        )
    if allow_unclaimed_note_arg:
        parser.add_argument(
            "--allow-unclaimed-note",
            action="store_true",
            help=(
                "Explicitly allow a low-blast progress/note append without an active td_id "
                "claim; writes warning metadata."
            ),
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Unified work ledger CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    bootstrap = subparsers.add_parser("bootstrap")
    bootstrap.add_argument("--phase-id", default=None)
    bootstrap.add_argument("--family-id", default=None)
    bootstrap.set_defaults(func=cmd_bootstrap)

    session_bootstrap = subparsers.add_parser(
        "session-bootstrap",
        aliases=["session-start"],
        help="Bootstrap a Work Ledger session; session-start is a compatibility alias.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_bootstrap.add_argument("--session-id", required=True)
    session_bootstrap.add_argument("--actor", default="codex")
    session_bootstrap.add_argument("--phase-id", default=None)
    session_bootstrap.add_argument("--family-id", default=None)
    session_bootstrap.add_argument("--limit", type=int, default=work_ledger_runtime.BOOTSTRAP_SLICE_LIMIT)
    session_bootstrap.set_defaults(func=cmd_session_bootstrap)

    session_activity = subparsers.add_parser("session-activity")
    session_activity.add_argument("--session-id", required=True)
    session_activity.add_argument("--action", required=True)
    session_activity.add_argument("--td-id", default=None)
    session_activity.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_activity.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_activity.set_defaults(func=cmd_session_activity)

    session_heartbeat = subparsers.add_parser(
        "session-heartbeat",
        help="Write a bounded public now/done pass heartbeat for one live session.",
        epilog=f"{SERIAL_MUTATION_HELP} {HEARTBEAT_PARTICIPATION_HELP}",
    )
    session_heartbeat.add_argument("--session-id", required=True)
    session_heartbeat.add_argument(
        "--state",
        default="inspecting",
        choices=sorted(
            set(work_ledger_runtime.PASS_HEARTBEAT_STATES)
            | set(SESSION_HEARTBEAT_STATE_ALIASES)
        ),
    )
    session_heartbeat.add_argument(
        "--current-pass-line",
        "--now",
        dest="current_pass_line",
        default=None,
        help=f"Public one-sentence current pass line, <= {work_ledger_runtime.PASS_CURRENT_LINE_LIMIT} chars.",
    )
    session_heartbeat.add_argument(
        "--last-pass-result-line",
        "--done",
        dest="last_pass_result_line",
        default=None,
        help=f"Public one-sentence previous pass result, <= {work_ledger_runtime.PASS_RESULT_LINE_LIMIT} chars.",
    )
    session_heartbeat.add_argument("--td-id", "--work-item-id", dest="td_id", default=None)
    session_heartbeat.add_argument(
        "--scope-ref",
        action="append",
        default=[],
        help="Bounded public scope/evidence ref such as a path, claim id, or receipt. Repeatable.",
    )
    session_heartbeat.add_argument("--pass-id", default=None)
    session_heartbeat.add_argument(
        "--source",
        default="manual_cli",
        choices=sorted(work_ledger_runtime.PASS_HEARTBEAT_SOURCES),
    )
    session_heartbeat.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_heartbeat.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_heartbeat.set_defaults(func=cmd_session_heartbeat)

    session_finalize = subparsers.add_parser(
        "session-finalize",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_finalize.add_argument("--session-id", required=True)
    session_finalize.add_argument("--action", default="session-end")
    session_finalize.add_argument(
        "--read-receipt-id",
        default="",
        help="Live session read receipt; required when recording append-exempt closeout.",
    )
    session_finalize.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
        help="Limit compact overview rows included in the lifecycle result.",
    )
    session_finalize.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_finalize.add_argument(
        "--no-release-claims",
        action="store_true",
        help="Diagnostic escape hatch: finalize the session without releasing its active claims.",
    )
    session_finalize.add_argument(
        "--allow-missing-append",
        action="store_true",
        help=(
            "Diagnostic escape hatch only: allow finalizing a touched session that "
            "has not written a Work Ledger append; this marks the session stale. "
            "Normal closeout should append Work Ledger evidence first or use "
            "--append-exempt-reason with --read-receipt-id and --append-exempt-ref."
        ),
    )
    session_finalize.add_argument(
        "--append-exempt-reason",
        default="",
        help=(
            "Record a non-stale append-exempt closeout for commit-only or "
            "projection-only sessions before finalizing. Requires --read-receipt-id."
        ),
    )
    session_finalize.add_argument(
        "--append-exempt-ref",
        action="append",
        default=[],
        help="Evidence ref for append-exempt closeout, such as a commit hash or receipt id.",
    )
    session_finalize.add_argument(
        "--append-exempt-td-id",
        action="append",
        default=[],
        help="Optional td_* touched by the append-exempt closeout.",
    )
    session_finalize.add_argument(
        "--append-exempt-work-item-id",
        action="append",
        default=[],
        help="Optional Task Ledger WorkItem id touched by the append-exempt closeout.",
    )
    session_finalize.set_defaults(func=cmd_session_finalize)

    session_status = subparsers.add_parser("session-status")
    session_status.add_argument(
        "--overview",
        action="store_true",
        help="Print the compact multi-agent session overview. This is the default.",
    )
    session_status.add_argument(
        "--full",
        action="store_true",
        help="Print the full runtime_status object for diagnostics.",
    )
    session_status.add_argument(
        "--with-session-cards",
        action="store_true",
        help="Include detailed compact session cards in overview output.",
    )
    session_status.add_argument(
        "--cards-only",
        action="store_true",
        help="Omit session row arrays from compact overview; keep counts, monitor cards, and drilldown commands.",
    )
    session_status.add_argument(
        "--seed-speed",
        action="store_true",
        help="Print the tiny active-seed coordination packet: claim sessions, heartbeat counts, risks, and drilldowns.",
    )
    session_status.add_argument(
        "--speed-only",
        action="store_true",
        help="Alias for --seed-speed.",
    )
    session_status.add_argument(
        "--no-heartbeat",
        action="store_true",
        help=(
            "For --seed-speed, promote the non-heartbeat coordination lane to "
            "first_action when heartbeat repair would otherwise be first."
        ),
    )
    session_status.add_argument(
        "--dirty-tree-pressure",
        action="store_true",
        help=(
            "For --seed-speed, include a compact dirty-tree pressure focus; "
            "--no-heartbeat enables this automatically."
        ),
    )
    session_status.add_argument(
        "--bankruptcy-authorized",
        action="store_true",
        help=(
            "For --seed-speed --dirty-tree-pressure, evaluate the broad checkpoint "
            "guard as operator-authorized while still remaining read-only."
        ),
    )
    session_status.add_argument(
        "--session-id",
        default="",
        help="Print one bounded session card; combine with --full for that session only.",
    )
    session_status.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    session_status.set_defaults(func=cmd_session_status)

    session_claims = subparsers.add_parser(
        "session-claims",
        help="Print the compact active-claims snapshot without expanding session cards.",
    )
    session_claims.add_argument(
        "--limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    session_claims.add_argument(
        "--refresh",
        action="store_true",
        help="Rebuild the active-claims snapshot from runtime_status.json before printing it.",
    )
    session_claims.add_argument(
        "--allow-stale",
        action="store_true",
        help="Print a stale snapshot with source-freshness metadata instead of suppressing rows.",
    )
    session_claims.add_argument(
        "--full",
        action="store_true",
        help="Print full claim rows, notes, source receipts, and nested collision details.",
    )
    session_claims.add_argument(
        "--cards-only",
        action="store_true",
        help="Compatibility no-op: compact cards are the default output.",
    )
    session_claims.set_defaults(func=cmd_session_claims)

    session_import_codex = subparsers.add_parser(
        "session-import-codex",
        help="Import recently updated local Codex threads as runtime-only work-ledger sessions.",
    )
    session_import_codex.add_argument("--actor", default="codex")
    session_import_codex.add_argument("--phase-id", default=None)
    session_import_codex.add_argument("--family-id", default=None)
    session_import_codex.add_argument("--since-minutes", type=float, default=60.0)
    session_import_codex.add_argument("--limit", type=int, default=20)
    session_import_codex.add_argument("--db-path", default=None)
    session_import_codex.add_argument("--include-all-cwds", action="store_true")
    session_import_codex.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview candidate Codex threads without mutating runtime_status.json.",
    )
    session_import_codex.set_defaults(func=cmd_session_import_codex)

    session_import_host = subparsers.add_parser(
        "session-import-host-surfaces",
        help="Import visible Codex threads plus Claude IDE locks as runtime-only coordination sessions.",
    )
    session_import_host.add_argument("--phase-id", default=None)
    session_import_host.add_argument("--family-id", default=None)
    session_import_host.add_argument("--since-minutes", type=float, default=60.0)
    session_import_host.add_argument("--limit", type=int, default=20)
    session_import_host.add_argument("--overview-limit", type=int, default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT)
    session_import_host.add_argument("--db-path", default=None)
    session_import_host.add_argument("--include-all-cwds", action="store_true")
    session_import_host.add_argument("--include-all-workspaces", action="store_true")
    session_import_host.add_argument("--skip-codex", action="store_true")
    session_import_host.add_argument("--skip-claude", action="store_true")
    session_import_host.add_argument("--dry-run", action="store_true")
    session_import_host.set_defaults(func=cmd_session_import_host_surfaces)

    mutation_check = subparsers.add_parser(
        "mutation-check",
        help="Check requested paths/write profiles against active path claims without mutating runtime state.",
    )
    mutation_check.add_argument("--session-id", default=None)
    mutation_check.add_argument("--path", action="append", default=[])
    mutation_check.add_argument(
        "--write-profile",
        action="append",
        choices=sorted(WRITE_PROFILE_PATHS),
        default=[],
    )
    mutation_check.add_argument("--require-exclusive", action="store_true")
    mutation_check.set_defaults(func=cmd_mutation_check)

    helper_lease_admission = subparsers.add_parser(
        "helper-lease-admission",
        help=(
            "Gate a proposed persistent helper/tool lease through the host-pressure "
            "budget before starting another MCP/Codex helper process."
        ),
    )
    helper_lease_admission.add_argument(
        "--lease-kind",
        required=True,
        choices=work_admission.HELPER_LEASE_KINDS,
    )
    helper_lease_admission.add_argument("--request-id", default=None)
    helper_lease_admission.add_argument("--requested-by", default=None)
    helper_lease_admission.add_argument("--owner-status", default="unknown")
    helper_lease_admission.add_argument("--current-lease-count", type=int, default=None)
    helper_lease_admission.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=os.environ.get("AIW_HELPER_LEASE_HOST_PRESSURE_POLICY", "auto"),
        help=(
            "Admission policy before allocating a persistent helper lease: auto queues "
            "under degraded pressure, warn reports but admits, off disables the gate."
        ),
    )
    helper_lease_admission.set_defaults(func=cmd_helper_lease_admission)

    resident_pressure_relief = subparsers.add_parser(
        "resident-pressure-relief",
        help=(
            "Record a resident-pressure relief attempt: owner-release result, "
            "optional background-loop downshift, and recovery-window verdict."
        ),
    )
    resident_pressure_relief.add_argument(
        "--process-kind",
        required=True,
        choices=work_admission.HELPER_LEASE_KINDS,
    )
    resident_pressure_relief.add_argument("--owner-status", default="unknown")
    resident_pressure_relief.add_argument("--target-owner", default=None)
    resident_pressure_relief.add_argument("--rss-mb-total", type=float, default=None)
    resident_pressure_relief.add_argument(
        "--pressure-mode",
        choices=("normal", "degraded", "relief_window", "recovery_monitoring", "unknown"),
        default="degraded",
    )
    resident_pressure_relief.add_argument(
        "--owner-release-result",
        choices=work_admission.OWNER_RELEASE_RESULT_VALUES,
        default="unsupported",
    )
    resident_pressure_relief.add_argument("--result-note", default=None)
    resident_pressure_relief.add_argument(
        "--background-loop-kind",
        choices=work_admission.BACKGROUND_LOOP_KINDS,
        default=None,
    )
    resident_pressure_relief.add_argument("--owner-surface", default=None)
    resident_pressure_relief.add_argument(
        "--background-loop-result",
        choices=work_admission.BACKGROUND_DOWNSHIFT_RESULTS,
        default="unsupported",
    )
    resident_pressure_relief.add_argument("--duration-s", type=int, default=600)
    resident_pressure_relief.add_argument("--effective-interval-s", type=float, default=15.0)
    resident_pressure_relief.add_argument(
        "--apply-background-downshift",
        action="store_true",
        help=(
            "Write the background-loop downshift receipt to the resident state file. "
            "Current consumers only downshift known loops such as agent_observability_sampler."
        ),
    )
    resident_pressure_relief.add_argument("--blocked-work-starts", type=int, default=0)
    resident_pressure_relief.add_argument("--blocked-helper-leases", type=int, default=0)
    resident_pressure_relief.add_argument("--workload-mix-changed", action="store_true")
    resident_pressure_relief.set_defaults(func=cmd_resident_pressure_relief)

    session_yield_request = subparsers.add_parser(
        "session-yield-request",
        help=(
            "Append a non-destructive owner-visible yield/release request for "
            "already-resident pressure. This is a request bus, not a kill lane."
        ),
    )
    session_yield_request.add_argument("--target-session-id", required=True)
    session_yield_request.add_argument("--request-id", default=None)
    session_yield_request.add_argument(
        "--target-class",
        choices=("idle_session", "low_progress_session", "high_helper_footprint_session", "background_loop_owner"),
        default="high_helper_footprint_session",
    )
    session_yield_request.add_argument(
        "--requested-action",
        choices=work_admission.SESSION_YIELD_ACTIONS,
        default="release_tool_lease",
    )
    session_yield_request.add_argument("--owner-status", default="active_session")
    session_yield_request.add_argument(
        "--pressure-mode",
        choices=("normal", "degraded", "relief_window", "recovery_monitoring", "unknown"),
        default="degraded",
    )
    session_yield_request.add_argument(
        "--result",
        choices=work_admission.SESSION_YIELD_RESULTS,
        default="requested",
    )
    session_yield_request.add_argument("--helper-rss-mb", type=float, default=0.0)
    session_yield_request.add_argument("--recent-progress-units", type=float, default=0.0)
    session_yield_request.add_argument("--idle-age-s", type=float, default=0.0)
    session_yield_request.add_argument("--last-heartbeat-age-s", type=float, default=0.0)
    session_yield_request.add_argument("--active-claim-count", type=int, default=0)
    session_yield_request.add_argument("--operator-priority-hint", default=None)
    session_yield_request.add_argument("--result-note", default=None)
    session_yield_request.add_argument("--dry-run", action="store_true")
    session_yield_request.set_defaults(func=cmd_session_yield_request)

    session_yield_result = subparsers.add_parser(
        "session-yield-result",
        help=(
            "Close a resident pressure yield request with the owning session's "
            "visible result. Accepted still requires an applied action to count as relief."
        ),
    )
    session_yield_result.add_argument("--request-id", default=None)
    session_yield_result.add_argument("--target-session-id", default=None)
    session_yield_result.add_argument(
        "--result",
        choices=work_admission.OWNER_YIELD_RESULT_VALUES,
        required=True,
    )
    session_yield_result.add_argument(
        "--applied-action",
        choices=work_admission.OWNER_YIELD_APPLIED_ACTIONS,
        default="none",
    )
    session_yield_result.add_argument(
        "--delivery",
        choices=work_admission.OWNER_YIELD_DELIVERY_VALUES,
        default="visible_to_owner",
    )
    session_yield_result.add_argument("--result-note", default=None)
    session_yield_result.add_argument("--dry-run", action="store_true")
    session_yield_result.set_defaults(func=cmd_session_yield_result)

    session_yield_control = subparsers.add_parser(
        "session-yield-control",
        help="Summarize pending, accepted, and applied resident pressure relief requests.",
    )
    session_yield_control.add_argument("--limit", type=int, default=20)
    session_yield_control.set_defaults(func=cmd_session_yield_control)

    session_preflight = subparsers.add_parser(
        "session-preflight",
        help=(
            "One-command autonomous-seed preflight: import recent Codex peers, "
            "bootstrap this session, optionally claim td/path scopes, and print closeout commands."
        ),
        epilog=(
            "This is the serial setup lane for one session; prefer it over parallel "
            "session-bootstrap plus session-claim-path calls."
        ),
    )
    session_preflight.add_argument("--session-id", default=None)
    session_preflight.add_argument("--session-slug", default="autonomous")
    session_preflight.add_argument("--actor", default="codex")
    session_preflight.add_argument("--phase-id", default=None)
    session_preflight.add_argument("--family-id", default=None)
    session_preflight.add_argument("--td-id", "--work-item-id", dest="td_id", action="append", default=[])
    session_preflight.add_argument("--path", "--claim-path", dest="path", action="append", default=[])
    session_preflight.add_argument(
        "--write-profile",
        action="append",
        choices=sorted(WRITE_PROFILE_PATHS),
        default=[],
        help=(
            "Claim the known generated write set for a projection command. "
            "May be repeated; choices: %(choices)s."
        ),
    )
    session_preflight.add_argument("--lease-minutes", type=float, default=30.0)
    session_preflight.add_argument("--note", default=None)
    session_preflight.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=os.environ.get("AIW_WORK_LEDGER_HOST_PRESSURE_POLICY", "auto"),
        help=(
            "Admission policy before creating session claims: auto queues heavy work "
            "under host-pressure load-shed, warn reports but admits, off disables the gate."
        ),
    )
    session_preflight.add_argument(
        "--work-admission-class",
        default=None,
        choices=sorted(work_admission.HOST_PRESSURE_WORKLOAD_BY_CLASS),
        help="Override the inferred work-creation class for this session preflight.",
    )
    session_preflight.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse any requested td/path claim that collides with an active overlapping claim.",
    )
    session_preflight.add_argument(
        "--skip-import-codex",
        action="store_true",
        help="Do not import recent Codex host threads before bootstrapping this session.",
    )
    session_preflight.add_argument(
        "--skip-import-claude",
        action="store_true",
        help="Do not import Claude IDE lock observations before bootstrapping this session.",
    )
    session_preflight.add_argument("--since-minutes", type=float, default=60.0)
    session_preflight.add_argument("--import-limit", type=int, default=20)
    session_preflight.add_argument("--bootstrap-limit", type=int, default=work_ledger_runtime.BOOTSTRAP_SLICE_LIMIT)
    session_preflight.add_argument(
        "--overview-limit",
        "--limit",
        dest="overview_limit",
        type=int,
        default=work_ledger_runtime.SESSION_COHORT_OVERVIEW_LIMIT,
    )
    session_preflight.add_argument("--db-path", default=None)
    session_preflight.add_argument("--include-all-cwds", action="store_true")
    session_preflight.add_argument("--include-all-workspaces", action="store_true")
    session_preflight.add_argument(
        "--full",
        action="store_true",
        help="Print the full bootstrap/import/cohort payload instead of the compact default.",
    )
    session_preflight.set_defaults(func=cmd_session_preflight)

    session_claim = subparsers.add_parser(
        "session-claim",
        help="Record a forward-looking lease on a td_* and surface any active claim collision.",
    )
    session_claim.add_argument("--session-id", required=True)
    session_claim.add_argument("--td-id", required=True)
    session_claim.add_argument(
        "--lease-minutes",
        type=float,
        default=30.0,
        help="Lease duration in minutes (default 30, clamped to 12h max).",
    )
    session_claim.add_argument("--note", default=None)
    session_claim.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse the claim if another active session holds an unexpired claim on the same td_id, WorkItem id, or path.",
    )
    session_claim.set_defaults(func=cmd_session_claim)

    session_claim_path = subparsers.add_parser(
        "session-claim-path",
        help="Record a forward-looking lease on a repo-relative path and surface active path collisions.",
        epilog=SERIAL_MUTATION_HELP,
    )
    session_claim_path.add_argument("--session-id", required=True)
    session_claim_path.add_argument("--path", required=True)
    session_claim_path.add_argument(
        "--lease-minutes",
        type=float,
        default=30.0,
        help="Lease duration in minutes (default 30, clamped to 12h max).",
    )
    session_claim_path.add_argument("--note", default=None)
    session_claim_path.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Refuse the claim if another active session holds an overlapping unexpired path claim.",
    )
    session_claim_path.set_defaults(func=cmd_session_claim_path)

    session_release_claim = subparsers.add_parser(
        "session-release-claim",
        help="Release an active claim by --claim-id, --td-id, or --path.",
    )
    session_release_claim.add_argument("--session-id", required=True)
    session_release_claim.add_argument("--claim-id", default=None)
    session_release_claim.add_argument("--td-id", default=None)
    session_release_claim.add_argument("--path", default=None)
    session_release_claim.add_argument(
        "--reason",
        default="released_by_operator",
        help="Free-form release reason recorded on the claim.",
    )
    session_release_claim.set_defaults(func=cmd_session_release_claim)

    session_sweep = subparsers.add_parser(
        "session-sweep",
        help=(
            "Auto-finalize crashed orphan sessions and mark expired claims. "
            "Idempotent; preserves history (end_action=auto_orphan_sweep, expired_at set explicitly)."
        ),
    )
    session_sweep.add_argument(
        "--orphan-after-hours",
        type=float,
        default=0.0,
        help=(
            "Override the orphan sweep threshold in hours "
            "(default uses ACTIVE_SESSION_ORPHAN_SWEEP_AFTER = 24h)."
        ),
    )
    session_sweep.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview which sessions/claims would be swept without mutating state.",
    )
    session_sweep.add_argument(
        "--dirty-tree-pressure",
        action="store_true",
        help=(
            "Include a read-only dirty-tree bankruptcy pressure card that routes "
            "expired work to sweep/private-backup/scoped owner lanes without committing from age alone."
        ),
    )
    session_sweep.add_argument(
        "--dirty-path",
        action="append",
        default=[],
        help=(
            "Repo-relative dirty path fixture for pressure classification. "
            "Repeatable; when omitted, git status --porcelain=v1 -z --untracked-files=all is read."
        ),
    )
    session_sweep.add_argument(
        "--bankruptcy-authorized",
        action="store_true",
        help=(
            "For explicit operator dirty-tree-bankruptcy requests, allow the pressure "
            "card to route to the broad checkpoint arbiter command when no dirty path "
            "is covered by an active claim."
        ),
    )
    session_sweep.add_argument(
        "--dedupe-duplicate-claims",
        action="store_true",
        help=(
            "Release older duplicate claims held by the same session and scope. "
            "True cross-session collisions remain explicit coordination blockers."
        ),
    )
    session_sweep.set_defaults(func=cmd_session_sweep)

    append_open = subparsers.add_parser("append-open")
    _add_common_mutation_args(append_open)
    append_open.set_defaults(func=cmd_append_open)

    progress = subparsers.add_parser("progress")
    _add_common_mutation_args(progress, require_td_id=True, allow_unclaimed_note_arg=True)
    progress.set_defaults(func=cmd_progress)

    note = subparsers.add_parser("note")
    _add_common_mutation_args(note, require_td_id=True, allow_unclaimed_note_arg=True)
    note.set_defaults(func=cmd_progress)

    close = subparsers.add_parser("close")
    _add_common_mutation_args(close, require_td_id=True)
    close.add_argument("--resolution-kind", required=True, choices=sorted(work_ledger.RESOLUTION_KINDS))
    close.add_argument("--resolution-ref", required=True)
    close.add_argument("--resolution-label", default=None)
    close.add_argument("--resolution-metadata-json", default=None)
    close.set_defaults(func=cmd_close)

    supersede = subparsers.add_parser("supersede")
    _add_common_mutation_args(supersede, require_td_id=True)
    supersede.add_argument("--resolution-kind", required=True, choices=sorted(work_ledger.RESOLUTION_KINDS))
    supersede.add_argument("--resolution-ref", required=True)
    supersede.add_argument("--resolution-label", default=None)
    supersede.add_argument("--resolution-metadata-json", default=None)
    supersede.set_defaults(func=cmd_supersede)

    reopen = subparsers.add_parser("reopen")
    _add_common_mutation_args(reopen, require_td_id=True)
    reopen.set_defaults(func=cmd_reopen)

    project = subparsers.add_parser("project")
    project.add_argument("--phase-id", default=None)
    project.add_argument("--family-id", default=None)
    project.add_argument("--all", action="store_true")
    project.add_argument("--check", action="store_true")
    project.set_defaults(func=cmd_project)

    query = subparsers.add_parser("query")
    query.add_argument("--recipe", required=True, choices=work_ledger.supported_query_recipes())
    query.add_argument("--phase-id", default=None)
    query.add_argument("--family-id", default=None)
    query.add_argument("--actor", default=None)
    query.add_argument("--actor-session-id", default=None)
    query.add_argument("--td-id", default=None)
    query.add_argument("--limit", type=int, default=20)
    query.add_argument("--read-receipt-id", default=None)
    query.set_defaults(func=cmd_query)

    handoffs = subparsers.add_parser(
        "agent-seed-handoffs",
        help="Extract agent_seed handoff/deferred-work paragraphs and optionally open deduped work-ledger rows.",
    )
    handoffs.add_argument("--phase-id", default=None)
    handoffs.add_argument("--family-id", default=None)
    handoffs.add_argument("--since-date", default=None)
    handoffs.add_argument("--limit", type=int, default=100)
    handoffs.add_argument("--include-imported", action="store_true")
    handoffs.add_argument("--live", action="store_true")
    handoffs.add_argument("--read-receipt-id", default=None)
    handoffs.add_argument("--actor", default=None)
    handoffs.add_argument("--actor-session-id", default=None)
    handoffs.set_defaults(func=cmd_agent_seed_handoffs)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
