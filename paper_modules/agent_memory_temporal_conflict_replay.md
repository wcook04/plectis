# Agent Memory Temporal-Conflict Replay

This module is the public Microcosm projection of an agent-memory honesty
contract. It is a synthetic replay fixture, not a live memory product, private
transcript export, source-authority claim, or release claim.

The fixture models three public episodes: episode A records a scoped preference
and a tool-result fact, episode B updates the preference scope and deletes the
now-stale fact through conflict-edge and downgrade receipts, and episode C
replays the task with memory enabled and disabled. The replay is admitted only
when ADD, UPDATE, DELETE, and NOOP decisions, metadata-only private refs,
evidence handles, cold replay refs, and an answer-delta receipt line up.

## Public Mechanics

- Memory update claims require route refs, evidence handles, and explicit
  ADD/UPDATE/DELETE/NOOP decisions.
- Updates and deletes that touch older memory require temporal conflict-edge
  refs plus stale-downgrade refs before memory can affect replay credit.
- Private thread references are metadata-only; transcript bodies and private
  memory candidate bodies stay omitted.
- Utility language requires paired memory-enabled and memory-disabled cold
  replay receipts, not final-answer-only comparison.
- Raw transcript export, private candidate auto-promotion, stale preference
  override, memory-as-source-authority, vector recall without evidence,
  final-answer-only memory credit, and active-injection authority are expected
  falsification fixtures.

## Anti-Claim

This module does not run live memory, claim memory product quality, export
private transcripts, auto-promote private candidates, treat memory recall as
source authority, adopt active injection, call providers, mutate source,
publish results, or authorize release.
