# SPDX-FileCopyrightText: 2026 Will Cook
# SPDX-License-Identifier: CC-BY-4.0
"""Classify, mechanically, what every component's checks actually do.

The paper says that a validator "checks exactly the property written into it,
which can be narrower than the claim as worded", and then leaves the reader to
take that on trust.  This script replaces the general warning with a count.

It parses every component's source with Python's own ``ast`` module and
classifies the *operations* each check performs into five kinds:

``text_presence``
    A literal substring test against text that is never executed --
    ``"some literal" in source_text``.  This is the weakest possible check: it
    passes if the string appears anywhere in the file, including inside a
    comment, and fails on a functionally identical rewrite.

``existence_or_digest``
    A file-existence test or a hash comparison.  Establishes that a named file
    is present and unchanged; establishes nothing about behaviour.

``external_tool``
    A subprocess invocation of a named external tool (``lean``, ``lake``,
    ``swift``, ``git``, ``pytest``, ``python``).  Inherits whatever the tool
    warrants.

``recomputation``
    Arithmetic or logical work that derives a value and compares it against a
    separately supplied one.  This is the only kind that can catch a wrong
    answer as opposed to a changed file.

``structural``
    Schema, key-presence, and type checks over parsed data.

The output is a per-component profile plus a whole-registry summary.  Nothing
here is a judgement about whether a component's prose oversells its mechanism;
that comparison needs a reader.  This script establishes the mechanical facts
that such a reading has to start from, and it is rerunnable by anyone.

Usage::

    python3 scripts/audit_check_composition.py --out /tmp/plectis-composition.json
"""

from __future__ import annotations

import argparse
import ast
import json
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
REGISTRY = REPO / "core" / "organ_registry.json"
ORGAN_DIR = REPO / "src" / "microcosm_core" / "organs"

EXTERNAL_TOOLS = {"lean", "lake", "swift", "git", "pytest", "python", "python3", "pip"}

TEXT_PRESENCE = "text_presence"
EXISTENCE_OR_DIGEST = "existence_or_digest"
EXTERNAL_TOOL = "external_tool"
RECOMPUTATION = "recomputation"
STRUCTURAL = "structural"

KINDS = (TEXT_PRESENCE, EXISTENCE_OR_DIGEST, EXTERNAL_TOOL, RECOMPUTATION, STRUCTURAL)


class CheckVisitor(ast.NodeVisitor):
    """Count check operations by kind within one module."""

    def __init__(self) -> None:
        self.counts: Counter[str] = Counter()
        self.text_presence_examples: list[str] = []

    # `"literal" in name` -- substring containment against unexecuted text.
    def visit_Compare(self, node: ast.Compare) -> None:
        for op, comparator in zip(node.ops, node.comparators):
            if isinstance(op, ast.In) and isinstance(node.left, ast.Constant):
                if isinstance(node.left.value, str) and len(node.left.value) > 3:
                    # A containment test against a dict/set literal is a
                    # membership test, not a text scan; only count when the
                    # right-hand side is a plain name or attribute (a blob of
                    # text) rather than a collection display.
                    if isinstance(comparator, (ast.Name, ast.Attribute, ast.Subscript)):
                        self.counts[TEXT_PRESENCE] += 1
                        if len(self.text_presence_examples) < 5:
                            self.text_presence_examples.append(node.left.value[:90])
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        name = _call_name(node)

        if name in {"exists", "is_file", "is_dir"}:
            self.counts[EXISTENCE_OR_DIGEST] += 1
        elif name in {"sha256", "md5", "sha1", "blake2b", "hexdigest"}:
            self.counts[EXISTENCE_OR_DIGEST] += 1
        elif name in {"run", "check_output", "Popen", "call", "check_call"}:
            if _mentions_external_tool(node):
                self.counts[EXTERNAL_TOOL] += 1
        elif name in {"isinstance", "get", "keys", "items"}:
            self.counts[STRUCTURAL] += 1
        elif name in {"sqrt", "fsum", "abs", "round", "sum", "min", "max", "pow"}:
            self.counts[RECOMPUTATION] += 1
        elif name in {"Fraction", "Decimal", "isclose"}:
            self.counts[RECOMPUTATION] += 1

        self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> None:
        if isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod)):
            self.counts[RECOMPUTATION] += 1
        self.generic_visit(node)


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _mentions_external_tool(node: ast.Call) -> bool:
    for sub in ast.walk(node):
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            head = sub.value.strip().split("/")[-1].split()[0] if sub.value.strip() else ""
            if head in EXTERNAL_TOOLS:
                return True
    return False


def profile(path: Path) -> dict:
    source = path.read_text(encoding="utf-8", errors="replace")
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return {"error": f"unparsable: {exc}"}
    visitor = CheckVisitor()
    visitor.visit(tree)
    counts = {kind: visitor.counts.get(kind, 0) for kind in KINDS}
    total = sum(counts.values())
    return {
        "counts": counts,
        "total_operations": total,
        "share": {
            kind: (round(counts[kind] / total, 3) if total else 0.0) for kind in KINDS
        },
        "text_presence_examples": visitor.text_presence_examples,
        "lines": source.count("\n") + 1,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/plectis-composition.json")
    args = parser.parse_args()

    registry = json.loads(REGISTRY.read_text())
    components = registry["implemented_organs"]

    profiles = {}
    missing = []
    for component in components:
        organ_id = component["organ_id"]
        path = ORGAN_DIR / f"{organ_id}.py"
        if not path.exists():
            missing.append(organ_id)
            continue
        record = profile(path)
        record["organ_id"] = organ_id
        record["evidence_class"] = component.get("evidence_class")
        record["evidence_strength_rank"] = component.get("evidence_strength_rank")
        profiles[organ_id] = record

    # Whole-registry aggregates.
    totals = Counter()
    for record in profiles.values():
        for kind in KINDS:
            totals[kind] += record["counts"][kind]

    # A component "leans on text presence" when substring containment is its
    # single largest category of check operation.
    text_led = sorted(
        organ_id
        for organ_id, record in profiles.items()
        if record["counts"][TEXT_PRESENCE] > 0
        and record["counts"][TEXT_PRESENCE]
        == max(record["counts"][kind] for kind in KINDS)
    )
    any_text = sorted(
        organ_id
        for organ_id, record in profiles.items()
        if record["counts"][TEXT_PRESENCE] > 0
    )
    no_recompute = sorted(
        organ_id
        for organ_id, record in profiles.items()
        if record["counts"][RECOMPUTATION] == 0
    )
    uses_external = sorted(
        organ_id
        for organ_id, record in profiles.items()
        if record["counts"][EXTERNAL_TOOL] > 0
    )

    report = {
        "components_profiled": len(profiles),
        "components_missing_source": missing,
        "operation_totals": dict(totals),
        "components_with_any_text_presence_check": {
            "count": len(any_text),
            "ids": any_text,
        },
        "components_whose_largest_category_is_text_presence": {
            "count": len(text_led),
            "ids": text_led,
        },
        "components_with_no_recomputation": {
            "count": len(no_recompute),
            "ids": no_recompute,
        },
        "components_invoking_an_external_tool": {
            "count": len(uses_external),
            "ids": uses_external,
        },
        "profiles": profiles,
    }

    Path(args.out).write_text(json.dumps(report, indent=2))

    print(f"components profiled: {len(profiles)}")
    if missing:
        print(f"missing source     : {len(missing)} -> {missing}")
    print()
    print("operation totals across the registry:")
    for kind in KINDS:
        print(f"  {kind:<22} {totals[kind]}")
    print()
    print(f"with any text-presence check          : {len(any_text)}/{len(profiles)}")
    print(f"whose largest category is text presence: {len(text_led)}/{len(profiles)}")
    print(f"with no recomputation at all           : {len(no_recompute)}/{len(profiles)}")
    print(f"invoking an external tool              : {len(uses_external)}/{len(profiles)}")
    print(f"\nreport: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
