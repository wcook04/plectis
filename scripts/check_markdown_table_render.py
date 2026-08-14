#!/usr/bin/env python3
"""Flag markdown tables that render badly on GitHub.

Why this exists
---------------
GitHub renders markdown into a fixed content column (1012px at a 1440px
viewport, and narrower on smaller screens). A table has no wrapping escape: if
its *minimum intrinsic width* exceeds that column, the reader gets a horizontal
scrollbar and every other column is squashed to unreadable slivers.

The minimum width of a column is set by its longest **unbreakable** token.
Prose wraps at spaces, but a Lean declaration name, a file path, or a
snake_case identifier has no break opportunity at all, so it sets a hard floor.

Three facts were measured against live github.com rather than assumed
(the record is in the commit that introduced this script):

1. The content column is 1012px at a 1440px viewport.
2. ``<wbr>`` is **stripped by GitHub's HTML sanitiser**, so it cannot be used
   to introduce break opportunities. Neither can CSS: ``style`` is stripped too.
3. Fenced code blocks (``<pre>``) carry ``overflow-x: auto``, so they scroll
   inside themselves and never break the page. They are the correct home for a
   long identifier, and they keep it copy-paste clean.

So the only real fixes are structural: shorten the cell, drop a column, or move
the long token out of the table into a fenced block or a per-item section.

Usage
-----
    python3 scripts/check_markdown_table_render.py PATH [PATH ...]
    check_markdown_table_render.py --json PATH
    check_markdown_table_render.py --fail-on overflow PATH   # CI gate
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys

# --- Rendering model, calibrated against live github.com -------------------

# Content column of the markdown body at a 1440px viewport.
CONTENT_PX = 1012
# Advance width of one character. GitHub sets 12px SFMono for code (~7.2px) and
# 16px system prose (~7.6px average). Code is what drives table minimums, so the
# monospace figure is the operative one.
CODE_PX_PER_CHAR = 7.2
PROSE_PX_PER_CHAR = 7.6
# td padding: 13px each side, plus the 1px border.
COL_CHROME_PX = 27

# A cell longer than this makes a table tall and hard to scan even when it fits.
PROSE_CELL_LIMIT = 120
# Beyond this many columns, a table with any prose in it stops being scannable.
PROSE_COL_LIMIT = 4
TERSE_COL_LIMIT = 6
# An unbreakable run longer than this sets a floor that crowds every other
# column, even in a table that happens to fit today.
TOKEN_LIMIT = 40

CODE_SPAN = re.compile(r"`([^`]+)`")
LINK = re.compile(r"\[([^\]]*)\]\(([^)]*)\)")
IMG = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
HTML_TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")
DELIM = re.compile(r"^\s*\|?\s*:?-{1,}:?\s*(\|\s*:?-{1,}:?\s*)*\|?\s*$")


def strip_inline(text: str) -> str:
    """Reduce a cell to the text that actually occupies width."""
    text = IMG.sub(r"\1", text)
    text = LINK.sub(r"\1", text)  # link text renders; the URL does not
    text = HTML_TAG.sub("", text)
    return text


def cell_metrics(cell: str) -> tuple[float, int, str]:
    """Return (min_px, visible_chars, worst_token) for one cell."""
    worst_px = 0.0
    worst_tok = ""
    for m in CODE_SPAN.finditer(cell):
        for tok in WS.split(m.group(1)):
            px = len(tok) * CODE_PX_PER_CHAR
            if px > worst_px:
                worst_px, worst_tok = px, tok
    rest = strip_inline(CODE_SPAN.sub(" ", cell))
    for tok in WS.split(rest):
        px = len(tok) * PROSE_PX_PER_CHAR
        if px > worst_px:
            worst_px, worst_tok = px, tok
    visible = len(strip_inline(CODE_SPAN.sub(lambda m: m.group(1), cell)))
    return worst_px, visible, worst_tok


def split_row(line: str) -> list[str]:
    s = line.strip()
    if s.startswith("|"):
        s = s[1:]
    if s.endswith("|"):
        s = s[:-1]
    cells, buf, in_code, i = [], [], False, 0
    while i < len(s):
        ch = s[i]
        if ch == "\\" and i + 1 < len(s):
            buf.append(s[i : i + 2])
            i += 2
            continue
        if ch == "`":
            in_code = not in_code
        if ch == "|" and not in_code:
            cells.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
        i += 1
    cells.append("".join(buf))
    return [c.strip() for c in cells]


def find_tables(lines: list[str]):
    """Yield (start_line_idx, header_cells, body_rows), skipping fenced code."""
    i, in_fence, fence = 0, False, ""
    while i < len(lines):
        stripped = lines[i].lstrip()
        if in_fence:
            if stripped.startswith(fence):
                in_fence = False
            i += 1
            continue
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence, fence = True, stripped[:3]
            i += 1
            continue
        if (
            "|" in lines[i]
            and i + 1 < len(lines)
            and "|" in lines[i + 1]
            and DELIM.match(lines[i + 1])
        ):
            header = split_row(lines[i])
            start, j, body = i, i + 2, []
            while j < len(lines) and "|" in lines[j] and lines[j].strip():
                body.append(split_row(lines[j]))
                j += 1
            yield start, header, body
            i = j
            continue
        i += 1


def analyse(header: list[str], body: list[list[str]]) -> dict:
    ncols = len(header)
    rows = [header] + [r for r in body if r]
    col_px = [0.0] * ncols
    findings = []
    worst_tok, worst_tok_px = "", 0.0
    long_cells = 0
    for r in rows:
        for c in range(min(ncols, len(r))):
            px, visible, tok = cell_metrics(r[c])
            if px > col_px[c]:
                col_px[c] = px
            if px > worst_tok_px:
                worst_tok_px, worst_tok = px, tok
            if visible > PROSE_CELL_LIMIT:
                long_cells += 1
    min_px = sum(col_px) + COL_CHROME_PX * ncols + 2
    has_prose = long_cells > 0 or any(
        len(strip_inline(c)) > 60 for r in rows for c in r
    )
    col_cap = PROSE_COL_LIMIT if has_prose else TERSE_COL_LIMIT

    if min_px > CONTENT_PX:
        findings.append(
            (
                "overflow",
                f"table needs {min_px:.0f}px but the column is {CONTENT_PX}px "
                f"— overflows by {min_px - CONTENT_PX:.0f}px, so it gets a "
                f"horizontal scrollbar",
            )
        )
    if worst_tok_px / CODE_PX_PER_CHAR > TOKEN_LIMIT:
        findings.append(
            (
                "long_token",
                f"unbreakable token of {len(worst_tok)} chars sets a hard column "
                f"floor: {worst_tok[:70]}",
            )
        )
    if ncols > col_cap:
        findings.append(
            (
                "too_many_columns",
                f"{ncols} columns with "
                f"{'prose' if has_prose else 'terse'} cells (cap {col_cap})",
            )
        )
    if long_cells:
        findings.append(
            (
                "prose_cells",
                f"{long_cells} cell(s) over {PROSE_CELL_LIMIT} chars — move the "
                f"detail below the table",
            )
        )
    return {
        "ncols": ncols,
        "nrows": len(body),
        "min_px": round(min_px),
        "overflow_px": max(0, round(min_px - CONTENT_PX)),
        "worst_token": worst_tok,
        "worst_token_len": len(worst_tok),
        "long_cells": long_cells,
        "findings": findings,
    }


SEVERITY = {"overflow": 3, "too_many_columns": 2, "long_token": 2, "prose_cells": 1}


def check_file(path: str) -> list[dict]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
    except OSError:
        return []
    out = []
    for start, header, body in find_tables(lines):
        if not body:
            continue
        a = analyse(header, body)
        if a["findings"]:
            a["path"] = path
            a["line"] = start + 1
            a["severity"] = max(SEVERITY[k] for k, _ in a["findings"])
            out.append(a)
    return out


SKIP_DIRS = {
    ".git", "node_modules", ".lake", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".worktrees",
}


def walk(paths):
    for p in paths:
        if os.path.isfile(p):
            if p.endswith(".md"):
                yield p
            continue
        for dirpath, dirnames, filenames in os.walk(p):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                if fn.endswith(".md"):
                    yield os.path.join(dirpath, fn)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--json", action="store_true")
    ap.add_argument(
        "--fail-on",
        choices=["none", "overflow", "any"],
        default="none",
        help="exit non-zero when findings at or above this level exist",
    )
    ap.add_argument("--limit", type=int, default=60)
    args = ap.parse_args()


    results = []
    for path in walk(args.paths):
        results.extend(check_file(path))
    results.sort(key=lambda r: (-r["severity"], -r["overflow_px"]))

    if args.json:
        json.dump(results, sys.stdout, indent=1)
        print()
    else:
        overflow = [r for r in results if r["overflow_px"] > 0]
        print(
            f"{len(results)} table(s) with findings across "
            f"{len({r['path'] for r in results})} file(s); "
            f"{len(overflow)} overflow the {CONTENT_PX}px column"
        )
        for r in results[: args.limit]:
            print(f"\n{r['path']}:{r['line']}  ({r['ncols']} cols, {r['nrows']} rows)")
            for kind, msg in r["findings"]:
                print(f"    [{kind}] {msg}")
        if len(results) > args.limit:
            print(f"\n... and {len(results) - args.limit} more")

    if args.fail_on == "overflow":
        return 1 if any(r["overflow_px"] > 0 for r in results) else 0
    if args.fail_on == "any":
        return 1 if results else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
