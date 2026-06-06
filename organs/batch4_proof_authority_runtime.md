# batch4_proof_authority_runtime Proof / Control / Runtime Import Capsule

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/batch4_proof_authority_runtime.json`
- Atlas source of record: `core/organ_atlas.json::organs[54:batch4_proof_authority_runtime]`
- Registry source of record: `core/organ_registry.json::implemented_organs[54:batch4_proof_authority_runtime]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs it to validate the Batch-4 source-open capsule: all 14 proof, authority, and runtime mechanisms must be present, the copied source-module manifest must preserve public anchors, and planted overclaim/leakage/lease/runtime-negative cases must reject with typed findings.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.batch4_proof_authority_runtime` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.batch4_proof_authority_runtime.validates_public_proof_authority_runtime_capsule` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/batch4_proof_authority_runtime.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-2` (resolved_json_instance)
- `governed_by` -> `principle:P-5` (resolved_json_instance)
- `governed_by` -> `principle:P-9` (resolved_json_instance)
- `governed_by` -> `principle:P-15` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-4` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-8` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-10` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-11` (resolved_json_instance)
- `organ.wires_to.organ` -> residual pressure (Organ atlas row does not name sibling wires_to targets.)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
