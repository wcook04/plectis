#!/usr/bin/env python3
"""Check the README binding for the public Lean companion snapshot."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from microcosm_core.validators.lean_companion_snapshot import (
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
    args = parser.parse_args()

    receipt = validate_lean_companion_snapshot(
        args.root,
        upstream_root=args.upstream_root,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
