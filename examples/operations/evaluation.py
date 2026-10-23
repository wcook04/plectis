"""Change an evaluation, retain observations, and publish the current result.

Adapted from research return p04's prototype/demo.py (evaluation graph and
equally informed cache comparison) and p13's artifacts/worker_integration.py
(a paused ordinary Python worker), 23 October 2026. The public Repair and
Publish implementations retain their own source/proof provenance.

All observations are deterministic local fixtures standing in for costly model
calls. No model, service or network is used. The separate export is a local
file write with deliberately lost acknowledgement, not a sent notification.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import tempfile
from threading import Event

from plectis.publish import PublishStore, StaleTicket
from plectis.repair import RepairSession, Task


def encode(value):
    return json.dumps(value, sort_keys=True, allow_nan=False,
                      separators=(",", ":")).encode("utf-8")


def graph(calls, metric_version="1", *, include_export=True):
    """Three observation sets; only dataset a's scoring rule changes in v2."""
    def task(name, callback, *, deps=(), inputs=None, version="1", replayable=True):
        def counted(arguments, outputs):
            calls[name] += 1
            return callback(arguments, outputs)
        return Task(name, code_id="evaluation-example/" + name, version=version,
                    deps=deps, inputs=inputs, contract="evaluation-json-v1",
                    environment="stdlib-fixture-v1", freshness="frozen-input-v1",
                    replayable=replayable, fn=counted)

    def observe(inputs, outputs):
        seed = outputs[0]["seed"]
        return [{"quality": (seed * 7 + i * 11) % 101,
                 "tokens": 70 + (seed * 13 + i * 3) % 40} for i in range(6)]

    def score(inputs, outputs):
        rows = outputs[0]
        return sum(row["quality"] - inputs["token_penalty"] * row["tokens"]
                   for row in rows) / len(rows)

    tasks = []
    for index, dataset in enumerate("abc"):
        tasks.append(task("input_" + dataset, lambda inputs, outputs: inputs,
                          inputs={"dataset": dataset, "seed": index + 1}))
        tasks.append(task("observe_" + dataset, observe, deps=("input_" + dataset,)))
        changed = dataset == "a" and metric_version != "1"
        tasks.append(task("score_" + dataset, score, deps=("observe_" + dataset,),
                          inputs={"token_penalty": 0.2 if changed else 0},
                          version=metric_version if dataset == "a" else "1"))
    tasks.append(task("aggregate", lambda inputs, values: {"mean": sum(values) / len(values)},
                      deps=("score_a", "score_b", "score_c")))
    tasks.append(task("report", lambda inputs, values: {**values[0], **inputs},
                      deps=("aggregate",), inputs={"metric_version": metric_version}))
    if include_export:
        # Supplied so a test can observe an accidental dispatch. Repair must
        # leave this non-replayable action to an explicit external resolver.
        tasks.append(task("export", lambda inputs, values: values[0],
                          deps=("report",), replayable=False))
    return tasks


def ordinary_cache_oracle(plan):
    """Independent equally informed dependency-cache decision baseline.

    This comparison is not used by Repair's dispatcher. It expands sets along
    graph edges instead of calling the generated planner/checker.
    """
    children = {i: [] for i in range(len(plan.order))}
    for child, parents in enumerate(plan.deps):
        for parent in parents:
            children[parent].append(child)

    def closure(seeds):
        reached = set(seeds)
        pending = list(reached)
        while pending:
            for child in children[pending.pop()]:
                if child not in reached:
                    reached.add(child)
                    pending.append(child)
        return reached

    dirty = closure(i for i, value in enumerate(plan.roots) if value)
    blocked = closure(i for i in dirty if plan.effects[i])
    return {name: "blocked" if i in blocked else "rerun" if i in dirty else "reuse"
            for i, name in enumerate(plan.order)}


def counts(result):
    return {"reuse": len(result.reused), "rerun": len(result.executed),
            "blocked": len(result.blocked)}


def _paused_publication(database, ticket, payload, started, resume):
    with PublishStore(database) as store:
        started.set()
        if not resume.wait(timeout=15):
            raise TimeoutError("coordinator did not resume the demonstration worker")
        try:
            store.publish(ticket, "late-worker-v1", payload)
        except StaleTicket:
            return "rejected_stale"
        return "published"


def run_demo(directory):
    """Use a fresh caller-owned directory; return ordinary JSON evidence."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    checkpoint, journal = directory / "checkpoint.json", directory / "effects.jsonl"
    database, export_file = directory / "results.sqlite", directory / "export.jsonl"
    if any(path.exists() for path in (checkpoint, journal, database, export_file)):
        raise ValueError("the example requires a fresh directory")

    calls = Counter()
    first = RepairSession(graph(calls), checkpoint=checkpoint, journal=journal)
    initial = first.run(first.plan())
    initial_report = initial.outputs["report"]
    initial_payload = encode(initial_report)
    initial_observation_calls = sum(calls["observe_" + name] for name in "abc")

    # A separate local action may have happened even when its acknowledgement
    # is missing. Its journal is independent of the SQLite publication store.
    attempt = first.begin_effect("export")
    with export_file.open("ab") as handle:
        handle.write(initial_payload + b"\n")
        handle.flush()
        os.fsync(handle.fileno())
    first.mark_unknown(attempt, "local export completed; acknowledgement deliberately lost")

    with PublishStore(database) as store:
        store.create("evaluation", "frozen-input-v1", "metric-v1")
        initial_ticket = store.grant("evaluation", "first-worker")
        initial_publication = store.publish(initial_ticket, "evaluation-v1", initial_payload)
        old_ticket = store.grant("evaluation", "paused-worker")
        started, resume = Event(), Event()
        with ThreadPoolExecutor(max_workers=1) as executor:
            late = executor.submit(_paused_publication, database, old_ticket,
                                   initial_payload, started, resume)
            try:
                if not started.wait(timeout=15):
                    raise TimeoutError("demonstration worker did not start")
                before = calls.copy()
                changed = RepairSession(graph(calls, "2"), checkpoint=checkpoint,
                                        journal=journal)
                plan = changed.plan()
                ordinary = ordinary_cache_oracle(plan)
                updated = changed.run(plan)
                updated_payload = encode(updated.outputs["report"])
                repair_observation_calls = sum(calls["observe_" + name] - before["observe_" + name]
                                               for name in "abc")
                store.change_identity("evaluation", "frozen-input-v1", "metric-v2")
                current_before_publication = store.read_current("evaluation")
                new_ticket = store.grant("evaluation", "metric-v2-worker")
                publication = store.publish(new_ticket, "evaluation-v2", updated_payload)
            finally:
                resume.set()
            old_worker = late.result(timeout=15)

    # Reopening demonstrates durable state and exact-request replay. Historical
    # replay is an observation of the old publication, not renewed permission.
    with PublishStore(database) as restarted:
        historical = restarted.publish(initial_ticket, "evaluation-v1", initial_payload)
        current = restarted.read_current("evaluation")
    if current is None:
        raise AssertionError("new evaluation was not retained")

    pruned = RepairSession(graph(calls, "2", include_export=False),
                           checkpoint=checkpoint, journal=journal)
    without_export = pruned.run(pruned.plan())
    restored = RepairSession(graph(calls, "2"), checkpoint=checkpoint, journal=journal)
    after_restart = restored.run(restored.plan())
    try:
        restored.begin_effect("export")
    except ValueError:
        retry_blocked = True
    else:
        raise AssertionError("an unsettled export acquired a second attempt")

    ordinary_counts = dict(Counter(ordinary.values()))
    result = {
        "evaluation": {"initial": initial_report, "updated": updated.outputs["report"]},
        "repair": {"initial": counts(initial), "metric_change": counts(updated),
                   "rerun_tasks": list(updated.executed),
                   "initial_observation_calls": initial_observation_calls,
                   "repair_observation_calls": repair_observation_calls},
        "publication": {"old_worker": old_worker,
                        "initial_generation": initial_publication.result.generation,
                        "current_generation": publication.result.generation,
                        "old_result_hidden_after_metric_change": current_before_publication is None,
                        "historical_retry": historical.status,
                        "historical_retry_is_current": historical.result == current,
                        "current_result": json.loads(current.payload)},
        "external_action": {
            "local_exports_observed": len(export_file.read_bytes().splitlines()),
            "automatic_export_callbacks": calls["export"],
            "unsettled_after_graph_removal": [item["task"] for item in without_export.unresolved_effects],
            "restored_blocked_tasks": list(after_restart.blocked),
            "retry_blocked": retry_blocked, "settled": after_restart.settled},
        "comparison": {"ordinary_cache_decisions": ordinary_counts,
                       "repair_decisions": counts(updated),
                       "equally_informed_cache_ties": ordinary == plan.classification(),
                       "speed_advantage_claimed": False},
        "assurance": {
            "proved": "Dafny graph planner/checker over supplied graph facts",
            "tested": "Python host, persistence, callbacks, and SQLite publication adapter",
            "boundary": "Declared dependencies and replayability are trusted; this is a local fixture, not a proof of end-to-end evaluation correctness."},
    }
    if (old_worker != "rejected_stale" or current.payload != updated_payload
            or historical.status != "replayed" or historical.result == current
            or calls["export"] or not without_export.unresolved_effects):
        raise AssertionError("combined example violated its observed behavior contract")
    return result


def render_text(result):
    """Summarise the observed result without replacing its JSON evidence."""
    repair = result["repair"]
    changed = repair["metric_change"]
    publication = result["publication"]
    external = result["external_action"]
    comparison = result["comparison"]
    ordinary = comparison["ordinary_cache_decisions"]
    assurance = result["assurance"]
    return "\n".join([
        f"After metric change: {changed['reuse']} reused, {changed['rerun']} rerun, "
        f"{changed['blocked']} blocked.",
        "Rerun tasks: " + (", ".join(repair["rerun_tasks"]) or "none") + ".",
        f"New observation calls: {repair['repair_observation_calls']}.",
        f"Delayed worker: {publication['old_worker'].replace('_', ' ')}; "
        f"current metric: {publication['current_result']['metric_version']}.",
        f"Historical retry: {publication['historical_retry']}; historical result is current: "
        f"{'yes' if publication['historical_retry_is_current'] else 'no'}.",
        "Unresolved after graph removal: "
        + (", ".join(external["unsettled_after_graph_removal"]) or "none")
        + f"; retry blocked: {'yes' if external['retry_blocked'] else 'no'}.",
        "Equally informed cache ties: "
        + ("yes" if comparison["equally_informed_cache_ties"] else "no")
        + f" ({ordinary.get('reuse', 0)} reuse, {ordinary.get('rerun', 0)} rerun, "
        f"{ordinary.get('blocked', 0)} blocked).",
        "Proved: " + assurance["proved"],
        "Tested: " + assurance["tested"],
        "Boundary: " + assurance["boundary"],
    ]) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, help="retain the observed JSON summary at this path")
    parser.add_argument("--format", choices=("json", "text"), default="json",
                        help="terminal output format (default: json; --out always writes JSON)")
    arguments = parser.parse_args(argv)
    with tempfile.TemporaryDirectory(prefix="plectis-evaluation-") as folder:
        result = run_demo(folder)
    json_text = json.dumps(result, indent=2, allow_nan=False) + "\n"
    if arguments.out is not None:
        arguments.out.parent.mkdir(parents=True, exist_ok=True)
        arguments.out.write_text(json_text, encoding="utf-8")
    print(render_text(result) if arguments.format == "text" else json_text, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
