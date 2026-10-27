# Replay concurrent-work ownership cases

`concurrency_mission_control` runs a copied mission-control builder against a temporary example directory. It then evaluates fixture cases about overlapping file claims, stale owners, deferred validation and commit status. The output is a JSON account of how those supplied cases are classified.

## Run the example

From the repository root, with Python 3.11 or later:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.concurrency_mission_control run \
  --input fixtures/first_wave/concurrency_mission_control/input \
  --out .microcosm/component-guides/concurrency_mission_control \
  --acceptance-out .microcosm/component-guides/concurrency_mission_control/acceptance.json
```

The result contains separate checks for the builder, transaction failure cases, provider-bridge records, claim ownership and closure status. Source-copy digests are checked before the exercise is accepted.

## What this checks

The classification functions derive their answers from the supplied owner and path records. A generated file with a live owner is assigned a handoff action, even if an earlier claim is stale. Release or replacement is advised when all matching claims are known stale; uncertain freshness calls for inspection. The closure classifier distinguishes completed validation from validation deferred because of host pressure. A missing seed root is rejected by the fixture. Tests alter ownership and path topology while leaving prewritten labels unchanged, checking that the computed classification changes.

## Limits

These are synthetic scenarios and copied-builder executions. The run does not coordinate currently running agents, acquire a lock in another repository or dispatch a provider job. A recommended action is a classification output, not enforcement against concurrent writers. The fixture therefore does not establish production concurrency safety.

## Verification

The generated-surface classifier calls the [proved ownership core](../formal/components/ownership_classification/README.md). For each normalized path it considers every matching claim, selecting a live claim ahead of uncertain or stale claims. The proof establishes that any matching live claim leads to a live-owner classification and handoff action. The host supplies the exact paths and freshness observations and reports the live representative; the proof does not establish actual liveness or enforce a lock.

The direct example uses that classifier. `make component-replays` separately applies the shared [replay admission check](../formal/replay/README.md) to the exported bundle.

## Sources

- [Implementation](../src/microcosm_core/organs/concurrency_mission_control.py), [exercise inputs](../fixtures/first_wave/concurrency_mission_control/input) and [tests](../tests/test_concurrency_mission_control.py).
- [Historical result](../receipts/first_wave/concurrency_mission_control/concurrency_mission_control_result.json) and [canonical description](../core/paper_module_capsules.json).
