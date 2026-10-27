# Share a duplicate command run

Singleflight coordinates matching local command invocations. It keys a run by command, working directory, resource class and scoped state, then lets a leader execute while a concurrent follower waits and receives the leader’s result. Completed results can also be reused when explicitly requested.

## Run the example

From the repository root, with Python 3.11 or newer and a POSIX environment providing file locks:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.command_run_singleflight evaluate-fixtures \
  --input fixtures/first_wave/engine_room_command_run_singleflight/input --json
```

The fixtures exercise leader execution, completed-result reuse, a changed scoped file and an empty command. The empty command is rejected. The result reports whether each case met its expectation; fixture execution uses temporary state. The tests also start concurrent processes and verify that one command ran and both received its output. A follower that times out does not launch a duplicate.

This is a local command coordination helper, not a scheduler or a guarantee that a command is safe to execute. Scope choices affect the key, so include relevant files when using reuse. Only `PYTHONPATH` and `PYTEST_ADDOPTS` are included from the environment; changes to other variables do not invalidate a cached result. The name follows the duplicate-suppression pattern of [Go singleflight](https://pkg.go.dev/golang.org/x/sync/singleflight).

## Verification

The focused tests check duplicate execution, completed-result reuse and timeout behavior. This helper has no registered component replay route and no component-specific formal proof in this repository. Those tests do not prove the coordination algorithm for every process or failure scenario.

## Source and evidence

- [Implementation](../src/microcosm_core/engine_room/command_run_singleflight.py) and [focused tests](../tests/test_engine_room_command_run_singleflight.py).
- [Fixture inputs](../fixtures/first_wave/engine_room_command_run_singleflight/input/); [historical Engine Room composition result](../receipts/first_wave/engine_room_demo/engine_room_demo_result.json) (summary, not a detailed result for this individual fixture).
- [JSON record](../paper_modules/engine_room_command_run_singleflight.json); canonical metadata: [`core/paper_module_capsules.json`](../core/paper_module_capsules.json).
