# Microcosm Mechanism Refine Standard And Propagate

Use this public-safe skill projection only when std_microcosm_mechanism itself must change and that change must propagate through mechanism instances, validators, projections, and health checks.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_standard_and_propagate",
  "operates_standard": "std_microcosm_mechanism",
  "acts_on_kind": "mechanism",
  "trigger_summary": [
    "A reusable mechanism invariant belongs in std_microcosm_mechanism rather than one mechanism row.",
    "Changing the mechanism standard alters source-row, edge, receipt, support, or projection validation behavior."
  ],
  "workflow_summary": [
    "Prove the invariant from live mechanism evidence before editing the standard.",
    "Update validators and builder logic so support, witness gaps, and authority boundaries are computed.",
    "Regenerate the lattice and leave every unsupported mechanism claim as typed residual pressure."
  ],
  "concept_refs": [
    "concept.standards_meta_diagnostics_bundle"
  ],
  "mechanism_refs": [
    "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics"
  ],
  "mapping_basis": "This markdown maps mechanism standard propagation to std_microcosm_mechanism, the mechanism doctrine kind, and standards-meta diagnostics because standard changes must be reflected in validators and generated health before they govern mechanism nodes."
}
```

## Authority Boundary

This skill source governs standard propagation for mechanisms only. It does not make mechanism parity, graph count, or validator existence into evidence that a mechanism is complete.

Anti-claims:

- Do not weaken the mechanism standard to make health greener.
- Do not read generated graph edges back into source support.
- Do not close a propagation lane without builder parity, validator checks, and scoped receipt binding.
