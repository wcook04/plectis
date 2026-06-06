# Microcosm Task Ledger Refine Standard And Propagate

Use this public-safe skill projection only when std_microcosm_task_ledger itself must change and the change must propagate through task-ledger records, generated views, Work Ledger coordination, receipts, validators, and doctrine-lattice projections.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_standard_and_propagate",
  "operates_standard": "std_microcosm_task_ledger",
  "acts_on_kind": "task_ledger",
  "trigger_summary": [
    "A reusable task-ledger invariant belongs in std_microcosm_task_ledger rather than one record or view.",
    "Changing the task-ledger standard alters event fields, state transitions, dependency semantics, receipt requirements, projection visibility, capture-before-prose rules, or public/private boundaries across task-ledger artifacts."
  ],
  "workflow_summary": [
    "Prove the invariant from authority events, generated views, Work Ledger coordination, receipts, validators, generated health, and relation registry before editing the task-ledger standard.",
    "Update builder and validator logic so state transitions, dependencies, receipts, source refs, projection visibility, and claim ceilings are computed or explicitly bounded rather than asserted.",
    "Regenerate the lattice and keep unsupported completion, release, private-equivalence, projection-freshness, or whole-artifact claims as residual pressure until source evidence resolves them."
  ],
  "concept_refs": [
    "concept.standards_meta_diagnostics_bundle"
  ],
  "mechanism_refs": [
    "mechanism.pattern_binding_contract.validates_public_pattern_bindings"
  ],
  "mapping_basis": "This markdown maps task-ledger standard propagation to std_microcosm_task_ledger, the task_ledger doctrine kind, and pattern binding because task-ledger standard changes must propagate through event authority, generated views, and receipt-backed status surfaces before they govern downstream claims."
}
```

## Authority Boundary

This skill source governs task-ledger standard propagation only. It does not make task-ledger JSON parity, resolved triad edges, generated view availability, or capture presence into proof that every work item is complete, validated, public-safe, or release-ready.

Anti-claims:

- Do not weaken std_microcosm_task_ledger to make health greener.
- Do not convert generated task views, capture presence, or status labels into execution or release proof.
- Do not close task-ledger propagation without authority events, builder parity, validator checks, and scoped receipt binding.
