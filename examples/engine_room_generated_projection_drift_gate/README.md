# Engine Room Generated Projection Drift Gate

Public exercise:

```bash
PYTHONPATH=src python3 -m microcosm_core.engine_room.generated_projection_drift_gate evaluate-fixtures --input fixtures/first_wave/engine_room_generated_projection_drift_gate/input --json
```

This capsule is a source-faithful public refactor of
`tools/meta/control/projection_drift.py` and
`system/lib/generated_projection_registry.py`. It demonstrates owner-scoped
selection from changed paths, source and artifact fingerprints, clean-receipt
cache hits, no-write check command return codes, missing-artifact rejection,
and a planted-byte drift case.

It does not claim that every macro projection owner has content-diff semantics,
does not repair generated files, and does not authorize release.
