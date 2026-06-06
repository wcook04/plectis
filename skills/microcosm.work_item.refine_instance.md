# Microcosm Work Item Refine Instance

Use this public-safe skill projection when an existing Microcosm work item needs a bounded correction to subject, state, dependency, evidence refs, acceptance condition, re-entry condition, receipt refs, or authority boundary. It is not a route for hiding unfinished work by rewriting status language.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_work_item",
  "acts_on_kind": "work_item",
  "trigger_summary": [
    "A governed work item has stale state, ambiguous subject, weak dependency semantics, missing acceptance, missing receipt refs, stale re-entry, or a claim ceiling that outruns evidence.",
    "The correction can be scoped from source refs, Work Ledger claims, Task Ledger authority, execution receipts, generated views, validator output, or doctrine lattice health without changing std_microcosm_work_item itself."
  ],
  "workflow_summary": [
    "Inspect the work-item source refs, related Task Ledger record, Work Ledger session, receipts, dependency graph, generated views, and downstream claims before mutation.",
    "Change only fields that clarify state, evidence, dependency, acceptance, re-entry, receipt linkage, or authority boundary from source evidence.",
    "Regenerate through the builder and keep unsupported completion, validation, release, private-equivalence, or projection-freshness claims as typed residual pressure."
  ],
  "concept_refs": [
    "concept.voice_to_doctrine_self_improvement_loop_bundle"
  ],
  "mechanism_refs": [
    "mechanism.durable_agent_work_landing_replay.validates_public_work_landing_replay_contract"
  ],
  "mapping_basis": "This markdown maps work-item instance refinement to std_microcosm_work_item, the work_item doctrine kind, and durable work-landing replay because state and closure corrections must be receipt- and evidence-bound rather than status-label laundering."
}
```

## Authority Boundary

This skill source governs bounded work-item instance correction only. It does not authorize release, erase dependencies, expose private task content, or prove execution outside the evidence and receipt state it repairs.

Anti-claims:

- Rewording a status label is not evidence that the work item is closed.
- Generated queues and views can expose stale state, but source refs and receipts must settle authority.
- Work-item refinement must not collapse dependencies, blockers, or re-entry conditions into a green projection.
