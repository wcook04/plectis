#!/usr/bin/env python3
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

from microcosm_core.runtime_shell import RuntimeShell  # noqa: E402


def workingness_card(root: Path = MICROCOSM_ROOT) -> dict[str, Any]:
    return RuntimeShell(root).workingness_card()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="workingness_card",
        description="Emit a compact first-screen card for Microcosm workingness.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=MICROCOSM_ROOT,
        help="Microcosm public root; defaults to the script's parent tree.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = workingness_card(args.root)
    print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
