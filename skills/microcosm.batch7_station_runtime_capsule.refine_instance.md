# Microcosm Batch7 Station Runtime Capsule Refine Instance

Use this public-safe skill when a Batch 7 station runtime instance needs scoped repair from newer station witness, exercise, negative-case, receipt, or authority-boundary evidence.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_batch7_station_runtime_capsule",
  "acts_on_kind": "batch7_station_runtime_capsule",
  "trigger_summary": [
    "A Batch 7 station runtime instance exists, but source witness, exercise, negative-case, receipt, or authority-boundary fields need repair.",
    "The repair can be made from public copied source evidence, deterministic exercise output, body-free receipts, and authority-boundary deltas."
  ],
  "workflow_summary": [
    "Diff the current instance against the standard, paper-module capsule, runtime source locus, source-module evidence, receipts, and generated health.",
    "Repair only source-backed station witness, exercise, negative-case, receipt, omission, authority-boundary, and anti-claim fields.",
    "Regenerate the skill corpus and lattice projection without promoting station runtime exercises into hosted UI proof or release proof."
  ],
  "concept_refs": [
    "concept.executable_doctrine_grammar_standard_bundle"
  ],
  "mechanism_refs": [
    "mechanism.batch7_station_runtime_capsule.validates_public_station_runtime_capsule"
  ],
  "mapping_basis": "The standard declares this exact refine-instance skill id, and the resolved mechanism supplies the public validation surface for Batch 7 station runtime instance repair."
}
```

## Authority Boundary

This skill governs public Batch 7 station runtime instance repair only. It does not certify hosted UI readiness, browser/operator access, private-root equivalence, publication readiness, release readiness, or whole-system correctness.

Anti-claims:

- Instance repair is not hosted UI proof.
- Negative cases are bounded evidence, not exhaustive frontend falsification.
- Generated projections are not release evidence.
