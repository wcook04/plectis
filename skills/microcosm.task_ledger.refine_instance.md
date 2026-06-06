# Microcosm Task Ledger Refine Instance

Use this public-safe skill projection when an existing Microcosm task-ledger record needs a bounded correction to state, subject id, dependency, acceptance, re-entry, evidence refs, receipt refs, projection visibility, or authority boundary. It is not a route for hiding an unresolved residual by changing status language.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_task_ledger",
  "acts_on_kind": "task_ledger",
  "trigger_summary": [
    "A governed task-ledger record has stale state, missing acceptance, unclear dependency, weak source refs, stale projection visibility, or a closeout claim that outruns evidence.",
    "The refinement can be scoped from authority events, generated views, execution receipts, Work Ledger coordination, source evidence, or validator output without changing std_microcosm_task_ledger itself."
  ],
  "workflow_summary": [
    "Inspect the authority event, generated view state, related Work Ledger session, receipt refs, dependencies, acceptance text, and downstream claims before mutation.",
    "Change only event-sourced or source-authority fields that clarify state, narrow claim ceiling, resolve a dependency, or bind a re-entry condition from evidence.",
    "Regenerate through the builder and leave unsupported completion, release, private-equivalence, or projection-visibility claims as typed residual pressure."
  ],
  "concept_refs": [
    "concept.voice_to_doctrine_self_improvement_loop_bundle"
  ],
  "mechanism_refs": [
    "mechanism.doctrine_fact_claim_audit.validates_public_doctrine_fact_claim_audit"
  ],
  "mapping_basis": "This markdown maps task-ledger instance refinement to std_microcosm_task_ledger, the task_ledger doctrine kind, and doctrine fact-claim audit because status corrections must stay tied to authority events and evidence instead of laundering residuals into green views."
}
```

## Authority Boundary

This skill source governs bounded task-ledger instance correction only. It does not authorize release, erase dependencies, expose private ledger content, or prove completion outside the event, receipt, and projection state it repairs.

Anti-claims:

- Changing a generated task view is not a task-ledger authority mutation.
- Closing a task-ledger record is not proof that downstream work, validation, or release gates are complete.
- Projection visibility can expose or confirm state, but authority events and receipts must settle the status.
