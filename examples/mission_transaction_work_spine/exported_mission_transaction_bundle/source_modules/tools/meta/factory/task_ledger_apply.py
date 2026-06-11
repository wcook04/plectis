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
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import (
    resource_work_queue,
    task_ledger_events,
    work_admission,
)


TASK_LEDGER_SEARCH_SCHEMA = "task_ledger_search_v0"
TASK_LEDGER_PROJECTION_REBUILD_LEASE_CONTEXT_SCHEMA = (
    "task_ledger_projection_rebuild_lease_context_v1"
)
TASK_LEDGER_PROJECTION_REBUILD_DEFERRED_SCHEMA = (
    "task_ledger_projection_rebuild_deferred_receipt_v1"
)
TASK_LEDGER_QUEUED_PROJECTION_REBUILD_SCHEMA = "task_ledger_queued_projection_rebuild_v1"
TASK_LEDGER_EXECUTION_RECEIPT_INTAKE_FALLBACK_SCHEMA = (
    "task_ledger_execution_receipt_intake_fallback_v1"
)
TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION = "task_ledger_projection_rebuild"
TASK_LEDGER_FOCUSED_VALIDATION_QUEUE_SCHEMA = "task_ledger_queued_focused_validation_v1"
FOCUSED_VALIDATION_QUEUE_ACTION = "focused_pytest_or_scoped_validation"
FOCUSED_VALIDATION_HANDLER_VERSION = "focused_pytest_or_scoped_validation_v1"
FOCUSED_VALIDATION_RESOURCE_KIND = "test_worker_pool"
RESOURCE_WORK_HANDLER_REGISTRY_SCHEMA = "resource_work_handler_registry_v1"
TASK_LEDGER_REBUILD_PRESSURE_POLICY_ENV_VAR = "AIW_TASK_LEDGER_REBUILD_PRESSURE_POLICY"
PROMOTED_RENDER_RECEIPT_STATUSES = ("runtime_only", "promoted_evidence", "invalidated")

_TASK_LEDGER_PARALLEL_SAFETY_NOTE = (
    "Parallel safety: Task Ledger mutation commands are single-writer operations; "
    "run them sequentially or use the batch lane for one logical closeout. "
    "Do not launch multiple quick-capture --rebuild commands in parallel; "
    "each command appends to events.jsonl and may refresh shared projections. "
    "For parallel read-only searches, do not reuse one shared temp query file; "
    "prefer stdin or one unique file path per process."
)

_TASK_LEDGER_TAG_FLAG_HINT = (
    "Task Ledger commands prefer repeated --tag flags. quick-capture also accepts "
    "--tags as a compatibility alias and normalizes comma-separated values. "
    "Example: --tag self_error --tag task_ledger."
)

_TASK_LEDGER_QUICK_CAPTURE_POSITIONAL_TITLE_HINT = (
    "quick-capture accepts one positional title as a compatibility alias, "
    "but the canonical form is --title '<title>' plus --statement/--note/--problem. "
    "--description is accepted as a compatibility alias for --summary."
)

_TASK_LEDGER_QUICK_CAPTURE_REBUILD_ECONOMY_HINT = (
    "Speed policy: quick-capture appends authority without rebuilding projections by "
    "default. Add --rebuild only when card/projection visibility is required now; "
    "otherwise run `rebuild --status-only --quiet-progress` before a full projection "
    "refresh."
)

_TASK_LEDGER_EXECUTION_RECEIPT_HINT = """\
Validated-uncommitted CAS-stop closeout:
  Use this only after a scoped commit lost its allowed refreshed HEAD-CAS retry.
  It records an auditable blocker receipt, not a commit replacement.

  ./repo-python tools/meta/factory/task_ledger_apply.py record-execution-receipt \\
    --subject-id <work_item_or_cap_id> \\
    --transaction-id <transaction_id> \\
    --work-ledger-session-id <session_id> \\
    --read-receipt-id <read_receipt_id> \\
    --closeout-state validated_uncommitted_git_metadata_blocked \\
    --no-commit-reason parent_cas_retry_exhausted \\
    --validation-ref <focused_validation_or_diff_check_ref> \\
    --commit-blocker-ref <head_moved_or_cas_retry_ref> \\
    --payload-file <receipt.json> \\
    --projection-rebuild-policy off

  receipt.json should carry the expected parent, observed HEAD after failure,
  owned paths or write-set hash, overlap/preflight refs, artifact refs, and
  re-entry condition. Prefer --payload-file or --payload-stdin for rich
  closeout evidence; do not paste shell-sensitive JSON inline.
"""


def _station_render_module() -> Any:
    from tools.meta.observability import station_render

    return station_render


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


def _compact_event_ref(event: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "event_id": event.get("event_id"),
        "event_type": event.get("event_type"),
        "subject_id": event.get("subject_id"),
        "created_at": event.get("created_at"),
        "event_hash": event.get("event_hash"),
        "previous_event_hash": event.get("previous_event_hash"),
    }


def _compact_quick_capture_visibility_receipt(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    assimilation = (
        receipt.get("projection_assimilation_state")
        if isinstance(receipt.get("projection_assimilation_state"), Mapping)
        else {}
    )
    compact: Dict[str, Any] = {
        "schema": "task_ledger_quick_capture_visibility_compact_v1",
        "authority_status": receipt.get("authority_status"),
        "projection_status": receipt.get("projection_status"),
        "projection_rebuilt": receipt.get("projection_rebuilt"),
        "selected_subject_ids": receipt.get("selected_subject_ids") or [],
        "selected_event_ids": receipt.get("selected_event_ids") or [],
        "event_ids_visible_in_authority": receipt.get("event_ids_visible_in_authority") or {},
        "all_selected_cards_visible": receipt.get("all_selected_cards_visible"),
    }
    if assimilation:
        compact["projection_assimilation_state"] = {
            "status": assimilation.get("status"),
            "authority_event_visible": assimilation.get("authority_event_visible"),
            "projection_visible": assimilation.get("projection_visible"),
            "projection_card_visibility": assimilation.get("projection_card_visibility"),
            "terminal_for_authority": assimilation.get("terminal_for_authority"),
            "projection_required_now": assimilation.get("projection_required_now"),
            "read_model_lag_expected": assimilation.get("read_model_lag_expected"),
            "queued_for_drain": assimilation.get("queued_for_drain"),
            "next_safe_action": assimilation.get("next_safe_action"),
        }
    return compact


def _compact_projection_rebuild_deferred(receipt: Mapping[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "task_ledger_projection_rebuild_deferred_compact_v1",
        "status": receipt.get("status"),
        "projection_rebuilt": receipt.get("projection_rebuilt"),
        "authority_appended": receipt.get("authority_appended"),
        "queued_for_drain": receipt.get("queued_for_drain"),
        "resource_kind": receipt.get("resource_kind"),
        "reason": receipt.get("reason"),
        "reentry_condition": receipt.get("reentry_condition"),
    }


def _compact_projection_result(projection: Mapping[str, Any]) -> Dict[str, Any]:
    compact = {
        "status": projection.get("status"),
        "ok": projection.get("ok"),
        "generated_at": projection.get("generated_at"),
        "checked_at": projection.get("checked_at"),
    }
    build_reuse = projection.get("build_reuse")
    if isinstance(build_reuse, Mapping):
        compact["build_reuse"] = {
            "saved_projection_rebuild": build_reuse.get("saved_projection_rebuild"),
            "reuse_status": build_reuse.get("reuse_status"),
        }
    return compact


def _compact_quick_capture_result(result: Mapping[str, Any]) -> Dict[str, Any]:
    event = result.get("event") if isinstance(result.get("event"), Mapping) else {}
    visibility = (
        result.get("visibility_receipt")
        if isinstance(result.get("visibility_receipt"), Mapping)
        else {}
    )
    compact: Dict[str, Any] = {
        "schema": "task_ledger_quick_capture_compact_v1",
        "output_profile": "compact",
        "ok": result.get("ok", True),
        "status": result.get("status"),
        "event": _compact_event_ref(event),
        "quick_capture": result.get("quick_capture") or {},
        "visibility_receipt": _compact_quick_capture_visibility_receipt(visibility),
        "omission_receipt": {
            "omitted": [
                "full event payload body",
                "full selected_card_visibility rows",
                "full projection_assimilation_state body",
                "full projection rebuild payload",
            ],
            "reason": "quick-capture --compact preserves authority ids and visibility scalars for capture-before-prose without emitting full append/projection bodies.",
            "full_profile": "rerun without --compact when full event payload or projection body evidence is required",
        },
    }
    serialization = result.get("task_ledger_mutation_serialization")
    if isinstance(serialization, Mapping):
        compact["task_ledger_mutation_serialization"] = {
            "schema": serialization.get("schema"),
            "mode": serialization.get("mode"),
            "event_count": serialization.get("event_count"),
            "projection_rebuilt": serialization.get("projection_rebuilt"),
            "projection_write_under_same_lock": serialization.get(
                "projection_write_under_same_lock"
            ),
        }
    projection = result.get("projection")
    if isinstance(projection, Mapping):
        compact["projection"] = _compact_projection_result(projection)
    deferred = result.get("projection_rebuild_deferred")
    if isinstance(deferred, Mapping):
        compact["projection_rebuild_deferred"] = _compact_projection_rebuild_deferred(deferred)
    return compact


def _work_ledger_module() -> Any:
    from system.lib import work_ledger as module

    return module


def _work_ledger_runtime_module() -> Any:
    from system.lib import work_ledger_runtime as module

    return module


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
    projection_rebuild_deferred: Dict[str, Any] | None = None,
    authority_health_hint: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    return task_ledger_events.visibility_receipt(
        REPO_ROOT,
        subject_ids=subject_ids,
        event_ids=event_ids,
        projection_rebuilt=projection_result is not None,
        projection_result=projection_result,
        projection_rebuild_deferred=projection_rebuild_deferred,
        authority_health_hint=authority_health_hint,
    )


def _task_ledger_projection_rebuild_policy(args: argparse.Namespace) -> str:
    raw_policy = (
        getattr(args, "projection_rebuild_policy", None)
        or os.environ.get(TASK_LEDGER_REBUILD_PRESSURE_POLICY_ENV_VAR)
        or "auto"
    )
    if getattr(args, "ignore_host_pressure", False):
        raw_policy = "off"
    return work_admission.normalize_work_admission_policy(raw_policy)


def build_task_ledger_projection_rebuild_lease_context(
    *,
    command_name: str,
    policy: str = "auto",
    check: bool = False,
) -> Dict[str, Any]:
    fingerprint = {
        "owner_surface": "task_ledger_apply",
        "projection": "task_ledger",
        "command": command_name,
        "check": bool(check),
        "repo_root": str(REPO_ROOT),
        "authority_log": str(task_ledger_events.EVENTS_REL),
        "projection_outputs": [
            str(task_ledger_events.LEDGER_REL),
            str(task_ledger_events.SIGNOFFS_REL),
            str(task_ledger_events.VIEWS_REL),
        ],
        "admission_work_class": work_admission.PROJECTION_SETTLEMENT,
    }
    decision = work_admission.build_dev_resource_lease_decision(
        REPO_ROOT,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        fingerprint=fingerprint,
        existing_leases=[],
        policy=policy,
        request_id=f"task_ledger:{command_name}:projection_rebuild",
        requested_by="task_ledger_apply",
        exclusive_required=True,
    )
    lease = decision.get("lease") if isinstance(decision.get("lease"), dict) else {}
    return {
        "schema": TASK_LEDGER_PROJECTION_REBUILD_LEASE_CONTEXT_SCHEMA,
        "command": command_name,
        "policy": policy,
        "check": bool(check),
        "decision": decision,
        "lease_id": lease.get("lease_id"),
        "fingerprint_hash": lease.get("fingerprint_hash"),
    }


def _projection_rebuild_allowed(lease_context: Dict[str, Any] | None) -> bool:
    if not lease_context:
        return True
    decision = lease_context.get("decision")
    return isinstance(decision, dict) and bool(decision.get("allow"))


def _projection_check_read_only_context(*, command_name: str, policy: str) -> Dict[str, Any]:
    return {
        "schema": TASK_LEDGER_PROJECTION_REBUILD_LEASE_CONTEXT_SCHEMA,
        "command": command_name,
        "policy": policy,
        "check": True,
        "decision": {
            "schema": "task_ledger_projection_check_admission_v0",
            "allow": True,
            "status": "read_only_projection_check_no_builder_lease",
            "reason": (
                "Task Ledger projection checks read authority and projection manifests only; "
                "projection-builder admission is reserved for mutating rebuilds."
            ),
            "resource_kind": "task_ledger_projection_check",
            "resource_work_class": "read_only_check",
        },
        "lease_id": None,
        "fingerprint_hash": None,
    }


def _resolve_projection_rebuild_request(
    args: argparse.Namespace,
    command_name: str,
    *,
    requested: bool,
    check: bool = False,
) -> tuple[bool, Dict[str, Any] | None]:
    if not requested:
        return False, None
    policy = _task_ledger_projection_rebuild_policy(args)
    if check:
        return True, _projection_check_read_only_context(
            command_name=command_name,
            policy=policy,
        )
    lease_context = build_task_ledger_projection_rebuild_lease_context(
        command_name=command_name,
        policy=policy,
        check=check,
    )
    return _projection_rebuild_allowed(lease_context), lease_context


def _projection_rebuild_queue_payload(*, command_name: str, check: bool = False) -> Dict[str, Any]:
    return {
        "schema": TASK_LEDGER_QUEUED_PROJECTION_REBUILD_SCHEMA,
        "command_name": str(command_name),
        "check": bool(check),
    }


def _enqueue_deferred_projection_rebuild(
    lease_context: Dict[str, Any] | None,
    *,
    command_name: str,
    check: bool = False,
    authority_appended: bool,
) -> Dict[str, Any]:
    try:
        return resource_work_queue.enqueue_resource_work(
            REPO_ROOT,
            resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
            work_class=work_admission.PROJECTION_REBUILD,
            owner_surface="task_ledger_apply",
            action=TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION,
            request_key=f"task_ledger_projection_rebuild:check={bool(check)}",
            payload=_projection_rebuild_queue_payload(command_name=command_name, check=check),
            reason="host_pressure_deferred_projection_rebuild",
            lease_context=lease_context or {},
            source_refs=[str(task_ledger_events.EVENTS_REL)] if authority_appended else [],
        )
    except Exception as exc:
        return {
            "schema": "resource_work_enqueue_receipt_v1",
            "status": "queue_append_failed",
            "queued": False,
            "error": str(exc),
            "authority": str(resource_work_queue.RESOURCE_QUEUE_EVENTS_REL),
        }


def _projection_queue_result_ref(projection_result: Dict[str, Any] | None) -> str | None:
    if not projection_result:
        return None
    generated_at = projection_result.get("generated_at") or projection_result.get("checked_at")
    status = projection_result.get("status") or projection_result.get("validation_status")
    if generated_at or status:
        return f"task_ledger_projection:{status or 'rebuilt'}:{generated_at or 'unknown_time'}"
    return "task_ledger_projection:rebuilt"


def _settle_queued_projection_rebuilds_after_success(
    projection_result: Dict[str, Any] | None,
    *,
    command_name: str,
    check: bool = False,
) -> Dict[str, Any] | None:
    if not projection_result:
        return None
    pending = resource_work_queue.pending_resource_work(
        REPO_ROOT,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        work_class=work_admission.PROJECTION_REBUILD,
        owner_surface="task_ledger_apply",
        action=TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION,
    )
    settled: list[Dict[str, Any]] = []
    for item in pending:
        payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
        item_check = bool(payload.get("check"))
        if check and not item_check:
            continue
        receipt = resource_work_queue.record_resource_work_event(
            REPO_ROOT,
            queue_id=str(item.get("queue_id") or ""),
            event_type="resource_work.succeeded",
            reason=f"satisfied_by_task_ledger_{command_name}",
            result_ref=_projection_queue_result_ref(projection_result),
            result_summary={
                "command_name": command_name,
                "check": bool(check),
                "projection_status": projection_result.get("status"),
                "projection_ok": projection_result.get("ok"),
            },
        )
        settled.append(receipt)
    if not settled:
        return None
    return {
        "schema": "task_ledger_projection_rebuild_queue_settlement_v1",
        "status": "settled",
        "settled_count": len(settled),
        "settled": settled,
    }


def _attach_projection_queue_settlement(
    result: Dict[str, Any],
    projection_result: Dict[str, Any] | None,
    *,
    command_name: str,
    check: bool = False,
) -> None:
    settlement = _settle_queued_projection_rebuilds_after_success(
        projection_result,
        command_name=command_name,
        check=check,
    )
    if settlement:
        result["projection_rebuild_queue_settlement"] = settlement


def _pending_task_ledger_projection_rebuilds(*, limit: int | None = None) -> list[Dict[str, Any]]:
    return resource_work_queue.pending_resource_work(
        REPO_ROOT,
        resource_kind=work_admission.GENERATED_PROJECTION_BUILDER,
        work_class=work_admission.PROJECTION_REBUILD,
        owner_surface="task_ledger_apply",
        action=TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION,
        limit=limit,
    )


def _task_ledger_projection_rebuild_queue_scope(pending: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema": "task_ledger_projection_rebuild_queue_scope_v1",
        "drainable_pending_count": len(pending),
        "resource_kind": work_admission.GENERATED_PROJECTION_BUILDER,
        "work_class": work_admission.PROJECTION_REBUILD,
        "owner_surface": "task_ledger_apply",
        "action": TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION,
        "drain_command": task_ledger_events.TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND,
        "full_rebuild_command": task_ledger_events.TASK_LEDGER_REBUILD_QUIET_COMMAND,
        "status_check_command": task_ledger_events.TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND,
    }


def _repair_projection_behind_authority_next_command(result: Dict[str, Any]) -> None:
    if result.get("status") != "projection_behind_authority":
        return
    pending = _pending_task_ledger_projection_rebuilds()
    queue_scope = _task_ledger_projection_rebuild_queue_scope(pending)
    result["task_ledger_projection_rebuild_queue"] = queue_scope
    if pending:
        result["safe_next_command"] = task_ledger_events.TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND
        result["next_step"] = (
            "Task Ledger deterministic projections are behind the authority log and a "
            "matching deferred projection rebuild is queued; drain that queued owner work."
        )
        return
    rebuild_priority = (
        result.get("rebuild_priority")
        if isinstance(result.get("rebuild_priority"), Mapping)
        else {}
    )
    if rebuild_priority.get("status") == "low_active_authority_delta":
        result["safe_next_command"] = task_ledger_events.TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND
        result["rebuild_priority"]["command_policy"] = (
            "defer_full_rebuild_for_authority_only_closeout"
        )
        result["rebuild_priority"]["recheck_command"] = (
            task_ledger_events.TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND
        )
        result["deferred_rebuild_command_when_queued"] = (
            task_ledger_events.TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND
        )
        result["next_step"] = (
            "Task Ledger deterministic projections are behind by a small active-authority "
            "delta and no deferred rebuild is queued. Continue with authority-visible "
            "receipts for normal closeout; run the full owner rebuild only when generated "
            "card/projection visibility is required."
        )
        result["reentry_condition"] = (
            "Run the full rebuild only when a later status check reports a medium/high "
            "delta, a deferred rebuild is queued, or card/projection visibility is needed."
        )
        return
    result["safe_next_command"] = task_ledger_events.TASK_LEDGER_REBUILD_QUIET_COMMAND
    result["deferred_rebuild_command_when_queued"] = (
        task_ledger_events.TASK_LEDGER_DRAIN_DEFERRED_REBUILD_QUIET_COMMAND
    )
    result["next_step"] = (
        "Task Ledger deterministic projections are behind the authority log, but no "
        "matching deferred Task Ledger projection rebuild is queued. Run the owner "
        "rebuild route; if host pressure blocks it, that command will queue drainable "
        "projection work."
    )
    result["reentry_condition"] = (
        "Use drain-deferred-rebuilds only after task_ledger_projection_rebuild_queue."
        "drainable_pending_count is greater than zero."
    )


def _projection_rebuild_deferred_receipt(
    lease_context: Dict[str, Any] | None,
    *,
    authority_appended: bool,
    command_name: str = "unknown",
    check: bool = False,
) -> Dict[str, Any] | None:
    if not lease_context or _projection_rebuild_allowed(lease_context):
        return None
    decision = lease_context.get("decision") if isinstance(lease_context.get("decision"), dict) else {}
    queue_item = (
        decision.get("resource_queue_item")
        if isinstance(decision.get("resource_queue_item"), dict)
        else {}
    )
    queued_work = _enqueue_deferred_projection_rebuild(
        lease_context,
        command_name=command_name,
        check=check,
        authority_appended=authority_appended,
    )
    return {
        "schema": TASK_LEDGER_PROJECTION_REBUILD_DEFERRED_SCHEMA,
        "status": "deferred_by_host_pressure",
        "projection_rebuilt": False,
        "authority_appended": bool(authority_appended),
        "queued_for_drain": queued_work.get("status") in {"queued", "already_queued"},
        "queued_work": queued_work,
        "resource_kind": work_admission.GENERATED_PROJECTION_BUILDER,
        "result": decision.get("result"),
        "reason": decision.get("status"),
        "reentry_condition": queue_item.get("reentry_condition")
        or decision.get("reentry_condition")
        or "retry after host pressure admission allows projection_rebuild starts",
        "lease_context": lease_context,
    }


def _strip_remainder(values: Sequence[str] | None) -> list[str]:
    rows = list(values or [])
    if rows and rows[0] == "--":
        return rows[1:]
    return rows


def _short_digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()[:16]


def _git_head(repo_root: Path) -> str | None:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        return None
    return completed.stdout.strip() or None


_PYTEST_OPTIONS_WITH_VALUE = {
    "--basetemp",
    "--root",
    "--durations",
    "--durations-min",
    "-k",
    "-m",
    "-o",
    "--tb",
    "--junitxml",
}


def _pytest_source_paths(pytest_args: Sequence[str], source_refs: Sequence[str]) -> list[str]:
    paths: list[str] = []
    seen: set[str] = set()
    root_prefix: str | None = None
    expect_root_value = False
    skip_next = False
    for raw in [*list(source_refs or []), *list(pytest_args or [])]:
        token = str(raw or "").strip()
        if expect_root_value:
            root_prefix = token
            expect_root_value = False
            continue
        if skip_next:
            skip_next = False
            continue
        if not token:
            continue
        if token == "--root":
            expect_root_value = True
            continue
        if token.startswith("--root="):
            root_prefix = token.split("=", 1)[1]
            continue
        if token in _PYTEST_OPTIONS_WITH_VALUE:
            skip_next = True
            continue
        if token.startswith("-"):
            continue
        token = token.split("::", 1)[0]
        if token.startswith("{") or token.startswith("["):
            continue
        if root_prefix and not Path(token).is_absolute() and ("/" in token or token.endswith(".py")):
            token = str(Path(root_prefix) / token)
        if token not in seen:
            paths.append(token)
            seen.add(token)
    return paths


def _file_digest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"status": "missing"}
    if not path.is_file():
        return {"status": "not_file"}
    data = path.read_bytes()
    return {
        "status": "hashed",
        "sha256": hashlib.sha256(data).hexdigest(),
        "byte_count": len(data),
    }


def _focused_validation_source_snapshot(
    repo_root: Path,
    *,
    pytest_args: Sequence[str],
    source_refs: Sequence[str],
) -> dict[str, Any]:
    source_paths = _pytest_source_paths(pytest_args, source_refs)
    file_hashes: dict[str, Any] = {}
    for rel in source_paths:
        path = repo_root / rel
        file_hashes[rel] = _file_digest(path)
    return {
        "schema": "focused_validation_source_snapshot_v1",
        "head": _git_head(repo_root),
        "pytest_args": list(pytest_args),
        "source_refs": list(source_refs),
        "source_paths": source_paths,
        "file_hashes": file_hashes,
        "dirty_scope_policy": "supersede_if_relevant_file_hash_changes",
    }


def _focused_validation_source_status(item: Mapping[str, Any]) -> dict[str, Any]:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    original = item.get("source_snapshot") if isinstance(item.get("source_snapshot"), dict) else {}
    pytest_args = payload.get("pytest_args") if isinstance(payload.get("pytest_args"), list) else []
    source_refs = payload.get("source_refs") if isinstance(payload.get("source_refs"), list) else []
    current = _focused_validation_source_snapshot(
        REPO_ROOT,
        pytest_args=[str(arg) for arg in pytest_args],
        source_refs=[str(ref) for ref in source_refs],
    )
    original_hashes = original.get("file_hashes") if isinstance(original.get("file_hashes"), dict) else {}
    current_hashes = current.get("file_hashes") if isinstance(current.get("file_hashes"), dict) else {}
    changed_paths = [
        path
        for path in sorted(set(original_hashes) | set(current_hashes))
        if current_hashes.get(path) != original_hashes.get(path)
    ]
    return {
        "schema": "focused_validation_source_status_v1",
        "status": "source_changed" if changed_paths else "unchanged",
        "changed_paths": changed_paths,
        "head_changed": bool(original.get("head") and current.get("head") != original.get("head")),
        "original_head": original.get("head"),
        "current_head": current.get("head"),
        "current_snapshot": current,
    }


def _action_quote_host_pressure_snapshot(quote: Mapping[str, Any]) -> dict[str, Any]:
    host_pressure = quote.get("host_pressure_admission")
    disk_pressure = quote.get("disk_pressure_admission")
    if not isinstance(host_pressure, dict) and not isinstance(disk_pressure, dict):
        return {}
    if not isinstance(host_pressure, dict):
        host_pressure = {}
    if not isinstance(disk_pressure, dict):
        disk_pressure = {}
    admission = host_pressure.get("admission") if isinstance(host_pressure.get("admission"), dict) else {}
    summary = host_pressure.get("summary") if isinstance(host_pressure.get("summary"), dict) else {}
    disk_reason = disk_pressure.get("reason")
    return {
        "schema": "focused_validation_pressure_snapshot_v1",
        "decision": host_pressure.get("decision") or admission.get("decision"),
        "reason": admission.get("reason") or disk_reason,
        "requested_workload_class": host_pressure.get("requested_workload_class"),
        "active_agents": admission.get("active_agents") or summary.get("active_agents"),
        "pressure_index": summary.get("pressure_index"),
        "bottleneck_class": summary.get("bottleneck_class"),
        "recheck_command": quote.get("host_pressure_recheck_command")
        or host_pressure.get("quote_command"),
        "disk_pressure": {
            "decision": disk_pressure.get("decision"),
            "reason": disk_reason,
            "should_block_run": disk_pressure.get("should_block_run"),
            "free_human": disk_pressure.get("free_human"),
            "required_free_human": disk_pressure.get("required_free_human"),
        },
    }


def _resource_work_pressure_state() -> dict[str, Any]:
    """Return a compact live admission snapshot for queued validation work."""
    try:
        quote = _build_focused_validation_quote(
            pytest_args=[],
            source_refs=[],
            session_id=None,
        )
    except Exception as exc:  # pragma: no cover - local host adapters are best-effort status inputs.
        return {
            "schema": "resource_work_pressure_state_v1",
            "status": "unavailable",
            "error_class": type(exc).__name__,
            "should_block_run": False,
            "recheck_command": "./repo-python kernel.py --host-pressure --host-pressure-no-processes --json",
        }

    host_pressure = quote.get("host_pressure_admission")
    disk_pressure = quote.get("disk_pressure_admission")
    snapshot = _action_quote_host_pressure_snapshot(quote)
    if not snapshot and not isinstance(host_pressure, Mapping) and not isinstance(disk_pressure, Mapping):
        return {
            "schema": "resource_work_pressure_state_v1",
            "status": "missing",
            "should_block_run": False,
            "recheck_command": "./repo-python kernel.py --host-pressure --host-pressure-no-processes --json",
        }

    host_pressure = host_pressure if isinstance(host_pressure, Mapping) else {}
    admission = host_pressure.get("admission") if isinstance(host_pressure.get("admission"), Mapping) else {}
    summary = host_pressure.get("summary") if isinstance(host_pressure.get("summary"), Mapping) else {}
    return {
        "schema": "resource_work_pressure_state_v1",
        "status": host_pressure.get("status") or "available",
        "source": "action_quote.repo_pytest_validation",
        "decision": snapshot.get("decision") or admission.get("decision"),
        "reason": snapshot.get("reason") or admission.get("reason"),
        "should_block_run": _action_quote_blocks_work(quote),
        "requested_workload_class": snapshot.get("requested_workload_class")
        or host_pressure.get("requested_workload_class")
        or admission.get("requested_workload_class"),
        "active_agents": snapshot.get("active_agents")
        or admission.get("active_agents")
        or summary.get("active_agents"),
        "pressure_index": snapshot.get("pressure_index") or summary.get("pressure_index"),
        "bottleneck_class": snapshot.get("bottleneck_class") or summary.get("bottleneck_class"),
        "recommendation": quote.get("recommendation"),
        "current_status": quote.get("current_status"),
        "recheck_command": snapshot.get("recheck_command")
        or quote.get("host_pressure_recheck_command")
        or host_pressure.get("quote_command"),
        "disk_pressure": snapshot.get("disk_pressure", {}),
    }


def _action_quote_blocks_work(quote: Mapping[str, Any]) -> bool:
    host_pressure = quote.get("host_pressure_admission")
    if not isinstance(host_pressure, dict):
        host_pressure = {}
    admission = host_pressure.get("admission") if isinstance(host_pressure.get("admission"), dict) else {}
    decision = str(host_pressure.get("decision") or admission.get("decision") or "")
    disk_pressure = quote.get("disk_pressure_admission")
    disk_decision = ""
    disk_blocks = False
    if isinstance(disk_pressure, dict):
        disk_decision = str(disk_pressure.get("decision") or "")
        disk_blocks = bool(disk_pressure.get("should_block_run")) or disk_decision.startswith("queue_")
    return bool(host_pressure.get("should_block_run")) or disk_blocks or decision in {
        "queue_until_pressure_clears",
        "require_operator_override",
    }


def _build_focused_validation_quote(
    *,
    pytest_args: Sequence[str],
    source_refs: Sequence[str],
    session_id: str | None,
) -> dict[str, Any]:
    from system.lib.action_quote import build_action_quote

    return build_action_quote(
        REPO_ROOT,
        action_id="repo_pytest_validation",
        scope_paths=list(source_refs or []),
        extra_args=list(pytest_args or []),
        current_session_id=session_id,
    )


def _focused_validation_request_key(pytest_args: Sequence[str], source_refs: Sequence[str]) -> str:
    digest = _short_digest({"pytest_args": list(pytest_args), "source_refs": list(source_refs)})
    return f"focused_pytest_or_scoped_validation:{digest}"


def _resource_work_handler_registry() -> dict[str, Any]:
    return {
        "schema": RESOURCE_WORK_HANDLER_REGISTRY_SCHEMA,
        "handlers": {
            TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION: {
                "handler_id": TASK_LEDGER_PROJECTION_REBUILD_QUEUE_ACTION,
                "handler_version": "task_ledger_projection_rebuild_v1",
                "resource_kind": work_admission.GENERATED_PROJECTION_BUILDER,
                "work_class": work_admission.PROJECTION_REBUILD,
                "owner_surface": "task_ledger_apply",
                "drain_command": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "drain-deferred-rebuilds --limit 1"
                ),
            },
            FOCUSED_VALIDATION_QUEUE_ACTION: {
                "handler_id": FOCUSED_VALIDATION_QUEUE_ACTION,
                "handler_version": FOCUSED_VALIDATION_HANDLER_VERSION,
                "resource_kind": FOCUSED_VALIDATION_RESOURCE_KIND,
                "work_class": work_admission.VALIDATION_OR_BUILD,
                "owner_surface": "task_ledger_apply",
                "admission_action": "repo_pytest_validation",
                "drain_command": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "drain-resource-work --handler-id focused_pytest_or_scoped_validation "
                    "--limit 1 --stale-sweep-limit 12 --compact"
                ),
                "stale_sweep_command": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "drain-resource-work --handler-id focused_pytest_or_scoped_validation "
                    "--limit 12 --source-check-only --compact"
                ),
                "actuator_command": (
                    "./repo-python tools/meta/factory/task_ledger_apply.py "
                    "actuate-resource-work --mode throughput "
                    "--handler-id focused_pytest_or_scoped_validation "
                    "--stale-sweep-limit 24 --max-validation-drains 1 --compact"
                ),
            },
        },
    }


def _resource_work_wake_plan(
    operating_picture: Mapping[str, Any],
    handler_registry: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the owner-visible wake contract for queued resource work."""
    def _count_map(value: Any) -> dict[str, int]:
        if not isinstance(value, Mapping):
            return {}
        counts: dict[str, int] = {}
        for key, raw_count in value.items():
            try:
                counts[str(key)] = int(raw_count or 0)
            except (TypeError, ValueError):
                counts[str(key)] = 0
        return counts

    def _handler_status(handler_pending: int, handler_eligible: int) -> str:
        if running_count:
            return "active_drainer_running"
        if not handler_pending:
            return "no_pending_resource_work"
        if pressure_blocks:
            return "waiting_for_pressure_clear"
        if handler_eligible:
            return "ready_to_drain_now"
        return "waiting_for_next_attempt"

    pressure_state = (
        operating_picture.get("pressure_state")
        if isinstance(operating_picture.get("pressure_state"), Mapping)
        else {}
    )
    handlers = handler_registry.get("handlers")
    if not isinstance(handlers, Mapping):
        handlers = {}
    focused_handler = (
        handlers.get(FOCUSED_VALIDATION_QUEUE_ACTION)
        if isinstance(handlers.get(FOCUSED_VALIDATION_QUEUE_ACTION), Mapping)
        else {}
    )
    pending_count = int(operating_picture.get("pending_count") or 0)
    running_count = int(operating_picture.get("running_count") or 0)
    eligible_pending_count = int(operating_picture.get("eligible_pending_count") or 0)
    pressure_blocks = bool(pressure_state.get("should_block_run"))
    pending_count_by_handler = _count_map(operating_picture.get("pending_count_by_handler"))
    eligible_count_by_handler = _count_map(
        operating_picture.get("eligible_pending_count_by_handler")
    )
    handler_actions: list[dict[str, Any]] = []
    for handler_id, raw_handler in sorted(handlers.items()):
        if not isinstance(raw_handler, Mapping):
            continue
        handler_key = str(handler_id)
        handler_pending = pending_count_by_handler.get(handler_key, 0)
        handler_eligible = eligible_count_by_handler.get(handler_key, 0)
        handler_actions.append(
            {
                "handler_id": handler_key,
                "status": _handler_status(handler_pending, handler_eligible),
                "pending_count": handler_pending,
                "eligible_pending_count": handler_eligible,
                "resource_kind": raw_handler.get("resource_kind"),
                "work_class": raw_handler.get("work_class"),
                "owner_surface": raw_handler.get("owner_surface"),
                "drain_command": raw_handler.get("drain_command"),
                "stale_sweep_command": raw_handler.get("stale_sweep_command"),
                "actuator_command": raw_handler.get("actuator_command"),
            }
        )
    if running_count:
        status = "active_drainer_running"
        next_action = "wait_for_active_drainer"
    elif not pending_count:
        status = "no_pending_resource_work"
        next_action = "none"
    elif pressure_blocks:
        status = "waiting_for_pressure_clear"
        next_action = "poll_pressure_then_drain"
    elif eligible_pending_count:
        status = "ready_to_drain_now"
        next_action = "run_drain_command"
    else:
        status = "waiting_for_next_attempt"
        next_action = "wake_at_next_attempt"
    return {
        "schema": "resource_work_wake_plan_v1",
        "status": status,
        "next_action": next_action,
        "pending_count": pending_count,
        "running_count": running_count,
        "eligible_pending_count": eligible_pending_count,
        "future_pending_count": int(operating_picture.get("future_pending_count") or 0),
        "next_wake_at": operating_picture.get("next_wake_at"),
        "pressure_blocks": pressure_blocks,
        "pressure_recheck_command": pressure_state.get("recheck_command"),
        "wake_condition": "pressure_blocks=false and eligible_pending_count>0",
        "drain_command": focused_handler.get("drain_command"),
        "stale_sweep_command": focused_handler.get("stale_sweep_command"),
        "actuator_command": focused_handler.get("actuator_command"),
        "handler_action_count": len(handler_actions),
        "eligible_handler_count": sum(
            1 for action in handler_actions if action["eligible_pending_count"] > 0
        ),
        "handler_actions": handler_actions,
    }


def _record_queue_note_for_caps(
    *,
    cap_ids: Sequence[str],
    queue_receipt: Mapping[str, Any],
    created_by: str,
) -> list[dict[str, Any]]:
    queue_id = str(queue_receipt.get("queue_id") or "")
    if not queue_id:
        return []
    notes: list[dict[str, Any]] = []
    for cap_id in cap_ids:
        subject_id = str(cap_id or "").strip()
        if not subject_id:
            continue
        event = {
            "event_type": EVENT_BY_COMMAND["note"],
            "created_by": created_by,
            "subject_id": subject_id,
            "source": {"kind": "resource_work_queue", "refs": [queue_id]},
            "refs": {"queue_refs": [queue_id]},
            "payload": {
                "note": (
                    "Focused validation is now backed by resource work queue item "
                    f"{queue_id}; it should drain when host-pressure admission allows test_build."
                ),
                "queued_work": {
                    "queue_id": queue_id,
                    "handler_id": FOCUSED_VALIDATION_QUEUE_ACTION,
                    "status": queue_receipt.get("status"),
                },
            },
        }
        notes.append(
            task_ledger_events.append_event_and_rebuild(
                REPO_ROOT,
                event,
                rebuild=False,
            )
        )
    return notes


def _queue_focused_validation(
    *,
    pytest_args: Sequence[str],
    source_refs: Sequence[str],
    cap_ids: Sequence[str],
    workitem_refs: Sequence[str],
    session_id: str | None,
    reason: str | None,
    priority: int,
    admission_policy: str,
    created_by: str = "codex",
) -> dict[str, Any]:
    quote = _build_focused_validation_quote(
        pytest_args=pytest_args,
        source_refs=source_refs,
        session_id=session_id,
    )
    pressure_snapshot = _action_quote_host_pressure_snapshot(quote)
    blocked = _action_quote_blocks_work(quote)
    source_snapshot = _focused_validation_source_snapshot(
        REPO_ROOT,
        pytest_args=pytest_args,
        source_refs=source_refs,
    )
    payload = {
        "schema": TASK_LEDGER_FOCUSED_VALIDATION_QUEUE_SCHEMA,
        "pytest_args": list(pytest_args),
        "source_refs": list(source_refs),
        "command": shlex.join(["./repo-pytest", *list(pytest_args)]),
        "quote_status": quote.get("current_status"),
        "quote_recommendation": quote.get("recommendation"),
    }
    queue_receipt = resource_work_queue.enqueue_resource_work(
        REPO_ROOT,
        resource_kind=FOCUSED_VALIDATION_RESOURCE_KIND,
        work_class=work_admission.VALIDATION_OR_BUILD,
        owner_surface="task_ledger_apply",
        action=FOCUSED_VALIDATION_QUEUE_ACTION,
        handler_id=FOCUSED_VALIDATION_QUEUE_ACTION,
        handler_version=FOCUSED_VALIDATION_HANDLER_VERSION,
        request_key=_focused_validation_request_key(pytest_args, source_refs),
        payload=payload,
        reason=reason
        or (
            "host_pressure_deferred_focused_validation"
            if blocked
            else "operator_queued_focused_validation"
        ),
        blocked_reason=pressure_snapshot.get("reason") if blocked else None,
        priority=priority,
        next_attempt_at=(
            resource_work_queue.compute_backoff_next_attempt_at() if blocked else None
        ),
        pressure_snapshot=pressure_snapshot,
        source_snapshot=source_snapshot,
        owner_session_id=session_id,
        source_refs=source_snapshot.get("source_paths") or list(source_refs),
        cap_refs=list(cap_ids),
        workitem_refs=list(workitem_refs),
        admission_policy=admission_policy,
        replace_if_source_changed=True,
    )
    cap_notes = _record_queue_note_for_caps(
        cap_ids=cap_ids,
        queue_receipt=queue_receipt,
        created_by=created_by,
    )
    return {
        "schema": "focused_validation_queue_receipt_v1",
        "status": "queued" if queue_receipt.get("status") in {"queued", "already_queued"} else "failed",
        "host_pressure_blocked": blocked,
        "queue": queue_receipt,
        "cap_note_results": cap_notes,
        "action_quote": quote,
        "source_snapshot": source_snapshot,
    }


def _tail_text(value: str | None, *, limit: int = 4000) -> str:
    text = value or ""
    return text[-limit:] if len(text) > limit else text


def _drain_focused_validation_item(
    args: argparse.Namespace,
    item: Mapping[str, Any],
) -> dict[str, Any]:
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    pytest_args = [str(arg) for arg in payload.get("pytest_args") or []]
    source_refs = [str(ref) for ref in payload.get("source_refs") or []]
    queue_id = str(item.get("queue_id") or "")
    source_status = _focused_validation_source_status(item)
    if source_status.get("status") != "unchanged":
        receipt = resource_work_queue.record_resource_work_event(
            REPO_ROOT,
            queue_id=queue_id,
            event_type="resource_work.superseded",
            reason="focused_validation_source_snapshot_changed",
            blocked_reason="source_snapshot_changed",
            result_summary=source_status,
        )
        return {
            "status": "superseded",
            "queue_id": queue_id,
            "source_status": source_status,
            "superseded": receipt,
        }
    if getattr(args, "source_check_only", False):
        return {
            "status": "source_unchanged",
            "queue_id": queue_id,
            "source_status": source_status,
        }
    quote = _build_focused_validation_quote(
        pytest_args=pytest_args,
        source_refs=source_refs,
        session_id=getattr(args, "session_id", None),
    )
    if _action_quote_blocks_work(quote):
        pressure_snapshot = _action_quote_host_pressure_snapshot(quote)
        receipt = resource_work_queue.record_resource_work_event(
            REPO_ROOT,
            queue_id=queue_id,
            event_type="resource_work.deferred",
            reason="host_pressure_still_blocks_focused_validation",
            blocked_reason=str(pressure_snapshot.get("reason") or "host_pressure_blocks_test_build"),
            next_attempt_at=resource_work_queue.compute_backoff_next_attempt_at(item),
            pressure_snapshot=pressure_snapshot,
        )
        return {
            "status": "deferred",
            "queue_id": queue_id,
            "deferred": receipt,
            "action_quote": quote,
        }
    started = resource_work_queue.record_resource_work_event(
        REPO_ROOT,
        queue_id=queue_id,
        event_type="resource_work.started",
        reason="focused_validation_admitted",
        result_summary={"action_quote_status": quote.get("current_status")},
    )
    command = [str(REPO_ROOT / "repo-pytest"), *pytest_args]
    try:
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=max(1, int(getattr(args, "validation_timeout_seconds", 300))),
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        failed = resource_work_queue.record_resource_work_event(
            REPO_ROOT,
            queue_id=queue_id,
            event_type="resource_work.failed",
            reason="focused_validation_timeout",
            error=str(exc),
            result_summary={"command": command, "timeout_seconds": exc.timeout},
        )
        return {"status": "failed", "queue_id": queue_id, "started": started, "failed": failed}
    result_summary = {
        "command": command,
        "returncode": completed.returncode,
        "stdout_tail": _tail_text(completed.stdout),
        "stderr_tail": _tail_text(completed.stderr),
    }
    if completed.returncode == 0:
        succeeded = resource_work_queue.record_resource_work_event(
            REPO_ROOT,
            queue_id=queue_id,
            event_type="resource_work.succeeded",
            reason="focused_validation_passed",
            result_ref=f"focused_pytest:{_short_digest({'argv': command})}:passed",
            result_summary=result_summary,
        )
        return {
            "status": "succeeded",
            "queue_id": queue_id,
            "started": started,
            "succeeded": succeeded,
        }
    failed = resource_work_queue.record_resource_work_event(
        REPO_ROOT,
        queue_id=queue_id,
        event_type="resource_work.failed",
        reason="focused_validation_failed",
        error=f"repo-pytest exited {completed.returncode}",
        result_summary=result_summary,
    )
    return {"status": "failed", "queue_id": queue_id, "started": started, "failed": failed}


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


def _payload_object_field(payload: Mapping[str, Any], field: str, *, command: str) -> Dict[str, Any]:
    value = payload.get(field)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(
            f"{command} payload field '{field}' must be a JSON object when provided; "
            f"got {type(value).__name__}. Put prose labels under a non-reserved key "
            "such as 'source_authority'."
        )
    return dict(value)


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


def _quote_command(parts: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(part)) for part in parts)


def _add_optional_flag(parts: list[str], flag: str, value: Any) -> None:
    text = str(value or "").strip()
    if text:
        parts.extend([flag, text])


def _add_repeated_flag(parts: list[str], flag: str, values: Sequence[Any]) -> None:
    for value in values:
        text = str(value or "").strip()
        if text:
            parts.extend([flag, text])


def _execution_receipt_serial_intake_fallback(args: argparse.Namespace) -> Dict[str, Any]:
    subject_id = str(getattr(args, "subject_id", "") or "").strip()
    transaction_id = str(getattr(args, "transaction_id", "") or "").strip()
    closeout_state = str(getattr(args, "closeout_state", "") or "").strip()
    commit_hash = str(getattr(args, "commit_hash", "") or "").strip()
    idempotency_key = task_ledger_events.execution_receipt_idempotency_key(
        subject_id=subject_id,
        transaction_id=transaction_id,
        commit_hash=commit_hash,
        closeout_state=closeout_state,
        event_type=EVENT_BY_COMMAND["execution-receipt"],
    )
    parts = [
        "./repo-python",
        "tools/meta/factory/task_ledger_apply.py",
        "enqueue-execution-receipt",
    ]
    _add_optional_flag(parts, "--subject-id", subject_id)
    _add_optional_flag(parts, "--transaction-id", transaction_id)
    _add_optional_flag(parts, "--created-by", getattr(args, "created_by", None))
    _add_optional_flag(parts, "--created-at", getattr(args, "created_at", None))
    _add_optional_flag(parts, "--agent-run-id", getattr(args, "agent_run_id", None))
    _add_optional_flag(parts, "--thread-id", getattr(args, "thread_id", None))
    _add_optional_flag(parts, "--work-ledger-session-id", getattr(args, "work_ledger_session_id", None))
    _add_optional_flag(parts, "--read-receipt-id", getattr(args, "read_receipt_id", None))
    _add_optional_flag(parts, "--commit-hash", commit_hash)
    _add_optional_flag(parts, "--read-set-hash", getattr(args, "read_set_hash", None))
    _add_optional_flag(parts, "--write-set-hash", getattr(args, "write_set_hash", None))
    _add_repeated_flag(parts, "--validation-ref", getattr(args, "validation_ref", []) or [])
    _add_repeated_flag(parts, "--projection-ref", getattr(args, "projection_ref", []) or [])
    _add_optional_flag(parts, "--closeout-state", closeout_state)
    _add_optional_flag(parts, "--no-commit-reason", getattr(args, "no_commit_reason", None))
    _add_repeated_flag(parts, "--commit-blocker-ref", getattr(args, "commit_blocker_ref", []) or [])
    _add_optional_flag(parts, "--receipt-schema", getattr(args, "receipt_schema", None))
    _add_optional_flag(parts, "--payload-json", getattr(args, "payload_json", None))
    _add_optional_flag(parts, "--payload-file", getattr(args, "payload_file", None))
    _add_optional_flag(
        parts,
        "--mission-closeout-report-json",
        getattr(args, "mission_closeout_report_json", None),
    )
    _add_optional_flag(
        parts,
        "--mission-closeout-report-file",
        getattr(args, "mission_closeout_report_file", None),
    )
    _add_repeated_flag(parts, "--depends-on", getattr(args, "depends_on", []) or [])
    _add_repeated_flag(parts, "--dependency", getattr(args, "dependency", []) or [])
    payload_stdin_required = bool(getattr(args, "payload_stdin", False))
    if payload_stdin_required:
        parts.append("--payload-stdin")
    return {
        "schema": TASK_LEDGER_EXECUTION_RECEIPT_INTAKE_FALLBACK_SCHEMA,
        "status": "available",
        "reason": "direct_authority_append_blocked_by_preexisting_dirty_task_ledger_authority",
        "idempotency_key": idempotency_key,
        "enqueue_command": _quote_command(parts),
        "intake_status_command": (
            "./repo-python tools/meta/factory/task_ledger_apply.py intake-status "
            f"--idempotency-key {shlex.quote(idempotency_key)}"
        ),
        "drain_command": (
            "./repo-python tools/meta/factory/task_ledger_apply.py drain-intake "
            f"--idempotency-key {shlex.quote(idempotency_key)}"
        ),
        "payload_transfer": (
            "stdin_replay_required" if payload_stdin_required else "command_replays_available_args"
        ),
        "rules": [
            "enqueue-execution-receipt queues the receipt without touching Task Ledger authority logs",
            "queued intake is not applied authority until drain-intake records an applied result",
            "use intake-status or drain-intake with the idempotency key for exact re-entry",
        ],
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
    checkpoint = {
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
    if blocked:
        checkpoint["serial_intake_fallback"] = _execution_receipt_serial_intake_fallback(args)
    return checkpoint


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
    station_render = _station_render_module()
    manifest_path = (
        Path(args.receipt_path)
        if args.receipt_path
        else station_render._manifest_path_for_receipt_ref(args.receipt_ref)
    )
    return manifest_path if manifest_path.is_absolute() else REPO_ROOT / manifest_path


def _promoted_render_evidence_payload(args: argparse.Namespace) -> Dict[str, Any]:
    station_render = _station_render_module()
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
        check_only = bool(args.check or getattr(args, "status_only", False))
        allow_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "rebuild",
            requested=True,
            check=check_only,
        )
        if not allow_rebuild:
            payload = {
                "ok": False,
                "status": "projection_rebuild_deferred_by_host_pressure",
                "projection_rebuild_lease": lease_context,
                "projection_rebuild_deferred": _projection_rebuild_deferred_receipt(
                    lease_context,
                    authority_appended=False,
                    command_name="rebuild",
                    check=check_only,
                ),
            }
            return _print_with_exit_code(payload, work_admission.ADMISSION_TEMPFAIL)
        result = task_ledger_events.rebuild_projections(
            REPO_ROOT,
            check=check_only,
            progress_callback=_progress_callback(args, "rebuild"),
        )
        result["projection_rebuild_lease"] = lease_context
        if getattr(args, "status_only", False):
            result["status_only"] = True
            result["exit_policy"] = (
                "projection_behind_authority_returns_zero_for_status_only"
            )
        _attach_projection_queue_settlement(
            result,
            result,
            command_name="rebuild",
            check=check_only,
        )
        if getattr(args, "status_only", False):
            _repair_projection_behind_authority_next_command(result)
        if (
            getattr(args, "status_only", False)
            and result.get("status") == "projection_behind_authority"
        ):
            return _print_with_exit_code(result, 0)
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_drain_deferred_rebuilds(args: argparse.Namespace) -> int:
    try:
        pending = _pending_task_ledger_projection_rebuilds(limit=args.limit)
        if not pending:
            queue = resource_work_queue.load_resource_work_queue(REPO_ROOT)
            queue_view = _compact_resource_work_queue_view(queue, limit=0)
            return _print(
                {
                    "ok": True,
                    "status": "no_pending_deferred_rebuilds",
                    "pending_count": 0,
                    "queue_scope": _task_ledger_projection_rebuild_queue_scope(pending),
                    "queue": queue_view,
                    "non_matching_pending_count": queue_view.get("pending_count"),
                    "next_step": (
                        "No Task Ledger projection rebuild is queued for this drain command. "
                        "If rebuild --status-only still reports projection_behind_authority, "
                        "run the owner rebuild route; unrelated resource-work queue items are "
                        "shown only as pressure context."
                    ),
                    "safe_next_command": task_ledger_events.TASK_LEDGER_REBUILD_QUIET_COMMAND,
                    "verification_command": (
                        task_ledger_events.TASK_LEDGER_REBUILD_STATUS_ONLY_QUIET_COMMAND
                    ),
                }
            )
        drained: list[Dict[str, Any]] = []
        blocked: list[Dict[str, Any]] = []
        failed: list[Dict[str, Any]] = []
        for item in pending:
            payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
            check = bool(payload.get("check"))
            allow_rebuild, lease_context = _resolve_projection_rebuild_request(
                args,
                "drain-deferred-rebuilds",
                requested=True,
                check=check,
            )
            queue_id = str(item.get("queue_id") or "")
            if not allow_rebuild:
                receipt = resource_work_queue.record_resource_work_event(
                    REPO_ROOT,
                    queue_id=queue_id,
                    event_type="resource_work.deferred",
                    reason="host_pressure_still_blocks_projection_rebuild",
                    lease_context=lease_context or {},
                )
                blocked.append(
                    {
                        "queue_id": queue_id,
                        "projection_rebuild_lease": lease_context,
                        "deferred_receipt": receipt,
                    }
                )
                break
            started = resource_work_queue.record_resource_work_event(
                REPO_ROOT,
                queue_id=queue_id,
                event_type="resource_work.started",
                reason="drain_deferred_rebuilds_admitted",
                lease_context=lease_context or {},
            )
            try:
                projection = task_ledger_events.rebuild_projections(
                    REPO_ROOT,
                    check=check,
                    progress_callback=_progress_callback(args, "drain-deferred-rebuilds"),
                )
            except Exception as exc:
                failed_receipt = resource_work_queue.record_resource_work_event(
                    REPO_ROOT,
                    queue_id=queue_id,
                    event_type="resource_work.failed",
                    reason="task_ledger_projection_rebuild_failed",
                    error=str(exc),
                )
                failed.append(
                    {
                        "queue_id": queue_id,
                        "started": started,
                        "failure": failed_receipt,
                    }
                )
                continue
            succeeded = resource_work_queue.record_resource_work_event(
                REPO_ROOT,
                queue_id=queue_id,
                event_type="resource_work.succeeded",
                reason="drain_deferred_rebuilds_completed",
                result_ref=_projection_queue_result_ref(projection),
                result_summary={
                    "projection_status": projection.get("status"),
                    "projection_ok": projection.get("ok"),
                    "check": check,
                },
            )
            drained.append(
                {
                    "queue_id": queue_id,
                    "started": started,
                    "succeeded": succeeded,
                    "projection": projection,
                }
            )
        exit_code = 0
        status = "drained"
        if blocked and not drained and not failed:
            status = "queue_until_pressure_clears"
            exit_code = work_admission.ADMISSION_TEMPFAIL
        elif failed:
            status = "drained_with_failures" if drained else "failed"
            exit_code = 1
        elif blocked:
            status = "partially_drained_then_blocked"
        payload = {
            "ok": exit_code == 0,
            "status": status,
            "drained_count": len(drained),
            "blocked_count": len(blocked),
            "failed_count": len(failed),
            "drained": drained,
            "blocked": blocked,
            "failed": failed,
            "queue": _compact_resource_work_queue_view(
                resource_work_queue.load_resource_work_queue(REPO_ROOT),
                limit=0,
            ),
        }
        return _print_with_exit_code(payload, exit_code)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def _bounded_resource_work_item_card(item: Mapping[str, Any]) -> dict[str, Any]:
    payload = item.get("payload") if isinstance(item.get("payload"), Mapping) else {}
    source_refs = [str(ref) for ref in item.get("source_refs") or []]
    pytest_args = [str(arg) for arg in payload.get("pytest_args") or []]
    command = str(payload.get("command") or "")
    if len(command) > 240:
        command = command[:237] + "..."
    return {
        "queue_id": item.get("queue_id"),
        "state": item.get("state"),
        "resource_kind": item.get("resource_kind"),
        "work_class": item.get("work_class"),
        "owner_surface": item.get("owner_surface"),
        "action": item.get("action"),
        "handler_id": item.get("handler_id"),
        "priority": item.get("priority"),
        "blocked_reason": item.get("blocked_reason"),
        "next_attempt_at": item.get("next_attempt_at"),
        "attempt_count": item.get("attempt_count"),
        "created_at": item.get("created_at"),
        "updated_at": item.get("updated_at"),
        "owner_session_id": item.get("owner_session_id"),
        "source_ref_count": len(source_refs),
        "source_refs_preview": source_refs[:5],
        "pytest_args_preview": pytest_args[:8],
        "command": command,
    }


def _compact_resource_work_queue_view(view: Mapping[str, Any], *, limit: int) -> dict[str, Any]:
    items = [item for item in view.get("items") or [] if isinstance(item, Mapping)]
    pending = [item for item in items if item.get("state") == "pending"]
    running = [item for item in items if item.get("state") == "running"]
    cards = pending[:limit]
    return {
        "schema": "resource_work_queue_projection_compact_v1",
        "generated_at": view.get("generated_at"),
        "authority": view.get("authority"),
        "item_count": view.get("item_count"),
        "pending_count": view.get("pending_count"),
        "running_count": view.get("running_count"),
        "terminal_count": view.get("terminal_count"),
        "pending_items": [_bounded_resource_work_item_card(item) for item in cards],
        "running_items": [_bounded_resource_work_item_card(item) for item in running[:limit]],
        "pending_items_omitted": max(0, len(pending) - len(cards)),
        "running_items_omitted": max(0, len(running) - min(len(running), limit)),
        "full_status_command": "./repo-python tools/meta/factory/task_ledger_apply.py resource-work-status --full",
    }


def _resource_work_queue_for_output(view: Mapping[str, Any], args: argparse.Namespace) -> Mapping[str, Any]:
    if not getattr(args, "compact", False):
        return view
    compact_limit = max(0, int(getattr(args, "compact_limit", getattr(args, "limit", 12)) or 0))
    return _compact_resource_work_queue_view(view, limit=compact_limit)


def _compact_resource_work_receipt(receipt: Any) -> Any:
    if not isinstance(receipt, Mapping):
        return receipt
    return {
        "schema": receipt.get("schema"),
        "status": receipt.get("status"),
        "queue_id": receipt.get("queue_id"),
        "event_id": receipt.get("event_id"),
        "authority": receipt.get("authority"),
        "projection": receipt.get("projection"),
    }


def _compact_source_status(source_status: Any) -> Any:
    if not isinstance(source_status, Mapping):
        return source_status
    changed_paths = [str(path) for path in source_status.get("changed_paths") or []]
    return {
        "schema": source_status.get("schema"),
        "status": source_status.get("status"),
        "changed_path_count": len(changed_paths),
        "changed_paths": changed_paths[:10],
        "head_changed": source_status.get("head_changed"),
        "original_head": source_status.get("original_head"),
        "current_head": source_status.get("current_head"),
    }


def _compact_resource_work_result(result: Mapping[str, Any]) -> dict[str, Any]:
    compact: dict[str, Any] = {
        "status": result.get("status"),
        "queue_id": result.get("queue_id"),
    }
    if "handler_id" in result:
        compact["handler_id"] = result.get("handler_id")
    if "source_status" in result:
        compact["source_status"] = _compact_source_status(result.get("source_status"))
    for key in ("deferred", "superseded", "started", "succeeded", "failed"):
        if key in result:
            compact[key] = _compact_resource_work_receipt(result.get(key))
    if "action_quote" in result:
        quote = result.get("action_quote")
        if isinstance(quote, Mapping):
            compact["action_quote"] = {
                "current_status": quote.get("current_status"),
                "recommendation": quote.get("recommendation"),
            }
    return compact


def _resource_work_results_for_output(results: Sequence[Mapping[str, Any]], args: argparse.Namespace) -> list[Mapping[str, Any]]:
    if not getattr(args, "compact", False):
        return list(results)
    return [_compact_resource_work_result(result) for result in results]


def _resource_work_status_snapshot() -> dict[str, Any]:
    view = resource_work_queue.load_resource_work_queue(REPO_ROOT)
    has_live_work = bool(view.get("pending_count") or view.get("running_count"))
    operating_picture = resource_work_queue.build_resource_work_queue_operating_picture(
        view,
        pressure_state=_resource_work_pressure_state() if has_live_work else {},
    )
    handler_registry = _resource_work_handler_registry()
    return {
        "view": view,
        "operating_picture": operating_picture,
        "wake_plan": _resource_work_wake_plan(operating_picture, handler_registry),
        "handler_registry": handler_registry,
    }


def _resource_work_controller_counts(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    view = snapshot.get("view") if isinstance(snapshot.get("view"), Mapping) else {}
    operating_picture = (
        snapshot.get("operating_picture")
        if isinstance(snapshot.get("operating_picture"), Mapping)
        else {}
    )
    pressure_state = (
        operating_picture.get("pressure_state")
        if isinstance(operating_picture.get("pressure_state"), Mapping)
        else {}
    )
    return {
        "pending_count": view.get("pending_count"),
        "running_count": view.get("running_count"),
        "terminal_count": view.get("terminal_count"),
        "drain_status": operating_picture.get("drain_status"),
        "drain_next_action": operating_picture.get("drain_next_action"),
        "drain_recommended": operating_picture.get("drain_recommended"),
        "eligible_pending_count": operating_picture.get("eligible_pending_count"),
        "eligible_stale_pending_count": operating_picture.get("eligible_stale_pending_count"),
        "stale_pending_count": operating_picture.get("stale_pending_count"),
        "pressure_decision": pressure_state.get("decision"),
        "pressure_blocks": pressure_state.get("should_block_run"),
        "disk_decision": (
            pressure_state.get("disk_pressure", {}).get("decision")
            if isinstance(pressure_state.get("disk_pressure"), Mapping)
            else None
        ),
    }


def cmd_resource_work_status(args: argparse.Namespace) -> int:
    try:
        snapshot = _resource_work_status_snapshot()
        view = snapshot["view"]
        operating_picture = snapshot["operating_picture"]
        wake_plan = snapshot["wake_plan"]
        handler_registry = snapshot["handler_registry"]
        if not getattr(args, "full", False):
            return _print(
                {
                    "ok": True,
                    "schema": "task_ledger_resource_work_status_compact_v1",
                    "queue": _compact_resource_work_queue_view(
                        view,
                        limit=max(0, int(getattr(args, "limit", 12))),
                    ),
                    "operating_picture": operating_picture,
                    "wake_plan": wake_plan,
                    "handler_registry": handler_registry,
                }
            )
        return _print(
            {
                "ok": True,
                "schema": "task_ledger_resource_work_status_v1",
                "queue": view,
                "operating_picture": operating_picture,
                "wake_plan": wake_plan,
                "handler_registry": handler_registry,
            }
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_queue_focused_validation(args: argparse.Namespace) -> int:
    try:
        pytest_args = _strip_remainder(getattr(args, "pytest_args", []))
        if not pytest_args:
            return _print(
                {
                    "ok": False,
                    "status": "missing_pytest_args",
                    "error": "queue-focused-validation requires pytest args after --",
                }
            )
        receipt = _queue_focused_validation(
            pytest_args=pytest_args,
            source_refs=list(getattr(args, "source_ref", []) or []),
            cap_ids=list(getattr(args, "cap_id", []) or []),
            workitem_refs=list(getattr(args, "work_item_id", []) or []),
            session_id=getattr(args, "session_id", None),
            reason=getattr(args, "reason", None),
            priority=int(getattr(args, "priority", 50)),
            admission_policy=str(getattr(args, "host_pressure_policy", "auto") or "auto"),
            created_by=str(getattr(args, "created_by", "codex") or "codex"),
        )
        return _print(
            {
                "ok": receipt.get("status") == "queued",
                "status": receipt.get("status"),
                "receipt": receipt,
                "queue": _resource_work_queue_for_output(
                    resource_work_queue.load_resource_work_queue(REPO_ROOT),
                    args,
                ),
            }
        )
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def _drain_resource_work_payload(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    try:
        view = resource_work_queue.load_resource_work_queue(REPO_ROOT)
        running = [
            row
            for row in view.get("items", [])
            if row.get("state") == "running"
            and (
                not getattr(args, "handler_id", None)
                or row.get("handler_id") == getattr(args, "handler_id", None)
            )
        ]
        if running and not getattr(args, "ignore_running", False):
            return (
                {
                    "ok": False,
                    "status": "resource_work_drainer_already_running",
                    "running": running[:5],
                    "queue": _resource_work_queue_for_output(view, args),
                },
                work_admission.ADMISSION_TEMPFAIL,
            )
        drain_limit = max(1, int(getattr(args, "limit", 1) or 1))
        pending_limit = drain_limit
        if (
            not getattr(args, "source_check_only", False)
            and getattr(args, "sweep_stale_after_deferred", True)
        ):
            pending_limit = max(
                pending_limit,
                max(0, int(getattr(args, "stale_sweep_limit", 12) or 0)),
            )
        pending = resource_work_queue.pending_resource_work(
            REPO_ROOT,
            handler_id=getattr(args, "handler_id", None),
            eligible_only=True,
            limit=pending_limit,
        )
        if not pending:
            return (
                {
                    "ok": True,
                    "status": "no_eligible_resource_work",
                    "queue": _resource_work_queue_for_output(view, args),
                    "handler_registry": _resource_work_handler_registry(),
                },
                0,
            )
        drained: list[Dict[str, Any]] = []
        deferred: list[Dict[str, Any]] = []
        failed: list[Dict[str, Any]] = []
        superseded: list[Dict[str, Any]] = []
        checked: list[Dict[str, Any]] = []
        seen_work_classes: set[str] = set()
        source_check_args = argparse.Namespace(**vars(args))
        setattr(source_check_args, "source_check_only", True)
        for index, item in enumerate(pending):
            work_class = str(item.get("work_class") or "")
            if (
                not getattr(args, "source_check_only", False)
                and getattr(args, "one_per_class", True)
                and work_class in seen_work_classes
            ):
                continue
            seen_work_classes.add(work_class)
            handler_id = str(item.get("handler_id") or item.get("action") or "")
            if handler_id == FOCUSED_VALIDATION_QUEUE_ACTION:
                result = _drain_focused_validation_item(args, item)
            else:
                result = {
                    "status": "unsupported_handler",
                    "queue_id": item.get("queue_id"),
                    "handler_id": handler_id,
                }
            status = str(result.get("status") or "")
            if status == "deferred":
                deferred.append(result)
                if getattr(args, "stop_on_deferred", True):
                    if (
                        getattr(args, "sweep_stale_after_deferred", True)
                        and not getattr(args, "source_check_only", False)
                    ):
                        for sweep_item in pending[index + 1 :]:
                            sweep_handler_id = str(
                                sweep_item.get("handler_id") or sweep_item.get("action") or ""
                            )
                            if sweep_handler_id != FOCUSED_VALIDATION_QUEUE_ACTION:
                                continue
                            sweep_result = _drain_focused_validation_item(
                                source_check_args,
                                sweep_item,
                            )
                            sweep_status = str(sweep_result.get("status") or "")
                            if sweep_status == "superseded":
                                superseded.append(sweep_result)
                            elif sweep_status == "source_unchanged":
                                checked.append(sweep_result)
                            else:
                                failed.append(sweep_result)
                    break
            elif status == "succeeded":
                drained.append(result)
            elif status == "superseded":
                superseded.append(result)
            elif status == "source_unchanged":
                checked.append(result)
            else:
                failed.append(result)
        exit_code = 0
        status = "drained"
        if deferred and not drained and not failed:
            status = (
                "queue_until_pressure_clears_after_stale_sweep"
                if superseded or checked
                else "queue_until_pressure_clears"
            )
            exit_code = work_admission.ADMISSION_TEMPFAIL
        elif failed:
            status = "drained_with_failures" if drained else "failed"
            exit_code = 1
        elif superseded and not drained:
            status = "superseded"
        elif checked and not drained:
            status = "source_checked"
        elif deferred:
            status = "partially_drained_then_blocked"
        return (
            {
                "ok": exit_code == 0,
                "status": status,
                "drained_count": len(drained),
                "deferred_count": len(deferred),
                "failed_count": len(failed),
                "superseded_count": len(superseded),
                "checked_count": len(checked),
                "drained": _resource_work_results_for_output(drained, args),
                "deferred": _resource_work_results_for_output(deferred, args),
                "failed": _resource_work_results_for_output(failed, args),
                "superseded": _resource_work_results_for_output(superseded, args),
                "checked": _resource_work_results_for_output(checked, args),
                "queue": _resource_work_queue_for_output(
                    resource_work_queue.load_resource_work_queue(REPO_ROOT),
                    args,
                ),
                "handler_registry": _resource_work_handler_registry(),
            },
            exit_code,
        )
    except Exception as exc:
        return {"ok": False, "status": "resource_work_drain_error", "error": str(exc)}, 1


def cmd_drain_resource_work(args: argparse.Namespace) -> int:
    payload, exit_code = _drain_resource_work_payload(args)
    return _print_with_exit_code(payload, exit_code)


def _resource_work_actuator_drain_args(
    args: argparse.Namespace,
    *,
    source_check_only: bool,
    limit: int,
) -> argparse.Namespace:
    drain_args = argparse.Namespace(**vars(args))
    setattr(drain_args, "limit", max(1, int(limit or 1)))
    setattr(drain_args, "source_check_only", bool(source_check_only))
    setattr(drain_args, "ignore_running", False)
    setattr(drain_args, "one_per_class", True)
    setattr(drain_args, "stop_on_deferred", True)
    setattr(drain_args, "sweep_stale_after_deferred", not source_check_only)
    setattr(drain_args, "compact", True)
    setattr(drain_args, "compact_limit", int(getattr(args, "compact_limit", 12) or 12))
    setattr(
        drain_args,
        "validation_timeout_seconds",
        int(getattr(args, "validation_timeout_seconds", 300) or 300),
    )
    return drain_args


def _resource_work_actuator_action_summary(
    *,
    action: str,
    payload: Mapping[str, Any],
    exit_code: int,
) -> dict[str, Any]:
    return {
        "action": action,
        "exit_code": exit_code,
        "status": payload.get("status"),
        "drained_count": int(payload.get("drained_count") or 0),
        "deferred_count": int(payload.get("deferred_count") or 0),
        "failed_count": int(payload.get("failed_count") or 0),
        "superseded_count": int(payload.get("superseded_count") or 0),
        "checked_count": int(payload.get("checked_count") or 0),
    }


def _resource_work_actuator_status(actions: Sequence[Mapping[str, Any]]) -> str:
    if not actions:
        return "no_action"
    if any(int(action.get("failed_count") or 0) for action in actions):
        return "failed"
    if any(int(action.get("deferred_count") or 0) for action in actions):
        return "blocked_after_attempt"
    if any(int(action.get("drained_count") or 0) for action in actions):
        return "drained"
    if any(int(action.get("superseded_count") or 0) for action in actions):
        return "swept"
    if any(int(action.get("checked_count") or 0) for action in actions):
        return "checked"
    return "attempted"


def cmd_actuate_resource_work(args: argparse.Namespace) -> int:
    try:
        before_snapshot = _resource_work_status_snapshot()
        before_counts = _resource_work_controller_counts(before_snapshot)
        operating_picture = before_snapshot["operating_picture"]
        actions: list[dict[str, Any]] = []
        exit_code = 0
        status = "no_action"
        reason = None
        if getattr(args, "dry_run", False):
            status = "dry_run"
            reason = "dry_run_requested"
        elif int(operating_picture.get("running_count") or 0) and not getattr(
            args,
            "ignore_running",
            False,
        ):
            status = "active_drainer_running"
            reason = "resource_work_drainer_already_running"
        elif not bool(operating_picture.get("drain_recommended")):
            status = "no_action"
            reason = str(operating_picture.get("drain_status") or "drain_not_recommended")
        else:
            stale_limit = max(0, int(getattr(args, "stale_sweep_limit", 24) or 0))
            if (
                getattr(args, "source_check_first", True)
                and stale_limit
                and int(operating_picture.get("eligible_stale_pending_count") or 0)
            ):
                sweep_payload, sweep_exit_code = _drain_resource_work_payload(
                    _resource_work_actuator_drain_args(
                        args,
                        source_check_only=True,
                        limit=stale_limit,
                    )
                )
                actions.append(
                    _resource_work_actuator_action_summary(
                        action="source_check_sweep",
                        payload=sweep_payload,
                        exit_code=sweep_exit_code,
                    )
                )
                exit_code = max(exit_code, sweep_exit_code)
            if str(getattr(args, "mode", "throughput") or "throughput") == "throughput":
                after_sweep = _resource_work_status_snapshot()
                after_sweep_picture = after_sweep["operating_picture"]
                if int(after_sweep_picture.get("running_count") or 0):
                    reason = "active_drainer_running_after_sweep"
                elif not bool(after_sweep_picture.get("drain_pressure_blocks")):
                    drain_limit = max(
                        0,
                        int(getattr(args, "max_validation_drains", 1) or 0),
                    )
                    if drain_limit and int(after_sweep_picture.get("eligible_pending_count") or 0):
                        drain_payload, drain_exit_code = _drain_resource_work_payload(
                            _resource_work_actuator_drain_args(
                                args,
                                source_check_only=False,
                                limit=drain_limit,
                            )
                        )
                        actions.append(
                            _resource_work_actuator_action_summary(
                                action="focused_validation_drain",
                                payload=drain_payload,
                                exit_code=drain_exit_code,
                            )
                        )
                        exit_code = max(exit_code, drain_exit_code)
                else:
                    reason = "pressure_gate_blocks_validation_drain"
            status = _resource_work_actuator_status(actions)
        after_snapshot = _resource_work_status_snapshot()
        after_counts = _resource_work_controller_counts(after_snapshot)
        receipt = None
        if not getattr(args, "dry_run", False) and not getattr(args, "no_record", False):
            receipt = resource_work_queue.record_resource_work_controller_event(
                REPO_ROOT,
                controller_id="task_ledger_apply.actuate-resource-work",
                status=status,
                mode=str(getattr(args, "mode", "throughput") or "throughput"),
                reason=reason,
                before=before_counts,
                after=after_counts,
                actions=actions,
                pressure_state=after_snapshot["operating_picture"].get("pressure_state")
                if isinstance(after_snapshot.get("operating_picture"), Mapping)
                else {},
                result_summary={
                    "max_validation_drains": int(
                        getattr(args, "max_validation_drains", 1) or 0
                    ),
                    "stale_sweep_limit": int(getattr(args, "stale_sweep_limit", 24) or 0),
                    "source_check_first": bool(getattr(args, "source_check_first", True)),
                },
            )
            after_snapshot = _resource_work_status_snapshot()
            after_counts = _resource_work_controller_counts(after_snapshot)
        payload = {
            "ok": exit_code == 0,
            "schema": "task_ledger_resource_work_actuator_v1",
            "status": status,
            "mode": str(getattr(args, "mode", "throughput") or "throughput"),
            "reason": reason,
            "exit_code": exit_code,
            "before": before_counts,
            "after": after_counts,
            "actions": actions,
            "controller_receipt": receipt,
            "queue": _resource_work_queue_for_output(after_snapshot["view"], args),
            "wake_plan": after_snapshot["wake_plan"],
            "handler_registry": after_snapshot["handler_registry"],
        }
        return _print_with_exit_code(payload, exit_code)
    except Exception as exc:
        return _print_with_exit_code(
            {"ok": False, "status": "resource_work_actuator_error", "error": str(exc)},
            1,
        )


def cmd_authority_health(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.authority_health(
            REPO_ROOT,
            ids=_parse_ids_arg(args.ids),
            projection_check=bool(args.projection_check),
        )
        authority_storage = task_ledger_events.task_ledger_authority_storage_status(REPO_ROOT)
        payload["authority_storage"] = authority_storage
        payload["resource_pressure"] = {
            "schema": "task_ledger_authority_resource_pressure_v0",
            "status": authority_storage.get("status"),
            "write_admission": authority_storage.get("write_admission"),
            "events_human": authority_storage.get("events_human"),
            "authority_human": authority_storage.get("authority_human"),
            "next_step": authority_storage.get("next_step"),
        }
        return _print(payload)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_authority_migration_plan(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.task_ledger_authority_migration_plan(
            REPO_ROOT,
            max_segment_bytes=args.max_segment_bytes,
            include_audit=not bool(args.skip_audit),
        )
        return _print(payload)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_authority_migration_apply(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.task_ledger_authority_migration_apply(
            REPO_ROOT,
            activate=bool(args.activate),
            max_segment_bytes=args.max_segment_bytes,
            include_audit=not bool(args.skip_audit),
        )
        return _print(payload)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_authority_export_compatibility(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.task_ledger_authority_export_compatibility(REPO_ROOT)
        return _print(payload)
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


def _organizer_report_transcript_admission(args: argparse.Namespace) -> dict[str, Any]:
    requested_limit = max(0, int(getattr(args, "transcript_file_limit", 8) or 0))
    raw_policy = "off" if getattr(args, "ignore_host_pressure", False) else getattr(
        args, "host_pressure_policy", "auto"
    )
    policy = work_admission.normalize_work_admission_policy(str(raw_policy or "auto"))
    base = {
        "schema": "organizer_report_transcript_admission_v1",
        "policy": policy,
        "requested_transcript_file_limit": requested_limit,
        "effective_transcript_file_limit": requested_limit,
        "scan_lane": "adapter_leak_audit",
        "work_class": work_admission.SUMMARY_FIRST_DIAGNOSTIC,
        "reason": None,
        "pressure_state": {},
    }
    if requested_limit == 0:
        return {
            **base,
            "status": "scan_disabled_by_request",
            "reason": "transcript_file_limit_zero",
        }
    if policy == "off":
        return {
            **base,
            "status": "pressure_check_disabled",
            "reason": "host_pressure_policy_off",
        }

    pressure_state = _resource_work_pressure_state()
    pressure_blocks = bool(pressure_state.get("should_block_run"))
    if pressure_blocks and policy == "auto":
        return {
            **base,
            "status": "transcript_scan_deferred_by_host_pressure",
            "effective_transcript_file_limit": 0,
            "reason": pressure_state.get("reason") or "host_pressure_blocks_summary_scan",
            "pressure_state": pressure_state,
            "recheck_command": pressure_state.get("recheck_command"),
            "override": (
                "--host-pressure-policy warn to run the bounded transcript scan with a warning; "
                "--ignore-host-pressure to bypass the check"
            ),
        }
    if pressure_blocks:
        return {
            **base,
            "status": "pressure_warning_scan_allowed",
            "reason": pressure_state.get("reason") or "host_pressure_warn_policy_allows_scan",
            "pressure_state": pressure_state,
            "recheck_command": pressure_state.get("recheck_command"),
        }
    return {
        **base,
        "status": "scan_allowed",
        "reason": pressure_state.get("reason") or "host_pressure_allows_summary_scan",
        "pressure_state": pressure_state,
        "recheck_command": pressure_state.get("recheck_command"),
    }


def cmd_organizer_report(args: argparse.Namespace) -> int:
    try:
        transcript_admission = _organizer_report_transcript_admission(args)
        transcript_file_limit = int(
            transcript_admission.get("effective_transcript_file_limit") or 0
        )
        report = task_ledger_events.build_organizer_report(
            REPO_ROOT,
            transcript_file_limit=transcript_file_limit,
            detail=args.detail,
        )
        report["organizer_report_admission"] = transcript_admission
        return _print(
            report
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


def _normalize_quick_capture_tags(
    preferred_tags: Sequence[str],
    compatibility_tags: Sequence[str],
) -> List[str]:
    normalized: List[str] = []
    seen: set[str] = set()
    for raw in list(preferred_tags or []) + list(compatibility_tags or []):
        for tag in str(raw or "").split(","):
            token = tag.strip()
            if not token or token in seen:
                continue
            normalized.append(token)
            seen.add(token)
    return normalized


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
        summary_text = _text_arg(args, "summary")
        if statement_text and summary_text:
            raise ValueError("--statement and --summary are aliases; provide only one")
        statement_text = statement_text or summary_text
        problem = str(_text_arg(args, "problem") or "").strip()
        impact = str(_text_arg(args, "impact") or "").strip()
        acceptance = str(_text_arg(args, "acceptance") or "").strip()
        evidence = [str(item).strip() for item in getattr(args, "evidence", []) if str(item).strip()]
        legacy_title = str(getattr(args, "legacy_title", None) or "").strip()
        title = str(args.title or legacy_title or "").strip()
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
        tags = _normalize_quick_capture_tags(
            getattr(args, "tag", []) or [],
            getattr(args, "tags", []) or [],
        )
        if tags:
            payload.setdefault("tags", tags)
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
            integration = _payload_object_field(
                payload,
                "integration_contract",
                command="quick-capture",
            )
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
            refs = _payload_object_field(payload, "refs", command="quick-capture")
            refs.setdefault("source_refs", args.source_ref)
            payload["refs"] = refs
            provenance = _payload_object_field(payload, "provenance", command="quick-capture")
            provenance.setdefault("source_refs", args.source_ref)
            payload["provenance"] = provenance
        if args.surface:
            integration = _payload_object_field(
                payload,
                "integration_contract",
                command="quick-capture",
            )
            discovered = list(integration.get("exact_surfaces_discovered") or [])
            for surface in args.surface:
                discovered.append(_quick_capture_surface_entry(surface))
            integration["exact_surfaces_discovered"] = discovered
            payload["integration_contract"] = integration
        payload.setdefault("authority", {})
        authority = _payload_object_field(payload, "authority", command="quick-capture")
        authority.setdefault("work_authority", str(task_ledger_events.EVENTS_REL))
        authority.setdefault("capture_mode", "quick_capture_low_ceremony")
        payload["authority"] = authority
        payload.setdefault("completion", {})
        completion = _payload_object_field(payload, "completion", command="quick-capture")
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
        provenance = _payload_object_field(payload, "provenance", command="quick-capture")
        provenance.setdefault("source_kind", args.source_kind)
        provenance.setdefault("capture_affordance", "task_ledger_apply.quick_capture")
        if legacy_title and not args.title:
            compatibility_aliases = list(provenance.get("compatibility_aliases") or [])
            if "quick_capture_positional_title" not in compatibility_aliases:
                compatibility_aliases.append("quick_capture_positional_title")
            provenance["compatibility_aliases"] = compatibility_aliases
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
        requested_rebuild = bool(args.rebuild)
        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "quick-capture",
            requested=requested_rebuild,
        )
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=effective_rebuild,
            fast_unique_capture_append=bool(not args.event_id and not effective_rebuild),
            progress_callback=(
                _progress_callback(args, "quick-capture") if effective_rebuild else None
            ),
        )
        projection_result = result.get("projection") if effective_rebuild else None
        _attach_projection_queue_settlement(
            result,
            projection_result,
            command_name="quick-capture",
        )
        if requested_rebuild:
            result["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(result.get("ok", True)),
            command_name="quick-capture",
        )
        if deferred_receipt:
            result["projection_rebuild_deferred"] = deferred_receipt
        result["quick_capture"] = {
            "subject_id": event["subject_id"],
            "source_refs": source_refs,
            "next_action": "triage, merge, promote, retire, or leave as capture inbox material",
        }
        appended_event = result.get("event") if isinstance(result.get("event"), dict) else {}
        selected_event_ids = [str(appended_event.get("event_id") or event.get("event_id") or "")]
        authority_health_hint = (
            task_ledger_events.authority_health_hint_from_append_result(
                REPO_ROOT,
                result,
                event_ids=selected_event_ids,
            )
            if projection_result is None
            else None
        )
        result["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(event["subject_id"])],
            event_ids=selected_event_ids,
            projection_result=projection_result,
            projection_rebuild_deferred=deferred_receipt,
            authority_health_hint=authority_health_hint,
        )
        if getattr(args, "compact", False):
            return _print(_compact_quick_capture_result(result))
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
            payload.setdefault("reason", _text_arg(args, "reason"))
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
                    "idempotency_status": receipt_reconcile.get("idempotency_status") or "duplicate_noop",
                    "receipt_reconcile": receipt_reconcile,
                }
                effective_rebuild, lease_context = _resolve_projection_rebuild_request(
                    args,
                    args.command_name,
                    requested=bool(args.rebuild),
                )
                if args.rebuild:
                    result["projection_rebuild_lease"] = lease_context
                if effective_rebuild:
                    result["projection"] = task_ledger_events.rebuild_projections(
                        REPO_ROOT,
                        progress_callback=_progress_callback(args, args.command_name),
                    )
                    _attach_projection_queue_settlement(
                        result,
                        result.get("projection") if isinstance(result.get("projection"), dict) else None,
                        command_name=args.command_name,
                    )
                deferred_receipt = _projection_rebuild_deferred_receipt(
                    lease_context,
                    authority_appended=False,
                    command_name=args.command_name,
                )
                if deferred_receipt:
                    result["projection_rebuild_deferred"] = deferred_receipt
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
        requested_rebuild = bool(args.rebuild)
        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            args.command_name,
            requested=requested_rebuild,
        )
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=effective_rebuild,
            progress_callback=(
                _progress_callback(args, args.command_name) if effective_rebuild else None
            ),
        )
        projection_result = result.get("projection") if effective_rebuild else None
        _attach_projection_queue_settlement(
            result,
            projection_result,
            command_name=args.command_name,
        )
        if requested_rebuild:
            result["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(result.get("ok", True)),
            command_name=args.command_name,
        )
        if deferred_receipt:
            result["projection_rebuild_deferred"] = deferred_receipt
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
            projection_rebuild_deferred=deferred_receipt,
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
        requested_rebuild = bool(args.rebuild)
        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "attach-promoted-render-receipt",
            requested=requested_rebuild,
        )
        result = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=effective_rebuild,
            progress_callback=(
                _progress_callback(args, "attach-promoted-render-receipt")
                if effective_rebuild
                else None
            ),
        )
        projection_result = result.get("projection") if effective_rebuild else None
        _attach_projection_queue_settlement(
            result,
            projection_result,
            command_name="attach-promoted-render-receipt",
        )
        if requested_rebuild:
            result["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(result.get("ok", True)),
            command_name="attach-promoted-render-receipt",
        )
        if deferred_receipt:
            result["projection_rebuild_deferred"] = deferred_receipt
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
            projection_rebuild_deferred=deferred_receipt,
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

        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "batch",
            requested=rebuild_at_end,
        )
        batch_append = task_ledger_events.append_events_and_rebuild(
            REPO_ROOT,
            [row["event"] for row in append_requests],
            rebuild=effective_rebuild,
            progress_callback=_progress_callback(args, "batch") if effective_rebuild else None,
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
        projection_result = batch_append.get("projection") if effective_rebuild else None
        if projection_result is not None:
            out["projection"] = projection_result
        _attach_projection_queue_settlement(
            out,
            projection_result,
            command_name="batch",
        )
        if rebuild_at_end:
            out["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(batch_append.get("ok", True)),
            command_name="batch",
        )
        if deferred_receipt:
            out["projection_rebuild_deferred"] = deferred_receipt
        out["task_ledger_mutation_serialization"] = batch_append.get("task_ledger_mutation_serialization")
        out["visibility_receipt"] = _visibility_receipt(
            subject_ids=[str(row.get("subject_id") or "") for row in appended],
            event_ids=[str(row.get("event_id") or "") for row in appended],
            projection_result=projection_result,
            projection_rebuild_deferred=deferred_receipt,
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
        requested_rebuild = not bool(args.no_rebuild)
        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "drain-intake",
            requested=requested_rebuild,
        )
        result = task_ledger_events.drain_task_ledger_intake(
            REPO_ROOT,
            limit=args.limit,
            created_by=args.created_by,
            rebuild=effective_rebuild,
            request_ids=args.request_id,
            idempotency_keys=args.idempotency_key,
        )
        projection_result = result.get("projection") if effective_rebuild else None
        _attach_projection_queue_settlement(
            result,
            projection_result if isinstance(projection_result, dict) else None,
            command_name="drain-intake",
        )
        if requested_rebuild:
            result["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(result.get("ok", True)),
            command_name="drain-intake",
        )
        if deferred_receipt:
            result["projection_rebuild_deferred"] = deferred_receipt
        return _print(result)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})


def cmd_intake_status(args: argparse.Namespace) -> int:
    try:
        return _print(
            task_ledger_events.task_ledger_intake_status(
                REPO_ROOT,
                request_ids=args.request_id,
                idempotency_keys=args.idempotency_key,
                full=args.full,
                limit=args.limit,
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
        status = _work_ledger_runtime_module().load_runtime_status(REPO_ROOT)
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
    if _work_ledger_module().TD_ID_RE.fullmatch(target_id):
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
        closeout_assurance_claim = getattr(args, "closeout_assurance_claim", None)
        closeout_assurance_evidence_ref = getattr(args, "closeout_assurance_evidence_ref", [])
        closeout_assurance_strength = getattr(args, "closeout_assurance_strength", None)
        closeout_assurance_counterexample_check = getattr(
            args, "closeout_assurance_counterexample_check", []
        )
        closeout_assurance_owner_surface = getattr(args, "closeout_assurance_owner_surface", None)
        closeout_assurance_owner_surface_changed = getattr(
            args, "closeout_assurance_owner_surface_changed", []
        )
        closeout_assurance_residual = getattr(args, "closeout_assurance_residual", [])
        closeout_assurance_no_residuals = bool(
            getattr(args, "closeout_assurance_no_residuals", False)
        )

        closeout_assurance: dict[str, Any] = {}
        if closeout_assurance_claim:
            closeout_assurance["claim"] = closeout_assurance_claim
        if closeout_assurance_evidence_ref:
            closeout_assurance["evidence_refs"] = closeout_assurance_evidence_ref
        if closeout_assurance_strength:
            closeout_assurance["corrective_action_strength"] = closeout_assurance_strength
        if closeout_assurance_counterexample_check:
            closeout_assurance["counterexample_checks"] = closeout_assurance_counterexample_check
        if closeout_assurance_owner_surface:
            closeout_assurance["owner_surface"] = closeout_assurance_owner_surface
        if closeout_assurance_owner_surface_changed:
            closeout_assurance["owner_surfaces_changed"] = closeout_assurance_owner_surface_changed
        if (
            closeout_assurance
            or closeout_assurance_residual
            or closeout_assurance_no_residuals
        ):
            closeout_assurance["residuals"] = closeout_assurance_residual
        if closeout_assurance:
            signoff["closeout_assurance"] = task_ledger_events._normalize_closeout_assurance(
                closeout_assurance
            )
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
        effective_rebuild, lease_context = _resolve_projection_rebuild_request(
            args,
            "closeout-slice",
            requested=True,
        )
        append = task_ledger_events.append_event_and_rebuild(
            REPO_ROOT,
            event,
            expected_previous_event_hash=args.expected_previous_event_hash,
            rebuild=effective_rebuild,
            progress_callback=_progress_callback(args, "closeout-slice")
            if effective_rebuild
            else None,
        )
        rebuild = append.get("projection") if effective_rebuild else None
        _attach_projection_queue_settlement(
            append,
            rebuild if isinstance(rebuild, dict) else None,
            command_name="closeout-slice",
        )
        append["projection_rebuild_lease"] = lease_context
        deferred_receipt = _projection_rebuild_deferred_receipt(
            lease_context,
            authority_appended=bool(append.get("ok", True)),
            command_name="closeout-slice",
        )
        if deferred_receipt:
            append["projection_rebuild_deferred"] = deferred_receipt
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
                    projection_rebuild_deferred=deferred_receipt,
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
    _add_projection_rebuild_admission_args(parser)
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


def _add_projection_rebuild_admission_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--projection-rebuild-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default=None,
        help=(
            "Host-pressure policy for Task Ledger projection rebuilds. Defaults to "
            f"{TASK_LEDGER_REBUILD_PRESSURE_POLICY_ENV_VAR} or auto."
        ),
    )
    parser.add_argument(
        "--ignore-host-pressure",
        action="store_true",
        help="Compatibility alias for --projection-rebuild-policy off.",
    )


def _add_text_input_args(
    parser: argparse.ArgumentParser,
    name: str,
    *,
    required: bool = False,
    help_text: str | None = None,
    aliases: Sequence[str] | None = None,
) -> None:
    option = name.replace("_", "-")
    alias_options = [alias.replace("_", "-") for alias in aliases or ()]
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument(
        *[f"--{item}" for item in [option, *alias_options]],
        dest=name,
        default=None,
        help=help_text or f"Inline {option} text.",
    )
    group.add_argument(
        *[f"--{item}-file" for item in [option, *alias_options]],
        dest=f"{name}_file",
        default=None,
        help=(
            f"Read {option} text from a UTF-8 file. Use this for prose with "
            "quotes, backticks, parentheses, or shell-sensitive tokens. Use one "
            "unique file path per concurrent command."
        ),
    )
    group.add_argument(
        *[f"--{item}-stdin" for item in [option, *alias_options]],
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
    parser.add_argument(
        "--validation-ref",
        action="append",
        default=[],
        help=(
            "Focused validation, diff check, builder check, or receipt ref proving the "
            "closeout state. Required for validated-uncommitted closeouts."
        ),
    )
    parser.add_argument("--projection-ref", action="append", default=[])
    parser.add_argument(
        "--closeout-state",
        default="recorded",
        help=(
            "Use validated_uncommitted_git_metadata_blocked only for accepted "
            "commitless closeouts such as exhausted scoped-commit HEAD-CAS retry."
        ),
    )
    parser.add_argument(
        "--no-commit-reason",
        default=None,
        help=(
            "Required when commit_hash is absent; name the git-metadata blocker "
            "instead of implying a landed scoped commit."
        ),
    )
    parser.add_argument(
        "--commit-blocker-ref",
        action="append",
        default=[],
        help="Evidence ref for the parent-CAS loss, metadata blocker, or retry packet.",
    )
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
        epilog="\n\n".join(
            [
                _TASK_LEDGER_PARALLEL_SAFETY_NOTE,
                _TASK_LEDGER_QUICK_CAPTURE_POSITIONAL_TITLE_HINT,
                _TASK_LEDGER_QUICK_CAPTURE_REBUILD_ECONOMY_HINT,
            ]
        ),
    )
    quick.add_argument("legacy_title", nargs="?", help=argparse.SUPPRESS)
    quick.add_argument("--title", required=False)
    _add_text_input_args(quick, "statement", help_text="Inline statement text.")
    _add_text_input_args(
        quick,
        "summary",
        help_text="Compatibility alias for inline statement text. Also accepts --description.",
        aliases=("description",),
    )
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
    quick.add_argument(
        "--tags",
        action="append",
        default=[],
        help=(
            "Compatibility alias for --tag. Repeatable; comma-separated values "
            "are normalized into the same tags payload field."
        ),
    )
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
    quick.add_argument(
        "--rebuild",
        action="store_true",
        help=(
            "Refresh Task Ledger projections after appending so the captured card is "
            "visible immediately. Omit for capture-before-prose authority visibility; "
            "use rebuild --status-only --quiet-progress before full refreshes."
        ),
    )
    _add_projection_rebuild_admission_args(quick)
    quick.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during --rebuild phases.",
    )
    quick.add_argument(
        "--compact",
        action="store_true",
        help=(
            "Emit a bounded receipt with authority ids and visibility scalars instead of "
            "the full event/projection payload."
        ),
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
        elif name in {"execution-receipt", "record-execution-receipt"}:
            parser_kwargs.update(
                {
                    "formatter_class": argparse.RawDescriptionHelpFormatter,
                    "epilog": _TASK_LEDGER_EXECUTION_RECEIPT_HINT,
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
            _add_text_input_args(event_parser, "reason", help_text="Inline reason text.")
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
        choices=PROMOTED_RENDER_RECEIPT_STATUSES,
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
        "--status-only",
        action="store_true",
        help=(
            "Run the read-only projection check and return process exit 0 for the expected "
            "projection_behind_authority status while preserving the strict payload."
        ),
    )
    _add_projection_rebuild_admission_args(rebuild)
    rebuild.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during rebuild phases.",
    )
    rebuild.set_defaults(func=cmd_rebuild)

    drain_rebuilds = subparsers.add_parser(
        "drain-deferred-rebuilds",
        help=(
            "Drain queued Task Ledger projection rebuilds when the generated_projection_builder "
            "lease is admitted."
        ),
    )
    drain_rebuilds.add_argument("--limit", type=int, default=1)
    _add_projection_rebuild_admission_args(drain_rebuilds)
    drain_rebuilds.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Suppress stderr JSONL progress emitted during queued rebuild drains.",
    )
    drain_rebuilds.set_defaults(func=cmd_drain_deferred_rebuilds)

    resource_work_status = subparsers.add_parser(
        "resource-work-status",
        help="Print queued resource work, operating-picture counts, and typed handler registry.",
    )
    resource_work_status.add_argument(
        "--compact",
        action="store_true",
        help="Compatibility no-op: resource-work-status defaults to bounded queue cards.",
    )
    resource_work_status.add_argument(
        "--full",
        action="store_true",
        help="Emit full queued item payloads and source snapshots. Defaults to compact bounded cards.",
    )
    resource_work_status.add_argument(
        "--limit",
        type=int,
        default=12,
        help="Maximum pending and running item cards to include when --full is not set.",
    )
    resource_work_status.set_defaults(func=cmd_resource_work_status)

    actuate_resource = subparsers.add_parser(
        "actuate-resource-work",
        help=(
            "Close the resource-work liveness loop: source-check stale queued work first, "
            "then optionally drain a bounded focused validation under admission."
        ),
    )
    actuate_resource.add_argument(
        "--mode",
        choices=("throughput", "source-check-only"),
        default="throughput",
    )
    actuate_resource.add_argument(
        "--handler-id",
        default=FOCUSED_VALIDATION_QUEUE_ACTION,
    )
    actuate_resource.add_argument("--session-id", default=None)
    actuate_resource.add_argument("--validation-timeout-seconds", type=int, default=300)
    actuate_resource.add_argument("--ignore-running", action="store_true")
    actuate_resource.add_argument(
        "--stale-sweep-limit",
        type=int,
        default=24,
        help="Maximum queued focused-validation items to source-check before any validation drain.",
    )
    actuate_resource.add_argument(
        "--max-validation-drains",
        type=int,
        default=1,
        help="Maximum focused validations to launch after stale source cleanup in throughput mode.",
    )
    actuate_resource.add_argument("--source-check-first", action="store_true", default=True)
    actuate_resource.add_argument(
        "--no-source-check-first",
        dest="source_check_first",
        action="store_false",
    )
    actuate_resource.add_argument("--dry-run", action="store_true")
    actuate_resource.add_argument("--no-record", action="store_true")
    actuate_resource.add_argument(
        "--compact",
        action="store_true",
        help="Print a compact queue projection instead of full queued item payloads.",
    )
    actuate_resource.add_argument(
        "--compact-limit",
        type=int,
        default=12,
        help="Maximum pending and running item cards to include with --compact.",
    )
    actuate_resource.set_defaults(func=cmd_actuate_resource_work)

    queue_validation = subparsers.add_parser(
        "queue-focused-validation",
        help=(
            "Queue a focused pytest validation through the resource-work queue instead of "
            "losing it as a CAP-only deferred test."
        ),
    )
    queue_validation.add_argument("--created-by", default="codex")
    queue_validation.add_argument("--cap-id", action="append", default=[])
    queue_validation.add_argument("--work-item-id", action="append", default=[])
    queue_validation.add_argument("--source-ref", action="append", default=[])
    queue_validation.add_argument("--session-id", default=None)
    queue_validation.add_argument("--reason", default=None)
    queue_validation.add_argument("--priority", type=int, default=50)
    queue_validation.add_argument(
        "--host-pressure-policy",
        choices=work_admission.ADMISSION_POLICY_VALUES,
        default="auto",
    )
    queue_validation.add_argument(
        "--compact",
        action="store_true",
        help="Print a compact queue projection in the receipt instead of full queued item payloads.",
    )
    queue_validation.add_argument(
        "--compact-limit",
        type=int,
        default=12,
        help="Maximum pending and running item cards to include with --compact.",
    )
    queue_validation.add_argument(
        "pytest_args",
        nargs=argparse.REMAINDER,
        help="Focused pytest args after --, for example: -- system/server/tests/test_x.py -q",
    )
    queue_validation.set_defaults(func=cmd_queue_focused_validation)

    drain_resource = subparsers.add_parser(
        "drain-resource-work",
        help="Drain typed resource-work queue items with admission recheck and singleflight guard.",
    )
    drain_resource.add_argument("--limit", type=int, default=1)
    drain_resource.add_argument("--handler-id", default=None)
    drain_resource.add_argument("--session-id", default=None)
    drain_resource.add_argument("--validation-timeout-seconds", type=int, default=300)
    drain_resource.add_argument("--ignore-running", action="store_true")
    drain_resource.add_argument("--one-per-class", action="store_true", default=True)
    drain_resource.add_argument("--no-one-per-class", dest="one_per_class", action="store_false")
    drain_resource.add_argument("--stop-on-deferred", action="store_true", default=True)
    drain_resource.add_argument("--no-stop-on-deferred", dest="stop_on_deferred", action="store_false")
    drain_resource.add_argument(
        "--sweep-stale-after-deferred",
        dest="sweep_stale_after_deferred",
        action="store_true",
        default=True,
        help="After a pressure-deferred focused validation, source-check the rest of the bounded batch for stale items.",
    )
    drain_resource.add_argument(
        "--no-sweep-stale-after-deferred",
        dest="sweep_stale_after_deferred",
        action="store_false",
    )
    drain_resource.add_argument(
        "--stale-sweep-limit",
        type=int,
        default=12,
        help=(
            "Maximum focused-validation items to source-check after a pressure defer; "
            "does not increase admitted validation runs."
        ),
    )
    drain_resource.add_argument(
        "--source-check-only",
        "--stale-sweep",
        dest="source_check_only",
        action="store_true",
        help=(
            "Only compare queued focused-validation source snapshots and supersede stale items; "
            "do not request host-pressure admission or launch pytest."
        ),
    )
    drain_resource.add_argument(
        "--compact",
        action="store_true",
        help="Print a compact queue projection instead of full queued item payloads.",
    )
    drain_resource.add_argument(
        "--compact-limit",
        type=int,
        default=12,
        help="Maximum pending and running item cards to include with --compact.",
    )
    drain_resource.set_defaults(func=cmd_drain_resource_work)

    authority_health = subparsers.add_parser(
        "authority-health",
        help="Report whether events_audit.jsonl contains events missing from events.jsonl.",
    )
    authority_health.add_argument("--ids", default=None, help="Optional comma/space-separated WorkItem ids to check for card visibility.")
    authority_health.add_argument("--projection-check", action="store_true", help="Also check whether deterministic projections match events.jsonl.")
    authority_health.add_argument("--json", action="store_true", help="Compatibility no-op; output is already JSON.")
    authority_health.add_argument(
        "--quiet-progress",
        action="store_true",
        help="Compatibility no-op; authority-health does not emit rebuild progress.",
    )
    authority_health.set_defaults(func=cmd_authority_health)

    authority_migration = subparsers.add_parser(
        "authority-migration-plan",
        help=(
            "Dry-run a segmented authority-storage migration plan without changing "
            "events.jsonl, events_audit.jsonl, projections, or append writers."
        ),
    )
    authority_migration.add_argument(
        "--max-segment-bytes",
        type=int,
        default=None,
        help=(
            "Maximum normalized JSONL bytes per proposed closed segment. Defaults to "
            "AIW_TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES or 8 MiB."
        ),
    )
    authority_migration.add_argument(
        "--skip-audit",
        action="store_true",
        help="Do not include events_audit.jsonl in the dry-run co-migration plan.",
    )
    authority_migration.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; output is already JSON.",
    )
    authority_migration.set_defaults(func=cmd_authority_migration_plan)

    authority_migration_apply = subparsers.add_parser(
        "authority-migration-apply",
        help=(
            "Materialize segmented Task Ledger authority under the ledger lock; "
            "--prepare keeps legacy writer mode, --activate cuts ordinary appends "
            "over to the segmented open tail."
        ),
    )
    mode_group = authority_migration_apply.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--prepare",
        action="store_true",
        help="Materialize segments and manifest without writer cutover. This is the default.",
    )
    mode_group.add_argument(
        "--activate",
        action="store_true",
        help="Materialize if needed, then enable active_segmented writer mode.",
    )
    authority_migration_apply.add_argument(
        "--max-segment-bytes",
        type=int,
        default=None,
        help=(
            "Maximum normalized JSONL bytes per closed segment. Defaults to "
            "AIW_TASK_LEDGER_AUTHORITY_MIGRATION_SEGMENT_BYTES or 8 MiB."
        ),
    )
    authority_migration_apply.add_argument(
        "--skip-audit",
        action="store_true",
        help="Do not include events_audit.jsonl in the segmented materialization.",
    )
    authority_migration_apply.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; output is already JSON.",
    )
    authority_migration_apply.set_defaults(func=cmd_authority_migration_apply)

    authority_export = subparsers.add_parser(
        "authority-export-compatibility",
        help=(
            "Regenerate events.jsonl/events_audit.jsonl compatibility exports from "
            "active segmented authority. Ordinary appends do not run this."
        ),
    )
    authority_export.add_argument(
        "--json",
        action="store_true",
        help="Compatibility no-op; output is already JSON.",
    )
    authority_export.set_defaults(func=cmd_authority_export_compatibility)

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
        "--host-pressure-policy",
        choices=("auto", "warn", "off"),
        default="auto",
        help=(
            "Host-pressure policy for the bounded transcript scan. In auto mode, "
            "organizer-report still returns the projection summary but skips adapter "
            "transcript scanning when admission says heavy work should queue."
        ),
    )
    organizer.add_argument(
        "--ignore-host-pressure",
        action="store_true",
        help="Compatibility alias for --host-pressure-policy off.",
    )
    organizer.add_argument(
        "--detail",
        choices=("compact", "full"),
        default="compact",
        help="Use compact first-read output by default; use full for complete samples and adapter audit examples.",
    )
    organizer.add_argument("--json", action="store_true", help="Compatibility no-op; output is already JSON.")
    organizer.add_argument(
        "--top",
        type=int,
        default=None,
        help="Compatibility no-op for status-style callers; compact organizer output uses built-in bounded samples.",
    )
    organizer.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Compatibility no-op for status-style callers; compact organizer output uses built-in bounded samples.",
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
    closeout.add_argument("--closeout-assurance-claim", default=None)
    closeout.add_argument("--closeout-assurance-evidence-ref", action="append", default=[])
    closeout.add_argument(
        "--closeout-assurance-strength",
        choices=["weak", "medium", "strong", "very_strong"],
        default=None,
    )
    closeout.add_argument("--closeout-assurance-counterexample-check", action="append", default=[])
    closeout.add_argument("--closeout-assurance-owner-surface", default=None)
    closeout.add_argument("--closeout-assurance-owner-surface-changed", action="append", default=[])
    closeout.add_argument("--closeout-assurance-residual", action="append", default=[])
    closeout.add_argument(
        "--closeout-assurance-no-residuals",
        action="store_true",
        help="Include an explicit empty residuals list for high-risk closeout assurance.",
    )
    closeout.add_argument("--work-ledger-session-id", default=None)
    closeout.add_argument("--work-ledger-td-id", default=None)
    closeout.add_argument("--read-receipt-id", default=None)
    closeout.add_argument("--phase-id", default=None)
    closeout.add_argument("--family-id", default=None)
    closeout.add_argument("--claims-released", action="store_true")
    closeout.add_argument("--validate", action="store_true", default=True)
    _add_projection_rebuild_admission_args(closeout)
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
    _add_projection_rebuild_admission_args(batch)
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
    _add_projection_rebuild_admission_args(drain)
    drain.add_argument(
        "--quiet-progress",
        action="store_true",
        help=(
            "Compatibility flag accepted for parity with other Task Ledger mutation "
            "commands; drain-intake does not emit progress for its rebuild path."
        ),
    )
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
    intake_status.add_argument(
        "--full",
        action="store_true",
        help="Emit full intake request bodies. Defaults to compact bounded cards.",
    )
    intake_status.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum compact request cards to emit when --full is not set.",
    )
    intake_status.set_defaults(func=cmd_intake_status)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
