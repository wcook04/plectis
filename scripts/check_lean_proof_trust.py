#!/usr/bin/env python3
"""Fail closed when shipped Lean source weakens the public proof-trust floor."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
NATIVE_DECIDE = "native_" + "decide"
PROOF_TRUST_RE = re.compile(
    rf"\bsorry\b|\badmit\b|(?<![\w.])axiom\s+"
    rf"|{re.escape(NATIVE_DECIDE)}"
    r"|\+native\b|\bnative\s*:=\s*true\b"
    r"|^\s*(?:unsafe|partial)\s+(?:def|theorem|opaque|instance)\b"
    r"|^\s*set_option\s+(?:maxHeartbeats|maxRecDepth)\s+0\b",
    re.M,
)


def lean_code_without_comments_and_strings(text: str) -> str:
    """Remove nested comments, line comments, and strings while preserving lines."""
    out: list[str] = []
    index = 0
    block_depth = 0
    in_string = False
    while index < len(text):
        if block_depth:
            if text.startswith("/-", index):
                block_depth += 1
                out.extend("  ")
                index += 2
            elif text.startswith("-/", index):
                block_depth -= 1
                out.extend("  ")
                index += 2
            else:
                out.append("\n" if text[index] == "\n" else " ")
                index += 1
        elif in_string:
            if text[index] == "\\" and index + 1 < len(text):
                out.extend("  ")
                index += 2
            elif text[index] == '"':
                in_string = False
                out.append(" ")
                index += 1
            else:
                out.append("\n" if text[index] == "\n" else " ")
                index += 1
        elif text.startswith("--", index):
            end = text.find("\n", index)
            if end < 0:
                out.extend(" " * (len(text) - index))
                break
            out.extend(" " * (end - index))
            index = end
        elif text.startswith("/-", index):
            block_depth = 1
            out.extend("  ")
            index += 2
        elif text[index] == '"':
            in_string = True
            out.append(" ")
            index += 1
        else:
            out.append(text[index])
            index += 1
    return "".join(out)


def first_violation(text: str) -> tuple[int, str] | None:
    """Return the first executable violation as a one-based line and token."""
    if PROOF_TRUST_RE.search(text) is None:
        return None
    match = PROOF_TRUST_RE.search(lean_code_without_comments_and_strings(text))
    if match is None:
        return None
    return text.count("\n", 0, match.start()) + 1, match.group(0).strip()


def shipped_lean_sources() -> list[Path]:
    """Enumerate every shipped Lean file, excluding only local build/cache roots."""
    excluded_parts = {".git", ".lake", ".microcosm", "__pycache__"}
    return sorted(
        path
        for path in ROOT.rglob("*.lean")
        if not any(part in excluded_parts for part in path.relative_to(ROOT).parts)
    )


def main() -> int:
    sources = shipped_lean_sources()
    failures: list[str] = []
    for path in sources:
        violation = first_violation(path.read_text(encoding="utf-8"))
        if violation is None:
            continue
        line, token = violation
        failures.append(f"{path.relative_to(ROOT)}:{line}: {token}")

    if failures:
        print(
            f"Lean proof-trust check: {len(failures)} violation(s) "
            f"across {len(sources)} shipped Lean files",
            file=sys.stderr,
        )
        for failure in failures:
            print(f"  FAIL {failure}", file=sys.stderr)
        return 1

    print(
        "Lean proof-trust check: pass "
        f"({len(sources)} shipped Lean files; no placeholders, custom axioms, "
        "native evaluation, unsafe declarations, or unbounded kernel limits)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
