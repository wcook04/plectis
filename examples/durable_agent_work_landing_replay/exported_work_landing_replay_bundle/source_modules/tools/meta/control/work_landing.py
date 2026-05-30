#!/usr/bin/env python3
"""WorkItem landing status and opt-in reconcile controller surface."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.work_landing_status import (  # noqa: E402
    build_work_landing_attempt_binding,
    build_work_landing_reconcile_plan,
    build_work_landing_status,
    build_workitem_write_admission,
)


def _add_common(subparser: argparse.ArgumentParser) -> None:
    subparser.add_argument(
        "--subject-id",
        action="append",
        required=True,
        help="Task Ledger WorkItem/CAP id to inspect. Repeatable.",
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
    begin_parser = subparsers.add_parser("begin", help="Establish a pre-mutation WorkItem landing attempt binding.")
    _add_common(begin_parser)
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
    elif args.command == "begin":
        payload = build_work_landing_attempt_binding(
            repo_root,
            **common,
            created_by=args.created_by,
            lease_minutes=args.lease_minutes,
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
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
