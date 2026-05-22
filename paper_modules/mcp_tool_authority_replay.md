# MCP Tool Authority Replay

This module is the public Microcosm projection of a tool-authority claim
contract. It is a synthetic MCP-like replay fixture, not a live MCP account
test, provider call, credential-handling certification, benchmark security
result, or release claim.

The fixture models three public tools: a readonly docs lookup, a write-capable
ticket update, and an untrusted result source. The claim is admitted only when
tool manifest scope refs, call argument hashes, approval token refs, side-effect
ledger refs, rollback receipts, untrusted-output instruction/data splits, cold
replay receipts, negative cases, and authority ceilings line up.

## Public Mechanics

- Every tool call must bind to a narrow capability scope ref before admission.
- Write-capable calls require approval token refs, side-effect ledger refs, and
  rollback receipt refs.
- Untrusted tool output is data, not instruction, and must cite an
  instruction/data split ref.
- Call arguments, tool outputs, account refs, and result bodies stay redacted or
  metadata-only.
- Overbroad scopes, hidden credential export, tool-output-as-instruction,
  unapproved side effects, live account access, final-answer-only grading,
  missing rollback receipts, and unredacted tool payloads are expected
  falsification fixtures.

## Anti-Claim

This module does not access live MCP accounts, export credentials or provider
payloads, obey tool output as instruction, run live tools, mutate source, claim
benchmark safety, publish results, or authorize release.
