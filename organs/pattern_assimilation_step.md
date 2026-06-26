# pattern_assimilation_step Pattern Assimilation Step

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/pattern_assimilation_step.json`
- Atlas source of record: `core/organ_atlas.json::organs[28:pattern_assimilation_step]`
- Registry source of record: `core/organ_registry.json::implemented_organs[28:pattern_assimilation_step]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that each landed organ in the fixture set has exactly one same-lane closeout decision: either a concrete refinement receipt naming the owner surface and changed artifact, or a typed nothing_to_refine receipt with stewardship checked, next-best-lane checked, and a re-entry condition. It also checks residual lifecycle posture, rejects duplicate refinement receipt ids, rejects local-lesson authority upgrades to global doctrine, and rejects raw-seed bodies in fixtures. It asserts only that the declared closeout contract holds over fixtures, not that any live learning actually occurred.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.pattern_assimilation` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.pattern_assimilation_step.validates_public_pattern_assimilation_step` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/validators/acceptance.py` (resolved_code_locus)
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
