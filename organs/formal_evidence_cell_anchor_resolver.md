# formal_evidence_cell_anchor_resolver Formal Evidence Cell Anchor Resolver

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/formal_evidence_cell_anchor_resolver.json`
- Atlas source of record: `core/organ_atlas.json::organs[11:formal_evidence_cell_anchor_resolver]`
- Registry source of record: `core/organ_registry.json::implemented_organs[11:formal_evidence_cell_anchor_resolver]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to validate that every formal-math claim resolves to a known evidence cell with public source-anchor refs and a permitted claim strength, that the copied macro source-module bodies match their recorded digests, and that the authority ceiling stays at metadata-only (no theorem correctness, Lean/Lake, providers, or release). The cited run-anchor-bundle command validates the clean exported bundle; running the organ's fixture mode (the `run` subcommand) instead is what exercises and confirms all seven leakage/overclaim refusal cases.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.formal_evidence_cell_anchor_resolver` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.formal_evidence_cell_anchor_resolver.validates_public_evidence_cell_anchors` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/formal_evidence_cell_anchor_resolver.py` (resolved_code_locus)
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
- `wires_to` -> `organ:proof_diagnostic_evidence_spine` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:target_shape_tactic_routing_gate` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
