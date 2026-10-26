#!/usr/bin/env python3
"""An unrelated SQLite reporting application using only the portable package.

All database rows are synthetic. No model, provider, network or Plectis catalogue.
The authoriser is an additional observed integration boundary, not proved SQLite.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import platform
import sqlite3
import tempfile
import time

from plectis.views import compile_public, run_public_batch, RejectedPlan, InvalidInput

HERE = Path(__file__).resolve().parent / "public_views"


def ordinary_public_renderer(row):
    """Competent simple baseline: receives exactly the same public data."""
    return (row["run_id"] + ": " + row["score"], "passed" if row["passed"] else "needs review")


def demonstrate():
    schema = json.loads((HERE / "schema.json").read_text())
    plan = json.loads((HERE / "mixed_report.json").read_text())
    started = time.perf_counter()
    compiled = compile_public(plan, schema)
    compile_seconds = time.perf_counter() - started
    with tempfile.TemporaryDirectory(prefix="outside-report-") as temporary:
        database = Path(temporary) / "independent-lab.sqlite3"
        conn = sqlite3.connect(database)
        conn.execute("CREATE TABLE results(run_id TEXT PRIMARY KEY, score TEXT, passed INTEGER, private_note TEXT, embargo INTEGER)")
        conn.executemany("INSERT INTO results VALUES (?, ?, ?, ?, ?)", [
            ("run-001", "7/10", 1, "SYNTHETIC_PRIVATE_A", 1),
            ("run-002", "4/10", 0, "SYNTHETIC_PRIVATE_B", 0),
        ])
        conn.commit()
        reads, refused_reads = [], []

        def authorise(action, table, column, dbname, trigger):
            if action == sqlite3.SQLITE_READ and table == "results":
                if column in ("private_note", "embargo"):
                    refused_reads.append(column)
                    return sqlite3.SQLITE_DENY
                reads.append(column)
            return sqlite3.SQLITE_OK

        conn.set_authorizer(authorise)
        # Identifiers originate only in the separately owned validated schema.
        # This application fixes row membership/order independently of private data.
        selected = ", ".join('"' + name + '"' for name in compiled.public_fields)
        query = "SELECT " + selected + " FROM results ORDER BY run_id"
        rows = []
        for record in conn.execute(query):
            row = dict(zip(compiled.public_fields, record))
            if type(row["passed"]) is not int or row["passed"] not in (0, 1):
                raise ValueError("Application Boolean decoding failed")
            row["passed"] = bool(row["passed"])
            rows.append(row)
        started = time.perf_counter()
        observed = run_public_batch(compiled, rows)
        run_seconds = time.perf_counter() - started
        expected = tuple(ordinary_public_renderer(row) for row in rows)
        assert observed == expected == (("run-001: 7/10", "passed"), ("run-002: 4/10", "needs review"))
        try:
            conn.execute("SELECT private_note FROM results").fetchall()
        except sqlite3.DatabaseError:
            negative_sql_refused = True
        else:
            negative_sql_refused = False
        try:
            conn.execute("SELECT run_id FROM results WHERE embargo = 0").fetchall()
        except sqlite3.DatabaseError:
            negative_private_filter_refused = True
        else:
            negative_private_filter_refused = False
        conn.close()
    bad = json.loads((HERE / "implicit_leak.json").read_text())
    try:
        compile_public(bad, schema)
    except RejectedPlan as error:
        bad_result = str(error)
    else:
        raise AssertionError("Implicit leak accepted")
    try:
        run_public_batch(compiled, [{**rows[0], "private_note": "SYNTHETIC_PRIVATE_NOT_TRANSMITTED"}])
    except InvalidInput:
        mixed_input_refused = True
    else:
        mixed_input_refused = False
    assert negative_sql_refused and negative_private_filter_refused and mixed_input_refused
    assert not set(reads).intersection(("private_note", "embargo"))
    return {
        "status": "tested_local_integration", "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version, "rows": len(rows), "public_traces": observed,
        "query": query, "observed_successful_sql_read_columns": sorted(set(reads)),
        "negative_sql_private_read_refused": negative_sql_refused,
        "negative_sql_private_row_filter_refused": negative_private_filter_refused,
        "mixed_record_refused_before_worker_transfer": mixed_input_refused,
        "implicit_flow_rejection": bad_result,
        "public_slice": compiled.public_plan, "syntactic_read_fields": compiled.read_fields,
        "competent_public_projection_baseline_matches": observed == expected,
        "elapsed_seconds": {"compile": compile_seconds, "batch_with_recheck": run_seconds},
        "limits": ["Synthetic records and authored plan; no adoption or agent-generation study.",
                   "SQLite, Python boundary and source labelling are not formally verified.",
                   "Row membership/order and all public values are authorised inputs.",
                   "Baseline is equally confidential; no speed or maintenance advantage established."]
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    result = demonstrate()
    encoded = json.dumps(result, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded)
    print(encoded, end="")


if __name__ == "__main__":
    main()
