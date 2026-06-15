# mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness validates public verifier transition witness

_Generated from the governed mechanism JSON instance. Do not edit this markdown by hand._

- Source JSON: `mechanisms/mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness.json`
- Registry source of record: `core/mechanism_sources.json::mechanisms[37:mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness]`
- Authority boundary: JSON parity seed; mechanism registry source authority has not flipped.

## Statement

The verifier lab execution spine validates bounded public Lean transition rows by running the local checker on a temporary fixture, preserving accept/reject and residual-retry buckets, safety counters, source-module manifests, and redacted body-free receipts.

## Lattice Neighbours

- `grounded_in` -> `code_locus:src/microcosm_core/organs/verifier_lab_execution_spine.py` (resolved_code_locus)
- `runs_in` -> `organ:verifier_lab_execution_spine` (resolved_registry_or_atlas_target)
- `grounds` -> `concept:concept.formal_math_and_proof_witness_bundle` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.certificate_kernel_execution_lab.validates_public_certificate_kernel_execution` (resolved_json_instance)
- `upstream_of` -> `mechanism:mechanism.engine_room_lean_proof_search_lab.validates_public_lean_proof_search_lab` (resolved_json_instance)

## Anti-Claims

- This mechanism JSON seed does not flip source authority away from core/mechanism_sources.json.
- Resolved code-locus paths prove filesystem grounding only, not runtime correctness or release readiness.
- Absent concept or sibling mechanism edges are residual pressure, not evidence that no neighbours exist.
- Generated markdown, graph, health, and atlas projections cannot be read back as source evidence.
