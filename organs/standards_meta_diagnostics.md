# standards_meta_diagnostics Standards Meta Diagnostics

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/standards_meta_diagnostics.json`
- Atlas source of record: `core/organ_atlas.json::organs[32:standards_meta_diagnostics]`
- Registry source of record: `core/organ_registry.json::implemented_organs[32:standards_meta_diagnostics]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to confirm that every accepted organ in the public inventory maps to a standard, a runtime contract (CLI command plus runtime step), and at least one receipt ref, and that the diagnostic policy and inputs carry no release/provider overclaim and no private-source or provider-payload body.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.standards_meta_diagnostics` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/standards_meta_diagnostics.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.architecture_and_navigation_route_contract_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-12` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `governed_by` -> `principle:P-17` (resolved_json_instance)
- `governed_by` -> `principle:P-18` (resolved_json_instance)
- `governed_by` -> `principle:P-19` (resolved_json_instance)
- `governed_by` -> `principle:P-20` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
