"""
[PURPOSE]
- Teleology: Exposes `microcosm_core.macro_tools.work_landing` as a documented Microcosm public source module.
- Mechanism: Keeps executable source as authority while adding the file-level contract required by `std_python.py`.
- Guarantee: Importing this module defines its declared constants, classes, and functions without granting authority outside the public package boundary.

[INTERFACE]
- Exports: PASS, BLOCKED, SOURCE_REF, SOURCE_SYMBOL_REFS, TARGET_SYMBOL_REFS, ORDERED_CONTROLLER_ACTION_IDS, CONTROLLER_ACTION_PREREQUISITES, CONTROLLER_ACTION_ORDER_GUARDS, AUTHORITY_CEILING, build_public_work_landing_status, build_public_work_landing_reconcile_plan, build_public_work_landing_attempt_binding, build_public_workitem_write_admission, build_parser, main
- Reads: call arguments, module constants, imported helpers.
- Writes: return values, stdout/stderr or CLI result text and any explicit side effects performed by exported entry points.
- Non-goal: Does not authorize private-source export, Drive sharing, network publication, or mutation outside the callable body.

[FLOW]
- Loads imports and constants, then exposes helpers and public callables for package, test, CLI, or exported-bundle callers.
- Delegates validation, projection, serialization, and receipt behavior to file-local functions and classes.
- Surfaces errors through normal Python exceptions or body-defined result envelopes so callers can bind failures to receipts.

[DEPENDENCIES]
- Required: None beyond the Python standard library and local package imports.
- Optional Runtime: Filesystem, CLI arguments, package data, subprocesses, or environment variables only where individual call bodies reference them.

[CONSTRAINTS]
- Atomicity: Module import is declaration-only; mutating operations are scoped to the explicit function or method invocation that performs them.
- Determinism: Pure computations are deterministic for equal inputs; filesystem, clock, subprocess, and environment reads are the only admitted runtime variability.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

PASS = "pass"
BLOCKED = "blocked"

SOURCE_REF = "tools/meta/control/work_landing.py"
SOURCE_SYMBOL_REFS = [
    "system/lib/work_landing_status.py::ORDERED_CONTROLLER_ACTION_IDS",
    "tools/meta/control/work_landing.py::build_parser",
    "tools/meta/control/work_landing.py::main",
    "system/lib/work_landing_status.py::build_work_landing_status",
    "system/lib/work_landing_status.py::build_work_landing_reconcile_plan",
    "system/lib/work_landing_status.py::build_work_landing_attempt_binding",
    "system/lib/work_landing_status.py::build_workitem_write_admission",
]
TARGET_SYMBOL_REFS = [
    "microcosm_core.macro_tools.work_landing::ORDERED_CONTROLLER_ACTION_IDS",
    "microcosm_core.macro_tools.work_landing::build_parser",
    "microcosm_core.macro_tools.work_landing::main",
    "microcosm_core.macro_tools.work_landing::build_public_work_landing_status",
    "microcosm_core.macro_tools.work_landing::build_public_work_landing_reconcile_plan",
    "microcosm_core.macro_tools.work_landing::build_public_work_landing_attempt_binding",
    "microcosm_core.macro_tools.work_landing::build_public_workitem_write_admission",
]
ORDERED_CONTROLLER_ACTION_IDS = [
    "verify_scoped_commit_landed",
    "ensure_work_ledger_progress_event",
    "record_scoped_commit_landing",
    "ensure_task_ledger_receipt_intake_or_event",
    "drain_task_ledger_intake_if_exclusive",
    "closeout_landing_attempt",
    "rebuild_task_ledger_projection",
    "check_work_ledger_projection",
    "close_work_ledger_transaction_thread",
    "finalize_work_ledger_session",
    "release_claims",
    "recompute_convergence",
]
CONTROLLER_ACTION_PREREQUISITES = {
    "ensure_work_ledger_progress_event": ["verify_scoped_commit_landed"],
    "record_scoped_commit_landing": [
        "verify_scoped_commit_landed",
        "ensure_work_ledger_progress_event",
    ],
    "ensure_task_ledger_receipt_intake_or_event": [
        "record_scoped_commit_landing",
    ],
    "drain_task_ledger_intake_if_exclusive": [
        "ensure_task_ledger_receipt_intake_or_event",
    ],
    "closeout_landing_attempt": ["drain_task_ledger_intake_if_exclusive"],
    "rebuild_task_ledger_projection": ["closeout_landing_attempt"],
    "check_work_ledger_projection": ["rebuild_task_ledger_projection"],
    "close_work_ledger_transaction_thread": ["check_work_ledger_projection"],
    "finalize_work_ledger_session": ["close_work_ledger_transaction_thread"],
    "release_claims": ["finalize_work_ledger_session"],
    "recompute_convergence": ["release_claims"],
}
CONTROLLER_ACTION_ORDER_GUARDS = {
    "release_claims": "claim_release_after_work_ledger_session_finalize_only",
    "recompute_convergence": "convergence_after_claim_release_only",
}
AUTHORITY_CEILING = {
    "live_task_ledger_mutation_authorized": False,
    "live_work_ledger_mutation_authorized": False,
    "git_mutation_authorized": False,
    "broad_checkpoint_authorized": False,
    "private_root_required": False,
    "release_authorized": False,
}


def _strings(values: list[str] | None) -> list[str]:
    """
    [ACTION]
    - Teleology: Implements `_strings` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    out: list[str] = []
    for value in values or []:
        text = str(value or "").strip().strip("/")
        if text and text not in out:
            out.append(text)
    return out


def _stable_digest(payload: object) -> str:
    """
    [ACTION]
    - Teleology: Implements `_stable_digest` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _controller_action_rows() -> list[dict[str, Any]]:
    """
    [ACTION]
    - Teleology: Implements `_controller_action_rows` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    rows: list[dict[str, Any]] = []
    for sequence, action_id in enumerate(ORDERED_CONTROLLER_ACTION_IDS, start=1):
        row = {
            "sequence": sequence,
            "action_id": action_id,
            "prerequisite_action_ids": CONTROLLER_ACTION_PREREQUISITES.get(
                action_id, []
            ),
            "mutation_authorized": False,
            "live_state_mutation_authorized": False,
        }
        order_guard = CONTROLLER_ACTION_ORDER_GUARDS.get(action_id)
        if order_guard:
            row["order_guard"] = order_guard
        rows.append(row)
    return rows


def _base_payload(
    *,
    schema: str,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None,
    require_exclusive: bool,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `_base_payload` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    missing: list[str] = []
    if not subject_ids:
        missing.append("subject_id")
    if not owned_paths:
        missing.append("owned_path")
    return {
        "schema": schema,
        "status": PASS if not missing else BLOCKED,
        "source_ref": SOURCE_REF,
        "source_symbols": SOURCE_SYMBOL_REFS,
        "target_symbols": TARGET_SYMBOL_REFS,
        "subject_ids": subject_ids,
        "owned_paths": owned_paths,
        "session_id": session_id,
        "require_exclusive": require_exclusive,
        "missing_fields": missing,
        "body_in_receipt": False,
        "source_order_ref": "system/lib/work_landing_status.py::ORDERED_CONTROLLER_ACTION_IDS",
        "target_order_ref": (
            "microcosm_core.macro_tools.work_landing::ORDERED_CONTROLLER_ACTION_IDS"
        ),
        "source_faithful_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
        "authority_ceiling": AUTHORITY_CEILING,
        "anti_claim": (
            "This public work-landing tool is a source-faithful public refactor of "
            "the macro command and controller-action shape. It emits deterministic local receipts only; "
            "it does not mutate Task Ledger, Work Ledger, Git, or private macro state."
        ),
    }


def build_public_work_landing_status(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None = None,
    require_exclusive: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_work_landing_status` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = _base_payload(
        schema="public_work_landing_status_v0",
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    payload.update(
        {
            "landing_lane": "scoped_commit" if payload["status"] == PASS else "blocked",
            "claim_conflict_status": "not_evaluated_public_fixture",
            "same_path_conflict_claim_ids": [],
            "recommended_next_action": (
                "run_reconcile_plan"
                if payload["status"] == PASS
                else "provide_subject_id_and_owned_path"
            ),
        }
    )
    return payload


def build_public_work_landing_reconcile_plan(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None = None,
    require_exclusive: bool = False,
    apply: bool = False,
    only: str | None = None,
    commit_hash: str | None = None,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_work_landing_reconcile_plan` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = _base_payload(
        schema="public_work_landing_reconcile_plan_v0",
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    actions = _controller_action_rows()
    payload.update(
        {
            "mode": "apply_requested_but_public_tool_is_dry_run" if apply else "dry_run",
            "only": only,
            "commit_hash": commit_hash,
            "ordered_controller_action_ids": ORDERED_CONTROLLER_ACTION_IDS,
            "controller_action_count": len(ORDERED_CONTROLLER_ACTION_IDS),
            "actions": actions,
            "work_landing_reconcile_status": (
                "ordered_dry_run_plan_emitted"
                if payload["status"] == PASS
                else "blocked_missing_required_fields"
            ),
            "apply_result": {
                "applied": False,
                "reason": "public_microcosm_tool_never_mutates_live_state",
            },
        }
    )
    return payload


def build_public_work_landing_attempt_binding(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None = None,
    require_exclusive: bool = False,
    created_by: str = "microcosm",
    lease_minutes: float = 120.0,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_work_landing_attempt_binding` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = _base_payload(
        schema="public_work_landing_attempt_binding_v0",
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    subject = subject_ids[0] if subject_ids else "missing_subject"
    digest = _stable_digest(
        {
            "subject_ids": subject_ids,
            "owned_paths": owned_paths,
            "session_id": session_id,
            "created_by": created_by,
        }
    )
    payload.update(
        {
            "created_by": created_by,
            "lease_minutes": lease_minutes,
            "idempotency_key": f"{subject}:public_work_landing_attempt:{digest}",
            "claim_ids": [
                f"public_claim:{_stable_digest({'path': path, 'subject': subject})}"
                for path in owned_paths
            ],
        }
    )
    return payload


def build_public_workitem_write_admission(
    *,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None = None,
    require_exclusive: bool = True,
    explicit_subject_override: bool = False,
) -> dict[str, Any]:
    """
    [ACTION]
    - Teleology: Implements `build_public_workitem_write_admission` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values.
    """
    payload = _base_payload(
        schema="public_workitem_write_admission_v0",
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    payload.update(
        {
            "write_admitted": payload["status"] == PASS,
            "explicit_subject_override": explicit_subject_override,
            "reason": (
                "public_fixture_claim_envelope_complete"
                if payload["status"] == PASS
                else "missing_public_fixture_claim_field"
            ),
        }
    )
    return payload


def _add_common(subparser: argparse.ArgumentParser) -> None:
    """
    [ACTION]
    - Teleology: Implements `_add_common` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    subparser.add_argument("--subject-id", action="append", required=True)
    subparser.add_argument("--owned-path", action="append", default=[])
    subparser.add_argument("--session-id", default=None)
    subparser.add_argument("--require-exclusive", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    """
    [ACTION]
    - Teleology: Implements `build_parser` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status")
    _add_common(status_parser)

    reconcile_parser = subparsers.add_parser("reconcile")
    _add_common(reconcile_parser)
    reconcile_parser.add_argument("--dry-run", action="store_true")
    reconcile_parser.add_argument("--apply", action="store_true")
    reconcile_parser.add_argument("--only", default=None)
    reconcile_parser.add_argument("--commit-hash", default=None)

    begin_parser = subparsers.add_parser("begin")
    _add_common(begin_parser)
    begin_parser.add_argument("--created-by", default="microcosm")
    begin_parser.add_argument("--lease-minutes", type=float, default=120.0)

    admission_parser = subparsers.add_parser("admission-check")
    _add_common(admission_parser)
    admission_parser.add_argument("--explicit-subject-override", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    """
    [ACTION]
    - Teleology: Implements `main` for `microcosm_core.macro_tools.work_landing` while keeping the callable contract visible to source-module readers.
    - Preconditions: Caller supplies arguments satisfying the signature plus any path, schema, state, or type constraints enforced by the body.
    - Guarantee: On success returns the body-defined value or performs only the explicit side effects encoded in the callable body.
    - Fails: Propagates validation, IO, JSON, subprocess, import, and dependency errors raised by the body; explicit failure envelopes remain as encoded by the source.
    - Reads: call arguments, module constants, imported helpers.
    - Writes: return values, stdout/stderr or CLI result text.
    """
    args = build_parser().parse_args(argv)
    subject_ids = _strings(args.subject_id)
    owned_paths = _strings(args.owned_path)
    common = {
        "subject_ids": subject_ids,
        "owned_paths": owned_paths,
        "session_id": args.session_id,
        "require_exclusive": bool(args.require_exclusive),
    }
    if args.command == "reconcile":
        payload = build_public_work_landing_reconcile_plan(
            **common,
            apply=bool(args.apply),
            only=args.only,
            commit_hash=args.commit_hash,
        )
    elif args.command == "begin":
        payload = build_public_work_landing_attempt_binding(
            **common,
            created_by=args.created_by,
            lease_minutes=args.lease_minutes,
        )
    elif args.command == "admission-check":
        payload = build_public_workitem_write_admission(
            **common,
            explicit_subject_override=bool(args.explicit_subject_override),
        )
    else:
        payload = build_public_work_landing_status(**common)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
