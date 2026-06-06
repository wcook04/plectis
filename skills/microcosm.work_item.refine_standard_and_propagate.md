# Microcosm Work Item Refine Standard And Propagate

Use this public-safe skill projection only when std_microcosm_work_item itself must change and the change must propagate through work-item instances, Task Ledger links, Work Ledger coordination, receipts, validators, generated views, and doctrine-lattice projections.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_standard_and_propagate",
  "operates_standard": "std_microcosm_work_item",
  "acts_on_kind": "work_item",
  "trigger_summary": [
    "A reusable invariant about work-item state, dependencies, source refs, acceptance, re-entry, receipts, public/private boundary, or closure semantics belongs in std_microcosm_work_item.",
    "Changing the work-item standard alters governed work-item records, Task Ledger/Work Ledger linkage, receipt requirements, validator behavior, generated views, or doctrine-lattice claim ceilings."
  ],
  "workflow_summary": [
    "Prove the invariant from work-item records, Task Ledger authority, Work Ledger coordination, receipts, validators, generated health, and relation registry before editing the standard.",
    "Update builder and validator logic so state transitions, dependency semantics, receipt requirements, source refs, and authority ceilings are computed or explicitly bounded.",
    "Regenerate the lattice and leave unsupported completion, validation, release, private-equivalence, projection-freshness, or whole-artifact claims as residual pressure until source evidence resolves them."
  ],
  "concept_refs": [
    "concept.standards_meta_diagnostics_bundle"
  ],
  "mechanism_refs": [
    "mechanism.pattern_binding_contract.validates_public_pattern_bindings"
  ],
  "mapping_basis": "This markdown maps work-item standard propagation to std_microcosm_work_item, the work_item doctrine kind, and pattern binding because work-item standard changes must propagate through state, dependency, receipt, validator, and projection surfaces before they govern downstream closure claims."
}
```

## Authority Boundary

This skill source governs work-item standard propagation only. It does not make JSON parity, resolved triad edges, generated queue visibility, or status labels into proof that every work item is executed, validated, public-safe, or release-ready.

Anti-claims:

- Do not weaken std_microcosm_work_item to make health greener.
- Do not convert status labels, generated queues, or capture presence into execution or release proof.
- Do not close work-item propagation without source-authority mutation, builder parity, validator checks, and scoped receipt binding.
