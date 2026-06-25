# proof_diagnostic_evidence_spine Proof Diagnostic Evidence Spine

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/proof_diagnostic_evidence_spine.json`
- Atlas source of record: `core/organ_atlas.json::organs[2:proof_diagnostic_evidence_spine]`
- Registry source of record: `core/organ_registry.json::implemented_organs[2:proof_diagnostic_evidence_spine]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to turn upstream Ring2 proof-pipeline receipt references (failure-taxonomy, graph-update, verifier-trace repair, evidence-cell anchor) into accepted/rejected diagnostic receipts, and to confirm forbidden cases (provider proof bodies, source-authority upgrades, stale receipt coupling, runtime-correctness overclaims) are rejected as regression guards before any downstream proof-witness step. It emits a diagnostic board, proof receipts, a provider-payload policy result, and a proof-evidence validation receipt over receipt refs only.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.proof_diagnostic_evidence_spine` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.proof_diagnostic_evidence_spine.validates_ring2_diagnostic_evidence_membrane` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/proof_diagnostic_evidence_spine.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-1` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `governed_by` -> `principle:P-6` (resolved_json_instance)
- `governed_by` -> `principle:P-8` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `governed_by` -> `principle:P-19` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-1` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-5` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-7` (resolved_json_instance)
- `wires_to` -> `organ:formal_math_verifier_trace_repair_loop` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_evidence_cell_anchor_resolver` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_math_lean_proof_witness` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:ring2_premise_retrieval_precision_recall_harness` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:target_shape_tactic_routing_gate` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
