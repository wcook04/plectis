#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from system.lib import task_ledger_events


def _print(payload: dict) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if payload.get("ok", True) else 1


def cmd_rebuild(args: argparse.Namespace) -> int:
    return _print(task_ledger_events.rebuild_projections(REPO_ROOT, check=bool(args.check)))


def cmd_validate(args: argparse.Namespace) -> int:
    try:
        payload = task_ledger_events.validate_event_log(REPO_ROOT)
    except Exception as exc:
        return _print({"ok": False, "error": str(exc)})
    return _print(payload)


def cmd_views(args: argparse.Namespace) -> int:
    payload = task_ledger_events.rebuild_projections(REPO_ROOT, check=True)
    if payload.get("ok"):
        projection = task_ledger_events.build_projection(
            task_ledger_events.load_and_validate_events(REPO_ROOT)
        )
        return _print(
            {
                "ok": True,
                "views": {
                    key: {
                        "path": str(task_ledger_events.VIEWS_REL / f"{key}.json"),
                        "count": value.get("count"),
                    }
                    for key, value in projection["views"].items()
                },
            }
        )
    return _print(payload)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Rebuild and validate Task Ledger projections.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    rebuild = subparsers.add_parser("rebuild", help="Rebuild Task Ledger projections from events.")
    rebuild.add_argument("--check", action="store_true", help="Report projection mismatch without writing.")
    rebuild.set_defaults(func=cmd_rebuild)

    validate = subparsers.add_parser("validate", help="Validate events and projection invariants.")
    validate.set_defaults(func=cmd_validate)

    views = subparsers.add_parser("views", help="List deterministic view projection paths.")
    views.set_defaults(func=cmd_views)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
