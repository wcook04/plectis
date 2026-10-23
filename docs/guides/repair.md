# Keep valid work after a change

Repair answers “what can I keep, what must run again, and what needs explicit
handling?” You declare a task graph and which inputs changed. Its generated
Dafny core propagates those changes and blocks automatic replay of effects.

## Start with a graph

After [installing the checkout](../../examples/operations/README.md), run:

```python
from plectis.repair import make_plan, check_plan

deps = [[], [0], [1]]          # input -> score -> send
roots = [False, True, False]  # only the scoring rule changed
effects = [False, False, True]
dirty, blocked = make_plan(deps, roots, effects)
assert dirty == (False, True, True)
assert blocked == (False, False, True)
assert check_plan(deps, roots, effects, dirty, blocked)
assert not check_plan(deps, roots, effects,
                      [False, False, False], [False, False, False])
```

The input can be reused, the score must rerun and sending stays blocked. Each
dependency must precede its consumer. Exact Booleans and integer indices are
required; malformed requests raise `InvalidPlan`. A well-formed but incorrect
candidate returns `False` from `check_plan`.

## Connect functions

`Task` and `RepairSession` provide a small synchronous host:

```python
from plectis.repair import Task, RepairSession

task = Task("double", code_id="example/double", version="1",
            inputs=21, contract="integer-v1", environment="example-v1",
            freshness="fixed-input", replayable=True,
            fn=lambda value, deps: value * 2)
session = RepairSession([task])
first = session.run(session.plan())
assert first.outputs["double"] == 42
second = session.run(session.plan())
assert second.reused == ("double",)
```

Declare dependencies using `deps=("upstream_id",)`. The callback receives its
own JSON input and dependency outputs in that order. Change `version` or the
relevant contract/environment/freshness identity when their meaning changes.
The host cannot detect hidden file reads or an undeclared callback change.

Use `RepairSession(tasks, checkpoint=path)` to persist results. It creates a
companion `path.effects.jsonl` journal by default. Keep both files. You can
supply a different persistent `journal=path`; a persistent checkpoint cannot
be paired with an explicit memory-only journal. One cooperative writer owns
these files. In-memory sessions are useful for experiments, not recovery.

Mark external actions `replayable=False`. The host never calls their callback
automatically. Explicit resolution uses `begin_effect(task_id)`,
`mark_unknown(attempt, reason)` and `resolve_effect(attempt, output)`; see the
[runnable repair example](../../examples/operations/repair.py). Unknown actions
remain unsettled even if their task is removed from the graph. A matching
confirmed journal entry also prevents redispatch if its checkpoint save failed.
That case fails closed; the API does not automatically reconstruct the missing
checkpoint or promise an atomic commit across the two files.

A stale plan raises `StalePlan`; rejected or malformed plans raise `InvalidPlan`.
The combined [evaluation example](../../examples/operations/evaluation.py) shows
restart, graph removal and guarded result publication.

## What the proof says

For any valid finite declared DAG, the generated producer terminates and the
checker accepts exactly the least dirty and blocked closures. There is no fixed
graph-size bound. This establishes the decisions over your supplied facts,
not the truth of those facts or correctness of a task's output. The Python host,
filesystem and external resolver are tested separately. Hash chaining detects
accidental journal edits, not malicious replacement. No sandbox, concurrency,
external exactly-once or general crash-recovery theorem is claimed.

See the [statement and recheck command](../../formal/repair/README.md).
An equally informed ordinary cache matches the reuse decisions in the example;
there is no claimed caching novelty or measured speed advantage.
