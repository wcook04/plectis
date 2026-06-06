# batch7_station_runtime_capsule Station Runtime Evidence Capsule

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/batch7_station_runtime_capsule.json`
- Atlas source of record: `core/organ_atlas.json::organs[76:batch7_station_runtime_capsule]`
- Registry source of record: `core/organ_registry.json::implemented_organs[76:batch7_station_runtime_capsule]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate the Batch 7 station runtime capsule: exact copied station host, live instrument, store, and source-test bodies must preserve digests and anchors, frontend witness metadata must stay bounded, all five negative cases must be observed, and receipts must omit copied body text, private refs, browser/HUD state, provider payloads, source mutation, release authority, and live UI correctness overclaims.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.batch7_station_runtime_capsule` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.batch7_station_runtime_capsule.validates_public_station_runtime_capsule` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/batch7_station_runtime_capsule.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.agent_reliability_and_safety_validator_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `wires_to` -> `organ:batch8_station_surface_atlas_layout_port` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
