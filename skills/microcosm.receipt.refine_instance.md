# Microcosm Receipt Refine Instance

Use this public-safe skill projection when an existing Microcosm receipt needs a bounded correction to command or validator refs, result status, evidence refs, omissions, authority ceiling, anti-claims, replay inputs, or public/private boundary. It is not a route for widening a receipt claim beyond the evidence it records.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_receipt",
  "acts_on_kind": "receipt",
  "trigger_summary": [
    "A governed receipt row has stale output refs, missing omission language, unclear source coupling, weak anti-claims, absent replay inputs, or an overbroad authority ceiling.",
    "The refinement can be scoped from the producing command, validator output, fixture ids, source refs, generated health, or related receipt evidence without changing std_microcosm_receipt itself."
  ],
  "workflow_summary": [
    "Inspect the receipt payload, producing command or validator, referenced artifacts, omitted bodies, source boundary, generated health, and downstream claims before mutation.",
    "Change only source-authority receipt fields that narrow the claim ceiling or resolve a named evidence/ref/omission gap from source evidence.",
    "Regenerate through the builder and leave unsupported release, private-equivalence, source-body completeness, or propagation claims as typed residual pressure."
  ],
  "concept_refs": [
    "concept.voice_to_doctrine_self_improvement_loop_bundle"
  ],
  "mechanism_refs": [
    "mechanism.doctrine_fact_claim_audit.validates_public_doctrine_fact_claim_audit"
  ],
  "mapping_basis": "This markdown maps receipt instance refinement to std_microcosm_receipt, the receipt doctrine kind, and doctrine fact-claim audit because receipt corrections must tighten evidence and authority ceilings instead of laundering existing receipt presence into broad support."
}
```

## Authority Boundary

This skill source governs bounded receipt-instance correction only. It does not authorize release, private-data equivalence, source-body exposure, runtime correctness outside the recorded command, or broad doctrine wiring without source evidence.

Anti-claims:

- Receipt presence is not proof that every referenced artifact is complete or safe.
- Endpoint, negative-case, or projection coverage is not propagation proof.
- Generated health can expose receipt gaps, but source evidence, command output, validator output, or typed residual pressure must settle them.
