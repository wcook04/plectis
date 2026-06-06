# materials_chemistry_closed_loop_lab_safety_replay Materials Chemistry Closed Loop Lab Safety Replay

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/materials_chemistry_closed_loop_lab_safety_replay.json`
- Atlas source of record: `core/organ_atlas.json::organs[44:materials_chemistry_closed_loop_lab_safety_replay]`
- Registry source of record: `core/organ_registry.json::implemented_organs[44:materials_chemistry_closed_loop_lab_safety_replay]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that a closed-loop materials-lab replay fixture is body-free and simulator-only, and to confirm its safety gates reject wetlab protocols, hazardous synthesis steps, reagent amounts, controlled/bioactive targets, live lab credentials, robot commands, private lab notebooks, and discovery claims.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.materials_chemistry_closed_loop_lab_safety_replay` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.materials_chemistry_closed_loop_lab_safety_replay.validates_public_materials_lab_safety_replay` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/materials_chemistry_closed_loop_lab_safety_replay.py` (resolved_code_locus)
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
- `wires_to` -> `organ:spatial_world_model_counterfactual_simulation_replay` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
