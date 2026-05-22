# Agent Benchmark Integrity Anti-Gaming Replay

This module is the public Microcosm projection of the rule that agent benchmark
claims must be replay-backed before they are score-backed. It is a synthetic
integrity organ, not a benchmark runner.

The fixture models a repository repair benchmark with public case ids, task and
patch hashes, locked evaluator ids, evaluator config hashes, file-access log
refs, contamination-check refs, trusted-reference score refs, output-replay
refs, and held-out guard ids. It deliberately keeps issue bodies, oracle patch
bodies, hidden-gold answers, provider payloads, and live repository paths out of
the public boundary.

## Public Mechanics

- A replay cannot pass unless the evaluator id and config hash are locked.
- File-access logs, contamination checks, trusted references, and output replay
  refs are required before any benchmark-style language can be considered.
- Train/test leakage, hidden-gold access, oracle patch bodies, provider
  payloads, final-answer-only grading, pass-k cherry-picking, misleading tests,
  private issue bodies, and score overclaims are quarantine cases.
- `integrity_pass` is evidence that a synthetic replay respected the boundary,
  not evidence of a SWE-bench score or live agent capability.
- Receipts expose ids, refs, verdicts, counts, negative cases, and authority
  ceilings only.

## Anti-Claim

This module does not claim benchmark performance, run providers, expose private
issue or oracle patch bodies, access hidden-gold answers, mutate live
repositories, publish results, host a benchmark, or authorize release.
