# spatial_world_model_counterfactual_simulation_replay Spatial World Model Counterfactual Simulation Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/spatial_world_model_counterfactual_simulation_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[24:spatial_world_model_counterfactual_simulation_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[24:spatial_world_model_counterfactual_simulation_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate that the synthetic counterfactual-replay rows are well-formed (each cites scene-state, action-trace, predicted-state, transition-diff, oracle-check, and public sensor-packet refs plus limitation labels) and that every forbidden claim (private video export, raw sensor export, live robot/AV operation, real-world geographic accuracy, simulator-product claim, generated-video-only authority, benchmark scores, release) is rejected by a negative-case receipt.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.spatial_world_model_counterfactual_simulation_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.spatial_world_model_counterfactual_simulation_replay.validates_public_spatial_world_model_counterfactual_simulation_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/spatial_world_model_counterfactual_simulation_replay.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.research_and_science_replay_evidence_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
