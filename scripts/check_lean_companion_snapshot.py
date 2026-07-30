#!/usr/bin/env python3
"""Check the README binding for the public Lean companion snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from microcosm_core.validators.lean_companion_snapshot import (
    refresh_lean_companion_snapshot,
    validate_lean_companion_snapshot,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=REPO_ROOT)
    parser.add_argument(
        "--upstream-root",
        type=Path,
        help="optional local checkout of plectis-lean-erdos249-257",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="refresh the snapshot and README binding from the upstream public ref",
    )
    args = parser.parse_args()

    if args.write:
        if args.upstream_root is None:
            parser.error("--write requires --upstream-root")
        receipt = refresh_lean_companion_snapshot(
            args.root,
            upstream_root=args.upstream_root,
        )
    else:
        receipt = validate_lean_companion_snapshot(
            args.root,
            upstream_root=args.upstream_root,
        )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
