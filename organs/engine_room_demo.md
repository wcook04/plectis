# engine_room_demo Engine Room Demo

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/engine_room_demo.json`
- Atlas source of record: `core/organ_atlas.json::organs[65:engine_room_demo]`
- Registry source of record: `core/organ_registry.json::implemented_organs[65:engine_room_demo]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate the staged Engine Room composition: all 14 targets must be covered, every capsule surface must exist, the executable capsule chain must pass, and the planted missing-target case must be observed.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.engine_room_demo` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.engine_room_demo.validates_public_engine_room_demo` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/engine_room_demo.py` (resolved_code_locus)
- `implemented_by` -> `code_locus:src/microcosm_core/engine_room/demo.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.import_projection_and_drift_control_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `governed_by` -> `principle:P-12` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `wires_to` -> `organ:batch8_compliance_pipeline_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_validator_checker_capsule` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
