"""Local evaluation-repair example: no model, network or service calls."""
from collections import Counter
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from time import perf_counter

from plectis.repair import InvalidPlan, RepairSession, Task


def ordinary_cache_oracle(plan):
    """Equally informed comparison ONLY; the dispatcher never uses this code.

    Independent set expansion, rather than the generated topological recurrence.
    """
    children = {i: set() for i in range(len(plan.order))}
    for child, parents in enumerate(plan.deps):
        for parent in parents:
            children[parent].add(child)
    def reachable(seeds):
        reached = set(seeds)
        frontier = list(reached)
        while frontier:
            for child in children[frontier.pop()]:
                if child not in reached:
                    reached.add(child)
                    frontier.append(child)
        return reached
    dirty = reachable(i for i, value in enumerate(plan.roots) if value)
    blocked = reachable(i for i in dirty if plan.effects[i])
    return {key: ("blocked" if i in blocked else "rerun" if i in dirty else "reuse")
            for i, key in enumerate(plan.order)}


def graph(calls, metric_version="1", include_publish=True):
    def counted(name, callback):
        def run(inputs, deps):
            calls[name] += 1
            return callback(inputs, deps)
        return run

    def task(name, fn, *, deps=(), inputs=None, version="1", replayable=True):
        return Task(name, code_id="evaluation-demo/" + name, version=version,
                    deps=deps, inputs=inputs, contract="demo-json-v1",
                    environment="stdlib-python-demo-v1", freshness="frozen-sample-epoch-1",
                    replayable=replayable, fn=counted(name, fn))

    def generate(inputs, deps):
        seed = deps[0]["seed"]
        # Small deterministic fixture standing in for expensive generation.
        # The measured counts are callback invocations, not model costs.
        return [{"quality": (seed * 7 + i * 11) % 101,
                 "tokens": 70 + (seed * 13 + i * 3) % 40} for i in range(6)]

    def score(inputs, deps):
        records = deps[0]
        return sum(row["quality"] - inputs["penalty"] * row["tokens"]
                   for row in records) / len(records)

    tasks = []
    for index, branch in enumerate("abc"):
        tasks.append(task("input_" + branch, lambda inputs, deps: inputs,
                          inputs={"dataset": branch, "seed": index + 1}))
        tasks.append(task("sample_" + branch, generate, deps=("input_" + branch,)))
        changed = branch == "a" and metric_version != "1"
        tasks.append(task("score_" + branch, score, deps=("sample_" + branch,),
                          inputs={"penalty": int(metric_version) / 10 if changed else 0},
                          version=metric_version if branch == "a" else "1"))
    tasks.append(task("aggregate", lambda inputs, deps: {"mean": sum(deps) / len(deps)},
                      deps=("score_a", "score_b", "score_c")))
    tasks.append(task("report", lambda inputs, deps: {"evaluation": deps[0], "schema": 1},
                      deps=("aggregate",)))
    if include_publish:
        # This callable is deliberately supplied to test that the host never
        # invokes it. Only the explicit external resolver may act.
        tasks.append(task("publish", lambda inputs, deps: {"danger": "called"},
                          deps=("report",), replayable=False))
    return tasks


def describe(result):
    return {"reused": list(result.reused), "executed": list(result.executed),
            "blocked": list(result.blocked), "failed": result.failed,
            "settled": result.settled,
            "unsettled_tasks": [item["task"] for item in result.unresolved_effects]}


def run_demo(directory):
    directory = Path(directory)
    checkpoint, journal = directory / "checkpoint.json", directory / "effects.jsonl"
    calls, restart_calls = Counter(), Counter()
    session = RepairSession(graph(calls), checkpoint=checkpoint, journal=journal)
    start = perf_counter()
    first_plan = session.plan()
    initial = session.run(first_plan)
    initial_seconds = perf_counter() - start
    assert len(initial.executed) == 11 and initial.blocked == ("publish",)

    # An external resolver makes ONE simulated publish, then loses the ack.
    # This is a local list append, with no external service or network access.
    attempt = session.begin_effect("publish")
    simulated_sink = [initial.outputs["report"]]
    session.mark_unknown(attempt, "simulated publish committed; acknowledgement lost")

    repaired = RepairSession(graph(calls, "2"), checkpoint=checkpoint, journal=journal)
    start = perf_counter()
    plan = repaired.plan()
    plan_seconds = perf_counter() - start
    ordinary = ordinary_cache_oracle(plan)
    assert ordinary == plan.classification()
    try:
        repaired.run(replace(plan, blocked=tuple(False for _ in plan.blocked)))
    except InvalidPlan:
        barrier_mutant_rejected = True
    else:
        raise AssertionError("unsafe candidate accepted")
    repaired_result = repaired.run(plan)
    assert len(repaired_result.reused) == 8 and len(repaired_result.executed) == 3
    assert repaired_result.blocked == ("publish",) and not repaired_result.settled
    try:
        repaired.begin_effect("publish")
    except ValueError:
        automatic_second_attempt_prevented = True
    else:
        raise AssertionError("unsettled effect was retried")

    restart = RepairSession(graph(restart_calls, "2"),
                            checkpoint=directory / "restart.json", journal=journal)
    restarted_result = restart.run(restart.plan())
    assert len(restarted_result.executed) == 11
    assert restarted_result.outputs["report"] == repaired_result.outputs["report"]

    # Remove publish from the DAG and change the metric again. Pure work still
    # proceeds, but the removed ambiguous effect remains an unresolved fact.
    pruned = RepairSession(graph(calls, "3", include_publish=False),
                           checkpoint=checkpoint, journal=journal)
    pruned_result = pruned.run(pruned.plan())
    assert len(pruned_result.executed) == 3 and not pruned_result.blocked
    assert not pruned_result.settled and pruned_result.unresolved_effects[0]["task"] == "publish"
    assert calls["publish"] == 0 and restart_calls["publish"] == 0

    comparison = {
        "verified_repair": {"reuse": 8, "rerun": 3, "blocked": 1,
                            "sample_callbacks": 0},
        "equally_informed_dependency_cache": {
            "reuse": sum(value == "reuse" for value in ordinary.values()),
            "rerun": sum(value == "rerun" for value in ordinary.values()),
            "blocked": sum(value == "blocked" for value in ordinary.values()),
            "sample_callbacks": sum(ordinary["sample_" + key] == "rerun" for key in "abc")},
        "restart_with_same_effect_safety": {"reuse": 0, "rerun": 11, "blocked": 1,
                                             "sample_callbacks": 3}}
    result = {"example": "local deterministic evaluation fixture; no model/service calls",
              "initial": describe(initial), "repair": describe(repaired_result),
              "repair_classification": plan.classification(), "comparison": comparison,
              "restart": describe(restarted_result), "pruned_graph": describe(pruned_result),
              "simulated_publish_invocations": len(simulated_sink),
              "automatic_publish_callback_invocations": calls["publish"] + restart_calls["publish"],
              "barrier_mutant_rejected": barrier_mutant_rejected,
              "second_effect_attempt_prevented": automatic_second_attempt_prevented,
              "illustrative_wall_seconds": {"initial_plan_and_run": initial_seconds,
                                             "repair_plan": plan_seconds},
              "timing_note": "Includes fresh Python process startup; not a benchmark or model-cost estimate."}
    (directory / "result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    # A fresh directory makes repeated executions independent and reproducible.
    with tempfile.TemporaryDirectory(prefix="plectis-repair-demo-") as directory:
        print(json.dumps(run_demo(directory), indent=2))
