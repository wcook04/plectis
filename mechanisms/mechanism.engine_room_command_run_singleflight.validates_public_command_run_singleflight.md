# mechanism.engine_room_command_run_singleflight.validates_public_command_run_singleflight validates public command run singleflight

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.engine_room_command_run_singleflight.validates_public_command_run_singleflight.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[77:mechanism.engine_room_command_run_singleflight.validates_public_command_run_singleflight]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The Engine Room command-run singleflight mechanism validates content-addressed subprocess run keys, fcntl-backed leader/follower collapse, completed-run reuse, scoped dirty/content fingerprint invalidation, captured stdout/stderr replay, and empty-command refusal over public fixtures without claiming scheduler, daemon, live command_runs export, distributed-lock, release, or private-root authority.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/engine_room/command_run_singleflight.py` (resolved_code_locus)
- `runs_in` -> `organ:engine_room_demo` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.import_projection_and_drift_control_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.engine_room_demo.validates_public_engine_room_demo` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
