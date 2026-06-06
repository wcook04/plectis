# mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity validates synthetic bridge continuity

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[2:mechanism.bridge_phase_continuity_runtime.validates_synthetic_bridge_continuity]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The bridge phase continuity runtime validates public synthetic observe/apply bridge continuity by checking disk-first continuation packets, heartbeat liveness boundaries, resource-pressure dispatch blocks, resume-once semantics, duplicate-resume rejection, worker-skip dedupe, copied observe-runtime source-module digests, tracked receipt-write gating, private-state scans, and authority ceilings before writing bounded body-free receipts.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/organs/bridge_phase_continuity_runtime.py` (resolved_code_locus)
- `runs_in` -> `organ:bridge_phase_continuity_runtime` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.work_landing_and_continuity_control_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.concurrency_mission_control.validates_public_concurrency_mission_control` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.workstream_driver_recency_coalescer.validates_public_workstream_driver_recency_coalescer` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
