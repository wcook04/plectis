# Engine Room Public Projection Leak Gate

Public exercise:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.public_projection_leak_gate evaluate-fixtures --input fixtures/first_wave/engine_room_public_projection_leak_gate/input --json
```

This capsule is a source-faithful public refactor of the macro public
projection leakage scan and portability gitleaks witness. It demonstrates
private-path detection, credential-shape detection, policy-exception handling,
symlink escape blocking, and hash-only match receipts. It does not authorize
release and it is not a general security scanner.
