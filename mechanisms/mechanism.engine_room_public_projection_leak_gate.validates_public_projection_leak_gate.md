# mechanism.engine_room_public_projection_leak_gate.validates_public_projection_leak_gate validates public projection leak gate

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.engine_room_public_projection_leak_gate.validates_public_projection_leak_gate.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[85:mechanism.engine_room_public_projection_leak_gate.validates_public_projection_leak_gate]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The Engine Room public projection leak gate validates rendered public projection roots by scanning file content, path names, symlink targets, policy exceptions, and optional gitleaks output for credential-shaped or private-root leakage, returning bounded hash-only receipts without copying sensitive payloads or granting release authority.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/engine_room/public_projection_leak_gate.py` (resolved_code_locus)
- `runs_in` -> `organ:engine_room_demo` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.import_projection_and_drift_control_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.engine_room_demo.validates_public_engine_room_demo` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.engine_room_egress_self_compliance_gate.validates_public_egress_self_compliance_gate` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
