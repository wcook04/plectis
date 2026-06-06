# Microcosm Validator Refine Standard And Propagate

Use this public-safe skill projection only when std_microcosm_validator itself must change and the change must propagate through validator instances, checked standards, receipts, generated projections, and health checks.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_standard_and_propagate",
  "operates_standard": "std_microcosm_validator",
  "acts_on_kind": "validator",
  "trigger_summary": [
    "A reusable validator invariant belongs in std_microcosm_validator rather than one validator row.",
    "Changing the validator standard alters required input contracts, command/callable semantics, negative-case floors, receipt requirements, omission boundaries, or authority ceilings across validator artifacts."
  ],
  "workflow_summary": [
    "Prove the invariant from live validator routes, governed standards, fixture evidence, receipts, generated health, and relation registry before editing the validator standard.",
    "Update builder and validator logic so checked inputs, receipts, negative cases, anti-claims, and claim ceilings are computed or explicitly bounded rather than asserted.",
    "Regenerate the lattice and keep unsupported propagation, release, runtime, or whole-artifact completeness claims as residual pressure until source evidence resolves them."
  ],
  "concept_refs": [
    "concept.standards_meta_diagnostics_bundle"
  ],
  "mechanism_refs": [
    "mechanism.standards_meta_diagnostics.validates_public_standards_meta_diagnostics"
  ],
  "mapping_basis": "This markdown maps validator standard propagation to std_microcosm_validator, the validator doctrine kind, and standards-meta diagnostics because validator-standard changes must be checked across generated corpora before they govern downstream proof claims."
}
```

## Authority Boundary

This skill source governs validator-standard propagation only. It does not make validator JSON parity, resolved triad edges, graph reachability, or pass status into proof that every validator is complete, runtime-safe, release-ready, or propagated through all downstream artifacts.

Anti-claims:

- Do not weaken std_microcosm_validator to make health greener.
- Do not convert generated projection availability or validator pass status into release, runtime, source-body, or propagation support.
- Do not close validator propagation without builder parity, validator checks, and scoped receipt binding.
