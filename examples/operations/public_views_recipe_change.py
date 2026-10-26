#!/usr/bin/env python3
"""Change one mixed recipe and compare its public job with full semantics.

The development-only reference process uses synthetic mixed records and the
actual generated RunAll. The public API always receives public fields only.
An independently updated ordinary renderer produces the same required output.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import runpy
import subprocess
import sys

HERE = Path(__file__).resolve().parent
PUBLIC_ROW = {"run_id": "run-001", "score": "7/10", "passed": True}


def recipes():
    schema = json.loads((HERE / "public_views/schema.json").read_text())
    before = json.loads((HERE / "public_views/mixed_report.json").read_text())
    after = copy.deepcopy(before)
    after["seq"][1]["seq"][1]["if"]["then"]["emit"]["value"]["literal"] = "approved"
    return schema, {"before": before, "after": after}


def reference_observations(views_root):
    """Development helper for these synthetic fixtures, never public execution.

    Run in an isolated subprocess. Reuse the tested decoder and sealed loader;
    this helper does not expose a supported mixed-record library interface.
    """
    worker = runpy.run_path(str(views_root / "_worker.py"))
    loader = runpy.run_path(str(views_root.parent / "_sealed_kernel.py"))
    schema, plans = recipes()
    synthetic_rows = [
        {**PUBLIC_ROW, "private_note": "SYNTHETIC_PRIVATE_A", "embargo": True},
        {**PUBLIC_ROW, "private_note": "SYNTHETIC_PRIVATE_B", "embargo": False},
    ]
    result = {}
    with loader["sealed_kernel"](views_root / "_generated", "Release"):
        import _dafny
        import Release

        # run_path returns a copy; the decoder functions retain their globals.
        decoder_globals = worker["decode_schema"].__globals__
        decoder_globals.update(_dafny=_dafny, R=Release)
        names, types, high = worker["decode_schema"](schema)
        for revision, plan in plans.items():
            program = worker["Decoder"](names).cmd(plan)
            accepted, _ = Release.default__.CheckAndSlice(types, high, program)
            if not accepted:
                raise RuntimeError("Synthetic reference recipe was rejected")
            result[revision] = []
            for row in synthetic_rows:
                values = _dafny.Seq([worker["value"](row[name]) for name in names])
                if not Release.default__.ValidEnvironment(types, values):
                    raise RuntimeError("Invalid synthetic reference environment")
                events = Release.default__.RunAll(program, values)
                result[revision].append([
                    {"public": event.isPublic, "text": event.text.VerbatimString(False)}
                    for event in events
                ])
    return result


def ordinary_public_renderer(row, passed_message):
    """Equal-information baseline, explicitly updated for each requirement."""
    return [row["run_id"] + ": " + row["score"],
            passed_message if row["passed"] else "needs review"]


def demonstrate():
    from plectis.views import compile_public, run_public, RejectedPlan
    from plectis.views import _api

    views_root = Path(_api.__file__).resolve().parent
    process = subprocess.run(
        [sys.executable, "-I", "-B", str(Path(__file__).resolve()),
         "--reference-root", str(views_root)],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=True,
    )
    references = json.loads(process.stdout)
    schema, plans = recipes()
    revisions = {}
    for revision, message in (("before", "passed"), ("after", "approved")):
        compiled = compile_public(plans[revision], schema)
        public = list(run_public(compiled, dict(PUBLIC_ROW)))
        expected = ["run-001: 7/10", message]
        ordinary = ordinary_public_renderer(PUBLIC_ROW, message)
        mixed = references[revision]
        projections = [[event["text"] for event in trace if event["public"]]
                       for trace in mixed]
        assert public == expected == ordinary
        assert projections == [public, public]
        assert mixed[0] != mixed[1]
        assert set(compiled.read_fields) <= set(PUBLIC_ROW)
        revisions[revision] = {"public_trace": public, "ordinary_trace": ordinary,
                               "mixed_reference_traces": mixed,
                               "public_read_fields": compiled.read_fields}

    leaking = copy.deepcopy(plans["after"])
    leaking["seq"][1]["seq"][1]["if"]["condition"] = {"input": "embargo"}
    try:
        compile_public(leaking, schema)
    except RejectedPlan:
        private_control_refused = True
    else:
        raise AssertionError("Private control of public output was accepted")
    return {
        "status": "tested_changed_recipe", "revisions": revisions,
        "private_control_change_refused": private_control_refused,
        "ordinary_renderer_matches_both_revisions": True,
        "limits": [
            "Synthetic fixture; mixed execution is a development reference only.",
            "Public worker receives only run_id, score and passed.",
            "The ordinary renderer matches; no maintenance or performance advantage measured.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--format", choices=("json", "text"), default="json")
    parser.add_argument("--reference-root", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.reference_root is not None:
        print(json.dumps(reference_observations(args.reference_root)))
        return
    result = demonstrate()
    if args.format == "text":
        print("One recipe change: passed -> approved.")
        print("Both public jobs match the full mixed recipe's public output.")
        print("Private variations change only internal events; private-controlled public output is refused.")
        print("The ordinary public renderer matches both versions; no maintenance advantage is measured.")
    else:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
