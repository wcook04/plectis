# world_model_projection_drift_control_room World Model Projection Drift Control Room

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/world_model_projection_drift_control_room.json`
- Atlas source of record: `core/organ_atlas.json::organs[23:world_model_projection_drift_control_room]`
- Registry source of record: `core/organ_registry.json::implemented_organs[23:world_model_projection_drift_control_room]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that a set of body-free drift rows each cite a source ref, repair route, validation ref, and target ref while keeping the forbidden booleans (source-authority, live-repair, source-mutation, doctrine-promotion, provider-export, private-export, release) false, and that the secret-exclusion scan passes with no body text emitted. The organ's fixture mode additionally asserts that the eight expected negative cases (missing source ref, missing validation ref, source-authority claim, live-repair authorization, private-runtime export, provider-payload export, automatic doctrine promotion, release claim) are rejected; the validation receipt records 8/8.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.world_model_projection_drift_control_room` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.world_model_projection_drift_control_room.validates_public_projection_drift_control_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/world_model_projection_drift_control_room.py` (resolved_code_locus)
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
- `wires_to` -> `organ:materials_chemistry_closed_loop_lab_safety_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:mechanistic_interpretability_circuit_attribution_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:prediction_oracle_reconciliation` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:spatial_world_model_counterfactual_simulation_replay` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tool_server_pressure_inventory` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch12_market_dashboard_read_model_capsule` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_station_surface_atlas_layout_port` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch8_structural_theses_capsule` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
