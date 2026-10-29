# Queue reconciliation in a temporary SQLite store

> **In plain terms.** A queue of jobs for programs to work on can contradict itself, for example a job marked as running that has no run on record. This component is given made-up queue scenarios, each run in a temporary database, such as lending a job out and recovering it when the loan expires. A checker then compares the job, run and log records against its consistency rules and reports whether the outcome matches what each scenario expects. Where a contradiction is planted on purpose, success means the expected rule fires.

Runs queue scenarios in temporary SQLite stores and reports whether the reconciliation rules match each case’s expectation.

## Run the example

From the repository root with Python 3.11 or newer:

```bash
PYTHONPATH=src python3 -m microcosm_core.organs.metabolism_queue_reconciliation run --input fixtures/first_wave/metabolism_queue_reconciliation/input --out .microcosm/component-guides/metabolism_queue_reconciliation --acceptance-out .microcosm/component-guides/metabolism_queue_reconciliation/acceptance.json --json
```

Inspect the status and findings in `.microcosm/component-guides/`; the linked result below is a historical sample.

## What it checks

The cases exercise idempotent enqueue, leases and expired-lease recovery, plus a blackboard projection. The reconciler examines job, run and log records. A running job without a run row, or a finalised run whose job is still running, is a named negative case. A negative case succeeds when the expected rule fires; the inconsistent queue is not thereby healthy.

## Limits

Runs synthetic queue cases in temporary SQLite databases and checks that the reconciler rejects a running job with no run row and a finished run whose job is still running.

## Verification

The focused tests exercise this component’s checks; they do not prove its algorithm. `make component-replays` runs its registered queue fixture cases through the shared [Dafny admission check](../formal/replay/README.md), which checks source, input, claim-policy and receipt agreement within the host’s observations. The direct command above does not itself invoke that admission gate.

## Source and evidence

- [Implementation](../src/microcosm_core/organs/metabolism_queue_reconciliation.py) and [focused tests](../tests/test_engine_room_metabolism_runtime.py)
- [Example input](../fixtures/first_wave/metabolism_queue_reconciliation/input/running_job_no_run_row_rejected.json) and [historical sample result](../receipts/first_wave/metabolism_queue_reconciliation/metabolism_queue_reconciliation_result.json)
- [Component JSON record](./metabolism_queue_reconciliation.json) and [canonical capsule](../core/paper_module_capsules.json)
- [Supporting implementation](../src/microcosm_core/engine_room/metabolism_runtime.py)
