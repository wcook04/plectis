#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import task_ledger_events, work_ledger, work_ledger_runtime
from tools.meta.observability import station_render


TASK_LEDGER_SEARCH_SCHEMA = "task_ledger_search_v0"

_TASK_LEDGER_PARALLEL_SAFETY_NOTE = (
    "Parallel safety: Task Ledger mutation commands are single-writer operations; "
    "run them sequentially or use the batch lane for one logical closeout. "
    "Do not launch multiple quick-capture --rebuild commands in parallel; "
    "each command appends to events.jsonl and may refresh shared projections. "
    "For parallel read-only searches, do not reuse one shared temp query file; "
    "prefer stdin or one unique file path per process."
)

_TASK_LEDGER_TAG_FLAG_HINT = (
    "Task Ledger commands use repeated --tag flags, not --tags or comma-separated "
    "tag lists. Example: --tag self_error --tag task_ledger."
)


class TaskLedgerArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        if "--tags" in message:
            message = f"{message}\nHint: {_TASK_LEDGER_TAG_FLAG_HINT}"
        super().error(message)


EVENT_BY_COMMAND = {
    "capture": "work_item.captured",
    "triage": "work_item.triaged",
    "promote": "work_item.promoted",
    "shape": "work_item.shaped",
    "claim": "work_item.claimed",
    "release": "work_item.released",
    "note": "work_item.note_added",
    "transition": "work_item.state_transitioned",
    "block": "work_item.blocked",
    "unblock": "work_item.unblocked",
    "rerank-propose": "work_item.rerank_proposed",
    "rerank-commit": "work_item.rerank_committed",
    "sign-off": "work_item.signoff_recorded",
    "execution-receipt": "work_item.execution_receipt_recorded",
    "record-execution-receipt": "work_item.execution_receipt_recorded",
    "bridge-delegate": "work_item.bridge_delegated",
    "provider-job-create": "work_item.provider_job_created",
    "schema-migrate": "work_item.schema_migrated",
    "propagate": "work_item.propagation_recorded",
    "retire": "work_item.retired",
}

PROMOTED_RENDER_RECEIPT_ATTACHMENT_SCHEMA = "task_ledger_promoted_render_receipt_attachment_v1"
TASK_LEDGER_AUTHORITY_MUTATION_CHECKPOINT_SCHEMA = "task_ledger_authority_mutation_checkpoint_v1"
TASK_LEDGER_AUTHORITY_MUTATION_PATHS = (
    "state/task_ledger/events.jsonl",
    "state/task_ledger/events_audit.jsonl",
    "state/task_ledger/ledger.json",
    "state/task_ledger/sign_offs.json",
    "state/task_ledger/views",
)
TASK_LEDGER_CLEAN_CLOSEOUT_STATES = {
    "complete",
    "completed",
    "closed",
    "done",
    "landed",
    "propagated",
    "refined",
    "signed_off",
}


def _print(payload: Dict[str, Any]) -> int:
    try:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    return 0 if payload.get("ok", True) else 1


def _print_with_exit_code(payload: Dict[str, Any], exit_code: int) -> int:
    try:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except Exception:
            pass
        return 0
    return exit_code


def _stderr_progress(payload: Dict[str, Any]) -> None:
    try:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True), file=sys.stderr, flush=True)
    except BrokenPipeError:
        try:
            sys.stderr.close()
        except Exception:
            pass


def _progress_callback(args: argparse.Namespace, command_name: str):
    if getattr(args, "quiet_progress", False):
        return None

    def emit(payload: Dict[str, Any]) -> None:
        enriched = dict(payload)
        enriched.setdefault("schema", "task_ledger_apply_progress_v0")
        enriched["command"] = command_name
        _stderr_progress(enriched)

    return emit


def _parse_ids_arg(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in re.split(r"[,\s]+", value.strip()) if part]


def _norm_search_text(value: object) -> str:
    return " ".join(str(value or "").lower().split())


def _search_tokens(value: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9_:-]+", _norm_search_text(value)) if token]


def _search_field_text(value: object, *, max_items: int = 16) -> str:
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    if isinstance(value, list):
        parts = [_search_field_text(item, max_items=max_items) for item in value[:max_items]]
        return " ".join(part for part in parts if part)
    if isinstance(value, dict):
        parts: list[str] = []
        for key in sorted(value)[:max_items]:
            parts.append(str(key))
            parts.append(_search_field_text(value.get(key), max_items=max_items))
        return " ".join(part for part in parts if part)
    return str(value)


def _string_list(value: object, *, limit: int | None = None) -> list[str]:
    if value is None:
        return []
    raw = value if isinstance(value, list) else [value]
    items = [str(item) for item in raw if str(item).strip()]
    return items if limit is None else items[:limit]


def _row_rank_value(row: Dict[str, Any]) -> int:
    try:
        return int(row.get("rank") or 999_999)
    except (TypeError, ValueError):
        return 999_999


def _task_ledger_search_text(row: Dict[str, Any]) -> dict[str, str]:
    execution = row.get("execution") if isinstance(row.get("execution"), dict) else {}
    fields = {
        "id": row.get("id"),
        "title": row.get("title"),
        "statement": row.get("statement"),
        "state": row.get("state") or row.get("status"),
        "work_item_type": row.get("work_item_type") or row.get("candidate_work_item_type"),
        "tags": row.get("tags"),
        "owner": row.get("owner") or execution.get("owner"),
        "notes": row.get("notes"),
        "depends_on": row.get("depends_on"),
        "dependencies": row.get("dependencies"),
        "evidence_refs": row.get("evidence_refs"),
        "receipt_refs": row.get("receipt_refs"),
        "evidence_attachments": row.get("evidence_attachments"),
    }
    return {key: _norm_search_text(_search_field_text(value)) for key, value in fields.items()}


def _task_ledger_search_score(row: Dict[str, Any], query: str, tokens: list[str]) -> tuple[float, list[str]]:
    fields = _task_ledger_search_text(row)
    haystack = " ".join(fields.values())
    if not haystack:
        return 0.0, []

    phrase = _norm_search_text(query)
    score = 0.0
    matched: list[str] = []
    row_id = fields.get("id", "")
    title = fields.get("title", "")
    statement = fields.get("statement", "")
    tags = fields.get("tags", "")
    notes = fields.get("notes", "")

    if phrase:
        if phrase == row_id:
            score += 500.0
        elif phrase in row_id:
            score += 160.0
        if phrase in title:
            score += 120.0
        if phrase in statement:
            score += 50.0
        if phrase in haystack:
            score += 25.0

    for token in tokens:
        token_score = 0.0
        if token == row_id:
            token_score += 120.0
        elif token in row_id:
            token_score += 45.0
        if token in title:
            token_score += 35.0
        if token in statement:
            token_score += 16.0
        if token in tags:
            token_score += 14.0
        if token in notes:
            token_score += 5.0
        if token in haystack:
            token_score += 2.0
        if token_score:
            matched.append(token)
            score += token_score

    if not matched and tokens:
        return 0.0, []
    if tokens and len(set(matched)) == len(set(tokens)):
        score += 30.0
    if row.get("state") in {"ready", "claimed", "active", "review"}:
        score += 3.0
    rank = _row_rank_value(row)
    if rank < 999_999:
        score += max(0.0, 2.0 - (rank * 0.01))
    return score, sorted(set(matched))


def _compact_task_ledger_search_row(row: Dict[str, Any], *, score: float, matched_tokens: list[str]) -> Dict[str, Any]:
    row_id = str(row.get("id") or "").strip()
    return {
        "id": row_id,
        "title": row.get("title"),
        "state": row.get("state") or row.get("status"),
        "rank": row.get("rank"),
        "work_item_type": row.get("work_item_type") or row.get("candidate_work_item_type"),
        "score": round(score, 3),
        "matched_tokens": matched_tokens,
        "updated_at": row.get("updated_at"),
        "tags": _string_list(row.get("tags"), limit=8),
        "statement": str(row.get("statement") or "")[:360],
        "drilldown_command": (
            f"./repo-python kernel.py --option-surface task_ledger --band card --ids {shlex.quote(row_id)}"
            if row_id
            else None
        ),
    }


def _load_task_ledger_projection() -> tuple[Dict[str, Any], Path]:
    ledger_path = REPO_ROOT / task_ledger_events.LEDGER_REL
    if not ledger_path.exists():
        raise FileNotFoundError(f"Task Ledger projection missing: {task_ledger_events.LEDGER_REL}")
    payload = json.loads(ledger_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Task Ledger projection must decode to an object: {task_ledger_events.LEDGER_REL}")
    return payload, ledger_path


def _visibility_receipt(
    *,
    subject_ids: list[str],
    event_ids: list[str],
    projection_result: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    return task_ledger_events.visibility_receipt(
        REPO_ROOT,
        subject_ids=subject_ids,
        event_ids=event_ids,
        projection_rebuilt=projection_result is not None,
        projection_result=projection_result,
    )


def _load_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {}
    if getattr(args, "payload_json", None):
        loaded = json.loads(args.payload_json)
        if not isinstance(loaded, dict):
            raise ValueError("--payload-json must decode to an object")
        payload.update(loaded)
    if getattr(args, "payload_file", None):
        loaded = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("--payload-file must decode to an object")
        payload.update(loaded)
    if getattr(args, "payload_stdin", False):
        loaded = json.loads(sys.stdin.read())
        if not isinstance(loaded, dict):
            raise ValueError("--payload-stdin must decode to an object")
        payload.update(loaded)
    return payload


def _load_mission_closeout_report(args: argparse.Namespace) -> Dict[str, Any]:
    inline = getattr(args, "mission_closeout_report_json", None)
    file_path = getattr(args, "mission_closeout_report_file", None)
    if inline and file_path:
        raise ValueError("--mission-closeout-report-json and --mission-closeout-report-file are mutually exclusive")
    if not inline and not file_path:
        return {}
    raw = inline if inline is not None else Path(file_path).read_text(encoding="utf-8")
    loaded = json.loads(raw)
    if not isinstance(loaded, dict):
        raise ValueError("--mission-closeout-report-json/file must decode to an object")
    return loaded


def _nested_mapping(source: Dict[str, Any], *path: str) -> Dict[str, Any]:
    current: Any = source
    for key in path:
        if not isinstance(current, dict):
            return {}
        current = current.get(key)
    return dict(current) if isinstance(current, dict) else {}


def _mission_blocked_primary_continuation(report: Dict[str, Any]) -> Dict[str, Any]:
    for path in (
        ("review", "blocked_primary_continuation"),
        ("owned_closeout", "blocked_primary_continuation"),
        ("blocked_primary_continuation",),
    ):
        candidate = _nested_mapping(report, *path)
        if candidate:
            return candidate
    return {}


def _append_unique_strings(values: list[Any], additions: list[Any]) -> list[Any]:
    merged = list(values)
    seen = {str(item) for item in merged if str(item).strip()}
    for item in additions:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        merged.append(text)
        seen.add(text)
    return merged


def _mission_closeout_report_digest(report: Dict[str, Any]) -> str:
    encoded = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _git_dirty_paths(repo_root: Path, pathspecs: tuple[str, ...]) -> Dict[str, Any]:
    try:
        completed = subprocess.run(
            ["git", "status", "--porcelain=v1", "--", *pathspecs],
            cwd=repo_root,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        return {"status": "unknown", "error": str(exc), "dirty_paths": []}
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        status = "not_git_repository" if "not a git repository" in stderr.lower() else "unknown"
        return {"status": status, "error": stderr, "dirty_paths": []}

    dirty_paths: list[str] = []
    for line in completed.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[-1].strip()
        if path:
            dirty_paths.append(path)
    return {
        "status": "dirty" if dirty_paths else "clean",
        "dirty_paths": dirty_paths,
    }


def _execution_receipt_authority_mutation_checkpoint(args: argparse.Namespace) -> Dict[str, Any]:
    closeout_state = str(getattr(args, "closeout_state", "") or "").strip()
    git_state = _git_dirty_paths(REPO_ROOT, TASK_LEDGER_AUTHORITY_MUTATION_PATHS)
    dirty_paths = list(git_state.get("dirty_paths") or [])
    clean_closeout = closeout_state in TASK_LEDGER_CLEAN_CLOSEOUT_STATES
    dirty_before_append = git_state.get("status") == "dirty"
    blocked = bool(dirty_before_append and clean_closeout)
    status = "blocked_preexisting_dirty_authority" if blocked else "pre_append_authority_checked"
    if git_state.get("status") == "clean":
        anchor_status = "clean_before_append_scoped_commit_required_after_append"
    elif dirty_before_append:
        anchor_status = "dirty_before_append"
    else:
        anchor_status = "git_status_unavailable"
    return {
        "schema": TASK_LEDGER_AUTHORITY_MUTATION_CHECKPOINT_SCHEMA,
        "status": status,
        "ok": not blocked,
        "command": str(getattr(args, "command_name", "") or ""),
        "subject_id": str(getattr(args, "subject_id", "") or ""),
        "transaction_id": str(getattr(args, "transaction_id", "") or ""),
        "closeout_state": closeout_state,
        "clean_closeout_requires_anchor": clean_closeout,
        "pre_append_git_status": git_state.get("status"),
        "pre_append_anchor_status": anchor_status,
        "dirty_paths": dirty_paths[:50],
        "dirty_path_count": len(dirty_paths),
        "authority_pathspecs": list(TASK_LEDGER_AUTHORITY_MUTATION_PATHS),
        "required_action": (
            "checkpoint, isolate, or residualize pre-existing Task Ledger authority dirt before clean closeout append"
            if blocked
            else "append may proceed; scoped commit or governed settle remains required for the new authority delta"
        ),
        "standard_ref": "std_task_ledger.execution_receipt_contract.authority_mutation_checkpoint_rule",
    }


def _apply_mission_closeout_report(args: argparse.Namespace, payload: Dict[str, Any]) -> Dict[str, Any]:
    report = _load_mission_closeout_report(args)
    if not report:
        return payload
    continuation = _mission_blocked_primary_continuation(report)
    if not continuation:
        return payload

    closeout = dict(payload.get("closeout_assurance") or {})
    closeout.setdefault("claim", "Mission runtime closeout validated blocked-primary continuation evidence.")
    closeout["evidence_refs"] = _append_unique_strings(
        list(closeout.get("evidence_refs") or []),
        [
            "mission_closeout_report:review.blocked_primary_continuation",
            "system/lib/mission_transaction_landing_preflight.py::build_explore_execute_review_runtime_closeout",
            "tools/meta/factory/task_ledger_apply.py::record-execution-receipt",
        ],
    )
    closeout.setdefault("corrective_action_strength", "strong")
    closeout["counterexample_checks"] = _append_unique_strings(
        list(closeout.get("counterexample_checks") or []),
        [
            "missing blocked-primary continuation receipt blocks Task Ledger done-claim append",
            "complete mission closeout blocked_primary_continuation is re-observable on Task Ledger cards",
        ],
    )
    closeout.setdefault("owner_surface", "tools/meta/factory/task_ledger_apply.py::record-execution-receipt")
    closeout.setdefault("residuals", [])
    if not isinstance(closeout.get("blocked_primary_continuation"), dict):
        closeout["blocked_primary_continuation"] = continuation
    payload["closeout_assurance"] = task_ledger_events._normalize_closeout_assurance(closeout)

    report_sha16 = _mission_closeout_report_digest(report)
    execution = dict(payload.get("execution") or {})
    execution.setdefault("mission_closeout_report_consumed", True)
    execution.setdefault("mission_closeout_report_sha16", report_sha16)
    status = str(continuation.get("status") or "").strip()
    if status:
        execution.setdefault("blocked_primary_continuation_status", status)
    payload["execution"] = execution

    source = dict(payload.get("source") if isinstance(payload.get("source"), dict) else {"kind": "task_ledger_apply", "refs": []})
    source_refs = list(source.get("refs") or [])
    source["refs"] = _append_unique_strings(source_refs, ["mission_closeout_report", f"sha16:{report_sha16}"])
    payload["source"] = source
    return payload


def _text_arg(args: argparse.Namespace, name: str) -> str | None:
    inline = getattr(args, name, None)
    file_path = getattr(args, f"{name}_file", None)
    stdin_flag = bool(getattr(args, f"{name}_stdin", False))
    provided = [inline is not None, file_path is not None, stdin_flag]
    if sum(provided) > 1:
        option = name.replace("_", "-")
        raise ValueError(
            f"--{option}, --{option}-file, and --{option}-stdin are mutually exclusive"
        )
    if file_path is not None:
        return Path(file_path).read_text(encoding="utf-8")
    if stdin_flag:
        return sys.stdin.read()
    return inline


def _validate_command_payload(command: str, payload: Dict[str, Any]) -> None:
    if command == "transition":
        state = str(payload.get("state") or "").strip()
        if state and state not in task_ledger_events.WORK_ITEM_STATES:
            valid_states = ", ".join(sorted(task_ledger_events.WORK_ITEM_STATES))
            raise ValueError(
                f"transition state {state!r} is not projection-consumable; "
                f"use one of: {valid_states}"
            )
        return
    if command != "propagate":
        return
    propagation = payload.get("propagation")
    if not isinstance(propagation, dict) or not propagation:
        raise ValueError(
            "propagate requires --payload-json/--payload-file/--payload-stdin "
            "with a non-empty 'propagation' object"
        )


_TASK_LEDGER_EVENT_ID_RE = re.compile(r"^wie_\d{8}T\d{6}Z_[0-9a-f]+$")


def _validate_depends_on_args(depends_on: list[str], *, command: str) -> None:
    event_ids = [
        str(dep_id).strip()
        for dep_id in depends_on
        if _TASK_LEDGER_EVENT_ID_RE.fullmatch(str(dep_id).strip())
    ]
    if not event_ids:
        return
    sample = event_ids[0]
    raise ValueError(
        f"{command} --depends-on expects WorkItem ids, not Task Ledger event ids; "
        f"got {sample}. Use the WorkItem subject_id for hard prerequisite edges, "
        "or use --dependency for broad context/event references."
    )


def _apply_execution_receipt_args(args: argparse.Namespace, payload: Dict[str, Any]) -> Dict[str, Any]:
    payload = _apply_mission_closeout_report(args, payload)
    receipt = dict(payload.get("execution_receipt") or payload.get("receipt") or {})
    receipt.setdefault("schema", args.receipt_schema)
    receipt.setdefault("transaction_id", args.transaction_id)
    receipt.setdefault("work_ledger_session_id", args.work_ledger_session_id)
    receipt.setdefault("read_receipt_id", args.read_receipt_id)
    receipt.setdefault("commit_hash", args.commit_hash)
    receipt.setdefault("read_set_hash", args.read_set_hash)
    receipt.setdefault("write_set_hash", args.write_set_hash)
    receipt.setdefault("validation_refs", args.validation_ref)
    receipt.setdefault("projection_refs", args.projection_ref)
    receipt.setdefault("closeout_state", args.closeout_state)
    receipt.setdefault("no_commit_reason", args.no_commit_reason)
    receipt.setdefault("commit_blocker_refs", args.commit_blocker_ref)
    payload["execution_receipt"] = {key: value for key, value in receipt.items() if value not in (None, [], {})}

    execution = dict(payload.get("execution") or {})
    if args.work_ledger_session_id:
        execution.setdefault("work_ledger_session_id", args.work_ledger_session_id)
    if args.read_receipt_id:
        execution.setdefault("read_receipt_id", args.read_receipt_id)
    if execution:
        payload["execution"] = execution

    refs = dict(payload.get("refs") or {})
    work_refs = list(refs.get("work_ledger_refs") or [])
    for ref in (args.work_ledger_session_id, args.read_receipt_id):
        if ref and ref not in work_refs:
            work_refs.append(ref)
    if work_refs:
        refs["work_ledger_refs"] = work_refs
        payload["work_ledger_refs"] = work_refs
    commit_refs = list(refs.get("commit_refs") or [])
    if args.commit_hash and args.commit_hash not in commit_refs:
        commit_refs.append(args.commit_hash)
    if commit_refs:
        refs["commit_refs"] = commit_refs
        payload["commit_refs"] = commit_refs
    receipt_refs = list(refs.get("receipt_refs") or [])
    if args.transaction_id and args.transaction_id not in receipt_refs:
        receipt_refs.append(args.transaction_id)
    if receipt_refs:
        refs["receipt_refs"] = receipt_refs
        payload["receipt_refs"] = receipt_refs
    if refs:
        payload["refs"] = refs
    return payload


def _promoted_render_manifest_path(args: argparse.Namespace) -> Path:
    manifest_path = (
        Path(args.receipt_path)
        if args.receipt_path
        else station_render._manifest_path_for_receipt_ref(args.receipt_ref)
    )
    return manifest_path if manifest_path.is_absolute() else REPO_ROOT / manifest_path


def _promoted_render_evidence_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload = _load_payload(args)
    promoted = station_render.build_promoted_render_receipt(
        manifest_path=_promoted_render_manifest_path(args),
        receipt_ref=args.receipt_ref,
        subject_id=args.subject_id,
        promotion_status=args.promotion_status,
        consumer=args.consumer,
    )
    receipt_ref = str(promoted.get("receipt_ref") or args.receipt_ref).strip()
    receipt_path = str(promoted.get("receipt_path") or "").strip()
    attachment = dict(payload.get("evidence_attachment") or {})
    attachment.setdefault("schema", PROMOTED_RENDER_RECEIPT_ATTACHMENT_SCHEMA)
    attachment.setdefault("attachment_kind", "station_render_promoted_receipt")
    attachment.setdefault("receipt_schema", promoted.get("schema"))
    attachment.setdefault("promotion_status", promoted.get("promotion_status"))
    attachment.setdefault("receipt_ref", receipt_ref)
    attachment.setdefault("receipt_path", receipt_path)
    attachment.setdefault("subject_id", args.subject_id)
    attachment.setdefault("promoted_receipt", promoted)
    payload["evidence_attachment"] = attachment
    payload.setdefault("receipt_refs", [receipt_ref] if receipt_ref else [])
    payload.setdefault("evidence_refs", [receipt_path] if receipt_path else [])
    note_text = _text_arg(args, "note")
    if note_text:
        payload.setdefault("note", note_text)
    source = dict(payload.get("source") or {})
    source.setdefault("kind", "task_ledger_apply.attach_promoted_render_receipt")
    source["refs"] = _append_unique_strings(
        list(source.get("refs") or []),
        [receipt_ref, receipt_path],
    )
    payload["source"] = source
    refs = dict(payload.get("refs") or {})
    refs["receipt_refs"] = _append_unique_strings(
        list(refs.get("receipt_refs") or []),
        [receipt_ref],
    )
    refs["evidence_refs"] = _append_unique_strings(
        list(refs.get("evidence_refs") or []),
        [receipt_path],
    )
    payload["refs"] = refs
    return payload


def _base_event(args: argparse.Namespace, *, event_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    event: Dict[str, Any] = {
        "event_id": args.event_id,
        "event_type": event_type,
        "created_at": args.created_at,
        "created_by": args.created_by,
        "agent_run_id": args.agent_run_id,
        "thread_id": args.thread_id,
        "subject_id": args.subject_id,
        "source": payload.pop("source", {"kind": "task_ledger_apply", "refs": []}),
        "refs": payload.pop("refs", {}),
        "payload": payload,
    }
    return {key: value for key, value in event.items() if value is not None}


def cmd_bootstrap_v0(args: argparse.Namespace) -> int:
    try:
        return _print(task_ledger_events.bootstrap_legacy_events(REPO_ROOT, created_by=args.created_by))
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.validate_event_log(REPO_ROOT)
        if not getattr(args, "allow_warnings", False):
            return _print(payload)
        error_count = int(payload.get("error_count") or 0)
        warning_only = (
            str(payload.get("validation_status") or "") == "valid_with_warnings"
            and error_count == 0
        )
        exit_code = 0 if payload.get("ok", True) or warning_only else 1
        payload = dict(payload)
        payload["exit_policy"] = {
            "mode": "allow_warnings",
            "process_exit_code": exit_code,
            "warning_only_exit_zero": warning_only,
            "payload_ok_preserved": True,
        }
        return _print_with_exit_code(payload, exit_code)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_rebuild(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.rebuild_projections(
                REPO_ROOT,
                check=bool(args.check),
                progress_callback=_progress_callback(args, "rebuild"),
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_authority_health(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.authority_health(
                REPO_ROOT,
                ids=_parse_ids_arg(args.ids),
                projection_check=bool(args.projection_check),
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_audit_recover(args: argparse.Namespace) -> int:
    try:
        if args.replay:
            result = task_ledger_events.replay_lost_audit_events(REPO_ROOT)
        else:
            lost = task_ledger_events.find_lost_audit_events(REPO_ROOT)
            result = {
                "ok": True,
                "lost_count": len(lost),
                "lost_event_ids": [str(row.get("event_id") or "") for row in lost],
                "next_step": (
                    "Run with --replay to re-append lost events through append_event."
                    if lost
                    else "events.jsonl already covers every audit-journal event."
                ),
                "authority_health": task_ledger_events.authority_health(REPO_ROOT),
            }
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_organizer_report(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.build_organizer_report(
                REPO_ROOT,
                transcript_file_limit=args.transcript_file_limit,
                detail=args.detail,
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_search(args: argparse.Namespace) -> int:
    try:
        query = str(_text_arg(args, "query") or "").strip()
        if not query:
            raise ValueError("search requires --query/--query-file/--query-stdin")
        limit = max(1, min(int(args.limit or 20), 100))
        projection, ledger_path = _load_task_ledger_projection()
        rows = projection.get("work_items")
        source_field = "work_items"
        if not isinstance(rows, list):
            rows = projection.get("tasks")
            source_field = "tasks"
        if not isinstance(rows, list):
            rows = []

        state_filters = {str(item).strip() for item in args.state if str(item).strip()}
        tag_filters = {str(item).strip().lower() for item in args.tag if str(item).strip()}
        tokens = _search_tokens(query)
        scored: list[tuple[float, Dict[str, Any], list[str]]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            if state_filters and str(row.get("state") or row.get("status") or "") not in state_filters:
                continue
            if tag_filters:
                row_tags = {tag.strip().lower() for tag in _string_list(row.get("tags"))}
                if not tag_filters.issubset(row_tags):
                    continue
            score, matched_tokens = _task_ledger_search_score(row, query, tokens)
            if score <= 0:
                continue
            scored.append((score, row, matched_tokens))

        scored.sort(
            key=lambda item: (
                -item[0],
                _row_rank_value(item[1]),
                str(item[1].get("updated_at") or ""),
                str(item[1].get("id") or ""),
            )
        )
        selected = scored[:limit]
        stat = ledger_path.stat()
        result = {
            "ok": True,
            "schema": TASK_LEDGER_SEARCH_SCHEMA,
            "query": query,
            "source": {
                "projection": str(task_ledger_events.LEDGER_REL),
                "source_field": source_field,
                "projection_generated_at": projection.get("generated_at"),
                "event_count": projection.get("event_count"),
                "ledger_mtime_ns": stat.st_mtime_ns,
                "rebuild_skipped": True,
            },
            "total_rows_scanned": len(rows),
            "match_count": len(scored),
            "limit": limit,
            "filters": {
                "state": sorted(state_filters),
                "tag": sorted(tag_filters),
            },
            "rows": [
                _compact_task_ledger_search_row(row, score=score, matched_tokens=matched_tokens)
                for score, row, matched_tokens in selected
            ],
            "drilldown_hint": "./repo-python kernel.py --option-surface task_ledger --band card --ids <id>",
        }
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def _slug_token(value: object, *, fallback: str = "note", limit: int = 48) -> str:
    text = str(value or "").strip().lower()
    chars: list[str] = []
    last_was_sep = False
    for char in text:
        if char.isalnum():
            chars.append(char)
            last_was_sep = False
        elif not last_was_sep:
            chars.append("_")
            last_was_sep = True
    token = "".join(chars).strip("_") or fallback
    return token[:limit].strip("_") or fallback


def _quick_capture_subject_id(title: str, statement: str) -> str:
    token = _slug_token(title or statement, fallback="note", limit=40)
    digest = hashlib.sha256(f"{title}\n{statement}".encode("utf-8")).hexdigest()[:12]
    return f"cap_quick_{token}_{digest}"


_PATHLIKE_SURFACE_SUFFIXES = {
    ".css",
    ".csv",
    ".html",
    ".js",
    ".json",
    ".jsonl",
    ".md",
    ".py",
    ".sh",
    ".sql",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}

_BARE_SURFACE_REF_PRUNE_DIR_NAMES = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "node_modules",
}

_BARE_SURFACE_REF_SEARCH_ROOTS = (
    Path("tools"),
    Path("system"),
    Path("codex/standards"),
    Path("codex/doctrine/paper_modules"),
    Path("codex/doctrine/skills"),
    Path(".agents/skills"),
    Path("docs"),
)

_PYTEST_SELECTOR_RE = re.compile(
    r"(?P<selector>(?P<surface>(?:(?:[\w.-]+/)+)?test[\w.-]*\.py)::"
    r"(?P<node>[A-Za-z_][\w]*(?:::[A-Za-z_][\w]*(?:\[[^\]\s]+\])?)*))"
)


def _surface_ref_looks_pathlike(surface: str) -> bool:
    value = str(surface or "").strip()
    if not value:
        return False
    path = Path(value)
    if path.is_absolute() or value.startswith(("./", "../", "~/")):
        return True
    if "/" in value or "\\" in value:
        return True
    return path.suffix in _PATHLIKE_SURFACE_SUFFIXES


def _bare_repo_surface_ref_matches(value: str) -> list[str]:
    path = Path(value)
    if (
        not value
        or path.name != value
        or path.is_absolute()
        or value.startswith(("./", "../", "~/"))
        or path.suffix not in _PATHLIKE_SURFACE_SUFFIXES
    ):
        return []

    matches: list[str] = []
    for search_root in _BARE_SURFACE_REF_SEARCH_ROOTS:
        root = REPO_ROOT / search_root
        if not root.is_dir():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            rel_dir = Path(dirpath).relative_to(REPO_ROOT)
            dirnames[:] = [
                dirname
                for dirname in dirnames
                if dirname not in _BARE_SURFACE_REF_PRUNE_DIR_NAMES
            ]

            if value not in filenames:
                continue
            matches.append((rel_dir / value).as_posix())
    return matches


def _quick_capture_surface_entry(surface: str) -> Dict[str, Any]:
    value = str(surface or "").strip()
    if _surface_ref_looks_pathlike(value):
        resolved_value = value
        exists = (REPO_ROOT / value).exists()
        if not exists:
            matches = _bare_repo_surface_ref_matches(value)
            if len(matches) == 1:
                resolved_value = matches[0]
                exists = True
            elif len(matches) > 1:
                return {
                    "path": value,
                    "surface_id": value,
                    "status": "implied",
                    "role": "quick_capture_ambiguous_surface_ref",
                    "evidence": {
                        "surface_kind": "ambiguous_bare_pathlike_surface_ref",
                        "filesystem_probe": "ambiguous",
                        "candidate_paths": matches,
                        "reason": (
                            "Bare filename matched multiple durable repo paths; pass an exact "
                            "--surface path to ground the receipt."
                        ),
                    },
                }
        return {
            "path": resolved_value,
            **({"surface_id": value} if resolved_value != value else {}),
            "status": "exists" if exists else "missing",
            "role": "quick_capture_surface_ref",
            "evidence": {
                "command": f"test -e {shlex.quote(resolved_value)}",
                "observed_result": "exists" if exists else "missing",
                **(
                    {
                        "surface_ref": value,
                        "resolution": "unique_bare_filename_match",
                    }
                    if resolved_value != value
                    else {}
                ),
            },
        }
    return {
        "path": value,
        "surface_id": value,
        "status": "implied",
        "role": "quick_capture_logical_surface_ref",
        "evidence": {
            "surface_kind": "logical_route_or_surface_id",
            "filesystem_probe": "skipped",
            "reason": "surface ref is not path-like; avoid false missing exact surface receipt",
        },
    }


def _quick_capture_pytest_selector_contract(text: str) -> Dict[str, Any]:
    value = str(text or "")
    if not value:
        return {}

    discovered: list[Dict[str, Any]] = []
    acceptance_checks: list[str] = []
    seen_selectors: set[str] = set()
    for match in _PYTEST_SELECTOR_RE.finditer(value):
        surface_ref = str(match.group("surface") or "").strip()
        selector_ref = str(match.group("selector") or "").strip()
        if not surface_ref or not selector_ref or selector_ref in seen_selectors:
            continue
        seen_selectors.add(selector_ref)

        resolved_surface = surface_ref
        resolved_selector = selector_ref
        exists = (REPO_ROOT / resolved_surface).exists()
        evidence: Dict[str, Any] = {
            "surface_kind": "pytest_selector",
            "selector_ref": selector_ref,
        }
        if not exists:
            matches = _bare_repo_surface_ref_matches(Path(surface_ref).name)
            if len(matches) == 1:
                resolved_surface = matches[0]
                resolved_selector = f"{resolved_surface}::{match.group('node')}"
                exists = True
                evidence["resolution"] = "unique_bare_filename_match"
            elif len(matches) > 1:
                evidence.update(
                    {
                        "filesystem_probe": "ambiguous",
                        "candidate_paths": matches,
                        "reason": (
                            "Embedded pytest selector used a bare filename with multiple "
                            "repo matches; pass --surface or an exact selector path."
                        ),
                    }
                )

        if exists:
            evidence.update(
                {
                    "command": f"test -e {shlex.quote(resolved_surface)}",
                    "observed_result": "exists",
                }
            )
            status = "exists"
        elif evidence.get("filesystem_probe") == "ambiguous":
            status = "implied"
        else:
            evidence.update(
                {
                    "command": f"test -e {shlex.quote(resolved_surface)}",
                    "observed_result": "missing",
                }
            )
            status = "missing"

        discovered.append(
            {
                "path": resolved_surface,
                **({"surface_id": surface_ref} if resolved_surface != surface_ref else {}),
                "status": status,
                "role": "quick_capture_pytest_selector_ref",
                "selector": resolved_selector,
                "evidence": evidence,
            }
        )
        acceptance_checks.append(f"./repo-pytest {shlex.quote(resolved_selector)} -q")

    if not discovered:
        return {}
    return {
        "satisfaction_contract": {
            "definition_of_done": [
                "Embedded pytest selector is validated or explicitly dispositioned before closeout."
            ]
        },
        "integration_contract": {
            "exact_surfaces_discovered": discovered,
            "acceptance_checks": acceptance_checks,
        },
    }


def cmd_quick_capture(args: argparse.Namespace) -> int:
    try:
        note_text = _text_arg(args, "note")
        statement_text = _text_arg(args, "statement")
        problem = str(_text_arg(args, "problem") or "").strip()
        impact = str(_text_arg(args, "impact") or "").strip()
        acceptance = str(_text_arg(args, "acceptance") or "").strip()
        evidence = [str(item).strip() for item in getattr(args, "evidence", []) if str(item).strip()]
        title = str(args.title or "").strip()
        statement = str(statement_text or note_text or problem or "").strip()
        if not title:
            title = statement[:80].strip() or "Quick capture"
        if not statement:
            statement = title
        payload = _load_payload(args)
        payload_title = str(payload.get("title") or "").strip()
        payload_statement = str(payload.get("statement") or "").strip()
        payload_subject_id = str(payload.pop("subject_id", "") or "").strip()
        if not args.title and payload_title:
            title = payload_title
        if not (statement_text or note_text or problem) and payload_statement:
            statement = payload_statement
        payload.setdefault("title", title)
        payload.setdefault("statement", statement)
        if problem:
            payload.setdefault("problem", problem)
        if impact:
            payload.setdefault("impact", impact)
        if acceptance:
            payload.setdefault("acceptance", acceptance)
        if evidence:
            payload.setdefault("evidence", evidence)
        payload.setdefault("work_item_type", "capture")
        if args.candidate_work_item_type:
            payload.setdefault("candidate_work_item_type", args.candidate_work_item_type)
        if args.confidence is not None:
            payload.setdefault("confidence", args.confidence)
        if args.tag:
            payload.setdefault("tags", args.tag)
        if args.depends_on:
            _validate_depends_on_args(args.depends_on, command="quick-capture")
            payload.setdefault("depends_on", args.depends_on)
        if args.dependency:
            payload.setdefault("dependencies", args.dependency)
        selector_contract = _quick_capture_pytest_selector_contract(
            "\n".join(part for part in [statement, problem, acceptance, note_text] if part)
        )
        if selector_contract:
            payload.setdefault("satisfaction_contract", selector_contract["satisfaction_contract"])
            integration = dict(payload.get("integration_contract") or {})
            discovered = list(integration.get("exact_surfaces_discovered") or [])
            for surface in selector_contract["integration_contract"].get(
                "exact_surfaces_discovered", []
            ):
                discovered.append(surface)
            integration["exact_surfaces_discovered"] = discovered
            checks = list(integration.get("acceptance_checks") or [])
            for check in selector_contract["integration_contract"].get("acceptance_checks", []):
                if check not in checks:
                    checks.append(check)
            integration["acceptance_checks"] = checks
            payload["integration_contract"] = integration
        if args.source_ref:
            refs = dict(payload.get("refs") or {})
            refs.setdefault("source_refs", args.source_ref)
            payload["refs"] = refs
            provenance = dict(payload.get("provenance") or {})
            provenance.setdefault("source_refs", args.source_ref)
            payload["provenance"] = provenance
        if args.surface:
            integration = dict(payload.get("integration_contract") or {})
            discovered = list(integration.get("exact_surfaces_discovered") or [])
            for surface in args.surface:
                discovered.append(_quick_capture_surface_entry(surface))
            integration["exact_surfaces_discovered"] = discovered
            payload["integration_contract"] = integration
        payload.setdefault("authority", {})
        authority = dict(payload.get("authority") or {})
        authority.setdefault("work_authority", str(task_ledger_events.EVENTS_REL))
        authority.setdefault("capture_mode", "quick_capture_low_ceremony")
        payload["authority"] = authority
        payload.setdefault("completion", {})
        completion = dict(payload.get("completion") or {})
        completion.setdefault(
            "closure_condition",
            "Capture is triaged, merged with an existing WorkItem, promoted, retired, or linked as evidence.",
        )
        if selector_contract:
            checks = list(completion.get("acceptance_checks") or [])
            for check in selector_contract["integration_contract"].get("acceptance_checks", []):
                if check not in checks:
                    checks.append(check)
            completion["acceptance_checks"] = checks
        completion.setdefault("signoff_required", False)
        payload["completion"] = completion
        payload.setdefault("provenance", {})
        provenance = dict(payload.get("provenance") or {})
        provenance.setdefault("source_kind", args.source_kind)
        provenance.setdefault("capture_affordance", "task_ledger_apply.quick_capture")
        payload["provenance"] = provenance

        source_refs = args.source_ref or []
        event_payload = dict(payload)
        event = _base_event(
            argparse.Namespace(
                event_id=args.event_id,
                created_at=args.created_at,
                created_by=args.created_by,
                agent_run_id=args.agent_run_id,
                thread_id=args.thread_id,
                subject_id=args.subject_id or payload_subject_id or _quick_capture_subject_id(title, statement),
            ),
            event_type=EVENT_BY_COMMAND["capture"],
            payload=event_payload,
        )
        if source_refs:
            event.setdefault("source", {"kind": args.source_kind, "refs": source_refs})
            event["source"] = {"kind": args.source_kind, "refs": source_refs}
        else:
            event.setdefault("source", {"kind": args.source_kind, "refs": []})
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=bool(args.rebuild),
            progress_callback=_progress_callback(args, "quick-capture") if args.rebuild else None,
        )
        projection_result = result.get("projection") if args.rebuild else None
        result["quick_capture"] = {
            "subject_id": event["subject_id"],
            "source_refs": source_refs,
            "next_action": "triage, merge, promote, retire, or leave as capture inbox material",
        }
        appended_event = result.get("event") if isinstance(result.get("event"), dict) else {}
        result["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(event["subject_id"])],
            event_ids=[str(appended_event.get("event_id") or event.get("event_id") or "")],
            projection_result=projection_result,
        )
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_event(args: argparse.Namespace) -> int:
    try:
        payload = _load_payload(args)
        if getattr(args, "depends_on", None):
            _validate_depends_on_args(args.depends_on, command=args.command_name)
            payload.setdefault("depends_on", args.depends_on)
        if getattr(args, "dependency", None):
            payload.setdefault("dependencies", args.dependency)
        if args.command_name == "capture":
            payload.setdefault("title", args.title)
            payload.setdefault("statement", _text_arg(args, "statement"))
            payload.setdefault("work_item_type", args.work_item_type)
            if args.confidence is not None:
                payload.setdefault("confidence", args.confidence)
        elif args.command_name == "note":
            payload.setdefault("note", _text_arg(args, "note"))
        elif args.command_name == "transition":
            payload.setdefault("state", args.state)
        elif args.command_name in {"block", "retire", "release"}:
            payload.setdefault("reason", _text_arg(args, "reason"))
        elif args.command_name in {"rerank-propose", "rerank-commit"}:
            payload.setdefault("rank", args.rank)
            payload.setdefault("justification", _text_arg(args, "justification"))
        elif args.command_name == "claim":
            payload.setdefault("owner", args.owner)
            execution = dict(payload.get("execution") or {})
            if args.route:
                execution.setdefault("route", args.route)
            if args.agent_run_id:
                execution.setdefault("agent_run_id", args.agent_run_id)
            if execution:
                payload["execution"] = execution
        elif args.command_name in {"execution-receipt", "record-execution-receipt"}:
            payload = _apply_execution_receipt_args(args, payload)
        _validate_command_payload(args.command_name, payload)
        receipt_reconcile: dict[str, Any] | None = None
        authority_mutation_checkpoint: dict[str, Any] | None = None
        if args.command_name in {"execution-receipt", "record-execution-receipt"}:
            receipt_reconcile = task_ledger_events.execution_receipt_reconcile_state(
                REPO_ROOT,
                subject_id=args.subject_id,
                receipt=payload.get("execution_receipt") if isinstance(payload.get("execution_receipt"), dict) else {},
            )
            reconcile_status = str(receipt_reconcile.get("status") or "")
            if reconcile_status == "receipt_already_recorded":
                result: dict[str, Any] = {
                    "ok": True,
                    "status": "receipt_already_recorded",
                    "receipt_reconcile": receipt_reconcile,
                }
                if args.rebuild:
                    result["projection"] = task_ledger_events.rebuild_projections(
                        REPO_ROOT,
                        progress_callback=_progress_callback(args, args.command_name),
                    )
                return _print(result)
            if not receipt_reconcile.get("ok", True):
                return _print(
                    {
                        "ok": False,
                        "status": reconcile_status or "receipt_reconcile_blocked",
                        "receipt_reconcile": receipt_reconcile,
                    }
                )
            authority_mutation_checkpoint = _execution_receipt_authority_mutation_checkpoint(args)
            if not authority_mutation_checkpoint.get("ok", True):
                return _print(
                    {
                        "ok": False,
                        "status": "task_ledger_authority_mutation_unanchored",
                        "error": (
                            "Task Ledger authority paths are dirty before a clean execution receipt closeout; "
                            "checkpoint, isolate, or residualize the authority delta before appending."
                        ),
                        "authority_mutation_checkpoint": authority_mutation_checkpoint,
                        "receipt_reconcile": receipt_reconcile,
                    }
                )
        event = _base_event(
            args,
            event_type=EVENT_BY_COMMAND[args.command_name],
            payload=payload,
        )
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=bool(args.rebuild),
            progress_callback=_progress_callback(args, args.command_name) if args.rebuild else None,
        )
        projection_result = result.get("projection") if args.rebuild else None
        if receipt_reconcile is not None:
            result["receipt_reconcile"] = receipt_reconcile
            result["receipt_reconcile_outcome"] = "receipt_recorded"
            if receipt_reconcile.get("alias_status"):
                result["receipt_reconcile_warning"] = receipt_reconcile.get("alias_status")
        appended_event = result.get("event") if isinstance(result.get("event"), dict) else {}
        if authority_mutation_checkpoint is not None:
            result["authority_mutation_checkpoint"] = {
                **authority_mutation_checkpoint,
                "event_id": str(appended_event.get("event_id") or event.get("event_id") or ""),
                "post_append_anchor_status": "scoped_commit_or_governed_state_settle_required",
            }
        result["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(args.subject_id)],
            event_ids=[str(appended_event.get("event_id") or event.get("event_id") or "")],
            projection_result=projection_result,
        )
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_attach_promoted_render_receipt(args: argparse.Namespace) -> int:
    try:
        payload = _promoted_render_evidence_payload(args)
        event = _base_event(
            args,
            event_type="work_item.evidence_attached",
            payload=payload,
        )
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=bool(args.rebuild),
            progress_callback=(
                _progress_callback(args, "attach-promoted-render-receipt")
                if args.rebuild
                else None
            ),
        )
        projection_result = result.get("projection") if args.rebuild else None
        appended_event = result.get("event") if isinstance(result.get("event"), dict) else {}
        attachment = event.get("payload", {}).get("evidence_attachment") if isinstance(event.get("payload"), dict) else {}
        result["promoted_receipt_attachment"] = {
            "subject_id": args.subject_id,
            "receipt_ref": attachment.get("receipt_ref") if isinstance(attachment, dict) else args.receipt_ref,
            "receipt_path": attachment.get("receipt_path") if isinstance(attachment, dict) else None,
            "attachment_kind": (
                attachment.get("attachment_kind") if isinstance(attachment, dict) else None
            ),
        }
        result["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(args.subject_id)],
            event_ids=[str(appended_event.get("event_id") or event.get("event_id") or "")],
            projection_result=projection_result,
        )
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


_BATCH_ALLOWED_COMMANDS = {
    "note",
    "promote",
    "rerank-commit",
    "rerank-propose",
    "claim",
    "release",
    "transition",
    "block",
    "unblock",
    "shape",
    "triage",
    "sign-off",
    "execution-receipt",
    "record-execution-receipt",
    "propagate",
    "retire",
    "capture",
}


def cmd_batch(args: argparse.Namespace) -> int:
    """Append a batch of WorkItem events from a single payload file, run one rebuild at the end."""
    try:
        if not args.payload_file:
            raise ValueError("--payload-file is required for batch")
        manifest = json.loads(Path(args.payload_file).read_text(encoding="utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("--payload-file must decode to an object with an 'events' list")
        events_in = manifest.get("events")
        if not isinstance(events_in, list) or not events_in:
            raise ValueError("manifest 'events' must be a non-empty list")
        rebuild_at_end = bool(manifest.get("rebuild", True))
        print_top = int(manifest.get("print_execution_menu_top", 0) or 0)
        default_created_by = str(manifest.get("created_by") or args.created_by or "claude_code")

        # Validate all events first.
        for idx, ev in enumerate(events_in):
            if not isinstance(ev, dict):
                raise ValueError(f"events[{idx}] must be an object")
            command = str(ev.get("command") or "").strip()
            if command not in _BATCH_ALLOWED_COMMANDS:
                raise ValueError(f"events[{idx}].command={command!r} not allowed in batch (allowed: {sorted(_BATCH_ALLOWED_COMMANDS)})")
            if not str(ev.get("subject_id") or "").strip():
                raise ValueError(f"events[{idx}] missing subject_id")

        append_requests: list[dict[str, Any]] = []
        for idx, ev in enumerate(events_in):
            command = str(ev["command"]).strip()
            subject_id = str(ev["subject_id"]).strip()
            payload = dict(ev.get("payload") or {})
            # Map convenience fields to payload defaults (mirrors cmd_event).
            if command == "note":
                if ev.get("note") is not None:
                    payload.setdefault("note", ev["note"])
            elif command == "transition":
                if ev.get("state") is not None:
                    payload.setdefault("state", ev["state"])
            elif command in {"block", "retire", "release"}:
                if ev.get("reason") is not None:
                    payload.setdefault("reason", ev["reason"])
            elif command in {"rerank-propose", "rerank-commit"}:
                if ev.get("rank") is not None:
                    payload.setdefault("rank", ev["rank"])
                if ev.get("justification") is not None:
                    payload.setdefault("justification", ev["justification"])
            elif command == "claim":
                if ev.get("owner") is not None:
                    payload.setdefault("owner", ev["owner"])
                if ev.get("route") is not None:
                    execution = dict(payload.get("execution") or {})
                    execution.setdefault("route", ev["route"])
                    payload["execution"] = execution
            elif command == "capture":
                if ev.get("title") is not None:
                    payload.setdefault("title", ev["title"])
                if ev.get("statement") is not None:
                    payload.setdefault("statement", ev["statement"])
                if ev.get("work_item_type") is not None:
                    payload.setdefault("work_item_type", ev["work_item_type"])
                if ev.get("confidence") is not None:
                    payload.setdefault("confidence", ev["confidence"])

            _validate_command_payload(command, payload)
            event = {
                "event_id": ev.get("event_id"),
                "event_type": EVENT_BY_COMMAND[command],
                "created_at": ev.get("created_at"),
                "created_by": str(ev.get("created_by") or default_created_by),
                "agent_run_id": ev.get("agent_run_id"),
                "thread_id": ev.get("thread_id"),
                "subject_id": subject_id,
                "source": payload.pop("source", {"kind": "task_ledger_apply", "refs": []}),
                "refs": payload.pop("refs", {}),
                "payload": payload,
            }
            event = {k: v for k, v in event.items() if v is not None}
            append_requests.append(
                {
                    "index": idx,
                    "command": command,
                    "subject_id": subject_id,
                    "event": event,
                }
            )

        batch_append = task_ledger_events.append_events_and_rebuild(
            REPO_ROOT,
            [row["event"] for row in append_requests],
            rebuild=rebuild_at_end,
            progress_callback=_progress_callback(args, "batch") if rebuild_at_end else None,
        )
        append_results = batch_append.get("append_results") if isinstance(batch_append.get("append_results"), list) else []
        appended: list[dict] = []
        for request, result in zip(append_requests, append_results):
            appended_event = result.get("event") if isinstance(result.get("event"), dict) else {}
            appended.append({
                "index": request["index"],
                "command": request["command"],
                "subject_id": request["subject_id"],
                "event_id": appended_event.get("event_id") or request["event"].get("event_id"),
                "status": result.get("status"),
                "ok": result.get("ok", True),
            })

        out: dict = {"ok": True, "appended_count": len(appended), "events": appended}
        projection_result = batch_append.get("projection") if rebuild_at_end else None
        if projection_result is not None:
            out["projection"] = projection_result
        out["task_ledger_mutation_serialization"] = batch_append.get("task_ledger_mutation_serialization")
        out["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(row.get("subject_id") or "") for row in appended],
            event_ids=[str(row.get("event_id") or "") for row in appended],
            projection_result=projection_result,
        )
        if print_top > 0:
            menu_path = REPO_ROOT / "state" / "task_ledger" / "views" / "execution_menu.json"
            if menu_path.exists():
                menu = json.loads(menu_path.read_text(encoding="utf-8"))
                items = (menu.get("items") or [])[:print_top]
                out["execution_menu_top"] = [
                    {"menu_rank": i.get("menu_rank"), "rank": i.get("rank"), "state": i.get("state"), "owner": i.get("owner"), "id": i.get("id")}
                    for i in items
                ]
        return _print(out)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_enqueue_execution_receipt(args: argparse.Namespace) -> int:
    try:
        payload = _apply_execution_receipt_args(args, _load_payload(args))
        refs = dict(payload.pop("refs", {}) or {})
        source = payload.pop("source", {"kind": "task_ledger_intake", "refs": []})
        request = {
            "request_id": args.request_id,
            "kind": "execution_receipt",
            "event_type": "work_item.execution_receipt_recorded",
            "subject_id": args.subject_id,
            "created_at": args.created_at,
            "created_by": args.created_by,
            "agent_run_id": args.agent_run_id,
            "thread_id": args.thread_id,
            "source": source,
            "refs": refs,
            "payload": payload,
        }
        return _print(
            task_ledger_events.enqueue_task_ledger_intake_request(
                REPO_ROOT,
                request,
                replace_pending=bool(args.replace_pending),
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_drain_intake(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.drain_task_ledger_intake(
                REPO_ROOT,
                limit=args.limit,
                created_by=args.created_by,
                rebuild=not bool(args.no_rebuild),
                request_ids=args.request_id,
                idempotency_keys=args.idempotency_key,
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_intake_status(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.task_ledger_intake_status(
                REPO_ROOT,
                request_ids=args.request_id,
                idempotency_keys=args.idempotency_key,
            )
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def _shell_join(parts: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in parts)


def _extend_arg(parts: list[str], flag: str, value: object | None) -> None:
    text = str(value or "").strip()
    if text:
        parts.extend([flag, text])


def _first_text(values: list[str]) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _work_ledger_resolution_command_args(args: argparse.Namespace) -> tuple[str, str, str]:
    commit_ref = _first_text(args.commit_ref)
    if commit_ref:
        return "git_commit", commit_ref, "Task Ledger closeout commit"

    receipt_ref = _first_text(args.receipt_ref)
    if receipt_ref:
        return "artifact", receipt_ref, "Task Ledger closeout receipt"

    evidence_ref = _first_text(args.evidence_ref)
    if evidence_ref:
        return "artifact", evidence_ref, "Task Ledger closeout evidence"

    return "session", str(args.work_ledger_session_id), "Task Ledger closeout session"


def _work_ledger_receipt_runtime_state(args: argparse.Namespace) -> dict[str, Any]:
    session_id = str(args.work_ledger_session_id or "").strip()
    read_receipt_id = str(args.read_receipt_id or "").strip()
    if not (session_id and read_receipt_id):
        return {"status": "not_requested"}

    try:
        status = work_ledger_runtime.load_runtime_status(REPO_ROOT)
    except Exception as exc:
        return {"status": "unknown", "reason": str(exc)}

    for key, session in (status.get("sessions") or {}).items():
        if str(session.get("read_receipt_id") or "").strip() != read_receipt_id:
            continue
        if str(key) != session_id:
            return {
                "status": "invalid",
                "reason": "read_receipt_id does not match actor_session_id",
                "actual_session_id": str(key),
            }
        ended_at = str(session.get("ended_at") or "").strip()
        if ended_at:
            return {
                "status": "ended",
                "reason": "read_receipt_id belongs to an ended session",
                "ended_at": ended_at,
            }
        return {"status": "active"}

    return {"status": "unknown", "reason": "read_receipt_id not found in runtime_status"}


def _supplemental_work_ledger_session_command(
    args: argparse.Namespace,
    *,
    work_item_id: str,
    receipt_state: dict[str, Any],
) -> str:
    session_id = str(args.work_ledger_session_id or "").strip()
    supplemental_session_id = f"{session_id}_closeout" if session_id else f"closeout_{work_item_id}"
    note_reason = str(receipt_state.get("reason") or "original read receipt is not live")
    parts = [
        "./repo-python",
        "tools/meta/factory/work_ledger.py",
        "session-preflight",
        "--session-id",
        supplemental_session_id,
    ]
    _extend_arg(parts, "--actor", args.created_by)
    _extend_arg(parts, "--phase-id", args.phase_id)
    _extend_arg(parts, "--family-id", args.family_id)
    _extend_arg(parts, "--td-id", work_item_id)
    parts.extend(["--lease-minutes", "30"])
    _extend_arg(
        parts,
        "--note",
        f"Supplemental Work Ledger receipt for Task Ledger closeout: {note_reason}.",
    )
    return _shell_join(parts)


def _work_ledger_receipt_command(
    args: argparse.Namespace,
    *,
    work_item_id: str,
    signoff_id: str,
) -> tuple[str | None, str | None, str | None, dict[str, Any]]:
    if not (args.work_ledger_session_id and args.read_receipt_id):
        return None, None, None, {"status": "not_requested"}

    receipt_state = _work_ledger_receipt_runtime_state(args)
    if receipt_state.get("status") in {"ended", "invalid"}:
        command = _supplemental_work_ledger_session_command(
            args,
            work_item_id=work_item_id,
            receipt_state=receipt_state,
        )
        return command, command, "supplemental_receipt_session_required", receipt_state

    target_id = str(args.work_ledger_td_id or "").strip()
    evidence_refs = args.commit_ref + args.evidence_ref
    if work_ledger.TD_ID_RE.fullmatch(target_id):
        resolution_kind, resolution_ref, resolution_label = _work_ledger_resolution_command_args(args)
        close_parts = [
            "./repo-python",
            "tools/meta/factory/work_ledger.py",
            "close",
            "--td-id",
            target_id,
        ]
        _extend_arg(close_parts, "--actor", args.created_by)
        _extend_arg(close_parts, "--actor-session-id", args.work_ledger_session_id)
        _extend_arg(close_parts, "--phase-id", args.phase_id)
        _extend_arg(close_parts, "--family-id", args.family_id)
        _extend_arg(close_parts, "--read-receipt-id", args.read_receipt_id)
        _extend_arg(close_parts, "--body", args.summary)
        _extend_arg(close_parts, "--resolution-kind", resolution_kind)
        _extend_arg(close_parts, "--resolution-ref", resolution_ref)
        _extend_arg(close_parts, "--resolution-label", resolution_label)
        for ref in evidence_refs:
            _extend_arg(close_parts, "--evidence-ref", ref)
        return _shell_join(close_parts), _shell_join(close_parts), "close_thread", receipt_state

    receipt_target_id = target_id or work_item_id
    metadata = {
        "receipt_mode": "task_ledger_work_item_closeout",
        "task_ledger_work_item_id": work_item_id,
        "task_ledger_signoff_id": signoff_id,
        "requested_work_ledger_td_id": target_id or None,
        "receipt_target_id": receipt_target_id,
        "reason": "missing_work_ledger_td_id_requires_append_receipt"
        if not target_id
        else "non_td_work_item_id_requires_append_receipt",
    }
    receipt_parts = [
        "./repo-python",
        "tools/meta/factory/work_ledger.py",
        "append-open",
    ]
    _extend_arg(receipt_parts, "--actor", args.created_by)
    _extend_arg(receipt_parts, "--actor-session-id", args.work_ledger_session_id)
    _extend_arg(receipt_parts, "--phase-id", args.phase_id)
    _extend_arg(receipt_parts, "--family-id", args.family_id)
    _extend_arg(receipt_parts, "--read-receipt-id", args.read_receipt_id)
    _extend_arg(receipt_parts, "--title", f"Task Ledger closeout receipt: {work_item_id}")
    _extend_arg(receipt_parts, "--body", args.summary)
    _extend_arg(receipt_parts, "--metadata-json", json.dumps(metadata, sort_keys=True))
    for ref in evidence_refs:
        _extend_arg(receipt_parts, "--evidence-ref", ref)
    command = _shell_join(receipt_parts)
    return command, command, "append_receipt", receipt_state


def cmd_closeout_slice(args: argparse.Namespace) -> int:
    try:
        work_item_id = str(args.work_item_id).strip()
        if not work_item_id:
            raise ValueError("--work-item-id is required")
        result = str(args.result).strip()
        now = args.created_at or task_ledger_events.utc_now()
        signoff_id = args.signoff_id or f"signoff_{work_item_id}_{now.replace('+00:00', 'Z').replace('-', '').replace(':', '')}"
        signoff = {
            "id": signoff_id,
            "work_item_id": work_item_id,
            "result": result,
            "signed_off_at": now,
            "signed_off_by": args.created_by,
            "outcome_summary": args.summary,
            "definition_of_done_result": {
                "status": args.definition_of_done_status,
                "summary": args.definition_of_done_summary or args.summary,
            },
            "acceptance_checks_result": {
                "status": args.acceptance_status,
                "commands": args.acceptance_command,
            },
            "evidence_refs": args.evidence_ref,
            "commit_refs": args.commit_ref,
            "receipt_refs": args.receipt_ref,
            "lessons_propagated": args.lesson_propagated,
            "propagation_targets": args.propagation_target,
            "followup_captures_filed": args.followup_capture,
            "raw_seed_effects": getattr(args, "raw_seed_effect", []),
            "synth_seed_effects": getattr(args, "synth_seed_effect", []),
            "principle_axiom_effects": getattr(args, "principle_axiom_effect", []),
            "surfaces_updated": args.surface_updated,
            "concurrency_closure": {
                "work_ledger_session_id": args.work_ledger_session_id,
                "work_ledger_td_id": args.work_ledger_td_id,
                "read_receipt_id": args.read_receipt_id,
                "closeout_appended_before_finalize": bool(args.work_ledger_session_id and args.read_receipt_id),
                "claims_released": bool(args.claims_released),
                "session_finalize_after_closeout_required": bool(args.work_ledger_session_id),
            },
            "rank_board_impact": {
                "previous_capture_may_leave_capture_inbox": True,
            },
            "no_orphan_closeout_result": {
                "status": "residuals_filed" if args.followup_capture else "no_residuals_reported",
            },
        }
        payload = {
            "state": args.state,
            "signoff": signoff,
            "source": {"kind": "task_ledger_apply.closeout_slice", "refs": []},
            "refs": {
                "commit_refs": args.commit_ref,
                "receipt_refs": args.receipt_ref,
                "work_ledger_refs": [
                    ref
                    for ref in [
                        args.work_ledger_session_id,
                        args.work_ledger_td_id,
                        args.read_receipt_id,
                    ]
                    if ref
                ],
            },
        }
        event = {
            "event_id": args.event_id,
            "event_type": "work_item.signoff_recorded",
            "created_at": now,
            "created_by": args.created_by,
            "agent_run_id": args.agent_run_id,
            "thread_id": args.thread_id,
            "subject_id": work_item_id,
            "source": payload.pop("source"),
            "refs": payload.pop("refs"),
            "payload": payload,
        }
        event = {key: value for key, value in event.items() if value is not None}
        append = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=True,
            progress_callback=_progress_callback(args, "closeout-slice"),
        )
        rebuild = append.get("projection")
        validation = task_ledger_events.validate_event_log(REPO_ROOT) if args.validate else None

        work_ledger_close_command = None
        work_ledger_receipt_command = None
        work_ledger_command_kind = None
        work_ledger_receipt_status = {"status": "not_requested"}
        finalize_command = None
        if args.work_ledger_session_id and args.read_receipt_id:
            finalize_command = _shell_join(
                [
                    "./repo-python",
                    "tools/meta/factory/work_ledger.py",
                    "session-finalize",
                    "--session-id",
                    args.work_ledger_session_id,
                    "--action",
                    "codex-turn-end",
                ]
            )
            (
                work_ledger_close_command,
                work_ledger_receipt_command,
                work_ledger_command_kind,
                work_ledger_receipt_status,
            ) = _work_ledger_receipt_command(args, work_item_id=work_item_id, signoff_id=signoff_id)
        return _print(
            {
                "ok": True,
                "append": append,
                "projection": rebuild,
                "validation": validation,
                "visibility_receipt": _visibility_receipt(
                    subject_ids=[work_item_id],
                    event_ids=[
                        str(
                            (append.get("event") if isinstance(append.get("event"), dict) else {}).get("event_id")
                            or event.get("event_id")
                            or ""
                        )
                    ],
                    projection_result=rebuild,
                ),
                "work_ledger_close_command": work_ledger_close_command,
                "work_ledger_receipt_command": work_ledger_receipt_command,
                "work_ledger_command_kind": work_ledger_command_kind,
                "work_ledger_receipt_status": work_ledger_receipt_status,
                "session_finalize_command": finalize_command,
            }
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def _add_common_event_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--subject-id", required=True)
    parser.add_argument(
        "--payload-json",
        default=None,
        help=(
            "Inline JSON object. For prose-heavy payloads, prefer --payload-file "
            "or --payload-stdin to avoid shell command-substitution corruption."
        ),
    )
    parser.add_argument(
        "--payload-file",
        default=None,
        help=(
            "Read a UTF-8 JSON object from a file; useful for rich text with quotes, "
            "backticks, or parentheses. Use one unique file path per concurrent command."
        ),
    )
    parser.add_argument(
        "--payload-stdin",
        action="store_true",
        help=(
            "Read a UTF-8 JSON object from stdin; useful for heredocs, generated payloads, "
            "and avoiding shared temp-file races."
        ),
    )
    parser.add_argument("--event-id", default=None)
    parser.add_argument("--created-at", default=None)
    parser.add_argument("--created-by", default="codex")
    parser.add_argument("--agent-run-id", default=None)
    parser.add_argument("--thread-id", default=None)
    parser.add_argument("--expected-previous-event-hash", default=None)
    parser.add_argument("--rebuild", action="store_true")
    parser.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during --rebuild phases.",
    )
    parser.add_argument(
        "--depends-on",
        action="append",
        default=[],
        help="Hard internal WorkItem prerequisite id; may be repeated.",
    )
    parser.add_argument(
        "--dependency",
        action="append",
        default=[],
        help="Broad dependency/context ref, not scheduler authority; may be repeated.",
    )


def _add_text_input_args(
    parser: argparse.ArgumentParser,
    name: str,
    *,
    required: bool = False,
    help_text: str | None = None,
) -> None:
    option = name.replace("_", "-")
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(
        f"--{option}",
        dest=name,
        default=None,
        help=help_text or f"Inline {option} text.",
    )
    group.add_argument(
        f"--{option}-file",
        dest=f"{name}_file",
        default=None,
        help=(
            f"Read {option} text from a UTF-8 file. Use this for prose with "
            "quotes, backticks, parentheses, or shell-sensitive tokens. Use one "
            "unique file path per concurrent command."
        ),
    )
    group.add_argument(
        f"--{option}-stdin",
        dest=f"{name}_stdin",
        action="store_true",
        help=(
            f"Read {option} text from stdin (UTF-8). Use this with heredocs "
            "to avoid shell interpolation and shared temp-file races."
        ),
    )


def _add_execution_receipt_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--work-ledger-session-id", default=None)
    parser.add_argument("--read-receipt-id", default=None)
    parser.add_argument("--commit-hash", default=None)
    parser.add_argument("--read-set-hash", default=None)
    parser.add_argument("--write-set-hash", default=None)
    parser.add_argument("--validation-ref", action="append", default=[])
    parser.add_argument("--projection-ref", action="append", default=[])
    parser.add_argument("--closeout-state", default="recorded")
    parser.add_argument("--no-commit-reason", default=None)
    parser.add_argument("--commit-blocker-ref", action="append", default=[])
    parser.add_argument("--receipt-schema", default="transaction_receipt_v0")
    parser.add_argument(
        "--mission-closeout-report-json",
        default=None,
        help=(
            "Inline mission explore/execute/review closeout JSON. When it contains "
            "review.blocked_primary_continuation, record-execution-receipt carries "
            "that safe metadata into Task Ledger closeout_assurance."
        ),
    )
    parser.add_argument(
        "--mission-closeout-report-file",
        default=None,
        help=(
            "Read a mission explore/execute/review closeout JSON object from a UTF-8 file "
            "and carry review.blocked_primary_continuation into closeout_assurance."
        ),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = TaskLedgerArgumentParser(
        description="Append Task Ledger WorkItem events.",
        epilog=_TASK_LEDGER_PARALLEL_SAFETY_NOTE,
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
        parser_class=TaskLedgerArgumentParser,
    )

    bootstrap = subparsers.add_parser("bootstrap-v0", help="Bootstrap legacy ledger rows into events.")
    bootstrap.add_argument("--created-by", default="codex")
    bootstrap.set_defaults(func=cmd_bootstrap_v0)

    quick = subparsers.add_parser(
        "quick-capture",
        help="Low-friction todo capture for noticed side work; appends a normal work_item.captured event.",
        epilog=_TASK_LEDGER_PARALLEL_SAFETY_NOTE,
    )
    quick.add_argument("--title", required=False)
    _add_text_input_args(quick, "statement", help_text="Inline statement text.")
    _add_text_input_args(quick, "note", help_text="Inline note text.")
    _add_text_input_args(quick, "problem", help_text="Inline problem text.")
    _add_text_input_args(quick, "impact", help_text="Inline impact text.")
    _add_text_input_args(quick, "acceptance", help_text="Inline acceptance text.")
    quick.add_argument("--evidence", action="append", default=[])
    quick.add_argument("--subject-id", default=None)
    quick.add_argument("--candidate-work-item-type", default=None)
    quick.add_argument("--source-ref", action="append", default=[])
    quick.add_argument("--source-kind", default="quick_capture")
    quick.add_argument("--surface", action="append", default=[])
    quick.add_argument("--tag", action="append", default=[])
    quick.add_argument("--depends-on", action="append", default=[])
    quick.add_argument("--dependency", action="append", default=[])
    quick.add_argument("--confidence", type=float, default=None)
    quick.add_argument(
        "--payload-json",
        default=None,
        help=(
            "Inline JSON object. For prose-heavy payloads, prefer --payload-file "
            "or --payload-stdin to avoid shell command-substitution corruption."
        ),
    )
    quick.add_argument(
        "--payload-file",
        default=None,
        help=(
            "Read a UTF-8 JSON object from a file; useful for rich text with quotes, "
            "backticks, or parentheses. Use one unique file path per concurrent command."
        ),
    )
    quick.add_argument(
        "--payload-stdin",
        action="store_true",
        help=(
            "Read a UTF-8 JSON object from stdin; useful for heredocs, generated payloads, "
            "and avoiding shared temp-file races."
        ),
    )
    quick.add_argument("--event-id", default=None)
    quick.add_argument("--created-at", default=None)
    quick.add_argument("--created-by", default="codex")
    quick.add_argument("--agent-run-id", default=None)
    quick.add_argument("--thread-id", default=None)
    quick.add_argument("--expected-previous-event-hash", default=None)
    quick.add_argument("--rebuild", action="store_true")
    quick.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during --rebuild phases.",
    )
    quick.set_defaults(func=cmd_quick_capture)

    for name in EVENT_BY_COMMAND:
        parser_kwargs: Dict[str, Any] = {"help": f"Append {EVENT_BY_COMMAND[name]}."}
        if name == "propagate":
            parser_kwargs.update(
                {
                    "formatter_class": argparse.RawDescriptionHelpFormatter,
                    "epilog": (
                        "Required payload shape:\n"
                        "  --payload-json '{\"propagation\":{\"status\":\"recorded\","
                        "\"classification\":\"already_propagated_verified | nothing_to_refine | propagation_debt\","
                        "\"targets\":[],\"lesson\":\"<lesson or rationale>\","
                        "\"nothing_to_refine\":false}}'"
                    ),
                }
            )
        elif name == "shape":
            parser_kwargs.update(
                {
                    "formatter_class": argparse.RawDescriptionHelpFormatter,
                    "epilog": (
                        "Preferred payload shape:\n"
                        "  --payload-file /tmp/task-ledger-shape.json\n\n"
                        "task-ledger-shape.json:\n"
                        "  {\"title\":\"<refined title>\","
                        "\"candidate_work_item_type\":\"<task | substrate_fix | owner_surface_patch>\","
                        "\"satisfaction_contract\":{\"definition_of_done\":[\"<observable done condition>\"]},"
                        "\"integration_contract\":{\"exact_surfaces_discovered\":[{\"path\":\"<repo path>\",\"status\":\"exists\"}],"
                        "\"acceptance_checks\":[\"<validation command>\"]}}\n\n"
                        "Legacy compatibility: a payload with contracts.satisfaction_refs, "
                        "contracts.integration_paths, contracts.acceptance_checks, depends_on, or dependencies "
                        "is also projected into satisfaction_contract, integration_contract, and dependencies."
                    ),
                }
            )
        event_parser = subparsers.add_parser(name, **parser_kwargs)
        _add_common_event_args(event_parser)
        event_parser.set_defaults(func=cmd_event, command_name=name)
        if name == "capture":
            event_parser.add_argument("--title", default=None)
            _add_text_input_args(event_parser, "statement", help_text="Inline statement text.")
            event_parser.add_argument("--work-item-type", default="capture")
            event_parser.add_argument("--confidence", type=float, default=None)
        elif name == "note":
            _add_text_input_args(event_parser, "note", help_text="Inline note text.")
        elif name == "transition":
            event_parser.add_argument("--state", required=False)
        elif name in {"block", "retire", "release"}:
            _add_text_input_args(event_parser, "reason", help_text="Inline reason text.")
        elif name in {"rerank-propose", "rerank-commit"}:
            event_parser.add_argument("--rank", type=int, default=None)
            _add_text_input_args(event_parser, "justification", help_text="Inline justification text.")
        elif name == "claim":
            event_parser.add_argument("--owner", default=None)
            event_parser.add_argument("--route", default=None)
        elif name in {"execution-receipt", "record-execution-receipt"}:
            _add_execution_receipt_args(event_parser)

    attach_promoted = subparsers.add_parser(
        "attach-promoted-render-receipt",
        help=(
            "Attach a promoted station-render receipt as structured WorkItem evidence "
            "without flattening it into note prose."
        ),
    )
    _add_common_event_args(attach_promoted)
    attach_promoted.add_argument("--receipt-ref", required=True)
    attach_promoted.add_argument(
        "--receipt-path",
        default=None,
        help="Per-run manifest path; defaults from the run stamp in --receipt-ref.",
    )
    attach_promoted.add_argument(
        "--promotion-status",
        default="promoted_evidence",
        choices=station_render.PROMOTED_RENDER_RECEIPT_STATUSES,
    )
    attach_promoted.add_argument("--consumer", default="task_ledger")
    _add_text_input_args(
        attach_promoted,
        "note",
        help_text="Optional note text stored alongside the structured evidence attachment.",
    )
    attach_promoted.set_defaults(func=cmd_attach_promoted_render_receipt)

    validate = subparsers.add_parser("validate", help="Validate event log and projection invariants.")
    validate.add_argument(
        "--allow-warnings",
        action="store_true",
        help=(
            "Return process exit 0 for valid_with_warnings when error_count is 0. "
            "The payload ok field is preserved for callers that need strict semantics."
        ),
    )
    validate.set_defaults(func=cmd_validate)

    rebuild = subparsers.add_parser("rebuild", help="Rebuild deterministic projections.")
    rebuild.add_argument("--check", action="store_true")
    rebuild.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during rebuild phases.",
    )
    rebuild.set_defaults(func=cmd_rebuild)

    authority_health = subparsers.add_parser(
        "authority-health",
        help="Report whether events_audit.jsonl contains events missing from events.jsonl.",
    )
    authority_health.add_argument("--ids", default=None, help="Optional comma/space-separated WorkItem ids to check for card visibility.")
    authority_health.add_argument("--projection-check", action="store_true", help="Also check whether deterministic projections match events.jsonl.")
    authority_health.set_defaults(func=cmd_authority_health)

    audit_recover = subparsers.add_parser(
        "audit-recover",
        help="Detect events lost from events.jsonl by git operations using the unstaged audit journal; replay with --replay.",
    )
    audit_recover.add_argument(
        "--replay",
        action="store_true",
        help="Re-append every audit-journal event missing from events.jsonl through append_event.",
    )
    audit_recover.set_defaults(func=cmd_audit_recover)

    organizer = subparsers.add_parser(
        "organizer-report",
        help="Read-only organizer health, classifier, propagation, and possible adapter-leak report.",
    )
    organizer.add_argument(
        "--transcript-file-limit",
        type=int,
        default=8,
        help="Recent Claude transcript files to scan for possible adapter leak signals.",
    )
    organizer.add_argument(
        "--detail",
        choices=("compact", "full"),
        default="compact",
        help="Use compact first-read output by default; use full for complete samples and adapter audit examples.",
    )
    organizer.set_defaults(func=cmd_organizer_report)

    search = subparsers.add_parser(
        "search",
        help="Read-only Task Ledger projection search; no event append, projection rebuild, or repo scan.",
        epilog=_TASK_LEDGER_PARALLEL_SAFETY_NOTE,
    )
    _add_text_input_args(
        search,
        "query",
        required=True,
        help_text="Inline text or WorkItem id fragment to search in projected WorkItems.",
    )
    search.add_argument("--limit", type=int, default=20, help="Maximum compact rows to emit, capped at 100.")
    search.add_argument("--state", action="append", default=[], help="Optional state/status filter. Repeatable.")
    search.add_argument("--tag", action="append", default=[], help="Optional tag filter. Repeatable; all tags must match.")
    search.set_defaults(func=cmd_search)

    closeout = subparsers.add_parser(
        "closeout-slice",
        help="Record a WorkItem sign-off and print Work Ledger close/finalize commands.",
    )
    closeout.add_argument("--work-item-id", required=True)
    closeout.add_argument(
        "--result",
        default="accepted_with_residuals",
        choices=[
            "accepted",
            "accepted_with_residuals",
            "rejected",
            "blocked_pending_operator",
            "propagated_no_local_change",
            "retired_duplicate",
            "retired_obsolete",
        ],
    )
    closeout.add_argument("--state", default="done")
    closeout.add_argument("--summary", required=True)
    closeout.add_argument("--signoff-id", default=None)
    closeout.add_argument("--event-id", default=None)
    closeout.add_argument("--created-at", default=None)
    closeout.add_argument("--created-by", default="codex")
    closeout.add_argument("--agent-run-id", default=None)
    closeout.add_argument("--thread-id", default=None)
    closeout.add_argument("--expected-previous-event-hash", default=None)
    closeout.add_argument("--definition-of-done-status", default="passed")
    closeout.add_argument("--definition-of-done-summary", default=None)
    closeout.add_argument("--acceptance-status", default="passed")
    closeout.add_argument("--acceptance-command", action="append", default=[])
    closeout.add_argument("--evidence-ref", action="append", default=[])
    closeout.add_argument("--commit-ref", action="append", default=[])
    closeout.add_argument("--receipt-ref", action="append", default=[])
    closeout.add_argument("--lesson-propagated", action="append", default=[])
    closeout.add_argument("--propagation-target", action="append", default=[])
    closeout.add_argument("--followup-capture", action="append", default=[])
    closeout.add_argument("--raw-seed-effect", action="append", default=[])
    closeout.add_argument("--synth-seed-effect", action="append", default=[])
    closeout.add_argument(
        "--synth-seed-delta-ref",
        action="append",
        dest="synth_seed_effect",
        default=[],
        help="Alias for --synth-seed-effect when the sign-off captured or applied a typed synth_seed_delta receipt.",
    )
    closeout.add_argument("--principle-axiom-effect", action="append", default=[])
    closeout.add_argument("--surface-updated", action="append", default=[])
    closeout.add_argument("--work-ledger-session-id", default=None)
    closeout.add_argument("--work-ledger-td-id", default=None)
    closeout.add_argument("--read-receipt-id", default=None)
    closeout.add_argument("--phase-id", default=None)
    closeout.add_argument("--family-id", default=None)
    closeout.add_argument("--claims-released", action="store_true")
    closeout.add_argument("--validate", action="store_true", default=True)
    closeout.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during Task Ledger rebuild.",
    )
    closeout.set_defaults(func=cmd_closeout_slice)

    batch = subparsers.add_parser(
        "batch",
        help="Append multiple WorkItem events from a single JSON manifest, then run one rebuild.",
        epilog=_TASK_LEDGER_PARALLEL_SAFETY_NOTE,
    )
    batch.add_argument(
        "--payload-file",
        required=True,
        help=(
            "JSON manifest with an 'events' list. See docs/task_ledger_batch.md for shape. "
            "Prefer this over parallel note/capture mutations for one logical closeout."
        ),
    )
    batch.add_argument("--created-by", default=None, help="Default created_by for events without one set.")
    batch.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during the final rebuild.",
    )
    batch.set_defaults(func=cmd_batch)

    enqueue_receipt = subparsers.add_parser(
        "enqueue-execution-receipt",
        help="Queue one execution receipt request in the Task Ledger serial intake without touching the event log.",
    )
    _add_common_event_args(enqueue_receipt)
    _add_execution_receipt_args(enqueue_receipt)
    enqueue_receipt.add_argument("--request-id", default=None)
    enqueue_receipt.add_argument(
        "--replace-pending",
        action="store_true",
        help=(
            "Replace an existing pending intake request with the same idempotency key. "
            "Applied and blocked requests are never replaced."
        ),
    )
    enqueue_receipt.set_defaults(func=cmd_enqueue_execution_receipt)

    drain = subparsers.add_parser(
        "drain-intake",
        help="Serially drain pending Task Ledger intake requests into the event log and projections.",
    )
    drain.add_argument("--limit", type=int, default=None)
    drain.add_argument("--created-by", default="codex")
    drain.add_argument("--no-rebuild", action="store_true")
    drain.add_argument(
        "--request-id",
        action="append",
        default=[],
        help="Drain only the exact pending intake request id. Repeatable.",
    )
    drain.add_argument(
        "--idempotency-key",
        action="append",
        default=[],
        help="Drain only the exact pending intake request matching this idempotency key. Repeatable.",
    )
    drain.set_defaults(func=cmd_drain_intake)

    intake_status = subparsers.add_parser(
        "intake-status",
        help="Read Task Ledger serial intake pending/applied/blocked request state.",
    )
    intake_status.add_argument(
        "--request-id",
        action="append",
        default=[],
        help="Show only the exact intake request id. Repeatable.",
    )
    intake_status.add_argument(
        "--idempotency-key",
        action="append",
        default=[],
        help="Show only the exact intake request matching this idempotency key. Repeatable.",
    )
    intake_status.set_defaults(func=cmd_intake_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
