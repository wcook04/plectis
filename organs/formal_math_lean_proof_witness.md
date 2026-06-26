# formal_math_lean_proof_witness Formal Math Lean Proof Witness

_Generated from the governed organ JSON instance. Do not edit this markdown by hand._

- Source JSON: `organs/formal_math_lean_proof_witness.json`
- Atlas source of record: `core/organ_atlas.json::organs[16:formal_math_lean_proof_witness]`
- Registry source of record: `core/organ_registry.json::implemented_organs[16:formal_math_lean_proof_witness]`
- Authority boundary: JSON parity seed; organ atlas/registry source authority has not flipped.

## Role

An agent runs this to get a redacted receipt confirming that a small public Lean fixture compiles under the locally installed Lean/Lake toolchain, and that the guardrails fire on the negative cases: Mathlib/Aesop/Batteries imports are rejected, private source refs and embedded proof bodies in manifests are refused, and an intentionally invalid Lean proof is rejected. The receipt carries tool-availability status, Lake build status, source hashes, declaration names, line counts, and negative-case coverage only; it never exports proof bodies, stdout/stderr text, or provider payloads.

## Lattice Neighbours

- `explained_by` -> `paper_module:paper_module.formal_math_lean_proof_witness` (resolved_paper_module_ref)
- `operates_through` -> `mechanism:mechanism.formal_math_lean_proof_witness.validates_public_lean_witness` (resolved_json_instance)
- `implemented_by` -> `code_locus:src/microcosm_core/organs/formal_math_lean_proof_witness.py` (resolved_code_locus)
- `instantiates` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `governed_by` -> `principle:P-3` (resolved_json_instance)
- `constrained_by` -> `axiom:AX-2` (resolved_json_instance)
- `wires_to` -> `organ:formal_math_premise_retrieval` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:formal_math_readiness_gate` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:proof_diagnostic_evidence_spine` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_kernel` (resolved_registry_or_atlas_target)
- `wires_to` -> `organ:verifier_lab_execution_spine` (resolved_registry_or_atlas_target)

## Anti-Claims

- This organ JSON seed does not flip source authority away from core/organ_atlas.json and core/organ_registry.json.
- Required paper/mechanism/code links prove declared structural references only, not runtime correctness or release readiness.
- Selective concept, principle, axiom, and sibling-organ edges are not inferred from prose, specialty, family, or evidence class.
- Absent selective organ edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
