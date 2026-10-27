# SQLite queue and reconciliation fixtures

The fixture evaluator creates temporary SQLite databases to exercise a job queue, expiring leases, a claim event log with an active view, and reconciliation. The queue rejects a duplicate idempotency key while its job is active. An expired claim can be requeued; a running job without a run row instead produces an operator-review finding.

When a later event contradicts an assertion, the active view excludes it while retaining the original assertion and contradiction in the event history. Tests also cover finalized runs whose jobs still say running and stale launch logs. The fixture matrix passes when each case produces its expected result; an unknown exercise is rejected.

This is a synthetic local SQLite exercise. It does not dispatch workers or providers, reproduce a distributed database, or automatically repair ambiguous state.

## Run the example

Python 3.11 or later is required. From the repository root, run the public fixture matrix. The JSON goes to standard output; temporary databases or files are cleaned up by the evaluator.

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.metabolism_runtime evaluate-fixtures --input fixtures/first_wave/engine_room_metabolism_runtime/input --json
```

## Verification

The fixture and tests exercise the queue, event projection and reconciliation rules. This helper has no separate registered component replay or component-specific formal proof; the Engine Room composition does not confer one. Passing tests support the exercised SQLite cases, not every possible runtime state.

## Source

[Implementation](../src/microcosm_core/engine_room/metabolism_runtime.py) · [Input](../fixtures/first_wave/engine_room_metabolism_runtime/input) · [Tests](../tests/test_engine_room_metabolism_runtime.py) · [Historical sample](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) · [JSON record](engine_room_metabolism_runtime.json) (the sample is the composed Engine Room result)

[SQLite write-ahead logging](https://www.sqlite.org/wal.html) describes the database mode used here.
