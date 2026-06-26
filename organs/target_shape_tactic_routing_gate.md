# target_shape_tactic_routing_gate Target Shape Tactic Routing Gate

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/target_shape_tactic_routing_gate.json`
- Atlas source of record: `core/organ_atlas.json::organs[7:target_shape_tactic_routing_gate]`
- Registry source of record: `core/organ_registry.json::implemented_organs[7:target_shape_tactic_routing_gate]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to produce an auditable per-tactic decision record (admissible / unavailable / unprobed / shape-inadmissible, each with a reason) over real Ring2 route references, asserting the decision is made before any proof execution. It is a checker/projector of the pre-execution routing decision, not a live prover gate: it reads supplied route refs and emits allow/reject decisions plus authority-ceiling and secret-exclusion receipts; it does not run Lean/Lake or attempt a proof.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.target_shape_tactic_routing` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.target_shape_tactic_routing_gate.validates_public_tactic_routing_boundary` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/target_shape_tactic_routing_gate.py` (resolved_code_locus)
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
- `wires_to` -> `organ:formal_math_verifier_trace_repair_loop` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_evidence_cell_anchor_resolver` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:proof_diagnostic_evidence_spine` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:tactic_portfolio_availability_probe` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
