#!/usr/bin/env python3
"""Generate organ atlas entry surfaces from public substrate.

Thin CLI wrapper over ``microcosm_core.projections.organ_atlas``. The atlas is
a projection of ``core/organ_registry.json`` + ``core/organ_families.json`` +
``core/organ_atlas.json`` + ``core/organ_evidence_classes.json`` +
``core/architecture_kernel.json``; it carries no authority above each organ's
own claim ceiling.

Usage:
  PYTHONPATH=src python3 scripts/build_organ_atlas.py            # status JSON
  PYTHONPATH=src python3 scripts/build_organ_atlas.py --write    # write generated files
  PYTHONPATH=src python3 scripts/build_organ_atlas.py --check    # fail on drift
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = MICROCOSM_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from microcosm_core.projections.organ_atlas import build  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="build_organ_atlas",
        description="Generate organ atlas entry surfaces from public substrate.",
    )
    parser.add_argument("--root", type=Path, default=MICROCOSM_ROOT)
    parser.add_argument(
        "--write", action="store_true", help="write generated atlas files"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail (exit 1) if the on-disk files drift from the rendered atlas",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = build(args.root, write=args.write)
    summary: dict[str, Any] = {
        "status": result["status"],
        "blocking_reasons": result["blocking_reasons"],
        "coverage": result["coverage"],
        "drift": result["drift"],
        "wrote": result["wrote"],
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2, sort_keys=True))
    if result["status"] != "pass":
        return 1
    if args.check and result["drift"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
