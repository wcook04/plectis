#!/usr/bin/env python3
"""
[PURPOSE]
- Teleology: Wave_004B2 targeted-fire proof CLI. Drives the existing reactions
  engine's preview_reaction / fire_reaction helpers so the operator can prove
  one specific reaction id fires through the real engine path (signal load,
  predicate evaluation, digest computation, gate check, parameter rendering,
  subprocess invocation, ledger append) without running a global tick that
  might fire a higher-priority reaction first.
- Mechanism: Argparse over reaction id + preview/execute mode; pure shell over
  reactions_engine.preview_reaction and reactions_engine.fire_reaction.
- Non-goal: Re-implement engine semantics, manage barriers, mutate engine
  state, or replace tick_engine for production use.

[INTERFACE]
- CLI: ./repo-python tools/meta/control/reaction_proof.py preview --reaction-id ID --json
       ./repo-python tools/meta/control/reaction_proof.py fire --reaction-id ID [--force] --json

[CONSTRAINTS]
- Forbid: source mutation, provider dispatch outside the prepared launch.
- Determinism: same engine state -> same preview output (timestamps differ).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.meta.control import reactions_engine  # noqa: E402


def cmd_preview(args: argparse.Namespace) -> int:
    payload = reactions_engine.preview_reaction(REPO_ROOT, args.reaction_id)
    print(json.dumps(payload, indent=2, default=str))
    return 0


def cmd_fire(args: argparse.Namespace) -> int:
    payload = reactions_engine.fire_reaction(
        REPO_ROOT,
        args.reaction_id,
        force=bool(args.force),
        timeout_seconds=int(args.timeout),
    )
    print(json.dumps(payload, indent=2, default=str))
    if payload.get("status") == "ok":
        return 0
    if payload.get("status") in {"predicate_not_matched", "render_failed", "unsupported_source_kind", "unknown_reaction_id"}:
        return 2
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_preview = sub.add_parser("preview", help="Preview one reaction without firing.")
    p_preview.add_argument("--reaction-id", required=True)
    p_preview.set_defaults(func=cmd_preview)

    p_fire = sub.add_parser("fire", help="Engine-path fire (manual proof; ledger kind: reaction_fired_manual_proof).")
    p_fire.add_argument("--reaction-id", required=True)
    p_fire.add_argument("--force", action="store_true", help="Fire even if the predicate did not match (not recommended).")
    p_fire.add_argument("--timeout", type=int, default=120, help="Subprocess timeout in seconds.")
    p_fire.set_defaults(func=cmd_fire)

    p_tick = sub.add_parser(
        "tick",
        help=(
            "Daemon-path targeted tick (Wave_004B3 proof; ledger kind: reaction_fired). "
            "Reuses tick_engine path and closes runtime dedupe state via _finalize_action_state."
        ),
    )
    p_tick.add_argument("--reaction-id", required=True)
    p_tick.add_argument("--wait", action="store_true", default=True, help="Wait for the operation to complete (default).")
    p_tick.add_argument("--no-wait", dest="wait", action="store_false", help="Append reaction_fired ledger row but do not block on subprocess completion.")
    p_tick.add_argument("--timeout", type=int, default=120)
    p_tick.set_defaults(func=cmd_tick)

    return parser


def cmd_tick(args: argparse.Namespace) -> int:
    payload = reactions_engine.tick_engine_targeted(
        REPO_ROOT,
        reaction_ids=[args.reaction_id],
        wait=bool(args.wait),
        timeout_seconds=int(args.timeout),
    )
    print(json.dumps(payload, indent=2, default=str))
    if payload.get("status") in {"completed", "fired_no_wait"}:
        return 0
    if payload.get("status") in {
        "cannot_fire_dedupe_or_cooldown",
        "predicate_not_matched",
        "render_failed",
        "unknown_reaction_id",
        "no_reaction_ids",
    }:
        return 2
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
