# formal_math_readiness_gate Formal Math Readiness Gate

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/formal_math_readiness_gate.json`
- Atlas source of record: `core/organ_atlas.json::organs[3:formal_math_readiness_gate]`
- Registry source of record: `core/organ_registry.json::implemented_organs[3:formal_math_readiness_gate]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to get a machine-readable readiness board listing available vs. blocked tactics, allowed lemma-lookup rows, and admissible target-shape routes before deciding what a downstream prover step may safely attempt. The board is derived from declared metadata only, so treat it as a permission/boundary surface, not as evidence the environment actually works.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.formal_math_readiness_gate` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.formal_math_readiness_gate.validates_public_readiness_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/formal_math_readiness_gate.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `wires_to` -> `organ:formal_math_lean_proof_witness` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:macro_projection_import_protocol` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:batch4_proof_authority_runtime` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:provider_context_recipe_budget_policy` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tactic_portfolio_availability_probe` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:target_shape_tactic_routing_gate` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
