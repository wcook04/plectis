# Microcosm Verifier Lab Execution Spine Refine Instance

Use this public-safe skill when `std_microcosm_verifier_lab_execution_spine` declares the `refine_instance` triad route for `verifier_lab_execution_spine`. It is a governed route source for the declared skill id. It does not upgrade the standard from `public_microcosm_standard_v1` / `draft`, prove runtime correctness, authorize release, publication, provider calls, private-body export, source mutation, or whole-system correctness.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_verifier_lab_execution_spine",
  "acts_on_kind": "verifier_lab_execution_spine",
  "trigger_summary": [
    "The Verifier lab execution spine standard declares this refine instance skill id with status planned.",
    "A governed skill source row is needed before standard.owns_triad.skill can resolve without treating generated projections as authority."
  ],
  "workflow_summary": [
    "Read std_microcosm_verifier_lab_execution_spine JSON, its authority ceiling, validator refs, receipt refs, and lattice health before editing verifier_lab_execution_spine artifacts.",
    "Tighten an existing instance without widening its authority ceiling, weakening validator expectations, or treating receipt presence as proof of runtime correctness.",
    "Regenerate the skill corpus and preserve missing mechanism or concept neighbours as residual pressure unless a source mapping names them."
  ],
  "concept_refs": [
    "concept.formal_math_and_proof_witness_bundle"
  ],
  "mechanism_refs": [
    "mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness"
  ],
  "mapping_basis": "The standard JSON at standards/std_microcosm_verifier_lab_execution_spine.json declares this refine_instance skill route for verifier_lab_execution_spine, and core/organ_atlas.json::verifier_lab_execution_spine names mechanism_refs=mechanism.verifier_lab_execution_spine.validates_public_verifier_transition_witness and concept_refs=concept.formal_math_and_proof_witness_bundle. This source mapping binds the skill to those accepted organ neighbours without inferring from prose, generated projections, endpoint coverage, or release claims."
}
```

## Authority Boundary

This skill binds a declared triad route to a governed skill source row. It does not make the standard active, complete, or accepted beyond the standard source status, and it does not infer concept or mechanism neighbours not named in this skill mapping.

Anti-claims:

- A resolved triad skill edge is route coverage, not runtime proof.
- Planned standard skill ids remain bounded by the standard authority ceiling and validation receipts.
- Generated lattice projections are not source evidence for release, capability, or correctness claims.
