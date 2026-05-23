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
AUTHORITY_CEILING = {
    "live_task_ledger_mutation_authorized": False,
    "live_work_ledger_mutation_authorized": False,
    "git_mutation_authorized": False,
    "broad_checkpoint_authorized": False,
    "private_root_required": False,
    "release_authorized": False,
}


def _strings(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        text = str(value or "").strip().strip("/")
        if text and text not in out:
            out.append(text)
    return out


def _stable_digest(payload: object) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


def _base_payload(
    *,
    schema: str,
    subject_ids: list[str],
    owned_paths: list[str],
    session_id: str | None,
    require_exclusive: bool,
) -> dict[str, Any]:
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
    payload = _base_payload(
        schema="public_work_landing_reconcile_plan_v0",
        subject_ids=subject_ids,
        owned_paths=owned_paths,
        session_id=session_id,
        require_exclusive=require_exclusive,
    )
    actions = [
        {"action_id": action_id, "mutation_authorized": False}
        for action_id in ORDERED_CONTROLLER_ACTION_IDS
    ]
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
    subparser.add_argument("--subject-id", action="append", required=True)
    subparser.add_argument("--owned-path", action="append", default=[])
    subparser.add_argument("--session-id", default=None)
    subparser.add_argument("--require-exclusive", action="store_true")


def build_parser() -> argparse.ArgumentParser:
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
