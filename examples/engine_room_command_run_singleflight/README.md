# Engine Room Command-Run Singleflight

Public exercise:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.command_run_singleflight evaluate-fixtures --input fixtures/first_wave/engine_room_command_run_singleflight/input --json
```

This capsule is a source-faithful public refactor of `system/lib/command_run_singleflight.py`.
It demonstrates command-key fingerprinting, fcntl leader/follower collapse,
completed-run reuse, and output replay on synthetic fixture commands. It does
not copy or expose live `state/command_runs/` data.
