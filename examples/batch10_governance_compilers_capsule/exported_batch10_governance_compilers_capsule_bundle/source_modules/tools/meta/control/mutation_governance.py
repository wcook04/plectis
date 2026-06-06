#!/usr/bin/env python3
"""Emit read-only mutation-governance gates for latest-intent safety."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib.mutation_governance import (  # noqa: E402
    build_candidate_row_preflight,
    build_compaction_resume_capsule,
    build_diff_safety_gate,
    build_landing_preflight_gate,
    build_latest_intent_gate,
    build_ledger_growth_budget,
    build_mutation_governance_packet,
    build_operator_goal_satisfaction,
    build_stutter_loop_detector,
    classify_latest_user_intent,
    mutation_idempotency_key,
)


BLOCKED_STATUSES = {"blocked", "failed"}


def _read_text_arg(value: str | None, path: str | None) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return value or ""


def _load_json_rows(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return [dict(item) for item in payload if isinstance(item, dict)]
    if isinstance(payload, dict):
        rows = payload.get("candidate_rows") or payload.get("rows") or []
        if isinstance(rows, list):
            return [dict(item) for item in rows if isinstance(item, dict)]
    return []


def _blocked(payload: dict) -> bool:
    for value in payload.values():
        if isinstance(value, dict):
            if str(value.get("status") or "") in BLOCKED_STATUSES:
                return True
            if _blocked(value):
                return True
    return str(payload.get("status") or "") in BLOCKED_STATUSES


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--latest-user-message", default=None)
    parser.add_argument("--latest-user-message-file", default=None)
    parser.add_argument("--requested-route", default=None)
    parser.add_argument("--owned-path", action="append", default=[])
    parser.add_argument("--prompt-event", action="append", default=[])
    parser.add_argument("--route-event", action="append", default=[])
    parser.add_argument("--context-compaction-count", type=int, default=0)
    parser.add_argument("--steer-count", type=int, default=0)
    parser.add_argument("--new-rows-requested", type=int, default=0)
    parser.add_argument("--growth-passes-for-operator-seed", type=int, default=0)
    parser.add_argument("--generated-sidecars-touched", type=int, default=0)
    parser.add_argument("--previous-successful-append", action="store_true")
    parser.add_argument("--commit-blocker-seen", action="store_true")
    parser.add_argument("--high-novelty-low-risk-backlog-count", type=int, default=None)
    parser.add_argument("--tranche-theme", action="append", default=[])
    parser.add_argument("--ledger-start-count", type=int, default=None)
    parser.add_argument("--active-transaction-id", default=None)
    parser.add_argument("--appended-row", action="append", default=[])
    parser.add_argument("--refreshed-sidecar", action="append", default=[])
    parser.add_argument("--blocker-seen", action="append", default=[])
    parser.add_argument("--performed-mutation", action="store_true")
    parser.add_argument("--quoted-context-executed", action="store_true")
    parser.add_argument("--candidate-rows-json", default=None)
    parser.add_argument("--ledger-path", default=None)
    parser.add_argument(
        "--section",
        choices=(
            "packet",
            "latest-intent",
            "stutter-loop",
            "budget",
            "idempotency-key",
            "diff-safety",
            "landing-preflight",
            "compaction-capsule",
            "operator-goal",
            "candidate-row-preflight",
        ),
        default="packet",
    )
    parser.add_argument("--fail-on-blocked", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    repo_root = Path(args.repo_root)
    latest_user_message = _read_text_arg(args.latest_user_message, args.latest_user_message_file)
    latest_intent = classify_latest_user_intent(latest_user_message)

    if args.section == "latest-intent":
        payload = build_latest_intent_gate(
            latest_user_message,
            requested_route=args.requested_route,
        )
    elif args.section == "stutter-loop":
        payload = build_stutter_loop_detector(
            prompt_events=args.prompt_event,
            route_events=args.route_event,
            context_compaction_count=args.context_compaction_count,
            steer_count=args.steer_count,
        )
    elif args.section == "budget":
        payload = build_ledger_growth_budget(
            new_rows_requested=args.new_rows_requested,
            growth_passes_for_operator_seed=args.growth_passes_for_operator_seed,
            generated_sidecars_touched=args.generated_sidecars_touched,
            previous_successful_append=args.previous_successful_append,
            context_compaction_count=args.context_compaction_count,
            commit_blocker_seen=args.commit_blocker_seen,
            high_novelty_low_risk_backlog_count=args.high_novelty_low_risk_backlog_count,
        )
    elif args.section == "idempotency-key":
        payload = mutation_idempotency_key(
            route=args.requested_route or "unknown",
            latest_user_seed=latest_user_message,
            tranche_themes=args.tranche_theme,
            ledger_start_count=args.ledger_start_count,
        )
    elif args.section == "diff-safety":
        payload = build_diff_safety_gate(repo_root, expected_owned_paths=args.owned_path)
    elif args.section == "landing-preflight":
        payload = build_landing_preflight_gate(repo_root, owned_paths=args.owned_path)
    elif args.section == "compaction-capsule":
        payload = build_compaction_resume_capsule(
            latest_user_intent=latest_intent,
            active_transaction_id=args.active_transaction_id,
            appended_rows=args.appended_row,
            refreshed_sidecars=args.refreshed_sidecar,
            blockers_seen=args.blocker_seen,
            successful_append=args.previous_successful_append,
        )
    elif args.section == "operator-goal":
        payload = build_operator_goal_satisfaction(
            latest_user_intent=latest_intent,
            performed_mutation=args.performed_mutation,
            quoted_context_executed=args.quoted_context_executed,
        )
    elif args.section == "candidate-row-preflight":
        payload = build_candidate_row_preflight(
            repo_root,
            candidate_rows=_load_json_rows(args.candidate_rows_json),
            ledger_path=args.ledger_path,
        )
    else:
        payload = build_mutation_governance_packet(
            repo_root,
            latest_user_message=latest_user_message,
            requested_route=args.requested_route,
            expected_owned_paths=args.owned_path,
        )

    sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    if args.fail_on_blocked and _blocked(payload):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
