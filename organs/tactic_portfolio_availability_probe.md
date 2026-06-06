# tactic_portfolio_availability_probe Tactic Portfolio Availability Probe

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/tactic_portfolio_availability_probe.json`
- Atlas source of record: `core/organ_atlas.json::organs[6:tactic_portfolio_availability_probe]`
- Registry source of record: `core/organ_registry.json::implemented_organs[6:tactic_portfolio_availability_probe]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent reads it to get an environment-scoped map of which tactics were recorded as compiling, and relies on its checks: every tactic must carry a compile status, no Mathlib-dependent tactic may be marked available unless the Mathlib import probe passed, and any tactic a consumer references must exist in the probed portfolio.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.tactic_portfolio_availability` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.tactic_portfolio_availability_probe.validates_public_tactic_availability_projection` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/tactic_portfolio_availability_probe.py` (resolved_code_locus)
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
- `wires_to` -> `organ:corpus_readiness_mathlib_absence_gate` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_math_verifier_trace_repair_loop` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:target_shape_tactic_routing_gate` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:undeclared_library_prior_symbol_classifier` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
