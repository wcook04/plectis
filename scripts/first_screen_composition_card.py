#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


MICROCOSM_ROOT = Path(__file__).resolve().parents[1]
MICROCOSM_SRC = MICROCOSM_ROOT / "src"
if str(MICROCOSM_SRC) not in sys.path:
    sys.path.insert(0, str(MICROCOSM_SRC))

from microcosm_core.first_screen_composition import (  # noqa: E402
    COMPACT_JSON_CARD_MAX_CHARS,
    TEXT_CARD_MAX_LINES,
    TEXT_READER_CHOICES,
    first_screen_composition_card,
    first_screen_compact_card,
    first_screen_text_card,
)

__all__ = (
    "COMPACT_JSON_CARD_MAX_CHARS",
    "TEXT_CARD_MAX_LINES",
    "TEXT_READER_CHOICES",
    "first_screen_composition_card",
    "first_screen_compact_card",
    "first_screen_text_card",
)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the first-screen composition card CLI.

    - Teleology: defines the CLI surface (root/project-label/format/reader) for the standalone first-screen card script.
    - Guarantee: returns an ArgumentParser whose parsed args carry root, project_label, format, and reader.
    - Fails: None (constructs and returns a parser; no I/O).
    """
    parser = argparse.ArgumentParser(
        prog="first_screen_composition_card",
        description="Emit the Microcosm first-screen composition card.",
    )
    parser.add_argument(
        "--root",
        type=Path,
        default=MICROCOSM_ROOT,
        help="Microcosm public root; defaults to the script's parent tree.",
    )
    parser.add_argument(
        "--project-label",
        default="<project>",
        help="Label to place in the shared first command.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "text"),
        default="json",
        help="Output JSON contract or terminal-sized text card.",
    )
    parser.add_argument(
        "--reader",
        choices=TEXT_READER_CHOICES,
        default="all",
        help="Reader branch to focus when emitting the terminal text card.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Emit the first-screen composition card as JSON or terminal text and return its exit code.

    - Teleology: standalone entrypoint so the first-screen card can be emitted without the full microcosm console.
    - Guarantee: prints the composition payload (JSON or reader-focused text card) to stdout.
    - Fails: card payload status != 'pass' -> non-pass result -> returns exit code 1.
    - Reads: the Microcosm root tree via first_screen_composition_card.
    - Writes: stdout only.
    """
    args = build_parser().parse_args(argv)
    payload = first_screen_composition_card(args.root, project_label=args.project_label)
    if args.format == "text":
        print(first_screen_text_card(payload, reader_id=args.reader), end="")
    else:
        print(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True))
    return 0 if payload.get("status") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
