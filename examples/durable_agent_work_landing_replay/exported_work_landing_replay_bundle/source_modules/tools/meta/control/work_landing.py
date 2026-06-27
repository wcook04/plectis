#!/usr/bin/env python3
"""WorkItem landing status and opt-in reconcile controller surface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.work_landing_status import (  # noqa: E402
    build_work_landing_attempt_binding,
    build_work_landing_reconcile_plan,
    build_work_landing_status,
    build_workitem_write_admission,
)
from system.lib import work_ledger_runtime  # noqa: E402


_STEP_RESULT_KEYS = (
    "ok",
    "status",
    "mutated",
    "mutated_steps",
    "idempotency_key",
    "commit_hash",
    "transaction_id",
    "td_id",
    "session_id",
    "request_id",
    "request_path",
    "work_ledger_event_id",
    "read_receipt_id",
    "task_ledger_receipt_event_id",
    "projection_rebuild",
    "elapsed_ms",
)


def _compact_step_result(result: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(result, Mapping):
        return {}
    compact = {key: result.get(key) for key in _STEP_RESULT_KEYS if key in result}
    receipt_reconcile = result.get("receipt_reconcile")
    if isinstance(receipt_reconcile, Mapping):
        compact["receipt_reconcile"] = {
            key: receipt_reconcile.get(key)
            for key in ("ok", "status", "alias_status", "closeout_state")
            if key in receipt_reconcile
        }
    runtime_append_mark = result.get("runtime_append_mark")
    if isinstance(runtime_append_mark, Mapping):
        compact["runtime_append_mark"] = {
            key: runtime_append_mark.get(key)
            for key in ("ok", "status", "session_id", "read_receipt_id")
            if key in runtime_append_mark
        }
    step_elapsed_ms = result.get("step_elapsed_ms")
    if isinstance(step_elapsed_ms, Mapping):
        compact["step_elapsed_ms"] = dict(step_elapsed_ms)
    step_results = result.get("step_results")
    if isinstance(step_results, Mapping):
        compact["step_results"] = {
            str(step_name): _compact_step_result(step_result)
            for step_name, step_result in step_results.items()
            if isinstance(step_result, Mapping)
        }
    final_state = result.get("final_state")
    if isinstance(final_state, Mapping):
        compact["final_state"] = {
            key: final_state.get(key)
            for key in ("apply_status", "blocked_by")
            if key in final_state
        }
    return compact


def _compact_reconcile_action(action: Mapping[str, Any]) -> dict[str, Any]:
    compact = {
        key: action.get(key)
        for key in (
            "action_id",
            "sequence",
            "owner_plane",
            "apply_supported",
            "apply_status",
            "would_mutate",
            "blocked_by",
            "command_or_function",
        )
        if key in action
    }
    apply_result = action.get("apply_result")
    if isinstance(apply_result, Mapping):
        compact["apply_result"] = _compact_step_result(apply_result)
    return compact


def _compact_reconcile_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    actions = payload.get("actions") if isinstance(payload.get("actions"), list) else []
    return {
        "schema": "work_landing_reconcile_cli_compact_v0",
        "full_schema": payload.get("schema"),
        "mode": payload.get("mode"),
        "status": payload.get("status"),
        "subject_ids": payload.get("subject_ids") or [],
        "transaction_id": payload.get("transaction_id"),
        "recommended_next_action": payload.get("recommended_next_action"),
        "action_count": len(actions),
        "actions": [
            _compact_reconcile_action(action)
            for action in actions
            if isinstance(action, Mapping)
        ],
        "apply_result": (
            _compact_step_result(payload.get("apply_result"))
            if isinstance(payload.get("apply_result"), Mapping)
            else None
        ),
        "post_apply_status_refresh": payload.get("post_apply_status_refresh"),
        "mutation_policy": payload.get("mutation_policy") or {},
        "full_output_hint": "rerun with --output-profile full",
    }


def _add_common(subparser: argparse.ArgumentParser, *, subject_help: str | None = None) -> None:
    subparser.add_argument(
        "--subject-id",
        action="append",
        required=True,
        help=subject_help or "Task Ledger WorkItem/CAP id to inspect. Repeatable.",
    )
    subparser.add_argument(
        "--owned-path",
        action="append",
        default=[],
        help="Repo-relative path owned by this landing attempt. Repeatable.",
    )
    subparser.add_argument(
        "--session-id",
        default=None,
        help="Work Ledger session id for the current execution attempt.",
    )
    subparser.add_argument(
        "--require-exclusive",
        action="store_true",
        help="Treat overlapping Work Ledger claims as blockers.",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        default=str(REPO_ROOT),
        help="Repository root to inspect. Defaults to this ai_workflow checkout.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Emit work_landing_status_v0.")
    _add_common(status_parser)

    reconcile_parser = subparsers.add_parser("reconcile", help="Emit or apply a landing reconcile plan.")
    _add_common(reconcile_parser)
    mode_group = reconcile_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry-run only. This is the default when --apply is absent.",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        help="Apply the requested controller action class. Must be paired with --only.",
    )
    reconcile_parser.add_argument(
        "--only",
        choices=(
            "receipt_intake",
            "ensure_task_ledger_receipt_intake_or_event",
            "record_scoped_commit_landing",
            "attach_commit_hash_to_attempt",
            "commit_landing",
            "land_scoped_commit_attempt",
            "land_scoped_commit",
            "commit_and_closeout",
            "closeout_landing_attempt",
            "landing_closeout",
            "closeout",
        ),
        default=None,
        help="Single action class to apply.",
    )
    reconcile_parser.add_argument(
        "--commit-hash",
        default=None,
        help="Landed scoped commit hash to bind to the active WorkItem landing attempt.",
    )
    reconcile_parser.add_argument(
        "--created-by",
        default="codex",
        help="Actor name used when an apply action queues intake.",
    )
    reconcile_parser.add_argument(
        "--output-profile",
        choices=("auto", "compact", "full"),
        default="auto",
        help="Output shape for reconcile. auto compacts mutating --apply output and keeps dry-runs full.",
    )
    begin_parser = subparsers.add_parser("begin", help="Establish a pre-mutation WorkItem landing attempt binding.")
    _add_common(
        begin_parser,
        subject_help="Task Ledger WorkItem/CAP id to bind. Exactly one is accepted by begin.",
    )
    begin_parser.add_argument(
        "--created-by",
        default="codex",
        help="Actor name used for the Work Ledger session and attempt td thread.",
    )
    begin_parser.add_argument(
        "--lease-minutes",
        type=float,
        default=120.0,
        help="Lease duration for WorkItem, path, and td claims.",
    )
    begin_parser.add_argument(
        "--heartbeat-current-pass-line",
        "--heartbeat-now",
        dest="heartbeat_current_pass_line",
        default=None,
        help="Optional public current-pass line to write during the begin mutation.",
    )
    begin_parser.add_argument(
        "--heartbeat-last-pass-result-line",
        "--heartbeat-done",
        dest="heartbeat_last_pass_result_line",
        default=None,
        help="Optional public previous-result line to write during the begin mutation.",
    )
    begin_parser.add_argument(
        "--heartbeat-clip-lines",
        action="store_true",
        help=(
            "Trim begin heartbeat now/done text to Work Ledger public line limits "
            "before runtime validation. Default is strict rejection."
        ),
    )
    begin_parser.add_argument(
        "--heartbeat-state",
        default="inspecting",
        choices=sorted(work_ledger_runtime.PASS_HEARTBEAT_STATES),
        help="Public pass state to store when heartbeat text is supplied.",
    )
    begin_parser.add_argument(
        "--heartbeat-scope-ref",
        action="append",
        default=[],
        help=(
            "Optional heartbeat scope ref. Repeatable. Defaults to the WorkItem, "
            "landing thread, and owned paths when heartbeat text is supplied."
        ),
    )
    begin_parser.add_argument(
        "--heartbeat-source",
        default="manual_cli",
        choices=sorted(work_ledger_runtime.PASS_HEARTBEAT_SOURCES),
        help="Public source label for the begin-time heartbeat.",
    )
    begin_parser.add_argument(
        "--explicit-subject-override",
        action="store_true",
        help=(
            "Allow an explicitly named non-Task-Ledger seed/lane subject to bind "
            "only for this begin attempt; normal missing-subject refusal remains the default."
        ),
    )
    admission_parser = subparsers.add_parser(
        "admission-check",
        help="Check whether a write-capable agent has a valid WorkItem landing attempt before editing.",
    )
    _add_common(admission_parser)
    admission_parser.add_argument("--domain", default=None, help="Optional WorkItem selector domain filter.")
    mode_group = admission_parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--for-agent",
        dest="selector_mode",
        action="store_const",
        const="agent",
        default="agent",
        help="Require autonomous-agent executability. Default.",
    )
    mode_group.add_argument(
        "--for-operator",
        dest="selector_mode",
        action="store_const",
        const="operator",
        help="Inspect operator/external subject context while still requiring explicit override for writes.",
    )
    admission_parser.add_argument(
        "--include-signoff",
        action="store_true",
        help="Mirror work_control selector labeling for signoff/external subjects; does not grant write admission.",
    )
    admission_parser.add_argument(
        "--explicit-subject-override",
        action="store_true",
        help="Allow an explicitly named non-agent WorkItem only when the attempt/session/claims envelope is valid.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(args.repo_root)
    common = {
        "subject_ids": list(args.subject_id or []),
        "owned_paths": list(args.owned_path or []),
        "session_id": args.session_id,
        "require_exclusive": bool(args.require_exclusive),
    }
    if args.command == "reconcile":
        payload = build_work_landing_reconcile_plan(
            repo_root,
            **common,
            apply=bool(args.apply),
            only=args.only,
            created_by=args.created_by,
            commit_hash=args.commit_hash,
        )
        compact_output = args.output_profile == "compact" or (
            args.output_profile == "auto" and bool(args.apply)
        )
        if compact_output:
            payload = _compact_reconcile_payload(payload)
    elif args.command == "begin":
        payload = build_work_landing_attempt_binding(
            repo_root,
            **common,
            created_by=args.created_by,
            lease_minutes=args.lease_minutes,
            heartbeat_current_pass_line=args.heartbeat_current_pass_line,
            heartbeat_last_pass_result_line=args.heartbeat_last_pass_result_line,
            heartbeat_clip_lines=bool(args.heartbeat_clip_lines),
            heartbeat_state=args.heartbeat_state,
            heartbeat_scope_refs=args.heartbeat_scope_ref,
            heartbeat_source=args.heartbeat_source,
            explicit_subject_override=bool(args.explicit_subject_override),
        )
    elif args.command == "admission-check":
        admission_common = {**common, "require_exclusive": True}
        payload = build_workitem_write_admission(
            repo_root,
            **admission_common,
            selector_mode=getattr(args, "selector_mode", "agent"),
            include_signoff=bool(getattr(args, "include_signoff", False)),
            domain=getattr(args, "domain", None),
            explicit_subject_override=bool(getattr(args, "explicit_subject_override", False)),
        )
    else:
        payload = build_work_landing_status(repo_root, **common)
    compact_reconcile_output = args.command == "reconcile" and (
        args.output_profile == "compact" or (args.output_profile == "auto" and bool(args.apply))
    )
    if compact_reconcile_output:
        print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    else:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
