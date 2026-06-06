# Microcosm Work Ledger Refine Instance

Use this public-safe skill projection when an existing Microcosm Work Ledger record needs a bounded correction to session id, actor, claim scope, lease, heartbeat, read receipt, append evidence, collision state, append-exempt closeout, or authority boundary. It is not a route for silently changing claim ownership or releasing another session's claim.

## Typed Skill Mapping

```json
{
  "triad_role": "refine_instance",
  "operates_standard": "std_microcosm_work_ledger",
  "acts_on_kind": "work_ledger",
  "trigger_summary": [
    "A governed Work Ledger record has stale claim state, ambiguous scope, wrong session binding, weak heartbeat evidence, missing read receipt, missing append-exempt reason, or a collision/closeout claim that outruns evidence.",
    "The correction can be scoped from Work Ledger runtime state, mission-transaction preflight, Task Ledger receipts, exact-copy import receipts, generated coordination views, or validator output without changing std_microcosm_work_ledger itself."
  ],
  "workflow_summary": [
    "Inspect the source Work Ledger row, runtime status, read receipt, related Task Ledger record, mission-transaction preflight, scoped commit evidence, generated views, and active claims before mutation.",
    "Change only fields that clarify scope, lease, heartbeat, collision, append evidence, closeout state, or authority ceiling from source evidence.",
    "Regenerate through the builder and keep unsupported live mutation, claim-release, Git, provider, release, private-equivalence, or projection-freshness claims as typed residual pressure."
  ],
  "concept_refs": [
    "concept.voice_to_doctrine_self_improvement_loop_bundle"
  ],
  "mechanism_refs": [
    "mechanism.mission_transaction_work_spine.validates_public_mission_transaction_bundle"
  ],
  "mapping_basis": "This markdown maps Work Ledger instance refinement to std_microcosm_work_ledger, the work_ledger doctrine kind, and mission transaction work spine because session and claim corrections must be tied to read receipts, preflight state, append evidence, and scoped commit evidence rather than status-board prose."
}
```

## Authority Boundary

This skill source governs bounded Work Ledger instance correction only. It does not authorize live mutation, claim release, Git mutation, provider calls, private content exposure, release, or completion proof beyond the evidence it repairs.

Anti-claims:

- Rewording a heartbeat or closeout state is not evidence that a session is complete.
- A generated Work Ledger view can expose coordination state, but source rows, read receipts, and append evidence settle authority.
- Work Ledger refinement must not collapse active claims, blockers, or collision state into a green projection.
