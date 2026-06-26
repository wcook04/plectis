# pattern_binding_contract Pattern Binding Contract

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/pattern_binding_contract.json`
- Atlas source of record: `core/organ_atlas.json::organs[0:pattern_binding_contract]`
- Registry source of record: `core/organ_registry.json::implemented_organs[0:pattern_binding_contract]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate that public pattern rows meet the declared binding contract (required fields, no duplicate pattern IDs, resolved reference capsules, no private-body or secret leakage, no public-leaf overclaim) and to read the pass/reject findings and per-row anti-claims from the emitted JSON receipt.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.pattern_binding_contract` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.pattern_binding_contract.validates_public_pattern_bindings` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/pattern_binding_contract.py` (resolved_code_locus)
- `implemented_by` -> `code_locus:src/microcosm_core/macro_tools/pattern_route_readiness.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.architecture_and_navigation_route_contract_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `governed_by` -> `principle:P-12` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `governed_by` -> `principle:P-19` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `wires_to` -> `organ:navigation_hologram_route_plane` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:agent_route_observability_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:cold_reader_route_map` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:macro_projection_import_protocol` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:pattern_assimilation_step` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:voice_to_doctrine_self_improvement_loop` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
