# Engine Room Metabolism Runtime

Public exercise:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.metabolism_runtime evaluate-fixtures --input fixtures/first_wave/engine_room_metabolism_runtime/input --json
```

This capsule is a source-faithful public refactor of the macro metabolism
runtime's durable SQLite queue, lease recovery, blackboard claim-event
projection, and cold-start reconciler. It runs only on synthetic fixture
databases and fixture logs.

It does not ship the private live metabolism database, runtime status JSON,
operator sessions, provider state, or live logs. It does not dispatch agents or
providers, and reconciliation findings require operator review for ambiguous
runtime cases.
