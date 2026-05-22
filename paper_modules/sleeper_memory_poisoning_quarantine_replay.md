# Sleeper Memory Poisoning Quarantine Replay

This module is the public Microcosm projection of a persistent-memory security
claim contract. It is a synthetic replay fixture, not a live memory product,
live user memory import, benchmark security result, private memory export, or
release claim.

The fixture models four public sessions: a poisoned source capsule is seen, a
memory write proposal is quarantined, later retrieval is blocked before action,
and rollback plus cold rerun proves the poisoned memory is absent at the receipt
boundary. The claim is admitted only when source capsule refs, provenance refs,
quarantine verdicts, classifier labels, retrieval influence gates, rollback
audit refs, rerun receipts, negative cases, and authority ceilings line up.

## Public Mechanics

- Memory write proposals require source capsule and provenance refs before
  admission.
- Untrusted source context with a sleeper-poisoning classifier label must be
  quarantined; it cannot become trusted memory.
- Later retrieval of quarantined memory must be explicitly blocked before any
  action can use it.
- Rollback language requires a deletion audit ref and cold rerun receipt showing
  the poisoned memory is absent.
- Private memory body export, live user memory claims, raw transcript export,
  memory writes without provenance, trusted promotion from untrusted context,
  deletion without audit, final-answer-only grading, and unmetered poison
  influence are expected falsification fixtures.

## Anti-Claim

This module does not run live memory, claim memory product quality, import live
user memory, export private memory bodies or raw transcripts, promote untrusted
context into trusted memory, call providers, mutate source, claim benchmark
security, publish results, or authorize release.
