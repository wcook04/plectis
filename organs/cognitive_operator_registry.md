# cognitive_operator_registry Cognitive Operator Registry

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/cognitive_operator_registry.json`
- Atlas source of record: `core/organ_atlas.json::organs[47:cognitive_operator_registry]`
- Registry source of record: `core/organ_registry.json::implemented_organs[47:cognitive_operator_registry]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to confirm every operator row in the public cognitive-operator registry carries the required operator-shape fields (activation, process, integration, validation, evidence, dogfood receipts), that each active operator has a dogfood receipt with cognition_delta_evidence, that near-duplicate operators carry an accretion decision (anti-sprawl), and that no row claims operator-voice authority, leaks a private body, or sets a release/provider/mutation overclaim.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.cognitive_operator_registry` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.cognitive_operator_registry.validates_public_operator_contract` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/cognitive_operator_registry.py` (resolved_code_locus)
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
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
